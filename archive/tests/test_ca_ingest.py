"""
Unit tests for scripts/ingest_ca.py (PIPE-02, CA-01, PIPE-04).

All Ollama calls are mocked — these tests do NOT require Ollama to be running.
Synthetic clause data is injected directly into upsert_ca_clauses().
"""
from __future__ import annotations

import hashlib
import json

import pytest


# --------------------------------------------------------------------
# Synthetic CA clause data (mirrors what extract_clauses_via_llm would return)
# --------------------------------------------------------------------

SYNTHETIC_EC_CLAUSES = [
    {"clause_type": "scope",       "article_ref": "Article 1",  "clause_text": "This agreement applies to all employees in the Economics and Social Science Services group."},
    {"clause_type": "restriction", "article_ref": "Article 7",  "clause_text": "Employees shall not be required to perform duties outside the EC group definition without consent."},
    {"clause_type": "exclusion",   "article_ref": "Article 2",  "clause_text": "Persons appointed for periods of less than three months are excluded."},
    {"clause_type": "definition",  "article_ref": "Article 2",  "clause_text": "'Employee' means a person employed in the public service who is a member of the bargaining unit."},
]

SYNTHETIC_IT_CS_CLAUSES = [
    {"clause_type": "scope",       "article_ref": "Article 1",  "clause_text": "Applies to all IT and CS group employees."},
    {"clause_type": "restriction", "article_ref": "Article 11", "clause_text": "On-call duties limited to operational requirements."},
]


def _hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _run_ca_ingest(
    con,
    source_name: str = "EC_full.json",
    og_codes: list[str] | None = None,
    clauses: list[dict] | None = None,
    source_hash: str | None = None,
    version_label: str = "CA 2023-2026 v1.0",
):
    """
    Helper: run ingest_ca stages directly against a fixture connection,
    bypassing file I/O and Ollama (both mocked).
    """
    from scripts.ingest_ca import (
        upsert_source_document,
        upsert_ca_clauses,
    )
    og_codes = og_codes or ["EC"]
    clauses = clauses or SYNTHETIC_EC_CLAUSES
    if source_hash is None:
        source_hash = _hash(source_name.encode("utf-8"))

    upsert_source_document(con, source_name, version_label, source_hash)
    upsert_ca_clauses(con, og_codes, clauses, source_hash)


# --------------------------------------------------------------------
# PIPE-04: source_documents row written per CA file
# --------------------------------------------------------------------

def test_ca_ingest_creates_source_document_row(ca_jes_db):
    """After ingest, source_documents has a row for EC_full.json with 64-char content_hash (PIPE-04)."""
    _run_ca_ingest(ca_jes_db)
    row = ca_jes_db.execute(
        "SELECT content_hash, version_label FROM source_documents WHERE source_name = 'EC_full.json'"
    ).fetchone()
    assert row is not None, "source_documents row for EC_full.json missing after ingest"
    assert len(row["content_hash"]) == 64, "content_hash must be 64-char SHA-256 hex"
    assert row["version_label"], "version_label must be non-empty"


# --------------------------------------------------------------------
# PIPE-02 + CA-01: ca_clauses rows present, queryable by og_code
# --------------------------------------------------------------------

def test_ca_ingest_creates_clause_rows(ca_jes_db):
    """After ingest, ca_clauses has >=1 row for og_code='EC' (PIPE-02, CA-01)."""
    _run_ca_ingest(ca_jes_db)
    count = ca_jes_db.execute(
        "SELECT COUNT(*) FROM ca_clauses WHERE og_code = 'EC'"
    ).fetchone()[0]
    assert count >= 1, f"Expected >=1 ca_clauses row for EC; got {count}"


def test_ca_clause_query_by_og(ca_jes_db):
    """Querying ca_clauses by og_code returns rows with clause_type, article_ref, clause_text (PIPE-02)."""
    _run_ca_ingest(ca_jes_db)
    rows = ca_jes_db.execute(
        "SELECT og_code, clause_type, article_ref, clause_text FROM ca_clauses WHERE og_code = 'EC'"
    ).fetchall()
    assert len(rows) == len(SYNTHETIC_EC_CLAUSES)
    clause_types = {row["clause_type"] for row in rows}
    assert {"scope", "restriction", "exclusion", "definition"}.issubset(clause_types)


# --------------------------------------------------------------------
# PIPE-04: derived rows store source_hash
# --------------------------------------------------------------------

def test_ca_clauses_store_source_hash(ca_jes_db):
    """Each ca_clauses row carries the source_hash of the originating CA file (PIPE-04)."""
    known_hash = "a" * 64
    _run_ca_ingest(ca_jes_db, source_hash=known_hash)
    rows = ca_jes_db.execute("SELECT source_hash FROM ca_clauses WHERE og_code = 'EC'").fetchall()
    assert all(row["source_hash"] == known_hash for row in rows), \
        "ca_clauses rows must store the CA file's source_hash"


# --------------------------------------------------------------------
# Idempotency (SC-4 analog for CA corpus)
# --------------------------------------------------------------------

def test_ca_ingest_idempotent(ca_jes_db):
    """Running ingest twice on identical input produces identical row count (idempotency)."""
    _run_ca_ingest(ca_jes_db)
    count_1 = ca_jes_db.execute("SELECT COUNT(*) FROM ca_clauses").fetchone()[0]
    _run_ca_ingest(ca_jes_db)
    count_2 = ca_jes_db.execute("SELECT COUNT(*) FROM ca_clauses").fetchone()[0]
    assert count_1 == count_2, f"ca_clauses grew on second ingest: {count_1} -> {count_2}"


# --------------------------------------------------------------------
# PIPE-02: multi-OG CA produces one row set per OG code
# --------------------------------------------------------------------

def test_ca_ingest_multi_og_ca(ca_jes_db):
    """IT_CS ingest creates rows for both og_code='IT' and og_code='CS' (PIPE-02 multi-OG)."""
    _run_ca_ingest(
        ca_jes_db,
        source_name="IT_CS_full.json",
        og_codes=["IT", "CS"],
        clauses=SYNTHETIC_IT_CS_CLAUSES,
    )
    it_count = ca_jes_db.execute("SELECT COUNT(*) FROM ca_clauses WHERE og_code = 'IT'").fetchone()[0]
    cs_count = ca_jes_db.execute("SELECT COUNT(*) FROM ca_clauses WHERE og_code = 'CS'").fetchone()[0]
    assert it_count == len(SYNTHETIC_IT_CS_CLAUSES), f"Expected {len(SYNTHETIC_IT_CS_CLAUSES)} IT rows, got {it_count}"
    assert cs_count == len(SYNTHETIC_IT_CS_CLAUSES), f"Expected {len(SYNTHETIC_IT_CS_CLAUSES)} CS rows, got {cs_count}"
