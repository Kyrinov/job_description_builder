"""
tests/test_export.py — Phase 8 Export contract tests.

All tests skip (not error) until app/services/export_service.py lands in
Plan 08-02 and app/api/export.py lands in Plan 08-03.

The contract being asserted:
    - generate_export(wd_id, db_path) returns dict with non-empty file_bytes,
      a .docx filename, and a 64-char hex SHA-256 export_hash
    - Successful export advances WorkDescription.stage to "exported" and
      populates export_hash + exported_at
    - Incomplete JES scoring (level=-1 or points=None) blocks export with a
      ValueError naming the failed factor and mentioning JES/scoring
    - Blocked export does NOT advance stage
    - validate_export_readiness(wd) returns a list of human-readable errors
      for an incomplete WD; [] for a complete WD
    - build_version_manifest(wd) returns a list of dicts deduplicating on
      (source_type, source_id, source_version), one entry per unique source
      referenced from any element of the WD (NOC, JES, TBS_OG_DEF, ADVISOR
      all represented)

test_pdf_route_returns_501 is deferred to Plan 08-03 (router not in this plan).
"""
from __future__ import annotations

import pytest

from tests.conftest import make_exported_wd

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
def _bootstrap_app_modules(export_db, monkeypatch, tmp_path):
    global _app_bootstrapped
    if not _app_bootstrapped:
        _set_env(monkeypatch, str(export_db), tmp_path)
        _clear_app_modules()
        try:
            import app.main  # noqa: F401
            _app_bootstrapped = True
        except Exception:
            pass
    yield


# ---------------------------------------------------------------------------
# Service contract: generate_export
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_export_returns_file_bytes(export_db):
    """generate_export returns a dict with non-empty file_bytes, a .docx
    filename, and a 64-char hex SHA-256 export_hash."""
    try:
        from app.services.export_service import generate_export
    except ImportError:
        pytest.skip("export_service not yet implemented")

    from app.services.wd_store import load_work_description  # noqa: F401
    from app.db import get_connection  # noqa: F401

    wd_id = make_exported_wd(export_db, complete=True)
    result = await generate_export(wd_id=wd_id, db_path=export_db)

    assert isinstance(result, dict)
    assert "file_bytes" in result
    assert isinstance(result["file_bytes"], (bytes, bytearray))
    assert len(result["file_bytes"]) > 0
    assert "filename" in result
    assert result["filename"].endswith(".docx")
    assert "export_hash" in result
    assert isinstance(result["export_hash"], str)
    assert len(result["export_hash"]) == 64  # SHA-256 hex digest length


@pytest.mark.asyncio
async def test_export_advances_stage_to_exported(export_db):
    """Successful generate_export advances stage to 'exported' and sets
    export_hash + exported_at on the WorkDescription."""
    try:
        from app.services.export_service import generate_export
    except ImportError:
        pytest.skip("export_service not yet implemented")

    from app.db import get_connection
    from app.services.wd_store import load_work_description

    wd_id = make_exported_wd(export_db, complete=True)
    await generate_export(wd_id=wd_id, db_path=export_db)

    conn = get_connection(export_db)
    try:
        wd = load_work_description(conn, wd_id)
    finally:
        conn.close()

    assert wd is not None
    assert wd.stage == "exported"
    assert wd.export_hash is not None
    assert wd.exported_at is not None


@pytest.mark.asyncio
async def test_export_blocked_on_incomplete_jes(export_db):
    """generate_export raises ValueError naming the failed factor and
    mentioning JES/scoring when the JES sheet is incomplete (D-01, D-02)."""
    try:
        from app.services.export_service import generate_export
    except ImportError:
        pytest.skip("export_service not yet implemented")

    wd_id = make_exported_wd(export_db, complete=False)

    with pytest.raises(ValueError) as exc:
        await generate_export(wd_id=wd_id, db_path=export_db)

    msg = str(exc.value)
    # Per D-01: error must name the specific factor that failed
    assert "Communication" in msg
    # Per D-01: error must direct advisor back to JES scoring
    assert ("JES" in msg) or ("scoring" in msg)


