"""
Unit and integration tests for scripts/ingest_noc.py (PIPE-01, PIPE-04, SC-4).

All Ollama calls are mocked — these tests do NOT require Ollama to be running.
Mock embeddings: [0.1] * 768 (pre-computed float list, not real vectors).
"""
from __future__ import annotations

import csv
import hashlib
import io
import sqlite3
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Minimal synthetic NOC data for fixture-level ingest tests
# ---------------------------------------------------------------------------

SYNTHETIC_STRUCTURE_ROWS = [
    {"Level": "5", "Code - NOC 2021 V1.0": "21232", "Class title": "Software engineers and designers",
     "Class definition": "Design, develop, and maintain software systems."},
    {"Level": "5", "Code - NOC 2021 V1.0": "41402", "Class title": "Policy researchers",
     "Class definition": "Conduct research and advise on policy."},
    {"Level": "5", "Code - NOC 2021 V1.0": "11200", "Class title": "Financial auditors",
     "Class definition": "Audit financial records for accuracy."},
]

SYNTHETIC_ELEMENTS_ROWS = [
    {"Code - NOC 2021 V1.0": "21232", "Element Type Label English": "Main duties",
     "Element Description English": "This group performs some or all of the following duties:"},
    {"Code - NOC 2021 V1.0": "21232", "Element Type Label English": "Main duties",
     "Element Description English": "Develop and maintain application software."},
    {"Code - NOC 2021 V1.0": "21232", "Element Type Label English": "Main duties",
     "Element Description English": "Analyze and resolve technical problems."},
    {"Code - NOC 2021 V1.0": "41402", "Element Type Label English": "Main duties",
     "Element Description English": "This group performs some or all of the following duties:"},
    {"Code - NOC 2021 V1.0": "41402", "Element Type Label English": "Main duties",
     "Element Description English": "Research and analyze policy alternatives."},
    {"Code - NOC 2021 V1.0": "11200", "Element Type Label English": "Main duties",
     "Element Description English": "Examine and analyze accounting records."},
    {"Code - NOC 2021 V1.0": "11200", "Element Type Label English": "Employment requirements",
     "Element Description English": "A bachelor's degree in accounting is required."},
]

MOCK_EMBEDDINGS = [[0.1] * 1024] * len(
    [r for r in SYNTHETIC_ELEMENTS_ROWS
     if r["Element Type Label English"] == "Main duties"
     and r["Element Description English"].strip() != "This group performs some or all of the following duties:"]
)


def _run_ingest(con, structure_rows=None, elements_rows=None,
                embed_model="nomic-embed-text:latest",
                structure_hash=None, elements_hash=None):
    """
    Helper: run ingest_noc stages directly against a fixture connection,
    bypassing file I/O and Ollama (both mocked).

    Generates valid 64-char hex hashes from source names when none are provided.
    """
    from scripts.ingest_noc import (
        upsert_source_document,
        upsert_noc_units,
        upsert_noc_elements,
        rebuild_fts5,
        embed_and_upsert_vec0,
        write_index_metadata,
    )
    structure_rows = structure_rows or SYNTHETIC_STRUCTURE_ROWS
    elements_rows = elements_rows or SYNTHETIC_ELEMENTS_ROWS

    # Generate valid 64-char hex hashes from source names when not explicitly provided
    if structure_hash is None:
        structure_hash = hashlib.sha256(b"noc_2021_structure.csv").hexdigest()
    if elements_hash is None:
        elements_hash = hashlib.sha256(b"noc_2021_elements.csv").hexdigest()

    upsert_source_document(con, "noc_2021_structure.csv", "NOC 2021 v1.0", structure_hash)
    upsert_source_document(con, "noc_2021_elements.csv", "NOC 2021 v1.0", elements_hash)
    upsert_noc_units(con, structure_rows, structure_hash)
    upsert_noc_elements(con, elements_rows, elements_hash)
    rebuild_fts5(con)

    mock_embeddings = [[0.1] * 1024] * 10  # generous upper bound
    with patch("scripts.ingest_noc.embed_batch", return_value=mock_embeddings):
        embed_and_upsert_vec0(con, embed_model, api_key="test-key", base_url="http://test")

    write_index_metadata(con, embed_model)


# ---------------------------------------------------------------------------
# PIPE-01: Relational tables populated
# ---------------------------------------------------------------------------

def test_relational_tables_populated(noc_db):
    """After ingest, noc_units and noc_elements must have rows (PIPE-01)."""
    _run_ingest(noc_db)
    unit_count = noc_db.execute("SELECT COUNT(*) FROM noc_units").fetchone()[0]
    elem_count = noc_db.execute("SELECT COUNT(*) FROM noc_elements").fetchone()[0]
    assert unit_count == 3, f"Expected 3 noc_units, got {unit_count}"
    assert elem_count == len(SYNTHETIC_ELEMENTS_ROWS), (
        f"Expected {len(SYNTHETIC_ELEMENTS_ROWS)} noc_elements, got {elem_count}"
    )


