"""
app/api/noc_mapping.py — POST /api/noc/map — NL→NOC mapping endpoint.

JSON-only (no HTMX). Accepts a free-text work description, runs the three-stage
pipeline (FTS5 → sqlite-vec rerank → LLM justification), and returns top candidates.

The route does NOT persist candidates to the WD database — that happens in Phase 15
when the advisor commits the NOC step via PATCH /api/wd/{id}. This endpoint is
stateless: call it, get candidates, SPA handles selection.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.db import get_noc_connection
from app.models.noc import NocCandidateOut, NocMapResponse, WorkDescriptionRequest
from app.services.noc_mapper import map_work_description

router = APIRouter()


@router.post("/noc/map", response_model=NocMapResponse)
async def map_noc(body: WorkDescriptionRequest) -> NocMapResponse:
    """Run the three-stage NL→NOC pipeline and return top candidates.

    Raises 422 if:
    - work_description is shorter than 10 characters (Pydantic validation)
    - FTS5 shortlist is empty (no lexical overlap with NOC corpus)
    - All candidates had fabricated duties (verbatim guardrail)
    """
    settings = get_settings()
    try:
        result = await map_work_description(
            work_description=body.work_description,
            noc_db_path=settings.noc_db_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    candidates_out = [
        NocCandidateOut(
            noc_code=c.noc_code,
            title=c.title,
            teer=c.teer,
            rank=c.rank,
            matched_duties=c.matched_duties,
            justification=c.justification,
        )
        for c in result.candidates
    ]
    return NocMapResponse(candidates=candidates_out)


@router.get("/noc/{noc_code}/duties")
async def get_noc_duties(noc_code: str) -> dict:
    """Return verbatim Main duties for a confirmed NOC code.

    Reads noc_elements WHERE element_type='Main duties' for the given noc_code.
    Returns source_hash for ProvenanceTag content hash (JD-02).
    Uses get_noc_connection() — NOT get_connection() (different DB files).
    EC and IT positions have exclusions defined; EC orphan check always returns 0 flags.
    """
    if not noc_code or len(noc_code) < 3:
        raise HTTPException(status_code=422, detail="noc_code must be at least 3 characters")
    settings = get_settings()
    con = get_noc_connection(settings.noc_db_path)
    try:
        rows = con.execute(
            "SELECT id, element_text, source_hash FROM noc_elements "
            "WHERE noc_code = ? AND element_type = 'Main duties' "
            "ORDER BY id",
            (noc_code,),
        ).fetchall()
    finally:
        con.close()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No Main duties found for NOC {noc_code!r}")
    return {
        "noc_code": noc_code,
        "duties": [
            {
                "id": row["id"],
                "text": row["element_text"],
                "source_hash": row["source_hash"] or None,
            }
            for row in rows
        ],
    }
