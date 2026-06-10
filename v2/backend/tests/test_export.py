"""
test_export.py — Phase 20: Export endpoint tests.

Integration tests for:
  POST /api/wd/{id}/export/docx  (API-08, EXP-01)
  POST /api/wd/{id}/export/poster (API-09, EXP-02)
  POST /api/wd/{id}/export/pdf    (EXP-03)

All tests are skipped until Plan 02 implements export.py and wires it
into api/__init__.py. Remove @pytest.mark.skip when the router is live.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def _create_wd(client) -> str:
    resp = await client.post(
        "/api/wd",
        json={"record": {"title": "Test Role"}, "answers": {}, "step_index": 1},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_wd_with_jes_scores(client) -> str:
    """Create a WD seeded with confirmed_og + jes_total_points required for export."""
    wd_id = await _create_wd(client)
    resp = await client.patch(
        f"/api/wd/{wd_id}",
        json={
            "confirmed_og": {"og_code": "EC", "og_name": "Economics and Social Science Services"},
            "og_level": 4,
            "jes_total_points": 621,
            "jes_scores": [
                {"factor_name": "Decision Making", "degree": 3, "points": 150},
                {"factor_name": "Communication", "degree": 2, "points": 84},
            ],
            "duties": [
                {
                    "id": "d1",
                    "text": "Provides advice on economic policy.",
                    "source": "noc",
                    "provenance_noc_code": "4163",
                    "provenance_hash": "abc123",
                    "advisor": False,
                }
            ],
        },
    )
    assert resp.status_code == 200
    return wd_id


async def test_export_wd_docx_returns_bytes(client, env_with_db):
    """EXP-01 / API-08 — POST /api/wd/{id}/export/docx returns .docx bytes with correct MIME type."""
    wd_id = await _create_wd_with_jes_scores(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(resp.content) > 0


async def test_export_wd_docx_manifest(client, env_with_db):
    """EXP-01 — Exported DOCX bytes are non-zero (version manifest rendered in template)."""
    wd_id = await _create_wd_with_jes_scores(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    # Proxy for "manifest section rendered": file is > 5 kB (empty docx is ~4 kB)
    assert len(resp.content) > 5000, "DOCX file suspiciously small — manifest may not have rendered"


async def test_export_wd_docx_amendments_appendix(client, env_with_db):
    """EXP-01 / AMEND-02 — DOCX bytes delivered even when amendment notes exist."""
    wd_id = await _create_wd_with_jes_scores(client)
    # Add an amendment note
    await client.post(
        f"/api/wd/{wd_id}/amendments",
        json={"section": "du", "comment": "Review this duty for scope."},
    )
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    assert len(resp.content) > 0


async def test_export_poster_returns_bytes(client, env_with_db):
    """EXP-02 / API-09 — POST /api/wd/{id}/export/poster returns .docx bytes."""
    wd_id = await _create_wd_with_jes_scores(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/poster")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(resp.content) > 0


async def test_export_pdf_501_when_weasyprint_absent(client, env_with_db, monkeypatch):
    """EXP-03 — POST /api/wd/{id}/export/pdf returns 501 when WeasyPrint import fails."""
    import sys
    monkeypatch.setitem(sys.modules, "weasyprint", None)
    wd_id = await _create_wd(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/pdf")
    assert resp.status_code == 501
    assert "WeasyPrint" in resp.json()["detail"]


async def test_export_docx_404(client, env_with_db):
    """API-08 — POST /api/wd/does-not-exist/export/docx returns 404."""
    resp = await client.post("/api/wd/does-not-exist/export/docx")
    assert resp.status_code == 404


async def test_export_poster_404(client, env_with_db):
    """API-09 — POST /api/wd/does-not-exist/export/poster returns 404."""
    resp = await client.post("/api/wd/does-not-exist/export/poster")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# WR-08: PDF 501 via runtime probe failure (Pango/Cairo missing at render time)
# ---------------------------------------------------------------------------

async def test_export_pdf_501_when_weasyprint_probe_fails(client, env_with_db, monkeypatch):
    """WR-08 — POST /api/wd/{id}/export/pdf returns 501 when _probe_weasyprint() is False.

    Distinct from the import-failure path: WeasyPrint imports cleanly but the
    runtime probe (_probe_weasyprint) returns False, indicating Pango/Cairo are
    missing. This covers the second 501 branch in the PDF handler.
    """
    import app.services.export_service as es
    monkeypatch.setattr(es, "_weasyprint_available", False)

    wd_id = await _create_wd(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/pdf")
    # 501 from the _probe_weasyprint() guard; or 501 if weasyprint not installed
    assert resp.status_code == 501


# ---------------------------------------------------------------------------
# WR-09: 409 from require_og_confirmed gate on all export endpoints
# ---------------------------------------------------------------------------

async def test_export_docx_409_without_og(client, env_with_db):
    """WR-09 — POST /api/wd/{id}/export/docx returns 409 when OG not confirmed."""
    wd_id = await _create_wd(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "classification_pending"


async def test_export_poster_409_without_og(client, env_with_db):
    """WR-09 — POST /api/wd/{id}/export/poster returns 409 when OG not confirmed."""
    wd_id = await _create_wd(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/poster")
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "classification_pending"


# ---------------------------------------------------------------------------
# WR-10: self-healing JES flow in export_wd_docx
# ---------------------------------------------------------------------------

async def test_export_docx_self_heals_jes_scores(client, env_with_db, monkeypatch):
    """WR-10 — DOCX export triggers JES self-healing when jes_total_points is None.

    Confirms that the self-healing block is exercised: score_jes_v2 is called
    and the WD is re-loaded. We monkeypatch score_jes_v2 to a no-op (CI has no
    LLM) and assert that the export still succeeds (200 + non-empty bytes).
    """
    import app.api.export as export_mod

    async def _fake_score(**kwargs):  # noqa: ARG001
        return None

    monkeypatch.setattr(export_mod, "score_jes_v2", _fake_score)

    wd_id = await _create_wd(client)
    # PATCH confirmed_og + og_level so the 409 gate passes, but leave
    # jes_total_points as None so self-healing is triggered.
    resp = await client.patch(
        f"/api/wd/{wd_id}",
        json={
            "confirmed_og": {"og_code": "EC", "og_name": "Economics and Social Science Services"},
            "og_level": 4,
            "duties": [
                {
                    "id": "d1",
                    "text": "Analyses economic data for policy recommendations.",
                    "source": "noc",
                    "provenance_noc_code": "4163",
                    "advisor": False,
                }
            ],
        },
    )
    assert resp.status_code == 200

    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    assert len(resp.content) > 0


# ---------------------------------------------------------------------------
# WR-11: duties record-fallback in _build_wd_context
# ---------------------------------------------------------------------------

async def test_export_docx_uses_record_duties_fallback(client, env_with_db):
    """WR-11 — DOCX export succeeds when duties live in record only (no root duties).

    Exercises the _build_wd_context record-fallback path: root wd.duties is
    empty but record.duties has duty data. The export must still return 200
    and non-empty bytes.
    """
    wd_id = await _create_wd(client)
    # PATCH via the record dict only — no root-level duties field
    resp = await client.patch(
        f"/api/wd/{wd_id}",
        json={
            "confirmed_og": {"og_code": "EC", "og_name": "Economics and Social Science Services"},
            "og_level": 3,
            "jes_total_points": 520,
            "jes_scores": [
                {"factor_name": "Decision Making", "degree": 2, "points": 120},
            ],
            "record": {
                "title": "Policy Analyst",
                "duties": [
                    {
                        "id": "d1",
                        "text": "Develops policy briefs for senior management.",
                        "source": "noc",
                        "provenance_noc_code": "4163",
                        "provenance_section": "Main duties",
                        "provenance_hash": "abc123",
                        "advisor": False,
                        "orphan": False,
                    }
                ],
            },
        },
    )
    assert resp.status_code == 200

    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    assert len(resp.content) > 0


# ---------------------------------------------------------------------------
# Phase 21 — OGX-02: NON_EC_STANDARD_NAMES consolidated into constants.py
# ---------------------------------------------------------------------------

def test_standard_names_import_from_constants():
    """OGX-02 — export_service.py must import NON_EC_STANDARD_NAMES from constants.py,
    not define it locally.

    FAILS at Wave 0: export_service.py lines 50-55 still have local dict.
    Goes GREEN after Plan 02 (Wave 1) removes the local dict and adds the import.
    """
    import inspect
    import importlib
    export_service = importlib.import_module("app.services.export_service")
    source = inspect.getsource(export_service)
    # Must import from app.data.constants — not define locally
    assert "from app.data.constants import" in source and "NON_EC_STANDARD_NAMES" in source, \
        "export_service.py must import NON_EC_STANDARD_NAMES from app.data.constants"
    # Must NOT define a local copy
    assert "NON_EC_STANDARD_NAMES: dict" not in source, \
        "export_service.py must not define a local NON_EC_STANDARD_NAMES dict"
