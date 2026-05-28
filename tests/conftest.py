"""Shared pytest fixtures for Phase 1 tests."""
import os
import tempfile
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def temp_db_path(tmp_path):
    """Temporary SQLite database file path for isolation."""
    return str(tmp_path / "test_app.db")


@pytest.fixture
def valid_env(monkeypatch, temp_db_path, tmp_path):
    """Set all required env vars for a valid Settings instantiation."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "qwen3.6:latest")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    monkeypatch.setenv("DB_PATH", temp_db_path)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))


@pytest.fixture
def mock_ollama_client():
    """Mock ollama.AsyncClient that simulates healthy Ollama with required models."""
    mock = MagicMock()
    model_entry = MagicMock()
    model_entry.model = "qwen3.6:latest"
    embed_entry = MagicMock()
    embed_entry.model = "nomic-embed-text:latest"
    response = MagicMock()
    response.models = [model_entry, embed_entry]
    mock.list = AsyncMock(return_value=response)
    return mock


@pytest_asyncio.fixture
async def test_app(valid_env, mock_ollama_client, temp_db_path, monkeypatch):
    """FastAPI test application with mocked Ollama and temp database."""
    import app.main as main_module
    monkeypatch.setattr("app.main.ollama_client_factory", lambda: mock_ollama_client)
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
