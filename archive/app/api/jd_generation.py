"""
app/api/jd_generation.py — FastAPI router for JD generation.

Routes:
  POST /api/jd/generate-duties   — runs generate_duties() pipeline; returns duty card list
  POST /api/jd/check-orphan-statements — runs check_orphan_statements(); returns orphan flags
  POST /api/jd/add-advisor-duty  — adds advisor duty; returns updated duty list
  POST /api/jd/confirm-duties    — confirms duties; sets stage='jd_drafted'; returns confirmed partial

All POST routes support dual HTMX/JSON response paths.
Stage gates: generate-duties and confirm-duties require stage='og_classified'.
             check-orphan-statements and add-advisor-duty accept 'og_classified' or 'jd_drafted'.
"""
from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.jd_service import (
    add_advisor_duty,
    check_orphan_statements,
    confirm_duties,
    generate_duties,
)

router = APIRouter()

_templates_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"
)
templates = Jinja2Templates(directory=_templates_dir)


@router.post("/api/jd/generate-duties")
async def generate_duties_route(
    request: Request,
    wd_id: str = Form(...),
):
    """
    Run the 3-step duty selection pipeline for a confirmed NOC + OG.
    Requires stage='og_classified'. Returns duty card list partial (HTMX) or JSON.
    """
    try:
        result = await generate_duties(wd_id=wd_id, db_path=settings.db_path)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=422, detail=msg)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/jd_duties.html",
            {
                "request": request,
                "duties": result["duties"],
                "selection_rationale": result["selection_rationale"],
                "wd_id": wd_id,
            },
        )
    return result


@router.post("/api/jd/check-orphan-statements")
async def check_orphan_statements_route(
    request: Request,
    wd_id: str = Form(...),
):
    """
    Run orphan statement check for all draft + advisor duties.
    Accepts stage 'og_classified' or 'jd_drafted'.
    Returns orphan flag list (HTMX) or JSON. Empty flags = clean (HTTP 200, not error).
    """
    try:
        result = await check_orphan_statements(wd_id=wd_id, db_path=settings.db_path)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=422, detail=msg)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/jd_orphan_results.html",
            {
                "request": request,
                "flags": result.flags,
                "summary": result.summary,
                "wd_id": wd_id,
            },
        )
    return {"flags": [f.model_dump() for f in result.flags], "summary": result.summary, "wd_id": wd_id}


@router.post("/api/jd/add-advisor-duty")
async def add_advisor_duty_route(
    request: Request,
    wd_id: str = Form(...),
    duty_text: str = Form(...),
):
    """
    Add an advisor-entered duty to advisor_additions with source_type='ADVISOR' (JD-03).
    Returns updated duty card list (HTMX) or JSON count.
    """
    try:
        result = await add_advisor_duty(
            wd_id=wd_id, duty_text=duty_text, db_path=settings.db_path
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=422, detail=msg)

    if request.headers.get("HX-Request"):
        # Re-load duties for the updated partial
        from app.db import get_connection
        from app.services.wd_store import load_work_description

        conn = await asyncio.to_thread(lambda: get_connection(settings.db_path))
        try:
            wd = await asyncio.to_thread(lambda: load_work_description(conn, wd_id))
        finally:
            await asyncio.to_thread(conn.close)

        if wd is None:
            raise HTTPException(status_code=404, detail=f"WorkDescription {wd_id!r} not found after save")

        all_duties = [
            {
                "id": str(d.id),
                "text": d.text,
                "source_type": d.provenance.source_type,
                "source_id": d.provenance.source_id,
                "source_version": d.provenance.source_version,
            }
            for d in list(wd.draft_duties) + list(wd.advisor_additions)
        ]
        return templates.TemplateResponse(
            "partials/jd_duties.html",
            {
                "request": request,
                "duties": all_duties,
                "selection_rationale": "",
                "wd_id": wd_id,
            },
        )
    return result


@router.post("/api/jd/confirm-duties")
async def confirm_duties_route(
    request: Request,
    wd_id: str = Form(...),
):
    """
    Confirm the current duty list. Sets stage='jd_drafted'. Persists WD to SQLite.
    Returns confirmation partial (HTMX) or JSON.
    """
    try:
        result = await confirm_duties(wd_id=wd_id, db_path=settings.db_path)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=422, detail=msg)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/jd_confirmed.html",
            {
                "request": request,
                "wd_id": wd_id,
                "duty_count": result["duty_count"],
                "stage": result["stage"],
            },
        )
    return result
