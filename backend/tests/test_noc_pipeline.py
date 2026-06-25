"""
Phase 14 NOC Pipeline tests — Wave 0 stubs.

All tests use pytest.importorskip so they skip gracefully before Plan 02
creates app/ai/noc_ranking.py and app/services/noc_mapper.py.

Import paths: v2 backend uses `app.*` (same as v1.0 because the v2 backend
is launched with PYTHONPATH=backend/). These tests run from backend/.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers (mirrors v1.0 test helpers, adapted for v2)
# ---------------------------------------------------------------------------


def _make_embed_mock():
    """Mock OllamaAsyncClient.embed returning a fake 768-dim embedding."""
    embed_resp = MagicMock()
    embed_resp.embeddings = [[0.1] * 768]
    mock = MagicMock()
    mock.embed = AsyncMock(return_value=embed_resp)
    return mock


def _make_ranking_mock():
    """Mock NOCRankingResult with one plausible candidate."""
    noc_ranking = pytest.importorskip("app.ai.noc_ranking")
    return noc_ranking.NOCRankingResult(
        candidates=[
            noc_ranking.NOCCandidate(
                noc_code="21232",
                title="Software engineers and designers",
                teer=1,
                rank=1,
                matched_duties=["Develop and maintain application software."],
                justification=(
                    "This unit group matches the work because it covers software "
                    "development and maintenance of application systems."
                ),
            )
        ]
    )


# ---------------------------------------------------------------------------
# Stage 1 / _fts_query_from_text unit tests (NOC-01)
# ---------------------------------------------------------------------------


def test_fts5_query_rewriting_strips_stop_words():
    """_fts_query_from_text OR-joins non-stop keywords; drops 'reviews', 'analyzes', 'and'."""
    noc_mapper = pytest.importorskip("app.services.noc_mapper")
    result = noc_mapper._fts_query_from_text(
        "Reviews and analyzes federal government procurement policies"
    )
    terms = set(result.split(" OR "))
    assert "federal" in terms
    assert "government" in terms
    assert "procurement" in terms
    assert "policies" in terms
    assert "and" not in terms
    assert "reviews" not in terms
    assert "analyzes" not in terms


def test_fts5_query_empty_after_filtering_raises(noc_mapping_db, monkeypatch):
    """map_work_description raises ValueError (→ 422) when all tokens are stop words."""
    monkeypatch.setenv("NOC_DB_PATH", noc_mapping_db)
    noc_mapper = pytest.importorskip("app.services.noc_mapper")

    async def _run():
        with pytest.raises(ValueError, match="no usable search terms"):
            await noc_mapper.map_work_description(
                work_description="the a an",
                noc_db_path=noc_mapping_db,
            )

    import asyncio
    asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# Stage 1 + full pipeline (NOC-01)
# ---------------------------------------------------------------------------


async def test_fts5_stage_returns_noc_codes(noc_mapping_db, monkeypatch):
    """Stage 1 FTS5 query returns at least one NOC code from the noc_mapping_db fixture."""
    monkeypatch.setenv("NOC_DB_PATH", noc_mapping_db)
    noc_mapper = pytest.importorskip("app.services.noc_mapper")

    embed_mock = _make_embed_mock()
    ranking = _make_ranking_mock()

    with patch("app.services.noc_mapper.OllamaAsyncClient", return_value=embed_mock), \
         patch("app.services.noc_mapper.instructor_client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=ranking)
        result = await noc_mapper.map_work_description(
            work_description="develop and maintain application software",
            noc_db_path=noc_mapping_db,
        )
        assert isinstance(result.candidates, list)
        assert len(result.candidates) >= 1
        assert all(c.noc_code for c in result.candidates)


async def test_stage2_calls_embed_model(noc_mapping_db, monkeypatch):
    """Stage 2 calls OllamaAsyncClient.embed with model matching OLLAMA_EMBED_MODEL."""
    monkeypatch.setenv("NOC_DB_PATH", noc_mapping_db)
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    noc_mapper = pytest.importorskip("app.services.noc_mapper")

    embed_mock = _make_embed_mock()
    ranking = _make_ranking_mock()

    with patch("app.services.noc_mapper.OllamaAsyncClient", return_value=embed_mock), \
         patch("app.services.noc_mapper.instructor_client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=ranking)
        await noc_mapper.map_work_description(
            work_description="develop and maintain application software",
            noc_db_path=noc_mapping_db,
        )
        embed_mock.embed.assert_called_once()
        assert embed_mock.embed.call_args.kwargs["model"] == "nomic-embed-text:latest"


async def test_pipeline_returns_candidates(noc_mapping_db, monkeypatch):
    """Full mocked 3-stage pipeline returns NOCRankingResult with >= 1 candidate."""
    monkeypatch.setenv("NOC_DB_PATH", noc_mapping_db)
    noc_mapper = pytest.importorskip("app.services.noc_mapper")
    noc_ranking = pytest.importorskip("app.ai.noc_ranking")

    embed_mock = _make_embed_mock()
    ranking = _make_ranking_mock()

    with patch("app.services.noc_mapper.OllamaAsyncClient", return_value=embed_mock), \
         patch("app.services.noc_mapper.instructor_client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=ranking)
        result = await noc_mapper.map_work_description(
            work_description="develop and maintain application software",
            noc_db_path=noc_mapping_db,
        )
        assert isinstance(result, noc_ranking.NOCRankingResult)
        assert len(result.candidates) >= 1


# ---------------------------------------------------------------------------
# Verbatim guardrail tests (NOC-01)
# ---------------------------------------------------------------------------


async def test_verbatim_guardrail_strips_fabricated(noc_mapping_db, monkeypatch):
    """_check_verbatim_fidelity strips duties not verbatim in DB; keeps real ones."""
    monkeypatch.setenv("NOC_DB_PATH", noc_mapping_db)
    noc_mapper = pytest.importorskip("app.services.noc_mapper")
    noc_ranking = pytest.importorskip("app.ai.noc_ranking")

    mock_conn = MagicMock()

    def execute_side_effect(sql, params):
        duty = params[1]
        res = MagicMock()
        res.fetchone.return_value = None if "FABRICATED" in duty else (1,)
        return res

    mock_conn.execute.side_effect = execute_side_effect

    result = noc_ranking.NOCRankingResult(
        candidates=[
            noc_ranking.NOCCandidate(
                noc_code="21232",
                title="Software engineers and designers",
                teer=1,
                rank=1,
                matched_duties=[
                    "Develop and maintain application software.",
                    "FABRICATED DUTY NOT IN DB EVER",
                ],
                justification=(
                    "This unit group matches because the duty text aligns with the "
                    "described software maintenance work performed by the position."
                ),
            )
        ]
    )

    cleaned = await noc_mapper._check_verbatim_fidelity(mock_conn, result)
    assert len(cleaned.candidates) == 1
    duties = cleaned.candidates[0].matched_duties
    assert "Develop and maintain application software." in duties
    assert "FABRICATED DUTY NOT IN DB EVER" not in duties


async def test_verbatim_guardrail_raises_when_all_stripped(noc_mapping_db, monkeypatch):
    """_check_verbatim_fidelity raises ValueError if all candidates' duties are fabricated."""
    monkeypatch.setenv("NOC_DB_PATH", noc_mapping_db)
    noc_mapper = pytest.importorskip("app.services.noc_mapper")
    noc_ranking = pytest.importorskip("app.ai.noc_ranking")

    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_conn.execute.return_value = mock_result

    result = noc_ranking.NOCRankingResult(
        candidates=[
            noc_ranking.NOCCandidate(
                noc_code="99999",
                title="Imaginary occupation",
                teer=1,
                rank=1,
                matched_duties=["ENTIRELY FABRICATED DUTY TEXT"],
                justification=(
                    "This justification is long enough to satisfy the min_length validator "
                    "even though the candidate is wholly fabricated."
                ),
            )
        ]
    )

    with pytest.raises(ValueError, match="fabricated"):
        await noc_mapper._check_verbatim_fidelity(mock_conn, result)


