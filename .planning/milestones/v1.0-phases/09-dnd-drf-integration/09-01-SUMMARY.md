---
phase: 09-dnd-drf-integration
plan: 01
subsystem: testing
tags: [pydantic, sqlite, drf, fixture, tdd]

# Dependency graph
requires: []
provides:
  - "WorkDescription model extended with is_dnd_position + drf_linkages fields"
  - "DRF_SCHEMA_DDL constant + drf_rows table created in create_schema()"
  - "tests/test_drf.py with 9 skipping test stubs covering DRF-01 acceptance surface"
  - "drf_db pytest fixture for Phase 9 test isolation"
affects: [09-02, 09-03, 09-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic default_factory=list for additive-optional list[dict] fields"
    - "Per-phase test module uses rebootstrap pattern (module-level global + autouse fixture)"
    - "Test stubs skip cleanly on missing app modules (defensive ImportError handling)"

key-files:
  created:
    - tests/test_drf.py
  modified:
    - app/models/work_description.py
    - app/db.py
    - tests/conftest.py

key-decisions:
  - "is_dnd_position + drf_linkages are additive-optional (defaults safe for legacy rows); schema_version stays at 1"
  - "drf_rows table uses UNIQUE(fiscal_year, core_responsibility, departmental_result) to enforce canonical triples from dnd_drf_dataset.csv"
  - "Test stubs are skipped (not errored) so the suite stays green until 09-02/09-03/09-04 land"

requirements-completed: [DRF-01]

# Metrics
duration: 15min
completed: 2026-06-03
---

# Phase 9 Plan 01: DND DRF Foundation Summary

**WorkDescription model extended with DND position flags, drf_rows SQLite table with matching schema DDL, and 9-test DRF-01 acceptance surface (all skipping) defined before any implementation ships**

## Performance

- **Duration:** 15 min
- **Started:** 2026-06-03T12:05:30Z
- **Completed:** 2026-06-03T12:21:00Z
- **Tasks:** 3 (1 TDD = RED + GREEN)
- **Files modified:** 3 (1 created, 3 modified, 1 fixture appended)

## Accomplishments

- WorkDescription model gains `is_dnd_position: bool = False` and `drf_linkages: list[dict] = Field(default_factory=list)` — every downstream Phase 9 plan reads/writes through these fields
- `app.db` exports `DRF_SCHEMA_DDL` constant and `create_schema()` now creates the `drf_rows` table + `idx_drf_rows_cr` index on every startup (idempotent)
- `tests/test_drf.py` defines the DRF-01 acceptance surface (9 test functions across 5 test classes) before any service/router code lands — TDD contract
- `drf_db` fixture in `tests/conftest.py` provides a fresh SQLite DB for Phase 9 tests, mirroring the `export_db` pattern
- TDD discipline maintained: failing test committed first (`3a1f74b`), then GREEN implementation (`904e59d`) — RED gate, GREEN gate visible in git log

## Task Commits

Each task was committed atomically:

1. **Task 1 (TDD RED):** Add failing test for new model fields — `3a1f74b` (test)
2. **Task 1 (TDD GREEN):** Add is_dnd_position + drf_linkages to WorkDescription — `904e59d` (feat)
3. **Task 2:** Add DRF_SCHEMA_DDL to db.py and register in create_schema() — `f84e9e5` (feat)
4. **Task 3:** Create test_drf.py stubs + drf_db fixture — `c62711a` (feat)

## Files Created/Modified

- `app/models/work_description.py` — Two new fields appended after `exported_at` (last existing field) with explanatory comment block
- `app/db.py` — New `DRF_SCHEMA_DDL` constant (drf_rows + idx_drf_rows_cr); `create_schema()` executes the script after `NOC_MAPPING_SCHEMA_DDL`; docstring updated
- `tests/conftest.py` — New `drf_db` fixture (mirrors `export_db` pattern)
- `tests/test_drf.py` — New file: 9 skipping test stubs across 5 test classes (TestGetDRFLinks, TestConfirmDRFLinks, TestDRFMatchingService, TestDRFExport, TestDRFWizardStep)

## Decisions Made

- **Additive-optional fields, no schema_version bump.** `is_dnd_position=False` and `drf_linkages=[]` defaults make the new fields backward-compatible with existing rows in `work_descriptions.data` (JSON). The Phase 1 schema_version=1 invariant holds.
- **UNIQUE constraint on (fiscal_year, core_responsibility, departmental_result).** The DRF ingest script (Plan 09-02) is expected to populate one row per canonical triple; the unique constraint prevents duplicates if the CSV has multiple instances of the same triple.
- **search_text column denormalized at ingest time.** The lowercase concat of `core_responsibility + ' ' + departmental_result` lives in the table so the matching service (Plan 09-02) can do simple keyword overlap without reconstructing it on every query.
- **Test module uses `_drf_app_bootstrapped` global** (not `_app_bootstrapped`) to avoid collision with `test_jes_scoring.py` and `test_export.py` rebootstrap globals — pytest modules share `sys.modules` so a single global would race between test files in the same `pytest` run.
- **Each test stub has its own `_set_env` + `_clear_app_modules` block** even though the autouse fixture also does it. Mirrors the pattern in `test_jes_scoring.py` — the explicit block in each test gives the test body full control over env state without relying on autouse ordering.

## Deviations from Plan

None — plan executed exactly as written. All three tasks followed the prescribed actions, the verification commands all returned the expected output, and no auto-fixes (Rules 1-3) were required.

## Issues Encountered

None.

## TDD Gate Compliance

Verified in git log:
- `3a1f74b` (test): RED gate — failing test for `is_dnd_position` + `drf_linkages` defaults and settability
- `904e59d` (feat): GREEN gate — fields added; both tests now pass
- No REFACTOR commit needed (implementation is two lines + comment)

## User Setup Required

None — no external service configuration required for the foundation.

## Next Phase Readiness

- **09-02 (DRF ingest + matching service)** is unblocked: `drf_rows` table exists, `WorkDescription.is_dnd_position` is queryable, and `tests/test_drf.py::TestDRFMatchingService` defines the matching acceptance test
- **09-03 (API routes)** is unblocked: `tests/test_drf.py::TestGetDRFLinks` and `TestConfirmDRFLinks` define the router acceptance surface
- **09-04 (wizard step + DOCX section)** is unblocked: `tests/test_drf.py::TestDRFExport` and `TestDRFWizardStep` define the wizard + export acceptance surface

Full suite: 180 passed, 10 skipped (was 1 pre-existing skip + 9 new DRF stubs), 0 regressions.

---
*Phase: 09-dnd-drf-integration*
*Completed: 2026-06-03*

## Self-Check: PASSED

- `.planning/phases/09-dnd-drf-integration/09-01-SUMMARY.md` exists
- `3a1f74b` (test) — RED gate commit exists
- `904e59d` (feat) — GREEN gate commit exists
- `f84e9e5` (feat) — DRF_SCHEMA_DDL commit exists
- `c62711a` (feat) — test_drf.py + drf_db fixture commit exists
- Full suite: 180 passed, 10 skipped, 0 regressions
