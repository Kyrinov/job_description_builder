"""
app/api/wd.py — WD CRUD: POST /api/wd, GET /api/wd/{id}, PATCH /api/wd/{id}.

Serialises WorkDescription to JSON in the work_descriptions.data column.
Each step commit from the SPA calls PATCH; first commit calls POST.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional, Union
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.config import get_settings
from app.db import get_connection
from app.models.work_description import WorkDescription

router = APIRouter()


# ---------------------------------------------------------------------------
# SJD seed duties (Phase 22 — SJD-02)
# Duty text sourced from frontend DUTY_SUGGESTIONS (data.jsx) for parity.
# Groups present in SJD_LIBRARY: AS, FI, EC, IT, EN, PE, WP.
# ---------------------------------------------------------------------------
_SJD_DUTY_SUGGESTIONS: dict[str, list[dict]] = {
    "AS": [
        {"plain": "Manage administrative operations",
         "polished": "Plans, coordinates and manages administrative operations, services and support functions in accordance with departmental policies and priorities."},
        {"plain": "Provide advice and guidance to management",
         "polished": "Provides expert advice, options analyses and recommendations to management on administrative programs, policies and procedures."},
        {"plain": "Prepare reports and correspondence",
         "polished": "Prepares reports, briefing materials, correspondence and submissions for management review and decision."},
    ],
    "FI": [
        {"plain": "Develop and manage budgets and forecasts",
         "polished": "Develops, manages and monitors budgets, financial plans and forecasts in accordance with Treasury Board policies and departmental priorities."},
        {"plain": "Prepare financial reports and analyses",
         "polished": "Prepares financial reports, costing analyses, variance explanations and recommendations for senior management and central agencies."},
        {"plain": "Advise on financial management controls",
         "polished": "Advises management on financial management policies, internal controls, expenditure review and compliance with financial authorities."},
    ],
    "EC": [
        {"plain": "Develop and analyze policy options",
         "polished": "Develops, analyzes and interprets policy options, program frameworks and strategic guidance, and assesses their implications for departmental operations."},
        {"plain": "Provide evidence-based advice to management",
         "polished": "Provides expert advice, options analyses and recommendations to senior management on programs, policies and emerging issues."},
        {"plain": "Conduct research on economic or social issues",
         "polished": "Plans, leads and conducts research on economic, social, environmental or policy issues using appropriate qualitative and quantitative methods."},
    ],
    "IT": [
        {"plain": "Design and develop software systems",
         "polished": "Designs, develops, tests and maintains software systems, applications and digital services in accordance with enterprise architecture and security standards."},
        {"plain": "Provide technical advice and support",
         "polished": "Provides technical advice, troubleshooting support and guidance to clients, team members and stakeholders on IT systems and solutions."},
        {"plain": "Manage IT projects and initiatives",
         "polished": "Plans, manages and delivers IT projects and initiatives, including requirements, scope, schedule, risk and stakeholder engagement."},
    ],
    "EN": [
        {"plain": "Provide engineering analysis and technical advice",
         "polished": "Provides engineering analysis, technical assessments and specialist advice on projects, programs and procurement activities."},
        {"plain": "Review engineering designs and specifications",
         "polished": "Reviews and evaluates engineering designs, drawings, specifications and technical documentation to ensure compliance with applicable standards."},
        {"plain": "Lead engineering projects",
         "polished": "Plans, leads and manages engineering projects, coordinates with contractors and stakeholders, and ensures delivery within scope, schedule and budget."},
    ],
    "PE": [
        {"plain": "Provide HR advice and services",
         "polished": "Provides expert advice, guidance and services to management and employees on human resources policies, programs and collective agreement provisions."},
        {"plain": "Manage staffing and classification actions",
         "polished": "Manages staffing processes, classification actions and organizational reviews in compliance with the Public Service Employment Act and Treasury Board policies."},
        {"plain": "Develop HR policies and programs",
         "polished": "Develops, implements and evaluates HR policies, programs and initiatives aligned with departmental priorities and central agency direction."},
    ],
    "WP": [
        {"plain": "Administer welfare programs and benefits",
         "polished": "Administers welfare programs, processes applications, determines eligibility and delivers income support or benefits in accordance with applicable legislation and policies."},
        {"plain": "Provide case management support",
         "polished": "Provides case management support, counselling referrals and follow-up to clients to facilitate access to services and support self-sufficiency."},
        {"plain": "Liaise with community partners and service providers",
         "polished": "Liaises with community partners, service providers and other departments to coordinate service delivery and promote awareness of available programs."},
    ],
}
_SJD_DUTY_SUGGESTIONS["default"] = _SJD_DUTY_SUGGESTIONS["EC"]  # fallback


def _build_sjd_seed_duties(entry: object) -> list:
    """Build DraftDuty list seeded from _SJD_DUTY_SUGGESTIONS for the SJD's OG group.

    Each duty has source='sjd' and sjd_number set to the entry's sjd_number.
    Uses _SJD_DUTY_SUGGESTIONS keyed by og_code; falls back to 'default' (EC).
    """
    from app.models.draft_duty import DraftDuty
    import uuid
    suggestions = _SJD_DUTY_SUGGESTIONS.get(entry.og_code, _SJD_DUTY_SUGGESTIONS["default"])
    duties = []
    for idx, sug in enumerate(suggestions):
        duties.append(DraftDuty(
            id=str(uuid.uuid4()),
            text=sug["polished"],
            plain_trigger=sug["plain"],
            source="sjd",
            sjd_number=entry.sjd_number,
            provenance_section="Main duties",
            advisor=False,
        ))
    return duties


class WDCreateRequest(BaseModel):
    """Mutable fields for creating a new WD. Server generates id and timestamps."""

    record: dict = Field(default_factory=dict)
    answers: dict = Field(default_factory=dict)
    step_index: int = 0
    draft: Optional[dict] = None
    reviewing: bool = False
    editing_return: bool = False


class WDPatchRequest(BaseModel):
    """Partial update fields. Only provided fields are merged onto the stored WD.

    confirmed_noc and confirmed_og accept either a string (just the code) or
    a dict (full candidate metadata). The SPA's noc_confirm step sends a bare
    code string; og_confirm sends the full candidate dict. Both are valid
    shapes for the same conceptual value.
    """

    model_config = ConfigDict(extra="ignore")

    record: Optional[dict] = None
    answers: Optional[dict] = None
    step_index: Optional[int] = None
    draft: Optional[dict] = None
    reviewing: Optional[bool] = None
    editing_return: Optional[bool] = None
    confirmed_noc: Optional[Union[str, dict]] = None
    confirmed_og: Optional[Union[str, dict]] = None
    confirmed_sub_group: Optional[str] = None  # Phase 21: NU/SW/ED sub-group routing key
    og_level: Optional[int] = None
    reports_to_military: Optional[bool] = None
    jes_scores: Optional[list[dict]] = None
    jes_total_points: Optional[int] = None
    duties: Optional[list[dict]] = None
    qualification: Optional[dict] = None


@router.post("/wd", status_code=201)
async def create_wd(body: WDCreateRequest) -> dict:
    """Create a new WorkDescription and return its generated id."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    wd = WorkDescription(
        id=str(uuid4()),
        record=body.record,
        answers=body.answers,
        step_index=body.step_index,
        draft=body.draft,
        reviewing=body.reviewing,
        editing_return=body.editing_return,
        created_at=now,
        last_modified=now,
    )
    con = get_connection(settings.db_path)
    try:
        con.execute(
            "INSERT INTO work_descriptions (id, title, data, schema_version, created_at, last_modified) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                wd.id,
                wd.title,
                wd.model_dump_json(),
                wd.schema_version,
                wd.created_at.isoformat(),
                wd.last_modified.isoformat(),
            ),
        )
        con.commit()
    finally:
        con.close()
    return {"id": wd.id}


