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
# Deferrals
# ---------------------------------------------------------------------------
#
# test_pdf_route_returns_501 — covered in tests/test_export_router.py (Plan 08-03).
# The router for /export/{wd_id}/pdf is mounted in Plan 08-03; this plan
# (08-01) only establishes the service contract and template artifact.
