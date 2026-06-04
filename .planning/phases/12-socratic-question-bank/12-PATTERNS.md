# Phase 12: Socratic Question Bank — Pattern Map

**Mapped:** 2026-06-04
**Files analyzed:** 2 (1 modified, 1 created)
**Analogs found:** 2 / 2

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `v2/backend/app/data/constants.py` | config / data constant | transform (append-only) | `v2/backend/app/data/constants.py` itself (existing OG_LEVELS + CAF_RANK_OG_EQUIVALENCE blocks) | exact — same file, same pattern |
| `v2/backend/tests/test_question_bank.py` | test | transform (validation) | `v2/backend/tests/test_constants.py` | exact — same test style, same cross-reference pattern |

---

## Pattern Assignments

### `v2/backend/app/data/constants.py` — MODIFIED (append KNOWN_JES_FACTORS + QUESTION_BANK)

**Analog:** The existing constants.py itself — `OG_LEVELS` block (lines 33–48) and `CAF_RANK_OG_EQUIVALENCE` block (lines 64–149).

**File-header / module docstring pattern** (lines 5–16):
```python
"""
app/data/constants.py — Authoritative data constants for v2.0.

OG_LEVELS: maps OG code -> list of level integers ...
CAF_RANK_OG_EQUIVALENCE: maps CAF rank name -> approximate civilian OG equivalents.
"""
from __future__ import annotations
```
New appended constants must add a one-line entry to the module docstring before the closing `"""`. No new imports needed — `QUESTION_BANK` is a plain `list[dict]` and `KNOWN_JES_FACTORS` is a `frozenset[str]`; both use only stdlib types already available via `from __future__ import annotations`.

**Section-separator + inline documentation pattern** (lines 20–31 and lines 50–63):
```python
# ---------------------------------------------------------------------------
# CONSTANT_NAME
# One-sentence description of what this maps.
# Source: where data came from.
# Key: description. Value: description.
# ---------------------------------------------------------------------------
```
Every new constant block must open with this 7-line section header. Include source provenance and key/value semantics. This is the only documentation convention used in this file — no docstrings on individual constants.

**Simple dict/list constant declaration pattern** (lines 33–48 — OG_LEVELS):
```python
OG_LEVELS: dict[str, list[int]] = {
    # Focus groups for v2.0 OG classification (EC, IT, AS, FI)
    "EC": list(range(1, 9)),   # EC-01 to EC-08 — EC_rates.csv
    "IT": list(range(1, 6)),   # IT-01 to IT-05 — IT_CS_rates.csv (CS merged into IT)
    ...
}
```
Type annotations are on the assignment, not inside the value. Inline comments after each entry explain the source file. Use the same `CONSTANT_NAME: type = value` shape for both `KNOWN_JES_FACTORS` and `QUESTION_BANK`.

**KNOWN_JES_FACTORS pattern to append** (after CAF_RANK_OG_EQUIVALENCE, before QUESTION_BANK):
```python
# ---------------------------------------------------------------------------
# KNOWN_JES_FACTORS
# Canonical JES factor names from EC_ELEMENTS (prototype data.jsx, verified).
# Used by test_question_bank.py to cross-reference jes_factor_hints signals.
# Key: frozenset of exact factor name strings (use & not "and").
# ---------------------------------------------------------------------------

KNOWN_JES_FACTORS: frozenset[str] = frozenset({
    "Decision making",
    "Leadership & operational mgmt",
    "Communication",
    "Knowledge of specialized fields",
    "Contextual knowledge",
    "Research & analysis",
    "Physical effort",
    "Sensory effort",
    "Working conditions",
})
```

**QUESTION_BANK constant pattern to append** (after KNOWN_JES_FACTORS):
```python
# ---------------------------------------------------------------------------
# QUESTION_BANK
# Socratic work-description questions that drive the work_type conversation phase.
# Each entry elicits a natural-language description from the manager; OG group
# is derived from accumulated signals, never directly selected by the user.
# QUES-02 constraint: OG codes must not appear in "question", "helper", or
# options[].label — only inside signals.og_candidates.
# ---------------------------------------------------------------------------

QUESTION_BANK: list[dict] = [
    {
        "id": str,           # stable slug — used by Phase 15 for stepId routing
        "phase_slot": str,   # always "work_type" for this bank
        "question": str,     # plain-language question, no OG codes in text
        "helper": str,       # sub-label shown below question
        "input_type": str,   # "choices" | "scale"
        "options": [
            {
                "id": str,       # stable slug
                "label": str,    # display text — must not contain OG codes
                "signals": {
                    "og_candidates": list[str],    # OG codes from OG_LEVELS keys
                    "jes_factor_hints": list[str], # names from KNOWN_JES_FACTORS
                    "teer_affinity": list[int],    # NOC TEER levels (1=highest)
                },
            },
        ],
    },
    # ... additional entries follow same schema
]
```

---

### `v2/backend/tests/test_question_bank.py` — CREATED

**Analog:** `v2/backend/tests/test_constants.py` (lines 1–59)

**Module docstring + import pattern** (lines 1–11):
```python
"""
tests/test_question_bank.py — Unit tests for QUESTION_BANK in app/data/constants.py.

QUES-01 (N tests): every entry has required keys; OG codes valid; JES hints valid; covers EC/AS/IT/FI.
QUES-02 (1 test): no OG code in user-visible text fields.
QUES-03 (1 test): all entries have phase_slot="work_type"; input_type is a known value.

Wave 0: All tests are RED (ImportError or structural) until QUESTION_BANK is written.
Wave 1 (Plan 01): Stub QUESTION_BANK written; structural tests go GREEN.
Wave 1 (Plan 02): Full content written; all tests GREEN.
"""
from app.data.constants import QUESTION_BANK, OG_LEVELS, KNOWN_JES_FACTORS
```
Single import line. No `pytest` import needed unless fixtures are used — none are required here. Follow the exact same docstring format as `test_constants.py`: req-ID prefix, count, description, wave annotation.

