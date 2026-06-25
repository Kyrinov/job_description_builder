"""
app/services/jes_service.py — Per-factor JES scoring pipeline.

Public API:
    score_jes(wd_id, db_path) -> dict
    async retry_jes_factor(wd_id, factor_name, db_path) -> dict
    def override_jes_factor(wd_id, factor_name, *, level, points, rationale, db_path) -> dict

Architecture:
    - One jes_instructor_client call per JES factor (no array-collapse — STATE.md non-negotiable)
    - Sequential calls (not asyncio.gather) to avoid Ollama OOM on ARM64
    - Failed factor → JESFactorScore(level=-1, ...) sentinel, NOT raised exception
    - Stage gate: wd.stage must == 'jd_drafted'; advances to 'jes_scored' after all factors
    - retry_jes_factor: re-runs the LLM for ONE factor; preserves old score on LLM failure
    - override_jes_factor: SYNC; sets advisor_adjusted fields, flips provenance to ADVISOR

Direct analog: app/services/jd_service.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import date
from typing import Optional

from app.ai.jes_scoring import (
    JES_SCORING_SYSTEM_PROMPT,
    JESFactorRating,
    get_jes_version_info,
    jes_instructor_client,
)
from app.config import settings
from app.db import get_connection
from app.models.work_description import JESFactorScore, ProvenanceTag, WorkDescription
from app.services.wd_store import load_work_description, save_work_description

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_factor_user_prompt(
    factor_row, duties: list, work_description_raw: str
) -> str:
    """Build the per-factor user prompt injecting full degree definitions from DB row.

    CRITICAL: json.loads(factor_row["degree_descriptors"]) — stored as JSON TEXT.
    Truncates duties to top 10 and raw_input to 300 chars to stay within num_ctx=8192.
    """
    degrees = json.loads(factor_row["degree_descriptors"])
    degree_text = "\n".join(
        f"  {d['degree']} ({d.get('points', '?')} pts): {d['text']}"
        for d in degrees
    )
    duties_text = "\n".join(f"{i + 1}. {d}" for i, d in enumerate(duties[:10]))
    return (
        f"Factor: {factor_row['factor_name']}\n"
        f"Definition: {factor_row['factor_definition'] or '(none)'}\n\n"
        f"Degree Definitions:\n{degree_text}\n\n"
        f"Position duties:\n{duties_text}\n\n"
        f"Work description: {work_description_raw[:300]}\n\n"
        "Select the degree that best fits this position and provide a rationale."
    )


def _resolve_degree(degree_str: str, point_values: dict) -> tuple[str, Optional[int]]:
    """Return (canonical_key, points) by normalizing degree_str to match point_values keys.

    LLMs sometimes return "D3" when the DB key is "3", or "3" when the key is "D3".
    Try: exact → strip-D → add-D, in order. Return (degree_str, None) if no match.
    """
    if degree_str in point_values:
        return degree_str, point_values[degree_str]
    stripped = degree_str.lstrip("D").strip()
    if stripped in point_values:
        return stripped, point_values[stripped]
    with_d = "D" + stripped
    if with_d in point_values:
        return with_d, point_values[with_d]
    return degree_str, None


def _build_jes_factor_score(
    factor_row,
    rating: JESFactorRating,
    og_code: str,
    jes_version: str,
) -> JESFactorScore:
    """Map a successful JESFactorRating to a JESFactorScore with ProvenanceTag.

    Normalizes the returned degree string against point_values keys so that
    "3" and "D3" are treated as equivalent (LLMs mix formats due to prompt examples).
    level = leading integer extracted from the canonical key; -1 if unparseable.
    """
    point_values: dict = json.loads(factor_row["point_values"])
    canonical_key, points = _resolve_degree(rating.degree, point_values)
    if points is None:
        logger.warning(
            "JES factor %r/%r returned degree %r (canonical: %r) but point_values has no match — "
            "factor will contribute 0 to total",
            og_code, factor_row["factor_name"], rating.degree, canonical_key,
        )
    m = re.search(r"\d+", canonical_key)
    level = int(m.group()) if m else -1

    return JESFactorScore(
        factor_name=factor_row["factor_name"],
        level=level,
        points=points,
        rationale=rating.rationale,
        provenance=ProvenanceTag(
            source_type="JES",
            source_id=f"{og_code}/{factor_row['factor_name']}",
            source_version=jes_version,
            retrieved_date=date.today(),
        ),
    )


def _make_error_score(
    factor_row, og_code: str, jes_version: str, exc: Exception
) -> JESFactorScore:
    """Produce a sentinel JESFactorScore(level=-1) for a factor that failed after 3 retries.

    level=-1 is the sentinel for 'scoring failed'. JESFactorScore.level is int (non-optional)
    so None is not valid — Pydantic would raise a ValidationError.
    """
    return JESFactorScore(
        factor_name=factor_row["factor_name"],
        level=-1,
        points=None,
        rationale=f"Scoring failed after 3 retries: {exc}",
        provenance=ProvenanceTag(
            source_type="JES",
            source_id=f"{og_code}/{factor_row['factor_name']}",
            source_version=jes_version,
            retrieved_date=date.today(),
        ),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def score_jes(wd_id: str, db_path: str) -> dict:
    """Run per-factor JES scoring pipeline for a confirmed WorkDescription.

    Requirements:
        - wd.stage == 'jd_drafted' (raises ValueError otherwise)
        - wd.confirmed_og is not None (raises ValueError otherwise)
        - jes_factors rows exist for confirmed_og (raises ValueError if empty)

    Returns:
        dict with keys: wd_id, jes_scores (list[dict]), jes_total_points (int), factor_count (int)
    """
    conn = await asyncio.to_thread(lambda: get_connection(db_path))
    try:
        # 1. Load and validate WorkDescription
        wd: WorkDescription | None = await asyncio.to_thread(
            lambda: load_work_description(conn, wd_id)
        )
        if wd is None:
            raise ValueError(f"WorkDescription {wd_id!r} not found")
        if wd.stage != "jd_drafted":
            raise ValueError(
                f"WorkDescription is in stage {wd.stage!r}, expected 'jd_drafted'"
            )
        if wd.confirmed_og is None:
            raise ValueError(
                "WorkDescription has no confirmed OG — complete OG classification first"
            )

        confirmed_og: str = wd.confirmed_og

        # 2. Load JES factors for this OG
        factor_rows = await asyncio.to_thread(
            lambda: conn.execute(
                "SELECT id, factor_name, factor_definition, degree_descriptors, "
                "point_values, max_points, source_hash "
                "FROM jes_factors WHERE og_code = ? ORDER BY id",
                (confirmed_og,),
            ).fetchall()
        )
        if not factor_rows:
            raise ValueError(
                f"No JES factors found for OG {confirmed_og!r} — check jes_factors table"
            )

        # 3. Get JES version info for ProvenanceTag
        jes_version_label, _jes_hash = get_jes_version_info(conn, confirmed_og)

        # 4. Get OG name for system prompt (fallback to og_code if not found)
        og_name_row = await asyncio.to_thread(
            lambda: conn.execute(
                "SELECT og_name FROM og_definitions WHERE og_code = ? LIMIT 1",
                (confirmed_og,),
            ).fetchone()
        )
        og_name = og_name_row["og_name"] if og_name_row else confirmed_og

        # 5. Build duty text list from draft_duties
        duties: list[str] = [d.text for d in (wd.draft_duties or [])]

        # 6. Per-factor scoring loop (sequential — not asyncio.gather; avoids Ollama OOM)
        extra_kwargs: dict = {}
        if not settings.cloud_api_key:
            extra_kwargs["extra_body"] = {"options": {"num_ctx": 8192}}

        jes_scores: list[JESFactorScore] = []
        for factor_row in factor_rows:
            user_prompt = _build_factor_user_prompt(factor_row, duties, wd.raw_input)
            try:
                factor_rating: JESFactorRating = await jes_instructor_client.chat.completions.create(
                    model=settings.generation_model,
                    messages=[
                        {
                            "role": "system",
                            "content": JES_SCORING_SYSTEM_PROMPT.format(
                                og_name=og_name, og_code=confirmed_og
                            ),
                        },
                        {"role": "user", "content": user_prompt},
                    ],
                    response_model=JESFactorRating,
                    max_retries=3,
                    max_tokens=1024,
                    temperature=0.0,
                    **extra_kwargs,
                )
                score = _build_jes_factor_score(
                    factor_row, factor_rating, confirmed_og, jes_version_label
                )
            except Exception as exc:
                logger.warning(
                    "JES factor scoring failed for %r/%r after 3 retries: %s",
                    confirmed_og, factor_row["factor_name"], exc,
                )
                score = _make_error_score(factor_row, confirmed_og, jes_version_label, exc)

            jes_scores.append(score)

        # 7. Compute total points (exclude failed factors with level=-1 / points=None)
        jes_total = sum(s.points for s in jes_scores if s.points is not None)

        # 8. Advance stage ONLY after all factors collected
        updated_wd = wd.model_copy(
            update={
                "jes_scores": jes_scores,
                "jes_total_points": jes_total,
                "stage": "jes_scored",
            }
        )
        await asyncio.to_thread(lambda: save_work_description(conn, updated_wd))

        return {
            "wd_id": str(wd.id),
            "jes_scores": [s.model_dump() for s in jes_scores],
            "jes_total_points": jes_total,
            "factor_count": len(jes_scores),
        }

    finally:
        await asyncio.to_thread(conn.close)


# ---------------------------------------------------------------------------
# Per-factor recovery: retry (async) + override (sync)
# (Phase 08.1 — closes the gap where blocked exports had no recovery path)
# ---------------------------------------------------------------------------


async def retry_jes_factor(
    wd_id: str, factor_name: str, db_path: str
) -> dict:
    """Re-run the LLM scoring call for a single JES factor and replace its score in the WD.

    On LLM success: the new score replaces the old one in wd.jes_scores (order-preserved),
    wd.jes_total_points is recomputed, the WD is saved (stage unchanged: still 'jes_scored').

    On LLM failure: the old score is preserved (retry does not lose progress) and the
    function raises the failure reason — caller (route handler) maps to HTTP 422.

    Validation:
        - wd_id exists (raises ValueError otherwise)
        - wd.stage == 'jes_scored' (raises ValueError otherwise)
        - factor_name is present in wd.jes_scores (raises ValueError otherwise)
        - wd.confirmed_og is set (raises ValueError otherwise)
        - jes_factors row exists for (wd.confirmed_og, factor_name) (raises ValueError otherwise)

    Returns:
        dict with keys: wd_id, factor_name, score (JESFactorScore), jes_total_points (int),
        level (int), points (Optional[int])
    """
    conn = await asyncio.to_thread(lambda: get_connection(db_path))
    try:
        # 1. Load and validate WorkDescription
        wd: WorkDescription | None = await asyncio.to_thread(
            lambda: load_work_description(conn, wd_id)
        )
        if wd is None:
            raise ValueError(f"WorkDescription {wd_id!r} not found")
        if wd.stage != "jes_scored":
            raise ValueError(
                f"WorkDescription is in stage {wd.stage!r}, expected 'jes_scored'"
            )
        if wd.confirmed_og is None:
            raise ValueError(
                "WorkDescription has no confirmed OG — complete OG classification first"
            )

        confirmed_og: str = wd.confirmed_og

        # 2. Find the factor index in wd.jes_scores (preserve order on replace)
        factor_index: int | None = None
        for i, s in enumerate(wd.jes_scores):
            if s.factor_name == factor_name:
                factor_index = i
                break
        if factor_index is None:
            raise ValueError(
                f"JES factor {factor_name!r} not found in WorkDescription"
            )

        # 3. Re-fetch the single factor row from jes_factors
        factor_row = await asyncio.to_thread(
            lambda: conn.execute(
                "SELECT id, factor_name, factor_definition, degree_descriptors, "
                "point_values, max_points, source_hash "
                "FROM jes_factors WHERE og_code = ? AND factor_name = ? LIMIT 1",
                (confirmed_og, factor_name),
            ).fetchone()
        )
        if factor_row is None:
            raise ValueError(
                f"No JES factor row for {factor_name!r} in OG {confirmed_og!r}"
            )

        # 4. Get JES version info for ProvenanceTag
        jes_version_label, _jes_hash = get_jes_version_info(conn, confirmed_og)

        # 5. Get OG name for system prompt (fallback to og_code if not found)
        og_name_row = await asyncio.to_thread(
            lambda: conn.execute(
                "SELECT og_name FROM og_definitions WHERE og_code = ? LIMIT 1",
                (confirmed_og,),
            ).fetchone()
        )
        og_name = og_name_row["og_name"] if og_name_row else confirmed_og

        # 6. Build duty text list from draft_duties
        duties: list[str] = [d.text for d in (wd.draft_duties or [])]

        # 7. Per-factor scoring call (mirrors score_jes lines 195-214)
        extra_kwargs: dict = {}
        if not settings.cloud_api_key:
            extra_kwargs["extra_body"] = {"options": {"num_ctx": 8192}}

        user_prompt = _build_factor_user_prompt(factor_row, duties, wd.raw_input)
        try:
            factor_rating: JESFactorRating = await jes_instructor_client.chat.completions.create(
                model=settings.generation_model,
                messages=[
                    {
                        "role": "system",
                        "content": JES_SCORING_SYSTEM_PROMPT.format(
                            og_name=og_name, og_code=confirmed_og
                        ),
                    },
                    {"role": "user", "content": user_prompt},
                ],
                response_model=JESFactorRating,
                max_retries=3,
                max_tokens=1024,
                temperature=0.0,
                **extra_kwargs,
            )
            score = _build_jes_factor_score(
                factor_row, factor_rating, confirmed_og, jes_version_label
            )
        except Exception as exc:
            # On LLM failure: preserve the old score (do NOT replace it) and raise
            logger.warning(
                "JES retry failed for %r/%r after 3 retries: %s",
                confirmed_og, factor_name, exc,
            )
            raise ValueError(
                f"Retry failed for {factor_name!r}: {exc}"
            ) from exc

        # 8. Replace the old score in wd.jes_scores (preserve order)
        new_scores: list[JESFactorScore] = list(wd.jes_scores)
        new_scores[factor_index] = score

        # 9. Recompute jes_total_points (exclude failed factors with points=None)
        new_total = sum(s.points for s in new_scores if s.points is not None)

        # 10. Save the WD (stage unchanged — still 'jes_scored')
        updated_wd = wd.model_copy(
            update={
                "jes_scores": new_scores,
                "jes_total_points": new_total,
            }
        )
        await asyncio.to_thread(lambda: save_work_description(conn, updated_wd))

        return {
            "wd_id": str(wd.id),
            "factor_name": factor_name,
            "score": score,
            "jes_total_points": new_total,
            "level": score.level,
            "points": score.points,
        }

    finally:
        await asyncio.to_thread(conn.close)


def override_jes_factor(
    wd_id: str,
    factor_name: str,
    *,
    level: int,
    points: Optional[int],
    rationale: str,
    db_path: str,
) -> dict:
    """Manually set level + points + rationale for one JES factor; record as advisor override.

    Sets advisor_adjusted=True, advisor_adjusted_level=level,
    advisor_adjustment_rationale=rationale, and flips provenance.source_type to
    "ADVISOR" (with retrieved_date=date.today() and modified_by_advisor=True).
    Recomputes jes_total_points and saves the WD (stage unchanged: still 'jes_scored').

    Validation:
        - level is an int >= 1
        - rationale is a string with len(strip()) >= 10 chars
        - wd_id exists
        - wd.stage == 'jes_scored'
        - factor_name is present in wd.jes_scores
        - wd.confirmed_og is set

    Returns:
        dict with keys: wd_id, factor_name, score (JESFactorScore), jes_total_points (int)
    """
    if not isinstance(level, int) or level < 1:
        raise ValueError(f"level must be an int >= 1, got {level!r}")
    if not isinstance(rationale, str) or len(rationale.strip()) < 10:
        raise ValueError(
            f"rationale must be at least 10 characters, got {len(rationale.strip())} chars"
        )

    conn = get_connection(db_path)
    try:
        # 1. Load and validate WorkDescription
        wd: WorkDescription | None = load_work_description(conn, wd_id)
        if wd is None:
            raise ValueError(f"WorkDescription {wd_id!r} not found")
        if wd.stage != "jes_scored":
            raise ValueError(
                f"WorkDescription is in stage {wd.stage!r}, expected 'jes_scored'"
            )
        if wd.confirmed_og is None:
            raise ValueError(
                "WorkDescription has no confirmed OG — complete OG classification first"
            )

        # 2. Find the factor index in wd.jes_scores (preserve order on replace)
        factor_index: int | None = None
        for i, s in enumerate(wd.jes_scores):
            if s.factor_name == factor_name:
                factor_index = i
                break
        if factor_index is None:
            raise ValueError(
                f"JES factor {factor_name!r} not found in WorkDescription"
            )

        og_code: str = wd.confirmed_og

        # 3. Build the new JESFactorScore with advisor-adjusted fields and ADVISOR provenance
        new_score = JESFactorScore(
            factor_name=factor_name,
            level=level,
            points=points,
            rationale=rationale.strip(),
            provenance=ProvenanceTag(
                source_type="ADVISOR",
                source_id=f"{og_code}/{factor_name}",
                source_version="advisor manual override",
                retrieved_date=date.today(),
                modified_by_advisor=True,
            ),
            advisor_adjusted=True,
            advisor_adjusted_level=level,
            advisor_adjustment_rationale=rationale.strip(),
        )

        # 4. Replace the old score in wd.jes_scores (preserve order)
        new_scores: list[JESFactorScore] = list(wd.jes_scores)
        new_scores[factor_index] = new_score

        # 5. Recompute jes_total_points (exclude factors with points=None — e.g., effort)
        new_total = sum(s.points for s in new_scores if s.points is not None)

        # 6. Save the WD (stage unchanged — still 'jes_scored')
        updated_wd = wd.model_copy(
            update={
                "jes_scores": new_scores,
                "jes_total_points": new_total,
            }
        )
        save_work_description(conn, updated_wd)

        return {
            "wd_id": str(wd.id),
            "factor_name": factor_name,
            "score": new_score,
            "jes_total_points": new_total,
        }

    finally:
        conn.close()
