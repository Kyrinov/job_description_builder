"""
app/services/classification_gate.py — CLASS-04 hard gate utility.

Imported by Phase 17 (JES scoring), Phase 18 (JD composition), and Phase 20
(export routes). Raises 409 Conflict if OG group and level are not yet confirmed
on the WorkDescription, blocking job description generation until classification
is complete.

Usage:
    from app.services.classification_gate import require_og_confirmed
    ...
    require_og_confirmed(wd)  # raises 409 if not classified
"""
from __future__ import annotations

from fastapi import HTTPException

from app.models.work_description import WorkDescription


def require_og_confirmed(wd: WorkDescription) -> None:
    """Raise 409 Conflict if OG group and level are not yet confirmed.

    CLASS-04: JD generation is blocked at the API layer until both
    confirmed_og (the full OGCandidate dict) and og_level (an integer >= 1)
    are set on the WorkDescription.
    """
    if not wd.confirmed_og or wd.og_level is None:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "classification_pending",
                "message": (
                    "OG group and level must be confirmed before generating a job description."
                ),
            },
        )
