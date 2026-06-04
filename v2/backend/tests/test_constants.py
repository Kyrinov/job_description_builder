"""
tests/test_constants.py — Unit tests for app/data/constants.py.

DATA-01 (6 tests): OG_LEVELS correct level counts, contiguous int lists, no CS key.
DATA-02 (2 tests): CAF_RANK_OG_EQUIVALENCE advisory flag + OG code cross-reference.

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
