"""
app/services/jd_service.py — JD generation pipeline service functions.

Four public functions:
  generate_duties(wd_id, db_path) — load NOC candidates → LLM selection → DB reconstruction guardrail → save WD
  check_orphan_statements(wd_id, db_path) — load duties + OG rules → LLM orphan check → return OrphanCheckResult
  add_advisor_duty(wd_id, duty_text, db_path) — add advisor-entered duty to advisor_additions
  confirm_duties(wd_id, db_path) — set stage='jd_drafted' + save WD

Architecture non-negotiables (JD-01):
  - LLM returns row IDs; server reads element_text from DB to build DraftDuty
  - candidate_map guardrail: any row_id not in pre-loaded candidate set is dropped silently
  - generate_duties() preserves advisor_additions — never clears them on re-generate
  - stage='jd_drafted' is set ONLY in confirm_duties(), never in generate_duties()
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date

from app.ai.jd_ranking import (
    DUTY_SELECTION_SYSTEM_PROMPT,
    ORPHAN_CHECK_SYSTEM_PROMPT,
    DutyRankingResult,
    OrphanCheckResult,
    get_noc_version_info,
    jd_instructor_client,
)
from app.config import settings
from app.db import get_connection
from app.models.work_description import DraftDuty, ProvenanceTag, WorkDescription
from app.services.wd_store import load_work_description, save_work_description

logger = logging.getLogger(__name__)

# Maximum length for advisor-entered duty text
_ADVISOR_DUTY_MAX_LEN = 500


def _build_duty_from_row(row, confirmed_noc: str, noc_version: str) -> DraftDuty:
    """
    Construct a DraftDuty from a noc_elements row.
    Text and source_hash come from the DB row — never from the LLM response (JD-01).
    """
    return DraftDuty(
        text=row["element_text"],
        provenance=ProvenanceTag(
            source_type="NOC",
            source_id=confirmed_noc,
            source_version=noc_version,
            retrieved_date=date.today(),
        ),
        advisor_modified=False,
    )


def _build_advisor_duty(text: str) -> DraftDuty:
    """
    Construct a DraftDuty for advisor-entered content (JD-03).
    source_type='ADVISOR'; goes into advisor_additions, not draft_duties.
    """
    return DraftDuty(
        text=text[:_ADVISOR_DUTY_MAX_LEN],
        provenance=ProvenanceTag(
            source_type="ADVISOR",
            source_id="advisor-input",
            source_version="advisor-added",
            retrieved_date=date.today(),
        ),
        advisor_modified=False,
    )


async def generate_duties(wd_id: str, db_path: str) -> dict:
    """
    Three-step duty selection pipeline:
      1. Load noc_elements Main duties rows for confirmed NOC code
      2. LLM selects relevant row IDs (DutyRankingResult)
      3. Reconstruct duties from DB rows — never from LLM text echo

    Returns:
        {"duties": list[dict], "selection_rationale": str}
        where each duty dict has: text, source_type, source_id, source_version

    Raises:
        ValueError: if WorkDescription not found, stage invalid, or confirmed_noc is None
    """
    conn = await asyncio.to_thread(lambda: get_connection(db_path))
    try:
        wd = await asyncio.to_thread(lambda: load_work_description(conn, wd_id))
        if wd is None:
            raise ValueError(f"WorkDescription {wd_id!r} not found")
        if wd.stage != "og_classified":
            raise ValueError(
                f"WorkDescription is in stage {wd.stage!r}, expected 'og_classified'"
            )
        if wd.confirmed_noc is None:
            raise ValueError("WorkDescription has no confirmed NOC — complete NOC mapping first")
        if wd.confirmed_og is None:
            raise ValueError("WorkDescription has no confirmed OG — complete OG classification first")

        confirmed_noc = str(wd.confirmed_noc.noc_code)
        confirmed_og = wd.confirmed_og

        # Step 1: Load NOC duty candidates from DB
        candidate_rows = await asyncio.to_thread(
            lambda: conn.execute(
                "SELECT id, element_text, source_hash FROM noc_elements "
                "WHERE noc_code = ? AND element_type = 'Main duties' "
                "ORDER BY id",
                (confirmed_noc,),
            ).fetchall()
        )
        if not candidate_rows:
            raise ValueError(
                f"No 'Main duties' rows found for NOC {confirmed_noc!r} in noc_elements. "
                "Run scripts/ingest_noc.py first."
            )

        # Build candidate map: {row_id: row} for guardrail lookup
        candidate_map = {row["id"]: row for row in candidate_rows}

        # Numbered list for LLM prompt
        numbered = "\n".join(
            f"[{row['id']}] {row['element_text']}" for row in candidate_rows
        )

        # Load OG name for prompt
        og_row = await asyncio.to_thread(
            lambda: conn.execute(
                "SELECT og_name FROM og_definitions WHERE og_code = ? LIMIT 1",
                (confirmed_og,),
            ).fetchone()
        )
        og_name = og_row["og_name"] if og_row else confirmed_og

        # Get NOC version info for ProvenanceTag
        noc_version, _ = await asyncio.to_thread(lambda: get_noc_version_info(conn))

        # Build user prompt
        user_prompt = (
            f"Confirmed NOC: {confirmed_noc}\n"
            f"Confirmed OG: {confirmed_og} — {og_name}\n"
            f"Work Description: {wd.raw_input[:500]}\n\n"
            f"Available duty statements (select by row_id only):\n{numbered}"
        )

        # Step 2: LLM duty selection
        extra_kwargs: dict = {}
        if not settings.cloud_api_key:
            extra_kwargs["extra_body"] = {"options": {"num_ctx": 8192}}

        ranking_result: DutyRankingResult = await jd_instructor_client.chat.completions.create(
            model=settings.generation_model,
            messages=[
                {
                    "role": "system",
                    "content": DUTY_SELECTION_SYSTEM_PROMPT.format(
                        og_name=og_name, og_code=confirmed_og
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
            response_model=DutyRankingResult,
            max_retries=3,
            max_tokens=2048,
            temperature=0.0,
            **extra_kwargs,
        )

        # Step 3: Reconstruct duties from DB — guardrail: only IDs in candidate_map
        draft_duties: list[DraftDuty] = []
        for selection in sorted(ranking_result.selections, key=lambda s: s.rank):
            row_id = selection.row_id
            if row_id not in candidate_map:
                logger.warning(
                    "LLM returned row_id %d which is not in candidate set for NOC %s — dropping",
                    row_id, confirmed_noc,
                )
                continue
            row = candidate_map[row_id]
            draft_duties.append(_build_duty_from_row(row, confirmed_noc, noc_version))

        if not draft_duties:
            raise ValueError(
                "All LLM-selected row IDs were invalid (not in candidate set for this NOC). "
                "Check DUTY_SELECTION_SYSTEM_PROMPT and candidate list format."
            )

        # Preserve existing advisor_additions — never clear them on re-generate (Pitfall 5)
        existing_advisor_additions = wd.advisor_additions

        # Save WD with updated draft_duties; stage stays 'og_classified' until confirm_duties()
        updated_wd = wd.model_copy(
            update={
                "draft_duties": draft_duties,
                "advisor_additions": existing_advisor_additions,
                # stage intentionally NOT changed here — set only at confirm_duties()
            }
        )
        await asyncio.to_thread(lambda: save_work_description(conn, updated_wd))

    finally:
        await asyncio.to_thread(conn.close)

    return {
        "duties": [
            {
                "id": str(d.id),
                "text": d.text,
                "source_type": d.provenance.source_type,
                "source_id": d.provenance.source_id,
                "source_version": d.provenance.source_version,
            }
            for d in draft_duties
        ],
        "selection_rationale": ranking_result.selection_rationale,
        "wd_id": wd_id,
    }


async def check_orphan_statements(wd_id: str, db_path: str) -> OrphanCheckResult:
    """
    Orphan statement check pipeline:
      - Load WD draft_duties + advisor_additions
      - Load OG exclusion/inclusion rules from og_definitions
      - LLM checks all duties in one call (OrphanCheckResult)
      - Verify each rule_violated is a substring of og_full_text (fabrication guardrail)
      - Return OrphanCheckResult — empty flags = clean result (JD-04)

    Accepts stage 'og_classified' OR 'jd_drafted' (check can run before or after confirmation).

    Raises:
        ValueError: if WD not found or stage is invalid for orphan check
    """
    conn = await asyncio.to_thread(lambda: get_connection(db_path))
    try:
        wd = await asyncio.to_thread(lambda: load_work_description(conn, wd_id))
        if wd is None:
            raise ValueError(f"WorkDescription {wd_id!r} not found")
        if wd.stage not in ("og_classified", "jd_drafted"):
            raise ValueError(
                f"WorkDescription is in stage {wd.stage!r}, "
                "expected 'og_classified' or 'jd_drafted' for orphan check"
            )
        if wd.confirmed_og is None:
            raise ValueError("WorkDescription has no confirmed OG — complete OG classification first")

        confirmed_og = wd.confirmed_og

        # Collect all duties to check
        all_duties = list(wd.draft_duties) + list(wd.advisor_additions)
        if not all_duties:
            return OrphanCheckResult(
                flags=[],
                summary=f"No duties to check for {confirmed_og}.",
            )

        # Load OG rules from og_definitions
        og_row = await asyncio.to_thread(
            lambda: conn.execute(
                "SELECT og_name, definition, inclusions, exclusions "
                "FROM og_definitions WHERE og_code = ? LIMIT 1",
                (confirmed_og,),
            ).fetchone()
        )
        if og_row is None:
            logger.warning(
                "No og_definitions row found for og_code=%r — returning empty orphan check result",
                confirmed_og,
            )
            return OrphanCheckResult(
                flags=[],
                summary=f"No functional authority rules found for {confirmed_og} — check skipped.",
            )

        og_name = og_row["og_name"]
        # PE and some OGs have inclusions=NULL; fall back to definition column (Pitfall 3)
        og_inclusions = og_row["inclusions"] or og_row["definition"] or ""
        og_exclusions = og_row["exclusions"] or ""

        # Build full text for fabrication guardrail
        og_full_text = " ".join(filter(None, [og_row["definition"], og_inclusions, og_exclusions]))

        # Build duty list for LLM prompt
        duties_text = "\n".join(
            f"{i + 1}. {d.text}" for i, d in enumerate(all_duties)
        )

        # LLM orphan check — all duties in one call
        extra_kwargs: dict = {}
        if not settings.cloud_api_key:
            extra_kwargs["extra_body"] = {"options": {"num_ctx": 8192}}

        orphan_result: OrphanCheckResult = await jd_instructor_client.chat.completions.create(
            model=settings.generation_model,
            messages=[
                {
                    "role": "system",
                    "content": ORPHAN_CHECK_SYSTEM_PROMPT.format(
                        og_name=og_name,
                        og_code=confirmed_og,
                        og_exclusions=og_exclusions[:800] or "(none defined)",
                        og_inclusions=og_inclusions[:800] or "(none defined)",
                    ),
                },
                {
                    "role": "user",
                    "content": f"Review the following duties for {confirmed_og} classification correctness:\n\n{duties_text}",
                },
            ],
            response_model=OrphanCheckResult,
            max_retries=3,
            max_tokens=2048,
            temperature=0.0,
            **extra_kwargs,
        )

        # Fabrication guardrail: verify rule_violated is a substring of og_full_text
        verified_flags = []
        for flag in orphan_result.flags:
            if flag.rule_violated and flag.rule_violated in og_full_text:
                verified_flags.append(flag)
            else:
                logger.warning(
                    "OrphanFlag.rule_violated %r is not a substring of og_definitions text — dropping flag",
                    flag.rule_violated[:80],
                )

        return OrphanCheckResult(
            flags=verified_flags,
            summary=orphan_result.summary if verified_flags else f"No orphan statements detected for {confirmed_og}.",
        )

    finally:
        await asyncio.to_thread(conn.close)


async def add_advisor_duty(wd_id: str, duty_text: str, db_path: str) -> dict:
    """
    Add an advisor-entered duty to WorkDescription.advisor_additions (JD-03).
    duty_text is truncated to 500 characters. source_type='ADVISOR'.

    Returns:
        {"wd_id": str, "advisor_additions_count": int}

    Raises:
        ValueError: if WD not found or stage is not og_classified or jd_drafted
    """
    if not duty_text or not duty_text.strip():
        raise ValueError("duty_text must not be empty")

    conn = await asyncio.to_thread(lambda: get_connection(db_path))
    try:
        wd = await asyncio.to_thread(lambda: load_work_description(conn, wd_id))
        if wd is None:
            raise ValueError(f"WorkDescription {wd_id!r} not found")
        if wd.stage not in ("og_classified", "jd_drafted"):
            raise ValueError(
                f"WorkDescription is in stage {wd.stage!r}, "
                "expected 'og_classified' or 'jd_drafted' for advisor duty addition"
            )

        new_duty = _build_advisor_duty(duty_text.strip())
        updated_additions = list(wd.advisor_additions) + [new_duty]
        updated_wd = wd.model_copy(update={"advisor_additions": updated_additions})
        await asyncio.to_thread(lambda: save_work_description(conn, updated_wd))

    finally:
        await asyncio.to_thread(conn.close)

    return {"wd_id": wd_id, "advisor_additions_count": len(updated_additions)}


async def confirm_duties(wd_id: str, db_path: str) -> dict:
    """
    Confirm the current duty list and set stage='jd_drafted' (JD-01+JD-02+JD-03).

    This is the ONLY function that sets stage='jd_drafted'. generate_duties() does NOT
    set this stage to avoid the stage-too-early pitfall (Pitfall 4 in RESEARCH.md).

    Returns:
        {"wd_id": str, "stage": "jd_drafted", "duty_count": int}

    Raises:
        ValueError: if WD not found or stage is not og_classified
    """
    conn = await asyncio.to_thread(lambda: get_connection(db_path))
    try:
        wd = await asyncio.to_thread(lambda: load_work_description(conn, wd_id))
        if wd is None:
            raise ValueError(f"WorkDescription {wd_id!r} not found")
        if wd.stage != "og_classified":
            raise ValueError(
                f"WorkDescription is in stage {wd.stage!r}, expected 'og_classified' for duty confirmation"
            )

        total_duties = len(wd.draft_duties) + len(wd.advisor_additions)
        updated_wd = wd.model_copy(update={"stage": "jd_drafted"})
        await asyncio.to_thread(lambda: save_work_description(conn, updated_wd))

    finally:
        await asyncio.to_thread(conn.close)

    return {
        "wd_id": wd_id,
        "stage": "jd_drafted",
        "duty_count": total_duties,
    }
