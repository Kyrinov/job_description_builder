---
phase: 22-sjd-library
plan: 01
subsystem: testing
tags: [pytest, tdd, wave-0, red-baseline, sjd-library, fastapi]

# Dependency graph
requires:
  - phase: 21-og-expansion
    provides: "FastAPI test infrastructure (conftest.py with client fixture, tmp_db_path, env_with_db), WorkDescription Pydantic model, /api/wd CRUD endpoints, /api/og/classify pattern, Socratic + OG classification flows"
provides:
  - "Wave 0 RED test baseline for SJD-01 (SJD_LIBRARY constant, GET /api/sjd, GET /api/sjd/{number}, POST /api/wd/{id}/sjd-start) and SJD-02 (DraftDuty source='sjd' provenance, DOCX manifest SJD entry)"
affects: [22-02-sjd-library, 22-03-sjd-start, 22-04-sjd-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave 0 RED baseline: test file imports from not-yet-existing modules so pytest fails at collection on the 3 unit tests and on HTTP 404 for the 6 integration tests"
    - "Module-level pytestmark = pytest.mark.asyncio + 4 sync unit tests sharing the same module marker (matches plan action content; informational warnings only, not errors)"

key-files:
  created:
    - v2/backend/tests/test_sjd.py

key-decisions:
  - "Test count: file contains 10 test functions (4 unit + 6 integration). The plan frontmatter/objective text states 8 or 9, but the action content (authoritative) has 10 distinct named tests. Wrote all 10 verbatim from the action content."
  - "Test seed duties via direct call to _build_sjd_seed_duties (unit test). This means Wave 1 (plan 22-02) must export _build_sjd_seed_duties as a module-level function, not a private closure inside the sjd-start route handler."
  - "DOCX manifest provenance assertion uses _build_v2_manifest directly (existing helper in app/services/export_service.py) rather than parsing the DOCX binary — this is faster and isolates the assertion to the manifest data structure."

patterns-established:
  - "Wave 0 negative test passes incidentally: test_get_sjd_404 returns 404 from FastAPI's default catch-all (no implementation) AND from a correctly-implemented 404 handler — both pre- and post-implementation states. Documented as expected Wave 0 behavior; not a false positive."
  - "Test file imports app.api.wd._build_sjd_seed_duties and app.data.sjd_library.SJD_LIBRARY at function-level (inside each test) so the missing-module ImportError is reported as a per-test failure, not a collection error — improves failure granularity for future debugging."

requirements-completed: [SJD-01, SJD-02]

# Metrics
duration: ~3min
completed: 2026-06-11
---

# Phase 22: SJD Library — Plan 01 Summary

**Wave 0 RED test scaffold for SJD-01 and SJD-02: 10 named test functions (3 unit + 7 integration) covering SJD_LIBRARY constant, /api/sjd endpoints, /api/wd/{id}/sjd-start, DraftDuty source='sjd' provenance, and DOCX manifest SJD entry.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-06-11T18:10:05Z
- **Completed:** 2026-06-11T18:13:00Z
- **Tasks:** 1 (Wave 0 test scaffold — single task per plan)
- **Files modified:** 1 (created)

## Accomplishments

- `v2/backend/tests/test_sjd.py` created with exactly 10 test functions (155 lines), syntactically valid Python, all matching the plan's action content
- 9 of 10 tests fail RED because the SJD implementation modules do not yet exist:
  - 3 unit tests fail with `ModuleNotFoundError: No module named 'app.data.sjd_library'`
  - 1 unit test fails with `ImportError: cannot import name '_build_sjd_seed_duties' from 'app.api.wd'`
  - 5 integration tests fail with `assert 404 == 200` (no /api/sjd router, no /api/wd/{id}/sjd-start endpoint)
- 1 test (`test_get_sjd_404`) is incidentally green — FastAPI's default catch-all returns 404 for any unregistered route, so the negative-test assertion holds both pre- and post-implementation
- Plan 22-02 (SJD_LIBRARY constant + GET endpoints) and 22-03 (sjd-start + manifest extension) now have a concrete pass/fail baseline to turn GREEN against

## Task Commits

1. **Task 1: Write all SJD test stubs (RED baseline)** - `43814c1` (test)

**Plan metadata:** `43814c1` (test)

## Files Created/Modified

- `v2/backend/tests/test_sjd.py` (155 lines) — Wave 0 RED test stubs for SJD-01 and SJD-02. Imports from `app.data.sjd_library` (does not exist), `app.api.wd._build_sjd_seed_duties` (does not exist), and calls `/api/sjd` + `/api/wd/{id}/sjd-start` endpoints (not yet registered). 9/10 fail at collection/runtime; 1 is incidentally green.

## Decisions Made

- **Test count discrepancy:** The plan frontmatter says "9 test functions (3 unit + 6 integration)" and the objective says "8 test functions", but the action content has 10 distinct test functions. The grep-pattern list in `acceptance_criteria` has 10 patterns. Wrote 10 functions verbatim from the action content, treating it as the authoritative source.
- **No modification of test_get_sjd_404:** Considered tightening the assertion to discriminate "no implementation" from "implementation returns 404" (e.g., checking response body shape or specific error message), but the plan's literal test text and the TDD contract (assertion holds both pre- and post-implementation for a negative test) are valid. Documented as expected Wave 0 behavior instead.
- **Pytest warnings about sync tests under `pytest.mark.asyncio`:** The plan uses module-level `pytestmark = pytest.mark.asyncio` with 4 sync unit tests, which produces 4 informational `PytestWarning`s. The warnings do not affect test results (9 failed, 1 passed) and match the plan's design exactly. No action taken.

## Deviations from Plan

### Plan-text inconsistencies (informational, not code changes)

**1. Test count: plan says 8/9, file has 10**
- **Found during:** Task 1 (writing test file)
- **Issue:** Plan frontmatter claims "9 test functions (3 unit + 6 integration)" and objective claims "8 test functions", but the plan's action content (the complete file body) contains 10 test functions. The `acceptance_criteria` grep pattern list has 10 patterns.
- **Resolution:** Wrote the file exactly as the action content specifies (10 test functions). The action content is the authoritative source; the frontmatter/objective numbers are typos. `grep -c` returns 10, not 8 (this is correct, not a deviation from intent).
- **Files modified:** v2/backend/tests/test_sjd.py
- **Verification:** `grep -c "^def test_\|^async def test_" v2/backend/tests/test_sjd.py` returns 10. All 10 names from the grep-pattern list match.

**2. test_get_sjd_404 passes incidentally (not strictly RED)**
- **Found during:** Verification (running pytest)
- **Issue:** Plan `done` says "all RED because implementation modules do not yet exist", but the negative test `test_get_sjd_404` asserts 404 for an unknown SJD — and FastAPI returns 404 by default for any unregistered route. So 1 of 10 tests is green in Wave 0, not 9/10 RED.
- **Resolution:** Left the test as written. This is normal TDD Wave 0 behavior for negative tests: the assertion (404) is satisfied by both "no implementation" and "correct 404 handling" states. The test is correctly written for its purpose. Test result is 9 failed, 1 passed.
- **Files modified:** none
- **Verification:** `python -m pytest tests/test_sjd.py --tb=line` exits non-zero with 9 failures (RED) and 1 pass (test_get_sjd_404).

### Auto-fixed Issues

None.

---

**Total deviations:** 2 informational (test count wording, 1 test incidentally green) — neither is a code change.

**Impact on plan:** None. The test file is correct and provides the intended Wave 0 baseline. Plan 22-02 and 22-03 can turn the 9 RED tests GREEN; the 1 incidentally-green test will continue to pass and validate the 404 contract.

## Issues Encountered

None — the test file was written and committed in a single pass.

## Test Results Summary

```
$ python -m pytest tests/test_sjd.py --tb=line
FAILED tests/test_sjd.py::test_sjd_library_count - ModuleNotFoundError: No module named 'app.data.sjd_library'
FAILED tests/test_sjd.py::test_sjd_entry_fields - ModuleNotFoundError: No module named 'app.data.sjd_library'
FAILED tests/test_sjd.py::test_og_code_normalization - ModuleNotFoundError: No module named 'app.data.sjd_library'
FAILED tests/test_sjd.py::test_list_sjds_returns_all - assert 404 == 200
FAILED tests/test_sjd.py::test_list_sjds_filter_by_og - assert 404 == 200
FAILED tests/test_sjd.py::test_get_sjd_by_number - assert 404 == 200
FAILED tests/test_sjd.py::test_sjd_start_prefills_wd - assert 404 == 200
FAILED tests/test_sjd.py::test_seed_duties_provenance - ImportError: cannot import name '_build_sjd_seed_duties' from 'app.api.wd'
FAILED tests/test_sjd.py::test_manifest_includes_sjd_source - assert 404 == 200
PASSED tests/test_sjd.py::test_get_sjd_404
=================== 9 failed, 1 passed, 4 warnings in 4.70s ====================
```

- 9 tests RED (as intended)
- 1 test incidentally GREEN (negative test, FastAPI default 404 matches)
- 4 informational warnings (sync unit tests under module-level `pytest.mark.asyncio`)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 22-02 (SJD_LIBRARY constant + GET endpoints) can start immediately. The test stubs assert the exact contract for:

- `SJD_LIBRARY` constant shape: 10 entries from `data/SJD Examples.txt`
- `SJDEntry` dataclass with `sjd_number`, `title`, `og_code`, `og_level` (positive int)
- OG code normalization: no org-unit codes like PA, HM, NR; must be in {AS, FI, EC, IT, EN, PE, WP, PS, NU, SW, FB, FS, LC, LP, MT, NT, PO}
- `GET /api/sjd` returns list of 10 entries
- `GET /api/sjd?og_code=EC` filters by OG group
- `GET /api/sjd/{number}` returns single entry, 404 for unknown
- `_build_sjd_seed_duties(entry)` returns duties with `source="sjd"` and `sjd_number` set

Plan 22-03 will use the same test file to validate `POST /api/wd/{id}/sjd-start` and the DOCX manifest SJD provenance entry.

No blockers. No concerns.

---

*Phase: 22-sjd-library*
*Completed: 2026-06-11*

---

## Self-Check: PASSED

- File `v2/backend/tests/test_sjd.py` exists (155 lines, syntactically valid Python)
- File `.planning/phases/22-sjd-library/22-01-SUMMARY.md` exists
- Commit `43814c1` exists in git log
- 10 test functions collected by pytest
- 9 tests fail RED (4 ModuleNotFoundError/ImportError, 5 assert 404 == 200)
- 1 test passes incidentally (`test_get_sjd_404` — negative test, FastAPI default 404 matches)
