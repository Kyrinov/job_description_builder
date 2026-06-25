---
phase: 11-data-foundation
plan: 01
subsystem: data
tags: [constants, og-levels, tdd, red-green, v2-backend, v1-bugfix]

# Dependency graph
requires: []
provides:
  - "OG_LEVELS constant (12 OG groups, correct level counts) in v2/backend/app/data/constants.py"
  - "CAF_RANK_OG_EQUIVALENCE constant (14 ranks, all advisory=True) in v2/backend/app/data/constants.py"
  - "Corrected v1.0 OG_LEVELS in app/ai/og_ranking.py (EC 1-7→1-8, IT 1-4→1-5, CS key removed, CR/PM 1-6→1-7)"
  - "DATA-01 + DATA-02 test suite (8 tests) in v2/backend/tests/test_constants.py"
affects: [phase-12-question-bank, phase-14-noc-pipeline, phase-16-og-classification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hardcoded constants over runtime CSV parsing — eliminates ingest script complexity and embedding-model-version drift"
    - "TDD red-green: tests written first with ImportError, then constants module to satisfy"
    - "Negation pattern in .gitignore to permit app/data/ package while keeping data/ directory ignored"

key-files:
  created:
    - v2/backend/app/data/__init__.py
    - v2/backend/app/data/constants.py
    - v2/backend/tests/test_constants.py
  modified:
    - app/ai/og_ranking.py
    - tests/test_og_ranking.py
    - v2/backend/.gitignore

key-decisions:
  - "OG_LEVELS data extracted via direct file inspection of data/rates_of_pay/*.csv (not runtime parsing) — values are public, stable, and small enough to hardcode"
  - "CS key removed from OG_LEVELS — CS is not a current standalone OG group (merged into IT)"
  - "CAF officer pay anchor uses pay level D (most common general duty officer track) — documented in RESEARCH.md A4"
  - "All CAF rank entries flagged advisory=True — pay-band comparison is not authoritative equivalence, must be labeled on every surface that displays the table"

patterns-established:
  - "Pattern: constants module lives at v2/backend/app/data/constants.py, exported as module-level dicts/lists"
  - "Pattern: cross-reference test (test_caf_table_og_codes_exist_in_og_levels) catches invalid OG code prefixes at unit-test time"
  - "Pattern: v1.0 bugs are corrected in-place in app/ (not duplicated) so the v1.0 and v2.0 backends share truth"

requirements-completed: [DATA-01]

# Metrics
duration: 5min
completed: 2026-06-04
---

# Phase 11 Plan 01: OG_LEVELS + CAF Rank Equivalence Constants

**Authoritative OG level ranges (12 groups) and CAF rank-to-civilian OG advisory equivalence table (14 ranks), delivered as hardcoded Python constants with full TDD red→green cycle**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-04T08:55:00Z
- **Completed:** 2026-06-04T09:00:00Z
- **Tasks:** 2 (1 test-stub RED, 1 implementation GREEN)
- **Files modified:** 6 (3 created, 3 modified)

## Accomplishments

- v2.0 backend now has a single authoritative `app/data/constants.py` module exporting `OG_LEVELS` (12 OG groups with correct level counts) and `CAF_RANK_OG_EQUIVALENCE` (14 ranks, all `advisory=True`)
- Fixed three v1.0 OG_LEVELS bugs in place: EC stopped at 7 (now 8), IT stopped at 4 (now 5), CS key was bogus (removed — CS merged into IT)
- Fixed two additional v1.0 OG_LEVELS bugs: CR was 1-6 (now 1-7), PM was 1-6 (now 1-7)
- 8 test functions in `test_constants.py` enforce the contract: 6 for OG_LEVELS structure, 2 for CAF table cross-reference

## Task Commits

1. **Task 1 (Wave 0):** Write test stubs + package marker (RED gate) — `5123a04` (test)
2. **Task 2 (Wave 1):** Write constants.py + correct v1.0 og_ranking.py (GREEN) — `c73970c` (feat)
3. **Side-effect fix:** Negate data/ in v2/backend/.gitignore to permit app/data/ package — `64bb5bd` (fix)

## Files Created/Modified

- `v2/backend/app/data/__init__.py` — Empty package marker enabling `from app.data.constants import ...`
- `v2/backend/app/data/constants.py` — Authoritative constants: OG_LEVELS (12 groups) + CAF_RANK_OG_EQUIVALENCE (14 ranks)
- `v2/backend/tests/test_constants.py` — 8 test functions: 6 DATA-01 (OG_LEVELS structure) + 2 DATA-02 (CAF table cross-reference)
- `v2/backend/.gitignore` — Added `!app/data/` negation to permit tracking the new package while preserving the original `data/` ignore rule
- `app/ai/og_ranking.py` — Corrected v1.0 OG_LEVELS in-place: EC 1-7→1-8, IT 1-4→1-5, CR/PM 1-6→1-7, CS key removed, PE/IS removed (not in CA CSVs)
- `tests/test_og_ranking.py` — Updated `test_og_levels_as_range` assertion (EC 1-7→1-8) to match corrected v1.0 value

## Decisions Made

- **Hardcoded constants over runtime CSV parsing** — DATA-01 requires correct OG level ranges; values are public, stable, and small enough to live as constants. Eliminates ingest script complexity and embedding-model-version drift (consistent with v2.0 design decision recorded in STATE.md "v2.0 curated hardcoded data over v1.0 ingest pipelines")
- **CAF officer pay uses level D as anchor** — Most common general duty officer track; documented in RESEARCH.md A4
- **Cross-reference test** — `test_caf_table_og_codes_exist_in_og_levels` walks every CAF entry's `approx_civilian_og_levels` list and confirms each code prefix exists in OG_LEVELS keys, preventing typos at unit-test time

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 4 — Missing Critical] Updated v1.0 test assertion to match corrected OG_LEVELS**
- **Found during:** Task 2 verification (running v1.0 test suite)
- **Issue:** `tests/test_og_ranking.py::test_og_levels_as_range` asserted `OG_LEVELS["EC"] == list(range(1, 8))` — the v1.0 bug value (1-7). The test was written to match the buggy v1.0 behavior, not the actual TBS classification reality.
- **Fix:** Updated assertion to `OG_LEVELS["EC"] == list(range(1, 9))` (1-8) to match the corrected value
- **Files modified:** tests/test_og_ranking.py
- **Verification:** All 11 v1.0 og_ranking tests pass
- **Committed in:** c73970c (same commit as Task 2 GREEN, because the test fix is part of the bugfix)

