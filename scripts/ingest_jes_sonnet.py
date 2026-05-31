"""
scripts/ingest_jes_sonnet.py — JES factor extraction via Claude Sonnet API (PIPE-03).

Identical pipeline to ingest_jes.py but uses the Anthropic API instead of Ollama.
All pre-processing (web boilerplate strip, benchmark strip) and DB upsert logic is
imported from ingest_jes.py — only the LLM call layer differs.

Structured output is obtained via Claude tool_use with forced tool_choice, which is
more reliable than prompt-only JSON extraction and eliminates the grammar-constraint
issues seen with local models.

Default chunk size is 40,000 chars (≈10K tokens) — larger than the Ollama default
of 12,000 chars, taking advantage of Sonnet's 200K context window to reduce the
number of API calls and keep more factor context together per call.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python scripts/ingest_jes_sonnet.py \\
        --db-path app.db \\
        --data-dir data/Job_evaluation

Tier notes:
    Anthropic API access is billed separately from Claude.ai Pro. Add credits at
    console.anthropic.com. A full 16-OG run costs approximately $2.50 at Sonnet rates.
    The SDK retries 429 rate-limit responses automatically with exponential backoff.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import anthropic

# ---------------------------------------------------------------------------
# Import shared functions from ingest_jes.py (same scripts/ directory)
# ---------------------------------------------------------------------------
_scripts_dir = Path(__file__).resolve().parent
_project_root = _scripts_dir.parent
for _p in (str(_scripts_dir), str(_project_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ingest_jes import (  # noqa: E402
    DEFAULT_CHUNK_OVERLAP,
    DegreeDescriptor,  # noqa: F401 — re-exported for tests
    ExtractedFactor,   # noqa: F401
    GroupMetadataResult,
    JESExtractionResult,
    _derived_count_for_og,
    chunk_text,
    compute_file_hash,
    discover_jes_files,
    extract_og_code,
    load_connection,
    merge_extracted_factors,
    preprocess_jes_text,
    replace_jes_factors,
    upsert_og_metadata,
    upsert_source_document,
    validate_db_path,
)

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_CHUNK_CHARS = 40_000   # Larger than Ollama default; Sonnet handles 200K context
DEFAULT_MAX_TOKENS = 8_192     # Output budget per API call


# ---------------------------------------------------------------------------
# Anthropic tool_use schemas (derived from shared Pydantic models)
# ---------------------------------------------------------------------------

_FACTOR_TOOL = {
    "name": "store_jes_factors",
    "description": (
        "Store the structured JES factors extracted from this document chunk. "
        "Call this tool with every complete factor/element rating scale found."
    ),
    "input_schema": JESExtractionResult.model_json_schema(),
}

_METADATA_TOOL = {
    "name": "store_og_metadata",
    "description": (
        "Store the occupational group metadata extracted from the JES standard header."
    ),
    "input_schema": GroupMetadataResult.model_json_schema(),
}


# ---------------------------------------------------------------------------
# LLM extraction — Anthropic API
# ---------------------------------------------------------------------------

def extract_factors_via_sonnet(
    text: str,
    og_code: str,
    client: anthropic.Anthropic,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    max_retries: int = 3,
) -> list[dict]:
    """
    Extract structured JES factors from one chunk using Claude tool_use.
    Returns list of dicts matching ExtractedFactor fields.
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
        f"    Effort' under 'Effort') — extract each sub-element as a distinct factor\n"
        f"  - Level-description standards (e.g. NT Nutrition, CT Comptrollership) describe\n"
        f"    levels narratively rather than awarding points — extract each level as a degree\n"
        f"    with points=0 and capture the full narrative text in degree_descriptors\n\n"
        f"If the standard has subgroups (e.g. CT-IAU, CT-FIN), extract the factors for ALL\n"
        f"subgroups present in this chunk, prefixing the factor_name with the subgroup code\n"
        f"when needed for uniqueness (e.g. 'CT-IAU: Knowledge', 'CT-FIN: Knowledge').\n\n"
        f"Only extract formal job-evaluation factor or element rating scales. Do not extract\n"
        f"benchmark positions, illustrative positions, examples, notes to raters, glossary\n"
        f"entries, group definitions, inclusions, exclusions, or point-range tables as factors.\n"
        f"If this chunk has no complete factor or element rating scale, call the tool with an "
        f"empty factors list.\n\n"
        f"TEXT CHUNK:\n{text}"
    )

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                tools=[_FACTOR_TOOL],
                tool_choice={"type": "tool", "name": "store_jes_factors"},
                messages=[{"role": "user", "content": prompt}],
            )
            tool_block = next(b for b in response.content if b.type == "tool_use")
            result = JESExtractionResult.model_validate(tool_block.input)
            return [f.model_dump() for f in result.factors]
        except Exception as exc:
            last_error = exc
            print(f"  [{og_code}] request attempt {attempt}/{max_retries} failed: {exc}", flush=True)

    raise RuntimeError(f"extraction failed after {max_retries} attempts: {last_error}") from last_error