@pytest.mark.asyncio
async def test_export_blocked_does_not_advance_stage(export_db):
    """When export is blocked, WorkDescription.stage remains 'jes_scored'
    (NOT 'exported')."""
    try:
        from app.services.export_service import generate_export
    except ImportError:
        pytest.skip("export_service not yet implemented")

    from app.db import get_connection
    from app.services.wd_store import load_work_description

    wd_id = make_exported_wd(export_db, complete=False)

    with pytest.raises(ValueError):
        await generate_export(wd_id=wd_id, db_path=export_db)

    conn = get_connection(export_db)
    try:
        wd = load_work_description(conn, wd_id)
    finally:
        conn.close()

    assert wd is not None
    assert wd.stage == "jes_scored"
    assert wd.export_hash is None
    assert wd.exported_at is None


# ---------------------------------------------------------------------------
# Service contract: validate_export_readiness
# ---------------------------------------------------------------------------


def test_validate_export_returns_failed_factor_names(export_db):
    """validate_export_readiness returns a list of error strings naming the
    failed factor for an incomplete WD; [] for a complete WD."""
    try:
        from app.services.export_service import validate_export_readiness
    except ImportError:
        pytest.skip("export_service not yet implemented")

    from app.db import get_connection
    from app.services.wd_store import load_work_description

    # Incomplete: should report at least the failed factor name
    wd_id_incomplete = make_exported_wd(export_db, complete=False)
    conn = get_connection(export_db)
    try:
        wd_inc = load_work_description(conn, wd_id_incomplete)
    finally:
        conn.close()
    assert wd_inc is not None

    errors = validate_export_readiness(wd_inc)
    assert isinstance(errors, list)
    assert len(errors) > 0
    assert any("Communication" in e for e in errors)

    # Complete: should return empty list
    wd_id_complete = make_exported_wd(export_db, complete=True)
    conn = get_connection(export_db)
    try:
        wd_comp = load_work_description(conn, wd_id_complete)
    finally:
        conn.close()
    assert wd_comp is not None

    errors_ok = validate_export_readiness(wd_comp)
    assert errors_ok == []


# ---------------------------------------------------------------------------
# Service contract: build_version_manifest
# ---------------------------------------------------------------------------


def test_version_manifest_includes_all_sources(export_db):
    """build_version_manifest returns a list of dicts (one per unique
    ProvenanceTag) deduplicated on (source_type, source_id, source_version),
    with entries for NOC, JES, TBS_OG_DEF, and ADVISOR sources."""
    try:
        from app.services.export_service import build_version_manifest
    except ImportError:
        pytest.skip("export_service not yet implemented")

    from app.db import get_connection
    from app.services.wd_store import load_work_description

    wd_id = make_exported_wd(export_db, complete=True)
    conn = get_connection(export_db)
    try:
        wd = load_work_description(conn, wd_id)
    finally:
        conn.close()
    assert wd is not None

    manifest = build_version_manifest(wd)
    assert isinstance(manifest, list)
    assert len(manifest) > 0

    required_keys = {"source_type", "source_id", "source_version", "retrieved_date"}
    for entry in manifest:
        assert isinstance(entry, dict)
        assert required_keys.issubset(entry.keys())

    source_types_present = {e["source_type"] for e in manifest}
    assert "NOC" in source_types_present
    assert "JES" in source_types_present
    assert "TBS_OG_DEF" in source_types_present
    assert "ADVISOR" in source_types_present

    # Dedup invariant: no duplicate (source_type, source_id, source_version)
    seen: set = set()
    for entry in manifest:
        key = (entry["source_type"], entry["source_id"], entry["source_version"])
        assert key not in seen, f"duplicate manifest entry: {key}"
        seen.add(key)


# ---------------------------------------------------------------------------
# Router contract (Plan 08-03): /export/{wd_id}/docx and /export/{wd_id}/pdf
# ---------------------------------------------------------------------------
#
# These tests use the per-test rebootstrap pattern (mirroring tests/test_jes_scoring.py):
# _set_env + _clear_app_modules + from app.main import app + TestClient(app).
# Required because the autouse _bootstrap_app_modules fixture only runs once
# (on the first test in the file) and binds settings.db_path to that first
# test's export_db. Each router test needs settings.db_path to point at its
# own export_db (which is fresh per-test), so we re-set DB_PATH and re-import
# app.main inside the test body.


