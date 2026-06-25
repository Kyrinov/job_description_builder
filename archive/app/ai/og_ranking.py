"""
app/ai/og_ranking.py — Instructor client singleton and Pydantic output models for OG ranking.

OGCandidate, OGRankingResult, and PolicyAdjacencyResult are the structured output
types for the OG classification pipeline. og_instructor_client is the module-level
singleton; construct once at import time, never per-request.

Architecture non-negotiable: Do not construct og_instructor_client inside route handlers
or service functions — it creates an httpx connection pool on every call.
"""
from __future__ import annotations

from typing import Any

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config import settings


class OGCandidate(BaseModel):
    """One ranked OG candidate returned by the LLM."""

    og_code: str = Field(description="OG code — must be from the provided list only")
    rank: int = Field(ge=1, le=3, description="Rank 1 = highest confidence")
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(description="Why this OG matches the confirmed NOC and work description")
    evidence_quotes: list[str] = Field(
        default_factory=list,
        description="Verbatim text excerpts from provided OG definition — no paraphrases",
    )


class OGRankingResult(BaseModel):
    """Top-3 OG candidates from a single LLM call."""

    candidates: list[OGCandidate] = Field(min_length=1, max_length=3)


class PolicyAdjacencyResult(BaseModel):
    """instructor output for Step 2 policy-adjacent detection."""

    is_policy_adjacent: bool = Field(
        description="True if work description contains policy development/research duties"
    )
    confidence: float = Field(ge=0.0, le=1.0)
    policy_phrases: list[str] = Field(
        default_factory=list,
        description="Verbatim phrases from work description that indicate policy work",
    )
    rationale: str


OG_LEVELS: dict[str, list[int]] = {
    "AS": list(range(1, 9)),
    "CR": list(range(1, 8)),
    "PM": list(range(1, 8)),
    "EC": list(range(1, 9)),
    "IT": list(range(1, 6)),
    "EX": list(range(1, 6)),
    "GT": list(range(1, 9)),
}


SYSTEM_PROMPT = """
You are a Government of Canada HR classification specialist.
Given a confirmed NOC code + unit group profile and a work description,
identify the top 3 most likely occupational groups (OGs) from the list provided.

CRITICAL RULES:
- You may ONLY select OG codes from the provided list — never invent codes
- evidence_quotes must be exact verbatim excerpts from the provided OG definition text,
  not paraphrases
- Return exactly 3 candidates (or fewer if fewer than 3 OGs are plausible), ranked by confidence descending
- confidence must reflect how well the OG definition matches the confirmed NOC and work description
""".strip()


POLICY_DETECTION_PROMPT = """
Determine if the following work description contains duties that are primarily
policy-development, research, or analysis work directed at the Canadian public
(external stakeholders) as opposed to internal administrative support to the
Public Service.

Policy-adjacent signals: "develop policy", "provide policy advice", "policy analysis",
"research and analysis", "socio-economic", "program evaluation", "economic research",
"evidence-based recommendations", "policy framework", "policy proposals".

Internal administrative signals: "process transactions", "provide administrative support",
"administer programs", "coordinate activities", "manage HR operations".

Work description:
{work_description}
""".strip()


def build_og_context(og_rows: list, confirmed_noc_code: str, work_description: str) -> str:
    """
    Assemble a single prompt string containing:
    - Confirmed NOC code
    - Work description (truncated at 500 chars to conserve tokens)
    - All OG definitions with inclusions and exclusions

    og_rows: list of sqlite3.Row or tuple with (og_code, og_name, definition, inclusions, exclusions)
    """
    lines = [
        f"Confirmed NOC: {confirmed_noc_code}",
        f"\nWork Description: {work_description[:500]}",
        "\n--- Occupational Group Definitions ---",
    ]
    for row in og_rows:
        if hasattr(row, "keys"):
            og_code = row["og_code"]
            og_name = row["og_name"]
            definition = row["definition"]
            inclusions = row["inclusions"]
            exclusions = row["exclusions"]
        else:
            og_code, og_name, definition, inclusions, exclusions = (
                row[0], row[1], row[2], row[3], row[4]
            )

        lines.append(f"\n[{og_code}] {og_name}")
        lines.append(f"Definition: {(definition or '')[:400]}")
        if inclusions:
            lines.append(f"Inclusions: {inclusions[:400]}")
        if exclusions:
            lines.append(f"Exclusions: {exclusions[:300]}")

    lines.append(
        "\n\nSelect the top 3 OG codes from the list above that best match the confirmed NOC "
        "and work description. Use only the OG codes shown — never invent new ones."
    )
    return "\n".join(lines)


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

og_instructor_client = instructor.from_openai(_openai_client, mode=instructor.Mode.JSON)