**Cross-reference validation pattern** (lines 52–58 of test_constants.py — `test_caf_table_og_codes_exist_in_og_levels`):
```python
def test_caf_table_og_codes_exist_in_og_levels():
    all_og_codes = set(OG_LEVELS.keys())
    for rank, entry in CAF_RANK_OG_EQUIVALENCE.items():
        for og_level_str in entry["approx_civilian_og_levels"]:
            og_code = og_level_str.split("-")[0]
            assert og_code in all_og_codes, \
                f"CAF rank '{rank}' references OG code '{og_code}' not in OG_LEVELS"
```
Apply the same structure for `test_og_candidates_all_exist_in_og_levels` and `test_jes_factor_hints_all_known` in `test_question_bank.py`: iterate entries → iterate options → iterate signal list → assert membership in the reference set. Use the same f-string failure message convention: `f"<entity> references <value> not in <constant>"`.

**Nested iteration pattern for multi-level data** (same analog — lines 53–58):
```python
for rank, entry in CAF_RANK_OG_EQUIVALENCE.items():
    for og_level_str in entry["approx_civilian_og_levels"]:
        assert ..., f"..."
```
`QUESTION_BANK` entries are three levels deep (entry → option → signal list). Use:
```python
for entry in QUESTION_BANK:
    for opt in entry["options"]:
        for code in opt["signals"]["og_candidates"]:
            assert code in OG_LEVELS, f"OG code '{code}' not in OG_LEVELS"
```

**Advisory flag pattern** (lines 46–49 of test_constants.py — `test_caf_table_all_entries_advisory_flagged`):
```python
def test_caf_table_all_entries_advisory_flagged():
    for rank, entry in CAF_RANK_OG_EQUIVALENCE.items():
        assert entry.get("advisory") is True, \
            f"CAF rank '{rank}' must have advisory=True"
```
This is the pattern for "every entry must have a required field equal to a specific value." Apply same structure for `test_all_entries_have_phase_slot_work_type`:
```python
def test_all_entries_have_phase_slot_work_type():
    for entry in QUESTION_BANK:
        assert entry.get("phase_slot") == "work_type", \
            f"Entry '{entry.get('id')}' must have phase_slot='work_type'"
```

**Key-presence validation pattern** (lines 34–39 of test_constants.py — `test_og_levels_all_groups_are_lists_of_ints`):
```python
def test_og_levels_all_groups_are_lists_of_ints():
    for code, levels in OG_LEVELS.items():
        assert isinstance(levels, list), f"{code} levels must be a list"
        assert all(isinstance(n, int) for n in levels), f"{code} levels must be ints"
```
For key-presence on dict entries, adapt to `.issubset()`:
```python
REQUIRED_KEYS = {"id", "phase_slot", "question", "helper", "input_type", "options"}

def test_every_entry_has_required_keys():
    for entry in QUESTION_BANK:
        assert REQUIRED_KEYS.issubset(entry.keys()), \
            f"Entry '{entry.get('id')}' missing keys: {REQUIRED_KEYS - entry.keys()}"
```

**Negative assertion pattern** (lines 42–43 of test_constants.py — `test_og_levels_no_cs_key`):
```python
def test_og_levels_no_cs_key():
    assert "CS" not in OG_LEVELS, "CS is not a current standalone OG group (merged into IT)"
```
Apply same "assert X not in Y" style for QUES-02 Socratic constraint:
```python
def test_no_og_codes_in_user_visible_text():
    og_codes = set(OG_LEVELS.keys())
    for entry in QUESTION_BANK:
        for field in ("question", "helper"):
            for code in og_codes:
                assert code not in entry[field], \
                    f"OG code '{code}' found in user-visible field '{field}' of '{entry['id']}'"
        for opt in entry["options"]:
            for code in og_codes:
                assert code not in opt["label"], \
                    f"OG code '{code}' found in option label of '{entry['id']}'"
```

---

## Shared Patterns

### Section Separator Block
**Source:** `v2/backend/app/data/constants.py` lines 20–31 and 50–63
**Apply to:** Every new constant appended to constants.py
```python
# ---------------------------------------------------------------------------
# CONSTANT_NAME
# Description sentence.
# Source: provenance note.
# Key: ... Value: ...
# ---------------------------------------------------------------------------
```

### Cross-Reference Assertion (iterate → assert membership)
**Source:** `v2/backend/tests/test_constants.py` lines 52–58
**Apply to:** All signal cross-reference tests in test_question_bank.py
```python
for entry in QUESTION_BANK:
    for opt in entry["options"]:
        for value in opt["signals"]["<key>"]:
            assert value in REFERENCE_SET, f"'<value>' not in <CONSTANT_NAME>"
```

### f-String Failure Message Convention
**Source:** `v2/backend/tests/test_constants.py` — all assertion f-strings
**Apply to:** Every assertion in test_question_bank.py
Pattern: `f"<entity descriptor> '<identifier>' <verb> <what went wrong>"`
Examples from analog: `f"CAF rank '{rank}' references OG code '{og_code}' not in OG_LEVELS"`, `f"{code} levels must be a list"`

---

## No Analog Found

None. Both files have direct analogs in the codebase.

---

## Metadata

**Analog search scope:** `v2/backend/app/data/`, `v2/backend/tests/`
**Files scanned:** 2 (constants.py, test_constants.py)
**Pattern extraction date:** 2026-06-04
