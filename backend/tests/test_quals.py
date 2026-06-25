"""
test_quals.py — Phase 19 QUAL-01: OG-keyed qualification defaults.

Tests that QUAL_STANDARDS in app/data/constants.py contains correct
OG-matched education + experience text for EC, AS, IT, FI, and default.
These tests verify the backend constant that feeds GET /api/quals/default.
The frontend QUAL_DEFAULTS map (data.jsx) must mirror these values exactly.

QUAL-01 requirement: EC/AS/IT/FI defaults from TBS Qualification Standards.
"""
import pytest

pytestmark = pytest.mark.asyncio


def test_qual_default_ec():
    """QUAL-01 — EC default has education (degree) and experience (policy analysis)."""
    from app.data.constants import QUAL_STANDARDS
    ec = QUAL_STANDARDS.get("EC")
    assert ec is not None, "EC entry missing from QUAL_STANDARDS"
    assert ec.get("education"), "EC education field is empty"
    assert ec.get("experience"), "EC experience field is empty"
    assert "degree" in ec["education"].lower() or "recognized post-secondary" in ec["education"].lower(), \
        f"EC education should reference a degree; got: {ec['education']}"
    assert "policy" in ec["experience"].lower() or "analysis" in ec["experience"].lower(), \
        f"EC experience should reference policy/analysis; got: {ec['experience']}"


def test_qual_default_all_groups():
    """QUAL-01 — AS, IT, FI defaults all have non-empty education + experience fields."""
    from app.data.constants import QUAL_STANDARDS
    for og_code in ("AS", "IT", "FI"):
        entry = QUAL_STANDARDS.get(og_code)
        assert entry is not None, f"{og_code} entry missing from QUAL_STANDARDS"
        assert entry.get("education"), f"{og_code} education field is empty"
        assert entry.get("experience"), f"{og_code} experience field is empty"


def test_qual_default_fallback():
    """QUAL-01 — 'default' entry exists for unknown OG codes; does not raise."""
    from app.data.constants import QUAL_STANDARDS
    default = QUAL_STANDARDS.get("default")
    assert default is not None, "'default' entry missing from QUAL_STANDARDS"
    assert default.get("education"), "default education field is empty"
    assert default.get("experience"), "default experience field is empty"
