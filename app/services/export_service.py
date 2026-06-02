"""
app/services/export_service.py — DOCX export pipeline for completed WorkDescriptions.

Public API:
    validate_export_readiness(wd) -> list[str]
    build_version_manifest(wd) -> list[dict]
    async generate_export(wd_id, db_path) -> dict

Architecture:
    - Pre-export validator (D-01/D-02) blocks on level==-1 or points is None,
      fixing the Phase 7 silent-zero bug at jes_service.py:76-77.
    - Version manifest (D-07) deduplicates every ProvenanceTag on the WD by
      (source_type, source_id, source_version).
    - DOCX render (D-05/D-06) uses docxtpl — citations and advisor markers are
      derived from ProvenanceTag fields, not hardcoded prose.
    - Stage advancement (D-03) only happens after confirmed non-empty file bytes.

Direct analog: app/services/jes_service.py
"""
from __future__ import annotations

import logging
from typing import Optional

from app.models.work_description import WorkDescription

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pre-export validation gate (D-01 / D-02)
# ---------------------------------------------------------------------------


def validate_export_readiness(wd: WorkDescription) -> list[str]:
    """Return a list of human-readable error messages blocking export.

    Blocking conditions (D-01 / D-02):
        - Any JESFactorScore with level == -1 (failed-factor sentinel)
        - Any JESFactorScore with points is None (silent-zero bug at
          jes_service.py:76-77 — the LLM returned a degree that did not
          map to a value in the point_values dict)
        - No JES scores recorded at all

    Returns [] when the WD is ready to export.
    """
    errors: list[str] = []
    for s in wd.jes_scores:
        if s.level == -1 or s.points is None:
            errors.append(
                f"JES factor {s.factor_name!r} is incomplete "
                f"(level={s.level}, points={s.points}) — return to JES scoring."
            )
    if not wd.jes_scores:
        errors.append("No JES factors scored — complete JES scoring before export.")
    return errors


# ---------------------------------------------------------------------------
# Version manifest (D-07)
# ---------------------------------------------------------------------------


def _tag_to_dict(tag) -> dict:
    """Convert a ProvenanceTag to the manifest dict shape used in docxtpl."""
    return {
        "source_type": tag.source_type,
        "source_id": tag.source_id,
        "source_version": tag.source_version,
        "retrieved_date": str(tag.retrieved_date),
    }


def build_version_manifest(wd: WorkDescription) -> list[dict]:
    """Return a deduplicated list of every source document used in this WD.

    Walks every element on the WD that carries a ProvenanceTag (NOC match,
    OG recommendation + its cited articles, organizational context, every
    DraftDuty in draft_duties + advisor_additions, every JESFactorScore in
    jes_scores) and emits one entry per unique
    (source_type, source_id, source_version) tuple. First-seen order is
    preserved (D-07).
    """
    seen: set[tuple[str, str, str]] = set()
    manifest: list[dict] = []

    def _maybe_emit(tag) -> None:
        if tag is None:
            return
        key = (tag.source_type, tag.source_id, tag.source_version)
        if key in seen:
            return
        seen.add(key)
        manifest.append(_tag_to_dict(tag))

    # NOC match
    if wd.confirmed_noc is not None:
        _maybe_emit(wd.confirmed_noc.provenance)

    # OG recommendation + cited articles
    if wd.og_recommendation is not None:
        _maybe_emit(wd.og_recommendation.provenance)
        for article in wd.og_recommendation.cited_articles or []:
            _maybe_emit(article)

    # Organizational context
    if wd.organizational_context is not None:
        _maybe_emit(wd.organizational_context.provenance)

    # Draft duties
    for duty in wd.draft_duties or []:
        _maybe_emit(duty.provenance)

    # Advisor additions
    for duty in wd.advisor_additions or []:
        _maybe_emit(duty.provenance)

    # JES factor scores
    for score in wd.jes_scores or []:
        _maybe_emit(score.provenance)

    return manifest
