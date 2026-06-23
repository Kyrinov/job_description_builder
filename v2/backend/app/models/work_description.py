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

confirmed_noc and confirmed_og accept either a string (bare code) or a
dict/NOCMatch (full candidate). The SPA's noc_confirm step persists a
bare code; og_confirm persists the full candidate dict.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

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
    confirmed_noc: Optional[Union[str, NOCMatch, dict]] = None
    confirmed_og: Optional[Union[str, dict]] = None
    confirmed_sub_group: Optional[str] = None  # Phase 21: NU/SW/ED sub-group (e.g. "SCW", "CHA", "EDS")
    og_level: Optional[int] = Field(default=None, ge=1)
    sjd_source: Optional[dict] = None  # Phase 22: {sjd_number, title, og_code, og_level} — set by sjd-start
    org_context: Optional[str] = None  # Phase 26 — ORG-01
    reports_to_military: Optional[bool] = None
    jes_scores: list[dict] = Field(default_factory=list)
    jes_total_points: Optional[int] = None
    schema_version: int = 1
    created_at: datetime
    last_modified: datetime