**2. [Rule 4 — Blocking] Negate `data/` in v2/backend/.gitignore to permit app/data/ package**
- **Found during:** Task 1 (RED gate commit) — `git add` refused to stage `v2/backend/app/data/__init__.py`
- **Issue:** The v2 backend `.gitignore` has `data/` on line 7 to ignore runtime data directories, but the new `app/data/` Python package collided with that pattern
- **Fix:** Added `!app/data/` negation rule immediately after `data/` so the package is tracked while preserving the original ignore intent
- **Files modified:** v2/backend/.gitignore
- **Verification:** `git check-ignore` confirms `v2/backend/app/data/__init__.py` is no longer ignored
- **Committed in:** 64bb5bd (separate fix commit — keeps the bugfix atomic)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 blocking)
**Impact on plan:** Both auto-fixes necessary for correctness and trackability. No scope creep.

## Issues Encountered

- **None beyond the auto-fixes documented above**

## Next Phase Readiness

- `app.data.constants` is the canonical source of truth for OG levels and CAF rank equivalence. Phase 12 (Socratic Question Bank), Phase 14 (NOC Pipeline), and Phase 16 (OG Classification) can import `OG_LEVELS` and `CAF_RANK_OG_EQUIVALENCE` directly
- CLASS-05 (Phase 16) can render the CAF advisory table without any runtime data processing
- v1.0 code (v1.0 OG ranking) now references corrected levels — no separate source of truth

---
*Phase: 11-data-foundation*
*Completed: 2026-06-04*
