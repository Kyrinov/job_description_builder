"""
scripts/ingest_ca.py — Collective Agreement clause extraction pipeline (PIPE-02, CA-01, PIPE-04).

Walks data/agreements/{OG}/{OG}_full.json files, parses index_record.abbreviation to resolve
OG codes (handling multi-OG CAs like "(IT)(CS)"), selects relevant sections, calls Ollama via
instructor for structured clause extraction, and upserts ca_clauses rows keyed by og_code.

Usage:
    python scripts/ingest_ca.py \\
        --db-path /home/charles/job_description_builder/app.db \\
        --data-dir /home/charles/job_description_builder/data \\
        --model gemma4:31b \\
        --version-label "CA 2023-2026 v1.0"

Re-running on unchanged files is fully idempotent (skips LLM extraction).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# Ensure project root is on sys.path so imports from app.* work
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AGREEMENTS_SUBDIR = "agreements"

# Section title keywords that indicate restriction/scope/exclusion content
RELEVANT_SECTION_KEYWORDS = (
    "scope", "purpose", "application", "restriction", "definition",
    "duties", "statement of duties", "exclusion", "interpretation",
)

VALID_CLAUSE_TYPES = ("restriction", "scope", "exclusion", "definition")


# ---------------------------------------------------------------------------
# Pydantic models for instructor-validated LLM output
# ---------------------------------------------------------------------------

class ExtractedClause(BaseModel):
    clause_type: str = Field(..., description="One of: restriction, scope, exclusion, definition")
    article_ref: str = Field(..., description="Article or part reference, e.g. 'Article 1'")
    clause_text: str = Field(..., min_length=10)


class CAExtractionResult(BaseModel):
    clauses: list[ExtractedClause]


# ---------------------------------------------------------------------------
# Security: path traversal guard (T-3-01)
# ---------------------------------------------------------------------------

def validate_db_path(db_path: str) -> Path:
    """Resolve --db-path and reject paths outside project root. Mirrors ingest_noc.py."""
    resolved = Path(db_path).resolve()
    project_root = Path(__file__).resolve().parent.parent
    try:
        resolved.relative_to(project_root)
        return resolved
    except ValueError:
        print(
            f"Error: --db-path must be under the project root ({project_root}).\n"
            f"Got: {resolved!r}\nPath traversal is not permitted.",
            file=sys.stderr,
        )
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Connection factory (no app.config import)
# ---------------------------------------------------------------------------

def load_connection(db_path: str) -> sqlite3.Connection:
    """Open SQLite + register sqlite-vec. Mirrors ingest_noc.py."""
    import sqlite_vec
    con = sqlite3.connect(str(db_path), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    return con


# ---------------------------------------------------------------------------
# Stage 0: Content hash (PIPE-04)
# ---------------------------------------------------------------------------

def compute_file_hash(path: str) -> str:
    """SHA-256 of raw file bytes."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---------------------------------------------------------------------------
# Stage 1: Parse OG codes from index_record.abbreviation
# ---------------------------------------------------------------------------

_OG_ABBR_PATTERN = re.compile(r"\(([A-Z]{1,4})\)")


def parse_og_codes(abbreviation: str) -> list[str]:
    """
    Extract OG codes from an index_record.abbreviation field.

    Examples:
      "(EC)"      -> ["EC"]
      "(IT)(CS)"  -> ["IT", "CS"]
      "(CT)(FI)"  -> ["CT", "FI"]
      "(LP)(LA)"  -> ["LP", "LA"]
      ""          -> []  (caller must handle)
    """
    if not abbreviation:
        return []
    return _OG_ABBR_PATTERN.findall(abbreviation)


# ---------------------------------------------------------------------------
# Stage 2: Section selection — reduce LLM input size
# ---------------------------------------------------------------------------

def select_relevant_sections(ca_json: dict) -> str:
    """
    Concatenate text of sections whose title matches RELEVANT_SECTION_KEYWORDS.
    Falls back to preamble + first 3 sections if no keyword matches.
    """
    sections = ca_json.get("sections", []) or []
    matching: list[str] = []
    for s in sections:
        title = (s.get("title") or "").lower()
        if any(kw in title for kw in RELEVANT_SECTION_KEYWORDS):
            text = s.get("text") or ""
            matching.append(f"=== {s.get('title')} ===\n{text}")
    if matching:
        return "\n\n".join(matching)
    # Fallback: preamble + first 3 sections
    preamble = ca_json.get("preamble") or ""
    fallback = [preamble]
    for s in sections[:3]:
        fallback.append(f"=== {s.get('title')} ===\n{s.get('text') or ''}")
    return "\n\n".join(fallback)


# ---------------------------------------------------------------------------
# Model lifecycle helpers
# ---------------------------------------------------------------------------

