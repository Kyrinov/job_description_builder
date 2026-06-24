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
from app.data.constants import (
    EC_JES_ELEMENTS,
    JES_FACTORS_BY_GROUP,
    NON_EC_STANDARD_NAMES,
)
from app.models.draft_duty import DraftDuty
from app.models.work_description import WorkDescription

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# Runtime probe cache for WeasyPrint. Set to True or False after the first
# call to _probe_weasyprint(); None means "not yet probed". See EXP-03.
_weasyprint_available: bool | None = None

# Accessible-template placeholder (Phase 25, ACC-02 fallback). Used for any
# Part 1 / Part 2 scalar that has no authoritative source on the WD, and for
# the Effort / Working-Conditions sections when the OG group has no factors
# in that category. Locked decision 2 (RESEARCH.md): all 17 Part 1 fields
# render even when the WD does not yet carry a value, so the advisor can
# hand-fill them after print.
_ADVISOR_PLACEHOLDER = "[To be completed by advisor]"


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
    wd_accessible_template.docx {%p for entry in manifest %} loop expects.
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

    # SJD provenance entry (Phase 22 — SJD-02)
    if wd.sjd_source:
        sjd_num = wd.sjd_source.get("sjd_number", "")
        if sjd_num:
            _add("SJD", sjd_num, "DND SJD Library")

    return manifest


