"""
Unit tests for scripts/ingest_jes.py (PIPE-03, PIPE-04).

All Ollama calls are mocked. Synthetic factor data is injected directly into
upsert_jes_factors().
"""
from __future__ import annotations

import hashlib
import json

import pytest


# --------------------------------------------------------------------
# Synthetic JES factor data (mirrors what extract_factors_via_llm would return)
# --------------------------------------------------------------------

SYNTHETIC_EC_FACTORS = [
    {
        "factor_name": "Decision Making",
        "factor_definition": "Measures latitude applied and impact of decision making.",
        "degree_descriptors": [
            {"degree": "D1", "text": "Issue-specific, impact on own work unit.",      "points": 5},
            {"degree": "D2", "text": "Defined scope, impact on team objectives.",     "points": 15},
            {"degree": "D3", "text": "Broader analytical scope.",                     "points": 35},
            {"degree": "D4", "text": "Multiple programs.",                            "points": 60},
            {"degree": "D5", "text": "Significant policy implications.",              "points": 90},
            {"degree": "D6", "text": "Departmental-level decisions.",                 "points": 125},
            {"degree": "D7", "text": "Inter-departmental decisions.",                 "points": 165},
            {"degree": "D8", "text": "Government-wide decisions.",                    "points": 210},
        ],
        "point_values": {"D1": 5, "D2": 15, "D3": 35, "D4": 60, "D5": 90, "D6": 125, "D7": 165, "D8": 210},
        "max_points": 210,
    },
    {
        "factor_name": "Working Conditions",
        "factor_definition": "Measures the physical and psychological environment.",
        "degree_descriptors": [
            {"degree": "D1", "text": "Normal office environment.",         "points": 5},
            {"degree": "D2", "text": "Occasional discomfort or stress.",   "points": 15},
            {"degree": "D3", "text": "Frequent stress or travel.",         "points": 30},
        ],
        "point_values": {"D1": 5, "D2": 15, "D3": 30},
        "max_points": 30,
    },
]


def _hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _run_jes_ingest(
    con,
    source_name: str = "EC Economics and Social Science Services - Job Evaluation Standard 2017.txt",
    og_code: str = "EC",
    factors: list[dict] | None = None,
    source_hash: str | None = None,
    version_label: str = "JES v1.0",
):
    """Helper: run ingest_jes stages directly, bypassing file I/O and Ollama."""
    from scripts.ingest_jes import (
        upsert_source_document,
        upsert_jes_factors,
    )
    factors = factors or SYNTHETIC_EC_FACTORS
    if source_hash is None:
        source_hash = _hash(source_name.encode("utf-8"))

    upsert_source_document(con, source_name, version_label, source_hash)
    upsert_jes_factors(con, og_code, factors, source_hash)


# --------------------------------------------------------------------
# PIPE-04: source_documents row written per JES file
# --------------------------------------------------------------------

def test_jes_ingest_creates_source_document_row(ca_jes_db):
    """After ingest, source_documents has a row for the JES TXT with 64-char content_hash (PIPE-04)."""
    _run_jes_ingest(ca_jes_db)
    row = ca_jes_db.execute(
        "SELECT content_hash FROM source_documents WHERE source_name LIKE 'EC Economics%'"
    ).fetchone()
    assert row is not None, "source_documents row for EC JES missing after ingest"
    assert len(row["content_hash"]) == 64


# --------------------------------------------------------------------
# PIPE-03: jes_factors rows present, queryable by (og_code, factor_name)
# --------------------------------------------------------------------

def test_jes_ingest_creates_factor_rows(ca_jes_db):
    """SELECT FROM jes_factors WHERE og_code='EC' AND factor_name LIKE '%Decision%' returns 1 row (PIPE-03)."""
    _run_jes_ingest(ca_jes_db)
    rows = ca_jes_db.execute(
        "SELECT factor_name, max_points FROM jes_factors WHERE og_code = 'EC' AND factor_name LIKE '%Decision%'"
    ).fetchall()
    assert len(rows) == 1, f"Expected 1 Decision-Making factor row for EC; got {len(rows)}"
    assert rows[0]["max_points"] == 210, f"Expected max_points=210; got {rows[0]['max_points']}"


def test_jes_factor_query_by_og_and_name(ca_jes_db):
    """Querying jes_factors by (og_code, factor_name) returns the correct factor (PIPE-03)."""
    _run_jes_ingest(ca_jes_db)
    row = ca_jes_db.execute(
        "SELECT factor_definition FROM jes_factors WHERE og_code = ? AND factor_name = ?",
        ["EC", "Working Conditions"],
    ).fetchone()
    assert row is not None
    assert "physical and psychological environment" in row["factor_definition"]


