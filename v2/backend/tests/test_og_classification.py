"""
test_og_classification.py — Phase 16 OG classification API tests.

Wave 0 stubs: RED until og_classification.py route is registered in api/__init__.py.
Tests use the shared `client` fixture from conftest.py (AsyncClient against test_app).

Requirements covered: CLASS-01, CLASS-02, CLASS-04, API-06, API-03.
"""
import pytest

pytestmark = pytest.mark.asyncio


async def test_og_classify_returns_candidates(client):
    """CLASS-01 / API-06: POST /api/og/classify returns top-3 OG candidates ranked by signal tally."""
    response = await client.post(
        "/api/og/classify",
        json={
            "confirmed_noc_code": "41402",
            "work_description": "Develops environmental policy and advises senior management on regulatory matters",
            "signal_tally": {"EC": 3, "AS": 1},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "candidates" in data
    assert len(data["candidates"]) >= 1
    assert data["candidates"][0]["og_code"] == "EC"


async def test_og_classify_asec_alert_when_both_present(client):
    """CLASS-02: POST /api/og/classify includes asec_alert when AS + EC both in top-3."""
    response = await client.post(
        "/api/og/classify",
        json={
            "confirmed_noc_code": "11109",
            "work_description": "Coordinates policy and administrative support functions",
            "signal_tally": {"EC": 2, "AS": 2},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("asec_alert") is not None
    assert "disambiguation_text" in data["asec_alert"]


async def test_og_classify_no_asec_alert_when_only_ec(client):
    """CLASS-02: POST /api/og/classify omits asec_alert when AS not in top-3."""
    response = await client.post(
        "/api/og/classify",
        json={
            "confirmed_noc_code": "41401",
            "work_description": "Pure economic policy research and statistical analysis",
            "signal_tally": {"EC": 4},
        },
    )
    assert response.status_code == 200
    assert response.json().get("asec_alert") is None


async def test_og_definitions_returns_ec_definition(client):
    """API-03: GET /api/og/definitions?og_code=EC returns definition with og_code field."""
    response = await client.get("/api/og/definitions?og_code=EC")
    assert response.status_code == 200
    data = response.json()
    assert data["og_code"] == "EC"
    assert len(data["definition"]) > 20


async def test_og_definitions_404_for_unknown_code(client):
    """API-03 / T-16-02: GET /api/og/definitions returns 404 for unknown OG code."""
    response = await client.get("/api/og/definitions?og_code=ZZ")
    assert response.status_code == 404


async def test_quals_default_returns_ec_text(client):
    """API-03: GET /api/quals/default?og_code=EC returns education + experience text."""
    response = await client.get("/api/quals/default?og_code=EC")
    assert response.status_code == 200
    data = response.json()
    assert "education" in data
    assert "experience" in data
    assert len(data["education"]) > 10


async def test_patch_wd_confirmed_og_persists(client):
    """CLASS-04: PATCH /api/wd/{id} with confirmed_og + og_level persists both fields."""
    create_resp = await client.post(
        "/api/wd",
        json={"record": {"title": "Policy Analyst"}, "answers": {}, "step_index": 0},
    )
    assert create_resp.status_code == 201
    wd_id = create_resp.json()["id"]
    patch_resp = await client.patch(
        f"/api/wd/{wd_id}",
        json={
            "confirmed_og": {"og_code": "EC", "og_name": "Economics and Social Science Services"},
            "og_level": 5,
        },
    )
    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert body["confirmed_og"]["og_code"] == "EC"
    assert body["og_level"] == 5