@router.get("/wd/{wd_id}")
async def get_wd(wd_id: str) -> WorkDescription:
    """Return the stored WorkDescription for the given id."""
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
    finally:
        con.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Work description not found")
    return WorkDescription.model_validate_json(row["data"])


@router.patch("/wd/{wd_id}")
async def patch_wd(wd_id: str, body: WDPatchRequest) -> WorkDescription:
    """Merge patch fields onto the stored WorkDescription and update last_modified."""
    import logging
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Work description not found")
        wd = WorkDescription.model_validate_json(row["data"])
        # Separate duties from scalar fields to enable validated merge
        raw_duties = body.duties  # extract before model_dump excludes it
        raw_qualification = body.qualification
        body_dump = body.model_dump(exclude_unset=True, exclude={'duties', 'qualification'})
        # Diagnostic: log classification-related fields if present
        cls_keys = [k for k in body_dump if k in ('confirmed_og', 'og_level', 'confirmed_noc', 'jes_total_points')]
        if cls_keys:
            logging.getLogger(__name__).info(
                "PATCH wd=%s classification fields: %s",
                wd_id[:8], {k: body_dump[k] for k in cls_keys},
            )
        for field, val in body_dump.items():
            setattr(wd, field, val)
        # Duties: validate each item against DraftDuty; cap at 20 (DoS mitigation)
        if raw_duties is not None:
            from app.models.draft_duty import DraftDuty as DD
            wd.duties = [DD(**d) for d in raw_duties[:20]]
        # Qualification: validate against QualificationStandard
        if raw_qualification is not None:
            from app.models.qualification_standard import QualificationStandard as QS
            wd.qualification = QS(**raw_qualification)
        wd.last_modified = datetime.now(timezone.utc)
        con.execute(
            "UPDATE work_descriptions SET data = ?, last_modified = ? WHERE id = ?",
            (wd.model_dump_json(), wd.last_modified.isoformat(), wd_id),
        )
        con.commit()
    finally:
        con.close()
    return wd


