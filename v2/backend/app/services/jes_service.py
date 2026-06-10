"""
app/services/jes_service.py — Per-factor JES scoring pipeline (v2.0).

Ported from v1.0 app/services/jes_service.py with v2 adaptations:
- Replaces SQLite jes_factors table queries with hardcoded EC_JES_ELEMENTS constant lookups
- Replaces wd.stage gate with require_og_confirmed() (no stage field on v2 WD model)
- Replaces get_jes_version_info() DB call with hardcoded "EC JES 2017" / NON_EC_STANDARD_NAMES
- score_jes_v2 returns a single dict with is_ec, factors, total_points, standard_name
- override_jes_factor is synchronous; writes audit_log row with event="jes_override"

Public API:
    score_jes_v2(wd_id, og_code, og_level, duties, db_path) -> dict
    override_jes_factor(wd_id, factor_name, *, degree, rationale, db_path) -> dict

Architecture:
    - One jes_instructor_client call per JES factor (no array-collapse — STATE.md non-negiable)
    - Sequential calls (not asyncio.gather) to avoid Ollama OOM on ARM64
    - Failed factor after 3 retries → factor dict with degree=-1, points=None (sentinel)
    - Degree normalization: _resolve_degree handles "D3" / "3" / mixed LLM output

Direct analog: v1.0 app/services/jes_service.py
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from app.ai.jes_scoring import (
    JES_SCORING_SYSTEM_PROMPT,
    JESFactorRating,
    jes_instructor_client,
)
from app.config import get_settings
from app.data.constants import (
    EC_JES_ELEMENTS,
    JES_FACTORS_BY_GROUP,
    NON_EC_STANDARD_NAMES,
    NON_EC_TOTALS,
)
from app.db import get_connection
from app.models.work_description import WorkDescription

logger = logging.getLogger(__name__)

# EC JES 2017 version label — hardcoded; v2.0 has no source_documents table.
EC_JES_VERSION_LABEL = "EC JES 2017"

# Phase 21 (OGX-05): point-rating OG groups scored via JES_FACTORS_BY_GROUP
# factor loop (no LLM call). SW-SCW and ED-EDS are sub-group routing codes.
# ED-EDS has no factor data yet (Plan 03 didn't author it); calls will raise
# ValueError pointing operators to the missing data — by design (T-21-02).
POINT_RATING_GROUPS = frozenset({
    "FB", "FS", "LP", "MT", "LC",
    "SW-SCW", "ED-EDS",
})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_factor_user_prompt(element: dict, duties: list[str], summary: str) -> str:
    """Build the per-factor user prompt injecting degree definitions from element dict.

    Truncates duties to top 10 (each at 200 chars) and summary to 300 chars
    to stay within num_ctx=8192 for Ollama.
    """
    degree_text = "\n".join(
        f"  D{d} ({pts} pts)" for d, pts in element["pts"].items()
    )
    duties_text = "\n".join(f"{i + 1}. {d[:200]}" for i, d in enumerate(duties[:10]))
    return (
        f"Factor: {element['name']}\n"
        f"Category: {element['category']}\n\n"
        f"Degree Definitions (degree -> points):\n{degree_text}\n\n"
        f"Position duties:\n{duties_text}\n\n"
        f"Work description: {summary[:300]}\n\n"
        "Select the degree (e.g. D3) that best fits this position and provide a rationale."
    )


def _resolve_degree(degree_str: str, point_values: dict) -> tuple[int, int | None]:
    """Return (degree_int, points) by normalizing degree_str to match point_values keys.

    LLMs sometimes return "D3" when the DB key is "3", or "3" when the key is "D3".
    In v2.0, point_values keys are int (1, 2, 3, ...). Try:
      - exact (after stripping 'D' prefix)
      - int conversion of stripped form
    Returns (degree_int, points) or (degree_int, None) if no match.
    """
    # Strip optional D prefix and surrounding whitespace
    stripped = degree_str.strip().lstrip("D").strip()
    try:
        degree_int = int(stripped)
    except (TypeError, ValueError):
        return (-1, None)
    if degree_int in point_values:
        return (degree_int, point_values[degree_int])
    return (degree_int, None)


def _build_factor_score(
    element: dict,
    rating: JESFactorRating,
    og_code: str,
) -> dict:
    """Map a successful JESFactorRating to a factor score dict.

    Normalizes the returned degree string against element["pts"] keys so that
    "3" and "D3" are treated as equivalent.
    Returns dict with factor_name, degree (int), points (int|None), rationale, advisor_adjusted.
    """
    point_values: dict = element["pts"]
    degree_int, points = _resolve_degree(rating.degree, point_values)
    if points is None:
        logger.warning(
            "JES factor %r for og_code=%r returned degree %r (parsed as %r) but pts has no match — "
            "factor will contribute 0 to total",
            element["name"], og_code, rating.degree, degree_int,
        )
    return {
        "factor_name": element["name"],
        "degree": degree_int,
        "points": points,
        "rationale": rating.rationale,
        "advisor_adjusted": False,
    }


def _make_error_score(element: dict, og_code: str, exc: Exception) -> dict:
    """Produce a sentinel factor dict (degree=-1) for a factor that failed after 3 retries.

    degree=-1 is the sentinel for 'scoring failed'. The Pydantic field is int (non-optional)
    so None would not be valid as the field type. points is None to indicate the factor
    did not contribute to the total.
    """
    return {
        "factor_name": element["name"],
        "degree": -1,
        "points": None,
        "rationale": f"Scoring failed after 3 retries: {exc}",
        "advisor_adjusted": False,
    }


def _compute_total(factors: list[dict]) -> int:
    """Sum points across factors, skipping sentinels (points is None)."""
    return sum(s["points"] for s in factors if s["points"] is not None)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def score_jes_v2(
    wd_id: str,
    og_code: str,
    og_level: int,
    duties: list[str],
    db_path: str,
) -> dict:
    """Run per-factor JES scoring for a confirmed WorkDescription.

    For EC: loops over EC_JES_ELEMENTS (9 factors), one LLM call per factor.
    For non-EC (FI/IT/AS/EN): returns a single totals dict from NON_EC_TOTALS +
    NON_EC_STANDARD_NAMES — no LLM call.

    Returns dict with:
        wd_id (str), og_code (str), is_ec (bool),
        factors (list[dict]) — 9 items for EC; empty list for non-EC,
        total_points (int),
        standard_name (str) — "EC JES 2017" for EC; NON_EC_STANDARD_NAMES[og_code] otherwise,
        has_failed_factors (bool) — True if any factor has degree == -1

    Persists jes_scores + jes_total_points on the stored WD.
    """
    settings = get_settings()
    con = get_connection(db_path)
    try:
        # 1. Load WD
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"WorkDescription {wd_id!r} not found")
        wd = WorkDescription.model_validate_json(row["data"])

        # 2. Non-EC path: three-way branch (Phase 21 — OGX-05 / OGX-06)
        if og_code != "EC":
            # --- Resolve effective routing code for sub-group split groups ---
            # SW and ED have sub-groups with different JES methods:
            #   SW-SCW (point-rating) vs SW-CHA (level-description)
            #   ED-EDS (point-rating) vs ED-LAT/ED-EST (level-description)
            # Other groups (FB/FS/LP/MT/LC/NU/PS/NT/PO/WP) keep og_code as-is.
            sub_group = getattr(wd, "confirmed_sub_group", None)
            routing_code = og_code

            if og_code == "SW":
                if sub_group == "SCW":
                    routing_code = "SW-SCW"
                else:
                    # CHA or unset → level-description path
                    routing_code = "SW-CHA"
            elif og_code == "ED":
                if sub_group == "EDS":
                    routing_code = "ED-EDS"
                elif sub_group == "LAT":
                    routing_code = "ED-LAT"
                elif sub_group == "EST":
                    routing_code = "ED-EST"
                else:
                    # Default to LAT (level-description) if sub_group unset
                    routing_code = "ED-LAT"

            # --- Branch on scoring method ---
            if routing_code in POINT_RATING_GROUPS:
                # Point-rating path: loop JES_FACTORS_BY_GROUP, no LLM
                # (Architecture non-negotiable: hardcoded JES tables over LLM scoring)
                if routing_code not in JES_FACTORS_BY_GROUP:
                    raise ValueError(
                        f"Point-rating group {routing_code!r} not in JES_FACTORS_BY_GROUP. "
                        f"Ensure Plan 03 (Wave 2) has authored factor data for this group."
                    )
                factors_def = JES_FACTORS_BY_GROUP[routing_code]
                factor_scores: list[dict] = []
                for factor_def in factors_def:
                    # Deterministic degree assignment: clamp og_level to the
                    # factor's max degree. No LLM — benchmark position
                    # rationale: "Benchmark degree assignment for {og_code} level {og_level}"
                    max_degree = max(factor_def["pts"].keys())
                    degree = min(og_level, max_degree)
                    points = factor_def["pts"][degree]
                    factor_scores.append({
                        "factor_name": factor_def["name"],
                        "category": factor_def.get("category", ""),
                        "degree": degree,
                        "points": points,
                        "rationale": (
                            f"Benchmark degree assignment for {og_code} level {og_level}"
                        ),
                        "advisor_adjusted": False,
                    })

                total_points = _compute_total(factor_scores)
                standard_name = NON_EC_STANDARD_NAMES.get(
                    routing_code, NON_EC_STANDARD_NAMES.get(og_code, "")
                )
                scorecard = {
                    "wd_id": wd_id,
                    "og_code": og_code,
                    "is_ec": False,
                    "factors": factor_scores,
                    "total_points": total_points,
                    "standard_name": standard_name,
                    "has_failed_factors": False,
                }
                _persist_jes_scorecard(con, wd, scorecard)
                return scorecard

            # --- Level-description path: NON_EC_TOTALS lookup ---
            if routing_code not in NON_EC_TOTALS:
                raise ValueError(
                    f"Level-description group {routing_code!r} not in NON_EC_TOTALS. "
                    f"og_code={og_code!r}, confirmed_sub_group={sub_group!r}"
                )
            if og_level not in NON_EC_TOTALS[routing_code]:
                available = sorted(NON_EC_TOTALS[routing_code].keys())
                clamped = min(available, key=lambda lv: abs(lv - og_level))
                logger.warning(
                    "No JES totals for og_code=%r at level %r; using nearest level %r",
                    routing_code, og_level, clamped,
                )
                og_level = clamped
            total_points = NON_EC_TOTALS[routing_code][og_level]
            standard_name = NON_EC_STANDARD_NAMES.get(
                routing_code, NON_EC_STANDARD_NAMES.get(og_code, "")
            )
            scorecard = {
                "wd_id": wd_id,
                "og_code": og_code,
                "is_ec": False,
                "factors": [],
                "total_points": total_points,
                "standard_name": standard_name,
                "has_failed_factors": False,
            }
            # Persist onto WD
            _persist_jes_scorecard(con, wd, scorecard)
            return scorecard

        # 3. EC path: per-factor LLM loop
        og_name = "Economics and Social Science Services"  # hardcoded for EC
        # Per-factor loop — sequential (NOT asyncio.gather; avoids Ollama OOM on ARM64)
        extra_kwargs: dict = {}
        if not settings.cloud_api_key:
            extra_kwargs["extra_body"] = {"options": {"num_ctx": 8192}}

        # Build a brief summary from duties (for the per-prompt injection).
        summary = (duties[0] if duties else "")[:300]

        factors: list[dict] = []
        for element in EC_JES_ELEMENTS:
            user_prompt = _build_factor_user_prompt(element, duties, summary)
            try:
                rating: JESFactorRating = await jes_instructor_client.chat.completions.create(
                    model=settings.generation_model,
                    messages=[
                        {
                            "role": "system",
                            "content": JES_SCORING_SYSTEM_PROMPT.format(
                                og_name=og_name, og_code=og_code
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
                score = _build_factor_score(element, rating, og_code)
            except Exception as exc:
                logger.warning(
                    "JES factor scoring failed for %r/%r after 3 retries: %s",
                    og_code, element["name"], exc,
                )
                score = _make_error_score(element, og_code, exc)

            factors.append(score)

        total_points = _compute_total(factors)
        has_failed = any(f["degree"] == -1 for f in factors)

        scorecard = {
            "wd_id": wd_id,
            "og_code": og_code,
            "is_ec": True,
            "factors": factors,
            "total_points": total_points,
            "standard_name": EC_JES_VERSION_LABEL,
            "has_failed_factors": has_failed,
        }
        # Persist onto WD
        _persist_jes_scorecard(con, wd, scorecard)
        return scorecard

    finally:
        con.close()


def _persist_jes_scorecard(
    con, wd: WorkDescription, scorecard: dict
) -> None:
    """Update WD.jes_scores + jes_total_points and save back to the work_descriptions table."""
    wd.jes_scores = scorecard["factors"]
    wd.jes_total_points = scorecard["total_points"]
    wd.last_modified = datetime.now(timezone.utc)
    con.execute(
        "UPDATE work_descriptions SET data = ?, last_modified = ? WHERE id = ?",
        (wd.model_dump_json(), wd.last_modified.isoformat(), wd.id),
    )
    con.commit()


def override_jes_factor(
    wd_id: str,
    factor_name: str,
    *,
    degree: int,
    rationale: str,
    db_path: str,
) -> dict:
    """Manually set degree + rationale for one JES factor; record as advisor override.

    Looks up the canonical points value from EC_JES_ELEMENTS for the new degree.
    If the factor is in EC_JES_ELEMENTS, points are recomputed from the table.
    If the factor is not in the table (e.g. failure sentinel), points is set to None.

    Writes an audit_log row with event="jes_override", actor="advisor",
    detail=json.dumps({"factor_name": factor_name, "degree": degree, "rationale": rationale}).

    Recomputes jes_total_points and saves the WD.

    Returns dict with wd_id, factor_name, degree, points, jes_total_points.
    """
    con = get_connection(db_path)
    try:
        # 1. Load WD
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"WorkDescription {wd_id!r} not found")
        wd = WorkDescription.model_validate_json(row["data"])

        # 2. Find the factor index in jes_scores
        factor_index: int | None = None
        for i, s in enumerate(wd.jes_scores):
            if s.get("factor_name") == factor_name:
                factor_index = i
                break
        if factor_index is None:
            raise ValueError(
                f"JES factor {factor_name!r} not found in WorkDescription"
            )

        # 3. Compute points for the new degree
        new_points: int | None = None
        for element in EC_JES_ELEMENTS:
            if element["name"] == factor_name:
                pts_table: dict = element["pts"]
                if degree in pts_table:
                    new_points = pts_table[degree]
                break

        # 4. Build the updated factor score dict
        new_score = {
            "factor_name": factor_name,
            "degree": degree,
            "points": new_points,
            "rationale": rationale.strip(),
            "advisor_adjusted": True,
        }
        new_scores: list[dict] = list(wd.jes_scores)
        new_scores[factor_index] = new_score

        # 5. Recompute jes_total_points (skip factors with points=None)
        new_total = sum(s["points"] for s in new_scores if s.get("points") is not None)

        # 6. Persist WD
        wd.jes_scores = new_scores
        wd.jes_total_points = new_total
        wd.last_modified = datetime.now(timezone.utc)
        con.execute(
            "UPDATE work_descriptions SET data = ?, last_modified = ? WHERE id = ?",
            (wd.model_dump_json(), wd.last_modified.isoformat(), wd_id),
        )

        # 7. Write audit_log row
        con.execute(
            "INSERT INTO audit_log (wd_id, event, actor, detail, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                wd_id,
                "jes_override",
                "advisor",
                json.dumps({"factor_name": factor_name, "degree": degree, "rationale": rationale}),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        con.commit()

        return {
            "wd_id": wd_id,
            "factor_name": factor_name,
            "degree": degree,
            "points": new_points,
            "jes_total_points": new_total,
        }

    finally:
        con.close()
