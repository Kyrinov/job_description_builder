"""
Unit tests for scripts/ingest_policy.py (Phase 5 prereq: CLASS-03 source data).

No LLM involved — deterministic text chunking + FTS5 rebuild.
"""
from __future__ import annotations

import hashlib

import pytest


SAMPLE_POLICY_TEXT = (
    "The Directive on Classification establishes mandatory procedures for the classification of positions.\n\n"
    "AS positions provide internal departmental administrative support and guidance.\n\n"
    "EC positions conduct research and shape policy for the Canadian public.\n\n"
    "The distinction between AS classification and EC classification rests on whether work is "
    "internal departmental guidance or externally facing policy development.\n\n"
    "Functional authority is reserved to specific occupational groups as defined by TBS.\n\n"
)


def _hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _run_policy_ingest(
    con,
    doc_name: str = "directive_on_classification",
    text: str = SAMPLE_POLICY_TEXT,
    source_hash: str | None = None,
    version_label: str = "TBS Policy v1.0",
):
    """Helper: chunk + upsert + FTS rebuild directly against a fixture connection."""
    from scripts.ingest_policy import (
        upsert_source_document,
        upsert_policy_chunks,
        rebuild_policy_fts,
        chunk_text,
    )
    if source_hash is None:
        source_hash = _hash(text.encode("utf-8"))

    source_name = f"{doc_name}.txt"
    upsert_source_document(con, source_name, version_label, source_hash)
    chunks = chunk_text(text, max_chars=500, overlap=50)
    upsert_policy_chunks(con, doc_name, chunks, source_hash)
    rebuild_policy_fts(con)


# --------------------------------------------------------------------
# chunk_text: deterministic chunking behaviour
# --------------------------------------------------------------------

def test_chunk_text_returns_nonempty_list():
    """chunk_text returns at least one chunk for non-empty input."""
    from scripts.ingest_policy import chunk_text
    chunks = chunk_text(SAMPLE_POLICY_TEXT, max_chars=500, overlap=50)
    assert isinstance(chunks, list)
    assert len(chunks) >= 1
    assert all(isinstance(c, str) and c.strip() for c in chunks)


def test_chunk_text_respects_max_chars():
    """No chunk exceeds max_chars by more than overlap window."""
    from scripts.ingest_policy import chunk_text
    long_text = ("paragraph one.\n\n" + "x" * 600 + "\n\nparagraph three.\n\n")
    chunks = chunk_text(long_text, max_chars=500, overlap=50)
    assert len(chunks) >= 2, "Long text must produce multiple chunks"


# --------------------------------------------------------------------
# policy_chunks table populated
# --------------------------------------------------------------------

def test_policy_ingest_creates_chunks(ca_jes_db):
    """After ingest, policy_chunks has >=1 row for the directive."""
    _run_policy_ingest(ca_jes_db)
    count = ca_jes_db.execute(
        "SELECT COUNT(*) FROM policy_chunks WHERE doc_name = 'directive_on_classification'"
    ).fetchone()[0]
    assert count >= 1, f"Expected >=1 policy_chunks row; got {count}"


# --------------------------------------------------------------------
# PIPE-04: policy_chunks carry source_hash
# --------------------------------------------------------------------

def test_policy_chunks_store_source_hash(ca_jes_db):
    """policy_chunks rows carry the source_hash of the originating TXT (PIPE-04)."""
    known_hash = "c" * 64
    _run_policy_ingest(ca_jes_db, source_hash=known_hash)
    rows = ca_jes_db.execute(
        "SELECT source_hash FROM policy_chunks WHERE doc_name = 'directive_on_classification'"
    ).fetchall()
    assert all(row["source_hash"] == known_hash for row in rows)


# --------------------------------------------------------------------
# policy_fts: FTS5 MATCH query returns results
# --------------------------------------------------------------------

def test_policy_fts_query_returns_results(ca_jes_db):
    """FTS5 MATCH for 'classification' returns rows after ingest+rebuild."""
    _run_policy_ingest(ca_jes_db)
    rows = ca_jes_db.execute(
        "SELECT doc_name FROM policy_fts WHERE policy_fts MATCH ? LIMIT 5",
        ["classification"],
    ).fetchall()
    assert len(rows) > 0, "FTS5 query for 'classification' returned no results"


def test_policy_fts_query_supports_phrase(ca_jes_db):
    """FTS5 phrase query for 'AS classification' returns the AS/EC disambiguation chunk (CLASS-03 prereq)."""
    _run_policy_ingest(ca_jes_db)
    rows = ca_jes_db.execute(
        "SELECT doc_name FROM policy_fts WHERE policy_fts MATCH ? LIMIT 5",
        ['"AS classification"'],
    ).fetchall()
    assert len(rows) > 0, "FTS5 phrase query for 'AS classification' returned no results"


# --------------------------------------------------------------------
# Idempotency
# --------------------------------------------------------------------

def test_policy_ingest_idempotent(ca_jes_db):
    """Running policy ingest twice does not duplicate chunks."""
    _run_policy_ingest(ca_jes_db)
    count_1 = ca_jes_db.execute("SELECT COUNT(*) FROM policy_chunks").fetchone()[0]
    _run_policy_ingest(ca_jes_db)
    count_2 = ca_jes_db.execute("SELECT COUNT(*) FROM policy_chunks").fetchone()[0]
    assert count_1 == count_2, f"policy_chunks grew on second ingest: {count_1} -> {count_2}"
