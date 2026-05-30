"""
scripts/ingest_jes.py — JES factor extraction pipeline (PIPE-03, PIPE-04).

Walks data/Job_evaluation files, extracts OG code from the filename, calls Ollama for
structured factor extraction, and upserts jes_factors rows keyed by
(og_code, factor_name). Application Guidelines files (FB has both Standard and Guidelines)
are skipped — only the Job Evaluation Standard contains factor data.

Pre-processing applied to each file before LLM extraction:
  1. strip_web_boilerplate() — removes the Canada.ca navigation header present in
     web-scraped files (IT, LP, MT, LC, FS, NU, NT, PO, PS, SW, WP). Clean-format
     files (CT, EC, ED, EX, FB) are unaffected.
  2. strip_benchmark_section() — truncates individual benchmark/IPD position
     descriptions from the end of web-scraped files. These are LLM noise (the prompt
     already skips them) but consume multiple chunks in long files.

In addition to factor extraction, a separate pass extracts group-level metadata
(group definition, inclusions, exclusions, methodology) and stores it in the
jes_og_metadata table.

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
import re
import sqlite3
import sys
from pathlib import Path

from pydantic import BaseModel, Field

# Ensure project root is on sys.path so imports from app.* work
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_NUM_CTX = 65536
DEFAULT_NUM_PREDICT = 4096
DEFAULT_CHUNK_CHARS = 12000
DEFAULT_CHUNK_OVERLAP = 1500


# ---------------------------------------------------------------------------
# Pydantic models for instructor-validated LLM output
# ---------------------------------------------------------------------------

class DegreeDescriptor(BaseModel):
    degree: str = Field(..., description="Degree label, e.g. 'D1', 'D2', 'Aa1', 'F'")
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


class GroupMetadataResult(BaseModel):
    group_definition: str = Field(default="", description="Formal definition of the occupational group")
    inclusions: str = Field(default="", description="Verbatim inclusions text; empty string if absent")
    exclusions: str = Field(default="", description="Verbatim exclusions text; empty string if absent")
    methodology: str = Field(
        default="",
        description="e.g. 'point-rating', 'Hay Guide Chart', 'level-descriptions'",
    )
    subgroups: list[str] = Field(
        default_factory=list,
        description="Named subgroups if the standard defines them, e.g. ['CT-IAU', 'CT-FIN']",
    )


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
# Pre-processing: strip web boilerplate and benchmark sections
# ---------------------------------------------------------------------------

# Canada.ca navigation boilerplate is present in web-scraped files that were not
# manually cleaned. Detected by the first non-empty line being "Skip to main content".
_WEB_NAV_MARKER = re.compile(r"^\s*Skip to main content", re.MULTILINE)

# Individual benchmark / IPD position descriptions start at these section markers.
# These come after the rating scales and are noisy for factor extraction.
_BENCHMARK_SECTION_RE = re.compile(
    r"^(Benchmark \d+:\s+\S|Illustrative Position Descriptions Index\s*$)",
    re.MULTILINE,
)


def strip_web_boilerplate(text: str) -> str:
    """
    Remove Canada.ca navigation header from web-scraped JES files.

    Web-scraped files begin with ~18 lines of navigation chrome:
      "Skip to main content", language selection, Government of Canada header,
      breadcrumb ("Canada.ca Treasury Board...").
    The actual document title follows immediately after. Clean-format files (those
    beginning with "SOURCE: https://") are returned unchanged.
    """
    if not _WEB_NAV_MARKER.search(text):
        return text

    lines = text.splitlines(keepends=True)
    breadcrumb_seen = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if "Canada.ca" in stripped and "Treasury Board" in stripped:
            breadcrumb_seen = True
            continue
        if breadcrumb_seen and stripped and not any(
            stripped.startswith(kw)
            for kw in ("Skip", "Language", "Français", "Government", "Search", "Menu", "You are here")
        ):
            return "".join(lines[i:])
    return text


def strip_benchmark_section(text: str) -> tuple[str, str]:
    """
    Split text into (rating_scales_text, benchmarks_text).

    Individual benchmark position descriptions and illustrative position descriptions
    (IPDs) appear after the rating scales. They are expensive LLM tokens the model is
    instructed to skip anyway. Returns the rating-scales portion for factor extraction;
    the benchmark portion is discarded.

    Files that have no benchmark section are returned whole in the first element.
    """
    m = _BENCHMARK_SECTION_RE.search(text)
    if m is None:
        return text, ""
    cut = m.start()
    return text[:cut].strip(), text[cut:].strip()


def preprocess_jes_text(text: str) -> str:
    """Apply both pre-processing stages and return the cleaned text."""
    text = strip_web_boilerplate(text)
    text, _ = strip_benchmark_section(text)
    return text


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


def discover_jes_files(data_dir: Path) -> tuple[list[Path], list[str]]:
    """Return all direct child JES source files, including extensionless files."""
    all_files = sorted(p for p in data_dir.iterdir() if p.is_file() and not p.name.startswith("."))
    jes_files = [p for p in all_files if not is_application_guidelines(p.name)]
    skipped = [p.name for p in all_files if is_application_guidelines(p.name)]
    return jes_files, skipped


# ---------------------------------------------------------------------------
# Stage 2: Chunking + LLM extraction (Ollama schema output + Pydantic validation)
# ---------------------------------------------------------------------------

def _tail_overlap(text: str, overlap_chars: int) -> str:
    if overlap_chars <= 0 or len(text) <= overlap_chars:
        return text
    tail = text[-overlap_chars:]
    paragraph_boundary = tail.find("\n\n")
    if paragraph_boundary >= 0:
        return tail[paragraph_boundary + 2:].lstrip()
    return tail.lstrip()


def chunk_text(text: str, max_chars: int = DEFAULT_CHUNK_CHARS, overlap_chars: int = DEFAULT_CHUNK_OVERLAP) -> list[str]:
    """
    Split a full JES document into paragraph-aware chunks.

    Overlap preserves factor/degree context across chunk boundaries while keeping
    each LLM call bounded and observable.
    """
    stripped = text.strip()
    if not stripped:
        return []
    if len(stripped) <= max_chars:
        return [stripped]

    blocks = stripped.splitlines(keepends=True)
    chunks: list[str] = []
    current = ""

    for block in blocks:
        if current and len(current) + len(block) > max_chars:
            chunks.append(current.strip())
            current = _tail_overlap(current, overlap_chars)
        current += block

    if current.strip():
        chunks.append(current.strip())
    return chunks


def _merge_factor(existing: dict, incoming: dict) -> dict:
    """Merge duplicate factor records produced by overlapping chunks."""
    if len(incoming.get("factor_definition") or "") > len(existing.get("factor_definition") or ""):
        existing["factor_definition"] = incoming.get("factor_definition")

    descriptors_by_degree: dict[str, dict] = {}
    for descriptor in existing.get("degree_descriptors") or []:
        degree = str(descriptor.get("degree") or "").strip()
        if degree:
            descriptors_by_degree[degree] = descriptor
    for descriptor in incoming.get("degree_descriptors") or []:
        degree = str(descriptor.get("degree") or "").strip()
        if not degree:
            continue
        previous = descriptors_by_degree.get(degree)
        if previous is None or len(descriptor.get("text") or "") > len(previous.get("text") or ""):
            descriptors_by_degree[degree] = descriptor

    point_values = dict(existing.get("point_values") or {})
    point_values.update(incoming.get("point_values") or {})

    existing["degree_descriptors"] = list(descriptors_by_degree.values())
    existing["point_values"] = point_values
    existing["max_points"] = max(int(existing.get("max_points") or 0), int(incoming.get("max_points") or 0))
    return existing


def merge_extracted_factors(factors: list[dict]) -> list[dict]:
    """Collapse duplicate factors from adjacent chunks into one record per factor name."""
    merged: dict[str, dict] = {}
    for factor in factors:
        factor_name = (factor.get("factor_name") or "").strip()
        if not factor_name:
            continue
        factor["factor_name"] = factor_name
        key = factor_name.casefold()
        if key in merged:
            merged[key] = _merge_factor(merged[key], factor)
        else:
            merged[key] = factor
    return list(merged.values())


# ---------------------------------------------------------------------------
# Stage 3: LLM extraction (single chunk)
# ---------------------------------------------------------------------------

def extract_factors_via_llm(
    text: str,
    og_code: str,
    model: str = "gemma4:31b",
    num_ctx: int = DEFAULT_NUM_CTX,
    num_predict: int = DEFAULT_NUM_PREDICT,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    request_timeout: float = 1800.0,
    max_retries: int = 3,
) -> list[dict]:
    """
    Call Ollama to extract structured JES factors.
    Returns list of dicts: {factor_name, factor_definition, degree_descriptors, point_values, max_points}.
    """
    prompt = (
        f"You are extracting Job Evaluation Standard factors for the {og_code} occupational group "
        f"of the Canadian federal public service.\n\n"
        f"From the JES text chunk below, extract every complete factor (also called 'element') "
        f"that appears in this chunk. For each factor return:\n"
        f"  - factor_name: e.g. 'Decision Making', 'Working Conditions', 'Know-How'\n"
        f"  - factor_definition: the descriptive paragraph defining what the factor measures\n"
        f"  - degree_descriptors: list of {{degree, text, points}} entries for each degree\n"
        f"  - point_values: mapping from degree label to point value\n"
        f"  - max_points: the maximum point value across all degrees of this factor\n\n"
        f"Degree label conventions vary by standard:\n"
        f"  - Most standards use 'D1', 'D2', 'D3'... or 'Degree 1', 'Degree 2'...\n"
        f"  - The MT (Meteorology) standard uses a two-dimensional coordinate system with\n"
        f"    labels like 'Aa1', 'Ab2', 'Bc3'... — treat each coordinate as a separate degree\n"
        f"  - The EX (Executive) standard uses Hay Guide Chart sub-factor grades like\n"
        f"    'F-', 'F', 'F+', 'G-', 'G', 'G+' — extract each sub-factor (A, B, C) as a\n"
        f"    separate factor with these as its degrees\n"
        f"  - Some standards define nested sub-elements (e.g. 'Sensory Effort' and 'Physical\n"
        f"    Effort' under 'Effort') — extract each sub-element as a distinct factor\n\n"
        f"If the standard has subgroups (e.g. CT-IAU, CT-FIN), extract the factors for ALL\n"
        f"subgroups present in this chunk, prefixing the factor_name with the subgroup code\n"
        f"when needed for uniqueness (e.g. 'CT-IAU: Knowledge', 'CT-FIN: Knowledge').\n\n"
        f"Only extract formal job-evaluation factor or element rating scales. Do not extract\n"
        f"benchmark positions, illustrative positions, examples, notes to raters, glossary\n"
        f"entries, group definitions, inclusions, exclusions, or point-range tables as factors.\n"
        f"If this chunk has no complete factor or element rating scale, return an empty factors list.\n\n"
        f"TEXT CHUNK:\n{text}"
    )

    import httpx

    endpoint = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": JESExtractionResult.model_json_schema(),
        "options": {"num_ctx": num_ctx, "num_predict": num_predict, "temperature": 0},
    }

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = httpx.post(endpoint, json=payload, timeout=request_timeout)
            response.raise_for_status()
            content = response.json()["message"]["content"]
            result = JESExtractionResult.model_validate_json(content)
            return [f.model_dump() for f in result.factors]
        except Exception as exc:
            last_error = exc
            print(f"  [{og_code}] request attempt {attempt}/{max_retries} failed: {exc}", flush=True)

    raise RuntimeError(f"extraction failed after {max_retries} attempts: {last_error}") from last_error


def extract_group_metadata_via_llm(
    text: str,
    og_code: str,
    model: str = "gemma4:31b",
    num_ctx: int = DEFAULT_NUM_CTX,
    num_predict: int = DEFAULT_NUM_PREDICT,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    request_timeout: float = 1800.0,
    max_retries: int = 3,
) -> dict:
    """
    Extract occupational group metadata (definition, inclusions, exclusions, methodology).

    Only the first chunk of the document is needed — group definition and inclusions/
    exclusions always appear near the top of a JES standard.

    Returns a dict matching GroupMetadataResult fields.
    """
    prompt = (
        f"You are reading a Job Evaluation Standard (JES) for the {og_code} occupational group "
        f"of the Canadian federal public service.\n\n"
        f"Extract the following group-level metadata from the text:\n\n"
        f"  - group_definition: The formal definition of the occupational group (what types of "
        f"positions are in this group). This is usually under a heading like 'Group Definition', "
        f"'Occupational Group Definition', or 'Definition'.\n\n"
        f"  - inclusions: The verbatim text of the Inclusions section, listing specific activities "
        f"or position types that are explicitly included in the group. May appear under 'Inclusions', "
        f"'INCLUSIONS', or 'Notwithstanding the generality...' language. Include all bullet points "
        f"or numbered items verbatim. If absent, return null.\n\n"
        f"  - exclusions: The verbatim text of the Exclusions section, listing activities or position "
        f"types explicitly excluded from the group. May appear under 'Exclusions', 'EXCLUSIONS', or "
        f"'Positions excluded from...'. Include all bullet points or numbered items verbatim. "
        f"If absent, return null.\n\n"
        f"  - methodology: The evaluation methodology used. Common values:\n"
        f"    'point-rating' (most standards), 'Hay Guide Chart' (EX Executive), "
        f"    'level-descriptions' (standards that use narrative level descriptions rather than points).\n\n"
        f"  - subgroups: If the standard defines named subgroups (e.g. CT-IAU, CT-FIN, CT-EAV for "
        f"Comptrollership; ED-LAT, ED-EST, ED-EDS for Education), list their codes. "
        f"Return an empty list if there are no subgroups.\n\n"
        f"Do not infer or paraphrase — use verbatim text from the document for definitions, "
        f"inclusions, and exclusions.\n\n"
        f"TEXT:\n{text}"
    )

    import httpx

    endpoint = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": GroupMetadataResult.model_json_schema(),
        "options": {"num_ctx": num_ctx, "num_predict": num_predict, "temperature": 0},
    }

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = httpx.post(endpoint, json=payload, timeout=request_timeout)
            response.raise_for_status()
            content = response.json()["message"]["content"]
            result = GroupMetadataResult.model_validate_json(content)
            return result.model_dump()
        except Exception as exc:
            last_error = exc
            print(f"  [{og_code}] metadata attempt {attempt}/{max_retries} failed: {exc}", flush=True)

    raise RuntimeError(f"metadata extraction failed after {max_retries} attempts: {last_error}") from last_error


def extract_factors_from_chunks(
    text: str,
    og_code: str,
    model: str,
    num_ctx: int,
    num_predict: int,
    base_url: str,
    chunk_chars: int,
    chunk_overlap: int,
    request_timeout: float,
) -> list[dict]:
    """Extract factors from the full document in bounded chunks, then merge duplicates."""
    chunks = chunk_text(text, max_chars=chunk_chars, overlap_chars=chunk_overlap)
    if not chunks:
        return []

    all_factors: list[dict] = []
    print(f"  [{og_code}] split into {len(chunks)} chunk(s)", flush=True)
    for index, chunk in enumerate(chunks, 1):
        print(f"  [{og_code}] chunk {index}/{len(chunks)}: {len(chunk):,} chars", flush=True)
        try:
            factors = extract_factors_via_llm(
                chunk,
                og_code,
                model=model,
                num_ctx=num_ctx,
                num_predict=num_predict,
                base_url=base_url,
                request_timeout=request_timeout,
            )
        except Exception as exc:
            print(
                f"  [{og_code}] chunk {index}/{len(chunks)} FAILED (skipping): {exc}",
                flush=True,
            )
            continue
        print(f"  [{og_code}] chunk {index}/{len(chunks)} returned {len(factors)} factor(s)", flush=True)
        all_factors.extend(factors)

    return merge_extracted_factors(all_factors)


# ---------------------------------------------------------------------------
# Stage 4: source_documents upsert (PIPE-04)
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
# Stage 5: jes_factors replace/upsert (PIPE-03)
# ---------------------------------------------------------------------------

def replace_jes_factors(
    con: sqlite3.Connection,
    og_code: str,
    factors: list[dict],
    source_hash: str,
) -> None:
    """
    Replace factors for an OG after a successful full-document extraction.
    degree_descriptors and point_values stored as JSON TEXT.
    """
    with con:
        con.execute("DELETE FROM jes_factors WHERE og_code = ?", [og_code])
        for f in factors:
            factor_name = (f.get("factor_name") or "").strip()
            if not factor_name:
                continue
            descriptors = f.get("degree_descriptors") or []
            point_values = f.get("point_values") or {}
            max_points = int(f.get("max_points") or 0)
            con.execute(
                """INSERT INTO jes_factors(
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


def upsert_jes_factors(
    con: sqlite3.Connection,
    og_code: str,
    factors: list[dict],
    source_hash: str,
) -> None:
    """Backward-compatible helper used by tests and older callers."""
    replace_jes_factors(con, og_code, factors, source_hash)


def upsert_og_metadata(
    con: sqlite3.Connection,
    og_code: str,
    metadata: dict,
    source_hash: str,
) -> None:
    """Insert or replace occupational group metadata (definition, inclusions, exclusions)."""
    subgroups = metadata.get("subgroups") or []
    def _nonempty(v: str | None) -> str | None:
        return v if v else None

    with con:
        con.execute(
            """INSERT INTO jes_og_metadata(
                   og_code, group_definition, inclusions, exclusions,
                   methodology, subgroups, source_hash
               ) VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(og_code) DO UPDATE SET
                   group_definition = excluded.group_definition,
                   inclusions       = excluded.inclusions,
                   exclusions       = excluded.exclusions,
                   methodology      = excluded.methodology,
                   subgroups        = excluded.subgroups,
                   source_hash      = excluded.source_hash""",
            [
                og_code,
                _nonempty(metadata.get("group_definition")),
                _nonempty(metadata.get("inclusions")),
                _nonempty(metadata.get("exclusions")),
                _nonempty(metadata.get("methodology")),
                json.dumps(subgroups) if subgroups else None,
                source_hash,
            ],
        )


# ---------------------------------------------------------------------------
# Stage 6: per-file processing
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
    num_ctx: int,
    num_predict: int,
    base_url: str,
    chunk_chars: int,
    chunk_overlap: int,
    request_timeout: float,
) -> tuple[str, int]:
    """Returns (og_code, factors_inserted_or_skipped). Skips on unchanged hash."""
    file_hash = compute_file_hash(str(jes_path))
    source_name = jes_path.name
    og_code = extract_og_code(source_name)
    if not og_code:
        print(f"  [{source_name}] cannot derive OG code; skipping", flush=True)
        return "", 0

    existing = con.execute(
        "SELECT content_hash FROM source_documents WHERE source_name = ?",
        [source_name],
    ).fetchone()
    if existing and existing["content_hash"] == file_hash and _derived_count_for_og(con, og_code) > 0:
        print(f"  [{og_code}] Unchanged — skipping LLM extraction", flush=True)
        return og_code, 0

    with open(jes_path, encoding="utf-8") as f:
        raw_text = f.read()

    # Pre-process: strip web nav boilerplate and individual benchmark descriptions.
    text = preprocess_jes_text(raw_text)
    raw_chars = len(raw_text)
    clean_chars = len(text)
    if clean_chars < raw_chars:
        print(
            f"  [{og_code}] pre-processed: {raw_chars:,} → {clean_chars:,} chars "
            f"({raw_chars - clean_chars:,} stripped)",
            flush=True,
        )

    print(
        f"  [{og_code}] extracting group metadata via {model} ...",
        flush=True,
    )
    # Group metadata extraction uses only the first chunk (definition/inclusions are always at top).
    metadata_text = text[:chunk_chars]
    try:
        metadata = extract_group_metadata_via_llm(
            metadata_text,
            og_code,
            model=model,
            num_ctx=num_ctx,
            num_predict=num_predict,
            base_url=base_url,
            request_timeout=request_timeout,
        )
        upsert_og_metadata(con, og_code, metadata, file_hash)
        methodology = metadata.get("methodology") or "unknown"
        subgroups = metadata.get("subgroups") or []
        has_inclusions = bool(metadata.get("inclusions"))
        has_exclusions = bool(metadata.get("exclusions"))
        print(
            f"  [{og_code}] metadata: methodology={methodology}, "
            f"subgroups={subgroups or 'none'}, "
            f"inclusions={'yes' if has_inclusions else 'no'}, "
            f"exclusions={'yes' if has_exclusions else 'no'}",
            flush=True,
        )
    except Exception as exc:
        print(f"  [{og_code}] metadata extraction failed (non-fatal): {exc}", flush=True)

    print(
        f"  [{og_code}] extracting factors via {model} "
        f"(num_ctx={num_ctx}, num_predict={num_predict}, chunk_chars={chunk_chars}) ...",
        flush=True,
    )
    factors = extract_factors_from_chunks(
        text,
        og_code,
        model=model,
        num_ctx=num_ctx,
        num_predict=num_predict,
        base_url=base_url,
        chunk_chars=chunk_chars,
        chunk_overlap=chunk_overlap,
        request_timeout=request_timeout,
    )
    replace_jes_factors(con, og_code, factors, file_hash)
    upsert_source_document(con, source_name, version_label, file_hash)
    return og_code, len(factors)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest JES source files into jes_factors (PIPE-03).",
    )
    parser.add_argument("--db-path", required=True,
                        help="SQLite database path (must be under project root)")
    parser.add_argument("--data-dir", required=True,
                        help="Path to data/Job_evaluation/ directory")
    parser.add_argument("--model", default="gemma4:31b",
                        help="Ollama model for factor extraction (default: gemma4:31b)")
    parser.add_argument("--version-label", default="JES v1.0",
                        help="Version label stored in source_documents")
    parser.add_argument("--num-ctx", type=int, default=DEFAULT_NUM_CTX,
                        help=f"Ollama context window for extraction requests (default: {DEFAULT_NUM_CTX})")
    parser.add_argument("--num-predict", type=int, default=DEFAULT_NUM_PREDICT,
                        help=f"Maximum output tokens per extraction chunk (default: {DEFAULT_NUM_PREDICT})")
    parser.add_argument("--base-url", default=DEFAULT_OLLAMA_BASE_URL,
                        help=f"Ollama API endpoint (default: {DEFAULT_OLLAMA_BASE_URL})")
    parser.add_argument("--chunk-chars", type=int, default=DEFAULT_CHUNK_CHARS,
                        help=f"Maximum characters per extraction chunk (default: {DEFAULT_CHUNK_CHARS})")
    parser.add_argument("--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP,
                        help=f"Characters of overlap between chunks (default: {DEFAULT_CHUNK_OVERLAP})")
    parser.add_argument("--request-timeout", type=float, default=1800.0,
                        help="Per-request timeout in seconds for each extraction chunk (default: 1800)")
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

    print(f"[2/3] Discovering JES source files under {data_dir} ...", flush=True)
    jes_files, skipped = discover_jes_files(data_dir)
    print(f"  Found {len(jes_files)} JES Standard files; skipping {len(skipped)} Application Guidelines")
    for s in skipped:
        print(f"    skipped: {s}")

    print(
        f"[3/3] Extracting factors via {args.model} "
        f"(num_ctx={args.num_ctx}, num_predict={args.num_predict}, endpoint={args.base_url}) ...",
        flush=True,
    )
    failed_ogs: list[str] = []
    for i, jes_path in enumerate(jes_files, 1):
        print(f"  ({i}/{len(jes_files)}) {jes_path.name}", flush=True)
        try:
            process_one_jes(
                con,
                jes_path,
                args.model,
                args.version_label,
                args.num_ctx,
                args.num_predict,
                args.base_url,
                args.chunk_chars,
                args.chunk_overlap,
                args.request_timeout,
            )
        except Exception as exc:
            og_code = jes_path.stem.split()[0]
            print(f"  [{og_code}] FAILED (skipping file): {exc}", flush=True)
            failed_ogs.append(og_code)

    factor_total = con.execute("SELECT COUNT(*) FROM jes_factors").fetchone()[0]
    og_meta_total = con.execute("SELECT COUNT(*) FROM jes_og_metadata").fetchone()[0]
    print(
        f"\nIngest complete: jes_factors {factor_total:,} rows, "
        f"jes_og_metadata {og_meta_total:,} rows",
        flush=True,
    )
    if failed_ogs:
        print(f"  FAILED OGs ({len(failed_ogs)}): {', '.join(failed_ogs)}", flush=True)

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
