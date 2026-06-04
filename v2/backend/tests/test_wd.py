"""
test_wd.py — contract for POST /api/wd, GET /api/wd/{id}, PATCH /api/wd/{id}.

Wave 0 stub: fails because app/api/wd.py does not exist yet.
Plan 02 implements the routes and these tests must pass.
"""
import pytest

pytestmark = pytest.mark.asyncio


async def test_create_wd_returns_201_with_id(client):
    """POST /api/wd must return 201 with an id field."""
    response = await client.post(
        "/api/wd",
        json={"record": {"title": "Test Role"}, "answers": {}, "step_index": 1},
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert isinstance(data["id"], str)
    assert len(data["id"]) > 0


async def test_get_wd_returns_work_description(client):
    """GET /api/wd/{id} must return the WorkDescription that was POSTed."""
    create_resp = await client.post(
        "/api/wd",
        json={"record": {"title": "Test Role"}, "answers": {}, "step_index": 1},
    )
    assert create_resp.status_code == 201
    wd_id = create_resp.json()["id"]

    response = await client.get(f"/api/wd/{wd_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == wd_id


async def test_patch_wd_updates_step_index(client):
    """PATCH /api/wd/{id} must persist updated fields."""
    create_resp = await client.post(
        "/api/wd",
        json={"record": {}, "answers": {}, "step_index": 0},
    )
    wd_id = create_resp.json()["id"]

    patch_resp = await client.patch(f"/api/wd/{wd_id}", json={"step_index": 3})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["step_index"] == 3


async def test_get_wd_404_for_unknown_id(client):
    """GET /api/wd/{id} must return 404 for a non-existent id."""
    response = await client.get("/api/wd/does-not-exist")
    assert response.status_code == 404
