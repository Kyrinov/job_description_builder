"""Shared pytest fixtures for Phase 1 tests."""
import sys

import pytest


def _clear_app_modules():
    """Remove all app modules from sys.modules for a clean import."""
    for key in list(sys.modules.keys()):
        if key.startswith("app."):
            del sys.modules[key]


def _set_valid_env(monkeypatch, temp_db_path, tmp_path):
    """Helper to set all required env vars for a valid Settings instantiation."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "gemma4:31b")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    monkeypatch.setenv("DB_PATH", temp_db_path)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))


@pytest.fixture(autouse=True)
def _clean_module_state():
    """Clear app modules between tests to prevent cross-test contamination."""
    yield  # no-op


@pytest.fixture
def temp_db_path(tmp_path):
    """Temporary SQLite database file path for isolation."""
    return str(tmp_path / "test_app.db")


@pytest.fixture
def valid_env(monkeypatch, temp_db_path, tmp_path):
    """Set all required env vars for a valid Settings instantiation."""
    _set_valid_env(monkeypatch, temp_db_path, tmp_path)


@pytest.fixture
def mock_healthy_ollama():
    """Mock AsyncClient that simulates healthy Ollama with both required models."""
    from unittest.mock import AsyncMock, MagicMock

    mock = MagicMock()
    entries = []
    for name in ("gemma4:31b", "nomic-embed-text:latest"):
        entry = MagicMock()
        entry.model = name
        entries.append(entry)
    mock.list = AsyncMock(return_value=MagicMock(models=entries))
    return mock


@pytest.fixture
def noc_db(tmp_path):
    """
    Temp-file SQLite connection with NOC schema and sqlite_vec loaded.
    Used by test_noc_ingest.py tests — does NOT require Ollama to be running.
    """
    from app.db import get_connection, create_schema
    db_path = str(tmp_path / "test_noc.db")
    con = get_connection(db_path)
    create_schema(con)
    yield con
    con.close()


@pytest.fixture
def ca_jes_db(tmp_path):
    """
    Temp-file SQLite connection with full schema (NOC + CA/JES) and sqlite_vec loaded.
    Used by test_ca_ingest.py, test_jes_ingest.py, test_policy_ingest.py.
    Does NOT require Ollama to be running.

    Note: uses a different db_path ('test_ca_jes.db') than the noc_db fixture
    to avoid sharing state across test modules.
    """
    from app.db import get_connection, create_schema

    db_path = str(tmp_path / "test_ca_jes.db")
    con = get_connection(db_path)
    create_schema(con)  # creates all tables — NOC + CA_JES once Plan 03-02 lands
    yield con
    con.close()


@pytest.fixture
def noc_mapping_db(tmp_path):
    """
    Temp SQLite DB with NOC schema, synthetic FTS5 data, and 768-dim fake vec rows.
    Used by test_noc_mapping.py integration tests — does NOT require Ollama to be running.

    Synthetic data: NOC 21232 "Software engineers and designers", TEER 2,
    one Main duties element. FTS5 and vec populated. index_metadata set to
    nomic-embed-text:latest so assert_noc_index_model() passes.
    """
    import sqlite_vec as sv
    from app.db import create_schema, get_connection

    db_path = str(tmp_path / "test_noc_mapping.db")
    con = get_connection(db_path)
    create_schema(con)

    # Insert synthetic noc_units row
    con.execute(
        "INSERT OR IGNORE INTO noc_units(noc_code, teer_level, title, definition, source_hash) "
        "VALUES (?, ?, ?, ?, ?)",
        ("21232", "2", "Software engineers and designers",
         "Design, develop, and test software systems.", "fakehash_v1"),
    )
    # Insert synthetic noc_elements (Main duties)
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
    # Drop old vec table (may be FLOAT[1024] from Phase 2 ingest), recreate as FLOAT[768]
    con.execute("DROP TABLE IF EXISTS noc_chunks_vec")
    con.executescript(
        "CREATE VIRTUAL TABLE noc_chunks_vec USING vec0("
        "rowid INTEGER PRIMARY KEY, embedding FLOAT[768] distance_metric=cosine)"
    )
    # Insert fake 768-dim vector for the element row
    elem_row = con.execute(
        "SELECT id FROM noc_elements WHERE noc_code = '21232' LIMIT 1"
    ).fetchone()
    fake_vec = sv.serialize_float32([0.1] * 768)
    con.execute(
        "INSERT INTO noc_chunks_vec(rowid, embedding) VALUES (?, ?)",
        (elem_row["id"], fake_vec),
    )
    # Update index_metadata so assert_noc_index_model() passes during tests
    con.execute(
        "INSERT OR REPLACE INTO index_metadata(key, value, updated_at) "
        "VALUES (?, ?, datetime('now'))",
        ("embedding_model", "nomic-embed-text:latest"),
    )
    con.commit()

    yield db_path
    con.close()


@pytest.fixture
def og_db(tmp_path):
    """
    Temp SQLite DB with full schema + synthetic og_definitions rows for AS, EC, IT, PE.
    Used by test_og_classification.py and test_og_ranking.py.
    Does NOT require Ollama to be running.
    """
    from app.db import create_schema, get_connection

    db_path = str(tmp_path / "test_og.db")
    con = get_connection(db_path)
    create_schema(con)  # creates og_definitions table

    for row in [
        (
            "EC", "Economics and Social Science Services", "PA",
            "Positions primarily involved in economic and social research and related activities.",
            "the planning, development, delivery or management of policies, programs, services or other activities in the social sciences directed toward Canadians",
            "the planning, development, delivery or management of policies, programs, services or other activities directed to the public or to the Public Service",
        ),
        (
            "AS", "Administrative Services", "PA",
            "Positions primarily involved in administrative services work.",
            "the planning, development, delivery or management of government policies, programs, services or other activities directed to the Public Service",
            None,
        ),
        (
            "IT", "Information Technology", None,
            "Positions primarily involved in IT systems development and operation.",
            None,
            None,
        ),
        (
            "PE", "Personnel Administration", "PA",
            "Positions primarily involved in HR policy and classification work.",
            None,
            None,
        ),
    ]:
        con.execute(
            "INSERT OR IGNORE INTO og_definitions "
            "(og_code, og_name, parent_group, definition, inclusions, exclusions, source_file, source_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (*row, "TBS-OCHRO-OG.txt", "testhash_v1"),
        )
    con.commit()

    yield db_path
    con.close()
