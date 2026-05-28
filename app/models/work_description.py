"""
app/models/work_description.py — Canonical data model for JD Builder.

FINALIZED IN PHASE 1. Every Phase 2–8 service imports from this module.
Do not change field names or types without a migration script.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ProvenanceTag(BaseModel):
    """Carries the authoritative source for every content element in a WorkDescription.

    Attached at retrieval/write time — never inferred post-hoc.
    Every content sub-model (DraftDuty, NOCMatch, etc.) carries exactly one ProvenanceTag.
    """
    source_type: Literal[
        "NOC",           # NOC 2021 unit group profile
        "CA",            # Collective agreement article
        "JES",           # Job Evaluation Standard factor
        "TBS_OG_DEF",    # TBS OCHRO OG definition / inclusions / exclusions
        "TBS_DIRECTIVE", # TBS Directive on Classification
        "QUAL_STD",      # TBS Qualification Standard
        "DRF",           # DND Departmental Results Framework
        "ADVISOR",       # Entered directly by advisor — no authoritative source
        "AI_GENERATED",  # AI-generated text with no verbatim source match
    ]
    source_id: str         # e.g., "21232", "AI CA 2026 Article 5.02"
    source_version: str    # e.g., "NOC 2021", "AI CA 2026-2029"
    source_url: Optional[str] = None
    retrieved_date: date
    model_name: Optional[str] = None       # populated if source_type == "AI_GENERATED"
    prompt_version: Optional[str] = None   # populated if source_type == "AI_GENERATED"
    modified_by_advisor: bool = False


class NOCMatch(BaseModel):
    noc_code: str
    noc_title: str
    teer_level: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    matched_duty_statements: list[str] = Field(default_factory=list)
    provenance: ProvenanceTag


class DraftDuty(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    text: str
    provenance: ProvenanceTag
    advisor_modified: bool = False
    advisor_modified_text: Optional[str] = None


class OGRecommendation(BaseModel):
    og_code: str
    og_name: str
    level: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    provenance: ProvenanceTag
    evidence_quotes: list[str] = Field(default_factory=list)
    cited_articles: list[ProvenanceTag] = Field(default_factory=list)
    confirmed_by_advisor: bool = False


class JESFactorScore(BaseModel):
    factor_name: str
    level: int
    points: Optional[int] = None
    rationale: str
    evidence_quotes: list[str] = Field(default_factory=list)
    provenance: ProvenanceTag
    advisor_adjusted: bool = False
    advisor_adjusted_level: Optional[int] = None
    advisor_adjustment_rationale: Optional[str] = None


class DraftText(BaseModel):
    """Any AI-generated or sourced text block with provenance."""
    text: str
    provenance: ProvenanceTag


class WorkDescription(BaseModel):
    """
    Central entity. Created at first advisor input, persisted to SQLite after
    every state transition. Export renders directly from this — no reconstruction.

    FINALIZED PHASE 1 — schema_version = 1.
    Any change to field names/types after Phase 2 requires a migration script
    and a schema_version bump.
    """
    id: UUID = Field(default_factory=uuid4)
    session_id: str
    schema_version: int = 1  # Bump and write migration when model changes after Phase 2

    # TBS-required WD header fields (DATA-01)
    position_title: Optional[str] = None
    position_number: Optional[str] = None
    og_level: Optional[str] = None            # e.g., "EC-04"
    supervisor_title: Optional[str] = None
    supervisor_position_number: Optional[str] = None
    review_date: Optional[date] = None
    organizational_context: Optional[DraftText] = None

    # Stage: NL input
    raw_input: str
    input_timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Stage: NOC mapping
    noc_candidates: list[NOCMatch] = Field(default_factory=list)
    confirmed_noc: Optional[NOCMatch] = None

    # Stage: OG classification
    og_recommendation: Optional[OGRecommendation] = None
    confirmed_og: Optional[str] = None
    confirmed_level: Optional[str] = None

    # Stage: JD content
    draft_duties: list[DraftDuty] = Field(default_factory=list)
    advisor_additions: list[DraftDuty] = Field(default_factory=list)  # source_type="ADVISOR"

    # Stage: JES scoring
    jes_scores: list[JESFactorScore] = Field(default_factory=list)
    jes_total_points: Optional[int] = None

    # Metadata
    stage: Literal[
        "input", "noc_mapped", "og_classified",
        "jd_drafted", "jes_scored", "exported"
    ] = "input"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_modified: datetime = Field(default_factory=datetime.utcnow)
    export_hash: Optional[str] = None
    exported_at: Optional[datetime] = None
