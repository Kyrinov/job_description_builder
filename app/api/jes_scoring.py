"""
app/api/jes_scoring.py — FastAPI router for JES scoring (Phase 7).

POST /api/jes/score — run per-factor JES scoring for a confirmed WorkDescription.
  Requires stage='jd_drafted'. Returns HTMX partial or JSON.

Direct analog: app/api/jd_generation.py
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.jes_service import score_jes

router = APIRouter()

_templates_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"
)
templates = Jinja2Templates(directory=_templates_dir)


@router.post("/api/jes/score")
async def score_jes_route(
    request: Request,
    wd_id: str = Form(...),
):
    """Run the per-factor JES scoring pipeline for a confirmed WorkDescription.

    Requires stage='jd_drafted'. Returns factor score cards (HTMX) or JSON dict.
    Error mapping:
        ValueError("not found") → 404
        ValueError(other)       → 422
    """
    try:
        result = await score_jes(wd_id=wd_id, db_path=settings.db_path)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=422, detail=msg)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/jes_scores.html",
            {
                "request": request,
                "jes_scores": result["jes_scores"],
                "jes_total_points": result["jes_total_points"],
                "wd_id": wd_id,
            },
        )
    return result
