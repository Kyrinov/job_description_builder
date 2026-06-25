"""
app/api/export.py — Phase 20 export endpoints.

Routes:
  POST /api/wd/{wd_id}/export/docx    → TBS Work Description DOCX (EXP-01, API-08)
  POST /api/wd/{wd_id}/export/poster  → Job Poster DOCX (EXP-02, API-09)
  POST /api/wd/{wd_id}/export/pdf     → PDF via WeasyPrint with ARM64 gate (EXP-03)
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
from datetime import date

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.config import get_settings
from app.db import get_connection
from app.models.work_description import WorkDescription
from app.services.classification_gate import require_og_confirmed
from app.services.export_service import (
    _build_v2_manifest,
    _og_code_from,
    _og_level_str,
    _probe_weasyprint,
    _slugify_title,
    build_seven_elements,
    generate_poster_docx,
    generate_wd_docx,
)
from app.services.jes_service import score_jes_v2

router = APIRouter()

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

# Manager-track export placeholder (SEXP-04 SC-4 — JSON/CSV routes deliberately
# bypass the require_og_confirmed 409 gate so a manager WD without confirmed_og
# still exports. Classification metadata is replaced with this string instead
# of null, so analytics consumers see "[ADVISOR TO COMPLETE]" rather than
# silently inferring "no classification".
_MANAGER_PLACEHOLDER = "[ADVISOR TO COMPLETE]"


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

    # WR-01: mirror DOCX self-healing so PDF also has JES scores when available.
    # WR-02: fall back to record.duties for scoring (same as _build_wd_context).
    _has_duties = bool(wd.duties) or bool((wd.record or {}).get("duties"))
    _all_floor = (
        bool(wd.jes_scores)
        and all(s.get("degree", 0) <= 1 for s in wd.jes_scores)
        and _has_duties
    )
    if wd.jes_total_points is None or _all_floor:
        og_code_heal = _og_code_from(wd)
        og_level_heal = wd.og_level or 0
        duties_heal = [d.text for d in (wd.duties or [])]
        if not duties_heal:
            duties_heal = [
                d.get("text", "") for d in ((wd.record or {}).get("duties") or [])
            ]
        if og_code_heal and og_level_heal:
            try:
                await score_jes_v2(
                    wd_id=wd_id,
                    og_code=og_code_heal,
                    og_level=og_level_heal,
                    duties=duties_heal,
                    db_path=settings.db_path,
                )
            except Exception:
                pass  # proceed with empty JES section rather than blocking
        wd = _load_wd(wd_id, settings.db_path)

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


# ---------------------------------------------------------------------------
# Phase 29 — Structured Export (SEXP-01 JSON, SEXP-02 CSV)
# ---------------------------------------------------------------------------
# These two routes deliberately OMIT the require_og_confirmed(wd) gate so a
# manager-track WD (wd_type == 'manager', no confirmed_og) can still export.
# Classification metadata is rendered as "[ADVISOR TO COMPLETE]" instead of
# null so workforce analytics can detect the gap explicitly (SEXP-04 SC-4).


def _build_json_export(wd) -> dict:
    """Build 7-element analytics JSON for SEXP-01.

    Returns the 7 Part 2 element values plus per-element status, the
    complete_count/total progress pair, classification metadata (og_level /
    jes_total_points / og_name) with [ADVISOR TO COMPLETE] fallback for
    manager-track WDs, the deduplicated source provenance list from
    _build_v2_manifest(wd), and an export_date stamp for downstream
    analytics partitioning.
    """
    seven = build_seven_elements(wd)
    elements = {e["key"]: e for e in seven["elements"]}
    og_code = _og_code_from(wd)
    og_level_str = _og_level_str(og_code, wd.og_level or 0) if og_code else None

    return {
        "organizational_context": elements["organizational_context"]["value"] or None,
        "client_service_results": elements["client_service_results"]["value"] or None,
        "key_activities": [
            {"text": d.text, "noc_code": d.provenance_noc_code or None}
            for d in (elements["key_activities"]["value"] or [])
        ],
        "skills": None,
        "effort": None,
        "responsibility": elements["responsibility"]["value"] or None,
        "working_conditions": None,
        "element_status": {e["key"]: e["status"] for e in seven["elements"]},
        "complete_count": seven["complete_count"],
        "total": seven["total"],
        "classification": {
            "og_level": og_level_str or _MANAGER_PLACEHOLDER,
            "jes_total_points": wd.jes_total_points if wd.jes_total_points is not None else _MANAGER_PLACEHOLDER,
            "og_name": (wd.confirmed_og.get("og_name", "") if isinstance(wd.confirmed_og, dict) else "") or _MANAGER_PLACEHOLDER,
        },
        "provenance": _build_v2_manifest(wd),
        "wd_type": getattr(wd, "wd_type", "advisor"),
        "export_date": str(date.today()),
    }


def _build_csv_export(wd) -> bytes:
    """Build UTF-8-with-BOM CSV; one row per key activity (duty). SEXP-02.

    Each row carries the duty text + NOC code plus a copy of every scalar
    context (org_context, csr, status enums for the elements we don't
    unpack, classification metadata). Wraps with encode("utf-8-sig") so the
    leading \\xef\\xbb\\xbf BOM byte sequence is present and Excel
    auto-detects UTF-8 on open.
    """
    seven = build_seven_elements(wd)
    elements = {e["key"]: e for e in seven["elements"]}

    buf = io.StringIO()
    fieldnames = [
        "duty_text", "duty_noc_code",
        "organizational_context", "client_service_results",
        "skills_status", "effort_status", "responsibility",
        "working_conditions_status",
        "og_level", "jes_total_points", "complete_count", "total",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()

    og_code = _og_code_from(wd)
    og_level_str = _og_level_str(og_code, wd.og_level or 0) if og_code else None
    scalar = {
        "organizational_context": elements["organizational_context"]["value"] or _MANAGER_PLACEHOLDER,
        "client_service_results": elements["client_service_results"]["value"] or _MANAGER_PLACEHOLDER,
        "skills_status": elements["skills"]["status"],
        "effort_status": elements["effort"]["status"],
        "responsibility": elements["responsibility"]["value"] or _MANAGER_PLACEHOLDER,
        "working_conditions_status": elements["working_conditions"]["status"],
        "og_level": og_level_str or _MANAGER_PLACEHOLDER,
        "jes_total_points": str(wd.jes_total_points) if wd.jes_total_points is not None else _MANAGER_PLACEHOLDER,
        "complete_count": seven["complete_count"],
        "total": seven["total"],
    }
    duties = elements["key_activities"]["value"] or []
    if duties:
        for d in duties:
            # d is a DraftDuty Pydantic model — use .text and .provenance_noc_code (attribute access, NOT dict subscript)
            writer.writerow({**scalar, "duty_text": d.text, "duty_noc_code": d.provenance_noc_code or ""})
    else:
        writer.writerow({**scalar, "duty_text": _MANAGER_PLACEHOLDER, "duty_noc_code": ""})

    # encode("utf-8-sig") prepends the BOM byte sequence (\xef\xbb\xbf) — Excel auto-detects UTF-8
    return buf.getvalue().encode("utf-8-sig")


@router.post("/wd/{wd_id}/export/json")
async def export_wd_json(wd_id: str) -> Response:
    """SEXP-01 — Export 7-element analytics JSON.

    Manager-track WDs (wd_type='manager', no confirmed_og) deliberately
    skip the require_og_confirmed 409 gate so the export still succeeds;
    the classification block in the JSON carries [ADVISOR TO COMPLETE]
    placeholders instead.
    """
    settings = get_settings()
    wd = _load_wd(wd_id, settings.db_path)
    # NO require_og_confirmed — manager-track WDs must succeed (SEXP-04 success criterion)
    payload = _build_json_export(wd)
    safe_title = _slugify_title((wd.record or {}).get("title", ""), "work-description")
    filename = f"{safe_title}.json"
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/wd/{wd_id}/export/csv")
async def export_wd_csv(wd_id: str) -> Response:
    """SEXP-02 — Export 7-element analytics CSV (UTF-8-BOM for Excel).

    Manager-track WDs deliberately skip the require_og_confirmed 409 gate
    so a manager WD without confirmed_og still exports (SEXP-04 SC-4).
    """
    settings = get_settings()
    wd = _load_wd(wd_id, settings.db_path)
    # NO require_og_confirmed — manager-track WDs must succeed (SEXP-04 success criterion)
    csv_bytes = _build_csv_export(wd)
    safe_title = _slugify_title((wd.record or {}).get("title", ""), "work-description")
    filename = f"{safe_title}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
