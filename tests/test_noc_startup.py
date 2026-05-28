"""
Tests for assert_noc_index_model startup assertion (PIPE-05).

Pattern: same as tests/test_startup.py — async lifespan, RuntimeError, monkeypatch.
asyncio_mode = "auto" is set in pyproject.toml — @pytest.mark.asyncio not required.
"""
from __future__ import annotations

import sys

import pytest


def _set_valid_env(monkeypatch, temp_db_path, tmp_path):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "gemma4:31b")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    monkeypatch.setenv("DB_PATH", temp_db_path)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))


def _clear_app_modules():
    for key in list(sys.modules.keys()):
        if key.startswith("app."):
            del sys.modules[key]


# --------------------------------------------------------------
# PIPE-05: Mismatch raises RuntimeError
# --------------------------------------------------------------

def test_model_mismatch_raises_runtime_error(monkeypatch, temp_db_path, tmp_path):
    """assert_noc_index_model must raise RuntimeError on embedding model mismatch (PIPE-05)."""
    _set_valid_env(monkeypatch, temp_db_path, tmp_path)
    _clear_app_modules()

    from app.db import get_connection, create_schema, assert_noc_index_model

    con = get_connection(temp_db_path)
    create_schema(con)
    # Write a mismatched model name into index_metadata
    con.execute(
        "INSERT INTO index_metadata(key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ["embedding_model", "some-other-model:latest"],
    )
    con.commit()

    with pytest.raises(RuntimeError, match="NOC vector index was built with"):
        assert_noc_index_model(con, "nomic-embed-text:latest")

    con.close()


# --------------------------------------------------------------
# PIPE-05: Error message names both model values
# --------------------------------------------------------------

def test_model_mismatch_error_names_both_models(monkeypatch, temp_db_path, tmp_path):
    """RuntimeError message must name both the stored model and the configured model (PIPE-05)."""
    _set_valid_env(monkeypatch, temp_db_path, tmp_path)
    _clear_app_modules()

    from app.db import get_connection, create_schema, assert_noc_index_model

    con = get_connection(temp_db_path)
    create_schema(con)
    con.execute(
        "INSERT INTO index_metadata(key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ["embedding_model", "wrong-model:v1"],
    )
    con.commit()

    with pytest.raises(RuntimeError) as exc_info:
        assert_noc_index_model(con, "nomic-embed-text:latest")

    msg = str(exc_info.value)
    assert "wrong-model:v1" in msg, f"Error message must name stored model; got: {msg}"
    assert "nomic-embed-text" in msg, f"Error message must name configured model; got: {msg}"
    assert "ingest_noc.py" in msg, f"Error message must include remediation command; got: {msg}"

    con.close()


# --------------------------------------------------------------
# PIPE-05: No index_metadata row — fresh install must NOT raise
# --------------------------------------------------------------

def test_missing_index_metadata_no_error(monkeypatch, temp_db_path, tmp_path):
    """assert_noc_index_model must not raise when no embedding_model row exists (PIPE-05)."""
    _set_valid_env(monkeypatch, temp_db_path, tmp_path)
    _clear_app_modules()

    from app.db import get_connection, create_schema, assert_noc_index_model

    con = get_connection(temp_db_path)
    create_schema(con)
    # No INSERT — simulates fresh install where ingest has never run
    assert_noc_index_model(con, "nomic-embed-text:latest")  # must not raise

    con.close()


# --------------------------------------------------------------
# PIPE-05: Model name normalization — nomic-embed-text (no tag) matches nomic-embed-text:latest
# --------------------------------------------------------------

def test_model_name_normalization_no_false_positive(monkeypatch, temp_db_path, tmp_path):
    """
    assert_noc_index_model must not raise when stored model is 'nomic-embed-text' (no tag)
    and configured model is 'nomic-embed-text:latest' — they are the same after normalization.
    """
    _set_valid_env(monkeypatch, temp_db_path, tmp_path)
    _clear_app_modules()

    from app.db import get_connection, create_schema, assert_noc_index_model

    con = get_connection(temp_db_path)
    create_schema(con)
    con.execute(
        "INSERT INTO index_metadata(key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ["embedding_model", "nomic-embed-text"],  # stored without :latest tag
    )
    con.commit()

    # Must NOT raise — both normalize to nomic-embed-text:latest
    assert_noc_index_model(con, "nomic-embed-text:latest")

    con.close()
