---
phase: 29-structured-export-enhanced-poster
plan: 01
subsystem: testing
tags: [red-baseline, export, json, csv, poster, tdd-wave-0]

# Dependency graph
requires:
  - phase: 27-responsibilities-narrative-completeness-audit
    provides: build_seven_elements(wd) helper + complete_count contract
  - phase: 28-manager-track-ux
    provides: wd_type field + manager-bypass pattern for export gate
provides:
  - 5 RED backend stubs in test_export.py gating SEXP-01, SEXP-02, SEXP-04, POST-01
  - 2 RED frontend stubs in conversation.test.jsx gating SEXP-03
  - Wave 0 acceptance surface for Plan 29-02 (backend) and Plan 29-03 (frontend)
affects: [plan-29-02-backend-routes, plan-29-03-frontend-buttons]

# Tech tracking
tech-stack:
  added: []
  patterns: [wave-0-red-baseline, fixture-reuse, page-without-route-404-red]

key-files:
  created: []
  modified:
    - v2/backend/tests/test_export.py
    - v2/frontend/src/conversation.test.jsx

key-decisions:
  - "Plan specifies cls={null} for ReviewState stubs but ReviewState reads cls.code unconditionally in advisor mode — auto-fix to minimal valid cls object to preserve RED intent"
  - "screen must be added to existing @testing-library/react import — file imports render/fireEvent/waitFor only"
  - "Each stub is an honest acceptance gate: the route/button truly does not exist, so the test fails on the precise assertion the plan's Wave 1+2 work must satisfy"

patterns-established:
  - "Pattern: backend RED stubs target routes that don't exist (HTTP 404 is the failure mode) — no xfail marker, the assertion on status_code == 200 IS the RED signal"
  - "Pattern: frontend RED stubs target UI elements not yet rendered — queryByText returning null is the failure mode, satisfying plan acceptance criterion (AssertionError, not ReferenceError/SyntaxError)"

requirements-completed: []

# Metrics
duration: ~5min
completed: 2026-06-25
---

# Phase 29 Plan 01: Wave 0 RED Baseline Summary

**5 backend RED stubs (JSON 7-key shape, JSON metadata+provenance, CSV UTF-8-BOM one-row-per-duty, manager-track JSON no-409, poster org_context section) + 2 frontend RED stubs (Export JSON + Export CSV buttons in ReviewState) — 179 backend + 85 frontend pre-existing GREEN preserved as regression floor**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-25T12:13:38Z
- **Completed:** 2026-06-25T12:17:59Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- 5 backend RED stubs appended to `v2/backend/tests/test_export.py` after `test_build_seven_elements_total_seven` (line 954); 4 stubs fail with `AssertionError` on `assert resp.status_code == 200` (routes return 404), 1 stub fails with `AssertionError` on missing `About the Organization` heading in poster DOCX
- 2 frontend RED stubs appended to `v2/frontend/src/conversation.test.jsx` after the MGR-02 inspection test (line 1107); both fail with `AssertionError: expected null not to be null` because `screen.queryByText('Export JSON')` and `screen.queryByText('Export CSV')` return null
- Baseline preserved: 179 pre-existing backend tests remain GREEN; 85 pre-existing frontend tests remain GREEN
- Zero production code touched (per Wave 0 contract: stubs only)

## Task Commits

Each task was committed atomically:

1. **Task 1: 5 RED backend stubs in test_export.py** - `2393f8c` (test)
2. **Task 2: 2 RED frontend stubs in conversation.test.jsx** - `7893596` (test)

## Files Created/Modified

- `v2/backend/tests/test_export.py` — 5 RED stubs appended at end (86 lines added): `test_export_json_returns_all_seven_keys`, `test_export_json_metadata_and_provenance`, `test_export_csv_utf8_bom_one_row_per_duty`, `test_export_json_manager_no_409`, `test_poster_org_context_section`. Uses existing `_create_wd`, `_create_wd_ec`, `_create_wd_with_jes_scores` fixtures.
- `v2/frontend/src/conversation.test.jsx` — 2 RED stubs appended at end + `screen` added to existing `@testing-library/react` import (38 lines added, 1 line modified). Uses existing `ReviewState` import and `render` from `@testing-library/react`.

## Decisions Made

