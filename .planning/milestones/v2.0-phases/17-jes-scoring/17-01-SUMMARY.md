---
phase: 17-jes-scoring
plan: 01
subsystem: jes-scoring
tags: [backend, frontend, data-model, tdd-red]
requires: [phase-16]
provides:
  - EC_JES_ELEMENTS constant
  - EC_DEGREES constant
  - NON_EC_TOTALS constant
  - NON_EC_STANDARD_NAMES constant
  - jes_scores-field on WorkDescription
  - jes_total_points-field on WorkDescription
  - jes_scores-field on WDPatchRequest
  - jes_total_points-field on WDPatchRequest
  - jes-scoring-test-contract
affects: [17-02, 17-03, 17-04, 18-jd-composition, 19-qualifications, 20-export]
tech-stack:
  added: []
  patterns: [wave-0-red-stubs, verbatim-source-text, hardcoded-constants]
key-files:
  created:
    - v2/backend/tests/test_jes_scoring.py
    - v2/frontend/src/document.test.jsx
  modified:
    - v2/backend/app/data/constants.py
    - v2/backend/app/models/work_description.py
    - v2/backend/app/api/wd.py
key-decisions:
  - "EC_JES_ELEMENTS, EC_DEGREES, NON_EC_TOTALS, NON_EC_STANDARD_NAMES sourced verbatim from Job Description Builder/jd-builder/data.jsx (lines 79-88, 93-120) — Phase 16 precedent of verbatim source text"
  - "WorkDescription.jes_scores typed as list[dict] with default_factory=list (NOT Optional[list]); jes_total_points as Optional[int] = None — matches confirmed_og Optional[dict] pattern"
  - "WDPatchRequest.jes_scores as Optional[list[dict]] = None; WDPatchRequest.jes_total_points as Optional[int] = None — required for PATCH merge via setattr(model_dump(exclude_unset=True))"
  - "No changes needed to the PATCH handler in wd.py — generic for-loop over body.model_dump(exclude_unset=True) already handles the new fields transparently"
  - "Test count: 8 backend stubs (4 unit + 4 integration) instead of the 6 minimum noted in VALIDATION.md — provides complete coverage for all 5 JES/API requirements without gaps (matches plan body note)"
  - "ClassBlock RED stubs use top-level await import with try/catch to capture the 'ClassBlock not yet exported' state — this is the only way to make vitest fail RED (since dynamic import failure inside a beforeAll can hang); each test then re-checks ClassBlock truthiness to produce a deterministic RED error"
requirements-completed:
  - JES-01
  - JES-02
  - JES-03
  - JES-04
  - API-07
duration: ~5 min
completed: 2026-06-05T16:55:00Z
---

# Phase 17 Plan 01: JES Constants + Model Extension + RED Stubs Summary

Wave 0 of 4 for Phase 17. Establishes the JES scoring data foundations, model extensions, and RED test contract before any service or route work in Plans 02/03.

## One-liner

Added 4 JES constants (EC_JES_ELEMENTS 9-factor scale, EC_DEGREES EC-04/05/06 vectors, NON_EC_TOTALS FI/IT/AS/EN level totals, NON_EC_STANDARD_NAMES verbatim standard labels) sourced verbatim from data.jsx; extended WorkDescription and WDPatchRequest with jes_scores/jes_total_points fields; created 8 RED backend test stubs + 2 RED frontend ClassBlock stubs.

## Tasks completed

- **Task 1**: Added `EC_JES_ELEMENTS` (9 entries with name/category/pts dict), `EC_DEGREES` (3 keys: EC-04/05/06 with 9-element int lists), `NON_EC_TOTALS` (4 keys: FI/IT/AS/EN with level→points dicts), `NON_EC_STANDARD_NAMES` (4 keys: FI/IT/AS/EN with verbatim standard names from data.jsx WORK_TYPES). Extended `WorkDescription` with `jes_scores: list[dict] = Field(default_factory=list)` and `jes_total_points: Optional[int] = None`. Extended `WDPatchRequest` with `jes_scores: Optional[list[dict]] = None` and `jes_total_points: Optional[int] = None`. The existing PATCH handler (generic `for field, val in body.model_dump(exclude_unset=True).items(): setattr(wd, field, val)`) merges the new fields automatically — no code change required in the handler.
- **Task 2**: Created `v2/backend/tests/test_jes_scoring.py` with 8 RED stubs (4 unit + 4 integration), all using `pytest.fail("RED — not implemented")` for deterministic failure. Created `v2/frontend/src/document.test.jsx` with 2 RED ClassBlock render stubs (EC per-factor rows + non-EC single totals line). The frontend file uses `await import('./document.jsx')` with a try/catch to capture the "ClassBlock not yet exported" state — each test then re-checks `ClassBlock` truthiness and throws a clear RED error.

