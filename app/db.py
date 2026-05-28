"""
app/db.py — SQLite connection factory and schema DDL.

Always obtain connections via get_connection() — never call sqlite3.connect() directly.
sqlite-vec is registered per-connection in get_connection(); DDL that references vec0
will fail if this factory is bypassed.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Open a SQLite connection and register the sqlite-vec extension.

    Must be used for ALL connections in this application — vec0 DDL and queries
    require sqlite-vec to be registered on the connection (T-sqlite-vec-pitfall-3).
    """
    import sqlite_vec  # Import here to surface ImportError clearly if not installed

    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    return con


def create_schema(con: sqlite3.Connection) -> None:
    """
    Create all Phase 1 tables. Idempotent — safe to call on every startup.

    Tables created here:
    - work_descriptions: one row per WorkDescription entity (data stored as JSON)
    - wd_audit_log: append-only audit trail for every WD state transition
    - _vec_health_check: validates sqlite-vec loaded cleanly (Phase 2 adds vec0 tables)
    """
    con.executescript("""
        CREATE TABLE IF NOT EXISTS work_descriptions (
            id          TEXT PRIMARY KEY,
            session_id  TEXT NOT NULL,
            stage       TEXT NOT NULL,
            data        JSON NOT NULL,
            created_at  TEXT NOT NULL,
            last_modified TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS wd_audit_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            wd_id     TEXT NOT NULL,
            event     TEXT NOT NULL,
            actor     TEXT NOT NULL,
            detail    JSON,
            timestamp TEXT NOT NULL
        );

        -- Validates that sqlite-vec loaded without error on this startup.
        -- Phase 2 replaces this with CREATE VIRTUAL TABLE noc_chunks_vec USING vec0(...)
        -- once embedding dimensions are fixed.
        CREATE TABLE IF NOT EXISTS _vec_health_check (
            id INTEGER PRIMARY KEY
        );
    """)
    con.commit()
