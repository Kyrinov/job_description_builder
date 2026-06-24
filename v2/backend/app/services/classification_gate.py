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

    Fallback: also check wd.record (the SPA persists classification fields
    inside the record dict as well). If a SPA PATCH sets confirmed_og only
    inside record, the gate should still pass.

    Phase 28 (MGR-03): manager-track WDs deliberately skip classification.
    The bypass is intrinsic to wd_type — every caller (export.py DOCX/poster/
    PDF, jes_scoring.py) inherits it for free. getattr() with default
    "advisor" keeps old WD rows (serialized before this field existed)
    behaving as advisor — the gate behaves exactly as before for them.
    """
    if getattr(wd, "wd_type", "advisor") == "manager":
        return
    record_og = (wd.record or {}).get("confirmed_og")
    record_level = (wd.record or {}).get("og_level")
    confirmed_og = wd.confirmed_og or record_og
    og_level = wd.og_level if wd.og_level is not None else record_level
    if not confirmed_og or og_level is None:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "classification_pending",
                "message": (
                    "OG group and level must be confirmed before generating a job description."
                ),
            },
        )
