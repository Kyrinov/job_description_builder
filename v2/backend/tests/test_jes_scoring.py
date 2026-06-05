"""
tests/test_jes_scoring.py — Phase 17: JES Scoring tests (GREEN).

Unit tests cover the constants and model fields (JES-01, JES-03, API-07).
Integration tests cover the POST /api/jes/score and POST /api/jes/override
endpoints (JES-01, JES-02, JES-03, API-07).

Requirements coverage: JES-01, JES-02, JES-03, API-07.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.data.constants import (
    EC_DEGREES,
    EC_JES_ELEMENTS,
    KNOWN_JES_FACTORS,
    NON_EC_STANDARD_NAMES,
    NON_EC_TOTALS,
)


# ---------------------------------------------------------------------------
# Wave 0 — constants and model field tests (JES-01, JES-03, API-07)
# ---------------------------------------------------------------------------


def test_ec_jes_elements_defined():
    """JES-01 — EC_JES_ELEMENTS has 9 elements; each has name, category, pts dict."""
    assert len(EC_JES_ELEMENTS) == 9
    for el in EC_JES_ELEMENTS:
        assert "name" in el
        assert "category" in el
        assert "pts" in el
        assert isinstance(el["name"], str)
        assert isinstance(el["category"], str)
        assert isinstance(el["pts"], dict)


def test_ec_degrees_spot_check():
    """JES-01 — EC_DEGREES['EC-05'] is [5, 3, 5, 5, 4, 4, 1, 2, 2] (9 entries)."""
    assert EC_DEGREES["EC-05"] == [5, 3, 5, 5, 4, 4, 1, 2, 2]
    assert len(EC_DEGREES["EC-05"]) == 9


def test_non_ec_totals_coverage():
    """JES-03 — NON_EC_TOTALS covers FI, IT, AS, EN with level-keyed dicts."""
    assert set(NON_EC_TOTALS.keys()) >= {"FI", "IT", "AS", "EN"}
    for code, totals in NON_EC_TOTALS.items():
        assert isinstance(totals, dict)
        # Each entry should have int keys (levels) and int values (points)
        for level, points in totals.items():
            assert isinstance(level, int)
            assert isinstance(points, int)


def test_wd_model_jes_fields():
    """API-07 — WorkDescription instantiates with jes_scores=[] and jes_total_points=None."""
    from app.models.work_description import WorkDescription
    now = datetime.now(timezone.utc)
    wd = WorkDescription(
        id="test-wd",
        record={"title": "Test"},
        answers={},
        step_index=0,
        created_at=now,
        last_modified=now,
    )
    assert wd.jes_scores == []
    assert wd.jes_total_points is None


# ---------------------------------------------------------------------------
# Wave 2 — service and route tests (JES-01, JES-02, JES-03, API-07)
# ---------------------------------------------------------------------------


async def _create_wd_with_og(client, og_code: str = "EC", og_level: int = 5, *, set_og: bool = True):
    """Helper: create a WD and optionally set confirmed_og + og_level."""
    create_resp = await client.post(
        "/api/wd",
        json={"record": {"title": "Test Role"}, "answers": {}, "step_index": 0},
    )
    assert create_resp.status_code == 201
    wd_id = create_resp.json()["id"]
    if set_og:
        patch_resp = await client.patch(
            f"/api/wd/{wd_id}",
            json={
                "confirmed_og": {"og_code": og_code, "og_name": f"Test {og_code}"},
                "og_level": og_level,
            },
        )
        assert patch_resp.status_code == 200
    return wd_id


@pytest.mark.asyncio
async def test_score_ec_returns_9_factors(client, env_with_db):
    """JES-01 — POST /api/jes/score for EC group returns 9 factor rows.

    Mocks the LLM call to avoid hitting a real Ollama server in unit tests.
    """
    wd_id = await _create_wd_with_og(client, og_code="EC", og_level=5)

    # Mock the instructor client's chat.completions.create to return a fixed rating.
    # We use degree=5 because EC-05 factor pts[5] exists for every factor (or close to it).
    from app.ai.jes_scoring import JESFactorRating
    mock_rating = JESFactorRating(degree="D5", rationale="Mocked test rationale")

    with patch("app.services.jes_service.jes_instructor_client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_rating)
        response = await client.post(
            "/api/jes/score",
            json={
                "wd_id": wd_id,
                "og_code": "EC",
                "og_level": 5,
                "duties": ["Develop policy options", "Advise senior management"],
            },
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["is_ec"] is True
    assert len(data["factors"]) == 9
    assert data["og_code"] == "EC"
    # Each factor should have the mocked degree and rationale
    for factor in data["factors"]:
        assert factor["factor_name"]
        assert factor["degree"] == 5
        assert factor["rationale"] == "Mocked test rationale"
        # advisor_adjusted should be False for fresh scoring
        assert factor["advisor_adjusted"] is False


@pytest.mark.asyncio
async def test_override_writes_audit_log(client, env_with_db):
    """JES-02 — POST /api/jes/override/{wd_id}/{factor_name} writes audit_log row with event='jes_override'."""
    from app.db import get_connection
    from app.config import get_settings

    wd_id = await _create_wd_with_og(client, og_code="EC", og_level=5)

    # First, perform a score so we have a factor to override.
    from app.ai.jes_scoring import JESFactorRating
    mock_rating = JESFactorRating(degree="D3", rationale="Initial mocked rationale")

    with patch("app.services.jes_service.jes_instructor_client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_rating)
        score_resp = await client.post(
            "/api/jes/score",
            json={
                "wd_id": wd_id,
                "og_code": "EC",
                "og_level": 5,
                "duties": ["Test duty 1", "Test duty 2"],
            },
        )
    assert score_resp.status_code == 200, score_resp.text

    # Pick a known factor name to override
    factor_name = "Decision making"
    assert factor_name in KNOWN_JES_FACTORS

    # URL-encode the factor_name (it has a space). FastAPI path params accept literal strings,
    # so we pass it as-is — httpx will URL-encode the space.
    override_resp = await client.post(
        f"/api/jes/override/{wd_id}/{factor_name}",
        json={"degree": 4, "rationale": "Revised by advisor based on additional context"},
    )
    assert override_resp.status_code == 200, override_resp.text
    body = override_resp.json()
    assert body["factor_name"] == factor_name
    assert body["degree"] == 4
    # Decision making pts[4] = 60
    assert body["points"] == 60

    # Check audit_log
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        rows = con.execute(
            "SELECT event, actor, detail FROM audit_log WHERE wd_id = ? AND event = 'jes_override'",
            (wd_id,),
        ).fetchall()
    finally:
        con.close()

    assert len(rows) >= 1
    row = rows[0]
    assert row["event"] == "jes_override"
    assert row["actor"] == "advisor"
    import json as _json
    detail = _json.loads(row["detail"])
    assert detail["factor_name"] == factor_name
    assert detail["degree"] == 4


@pytest.mark.asyncio
async def test_score_non_ec_returns_totals(client, env_with_db):
    """JES-03 — POST /api/jes/score for non-EC (IT) returns single totals line + standard name."""
    wd_id = await _create_wd_with_og(
        client, og_code="IT", og_level=4
    )

    response = await client.post(
        "/api/jes/score",
        json={
            "wd_id": wd_id,
            "og_code": "IT",
            "og_level": 4,
            "duties": ["Develop and maintain application systems"],
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["is_ec"] is False
    # NON_EC_TOTALS["IT"][4] = 480
    assert data["total_points"] == 480
    assert "IT Job Evaluation Standard" in data["standard_name"]
    # Non-EC returns no factors (just a totals line)
    assert data["factors"] == []
    assert data["has_failed_factors"] is False


@pytest.mark.asyncio
async def test_score_requires_og_confirmed(client, env_with_db):
    """API-07 — POST /api/jes/score returns 409 when OG not yet confirmed."""
    # Create WD WITHOUT confirmed_og
    wd_id = await _create_wd_with_og(client, set_og=False)

    response = await client.post(
        "/api/jes/score",
        json={
            "wd_id": wd_id,
            "og_code": "EC",
            "og_level": 5,
            "duties": ["Test duty"],
        },
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    # The gate returns either a string detail or a dict; handle both
    if isinstance(detail, dict):
        assert detail.get("error") == "classification_pending"
    else:
        assert "classification" in detail.lower() or "OG" in detail