def _factor_category_map() -> dict[str, str]:
    """Merge EC_JES_ELEMENTS + every JES_FACTORS_BY_GROUP entry into factor_name -> category.

    Source of truth for factor categories is constants.py. Never trust
    wd.jes_scores[i]["category"] directly — the EC scoring path
    (_build_factor_score in jes_service.py) does NOT copy the category key
    onto the persisted score dict; only the non-EC point-rating path does.
    Reading wd.jes_scores[i].get("category") on an EC WD would return
    None/empty and silently mis-bucket every EC factor.

    Category values are exactly: "Effort", "Conditions", "Skill",
    "Responsibility". Keys are the canonical factor names from
    EC_JES_ELEMENTS and JES_FACTORS_BY_GROUP (e.g. "Physical effort",
    "Working conditions", "Risk to health"). The dict is built fresh on
    every call — this is module-cost-cheap (two short list comprehensions)
    and avoids any cross-test cache invalidation when the test suite
    monkeypatches constants.
    """
    mapping: dict[str, str] = {}
    for el in EC_JES_ELEMENTS:
        mapping[el["name"]] = el["category"]
    for group_factors in JES_FACTORS_BY_GROUP.values():
        for f in group_factors:
            mapping[f["name"]] = f.get("category", "")
    return mapping


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
    """Build the docxtpl context dict for the Accessible Work Description template.

    Phase 25 (ACC-01..04): keys are exactly the 29 variables declared in
    wd_accessible_template.docx. The {%p for %} / {%tr for %} loops receive
    lists of dicts; scalars are strings.

    Effort and Working-Conditions factors are bucketed via _factor_category_map()
    — never via score.get("category") on the persisted dict, because the EC
    scoring path does not copy the category key. Groups with no factors in a
    category (e.g. MT — Skill/Responsibility only; AS, NU, PS, … — level
    description with empty jes_scores) fall back to the _ADVISOR_PLACEHOLDER
    string for the corresponding placeholder variable.

    Per LOCKED DECISION 2, all 17 Part 1 fields render even when the WD does
    not yet carry a value; the 6 with no authoritative source (job_code,
    office_code, language/linguistic/communications/security requirements) are
    bound to _ADVISOR_PLACEHOLDER directly. supervisor_classification has no
    WD source and follows the same convention.
    """
    record = wd.record or {}
    og_code = _og_code_from(wd)
    og_level_int = wd.og_level or 0
    og_level_str = _og_level_str(og_code, og_level_int)

    # SW/ED routing-code resolution — replicate jes_service.py score_jes_v2
    # (lines 192-217). The dict keys in JES_FACTORS_BY_GROUP are routing codes
    # (e.g. "SW-SCW", "ED-LAT"), not raw og_codes, so a naive og_code lookup
    # would KeyError or silently mis-classify.
    sub_group = getattr(wd, "confirmed_sub_group", None)
    routing_code = og_code
    if og_code == "SW":
        routing_code = "SW-SCW" if sub_group == "SCW" else "SW-CHA"
    elif og_code == "ED":
        if sub_group == "EDS":
            routing_code = "ED-EDS"
        elif sub_group == "LAT":
            routing_code = "ED-LAT"
        elif sub_group == "EST":
            routing_code = "ED-EST"
        else:
            routing_code = "ED-LAT"

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

    # JES factor bucketing (ACC-02). Derive category from _factor_category_map()
    # — the persisted wd.jes_scores dict may lack a 'category' key (EC path)
    # or have one (point-rating path); the source of truth is constants.py.
    cat_map = _factor_category_map()
    scores = wd.jes_scores or []
    effort_factors = [s for s in scores if cat_map.get(s.get("factor_name", "")) == "Effort"]
    working_conditions_factors = [s for s in scores if cat_map.get(s.get("factor_name", "")) == "Conditions"]

    # Placeholder convention: when a category has no factors, set the
    # corresponding placeholder to _ADVISOR_PLACEHOLDER; when factors are
    # present, set the placeholder to "" so the rendered paragraph is empty
    # and the table fills the section visually.
    effort_placeholder = "" if effort_factors else _ADVISOR_PLACEHOLDER
    wc_placeholder = "" if working_conditions_factors else _ADVISOR_PLACEHOLDER

    # Phase 27 (RESP-03 / R-RESP-03): the Part 2 Responsibility element is
    # driven by the advisor-authored responsibilities_narrative typed
    # field on WorkDescription. When empty, show the advisor placeholder
    # (ROADMAP criterion #2) — NOT JES-derived responsibility factors and
    # NOT a synthesized fallback. Verified safe: no existing test asserted
    # the JES-derived responsibilities_text (only a docstring referenced
    # it as the previous source).
    responsibilities_text = (wd.responsibilities_narrative or "").strip() or _ADVISOR_PLACEHOLDER

    # Client service results — sourced from record.client_service_results
    # (captured by the conversation flow via the Writing Guide question
    # inserted in Phase 23 / WG-03). Falls back to placeholder when blank.
    client_service_results_text = (
        (record.get("client_service_results") or "").strip() or _ADVISOR_PLACEHOLDER
    )

    return {
        # Part 1 — 17-field position-identification table.
        # All scalars use the `or _ADVISOR_PLACEHOLDER` idiom so a blank WD
        # never renders "" or None in the table (docxtpl emits "None" for
        # None and an empty cell for "" — neither is acceptable per ACC-04).
        "position_number": record.get("position_number") or _ADVISOR_PLACEHOLDER,
        "position_title": record.get("title") or _ADVISOR_PLACEHOLDER,
        "og_level": og_level_str or _ADVISOR_PLACEHOLDER,
        "review_date": str(date.today()),
        "job_code": _ADVISOR_PLACEHOLDER,
        "noc_code": record.get("noc_code") or _ADVISOR_PLACEHOLDER,
        "department_name": record.get("department_name") or _ADVISOR_PLACEHOLDER,
        "geographic_location": record.get("location") or _ADVISOR_PLACEHOLDER,
        "org_component": record.get("branch") or _ADVISOR_PLACEHOLDER,
        "office_code": _ADVISOR_PLACEHOLDER,
        "language_requirements": _ADVISOR_PLACEHOLDER,
        "linguistic_profile": _ADVISOR_PLACEHOLDER,
        "communications_requirements": _ADVISOR_PLACEHOLDER,
        "security_requirements": _ADVISOR_PLACEHOLDER,
        "supervisor_position_number": record.get("supervisor_position_number") or _ADVISOR_PLACEHOLDER,
        "supervisor_title": record.get("reports") or _ADVISOR_PLACEHOLDER,
        "supervisor_classification": _ADVISOR_PLACEHOLDER,
        # Part 2 — 7 subsections.
        # organizational_context_text: Phase 26 (ORG-03) — prefer the typed
        # wd.org_context field captured by the conversational step over the
        # synthesized fallback. When the advisor has not yet populated
        # org_context, fall back to _build_organizational_context_text(wd)
        # so the section still renders (no {{template leak}}).
        "organizational_context_text": (
            wd.org_context
            if (wd.org_context or "").strip()
            else _build_organizational_context_text(wd)
        ),
        "client_service_results_text": client_service_results_text,
        "duties": [
            {
                "text": d.text,
                "noc_code": d.provenance_noc_code or "",
                "is_advisor": bool(d.advisor),
            }
            for d in root_duties
        ],
        "education_text": education_text or _ADVISOR_PLACEHOLDER,
        "experience_text": experience_text or _ADVISOR_PLACEHOLDER,
        "effort_factors": effort_factors,
        "effort_placeholder": effort_placeholder,
        "responsibilities_text": responsibilities_text,
        "working_conditions_factors": working_conditions_factors,
        "wc_placeholder": wc_placeholder,
        # Version manifest + amendments (same shape as TBS template;
        # _build_v2_manifest is reused verbatim).
        "manifest": _build_v2_manifest(wd),
        "amendments": amendments,
    }


