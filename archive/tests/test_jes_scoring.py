"""
tests/test_jes_scoring.py — Phase 7 JES Scoring tests.

All tests skip (not error) until app/ai/jes_scoring.py, app/services/jes_service.py,
and app/api/jes_scoring.py land in Plans 07-02 and 07-03.

Stage gate: WorkDescription must be in stage='jd_drafted' before POST /api/jes/score.
Sentinel: JESFactorScore.level == -1 indicates a failed factor (not None — level is non-optional int).
"""
from __future__ import annotations

import pytest

_app_bootstrapped = False


def _set_env(monkeypatch, db_path: str, tmp_path) -> None:
    """Set minimum required env vars for app startup in tests."""
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("GENERATION_MODEL", "gemma4:31b")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")


def _clear_app_modules():
    import sys
    for mod in list(sys.modules.keys()):
        if mod.startswith("app."):
            del sys.modules[mod]


@pytest.fixture(autouse=True)
def _bootstrap_app_modules(jes_db, monkeypatch, tmp_path):
    global _app_bootstrapped
    if not _app_bootstrapped:
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            import app.main  # noqa: F401
            _app_bootstrapped = True
        except Exception:
            pass
    yield


def _make_jd_drafted_wd(db_path: str) -> str:
    """Insert a WorkDescription in stage='jd_drafted' with confirmed OG=EC. Returns wd_id."""
    try:
        from app.db import get_connection
        from app.models.work_description import (
            DraftDuty, NOCMatch, OGRecommendation, ProvenanceTag, WorkDescription,
        )
        from app.services.wd_store import save_work_description
        from datetime import date
    except ImportError:
        pytest.skip("app modules not yet implemented")

    conn = get_connection(db_path)
    noc_prov = ProvenanceTag(
        source_type="NOC", source_id="21232",
        source_version="NOC 2021 v1.0", retrieved_date=date.today(),
    )
    noc_match = NOCMatch(
        noc_code="21232", noc_title="Software engineers and designers",
        teer_level="1", confidence=0.9, rationale="Test match",
        matched_duty_statements=[], provenance=noc_prov,
    )
    og_prov = ProvenanceTag(
        source_type="TBS_OG_DEF", source_id="EC",
        source_version="TBS-OCHRO-OG.txt", retrieved_date=date.today(),
    )
    og_rec = OGRecommendation(
        og_code="EC", og_name="Economics and Social Science Services",
        level="EC-04", confidence=0.85, rationale="Test OG",
        provenance=og_prov, confirmed_by_advisor=True,
    )
    duty_prov = ProvenanceTag(
        source_type="NOC", source_id="21232",
        source_version="NOC 2021 v1.0", retrieved_date=date.today(),
    )
    duties = [
        DraftDuty(text="Provides economic policy analysis.", provenance=duty_prov),
        DraftDuty(text="Conducts program evaluation research.", provenance=duty_prov),
    ]
    wd = WorkDescription(
        session_id="test-session-jes",
        raw_input="Provides economic policy analysis and program evaluation.",
        confirmed_noc=noc_match,
        confirmed_og="EC",
        confirmed_level="EC-04",
        og_recommendation=og_rec,
        draft_duties=duties,
        stage="jd_drafted",
    )
    save_work_description(conn, wd)
    conn.close()
    return str(wd.id)