# --------------------------------------------------------------------
# PIPE-03: degree_descriptors stored as valid JSON with degree+points keys
# --------------------------------------------------------------------

def test_jes_ingest_factor_has_degree_descriptors(ca_jes_db):
    """degree_descriptors column must be valid JSON list with 'degree' and 'points' keys (PIPE-03)."""
    _run_jes_ingest(ca_jes_db)
    row = ca_jes_db.execute(
        "SELECT degree_descriptors FROM jes_factors WHERE og_code = 'EC' AND factor_name = 'Decision Making'"
    ).fetchone()
    assert row is not None
    descriptors = json.loads(row["degree_descriptors"])
    assert isinstance(descriptors, list)
    assert len(descriptors) == 8
    for d in descriptors:
        assert "degree" in d, f"Missing 'degree' key in descriptor: {d}"
        assert "points" in d, f"Missing 'points' key in descriptor: {d}"


# --------------------------------------------------------------------
# PIPE-04: derived rows store source_hash
# --------------------------------------------------------------------

def test_jes_factors_store_source_hash(ca_jes_db):
    """Each jes_factors row carries the source_hash of the originating JES TXT (PIPE-04)."""
    known_hash = "b" * 64
    _run_jes_ingest(ca_jes_db, source_hash=known_hash)
    rows = ca_jes_db.execute("SELECT source_hash FROM jes_factors WHERE og_code = 'EC'").fetchall()
    assert all(row["source_hash"] == known_hash for row in rows)


# --------------------------------------------------------------------
# Idempotency
# --------------------------------------------------------------------

def test_jes_ingest_idempotent(ca_jes_db):
    """Running JES ingest twice on identical data does not duplicate rows."""
    _run_jes_ingest(ca_jes_db)
    count_1 = ca_jes_db.execute("SELECT COUNT(*) FROM jes_factors").fetchone()[0]
    _run_jes_ingest(ca_jes_db)
    count_2 = ca_jes_db.execute("SELECT COUNT(*) FROM jes_factors").fetchone()[0]
    assert count_1 == count_2, f"jes_factors grew on second ingest: {count_1} -> {count_2}"


def test_discover_jes_files_includes_extensionless_sources(tmp_path):
    """JES discovery must not require a .txt suffix."""
    from scripts.ingest_jes import discover_jes_files

    standard = tmp_path / "MT Meteorology - Job Evaluation Standard"
    txt_standard = tmp_path / "EC Economics - Job Evaluation Standard.txt"
    guidelines = tmp_path / "FS Foreign Service - Application Guidelines.txt"
    hidden = tmp_path / ".~lock.ignore"
    for path in (standard, txt_standard, guidelines, hidden):
        path.write_text("payload", encoding="utf-8")

    files, skipped = discover_jes_files(tmp_path)

    assert [p.name for p in files] == [
        "EC Economics - Job Evaluation Standard.txt",
        "MT Meteorology - Job Evaluation Standard",
    ]
    assert skipped == ["FS Foreign Service - Application Guidelines.txt"]


def test_chunk_text_uses_full_document_without_truncating():
    """Long JES documents are chunked rather than silently sliced at 40k chars."""
    from scripts.ingest_jes import chunk_text

    text = "\n".join(f"paragraph {i} " + ("x" * 80) for i in range(120))
    chunks = chunk_text(text, max_chars=1000, overlap_chars=100)

    assert len(chunks) > 1
    assert "paragraph 0" in chunks[0]
    assert "paragraph 119" in chunks[-1]


def test_merge_extracted_factors_combines_overlap_duplicates():
    """Duplicate factor records from chunk overlap should become one richer factor."""
    from scripts.ingest_jes import merge_extracted_factors

    factors = [
        {
            "factor_name": "Decision Making",
            "factor_definition": "short",
            "degree_descriptors": [{"degree": "D1", "text": "short", "points": 5}],
            "point_values": {"D1": 5},
            "max_points": 5,
        },
        {
            "factor_name": "decision making",
            "factor_definition": "longer definition",
            "degree_descriptors": [
                {"degree": "D1", "text": "longer descriptor", "points": 5},
                {"degree": "D2", "text": "second descriptor", "points": 15},
            ],
            "point_values": {"D2": 15},
            "max_points": 15,
        },
    ]

    merged = merge_extracted_factors(factors)

    assert len(merged) == 1
    assert merged[0]["factor_definition"] == "longer definition"
    assert merged[0]["point_values"] == {"D1": 5, "D2": 15}
    assert len(merged[0]["degree_descriptors"]) == 2
    assert merged[0]["max_points"] == 15


