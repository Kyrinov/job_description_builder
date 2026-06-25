"""
app/api/og_classification.py — OG classification endpoints.

POST /api/og/classify — deterministic signal-based OG ranking (no LLM calls).
GET /api/og/definitions — returns verbatim OG definition from OG_DEFINITIONS constant.
GET /api/quals/default — returns TBS qual standard text from QUAL_STANDARDS constant.
POST /api/wd/{wd_id}/confirm-subgroup — stores validated sub-group on WorkDescription
    (T-21-01: validates sub_group against ALLOWED_SUBGROUPS[og_code] frozenset).

Classification is fully deterministic: signal_tally from frontend QUESTION_BANK answers
is the sole ranking mechanism. No instructor, no Ollama calls in this module.

Security (per threat model):
  T-16-01: og_codes in signal_tally outside OG_DEFINITIONS are silently ignored.
  T-16-02: og_code query param validated against OG_DEFINITIONS before returning data.
  T-16-03: work_description capped at max_length=2000 via Pydantic Field.
  T-21-01: sub_group field on /confirm-subgroup validated against
           ALLOWED_SUBGROUPS[og_code] frozenset; invalid → 422 with allowed_values.
  T-21-02: SubGroupAlert constructed from SUBGROUP_DISAMBIGUATIONS constant
           (no user input flows into og_code in the alert payload).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.data.constants import (
    ASEC_DISAMBIGUATION,
    OG_DEFINITIONS,
    OG_LEVELS,
    QUAL_STANDARDS,
    SUBGROUP_DISAMBIGUATIONS,
)
from app.db import get_connection
from app.models.work_description import WorkDescription

router = APIRouter()


# ---------------------------------------------------------------------------
# T-21-01: allowed sub-group values per OG code — used for input validation
# on the /confirm-subgroup endpoint. Each value is a frozenset so the in-test
# containment check is O(1) and the set is immutable.
# ---------------------------------------------------------------------------
ALLOWED_SUBGROUPS: dict[str, frozenset] = {
    "NU": frozenset({"HOS", "CHN", "EMA"}),
    "SW": frozenset({"SCW", "CHA"}),
    "ED": frozenset({"EDS", "LAT", "EST"}),
}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class OGClassifyRequest(BaseModel):
    confirmed_noc_code: str = Field(min_length=1)
    work_description: str = Field(min_length=10, max_length=2000)  # T-16-03
    signal_tally: dict[str, int] = Field(default_factory=dict)
    confirmed_og: Optional[str] = None  # OGX-07: triggers sub-group disambiguation alert


class OGCandidate(BaseModel):
    og_code: str
    og_name: str
    rank: int
    confidence: float
    rationale: str
    evidence_quotes: list[str]
    definition_excerpt: str
    relevant_inclusions: str
    relevant_exclusions: str
    available_levels: list[int]


class ASECAlert(BaseModel):
    disambiguation_text: str
    citation: str


class SubGroupAlert(BaseModel):
    """OGX-07 — sub-group disambiguation alert for NU, SW, ED classifications.

    Sourced verbatim from SUBGROUP_DISAMBIGUATIONS constant (T-21-02):
    the og_code in SUBGROUP_DISAMBIGUATIONS is keyed by the request's
    confirmed_og (already validated against OG_DEFINITIONS in the
    classify_og endpoint), so this payload is never constructed from
    arbitrary user input.
    """
    subgroups: list[str]
    descriptions: dict[str, str]
    disambiguation_text: str
    citation: str


class OGClassifyResponse(BaseModel):
    candidates: list[OGCandidate]
    asec_alert: Optional[ASECAlert] = None
    subgroup_alert: Optional[SubGroupAlert] = None  # OGX-07


class OGDefinitionResponse(BaseModel):
    og_code: str
    og_name: str
    definition: str
    inclusions: str
    exclusions: str


class QualStandardResponse(BaseModel):
    og_code: str
    education: str
    experience: str
    source: str


class SubGroupConfirmRequest(BaseModel):
    """Request body for POST /api/wd/{id}/confirm-subgroup.

    T-21-01: sub_group is validated against ALLOWED_SUBGROUPS[og_code] before storage.
    """
    sub_group: str = Field(min_length=1, max_length=10)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _rank_og_candidates(
    signal_tally: dict[str, int],
    confirmed_noc_code: str,
) -> list[tuple[str, float]]:
    """Return list of (og_code, confidence) sorted descending by signal count.

    Only OG codes present in OG_DEFINITIONS are included (T-16-01: unknown codes
    from signal_tally are silently ignored).

    Fallback when signal_tally is empty or has no known codes: return fixed
    default ranking [EC, AS, IT] so the endpoint never returns an empty list.
    """
    known_tally = {k: v for k, v in signal_tally.items() if k in OG_DEFINITIONS}

    if not known_tally:
        return [("EC", 0.55), ("AS", 0.35), ("IT", 0.10)]

    total = sum(known_tally.values())
    ranked = sorted(known_tally.items(), key=lambda x: x[1], reverse=True)
    results = []
    for og_code, votes in ranked[:3]:
        confidence = round(votes / total * 0.9, 3)  # cap at 0.9 — signal-based only
        results.append((og_code, confidence))
    return results


def _build_rationale(
    og_code: str,
    signal_tally: dict[str, int],
    defn: dict,
) -> str:
    """Generate template rationale string (no LLM)."""
    total = sum(signal_tally.values()) or 1
    votes = signal_tally.get(og_code, 0)
    og_name = defn.get("og_name", og_code)
    excerpt = defn.get("definition", "")[:120]
    return (
        f"The signal profile from the work-type questions ({votes} of {total} signals "
        f"for {og_code}) aligns with the {og_name} group, which covers: {excerpt}."
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/og/classify")
async def classify_og(body: OGClassifyRequest) -> OGClassifyResponse:
    """POST /api/og/classify — deterministic OG ranking from signal_tally.

    OGX-07: when confirmed_og is one of {NU, SW, ED}, response includes
    a subgroup_alert built from SUBGROUP_DISAMBIGUATIONS[confirmed_og].
    """
    ranked = _rank_og_candidates(body.signal_tally, body.confirmed_noc_code)
    candidates = []
    for rank_idx, (og_code, confidence) in enumerate(ranked, start=1):
        defn = OG_DEFINITIONS.get(og_code, {})
        candidates.append(
            OGCandidate(
                og_code=og_code,
                og_name=defn.get("og_name", og_code),
                rank=rank_idx,
                confidence=confidence,
                rationale=_build_rationale(og_code, body.signal_tally, defn),
                evidence_quotes=[],  # deterministic — no fabricated quotes
                definition_excerpt=defn.get("definition", "")[:400],
                relevant_inclusions=defn.get("inclusions", "")[:400],
                relevant_exclusions=defn.get("exclusions", "")[:300],
                available_levels=OG_LEVELS.get(og_code, []),
            )
        )

    asec_alert = None
    og_codes_in_top3 = {c.og_code for c in candidates}
    if "AS" in og_codes_in_top3 and "EC" in og_codes_in_top3:
        asec_alert = ASECAlert(**ASEC_DISAMBIGUATION)

    # OGX-07 — sub-group disambiguation alert
    # Fires unconditionally when confirmed_og is in SUBGROUP_DISAMBIGUATIONS
    # (not conditional on top-3 overlap — these groups always have sub-groups).
    subgroup_alert: Optional[SubGroupAlert] = None
    if body.confirmed_og and body.confirmed_og in SUBGROUP_DISAMBIGUATIONS:
        subgroup_alert = SubGroupAlert(**SUBGROUP_DISAMBIGUATIONS[body.confirmed_og])

    return OGClassifyResponse(
        candidates=candidates,
        asec_alert=asec_alert,
        subgroup_alert=subgroup_alert,
    )


@router.get("/og/definitions")
async def get_og_definition(og_code: str) -> OGDefinitionResponse:
    """GET /api/og/definitions?og_code=EC — returns verbatim OG definition.

    Returns 404 if og_code is not in OG_DEFINITIONS (T-16-02 mitigation).
    """
    if og_code not in OG_DEFINITIONS:
        raise HTTPException(status_code=404, detail=f"OG code {og_code!r} not found")
    defn = OG_DEFINITIONS[og_code]
    return OGDefinitionResponse(
        og_code=og_code,
        og_name=defn.get("og_name", og_code),
        definition=defn.get("definition", ""),
        inclusions=defn.get("inclusions", ""),
        exclusions=defn.get("exclusions", ""),
    )


@router.get("/quals/default")
async def get_qual_default(og_code: str) -> QualStandardResponse:
    """GET /api/quals/default?og_code=EC — returns TBS qual standard text."""
    if og_code not in QUAL_STANDARDS:
        raise HTTPException(
            status_code=404,
            detail=f"Qualification standard for OG code {og_code!r} not found",
        )
    std = QUAL_STANDARDS[og_code]
    return QualStandardResponse(
        og_code=og_code,
        education=std["education"],
        experience=std["experience"],
        source=std["source"],
    )


@router.post("/wd/{wd_id}/confirm-subgroup")
async def confirm_subgroup(wd_id: str, body: SubGroupConfirmRequest) -> dict:
    """POST /api/wd/{wd_id}/confirm-subgroup — store validated sub-group on WD.

    T-21-01: validates body.sub_group against ALLOWED_SUBGROUPS[og_code] before
    storage. Returns 422 with allowed_values list when sub_group is not in
    the allowed set for the WD's confirmed_og. Returns 404 when the WD does
    not exist or has no confirmed_og set.
    """
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=404, detail=f"Work description {wd_id!r} not found"
            )
        wd = WorkDescription.model_validate_json(row["data"])

        # T-21-01 — determine og_code from confirmed_og (may be str or dict)
        confirmed_og = wd.confirmed_og
        if isinstance(confirmed_og, dict):
            og_code = confirmed_og.get("og_code", "") or ""
        else:
            og_code = confirmed_og or ""

        if not og_code:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Work description {wd_id!r} has no confirmed_og — "
                    "sub-group disambiguation requires a confirmed OG first"
                ),
            )

        # T-21-01 — validate sub_group against allowed set
        if og_code in ALLOWED_SUBGROUPS:
            allowed = ALLOWED_SUBGROUPS[og_code]
            if body.sub_group not in allowed:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "invalid_sub_group",
                        "message": (
                            f"sub_group {body.sub_group!r} is not valid for "
                            f"OG {og_code!r}"
                        ),
                        "allowed_values": sorted(allowed),
                    },
                )
        else:
            # The WD's confirmed_og is not a sub-group-bearing group; the
            # sub_group value is meaningless. Treat as 422 to surface the
            # data inconsistency to the caller (no silent acceptance).
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "og_has_no_subgroups",
                    "message": (
                        f"OG {og_code!r} does not have sub-groups; "
                        "sub_group is not applicable"
                    ),
                },
            )

        # Persist confirmed_sub_group on WD
        wd.confirmed_sub_group = body.sub_group
        wd.last_modified = datetime.now(timezone.utc)
        con.execute(
            "UPDATE work_descriptions SET data = ?, last_modified = ? WHERE id = ?",
            (wd.model_dump_json(), wd.last_modified.isoformat(), wd_id),
        )
        con.commit()
    finally:
        con.close()
    return {"status": "ok", "confirmed_sub_group": body.sub_group}
