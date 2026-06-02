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
