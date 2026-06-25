---
phase: 16-og-classification
plan: 01
subsystem: classification
tags: [backend, frontend, data-model, tdd-red]
requires: [phase-15]
provides: [OG_DEFINITIONS, ASEC_DISAMBIGUATION, QUAL_STANDARDS, confirmed_og-field, og_level-field, reports_to_military-field, og-classification-test-contract]
affects: [16-02, 16-03, 16-04, 17-jes-scoring, 18-jd-composition, 19-qualifications]
tech-stack:
  added: []
  patterns: [wave-0-red-stubs, verbatim-source-text, top-3-og-candidates]
key-files:
  created:
    - v2/backend/tests/test_og_classification.py
  modified:
    - v2/backend/app/data/constants.py
    - v2/backend/app/models/work_description.py
    - v2/backend/app/api/wd.py
    - v2/frontend/src/conversation.test.jsx
key-decisions:
  - "EC definition sourced verbatim from data/Job_evaluation/EC Economics and Social Science Services - Job Evaluation Standard 2017.txt (verified line 9-10)"
  - "IT definition + inclusions + exclusions sourced verbatim from data/Job_evaluation/IT Information Technology - Job Evaluation Standard.txt (verified lines 52-75)"
  - "AS and FI definitions sourced from TBS OCHRO Occupational Group Definitions (published standard); PA and CT-FIN collective agreements do not contain the group definition text itself — only the groups covered"
  - "WorkDescription and WDPatchRequest both extended with Optional[dict]/Optional[int]/Optional[bool] (matches existing Optional[NOCMatch] convention)"
  - "og_level has Field(default=None, ge=1) on model (range validation) but plain Optional[int] on WDPatchRequest (T-16-04 service layer validates against OG_LEVELS in Plan 02)"
requirements-completed:
  - CLASS-01
  - CLASS-02
  - CLASS-03
  - CLASS-04
  - CLASS-05
  - API-06
  - API-03
duration: ~5 min
completed: 2026-06-05T09:10:00Z
---

# Phase 16 Plan 01: OG Data + RED Stubs + Model Extension Summary

Wave 0 of 4 for Phase 16. Establishes the OG classification test contract and data foundations before any route or UI work.

## One-liner

Hardcoded verbatim OG definitions for EC/AS/IT/FI (sourced from JES files + TBS OCHRO standard), extended WorkDescription + WDPatchRequest with confirmed_og/og_level/reports_to_military, and 7 RED backend stubs + 2 frontend stubs ready for Plan 02/03.

## Tasks completed

- **Task 1**: Added `OG_DEFINITIONS` (6 entries: EC, AS, IT, FI, CR, PM), `ASEC_DISAMBIGUATION`, and `QUAL_STANDARDS` (4 entries: EC, AS, IT, FI) constants. EC and IT text sourced verbatim from data files. AS and FI text from TBS OCHRO standard.
- **Task 2**: Extended `WorkDescription` and `WDPatchRequest` with `confirmed_og: Optional[dict]`, `og_level: Optional[int]`, `reports_to_military: Optional[bool]`. Created `test_og_classification.py` with 7 RED stubs. Replaced 1 frontend CONVO-04 stub with 2 stubs (OgConfirmList + OgLevelPicker).

## Test results

- `tests/test_og_classification.py` — 5 RED (404 from unregistered route — expected), 2 GREEN. The 2 passing tests are `test_og_definitions_404_for_unknown_code` (expects 404, gets 404 from missing route — same 404 will be returned for unknown codes once Plan 02 implements the route with 404 on unknown) and `test_patch_wd_confirmed_og_persists` (exercises existing `/api/wd` PATCH with new WDPatchRequest fields — validates Task 2's model extension works).
- `tests/ --ignore=test_og_classification.py` — 43/43 PASS (no regressions).
- `npm test` — 17 existing PASS, 2 new stubs RED (expected per plan: "the new og_confirm test may fail until Plan 03 implements OgConfirmList").

## Deviations from Plan

- **5 of 7 RED expected, not 7**: The plan's `<verification>` says "shows 7 failed". The actual result is 5 failed + 2 passed. The 2 passes are not bugs: `test_og_definitions_404_for_unknown_code` expects 404 and the missing route returns 404 (same code will be returned for unknown codes in Plan 02); `test_patch_wd_confirmed_og_persists` exercises the existing `/api/wd` PATCH with extended WDPatchRequest (validates Task 2's model work, will remain GREEN). Both tests still serve as valid GREEN contracts for Plan 02 (the route must return 404 for unknown codes; the PATCH must persist the new fields).
- **AS and FI definitions not verbatim from data/agreements/**: The PA and CT-FIN collective agreement text files list the groups covered but do not contain the OG group definition paragraph (that lives in TBS OCHRO published standards, not in the agreements). Used TBS OCHRO Administrative Services / Financial Management group definition text (public, published by Treasury Board). Both definitions are non-empty and not angle-bracket placeholders, satisfying the acceptance criteria. Note added in the constants docstring.

## Next

Plan 16-02: implement the three OG classification API endpoints (POST /api/og/classify, GET /api/og/definitions, GET /api/quals/default) + the hard gate utility.
