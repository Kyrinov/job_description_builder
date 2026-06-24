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


# ---------------------------------------------------------------------------
# Phase 26 — ORG-01: RED baseline for org_context round-trip
# ---------------------------------------------------------------------------

async def test_patch_org_context_round_trip(client):
    """ORG-01: PATCH org_context → GET → assert org_context non-None.
    Confirms WDPatchRequest co-update (extra='ignore' would drop unknown field silently)."""
    create_resp = await client.post(
        "/api/wd", json={"record": {}, "answers": {}, "step_index": 0}
    )
    wd_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/wd/{wd_id}", json={"org_context": "Test org context text"}
    )
    assert patch_resp.status_code == 200

    get_resp = await client.get(f"/api/wd/{wd_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["org_context"] == "Test org context text"


async def test_patch_org_context_rejects_over_length(client):
    """F-02: PATCH org_context > 4000 chars returns 422 (ASVS V5 DoS mitigation).

    Guards the Field(default=None, max_length=4000) constraint on
    WDPatchRequest.org_context — a regression removing the constraint would
    not otherwise be caught.
    """
    create_resp = await client.post(
        "/api/wd", json={"record": {}, "answers": {}, "step_index": 0}
    )
    wd_id = create_resp.json()["id"]

    over_length_resp = await client.patch(
        f"/api/wd/{wd_id}", json={"org_context": "x" * 4001}
    )
    assert over_length_resp.status_code == 422


# ---------------------------------------------------------------------------
# Phase 27 — RESP-01: RED baseline for responsibilities_narrative round-trip
# (co-update rule: stays RED until BOTH WorkDescription.responsibilities_narrative
#  AND WDPatchRequest.responsibilities_narrative ship — extra="ignore" would
#  silently drop an unknown PATCH key with HTTP 200, so the GET round-trip
#  returns None and the assertion below fails).
# ---------------------------------------------------------------------------

async def test_patch_responsibilities_narrative_round_trip(client):
    """RESP-01: PATCH responsibilities_narrative → GET → assert value round-trips."""
    create_resp = await client.post(
        "/api/wd", json={"record": {}, "answers": {}, "step_index": 0}
    )
    wd_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/wd/{wd_id}",
        json={"responsibilities_narrative": "Owns the environmental policy portfolio and briefs senior leadership."},
    )
    assert patch_resp.status_code == 200

    get_resp = await client.get(f"/api/wd/{wd_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["responsibilities_narrative"] == (
        "Owns the environmental policy portfolio and briefs senior leadership."
    )


async def test_patch_responsibilities_narrative_rejects_over_length(client):
    """T-27-01 (ASVS V5 DoS): PATCH responsibilities_narrative > 4000 chars returns 422.

    Guards the Field(default=None, max_length=4000) constraint on
    WDPatchRequest.responsibilities_narrative — a regression removing the
    constraint would not otherwise be caught.
    """
    create_resp = await client.post(
        "/api/wd", json={"record": {}, "answers": {}, "step_index": 0}
    )
    wd_id = create_resp.json()["id"]

    over_length_resp = await client.patch(
        f"/api/wd/{wd_id}", json={"responsibilities_narrative": "x" * 4001}
    )
    assert over_length_resp.status_code == 422


# ---------------------------------------------------------------------------
# Phase 27 — ELEM-01: validate-elements endpoint integration tests
# (Plan 27-02 — Seven-Elements Completeness Audit)
#
# POST /api/wd/{id}/validate-elements returns the 7-element status array
# via build_seven_elements(wd). 404 on missing WD. Mirrors validate-duties
# / orphan_check / audit pattern (load WD, run service, return dict).
# ---------------------------------------------------------------------------


