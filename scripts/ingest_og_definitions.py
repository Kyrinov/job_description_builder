"""
scripts/ingest_og_definitions.py — TBS OCHRO OG definitions ingest (Phase 5 CLASS-01 prereq).

Reads data/TBS-OCHRO-OG.txt, parses each OG section into (og_code, og_name,
parent_group, definition, inclusions, exclusions), upserts into og_definitions table.

Usage:
    python scripts/ingest_og_definitions.py \
        --db-path /home/charles/job_description_builder/app.db \
        --data-dir /home/charles/job_description_builder/data
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sqlite3
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from app.db import create_schema, get_connection  # noqa: E402


def validate_db_path(db_path: str) -> Path:
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


def load_connection(db_path: Path) -> sqlite3.Connection:
    return get_connection(str(db_path))


def compute_file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_og_section(text: str) -> dict:
    """
    Given a raw text block for one OG, return a dict with keys:
    og_code, og_name, parent_group, definition, inclusions, exclusions.
    Returns og_code=None if no code found — caller should skip that row.
    """
    code_match = re.search(r'\(([A-Z]{2,4})\)', text)
    og_code = code_match.group(1) if code_match else None

    og_name = None
    if og_code:
        for line in text.splitlines():
            if f"({og_code})" in line:
                og_name = re.sub(r'\s*\([A-Z]{2,4}\)\s*$', '', line).strip()
                break

    parent_group = None
    if "Definition Excerpt" in text or "definition excerpt" in text.lower():
        pass

    inc_split = re.split(r'\nInclusions\n', text, maxsplit=1)
    definition = inc_split[0].strip() if len(inc_split) > 1 else text.strip()

    inclusions = exclusions = None
    if len(inc_split) > 1:
        exc_split = re.split(r'\nExclusions\n', inc_split[1], maxsplit=1)
        inclusions = exc_split[0].strip() or None
        if len(exc_split) > 1:
            exclusions = exc_split[1].strip() or None

    return {
        "og_code": og_code,
        "og_name": og_name or og_code,
        "parent_group": parent_group,
        "definition": definition,
        "inclusions": inclusions,
        "exclusions": exclusions,
    }


def parse_all_ogs(text: str) -> list[dict]:
    """
    Split TBS-OCHRO-OG.txt into per-OG sections.
    Each OG section starts with a line matching "<Name> (<CODE>)".
    Returns list of dicts from parse_og_section, skipping entries with og_code=None.
    """
    sections = re.split(r'\n(?=[A-Z][^\n]+\([A-Z]{2,4}\)\n)', text)
    results = []
    for section in sections:
        if not section.strip():
            continue
        parsed = parse_og_section(section)
        if parsed["og_code"] is not None:
            results.append(parsed)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest TBS OCHRO OG definitions into SQLite")
    parser.add_argument("--db-path", required=True, help="Path to app.db")
    parser.add_argument("--data-dir", required=True, help="Path to data/ directory")
    args = parser.parse_args()

    db_path = validate_db_path(args.db_path)
    data_dir = Path(args.data_dir).resolve()
    og_file = data_dir / "TBS-OCHRO-OG.txt"

    if not og_file.exists():
        print(f"Error: {og_file} not found", file=sys.stderr)
        return 1

    print(f"[1/3] Connecting to {db_path} ...", flush=True)
    con = load_connection(db_path)
    create_schema(con)

    print(f"[2/3] Parsing {og_file} ...", flush=True)
    text = og_file.read_text(encoding="utf-8", errors="replace")
    file_hash = compute_file_hash(og_file)
    ogs = parse_all_ogs(text)
    print(f"      Parsed {len(ogs)} OG sections", flush=True)

    print(f"[3/3] Upserting og_definitions ...", flush=True)
    inserted = 0
    for row in ogs:
        cur = con.execute(
            """
            INSERT OR IGNORE INTO og_definitions
                (og_code, og_name, parent_group, definition, inclusions, exclusions, source_file, source_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["og_code"], row["og_name"], row["parent_group"],
                row["definition"], row["inclusions"], row["exclusions"],
                "TBS-OCHRO-OG.txt", file_hash,
            ),
        )
        inserted += cur.rowcount
    con.commit()

    total = con.execute("SELECT COUNT(*) FROM og_definitions").fetchone()[0]
    con.close()
    print(f"\nIngest complete:\n  og_definitions: {total:,} rows ({inserted} new)\n", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
