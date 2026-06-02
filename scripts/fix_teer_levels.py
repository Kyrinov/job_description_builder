"""
scripts/fix_teer_levels.py — One-shot migration: derive correct TEER values from NOC codes.

Background: ingest_noc.py originally stored the structure CSV "Level" column (which
is the NOC hierarchy depth, always 5 for unit groups) into noc_units.teer_level. The
correct TEER is the second digit of the NOC 5-digit code:

    NOC 0X*** → TEER 0 (management)
    NOC 1X*** → TEER 1 (professional — university degree)
    NOC 2X*** → TEER 2 (post-secondary 2-3 years / apprenticeship)
    NOC 3X*** → TEER 3 (post-secondary < 2 years)
    NOC 4X*** → TEER 4 (secondary school)
    NOC 5X*** → TEER 5 (on-the-job training only)

This script fixes the existing rows in place — no re-ingest required.

Usage:
    python scripts/fix_teer_levels.py \\
        --db-path /home/charles/job_description_builder/app.db
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from app.db import get_connection  # noqa: E402
from scripts.ingest_noc import derive_teer_from_code, validate_db_path  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Recompute teer_level from NOC code second digit")
    parser.add_argument("--db-path", required=True, help="Path to app.db")
    args = parser.parse_args()

    db_path = validate_db_path(args.db_path)
    con = get_connection(str(db_path))

    rows = con.execute("SELECT noc_code, teer_level FROM noc_units").fetchall()
    print(f"Scanning {len(rows)} noc_units rows...")

    fixed = 0
    unchanged = 0
    for r in rows:
        correct = derive_teer_from_code(r["noc_code"])
        if correct and correct != r["teer_level"]:
            con.execute(
                "UPDATE noc_units SET teer_level = ? WHERE noc_code = ?",
                (correct, r["noc_code"]),
            )
            fixed += 1
        else:
            unchanged += 1
    con.commit()

    print(f"  Fixed:     {fixed} rows")
    print(f"  Unchanged: {unchanged} rows")

    dist = con.execute(
        "SELECT teer_level, COUNT(*) AS c FROM noc_units GROUP BY teer_level ORDER BY teer_level"
    ).fetchall()
    print(f"  Distribution: {[(r['teer_level'], r['c']) for r in dist]}")

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