def build_seven_elements(wd: WorkDescription) -> dict:
    """Single source of truth for the 7 Part 2 elements + per-element status.

    Phase 27 (ELEM-01): Consumed by POST /api/wd/{id}/validate-elements
    (ELEM-01) and, in Phase 29, by the JSON/CSV export routes (SEXP-01/02).

    Reads typed root fields directly — for Organizational Context it reads
    wd.org_context ONLY (never the synthesized fallback from
    _build_organizational_context_text), per ROADMAP criterion #4.
    Responsibility reads the responsibilities_narrative typed field
    (Phase 27 RESP-01) and is never 'not_applicable' (the field is open
    to all positions) per ROADMAP criterion #3.

    Status enum: 'populated' | 'derived' | 'missing'. Effort and Working
    Conditions are 'derived' when wd.jes_total_points is not None,
    'missing' otherwise (R-ELEM-01b).
    """
    record = wd.record or {}

    # Organizational Context — typed root field ONLY (ROADMAP #4).
    # The synthesized fallback _build_organizational_context_text() must
    # NOT influence the audit status; otherwise a WD with record.branch
    # + record.reports would falsely report "populated" even when the
    # advisor skipped the conversational step.
    oc_value = (wd.org_context or "").strip()

    # Client Service Results — stored in record (captured by Phase 23
    # client_service_results conversational step).
    csr_value = (record.get("client_service_results") or "").strip()

    # Key Activities — wd.duties (list). Non-empty list ⇒ populated.
    ka_value = wd.duties or []

    # Skills — qualification education OR experience. Falls back to
    # record.quals when root qualification not yet persisted (mirrors
    # _build_wd_context).
    if wd.qualification is not None:
        skills_present = bool(
            (wd.qualification.education or "").strip()
            or (wd.qualification.experience or "").strip()
        )
    else:
        rq = record.get("quals") or {}
        skills_present = bool(
            (rq.get("education") or "").strip()
            or (rq.get("experience") or "").strip()
        )

    # Effort / Working Conditions — derived from JES total points
    # (R-ELEM-01b). The presence of jes_total_points is the "derived"
    # signal that the JES ran; category-empty groups (e.g. MT) still
    # count as derived when jes_total_points is set.
    jes_present = wd.jes_total_points is not None

    # Responsibility — typed root field (Phase 27 RESP-01). Never
    # 'not_applicable' (R-ELEM-01a / ROADMAP #3).
    resp_value = (wd.responsibilities_narrative or "").strip()

    elements = [
        {
            "key": "organizational_context",
            "label": "Organizational Context",
            "status": "populated" if oc_value else "missing",
            "value": oc_value,
        },
        {
            "key": "client_service_results",
            "label": "Client Service Results",
            "status": "populated" if csr_value else "missing",
            "value": csr_value,
        },
        {
            "key": "key_activities",
            "label": "Key Activities",
            "status": "populated" if ka_value else "missing",
            "value": ka_value,
        },
        {
            "key": "skills",
            "label": "Skills",
            "status": "populated" if skills_present else "missing",
            "value": None,
        },
        {
            "key": "effort",
            "label": "Effort",
            "status": "derived" if jes_present else "missing",
            "value": None,
        },
        {
            "key": "responsibility",
            "label": "Responsibility",
            "status": "populated" if resp_value else "missing",
            "value": resp_value,
        },
        {
            "key": "working_conditions",
            "label": "Working Conditions",
            "status": "derived" if jes_present else "missing",
            "value": None,
        },
    ]
    complete_count = sum(
        1 for e in elements if e["status"] in ("populated", "derived")
    )
    return {"elements": elements, "complete_count": complete_count, "total": 7}


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
    og_level_str = _og_level_str(og_code, og_level_int)

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


def _og_level_str(og_code: str, og_level: int) -> str:
    """Return zero-padded OG level string (e.g. 'EC-04'), or '' when og_code absent."""
    return f"{og_code}-{int(og_level):02d}" if og_code else ""


def _slugify_title(title: str, default: str) -> str:
    """Lowercase + replace spaces with dashes; strip non-alphanumeric chars.

    Falls back to `default` when the resulting slug is empty.
    """
    if not title:
        return default
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or default


def _apply_draft_watermark(file_bytes: bytes) -> bytes:
    """Phase 28 (MGR-03): Insert a prominent DRAFT paragraph at the top of the DOCX.

    Post-processes the rendered DOCX bytes with python-docx: insert a new
    paragraph at index 0 with the text 'DRAFT — PENDING CLASSIFICATION' in
    bold dark-red, centered. Applied only to manager-track exports
    (wd.wd_type == 'manager'). The watermark is intrinsic to manager-track
    exports and cannot be suppressed by the client (T-28-05 mitigation —
    watermark text is a hardcoded constant; no user input reaches it).
    """
    import io
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor

    doc = Document(io.BytesIO(file_bytes))
    # insert_paragraph_before on the first paragraph places the new para at index 0
    new_para = doc.paragraphs[0].insert_paragraph_before("DRAFT — PENDING CLASSIFICATION")
    for run in new_para.runs:
        run.bold = True
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)  # dark red
    new_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


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
        template_path = _resolve_template_path("wd_accessible_template.docx")
        file_bytes = await _render_docx(template_path, context)
        # Phase 28 (MGR-03): DRAFT watermark on manager-track exports. Applied
        # here (inside generate_wd_docx) so the watermark is intrinsic to the
        # wd_type field — no caller can bypass it. getattr() with default
        # "advisor" keeps old WD rows (serialized before this field existed)
        # behaving as advisor (no watermark).
        if getattr(wd, "wd_type", "advisor") == "manager":
            file_bytes = _apply_draft_watermark(file_bytes)
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
