"""
app/api/og_classification.py — OG classification endpoints.

POST /api/og/classify — deterministic signal-based OG ranking (no LLM calls).
GET /api/og/definitions — returns verbatim OG definition from OG_DEFINITIONS constant.
GET /api/quals/default — returns TBS qual standard text from QUAL_STANDARDS constant.

Classification is fully deterministic: signal_tally from frontend QUESTION_BANK answers
is the sole ranking mechanism. No instructor, no Ollama calls in this module.

Security (per threat model):
  T-16-01: og_codes in signal_tally outside OG_DEFINITIONS are silently ignored.
  T-16-02: og_code query param validated against OG_DEFINITIONS before returning data.
  T-16-03: work_description capped at max_length=2000 via Pydantic Field.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.data.constants import ASEC_DISAMBIGUATION, OG_DEFINITIONS, OG_LEVELS, QUAL_STANDARDS

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class OGClassifyRequest(BaseModel):
    confirmed_noc_code: str = Field(min_length=1)
    work_description: str = Field(min_length=10, max_length=2000)  # T-16-03
    signal_tally: dict[str, int] = Field(default_factory=dict)


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


class OGClassifyResponse(BaseModel):
    candidates: list[OGCandidate]
    asec_alert: Optional[ASECAlert] = None


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
    """POST /api/og/classify — deterministic OG ranking from signal_tally."""
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

    return OGClassifyResponse(candidates=candidates, asec_alert=asec_alert)


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