## Test results

- `tests/test_jes_scoring.py` — 8 FAILED (all "Failed: RED — not implemented"), 0 errors. Confirms all stubs are RED as required by Wave 0 setup.
- `tests/ --ignore=test_jes_scoring.py` — 50 PASSED, 0 FAILED. No regressions from the WorkDescription model extension (existing WDPatchRequest tests still green because `extra="ignore"` on WorkDescription transparently accepts the new fields).
- `npx vitest run src/document.test.jsx` — 2 FAILED (both "RED — ClassBlock not exported from document.jsx"). Confirms the import-time fallback pattern works as intended.

## Verification commands run

- `python3 -c "from app.data.constants import EC_JES_ELEMENTS, EC_DEGREES, NON_EC_TOTALS, NON_EC_STANDARD_NAMES; assert len(EC_JES_ELEMENTS)==9"` exits 0
- `python3 -c "from app.models.work_description import WorkDescription; ..."` exits 0 with `wd.jes_scores==[]` and `wd.jes_total_points is None`
- `python3 -m pytest tests/test_jes_scoring.py -q` shows 8 FAILED 0 error
- `python3 -m pytest tests/ -q --ignore=tests/test_jes_scoring.py` shows 50 passed
- `grep -c "EC_JES_ELEMENTS" app/data/constants.py` returns 3 (definition + 1 docstring + comments)
- `grep -c "EC_DEGREES" app/data/constants.py` returns 3
- `grep -c "NON_EC_TOTALS" app/data/constants.py` returns 2
- `grep -c "NON_EC_STANDARD_NAMES" app/data/constants.py` returns 2

## Deviations from Plan

- **None substantive.** All task actions executed as written. The only nuance: 8 RED backend stubs were created (not 6) per the plan body's own note — "that is 8 stubs (4 unit + 4 integration). The 6-stub count in VALIDATION.md was a minimum; 8 provides complete coverage for all 5 requirements without gaps." VALIDATION.md still shows the 6-minimum (4 unit + 2 integration in its table), and 8 ⊇ 6 is compliant.

## Self-Check: PASSED

- [x] `v2/backend/app/data/constants.py` contains all 4 new constants (EC_JES_ELEMENTS, EC_DEGREES, NON_EC_TOTALS, NON_EC_STANDARD_NAMES)
- [x] `v2/backend/app/models/work_description.py` contains `jes_scores: list[dict] = Field(default_factory=list)` and `jes_total_points: Optional[int] = None`
- [x] `v2/backend/app/api/wd.py` contains `jes_scores: Optional[list[dict]] = None` and `jes_total_points: Optional[int] = None`
- [x] `v2/backend/tests/test_jes_scoring.py` exists with 8 RED stubs (all failing with pytest.fail)
- [x] `v2/frontend/src/document.test.jsx` exists with ClassBlock render stubs (all failing RED)
- [x] Commit `51eda83` (feat) exists
- [x] Commit `a384b1f` (test) exists
- [x] 50 existing backend tests still pass (no regressions)
- [x] STATE.md and ROADMAP.md NOT modified (orchestrator owns those writes)

## Next

Plan 17-02: implement the JES scoring service (`app/services/jes_service.py` with port of v1.0 `score_jes()` + `override_jes_factor()`), the instructor wrapper (`app/ai/jes_scoring.py`), and the `POST /api/jes/score` + `POST /api/jes/override/{wd_id}/{factor_name}` routes — turns the 4 integration RED stubs GREEN.