def _make_og_classified_wd(db_path: str) -> str:
    """Insert a WorkDescription in stage='og_classified' (wrong stage for JES). Returns wd_id."""
    try:
        from app.db import get_connection
        from app.models.work_description import (
            NOCMatch, OGRecommendation, ProvenanceTag, WorkDescription,
        )
        from app.services.wd_store import save_work_description
        from datetime import date
    except ImportError:
        pytest.skip("app modules not yet implemented")

    conn = get_connection(db_path)
    noc_prov = ProvenanceTag(
        source_type="NOC", source_id="21232",
        source_version="NOC 2021 v1.0", retrieved_date=date.today(),
    )
    noc_match = NOCMatch(
        noc_code="21232", noc_title="Software engineers and designers",
        teer_level="1", confidence=0.9, rationale="Test match",
        matched_duty_statements=[], provenance=noc_prov,
    )
    og_prov = ProvenanceTag(
        source_type="TBS_OG_DEF", source_id="EC",
        source_version="TBS-OCHRO-OG.txt", retrieved_date=date.today(),
    )
    og_rec = OGRecommendation(
        og_code="EC", og_name="Economics and Social Science Services",
        level="EC-04", confidence=0.85, rationale="Test OG",
        provenance=og_prov, confirmed_by_advisor=True,
    )
    wd = WorkDescription(
        session_id="test-session-jes-wrong-stage",
        raw_input="Test wrong stage WD.",
        confirmed_noc=noc_match,
        confirmed_og="EC",
        confirmed_level="EC-04",
        og_recommendation=og_rec,
        stage="og_classified",
    )
    save_work_description(conn, wd)
    conn.close()
    return str(wd.id)


