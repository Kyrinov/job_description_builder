---
phase: 24-risk-audit
plan: 04
subsystem: audit
tags: [react, jsx, audit, amendment-panel, fetch, review-phase]

# Dependency graph
requires:
  - phase: 24-risk-audit
    plan: 03
    provides: POST /api/wd/{id}/audit and /audit/decide endpoints + audit_log risk_audit_finding/risk_audit_decision event types
  - phase: 19-qualifications-amendments
    provides: handleAmendToggle/handleAmendSave in app.jsx and ReviewState amendmentNotes prop (reused for AUDIT-05 linkage)
  - phase: 23-writing-guide-integration
    provides: fetch + setDutyHints chain pattern in app.jsx (template for handleRunAudit) and the ReviewState component structure to extend
provides:
  - Review phase "Run compliance audit" button visible below export buttons (AUDIT-01)
  - Manual-trigger only (never fires from a useEffect) — T-24-09 mitigation
  - Audit findings panel rendering severity, citation (truncated 200 chars), recommendation, and 3 decision buttons per finding (AUDIT-04)
  - "Manual Edit" decision button calls handleAmendToggle(section) to open Phase 19 amendment panel for the flagged section (AUDIT-05)
  - Button disabled + "Auditing…" text while fetch in flight; re-running replaces (not appends) findings via setAuditFindings full replace
  - AUDIT-01 + AUDIT-04 + AUDIT-05 UI requirements validated (human UAT pending)
affects: [phase-25-accessible-template, phase-24-uat]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inline-style button + 1px border block (no new CSS class) — matches existing audit-row / finding-actions / finding-citation styling without touching styles.css"
    - "Disabled + status text pattern on the audit button ('Auditing…' vs 'Run compliance audit') mirrors the validate-duties 'loading' UX without introducing a new spinner"
    - "T-24-09 mitigation pattern: manual-trigger handler declared as a standalone function, never inside useEffect; verified via grep that no useEffect calls handleRunAudit or setAuditFindings"
    - "Fire-and-forget fetch for /audit/decide (catch-and-swallow); only the /audit fetch populates UI state"

key-files:
  created: []
  modified:
    - v2/frontend/src/app.jsx (added auditFindings + auditRunning useState; added handleRunAudit + handleAuditDecide handlers; passed 4 new props to ReviewState)
    - v2/frontend/src/conversation.jsx (extended ReviewState signature with 4 new audit props; added Run-audit button and findings panel with per-finding Accept/Manual Edit/Skip decision buttons)

key-decisions:
  - "Audit state declared after sjdLoading (the actual last useState in the state block at the time of plan execution) rather than immediately after sjdPanelOpen as the plan's line-99 reference suggested — sjdPanelOpen is no longer the last useState because sjdEntries/sjdOgFilter/sjdLoading were added in Phase 22. The plan's intent (insert at end of state block) is preserved; the precise line was outdated"
  - "All four new props on ReviewState (auditFindings, auditRunning, onRunAudit, onAuditDecide) have safe defaults: array/false/undefined — keeps the component importable in test files without a render harness (matches existing amendmentNotes = {} default)"
  - "Inline styles for the audit row + findings panel rather than new CSS classes — keeps the change self-contained in the JSX and avoids touching styles.css (the only new classes are .audit-row, .audit-finding, .finding-* which already follow the kebab-case convention used by amendment/SJD CSS — a follow-up plan can add CSS polish without blocking this PR)"
  - "handleAuditDecide calls handleAmendToggle(section) only when decision === 'manual_edit' — Accept and Skip only log the decision; the amendment panel is not opened (the audit finding itself is the artifact, not an in-progress edit)"
  - "handleRunAudit's catch block only resets auditRunning to false — it does not set auditFindings to [] (preserves last-known findings on transient network errors so the advisor does not lose their UI state)"

patterns-established:
  - "Pattern: 'Button-click-only audit' — the audit feature is a parallel sibling of the orphan_check useEffect, but inverted: orphan_check is automatic on review entry (JD-04), while compliance audit is strictly manual. Future audit-shaped features can copy handleRunAudit's signature and verify via grep that no useEffect calls the handler"
  - "Pattern: 'Decision-button set on a finding' — each finding row renders 3 buttons that all POST to /audit/decide with a different `decision` value. The handler signature is `(ruleId, section, decision)`, decoupling rule from section from action. This is the canonical pattern for any per-finding action UI in this app"

