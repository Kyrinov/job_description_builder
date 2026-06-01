"""
app/ai/noc_ranking.py — Instructor client singleton and Pydantic output models for NOC ranking.

NOCCandidate and NOCRankingResult are the structured output types for Stage 3 of the
NL→NOC pipeline. instructor_client is the module-level singleton; construct once at
import time, never per-request.

Architecture non-negotiable: Do not construct instructor_client inside route handlers
or service functions — it creates an httpx connection pool on every call.
"""
from __future__ import annotations

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, field_validator

from app.config import settings


class NOCCandidate(BaseModel):
    """A single ranked NOC unit group candidate returned by the pipeline."""

    noc_code: str = Field(
        ...,
        pattern=r"^\d{5}$",
        description="5-digit NOC 2021 unit group code, e.g. '21232'",
    )
    title: str = Field(..., description="NOC unit group title as it appears in noc_units.title")
    teer: int = Field(..., ge=0, le=5, description="TEER level 0–5 from noc_units (authoritative)")
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


# Module-level singleton — built once at import time, reused for the application lifetime.
# Mode.JSON is required for Ollama; Mode.TOOLS silently fails on most Ollama models.
# Do NOT construct per-request (creates and tears down httpx connection pool on every call).
instructor_client = instructor.from_openai(
    AsyncOpenAI(
        base_url=settings.ollama_base_url.rstrip("/") + "/v1",
        api_key="ollama",  # placeholder; Ollama does not validate this
    ),
    mode=instructor.Mode.JSON,
)