_SYNTHETIC_METADATA = {
    "group_definition": "Test group definition.",
    "inclusions": "Includes test positions.",
    "exclusions": "Excludes other positions.",
    "methodology": "point-rating",
    "subgroups": [],
}


def test_process_one_jes_reextracts_changed_source(ca_jes_db, tmp_path, monkeypatch):
    """Changed source hashes must replace stale factors instead of skipping."""
    import scripts.ingest_jes as ingest_jes

    path = tmp_path / "EC Economics and Social Science Services - Job Evaluation Standard 2017.txt"
    path.write_text("old source", encoding="utf-8")
    old_hash = _hash(b"old source")
    new_hash = _hash(b"new source")
    _run_jes_ingest(ca_jes_db, source_name=path.name, source_hash=old_hash)

    replacement = [
        {
            "factor_name": "New Factor",
            "factor_definition": "Replacement factor.",
            "degree_descriptors": [{"degree": "D1", "text": "replacement", "points": 10}],
            "point_values": {"D1": 10},
            "max_points": 10,
        }
    ]
    monkeypatch.setattr(ingest_jes, "extract_factors_from_chunks", lambda *args, **kwargs: replacement)
    monkeypatch.setattr(ingest_jes, "extract_group_metadata_via_llm", lambda *args, **kwargs: _SYNTHETIC_METADATA)

    path.write_text("new source", encoding="utf-8")
    og_code, count = ingest_jes.process_one_jes(
        ca_jes_db,
        path,
        "gemma4:31b",
        "JES v1.0",
        65536,
        4096,
        "http://localhost:11434/v1",
        35000,
        1200,
        1800.0,
    )

    assert og_code == "EC"
    assert count == 1
    rows = ca_jes_db.execute("SELECT factor_name, source_hash FROM jes_factors WHERE og_code = 'EC'").fetchall()
    assert [(row["factor_name"], row["source_hash"]) for row in rows] == [("New Factor", new_hash)]
    source = ca_jes_db.execute(
        "SELECT content_hash FROM source_documents WHERE source_name = ?",
        [path.name],
    ).fetchone()
    assert source["content_hash"] == new_hash


def test_process_one_jes_failed_reextract_preserves_existing_rows(ca_jes_db, tmp_path, monkeypatch):
    """A chunk failure must not delete previously ingested factors or update the source hash."""
    import scripts.ingest_jes as ingest_jes

    path = tmp_path / "EC Economics and Social Science Services - Job Evaluation Standard 2017.txt"
    path.write_text("old source", encoding="utf-8")
    old_hash = _hash(b"old source")
    _run_jes_ingest(ca_jes_db, source_name=path.name, source_hash=old_hash)

    def fail_extract(*args, **kwargs):
        raise RuntimeError("chunk failed")

    monkeypatch.setattr(ingest_jes, "extract_factors_from_chunks", fail_extract)
    monkeypatch.setattr(ingest_jes, "extract_group_metadata_via_llm", lambda *args, **kwargs: _SYNTHETIC_METADATA)

    path.write_text("new source", encoding="utf-8")
    with pytest.raises(RuntimeError, match="chunk failed"):
        ingest_jes.process_one_jes(
            ca_jes_db,
            path,
            "gemma4:31b",
            "JES v1.0",
            65536,
            4096,
            "http://localhost:11434/v1",
            35000,
            1200,
            1800.0,
        )

    names = ca_jes_db.execute("SELECT factor_name FROM jes_factors WHERE og_code = 'EC'").fetchall()
    assert {row["factor_name"] for row in names} == {"Decision Making", "Working Conditions"}
    source = ca_jes_db.execute(
        "SELECT content_hash FROM source_documents WHERE source_name = ?",
        [path.name],
    ).fetchone()
    assert source["content_hash"] == old_hash


# --------------------------------------------------------------------
# Pre-processing: web boilerplate stripping
# --------------------------------------------------------------------

_WEB_NAV_HEADER = """\
    Skip to main content
    Skip to "About government"
    Switch to basic HTML version

Language selection

    Français

Government of Canada / Gouvernement du Canada
Search
Search Canada.ca
Menu
You are here:

    Canada.ca Treasury Board of Canada Secretariat Job evaluation standards for public service employees

Information Technology Job Evaluation Standard
Amendments
"""

