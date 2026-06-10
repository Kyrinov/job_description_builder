"""
app/api/jes_scoring.py — JES scoring routes (v2.0).

Routes:
    POST /api/jes/score — score a WD against JES; requires OG confirmed (CLASS-04 gate)
    POST /api/jes/override/{wd_id}/{factor_name} — advisor manual degree override

Security (per threat model T-17-01 to T-17-04):
    T-17-01: og_code validated against {"EC"} | set(NON_EC_TOTALS.keys())
    T-17-02: duties list truncated to [:10] in _build_factor_user_prompt + per-duty [:200]
    T-17-03: factor_name validated against KNOWN_JES_FACTORS; 400 if not found
    T-17-04: work description summary truncated to [:300] in _build_factor_user_prompt
"""
from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.data.constants import (
    JES_FACTORS_BY_GROUP,
    KNOWN_JES_FACTORS,
    NON_EC_TOTALS,
)
from app.db import get_connection
from app.models.work_description import WorkDescription
from app.services.classification_gate import require_og_confirmed
from app.services.jes_service import override_jes_factor, score_jes_v2

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class JESScorecardRequest(BaseModel):
    """Request body for POST /api/jes/score.

    T-17-01: og_code is whitelisted in the route handler (must be 'EC' or in NON_EC_TOTALS).
    T-17-02: duties are truncated in the service layer ([:10] and per-duty [:200]).
    """

    wd_id: str = Field(min_length=1)
    og_code: str = Field(min_length=1)
    og_level: int = Field(ge=1)
    duties: list[str] = Field(default_factory=list)


class JESFactorScoreOut(BaseModel):
    """One JES factor row in the scorecard response."""

    factor_name: str
    degree: int  # -1 = failed sentinel
    points: int | None
    rationale: str
    advisor_adjusted: bool = False


class JESScorecardResponse(BaseModel):
    """Response body for POST /api/jes/score."""

    wd_id: str
    og_code: str
    is_ec: bool
    factors: list[JESFactorScoreOut]
    total_points: int
    standard_name: str
    has_failed_factors: bool


class JESOverrideRequest(BaseModel):
    """Request body for POST /api/jes/override/{wd_id}/{factor_name}."""

    degree: int = Field(ge=1, le=8)
    rationale: str = Field(min_length=1, max_length=500)


class JESOverrideResponse(BaseModel):
    """Response body for POST /api/jes/override/{wd_id}/{factor_name}."""

    wd_id: str
    factor_name: str
    degree: int
    points: int | None
    jes_total_points: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/jes/score")
async def score_jes(body: JESScorecardRequest) -> JESScorecardResponse:
    """Score a WD against the JES.

    Requires OG confirmed (CLASS-04 gate via require_og_confirmed).
    For EC: per-factor LLM scoring with 3 retries; sentinel on failure.
    For non-EC (FI/IT/AS/EN): single totals dict from NON_EC_TOTALS, no LLM.

    T-17-01: og_code is validated against {"EC"} | set(NON_EC_TOTALS.keys()).
    """
    # T-17-01: validate og_code (Phase 21: also accept point-rating groups + SW-SCW/ED-EDS sub-group routing codes)
    valid_og_codes = (
        {"EC"}
        | set(NON_EC_TOTALS.keys())
        | set(JES_FACTORS_BY_GROUP.keys())
        | {"SW-SCW", "ED-EDS"}
    )
    if body.og_code not in valid_og_codes:
        raise HTTPException(
            status_code=400,
            detail=f"unknown og_code {body.og_code!r}; must be one of {sorted(valid_og_codes)}",
        )

    # Load WD
    from app.config import get_settings
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (body.wd_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Work description not found")
        wd = WorkDescription.model_validate_json(row["data"])
    finally:
        con.close()

    # CLASS-04 gate
    require_og_confirmed(wd)

    # Run scoring
    result = await score_jes_v2(
        wd_id=body.wd_id,
        og_code=body.og_code,
        og_level=body.og_level,
        duties=body.duties,
        db_path=settings.db_path,
    )

    return JESScorecardResponse(
        wd_id=result["wd_id"],
        og_code=result["og_code"],
        is_ec=result["is_ec"],
        factors=[JESFactorScoreOut(**f) for f in result["factors"]],
        total_points=result["total_points"],
        standard_name=result["standard_name"],
        has_failed_factors=result["has_failed_factors"],
    )


@router.post("/jes/override/{wd_id}/{factor_name}")
async def override_jes(
    wd_id: str, factor_name: str, body: JESOverrideRequest
) -> JESOverrideResponse:
    """Advisor manually sets degree + rationale for one JES factor.

    T-17-03: factor_name validated against KNOWN_JES_FACTORS (400 if not found).
    Writes audit_log row with event='jes_override'.
    """
    # T-17-03: validate factor_name
    if factor_name not in KNOWN_JES_FACTORS:
        raise HTTPException(
            status_code=400,
            detail=f"unknown factor_name {factor_name!r}; must be one of {sorted(KNOWN_JES_FACTORS)}",
        )

    from app.config import get_settings
    settings = get_settings()
    result = override_jes_factor(
        wd_id=wd_id,
        factor_name=factor_name,
        degree=body.degree,
        rationale=body.rationale,
        db_path=settings.db_path,
    )

    return JESOverrideResponse(
        wd_id=result["wd_id"],
        factor_name=result["factor_name"],
        degree=result["degree"],
        points=result["points"],
        jes_total_points=result["jes_total_points"],
    )
