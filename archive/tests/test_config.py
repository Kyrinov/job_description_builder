"""Tests for env var validation via pydantic-settings Settings class (DATA-02)."""
from pathlib import Path

import pytest
import pydantic


def test_missing_required_var_raises(monkeypatch, temp_db_path, tmp_path):
    """Missing OLLAMA_GENERATION_MODEL must raise ValidationError at import time."""
    import sys
    for key in list(sys.modules.keys()):
        if "app.config" in key:
            del sys.modules[key]
    monkeypatch.chdir(tmp_path)
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
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OLLAMA_EMBED_MODEL", raising=False)
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "gemma4:31b")
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
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "gemma4:31b")
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
    assert s.ollama_generation_model == "gemma4:31b"
    assert s.ollama_embed_model == "nomic-embed-text:latest"
    assert "localhost" in s.ollama_base_url


def test_settings_loads_from_dotenv(monkeypatch, tmp_path):
    """Settings must read .env so uvicorn startup works without shell-exported variables."""
    import sys
    for key in list(sys.modules.keys()):
        if "app.config" in key:
            del sys.modules[key]

    for env_name in [
        "OLLAMA_BASE_URL",
        "OLLAMA_GENERATION_MODEL",
        "OLLAMA_EMBED_MODEL",
        "DB_PATH",
        "DATA_DIR",
    ]:
        monkeypatch.delenv(env_name, raising=False)

    project_root = Path(__file__).resolve().parents[1]
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "\n".join(
            [
                "OLLAMA_BASE_URL=http://localhost:11434",
                "OLLAMA_GENERATION_MODEL=gemma4:31b",
                "OLLAMA_EMBED_MODEL=nomic-embed-text:latest",
                f"DB_PATH={project_root / 'dotenv-test.db'}",
                f"DATA_DIR={project_root / 'data'}",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    from app.config import Settings

    s = Settings()
    assert s.ollama_generation_model == "gemma4:31b"
