"""
scripts/ingest_jes.py — JES factor extraction pipeline (PIPE-03, PIPE-04).

Walks data/Job_evaluation/*.txt files, extracts OG code from the filename, calls Ollama via
instructor for structured factor extraction, and upserts jes_factors rows keyed by
(og_code, factor_name). Application Guidelines files (FB has both Standard and Guidelines)
are skipped — only the Job Evaluation Standard contains factor data.

Usage:
    python scripts/ingest_jes.py \\
        --db-path /home/charles/job_description_builder/app.db \\
        --data-dir /home/charles/job_description_builder/data/Job_evaluation \\
        --model gemma4:31b \\
        --version-label "JES v1.0"

Re-running on unchanged files is fully idempotent (skips LLM extraction).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic models for instructor-validated LLM output
# ---------------------------------------------------------------------------

class DegreeDescriptor(BaseModel):
    degree: str = Field(..., description="Degree label, e.g. 'D1', 'D2'")
    text: str = Field(..., min_length=1)
    points: int = Field(..., ge=0)


class ExtractedFactor(BaseModel):
    factor_name: str = Field(..., min_length=1)
    factor_definition: str | None = None
    degree_descriptors: list[DegreeDescriptor]
    point_values: dict[str, int]
    max_points: int = Field(..., ge=0)


class JESExtractionResult(BaseModel):
    factors: list[ExtractedFactor]


# ---------------------------------------------------------------------------
# Security: path traversal guard (T-3-01)
# ---------------------------------------------------------------------------

def validate_db_path(db_path: str) -> Path:
    """Resolve --db-path and reject paths outside project root."""
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
# Connection factory
# ---------------------------------------------------------------------------

def load_connection(db_path: str) -> sqlite3.Connection:
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
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---------------------------------------------------------------------------
# Stage 1: OG code extraction + Application Guidelines filter
# ---------------------------------------------------------------------------

def extract_og_code(filename: str) -> str:
    """
    First whitespace-delimited token of the filename stem is the OG code.
    E.g. 'EC Economics and Social Science Services - Job Evaluation Standard 2017.txt' -> 'EC'.
    """
    stem = Path(filename).stem
    return stem.split()[0] if stem.strip() else ""


def is_application_guidelines(filename: str) -> bool:
    """FB has two files; only the 'Job Evaluation Standard' contains factor data."""
    name = filename.lower()
    return "application guidelines" in name or "application_guidelines" in name


# ---------------------------------------------------------------------------
# Stage 2: LLM extraction (instructor + Pydantic + 3 retries)
# ---------------------------------------------------------------------------

def extract_factors_via_llm(
    text: str,
    og_code: str,
    model: str = "gemma4:31b",
    max_retries: int = 3,
) -> list[dict]:
    """
    Call Ollama via instructor to extract structured JES factors.
    Returns list of dicts: {factor_name, factor_definition, degree_descriptors, point_values, max_points}.
    """
    import instructor
    from openai import OpenAI

    client = instructor.from_openai(
        OpenAI(base_url="http://localhost:11434/v1", api_key="ollama"),
        mode=instructor.Mode.JSON,
    )

    prompt = (
        f"You are extracting Job Evaluation Standard factors for the {og_code} occupational group "
        f"of the Canadian federal public service.\n\n"
        f"From the JES text below, extract every factor (also called 'element'). For each factor return:\n"
        f"  - factor_name: e.g. 'Decision Making', 'Working Conditions'\n"
        f"  - factor_definition: the descriptive paragraph defining what the factor measures\n"
        f"  - degree_descriptors: list of {{degree, text, points}} entries for each degree (D1, D2, ...)\n"
        f"  - point_values: mapping {{'D1': 5, 'D2': 15, ...}} from degree label to point value\n"
        f"  - max_points: the maximum point value across all degrees of this factor\n\n"
        f"TEXT:\n{text[:40000]}"
    )

    result: JESExtractionResult = client.chat.completions.create(
        model=model,
        response_model=JESExtractionResult,
        max_retries=max_retries,
        messages=[{"role": "user", "content": prompt}],
    )
    return [f.model_dump() for f in result.factors]


# ---------------------------------------------------------------------------
# Stage 3: source_documents upsert (PIPE-04)
# ---------------------------------------------------------------------------

def upsert_source_document(
    con: sqlite3.Connection,
    source_name: str,
    version_label: str,
    content_hash: str,
) -> None:
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
# Stage 4: jes_factors upsert — INSERT OR IGNORE (PIPE-03)
# ---------------------------------------------------------------------------

def upsert_jes_factors(
    con: sqlite3.Connection,
    og_code: str,
    factors: list[dict],
    source_hash: str,
) -> None:
    """
    Insert factors into jes_factors keyed by (og_code, factor_name).
    UNIQUE constraint + INSERT OR IGNORE = idempotent.
    degree_descriptors and point_values stored as JSON TEXT.
    """
    for f in factors:
        factor_name = (f.get("factor_name") or "").strip()
        if not factor_name:
            continue
        descriptors = f.get("degree_descriptors") or []
        point_values = f.get("point_values") or {}
        max_points = int(f.get("max_points") or 0)
        con.execute(
            """INSERT OR IGNORE INTO jes_factors(
                   og_code, factor_name, factor_definition,
                   degree_descriptors, point_values, max_points, source_hash
               ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                og_code,
                factor_name,
                f.get("factor_definition"),
                json.dumps(descriptors),
                json.dumps(point_values),
                max_points,
                source_hash,
            ],
        )
    con.commit()


