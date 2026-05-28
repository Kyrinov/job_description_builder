"""
scrape_collective_agreements.py
---------------------------------
Pass 1: Scrapes the TBS Collective Agreements index page (table of all groups).
Pass 2: Follows each agreement's URL and extracts the full agreement text,
        organized by article/appendix section, including any embedded tables.

Outputs:
  collective_agreements_index.csv      — index table (28 rows)
  collective_agreements_index.json     — same, as JSON
  agreements/                          — one folder per group abbreviation
      EC/
          EC_full.json                 — full agreement as structured JSON
          EC_full.txt                  — plain-text version (readable)
  collective_agreements_all.json       — all agreements in one combined JSON
  rates_of_pay/
      EC_rates.csv                     — extracted pay table(s) per agreement

Requirements:
    pip install requests beautifulsoup4

Usage:
    python scrape_collective_agreements.py
    python scrape_collective_agreements.py --out-dir ./output
    python scrape_collective_agreements.py --group EC IT PA    # specific groups only
    python scrape_collective_agreements.py --no-full-text      # index only
    python scrape_collective_agreements.py --delay 1.5         # polite crawl delay (seconds)
"""

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

from curl_cffi.requests import Session as CurlSession
from curl_cffi.requests import exceptions as requests_exceptions
from bs4 import BeautifulSoup

# ── Constants ────────────────────────────────────────────────────────────────

INDEX_URL = (
    "https://www.canada.ca/en/treasury-board-secretariat/topics/pay/"
    "collective-agreements.html"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-CA,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

INDEX_FIELDS = [
    "abbreviation",
    "group",
    "group_subgroup",
    "code",
    "union",
    "signing_date",
    "expiry_date",
    "url",
]

# ── HTTP helpers ──────────────────────────────────────────────────────────────

def fetch(url: str, session: CurlSession, retries: int = 3) -> BeautifulSoup:
    """Fetch a URL and return a BeautifulSoup object."""
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, headers=HEADERS, timeout=(15, 90))
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except (requests_exceptions.Timeout, requests_exceptions.ConnectionError):
            if attempt == retries:
                raise
            wait = attempt * 10
            print(f"  Error on attempt {attempt}/{retries}, retrying in {wait}s...")
            time.sleep(wait)


# ── Pass 1: index page ────────────────────────────────────────────────────────

def scrape_index(soup: BeautifulSoup) -> list[dict]:
    """Parse the main collective agreements table."""
    table = soup.find("table")
    if not table:
        raise RuntimeError("No <table> found on index page — page structure may have changed.")

    records = []
    for i, row in enumerate(table.find_all("tr")[1:], start=1):
        cells = row.find_all("td")
        if len(cells) < 7:
            print(f"  Warning: index row {i} has only {len(cells)} cells — skipping.")
            continue
        link = cells[1].find("a")
        records.append({
            "abbreviation":   cells[0].get_text(strip=True),
            "group":          cells[1].get_text(strip=True),
            "group_subgroup": cells[2].get_text(strip=True),
            "code":           cells[3].get_text(strip=True),
            "union":          cells[4].get_text(strip=True),
            "signing_date":   cells[5].get_text(strip=True),
            "expiry_date":    cells[6].get_text(strip=True),
            "url":            link["href"] if link else None,
        })
    print(f"  Index: {len(records)} agreements found.")
    return records


def write_index_csv(records: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=INDEX_FIELDS)
        writer.writeheader()
        writer.writerows(records)
    print(f"  Wrote: {path}")


