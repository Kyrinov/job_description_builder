"""
app/services/export_service.py — DOCX/Poster export pipeline (v2.0).

Public API:
    async generate_wd_docx(wd_id, db_path) -> dict
    async generate_poster_docx(wd_id, db_path) -> dict
    def _probe_weasyprint() -> bool        # runtime probe for PDF endpoint

Architecture (Phase 20):
    - DOCX/poster render via docxtpl, wrapped in asyncio.to_thread so the
      FastAPI event loop is not blocked by the synchronous python-docx work.
    - Version manifest (D-07 / EXP-01) deduplicates every source by
      (source_type, source_id, source_version). Walks v2.0 flat fields on
      DraftDuty (provenance_noc_code, advisor) — NOT the v1.0 ProvenanceTag
      sub-object, which does not exist in v2.0.
    - Amendment appendix (AMEND-02) re-queries audit_log for the latest note
      per section, ordered by id DESC.
    - WeasyPrint probe (EXP-03) is cached module-side so the runtime cost of
      importing + smoke-rendering the library is paid once.
    - og_level string is always zero-padded: f"{og_code}-{int(og_level):02d}".
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import os
import re
from datetime import date

from docxtpl import DocxTemplate

from app.db import get_connection
from app.models.draft_duty import DraftDuty
from app.models.work_description import WorkDescription

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# Mapping of non-EC OG codes to their published JES standard name. Used in
# the version manifest to credit the correct authoritative source for the
# classification. "FI" is Financial Institutions (CT JES 2023 is the
# published standard for that group).
NON_EC_STANDARD_NAMES: dict[str, str] = {
    "FI": "CT JES 2023",
    "IT": "IT JES",
    "AS": "UCS",
    "EN": "EN JES",
}

# Runtime probe cache for WeasyPrint. Set to True or False after the first
# call to _probe_weasyprint(); None means "not yet probed". See EXP-03.
_weasyprint_available: bool | None = None


# ---------------------------------------------------------------------------
# WeasyPrint probe (EXP-03)
# ---------------------------------------------------------------------------


def _probe_weasyprint() -> bool:
    """Return True if WeasyPrint is installed AND its system libs load.

    Caches the result in the module-level _weasyprint_available variable so
    the probe cost is paid at most once per process. The probe runs an
    actual write_pdf() call because cffi may import cleanly but fail at
    render time (Pitfall 5 in RESEARCH.md).
    """
    global _weasyprint_available
    if _weasyprint_available is not None:
        return _weasyprint_available
    try:
        import weasyprint as _wp
        _wp.HTML(string="<p>x</p>").write_pdf()
        _weasyprint_available = True
    except Exception as exc:
        logger.warning("WeasyPrint probe failed: %s", exc)
        _weasyprint_available = False
    return _weasyprint_available


# ---------------------------------------------------------------------------
# Template path resolution
# ---------------------------------------------------------------------------


def _resolve_template_path(template_name: str) -> str:
    """Return absolute path to app/templates/{template_name}.

    This module lives at app/services/export_service.py; going up two
    directories lands in app/, then into templates/{template_name}.
    """
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "templates",
        template_name,
    )


# ---------------------------------------------------------------------------
# Amendment query (AMEND-02)
# ---------------------------------------------------------------------------


def _get_amendments(con, wd_id: str) -> list[dict]:
    """Return the latest manager-amendment note per section, newest first.

    Mirrors the amendments.py GET pattern. ORDER BY id DESC ensures the
    first occurrence per section is the most recent. Returns a list of
    {section, comment, created_at} dicts.
    """
    rows = con.execute(
        "SELECT detail, created_at FROM audit_log "
        "WHERE wd_id = ? AND event = 'manager_amendment' "
        "ORDER BY id DESC",
        (wd_id,),
    ).fetchall()
    seen: set[str] = set()
    notes: list[dict] = []
    for row in rows:
        detail = json.loads(row["detail"])
        section = detail.get("section")
        if section and section not in seen:
            seen.add(section)
            notes.append(
                {
                    "section": section,
                    "comment": detail.get("comment", ""),
                    "created_at": row["created_at"],
                }
            )
    return notes


# ---------------------------------------------------------------------------
# Version manifest (EXP-01, v2.0 flat-field adaptation of D-07)
# ---------------------------------------------------------------------------


def _og_code_from(wd: WorkDescription) -> str:
    """Extract og_code from confirmed_og, tolerating both string and dict shapes.

    WorkDescription.confirmed_og is Optional[Union[str, dict]] — the SPA's
    og_confirm step persists a full candidate dict, but earlier sessions may
    have persisted a bare code string. Every consumer of confirmed_og.og_code
    must go through this helper to avoid AttributeError on string shape.
    """
    if isinstance(wd.confirmed_og, dict):
        return wd.confirmed_og.get("og_code", "")
    return wd.confirmed_og or ""


def _build_v2_manifest(wd: WorkDescription) -> list[dict]:
    """Return a deduplicated list of every source used in this WD.

    Walks v2.0 flat fields:
        - wd.duties[*].provenance_noc_code   -> NOC entries
        - wd.jes_total_points is not None    -> JES standard entry
        - wd.confirmed_og                    -> TBS OG Definitions entry
        - wd.qualification                   -> TBS Qualification Standard entry

    First-seen order is preserved. Each entry has the same shape that the
    wd_template.docx {%p for entry in manifest %} loop expects.
    """
    seen: set[tuple] = set()
    manifest: list[dict] = []

    def _add(source_type: str, source_id: str, source_version: str) -> None:
        key = (source_type, source_id, source_version)
        if key in seen:
            return
        seen.add(key)
        manifest.append(
            {
                "source_type": source_type,
                "source_id": source_id,
                "source_version": source_version,
                "retrieved_date": str(date.today()),
            }
        )

    # NOC duties — emit one NOC 2021 entry per unique NOC code cited
    for d in wd.duties or []:
        if d.provenance_noc_code:
            _add("NOC", d.provenance_noc_code, "NOC 2021")

    # JES standard — depends on the confirmed OG group
    if wd.jes_total_points is not None:
        og_code = _og_code_from(wd)
        if og_code == "EC":
            _add("JES", "EC JES 2017", "EC JES 2017")
        elif og_code:
            _add("JES", og_code, NON_EC_STANDARD_NAMES.get(og_code, "JES"))

    # TBS OG definitions
    if wd.confirmed_og:
        _add("OG", "TBS OG Definitions", "TBS OG Definitions 2024")

    # TBS Qualification Standard
    if wd.qualification:
        _add("QUAL", "TBS Qualification Standard", "TBS Qualification Standard 2024")

    return manifest


# ---------------------------------------------------------------------------
# WD context builder (D-04 / D-05 — v2.0 flat-field translation)
# ---------------------------------------------------------------------------


def _build_organizational_context_text(wd: WorkDescription) -> str:
    """Compose the organizational-context paragraph for the WD template.

    Mirrors the buildOverview() logic in document.jsx — lowercased sentence
    of the form:
        "Located within {branch}, and reporting to the {supervisor}, the
        {title} {summary}."
    Falls back to sensible defaults when fields are missing.
    """
    record = wd.record or {}
    branch = (record.get("branch") or "").strip()
    supervisor = (record.get("reports") or "").strip()
    title = (record.get("title") or "").strip() or "incumbent"
    summary = (record.get("summary") or "performs duties as assigned").strip()
    # Lowercase the first character so it slots into a sentence naturally.
    summary = summary[0].lower() + summary[1:] if summary else "performs duties as assigned"

    if branch and supervisor:
        return (
            f"Located within {branch}, and reporting to the {supervisor}, "
            f"the {title} {summary}."
        )
    if branch:
        return f"Located within {branch}, the {title} {summary}."
    if supervisor:
        return f"Reporting to the {supervisor}, the {title} {summary}."
    return f"The {title} {summary}."


def _build_wd_context(wd: WorkDescription, amendments: list[dict]) -> dict:
    """Build the docxtpl context dict for the TBS Work Description template.

    Keys are exactly the variables declared in wd_template.docx. The
    {%p for %} loops receive lists of dicts; scalars are strings.
    """
    record = wd.record or {}
    og_code = _og_code_from(wd)
    og_level_int = wd.og_level or 0
    og_level_str = f"{og_code}-{int(og_level_int):02d}" if og_code else ""

    # Qualification — fall back to record.quals when root qualification not yet persisted
    if wd.qualification is not None:
        education_text = wd.qualification.education
        experience_text = wd.qualification.experience
    else:
        record_quals = record.get("quals") or {}
        education_text = record_quals.get("education", "")
        experience_text = record_quals.get("experience", "")

    # Duties — fall back to record.duties when root duties not yet persisted
    root_duties = wd.duties or []
    if not root_duties:
        root_duties = [DraftDuty(**d) for d in (record.get("duties") or [])]

    return {
        "position_title": record.get("title", ""),
        "position_number": record.get("position_number", ""),
        "og_level": og_level_str,
        "supervisor_title": record.get("reports", ""),
        "supervisor_position_number": "",
        "review_date": str(date.today()),
        "organizational_context_text": _build_organizational_context_text(wd),
        "organizational_context_source": "Drafted from answers",
        "duties": [
            {
                "text": d.text,
                "noc_code": d.provenance_noc_code or "",
                "is_advisor": bool(d.advisor),
            }
            for d in root_duties
        ],
        "jes_scores": wd.jes_scores or [],
        "jes_total_points": wd.jes_total_points or 0,
        "manifest": _build_v2_manifest(wd),
        "amendments": amendments,
        "education_text": education_text,
        "experience_text": experience_text,
    }


# ---------------------------------------------------------------------------
# Poster context builder (EXP-02)
# ---------------------------------------------------------------------------


def _build_poster_context(wd: WorkDescription) -> dict:
    """Build the docxtpl context dict for the bilingual job-poster template.

    Top 5 duties are included; bilingual_title_fr is a placeholder (empty
    string) per REQUIREMENTS.md — French translation is out of scope.
    """
    record = wd.record or {}
    og_code = _og_code_from(wd)
    og_level_int = wd.og_level or 0
    og_level_str = f"{og_code}-{int(og_level_int):02d}" if og_code else ""

    if wd.qualification is not None:
        education_text = wd.qualification.education
        experience_text = wd.qualification.experience
    else:
        education_text = ""
        experience_text = ""

    return {
        "position_title": record.get("title", ""),
        "og_level": og_level_str,
        "og_name": (wd.confirmed_og.get("og_name", "") if isinstance(wd.confirmed_og, dict) else ""),
        "branch": record.get("branch", ""),
        "education": education_text,
        "experience": experience_text,
        "duties": [{"text": d.text} for d in (wd.duties or [])[:5]],
        "bilingual_title_fr": "",
    }


# ---------------------------------------------------------------------------
# DOCX render (D-05 / D-06)
# ---------------------------------------------------------------------------


async def _render_docx(template_path: str, context: dict) -> bytes:
    """Render a docxtpl template in a worker thread.

    asyncio.to_thread keeps the FastAPI event loop responsive during the
    CPU-bound render. DocxTemplate.render is synchronous; we wrap it
    ourselves to match the v1.0 pattern.
    """
    def _render() -> bytes:
        doc = DocxTemplate(template_path)
        doc.render(context)
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    return await asyncio.to_thread(_render)


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------


def _slugify_title(title: str, default: str) -> str:
    """Lowercase + replace spaces with dashes; strip non-alphanumeric chars.

    Falls back to `default` when the resulting slug is empty.
    """
    if not title:
        return default
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or default


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


async def generate_wd_docx(wd_id: str, db_path: str) -> dict:
    """Render the TBS Work Description DOCX for a completed WD.

    Loads the WD, queries amendments, builds the docxtpl context, renders
    the template, computes a SHA-256 export hash, and returns the bytes
    plus a downloadable filename.

    Returns:
        {wd_id, file_bytes, filename, export_hash}

    Raises:
        ValueError: when the WD is missing, or the render produced empty
            bytes (D-03 guard — never return blank documents).
    """
    con = get_connection(db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"WorkDescription {wd_id!r} not found")
        wd = WorkDescription.model_validate_json(row["data"])

        amendments = _get_amendments(con, wd_id)
        context = _build_wd_context(wd, amendments)
        template_path = _resolve_template_path("wd_template.docx")
        file_bytes = await _render_docx(template_path, context)
    finally:
        con.close()

    if not file_bytes:
        raise ValueError("Export produced empty document — aborting.")

    export_hash = hashlib.sha256(file_bytes).hexdigest()
    safe_title = _slugify_title(
        (wd.record or {}).get("title", ""), "work-description"
    )
    return {
        "wd_id": wd_id,
        "file_bytes": file_bytes,
        "filename": f"{safe_title}-work-description.docx",
        "export_hash": export_hash,
    }


async def generate_poster_docx(wd_id: str, db_path: str) -> dict:
    """Render the bilingual job-poster DOCX for a completed WD.

    Same shape as generate_wd_docx() but uses the poster template and the
    poster context (top 5 duties, bilingual placeholder).
    """
    con = get_connection(db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"WorkDescription {wd_id!r} not found")
        wd = WorkDescription.model_validate_json(row["data"])

        context = _build_poster_context(wd)
        template_path = _resolve_template_path("poster_template.docx")
        file_bytes = await _render_docx(template_path, context)
    finally:
        con.close()

    if not file_bytes:
        raise ValueError("Export produced empty document — aborting.")

    export_hash = hashlib.sha256(file_bytes).hexdigest()
    safe_title = _slugify_title(
        (wd.record or {}).get("title", ""), "work-description"
    )
    return {
        "wd_id": wd_id,
        "file_bytes": file_bytes,
        "filename": f"{safe_title}-job-poster.docx",
        "export_hash": export_hash,
    }
