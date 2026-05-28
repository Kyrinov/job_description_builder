"""
filter_jd_relevant.py
---------------------
Strips collective_agreements_all.json down to only the sections relevant
for job description creation and position classification.

Kept per agreement:
  - index_record (group metadata)
  - preamble
  - Sections whose titles match the KEEP_PATTERNS whitelist
  - Tables that are rates-of-pay tables (kept separately under rates_tables)

Output:
  collective_agreements_jd.json
"""

import json
import re
from pathlib import Path

SRC = Path(__file__).parent.parent / "collective_agreements_all.json"
DST = Path(__file__).parent.parent / "collective_agreements_jd.json"

# Section title substrings that are relevant to JD / classification
KEEP_PATTERNS = [
    "interpretation",
    "definition",
    "application",
    "statement of duties",
    "classification",
    "pay and duration",
    "rates of pay",
    "pay administration",
    "management rights",
    "job security",
    "probation",
    "appointment",
    "promotion",
    "performance assessment",
    "employee performance",
    "employee files",
    "education leave",       # career development angle
    "career development",
    # Part-structured agreements use broad headings — keep the intro and pay parts
    "part i:",
    "part 1:",
    "part i ",               # e.g. "Part I General"
    "part 1 ",
    ": pay",                 # "Part V: Pay", "Article 15: Pay"
    "part v: pay",
    "part vi: pay",
    "part vii: pay",
    "working conditions",    # often contains classification/duties content
]

# Table caption substrings that indicate a rates-of-pay table worth keeping
RATES_PATTERNS = [
    "rate",
    "salary",
    "pay",
    "annual",
]

# Section titles to always drop regardless of keyword matches
DROP_EXACT = {
    "table of contents",
    "page details",
}


def is_keep_section(title: str) -> bool:
    tl = title.lower().strip()
    if tl in DROP_EXACT:
        return False
    return any(pat in tl for pat in KEEP_PATTERNS)


def is_rates_table(table: dict) -> bool:
    caption = (table.get("caption") or "").lower()
    section = (table.get("section_title") or "").lower()
    combined = caption + " " + section
    if any(pat in combined for pat in RATES_PATTERNS):
        return True
    # Some agreements label pay tables only by group code, e.g. "LP-01" or "AI-01"
    # Detect step-structured tables (first row contains "Step" headers)
    rows = table.get("rows", [])
    if rows and isinstance(rows[0], list):
        header = " ".join(str(c) for c in rows[0]).lower()
        if "step" in header or "effective date" in header or "$" in header:
            return True
    return False


def filter_agreement(raw: dict) -> dict:
    kept_sections = [s for s in raw.get("sections", []) if is_keep_section(s.get("title", ""))]
    rates_tables = [t for t in raw.get("tables", []) if is_rates_table(t)]

    return {
        "title": raw["title"],
        "url": raw["url"],
        "preamble": raw.get("preamble", ""),
        "index_record": raw.get("index_record", {}),
        "sections": kept_sections,
        "rates_tables": rates_tables,
    }


def main():
    with open(SRC) as f:
        data = json.load(f)

    filtered = []
    stats = []

    for raw in data:
        slim = filter_agreement(raw)
        filtered.append(slim)

        orig_sections = len(raw.get("sections", []))
        orig_tables = len(raw.get("tables", []))
        kept_sections = len(slim["sections"])
        kept_tables = len(slim["rates_tables"])
        stats.append((raw["title"], orig_sections, kept_sections, orig_tables, kept_tables))

    with open(DST, "w") as f:
        json.dump(filtered, f, indent=2, ensure_ascii=False)

    # Report
    orig_size = SRC.stat().st_size
    new_size = DST.stat().st_size
    print(f"{'Agreement':<45} {'Sec kept/total':>15}  {'Tables kept/total':>18}")
    print("-" * 82)
    for title, os_, ks, ot, kt in stats:
        print(f"{title:<45} {ks:>6}/{os_:<6}        {kt:>5}/{ot:<5}")

    print()
    print(f"Original size : {orig_size:,} bytes ({orig_size/1024/1024:.1f} MB)")
    print(f"Filtered size : {new_size:,} bytes ({new_size/1024/1024:.1f} MB)")
    print(f"Reduction     : {100*(1 - new_size/orig_size):.0f}%")
    print(f"\nOutput: {DST}")


if __name__ == "__main__":
    main()
