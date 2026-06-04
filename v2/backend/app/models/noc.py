"""
app/models/noc.py — Request and response models for POST /api/noc/map.

NocCandidateOut is a separate response model from the internal NOCCandidate
(noc_ranking.py) to keep the API contract independent of the pipeline model.
WorkDescriptionRequest validates the incoming free-text work description.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WorkDescriptionRequest(BaseModel):
    """Request body for POST /api/noc/map."""

    model_config = ConfigDict(extra="ignore")

    work_description: str = Field(
        ...,
        min_length=10,
        description="Free-text description of the work to classify against NOC 2021",
    )


class NocCandidateOut(BaseModel):
    """JSON-serializable NOC candidate for the /api/noc/map response."""

    model_config = ConfigDict(extra="ignore")

    noc_code: str
    title: str
    teer: int
    rank: int
    matched_duties: list[str]
    justification: str


class NocMapResponse(BaseModel):
    """Response body for POST /api/noc/map."""

    model_config = ConfigDict(extra="ignore")

    candidates: list[NocCandidateOut]