def test_pdf_route_returns_501(export_db, monkeypatch, tmp_path):
    """GET /export/{wd_id}/pdf returns HTTP 501 with the deferred-PDF message (D-08).

    The route short-circuits to 501 immediately (no WeasyPrint render path
    reachable), so the test only needs a seeded wd_id to confirm the route
    is mounted and the message is exact.
    """
    _set_env(monkeypatch, str(export_db), tmp_path)
    _clear_app_modules()
    try:
        from fastapi.testclient import TestClient
        from app.main import app
    except ImportError:
        pytest.skip("app.main or TestClient not importable")

    client = TestClient(app)
    wd_id = make_exported_wd(export_db, complete=True)
    response = client.get(f"/export/{wd_id}/pdf")
    assert response.status_code == 501
    # D-08 message: must mention "PDF export is not yet available"
    assert "PDF export is not yet available" in response.text


def test_docx_route_404_for_unknown_wd(export_db, monkeypatch, tmp_path):
    """GET /export/{wd_id}/docx returns 404 when the WD does not exist.

    generate_export raises ValueError("not found") which the route maps to 404.
    No seeded WD is required — the rebootstrap ensures a valid app instance
    with settings.db_path pointing at a (fresh, empty) export_db.
    """
    _set_env(monkeypatch, str(export_db), tmp_path)
    _clear_app_modules()
    try:
        from fastapi.testclient import TestClient
        from app.main import app
    except ImportError:
        pytest.skip("app.main or TestClient not importable")

    client = TestClient(app)
    response = client.get("/export/nonexistent-id/docx")
    assert response.status_code == 404


def test_docx_route_422_when_blocked(export_db, monkeypatch, tmp_path):
    """GET /export/{wd_id}/docx returns 422 with the failed factor name when
    the JES sheet is incomplete (D-01: Communication sentinel level=-1)."""
    _set_env(monkeypatch, str(export_db), tmp_path)
    _clear_app_modules()
    try:
        from fastapi.testclient import TestClient
        from app.main import app
    except ImportError:
        pytest.skip("app.main or TestClient not importable")

    client = TestClient(app)
    wd_id = make_exported_wd(export_db, complete=False)
    response = client.get(f"/export/{wd_id}/docx")
    assert response.status_code == 422
    # D-01: error must name the failed factor (Communication is the sentinel)
    assert "Communication" in response.text


def test_docx_route_streams_file(export_db, monkeypatch, tmp_path):
    """GET /export/{wd_id}/docx (non-HTMX) returns 200 with DOCX content-type
    and a Content-Disposition: attachment header (T-08-12: filename is a
    server-set constant, not user-derived)."""
    _set_env(monkeypatch, str(export_db), tmp_path)
    _clear_app_modules()
    try:
        from fastapi.testclient import TestClient
        from app.main import app
    except ImportError:
        pytest.skip("app.main or TestClient not importable")

    client = TestClient(app)
    wd_id = make_exported_wd(export_db, complete=True)
    # No HX-Request header → non-HTMX path → binary file download
    response = client.get(f"/export/{wd_id}/docx")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(response.content) > 0
    assert "attachment" in response.headers.get("content-disposition", "")


def test_wizard_export_shows_block_errors_for_incomplete_wd(
    export_db, monkeypatch, tmp_path
):
    """Pre-UAT UX fix: /wizard/export pre-validates and shows a clear
    'Cannot export yet' block listing incomplete JES factors when the WD is
    not export-ready. The Download CTA is hidden so the user does not see a
    silent HTMX spinner followed by raw JSON.
    """
    _set_env(monkeypatch, str(export_db), tmp_path)
    _clear_app_modules()
    try:
        from fastapi.testclient import TestClient
        from app.main import app
    except ImportError:
        pytest.skip("app.main or TestClient not importable")

    client = TestClient(app)
    wd_id = make_exported_wd(export_db, complete=False)  # incomplete JES
    response = client.get(f"/wizard/export?wd_id={wd_id}")
    assert response.status_code == 200
    body = response.text
    assert "Cannot export yet" in body
    assert "Communication" in body  # the failed factor name
    # Download CTA should be hidden when blocked
    assert "id=\"download-btn\"" not in body