# ---------------------------------------------------------------------------
# API route tests (API-04)
# ---------------------------------------------------------------------------


async def test_api_route_200(env_with_db, noc_mapping_db, monkeypatch):
    """POST /api/noc/map returns 200 with candidates list."""
    monkeypatch.setenv("NOC_DB_PATH", noc_mapping_db)
    pytest.importorskip("app.api.noc_mapping")

    from httpx import ASGITransport, AsyncClient

    ranking = _make_ranking_mock()

    with patch("app.api.noc_mapping.map_work_description",
               new=AsyncMock(return_value=ranking)):
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/noc/map",
                json={"work_description": "develop and maintain application software"},
            )
            assert response.status_code == 200
            body = response.json()
            assert "candidates" in body
            assert len(body["candidates"]) >= 1
            assert body["candidates"][0]["noc_code"] == "21232"


async def test_empty_fts_result_raises_422(env_with_db, noc_mapping_db, monkeypatch):
    """POST /api/noc/map when pipeline raises ValueError returns HTTP 422."""
    monkeypatch.setenv("NOC_DB_PATH", noc_mapping_db)
    pytest.importorskip("app.api.noc_mapping")

    from httpx import ASGITransport, AsyncClient

    with patch("app.api.noc_mapping.map_work_description",
               new=AsyncMock(side_effect=ValueError("FTS5 shortlist empty — no lexical overlap"))):
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/noc/map",
                json={"work_description": "xyzzy no matching terms"},
            )
            assert response.status_code == 422
            assert "FTS5 shortlist" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Schema tests (NOC-02)
