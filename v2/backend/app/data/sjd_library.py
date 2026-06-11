"""
app/data/sjd_library.py — Static SJD (Standard Job Description) library.

Sourced from `data/SJD Examples.txt` (DND internal SJD examples). Parsed at
module load time into a typed constant `SJD_LIBRARY: list[SJDEntry]` so the
rest of the app can iterate / filter / lookup without touching the filesystem.

The SJD file is a tab-delimited record stream. Each entry opens with
`Job Title\t<value>` and ends before the next blank line. There are exactly
10 entries covering AS, CT-FIN (->FI), EC, EN-ENG (->EN), IT, PE, and WP groups.

OG code normalization (RESEARCH.md verified):
  - "AS-01"        -> ("AS", 1)
  - "CT-FIN-04"    -> ("FI", 4)   # CT-FIN maps to FI occupational group
  - "EN-ENG-04"    -> ("EN", 4)   # EN-ENG maps to EN occupational group
  - "PE-04"        -> ("PE", 4)
  - "WP-03"        -> ("WP", 3)

Security (per threat model):
  T-22-01: sjd_number validated by lookup against this static constant; 404 on miss.
  T-22-02: og_code filter is case-insensitive equality check; no SQL; no eval.
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# SJDEntry — immutable typed record for one SJD
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SJDEntry:
    sjd_number: str          # e.g. "DND-PA-57047"
    job_code: str            # e.g. "57047"
    title: str               # e.g. "Compensation Agent"
    og_code: str             # normalized: "AS", "FI", "EC", "IT", "EN", "PE", "WP"
    og_level: int            # bare integer: 1, 3, 7, 4, 2, 5, 4, 3, 4, 3
    group_level_str: str     # original string: "AS-01"
    supervisory: bool        # True/False from "Yes"/"No"
    noc_code: str            # e.g. "13100"
    salary_range: str        # e.g. "$61,786 - $69,106"
    organizational_context: str
    streams: str


# ---------------------------------------------------------------------------
# Data file path
# ---------------------------------------------------------------------------
# sjd_library.py is at v2/backend/app/data/sjd_library.py.
# Five parents up reaches the repo root (job_description_builder/) which
# contains the data/ directory.
_SJD_FILE_PATH = pathlib.Path(__file__).parent.parent.parent.parent.parent / "data" / "SJD Examples.txt"


# ---------------------------------------------------------------------------
# OG normalization helper
# ---------------------------------------------------------------------------

def _og_code_from_group_level(group_level: str) -> tuple[str, int]:
    """Map a Group Level string to a (og_code, level) tuple.

    Special cases:
      - "CT-FIN-NN"  -> ("FI", NN)
      - "EN-ENG-NN"  -> ("EN", NN)
    Default: take the part before the first "-" as the OG code, the part
    after the last "-" as the integer level. Falls back to (string, 1) for
    unparseable inputs (defensive).
    """
    gl = group_level.strip()
    if gl.startswith("CT-FIN-"):
        return ("FI", int(gl.split("-")[-1]))
    if gl.startswith("EN-ENG-"):
        return ("EN", int(gl.split("-")[-1]))
    parts = gl.split("-")
    if len(parts) >= 2:
        return (parts[0], int(parts[-1]))
    return (gl, 1)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _is_blank(line: str) -> bool:
    """True if the line is an entry separator (empty, whitespace-only, or
    zero-width-space-only). The DND SJD file uses CRLF line endings and
    occasionally includes U+200B zero-width-space chars around boundaries."""
    return not line.replace("\u200b", "").strip()


def _parse_sjd_file(path: pathlib.Path) -> list[SJDEntry]:
    """Parse the SJD Examples.txt file into a list of SJDEntry records.

    The file format is a tab-delimited key-value stream with one blank line
    between entries. Multi-line `Organizational Context` fields continue onto
    subsequent non-tab lines until the next key-value pair or blank line —
    those continuation lines are not captured by this simple parser (the
    `Organizational Context` column on each entry is left empty when the
    value spans multiple physical lines). SJD_LIBRARY consumers do not
    currently require the full context text.
    """
    entries: list[SJDEntry] = []
    current: dict[str, str] = {}

    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            # Strip CRLF and any zero-width-space artifacts (U+200B) that
            # the source file occasionally inserts at line boundaries.
            line = raw_line.rstrip("\r\n").replace("\u200b", "")
            if _is_blank(line):
                if current.get("SJD Number"):
                    entries.append(_make_entry(current))
                current = {}
                continue
            if "\t" not in line:
                # Continuation of a multi-line field (e.g. Organizational
                # Context) — silently drop. See docstring.
                continue
            key, _, val = line.partition("\t")
            key = key.strip()
            val = val.strip()
            # Keep the first occurrence of each key. Some entries repeat
            # the Title field near the end of the record; we want the
            # canonical occurrence (first one).
            if key and key not in current:
                current[key] = val

    # Flush the final entry (file may not end with a blank line).
    if current.get("SJD Number"):
        entries.append(_make_entry(current))

    return entries


def _make_entry(d: dict[str, str]) -> SJDEntry:
    """Build an SJDEntry from a key-value dict for one SJD record."""
    group_level = d.get("Group Level", "")
    og_code, og_level = _og_code_from_group_level(group_level)

    # Supervisory is a free-text field; canonical "Yes" -> True, anything
    # else -> False. Default is False for safety.
    supervisory = d.get("Supervisory", "").strip().lower() == "yes"

    # NOC / CNP is a 5-digit code followed by a description; take the first
    # whitespace-delimited token. Empty string if the field is absent.
    noc_field = d.get("NOC / CNP", "")
    noc_code = noc_field.split()[0] if noc_field else ""

    return SJDEntry(
        sjd_number=d.get("SJD Number", ""),
        job_code=d.get("JobCode", ""),
        title=d.get("Job Title", ""),
        og_code=og_code,
        og_level=og_level,
        group_level_str=group_level,
        supervisory=supervisory,
        noc_code=noc_code,
        salary_range=d.get("Salary", ""),
        organizational_context=d.get("Organizational Context", ""),
        streams=d.get("Streams", ""),
    )


# ---------------------------------------------------------------------------
# Module-level constant — parsed once at import time
# ---------------------------------------------------------------------------

SJD_LIBRARY: list[SJDEntry] = _parse_sjd_file(_SJD_FILE_PATH)
