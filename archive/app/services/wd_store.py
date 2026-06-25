"""
app/services/wd_store.py — WorkDescription CRUD helpers for SQLite persistence.

These are synchronous helpers called inside asyncio.to_thread() at the service layer.
They do NOT open connections — callers pass an open sqlite3.Connection.

Schema:
    work_descriptions(id TEXT PK, session_id TEXT, stage TEXT, data JSON, created_at TEXT, last_modified TEXT)
"""
from __future__ import annotations

import sqlite3
from datetime import datetime

from app.models.work_description import WorkDescription


def save_work_description(conn: sqlite3.Connection, wd: WorkDescription) -> None:
    """Upsert a WorkDescription to the work_descriptions table."""
    now = datetime.utcnow().isoformat()
    conn.execute(
        """INSERT OR REPLACE INTO work_descriptions(id, session_id, stage, data, created_at, last_modified)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(wd.id), wd.session_id, wd.stage, wd.model_dump_json(), now, now),
    )
    conn.commit()


def load_work_description(conn: sqlite3.Connection, wd_id: str) -> WorkDescription | None:
    """Load a WorkDescription by ID. Returns None if not found."""
    row = conn.execute(
        "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
    ).fetchone()
    if row is None:
        return None
    return WorkDescription.model_validate_json(row["data"])
