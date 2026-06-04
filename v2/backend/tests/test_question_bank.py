"""
tests/test_question_bank.py — Unit tests for QUESTION_BANK in app/data/constants.py.

QUES-01 (5 tests): every entry has required keys; OG codes valid; JES hints valid;
    minimum question count; covers EC/AS/IT/FI.
QUES-02 (1 test): no OG code appears in user-visible text (question, helper, option label).
QUES-03 (1 test): all entries have phase_slot="work_type"; input_type is a known value.

Wave 0 (Plan 01): All tests are importable; tests 1 and 7 are RED (QUESTION_BANK is []).
    Tests 2-6 pass vacuously (no entries to iterate). Test file itself is GREEN structurally.
Wave 1 (Plan 02): Full QUESTION_BANK written; all 7 tests GREEN.
"""
from app.data.constants import QUESTION_BANK, OG_LEVELS, KNOWN_JES_FACTORS

REQUIRED_ENTRY_KEYS = {"id", "phase_slot", "question", "helper", "input_type", "options"}
REQUIRED_SIGNAL_KEYS = {"og_candidates", "jes_factor_hints", "teer_affinity"}
KNOWN_INPUT_TYPES = {"choices", "scale"}


def test_question_bank_has_minimum_questions():
    assert len(QUESTION_BANK) >= 4, \
        f"QUESTION_BANK must have at least 4 entries, found {len(QUESTION_BANK)}"


def test_every_entry_has_required_keys():
    for entry in QUESTION_BANK:
        missing = REQUIRED_ENTRY_KEYS - entry.keys()
        assert not missing, \
            f"Entry '{entry.get('id')}' missing required keys: {missing}"


def test_every_option_has_required_signal_keys():
    for entry in QUESTION_BANK:
        for opt in entry["options"]:
            missing = REQUIRED_SIGNAL_KEYS - opt["signals"].keys()
            assert not missing, \
                f"Option '{opt.get('id')}' in entry '{entry.get('id')}' missing signal keys: {missing}"


def test_og_candidates_all_exist_in_og_levels():
    all_og_codes = set(OG_LEVELS.keys())
    for entry in QUESTION_BANK:
        for opt in entry["options"]:
            for code in opt["signals"]["og_candidates"]:
                assert code in all_og_codes, \
                    f"Entry '{entry.get('id')}' option '{opt.get('id')}' references OG code '{code}' not in OG_LEVELS"


def test_jes_factor_hints_all_known():
    for entry in QUESTION_BANK:
        for opt in entry["options"]:
            for hint in opt["signals"]["jes_factor_hints"]:
                assert hint in KNOWN_JES_FACTORS, \
                    f"Entry '{entry.get('id')}' option '{opt.get('id')}' references unknown JES factor hint: '{hint}'"


def test_no_og_codes_in_user_visible_text():
    og_codes = set(OG_LEVELS.keys())
    for entry in QUESTION_BANK:
        for field in ("question", "helper"):
            for code in og_codes:
                assert code not in entry[field], \
                    f"OG code '{code}' found in user-visible field '{field}' of entry '{entry.get('id')}'"
        for opt in entry["options"]:
            for code in og_codes:
                assert code not in opt["label"], \
                    f"OG code '{code}' found in option label of entry '{entry.get('id')}'"


def test_covers_minimum_four_groups():
    all_candidates: set[str] = set()
    for entry in QUESTION_BANK:
        for opt in entry["options"]:
            all_candidates.update(opt["signals"]["og_candidates"])
    for required_group in ("EC", "AS", "IT", "FI"):
        assert required_group in all_candidates, \
            f"Required group '{required_group}' has no signal anywhere in QUESTION_BANK"


def test_all_entries_have_phase_slot_work_type():
    for entry in QUESTION_BANK:
        assert entry.get("phase_slot") == "work_type", \
            f"Entry '{entry.get('id')}' must have phase_slot='work_type', got '{entry.get('phase_slot')}'"


def test_all_entries_have_known_input_type():
    for entry in QUESTION_BANK:
        assert entry.get("input_type") in KNOWN_INPUT_TYPES, \
            f"Entry '{entry.get('id')}' has unknown input_type '{entry.get('input_type')}'; must be one of {KNOWN_INPUT_TYPES}"
