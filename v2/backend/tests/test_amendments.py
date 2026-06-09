"""
test_amendments.py — Phase 19: Amendment note endpoint tests.

Integration tests for POST /api/wd/{id}/amendments and GET /api/wd/{id}/amendments.
Covers AMEND-01 (audit_log write, 201 response, field correctness, 404 guard)
and deduplication (GET returns latest note per section).

The amendments.py module does not exist yet; tests are marked skip until Wave 2.
Remove @pytest.mark.skip when amendments.py is wired in api/__init__.py.
"""
import json
import pytest

pytestmark = pytest.mark.asyncio


async def _create_wd(client) -> str:
    resp = await client.post(
        "/api/wd",
        json={"record": {"title": "Test Role"}, "answers": {}, "step_index": 1},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.skip(reason="amendments.py not yet implemented — unblock in Wave 2")
async def test_save_amendment_creates_audit_row(client, env_with_db):
    """AMEND-01 — POST /api/wd/{id}/amendments returns 201; writes audit_log row."""
    from app.config import get_settings
    from app.db import get_connection

    wd_id = await _create_wd(client)
    resp = await client.post(
        f"/api/wd/{wd_id}/amendments",
        json={"section": "du", "comment": "This duty seems outside scope."},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["saved"] is True
    assert body["section"] == "du"

    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        rows = con.execute(
            "SELECT event, actor, detail FROM audit_log "
            "WHERE wd_id = ? AND event = 'manager_amendment'",
            (wd_id,),
        ).fetchall()
    finally:
        con.close()

    assert len(rows) == 1
    assert rows[0]["event"] == "manager_amendment"
    assert rows[0]["actor"] == "advisor"
    detail = json.loads(rows[0]["detail"])
    assert detail["section"] == "du"
    assert detail["comment"] == "This duty seems outside scope."


@pytest.mark.skip(reason="amendments.py not yet implemented — unblock in Wave 2")
async def test_get_amendments_latest_per_section(client, env_with_db):
    """AMEND-01 — GET /api/wd/{id}/amendments returns only the latest note per section."""
    wd_id = await _create_wd(client)
    # Save note twice for same section; GET must return only the second (latest)
    await client.post(
        f"/api/wd/{wd_id}/amendments",
        json={"section": "ov", "comment": "First version"},
    )
    await client.post(
        f"/api/wd/{wd_id}/amendments",
        json={"section": "ov", "comment": "Updated version"},
    )

    resp = await client.get(f"/api/wd/{wd_id}/amendments")
    assert resp.status_code == 200
    data = resp.json()
    assert data["notes"]["ov"] == "Updated version"


@pytest.mark.skip(reason="amendments.py not yet implemented — unblock in Wave 2")
async def test_save_amendment_404(client, env_with_db):
    """AMEND-01 — POST returns 404 for non-existent WD."""
    resp = await client.post(
        "/api/wd/does-not-exist/amendments",
        json={"section": "du", "comment": "Note"},
    )
    assert resp.status_code == 404


@pytest.mark.skip(reason="amendments.py not yet implemented — unblock in Wave 2")
async def test_amendment_audit_log_fields(client, env_with_db):
    """AMEND-02 — audit_log row has event='manager_amendment', section, comment in detail JSON."""
    from app.config import get_settings
    from app.db import get_connection

    wd_id = await _create_wd(client)
    await client.post(
        f"/api/wd/{wd_id}/amendments",
        json={"section": "cls", "comment": "Review the OG level."},
    )

    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT event, actor, detail, created_at FROM audit_log "
            "WHERE wd_id = ? AND event = 'manager_amendment'",
            (wd_id,),
        ).fetchone()
    finally:
        con.close()

    assert row is not None
    assert row["event"] == "manager_amendment"
    assert row["actor"] == "advisor"
    assert row["created_at"]  # non-empty timestamp
    detail = json.loads(row["detail"])
    assert detail["section"] == "cls"
    assert detail["comment"] == "Review the OG level."


@pytest.mark.skip(reason="amendments.py not yet implemented — unblock in Wave 2")
async def test_save_amendment_invalid_section(client, env_with_db):
    """AMEND-01 security — section key outside allowed Literal set returns 422."""
    wd_id = await _create_wd(client)
    resp = await client.post(
        f"/api/wd/{wd_id}/amendments",
        json={"section": "INJECTED", "comment": "Attempt to inject an unknown key."},
    )
    assert resp.status_code == 422


@pytest.mark.skip(reason="amendments.py not yet implemented — unblock in Wave 2")
async def test_save_amendment_oversized_comment(client, env_with_db):
    """AMEND-01 security — comment exceeding 2000 chars returns 422."""
    wd_id = await _create_wd(client)
    resp = await client.post(
        f"/api/wd/{wd_id}/amendments",
        json={"section": "du", "comment": "x" * 2001},
    )
    assert resp.status_code == 422
