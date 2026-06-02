"""
app/config.py — Runtime configuration via pydantic-settings.

All required fields use Field(...) — missing vars raise ValidationError
at import time with the field name in the error message (DATA-02).
"""
from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root is two directories above this file:
# app/config.py → app/ → project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Ollama — default for base URL; generation/embed models are required
    ollama_base_url: str = "http://localhost:11434"
    ollama_generation_model: str = Field(
        ..., description="Ollama generation model name with tag, e.g. gemma4:31b"
    )
    ollama_embed_model: str = Field(
        ..., description="Ollama embedding model name with tag, e.g. nomic-embed-text:latest"
    )

    # Cloud generation API — optional; when set, Stage 3 uses this instead of local Ollama
    # Works with any OpenAI-compatible provider (DashScope, OpenRouter, etc.)
    cloud_api_key: str | None = Field(
        default=None,
        description="Cloud provider API key — Stage 3 switches to cloud when this is set",
    )
    cloud_model: str = "qwen3-7b"
    cloud_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    @property
    def generation_model(self) -> str:
        """Active generation model name — cloud model if configured, else local Ollama."""
        return self.cloud_model if self.cloud_api_key else self.ollama_generation_model

    # Database — required; validated against project root (T-1-01)
    db_path: str = Field(
        ..., description="Absolute path to SQLite database file — must be under project root"
    )

    # Data directory — required
    data_dir: str = Field(
        ..., description="Absolute path to data/ directory containing source files"
    )

    # ------------------------------------------------------------------ #
    # Validators                                                            #
    # ------------------------------------------------------------------ #

    @field_validator("ollama_base_url")
    @classmethod
    def ollama_url_must_be_localhost(cls, v: str) -> str:
        """Security T-1-02: Ollama must be on localhost — no external hosts."""
        allowed_prefixes = ("http://localhost", "http://127.0.0.1")
        if not any(v.startswith(prefix) for prefix in allowed_prefixes):
            raise ValueError(
                f"ollama_base_url must point to localhost "
                f"(got: {v!r}). External Ollama hosts are not permitted."
            )
        return v

    @field_validator("db_path")
    @classmethod
    def db_path_must_be_under_project_root(cls, v: str) -> str:
        """Security T-1-01: Prevent path traversal — db_path must be under PROJECT_ROOT,
        except when running under pytest (temp directories used for test isolation).
        """
        resolved = Path(v).resolve()
        # Accept paths under project root
        try:
            resolved.relative_to(PROJECT_ROOT)
            return str(resolved)
        except ValueError:
            pass
        # Outside project root: only allow pytest's own temp directories during tests.
        if "PYTEST_CURRENT_TEST" in os.environ and any("pytest" in part for part in resolved.parts):
            return str(resolved)
        raise ValueError(
            f"db_path must be under the project root ({PROJECT_ROOT}). "
            f"Got: {resolved!r}. Path traversal is not permitted."
        )


# Module-level singleton — raises ValidationError immediately if env vars are missing.
# This ensures startup fails before Uvicorn begins accepting connections (DATA-02).
settings = Settings()
