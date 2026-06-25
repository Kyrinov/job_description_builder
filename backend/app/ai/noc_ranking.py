"""
app/ai/noc_ranking.py — Instructor client singleton and Pydantic output models.

Ported from v1.0 app/ai/noc_ranking.py. Key v2 adaptation:
- Uses make_instructor_client() factory that calls get_settings() at call time,
  not at import time. This allows test monkeypatching of env vars before Settings
  is instantiated.

Architecture non-negotiable: instructor_client is built once at module import time.
Do not construct per-request — it creates an httpx connection pool on every call.
"""
from __future__ import annotations

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, field_validator

from app.config import get_settings


class NOCCandidate(BaseModel):
    """A single ranked NOC unit group candidate returned by the pipeline."""

    noc_code: str = Field(
        ...,
        pattern=r"^\d{5}$",
        description="5-digit NOC 2021 unit group code, e.g. '21232'",
    )
    title: str = Field(..., description="NOC unit group title as it appears in noc_units.title")
    teer: int = Field(..., ge=0, le=5, description="TEER level 0-5 from noc_units (authoritative)")
    rank: int = Field(..., ge=1, le=10)
    matched_duties: list[str] = Field(
        ...,
        min_length=1,
        description=(
            "Verbatim duty statements copied from the provided NOC profile. "
            "Each entry must be an exact substring of the provided profile text."
        ),
    )
    justification: str = Field(
        ...,
        min_length=30,
        description="Why this unit group matches the work description",
    )

    @field_validator("noc_code")
    @classmethod
    def noc_code_all_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError(f"noc_code must be all digits, got: {v!r}")
        return v

    @field_validator("matched_duties")
    @classmethod
    def duties_not_blank(cls, v: list[str]) -> list[str]:
        if any(not s.strip() for s in v):
            raise ValueError("matched_duties must not contain blank strings")
        return v


class NOCRankingResult(BaseModel):
    """Structured output from Stage 3 — ranked list of NOC candidates."""

    candidates: list[NOCCandidate] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Ranked list of NOC candidates, best match first (rank=1)",
    )

    @field_validator("candidates")
    @classmethod
    def ranks_are_sequential(cls, v: list[NOCCandidate]) -> list[NOCCandidate]:
        ranks = sorted(c.rank for c in v)
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError(
                f"candidate ranks must be 1..N with no gaps or duplicates, got: {ranks}"
            )
        return v


def make_instructor_client() -> instructor.Instructor:
    """Build instructor client from current settings.

    Called once at module import time to create the module-level singleton.
    Using a factory (vs. module-level code) allows test monkeypatching of
    env vars before Settings is instantiated (v2 lazy get_settings() pattern).
    """
    settings = get_settings()
    if settings.cloud_api_key:
        _client = AsyncOpenAI(
            base_url=settings.cloud_base_url,
            api_key=settings.cloud_api_key,
        )
    else:
        _client = AsyncOpenAI(
            base_url=settings.ollama_base_url.rstrip("/") + "/v1",
            api_key="ollama",  # placeholder; Ollama does not validate this
        )
    return instructor.from_openai(_client, mode=instructor.Mode.JSON)


# Module-level singleton — built once at import time.
# Tests that need to control the client mock app.services.noc_mapper.instructor_client directly.
instructor_client = make_instructor_client()
