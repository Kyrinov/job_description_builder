"""
conftest.py — shared test fixtures for the v2.0 backend.

Provides:
- tmp_db_path: per-test fresh SQLite file under pytest tmp_path
- env_with_db: env vars wired so Settings picks up tmp_db_path
- test_app: FastAPI app instance bound to tmp_db_path
- client: httpx.AsyncClient bound to test_app via ASGITransport
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def tmp_db_path(tmp_path) -> str:
    """Per-test fresh SQLite file path."""
    return str(tmp_path / "test.db")


@pytest.fixture
def env_with_db(tmp_db_path, monkeypatch):
    """Set env vars so Settings picks up tmp_db_path + NOC pipeline vars."""
    import os
    parent = os.path.dirname(tmp_db_path) or "."
    monkeypatch.setenv("DB_PATH", tmp_db_path)
    monkeypatch.setenv("PROJECT_ROOT", parent)
    monkeypatch.setenv("NOC_DB_PATH", tmp_db_path)       # overridden by noc_mapping_db tests
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "gemma4:31b")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    return tmp_db_path


@pytest.fixture(autouse=True)
def _settings_env_defaults(tmp_path, monkeypatch):
    """Autouse: set minimum env vars so Settings() can be instantiated at module import.

    Required because v2 Settings (Phase 14) requires NOC_DB_PATH, OLLAMA_GENERATION_MODEL,
    and OLLAMA_EMBED_MODEL in addition to DB_PATH + PROJECT_ROOT. Any test that
    transitively imports app.ai.noc_ranking (which builds an instructor_client singleton
    at import time) needs these env vars present BEFORE the import. monkeypatch auto-
    restores the env on test teardown so values do not leak between tests.

    Tests that request env_with_db get the same values explicitly — monkeypatch
    re-setting to the same value is a no-op. Tests that depend on specific NOC pipeline
    values (test_stage2_calls_embed_model) can still monkeypatch.setenv to override.
    """
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("NOC_DB_PATH", str(tmp_path / "test_noc.db"))
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "gemma4:31b")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")


@pytest_asyncio.fixture
async def test_app(env_with_db):
    """FastAPI app with schema initialized against tmp DB.

    Imports app.main and explicitly creates the v2 schema (work_descriptions
    + audit_log) on the tmp DB. Required because httpx 0.27.2's ASGITransport
    does not trigger FastAPI lifespan events, so the schema created in
    app.main:lifespan is never applied to the per-test tmp DB. The other
    39 tests passed without schema creation because none of them touched
    work_descriptions or audit_log; test_wd.py is the first to require it.
    """
    pytest.importorskip("app.main")
    from app.config import get_settings
    from app.db import create_schema, get_connection
    from app.main import app  # noqa: F401

    settings = get_settings()
    con = get_connection(settings.db_path)
    create_schema(con)
    con.close()
    return app


@pytest_asyncio.fixture
async def client(test_app):
    """AsyncClient bound to test_app for in-process HTTP calls."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def noc_mapping_db(tmp_path) -> str:
    """Temp NOC DB with synthetic FTS5 + 768-dim vec rows. No Ollama required.

    Creates the NOC schema (noc_units, noc_elements, noc_fts FTS5, noc_chunks_vec FLOAT[768])
    separately from the v2 WD DB schema (work_descriptions, audit_log).
    Does NOT use get_noc_connection() — that factory is created in Plan 02.
    Manages sqlite-vec loading inline.

    Synthetic data: NOC 21232 "Software engineers and designers", TEER 1,
    Main duties element "Develop and maintain application software."
    """
    import sqlite3
    import sqlite_vec as sv

    db_path = str(tmp_path / "test_noc.db")
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.enable_load_extension(True)
    sv.load(con)
    con.enable_load_extension(False)

    con.executescript("""
        CREATE TABLE IF NOT EXISTS noc_units (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            noc_code    TEXT NOT NULL UNIQUE,
            teer_level  TEXT NOT NULL,
            title       TEXT NOT NULL,
            definition  TEXT NOT NULL DEFAULT '',
            source_hash TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS noc_elements (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            noc_code     TEXT NOT NULL,
            element_type TEXT NOT NULL,
            element_text TEXT NOT NULL,
            source_hash  TEXT NOT NULL DEFAULT ''
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS noc_fts USING fts5(
            noc_code UNINDEXED,
            title,
            definition,
            element_type UNINDEXED,
            element_text
        );
        CREATE TABLE IF NOT EXISTS index_metadata (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)

    # Drop and recreate vec table at FLOAT[768] (not FLOAT[1024] from v1 DDL)
    con.execute("DROP TABLE IF EXISTS noc_chunks_vec")
    con.executescript(
        "CREATE VIRTUAL TABLE noc_chunks_vec USING vec0("
        "rowid INTEGER PRIMARY KEY, embedding FLOAT[768] distance_metric=cosine)"
    )

    # Synthetic noc_units row
    con.execute(
        "INSERT OR IGNORE INTO noc_units(noc_code, teer_level, title, definition, source_hash) "
        "VALUES (?, ?, ?, ?, ?)",
        ("21232", "1", "Software engineers and designers",
         "Design, develop, and test software systems.", "fakehash_v1"),
    )
    # Synthetic noc_elements row
    con.execute(
        "INSERT OR IGNORE INTO noc_elements(noc_code, element_type, element_text, source_hash) "
        "VALUES (?, ?, ?, ?)",
        ("21232", "Main duties", "Develop and maintain application software.", "fakehash_v1"),
    )
    # Populate FTS5 from noc_units + noc_elements
    con.execute(
        "INSERT INTO noc_fts(noc_code, title, definition, element_type, element_text) "
        "SELECT noc_code, title, definition, '', '' FROM noc_units"
    )
    con.execute(
        "INSERT INTO noc_fts(noc_code, title, definition, element_type, element_text) "
        "SELECT e.noc_code, u.title, u.definition, e.element_type, e.element_text "
        "FROM noc_elements e JOIN noc_units u ON u.noc_code = e.noc_code"
    )
    # Insert fake 768-dim vector
    elem_row = con.execute(
        "SELECT id FROM noc_elements WHERE noc_code = '21232' LIMIT 1"
    ).fetchone()
    fake_vec = sv.serialize_float32([0.1] * 768)
    con.execute(
        "INSERT INTO noc_chunks_vec(rowid, embedding) VALUES (?, ?)",
        (elem_row["id"], fake_vec),
    )
    # index_metadata so the embed model assertion passes
    con.execute(
        "INSERT OR REPLACE INTO index_metadata(key, value, updated_at) "
        "VALUES (?, ?, datetime('now'))",
        ("embedding_model", "nomic-embed-text:latest"),
    )
    con.commit()
    con.close()
    return db_path
