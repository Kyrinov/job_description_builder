"""
tests/test_jes_level_suggest.py — Phase 21 Plan 08 (JES-LEV-01): JES level-suggestion tests.

Wave 0 stubs: most tests will fail RED until Plan 08 Task 2 implements the
POST /api/jes/level-suggest, GET /api/jes/level-criteria, and
GET /api/jes/level-criteria-groups endpoints in jes_scoring.py.

Behavioural contract:
- POST /api/jes/level-suggest with og_code='NU', sub_group='HOS',
  answers={'nu_scope':'unit_mgmt_24hr','nu_autonomy':'policy_clinical'}
  → suggested_level=4, confidence='high'
- POST /api/jes/level-suggest with og_code='NU', sub_group='HOS',
  answers={'nu_scope':'unit_mgmt_24hr'} (partial) → suggested_level in {4,5},
  confidence in {'low','medium'}
- POST /api/jes/level-suggest with og_code='PS', sub_group=None,
  answers all 3 questions highest option → suggested_level=4, confidence='high'
- POST /api/jes/level-suggest with og_code='EC', sub_group=None, answers={} → 404
- POST /api/jes/level-suggest with og_code='INVALID' → 422
- GET /api/jes/level-criteria?og_code=NU&sub_group=HOS → returns NU-HOS entry
- GET /api/jes/level-criteria?og_code=EC → 404
- GET /api/jes/level-criteria-groups → returns list containing 'NU','PS','NT','PO','SW','ED'

Requirements coverage: JES-LEV-01.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXPECTED_OG_CODES_WITH_CRITERIA = {
    "NU-HOS", "NU-CHN", "NU-EMA", "PS",
    "NT-ADV", "NT-DIT", "NT-HME",
    "PO-TCO", "SW-CHA", "ED-LAT", "ED-EST",
}


# ---------------------------------------------------------------------------
# POST /api/jes/level-suggest
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_level_suggest_nu_hos_full_answers(client, env_with_db):
    """JES-LEV-01 — POST /api/jes/level-suggest NU-HOS full answers → level 4 high confidence.

    Fixture: nu_scope=unit_mgmt_24hr hints [4,5]; nu_autonomy=policy_clinical hints [3,4].
    Majority: level 4 appears in both hint lists (count=2) → suggested_level=4.
    All 2 questions answered, max_count == answered == total_q → confidence='high'.
    """
    response = await client.post(
        "/api/jes/level-suggest",
        json={
            "og_code": "NU",
            "sub_group": "HOS",
            "answers": {
                "nu_scope": "unit_mgmt_24hr",
                "nu_autonomy": "policy_clinical",
            },
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["suggested_level"] == 4
    assert data["confidence"] == "high"
    # level_range is the sorted union of all hinted levels
    assert 3 in data["level_range"]
    assert 4 in data["level_range"]
    assert 5 in data["level_range"]
    assert isinstance(data["rationale"], str) and len(data["rationale"]) > 0


@pytest.mark.asyncio
async def test_level_suggest_nu_hos_partial_answers(client, env_with_db):
    """JES-LEV-01 — POST /api/jes/level-suggest NU-HOS partial (1 of 2) → low/medium confidence.

    Fixture: only nu_scope=unit_mgmt_24hr (hints [4,5]).
    majority_hint resolution: counts={4:1, 5:1}; max_count=1, candidates=[4,5],
    suggested_level=4 (conservative lowest in tie). Confidence is NOT high
    (max_count=1 < answered=1, so the high branch fails).
    """
    response = await client.post(
        "/api/jes/level-suggest",
        json={
            "og_code": "NU",
            "sub_group": "HOS",
            "answers": {"nu_scope": "unit_mgmt_24hr"},
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["suggested_level"] in (4, 5)
    assert data["confidence"] in ("low", "medium")
    # level_range from this single answer is [4, 5]
    assert data["level_range"] == [4, 5]


@pytest.mark.asyncio
async def test_level_suggest_ps_all_highest_answers(client, env_with_db):
    """JES-LEV-01 — POST /api/jes/level-suggest PS with all highest options → level 4 high.

    PS sub-group is keyed by og_code (not sub_group code), so sub_group=None.
    Fixture: ps_independence=fully_independent + ps_methods=originates_new +
    ps_management=directs_program — all hint [4,5].
    Majority: 4 appears 3 times, 5 appears 3 times; tie → conservative lower=4.
    All 3 questions answered, max_count=3 == answered=3 == total_q=3 → high.
    """
    response = await client.post(
        "/api/jes/level-suggest",
        json={
            "og_code": "PS",
            "sub_group": None,
            "answers": {
                "ps_independence": "fully_independent",
                "ps_methods": "originates_new",
                "ps_management": "directs_program",
            },
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["suggested_level"] == 4
    assert data["confidence"] == "high"
    assert 4 in data["level_range"] and 5 in data["level_range"]


@pytest.mark.asyncio
async def test_level_suggest_ec_returns_404(client, env_with_db):
    """JES-LEV-01 — POST /api/jes/level-suggest for EC returns 404 (EC is point-rated, not level-described)."""
    response = await client.post(
        "/api/jes/level-suggest",
        json={"og_code": "EC", "sub_group": None, "answers": {}},
    )
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "EC" in detail or "level criteria" in detail.lower()


@pytest.mark.asyncio
async def test_level_suggest_invalid_og_returns_422(client, env_with_db):
    """JES-LEV-01 — POST /api/jes/level-suggest with unknown og_code returns 422."""
    response = await client.post(
        "/api/jes/level-suggest",
        json={"og_code": "INVALID", "sub_group": None, "answers": {}},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "INVALID" in detail or "unknown" in detail.lower()


@pytest.mark.asyncio
async def test_level_suggest_nu_ema_direct_returns_highest(client, env_with_db):
    """JES-LEV-01 — POST /api/jes/level-suggest NU-EMA with expert_direction → level 2 high.

    NU-EMA uses level_resolution='direct' (single question). The expert_direction
    option hints [2] (length-1 list) → direct map to level 2, confidence='high'.
    """
    response = await client.post(
        "/api/jes/level-suggest",
        json={
            "og_code": "NU",
            "sub_group": "EMA",
            "answers": {"ema_scope": "expert_direction"},
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["suggested_level"] == 2
    assert data["confidence"] == "high"
    assert data["level_range"] == [2]


@pytest.mark.asyncio
async def test_level_suggest_empty_answers_returns_null_suggestion(client, env_with_db):
    """JES-LEV-01 — POST /api/jes/level-suggest with empty answers → null suggestion, low confidence.

    No hint_lists to count → return shape with suggested_level=None and confidence='low'.
    """
    response = await client.post(
        "/api/jes/level-suggest",
        json={"og_code": "NU", "sub_group": "HOS", "answers": {}},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["suggested_level"] is None
    assert data["confidence"] == "low"
    assert data["level_range"] == []


# ---------------------------------------------------------------------------
# GET /api/jes/level-criteria
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_level_criteria_nu_hos_returns_entry(client, env_with_db):
    """JES-LEV-01 — GET /api/jes/level-criteria?og_code=NU&sub_group=HOS returns NU-HOS entry."""
    response = await client.get(
        "/api/jes/level-criteria",
        params={"og_code": "NU", "sub_group": "HOS"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["method"] == "level_description"
    assert "questions" in data
    assert len(data["questions"]) == 2  # nu_scope + nu_autonomy
    assert data["level_resolution"] == "majority_hint"
    # First question is nu_scope
    assert data["questions"][0]["id"] == "nu_scope"
    # First option has a level_hint
    assert "level_hint" in data["questions"][0]["options"][0]


@pytest.mark.asyncio
async def test_level_criteria_ps_returns_entry_no_subgroup(client, env_with_db):
    """JES-LEV-01 — GET /api/jes/level-criteria?og_code=PS (no sub_group) returns PS entry."""
    response = await client.get(
        "/api/jes/level-criteria",
        params={"og_code": "PS"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["method"] == "level_description"
    assert len(data["questions"]) == 3  # ps_independence + ps_methods + ps_management
    assert data["level_resolution"] == "majority_hint"


@pytest.mark.asyncio
async def test_level_criteria_ec_returns_404(client, env_with_db):
    """JES-LEV-01 — GET /api/jes/level-criteria?og_code=EC returns 404 (EC is point-rated)."""
    response = await client.get(
        "/api/jes/level-criteria",
        params={"og_code": "EC"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_level_criteria_unknown_og_returns_422(client, env_with_db):
    """JES-LEV-01 — GET /api/jes/level-criteria with unknown og_code returns 422."""
    response = await client.get(
        "/api/jes/level-criteria",
        params={"og_code": "BOGUS"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/jes/level-criteria-groups
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_level_criteria_groups_returns_six_og_codes(client, env_with_db):
    """JES-LEV-01 — GET /api/jes/level-criteria-groups returns sorted list of distinct og_codes.

    Expected: NU, PS, NT, PO, SW, ED (6 codes; the level-description OG groups
    that have at least one sub-group entry in JES_LEVEL_CRITERIA).
    """
    response = await client.get("/api/jes/level-criteria-groups")
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    # The 6 base OG codes
    assert set(data) >= {"NU", "PS", "NT", "PO", "SW", "ED"}
    # Sorted
    assert data == sorted(data)
    # Does NOT include EC (point-rated, no level criteria)
    assert "EC" not in data
    assert "AS" not in data
    assert "IT" not in data
