"""
scripts/ingest_drf.py — DND Departmental Results Framework (DRF) ingest pipeline.

Parses data/departmental_results_framework/dnd_drf_dataset.csv and populates
the drf_rows SQLite table with one row per unique
(fiscal_year, core_responsibility, departmental_result) triple.

Idempotent — uses INSERT OR IGNORE on the UNIQUE constraint. Running the
script repeatedly on the same database produces the same row count.

Usage:
    python scripts/ingest_drf.py app.db
    python -m scripts.ingest_drf app.db
    DB_PATH=app.db python scripts/ingest_drf.py
    python scripts/ingest_drf.py --csv path/to/dnd_drf_dataset.csv app.db
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default CSV path — relative to project root, NOT to scripts/ (Pitfall: scripts
# is one level down, so __file__.parent.parent is the project root).
DEFAULT_CSV_PATH = "data/departmental_results_framework/dnd_drf_dataset.csv"

# CSV column headers (exact, with spaces) — quoted strings so they don't drift
# from the source.
COL_FISCAL_YEAR = "Fiscal Year"
COL_ORG = "Organization"
COL_CR = "Core Responsibility"
COL_DR = "Departmental Results"
COL_INDICATOR = "Indicator"
COL_PUBLISHED = "Published on the Open government portal"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Ingest DND DRF dataset CSV into the drf_rows SQLite table. "
            "Idempotent — safe to re-run."
        )
    )
    parser.add_argument(
        "db_path",
        nargs="?",
        default=os.environ.get("DB_PATH") or "app.db",
        help=(
            "Path to the SQLite database file. Defaults to $DB_PATH or "
            "'app.db' in the project root."
        ),
    )
    parser.add_argument(
        "--csv",
        default=str(_project_root / DEFAULT_CSV_PATH),
        help=(
            "Path to the DRF CSV file. Default: "
            f"{DEFAULT_CSV_PATH} (relative to project root)"
        ),
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Stage 1: Parse CSV
# ---------------------------------------------------------------------------


def parse_drf_csv(csv_path: Path) -> list[dict]:
    """
    Parse the DRF CSV with utf-8-sig encoding (strips UTF-8 BOM if present).

    Falls back to cp1252 (Windows-1252) if the file is not valid UTF-8.
    The DND DRF dataset has 4 stray 0x92 bytes (cp1252 right-single-quote)
    embedded in otherwise-ASCII content — a known artifact of the original
    download. Falling back to cp1252 decodes those bytes as a proper
    apostrophe rather than raising UnicodeDecodeError.

    Returns a list of dicts keyed by the original CSV column headers.
    Yields all rows — dedup happens at the SQL layer via UNIQUE constraint.
    """
    if not csv_path.exists():
        raise FileNotFoundError(
            f"DRF CSV not found at: {csv_path}. "
            f"Pass --csv to point at the right location."
        )
    try:
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except UnicodeDecodeError:
        # Fallback: source file has stray cp1252 bytes — decode as cp1252
        # (the 0x92 byte becomes U+2019 RIGHT SINGLE QUOTATION MARK, which
        # is semantically correct for apostrophe use in the source text).
        with open(csv_path, encoding="cp1252", newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)


# ---------------------------------------------------------------------------
# Stage 2: Ingest to SQLite
# ---------------------------------------------------------------------------


def ingest_drf_rows(conn, csv_rows: list[dict], source_file: str) -> tuple[int, int]:
    """
    Insert CSV rows into drf_rows using INSERT OR IGNORE (idempotent).

    Each row's search_text is the lowercased concatenation of
    core_responsibility and departmental_result — used by the matching
    service for keyword overlap.

    Returns (inserted_count, skipped_count):
        inserted_count: number of rows that produced a new drf_rows row
        skipped_count:  number of rows that matched the UNIQUE constraint
                        and were silently ignored
    """
    inserted = 0
    skipped = 0
    for row in csv_rows:
        fiscal_year = (row.get(COL_FISCAL_YEAR) or "").strip()
        core_responsibility = (row.get(COL_CR) or "").strip()
        departmental_result = (row.get(COL_DR) or "").strip()

        # Skip malformed rows — all three key columns must be present
        if not fiscal_year or not core_responsibility or not departmental_result:
            skipped += 1
            continue

        # search_text: lowercased concat of core_responsibility + space + departmental_result
        # Used by the matching service (app/services/drf_service.py) for keyword overlap
        # against the WD's draft duty text.
        search_text = (core_responsibility + " " + departmental_result).lower()

        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO drf_rows
                (fiscal_year, core_responsibility, departmental_result, search_text, source_file)
            VALUES (?, ?, ?, ?, ?)
            """,
            (fiscal_year, core_responsibility, departmental_result, search_text, source_file),
        )
        # cursor.rowcount: 1 if inserted, 0 if UNIQUE collision
        if cursor.rowcount > 0:
            inserted += 1
        else:
            skipped += 1

    conn.commit()
    return inserted, skipped


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    args = parse_args()

    # Local import: keeps --help fast and gives a clean error if app modules are missing
    from app.db import create_schema, get_connection

    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = (_project_root / csv_path).resolve()

    print(f"[1/3] Reading DRF CSV: {csv_path}")
    csv_rows = parse_drf_csv(csv_path)
    print(f"  Parsed {len(csv_rows)} CSV rows")

    print(f"[2/3] Opening SQLite at {args.db_path} and ensuring schema ...")
    conn = get_connection(args.db_path)
    create_schema(conn)  # idempotent — safe to call on every startup

    print("[3/3] Inserting rows (INSERT OR IGNORE) ...")
    source_file = csv_path.name  # store basename only — keeps path portable
    inserted, skipped = ingest_drf_rows(conn, csv_rows, source_file)

    total_in_db = conn.execute("SELECT COUNT(*) FROM drf_rows").fetchone()[0]
    conn.close()

    print(
        f"\nIngested {inserted} rows into drf_rows (skipped {skipped} duplicates).\n"
        f"Total rows now in drf_rows: {total_in_db}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