def extract_group_metadata_via_sonnet(
    text: str,
    og_code: str,
    client: anthropic.Anthropic,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 2_048,
    max_retries: int = 3,
) -> dict:
    """
    Extract OG metadata (definition, inclusions, exclusions, methodology) from the
    first chunk of the document using Claude tool_use.
    """
    prompt = (
        f"You are reading a Job Evaluation Standard (JES) for the {og_code} occupational group "
        f"of the Canadian federal public service.\n\n"
        f"Extract the following group-level metadata from the text:\n\n"
        f"  - group_definition: The formal definition of the occupational group (what types of "
        f"positions are in this group). Usually under a heading like 'Group Definition', "
        f"'Occupational Group Definition', or 'Definition'.\n\n"
        f"  - inclusions: The verbatim text of the Inclusions section, listing specific activities "
        f"or position types explicitly included in the group. May appear under 'Inclusions', "
        f"'INCLUSIONS', or 'Notwithstanding the generality...' language. Include all bullet points "
        f"or numbered items verbatim. Empty string if absent.\n\n"
        f"  - exclusions: The verbatim text of the Exclusions section, listing activities or position "
        f"types explicitly excluded from the group. May appear under 'Exclusions', 'EXCLUSIONS', or "
        f"'Positions excluded from...'. Include all bullet points or numbered items verbatim. "
        f"Empty string if absent.\n\n"
        f"  - methodology: The evaluation methodology used. Common values:\n"
        f"    'point-rating' (most standards), 'Hay Guide Chart' (EX Executive), "
        f"    'level-descriptions' (standards using narrative levels rather than points).\n\n"
        f"  - subgroups: Named subgroups defined by the standard (e.g. CT-IAU, CT-FIN, CT-EAV for "
        f"Comptrollership; ED-LAT, ED-EST, ED-EDS for Education). Empty list if none.\n\n"
        f"Do not infer or paraphrase — use verbatim text for definitions, inclusions, and exclusions.\n\n"
        f"TEXT:\n{text}"
    )

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                tools=[_METADATA_TOOL],
                tool_choice={"type": "tool", "name": "store_og_metadata"},
                messages=[{"role": "user", "content": prompt}],
            )
            tool_block = next(b for b in response.content if b.type == "tool_use")
            result = GroupMetadataResult.model_validate(tool_block.input)
            return result.model_dump()
        except Exception as exc:
            last_error = exc
            print(f"  [{og_code}] metadata attempt {attempt}/{max_retries} failed: {exc}", flush=True)

    raise RuntimeError(f"metadata extraction failed after {max_retries} attempts: {last_error}") from last_error


# ---------------------------------------------------------------------------
# Per-chunk orchestration
# ---------------------------------------------------------------------------

def extract_factors_from_chunks(
    text: str,
    og_code: str,
    client: anthropic.Anthropic,
    model: str,
    max_tokens: int,
    chunk_chars: int,
    chunk_overlap: int,
) -> list[dict]:
    chunks = chunk_text(text, max_chars=chunk_chars, overlap_chars=chunk_overlap)
    if not chunks:
        return []

    all_factors: list[dict] = []
    print(f"  [{og_code}] split into {len(chunks)} chunk(s)", flush=True)
    for index, chunk in enumerate(chunks, 1):
        print(f"  [{og_code}] chunk {index}/{len(chunks)}: {len(chunk):,} chars", flush=True)
        try:
            factors = extract_factors_via_sonnet(chunk, og_code, client=client, model=model, max_tokens=max_tokens)
        except Exception as exc:
            print(f"  [{og_code}] chunk {index}/{len(chunks)} FAILED (skipping): {exc}", flush=True)
            continue
        print(f"  [{og_code}] chunk {index}/{len(chunks)} returned {len(factors)} factor(s)", flush=True)
        all_factors.extend(factors)

    return merge_extracted_factors(all_factors)


# ---------------------------------------------------------------------------
# Per-file processing
# ---------------------------------------------------------------------------

