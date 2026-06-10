"""
app/api/wd.py — WD CRUD: POST /api/wd, GET /api/wd/{id}, PATCH /api/wd/{id}.

Serialises WorkDescription to JSON in the work_descriptions.data column.
Each step commit from the SPA calls PATCH; first commit calls POST.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.config import get_settings
from app.db import get_connection
from app.models.work_description import WorkDescription

router = APIRouter()


class WDCreateRequest(BaseModel):
    """Mutable fields for creating a new WD. Server generates id and timestamps."""

    record: dict = Field(default_factory=dict)
    answers: dict = Field(default_factory=dict)
    step_index: int = 0
    draft: Optional[dict] = None
    reviewing: bool = False
    editing_return: bool = False


class WDPatchRequest(BaseModel):
    """Partial update fields. Only provided fields are merged onto the stored WD."""

    model_config = ConfigDict(extra="ignore")

    record: Optional[dict] = None
    answers: Optional[dict] = None
    step_index: Optional[int] = None
    draft: Optional[dict] = None
    reviewing: Optional[bool] = None
    editing_return: Optional[bool] = None
    confirmed_noc: Optional[dict] = None
    confirmed_og: Optional[dict] = None
    og_level: Optional[int] = None
    reports_to_military: Optional[bool] = None
    jes_scores: Optional[list[dict]] = None
    jes_total_points: Optional[int] = None
    duties: Optional[list[dict]] = None


@router.post("/wd", status_code=201)
async def create_wd(body: WDCreateRequest) -> dict:
    """Create a new WorkDescription and return its generated id."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    wd = WorkDescription(
        id=str(uuid4()),
        record=body.record,
        answers=body.answers,
        step_index=body.step_index,
        draft=body.draft,
        reviewing=body.reviewing,
        editing_return=body.editing_return,
        created_at=now,
        last_modified=now,
    )
    con = get_connection(settings.db_path)
    try:
        con.execute(
            "INSERT INTO work_descriptions (id, title, data, schema_version, created_at, last_modified) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                wd.id,
                wd.title,
                wd.model_dump_json(),
                wd.schema_version,
                wd.created_at.isoformat(),
                wd.last_modified.isoformat(),
            ),
        )
        con.commit()
    finally:
        con.close()
    return {"id": wd.id}


@router.get("/wd/{wd_id}")
async def get_wd(wd_id: str) -> WorkDescription:
    """Return the stored WorkDescription for the given id."""
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
    finally:
        con.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Work description not found")
    return WorkDescription.model_validate_json(row["data"])


@router.patch("/wd/{wd_id}")
async def patch_wd(wd_id: str, body: WDPatchRequest) -> WorkDescription:
    """Merge patch fields onto the stored WorkDescription and update last_modified."""
    import logging
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Work description not found")
        wd = WorkDescription.model_validate_json(row["data"])
        # Separate duties from scalar fields to enable validated merge
        raw_duties = body.duties  # extract before model_dump excludes it
        body_dump = body.model_dump(exclude_unset=True, exclude={'duties'})
        # Diagnostic: log classification-related fields if present
        cls_keys = [k for k in body_dump if k in ('confirmed_og', 'og_level', 'confirmed_noc', 'jes_total_points')]
        if cls_keys:
            logging.getLogger(__name__).info(
                "PATCH wd=%s classification fields: %s",
                wd_id[:8], {k: body_dump[k] for k in cls_keys},
            )
        for field, val in body_dump.items():
            setattr(wd, field, val)
        # Duties: validate each item against DraftDuty; cap at 20 (DoS mitigation)
        if raw_duties is not None:
            from app.models.draft_duty import DraftDuty as DD
            wd.duties = [DD(**d) for d in raw_duties[:20]]
        wd.last_modified = datetime.now(timezone.utc)
        con.execute(
            "UPDATE work_descriptions SET data = ?, last_modified = ? WHERE id = ?",
            (wd.model_dump_json(), wd.last_modified.isoformat(), wd_id),
        )
        con.commit()
    finally:
        con.close()
    return wd


def _duty_contradicts_og(duty_lower: str, exclusions_text: str) -> bool:
    """Keyword check: True if any exclusion keyword appears in duty text.

    EC exclusions are empty — always returns False for EC positions.
    IT exclusions contain keywords like 'business analysis', 'administrative programs'.
    """
    exclusion_keywords = [
        phrase.strip().lower()
        for phrase in exclusions_text.replace(';', ',').split(',')
        if len(phrase.strip()) > 4
    ]
    return any(kw in duty_lower for kw in exclusion_keywords)


@router.post("/wd/{wd_id}/orphan_check")
async def run_orphan_check(wd_id: str) -> dict:
    """Deterministic orphan check: verb-keyword match against OG_DEFINITIONS.exclusions.

    No LLM — v2.0 policy is deterministic classification throughout.
    EC positions always return flagged: [] (EC has no exclusions defined).
    """
    from app.data.constants import OG_DEFINITIONS
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
    finally:
        con.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Work description not found")
    wd = WorkDescription.model_validate_json(row["data"])
    if not wd.confirmed_og:
        raise HTTPException(status_code=422, detail="OG not confirmed — orphan check requires confirmed OG")
    og_code = (
        wd.confirmed_og.get("og_code")
        if isinstance(wd.confirmed_og, dict)
        else wd.confirmed_og.og_code
    )
    defn = OG_DEFINITIONS.get(og_code, {})
    exclusions_text = defn.get("exclusions", "")
    flagged = []
    for duty in wd.duties:
        duty_lower = duty.text.lower()
        if exclusions_text and _duty_contradicts_og(duty_lower, exclusions_text):
            flagged.append({
                "duty_id": duty.id,
                "orphan_rationale": (
                    f"This duty may fall outside the {og_code} functional authority: "
                    f"{exclusions_text[:200]}"
                ),
            })
    return {"wd_id": wd_id, "flagged": flagged}
