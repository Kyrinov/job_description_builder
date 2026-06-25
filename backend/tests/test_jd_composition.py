"""
test_jd_composition.py — Phase 18: JD composition backend contract.
Covers JD-01..04: duty fetch, provenance model, orphan check.
"""
import pytest

pytestmark = pytest.mark.asyncio


async def test_get_noc_duties_returns_main_duties(client, noc_duties_db):
    """JD-01: GET /api/noc/21232/duties returns list with text + source_hash."""
    response = await client.get("/api/noc/21232/duties")
    assert response.status_code == 200
    data = response.json()
    assert data["noc_code"] == "21232"
    assert len(data["duties"]) >= 1
    duty = data["duties"][0]
    assert "text" in duty
    assert duty["text"] == "Develop and maintain application software."
    assert "source_hash" in duty


async def test_get_noc_duties_404_for_unknown_noc(client, noc_duties_db):
    """JD-01: GET /api/noc/99999/duties → 404 when no Main duties exist."""
    response = await client.get("/api/noc/99999/duties")
    assert response.status_code == 404


async def test_draft_duty_provenance_fields(client):
    """JD-02: DraftDuty model accepts provenance_noc_code, provenance_section, provenance_hash."""
    from app.models.draft_duty import DraftDuty
    duty = DraftDuty(
        id="noc-1",
        text="Develop and maintain application software.",
        source="noc",
        provenance_noc_code="21232",
        provenance_section="Main duties",
        provenance_hash="fakehash_v1",
    )
    assert duty.provenance_noc_code == "21232"
    assert duty.provenance_section == "Main duties"
    assert duty.provenance_hash == "fakehash_v1"
    assert duty.advisor is False


async def test_advisor_duty_source_type(client):
    """JD-03: advisor duty has advisor=True and source='advisor'."""
    from app.models.draft_duty import DraftDuty
    duty = DraftDuty(
        id="adv-1",
        text="Manages stakeholder relationships.",
        source="advisor",
        advisor=True,
    )
    assert duty.advisor is True
    assert duty.source == "advisor"
    assert duty.provenance_noc_code is None


async def test_orphan_check_ec_no_flags(client, noc_duties_db):
    """JD-04: POST /api/wd/{id}/orphan_check with EC OG returns flagged: []."""
    # Create a WD with EC confirmed_og and a duty
    create_resp = await client.post("/api/wd", json={
        "title": "Policy Analyst",
        "branch": "Science Branch",
        "summary": "Develops policy.",
        "reports": "Director",
    })
    assert create_resp.status_code == 201
    wd_id = create_resp.json()["id"]

    # Patch: confirm OG as EC and add a duty
    patch_resp = await client.patch(f"/api/wd/{wd_id}", json={
        "confirmed_og": {"og_code": "EC", "og_name": "Economics and Social Science Services"},
        "duties": [{
            "id": "noc-1",
            "text": "Develops policy frameworks.",
            "source": "noc",
            "provenance_noc_code": "41401",
            "provenance_section": "Main duties",
            "provenance_hash": "fakehash_v1",
        }],
    })
    assert patch_resp.status_code == 200

    # Orphan check: EC has no exclusions → flagged must be empty
    check_resp = await client.post(f"/api/wd/{wd_id}/orphan_check")
    assert check_resp.status_code == 200
    data = check_resp.json()
    assert data["wd_id"] == wd_id
    assert data["flagged"] == []


async def test_patch_wd_duties_persists(client):
    """JD-01/02: PATCH /api/wd/{id} with duties[] stores DraftDuty objects."""
    create_resp = await client.post("/api/wd", json={
        "title": "Developer",
        "branch": "IT Branch",
        "summary": "Develops software.",
        "reports": "Manager",
    })
    assert create_resp.status_code == 201
    wd_id = create_resp.json()["id"]

    duties_payload = [{
        "id": "noc-42",
        "text": "Design and develop software systems.",
        "source": "noc",
        "provenance_noc_code": "21232",
        "provenance_section": "Main duties",
        "provenance_hash": "fakehash_v1",
        "advisor": False,
    }]
    patch_resp = await client.patch(f"/api/wd/{wd_id}", json={"duties": duties_payload})
    assert patch_resp.status_code == 200

    get_resp = await client.get(f"/api/wd/{wd_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert len(data["duties"]) == 1
    assert data["duties"][0]["id"] == "noc-42"
    assert data["duties"][0]["provenance_noc_code"] == "21232"