def process_one_jes(
    con,
    jes_path: Path,
    client: anthropic.Anthropic,
    model: str,
    version_label: str,
    chunk_chars: int,
    chunk_overlap: int,
    max_tokens: int,
    force: bool = False,
) -> tuple[str, int]:
    """Returns (og_code, factors_stored). Skips on unchanged hash."""
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
    if not force and existing and existing["content_hash"] == file_hash and _derived_count_for_og(con, og_code) > 0:
        print(f"  [{og_code}] Unchanged — skipping LLM extraction", flush=True)
        return og_code, 0

    with open(jes_path, encoding="utf-8") as f:
        raw_text = f.read()

    text = preprocess_jes_text(raw_text)
    raw_chars, clean_chars = len(raw_text), len(text)
    if clean_chars < raw_chars:
        print(
            f"  [{og_code}] pre-processed: {raw_chars:,} → {clean_chars:,} chars "
            f"({raw_chars - clean_chars:,} stripped)",
            flush=True,
        )

    print(f"  [{og_code}] extracting group metadata via {model} ...", flush=True)
    metadata_text = text[:chunk_chars]
    try:
        metadata = extract_group_metadata_via_sonnet(metadata_text, og_code, client=client, model=model)
        upsert_og_metadata(con, og_code, metadata, file_hash)
        methodology = metadata.get("methodology") or "unknown"
        subgroups = metadata.get("subgroups") or []
        print(
            f"  [{og_code}] metadata: methodology={methodology}, "
            f"subgroups={subgroups or 'none'}, "
            f"inclusions={'yes' if metadata.get('inclusions') else 'no'}, "
            f"exclusions={'yes' if metadata.get('exclusions') else 'no'}",
            flush=True,
        )
    except Exception as exc:
        print(f"  [{og_code}] metadata extraction failed (non-fatal): {exc}", flush=True)

    print(
        f"  [{og_code}] extracting factors via {model} (chunk_chars={chunk_chars}) ...",
        flush=True,
    )
    factors = extract_factors_from_chunks(
        text, og_code,
        client=client, model=model, max_tokens=max_tokens,
        chunk_chars=chunk_chars, chunk_overlap=chunk_overlap,
    )
    replace_jes_factors(con, og_code, factors, file_hash)
    upsert_source_document(con, source_name, version_label, file_hash)
    return og_code, len(factors)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest JES source files into jes_factors via Claude Sonnet API.",
    )
    parser.add_argument("--db-path", required=True,
                        help="SQLite database path (must be under project root)")
    parser.add_argument("--data-dir", required=True,
                        help="Path to data/Job_evaluation/ directory")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Anthropic model (default: {DEFAULT_MODEL})")
    parser.add_argument("--version-label", default="JES v1.0",
                        help="Version label stored in source_documents")
    parser.add_argument("--chunk-chars", type=int, default=DEFAULT_CHUNK_CHARS,
                        help=f"Max characters per extraction chunk (default: {DEFAULT_CHUNK_CHARS})")
    parser.add_argument("--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP,
                        help=f"Overlap chars between chunks (default: {DEFAULT_CHUNK_OVERLAP})")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS,
                        help=f"Max output tokens per API call (default: {DEFAULT_MAX_TOKENS})")
    parser.add_argument("--og-filter", nargs="+", metavar="OG",
                        help="Only process these OG codes, e.g. --og-filter NT CT EX WP")
    parser.add_argument("--force", action="store_true",
                        help="Re-extract even if source hash is unchanged")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = validate_db_path(args.db_path)

    data_dir = Path(args.data_dir).resolve()
    if not data_dir.is_dir():
        print(f"Error: data directory not found: {data_dir}", file=sys.stderr)
        return 1

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

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
        f"(chunk_chars={args.chunk_chars}, max_tokens={args.max_tokens}) ...",
        flush=True,
    )

    og_filter = {og.upper() for og in args.og_filter} if args.og_filter else None
    if og_filter:
        jes_files = [p for p in jes_files if extract_og_code(p.name).upper() in og_filter]
        print(f"  Filtered to {len(jes_files)} file(s): {', '.join(og_filter)}")

    failed_ogs: list[str] = []
    for i, jes_path in enumerate(jes_files, 1):
        print(f"  ({i}/{len(jes_files)}) {jes_path.name}", flush=True)
        try:
            process_one_jes(
                con, jes_path,
                client=client,
                model=args.model,
                version_label=args.version_label,
                chunk_chars=args.chunk_chars,
                chunk_overlap=args.chunk_overlap,
                max_tokens=args.max_tokens,
                force=args.force,
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
