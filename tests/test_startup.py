"""Integration tests for lifespan startup failure paths (DATA-03)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _set_valid_env(monkeypatch, temp_db_path, tmp_path):
    """Set all required env vars for a valid Settings instantiation."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "gemma4:31b")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    monkeypatch.setenv("DB_PATH", temp_db_path)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))


def _clear_app_modules():
    """Remove all app modules from sys.modules for a clean import."""
    import sys
    for key in list(sys.modules.keys()):
        if key.startswith("app."):
            del sys.modules[key]


@pytest.mark.asyncio
async def test_startup_fails_ollama_unreachable(monkeypatch, temp_db_path, tmp_path):
    """App lifespan must raise RuntimeError if Ollama is not reachable."""
    _set_valid_env(monkeypatch, temp_db_path, tmp_path)
    _clear_app_modules()

    # Patch ollama.AsyncClient globally (affects both lifespan and /health endpoint)
    mock_client = MagicMock()
    mock_client.list = AsyncMock(side_effect=Exception("Connection refused"))
    with patch("ollama.AsyncClient", return_value=mock_client):
        import app.main as main_module
        monkeypatch.setattr(main_module, "ollama_client_factory", lambda: mock_client)
        from app.main import lifespan, app
        with pytest.raises(RuntimeError, match="Ollama is not reachable"):
            async with lifespan(app):
                pass


@pytest.mark.asyncio
async def test_startup_fails_missing_model(monkeypatch, temp_db_path, tmp_path):
    """App lifespan must raise RuntimeError if a required model is absent."""
    _set_valid_env(monkeypatch, temp_db_path, tmp_path)
    _clear_app_modules()

    mock_client = MagicMock()
    gen_entry = MagicMock()
    gen_entry.model = "gemma4:31b"
    response = MagicMock()
    response.models = [gen_entry]  # nomic-embed-text:latest is absent
    mock_client.list = AsyncMock(return_value=response)

    with patch("ollama.AsyncClient", return_value=mock_client):
        import app.main as main_module
        monkeypatch.setattr(main_module, "ollama_client_factory", lambda: mock_client)
        from app.main import lifespan, app
        with pytest.raises(RuntimeError, match="Required Ollama models are not present"):
            async with lifespan(app):
                pass


@pytest.mark.asyncio
async def test_startup_error_names_missing_model(monkeypatch, temp_db_path, tmp_path):
    """RuntimeError message must name the missing model."""
    _set_valid_env(monkeypatch, temp_db_path, tmp_path)
    _clear_app_modules()

    mock_client = MagicMock()
    response = MagicMock()
    response.models = []  # All models missing
    mock_client.list = AsyncMock(return_value=response)

    with patch("ollama.AsyncClient", return_value=mock_client):
        import app.main as main_module
        monkeypatch.setattr(main_module, "ollama_client_factory", lambda: mock_client)
        from app.main import lifespan, app
        with pytest.raises(RuntimeError) as exc_info:
            async with lifespan(app):
                pass
        error_msg = str(exc_info.value)
        assert "gemma4:31b" in error_msg or "nomic-embed-text:latest" in error_msg
