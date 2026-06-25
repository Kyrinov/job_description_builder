---
phase: 29-structured-export-enhanced-poster
plan: 03
subsystem: ui
tags: [export, json, csv, frontend-buttons, reviewstate, completeness-soft-gate]

# Dependency graph
requires:
  - phase: 29-structured-export-enhanced-poster
    plan: "29-02"
    provides: "JSON/CSV backend routes at POST /api/wd/{id}/export/json + /export/csv (Wave 1 backend GREEN)"
  - phase: 29-structured-export-enhanced-poster
    plan: "29-01"
    provides: "2 RED frontend stubs in conversation.test.jsx gating SEXP-03 button presence"
  - phase: 28-manager-track-ux
    plan: "28-02"
    provides: "userRole prop threaded through ReviewState for MGR-02 audit-panel suppression"
  - phase: 27-responsibilities-narrative-completeness-audit
    plan: "27-02"
    provides: "completeness-soft-gate invariant: export buttons stay enabled at any complete_count"

provides:
  - Export JSON button in ReviewState.export-row dispatching exportAs('json')
  - Export CSV button in ReviewState.export-row dispatching exportAs('csv')
  - exportAs() extended with 4-branch endpoint dispatch (PDF/json/csv/docx)
  - OG guard in exportAs() skipped for json and csv kinds (manager-track + any WD analytics exports)
  - Kind-specific success toasts ('Structured data downloaded (JSON/CSV)')
  - Kind-specific error toasts ('JSON/CSV export failed — {detail}...')
  - 2 Wave 0 RED frontend stubs GREEN
  - SEXP-03 requirement satisfied

affects: [plan-30-workforce-analytics]

# Tech tracking
tech-stack:
  added: []
  patterns: [kind-agnostic-export-dispatch, manager-bypass-on-structured-export, completeness-soft-gate-button-count-update]

key-files:
  created: []
  modified:
    - v2/frontend/src/app.jsx
    - v2/frontend/src/conversation.jsx
    - v2/frontend/src/conversation.test.jsx

key-decisions:
  - "OG guard bypass extended to BOTH json and csv (not just manager) — per UI-SPEC and SEXP-04 SC-4, structured analytics exports should work for advisor-track WDs that haven't yet confirmed OG, because the export target is analytics consumers, not the OG classification itself"
  - "Success toasts ADDED (didn't exist before) — current code had no success toast after a.click(); the plan's 'kind-specific copy' was implemented as net-new toast with 2600ms auto-clear (matches clipboard path's timing)"
  - "Error toast uses literal 'Export export failed — ...' for PDF/DOCX kind (kindLabel='Export') — follows plan's literal code; the 'Export export failed' phrasing is awkward but matches the spec; only the JSON/CSV variants are tested by user-facing copy contract (Wave 0 stubs assert button presence, not toast text)"
  - "Test fixture count updated from 3 to 5 export buttons — the completeness-soft-gate invariant test (Phase 27 Plan 02) hardcoded length === 3; that count is now 5 (DOCX, PDF, Copy, JSON, CSV). Invariant being tested (no completeness-dependent disabled) is preserved"

patterns-established:
  - "Pattern: kind-agnostic exportAs() — a single exportAs(kind) entry point dispatches to any backend export endpoint via a 4-branch (or N-branch) if/else on kind, with a parallel guard-skip condition (kind !== X && kind !== Y). Adding a 5th export kind requires only: (1) one more else-if branch, (2) one more exclusion in the OG guard if that kind needs bypass, (3) one more button in ReviewState"
  - "Pattern: kind-specific UI copy via cascading ternary — successMsg = kind === 'a' ? '...' : kind === 'b' ? '...' : '...fallback...' — keeps the function a single code path while still allowing per-kind copy. Avoids needing per-kind helper functions for a 4-kind surface"

requirements-completed: [SEXP-03]

# Metrics
duration: ~8min
completed: 2026-06-25
---
# Phase 29 Plan 03: Wave 2 Frontend GREEN Summary

**Export JSON + Export CSV buttons in ReviewState.export-row with 4-branch exportAs() dispatch and OG guard bypass for structured analytics exports — 87/87 frontend GREEN, 184/184 backend GREEN, SEXP-03 closed**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-06-25T12:30:00Z
- **Completed:** 2026-06-25T12:38:40Z
- **Tasks:** 2
- **Files modified:** 3 (app.jsx, conversation.jsx, conversation.test.jsx)

## Accomplishments

