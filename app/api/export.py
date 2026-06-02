"""
app/api/export.py — FastAPI router for DOCX export (Phase 8).

GET /export/{wd_id}/docx — generate and stream DOCX for a completed WorkDescription.
  Requires stage='jes_scored'. Returns file download (non-HTMX) or HTMX partial.
GET /export/{wd_id}/pdf  — returns 501 Not Implemented (WeasyPrint ARM64 deferred, D-08).
Direct analog: app/api/jes_scoring.py
"""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.export_service import generate_export

router = APIRouter()

_templates_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"
)
templates = Jinja2Templates(directory=_templates_dir)


@router.get("/export/{wd_id}/docx")
async def export_docx(request: Request, wd_id: str):
    """Generate and stream the DOCX export for a completed WorkDescription.

    Requires stage='jes_scored' and a complete JES sheet (no level=-1 / points=None
    sentinels). On success, streams the file as a download (non-HTMX) or renders
    an HTMX partial (HX-Request) showing export metadata.

    Error mapping:
        ValueError("not found")           -> 404
        ValueError(export blocked / wrong stage) -> 422
    """
    try:
        result = await generate_export(wd_id=wd_id, db_path=settings.db_path)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=422, detail=msg)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/export_result.html",
            {
                "request": request,
                "wd_id": wd_id,
                "export_hash": result["export_hash"],
                "filename": result["filename"],
            },
        )

    return Response(
        content=result["file_bytes"],
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'},
    )


@router.get("/export/{wd_id}/pdf")
async def export_pdf(request: Request, wd_id: str):
    """PDF export stub — returns 501 Not Implemented (D-08).

    WeasyPrint + Pango/Cairo ARM64 compatibility on Jane (Jetson AGX Orin) is
    not yet verified. The advisor is directed to download the DOCX and convert
    locally until the dependency stack is confirmed.
    """
    raise HTTPException(
        status_code=501,
        detail="PDF export is not yet available — download DOCX and convert locally.",
    )
