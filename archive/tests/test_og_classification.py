"""
tests/test_og_classification.py — Integration tests for OG classification pipeline
and FastAPI routes POST /api/og/classify and POST /api/og/confirm.

Wave 0: stubs that skip until app/api/og_classification.py is implemented (Plan 05-03).
"""
from __future__ import annotations

import json
import pytest

# Module-level bootstrap guard (same pattern as test_noc_mapping.py)
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
def _bootstrap_app_modules(og_db, monkeypatch, tmp_path):
    global _app_bootstrapped
    if not _app_bootstrapped:
        _set_env(monkeypatch, str(og_db), tmp_path)
        _clear_app_modules()
        try:
            import app.main  # noqa: F401
            _app_bootstrapped = True
        except Exception:
            pass  # App may not be wired yet in Wave 0
    yield


class TestOGClassifyRoute:
    def test_classify_requires_noc_mapped_stage(self, og_db):
        """POST /api/og/classify returns 422 if WorkDescription not in noc_mapped stage."""
        try:
            from app.api import og_classification  # noqa: F401
        except ImportError:
            pytest.skip("app.api.og_classification not yet implemented")

    def test_classify_og_returns_3_candidates(self, og_db):
        """classify_og() returns 3 candidates with og_code, og_name, definition, inclusions, exclusions."""
        try:
            from app.services.og_classifier import classify_og  # noqa: F401
        except ImportError:
            pytest.skip("app.services.og_classifier not yet implemented")

    def test_api_route_htmx_returns_html(self, og_db):
        """HTMX POST /api/og/classify returns HTML partial (text/html content type)."""
        try:
            from app.api import og_classification  # noqa: F401
        except ImportError:
            pytest.skip("app.api.og_classification not yet implemented")


class TestOGConfirmRoute:
    def test_confirm_requires_valid_level(self, og_db):
        """POST /api/og/confirm returns 422 if og_level missing or invalid for og_code."""
        try:
            from app.api import og_classification  # noqa: F401
        except ImportError:
            pytest.skip("app.api.og_classification not yet implemented")

    def test_confirm_sets_stage_og_classified(self, og_db):
        """After confirm, WorkDescription.stage == 'og_classified'."""
        try:
            from app.api import og_classification  # noqa: F401
        except ImportError:
            pytest.skip("app.api.og_classification not yet implemented")

    def test_confirm_requires_og_level_not_empty(self, og_db):
        """POST /api/og/confirm returns 422 if og_level is empty string."""
        try:
            from app.api import og_classification  # noqa: F401
        except ImportError:
            pytest.skip("app.api.og_classification not yet implemented")


class TestOGProvenance:
    def test_og_candidate_provenance_tag_source_type(self, og_db):
        """OGCandidate cited_articles contain ProvenanceTag with source_type='TBS_OG_DEF'."""
        try:
            from app.services.og_classifier import classify_og  # noqa: F401
        except ImportError:
            pytest.skip("app.services.og_classifier not yet implemented")


class TestASECDisambiguation:
    def test_asec_alert_citations_are_verbatim(self, og_db):
        """AS/EC alert includes verbatim AS inclusion and EC exclusion text from og_definitions."""
        try:
            from app.services.og_classifier import classify_og  # noqa: F401
        except ImportError:
            pytest.skip("app.services.og_classifier not yet implemented")

    def test_as_ec_disambiguation_present_for_policy_work(self, og_db):
        """AS vs EC block present in response when policy duties detected."""
        try:
            from app.services.og_classifier import classify_og  # noqa: F401
        except ImportError:
            pytest.skip("app.services.og_classifier not yet implemented")


class TestOGGate:
    def test_og_gate_enforced(self, og_db, monkeypatch, tmp_path):
        """JD generation endpoint returns 422 without confirmed OG (CLASS-02 gate)."""
        import sys

        # Set env vars pointing to og_db fixture path
        monkeypatch.setenv("DB_PATH", str(og_db))
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
        monkeypatch.setenv("GENERATION_MODEL", "gemma4:31b")
        monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
        monkeypatch.setenv("LOG_LEVEL", "WARNING")

        for mod in list(sys.modules.keys()):
            if mod.startswith("app."):
                del sys.modules[mod]

        try:
            from app.api import jd_generation  # noqa: F401 — must exist for gate to be wired
        except ImportError:
            pytest.skip("app.api.jd_generation not yet implemented — Phase 6 plan 03 required")

        from fastapi.testclient import TestClient
        from app.main import app
        from app.db import get_connection
        from app.models.work_description import WorkDescription, NOCMatch, ProvenanceTag
        from app.services.wd_store import save_work_description
        from datetime import date

        # Create a WD in stage='noc_mapped' — not yet og_classified
        conn = get_connection(str(og_db))
        noc_prov = ProvenanceTag(
            source_type="NOC",
            source_id="21232",
            source_version="NOC 2021 v1.0",
            retrieved_date=date.today(),
        )
        noc_match = NOCMatch(
            noc_code="21232",
            noc_title="Software engineers and designers",
            teer_level="1",
            confidence=0.9,
            rationale="Test match",
            provenance=noc_prov,
        )
        wd = WorkDescription(
            session_id="test-gate-session",
            raw_input="Administers HR programs for the department.",
            confirmed_noc=noc_match,
            stage="noc_mapped",  # NOT og_classified — gate must reject this
        )
        save_work_description(conn, wd)
        conn.close()

        client = TestClient(app)
        resp = client.post("/api/jd/generate-duties", data={"wd_id": str(wd.id)})
        assert resp.status_code == 422, (
            f"Expected HTTP 422 for noc_mapped stage (CLASS-02 gate). "
            f"Got {resp.status_code}: {resp.text}"
        )
