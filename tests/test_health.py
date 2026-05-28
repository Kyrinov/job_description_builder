"""Smoke test for GET /health endpoint (DATA-03)."""
import pytest


@pytest.mark.asyncio
async def test_health_endpoint_200(test_app):
    """GET /health must return 200 when app starts cleanly."""
    response = await test_app.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_has_status_key(test_app):
    """GET /health response body must contain a 'status' key."""
    response = await test_app.get("/health")
    body = response.json()
    assert "status" in body


@pytest.mark.asyncio
async def test_health_response_has_model_keys(test_app):
    """GET /health must include required_models and missing_models keys."""
    response = await test_app.get("/health")
    body = response.json()
    assert "required_models" in body
    assert "missing_models" in body
