"""
test_jd_composition.py — Phase 18: JD composition backend contract.
Covers JD-01..04: duty fetch, provenance model, orphan check.
"""
import pytest

pytestmark = pytest.mark.asyncio


async def test_get_noc_duties_returns_main_duties(client, noc_duties_db):
    """JD-01: GET /api/noc/21232/duties returns list with text + source_hash."""
    assert False, "RED stub — Wave 1 implements GET /api/noc/{noc_code}/duties"


async def test_get_noc_duties_404_for_unknown_noc(client, noc_duties_db):
    """JD-01: GET /api/noc/99999/duties → 404 when no Main duties exist."""
    assert False, "RED stub — Wave 1 implements 404 path"


async def test_draft_duty_provenance_fields(client):
    """JD-02: DraftDuty model accepts provenance_noc_code, provenance_section, provenance_hash."""
    assert False, "RED stub — Wave 1 extends DraftDuty model"


async def test_advisor_duty_source_type(client):
    """JD-03: advisor duty has advisor=True and source='advisor'."""
    assert False, "RED stub — Wave 1 extends DraftDuty model"


async def test_orphan_check_ec_no_flags(client, noc_duties_db):
    """JD-04: POST /api/wd/{id}/orphan_check with EC OG returns flagged: []."""
    assert False, "RED stub — Wave 1 implements POST /api/wd/{id}/orphan_check"


async def test_patch_wd_duties_persists(client):
    """JD-01/02: PATCH /api/wd/{id} with duties[] list stores DraftDuty objects."""
    assert False, "RED stub — Wave 1 extends WDPatchRequest.duties"
