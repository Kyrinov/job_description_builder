"""
app/api/noc_mapping.py — FastAPI router for NL→NOC mapping endpoints.

Routes:
  POST /api/noc/map     — Submit work description, receive ranked NOC candidates.
                          Returns HTML partial (TemplateResponse) for HTMX requests
                          (HX-Request header present); returns NocMapResponse JSON for
                          direct API calls. This dual-path is required for HTMX hx-swap.
                          Persists candidates to WorkDescription.noc_candidates so the
                          confirm endpoint can match against them.
  POST /api/noc/confirm — Confirm a NOC candidate; stores confirmed_noc on WorkDescription
"""
from __future__ import annotations

import asyncio
import os
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.db import get_connection
from app.models.noc import NocMapResponse, WorkDescriptionRequest
from app.models.work_description import WorkDescription
from app.services.noc_mapper import map_work_description, to_noc_match
from app.services.wd_store import load_work_description, save_work_description

router = APIRouter()

_templates_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"
)
templates = Jinja2Templates(directory=_templates_dir)


@router.post("/api/noc/map")
async def map_noc(request: Request, body: WorkDescriptionRequest):
    """
    Run the three-stage NL→NOC pipeline and return ranked candidates.

    Persists the returned candidates to WorkDescription.noc_candidates so the
    subsequent /api/noc/confirm call can match against them. Creates a new
    WorkDescription if body.wd_id is not provided.

    HTMX requests (HX-Request header present) receive a TemplateResponse rendering
    partials/noc_results.html — the HTMX swap target expects server-rendered HTML.
    Direct API calls receive a NocMapResponse JSON object.
    """
    try:
        result = await map_work_description(
            work_description=body.work_description,
            db_path=settings.db_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # --- Persist candidates to WorkDescription so /api/noc/confirm can find them ---
    conn = await asyncio.to_thread(lambda: get_connection(settings.db_path))
    try:
        if body.wd_id:
            wd = await asyncio.to_thread(lambda: load_work_description(conn, body.wd_id))
            if wd is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"WorkDescription {body.wd_id!r} not found",
                )
        else:
            wd = WorkDescription(
                id=uuid4(),
                session_id=request.headers.get("X-Session-Id", "anonymous"),
                raw_input=body.work_description,
                stage="input",
            )

        # Convert NOCCandidate (pipeline output) → NOCMatch (WorkDescription storage type)
        wd.noc_candidates = [to_noc_match(c) for c in result.candidates]
        wd_id_str = str(wd.id)
        await asyncio.to_thread(lambda: save_work_description(conn, wd))
    finally:
        await asyncio.to_thread(conn.close)

    if request.headers.get("HX-Request"):
        # HTMX call — return HTML partial for hx-swap="innerHTML"
        return templates.TemplateResponse(
            "partials/noc_results.html",
            {
                "request": request,
                "candidates": result.candidates,
                "wd_id": wd_id_str,
            },
        )
    # Direct API call — return JSON (include wd_id so callers can follow up with confirm)
    return NocMapResponse(
        candidates=result.candidates,
        wd_id=wd_id_str,
    )


@router.post("/api/noc/confirm")
async def confirm_noc(
    request: Request,
    wd_id: str = Form(...),
    noc_code: str = Form(...),
) -> dict:
    """
    Confirm a NOC candidate for a WorkDescription.
    Loads the WorkDescription by wd_id, sets confirmed_noc, sets stage="noc_mapped", persists.
    Returns HTML partial for HTMX requests; JSON for direct API calls.
    """
    conn = await asyncio.to_thread(lambda: get_connection(settings.db_path))
    try:
        wd = await asyncio.to_thread(lambda: load_work_description(conn, wd_id))
        if wd is None:
            raise HTTPException(status_code=404, detail=f"WorkDescription {wd_id!r} not found")

        matched_candidate = next(
            (c for c in wd.noc_candidates if c.noc_code == noc_code), None
        )
        if matched_candidate is None:
            raise HTTPException(
                status_code=422,
                detail=f"noc_code {noc_code!r} not found in WorkDescription.noc_candidates",
            )

        wd.confirmed_noc = matched_candidate
        wd.stage = "noc_mapped"
        await asyncio.to_thread(lambda: save_work_description(conn, wd))
    finally:
        await asyncio.to_thread(conn.close)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/noc_confirmed.html",
            {
                "request": request,
                "noc_code": matched_candidate.noc_code,
                "noc_title": matched_candidate.noc_title,
                "teer": matched_candidate.teer_level,
            },
        )
    return {"status": "confirmed", "noc_code": noc_code, "wd_id": wd_id}