class TestJESScoringStageGate:
    def test_score_jes_stage_gate(self, jes_db, monkeypatch, tmp_path):
        """POST /api/jes/score returns 422 if stage != 'jd_drafted'."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.api import jes_scoring  # noqa: F401
        except ImportError:
            pytest.skip("app.api.jes_scoring not yet implemented")

        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)

        wd_id = _make_og_classified_wd(str(jes_db))
        resp = client.post("/api/jes/score", data={"wd_id": wd_id})
        assert resp.status_code == 422

    def test_score_jes_404_on_unknown_wd(self, jes_db, monkeypatch, tmp_path):
        """POST /api/jes/score returns 404 for unknown wd_id."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.api import jes_scoring  # noqa: F401
        except ImportError:
            pytest.skip("app.api.jes_scoring not yet implemented")

        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)

        resp = client.post(
            "/api/jes/score",
            data={"wd_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 404


class TestJESFactorScoreSchema:
    def test_jes_factor_score_has_required_fields(self, jes_db, monkeypatch, tmp_path):
        """JESFactorScore model has factor_name, level (int), rationale, provenance."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.models.work_description import JESFactorScore, ProvenanceTag
        except ImportError:
            pytest.skip("app.models.work_description not yet implemented")

        from datetime import date
        prov = ProvenanceTag(
            source_type="JES", source_id="EC/Decision making",
            source_version="JES v1.0", retrieved_date=date.today(),
        )
        score = JESFactorScore(
            factor_name="Decision making",
            level=3,
            points=35,
            rationale="Position makes branch-level decisions.",
            provenance=prov,
        )
        assert score.factor_name == "Decision making"
        assert score.level == 3
        assert score.points == 35
        assert score.rationale
        assert score.provenance.source_type == "JES"

    def test_jes_factor_score_sentinel_level(self, jes_db, monkeypatch, tmp_path):
        """JESFactorScore.level=-1 is valid (failure sentinel, not None)."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.models.work_description import JESFactorScore, ProvenanceTag
        except ImportError:
            pytest.skip("app.models.work_description not yet implemented")

        from datetime import date
        prov = ProvenanceTag(
            source_type="JES", source_id="EC/Decision making",
            source_version="JES v1.0", retrieved_date=date.today(),
        )
        score = JESFactorScore(
            factor_name="Decision making",
            level=-1,
            points=None,
            rationale="Scoring failed after 3 retries: model timeout",
            provenance=prov,
        )
        assert score.level == -1
        assert score.points is None


class TestJESFactorRatingSchema:
    def test_jes_factor_rating_validates_degree_rationale(self, jes_db, monkeypatch, tmp_path):
        """JESFactorRating Pydantic model validates degree + rationale fields."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.ai.jes_scoring import JESFactorRating
        except ImportError:
            pytest.skip("app.ai.jes_scoring not yet implemented")

        rating = JESFactorRating(degree="D3", rationale="Branch-level decision making.")
        assert rating.degree == "D3"
        assert rating.rationale


class TestProvenanceTagJES:
    def test_provenance_tag_source_type_jes(self, jes_db, monkeypatch, tmp_path):
        """ProvenanceTag with source_type='JES' is valid and renders source_id correctly."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.models.work_description import ProvenanceTag
        except ImportError:
            pytest.skip("app.models.work_description not yet implemented")

        from datetime import date
        prov = ProvenanceTag(
            source_type="JES",
            source_id="EC/Decision making",
            source_version="JES v1.0",
            retrieved_date=date.today(),
        )
        assert prov.source_type == "JES"
        assert prov.source_id == "EC/Decision making"
        assert prov.source_version == "JES v1.0"


class TestNoFactors:
    def test_score_jes_raises_on_empty_factor_list(self, jes_db, monkeypatch, tmp_path):
        """score_jes() raises ValueError when no jes_factors rows exist for the confirmed OG."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.services.jes_service import score_jes
        except ImportError:
            pytest.skip("app.services.jes_service not yet implemented")

        from app.db import get_connection

        try:
            from app.models.work_description import (
                NOCMatch, OGRecommendation, ProvenanceTag, WorkDescription,
            )
            from app.services.wd_store import save_work_description
            from datetime import date
        except ImportError:
            pytest.skip("app modules not yet implemented")

        conn = get_connection(str(jes_db))
        noc_prov = ProvenanceTag(
            source_type="NOC", source_id="21232",
            source_version="NOC 2021 v1.0", retrieved_date=date.today(),
        )
        noc_match = NOCMatch(
            noc_code="21232", noc_title="Admin officer",
            teer_level="1", confidence=0.7, rationale="Test",
            matched_duty_statements=[], provenance=noc_prov,
        )
        og_prov = ProvenanceTag(
            source_type="TBS_OG_DEF", source_id="AS",
            source_version="TBS-OCHRO-OG.txt", retrieved_date=date.today(),
        )
        og_rec = OGRecommendation(
            og_code="AS", og_name="Administrative Services",
            level="AS-03", confidence=0.7, rationale="Test",
            provenance=og_prov, confirmed_by_advisor=True,
        )
        wd = WorkDescription(
            session_id="test-no-factors",
            raw_input="Admin duties.",
            confirmed_noc=noc_match,
            confirmed_og="AS",
            confirmed_level="AS-03",
            og_recommendation=og_rec,
            stage="jd_drafted",
        )
        save_work_description(conn, wd)
        conn.close()

        import asyncio
        with pytest.raises(ValueError, match="No JES factors found for OG"):
            asyncio.run(score_jes(wd_id=str(wd.id), db_path=str(jes_db)))


class TestStageTransition:
    def test_stage_transitions_to_jes_scored(self, jes_db, monkeypatch, tmp_path):
        """WD stage == 'jes_scored' after successful score_jes() call (mocked LLM)."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.services.jes_service import score_jes
        except ImportError:
            pytest.skip("app.services.jes_service not yet implemented")

        pytest.skip("Requires LLM mock — implement after Plan 07-03 lands")


class TestJESInstructorClient:
    def test_jes_instructor_client_singleton_exists(self, jes_db, monkeypatch, tmp_path):
        """jes_instructor_client singleton is importable from app.ai.jes_scoring."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.ai.jes_scoring import jes_instructor_client
        except ImportError:
            pytest.skip("app.ai.jes_scoring not yet implemented")

        assert jes_instructor_client is not None


# ---------------------------------------------------------------------------
# Phase 08.1: per-factor retry + override (service-layer recovery paths)
# ---------------------------------------------------------------------------


def _make_jes_scored_wd(db_path: str, *, with_sentinel: bool = False) -> tuple:
    """Insert a WorkDescription in stage='jes_scored' with the two EC factors.

    When with_sentinel=False: both factors are fully scored (Decision making D3=35pts,
    Communication D2=30pts; total=65).
    When with_sentinel=True: Decision making is fully scored; Communication is the
    failed-factor sentinel (level=-1, points=None; total=35).

    Returns (wd_id, decision_factor_name, communication_factor_name).
    """
    try:
        from app.db import get_connection
        from app.models.work_description import (
            DraftDuty, JESFactorScore, NOCMatch, OGRecommendation,
            ProvenanceTag, WorkDescription,
        )
        from app.services.wd_store import save_work_description
        from datetime import date
    except ImportError:
        pytest.skip("app modules not yet implemented")

    conn = get_connection(db_path)
    noc_prov = ProvenanceTag(
        source_type="NOC", source_id="21232",
        source_version="NOC 2021 v1.0", retrieved_date=date.today(),
    )
    noc_match = NOCMatch(
        noc_code="21232", noc_title="Software engineers and designers",
        teer_level="1", confidence=0.9, rationale="Test match",
        matched_duty_statements=[], provenance=noc_prov,
    )
    og_prov = ProvenanceTag(
        source_type="TBS_OG_DEF", source_id="EC",
        source_version="TBS-OCHRO-OG.txt", retrieved_date=date.today(),
    )
    og_rec = OGRecommendation(
        og_code="EC", og_name="Economics and Social Science Services",
        level="EC-04", confidence=0.85, rationale="Test OG",
        provenance=og_prov, confirmed_by_advisor=True,
    )
    duty_prov = ProvenanceTag(
        source_type="NOC", source_id="21232",
        source_version="NOC 2021 v1.0", retrieved_date=date.today(),
    )
    duties = [
        DraftDuty(text="Provides economic policy analysis.", provenance=duty_prov),
        DraftDuty(text="Conducts program evaluation research.", provenance=duty_prov),
    ]
    jes_prov_dm = ProvenanceTag(
        source_type="JES", source_id="EC/Decision making",
        source_version="JES v1.0", retrieved_date=date.today(),
    )
    jes_prov_cm = ProvenanceTag(
        source_type="JES", source_id="EC/Communication",
        source_version="JES v1.0", retrieved_date=date.today(),
    )
    if with_sentinel:
        jes_scores = [
            JESFactorScore(
                factor_name="Decision making", level=3, points=35,
                rationale="High latitude",
                provenance=jes_prov_dm,
            ),
            JESFactorScore(
                factor_name="Communication", level=-1, points=None,
                rationale="Scoring failed after 3 retries: model timeout",
                provenance=jes_prov_cm,
            ),
        ]
        jes_total_points = 35
    else:
        jes_scores = [
            JESFactorScore(
                factor_name="Decision making", level=3, points=35,
                rationale="High latitude",
                provenance=jes_prov_dm,
            ),
            JESFactorScore(
                factor_name="Communication", level=2, points=30,
                rationale="Explains findings",
                provenance=jes_prov_cm,
            ),
        ]
        jes_total_points = 65
    wd = WorkDescription(
        session_id="test-session-jes-scored",
        raw_input="Provides economic policy analysis and program evaluation.",
        confirmed_noc=noc_match,
        confirmed_og="EC",
        confirmed_level="EC-04",
        og_recommendation=og_rec,
        draft_duties=duties,
        jes_scores=jes_scores,
        jes_total_points=jes_total_points,
        stage="jes_scored",
    )
    save_work_description(conn, wd)
    conn.close()
    return str(wd.id), "Decision making", "Communication"


def _make_jd_drafted_wd_for_retry(db_path: str) -> str:
    """Insert a WD in stage='jd_drafted' (wrong stage for retry)."""
    return _make_jd_drafted_wd(db_path)


class TestRetryJESFactor:
    def test_retry_jes_factor_replaces_failed_score(self, jes_db, monkeypatch, tmp_path):
        """retry_jes_factor replaces the failed factor's score and recomputes total."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.services.jes_service import retry_jes_factor
            from app.services.wd_store import load_work_description
            from app.db import get_connection
            from app.ai.jes_scoring import JESFactorRating
            from unittest.mock import AsyncMock, MagicMock, patch
        except ImportError:
            pytest.skip("retry_jes_factor dependencies not yet implemented")

        wd_id, _, comm_name = _make_jes_scored_wd(str(jes_db), with_sentinel=True)

        # Mock the LLM call to return a successful D2/30pts Communication rating
        mock_rating = JESFactorRating(degree="D2", rationale="Explains findings")
        mock_response = MagicMock()
        mock_response.degree = "D2"
        mock_response.rationale = "Explains findings"

        async def _fake_create(*args, **kwargs):
            return mock_response

        with patch(
            "app.services.jes_service.jes_instructor_client"
        ) as mock_client:
            mock_client.chat.completions.create = AsyncMock(side_effect=_fake_create)
            import asyncio
            result = asyncio.run(
                retry_jes_factor(wd_id=wd_id, factor_name=comm_name, db_path=str(jes_db))
            )

        assert result["wd_id"] == wd_id
        assert result["factor_name"] == comm_name
        assert result["level"] == 2
        assert result["points"] == 30
        assert result["jes_total_points"] == 65  # 35 (Decision making) + 30 (new Communication)

        # Verify the WD was saved with the replaced factor
        conn = get_connection(str(jes_db))
        try:
            wd = load_work_description(conn, wd_id)
        finally:
            conn.close()
        assert wd is not None
        comm_score = next(s for s in wd.jes_scores if s.factor_name == comm_name)
        assert comm_score.level == 2
        assert comm_score.points == 30
        # Order preserved: Decision making is still at index 0
        assert wd.jes_scores[0].factor_name == "Decision making"
        assert wd.jes_scores[1].factor_name == "Communication"

    def test_retry_jes_factor_raises_on_unknown_factor(self, jes_db, monkeypatch, tmp_path):
        """retry_jes_factor raises ValueError when factor_name not in wd.jes_scores."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.services.jes_service import retry_jes_factor
        except ImportError:
            pytest.skip("retry_jes_factor not yet implemented")

        wd_id, _, _ = _make_jes_scored_wd(str(jes_db))

        import asyncio
        with pytest.raises(ValueError, match="Nonexistent factor"):
            asyncio.run(
                retry_jes_factor(
                    wd_id=wd_id, factor_name="Nonexistent factor", db_path=str(jes_db)
                )
            )

    def test_retry_jes_factor_raises_on_wrong_stage(self, jes_db, monkeypatch, tmp_path):
        """retry_jes_factor raises ValueError when wd.stage != 'jes_scored'."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.services.jes_service import retry_jes_factor
        except ImportError:
            pytest.skip("retry_jes_factor not yet implemented")

        wd_id = _make_jd_drafted_wd_for_retry(str(jes_db))  # stage='jd_drafted'

        import asyncio
        with pytest.raises(ValueError, match="expected 'jes_scored'"):
            asyncio.run(
                retry_jes_factor(
                    wd_id=wd_id, factor_name="Decision making", db_path=str(jes_db)
                )
            )

    def test_retry_jes_factor_preserves_old_score_on_llm_failure(
        self, jes_db, monkeypatch, tmp_path
    ):
        """retry_jes_factor preserves the old score when the LLM call raises."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.services.jes_service import retry_jes_factor
            from app.services.wd_store import load_work_description
            from app.db import get_connection
            from unittest.mock import AsyncMock, patch
        except ImportError:
            pytest.skip("retry_jes_factor dependencies not yet implemented")

        wd_id, _, comm_name = _make_jes_scored_wd(str(jes_db), with_sentinel=True)

        async def _raise(*args, **kwargs):
            raise RuntimeError("simulated LLM timeout")

        with patch("app.services.jes_service.jes_instructor_client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(side_effect=_raise)
            import asyncio
            with pytest.raises(ValueError, match="Retry failed"):
                asyncio.run(
                    retry_jes_factor(
                        wd_id=wd_id, factor_name=comm_name, db_path=str(jes_db)
                    )
                )

        # Verify the old sentinel score is preserved (NOT replaced)
        conn = get_connection(str(jes_db))
        try:
            wd = load_work_description(conn, wd_id)
        finally:
            conn.close()
        assert wd is not None
        comm_score = next(s for s in wd.jes_scores if s.factor_name == comm_name)
        assert comm_score.level == -1
        assert comm_score.points is None
        assert "failed" in comm_score.rationale.lower()


class TestOverrideJESFactor:
    def test_override_jes_factor_sets_adjusted_fields(
        self, jes_db, monkeypatch, tmp_path
    ):
        """override_jes_factor sets advisor_adjusted fields and flips provenance to ADVISOR."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.services.jes_service import override_jes_factor
            from app.services.wd_store import load_work_description
            from app.db import get_connection
        except ImportError:
            pytest.skip("override_jes_factor dependencies not yet implemented")

        wd_id, _, comm_name = _make_jes_scored_wd(str(jes_db), with_sentinel=True)

        result = override_jes_factor(
            wd_id=wd_id,
            factor_name=comm_name,
            level=2,
            points=30,
            rationale="Communications align with the role's writing duties.",
            db_path=str(jes_db),
        )

        assert result["wd_id"] == wd_id
        assert result["factor_name"] == comm_name
        score = result["score"]
        assert score.advisor_adjusted is True
        assert score.advisor_adjusted_level == 2
        assert score.advisor_adjustment_rationale.startswith("Communications")
        assert score.provenance.source_type == "ADVISOR"
        assert score.provenance.modified_by_advisor is True
        assert score.level == 2
        assert score.points == 30

        # Verify the WD was saved
        conn = get_connection(str(jes_db))
        try:
            wd = load_work_description(conn, wd_id)
        finally:
            conn.close()
        assert wd is not None
        comm_score = next(s for s in wd.jes_scores if s.factor_name == comm_name)
        assert comm_score.advisor_adjusted is True

    def test_override_jes_factor_recomputes_total(self, jes_db, monkeypatch, tmp_path):
        """override_jes_factor recomputes jes_total_points using the new points."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.services.jes_service import override_jes_factor
        except ImportError:
            pytest.skip("override_jes_factor not yet implemented")

        wd_id, _, comm_name = _make_jes_scored_wd(str(jes_db), with_sentinel=True)
        # Sentinel WD has Decision making=35 + Communication=-1/None; total=35

        result = override_jes_factor(
            wd_id=wd_id,
            factor_name=comm_name,
            level=2,
            points=20,
            rationale="Test rationale text here for the override.",
            db_path=str(jes_db),
        )

        # Total should now be 35 (Decision making) + 20 (new Communication override) = 55
        assert result["jes_total_points"] == 55

    def test_override_jes_factor_raises_on_short_rationale(
        self, jes_db, monkeypatch, tmp_path
    ):
        """override_jes_factor raises ValueError when rationale is < 10 chars."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.services.jes_service import override_jes_factor
        except ImportError:
            pytest.skip("override_jes_factor not yet implemented")

        wd_id, _, comm_name = _make_jes_scored_wd(str(jes_db))

        with pytest.raises(ValueError, match="10 characters"):
            override_jes_factor(
                wd_id=wd_id,
                factor_name=comm_name,
                level=2,
                points=20,
                rationale="too short",
                db_path=str(jes_db),
            )

    def test_override_jes_factor_raises_on_invalid_level(
        self, jes_db, monkeypatch, tmp_path
    ):
        """override_jes_factor raises ValueError when level < 1."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.services.jes_service import override_jes_factor
        except ImportError:
            pytest.skip("override_jes_factor not yet implemented")

        wd_id, _, comm_name = _make_jes_scored_wd(str(jes_db))

        with pytest.raises(ValueError, match="level must be an int"):
            override_jes_factor(
                wd_id=wd_id,
                factor_name=comm_name,
                level=0,
                points=20,
                rationale="Test rationale text here for the override.",
                db_path=str(jes_db),
            )

    def test_override_jes_factor_raises_on_unknown_factor(
        self, jes_db, monkeypatch, tmp_path
    ):
        """override_jes_factor raises ValueError when factor_name not in wd.jes_scores."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.services.jes_service import override_jes_factor
        except ImportError:
            pytest.skip("override_jes_factor not yet implemented")

        wd_id, _, _ = _make_jes_scored_wd(str(jes_db))

        with pytest.raises(ValueError, match="Nonexistent factor"):
            override_jes_factor(
                wd_id=wd_id,
                factor_name="Nonexistent factor",
                level=2,
                points=20,
                rationale="Test rationale text here for the override.",
                db_path=str(jes_db),
            )


# ---------------------------------------------------------------------------
# Phase 08.1 Plan 02: per-factor retry + override HTTP routes
# ---------------------------------------------------------------------------


class TestRetryJESFactorRoute:
    def test_retry_route_returns_updated_factor_card(
        self, jes_db, monkeypatch, tmp_path
    ):
        """POST /api/jes/retry/{wd_id}/{Communication} (HTMX) returns 200 with
        the updated single-card partial (no longer in error state)."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.api.jes_scoring import retry_jes_factor_route  # noqa: F401
            from app.services.jes_service import retry_jes_factor  # noqa: F401
            from app.ai.jes_scoring import JESFactorRating
            from fastapi.testclient import TestClient
            from app.main import app
            from unittest.mock import AsyncMock, MagicMock, patch
        except ImportError:
            pytest.skip("retry route dependencies not yet implemented")

        wd_id, _, comm_name = _make_jes_scored_wd(str(jes_db), with_sentinel=True)

        mock_response = MagicMock()
        mock_response.degree = "D3"
        mock_response.rationale = "Communicates branch-level decisions and recommendations."

        async def _fake_create(*args, **kwargs):
            return mock_response

        with patch("app.services.jes_service.jes_instructor_client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(side_effect=_fake_create)
            client = TestClient(app)
            response = client.post(
                f"/api/jes/retry/{wd_id}/{comm_name}",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200
        body = response.text
        # Stable HTMX target id is in the card
        assert 'id="factor-communication"' in body
        # Mocked degree D3 should be present
        assert "D3" in body
        # The card is no longer in error state (override state is also not set)
        assert "jes-factor-card--error" not in body

    def test_retry_route_404_on_unknown_factor(
        self, jes_db, monkeypatch, tmp_path
    ):
        """POST /api/jes/retry/{wd_id}/NonexistentFactor returns 404 (the
        ValueError("JES factor 'X' not found in WorkDescription") matches
        the "not found" branch of the route's error mapping)."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")

        wd_id, _, _ = _make_jes_scored_wd(str(jes_db))

        client = TestClient(app)
        response = client.post(
            f"/api/jes/retry/{wd_id}/NonexistentFactor",
            headers={"HX-Request": "true"},
        )
        # 404: factor_name not in wd.jes_scores — matches "not found" in
        # the service's ValueError message
        assert response.status_code == 404
        body = response.text
        assert "NonexistentFactor" in body or "not found" in body.lower()


class TestOverrideJESFactorRoute:
    def test_override_route_returns_advisor_adjusted_card(
        self, jes_db, monkeypatch, tmp_path
    ):
        """POST /api/jes/override/{wd_id}/{Communication} (HTMX) returns 200
        with the advisor-adjusted card (jes-factor-card--advisor + badge)."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")

        wd_id, _, comm_name = _make_jes_scored_wd(str(jes_db), with_sentinel=True)

        client = TestClient(app)
        response = client.post(
            f"/api/jes/override/{wd_id}/{comm_name}",
            data={
                "level": "2",
                "points": "15",
                "rationale": "Test rationale text here for the override.",
            },
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 200
        body = response.text
        # The card is now advisor-adjusted
        assert "jes-factor-card--advisor" in body
        # The badge shows the override level
        assert "Advisor-adjusted (D2)" in body
        # The advisor rationale is rendered
        assert "Test rationale text here" in body

    def test_override_route_422_on_short_rationale(
        self, jes_db, monkeypatch, tmp_path
    ):
        """POST /api/jes/override with rationale < 10 chars returns 422 and
        re-renders the form partial with the validation error inline."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")

        wd_id, _, comm_name = _make_jes_scored_wd(str(jes_db), with_sentinel=True)

        client = TestClient(app)
        response = client.post(
            f"/api/jes/override/{wd_id}/{comm_name}",
            data={"level": "2", "points": "15", "rationale": "short"},
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 422
        body = response.text
        assert "10 characters" in body