def _duty_contradicts_og(duty_lower: str, exclusions_text: str) -> bool:
    """Keyword check: True if any exclusion keyword appears in duty text.

    EC exclusions are empty — always returns False for EC positions.
    IT exclusions contain keywords like 'business analysis', 'administrative programs'.
    """
    exclusion_keywords = [
        phrase.strip().lower()
        for phrase in exclusions_text.replace(';', ',').split(',')
        if len(phrase.strip()) > 4
    ]
    return any(kw in duty_lower for kw in exclusion_keywords)


@router.post("/wd/{wd_id}/orphan_check")
async def run_orphan_check(wd_id: str) -> dict:
    """Deterministic orphan check: verb-keyword match against OG_DEFINITIONS.exclusions.

    No LLM — v2.0 policy is deterministic classification throughout.
    EC positions always return flagged: [] (EC has no exclusions defined).
    """
    from app.data.constants import OG_DEFINITIONS
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
    finally:
        con.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Work description not found")
    wd = WorkDescription.model_validate_json(row["data"])
    if not wd.confirmed_og:
        raise HTTPException(status_code=422, detail="OG not confirmed — orphan check requires confirmed OG")
    og_code = (
        wd.confirmed_og.get("og_code")
        if isinstance(wd.confirmed_og, dict)
        else wd.confirmed_og or ""
    )
    defn = OG_DEFINITIONS.get(og_code, {})
    exclusions_text = defn.get("exclusions", "")
    flagged = []
    for duty in wd.duties:
        duty_lower = duty.text.lower()
        if exclusions_text and _duty_contradicts_og(duty_lower, exclusions_text):
            flagged.append({
                "duty_id": duty.id,
                "orphan_rationale": (
                    f"This duty may fall outside the {og_code} functional authority: "
                    f"{exclusions_text}"
                ),
            })
    return {"wd_id": wd_id, "flagged": flagged}