# ---------------------------------------------------------------------------
# Stage 5: per-file processing
# ---------------------------------------------------------------------------

def _derived_count_for_og(con: sqlite3.Connection, og_code: str) -> int:
    return con.execute(
        "SELECT COUNT(*) FROM jes_factors WHERE og_code = ?", [og_code]
    ).fetchone()[0]


def process_one_jes(
    con: sqlite3.Connection,
    jes_path: Path,
    model: str,
    version_label: str,
) -> tuple[str, int]:
    """Returns (og_code, factors_inserted_or_skipped). Skips on unchanged hash."""
    file_hash = compute_file_hash(str(jes_path))
    source_name = jes_path.name
    og_code = extract_og_code(source_name)
    if not og_code:
        print(f"  [{source_name}] cannot derive OG code; skipping", flush=True)
        return "", 0

    upsert_source_document(con, source_name, version_label, file_hash)

    existing = con.execute(
        "SELECT content_hash FROM source_documents WHERE source_name = ?",
        [source_name],
    ).fetchone()
    if existing and existing["content_hash"] == file_hash and _derived_count_for_og(con, og_code) > 0:
        print(f"  [{og_code}] Unchanged — skipping LLM extraction", flush=True)
        return og_code, 0

    with open(jes_path, encoding="utf-8") as f:
        text = f.read()

    print(f"  [{og_code}] extracting factors via {model} ...", flush=True)
    factors = extract_factors_via_llm(text, og_code, model=model)
    upsert_jes_factors(con, og_code, factors, file_hash)
    return og_code, len(factors)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest JES TXT files into jes_factors (PIPE-03).",
    )
    parser.add_argument("--db-path", required=True,
                        help="SQLite database path (must be under project root)")
    parser.add_argument("--data-dir", required=True,
                        help="Path to data/Job_evaluation/ directory")
    parser.add_argument("--model", default="gemma4:31b",
                        help="Ollama model for factor extraction (default: gemma4:31b)")
    parser.add_argument("--version-label", default="JES v1.0",
                        help="Version label stored in source_documents")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = validate_db_path(args.db_path)

    data_dir = Path(args.data_dir).resolve()
    if not data_dir.is_dir():
        print(f"Error: data directory not found: {data_dir}", file=sys.stderr)
        return 1

    print(f"[1/3] Connecting to {db_path} ...", flush=True)
    con = load_connection(str(db_path))
    from app.db import create_schema
    create_schema(con)

    print(f"[2/3] Discovering JES TXT files under {data_dir} ...", flush=True)
    all_files = sorted(p for p in data_dir.glob("*.txt") if p.is_file())
    jes_files = [p for p in all_files if not is_application_guidelines(p.name)]
    skipped = [p.name for p in all_files if is_application_guidelines(p.name)]
    print(f"  Found {len(jes_files)} JES Standard files; skipping {len(skipped)} Application Guidelines")
    for s in skipped:
        print(f"    skipped: {s}")

    print(f"[3/3] Extracting factors via {args.model} ...", flush=True)
    for i, jes_path in enumerate(jes_files, 1):
        print(f"  ({i}/{len(jes_files)}) {jes_path.name}", flush=True)
        process_one_jes(con, jes_path, args.model, args.version_label)

    factor_total = con.execute("SELECT COUNT(*) FROM jes_factors").fetchone()[0]
    print(f"\nIngest complete: jes_factors {factor_total:,} rows", flush=True)

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
