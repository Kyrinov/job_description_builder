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