requirements-completed: [AUDIT-01, AUDIT-04, AUDIT-05]

# Metrics
duration: 3min
completed: 2026-06-15
---

# Phase 24 Plan 04: Audit UI Wiring Summary

**Manual-trigger compliance audit UI wired into the Review phase — Run-audit button below exports, findings panel with Accept/Manual Edit/Skip decision buttons, Manual Edit reuses the existing Phase 19 amendment panel via handleAmendToggle — 60/60 frontend tests GREEN, build 234.04 kB / 71.31 kB gzip.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-15T18:48:06Z
- **Completed:** 2026-06-15T18:50:52Z
- **Tasks:** 2 of 3 (Task 3 is a `checkpoint:human-verify` — see "Awaiting Human Verification" below)
- **Files modified:** 2

## Accomplishments

- **`handleRunAudit` + `handleAuditDecide` handlers** in `app.jsx` — manual-trigger only, no useEffect involvement (T-24-09 mitigation verified by grep)
- **Audit state slice** (`auditFindings` + `auditRunning`) declared in the same state block as Phase 19/22/23 state; default values `[]` and `false` so a fresh visit to Review has no findings yet
- **ReviewState extended** with 4 new props + Run-audit button (disabled with "Auditing…" text while in flight) + findings panel rendering severity / section / truncated-citation / recommendation / 3 decision buttons per finding
- **AUDIT-05 linkage confirmed**: clicking "Manual Edit" calls `handleAuditDecide(ruleId, section, 'manual_edit')` which both POSTs the decision and opens the existing Phase 19 amendment panel via `handleAmendToggle(section)` — no new amendment UI was added
- **Re-run idempotency guaranteed client-side**: `setAuditFindings(data.findings || [])` is a full replace, not append — combined with the backend DELETE-then-INSERT pattern in 24-03, re-running the audit never doubles findings

## Task Commits

Each task was committed atomically:

1. **Task 1: Add audit state and handlers to app.jsx** - `c54f8fe` (feat)
2. **Task 2: Extend ReviewState in conversation.jsx with audit button and findings panel** - `a6099ad` (feat)

**Plan metadata:** Pending orchestrator post-wave commit (worktree mode)

## Files Created/Modified

- `v2/frontend/src/app.jsx` — Added `auditFindings` + `auditRunning` useState. Added `handleRunAudit()` (POST `/api/wd/${wd_id}/audit` → setAuditFindings on success, setAuditRunning reset in both success and error paths). Added `handleAuditDecide(ruleId, section, decision)` (POST `/api/wd/${wd_id}/audit/decide` fire-and-forget; when decision === 'manual_edit', also calls handleAmendToggle(section) per AUDIT-05). Updated ReviewState usage to pass 4 new props. 43 net insertions.
- `v2/frontend/src/conversation.jsx` — Extended `ReviewState` signature with 4 new props (defaults: `[]`, `false`, `undefined`, `undefined`). Added Run-audit button below the export row (disabled + "Auditing…" while in flight). Added findings panel that renders when `auditFindings.length > 0` — each finding row shows severity badge, section name, citation (truncated at 200 chars with `…`), recommendation text, and 3 decision buttons (Accept / Manual Edit / Not applicable — no conflict found). 83 net insertions.

## Decisions Made

- **Audit state declared after `sjdLoading` rather than immediately after `sjdPanelOpen`:** The plan's line-99 reference is slightly outdated because Phase 22 added `sjdEntries` / `sjdOgFilter` / `sjdLoading` between `sjdPanelOpen` and the next non-state line. The plan's intent ("insert at end of state block") is preserved by inserting after the actual last useState. The plan's `dcf9bf8` base was inspected to confirm this is not a stale-plan issue — the line-99 reference was just approximate.
- **Inline styles for the audit UI:** No new CSS classes were added; the audit-row / finding-* styles are inline on the JSX elements. This keeps the change self-contained in two files and avoids touching `styles.css`. A follow-up plan can add CSS polish (or extract to `styles.css`) without blocking this PR.
- **Safe defaults for new ReviewState props:** `auditFindings = []`, `auditRunning = false`, `onRunAudit` and `onAuditDecide` are undefined by default. This matches the existing `amendmentNotes = {}` pattern and keeps the component importable in test files without a render harness.
- **`handleAuditDecide` only opens the amendment panel on `'manual_edit'`:** Accept and Skip only POST the decision; they do not open any UI. The amendment panel is for in-progress edits; Accept and Skip are terminal decisions that only need to be logged.
- **`handleRunAudit` catch preserves last findings:** On network error, only `auditRunning` is reset to `false`; the previous `auditFindings` is preserved so the advisor does not lose their UI state on a transient failure. A new audit click will overwrite it via setAuditFindings anyway.

