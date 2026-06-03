"""
app/models/classification.py — Classification + JESFactor (v2.0).

Classification captures the resolved work-type + 3 scope questions +
deterministic group/level resolution. JESFactor is co-located here
because it only makes sense as part of a classification (per-factor
breakdown is only rendered for EC groups).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class JESFactor(BaseModel):
    """One of 9 EC JES 2017 elements (or non-EC equivalent)."""
    model_config = ConfigDict(extra="ignore")

    name: str
    degree: int = Field(ge=1, le=7)  # EC JES uses degrees 1-7
    points: int = Field(ge=0)
    category: Literal["Responsibility", "Skill", "Effort", "Conditions"]


class Classification(BaseModel):
    """Work-type + 3 scope answers → group + level + points + rationale."""
    model_config = ConfigDict(extra="ignore")

    work_type: Literal["EC", "FI", "IT", "AS", "EN"]
    work_type_name: str
    applicable_standard: str  # e.g. "EC Job Evaluation Standard (2017)"

    # Scope answers (1-3 each; None until answered)
    scope_direction: Optional[int] = Field(default=None, ge=1, le=3)
    scope_advises: Optional[int] = Field(default=None, ge=1, le=3)
    scope_impact: Optional[int] = Field(default=None, ge=1, le=3)

    # Resolved fields (None until scope answers are complete)
    code: Optional[str] = None          # e.g. "EC-05"
    group: Optional[Literal["EC", "FI", "IT", "AS", "EN"]] = None
    level: Optional[int] = Field(default=None, ge=4, le=6)
    points: Optional[int] = Field(default=None, ge=0)
    factors: Optional[list[JESFactor]] = None  # EC only
    rationale: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
