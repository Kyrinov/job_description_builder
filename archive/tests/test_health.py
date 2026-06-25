"""Smoke tests for GET /health endpoint (DATA-03)."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch


def _make_mock_client(available=None):
    """Create a mock ollama.AsyncClient with optional available models."""
    if available is None:
        available = ["gemma4:31b", "nomic-embed-text:latest"]
    mock = MagicMock()
    entries = [getattr(MagicMock(), "model", model) for model in available]
    model_objs = [MagicMock() for _ in available]
    for obj, model in zip(model_objs, available):
        obj.model = model
    response = MagicMock()
    response.models = model_objs
    mock.list = AsyncMock(return_value=response)
    return mock


@pytest.mark.asyncio
async def test_health_endpoint_200(monkeypatch, temp_db_path, tmp_path):
    """GET /health must return 200 when app starts cleanly."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "gemma4:31b")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    monkeypatch.setenv("DB_PATH", str(temp_db_path))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))

    mock_client = _make_mock_client()
    with patch("ollama.AsyncClient", return_value=mock_client):
        import app.main as main_module
        monkeypatch.setattr(main_module, "ollama_client_factory", lambda: mock_client)
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_has_status_key(monkeypatch, temp_db_path, tmp_path):
    """GET /health response body must contain a 'status' key."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "gemma4:31b")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    monkeypatch.setenv("DB_PATH", str(temp_db_path))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))

    mock_client = _make_mock_client()
    with patch("ollama.AsyncClient", return_value=mock_client):
        import app.main as main_module
        monkeypatch.setattr(main_module, "ollama_client_factory", lambda: mock_client)
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            body = response.json()
            assert "status" in body


@pytest.mark.asyncio
async def test_health_response_has_model_keys(monkeypatch, temp_db_path, tmp_path):
    """GET /health must include required_models and missing_models keys."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "gemma4:31b")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    monkeypatch.setenv("DB_PATH", str(temp_db_path))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))

    mock_client = _make_mock_client()
    with patch("ollama.AsyncClient", return_value=mock_client):
        import app.main as main_module
        monkeypatch.setattr(main_module, "ollama_client_factory", lambda: mock_client)
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            body = response.json()
            assert "required_models" in body
            assert "missing_models" in body
