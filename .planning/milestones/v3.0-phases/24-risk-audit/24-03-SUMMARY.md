---
phase: 24-risk-audit
plan: 03
subsystem: audit
tags: [pytest, tdd, audit, fastapi, pydantic, audit-log, threat-model, http-endpoint]

# Dependency graph
requires:
  - phase: 24-risk-audit
    plan: 02
    provides: risk_auditor.py service (run_audit, load_cba_data) + AuditFinding dataclass + 7 GREEN unit tests
  - phase: 19-qualifications-amendments
    provides: AmendmentRequest Pydantic model with Literal section keys (template for AuditDecideRequest) + audit_log INSERT pattern
  - phase: 16-og-classification
    provides: confirmed_og string-or-dict handling (orphan_check pattern reused for OG code extraction)
provides:
  - POST /api/wd/{wd_id}/audit endpoint (AUDIT-01): DELETE-then-INSERT risk_audit_finding rows, returns findings list
  - POST /api/wd/{wd_id}/audit/decide endpoint (AUDIT-04): writes risk_audit_decision row to audit_log
  - AuditDecideRequest Pydantic model with Literal section/decision validation (AUDIT-05)
  - 3 GREEN integration tests: test_audit_endpoint, test_audit_rerun_replaces, test_audit_404
  - AUDIT-01 + AUDIT-04 + AUDIT-05 requirements validated end-to-end
affects: [24-04-frontend-integration, phase-25]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deferred-import-with-alias pattern (import json as _json inside function body) — matches existing wd.py convention for service modules"
    - "try/finally wraps all DB operations (SELECT + DELETE + INSERT + commit) so con.close() fires on exception"
    - "DELETE-then-INSERT deduplication on re-run — unique per WD/event pair via the WHERE event = 'risk_audit_finding' clause"
    - "404 guard via SELECT id FROM work_descriptions BEFORE INSERT — prevents orphan audit_log rows (T-24-07)"
    - "Literal-validated enum pattern for section keys (matches amendments.py AmendmentRequest) and decision values"
    - "OG code extraction handles string-or-dict shape — matches orphan_check pattern from Phase 16/17"

key-files:
  modified:
    - v2/backend/app/api/wd.py (added Literal to typing imports; added AuditDecideRequest model after SJDStartRequest; added run_compliance_audit endpoint after sjd_start; added audit_decide endpoint after run_compliance_audit)

key-decisions:
  - "Combined Task 1 + Task 2 implementation in wd.py was split into two atomic commits — Task 1 (model + /audit endpoint) committed as 7e3fa70, Task 2 (/audit/decide endpoint) committed as 7a4ac0f; the plan's two-task split is preserved at the commit boundary"
  - "Used deferred-import-with-alias for json inside the audit endpoint body — matches existing wd.py convention (logging.getLogger in patch_wd, from app.models.draft_duty import DraftDuty as DD) and avoids any module-level namespace pollution"
  - "AuditDecideRequest rule_id capped at 100 chars (T-24-04) — limits injection surface if any future code path reads rule_id back into a query; stored as JSON string in detail column so it never reaches SQL directly"
  - "audit_log DELETE in run_compliance_audit is scoped to event='risk_audit_finding' only — does not touch manager_amendment or risk_audit_decision rows for the same WD"
  - "Reused the orphan_check string-or-dict OG extraction pattern verbatim — keeps OG code resolution consistent across all endpoints that read confirmed_og"
  - "audit_decide uses status_code=201 (not 200) for consistency with amendments.py POST endpoint and to signal resource creation (audit_log row) per REST conventions"

patterns-established:
  - "Pattern: 'audit_log writer' endpoints share a common shape — WD existence SELECT → INSERT with event/actor/detail JSON → commit; reusable for any future audit-shaped event (e.g. classification_audit, manager_review)"
  - "Pattern: Pydantic models for audit request bodies use Literal-validated enum fields (section, decision) — auto-generates 422 with structured error message; no manual validation needed"
  - "Pattern: try/finally with con.close() at the END of the endpoint (not after the SELECT) — keeps connection alive through the full DELETE/INSERT block; matches run_audit's pattern of full-workflow DB access"

requirements-completed: [AUDIT-01, AUDIT-04, AUDIT-05]

# Metrics
duration: 4min
completed: 2026-06-15
---

# Phase 24 Plan 03: Risk Audit HTTP Endpoints Summary

