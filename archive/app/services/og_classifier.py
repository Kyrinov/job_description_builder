"""
app/services/og_classifier.py — Three-step OG classification pipeline.

Steps:
  1. Load OG definitions from og_definitions table (~30 rows, direct context injection)
  2. AS vs EC policy-adjacent detection (instructor binary classification via PolicyAdjacencyResult)
  3. LLM rank top-3 OG candidates (instructor OGRankingResult + verbatim guardrail)

Online guardrail: evidence_quotes verified as substrings of og_definitions text before returning.
"""
from __future__ import annotations

import asyncio
import logging

from app.ai.og_ranking import (
    OG_LEVELS,
    POLICY_DETECTION_PROMPT,
    SYSTEM_PROMPT,
    OGRankingResult,
    PolicyAdjacencyResult,
    build_og_context,
    og_instructor_client,
)
from app.config import settings
from app.db import get_connection

logger = logging.getLogger(__name__)


def _strip_fabricated_quotes(quotes: list[str], og_full_text: str) -> list[str]:
    """
    Remove any evidence_quote that is NOT a verbatim substring of og_full_text.
    og_full_text should be the concatenation of definition + inclusions + exclusions for the OG.
    """
    return [q for q in quotes if q and q in og_full_text]


def _build_asec_alert(og_rows: list) -> dict | None:
    """
    Build the AS vs EC alert dict from og_definitions rows.
    Returns None if AS or EC rows are not present in og_rows.

    IMPORTANT: This is a PURE function — it only reads from the provided og_rows argument.
    It has NO hidden DB access. Step 1 (classify_og) always calls _fetch_og_rows() WITHOUT
    a WHERE filter so that all OG rows including AS and EC are guaranteed to be present.
    If AS or EC is somehow absent, this function returns None and the caller skips the alert.
    Do NOT add a DB fallback here — that would introduce a hidden side-effect.
    """
    as_row = None
    ec_row = None
    for row in og_rows:
        code = row[0] if not hasattr(row, "keys") else row["og_code"]
        if code == "AS":
            as_row = row
        elif code == "EC":
            ec_row = row

    if as_row is None or ec_row is None:
        logger.warning("_build_asec_alert: AS or EC row absent from og_rows — skipping alert")
        return None

    def _get(row, idx, key):
        return row[idx] if not hasattr(row, "keys") else row[key]

    as_inclusions = _get(as_row, 3, "inclusions") or ""
    ec_exclusions = _get(ec_row, 4, "exclusions") or ""

    return {
        "as_inclusions_excerpt": as_inclusions[:600],
        "ec_exclusions_excerpt": ec_exclusions[:600],
        "as_name": "Administrative Services (AS)",
        "ec_name": "Economics and Social Science Services (EC)",
        "citation_source": "TBS OCHRO OG Definitions",
    }


async def _fetch_directive_citation(db_path: str) -> str:
    """
    Fetch 1-2 chunks from policy_chunks WHERE doc_name='directive_on_classification'
    using FTS on terms related to occupational group classification authority.
    Returns a short citation string to include in the AS/EC alert (CLASS-03 grounding).
    """
    conn = await asyncio.to_thread(lambda: get_connection(db_path))
    try:
        rows = await asyncio.to_thread(
            lambda: conn.execute(
                """
                SELECT p.chunk_text
                FROM policy_chunks p
                JOIN policy_fts f ON p.id = f.rowid
                WHERE p.doc_name = 'directive_on_classification'
                  AND policy_fts MATCH 'occupational OR classification OR group'
                ORDER BY rank
                LIMIT 2
                """
            ).fetchall()
        )
        if rows:
            return " ".join(r[0][:400] for r in rows if r[0])[:600]
        rows = await asyncio.to_thread(
            lambda: conn.execute(
                "SELECT chunk_text FROM policy_chunks "
                "WHERE doc_name = 'directive_on_classification' LIMIT 1"
            ).fetchall()
        )
        return rows[0][0][:600] if rows else ""
    except Exception as exc:
        logger.warning("_fetch_directive_citation failed: %s", exc)
        return ""
    finally:
        await asyncio.to_thread(conn.close)


async def _fetch_og_rows(db_path: str) -> list:
    """Load all og_definitions rows for OG classification context."""
    conn = await asyncio.to_thread(lambda: get_connection(db_path))
    try:
        rows = await asyncio.to_thread(
            lambda: conn.execute(
                "SELECT og_code, og_name, definition, inclusions, exclusions FROM og_definitions"
            ).fetchall()
        )
        return list(rows)
    finally:
        await asyncio.to_thread(conn.close)


