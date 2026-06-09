---
phase: 19-qualifications-amendments
plan: 01
subsystem: testing
tags: [pytest, vitest, red-stubs, qual-01, qual-03, amend-01, audit-log, qual-standards]

# Dependency graph
requires:
  - phase: 16-og-classification
    provides: QUAL_STANDARDS constant + GET /api/quals/default + confirmed_og/og_level on WorkDescription
provides:
  - RED test baseline for QUAL-01 (backend) — 3 tests covering EC/AS/IT/FI/default entries in QUAL_STANDARDS
  - RED test baseline for AMEND-01 + AMEND-02 (backend) — 6 skip-decorated stubs covering POST/GET/404/audit_log/422 fields
  - RED test stub for QUAL-03 (frontend) — 1 failing test asserting Section 5 renders .qual-sub-k class
  - 'default' fallback entry added to QUAL_STANDARDS (Phase 16 gap closed)
affects:
  - 19-02 (Wave 1: turns QUAL-01/02/03 stubs GREEN by wiring OG-keyed defaults, QualEditor touched validation, .qual-sub-k CSS)
  - 19-03 (Wave 2: un-skips the 6 amendment stubs by implementing amendments.py backend + frontend panel)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RED stub strategy: backend tests that verify already-existing constants (test_quals.py) pass immediately; backend tests for not-yet-implemented endpoints decorated with @pytest.mark.skip so the suite stays at 64→67 passed with 0 failures"
    - "Frontend RED stub uses expect(container.innerHTML).toContain('qual-sub-k') to assert future CSS class — fails cleanly because document.jsx still uses inline styles, exactly the Wave 0 state the plan requires"

key-files:
  created:
    - v2/backend/tests/test_quals.py
    - v2/backend/tests/test_amendments.py
  modified:
    - v2/backend/app/data/constants.py
    - v2/frontend/src/document.test.jsx

key-decisions:
  - "Added 'default' fallback entry to QUAL_STANDARDS in constants.py (Rule 2 deviation) — Phase 16 left this gap; the test_qual_default_fallback stub would otherwise fail with 'default entry missing'; mirrors the frontend QUAL_DEFAULTS['default'] entry documented in 19-PATTERNS.md"
  - "Kept the 3 PytestWarning notifications about @pytest.mark.asyncio on sync tests — plan template includes pytestmark = pytest.mark.asyncio at module level; the warnings are informational only and match the plan's exact code"
  - "Acknowledged the 7-vs-6 mismatch on grep -c 'pytest.mark.skip' — the 7th match is a docstring mention in the file header, not a 7th decorator. The 6 actual @pytest.mark.skip decorators are correct."

patterns-established:
  - "Backend RED stub pattern for not-yet-existing endpoints: import client + env_with_db fixtures from conftest.py; create WD via _create_wd helper; assert 201/200/404 status; inspect audit_log via get_connection(settings.db_path); use @pytest.mark.skip(reason='<phase>-W<n>') for un-block control"
  - "Frontend RED stub pattern for future CSS classes: append a new describe block to the end of an existing test file; use expect(container.innerHTML).toContain('<class-name>') so the failure mode is clean and the test path to GREEN is well-defined"

requirements-completed: [QUAL-01, QUAL-02, QUAL-03, AMEND-01, AMEND-02]

# Metrics
duration: 8min
completed: 2026-06-09
---

# Phase 19 Plan 01: Wave 0 RED Test Stubs

**Backend RED stubs for QUAL-01 (test_quals.py: 3 tests) + AMEND-01/02 (test_amendments.py: 6 skip-decorated tests) and frontend RED stub for QUAL-03 (document.test.jsx); closed Phase 16 gap by adding 'default' fallback entry to QUAL_STANDARDS.**

## Performance

- **Duration:** 8 min (7m 22s)
- **Started:** 2026-06-09T14:06:43Z
- **Completed:** 2026-06-09T14:14:05Z
- **Tasks:** 2/2
- **Files modified:** 4 (3 created, 1 modified in Task 1; 1 modified in Task 2)

## Accomplishments

- `v2/backend/tests/test_quals.py` — 3 tests verifying the QUAL_STANDARDS constant contains EC (with degree + policy/analysis language), AS/IT/FI (all non-empty education + experience), and a 'default' fallback. All 3 pass immediately because Phase 16 already populated QUAL_STANDARDS with the data.
- `v2/backend/tests/test_amendments.py` — 6 tests for the not-yet-existing `POST /api/wd/{id}/amendments` and `GET /api/wd/{id}/amendments` endpoints, all decorated with `@pytest.mark.skip(reason="amendments.py not yet implemented — unblock in Wave 2")`. Covers the 201+audit_row happy path, dedup (latest note per section), 404 on non-existent WD, audit_log field shape (event='manager_amendment', actor='advisor', detail has section+comment), invalid section key (422 via Literal validation), and oversized comment (422 via max_length=2000).
- `v2/frontend/src/document.test.jsx` — appended a new `describe('DocumentPane — QUAL-03: Section 5 uses .qual-sub-k class (not inline style)')` block. Test renders DocumentPane with `qualsVisited: true` and asserts `container.innerHTML` contains the literal `qual-sub-k` string. Currently RED (fails) because `document.jsx` Section 5 still uses inline `<b style="...">`. Wave 1 (Plan 02) will extract the inline style into the `.qual-sub-k` CSS class and turn this GREEN.
- `v2/backend/app/data/constants.py` — added the missing `'default'` entry to `QUAL_STANDARDS` dict (Phase 16 gap). Mirrors the frontend `QUAL_DEFAULTS['default']` entry from 19-PATTERNS.md. Without this, the `test_qual_default_fallback` test would fail with `'default' entry missing from QUAL_STANDARDS`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test_quals.py and test_amendments.py RED stubs** - `4fbd243` (test)
2. **Task 2: Extend document.test.jsx with QUAL-03 sub-label stub** - `d0c913c` (test)

