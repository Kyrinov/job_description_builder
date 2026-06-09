"""
app/api/amendments.py — Amendment note routes (v2.0).

Routes:
    POST /api/wd/{wd_id}/amendments — save a manager amendment note to audit_log
    GET  /api/wd/{wd_id}/amendments — retrieve latest note per section (page-refresh hydration)

Security:
    Section key validated against known set via Literal type (ASVS V5 input validation).
    Comment max_length=2000 — same cap as work_description field (T-16-03 pattern).
    WD existence checked before INSERT (404 guard — same as jes_override).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.db import get_connection

router = APIRouter()


class AmendmentRequest(BaseModel):
    section: Literal['id', 'ov', 'du', 'cls', 'q', 'drf'] = Field(
        ..., description="Semantic section key"
    )
    comment: str = Field(min_length=1, max_length=2000)


@router.post("/wd/{wd_id}/amendments", status_code=201)
async def save_amendment(wd_id: str, body: AmendmentRequest) -> dict:
    """Save a manager amendment note to audit_log."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT id FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Work description not found")
        con.execute(
            "INSERT INTO audit_log (wd_id, event, actor, detail, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                wd_id,
                "manager_amendment",
                "advisor",
                json.dumps({"section": body.section, "comment": body.comment}),
                now.isoformat(),
            ),
        )
        con.commit()
    finally:
        con.close()
    return {"wd_id": wd_id, "section": body.section, "saved": True}


@router.get("/wd/{wd_id}/amendments")
async def get_amendments(wd_id: str) -> dict:
    """Return latest amendment note per section for page-refresh hydration.

    Uses ORDER BY id DESC so the first occurrence per section is the most recent.
    """
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        rows = con.execute(
            "SELECT detail, created_at FROM audit_log "
            "WHERE wd_id = ? AND event = 'manager_amendment' "
            "ORDER BY id DESC",
            (wd_id,),
        ).fetchall()
    finally:
        con.close()
    notes = {}
    for row in rows:
        detail = json.loads(row["detail"])
        section = detail.get("section")
        if section and section not in notes:
            notes[section] = detail.get("comment", "")
    return {"wd_id": wd_id, "notes": notes}
