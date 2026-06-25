"""
scripts/ingest_jes_qwen.py — JES factor extraction via OpenAI-compatible API (Qwen/DashScope).

Identical pipeline to ingest_jes.py but uses an OpenAI-compatible cloud API instead of Ollama.
Structured output is obtained via OpenAI-style tool/function calling.

Default endpoint: https://dashscope.aliyuncs.com/compatible-mode/v1  (Qwen / Alibaba Cloud)
Accepts any OpenAI-compatible endpoint via --base-url.

Usage:
    export DASHSCOPE_API_KEY=sk-...
    python scripts/ingest_jes_qwen.py \\
        --db-path app.db \\
        --data-dir data/Job_evaluation \\
        --model qwen-max-2025-01-25 \\
        --og-filter NT CT EX WP \\
        --force
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from openai import OpenAI

_scripts_dir = Path(__file__).resolve().parent
_project_root = _scripts_dir.parent
for _p in (str(_scripts_dir), str(_project_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ingest_jes import (  # noqa: E402
    DEFAULT_CHUNK_OVERLAP,
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

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_CHUNK_CHARS = 40_000
DEFAULT_MAX_TOKENS = 8_192

_FACTOR_TOOL = {
    "type": "function",
    "function": {
        "name": "store_jes_factors",
        "description": (
            "Store the structured JES factors extracted from this document chunk. "
            "Call this with every complete factor/element rating scale found."
        ),
        "parameters": JESExtractionResult.model_json_schema(),
    },
}

_METADATA_TOOL = {
    "type": "function",
    "function": {
        "name": "store_og_metadata",
        "description": "Store the occupational group metadata extracted from the JES standard header.",
        "parameters": GroupMetadataResult.model_json_schema(),
    },
}


def extract_factors_via_api(
    text: str,
    og_code: str,
    client: OpenAI,
    model: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    max_retries: int = 3,
) -> list[dict]:
    # OG-specific extraction guidance
    og_hints = ""
    if og_code == "CT":
        og_hints = (
            f"\n\nCRITICAL — CT has THREE subgroups: CT-IAU (Internal Audit), CT-FIN (Financial "
            f"Management), and CT-EAV (External Audit). You MUST extract factors for ALL THREE "
            f"subgroups. Each subgroup has its own set of 6 factors (Knowledge, Analytical and "
            f"critical thinking, Decision making, Communication, Effort, Working conditions). "
            f"Do NOT stop after CT-IAU. Continue reading the full text and extract CT-FIN and "
            f"CT-EAV factors as well, prefixing each factor_name with its subgroup code "
            f"(e.g. 'CT-FIN: Knowledge', 'CT-EAV: Decision making')."
        )
    elif og_code == "EX":
        og_hints = (
            f"\n\nCRITICAL — EX uses the Hay Guide Chart method with THREE main factors, each "
            f"with sub-factors. You MUST extract ALL of the following as separate factors:\n"
            f"  1. Know-How: sub-factors A (Practical/Technical/Specialized Know-How), "
            f"B (Planning/Organizing/Integrating), C (Communicating and Influencing)\n"
            f"  2. Problem Solving: sub-factors A (Thinking Environment), B (Thinking Challenge)\n"
            f"  3. Accountability: sub-factors A (Freedom to Act), B (Nature of Impact), "
            f"C (Area of Impact / Magnitude)\n"
            f"For each sub-factor, the degrees are Hay chart grades (e.g. F-, F, F+, G-, G, G+, "
            f"H-, H, H+...). Extract every grade row as a degree_descriptor with its letter+sign "
            f"label, the descriptive text, and the numeric point value from the chart. "
            f"Do NOT return empty degree_descriptors for any sub-factor — read the full chart."
        )

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
        f"  - Some standards define nested sub-elements — extract each sub-element as a distinct factor\n"
        f"  - Level-description standards (e.g. NT, CT) describe levels narratively rather than\n"
        f"    awarding points — extract each level as a degree with points=0\n\n"
        f"You MUST read and process the ENTIRE text chunk before calling the tool. "
        f"Do not stop after the first factor or subgroup — extract everything present.\n\n"
        f"If the standard has subgroups (e.g. CT-IAU, CT-FIN, CT-EAV), extract factors for ALL "
        f"subgroups present, prefixing factor_name with the subgroup code "
        f"(e.g. 'CT-FIN: Knowledge', 'CT-EAV: Decision making').\n\n"
        f"Only extract formal job-evaluation factor or element rating scales. Do not extract "
        f"benchmarks, illustrative positions, notes to raters, glossary entries, or point-range tables.\n"
        f"If this chunk has no complete factor, call the tool with an empty factors list."
        f"{og_hints}\n\n"
        f"TEXT CHUNK:\n{text}"
    )

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                tools=[_FACTOR_TOOL],
                tool_choice={"type": "function", "function": {"name": "store_jes_factors"}},
                messages=[{"role": "user", "content": prompt}],
                extra_body={"enable_thinking": False},
            )
            args_str = response.choices[0].message.tool_calls[0].function.arguments
            result = JESExtractionResult.model_validate(json.loads(args_str))
            return [f.model_dump() for f in result.factors]
        except Exception as exc:
            last_error = exc
            print(f"  [{og_code}] attempt {attempt}/{max_retries} failed: {exc}", flush=True)

    raise RuntimeError(f"extraction failed after {max_retries} attempts: {last_error}") from last_error


def extract_group_metadata_via_api(
    text: str,
    og_code: str,
    client: OpenAI,
    model: str,
    max_tokens: int = 2_048,
    max_retries: int = 3,
) -> dict:
    prompt = (
        f"You are reading a Job Evaluation Standard (JES) for the {og_code} occupational group "
        f"of the Canadian federal public service.\n\n"
        f"Extract the following group-level metadata:\n\n"
        f"  - group_definition: Formal definition of the occupational group.\n"
        f"  - inclusions: Verbatim text of the Inclusions section. Empty string if absent.\n"
        f"  - exclusions: Verbatim text of the Exclusions section. Empty string if absent.\n"
        f"  - methodology: Evaluation methodology — 'point-rating', 'Hay Guide Chart', or "
        f"'level-descriptions'.\n"
        f"  - subgroups: Named subgroups (e.g. CT-IAU, CT-FIN). Empty list if none.\n\n"
        f"Use verbatim text for definitions, inclusions, and exclusions.\n\n"
        f"TEXT:\n{text}"
    )

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                tools=[_METADATA_TOOL],
                tool_choice={"type": "function", "function": {"name": "store_og_metadata"}},
                messages=[{"role": "user", "content": prompt}],
                extra_body={"enable_thinking": False},
            )
            args_str = response.choices[0].message.tool_calls[0].function.arguments
            result = GroupMetadataResult.model_validate(json.loads(args_str))
            return result.model_dump()
        except Exception as exc:
            last_error = exc
            print(f"  [{og_code}] metadata attempt {attempt}/{max_retries} failed: {exc}", flush=True)

    raise RuntimeError(f"metadata extraction failed after {max_retries} attempts: {last_error}") from last_error


def extract_factors_from_chunks(
    text: str,
    og_code: str,
    client: OpenAI,
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
            factors = extract_factors_via_api(chunk, og_code, client=client, model=model, max_tokens=max_tokens)
        except Exception as exc:
            print(f"  [{og_code}] chunk {index}/{len(chunks)} FAILED (skipping): {exc}", flush=True)
            continue
        print(f"  [{og_code}] chunk {index}/{len(chunks)} returned {len(factors)} factor(s)", flush=True)
        all_factors.extend(factors)

    return merge_extracted_factors(all_factors)


def process_one_jes(
    con,
    jes_path: Path,
    client: OpenAI,
    model: str,
    version_label: str,
    chunk_chars: int,
    chunk_overlap: int,
    max_tokens: int,
    force: bool = False,
) -> tuple[str, int]:
    file_hash = compute_file_hash(str(jes_path))
    source_name = jes_path.name
    og_code = extract_og_code(source_name)
    if not og_code:
        print(f"  [{source_name}] cannot derive OG code; skipping", flush=True)
        return "", 0

    existing = con.execute(
        "SELECT content_hash FROM source_documents WHERE source_name = ?", [source_name]
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
    try:
        metadata = extract_group_metadata_via_api(text[:chunk_chars], og_code, client=client, model=model)
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

    print(f"  [{og_code}] extracting factors via {model} (chunk_chars={chunk_chars}) ...", flush=True)
    factors = extract_factors_from_chunks(
        text, og_code,
        client=client, model=model, max_tokens=max_tokens,
        chunk_chars=chunk_chars, chunk_overlap=chunk_overlap,
    )
    replace_jes_factors(con, og_code, factors, file_hash)
    upsert_source_document(con, source_name, version_label, file_hash)
    return og_code, len(factors)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest JES source files into jes_factors via OpenAI-compatible API (Qwen/DashScope).",
    )
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--model", required=True,
                        help="Model name, e.g. qwen-max-2025-01-25")
    parser.add_argument("--api-key",
                        help="API key (falls back to DASHSCOPE_API_KEY env var)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                        help=f"OpenAI-compatible endpoint (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--version-label", default="JES v1.0")
    parser.add_argument("--chunk-chars", type=int, default=DEFAULT_CHUNK_CHARS)
    parser.add_argument("--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
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

    api_key = args.api_key or os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: provide --api-key or set DASHSCOPE_API_KEY", file=sys.stderr)
        return 1

    client = OpenAI(api_key=api_key, base_url=args.base_url)

    print(f"[1/3] Connecting to {db_path} ...", flush=True)
    con = load_connection(str(db_path))
    from app.db import create_schema
    create_schema(con)

    print(f"[2/3] Discovering JES source files under {data_dir} ...", flush=True)
    jes_files, skipped = discover_jes_files(data_dir)
    print(f"  Found {len(jes_files)} JES Standard files; skipping {len(skipped)} Application Guidelines")

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
