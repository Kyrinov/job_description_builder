---
phase: 21-og-expansion-preview-fix
plan: 02
subsystem: ui,api,data
tags: [css, flexbox, constants, dedup, refactor, docx-export]

# Dependency graph
requires:
  - phase: 21-01
    provides: RED test stubs (test_standard_names_import_from_constants, OGX-01/03/05/07 stubs) and PLAN.md/RESEARCH.md/PATTERNS.md
  - phase: 20
    provides: export_service.py with local NON_EC_STANDARD_NAMES dict and 13-test export suite
  - phase: 13
    provides: styles.css with .doc-scroll rule
provides:
  - .doc-scroll CSS rule with align-items: flex-start — white document page now grows with content instead of stretching
  - export_service.py imports NON_EC_STANDARD_NAMES from app.data.constants — no local dict
  - test_standard_names_import_from_constants (RED at plan 21-01) now PASSES
affects:
  - plan 21-04 (OGX-05/06 JES scoring for new groups) — will rely on the now-consolidated NON_EC_STANDARD_NAMES source
  - any future export change must import NON_EC_STANDARD_NAMES from constants, not define locally

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single source of truth for shared dict constants in app.data.constants (no service-local copies)"
    - "align-items: flex-start on a vertically-scrolling flex container prevents child stretch-overflow"

key-files:
  created: []
  modified:
    - v2/frontend/src/styles.css
    - v2/backend/app/services/export_service.py

key-decisions:
  - "Used `align-items: flex-start` rather than restructuring the .doc-scroll layout — single property change, no risk of regression"
  - "Placed the `from app.data.constants import NON_EC_STANDARD_NAMES` import alphabetically after `from app.db import get_connection` to match the existing import ordering in the file"

patterns-established:
  - "When a constants dict exists in app.data.constants, services must import it rather than re-declare locally — the dual-copy drift between export_service.py and constants.py was a v2.0 phase 20 anti-pattern that this plan eliminates"

requirements-completed: [UI-01, OGX-02]

# Metrics
duration: 2min
completed: 2026-06-10
---

# Phase 21 Plan 02: OG Expansion + Preview Fix — UI-01 + OGX-02 Summary

**CSS preview overflow fix (`align-items: flex-start` on `.doc-scroll`) and `NON_EC_STANDARD_NAMES` consolidation (local dict → `app.data.constants` import) — the two prerequisite cleanups for Phase 21 data work.**

## Performance

- **Duration:** 2 min 10 s
- **Started:** 2026-06-10T21:06:25Z
- **Completed:** 2026-06-10T21:08:35Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- UI-01 closed: white `.doc` paper element now grows with content (no more stretch-overflow into the grey background at any document length)
- OGX-02 closed: `NON_EC_STANDARD_NAMES` now has a single source of truth in `app.data.constants`; `export_service.py` no longer carries a stale local copy
- The Wave 0 RED test `tests/test_export.py::test_standard_names_import_from_constants` (written in plan 21-01) now PASSES — guards against future re-introduction of the dual-copy pattern
- Full `tests/test_export.py` suite: 13/13 GREEN (no regressions in pre-existing export tests)

## Task Commits

1. **Task 1: Add `align-items: flex-start` to `.doc-scroll` (UI-01)** — `ce000d8` (fix)
2. **Task 2: Remove local `NON_EC_STANDARD_NAMES` from `export_service.py` and import from constants (OGX-02)** — `c722763` (refactor)

## Files Modified

- `v2/frontend/src/styles.css` — single property `align-items: flex-start` appended to the existing `.doc-scroll` declaration block at line 551; line count unchanged
- `v2/backend/app/services/export_service.py` — added `from app.data.constants import NON_EC_STANDARD_NAMES` (line 36) and removed the 9-line local dict definition (with its comment header); net change −10/+1 lines

## Decisions Made

None - followed plan as specified. Both changes are mechanical with no design judgment required:
- The CSS fix uses the exact `align-items: flex-start` property value the plan specified (root cause: `align-items` defaults to `stretch` in flex containers, which made `.doc` fill `.doc-scroll`'s height)
- The Python refactor deletes the local dict outright (not commented out) and adds the import in the same commit, per the plan's "intentional deletion, not commented out" guidance

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - both changes were trivial and behaved as predicted.

**Pre-existing failing tests in unrelated files** (not in scope, not caused by this plan):
- `tests/test_constants.py::test_og_constants_completeness` (RED stub for OGX-01/05 from plan 21-01) — fails because `JES_FACTORS_BY_GROUP` does not exist yet; addressed by plan 21-04
- `tests/test_constants.py::test_qual_defaults_parity` (RED stub for OGX-03 from plan 21-01) — fails because QUAL_STANDARDS is missing 12 new group keys; addressed by plan 21-03

## User Setup Required

None - no external service configuration required. Both changes are pure code/data modifications within the existing project.

## Next Phase Readiness

- UI-01 unblocks: any visual / screenshot / browser UAT (the white page now grows correctly)
- OGX-02 unblocks: plan 21-04 (JES scoring for point-rating groups) and any later export work — these plans can rely on a single `NON_EC_STANDARD_NAMES` source
- No blockers carried into plan 21-03

---

*Phase: 21-og-expansion-preview-fix*
*Completed: 2026-06-10*

## Self-Check: PASSED

- ✓ `v2/frontend/src/styles.css` exists and contains `align-items: flex-start` on line 551 (`.doc-scroll` rule)
- ✓ `v2/backend/app/services/export_service.py` exists; import on line 36, zero local `NON_EC_STANDARD_NAMES: dict` definitions
- ✓ `.planning/phases/21-og-expansion-preview-fix/21-02-SUMMARY.md` exists
- ✓ Commit `ce000d8` (Task 1 — CSS fix) present in git log
- ✓ Commit `c722763` (Task 2 — Python consolidation) present in git log
- ✓ `pytest tests/test_export.py -x -q` → 13/13 PASSED (including the previously-RED `test_standard_names_import_from_constants`)
