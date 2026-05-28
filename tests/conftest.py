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
    for name in ("gemma4:31b", "nomic-embed-text:latest"):
        entry = MagicMock()
        entry.model = name
        mock.list = AsyncMock(return_value=MagicMock(models=[entry]))
    return mock