async def test_validate_elements_returns_seven(client):
    """ELEM-01: POST /api/wd/{id}/validate-elements on a fully-populated WD
    returns 200 with elements length == 7, complete_count == 7, total == 7."""
    create_resp = await client.post(
        "/api/wd", json={"record": {}, "answers": {}, "step_index": 0}
    )
    wd_id = create_resp.json()["id"]

    # Seed the WD with every Part 2 element populated/derivable.
    patch_resp = await client.patch(
        f"/api/wd/{wd_id}",
        json={
            "confirmed_og": {"og_code": "EC", "og_name": "Economics and Social Science Services"},
            "og_level": 4,
            "jes_total_points": 621,
            "duties": [
                {
                    "id": "d1",
                    "text": "Provides advice on economic policy.",
                    "source": "noc",
                    "provenance_noc_code": "4163",
                    "advisor": False,
                }
            ],
            "org_context": "Within Branch X, reporting to the Director, the Analyst provides advice.",
            "responsibilities_narrative": "Owns the policy portfolio and briefs senior leadership.",
            "qualification": {
                "education": "Degree in economics.",
                "experience": "5 years policy analysis.",
                "source": "EC-05 default",
                "last_modified": "2026-06-16T00:00:00Z",
            },
            "record": {
                "client_service_results": "Citizens receive timely, accurate policy guidance.",
            },
        },
    )
    assert patch_resp.status_code == 200

    resp = await client.post(f"/api/wd/{wd_id}/validate-elements")
    assert resp.status_code == 200
    body = resp.json()
    assert body["wd_id"] == wd_id
    assert len(body["elements"]) == 7
    assert body["total"] == 7
    assert body["complete_count"] == 7
    # Spot-check the element shape contract
    expected_keys = {"key", "label", "status"}
    for el in body["elements"]:
        assert expected_keys.issubset(el.keys()), f"Element missing required keys: {el}"


async def test_validate_elements_missing_wd_404(client):
    """ELEM-01: POST /api/wd/{id}/validate-elements on a non-existent id returns 404.

    Mirrors validate-duties / orphan_check / audit 404-guard pattern."""
    resp = await client.post("/api/wd/does-not-exist/validate-elements")
    assert resp.status_code == 404


async def test_validate_elements_partial(client):
    """ELEM-01: POST /api/wd/{id}/validate-elements on a WD with only duties +
    jes_total_points returns 200 with complete_count reflecting only the
    populated|derived elements (effort + working_conditions derived,
    key_activities populated, others missing)."""
    create_resp = await client.post(
        "/api/wd", json={"record": {}, "answers": {}, "step_index": 0}
    )
    wd_id = create_resp.json()["id"]

    # Seed only duties + jes_total_points; everything else stays missing.
    patch_resp = await client.patch(
        f"/api/wd/{wd_id}",
        json={
            "confirmed_og": {"og_code": "EC", "og_name": "Economics and Social Science Services"},
            "og_level": 4,
            "jes_total_points": 621,
            "duties": [
                {
                    "id": "d1",
                    "text": "Provides advice on economic policy.",
                    "source": "noc",
                    "provenance_noc_code": "4163",
                    "advisor": False,
                }
            ],
        },
    )
    assert patch_resp.status_code == 200

    resp = await client.post(f"/api/wd/{wd_id}/validate-elements")
    assert resp.status_code == 200
    body = resp.json()
    assert body["wd_id"] == wd_id
    assert len(body["elements"]) == 7
    assert body["total"] == 7
    # 3 complete: effort (derived), working_conditions (derived), key_activities (populated)
    assert body["complete_count"] == 3
    elements = {e["key"]: e for e in body["elements"]}
    assert elements["key_activities"]["status"] == "populated"
    assert elements["effort"]["status"] == "derived"
    assert elements["working_conditions"]["status"] == "derived"
    # Everything else must be missing (not derived, not populated, never not_applicable)
    for key in ("organizational_context", "client_service_results", "skills", "responsibility"):
        assert elements[key]["status"] == "missing", (
            f"{key} should be missing when not seeded; got {elements[key]['status']!r}"
        )
