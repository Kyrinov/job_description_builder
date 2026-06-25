"""Tests for Phase 3: CA/JES Policy schema (03-02)."""
import sqlite3
import sys


def test_ca_jes_schema_ddl_exists():
    """app/db.py must export CA_JES_SCHEMA_DDL constant (03-02)."""
    from app.db import CA_JES_SCHEMA_DDL
    assert isinstance(CA_JES_SCHEMA_DDL, str)
    assert len(CA_JES_SCHEMA_DDL) > 0


def test_ca_clauses_table_created(ca_jes_db):
    """create_schema must create ca_clauses table (PIPE-02, CA-01)."""
    ca_jes_db.execute("SELECT name FROM sqlite_master WHERE name='ca_clauses'").fetchone()
    info = ca_jes_db.execute("PRAGMA table_info(ca_clauses)").fetchall()
    col_names = {row[1] for row in info}
    required = {"id", "og_code", "clause_type", "article_ref", "clause_text", "source_hash"}
    assert required.issubset(col_names), f"Missing columns: {required - col_names}"


def test_jes_factors_table_created(ca_jes_db):
    """create_schema must create jes_factors table (PIPE-03)."""
    ca_jes_db.execute("SELECT name FROM sqlite_master WHERE name='jes_factors'").fetchone()
    info = ca_jes_db.execute("PRAGMA table_info(jes_factors)").fetchall()
    col_names = {row[1] for row in info}
    required = {"id", "og_code", "factor_name", "factor_definition",
                "degree_descriptors", "point_values", "max_points", "source_hash"}
    assert required.issubset(col_names), f"Missing columns: {required - col_names}"


def test_policy_chunks_table_created(ca_jes_db):
    """create_schema must create policy_chunks table (Phase 5 prereq)."""
    ca_jes_db.execute("SELECT name FROM sqlite_master WHERE name='policy_chunks'").fetchone()
    info = ca_jes_db.execute("PRAGMA table_info(policy_chunks)").fetchall()
    col_names = {row[1] for row in info}
    required = {"id", "doc_name", "chunk_index", "chunk_text", "source_hash"}
    assert required.issubset(col_names), f"Missing columns: {required - col_names}"


def test_policy_fts_virtual_table_created(ca_jes_db):
    """create_schema must create policy_fts as FTS5 virtual table (Phase 5 CLASS-03 prereq)."""
    rows = ca_jes_db.execute(
        "SELECT type, name FROM sqlite_master WHERE name='policy_fts'"
    ).fetchall()
    assert len(rows) >= 1, "policy_fts not found in sqlite_master"
    # sqlite reports virtual tables as type='table' in sqlite_master
    assert any(name == 'policy_fts' for _, name in rows)


def test_create_schema_idempotent(ca_jes_db):
    """Running create_schema twice must not raise an error (idempotent DDL)."""
    con = ca_jes_db
    con.close()  # Close and re-open to test fresh
    import tempfile
    import os
    from app.db import get_connection, create_schema
    tmp = tempfile.mktemp()
    con = get_connection(tmp)
    create_schema(con)
    create_schema(con)  # second call — must not raise
    con.close()


def test_all_10_tables_created(ca_jes_db):
    """After create_schema, all 10 tables (Phase 1+2 + Phase 3) must exist."""
    from app.db import get_connection, create_schema
    con = ca_jes_db
    con.close()
    import tempfile
    import os
    con = get_connection(tempfile.mktemp())
    create_schema(con)
    tables = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','virtual_table')"
    ).fetchall()}
    required = {
        'work_descriptions', 'wd_audit_log', '_vec_health_check',
        'source_documents', 'index_metadata',
        'noc_units', 'noc_elements', 'noc_fts', 'noc_chunks_vec',
        'ca_clauses', 'jes_factors', 'policy_chunks', 'policy_fts',
    }
    missing = required - tables
    assert not missing, f"Missing tables: {missing}"
    con.close()


def test_create_schema_preserves_noc_exports():
    """All Phase 1+2 exports must still be available (no accidental breakage)."""
    from app.db import (
        get_connection, create_schema, assert_noc_index_model,
        NOC_SCHEMA_DDL, CA_JES_SCHEMA_DDL,
    )
    assert callable(get_connection)
    assert callable(create_schema)
    assert callable(assert_noc_index_model)
    assert isinstance(NOC_SCHEMA_DDL, str)
    assert isinstance(CA_JES_SCHEMA_DDL, str)