_CLEAN_HEADER = """\
SOURCE: https://www.canada.ca/en/treasury-board-secretariat/services/collective-agreements/job-evaluation/ec.html
TITLE ON INDEX PAGE: EC Job Evaluation Standard 2017
EFFECTIVE DATE: October 6, 2023

EC GROUP JOB EVALUATION STANDARD
"""


def test_strip_web_boilerplate_removes_nav_header():
    """Web nav boilerplate is stripped; real document title is the new first line."""
    from scripts.ingest_jes import strip_web_boilerplate

    result = strip_web_boilerplate(_WEB_NAV_HEADER + "Some factor content\n")
    assert result.splitlines()[0] == "Information Technology Job Evaluation Standard"
    assert "Skip to main content" not in result
    assert "Canada.ca Treasury Board" not in result
    assert "Some factor content" in result


def test_strip_web_boilerplate_leaves_clean_format_unchanged():
    """Files already in clean SOURCE: format are not modified."""
    from scripts.ingest_jes import strip_web_boilerplate

    result = strip_web_boilerplate(_CLEAN_HEADER + "Factor content\n")
    assert result == _CLEAN_HEADER + "Factor content\n"


# --------------------------------------------------------------------
# Pre-processing: benchmark section stripping
# --------------------------------------------------------------------

_RATING_SCALES = "Element 1: Critical Thinking\nD1 (5 pts): Basic analysis.\nD2 (20 pts): Complex analysis.\n\n"
_BENCHMARK_BODY = "Benchmark 1: Infrastructure Support Technician\nKey activities:\n- Maintains servers.\n"


def test_strip_benchmark_section_cuts_at_benchmark_marker():
    """Text before the first 'Benchmark N: Title' line is the rating-scales portion."""
    from scripts.ingest_jes import strip_benchmark_section

    rating, benchmarks = strip_benchmark_section(_RATING_SCALES + _BENCHMARK_BODY)
    assert "Element 1" in rating
    assert "D1" in rating
    assert "Benchmark 1" not in rating
    assert "Infrastructure Support Technician" in benchmarks


def test_strip_benchmark_section_no_benchmarks_returns_whole_text():
    """Documents without benchmark position descriptions are returned whole."""
    from scripts.ingest_jes import strip_benchmark_section

    text = "Element 1: Knowledge\nD1 (5 pts): Basic.\n"
    rating, benchmarks = strip_benchmark_section(text)
    assert rating == text
    assert benchmarks == ""


def test_strip_benchmark_section_does_not_cut_toc_entries():
    """Indented TOC mentions of 'Benchmark Position Descriptions' are not cut points."""
    from scripts.ingest_jes import strip_benchmark_section

    toc_line = "    Benchmark Position Descriptions\n"
    text = toc_line + _RATING_SCALES + _BENCHMARK_BODY
    rating, _ = strip_benchmark_section(text)
    assert "Element 1" in rating


# --------------------------------------------------------------------
# jes_og_metadata: upsert stores and overwrites group metadata
# --------------------------------------------------------------------

def test_upsert_og_metadata_stores_inclusions_exclusions(ca_jes_db):
    """upsert_og_metadata writes inclusions and exclusions to jes_og_metadata."""
    from scripts.ingest_jes import upsert_og_metadata

    upsert_og_metadata(ca_jes_db, "IT", _SYNTHETIC_METADATA, "a" * 64)
    row = ca_jes_db.execute(
        "SELECT group_definition, inclusions, exclusions, methodology FROM jes_og_metadata WHERE og_code = 'IT'"
    ).fetchone()
    assert row is not None
    assert row["inclusions"] == "Includes test positions."
    assert row["exclusions"] == "Excludes other positions."
    assert row["methodology"] == "point-rating"


def test_upsert_og_metadata_is_idempotent(ca_jes_db):
    """Calling upsert_og_metadata twice on the same og_code does not create duplicate rows."""
    from scripts.ingest_jes import upsert_og_metadata

    upsert_og_metadata(ca_jes_db, "IT", _SYNTHETIC_METADATA, "a" * 64)
    upsert_og_metadata(ca_jes_db, "IT", {**_SYNTHETIC_METADATA, "inclusions": "Updated inclusions."}, "b" * 64)
    rows = ca_jes_db.execute("SELECT inclusions FROM jes_og_metadata WHERE og_code = 'IT'").fetchall()
    assert len(rows) == 1
    assert rows[0]["inclusions"] == "Updated inclusions."
