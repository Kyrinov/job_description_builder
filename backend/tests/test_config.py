"""
test_config.py — contract for pydantic-settings Settings.

Wave 0 stub: fails because app.config does not exist.
Plan 02 implements Settings and these tests must pass after that plan.
"""
import pytest


def test_settings_loads_defaults(env_with_db):
    """Settings must load DB_PATH from env and validate it is a non-empty string."""
    from app.config import Settings  # Wave 0: ImportError
    s = Settings()
    assert s.db_path
    assert s.db_path.endswith(".db")


def test_missing_db_path_raises(monkeypatch):
    """Settings must raise ValidationError when DB_PATH is empty (or unset and no default)."""
    monkeypatch.delenv("DB_PATH", raising=False)
    monkeypatch.setenv("PROJECT_ROOT", "/tmp")
    from app.config import Settings
    with pytest.raises(Exception):  # pydantic.ValidationError
        Settings(_env_file=None, db_path="")  # explicit empty
