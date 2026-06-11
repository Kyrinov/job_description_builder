"""
app/api/sjd.py — SJD Library read-only endpoints.

GET /api/sjd              — list all SJD entries, optional ?og_code= filter
GET /api/sjd/{sjd_number} — single entry by sjd_number; 404 on miss

Security:
  T-22-01: sjd_number validated by lookup against static SJD_LIBRARY constant; 404 on miss.
  T-22-02: og_code filter is case-insensitive equality check; no SQL; no eval.
"""
from __future__ import annotations

import dataclasses
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.data.sjd_library import SJD_LIBRARY

router = APIRouter()


@router.get("/sjd")
def list_sjds(og_code: Optional[str] = Query(default=None)) -> list[dict]:
    """Return all SJD entries, optionally filtered by og_code (case-insensitive)."""
    entries = SJD_LIBRARY
    if og_code:
        entries = [e for e in entries if e.og_code.upper() == og_code.upper()]
    return [dataclasses.asdict(e) for e in entries]


@router.get("/sjd/{sjd_number}")
def get_sjd(sjd_number: str) -> dict:
    """Return a single SJD entry by sjd_number; 404 if not found (T-22-01)."""
    entry = next((e for e in SJD_LIBRARY if e.sjd_number == sjd_number), None)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"SJD {sjd_number!r} not found")
    return dataclasses.asdict(entry)