def test_wizard_export_hides_block_errors_for_complete_wd(
    export_db, monkeypatch, tmp_path
):
    """When the WD passes validation, /wizard/export shows the Download CTA
    and the manifest preview text, and does NOT show the 'Cannot export yet'
    error block."""
    _set_env(monkeypatch, str(export_db), tmp_path)
    _clear_app_modules()
    try:
        from fastapi.testclient import TestClient
        from app.main import app
    except ImportError:
        pytest.skip("app.main or TestClient not importable")

    client = TestClient(app)
    wd_id = make_exported_wd(export_db, complete=True)
    response = client.get(f"/wizard/export?wd_id={wd_id}")
    assert response.status_code == 200
    body = response.text
    assert "Cannot export yet" not in body
    assert "id=\"download-btn\"" in body
    assert "version manifest" in body.lower()


def test_docx_route_htmx_returns_error_partial_when_blocked(
    export_db, monkeypatch, tmp_path
):
    """Defense in depth: if a user somehow clicks Download DOCX on a blocked
    WD (e.g. by directly calling the route), the HTMX path must render the
    friendly export_error.html partial with 422, NOT raw JSON.
    """
    _set_env(monkeypatch, str(export_db), tmp_path)
    _clear_app_modules()
    try:
        from fastapi.testclient import TestClient
        from app.main import app
    except ImportError:
        pytest.skip("app.main or TestClient not importable")

    client = TestClient(app)
    wd_id = make_exported_wd(export_db, complete=False)
    response = client.get(
        f"/export/{wd_id}/docx", headers={"HX-Request": "true"}
    )
    assert response.status_code == 422
    body = response.text
    assert "Cannot export" in body
    assert "export-error" in body or "export-errors" in body
    assert "Communication" in body


# ---------------------------------------------------------------------------
# Phase 08.1: validator accepts advisor_adjusted factors (D-08.1-03)
# ---------------------------------------------------------------------------


def _make_advisor_adjusted_wd(db_path: str, *, with_override: bool) -> str:
    """Build a WD with one failed factor; optionally mark it advisor_adjusted."""
    from datetime import date

    from app.db import get_connection
    from app.models.work_description import (
        DraftDuty,
        DraftText,
        JESFactorScore,
        NOCMatch,
        OGRecommendation,
        ProvenanceTag,
        WorkDescription,
    )
    from app.services.wd_store import save_work_description

    conn = get_connection(db_path)
    noc_prov = ProvenanceTag(
        source_type="NOC", source_id="41401",
        source_version="NOC 2021 v1.0", retrieved_date=date.today(),
    )
    confirmed_noc = NOCMatch(
        noc_code="41401",
        noc_title="Economists and economic policy researchers and analysts",
        teer_level="1", confidence=0.9, rationale="Strong match",
        matched_duty_statements=["Conduct economic analysis."],
        provenance=noc_prov,
    )
    og_prov = ProvenanceTag(
        source_type="TBS_OG_DEF", source_id="EC",
        source_version="TBS-OCHRO-OG.txt", retrieved_date=date.today(),
    )
    og_recommendation = OGRecommendation(
        og_code="EC", og_name="Economics and Social Science Services",
        level="EC-05", confidence=0.85,
        rationale="Policy work directed to Canadians",
        provenance=og_prov, confirmed_by_advisor=True,
    )
    org_ctx = DraftText(
        text="Operates within the Policy Branch.",
        provenance=og_prov,
    )
    duty_prov = ProvenanceTag(
        source_type="NOC", source_id="41401",
        source_version="NOC 2021 v1.0", retrieved_date=date.today(),
    )
    draft_duties = [
        DraftDuty(
            text="Conduct economic analysis of policy options.",
            provenance=duty_prov,
        ),
    ]
    jes_prov_1 = ProvenanceTag(
        source_type="JES", source_id="EC/Decision making",
        source_version="JES v1.0", retrieved_date=date.today(),
    )
    jes_prov_2 = ProvenanceTag(
        source_type="JES", source_id="EC/Communication",
        source_version="JES v1.0", retrieved_date=date.today(),
    )
    if with_override:
        # Communication is the sentinel BUT marked advisor_adjusted (override applied)
        jes_scores = [
            JESFactorScore(
                factor_name="Decision making", level=3, points=35,
                rationale="High latitude",
                provenance=jes_prov_1,
            ),
            JESFactorScore(
                factor_name="Communication", level=2, points=30,
                rationale="Explains findings",
                provenance=ProvenanceTag(
                    source_type="ADVISOR", source_id="EC/Communication",
                    source_version="advisor manual override",
                    retrieved_date=date.today(),
                    modified_by_advisor=True,
                ),
                advisor_adjusted=True,
                advisor_adjusted_level=2,
                advisor_adjustment_rationale=(
                    "Communications align with the role's writing duties."
                ),
            ),
        ]
        jes_total_points = 65
    else:
        # Communication is the sentinel and NOT advisor_adjusted (blocks)
        jes_scores = [
            JESFactorScore(
                factor_name="Decision making", level=3, points=35,
                rationale="High latitude",
                provenance=jes_prov_1,
            ),
            JESFactorScore(
                factor_name="Communication", level=-1, points=None,
                rationale="Scoring failed after 3 retries",
                provenance=jes_prov_2,
            ),
        ]
        jes_total_points = 35
    wd = WorkDescription(
        session_id="test-session-advisor",
        raw_input="Develops policy options for senior management.",
        position_title="Senior Policy Analyst",
        position_number="12345",
        og_level="EC-05",
        supervisor_title="Manager, Policy",
        supervisor_position_number="00001",
        review_date=date(2026, 6, 2),
        organizational_context=org_ctx,
        confirmed_noc=confirmed_noc,
        og_recommendation=og_recommendation,
        confirmed_og="EC",
        confirmed_level="EC-05",
        draft_duties=draft_duties,
        jes_scores=jes_scores,
        jes_total_points=jes_total_points,
        stage="jes_scored",
    )
    save_work_description(conn, wd)
    conn.close()
    return str(wd.id)