# ---------------------------------------------------------------------------


class TestNOCCandidateSchema:
    def test_noc_candidate_schema(self):
        """NOCCandidate accepts valid data and rejects non-digit noc_code."""
        noc_ranking = pytest.importorskip("app.ai.noc_ranking")
        from pydantic import ValidationError
        c = noc_ranking.NOCCandidate(
            noc_code="21232", title="Software engineers and designers",
            teer=1, rank=1, matched_duties=["Develop software systems."],
            justification="This unit group matches because it covers software development work."
        )
        assert c.noc_code == "21232"
        with pytest.raises(ValidationError):
            noc_ranking.NOCCandidate(
                noc_code="ABCDE", title="X", teer=2, rank=1,
                matched_duties=["x"], justification="x" * 30,
            )

    def test_teer_is_integer(self):
        """NOCCandidate.teer accepts 0–5, rejects 6."""
        noc_ranking = pytest.importorskip("app.ai.noc_ranking")
        from pydantic import ValidationError
        c = noc_ranking.NOCCandidate(
            noc_code="21232", title="T", teer=0, rank=1,
            matched_duties=["d"], justification="x" * 30,
        )
        assert c.teer == 0
        with pytest.raises(ValidationError):
            noc_ranking.NOCCandidate(
                noc_code="21232", title="T", teer=6, rank=1,
                matched_duties=["d"], justification="x" * 30,
            )

    def test_ranks_are_sequential(self):
        """NOCRankingResult rejects non-sequential ranks [1,3]; accepts [1,2]."""
        noc_ranking = pytest.importorskip("app.ai.noc_ranking")
        from pydantic import ValidationError

        def make_c(rank):
            return noc_ranking.NOCCandidate(
                noc_code="21232", title="T", teer=1, rank=rank,
                matched_duties=["d"], justification="x" * 30,
            )

        noc_ranking.NOCRankingResult(candidates=[make_c(1), make_c(2)])
        with pytest.raises(ValidationError):
            noc_ranking.NOCRankingResult(candidates=[make_c(1), make_c(3)])
