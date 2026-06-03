"""
app/db.py — SQLite connection factory and schema DDL.

v2.0 uses a single-file SQLite at DB_PATH (configured via Settings).
The two tables are work_descriptions and audit_log. No sqlite-vec,
no FTS5 — v2.0 is a single-user local app with no vector search.

Always obtain connections via get_connection() — never call sqlite3.connect()
directly so that the connection configuration stays consistent.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def get_connection(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection with the project's standard config.

    - check_same_thread=False: required for FastAPI thread safety
    - row_factory=sqlite3.Row: rows support dict-like access
    - foreign_keys=ON: future-proofing for FK constraints

    Creates the parent directory if missing.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


SCHEMA_DDL = """
-- work_descriptions: the canonical WD entity, JSON-encoded
CREATE TABLE IF NOT EXISTS work_descriptions (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL DEFAULT '',
    data            TEXT NOT NULL,
    schema_version  INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL,
    last_modified   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_wd_created_at ON work_descriptions(created_at);

-- audit_log: per-step commit + advisor-modified + export events
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    wd_id       TEXT NOT NULL,
    event       TEXT NOT NULL,
    actor       TEXT NOT NULL,
    detail      TEXT,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_wd_id ON audit_log(wd_id);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_log(event);
"""


def create_schema(con: sqlite3.Connection) -> None:
    """Create the v2.0 schema (idempotent).

    Creates work_descriptions and audit_log tables plus their indexes.
    Safe to call multiple times — uses IF NOT EXISTS.
    """
    con.executescript(SCHEMA_DDL)
    con.commit()