def unload_model(model: str, base_url: str = "http://localhost:11434") -> None:
    """Force-unload the model from VRAM to reset KV cache state between files."""
    import httpx
    try:
        httpx.post(
            f"{base_url.rstrip('/')}/api/chat",
            json={"model": model, "messages": [{"role": "user", "content": ""}],
                  "stream": False, "keep_alive": 0},
            timeout=15,
        )
    except Exception:
        pass  # Best-effort — if Ollama is hung this will fail silently


# ---------------------------------------------------------------------------
# Stage 3: LLM extraction (httpx + Pydantic)
# ---------------------------------------------------------------------------

def extract_clauses_via_llm(
    text: str,
    og_codes: list[str],
    model: str = "gemma4:31b",
    num_ctx: int = 32768,
    num_predict: int = 4096,
    base_url: str = "http://localhost:11434",
    request_timeout: float = 600.0,
    max_retries: int = 3,
) -> list[dict]:
    """
    Call Ollama native /api/chat endpoint to extract structured clauses.

    Returns list of {clause_type, article_ref, clause_text} dicts.
    Wrapped so tests can patch this single function to inject synthetic clauses.
    """
    import httpx

    prompt = (
        f"You are extracting clauses from a Canadian federal public service collective agreement "
        f"for occupational group(s) {', '.join(og_codes)}.\n\n"
        f"From the text below, extract every clause that is one of: restriction, scope, exclusion, definition.\n"
        f"  - restriction: limits on duties, hours, transfers, or assignments\n"
        f"  - scope:       statements of who and what the agreement covers\n"
        f"  - exclusion:   classes of employees excluded from coverage\n"
        f"  - definition:  defined terms used in the agreement\n\n"
        f"For each, return article_ref (e.g. 'Article 7'), clause_type, and the verbatim clause_text "
        f"(minimum 10 characters).\n\n"
        f"TEXT:\n{text[:30000]}"
    )

    endpoint = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": CAExtractionResult.model_json_schema(),
        "options": {"num_ctx": num_ctx, "num_predict": num_predict, "temperature": 0},
    }

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = httpx.post(endpoint, json=payload, timeout=request_timeout)
            response.raise_for_status()
            content = response.json()["message"]["content"]
            result = CAExtractionResult.model_validate_json(content)
            return [c.model_dump() for c in result.clauses if c.clause_type in VALID_CLAUSE_TYPES]
        except Exception as exc:
            last_error = exc
            print(f"  request attempt {attempt}/{max_retries} failed: {exc}", flush=True)

    raise RuntimeError(f"extraction failed after {max_retries} attempts: {last_error}") from last_error


# ---------------------------------------------------------------------------
# Stage 4: source_documents upsert (PIPE-04) — copied from ingest_noc.py
# ---------------------------------------------------------------------------

def upsert_source_document(
    con: sqlite3.Connection,
    source_name: str,
    version_label: str,
    content_hash: str,
) -> None:
    """Record a source document with content hash + version label (PIPE-04)."""
    existing = con.execute(
        "SELECT content_hash FROM source_documents WHERE source_name = ?",
        [source_name],
    ).fetchone()

    if existing is None:
        con.execute(
            """INSERT INTO source_documents(source_name, version_label, content_hash, ingested_at)
               VALUES (?, ?, ?, datetime('now'))""",
            [source_name, version_label, content_hash],
        )
    elif existing["content_hash"] != content_hash:
        con.execute(
            """UPDATE source_documents
               SET content_hash = ?, version_label = ?, ingested_at = datetime('now')
               WHERE source_name = ?""",
            [content_hash, version_label, source_name],
        )
    con.commit()


# ---------------------------------------------------------------------------
# Stage 5: ca_clauses upsert — INSERT OR IGNORE per OG code (PIPE-02, CA-01)
# ---------------------------------------------------------------------------

def upsert_ca_clauses(
    con: sqlite3.Connection,
    og_codes: list[str],
    clauses: list[dict],
    source_hash: str,
) -> None:
    """
    Insert clauses into ca_clauses keyed by og_code.
    For multi-OG CAs, duplicates the same clause set across each OG code.
    UNIQUE(og_code, clause_type, article_ref, clause_text) + INSERT OR IGNORE = idempotent.
    """
    for og_code in og_codes:
        for clause in clauses:
            ctype = clause.get("clause_type", "").strip().lower()
            if ctype not in VALID_CLAUSE_TYPES:
                continue
            article_ref = (clause.get("article_ref") or "").strip()
            clause_text = (clause.get("clause_text") or "").strip()
            if not article_ref or not clause_text:
                continue
            con.execute(
                """INSERT OR IGNORE INTO ca_clauses(
                       og_code, clause_type, article_ref, clause_text, source_hash
                   ) VALUES (?, ?, ?, ?, ?)""",
                [og_code, ctype, article_ref, clause_text, source_hash],
            )
    con.commit()