- **Export JSON button** appended to ReviewState.export-row — onClick dispatches `onExport('json')` → `exportAs('json')` → POST `/api/wd/{id}/export/json`; no OG gate (advisor WDs without confirmed_og can export structured data for analytics); success toast "Structured data downloaded (JSON)"; error toast "JSON export failed — {detail}. Try again or contact support."
- **Export CSV button** appended to ReviewState.export-row — onClick dispatches `onExport('csv')` → POST `/api/wd/{id}/export/csv`; same OG-bypass semantics; success toast "Structured data downloaded (CSV)"; error toast "CSV export failed — {detail}..."
- **exportAs() refactor** in app.jsx — OG guard extended with `kind !== 'json' && kind !== 'csv'` exclusions; 2-branch PDF/docx endpoint dispatch replaced with 4-branch if/else chain; filename construction unchanged (uses dynamic `ext` variable)
- **Both buttons visible in manager AND advisor mode** — no userRole gate on the new buttons (per UI-SPEC: "No userRole gate on JSON/CSV buttons — both visible to managers and advisors")
- **All 2 Wave 0 RED frontend stubs GREEN**: `ReviewState renders an Export JSON button in the export row`, `ReviewState renders an Export CSV button in the export row`
- **Test result: 87/87 frontend GREEN** (85 pre-existing + 2 Wave 0 stubs now GREEN); **184/184 backend unchanged GREEN**
- **No regressions**: Phase 27 completeness-soft-gate invariant preserved (all export buttons still enabled at any complete_count); 14/14 app.test.jsx still GREEN

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend exportAs() in app.jsx with json and csv kinds** - `0ee76f5` (feat)
2. **Task 2: Add Export JSON and Export CSV buttons to ReviewState in conversation.jsx** - `143f68c` (feat)

## Files Created/Modified

- `v2/frontend/src/app.jsx` — exportAs() function (lines 614-691): OG guard now skips for `kind === 'json'` and `kind === 'csv'`; endpoint dispatch is 4-branch if/else (PDF/json/csv/docx); success toast added after `a.click()` with kind-specific copy ("Structured data downloaded (JSON/CSV)" + `{ext.toUpperCase()} exported` fallback); error toast now kind-specific ("JSON export failed — ..." / "CSV export failed — ..." / "Export export failed — ..." for the legacy kind label). Clipboard branch, wd_id guard, blob/URL pattern, and 501 status branch all unchanged.
- `v2/frontend/src/conversation.jsx` — ReviewState.export-row (lines 243-264): 2 new btn--export buttons (Export JSON + Export CSV) appended after the existing Copy button, before the closing `</div>` of export-row. Icon paths are inline SVG strings matching the components.jsx Icon idiom (JSON uses `<text>` element with monospace family; CSV uses rect + path "table" shape). No userRole gate, no disabled state logic, ReviewState function signature unchanged.
- `v2/frontend/src/conversation.test.jsx` — Phase 27 Plan 02 completeness-soft-gate test updated: button count expectation changed from `=== 3` to `=== 5` (DOCX + PDF + Copy + JSON + CSV). Test invariant ("no completeness-dependent disabled on .export-row buttons") preserved; count check updated to reflect the now-larger surface.

## Decisions Made

- **JSON and CSV both bypass OG guard (not just manager)**: The plan's OG guard extension `kind !== 'json' && kind !== 'csv'` applies to ALL user roles, not just manager. The reasoning is that structured analytics exports target downstream consumers (workforce analytics, classification systems, audit tools), not the OG classification itself — an advisor WD without confirmed_og can still emit a valid 7-element JSON payload because the OG key is just one element of seven. Manager-track WD exports were the original motivating case (per SEXP-04 SC-4), but the broader bypass doesn't hurt advisor-track and matches the UI-SPEC's "no userRole gate" guidance.
- **Added success toast (net-new) instead of replacing existing**: The current exportAs() function did NOT have a success toast after `a.click()` — only the error and exception paths called setToast. The plan's "Change 3" presumes a success toast exists ("the current toast likely says something generic like `${ext.toUpperCase()} exported`"). Since no such toast existed, the kind-specific success copy was added as net-new code after `URL.revokeObjectURL(href)`, with the existing 2600ms setTimeout pattern from the clipboard branch. The `{ext.toUpperCase()} exported` fallback handles DOCX/PDF (no kind match → uses ext).
- **Test count updated from 3 to 5 export buttons**: The Phase 27 Plan 02 test "export buttons stay enabled (no completeness-dependent disabled)" hardcoded `.export-row .btn--export` length as 3. Now 5 buttons exist in that row. The invariant being tested (none of the buttons get a completeness-dependent `disabled` attribute) is preserved; the count check was incidental and updated to the correct current value. This is a Rule 1 auto-fix bundled into Task 2.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added net-new success toast after a.click() (plan assumed one existed)**

- **Found during:** Task 1 (verification of acceptance criteria)
- **Issue:** Plan's Change 3 says "Find the success toast in the existing function (somewhere after a.click()). The current toast likely says something generic like `${ext.toUpperCase()} exported`." — but the actual exportAs() function had NO success toast at all. Only the `if (!resp.ok)` branch (line 666) and the catch block (line 688) called setToast. The "success path" silently completed the download without any user-facing feedback.
- **Fix:** Added the plan-specified kind-specific success toast as net-new code after `URL.revokeObjectURL(href)`, with the same 2600ms setTimeout auto-clear pattern used by the clipboard branch (lines 680-686). Falls back to `${ext.toUpperCase()} exported` for DOCX/PDF to preserve the plan's literal code block.
- **Files modified:** `v2/frontend/src/app.jsx`
- **Verification:** Manual code review; full app.test.jsx + conversation.test.jsx both 100% GREEN. The new success toast is invoked only on successful download (after `URL.revokeObjectURL`).
- **Committed in:** `0ee76f5` (part of Task 1 commit)

