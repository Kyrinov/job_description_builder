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

import asyncio
import hashlib
import io
import logging
import os
from datetime import datetime

from docxtpl import DocxTemplate

from app.config import settings
from app.db import get_connection
from app.models.work_description import WorkDescription
from app.services.wd_store import load_work_description, save_work_description

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pre-export validation gate (D-01 / D-02)
# ---------------------------------------------------------------------------


def validate_export_readiness(wd: WorkDescription) -> list[str]:
    """Return a list of human-readable error messages blocking export.

    Blocking conditions (D-01 / D-02):
        - Any JESFactorScore with level == -1 (failed-factor sentinel) AND
          advisor_adjusted=False (D-08.1-03: advisor override resolves the block)
        - Any JESFactorScore with points is None (silent-zero bug at
          jes_service.py:76-77 — the LLM returned a degree that did not
          map to a value in the point_values dict) AND advisor_adjusted=False
        - No JES scores recorded at all

    Returns [] when the WD is ready to export.
    """
    errors: list[str] = []
    for s in wd.jes_scores:
        # D-08.1-03: advisor override resolves the block — skip the failure check
        if s.advisor_adjusted:
            continue
        if s.level == -1 or s.points is None:
            errors.append(
                f"JES factor {s.factor_name!r} is incomplete "
                f"(level={s.level}, points={s.points}) — return to JES scoring "
                f"or apply advisor override."
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


# ---------------------------------------------------------------------------
# DOCX render + stage advancement (D-03 / D-05 / D-06)
# ---------------------------------------------------------------------------


def _build_context(wd: WorkDescription) -> dict:
    """Build the docxtpl context dict for the TBS Work Description template.

    All values are read directly from the WorkDescription model fields and
    ProvenanceTags — no prose citations are written here (D-05). Advisor-added
    content carries the `is_advisor` flag the template uses to render the
    'advisor-added / not from authoritative source' marker (D-06).
    """
    # Header scalars (TBS-required WD fields; D-04)
    header = {
        "position_title": wd.position_title or "",
        "position_number": wd.position_number or "",
        "og_level": wd.og_level or "",
        "supervisor_title": wd.supervisor_title or "",
        "supervisor_position_number": wd.supervisor_position_number or "",
        "review_date": str(wd.review_date) if wd.review_date is not None else "",
    }

    # Organizational context (text + ProvenanceTag-derived citation)
    org_text = ""
    org_source = ""
    if wd.organizational_context is not None:
        org_text = wd.organizational_context.text
        org_source = (
            f"{wd.organizational_context.provenance.source_id} "
            f"({wd.organizational_context.provenance.source_version})"
        )

    # Duties: combine authoritative DraftDuties and advisor additions; each
    # entry is a dict the template can iterate over with {%p for duty in duties %}.
    duties: list[dict] = []
    for d in (wd.draft_duties or []) + (wd.advisor_additions or []):
        is_advisor = bool(
            d.advisor_modified
            or (d.provenance is not None and d.provenance.source_type == "ADVISOR")
        )
        duties.append(
            {
                "text": d.advisor_modified_text or d.text,
                "source_id": d.provenance.source_id,
                "source_version": d.provenance.source_version,
                "is_advisor": is_advisor,
            }
        )

    # JES scores
    jes_scores: list[dict] = []
    for s in wd.jes_scores or []:
        jes_scores.append(
            {
                "factor_name": s.factor_name,
                "level": s.level,
                "points": str(s.points) if s.points is not None else "—",
                "source_id": s.provenance.source_id,
                "source_version": s.provenance.source_version,
            }
        )

    return {
        **header,
        "organizational_context_text": org_text,
        "organizational_context_source": org_source,
        "duties": duties,
        "jes_scores": jes_scores,
        "jes_total_points": wd.jes_total_points if wd.jes_total_points is not None else 0,
        "manifest": build_version_manifest(wd),
    }


def _resolve_template_path() -> str:
    """Locate the committed docxtpl template at templates/docx/work_description_template.docx.

    The service lives at app/services/export_service.py; the template lives at
    templates/docx/work_description_template.docx — three directories up, then
    into templates/docx/.
    """
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "templates",
        "docx",
        "work_description_template.docx",
    )


async def generate_export(wd_id: str, db_path: str) -> dict:
    """Render a DOCX export for a completed WorkDescription.

    Requirements:
        - wd.stage == 'jes_scored' (raises ValueError otherwise)
        - validate_export_readiness(wd) returns [] (raises ValueError otherwise)
        - docxtpl render produces non-empty file bytes
            (raises ValueError otherwise — stage is NOT advanced)

    On success:
        - Advances wd.stage to 'exported'
        - Records export_hash (SHA-256 hex of the file bytes) and exported_at
        - Returns a dict with file_bytes, filename, export_hash, wd_id

    Mirrors the async structure of app/services/jes_service.score_jes:
    conn in a try/finally, all SQLite ops wrapped in asyncio.to_thread, model_copy
    stage advancement after success.
    """
    conn = await asyncio.to_thread(lambda: get_connection(db_path))
    try:
        # 1. Load and validate WorkDescription stage gate
        wd: WorkDescription | None = await asyncio.to_thread(
            lambda: load_work_description(conn, wd_id)
        )
        if wd is None:
            raise ValueError(f"WorkDescription {wd_id!r} not found")
        if wd.stage not in ("jes_scored", "exported"):
            raise ValueError(
                f"WorkDescription is in stage {wd.stage!r}, expected 'jes_scored' or 'exported'"
            )

        # 2. Pre-export validation gate (D-01 / D-02).
        # Raise BEFORE any rendering so the stage is never advanced when the WD
        # is incomplete (D-03 / D-11).
        errors = validate_export_readiness(wd)
        if errors:
            raise ValueError("Export blocked — " + "; ".join(errors))

        # 3. Resolve template + build context dict from WD + ProvenanceTags (D-05)
        template_path = _resolve_template_path()
        context = _build_context(wd)

        # 4. Render in a worker thread (asyncio.to_thread) so the FastAPI event
        # loop is not blocked during docxtpl processing. Uses BytesIO per
        # D-discretion (no temp files on disk).
        def _render() -> bytes:
            doc = DocxTemplate(template_path)
            doc.render(context)
            buf = io.BytesIO()
            doc.save(buf)
            return buf.getvalue()

        file_bytes = await asyncio.to_thread(_render)

        # 5. D-03 guard — stage advancement only after confirmed non-empty bytes
        if not file_bytes:
            raise ValueError(
                "Export produced empty document — aborting stage advancement."
            )

        # 6. export_hash = SHA-256 hex of the file bytes
        export_hash = hashlib.sha256(file_bytes).hexdigest()

        # 7. Advance stage to 'exported' with the new hash + timestamp
        updated_wd = wd.model_copy(
            update={
                "stage": "exported",
                "export_hash": export_hash,
                "exported_at": datetime.utcnow(),
            }
        )
        await asyncio.to_thread(lambda: save_work_description(conn, updated_wd))

        return {
            "wd_id": str(wd.id),
            "file_bytes": file_bytes,
            "filename": "work_description.docx",
            "export_hash": export_hash,
        }

    finally:
        await asyncio.to_thread(conn.close)
