"""Phase 4 NL→NOC mapping integration tests."""
from __future__ import annotations

import json
import sys
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


def _set_env(monkeypatch, db_path, tmp_path):
    """Set all required env vars for a valid Settings instantiation.

    Must be called BEFORE any `app.*` module is imported so that the
    module-level `settings = Settings()` singleton sees these values.
    """
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "gemma4:31b")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))


def _make_mock_ollama_client():
    """Mock AsyncClient that simulates a healthy Ollama with both required models."""
    mock = MagicMock()
    entries = []
    for name in ("gemma4:31b", "nomic-embed-text:latest"):
        entry = MagicMock()
        entry.model = name
        entries.append(entry)
    mock.list = AsyncMock(return_value=MagicMock(models=entries))
    return mock


def _make_embed_mock():
    """Mock that returns a fake 768-dim embedding for any input."""
    embed_resp = MagicMock()
    embed_resp.embeddings = [[0.1] * 768]
    ollama_mock = MagicMock()
    ollama_mock.embed = AsyncMock(return_value=embed_resp)
    return ollama_mock


def _make_ranking_mock():
    """Mock NOCRankingResult with one plausible candidate."""
    from app.ai.noc_ranking import NOCCandidate, NOCRankingResult

    return NOCRankingResult(
        candidates=[
            NOCCandidate(
                noc_code="21232",
                title="Software engineers and designers",
                teer=2,
                rank=1,
                matched_duties=["Develop and maintain application software."],
                justification=(
                    "This unit group matches the work because it covers software "
                    "development and maintenance of application systems."
                ),
            )
        ]
    )


def _clear_app_modules():
    """Remove all app modules from sys.modules for a clean import."""
    for key in list(sys.modules.keys()):
        if key.startswith("app."):
            del sys.modules[key]


# Ensure `app.*` modules are loaded once with a known env, then cached.
# This avoids leaking httpx connection pools from the instructor singleton
# being recreated for every test.
_app_bootstrapped = False


@pytest.fixture(autouse=True)
def _bootstrap_app_modules(noc_mapping_db, monkeypatch, tmp_path):
    """Import app.* once per test module with a stable env, then leave cached."""
    global _app_bootstrapped
    if not _app_bootstrapped:
        _set_env(monkeypatch, str(noc_mapping_db), tmp_path)
        _clear_app_modules()
        import app.main  # noqa: F401  -- prime the module cache
        _app_bootstrapped = True
    yield


@pytest.fixture
def test_db_routing(noc_mapping_db, monkeypatch):
    """Route FastAPI tests' DB access to the per-test noc_mapping_db.

    Patches `app.db.get_connection` so that any code path which calls
    `get_connection(settings.db_path)` actually opens the test DB.
    This avoids the need to clear/reimport app modules (which leaks
    httpx connection pools from the instructor singleton).
    """
    from app.db import get_connection

    real_get_connection = get_connection

    def patched_get_connection(db_path=None):
        # Force the test DB regardless of what the caller passed
        return real_get_connection(str(noc_mapping_db))

    # Patch at every import site
    monkeypatch.setattr("app.db.get_connection", patched_get_connection)
    monkeypatch.setattr("app.api.noc_mapping.get_connection", patched_get_connection)
    monkeypatch.setattr("app.services.noc_mapper.get_connection", patched_get_connection)
    yield


# ---------------------------------------------------------------------------
# Pipeline tests — call map_work_description directly with explicit db_path.
# ---------------------------------------------------------------------------


async def test_fts5_stage_returns_noc_codes(noc_mapping_db, monkeypatch, tmp_path):
    """Stage 1 FTS5 query returns at least one NOC code using the noc_mapping_db fixture."""
    _set_env(monkeypatch, str(noc_mapping_db), tmp_path)

    embed_mock = _make_embed_mock()
    ranking = _make_ranking_mock()

    with patch("app.services.noc_mapper.OllamaAsyncClient", return_value=embed_mock), \
         patch("app.services.noc_mapper.instructor_client") as mock_instructor:
        mock_instructor.chat.completions.create = AsyncMock(return_value=ranking)

        from app.services.noc_mapper import map_work_description

        result = await map_work_description(
            work_description="develop and maintain application software",
            db_path=str(noc_mapping_db),
        )

        assert isinstance(result.candidates, list)
        assert len(result.candidates) >= 1
        assert all(c.noc_code for c in result.candidates)


