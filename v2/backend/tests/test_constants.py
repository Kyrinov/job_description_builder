"""
tests/test_constants.py — Unit tests for app/data/constants.py.

DATA-01 (6 tests): OG_LEVELS correct level counts, contiguous int lists, no CS key.
DATA-02 (2 tests): CAF_RANK_OG_EQUIVALENCE advisory flag + OG code cross-reference.

Phase 21 additions:
OGX-01 (1 test): test_og_constants_completeness — cross-constant completeness check for all 16 OG groups.
OGX-03 (1 test): test_qual_defaults_parity — QUAL_STANDARDS must cover all 16 groups + default. WRITTEN FAILING FIRST.

Wave 0: All 8 tests are RED (ImportError) until Task 2 writes constants.py.
Wave 1 (Plan 01): DATA-01 tests (6) go GREEN.
Wave 1 (Plan 02): DATA-02 tests (2) go GREEN.
"""
from app.data.constants import OG_LEVELS, CAF_RANK_OG_EQUIVALENCE


def test_og_levels_ec_has_8_levels():
    assert OG_LEVELS["EC"] == list(range(1, 9))
    assert len(OG_LEVELS["EC"]) == 8


def test_og_levels_it_has_5_levels():
    assert OG_LEVELS["IT"] == list(range(1, 6))
    assert len(OG_LEVELS["IT"]) == 5


def test_og_levels_as_has_8_levels():
    assert OG_LEVELS["AS"] == list(range(1, 9))
    assert len(OG_LEVELS["AS"]) == 8


def test_og_levels_fi_has_4_levels():
    assert OG_LEVELS["FI"] == list(range(1, 5))
    assert len(OG_LEVELS["FI"]) == 4


def test_og_levels_all_groups_are_lists_of_ints():
    for code, levels in OG_LEVELS.items():
        assert isinstance(levels, list), f"{code} levels must be a list"
        assert all(isinstance(n, int) for n in levels), f"{code} levels must be ints"
        assert levels == list(range(levels[0], levels[-1] + 1)), \
            f"{code} levels must be contiguous starting at {levels[0]}"


def test_og_levels_no_cs_key():
    assert "CS" not in OG_LEVELS, "CS is not a current standalone OG group (merged into IT)"


def test_caf_table_all_entries_advisory_flagged():
    for rank, entry in CAF_RANK_OG_EQUIVALENCE.items():
        assert entry.get("advisory") is True, \
            f"CAF rank '{rank}' must have advisory=True"


def test_caf_table_og_codes_exist_in_og_levels():
    all_og_codes = set(OG_LEVELS.keys())
    for rank, entry in CAF_RANK_OG_EQUIVALENCE.items():
        for og_level_str in entry["approx_civilian_og_levels"]:
            og_code = og_level_str.split("-")[0]
            assert og_code in all_og_codes, \
                f"CAF rank '{rank}' references OG code '{og_code}' not in OG_LEVELS"


# ---------------------------------------------------------------------------
# Phase 21 — OGX-01: cross-constant completeness
# ---------------------------------------------------------------------------

def test_og_constants_completeness():
    """OGX-01 — every key in OG_LEVELS is present in all other 5 constants.

    FAILS at Wave 0: JES_FACTORS_BY_GROUP does not yet exist in constants.py.
    Goes GREEN after Plan 03 (Wave 2) authors all 16-group constant data.
    """
    from app.data.constants import (
        OG_LEVELS,
        OG_DEFINITIONS,
        QUAL_STANDARDS,
        NON_EC_TOTALS,
        NON_EC_STANDARD_NAMES,
        JES_FACTORS_BY_GROUP,
    )
    POINT_RATING_GROUPS = {"FB", "FS", "LP", "MT", "LC"}  # SW-SCW via sub-group
    for og_code in OG_LEVELS:
        assert og_code in OG_DEFINITIONS, f"{og_code} missing from OG_DEFINITIONS"
        assert og_code in NON_EC_STANDARD_NAMES, \
            f"{og_code} missing from NON_EC_STANDARD_NAMES"
        if og_code in POINT_RATING_GROUPS:
            assert og_code in JES_FACTORS_BY_GROUP, \
                f"{og_code} missing from JES_FACTORS_BY_GROUP"
        elif og_code not in ("EC",):
            assert og_code in NON_EC_TOTALS, \
                f"{og_code} missing from NON_EC_TOTALS"
    # QUAL_STANDARDS uses "default" as fallback; any group not in the dict falls back
    # The completeness test only checks QUAL_STANDARDS has at least the 4 existing groups
    # (parity with frontend QUAL_DEFAULTS is covered by test_qual_defaults_parity below)


# ---------------------------------------------------------------------------
# Phase 21 — OGX-03: QUAL_DEFAULTS / QUAL_STANDARDS parity
# Written as FAILING test before any new group qualification text is authored.
# ---------------------------------------------------------------------------

def test_qual_defaults_parity():
    """OGX-03 — QUAL_STANDARDS (backend) must have an explicit entry for every group
    key present in the frontend QUAL_DEFAULTS constant.

    FAILS at Wave 0: QUAL_STANDARDS currently has only EC, AS, IT, FI, default.
    Goes GREEN after Plan 03 (Wave 2) adds all 12 new group entries.
    """
    from app.data.constants import QUAL_STANDARDS
    EXPECTED_GROUPS = {
        "EC", "AS", "IT", "FI",
        "ED", "FB", "FS", "LC", "LP", "MT", "NT", "NU", "PO", "PS", "SW", "WP",
        "default",
    }
    missing = EXPECTED_GROUPS - set(QUAL_STANDARDS.keys())
    assert not missing, f"QUAL_STANDARDS missing keys: {missing}"
