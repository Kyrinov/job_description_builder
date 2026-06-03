"""
app/models/qualification_standard.py — QualificationStandard entity (v2.0).

Pre-filled with the EC-05 default; advisor can edit both fields
(QUAL-01, QUAL-02). Source distinguishes "default" from "advisor-edited"
for the document preview's provenance rendering (QUAL-03).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class QualificationStandard(BaseModel):
    model_config = ConfigDict(extra="ignore")

    education: str
    experience: str
    source: Literal["EC-05 default", "advisor-edited"]
    last_modified: datetime
