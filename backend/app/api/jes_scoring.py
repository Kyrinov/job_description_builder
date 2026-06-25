"""
app/api/jes_scoring.py — JES scoring routes (v2.0).

Routes:
    POST /api/jes/score — score a WD against JES; requires OG confirmed (CLASS-04 gate)
    POST /api/jes/override/{wd_id}/{factor_name} — advisor manual degree override
    POST /api/jes/level-suggest — Socratic level-determination for level-description groups (Phase 21 Plan 08)
    GET  /api/jes/level-criteria — fetch level-determination question structure (Phase 21 Plan 08)
    GET  /api/jes/level-criteria-groups — list OG codes that have level-description criteria (Phase 21 Plan 08)

Security (per threat model T-17-01 to T-17-04, T-21-08-01 to T-21-08-03):
    T-17-01: og_code validated against {"EC"} | set(NON_EC_TOTALS.keys())
    T-17-02: duties list truncated to [:10] in _build_factor_user_prompt + per-duty [:200]
    T-17-03: factor_name validated against KNOWN_JES_FACTORS; 400 if not found
    T-17-04: work description summary truncated to [:300] in _build_factor_user_prompt
    T-21-08-01: POST /api/jes/level-suggest — og_code validated against KNOWN_OG_CODES (422 on unknown)
    T-21-08-02: POST /api/jes/level-suggest — unknown answer IDs silently skip (no security risk)
    T-21-08-03: GET /api/jes/level-criteria returns public JES data (no PII / proprietary data)
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.data.constants import (
    JES_FACTORS_BY_GROUP,
    JES_LEVEL_CRITERIA,
    KNOWN_JES_FACTORS,
    NON_EC_TOTALS,
)
from app.db import get_connection
from app.models.work_description import WorkDescription
from app.services.classification_gate import require_og_confirmed
from app.services.jes_service import override_jes_factor, score_jes_v2

router = APIRouter()


# ---------------------------------------------------------------------------
# Phase 21 Plan 08 (JES-LEV-01): known OG codes + level-suggest request model.
# Mirrors the 22 OG codes in OG_LEVELS + SW-SCW / ED-EDS sub-group routing
# codes (point-rating path; not in JES_LEVEL_CRITERIA but the level-suggest
# endpoint rejects them with 404, same as EC).
# ---------------------------------------------------------------------------

KNOWN_OG_CODES: frozenset[str] = frozenset({
    "EC", "IT", "AS", "FI", "CR", "PM", "GT", "EL", "FB", "FS", "AI", "AU",
    "ED", "LC", "LP", "MT", "NT", "NU", "PO", "PS", "SW", "WP",
})


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


# ---------------------------------------------------------------------------
# Phase 21 Plan 08 (JES-LEV-01) — Socratic level-determination endpoints
# ---------------------------------------------------------------------------


class LevelSuggestRequest(BaseModel):
    """Request body for POST /api/jes/level-suggest.

    T-21-08-01: og_code is whitelisted in the route handler (422 on unknown).
    T-21-08-02: unknown answer IDs are silently skipped (no level_hint added).
    """

    og_code: str = Field(min_length=1)
    sub_group: str | None = None
    answers: dict[str, str] = Field(default_factory=dict)


def _resolve_level_suggestion(
    criteria: dict, answers: dict[str, str]
) -> dict:
    """Compute suggested_level, confidence, level_range, and rationale.

    Pure helper (no I/O) — used by POST /api/jes/level-suggest route.

    level_resolution semantics:
      - "direct": single question, level_hint is length-1 list → direct map.
      - "majority_hint": level appearing in the most hint_lists wins;
                          tie → lower level (conservative).

    Confidence: 'high' when all questions answered AND the winning level
    appears in every answered list; 'medium' when winning level appears in
    >= 2 hint lists; 'low' otherwise (or when no answers provided).
    """
    questions = criteria["questions"]
    resolution = criteria["level_resolution"]

    # Collect level_hint lists for answered questions
    hint_lists: list[list[int]] = []
    for q in questions:
        ans_id = answers.get(q["id"])
        if ans_id is None:
            continue
        opt = next((o for o in q["options"] if o["id"] == ans_id), None)
        if opt:
            hint_lists.append(opt["level_hint"])

    if not hint_lists:
        return {
            "suggested_level": None,
            "confidence": "low",
            "level_range": [],
            "rationale": "No answers provided.",
        }

    if resolution == "direct":
        # Single question — return first hint directly
        suggested = hint_lists[0][0]
        level_range = hint_lists[0]
        return {
            "suggested_level": suggested,
            "confidence": "high",
            "level_range": level_range,
            "rationale": f"Your answer directly maps to Level {suggested:02d}.",
        }

    # majority_hint: find level appearing in the most hint_lists
    counts: Counter[int] = Counter()
    for hl in hint_lists:
        for lv in hl:
            counts[lv] += 1
    if not counts:
        return {
            "suggested_level": None,
            "confidence": "low",
            "level_range": [],
            "rationale": "Could not determine level.",
        }
    max_count = max(counts.values())
    # All levels at max_count; conservative: lowest
    candidates = sorted(k for k, v in counts.items() if v == max_count)
    suggested = candidates[0]
    total_q = len(questions)
    answered = len(hint_lists)
    if max_count == answered and answered == total_q:
        confidence = "high"
    elif max_count >= 2:
        confidence = "medium"
    else:
        confidence = "low"
    # level_range = sorted union of all hinted levels
    all_hinted = sorted(set(lv for hl in hint_lists for lv in hl))
    return {
        "suggested_level": suggested,
        "confidence": confidence,
        "level_range": all_hinted,
        "rationale": (
            f"Your answers suggest Level {suggested:02d} based on "
            f"{answered} of {total_q} factors."
        ),
    }


@router.post("/jes/level-suggest")
def level_suggest(req: LevelSuggestRequest) -> dict:
    """Socratic level-determination for level-description OG groups (Plan 08 JES-LEV-01).

    T-21-08-01: og_code is validated against KNOWN_OG_CODES (422 on unknown).
    T-21-08-02: unknown answer IDs are silently skipped (no level_hint added).
    Returns { suggested_level, confidence, level_range, rationale }.
    """
    # T-21-08-01: validate og_code
    if req.og_code not in KNOWN_OG_CODES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown og_code: {req.og_code}",
        )
    # Build lookup key: "OG-SUBGROUP" or bare "OG"
    key = f"{req.og_code}-{req.sub_group}" if req.sub_group else req.og_code
    if key not in JES_LEVEL_CRITERIA:
        raise HTTPException(
            status_code=404,
            detail=f"No level criteria for {key}",
        )
    criteria = JES_LEVEL_CRITERIA[key]
    return _resolve_level_suggestion(criteria, req.answers)


@router.get("/jes/level-criteria")
def level_criteria(og_code: str, sub_group: str | None = None) -> dict:
    """Return the JES level-determination question structure for one OG/sub-group.

    T-21-08-01: og_code is whitelisted (422 on unknown).
    T-21-08-03: returns public JES data only (no PII / proprietary data).
    """
    if og_code not in KNOWN_OG_CODES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown og_code: {og_code}",
        )
    key = f"{og_code}-{sub_group}" if sub_group else og_code
    if key not in JES_LEVEL_CRITERIA:
        raise HTTPException(
            status_code=404,
            detail=f"No level criteria for {key}",
        )
    return JES_LEVEL_CRITERIA[key]


@router.get("/jes/level-criteria-groups")
def level_criteria_groups() -> list[str]:
    """Return the sorted list of distinct og_codes that have JES level-description criteria.

    The OG codes that have at least one sub-group entry in JES_LEVEL_CRITERIA.
    Point-rating groups (EC, IT, AS, FI, etc.) are excluded — they do not
    have level-determination questions, only point totals.
    """
    og_codes: set[str] = set()
    for key in JES_LEVEL_CRITERIA.keys():
        og_codes.add(key.split("-")[0])
    return sorted(og_codes)
