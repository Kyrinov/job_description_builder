"""
app/services/drf_service.py — DND Departmental Results Framework service layer.

Public API:
    get_drf_candidates(wd_id, db_path) -> dict
    confirm_drf_linkages(wd_id, row_ids, db_path) -> dict

Architecture:
    - Keyword-based candidate matching (no LLM, no embeddings) — token overlap
      between the WD's draft duty text and the indexed drf_rows.search_text.
    - All DB calls go through asyncio.to_thread (mirrors jd_service.py /
      jes_service.py pattern) to keep the FastAPI event loop non-blocking.
    - Stage is NOT advanced by either function. confirm_drf_linkages persists
      linkages but leaves the WD in its current stage.
"""
from __future__ import annotations

import asyncio
import logging
import re

from app.db import get_connection
from app.models.work_description import WorkDescription
from app.services.wd_store import load_work_description, save_work_description

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token matching
# ---------------------------------------------------------------------------

# High-frequency English stopwords filtered out of token sets before
# computing overlap. Reduces noise (e.g., "of", "the", "and") so matching
# reflects domain-specific vocabulary rather than grammar tokens.
STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "in", "for",
    "with", "that", "this", "is", "are", "be", "by", "on", "at", "as",
    "it", "its", "from", "have", "has", "was", "were", "will", "can", "may",
    "not", "but", "if", "their", "they", "we", "our", "you", "your",
})


def _tokenize(text: str) -> set[str]:
    """Lowercase + split on non-letter boundaries, minus stopwords.

    Pattern: re.findall(r'[a-z]+', text) — emits only alphabetic tokens,
    no digits, no punctuation. Empty string returns empty set.
    """
    if not text:
        return set()
    return set(re.findall(r"[a-z]+", text.lower())) - STOPWORDS


def _collect_duty_text(wd: WorkDescription) -> str:
    """Concatenate all confirmed duty text (draft_duties + advisor_additions).

    Source: wd.draft_duties (LLM-generated, NOC-sourced) and
    wd.advisor_additions (advisor-entered). Both lists of DraftDuty.
    """
    parts: list[str] = []
    for duty in wd.draft_duties or []:
        if duty.text:
            parts.append(duty.text)
    for duty in wd.advisor_additions or []:
        if duty.text:
            parts.append(duty.text)
    return " ".join(parts)


def _score_drf_rows(drf_rows: list, duty_tokens: set[str]) -> list[dict]:
    """Build candidate dicts for drf_rows with at least 1 overlapping token.

    Each candidate dict:
        id: int (drf_rows.id)
        core_responsibility: str
        departmental_result: str
        fiscal_year: str
        score: int (overlap token count; >= 1)

    Returns candidates sorted descending by score (ties broken by id ascending
    for deterministic ordering in tests). Capped to the top 5 candidates
    (Plan 09-04, revised inline design) so the wizard panel shows the
    most-relevant matches rather than the entire scored list.
    """
    candidates: list[dict] = []
    for row in drf_rows:
        row_tokens = _tokenize(row["search_text"])
        overlap = duty_tokens & row_tokens
        if overlap:
            candidates.append(
                {
                    "id": int(row["id"]),
                    "core_responsibility": row["core_responsibility"],
                    "departmental_result": row["departmental_result"],
                    "fiscal_year": row["fiscal_year"],
                    "score": len(overlap),
                }
            )
    candidates.sort(key=lambda c: (-c["score"], c["id"]))
    return candidates[:5]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_drf_candidates(wd_id: str, db_path: str) -> dict:
    """Return DRF program linkage candidates for a WorkDescription's duties.

    Algorithm:
        1. Load the WorkDescription. Raise ValueError("not found") if missing.
        2. If is_dnd_position is False, return candidates=[] (no error).
        3. Load all drf_rows from the DB.
        4. Tokenize combined duty text (draft_duties + advisor_additions)
           and remove STOPWORDS.
        5. For each drf_row, count tokens in search_text that appear in the
           duty token set. Keep rows with score >= 1.
        6. Sort candidates descending by score. Return the result dict.

    Returns:
        dict: {wd_id, is_dnd_position, candidates: [list of candidate dicts]}

    Raises:
        ValueError: if wd_id does not exist in the work_descriptions table.
    """
    conn = await asyncio.to_thread(lambda: get_connection(db_path))
    try:
        # 1. Load WD (raises ValueError if missing)
        wd: WorkDescription | None = await asyncio.to_thread(
            lambda: load_work_description(conn, wd_id)
        )
        if wd is None:
            raise ValueError(f"WorkDescription {wd_id!r} not found")

        result: dict = {
            "wd_id": wd_id,
            "is_dnd_position": wd.is_dnd_position,
            "candidates": [],
        }

        # 2. Short-circuit for non-DND positions (Pitfall: never raise here)
        if not wd.is_dnd_position:
            return result

        # 3. Load all drf_rows
        drf_rows = await asyncio.to_thread(
            lambda: conn.execute(
                "SELECT id, fiscal_year, core_responsibility, "
                "departmental_result, search_text FROM drf_rows"
            ).fetchall()
        )

        # 4. Tokenize duty text (and drop stopwords)
        duty_text = _collect_duty_text(wd)
        duty_tokens = _tokenize(duty_text)

        # 5 + 6. Score, filter (score >= 1), sort
        result["candidates"] = _score_drf_rows(list(drf_rows), duty_tokens)

        return result

    finally:
        await asyncio.to_thread(conn.close)


