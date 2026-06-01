"""
app/services/noc_mapper.py — Three-stage NL→NOC mapping pipeline.

Stages:
  1. FTS5 keyword shortlist — SQLite BM25 over noc_fts, up to fts_limit candidates
  2. sqlite-vec embedding rerank — cosine KNN on noc_chunks_vec, up to rerank_limit candidates
  3. instructor LLM justification — gemma4:31b via instructor returns NOCRankingResult

Online guardrails run after Stage 3:
  - Verbatim fidelity check (strips fabricated matched_duties)
  - TEER DB correction (authoritative teer from noc_units overwrites LLM value)
  - Empty shortlist guard (raises ValueError → HTTP 422)

Architecture non-negotiables:
  - Connection opens per-request, closes in finally block (never module-level)
  - Stage 1 uses parameterized MATCH ? (never string interpolation)
  - Stage 2 join: noc_chunks_vec.rowid = noc_elements.id
"""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import date

import sqlite_vec
from ollama import AsyncClient as OllamaAsyncClient

from app.ai.noc_ranking import NOCCandidate, NOCRankingResult, instructor_client
from app.config import settings
from app.db import get_connection
from app.models.work_description import NOCMatch, ProvenanceTag

logger = logging.getLogger(__name__)


async def map_work_description(
    work_description: str,
    db_path: str,
    *,
    fts_limit: int = 30,
    rerank_limit: int = 10,
) -> NOCRankingResult:
    """
    Run the three-stage NL→NOC pipeline and return a validated NOCRankingResult.

    Raises ValueError for:
      - Empty FTS5 shortlist (HTTP 422 at route layer)
      - All candidates stripped by verbatim guardrail (HTTP 422 at route layer)
    """
    conn = await asyncio.to_thread(lambda: get_connection(db_path))
    try:
        # --- Stage 1: FTS5 keyword shortlist ---
        fts_rows = await asyncio.to_thread(
            lambda: conn.execute(
                """
                SELECT DISTINCT f.noc_code, u.title,
                       CAST(u.teer_level AS INTEGER) AS teer,
                       u.definition
                FROM noc_fts f
                JOIN noc_units u ON u.noc_code = f.noc_code
                WHERE noc_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (work_description, fts_limit),
            ).fetchall()
        )
        if not fts_rows:
            raise ValueError(
                "FTS5 shortlist empty — work description has no lexical overlap with NOC corpus"
            )

        # --- Stage 2: sqlite-vec embedding rerank ---
        ollama_client = OllamaAsyncClient(host=settings.ollama_base_url)
        embed_resp = await ollama_client.embed(
            model=settings.ollama_embed_model,
            input=work_description,
        )
        query_vec: list[float] = embed_resp.embeddings[0]

        fts_codes = [row["noc_code"] for row in fts_rows]
        placeholders = ",".join("?" * len(fts_codes))

        vec_rows = await asyncio.to_thread(
            lambda: conn.execute(
                f"""
                SELECT u.noc_code, u.title, CAST(u.teer_level AS INTEGER) as teer,
                       GROUP_CONCAT(e.element_text, char(10)) AS main_duties,
                       MIN(vec_distance_cosine(v.embedding, ?)) AS dist
                FROM noc_chunks_vec v
                JOIN noc_elements e ON e.id = v.rowid
                JOIN noc_units u ON u.noc_code = e.noc_code
                WHERE e.noc_code IN ({placeholders})
                  AND e.element_type = 'Main duties'
                GROUP BY u.noc_code
                ORDER BY dist ASC
                LIMIT ?
                """,
                (sqlite_vec.serialize_float32(query_vec), *fts_codes, rerank_limit),
            ).fetchall()
        )

        # --- Stage 3: instructor LLM justification ---
        candidate_block = _format_candidates(vec_rows)
        result: NOCRankingResult = await instructor_client.chat.completions.create(
            model=settings.ollama_generation_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a Government of Canada HR classification specialist with "
                        "expertise in NOC 2021 occupational taxonomy.\n\n"
                        "CRITICAL: You may only cite duty statements that appear verbatim "
                        "in the provided NOC profiles. Do not paraphrase, summarize, or "
                        "invent duties. If no duty directly supports a match, reduce the "
                        "candidate's rank rather than fabricating a citation.\n\n"
                        "Return 1 to 5 candidates ranked best-first (rank=1 is best fit)."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"WORK DESCRIPTION:\n{work_description}\n\n"
                        f"NOC CANDIDATES (top {rerank_limit} by semantic similarity):\n"
                        f"{candidate_block}"
                    ),
                },
            ],
            response_model=NOCRankingResult,
            max_retries=3,
            max_tokens=2048,
            temperature=0.0,
            extra_body={"options": {"num_ctx": 32768}},
        )

        # --- Online guardrails ---
        result = await _check_verbatim_fidelity(conn, result)
        result = await _correct_teer_from_db(conn, result)

    finally:
        await asyncio.to_thread(conn.close)

    return result


def _format_candidates(rows: list) -> str:
    """Format Stage 2 rows into a prompt-injectable candidate block."""
    blocks = []
    for row in rows:
        noc_code = row["noc_code"]
        title = row["title"]
        teer = row["teer"]
        main_duties = row["main_duties"] or ""
        dist = row["dist"]
        duties_text = main_duties[:1500] if len(main_duties) > 1500 else main_duties
        if len(main_duties) > 1500:
            logger.warning("noc_truncated noc_code=%s duties_chars=%d", noc_code, len(main_duties))
        blocks.append(
            f"[{noc_code}] {title} (TEER {teer})\n"
            f"Main duties:\n{duties_text}\n"
            f"(vector distance: {dist:.4f})"
        )
    return "\n\n---\n\n".join(blocks)


async def _check_verbatim_fidelity(
    conn: sqlite3.Connection,
    result: NOCRankingResult,
) -> NOCRankingResult:
    """Strip matched_duties entries not verbatim in noc_elements. Raise if all stripped."""
    clean_candidates = []
    for candidate in result.candidates:
        verified_duties = []
        for duty in candidate.matched_duties:
            row = await asyncio.to_thread(
                lambda c=candidate.noc_code, d=duty: conn.execute(
                    "SELECT 1 FROM noc_elements WHERE noc_code = ? AND instr(element_text, ?) > 0",
                    (c, d),
                ).fetchone()
            )
            if row:
                verified_duties.append(duty)
            else:
                logger.error(
                    "noc_guardrail=citation_fabrication noc_code=%s duty_preview=%s",
                    candidate.noc_code,
                    duty[:80],
                )
        if verified_duties:
            clean_candidates.append(candidate.model_copy(update={"matched_duties": verified_duties}))

    if not clean_candidates:
        raise ValueError("All candidates had fabricated duties — result withheld")

    return result.model_copy(update={"candidates": clean_candidates})


async def _correct_teer_from_db(
    conn: sqlite3.Connection,
    result: NOCRankingResult,
) -> NOCRankingResult:
    """Overwrite teer field with authoritative value from noc_units if LLM value differs."""
    corrected = []
    for candidate in result.candidates:
        db_row = await asyncio.to_thread(
            lambda nc=candidate.noc_code: conn.execute(
                "SELECT CAST(teer_level AS INTEGER) AS teer FROM noc_units WHERE noc_code = ?",
                (nc,),
            ).fetchone()
        )
        if db_row and db_row["teer"] != candidate.teer:
            logger.warning(
                "noc_teer_correction noc_code=%s llm_teer=%d db_teer=%d",
                candidate.noc_code,
                candidate.teer,
                db_row["teer"],
            )
            corrected.append(candidate.model_copy(update={"teer": db_row["teer"]}))
        else:
            corrected.append(candidate)
    return result.model_copy(update={"candidates": corrected})


def to_noc_match(candidate: NOCCandidate) -> NOCMatch:
    """Map a NOCCandidate (pipeline output) to a NOCMatch (WorkDescription storage type)."""
    return NOCMatch(
        noc_code=candidate.noc_code,
        noc_title=candidate.title,
        teer_level=str(candidate.teer),
        confidence=1.0 - (candidate.rank / 10.0),
        rationale=candidate.justification,
        matched_duty_statements=candidate.matched_duties,
        provenance=ProvenanceTag(
            source_type="NOC",
            source_id=candidate.noc_code,
            source_version="NOC 2021 v1.0",
            retrieved_date=date.today(),
            model_name=settings.ollama_generation_model,
        ),
    )
