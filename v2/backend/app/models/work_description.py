"""
app/models/work_description.py — WorkDescription entity (v2.0).

Stores the conversational state of an in-progress WD:
- record: committed answers (id -> answer)
- answers: per-step answer history (id -> [answer, answer, ...])
- step_index: current step in the 12-step interview
- draft: in-progress answer for the current step
- reviewing: True when advisor is on the review screen
- editing_return: True when advisor is re-answering a past step
- classification: resolved Classification (after work-type + 3 scope Qs)
- duties: selected/added duties
- qualification: edited or default EC-05 qualification
- drf_id: selected DND core responsibility (if applicable)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .classification import Classification
from .draft_duty import DraftDuty
from .noc_match import NOCMatch
from .qualification_standard import QualificationStandard


class WorkDescription(BaseModel):
    """Canonical WD entity for v2.0. JSON-encoded into work_descriptions.data."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    title: str = ""
    record: dict = Field(default_factory=dict)
    answers: dict = Field(default_factory=dict)
    step_index: int = 0
    draft: Optional[dict] = None
    reviewing: bool = False
    editing_return: bool = False
    classification: Optional[Classification] = None
    duties: list[DraftDuty] = Field(default_factory=list)
    qualification: Optional[QualificationStandard] = None
    drf_id: Optional[str] = None
    noc_candidates: list[NOCMatch] = Field(default_factory=list)
    confirmed_noc: Optional[NOCMatch] = None
    confirmed_og: Optional[dict] = None
    og_level: Optional[int] = Field(default=None, ge=1)
    reports_to_military: Optional[bool] = None
    schema_version: int = 1
    created_at: datetime
    last_modified: datetime
