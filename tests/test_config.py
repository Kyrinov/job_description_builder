"""Tests for env var validation via pydantic-settings Settings class (DATA-02)."""
import pytest
import pydantic


def test_missing_required_var_raises(monkeypatch, temp_db_path, tmp_path):
    """Missing OLLAMA_GENERATION_MODEL must raise ValidationError at import time."""
    import importlib, sys
    for key in list(sys.modules.keys()):
        if "app.config" in key:
            del sys.modules[key]
    monkeypatch.delenv("OLLAMA_GENERATION_MODEL", raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    monkeypatch.setenv("DB_PATH", temp_db_path)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    with pytest.raises(pydantic.ValidationError):
        from app.config import Settings
        Settings()


def test_missing_var_error_names_field(monkeypatch, temp_db_path, tmp_path):
    """ValidationError must name the missing field in its error message."""
    import sys
    for key in list(sys.modules.keys()):
        if "app.config" in key:
            del sys.modules[key]
    monkeypatch.delenv("OLLAMA_EMBED_MODEL", raising=False)
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "qwen3.6:latest")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("DB_PATH", temp_db_path)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    with pytest.raises(pydantic.ValidationError) as exc_info:
        from app.config import Settings
        Settings()
    assert "ollama_embed_model" in str(exc_info.value).lower()


def test_db_path_traversal_rejected(monkeypatch, tmp_path):
    """db_path set to /tmp (outside project dir) must raise ValidationError."""
    import sys
    for key in list(sys.modules.keys()):
        if "app.config" in key:
            del sys.modules[key]
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "qwen3.6:latest")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    monkeypatch.setenv("DB_PATH", "/tmp/evil.db")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    with pytest.raises(pydantic.ValidationError) as exc_info:
        from app.config import Settings
        Settings()
    assert "db_path" in str(exc_info.value).lower()


def test_valid_settings_load(valid_env):
    """With all required env vars set, Settings loads without error."""
    import sys
    for key in list(sys.modules.keys()):
        if "app.config" in key:
            del sys.modules[key]
    from app.config import Settings
    s = Settings()
    assert s.ollama_generation_model == "qwen3.6:latest"
    assert s.ollama_embed_model == "nomic-embed-text:latest"
    assert "localhost" in s.ollama_base_url
