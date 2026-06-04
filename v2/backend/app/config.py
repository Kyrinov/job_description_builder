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

    # NOC pipeline
    noc_db_path: str = Field(
        ...,
        min_length=1,
        description="Path to v1.0 NOC SQLite DB (app.db) — contains noc_units, noc_elements, noc_fts, noc_chunks_vec",
    )

    # Ollama (local LLM + embed)
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_generation_model: str = Field(..., description="e.g. gemma4:31b")
    ollama_embed_model: str = Field(..., description="e.g. nomic-embed-text:latest")

    # Cloud LLM fallback (optional — if set, generation routes to cloud instead of Ollama)
    cloud_api_key: str | None = Field(default=None)
    cloud_model: str = Field(default="MiniMax-M3")
    cloud_base_url: str = Field(default="https://api.minimax.io/v1")

    @property
    def generation_model(self) -> str:
        """Return cloud_model if cloud_api_key is set, else ollama_generation_model."""
        return self.cloud_model if self.cloud_api_key else self.ollama_generation_model


# Singleton accessor — use this everywhere instead of instantiating Settings() directly
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the cached Settings singleton (instantiates on first call)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