# ---------------------------------------------------------------------------
# Stage 6: per-CA processing loop with hash-check skip
# ---------------------------------------------------------------------------

def _derived_count_for_og(con: sqlite3.Connection, og_code: str) -> int:
    return con.execute(
        "SELECT COUNT(*) FROM ca_clauses WHERE og_code = ?", [og_code]
    ).fetchone()[0]


def process_one_ca(
    con: sqlite3.Connection,
    ca_json_path: Path,
    model: str,
    version_label: str,
    num_ctx: int = 32768,
    num_predict: int = 4096,
    base_url: str = "http://localhost:11434",
) -> tuple[list[str], int]:
    """
    Returns (og_codes, clauses_inserted_or_skipped_count).
    Skips LLM if hash unchanged and at least one ca_clauses row exists for every OG.
    """
    file_hash = compute_file_hash(str(ca_json_path))
    source_name = ca_json_path.name

    with open(ca_json_path, encoding="utf-8") as f:
        ca_json = json.load(f)

    abbreviation = ca_json.get("index_record", {}).get("abbreviation") or ""
    og_codes = parse_og_codes(abbreviation)
    if not og_codes:
        # Fallback: use the parent directory name as the OG code
        og_codes = [ca_json_path.parent.name]
        print(f"  [{source_name}] no abbreviation found; using dir name {og_codes[0]!r}", flush=True)

    upsert_source_document(con, source_name, version_label, file_hash)

    # Idempotency: skip if hash + rows already exist for every OG code
    existing = con.execute(
        "SELECT content_hash FROM source_documents WHERE source_name = ?",
        [source_name],
    ).fetchone()
    all_present = all(_derived_count_for_og(con, og) > 0 for og in og_codes)
    if existing and existing["content_hash"] == file_hash and all_present:
        print(f"  [{'+'.join(og_codes)}] Unchanged — skipping LLM extraction", flush=True)
        return og_codes, 0

    text = select_relevant_sections(ca_json)
    print(f"  [{'+'.join(og_codes)}] extracting clauses via {model} ...", flush=True)
    clauses = extract_clauses_via_llm(text, og_codes, model=model, num_ctx=num_ctx, num_predict=num_predict, base_url=base_url)
    upsert_ca_clauses(con, og_codes, clauses, file_hash)
    return og_codes, len(clauses) * len(og_codes)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest CA JSONs into ca_clauses (PIPE-02, CA-01).",
    )
    parser.add_argument("--db-path", required=True,
                        help="SQLite database path (must be under project root)")
    parser.add_argument("--data-dir", required=True,
                        help="Project data directory (contains agreements/<OG>/ subdirs)")
    parser.add_argument("--model", default="gemma4:31b",
                        help="Ollama model for clause extraction (default: gemma4:31b)")
    parser.add_argument("--version-label", default="CA 2023-2026 v1.0",
                        help="Version label stored in source_documents")
    parser.add_argument("--num-ctx", type=int, default=32768,
                        help="Ollama context window size (default: 32768)")
    parser.add_argument("--num-predict", type=int, default=4096,
                        help="Maximum output tokens per call (default: 4096)")
    parser.add_argument("--base-url", default="http://localhost:11434",
                        help="Ollama API endpoint (default: http://localhost:11434)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = validate_db_path(args.db_path)

    data_dir = Path(args.data_dir).resolve()
    agreements_root = data_dir / AGREEMENTS_SUBDIR
    if not agreements_root.is_dir():
        print(f"Error: agreements directory not found: {agreements_root}", file=sys.stderr)
        return 1

    print(f"[1/3] Connecting to {db_path} ...", flush=True)
    con = load_connection(str(db_path))
    from app.db import create_schema
    create_schema(con)

    print(f"[2/3] Discovering CA JSON files under {agreements_root} ...", flush=True)
    ca_files = sorted(p for p in agreements_root.glob("*/*_full.json") if p.is_file())
    print(f"  Found {len(ca_files)} CA JSON files")

    print(f"[3/3] Extracting clauses via {args.model} ...", flush=True)
    total_inserted = 0
    for i, ca_path in enumerate(ca_files, 1):
        print(f"  ({i}/{len(ca_files)}) {ca_path.name}", flush=True)
        _, inserted = process_one_ca(con, ca_path, args.model, args.version_label, args.num_ctx, args.num_predict, args.base_url)
        total_inserted += inserted
        unload_model(args.model, args.base_url)

    ca_total = con.execute("SELECT COUNT(*) FROM ca_clauses").fetchone()[0]
    print(f"\nIngest complete: ca_clauses {ca_total:,} rows ({total_inserted} new/refreshed this run)", flush=True)

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