def test_validator_accepts_advisor_adjusted_factor(export_db):
    """D-08.1-03: validate_export_readiness returns [] when a failed factor
    is marked advisor_adjusted=True (the override IS the resolution)."""
    try:
        from app.services.export_service import validate_export_readiness
    except ImportError:
        pytest.skip("export_service not yet implemented")

    from app.db import get_connection
    from app.services.wd_store import load_work_description

    wd_id = _make_advisor_adjusted_wd(export_db, with_override=True)
    conn = get_connection(export_db)
    try:
        wd = load_work_description(conn, wd_id)
    finally:
        conn.close()
    assert wd is not None

    errors = validate_export_readiness(wd)
    assert errors == []


def test_validator_still_rejects_unoverridden_failure(export_db):
    """D-08.1-03: validate_export_readiness still returns errors for an
    unoverridden factor (advisor_adjusted=False) with level=-1 / points=None."""
    try:
        from app.services.export_service import validate_export_readiness
    except ImportError:
        pytest.skip("export_service not yet implemented")

    from app.db import get_connection
    from app.services.wd_store import load_work_description

    wd_id = _make_advisor_adjusted_wd(export_db, with_override=False)
    conn = get_connection(export_db)
    try:
        wd = load_work_description(conn, wd_id)
    finally:
        conn.close()
    assert wd is not None

    errors = validate_export_readiness(wd)
    assert isinstance(errors, list)
    assert len(errors) > 0
    assert any("Communication" in e for e in errors)


def test_validator_message_mentions_override_option(export_db):
    """D-08.1-03: the validator's error message for an unoverridden failure
    mentions the override option so the user knows about the recovery path."""
    try:
        from app.services.export_service import validate_export_readiness
    except ImportError:
        pytest.skip("export_service not yet implemented")

    from app.db import get_connection
    from app.services.wd_store import load_work_description

    wd_id = _make_advisor_adjusted_wd(export_db, with_override=False)
    conn = get_connection(export_db)
    try:
        wd = load_work_description(conn, wd_id)
    finally:
        conn.close()
    assert wd is not None

    errors = validate_export_readiness(wd)
    assert any("override" in e.lower() or "advisor" in e.lower() for e in errors)
