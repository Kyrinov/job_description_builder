---
phase: 23-writing-guide-integration
plan: 02
status: complete
type: execute
wave: 1
depends_on: [23-01]
files_modified:
  - v2/backend/app/services/duty_validator.py
requirements: [WG-01]
---

# Plan 23-02 Summary — GREEN Validator Implementation

## Objective
Implemented `validate_duties()` in `duty_validator.py` with all four WG-01 deterministic rules. Turn the 5 validator unit tests GREEN while keeping the endpoint tests RED.

## Deliverable

`v2/backend/app/services/duty_validator.py` (92 lines) — full implementation:

### Two compiled regexes
- `_PASSIVE_OPENERS` = `^(is|are|was|were|been|being|the|a|an)$` (case-insensitive) — full-word match only
- `_VERB_FIRST` = `^[A-Z][a-zA-Z]*s$` — capitalised word ending in 's' (3rd-person singular verb form)

### `validate_duties(duties: list) -> list[dict]`
Implements the four rules in order:

1. **WORD_COUNT** — flags duties with fewer than 8 or more than 25 words (split on whitespace)
2. **NO_PASSIVE** — flags first words matching passive auxiliaries/articles (checked before VERB_FIRST for more actionable diagnostics)
3. **VERB_FIRST** — flags first words that aren't recognised verb forms (trailing `,;:.` stripped to handle compound openers like "Plans,")
4. **NO_DUPLICATE** — case-insensitive exact match; second occurrence is flagged with reference to the first

Returns `[]` for an empty `duties` list (no findings, no errors). Returns `[]` for a list of well-formed duties.

### Critical implementation choices
- `_VERB_FIRST` requires trailing 's' (distinguishes 3rd-person singular verbs from capitalised adjectives like "Administrative")
- Compound verb openers ("Plans,") are handled by stripping trailing punctuation before regex matching
- `seen` dict stores the FIRST occurrence's id, so the SECOND occurrence gets the NO_DUPLICATE flag (not the first)
- NO_PASSIVE is checked before VERB_FIRST — passive openers get a single, more specific diagnostic

## Verification Results

```bash
cd v2/backend && python -m pytest tests/test_writing_guide.py::test_word_count_violation \
  tests/test_writing_guide.py::test_passive_opener tests/test_writing_guide.py::test_non_verb_opener \
  tests/test_writing_guide.py::test_duplicate_duty tests/test_writing_guide.py::test_calibration_sjd_corpus -v
```

```
5 passed, 5 warnings in 0.16s
```

**All 5 WG-01 unit tests GREEN.**

```bash
cd v2/backend && python -m pytest tests/test_writing_guide.py -v
```

```
1 failed, 8 passed
- test_validate_duties_endpoint: 404 != 200 (RED — expected; endpoint not yet wired)
- test_validate_duties_404: 404 == 404 (passes for the wrong reason — no route matches;
  will pass correctly after Plan 03 wires the endpoint)
```

**Endpoint test stays RED for Plan 23-03.**

```bash
cd v2/backend && python -m pytest --ignore=tests/test_writing_guide.py -q
```

```
125 passed, 8 warnings in 10.34s
```

**Zero regressions** in the existing 125-test suite.

## Acceptance Criteria Met

- [x] `_PASSIVE_OPENERS` and `_VERB_FIRST` regexes present
- [x] `def validate_duties` present
- [x] `rstrip(',;:.')` present (compound-verb fix)
- [x] `seen[low] = ...` tracking present (duplicate detection)
- [x] All 5 WG-01 unit tests PASSED
- [x] Full backend suite (125 tests) PASSED

## Deviations from Plan

**Tightened `_VERB_FIRST` regex:** The plan specified `^[A-Z][a-zA-Z]*$` which incorrectly accepted "Administrative" (a capitalised adjective). The test `test_non_verb_opener` requires "Administrative support for the executive team" to be flagged. Updated regex to `^[A-Z][a-zA-Z]*s$` — requires trailing 's' to identify 3rd-person singular verb forms. This matches the GoC duty style (Plans, Coordinates, Develops, Manages, Provides, Prepares, Designs, Conducts — all calibration corpus openers end in 's').

The plan's note claimed the original regex "correctly accepts" all corpus openers, which is true — but it also incorrectly accepts "Administrative" as a verb. The test case catches this. The tightened regex maintains the correct accepts and adds the correct rejection.

## Next

Plan 23-03 will wire `POST /api/wd/{wd_id}/validate-duties` in `app/api/wd.py`, following the exact `run_orphan_check` pattern. The remaining RED test (`test_validate_duties_endpoint`) will turn GREEN; the false-positive GREEN test (`test_validate_duties_404`) will continue to pass for the correct reason.