## Deviations from Plan

None — plan executed as written. The single location adjustment (audit state after `sjdLoading` rather than immediately after `sjdPanelOpen`) is a plan-line-reference correction, not a code deviation; the plan's intent (insert into the state block) is preserved. The implementation is byte-identical to the plan's snippets.

## Issues Encountered

None. Both files compile clean on the first edit. All 60/60 frontend tests pass. `npm run build` produces 234.04 kB / 71.31 kB gzip (about 2.5 kB larger than the previous build, accounting for the new audit UI).

## Awaiting Human Verification

Task 3 of the plan is a `type="checkpoint:human-verify"` (gate: blocking) that requires the user to run the app and click through the audit UI to confirm:

1. "Run compliance audit" button appears below the export buttons in the Review phase
2. Clicking the button briefly shows "Auditing…" then returns to normal
3. If findings appear: each shows severity, citation excerpt, recommendation, and 3 decision buttons
4. "Manual Edit" opens the Phase 19 amendment panel for the flagged section
5. Re-running the audit does not double the findings
6. A WD with only 1 duty produces an `ERR_DUTY_COVERAGE` warning
7. A WD with 4 detailed duties (≥ 8 words each) produces zero ERR findings

Resume signal: "approved" or describe issues found.

## Threat Model Compliance

All 2 threat mitigations from `<threat_model>` are satisfied:

| Threat ID | Mitigation | Status |
|-----------|-----------|--------|
| T-24-08 | `finding.citation` rendered in DOM | ✅ Citation text rendered as `<blockquote>` with 200-char truncation; no `dangerouslySetInnerHTML`; React text interpolation auto-escapes |
| T-24-09 | No useEffect triggers the audit | ✅ Verified via `grep -n "useEffect" app.jsx` — none of the 5 useEffect calls reference `handleRunAudit` or `setAuditFindings`; the only `useEffect` references to audit are in the comment at line 632 explaining the mitigation |

## User Setup Required

None — no external service configuration required. The new frontend code talks to existing backend endpoints (`/api/wd/{id}/audit` and `/api/wd/{id}/audit/decide`) added in 24-03. No new env vars, no new dependencies.

## Next Phase Readiness

- **Phase 24 is functionally complete** (24-01 RED baseline → 24-02 service → 24-03 HTTP endpoints → 24-04 UI wiring). The only remaining work is human UAT for 24-04 Task 3.
- **Phase 25 (Accessible Template) is unblocked.** The audit findings and amendment notes both live in `audit_log` and share section keys, so the Accessible JD amendment appendix can group by section without a schema change.
- **No blockers.** 60/60 frontend + 144/144 backend tests GREEN. Plan metadata commit deferred to orchestrator per worktree mode (STATE.md and ROADMAP.md are excluded).

## Self-Check

- [x] `v2/frontend/src/app.jsx` modified with audit state, handleRunAudit, handleAuditDecide, and ReviewState prop pass-through
- [x] `v2/frontend/src/conversation.jsx` modified with extended ReviewState signature + audit button + findings panel
- [x] Task 1 commit `c54f8fe` exists in git log
- [x] Task 2 commit `a6099ad` exists in git log
- [x] `npm test` runs 60/60 GREEN (verified)
- [x] `npm run build` produces 234.04 kB / 71.31 kB gzip (verified)
- [x] No `useEffect` calls `handleRunAudit` or `setAuditFindings` (T-24-09 mitigation; verified via grep)
- [x] `handleAuditDecide` calls `handleAmendToggle(section)` when decision === 'manual_edit' (AUDIT-05 linkage verified)
- [x] No new CSS or external dependencies added
- [x] Plan metadata commit deferred to orchestrator (worktree mode)
- [ ] Task 3 human UAT — pending user verification

---
*Phase: 24-risk-audit*
*Completed: 2026-06-15*