## Files Created/Modified

- `v2/backend/tests/test_quals.py` *(new)* — 3 unit tests for QUAL-01; tests the QUAL_STANDARDS constant directly.
- `v2/backend/tests/test_amendments.py` *(new)* — 6 integration test stubs for AMEND-01 + AMEND-02; all decorated with @pytest.mark.skip until Wave 2 wires the amendments.py router.
- `v2/backend/app/data/constants.py` *(modified)* — added 'default' fallback entry to QUAL_STANDARDS dict.
- `v2/frontend/src/document.test.jsx` *(modified)* — appended QUAL-03 describe block to the end of the file.

## Decisions Made

- **Add 'default' entry to QUAL_STANDARDS in Wave 0** rather than defer to Plan 02. The plan's documented interface specifies `QUAL_STANDARDS` should contain a 'default' key, the plan's success criteria explicitly says "3 passing tests confirm QUAL_STANDARDS has EC/AS/IT/FI/default entries", and the frontend `getQualDefault(og_code)` function (to be added in Plan 02) will look up `QUAL_DEFAULTS['default']` as its fallback path. Closing the gap now keeps the test baseline green and removes a hidden landmine for Plan 02.
- **Follow the plan's exact code template for test_quals.py** including the `pytestmark = pytest.mark.asyncio` module-level mark on a file with all-sync tests. The resulting 3 PytestWarning notifications are non-blocking informational warnings only; they don't fail the test, and the plan's expected output (`67 passed, 6 skipped, 0 failed`) was achieved exactly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added 'default' fallback entry to QUAL_STANDARDS**
- **Found during:** Task 1 (running the test suite after creating test_quals.py)
- **Issue:** `test_qual_default_fallback` failed with `AssertionError: 'default' entry missing from QUAL_STANDARDS`. Phase 16 (which added QUAL_STANDARDS) populated only EC/AS/IT/FI keys and left the 'default' fallback unsaid. The plan's documented interface and the frontend's `getQualDefault(og_code)` design both require a 'default' key.
- **Fix:** Added a 'default' entry to QUAL_STANDARDS in `v2/backend/app/data/constants.py`. Text mirrors the frontend `QUAL_DEFAULTS['default']` entry from 19-PATTERNS.md: generic degree/diploma language + generic experience language; source label "TBS Qualification Standards (general fallback)".
- **Files modified:** v2/backend/app/data/constants.py
- **Verification:** `cd v2/backend && python -m pytest tests/ -q` → 67 passed, 6 skipped, 0 failed
- **Committed in:** `4fbd243` (Task 1 commit)

### Minor Documentation Mismatches (informational, no fix)

- **Plan acceptance criteria:** "`grep -c 'pytest.mark.skip' v2/backend/tests/test_amendments.py` outputs 6" → actual output: 7
- **Why:** Line 9 of test_amendments.py contains the string "pytest.mark.skip" in the file-header docstring ("Remove @pytest.mark.skip when amendments.py is wired in api/__init__.py."). The actual count of `@pytest.mark.skip` *decorators* is 6, which is the count that matters functionally. The grep mismatch is a docstring mention, not a real test count discrepancy.
- **Resolution:** No fix needed; the 6 skip-decorated tests are the correct count. Noted here for completeness.

---

**Total deviations:** 1 auto-fixed (1 missing critical functionality)
**Impact on plan:** Minimal. The 'default' entry was implicitly required by the plan's documented interface and the plan's success criteria; the plan just didn't include the code change for it. No scope creep.

## Issues Encountered

- **PytestWarning notifications on 3 sync tests in test_quals.py** — module-level `pytestmark = pytest.mark.asyncio` warns when applied to non-async functions. The plan's code template includes this mark; the warnings are informational only and don't fail the tests. Same pattern is used in test_wd.py and other backend test files. Left as-is to match the plan's exact code.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Plan 02 (Wave 1)** can proceed: it will un-block the QUAL-01/02/03 stubs by wiring `QUAL_DEFAULTS` map + `getQualDefault()` into `data.jsx`, threading `og_code` through `StepInput` to `QualEditor`, adding `touched` state and `onBlur` validation, and extracting the inline style to `.qual-sub-k` CSS class in `document.jsx`.
- **Plan 03 (Wave 2)** can proceed: it will un-skip the 6 amendment stubs by creating `v2/backend/app/api/amendments.py` (POST + GET endpoints following the `jes_service.py` audit_log pattern), including the router in `app/api/__init__.py`, and wiring the frontend amendment panel + state.
- **Plan 04 (Wave 3)** is the integration + UAT gate.

## Test Baseline State

- Backend: 64 passed → 67 passed (3 new QUAL-01 tests); 6 skipped (new AMEND stubs); 0 failed
- Frontend: 30 passed → 30 passed + 1 failed (the intentional QUAL-03 RED stub); 0 regressions
- Total: 97 passed, 6 skipped, 1 expected failure; 0 unexpected failures

---
*Phase: 19-qualifications-amendments*
*Completed: 2026-06-09*

## Self-Check: PASSED

- v2/backend/tests/test_quals.py: FOUND (40 lines, 3 tests)
- v2/backend/tests/test_amendments.py: FOUND (134 lines, 6 skip-decorated tests)
- .planning/phases/19-qualifications-amendments/19-01-SUMMARY.md: FOUND
- Commit 4fbd243: FOUND (Task 1)
- Commit d0c913c: FOUND (Task 2)
