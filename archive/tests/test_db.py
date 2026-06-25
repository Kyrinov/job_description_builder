"""Tests for SQLite schema creation and sqlite-vec extension loading (DATA-01)."""
import pytest
import sqlite3


def test_sqlite_vec_loads(temp_db_path):
    """sqlite-vec extension must load without error on this machine."""
    import sqlite_vec
    con = sqlite3.connect(temp_db_path)
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    con.close()


def test_schema_creation(temp_db_path):
    """create_schema must create work_descriptions and wd_audit_log tables."""
    from app.db import get_connection, create_schema
    con = get_connection(temp_db_path)
    create_schema(con)
    tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "work_descriptions" in tables, f"work_descriptions not found in: {tables}"
    assert "wd_audit_log" in tables, f"wd_audit_log not found in: {tables}"
    con.close()


def test_vec_health_check_table_created(temp_db_path):
    """create_schema must create _vec_health_check table."""
    from app.db import get_connection, create_schema
    con = get_connection(temp_db_path)
    create_schema(con)
    tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "_vec_health_check" in tables
    con.close()


def test_schema_creation_idempotent(temp_db_path):
    """Running create_schema twice must not raise an error."""
    from app.db import get_connection, create_schema
    con = get_connection(temp_db_path)
    create_schema(con)
    create_schema(con)
    con.close()


def test_work_descriptions_columns(temp_db_path):
    """work_descriptions table must have required columns."""
    from app.db import get_connection, create_schema
    con = get_connection(temp_db_path)
    create_schema(con)
    info = con.execute("PRAGMA table_info(work_descriptions)").fetchall()
    col_names = {row[1] for row in info}
    required = {"id", "session_id", "stage", "data", "created_at", "last_modified"}
    assert required.issubset(col_names), f"Missing columns: {required - col_names}"
    con.close()


def test_wd_audit_log_columns(temp_db_path):
    """wd_audit_log must have required columns."""
    from app.db import get_connection, create_schema
    con = get_connection(temp_db_path)
    create_schema(con)
    info = con.execute("PRAGMA table_info(wd_audit_log)").fetchall()
    col_names = {row[1] for row in info}
    required = {"id", "wd_id", "event", "actor", "detail", "timestamp"}
    assert required.issubset(col_names), f"Missing columns: {required - col_names}"
    con.close()
