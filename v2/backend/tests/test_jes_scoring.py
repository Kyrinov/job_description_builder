"""
tests/test_jes_scoring.py — Phase 17: JES Scoring RED stubs.

All tests currently raise pytest.fail (RED). Plans 17-02/17-03 turn them GREEN.
Requirements coverage: JES-01, JES-02, JES-03, JES-04, API-07.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Wave 0 — constants and model field tests (JES-01, JES-03, API-07)
# ---------------------------------------------------------------------------


def test_ec_jes_elements_defined():
    """JES-01 — EC_JES_ELEMENTS has 9 elements; each has name, category, pts dict."""
    pytest.fail("RED — not implemented")


def test_ec_degrees_spot_check():
    """JES-01 — EC_DEGREES['EC-05'] is [5, 3, 5, 5, 4, 4, 1, 2, 2] (9 entries)."""
    pytest.fail("RED — not implemented")


def test_non_ec_totals_coverage():
    """JES-03 — NON_EC_TOTALS covers FI, IT, AS, EN with level-keyed dicts."""
    pytest.fail("RED — not implemented")


def test_wd_model_jes_fields():
    """API-07 — WorkDescription instantiates with jes_scores=[] and jes_total_points=None."""
    pytest.fail("RED — not implemented")


# ---------------------------------------------------------------------------
# Wave 2 — service and route tests (JES-01, JES-02, JES-03, API-07)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_ec_returns_9_factors(client, env_with_db):
    """JES-01 — POST /api/jes/score for EC group returns 9 factor rows."""
    pytest.fail("RED — not implemented")


@pytest.mark.asyncio
async def test_override_writes_audit_log(client, env_with_db):
    """JES-02 — POST /api/jes/override/{wd_id}/{factor_name} writes audit_log row with event='jes_override'."""
    pytest.fail("RED — not implemented")


@pytest.mark.asyncio
async def test_score_non_ec_returns_totals(client, env_with_db):
    """JES-03 — POST /api/jes/score for non-EC (IT) returns single totals line + standard name."""
    pytest.fail("RED — not implemented")


@pytest.mark.asyncio
async def test_score_requires_og_confirmed(client, env_with_db):
    """API-07 — POST /api/jes/score returns 409 when OG not yet confirmed."""
    pytest.fail("RED — not implemented")