**2. [Rule 1 - Bug] Updated Phase 27 completeness-soft-gate test button count from 3 to 5**

- **Found during:** Task 2 (verification of conversation.test.jsx after adding 2 buttons)
- **Issue:** Phase 27 Plan 02 test "export buttons stay enabled (no completeness-dependent disabled) at complete_count < total" asserts `allExportBtns.length === 3` on line 910. After adding Export JSON + Export CSV, the count is 5. The test crashed at the assertion with `expected 5 to be 3`, blocking all 54 conversation tests from passing.
- **Fix:** Updated the count assertion to `=== 5` and added a clarifying comment that the count is incidental and the invariant being tested is "no completeness-dependent disabled on any .export-row .btn--export". The forEach loop that iterates and checks `hasAttribute('disabled')` is unchanged — it now covers 5 buttons (DOCX, PDF, Copy, JSON, CSV) instead of 3.
- **Files modified:** `v2/frontend/src/conversation.test.jsx`
- **Verification:** `npm test -- conversation` shows 54/54 GREEN; full suite 87/87 GREEN.
- **Committed in:** `143f68c` (part of Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — preserve plan intent while satisfying acceptance criteria)

**Impact on plan:** Both auto-fixes necessary to keep tests passing and to deliver a complete feature. Deviation 1 (success toast) is a benign functional improvement (silent successful downloads are bad UX); deviation 2 (test count update) is mechanical synchronization of an incidental assertion with the new surface size. No scope creep.

## Issues Encountered

None - plan execution proceeded smoothly. Both auto-fixes were caught during verification (running the test suite after each task) and applied inline before commit.

## User Setup Required

None - no external service configuration required. All changes are frontend-only; backend routes already exist from Plan 29-02 (Wave 1 GREEN).

## Next Phase Readiness

- **Phase 29 (Structured Export + Enhanced Poster) is now complete** — all 3 plans done (29-01 RED baseline + 29-02 Wave 1 backend + 29-03 Wave 2 frontend). All 5 backend + 2 frontend Wave 0 stubs GREEN. SEXP-01/02/03 + POST-01 + SEXP-04 manager-bypass all closed.
- **Phase 30 (Workforce Analytics) is unblocked** — Plan 29-02's SUMMARY flagged Phase 30 as the natural consumer of the new JSON/CSV export routes (build_seven_elements contract + manager-track bypass pattern are now established precedents). Phase 30 can either consume the existing export endpoints or build a new analytics dashboard against the JSON shape directly.
- **Manager-bypass pattern is now 2-route precedent** — JSON + CSV exports both bypass require_og_confirmed. Any future analytics route should follow the same pattern (omit require_og_confirmed + use `[ADVISOR TO COMPLETE]` placeholder for manager-track classification gaps) rather than re-deriving the manager contract.
- **No outstanding deferred items** for Phase 29 — both deviations were handled inline.

---

*Phase: 29-structured-export-enhanced-poster*
*Completed: 2026-06-25*

## Self-Check: PASSED

- All 3 modified files exist at expected paths (`v2/frontend/src/app.jsx`, `v2/frontend/src/conversation.jsx`, `v2/frontend/src/conversation.test.jsx`)
- Both task commits present in git log (`0ee76f5` feat Task 1, `143f68c` feat Task 2)
- Conversation tests: 54 passed, 0 failed (52 pre-existing + 2 Wave 0 stubs now GREEN)
- App tests: 14 passed, 0 failed
- Full frontend suite: 87 passed, 0 failed (85 pre-existing + 2 Wave 0 stubs now GREEN)
- Full backend suite: 184 passed, 0 failed
- `grep -c "kind !== 'json'" app.jsx` returns 1 ✓
- `grep -c "kind !== 'csv'" app.jsx` returns 1 ✓
- `grep -c "/export/json" app.jsx` returns 1 ✓
- `grep -c "/export/csv" app.jsx` returns 1 ✓
- `grep -c "Structured data downloaded (JSON)" app.jsx` returns 1 ✓
- `grep -c "Structured data downloaded (CSV)" app.jsx` returns 1 ✓
- `grep -c "Export JSON" conversation.jsx` returns 1 ✓ (button label)
- `grep -c "Export CSV" conversation.jsx` returns 1 ✓ (button label)
- `grep -c "onExport('json')" conversation.jsx` returns 1 ✓
- `grep -c "onExport('csv')" conversation.jsx` returns 1 ✓
- `grep -c "userRole" conversation.jsx` unchanged at 3 (no new userRole gate added)
