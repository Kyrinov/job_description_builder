"""
test_db.py — contract for SQLite schema creation.

Wave 0 stub: fails because app.db does not exist.
Plan 02 implements get_connection and create_schema; these tests must pass after.
"""
import pytest
import sqlite3


def test_create_schema_creates_work_descriptions(tmp_db_path, env_with_db):
    """create_schema() must create work_descriptions and audit_log tables."""
    from app.db import get_connection, create_schema  # Wave 0: ImportError
    con = get_connection(tmp_db_path)
    create_schema(con)
    tables = {row[0] for row in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "work_descriptions" in tables
    assert "audit_log" in tables
    con.close()


def test_create_schema_is_idempotent(tmp_db_path, env_with_db):
    """Calling create_schema() twice must not raise."""
    from app.db import get_connection, create_schema
    con = get_connection(tmp_db_path)
    create_schema(con)
    create_schema(con)  # Must not raise
    con.close()