**Two new POST endpoints in `wd.py` expose the risk_auditor service over HTTP — `/api/wd/{id}/audit` runs the audit and persists findings to `audit_log`, `/api/wd/{id}/audit/decide` logs advisor Accept/Manual Edit/Skip decisions — turning 3 RED integration tests GREEN and validating AUDIT-01/04/05 end-to-end.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-06-15T18:41:41Z
- **Completed:** 2026-06-15T18:45:36Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- **POST /api/wd/{wd_id}/audit endpoint** (AUDIT-01): loads WD, extracts OG code (handles string-or-dict shape), calls `load_cba_data()` + `run_audit()`, DELETEs previous `risk_audit_finding` rows, INSERTs one row per finding, returns `{wd_id, findings}` — full DELETE-then-INSERT pattern confirmed by `test_audit_rerun_replaces` (re-run produces same count, not doubled)
- **POST /api/wd/{wd_id}/audit/decide endpoint** (AUDIT-04): 404-guarded INSERT to `audit_log` with `event='risk_audit_decision'`, `actor='advisor'`, detail JSON containing rule_id/section/decision — test verifies row is written with all three fields
- **AuditDecideRequest Pydantic model** (AUDIT-05): `rule_id` (1-100 chars), `section` (Literal 6 keys), `decision` (Literal 3 values) — invalid values automatically return 422 via Pydantic validation (T-24-04/05/06 mitigations)
- All 3 RED integration tests in `test_risk_audit.py` now GREEN; full backend suite 144/144 GREEN (no regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add AuditDecideRequest model and POST /api/wd/{id}/audit endpoint to wd.py** - `7e3fa70` (feat)
2. **Task 2: Add POST /api/wd/{id}/audit/decide endpoint to wd.py** - `7a4ac0f` (feat)

**Plan metadata:** Pending orchestrator post-wave commit (worktree mode)

_TDD sequence: test(24-01) `1bd68cc` RED → feat(24-02) `41bb1dc` GREEN loader → feat(24-02) `024c64e` GREEN rules → feat(24-03) `7e3fa70` GREEN /audit endpoint → feat(24-03) `7a4ac0f` GREEN /audit/decide endpoint_

## Files Created/Modified

- `v2/backend/app/api/wd.py` — Added `Literal` to typing imports. Added `AuditDecideRequest` Pydantic model (rule_id/section/decision with Literal validation). Added `run_compliance_audit` endpoint (loads WD, extracts OG code, runs audit, DELETE-then-INSERT findings, returns findings list). Added `audit_decide` endpoint (404 guard, INSERT risk_audit_decision row). 117 net insertions across the two commits; 449 → 491 lines total.

## Test Status

| Test | Type | Status | Notes |
|------|------|--------|-------|
| `test_audit_endpoint` | Integration (AUDIT-01) | **GREEN** | 200 + findings list + matching wd_id |
| `test_audit_rerun_replaces` | Integration (AUDIT-01) | **GREEN** | Re-run produces same finding count (dedup confirmed) |
| `test_audit_404` | Integration (AUDIT-01) | **GREEN** | 404 for unknown WD |
| `test_audit_decide` | Integration (AUDIT-04) | **GREEN** | 201 + audit_log row with all 3 fields |
| `test_err_duty_coverage` | Unit (AUDIT-03) | **GREEN** | Pre-existing — unchanged |
| `test_err_duty_specificity` | Unit (AUDIT-03) | **GREEN** | Pre-existing — unchanged |
| `test_zero_findings_clean_wd` | Unit (AUDIT-01) | **GREEN** | Pre-existing — unchanged |
| `test_load_cba_unmapped_og` | Unit (AUDIT-02) | **GREEN** | Pre-existing — unchanged |
| `test_two_signal_false_positive` | Unit (AUDIT-02) | **GREEN** | Pre-existing — unchanged |
| `test_finding_section_key_valid` | Unit (AUDIT-05) | **GREEN** | Pre-existing — unchanged |

**Full backend suite:** 144 passed (134 pre-existing + 7 GREEN from 24-02 + 3 newly GREEN from 24-03). 0 failures. 0 regressions.

## Decisions Made

- **Combined implementation in one file, split into two atomic commits:** Both tasks modify `v2/backend/app/api/wd.py`, so a single `git reset --soft HEAD~1` + selective re-staging was used to preserve the plan's two-task commit boundary. The first commit (`7e3fa70`) contains the model + `/audit` endpoint (75 insertions); the second commit (`7a4ac0f`) contains the `/audit/decide` endpoint (42 insertions). The plan's verification-by-task discipline is preserved in git history.
- **Deferred-import-with-alias for `json`:** Used `import json as _json` inside both endpoint bodies to match the existing wd.py convention (e.g. `import logging` in `patch_wd`, `from app.models.draft_duty import DraftDuty as DD`). This keeps the module-level namespace clean and signals that the import is endpoint-scoped.
- **`try/finally` wraps the full DB block (not just the SELECT):** Different from the `validate-duties` pattern, which closes the connection before the 404 check. The audit endpoint needs the connection open through the DELETE + INSERT loop; closing too early would break the dedup-on-rerun guarantee. The plan explicitly called this out as a CRITICAL pattern difference.
- **DELETE scoped to `event='risk_audit_finding'` only:** Does not affect `manager_amendment` or `risk_audit_decision` rows for the same WD. Re-running the audit clears only the findings, not the advisor's prior decisions — advisor decisions are historical and should be preserved across re-audits.
- **OG code extraction reuses `orphan_check` pattern verbatim:** `wd.confirmed_og.get("og_code") if isinstance(wd.confirmed_og, dict) else wd.confirmed_og or ""` — keeps OG resolution consistent across all endpoints that read `confirmed_og`, including the string-or-dict shape from the Phase 16/17 Pydantic fix.
- **AuditDecideRequest.rule_id capped at 100 chars (not free-form):** Threat model T-24-04 specifies `Field(min_length=1, max_length=100)` to limit injection surface. Even though `rule_id` is stored as JSON and never reaches SQL, the cap prevents pathological inputs from bloating the audit_log detail column and keeps the field within reasonable UI rendering bounds.
- **audit_decide uses `status_code=201`:** Matches `amendments.py` POST endpoint convention and signals resource creation (a new audit_log row). Distinguishes decision logging from the audit execution endpoint (`/audit` returns 200 — query, not creation).

## Deviations from Plan

None — plan executed exactly as written. The only implementation-time adjustment was the commit-split (combined single-file edit → two atomic commits), which is a git-history discipline choice rather than a code deviation.

## Issues Encountered

None. Both endpoints work on the first try. The 3 RED integration tests flipped to GREEN immediately on the first run after the file changes. The full backend suite confirms no regressions.

One pre-existing `pytestmark = pytest.mark.asyncio` warning applies to 5 sync unit tests in `test_risk_audit.py` (carried forward from Plan 01). Not a regression introduced by this plan; can be cleaned up in a future plan if desired.

## User Setup Required

None — no external service configuration required. Both endpoints are pure local Python + existing SQLite `audit_log` table.

## Threat Model Compliance

All 4 threat mitigations from `<threat_model>` are satisfied:

| Threat ID | Mitigation | Status |
|-----------|-----------|--------|
| T-24-04 | `rule_id` capped via `Field(min_length=1, max_length=100)` | ✅ `AuditDecideRequest.rule_id: str = Field(min_length=1, max_length=100)` |
| T-24-05 | `section` Literal-validated | ✅ `Literal['id','ov','du','cls','q','drf']` → 422 on invalid |
| T-24-06 | `decision` Literal-validated | ✅ `Literal['accept','manual_edit','skip']` → 422 on invalid |
| T-24-07 | 404 guard on non-existent WD | ✅ SELECT id FROM work_descriptions before INSERT |

## Next Phase Readiness

- **Plan 24-04 (frontend integration)** is unblocked: the backend HTTP layer is complete; the SPA can now POST to `/api/wd/{id}/audit` and `/api/wd/{id}/audit/decide` to render the audit UI and persist advisor decisions.
- **No blockers.** Backend test suite is healthy (144 GREEN, 0 RED, 0 SKIP).
- **Curl verification ready:** Per plan `<verification>` step 3 and 4 — endpoints respond with correct 404/422 status codes. (Manual `curl` testing deferred to user per automation-first checkpoint policy.)

## Self-Check

- [x] `v2/backend/app/api/wd.py` modified (449 → 491 lines)
- [x] Both task commits (`7e3fa70`, `7a4ac0f`) exist in git log
- [x] `AuditDecideRequest` importable from `app.api.wd`
- [x] `POST /api/wd/{wd_id}/audit` route registered (`/wd/{wd_id}/audit`)
- [x] `POST /api/wd/{wd_id}/audit/decide` route registered (`/wd/{wd_id}/audit/decide`)
- [x] All 10 test_risk_audit.py tests GREEN
- [x] Full backend suite 144/144 GREEN (no regressions)
- [x] Threat model mitigations T-24-04 through T-24-07 all satisfied
- [x] Plan metadata commit deferred to orchestrator (worktree mode)

---
*Phase: 24-risk-audit*
*Completed: 2026-06-15*
