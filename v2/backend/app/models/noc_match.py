"""
app/models/noc_match.py — NOCMatch Pydantic model (v2.0).

Simplified relative to v1.0 NOCMatch (no ProvenanceTag — that's Phase 18).
Used to store NOC pipeline candidates and the confirmed selection on WorkDescription.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class NOCMatch(BaseModel):
    """A single NOC candidate from the three-stage pipeline."""

    model_config = ConfigDict(extra="ignore")

    noc_code: str = Field(..., description="5-digit NOC 2021 unit group code")
    noc_title: str = Field(..., description="NOC unit group title")
    teer: int = Field(..., ge=0, le=5, description="TEER level 0-5 (authoritative from DB)")
    matched_duties: list[str] = Field(default_factory=list, description="Verbatim duty matches")
    justification: str = Field(default="", description="LLM rationale for this candidate")
    rank: int = Field(..., ge=1, description="1 = best fit")
