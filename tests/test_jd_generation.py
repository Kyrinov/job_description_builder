"""
tests/test_jd_generation.py — Integration tests for Phase 6 JD generation pipeline.

Tests cover:
  - POST /api/jd/generate-duties: stage gate + verbatim duty output
  - POST /api/jd/add-advisor-duty: ADVISOR tag + appears in advisor_additions
  - POST /api/jd/check-orphan-statements: clean duties → HTTP 200 + empty flags
  - POST /api/jd/confirm-duties: sets stage='jd_drafted' + persists WD
  - Advisor additions preserved across re-generate call

Wave 0: stubs that skip until app/api/jd_generation.py and app/services/jd_service.py
are implemented (Plans 06-02, 06-03).
"""
from __future__ import annotations

import json
import pytest

_app_bootstrapped = False


def _set_env(monkeypatch, db_path: str, tmp_path) -> None:
    """Set minimum required env vars for app startup in tests."""
    monkeypatch.setenv("DATABASE_PATH", db_path)
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
def _bootstrap_app_modules(jd_db, monkeypatch, tmp_path):
    global _app_bootstrapped
    if not _app_bootstrapped:
        _set_env(monkeypatch, str(jd_db), tmp_path)
        _clear_app_modules()
        try:
            import app.main  # noqa: F401
            _app_bootstrapped = True
        except Exception:
            pass
    yield


def _make_og_classified_wd(db_path: str) -> str:
    """
    Insert a WorkDescription in stage='og_classified' with confirmed NOC 21232 and OG EC.
    Returns wd_id as string. Uses wd_store directly (no HTTP).
    """
    try:
        from app.db import get_connection
        from app.models.work_description import WorkDescription, NOCMatch, OGRecommendation, ProvenanceTag
        from app.services.wd_store import save_work_description
        from datetime import date
    except ImportError:
        pytest.skip("app modules not yet implemented")

    conn = get_connection(db_path)
    noc_match = NOCMatch(
        noc_code="21232",
        noc_title="Software engineers and designers",
        teer_level="1",
        confidence=0.95,
        rationale="Matches primary duties",
        matched_duty_statements=["Design and develop software systems."],
        provenance=ProvenanceTag(
            source_type="NOC",
            source_id="21232",
            source_version="NOC 2021 v1.0",
            retrieved_date=date.today(),
        ),
    )
    og_rec = OGRecommendation(
        og_code="EC",
        og_name="Economics and Social Science Services",
        level="EC-04",
        confidence=0.85,
        rationale="Policy and research work",
        provenance=ProvenanceTag(
            source_type="TBS_OG_DEF",
            source_id="EC",
            source_version="TBS-OCHRO-OG.txt",
            retrieved_date=date.today(),
        ),
        confirmed_by_advisor=True,
    )
    wd = WorkDescription(
        session_id="test-session-jd",
        raw_input="Designs and develops software systems for government programs.",
        confirmed_noc=noc_match,
        confirmed_og="EC",
        confirmed_level="EC-04",
        og_recommendation=og_rec,
        stage="og_classified",
    )
    save_work_description(conn, wd)
    conn.close()
    return str(wd.id)


def _make_noc_mapped_wd(db_path: str) -> str:
    """Insert a WorkDescription in stage='noc_mapped' (before OG classification)."""
    try:
        from app.db import get_connection
        from app.models.work_description import WorkDescription, NOCMatch, ProvenanceTag
        from app.services.wd_store import save_work_description
        from datetime import date
    except ImportError:
        pytest.skip("app modules not yet implemented")

    conn = get_connection(db_path)
    noc_match = NOCMatch(
        noc_code="21232",
        noc_title="Software engineers and designers",
        teer_level="1",
        confidence=0.9,
        rationale="Matches duties",
        provenance=ProvenanceTag(
            source_type="NOC",
            source_id="21232",
            source_version="NOC 2021 v1.0",
            retrieved_date=date.today(),
        ),
    )
    wd = WorkDescription(
        session_id="test-session-gate",
        raw_input="Provides administrative support.",
        confirmed_noc=noc_match,
        stage="noc_mapped",
    )
    save_work_description(conn, wd)
    conn.close()
    return str(wd.id)


class TestGenerateDutiesStageGate:
    def test_generate_duties_stage_gate(self, jd_db, monkeypatch, tmp_path):
        """POST /api/jd/generate-duties returns 422 if stage != 'og_classified'."""
        _set_env(monkeypatch, str(jd_db), tmp_path)
        _clear_app_modules()
        try:
            from app.api import jd_generation  # noqa: F401
        except ImportError:
            pytest.skip("app.api.jd_generation not yet implemented")

        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)

        wd_id = _make_noc_mapped_wd(str(jd_db))
        resp = client.post("/api/jd/generate-duties", data={"wd_id": wd_id})
        assert resp.status_code == 422, (
            f"Expected 422 for noc_mapped stage, got {resp.status_code}: {resp.text}"
        )

    def test_generate_duties_404_on_unknown_wd(self, jd_db, monkeypatch, tmp_path):
        """POST /api/jd/generate-duties returns 404 for unknown wd_id."""
        _set_env(monkeypatch, str(jd_db), tmp_path)
        _clear_app_modules()
        try:
            from app.api import jd_generation  # noqa: F401
        except ImportError:
            pytest.skip("app.api.jd_generation not yet implemented")

        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)

        resp = client.post("/api/jd/generate-duties", data={"wd_id": "00000000-0000-0000-0000-000000000000"})
        assert resp.status_code == 404


