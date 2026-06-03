"""
app/models/draft_duty.py — DraftDuty entity (v2.0).

Represents one duty in the WD. Two sources:
- "suggested": from the 7 pre-written duties (source_index is the index in DUTY_SUGGESTIONS)
- "advisor": typed in free-text by the advisor and refined via verb-mapping
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class DraftDuty(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    text: str
    plain_trigger: Optional[str] = None
    source: Literal["suggested", "advisor"]
    source_index: Optional[int] = None  # Index into DUTY_SUGGESTIONS (suggested only)
    refined_at: Optional[datetime] = None  # When verb-mapping was applied (advisor only)
