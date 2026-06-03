"""
app/config.py — pydantic-settings configuration.

Reads DB_PATH and PROJECT_ROOT from env (or .env file). Required fields
have no default — instantiation raises ValidationError with the field name
when missing.
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """v2.0 backend configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    db_path: str = Field(..., min_length=1)  # Required — no default; rejects empty string
    project_root: str = Field(..., min_length=1)  # Required — no default; rejects empty string


# Singleton accessor — use this everywhere instead of instantiating Settings() directly
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the cached Settings singleton (instantiates on first call)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