async def classify_og(
    work_description: str,
    confirmed_noc_code: str,
    db_path: str,
) -> dict:
    """
    Three-step OG classification pipeline.

    Returns:
        {
            "candidates": [
                {
                    "og_code": str,
                    "og_name": str,
                    "rank": int,
                    "confidence": float,
                    "rationale": str,
                    "evidence_quotes": list[str],
                    "definition_excerpt": str,
                    "relevant_inclusions": str,
                    "relevant_exclusions": str,
                    "available_levels": list[int],
                }
            ],
            "asec_alert": dict | None,
        }
    """
    og_rows = await _fetch_og_rows(db_path)
    if not og_rows:
        raise ValueError("og_definitions table is empty — run scripts/ingest_og_definitions.py first")

    og_text_map: dict[str, str] = {}
    og_name_map: dict[str, str] = {}
    og_detail_map: dict[str, dict] = {}
    for row in og_rows:
        if hasattr(row, "keys"):
            code = row["og_code"]
            name = row["og_name"]
            defn = row["definition"]
            incl = row["inclusions"]
            excl = row["exclusions"]
        else:
            code, name, defn, incl, excl = row[0], row[1], row[2], row[3], row[4]
        og_text_map[code] = " ".join(filter(None, [defn, incl, excl]))
        og_name_map[code] = name
        og_detail_map[code] = {
            "definition": defn or "",
            "inclusions": incl or "",
            "exclusions": excl or "",
        }

    valid_og_codes = set(og_text_map.keys())

    # Step 2: AS vs EC policy-adjacent detection
    asec_alert: dict | None = None
    policy_detection_prompt = POLICY_DETECTION_PROMPT.format(work_description=work_description)
    try:
        policy_result: PolicyAdjacencyResult = await og_instructor_client.chat.completions.create(
            model=settings.generation_model,
            messages=[
                {"role": "user", "content": policy_detection_prompt},
            ],
            response_model=PolicyAdjacencyResult,
            max_retries=2,
            max_tokens=512,
            temperature=0.0,
            **({"extra_body": {"options": {"num_ctx": 4096}}} if not settings.cloud_api_key else {}),
        )
        if policy_result.is_policy_adjacent:
            asec_alert = _build_asec_alert(og_rows)
            if asec_alert is not None:
                directive_citation = await _fetch_directive_citation(db_path)
                asec_alert["directive_citation"] = directive_citation
    except Exception as exc:
        logger.warning("Policy adjacency detection failed: %s — skipping AS/EC alert", exc)

    # Step 3: LLM rank top-3 OG candidates
    extra_kwargs: dict = {}
    if not settings.cloud_api_key:
        extra_kwargs["extra_body"] = {"options": {"num_ctx": 16384}}

    og_context = build_og_context(og_rows, confirmed_noc_code, work_description)
    ranking_result: OGRankingResult = await og_instructor_client.chat.completions.create(
        model=settings.generation_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": og_context},
        ],
        response_model=OGRankingResult,
        max_retries=3,
        max_tokens=2048,
        temperature=0.0,
        **extra_kwargs,
    )

    # Verbatim guardrail: remove candidates with invalid og_code or fabricated quotes
    candidates_out = []
    for candidate in ranking_result.candidates:
        if candidate.og_code not in valid_og_codes:
            logger.warning(
                "LLM returned unknown og_code %r — dropping candidate", candidate.og_code
            )
            continue
        og_text = og_text_map[candidate.og_code]
        verified_quotes = _strip_fabricated_quotes(candidate.evidence_quotes, og_text)
        detail = og_detail_map[candidate.og_code]
        candidates_out.append({
            "og_code": candidate.og_code,
            "og_name": og_name_map[candidate.og_code],
            "rank": candidate.rank,
            "confidence": candidate.confidence,
            "rationale": candidate.rationale,
            "evidence_quotes": verified_quotes,
            "definition_excerpt": detail["definition"][:400],
            "relevant_inclusions": detail["inclusions"][:400],
            "relevant_exclusions": detail["exclusions"][:300],
            "available_levels": OG_LEVELS.get(candidate.og_code, []),
        })

    if not candidates_out:
        raise ValueError("All LLM-returned OG candidates were invalid — no valid OG codes found")

    return {
        "candidates": candidates_out,
        "asec_alert": asec_alert,
    }
