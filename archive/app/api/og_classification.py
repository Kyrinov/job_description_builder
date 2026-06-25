"""
app/api/og_classification.py — FastAPI router for OG classification.

Routes:
  POST /api/og/classify  — runs classify_og() pipeline; returns top-3 OG candidates
  POST /api/og/confirm   — confirms OG and level; sets stage='og_classified'

Both routes support dual HTMX/JSON response paths.
"""
from __future__ import annotations

import asyncio
import os
from datetime import date

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.ai.og_ranking import OG_LEVELS
from app.config import settings
from app.db import get_connection
from app.models.og import OGClassifyResponse
from app.models.work_description import OGRecommendation, ProvenanceTag
from app.services.og_classifier import classify_og
from app.services.wd_store import load_work_description, save_work_description

router = APIRouter()

_templates_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"
)
templates = Jinja2Templates(directory=_templates_dir)


@router.post("/api/og/classify")
async def classify_og_route(
    request: Request,
    wd_id: str = Form(...),
) -> OGClassifyResponse:
    """
    Run the 3-step OG classification pipeline for a confirmed NOC match.
    The work description and confirmed NOC are loaded from the WorkDescription record.
    """
    conn = await asyncio.to_thread(lambda: get_connection(settings.db_path))
    try:
        wd = await asyncio.to_thread(lambda: load_work_description(conn, wd_id))
        if wd is None:
            raise HTTPException(status_code=404, detail=f"WorkDescription {wd_id!r} not found")
        if wd.stage != "noc_mapped":
            raise HTTPException(
                status_code=422,
                detail=f"WorkDescription is in stage {wd.stage!r}, expected 'noc_mapped'",
            )
        if wd.confirmed_noc is None:
            raise HTTPException(
                status_code=422,
                detail="WorkDescription has no confirmed NOC — complete NOC mapping first",
            )

        try:
            result = await classify_og(
                work_description=wd.raw_input,
                confirmed_noc_code=str(wd.confirmed_noc.noc_code),
                db_path=settings.db_path,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        if result["candidates"]:
            top = result["candidates"][0]
            og_rec = OGRecommendation(
                og_code=top["og_code"],
                og_name=top["og_name"],
                level=None,
                confidence=top["confidence"],
                rationale=top["rationale"],
                provenance=ProvenanceTag(
                    source_type="TBS_OG_DEF",
                    source_id=top["og_code"],
                    source_version="TBS-OCHRO-OG.txt",
                    retrieved_date=date.today(),
                    model_name=settings.generation_model,
                ),
                evidence_quotes=top["evidence_quotes"],
                cited_articles=[
                    ProvenanceTag(
                        source_type="TBS_OG_DEF",
                        source_id=candidate["og_code"],
                        source_version="TBS-OCHRO-OG.txt",
                        retrieved_date=date.today(),
                        model_name=settings.generation_model,
                    )
                    for candidate in result["candidates"]
                ],
                confirmed_by_advisor=False,
            )
            wd = wd.model_copy(update={"og_recommendation": og_rec})
            await asyncio.to_thread(lambda: save_work_description(conn, wd))

    finally:
        await asyncio.to_thread(conn.close)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/og_results.html",
            {
                "request": request,
                "candidates": result["candidates"],
                "asec_alert": result.get("asec_alert"),
                "wd_id": wd_id,
            },
        )
    from app.ai.og_ranking import OGCandidate as _OGCandidate
    json_candidates = [
        _OGCandidate(
            og_code=c["og_code"],
            rank=c["rank"],
            confidence=c["confidence"],
            rationale=c["rationale"],
            evidence_quotes=c["evidence_quotes"],
        )
        for c in result["candidates"]
    ]
    return OGClassifyResponse(
        candidates=json_candidates,
        wd_id=wd_id,
        asec_alert=result.get("asec_alert"),
    )


@router.post("/api/og/confirm")
async def confirm_og(
    request: Request,
    wd_id: str = Form(...),
    og_code: str = Form(...),
    og_level: str = Form(...),
) -> dict:
    """
    Confirm OG and level selection. Sets WorkDescription.stage='og_classified'.
    og_level must be a valid integer level for og_code per OG_LEVELS.
    """
    valid_levels = OG_LEVELS.get(og_code, [])
    try:
        level_int = int(og_level)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=422,
            detail=f"og_level must be an integer, got {og_level!r}",
        )
    if level_int not in valid_levels:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid level {og_level!r} for OG {og_code!r}. Valid levels: {valid_levels}",
        )

    conn = await asyncio.to_thread(lambda: get_connection(settings.db_path))
    try:
        wd = await asyncio.to_thread(lambda: load_work_description(conn, wd_id))
        if wd is None:
            raise HTTPException(status_code=404, detail=f"WorkDescription {wd_id!r} not found")
        if wd.stage != "noc_mapped":
            raise HTTPException(
                status_code=422,
                detail=f"WorkDescription is in stage {wd.stage!r}, expected 'noc_mapped' for OG confirmation",
            )

        og_rec_update: dict = {}
        if wd.og_recommendation and wd.og_recommendation.og_code == og_code:
            og_rec_update = {"og_recommendation": wd.og_recommendation.model_copy(
                update={
                    "confirmed_by_advisor": True,
                    "level": f"{og_code}-{level_int:02d}",
                }
            )}

        confirmed_level_str = f"{og_code}-{level_int:02d}"
        wd = wd.model_copy(
            update={
                "confirmed_og": og_code,
                "confirmed_level": confirmed_level_str,
                "og_level": confirmed_level_str,
                "stage": "og_classified",
                **og_rec_update,
            }
        )
        await asyncio.to_thread(lambda: save_work_description(conn, wd))
    finally:
        await asyncio.to_thread(conn.close)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/og_confirmed.html",
            {
                "request": request,
                "og_code": og_code,
                "og_level": confirmed_level_str,
                "og_name": wd.og_recommendation.og_name if wd.og_recommendation else og_code,
                "wd_id": wd_id,
            },
        )
    return {
        "status": "confirmed",
        "og_code": og_code,
        "og_level": confirmed_level_str,
        "wd_id": wd_id,
    }
