"""
app/ai/jes_scoring.py — Instructor client singleton and Pydantic output models for JES scoring.

Ported from v1.0 app/ai/jes_scoring.py with v2 adaptations:
- Version label is hardcoded ("EC JES 2017") — v2.0 has no source_documents table
- Singleton constructed at module import time via the same factory pattern as
  app/ai/noc_ranking.py (uses get_settings() at import time, not via property).

Architecture non-negiable: Do not construct jes_instructor_client inside route handlers
or service functions — it creates an httpx connection pool on every call.
"""
from __future__ import annotations

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config import get_settings


# ---------------------------------------------------------------------------
# Pydantic output model
# ---------------------------------------------------------------------------


class JESFactorRating(BaseModel):
    """Structured LLM output for a single JES factor rating.

    The LLM returns only `degree` (e.g., "D3") and `rationale`.
    The service maps degree → points via the element["pts"] dict from EC_JES_ELEMENTS.
    This prevents the LLM from hallucinating point values.
    """

    degree: str = Field(
        description=(
            "Degree identifier — must be from the provided degree list, e.g. 'D1', 'D3'"
        )
    )
    rationale: str = Field(
        description="Justification for the selected degree, citing the position's duties"
    )


# ---------------------------------------------------------------------------
# Prompt constants
# ---------------------------------------------------------------------------

JES_SCORING_SYSTEM_PROMPT = """
You are a Government of Canada HR classification specialist.
You are scoring a position against the Job Evaluation Standard (JES) for the {og_name} ({og_code}) group.

CRITICAL RULES:
- Select the degree identifier EXACTLY as shown in the degree list provided — e.g. "D1", "D3"
- Your degree selection must be justified by specific duties listed in the position description
- Do NOT invent degree identifiers; only use identifiers from the provided degree list
- Return only the degree identifier string and a rationale — do not compute points
""".strip()


# ---------------------------------------------------------------------------
# Instructor client singleton
# ---------------------------------------------------------------------------
# Constructed once at module-level. settings must be imported before this block.
# Never reconstruct inside service functions or route handlers.


def make_jes_instructor_client() -> instructor.Instructor:
    """Build instructor client from current settings.

    Called once at module import time to create the module-level singleton.
    Mirrors the factory pattern in app/ai/noc_ranking.py.
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
# Tests that need to control the client mock app.services.jes_service.jes_instructor_client directly.
jes_instructor_client = make_jes_instructor_client()
