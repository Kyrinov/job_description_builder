"""
tests/test_drf.py — Phase 9 DND DRF Integration tests.

All tests skip (not error) until Plans 09-02 (ingest script + service),
09-03 (router + API), and 09-04 (wizard step + DOCX section) land.

The contract being asserted:
    - GET /api/drf-links/{wd_id} returns 404 for unknown WD
    - GET /api/drf-links/{wd_id} returns 200 with empty candidates for
      non-DND positions
    - GET /api/drf-links/{wd_id} returns candidate list with
      (core_responsibility, departmental_result, fiscal_year) per item
      for DND positions
    - POST /api/drf-links/{wd_id}/confirm stores confirmed linkages on
      WD.drf_linkages (list of dicts)
    - After confirm, wd.drf_linkages[0]['provenance_source_id'] matches
      the drf_rows.id
    - Service-level: matching uses overlap between duty text tokens and
      the indexed drf_rows.search_text
    - DOCX export context dict contains drf_linkages key with at least
      1 entry when WD is DND with confirmed linkages
    - GET /wizard/drf?wd_id=... returns "not a DND position" indicator
      when is_dnd_position=False
    - GET /wizard/drf?wd_id=... renders candidate list when WD is DND
"""
from __future__ import annotations

import pytest

_drf_app_bootstrapped = False


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
def _bootstrap_app_modules(drf_db, monkeypatch, tmp_path):
    global _drf_app_bootstrapped
    if not _drf_app_bootstrapped:
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            import app.main  # noqa: F401
            _drf_app_bootstrapped = True
        except Exception:
            pass
    yield


# ---------------------------------------------------------------------------
# Router contract: GET /api/drf-links/{wd_id}
# ---------------------------------------------------------------------------


class TestGetDRFLinks:
    def test_drf_get_links_404_for_unknown_wd(self, drf_db, monkeypatch, tmp_path):
        """GET /api/drf-links/{wd_id} returns 404 when the WorkDescription is not found."""
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")
        pytest.skip("not yet implemented — Phase 9 plan 09-02/09-03/09-04")

    def test_drf_get_links_200_for_non_dnd_position(self, drf_db, monkeypatch, tmp_path):
        """GET /api/drf-links/{wd_id} returns 200 with empty candidates when is_dnd_position=False."""
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")
        pytest.skip("not yet implemented — Phase 9 plan 09-02/09-03/09-04")

    def test_drf_get_links_returns_candidates(self, drf_db, monkeypatch, tmp_path):
        """GET /api/drf-links/{wd_id} with DND position returns a list whose
        items each include core_responsibility, departmental_result, fiscal_year."""
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")
        pytest.skip("not yet implemented — Phase 9 plan 09-02/09-03/09-04")


# ---------------------------------------------------------------------------
# Router contract: POST /api/drf-links/{wd_id}/confirm
# ---------------------------------------------------------------------------


class TestConfirmDRFLinks:
    def test_drf_confirm_linkages_stores_on_wd(self, drf_db, monkeypatch, tmp_path):
        """POST /api/drf-links/{wd_id}/confirm stores the confirmed linkages on the WorkDescription."""
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")
        pytest.skip("not yet implemented — Phase 9 plan 09-02/09-03/09-04")

    def test_drf_confirm_sets_provenance(self, drf_db, monkeypatch, tmp_path):
        """After confirm, wd.drf_linkages[0]['provenance_source_id'] equals the drf_rows.id of the source row."""
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")
        pytest.skip("not yet implemented — Phase 9 plan 09-02/09-03/09-04")


# ---------------------------------------------------------------------------
# Service contract: matching
# ---------------------------------------------------------------------------


class TestDRFMatchingService:
    def test_drf_matching_uses_duty_text_keywords(self, drf_db, monkeypatch, tmp_path):
        """The DRF matching service returns rows whose search_text overlaps
        with tokens drawn from the WD's draft duty text."""
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from app.services.drf_service import find_drf_candidates  # noqa: F401
        except ImportError:
            pytest.skip("app.services.drf_service not yet implemented")
        pytest.skip("not yet implemented — Phase 9 plan 09-02")


# ---------------------------------------------------------------------------
# Export contract: DOCX render includes DRF section
# ---------------------------------------------------------------------------


class TestDRFExport:
    def test_drf_export_includes_drf_section(self, drf_db, monkeypatch, tmp_path):
        """After DRF confirm + export, the DOCX context dict contains a
        'drf_linkages' key with at least 1 entry."""
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from app.services.export_service import build_version_manifest  # noqa: F401
        except ImportError:
            pytest.skip("app.services.export_service not yet implemented")
        pytest.skip("not yet implemented — Phase 9 plan 09-04")


# ---------------------------------------------------------------------------
# Wizard contract: GET /wizard/drf
# ---------------------------------------------------------------------------


class TestDRFWizardStep:
    def test_drf_non_dnd_wizard_step_hidden(self, drf_db, monkeypatch, tmp_path):
        """GET /wizard/drf?wd_id=... when is_dnd_position=False returns a
        response that indicates the position is not a DND position."""
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")
        pytest.skip("not yet implemented — Phase 9 plan 09-04")

    def test_drf_wizard_step_renders_candidates(self, drf_db, monkeypatch, tmp_path):
        """GET /wizard/drf?wd_id=... with a DND WD renders the candidate list."""
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")
        pytest.skip("not yet implemented — Phase 9 plan 09-04")
