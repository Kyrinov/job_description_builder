---
phase: 23-writing-guide-integration
plan: 01
status: complete
type: execute
wave: 1
depends_on: []
files_modified:
  - v2/backend/app/services/duty_validator.py
  - v2/backend/tests/test_writing_guide.py
requirements: [WG-01, WG-02, WG-03, WG-04]
---

# Plan 23-01 Summary — RED Baseline for WG-01 Duty Validator

## Objective
Created the Wave 0 RED baseline: 9 failing test stubs in test_writing_guide.py and a stub duty_validator.py module that makes all imports resolve but all assertions fail.

## Deliverables

### 1. `v2/backend/app/services/duty_validator.py` (NEW — 8 lines)
Module docstring + stdlib imports + `validate_duties(duties: list) -> list[dict]` stub returning `[]` unconditionally. Implementation is Wave 1 (Plan 02).

### 2. `v2/backend/tests/test_writing_guide.py` (NEW — 190 lines)
9 test functions, all `import` correctly, following `test_amendments.py` module structure:

| # | Test | Requirement | Status |
|---|------|-------------|--------|
| 1 | test_word_count_violation | WG-01 | RED — stub returns [] |
| 2 | test_passive_opener | WG-01 | RED — stub returns [] |
| 3 | test_non_verb_opener | WG-01 | RED — stub returns [] |
| 4 | test_duplicate_duty | WG-01 | RED — stub returns [] |
| 5 | test_calibration_sjd_corpus | WG-01 | RED — stub returns [] |
| 6 | test_validate_duties_endpoint | WG-02 | RED — endpoint 404 |
| 7 | test_validate_duties_404 | WG-02 | RED — endpoint 404 |
| 8 | test_client_service_results_step | WG-03 | PASS — OG_DEFINITIONS guard |
| 9 | test_og_definitions_coverage | WG-04 | PASS — OG_DEFINITIONS guard |

## Verification Results

```bash
cd v2/backend && python -m pytest tests/test_writing_guide.py --tb=short
```

```
5 failed, 4 passed, 7 warnings in 4.67s
```

**RED status confirmed:** 5 validator/endpoint tests fail as expected.
**Sentinel tests pass:** 4 guard tests for existing OG_DEFINITIONS coverage.

```bash
cd v2/backend && python -m pytest --ignore=tests/test_writing_guide.py -q
```

```
125 passed, 8 warnings in 10.29s
```

**No regressions:** Existing 125-test suite all green.

## Acceptance Criteria Met

- [x] `duty_validator.py` exists with `validate_duties()` returning `[]`
- [x] `test_writing_guide.py` exists with 9 test functions
- [x] `pytestmark = pytest.mark.asyncio` present in test file
- [x] `CALIBRATION_CORPUS` constant present (9 polished SJD duties)
- [x] 5 tests RED (FAILED, not ERROR) — confirms imports resolve but logic missing
- [x] 125-test existing suite still green
- [x] Committed atomically

## Decisions

- **Stub returns `[]` not `None`:** Matches the documented signature `list[dict]`. Type-consistent.
- **Tests follow `test_amendments.py` shape:** Standard async integration test pattern with `_create_wd` helper.
- **Sentinel tests for OG_DEFINITIONS:** Guard tests that pass on current data — provides regression protection if `constants.py` is ever pruned.
- **pytest warnings on non-async `def` tests:** Cosmetic only — same pattern as `test_sjd.py`. Asyncio mark applies globally; warnings are non-fatal.

## Next

Plan 23-02 will replace the stub with the full 4-rule implementation. The 5 RED tests should turn GREEN; the 2 endpoint tests stay RED (endpoint not yet wired — that's Plan 23-03).
