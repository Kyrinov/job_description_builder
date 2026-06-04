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