def write_json(data, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Wrote: {path}")


# ── Pass 2: full agreement pages ──────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Normalise whitespace."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def table_to_rows(table_tag) -> list[list[str]]:
    """Convert an HTML table to a list of lists of strings."""
    rows = []
    for tr in table_tag.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        rows.append([clean_text(c.get_text(separator=" ")) for c in cells])
    return rows


def scrape_agreement(soup: BeautifulSoup, url: str) -> dict:
    """
    Extract the full agreement from a group page.

    Returns a dict:
        title       : str
        url         : str
        preamble    : str           (text before first h2)
        sections    : list[dict]    each with id, title, text, tables
        tables      : list[dict]    all tables (caption + rows) for easy access
    """
    # Canada.ca main content is in <main> or fallback to body
    main = (
        soup.find("main")
        or soup.find("div", {"id": "wb-cont"})
        or soup.find("div", {"class": "container"})
        or soup.body
    )

    # Title
    h1 = main.find("h1") if main else soup.find("h1")
    title = clean_text(h1.get_text()) if h1 else "Unknown"

    # Walk the DOM: gather preamble (before first h2) then sections
    preamble_parts: list[str] = []
    sections: list[dict] = []
    all_tables: list[dict] = []
    table_index = 0

    in_preamble = True
    current_section: dict | None = None

    elements = main.find_all(["h2", "h3", "p", "ul", "ol", "dl", "table", "div"],
                              recursive=False) if main else []

    # Some pages wrap everything in nested divs; fall back to all descendants
    if not elements:
        elements = main.descendants if main else []

    def flush_section():
        if current_section is not None:
            current_section["text"] = clean_text(" ".join(current_section["_parts"]))
            del current_section["_parts"]
            sections.append(current_section)

    for el in (main or soup).find_all(["h2", "h3", "p", "ul", "ol", "dl", "table"]):
        tag = el.name

        if tag == "h2":
            # Save previous section
            flush_section()
            in_preamble = False
            heading_text = clean_text(el.get_text()).lstrip("*").strip()
            current_section = {
                "id": el.get("id", ""),
                "title": heading_text,
                "_parts": [],
                "tables": [],
            }

        elif tag == "h3" and current_section is not None:
            # Sub-headings folded into current section text
            current_section["_parts"].append(f"\n### {clean_text(el.get_text())} ###\n")

        elif tag == "table":
            rows = table_to_rows(el)
            caption_el = el.find("caption")
            caption = clean_text(caption_el.get_text()) if caption_el else ""

            table_record = {
                "table_index": table_index,
                "caption": caption,
                "section_title": current_section["title"] if current_section else "preamble",
                "rows": rows,
            }
            all_tables.append(table_record)
            table_index += 1

            if in_preamble:
                preamble_parts.append(f"[TABLE {table_index}]")
            elif current_section is not None:
                current_section["tables"].append(table_record)
                current_section["_parts"].append(f"[TABLE {table_index}]")

        else:
            text = clean_text(el.get_text(separator=" "))
            if not text:
                continue
            if in_preamble:
                preamble_parts.append(text)
            elif current_section is not None:
                current_section["_parts"].append(text)

    flush_section()

    return {
        "title": title,
        "url": url,
        "preamble": clean_text(" ".join(preamble_parts)),
        "sections": sections,
        "tables": all_tables,
    }


def agreement_to_txt(agreement: dict) -> str:
    """Render a structured agreement dict as readable plain text."""
    lines = []
    sep = "=" * 72

    lines.append(sep)
    lines.append(agreement["title"].upper())
    lines.append(agreement["url"])
    lines.append(sep)

    if agreement.get("preamble"):
        lines.append("")
        lines.append(agreement["preamble"])

    for section in agreement.get("sections", []):
        lines.append("")
        lines.append("-" * 72)
        lines.append(section["title"].upper())
        lines.append("-" * 72)
        lines.append(section.get("text", ""))

        for table in section.get("tables", []):
            lines.append("")
            if table.get("caption"):
                lines.append(f"[Table: {table['caption']}]")
            for row in table.get("rows", []):
                lines.append("  | " + " | ".join(row) + " |")

    return "\n".join(lines)


def write_rates_csv(agreement: dict, path: Path) -> None:
    """Write any table whose section title contains 'rate' or 'pay' to a CSV."""
    rate_tables = [
        t for t in agreement.get("tables", [])
        if any(kw in t.get("section_title", "").lower() or kw in t.get("caption", "").lower()
               for kw in ("rate", "pay", "salary", "appendix a", "rémunération"))
    ]
    if not rate_tables:
        return

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for table in rate_tables:
            if table.get("caption"):
                writer.writerow([f"# {table['caption']}"])
            if table.get("section_title"):
                writer.writerow([f"# Section: {table['section_title']}"])
            for row in table.get("rows", []):
                writer.writerow(row)
            writer.writerow([])  # blank separator between tables
    print(f"    Wrote rates: {path}")


# ── Slug helper ───────────────────────────────────────────────────────────────

def group_slug(record: dict) -> str:
    """Derive a clean filesystem-safe slug from the abbreviation field."""
    abbrev = record.get("abbreviation", "UNKNOWN")
    # Strip parentheses and slashes, keep first token
    slug = re.sub(r"[^A-Za-z0-9]+", "_", abbrev).strip("_")
    return slug or "UNKNOWN"


# ── Main ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape TBS collective agreements — index + full text."
    )
    parser.add_argument(
        "--out-dir", default=".", help="Root output directory (default: current dir)."
    )
    parser.add_argument(
        "--group",
        nargs="+",
        metavar="ABBREV",
        help="Only scrape specific groups by abbreviation, e.g. --group EC IT PA",
    )
    parser.add_argument(
        "--no-full-text",
        action="store_true",
        help="Skip Pass 2 (index only).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between requests (default: 1.0).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    session = CurlSession(impersonate="chrome")

    # ── Pass 1: index ─────────────────────────────────────────────────────────
    print("\n[Pass 1] Fetching index page...")
    try:
        index_soup = fetch(INDEX_URL, session)
    except requests_exceptions.HTTPError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    records = scrape_index(index_soup)

    write_index_csv(records, out / "collective_agreements_index.csv")
    write_json(records, out / "collective_agreements_index.json")

    if args.no_full_text:
        print("\nDone (index only).")
        return

    # ── Pass 2: full agreements ───────────────────────────────────────────────
    print("\n[Pass 2] Scraping full agreement pages...")

    # Filter if --group specified
    filter_set = None
    if args.group:
        filter_set = {g.upper() for g in args.group}

    agreements_dir = out / "agreements"
    rates_dir = out / "rates_of_pay"
    agreements_dir.mkdir(exist_ok=True)
    rates_dir.mkdir(exist_ok=True)

    all_agreements = []
    failed = []

    for record in records:
        slug = group_slug(record)

        # Apply group filter
        if filter_set:
            # Match on the raw abbreviation string tokens
            abbrev_tokens = set(re.findall(r"[A-Za-z]+", record["abbreviation"]))
            if not abbrev_tokens.intersection(filter_set):
                continue

        url = record.get("url")
        if not url:
            print(f"  Skipping {slug}: no URL.")
            continue
        if url.startswith("/"):
            url = "https://www.canada.ca" + url

        print(f"  [{slug}] {record['group']}...")

        try:
            time.sleep(args.delay)
            page_soup = fetch(url, session)
            agreement = scrape_agreement(page_soup, url)
            agreement["index_record"] = record

            # Write per-group files
            group_dir = agreements_dir / slug
            group_dir.mkdir(exist_ok=True)

            write_json(agreement, group_dir / f"{slug}_full.json")

            txt_path = group_dir / f"{slug}_full.txt"
            txt_path.write_text(agreement_to_txt(agreement), encoding="utf-8")
            print(f"    Wrote txt: {txt_path}")

            write_rates_csv(agreement, rates_dir / f"{slug}_rates.csv")

            all_agreements.append(agreement)

        except Exception as e:
            print(f"  ERROR scraping {slug} ({url}): {e}", file=sys.stderr)
            failed.append({"slug": slug, "url": url, "error": str(e)})

    # Combined JSON
    write_json(all_agreements, out / "collective_agreements_all.json")

    if failed:
        write_json(failed, out / "scrape_errors.json")
        print(f"\nCompleted with {len(failed)} error(s) — see scrape_errors.json.")
    else:
        print(f"\nDone. {len(all_agreements)} agreements scraped successfully.")


if __name__ == "__main__":
    main()
