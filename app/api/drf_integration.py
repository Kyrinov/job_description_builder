"""
app/api/drf_integration.py — FastAPI router for DND DRF linkage operations (Phase 9).

Routes:
    GET  /api/drf-links/{wd_id}        — return DRF candidate linkages (HTMX or JSON)
    POST /api/drf-links/{wd_id}/confirm — store confirmed DRF linkages on the WD

Removed in Plan 09-04 (revised inline design):
    POST /api/drf-links/{wd_id}/flag-dnd — toggling is_dnd_position from the
    UI is no longer supported. The prototype is DND-only and is_dnd_position
    is set to True on every new WD in app/api/noc_mapping.py — there is no
    UI affordance to toggle it. The route and its partials/drf_flag.html
    target are gone.

Direct analog: app/api/jes_scoring.py (HTMX dual-path, _map_value_error, Form(...))
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.drf_service import confirm_drf_linkages, get_drf_candidates

router = APIRouter()

_templates_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"
)
templates = Jinja2Templates(directory=_templates_dir)


def _map_value_error(exc: ValueError) -> HTTPException:
    """Map a service ValueError to a 404 (not found) or 422 (other) HTTPException.

    Mirrors the mapping in app/api/jes_scoring.py — service raises
    ValueError("...not found") for missing WD; everything else is 422.
    """
    msg = str(exc)
    if "not found" in msg:
        return HTTPException(status_code=404, detail=msg)
    return HTTPException(status_code=422, detail=msg)


@router.get("/api/drf-links/{wd_id}")
async def get_drf_links(request: Request, wd_id: str):
    """Return DRF candidate linkages for a WorkDescription's duties.

    IDOR guard: wd_id is a UUID string; non-existent IDs return 404 via
    _map_value_error. Non-DND positions return 200 with an empty candidates
    list (no error). HTMX (HX-Request header present) returns the
    partials/drf_candidates.html template; non-HTMX returns the result dict
    as JSON.
    """
    try:
        result = await get_drf_candidates(wd_id=wd_id, db_path=settings.db_path)
    except ValueError as exc:
        raise _map_value_error(exc)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/drf_candidates.html",
            {
                "request": request,
                "wd_id": result["wd_id"],
                "is_dnd_position": result["is_dnd_position"],
                "candidates": result["candidates"],
            },
        )
    return result


@router.post("/api/drf-links/{wd_id}/confirm")
async def confirm_drf_links(
    request: Request,
    wd_id: str,
    row_ids: str = Form(...),
):
    """Confirm selected DRF linkages for a WorkDescription.

    row_ids: comma-separated string of drf_rows integer IDs (e.g. "3,7,12").
    The service does a SELECT-by-PK for each id; unknown ids are silently
    skipped (T-09-06 mitigation) — never raises for unknown row_ids.

    IDOR guard: wd_id is validated against DB; missing WD returns 404.
    HTMX (HX-Request header present) returns partials/drf_confirmed.html;
    non-HTMX returns the result dict as JSON.
    """
    parsed_ids: list[int] = []
    for token in row_ids.split(","):
        token = token.strip()
        if token.isdigit():
            parsed_ids.append(int(token))

    try:
        result = await confirm_drf_linkages(
            wd_id=wd_id, row_ids=parsed_ids, db_path=settings.db_path
        )
    except ValueError as exc:
        raise _map_value_error(exc)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/drf_confirmed.html",
            {
                "request": request,
                "wd_id": result["wd_id"],
                "confirmed_count": result["confirmed_count"],
                "drf_linkages": result["drf_linkages"],
            },
        )
    return result