async def confirm_drf_linkages(
    wd_id: str, row_ids: list[int], db_path: str
) -> dict:
    """Store advisor-confirmed DRF linkages on the WorkDescription.

    For each row_id, fetches the drf_rows record and appends a dict to
    wd.drf_linkages. Replaces any existing drf_linkages (idempotent re-confirm).
    Saves the WD with save_work_description. Stage is NOT advanced.

    Each linkage dict:
        core_responsibility: str
        departmental_result: str
        fiscal_year: str
        row_index: int  (= drf_rows.id)
        confirmed: True
        provenance_source_id: str  (= "DRF/" + str(drf_rows.id))

    Unknown row_ids (not in drf_rows) are silently skipped with a warning log
    rather than raising — per T-09-06 mitigation in the plan's threat model
    (Tampering of row_ids from untrusted form POSTs).

    Returns:
        dict: {wd_id, confirmed_count, drf_linkages: list[dict]}

    Raises:
        ValueError: if wd_id does not exist in the work_descriptions table.
    """
    conn = await asyncio.to_thread(lambda: get_connection(db_path))
    try:
        # 1. Load WD (raises ValueError if missing)
        wd: WorkDescription | None = await asyncio.to_thread(
            lambda: load_work_description(conn, wd_id)
        )
        if wd is None:
            raise ValueError(f"WorkDescription {wd_id!r} not found")

        # 1a. Defensive: empty row_ids is a no-op, not a wipe (WR-03).
        # Prevents silent data loss if the client posts an empty list due to
        # a JS bug or unintended click. Use a separate "Clear Linkages" UX
        # path (not yet implemented) to explicitly clear drf_linkages.
        if not row_ids:
            existing = wd.drf_linkages or []
            return {
                "wd_id": wd_id,
                "confirmed_count": sum(1 for l in existing if l.get("confirmed")),
                "drf_linkages": existing,
            }

        # 2. Build linkages from drf_rows (one SELECT per row_id)
        linkages: list[dict] = []
        for row_id in row_ids:
            # Capture row_id in default arg to avoid late-binding closure bug
            row = await asyncio.to_thread(
                lambda rid=row_id: conn.execute(
                    "SELECT id, fiscal_year, core_responsibility, "
                    "departmental_result FROM drf_rows WHERE id = ?",
                    (rid,),
                ).fetchone()
            )
            if row is None:
                logger.warning(
                    "confirm_drf_linkages: row_id %d not found in drf_rows — skipping",
                    row_id,
                )
                continue
            linkages.append(
                {
                    "core_responsibility": row["core_responsibility"],
                    "departmental_result": row["departmental_result"],
                    "fiscal_year": row["fiscal_year"],
                    "row_index": int(row["id"]),
                    "confirmed": True,
                    "provenance_source_id": f"DRF/{int(row['id'])}",
                }
            )

        # 3. Replace existing drf_linkages (idempotent re-confirm) and save
        updated_wd = wd.model_copy(update={"drf_linkages": linkages})
        await asyncio.to_thread(lambda: save_work_description(conn, updated_wd))

        return {
            "wd_id": wd_id,
            "confirmed_count": len(linkages),
            "drf_linkages": linkages,
        }

    finally:
        await asyncio.to_thread(conn.close)
