"""
app/ai/jes_scoring.py — Instructor client singleton and Pydantic output models for JES scoring.

JESFactorRating is the structured output type for the per-factor scoring pipeline.
jes_instructor_client is the module-level singleton; construct once at import time,
never per-request.

Architecture non-negotiable: Do not construct jes_instructor_client inside route handlers
or service functions — it creates an httpx connection pool on every call.

Direct analog: app/ai/jd_ranking.py
"""
from __future__ import annotations

import sqlite3

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config import settings

# ---------------------------------------------------------------------------
# Pydantic output model
# ---------------------------------------------------------------------------


class JESFactorRating(BaseModel):
    """Structured LLM output for a single JES factor rating.

    The LLM returns only `degree` (e.g., "D3") and `rationale`.
    The service maps degree → points via json.loads(row["point_values"]).
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
# DB helper
# ---------------------------------------------------------------------------


def get_jes_version_info(conn: sqlite3.Connection, og_code: str) -> tuple[str, str]:
    """Return (version_label, content_hash) for the JES source document for the given OG.

    Uses LIKE f"{og_code}%" on source_documents.source_name — sufficient for all
    known OG prefixes (each 2–3 char prefix uniquely matches one JES source file).
    Fallback: ("JES v1.0", "") if no matching row found.
    """
    try:
        row = conn.execute(
            "SELECT version_label, content_hash FROM source_documents "
            "WHERE source_name LIKE ? LIMIT 1",
            (f"{og_code}%",),
        ).fetchone()
        if row:
            return row["version_label"], row["content_hash"]
    except Exception:
        pass
    return ("JES v1.0", "")


# ---------------------------------------------------------------------------
# Instructor client singleton
# ---------------------------------------------------------------------------
# Constructed once at module-level. settings must be imported before this block.
# Never reconstruct inside service functions or route handlers.

if settings.cloud_api_key:
    _openai_client = AsyncOpenAI(
        base_url=settings.cloud_base_url,
        api_key=settings.cloud_api_key,
    )
else:
    _openai_client = AsyncOpenAI(
        base_url=settings.ollama_base_url.rstrip("/") + "/v1",
        api_key="ollama",
    )

jes_instructor_client = instructor.from_openai(_openai_client, mode=instructor.Mode.JSON)
