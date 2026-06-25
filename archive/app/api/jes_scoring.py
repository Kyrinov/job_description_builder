"""
app/api/jes_scoring.py — FastAPI router for JES scoring (Phase 7) +
per-factor recovery paths (Phase 08.1).

Routes:
    POST /api/jes/score — run per-factor JES scoring for a confirmed WorkDescription.
      Requires stage='jd_drafted'. Returns HTMX partial or JSON.
    POST /api/jes/retry/{wd_id}/{factor_name} — re-run the LLM for one factor
      (Phase 08.1). Returns HTMX factor card or JSON.
    POST /api/jes/override/{wd_id}/{factor_name} — advisor sets level/points/rationale
      (Phase 08.1). Returns HTMX factor card (on success) or override form (on
      validation error).
    GET /api/jes/override/{wd_id}/{factor_name}/form — render the override form
      partial (Phase 08.1).

Direct analog: app/api/jd_generation.py
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.jes_service import (
    override_jes_factor,
    retry_jes_factor,
    score_jes,
)

router = APIRouter()

_templates_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"
)
templates = Jinja2Templates(directory=_templates_dir)


def _map_value_error(exc: ValueError) -> HTTPException:
    """Map a service ValueError to a 404 (not found) or 422 (other) HTTPException.

    Mirrors the mapping in score_jes_route. Used by retry and override routes.
    """
    msg = str(exc)
    if "not found" in msg:
        return HTTPException(status_code=404, detail=msg)
    return HTTPException(status_code=422, detail=msg)


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
        raise _map_value_error(exc)

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


@router.post("/api/jes/retry/{wd_id}/{factor_name}")
async def retry_jes_factor_route(
    request: Request,
    wd_id: str,
    factor_name: str,
):
    """Re-run the LLM scoring call for a single JES factor.

    Requires stage='jes_scored'. Returns the updated single-card partial
    (HTMX) or JSON dict (non-HTMX).

    Error mapping:
        ValueError("not found") → 404
        ValueError("Retry failed...") → 422 (LLM still failing)
        ValueError(other)       → 422

    On LLM failure the old score is preserved in the WD (the service does not
    lose progress); the route surfaces the failure reason as 422.
    """
    try:
        result = await retry_jes_factor(
            wd_id=wd_id, factor_name=factor_name, db_path=settings.db_path
        )
    except ValueError as exc:
        raise _map_value_error(exc)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/jes_factor.html",
            {"request": request, "score": result["score"], "wd_id": wd_id},
        )
    return {
        "wd_id": result["wd_id"],
        "factor_name": result["factor_name"],
        "level": result["level"],
        "points": result["points"],
        "jes_total_points": result["jes_total_points"],
    }


@router.post("/api/jes/override/{wd_id}/{factor_name}")
async def override_jes_factor_route(
    request: Request,
    wd_id: str,
    factor_name: str,
    level: int = Form(...),
    points: str = Form(""),
    rationale: str = Form(...),
):
    """Advisor manually sets level/points/rationale for one JES factor.

    Requires stage='jes_scored'. On success returns the updated single-card
    partial (HTMX) or JSON. On validation error (e.g. rationale too short),
    re-renders the override form partial with the error inline.

    Server-side validation: level must be 1..4; rationale must be >= 10 chars
    (enforced by the service). Points is optional — empty string is mapped to
    None to support effort factors with no numeric scale.
    """
    # 1-4 range check (the service enforces level >= 1; the route enforces
    # the upper bound so the form can stay at 1-4 in the HTML)
    if level < 1 or level > 4:
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "partials/jes_override_form.html",
                {
                    "request": request,
                    "wd_id": wd_id,
                    "factor_name": factor_name,
                    "default_level": level,
                    "default_points": points,
                    "error": "Level must be 1–4.",
                },
                status_code=422,
            )
        raise HTTPException(status_code=422, detail="Level must be 1–4.")

    parsed_points: Optional[int]
    if points == "" or points is None:
        parsed_points = None
    else:
        try:
            parsed_points = int(points)
        except (TypeError, ValueError):
            if request.headers.get("HX-Request"):
                return templates.TemplateResponse(
                    "partials/jes_override_form.html",
                    {
                        "request": request,
                        "wd_id": wd_id,
                        "factor_name": factor_name,
                        "default_level": level,
                        "default_points": points,
                        "error": "Points must be a non-negative integer (or blank).",
                    },
                    status_code=422,
                )
            raise HTTPException(
                status_code=422, detail="Points must be a non-negative integer (or blank)."
            )

    try:
        result = override_jes_factor(
            wd_id=wd_id,
            factor_name=factor_name,
            level=level,
            points=parsed_points,
            rationale=rationale,
            db_path=settings.db_path,
        )
    except ValueError as exc:
        msg = str(exc)
        # Validation errors (length / level / points range) re-render the
        # form partial with the error inline; lookup errors (not found,
        # wrong stage) return 404/422 as JSON.
        if (
            "10 characters" in msg
            or "level must be" in msg
            or "rationale must be" in msg
        ):
            if request.headers.get("HX-Request"):
                return templates.TemplateResponse(
                    "partials/jes_override_form.html",
                    {
                        "request": request,
                        "wd_id": wd_id,
                        "factor_name": factor_name,
                        "default_level": level,
                        "default_points": parsed_points,
                        "error": msg,
                    },
                    status_code=422,
                )
            raise HTTPException(status_code=422, detail=msg)
        raise _map_value_error(exc)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/jes_factor.html",
            {"request": request, "score": result["score"], "wd_id": wd_id},
        )
    return {
        "wd_id": result["wd_id"],
        "factor_name": result["factor_name"],
        "jes_total_points": result["jes_total_points"],
    }


@router.get("/api/jes/override/{wd_id}/{factor_name}/form")
async def override_form_route(
    request: Request,
    wd_id: str,
    factor_name: str,
):
    """Render the override form partial.

    No service call — just a template render. The user clicked the "Override"
    button on a failed factor card, and this returns the form to fill in.
    """
    return templates.TemplateResponse(
        "partials/jes_override_form.html",
        {"request": request, "wd_id": wd_id, "factor_name": factor_name},
    )