async def test_stage2_calls_embed_model(noc_mapping_db, monkeypatch, tmp_path):
    """Stage 2 calls OllamaAsyncClient.embed with model matching OLLAMA_EMBED_MODEL."""
    _set_env(monkeypatch, str(noc_mapping_db), tmp_path)

    embed_mock = _make_embed_mock()
    ranking = _make_ranking_mock()

    with patch("app.services.noc_mapper.OllamaAsyncClient", return_value=embed_mock), \
         patch("app.services.noc_mapper.instructor_client") as mock_instructor:
        mock_instructor.chat.completions.create = AsyncMock(return_value=ranking)

        from app.services.noc_mapper import map_work_description

        await map_work_description(
            work_description="develop and maintain application software",
            db_path=str(noc_mapping_db),
        )

        embed_mock.embed.assert_called_once()
        call_kwargs = embed_mock.embed.call_args.kwargs
        assert call_kwargs["model"] == "nomic-embed-text:latest"


async def test_pipeline_returns_candidates(noc_mapping_db, monkeypatch, tmp_path):
    """Full mocked 3-stage pipeline returns NOCRankingResult with >= 1 candidate."""
    from app.ai.noc_ranking import NOCRankingResult

    _set_env(monkeypatch, str(noc_mapping_db), tmp_path)

    embed_mock = _make_embed_mock()
    ranking = _make_ranking_mock()

    with patch("app.services.noc_mapper.OllamaAsyncClient", return_value=embed_mock), \
         patch("app.services.noc_mapper.instructor_client") as mock_instructor:
        mock_instructor.chat.completions.create = AsyncMock(return_value=ranking)

        from app.services.noc_mapper import map_work_description

        result = await map_work_description(
            work_description="develop and maintain application software",
            db_path=str(noc_mapping_db),
        )

        assert isinstance(result, NOCRankingResult)
        assert len(result.candidates) >= 1