- Followed plan's exact stub bodies for the 5 backend tests (the plan bodies work as-written; routes don't exist, so 404 is the failure mode)
- For frontend stubs: chose Rule 1 auto-fix on `cls={null}` to provide minimal valid `cls={{ code: 'EC-04', points: 250, status: 'resolved' }}` — `ReviewState` reads `cls.code` unconditionally for advisor mode (line 199 of `conversation.jsx`), so passing `null` crashes the render before the button assertion runs. This violates the plan's acceptance criterion that tests fail with `AssertionError`, not `TypeError`.
- For frontend stubs: chose Rule 1 auto-fix on missing `screen` import — added `screen` to existing `import { render, fireEvent, screen, waitFor } from '@testing-library/react'` (the plan body uses `screen.queryByText` but the file did not import `screen` previously). Adding it to the existing import is the minimum diff that satisfies the plan's stated code.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Replaced `cls={null}` with minimal valid `cls` object in 2 frontend stubs**
- **Found during:** Task 2 (frontend stubs verification)
- **Issue:** Plan body uses `cls={null}`, but `ReviewState` for advisor mode (default `userRole='advisor'`) reads `cls.code` unconditionally at line 199 of `conversation.jsx`. The render crashes with `TypeError: Cannot read properties of null (reading 'code')` BEFORE the button assertion runs, violating the plan's explicit acceptance criterion: *"The 2 failing tests fail with 'expect(received).not.toBeNull()' where received is null — NOT with ReferenceError or SyntaxError"*. Both tests are RED for the wrong reason.
- **Fix:** Replaced `cls={null}` with `cls={{ code: 'EC-04', points: 250, status: 'resolved' }}` (matches the shape used by existing MGR-02 tests at lines 994 and 1015 of conversation.test.jsx). Now the render succeeds and the missing-button assertion is the failure mode — satisfying the acceptance criterion.
- **Files modified:** `v2/frontend/src/conversation.test.jsx`
- **Verification:** `npm test -- conversation` shows `AssertionError: expected null not to be null` on both stubs, not `TypeError`. Pre-existing 85 frontend tests still GREEN.
- **Committed in:** `7893596` (part of Task 2 commit)

**2. [Rule 1 - Bug] Added `screen` to existing `@testing-library/react` import**
- **Found during:** Task 2 (frontend stubs verification)
- **Issue:** Plan body uses `screen.queryByText('Export JSON')` and `screen.queryByText('Export CSV')`, but `conversation.test.jsx` imports only `{ render, fireEvent, waitFor }` — `screen` is not in scope. After Rule 1 fix #1 unblocked the render path, the stubs then crashed with `TypeError: screen.queryByText is not a function`. The plan acknowledges this risk in its IMPORTANT block ("check the imports at the top of conversation.test.jsx before appending") but doesn't specify the fix.
- **Fix:** Added `screen` to the existing destructured import: `import { render, fireEvent, screen, waitFor } from '@testing-library/react';` — minimum diff that brings `screen` into scope.
- **Files modified:** `v2/frontend/src/conversation.test.jsx`
- **Verification:** Both stubs now fail at the `expect(btn).not.toBeNull()` assertion with `expected null not to be null`.
- **Committed in:** `7893596` (part of Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 bug fixes — preserve plan's RED intent while satisfying acceptance criterion)

**Impact on plan:** Both auto-fixes necessary for the RED stubs to fail at the assertion (as the plan specifies) instead of crashing on import or render. No scope creep, no production code touched.

## Issues Encountered

None — plan execution proceeded smoothly. The 2 deviations were caught during the verification step (running the test suite) and fixed inline before commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 29-02 (Wave 1 backend) is unblocked — implementation order from PLAN.md: `/export/json` route (gates `test_export_json_returns_all_seven_keys` + `test_export_json_metadata_and_provenance` + `test_export_json_manager_no_409`) → `/export/csv` route (gates `test_export_csv_utf8_bom_one_row_per_duty`) → poster DOCX `About the Organization` section (gates `test_poster_org_context_section`)
- Plan 29-03 (Wave 2 frontend) is unblocked — gates `Export JSON` and `Export CSV` buttons inside `ReviewState`'s `.export-row` (currently has DOCX/PDF/Copy; need to add 2 more without disturbing completeness-soft-gate invariant locked by Phase 27 Plan 02)
- `build_seven_elements(wd)` helper from Phase 27 is the natural data source for the JSON export route — already returns `{key, label, status, value}` per element, total 7 keys
- manager-bypass pattern from Phase 28 Plan 01 (gate check `wd.wd_type == 'manager'`) applies to the new JSON/CSV export routes — manager JSON stub asserts `data["classification"]["og_level"] == "[ADVISOR TO COMPLETE]"`

---

*Phase: 29-structured-export-enhanced-poster*
*Completed: 2026-06-25*
