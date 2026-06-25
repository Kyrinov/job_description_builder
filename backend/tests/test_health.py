"""
test_health.py — contract for GET /api/health.

Wave 0 stub: fails because app.main does not exist (collection skip via conftest).
Plan 02 implements /api/health and this test must pass after that plan.
"""
import pytest

pytestmark = pytest.mark.asyncio


async def test_health_returns_200(client):
    """GET /api/health must return 200 with {"status": "ok"}."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