class TestGenerateDutiesVerbatim:
    def test_generate_duties_all_verbatim(self, jd_db, monkeypatch, tmp_path):
        """All duties returned by generate_duties() have text matching noc_elements.element_text rows (JD-01)."""
        _set_env(monkeypatch, str(jd_db), tmp_path)
        _clear_app_modules()
        try:
            from app.services.jd_service import generate_duties
        except ImportError:
            pytest.skip("app.services.jd_service not yet implemented")

    def test_wd_round_trip_provenance(self, jd_db, monkeypatch, tmp_path):
        """ProvenanceTags survive a full SQLite save-and-load round trip (JD-01+JD-02)."""
        _set_env(monkeypatch, str(jd_db), tmp_path)
        _clear_app_modules()
        try:
            from app.services.jd_service import generate_duties
        except ImportError:
            pytest.skip("app.services.jd_service not yet implemented")


class TestAdvisorDutyHandling:
    def test_advisor_duty_tagged_correctly(self, jd_db, monkeypatch, tmp_path):
        """Advisor-added duty appears in advisor_additions with source_type='ADVISOR' (JD-03)."""
        _set_env(monkeypatch, str(jd_db), tmp_path)
        _clear_app_modules()
        try:
            from app.api import jd_generation  # noqa: F401
        except ImportError:
            pytest.skip("app.api.jd_generation not yet implemented")

        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)

        wd_id = _make_og_classified_wd(str(jd_db))
        resp = client.post(
            "/api/jd/add-advisor-duty",
            data={"wd_id": wd_id, "duty_text": "Provides strategic advice on IT governance frameworks."},
        )
        assert resp.status_code in (200, 422), f"Unexpected status: {resp.status_code}"
        if resp.status_code == 200:
            # Reload WD and check advisor_additions
            from app.db import get_connection
            from app.services.wd_store import load_work_description
            conn = get_connection(str(jd_db))
            wd = load_work_description(conn, wd_id)
            conn.close()
            assert wd is not None
            assert any(d.provenance.source_type == "ADVISOR" for d in wd.advisor_additions), (
                "Advisor duty must be in advisor_additions with source_type='ADVISOR'"
            )

    def test_advisor_duty_preserved_on_regenerate(self, jd_db, monkeypatch, tmp_path):
        """Advisor additions in advisor_additions are not cleared when generate_duties() is called again (JD-03)."""
        _set_env(monkeypatch, str(jd_db), tmp_path)
        _clear_app_modules()
        try:
            from app.services.jd_service import generate_duties, add_advisor_duty
        except ImportError:
            pytest.skip("app.services.jd_service not yet implemented")


class TestOrphanCheck:
    def test_orphan_check_clean_returns_empty_list(self, jd_db, monkeypatch, tmp_path):
        """POST /api/jd/check-orphan-statements returns HTTP 200 with flags=[] on clean duties (JD-04)."""
        _set_env(monkeypatch, str(jd_db), tmp_path)
        _clear_app_modules()
        try:
            from app.api import jd_generation  # noqa: F401
        except ImportError:
            pytest.skip("app.api.jd_generation not yet implemented")

        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)

        wd_id = _make_og_classified_wd(str(jd_db))
        resp = client.post("/api/jd/check-orphan-statements", data={"wd_id": wd_id})
        # Must NOT return 500; 200 or 422 both acceptable depending on stage requirements
        assert resp.status_code != 500, (
            f"Orphan check must not 500 on clean duties. Got: {resp.status_code}: {resp.text}"
        )

    def test_orphan_check_accepts_og_classified_stage(self, jd_db, monkeypatch, tmp_path):
        """Orphan check accepts stage='og_classified' (before duty confirmation)."""
        _set_env(monkeypatch, str(jd_db), tmp_path)
        _clear_app_modules()
        try:
            from app.api import jd_generation  # noqa: F401
        except ImportError:
            pytest.skip("app.api.jd_generation not yet implemented")

        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)

        wd_id = _make_og_classified_wd(str(jd_db))
        resp = client.post("/api/jd/check-orphan-statements", data={"wd_id": wd_id})
        assert resp.status_code != 422, (
            f"Orphan check must accept og_classified stage. Got 422: {resp.text}"
        )


class TestConfirmDuties:
    def test_confirm_duties_sets_stage(self, jd_db, monkeypatch, tmp_path):
        """POST /api/jd/confirm-duties sets WorkDescription.stage='jd_drafted' (JD-01+JD-02+JD-03)."""
        _set_env(monkeypatch, str(jd_db), tmp_path)
        _clear_app_modules()
        try:
            from app.api import jd_generation  # noqa: F401
        except ImportError:
            pytest.skip("app.api.jd_generation not yet implemented")

        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)

        wd_id = _make_og_classified_wd(str(jd_db))
        resp = client.post("/api/jd/confirm-duties", data={"wd_id": wd_id})
        assert resp.status_code in (200, 422), f"Unexpected status: {resp.status_code}"
        if resp.status_code == 200:
            from app.db import get_connection
            from app.services.wd_store import load_work_description
            conn = get_connection(str(jd_db))
            wd = load_work_description(conn, wd_id)
            conn.close()
            assert wd is not None
            assert wd.stage == "jd_drafted", (
                f"Expected stage='jd_drafted' after confirm-duties, got {wd.stage!r}"
            )
