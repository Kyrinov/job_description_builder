"""
app/api/export.py — Phase 20 export endpoints.

Routes:
  POST /api/wd/{wd_id}/export/docx    → TBS Work Description DOCX (EXP-01, API-08)
  POST /api/wd/{wd_id}/export/poster  → Job Poster DOCX (EXP-02, API-09)
  POST /api/wd/{wd_id}/export/pdf     → PDF via WeasyPrint with ARM64 gate (EXP-03)
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.config import get_settings
from app.db import get_connection
from app.models.work_description import WorkDescription
from app.services.classification_gate import require_og_confirmed
from app.services.export_service import (
    _og_code_from,
    _og_level_str,
    _probe_weasyprint,
    _slugify_title,
    generate_poster_docx,
    generate_wd_docx,
)
from app.services.jes_service import score_jes_v2

router = APIRouter()

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _load_wd(wd_id: str, db_path: str) -> WorkDescription:
    """Load WD from SQLite; raise 404 if not found.

    Mirrors the WD load + 404 guard pattern from jes_scoring.py and
    amendments.py — single SELECT in a try/finally connection.
    """
    con = get_connection(db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Work description not found")
        return WorkDescription.model_validate_json(row["data"])
    finally:
        con.close()


@router.post("/wd/{wd_id}/export/docx")
async def export_wd_docx(wd_id: str) -> Response:
    """EXP-01 / API-08 — Export WD as DOCX with provenance citations and version manifest."""
    settings = get_settings()
    wd = _load_wd(wd_id, settings.db_path)
    require_og_confirmed(wd)
    _has_duties = bool(wd.duties) or bool((wd.record or {}).get("duties"))
    _all_floor = (
        bool(wd.jes_scores)
        and all(s.get("degree", 0) <= 1 for s in wd.jes_scores)
        and _has_duties
    )
    if wd.jes_total_points is None or _all_floor:
        og_code = (
            wd.confirmed_og.get("og_code", "")
            if isinstance(wd.confirmed_og, dict)
            else (wd.confirmed_og or "")
        )
        og_level = wd.og_level or 0
        duties = [d.text for d in (wd.duties or [])]
        if og_code and og_level:
            try:
                await score_jes_v2(
                    wd_id=wd_id,
                    og_code=og_code,
                    og_level=og_level,
                    duties=duties,
                    db_path=settings.db_path,
                )
            except Exception:
                pass  # proceed with empty JES section rather than blocking
        wd = _load_wd(wd_id, settings.db_path)
    result = await generate_wd_docx(wd_id=wd_id, db_path=settings.db_path)
    return Response(
        content=result["file_bytes"],
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'},
    )


@router.post("/wd/{wd_id}/export/poster")
async def export_poster(wd_id: str) -> Response:
    """EXP-02 / API-09 — Export job poster DOCX with bilingual headers."""
    settings = get_settings()
    wd = _load_wd(wd_id, settings.db_path)
    require_og_confirmed(wd)
    result = await generate_poster_docx(wd_id=wd_id, db_path=settings.db_path)
    return Response(
        content=result["file_bytes"],
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'},
    )


@router.post("/wd/{wd_id}/export/pdf")
async def export_pdf(wd_id: str) -> Response:
    """EXP-03 — Export PDF via WeasyPrint; returns 501 if unavailable.

    Probe WeasyPrint inside the handler (not at module import) so a missing
    system lib (Pango/Cairo) does not crash the whole app. The runtime
    probe is cached module-side in export_service._weasyprint_available.
    """
    # Import probe — must be inside handler, not at module level
    try:
        import weasyprint  # noqa: F401
    except (ImportError, TypeError):
        raise HTTPException(
            status_code=501,
            detail=(
                "PDF export unavailable — WeasyPrint not installed. "
                "Install with: pip install weasyprint==69.0"
            ),
        )
    if not _probe_weasyprint():
        raise HTTPException(
            status_code=501,
            detail=(
                "PDF export unavailable — ARM64 system libs (Pango/Cairo) not functional. "
                "Download the DOCX export instead."
            ),
        )
    settings = get_settings()
    wd = _load_wd(wd_id, settings.db_path)
    require_og_confirmed(wd)

    # Build HTML representation from WD data — never accept raw HTML from the client
    og_code = _og_code_from(wd)
    og_level_int = wd.og_level or 0
    og_str = _og_level_str(og_code, og_level_int)
    title = (wd.record or {}).get("title", "Work Description")
    # CR-02: html.escape all user-supplied strings before interpolation into
    # the WeasyPrint HTML string. Duty text and title are untrusted WD data
    # — without escaping, a duty like "Configure <Network>" breaks the HTML.
    import html as _html
    safe_title = _html.escape(title)
    safe_og_str = _html.escape(og_str)
    duties_html = "".join(
        f"<li>{_html.escape(d.text)}</li>" for d in (wd.duties or [])
    )
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{safe_title}</title>
<style>body{{font-family:Arial,sans-serif;margin:2cm;}}h1{{font-size:16pt;}}h2{{font-size:13pt;}}li{{margin-bottom:4pt;}}</style>
</head><body>
<h1>{safe_title}</h1>
<p><strong>Classification:</strong> {safe_og_str}</p>
<h2>Summary of Duties</h2><ul>{duties_html}</ul>
</body></html>"""

    import weasyprint as _wp

    def _render_pdf() -> bytes:
        return _wp.HTML(string=html).write_pdf()

    pdf_bytes = await asyncio.to_thread(_render_pdf)
    pdf_filename = _slugify_title(title, "work-description")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{pdf_filename}.pdf"'},
    )
