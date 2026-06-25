"""
app/models/og.py — Request and response Pydantic models for the OG classification API.

OGClassifyRequest: POST /api/og/classify body (wd_id only — work description loaded from DB)
OGClassifyResponse: POST /api/og/classify JSON response (HTMX returns TemplateResponse instead)
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.ai.og_ranking import OGCandidate


class OGClassifyRequest(BaseModel):
    wd_id: str = Field(..., description="WorkDescription ID — must be in 'noc_mapped' stage")


class OGClassifyResponse(BaseModel):
    candidates: list[OGCandidate] = Field(..., min_length=1, max_length=3)
    wd_id: str
    asec_alert: dict | None = None