async def test_verbatim_guardrail_strips_fabricated(noc_mapping_db, monkeypatch, tmp_path):
    """_check_verbatim_fidelity strips duties not verbatim in DB; raises if all stripped."""
    from app.ai.noc_ranking import NOCCandidate, NOCRankingResult
    from app.services.noc_mapper import _check_verbatim_fidelity

    _set_env(monkeypatch, str(noc_mapping_db), tmp_path)

    mock_conn = MagicMock()

    def execute_side_effect(sql, params):
        duty = params[1]
        result = MagicMock()
        if "FABRICATED" in duty or "not in db" in duty.lower():
            result.fetchone.return_value = None
        else:
            result.fetchone.return_value = (1,)
        return result

    mock_conn.execute.side_effect = execute_side_effect

    result = NOCRankingResult(
        candidates=[
            NOCCandidate(
                noc_code="21232",
                title="Software engineers and designers",
                teer=2,
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

    cleaned = await _check_verbatim_fidelity(mock_conn, result)
    assert len(cleaned.candidates) == 1
    duties = cleaned.candidates[0].matched_duties
    assert "Develop and maintain application software." in duties
    assert "FABRICATED DUTY NOT IN DB EVER" not in duties


async def test_verbatim_guardrail_raises_when_all_stripped(noc_mapping_db, monkeypatch, tmp_path):
    """_check_verbatim_fidelity raises ValueError if all candidates' duties stripped."""
    from app.ai.noc_ranking import NOCCandidate, NOCRankingResult
    from app.services.noc_mapper import _check_verbatim_fidelity

    _set_env(monkeypatch, str(noc_mapping_db), tmp_path)

    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_conn.execute.return_value = mock_result

    result = NOCRankingResult(
        candidates=[
            NOCCandidate(
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
        await _check_verbatim_fidelity(mock_conn, result)


# ---------------------------------------------------------------------------
# FastAPI route tests — need fresh app modules so settings.db_path is current.
# ---------------------------------------------------------------------------


async def test_empty_fts_result_raises_422(test_db_routing, noc_mapping_db):
    """POST /api/noc/map when FTS5 returns empty shortlist returns HTTP 422."""
    with patch("app.main.ollama_client_factory", return_value=_make_mock_ollama_client()), \
         patch("app.api.noc_mapping.map_work_description",
               new=AsyncMock(side_effect=ValueError("FTS5 shortlist empty — no lexical overlap"))):
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/noc/map",
                json={"work_description": "xyzzy no matching terms here at all"},
            )
            assert response.status_code == 422
            assert "FTS5 shortlist" in response.json()["detail"]


async def test_api_route_200(test_db_routing, noc_mapping_db):
    """POST /api/noc/map with mocked pipeline returns HTTP 200 with candidates and wd_id."""
    ranking = _make_ranking_mock()

    with patch("app.main.ollama_client_factory", return_value=_make_mock_ollama_client()), \
         patch("app.api.noc_mapping.map_work_description",
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
            # New: response must include wd_id for the follow-up confirm call
            assert "wd_id" in body
            assert len(body["wd_id"]) > 0


async def test_api_route_htmx_returns_html(test_db_routing, noc_mapping_db):
    """POST /api/noc/map with HX-Request header returns HTML partial (noc_results.html)."""
    ranking = _make_ranking_mock()

    with patch("app.main.ollama_client_factory", return_value=_make_mock_ollama_client()), \
         patch("app.api.noc_mapping.map_work_description",
               new=AsyncMock(return_value=ranking)):
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/noc/map",
                json={"work_description": "develop and maintain application software"},
                headers={"HX-Request": "true"},
            )
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/html")
            assert "Software engineers and designers" in response.text
            assert "Confirm this NOC" in response.text


async def test_end_to_end_map_then_confirm(test_db_routing, noc_mapping_db):
    """Full end-to-end: /api/noc/map returns wd_id, /api/noc/confirm with that wd_id succeeds.

    Regression test for the critical bug where map_noc never persisted candidates
    to WorkDescription.noc_candidates — making confirm_noc always 422.
    """
    ranking = _make_ranking_mock()

    with patch("app.main.ollama_client_factory", return_value=_make_mock_ollama_client()), \
         patch("app.api.noc_mapping.map_work_description",
               new=AsyncMock(return_value=ranking)):
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Step 1: map the work description
            map_resp = await client.post(
                "/api/noc/map",
                json={"work_description": "develop and maintain application software"},
            )
            assert map_resp.status_code == 200
            map_body = map_resp.json()
            wd_id = map_body["wd_id"]

            # Step 2: confirm one of the candidates — must succeed because map populated noc_candidates
            confirm_resp = await client.post(
                "/api/noc/confirm",
                data={"wd_id": wd_id, "noc_code": "21232"},
            )
            assert confirm_resp.status_code == 200, (
                f"Confirm failed (regression of critical bug): {confirm_resp.json()}"
            )
            assert confirm_resp.json()["status"] == "confirmed"
            assert confirm_resp.json()["noc_code"] == "21232"


async def test_confirm_noc_updates_wd(test_db_routing, noc_mapping_db):
    """POST /api/noc/confirm with valid wd_id + noc_code stores confirmed_noc on WorkDescription."""
    from app.db import get_connection
    from app.models.work_description import NOCMatch, ProvenanceTag, WorkDescription
    from app.services.wd_store import save_work_description

    # Pre-populate a WorkDescription with a matching noc_candidate
    wd = WorkDescription(
        session_id="test-session-1",
        raw_input="develop and maintain application software",
        stage="input",
    )
    wd.noc_candidates = [
        NOCMatch(
            noc_code="21232",
            noc_title="Software engineers and designers",
            teer_level="2",
            confidence=0.9,
            rationale="Matches software development work",
            matched_duty_statements=["Develop and maintain application software."],
            provenance=ProvenanceTag(
                source_type="NOC",
                source_id="21232",
                source_version="NOC 2021 v1.0",
                retrieved_date=date.today(),
            ),
        )
    ]
    conn = get_connection(str(noc_mapping_db))
    save_work_description(conn, wd)
    conn.close()

    with patch("app.main.ollama_client_factory", return_value=_make_mock_ollama_client()):
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/noc/confirm",
                data={"wd_id": str(wd.id), "noc_code": "21232"},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "confirmed"
            assert body["noc_code"] == "21232"
            assert body["wd_id"] == str(wd.id)

    # Verify persisted
    conn2 = get_connection(str(noc_mapping_db))
    from app.services.wd_store import load_work_description

    loaded = load_work_description(conn2, str(wd.id))
    conn2.close()
    assert loaded is not None
    assert loaded.confirmed_noc is not None
    assert loaded.confirmed_noc.noc_code == "21232"
    assert loaded.stage == "noc_mapped"


async def test_confirm_noc_htmx_renders_wd_id_in_continue_form(test_db_routing, noc_mapping_db):
    """
    HTMX path of /api/noc/confirm must render the Continue-to-OG form with a non-empty
    wd_id hidden input. Regression: the template needs {{ wd_id }} to be passed in
    context — without it, the form posts with an empty wd_id and /api/og/classify 404s.
    """
    from app.db import get_connection
    from app.models.work_description import NOCMatch, ProvenanceTag, WorkDescription
    from app.services.wd_store import save_work_description

    wd = WorkDescription(
        session_id="test-session-htmx",
        raw_input="develop and maintain application software",
        stage="input",
    )
    wd.noc_candidates = [
        NOCMatch(
            noc_code="21232",
            noc_title="Software engineers and designers",
            teer_level="2",
            confidence=0.9,
            rationale="Matches",
            matched_duty_statements=["Develop and maintain application software."],
            provenance=ProvenanceTag(
                source_type="NOC",
                source_id="21232",
                source_version="NOC 2021 v1.0",
                retrieved_date=date.today(),
            ),
        )
    ]
    conn = get_connection(str(noc_mapping_db))
    save_work_description(conn, wd)
    conn.close()

    with patch("app.main.ollama_client_factory", return_value=_make_mock_ollama_client()):
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/noc/confirm",
                data={"wd_id": str(wd.id), "noc_code": "21232"},
                headers={"HX-Request": "true"},
            )
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
            body = response.text
            # The hidden input must carry the actual wd_id, not an empty string
            import re
            m = re.search(r'<input type="hidden" name="wd_id" value="([^"]*)">', body)
            assert m is not None, "Continue-to-OG form missing wd_id hidden input"
            rendered_wd_id = m.group(1)
            assert rendered_wd_id == str(wd.id), (
                f"wd_id hidden input rendered empty — would cause /api/og/classify "
                f"to 404. Got: {rendered_wd_id!r}, expected: {str(wd.id)!r}"
            )
            # Sanity: the form targets /api/og/classify
            assert 'hx-post="/api/og/classify"' in body


# ---------------------------------------------------------------------------
# _fts_query_from_text unit tests (§4 in gsd-phase-4-issues.md)
# ---------------------------------------------------------------------------


def test_fts5_query_rewriting_strips_stop_words():
    """_fts_query_from_text OR-joins non-stop keywords from a natural-language description."""
    from app.services.noc_mapper import _fts_query_from_text

    result = _fts_query_from_text(
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


def test_fts5_query_empty_string_when_only_stop_words():
    """_fts_query_from_text returns '' when all tokens are stop words or too short."""
    from app.services.noc_mapper import _fts_query_from_text

    assert _fts_query_from_text("the") == ""
    assert _fts_query_from_text("a b c") == ""


async def test_stage1_returns_candidates_for_realistic_description(
    noc_mapping_db, monkeypatch, tmp_path
):
    """Stage 1 + full pipeline returns candidates for a realistic multi-sentence work description.

    Regression test: before the FTS5 OR-rewrite, this input produced an empty shortlist
    and raised ValueError → HTTP 422.
    """
    _set_env(monkeypatch, str(noc_mapping_db), tmp_path)

    embed_mock = _make_embed_mock()
    ranking = _make_ranking_mock()

    with patch("app.services.noc_mapper.OllamaAsyncClient", return_value=embed_mock), \
         patch("app.services.noc_mapper.instructor_client") as mock_instructor:
        mock_instructor.chat.completions.create = AsyncMock(return_value=ranking)

        from app.services.noc_mapper import map_work_description

        result = await map_work_description(
            work_description=(
                "Reviews and analyzes federal government software systems. "
                "Develops and maintains application software for internal clients."
            ),
            db_path=str(noc_mapping_db),
        )

        assert isinstance(result.candidates, list)
        assert len(result.candidates) >= 1


async def test_fts5_query_empty_after_filtering_raises_value_error(
    noc_mapping_db, monkeypatch, tmp_path
):
    """map_work_description raises ValueError (→ 422) when work description is all stop words."""
    _set_env(monkeypatch, str(noc_mapping_db), tmp_path)

    from app.services.noc_mapper import map_work_description

    with pytest.raises(ValueError, match="no usable search terms"):
        await map_work_description(
            work_description="the a an",
            db_path=str(noc_mapping_db),
        )


async def test_confirm_noc_404_when_wd_missing(test_db_routing, noc_mapping_db):
    """POST /api/noc/confirm with unknown wd_id returns HTTP 404."""
    with patch("app.main.ollama_client_factory", return_value=_make_mock_ollama_client()):
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/noc/confirm",
                data={"wd_id": "nonexistent-id", "noc_code": "21232"},
            )
            assert response.status_code == 404
