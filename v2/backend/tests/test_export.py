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
                    "provenance_noc_code": "4163",
                    "provenance_hash": "abc123",
                    "advisor": False,
                }
            ],
        },
    )
    assert resp.status_code == 200
    return wd_id


@pytest.mark.skip(reason="export.py not yet implemented — unblock in Plan 02")
async def test_export_wd_docx_returns_bytes(client, env_with_db):
    """EXP-01 / API-08 — POST /api/wd/{id}/export/docx returns .docx bytes with correct MIME type."""
    wd_id = await _create_wd_with_jes_scores(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(resp.content) > 0


@pytest.mark.skip(reason="export.py not yet implemented — unblock in Plan 02")
async def test_export_wd_docx_manifest(client, env_with_db):
    """EXP-01 — Exported DOCX bytes are non-zero (version manifest rendered in template)."""
    wd_id = await _create_wd_with_jes_scores(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    # Proxy for "manifest section rendered": file is > 5 kB (empty docx is ~4 kB)
    assert len(resp.content) > 5000, "DOCX file suspiciously small — manifest may not have rendered"


@pytest.mark.skip(reason="export.py not yet implemented — unblock in Plan 02")
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


@pytest.mark.skip(reason="export.py not yet implemented — unblock in Plan 02")
async def test_export_poster_returns_bytes(client, env_with_db):
    """EXP-02 / API-09 — POST /api/wd/{id}/export/poster returns .docx bytes."""
    wd_id = await _create_wd_with_jes_scores(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/poster")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(resp.content) > 0


@pytest.mark.skip(reason="export.py not yet implemented — unblock in Plan 02")
async def test_export_pdf_501_when_weasyprint_absent(client, env_with_db, monkeypatch):
    """EXP-03 — POST /api/wd/{id}/export/pdf returns 501 when WeasyPrint import fails."""
    import sys
    monkeypatch.setitem(sys.modules, "weasyprint", None)
    wd_id = await _create_wd(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/pdf")
    assert resp.status_code == 501
    assert "WeasyPrint" in resp.json()["detail"]


@pytest.mark.skip(reason="export.py not yet implemented — unblock in Plan 02")
async def test_export_docx_404(client, env_with_db):
    """API-08 — POST /api/wd/does-not-exist/export/docx returns 404."""
    resp = await client.post("/api/wd/does-not-exist/export/docx")
    assert resp.status_code == 404


@pytest.mark.skip(reason="export.py not yet implemented — unblock in Plan 02")
async def test_export_poster_404(client, env_with_db):
    """API-09 — POST /api/wd/does-not-exist/export/poster returns 404."""
    resp = await client.post("/api/wd/does-not-exist/export/poster")
    assert resp.status_code == 404
