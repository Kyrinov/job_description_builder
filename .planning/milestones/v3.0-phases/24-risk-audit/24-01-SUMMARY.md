---
phase: 24-risk-audit
plan: 01
subsystem: testing
tags: [pytest, tdd, red-baseline, audit, cba, err]

# Dependency graph
requires:
  - phase: 23-writing-guide-integration
    provides: test_writing_guide.py structural template, conftest.py fixtures (client, env_with_db), duty_validator.py stub pattern
provides:
  - risk_auditor.py stub module (run_audit, load_cba_data, AuditFinding) with OG_AGREEMENT_DIR and ERR constants
  - test_risk_audit.py with 10 RED test stubs covering AUDIT-01 through AUDIT-05
  - RED baseline: 5 AssertionError failures establishing test surface for Plans 02/03/04
affects: [24-02, 24-03, 24-04, phase-25]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deterministic rule matching in app/services/* (no LLM in audit path)"
    - "AuditFinding dataclass with Literal['id','ov','du','cls','q','drf'] section key (matches amendment panel keys)"
    - "OG_AGREEMENT_DIR maps 20 OG codes to agreement subdirectories in data/agreements/"

key-files:
  created:
    - v2/backend/app/services/risk_auditor.py
    - v2/backend/tests/test_risk_audit.py

key-decisions:
  - "Wave 0 scaffold pattern: stub module created BEFORE tests so RED tests fail on assertions (not ImportError)"
  - "OG_AGREEMENT_DIR explicitly excludes NT and ED with comment — CBA checks skipped for unmapped groups"
  - "ERR_MIN_DUTY_COUNT=3 (Cushnie) and ERR_SPECIFICITY_THRESHOLD=0.5 (Dervin/Trépanier) as module-level constants for Plan 02 reference"
  - "test_two_signal_false_positive uses pytest.skip when cba_data is None — graceful degradation until load_cba_data is implemented"

patterns-established:
  - "Pattern: stub service exports run_X, load_X, and Finding dataclass — tests import all three and assert on results"
  - "Pattern: integration tests for endpoints gated on (client, env_with_db) fixtures from conftest.py; pytestmark = pytest.mark.asyncio at module level"
  - "Pattern: test_audit_404 passes accidentally because FastAPI returns 404 for unknown routes — this will tighten to a specific assertion message in Plan 02"

requirements-completed: []  # Wave 0 scaffold — no AUDIT-01..05 requirements validated yet (intentional; Plans 02/03/04 implement them)

# Metrics
duration: 2min
completed: 2026-06-15
---

# Phase 24 Plan 01: Risk Audit RED Baseline Summary

**Wave 0 TDD scaffold for Phase 24: stub `risk_auditor.py` module + 10 RED test stubs establishing the test surface for CBA + ERR compliance audit requirements AUDIT-01 through AUDIT-05.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-15T18:31:32Z
- **Completed:** 2026-06-15T18:33:21Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `v2/backend/app/services/risk_auditor.py` stub with `run_audit()`, `load_cba_data()`, and `AuditFinding` dataclass — all imports succeed, all stubs return empty results
- Created `v2/backend/tests/test_risk_audit.py` with 10 test functions covering AUDIT-01 (3 tests), AUDIT-02 (2 tests), AUDIT-03 (3 tests), AUDIT-04 (1 test), AUDIT-05 (1 test)
- Confirmed RED baseline: **5 tests fail with AssertionError** (not ImportError), 4 tests pass (clean WD, unmapped OG, valid section key, 404 coincidence), 1 test skipped (CBA loader await)
- Verified **no regressions**: 134 pre-existing tests still pass; 138 total passing (134 prior + 4 new)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write stub risk_auditor.py module** - `f7dc28c` (feat)
2. **Task 2: Write 10 RED test stubs in test_risk_audit.py** - `1bd68cc` (test)

## Files Created/Modified

- `v2/backend/app/services/risk_auditor.py` — Stub service module exporting `run_audit`, `load_cba_data`, `AuditFinding` dataclass, `OG_AGREEMENT_DIR` constant (20 OG codes), `ERR_MIN_DUTY_COUNT=3`, `ERR_SPECIFICITY_THRESHOLD=0.5`. Stubs return `[]` and `None` respectively.
- `v2/backend/tests/test_risk_audit.py` — 10 test functions (6 unit + 4 integration). 5 currently fail (RED baseline for Plan 02 to GREEN).

## Test Status (RED Baseline)

| Test | Type | Status | Notes |
|------|------|--------|-------|
| `test_err_duty_coverage` | Unit (AUDIT-03) | **RED** | Plan 02 implements ERR_DUTY_COVERAGE rule |
| `test_err_duty_specificity` | Unit (AUDIT-03) | **RED** | Plan 02 implements ERR_DUTY_SPECIFICITY rule |
| `test_zero_findings_clean_wd` | Unit (AUDIT-01) | GREEN | Stub already returns `[]` for clean WD |
| `test_load_cba_unmapped_og` | Unit (AUDIT-02) | GREEN | Stub already returns `None` for NT/ED/UNKNOWN |
| `test_two_signal_false_positive` | Unit (AUDIT-02) | SKIP | Awaits `load_cba_data` implementation in Plan 02 |
| `test_finding_section_key_valid` | Unit (AUDIT-05) | GREEN | Dataclass exists, accepts valid key |
| `test_audit_endpoint` | Integration (AUDIT-01) | **RED** | Plan 03 creates `POST /api/wd/{id}/audit` |
| `test_audit_rerun_replaces` | Integration (AUDIT-01) | **RED** | Plan 03 creates endpoint with DELETE-before-INSERT |
| `test_audit_404` | Integration (AUDIT-01) | GREEN | FastAPI returns 404 for unknown routes (coincidental pass) |
| `test_audit_decide` | Integration (AUDIT-04) | **RED** | Plan 04 creates `POST /api/wd/{id}/audit/decide` |

## Decisions Made

- Followed the plan's Wave 0 scaffold pattern (stub-first) instead of strict TDD RED-then-GREEN, because the stub must exist for any test to import. The stub is the "GREEN-able skeleton" that satisfies the import contract; the actual rule logic lands in Plan 02.
- Kept `OG_AGREEMENT_DIR` mapping to 20 codes (excluded NT/ED) as specified in the plan's action block — this documents the explicit boundary of CBA coverage and gives Plan 02 a concrete set of groups to load agreement JSONs for.
- Documented the literal section key set `{'id', 'ov', 'du', 'cls', 'q', 'drf'}` matching the amendment panel keys (per `app/api/amendments.py:29`) so AUDIT-05 (test_finding_section_key_valid) anchors the contract.

## Deviations from Plan

None — plan executed exactly as written. Both files were created with the exact content provided in the plan's action blocks.

## Issues Encountered

None. The plan's specified test set is sufficient to establish the RED baseline: 5 failures with AssertionError (not ImportError) confirms imports work and tests assert on behavior.

## User Setup Required

None — no external service configuration required. This is a backend scaffolding plan with no LLM, no network, no new env vars.

## Next Phase Readiness

- **Plan 24-02** is unblocked: implements the actual CBA + ERR rule logic to GREEN the 2 unit test failures and un-skip `test_two_signal_false_positive`. Will need to read CBA JSON files from `data/agreements/{EC,IT_CS,PA,CT_FI,TC,EL,FB,FS,AI,LP_LA,SP_AP,SH,PO}/`.
- **Plan 24-03** is unblocked: creates the `POST /api/wd/{id}/audit` endpoint to GREEN the 2 endpoint integration tests.
- **Plan 24-04** is unblocked: creates the `POST /api/wd/{id}/audit/decide` endpoint and audit_log row to GREEN the decide test.
- **Frontend wiring** (audit panel UI, OG tips, decide flow) is a separate plan — the backend RED baseline does not block it.
- **No blockers.** Backend test suite is healthy (134 + 4 = 138 GREEN, 5 RED expected, 1 SKIP expected).

## Self-Check

- [x] `v2/backend/app/services/risk_auditor.py` exists
- [x] `v2/backend/tests/test_risk_audit.py` exists
- [x] Both task commits (`f7dc28c`, `1bd68cc`) exist in git log
- [x] Imports work: `from app.services.risk_auditor import run_audit, load_cba_data, AuditFinding` succeeds
- [x] RED baseline confirmed: 5 tests fail with AssertionError, not ImportError
- [x] No regressions: 134 pre-existing tests still pass
- [x] Plan metadata commit deferred to orchestrator (worktree mode)

---
*Phase: 24-risk-audit*
*Completed: 2026-06-15*
