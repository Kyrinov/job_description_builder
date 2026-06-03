"""
app/api/health.py — GET /api/health (Phase 10 scaffold).

Phase 18 will add /api/wd (POST/GET/PATCH), /api/work-types, /api/duties,
/api/quals/default, /api/classify. For Phase 10 we only ship /api/health
to prove the proxy works.
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Liveness probe — returns 200 with {"status": "ok"}."""
    return {"status": "ok"}
