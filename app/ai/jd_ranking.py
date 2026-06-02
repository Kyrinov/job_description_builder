"""
app/ai/jd_ranking.py — Instructor client singleton and Pydantic output models for JD generation.

DutySelection, DutyRankingResult, OrphanFlag, OrphanCheckResult are the structured output
types for the JD generation pipeline. jd_instructor_client is the module-level singleton;
construct once at import time, never per-request.

Architecture non-negotiable: Do not construct jd_instructor_client inside route handlers
or service functions — it creates an httpx connection pool on every call.
"""
from __future__ import annotations

import sqlite3
from typing import Literal

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config import settings


class DutySelection(BaseModel):
    """One duty row selected by the LLM from the noc_elements candidate list."""

    row_id: int = Field(
        description="ID from noc_elements table — must be from the provided candidate list"
    )
    rank: int = Field(
        ge=1,
        description="Rank 1 = most relevant to the confirmed OG and work description",
    )
    rationale: str = Field(
        description="Brief reason this duty is relevant to the confirmed OG and position"
    )


class DutyRankingResult(BaseModel):
    """Structured output from a single LLM duty selection call."""

    selections: list[DutySelection] = Field(
        min_length=1,
        max_length=15,
        description=(
            "Selected duty rows in relevance order — row_id values must be from the provided "
            "candidate list only; never invent IDs"
        ),
    )
    selection_rationale: str = Field(
        description="Overall rationale for the selection set — how these duties collectively "
        "describe the position in the confirmed OG"
    )


class OrphanFlag(BaseModel):
    """One duty flagged as a potential orphan statement by the LLM orphan check."""

    duty_text: str = Field(description="The duty statement that was flagged")
    rule_violated: str = Field(
        description=(
            "Verbatim text from og_definitions exclusions or inclusions that this duty "
            "violates — must be a substring of the provided rules text"
        )
    )
    source_document: str = Field(
        default="TBS OCHRO OG Definitions",
        description="Document containing the functional authority rule",
    )
    source_section: str = Field(
        description=(
            "Which section of the document: e.g., 'EC — Exclusions' or 'PE — Inclusions'"
        )
    )
    severity: Literal["hard", "soft"] = Field(
        description=(
            "'hard' if this duty is explicitly in another OG's inclusions; "
            "'soft' if it merely conflicts with this OG's exclusions"
        )
    )


class OrphanCheckResult(BaseModel):
    """Structured output from a single LLM orphan check call."""

    flags: list[OrphanFlag] = Field(
        default_factory=list,
        description=(
            "List of flagged duties. Empty list means all duties are consistent with the "
            "confirmed OG — this is a valid, expected result (JD-04)."
        ),
    )
    summary: str = Field(
        description="Brief summary of orphan check result; 'No orphan statements detected.' if flags is empty"
    )


DUTY_SELECTION_SYSTEM_PROMPT = """
You are a Government of Canada HR classification specialist.
You are selecting which NOC duty statements best describe the work of a position in the {og_name} ({og_code}) group.

CRITICAL RULES:
- You may ONLY return row_id values from the numbered list provided — never invent IDs
- Select 5-12 duties that collectively describe the full scope of the position
- Rank by relevance to the confirmed OG and the work description (rank 1 = most relevant)
- Do NOT paraphrase or modify duty text — select by ID only
- row_id must be an integer matching the number in square brackets before each duty
""".strip()


ORPHAN_CHECK_SYSTEM_PROMPT = """
You are a Government of Canada HR classification specialist reviewing draft job duties for classification correctness.

You are checking whether any duties listed below fall outside the functional authority of the {og_name} ({og_code}) occupational group.

A duty is an "orphan statement" if:
1. It is explicitly listed in the Exclusions for {og_code}, OR
2. It belongs primarily to another OG's Inclusions

Functional authority rules for {og_code}:
--- EXCLUSIONS ---
{og_exclusions}

--- INCLUSIONS (for reference) ---
{og_inclusions}

For each flagged duty, cite the EXACT verbatim text from the rules above that it violates.
If NO duties violate these rules, return an empty flags list — this is a valid and expected result.
Do NOT flag duties just because they are uncommon; only flag genuine classification conflicts.
""".strip()


def get_noc_version_info(conn: sqlite3.Connection) -> tuple[str, str]:
    """
    Return (version_label, content_hash) for the NOC elements source document.

    Used to populate ProvenanceTag.source_version when building DraftDuty objects.
    Fallback: ("NOC 2021 v1.0", "") if no matching source_documents row found.
    """
    try:
        row = conn.execute(
            "SELECT version_label, content_hash FROM source_documents "
            "WHERE source_name LIKE '%elements%' LIMIT 1"
        ).fetchone()
        if row:
            return row["version_label"], row["content_hash"]
    except Exception:
        pass
    return "NOC 2021 v1.0", ""


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

jd_instructor_client = instructor.from_openai(_openai_client, mode=instructor.Mode.JSON)