@router.post("/wd/{wd_id}/validate-duties")
async def validate_duties_endpoint(wd_id: str) -> dict:
    """WG-01/WG-02: Structural duty validation. Non-blocking advisory check.

    Loads the WorkDescription from DB, runs validate_duties() from the duty_validator
    service, and returns per-duty findings. Findings are advisory — the endpoint
    never raises an error for failing duties, only for a missing WD (404).

    Returns:
        {"wd_id": str, "findings": [{"duty_id": str, "rules_failed": [...]}]}
    """
    from app.services.duty_validator import validate_duties as _validate_duties
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
    finally:
        con.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Work description not found")
    wd = WorkDescription.model_validate_json(row["data"])
    findings = _validate_duties(wd.duties)
    return {"wd_id": wd_id, "findings": findings}


class SJDStartRequest(BaseModel):
    """Request body for POST /api/wd/{id}/sjd-start."""
    sjd_number: str


@router.post("/wd/{wd_id}/sjd-start")
async def sjd_start(wd_id: str, body: SJDStartRequest) -> WorkDescription:
    """Pre-fill confirmed_og, og_level, seed duties, and sjd_source from a selected SJD.

    Security: sjd_number validated by lookup against static SJD_LIBRARY; 404 on miss (T-22-01).
    """
    from app.data.sjd_library import SJD_LIBRARY
    entry = next((e for e in SJD_LIBRARY if e.sjd_number == body.sjd_number), None)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"SJD {body.sjd_number!r} not found")

    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Work description not found")
        wd = WorkDescription.model_validate_json(row["data"])

        seed_duties = _build_sjd_seed_duties(entry)
        wd.confirmed_og = {"og_code": entry.og_code, "og_name": entry.title}
        wd.og_level = entry.og_level
        wd.duties = seed_duties
        wd.sjd_source = {
            "sjd_number": entry.sjd_number,
            "title": entry.title,
            "og_code": entry.og_code,
            "og_level": entry.og_level,
        }
        wd.last_modified = datetime.now(timezone.utc)
        con.execute(
            "UPDATE work_descriptions SET data = ?, last_modified = ? WHERE id = ?",
            (wd.model_dump_json(), wd.last_modified.isoformat(), wd_id),
        )
        con.commit()
    finally:
        con.close()
    return wd


class AuditDecideRequest(BaseModel):
    """Request body for POST /api/wd/{id}/audit/decide (AUDIT-04).

    rule_id is a free-form string identifier for the audit finding the
    decision applies to (capped to limit injection surface — T-24-04).
    section must be one of the six amendment-panel keys; decision must be
    one of the three documented advisor actions (T-24-05, T-24-06).
    """

    rule_id: str = Field(min_length=1, max_length=100)
    section: Literal['id', 'ov', 'du', 'cls', 'q', 'drf']
    decision: Literal['accept', 'manual_edit', 'skip']


@router.post("/wd/{wd_id}/audit")
async def run_compliance_audit(wd_id: str) -> dict:
    """AUDIT-01: Deterministic CBA + ERR compliance audit. Manual trigger only.

    Deletes previous risk_audit_finding rows for this WD, then runs the audit
    and inserts one row per finding. Returns findings to frontend for UI rendering.

    Re-running replaces previous findings (DELETE-then-INSERT pattern).
    """
    from app.services.risk_auditor import run_audit, load_cba_data
    import json as _json

    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Work description not found")
        wd = WorkDescription.model_validate_json(row["data"])

        # Extract OG code (may be stored as dict or plain string — match orphan_check pattern)
        og_code = (
            wd.confirmed_og.get("og_code")
            if isinstance(wd.confirmed_og, dict)
            else wd.confirmed_og or ""
        )

        cba_data = load_cba_data(og_code)
        findings = run_audit(wd, cba_data)

        now = datetime.now(timezone.utc)

        # Delete previous findings for this WD (deduplication on re-run)
        con.execute(
            "DELETE FROM audit_log WHERE wd_id = ? AND event = 'risk_audit_finding'",
            (wd_id,),
        )

        # Insert one row per finding
        for finding in findings:
            con.execute(
                "INSERT INTO audit_log (wd_id, event, actor, detail, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    wd_id,
                    "risk_audit_finding",
                    "system",
                    _json.dumps(finding),
                    now.isoformat(),
                ),
            )
        con.commit()
    finally:
        con.close()

    return {"wd_id": wd_id, "findings": findings}