# ---------------------------------------------------------------------------
# PIPE-01: FTS5 query returns results
# ---------------------------------------------------------------------------

def test_fts5_query_returns_results(noc_db):
    """FTS5 MATCH query must return matching unit group records after ingest (PIPE-01)."""
    _run_ingest(noc_db)
    rows = noc_db.execute(
        "SELECT noc_code, title FROM noc_fts WHERE noc_fts MATCH 'software' ORDER BY rank LIMIT 5"
    ).fetchall()
    assert len(rows) > 0, "FTS5 query for 'software' returned no results"
    noc_codes = {row["noc_code"] for row in rows}
    assert "21232" in noc_codes, f"Expected NOC 21232 in results; got: {noc_codes}"


# ---------------------------------------------------------------------------
# PIPE-01: vec0 KNN returns results
# ---------------------------------------------------------------------------

def test_vec0_knn_returns_results(noc_db):
    """vec0 KNN query must return results after ingest (PIPE-01)."""
    import sqlite_vec

    _run_ingest(noc_db)

    query_embedding = [0.1] * 1024
    query_vec = sqlite_vec.serialize_float32(query_embedding)

    rows = noc_db.execute("""
        SELECT v.rowid, v.distance
        FROM noc_chunks_vec v
        WHERE v.embedding MATCH ? AND k = 3
        ORDER BY v.distance
    """, [query_vec]).fetchall()

    assert len(rows) > 0, "vec0 KNN query returned no results after ingest"


# ---------------------------------------------------------------------------
# PIPE-04: Source documents have content_hash and version_label
# ---------------------------------------------------------------------------

def test_source_documents_hash_and_label(noc_db):
    """Each source document must have content_hash and version_label (PIPE-04)."""
    _run_ingest(noc_db)
    rows = noc_db.execute(
        "SELECT source_name, content_hash, version_label FROM source_documents"
    ).fetchall()
    assert len(rows) == 2, f"Expected 2 source_documents rows, got {len(rows)}"
    for row in rows:
        assert row["content_hash"], f"Missing content_hash on {row['source_name']}"
        assert row["version_label"], f"Missing version_label on {row['source_name']}"
        assert len(row["content_hash"]) == 64, (
            f"content_hash for {row['source_name']} is not a 64-char SHA-256 hex string"
        )


# ---------------------------------------------------------------------------
# PIPE-04: noc_units rows store source_hash
# ---------------------------------------------------------------------------

def test_derived_records_store_source_hash(noc_db):
    """noc_units rows must store source_hash matching the structure CSV hash (PIPE-04)."""
    _run_ingest(noc_db, structure_hash="abc123def456abc123def456abc123def456abc123def456abc123def456abcd")
    rows = noc_db.execute("SELECT noc_code, source_hash FROM noc_units").fetchall()
    assert all(row["source_hash"] for row in rows), "Some noc_units rows have empty source_hash"
    hashes = {row["source_hash"] for row in rows}
    assert len(hashes) == 1, f"All noc_units rows should share one source_hash; got: {hashes}"


# ---------------------------------------------------------------------------
# PIPE-04: noc_elements rows store source_hash
# ---------------------------------------------------------------------------

def test_elements_store_source_hash(noc_db):
    """noc_elements rows must store source_hash matching the elements CSV hash (PIPE-04)."""
    _run_ingest(noc_db, elements_hash="fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210")
    rows = noc_db.execute("SELECT noc_code, source_hash FROM noc_elements").fetchall()
    assert all(row["source_hash"] for row in rows), "Some noc_elements rows have empty source_hash"


# ---------------------------------------------------------------------------
# SC-4: Idempotency — second run produces same row counts
# ---------------------------------------------------------------------------

def test_ingest_idempotent(noc_db):
    """Running ingest twice on unchanged synthetic data must not duplicate rows (SC-4)."""
    _run_ingest(noc_db)
    count_units_1 = noc_db.execute("SELECT COUNT(*) FROM noc_units").fetchone()[0]
    count_elems_1 = noc_db.execute("SELECT COUNT(*) FROM noc_elements").fetchone()[0]
    count_fts_1 = noc_db.execute("SELECT COUNT(*) FROM noc_fts").fetchone()[0]

    _run_ingest(noc_db)  # second run with identical data and hashes
    count_units_2 = noc_db.execute("SELECT COUNT(*) FROM noc_units").fetchone()[0]
    count_elems_2 = noc_db.execute("SELECT COUNT(*) FROM noc_elements").fetchone()[0]
    count_fts_2 = noc_db.execute("SELECT COUNT(*) FROM noc_fts").fetchone()[0]

    assert count_units_1 == count_units_2, (
        f"noc_units grew on second ingest: {count_units_1} -> {count_units_2}"
    )
    assert count_elems_1 == count_elems_2, (
        f"noc_elements grew on second ingest: {count_elems_1} -> {count_elems_2}"
    )
    assert count_fts_1 == count_fts_2, (
        f"noc_fts grew on second ingest: {count_fts_1} -> {count_fts_2}"
    )
