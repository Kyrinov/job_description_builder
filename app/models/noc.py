"""
app/models/noc.py — Request and response Pydantic models for the NL→NOC mapping API.

WorkDescriptionRequest: POST /api/noc/map body
NocMapResponse: POST /api/noc/map response

NocMapResponse wraps NOCRankingResult.candidates directly — the route handler
maps NOCRankingResult → NocMapResponse before returning to the client.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.ai.noc_ranking import NOCCandidate


class WorkDescriptionRequest(BaseModel):
    """Request body for POST /api/noc/map."""

    work_description: str = Field(
        ...,
        min_length=10,
        description="Plain-language description of the work to be performed",
    )
    wd_id: str | None = None


class NocMapResponse(BaseModel):
    """Response body for POST /api/noc/map — ranked NOC candidates."""

    candidates: list[NOCCandidate] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Ranked NOC candidates, best match first",
    )
    wd_id: str = Field(
        ...,
        description="WorkDescription ID. Use this in the subsequent POST /api/noc/confirm call.",
    )
