---
phase: 28-manager-track-ux
plan: 01
subsystem: ui, api
tags: [wd_type, manager-track, role-selector, og-bypass, docx-watermark, localStorage, pydantic-literal]

# Dependency graph
requires:
  - phase: 27-responsibilities-narrative-completeness-audit
    provides: responsibilities_narrative field + WDPatchRequest co-update pattern (mirrored here for wd_type)
  - phase: 26-org-context-conversational-step
    provides: stepIndex resume-by-last-answered reduce pattern (extended here for MANAGER_SKIP_STEPS filter)
  - phase: 25-accessible-template
    provides: generate_wd_docx template path + wd_accessible_template.docx (post-processed by new _apply_draft_watermark)
  - phase: 20-export
    provides: export.py DOCX/poster routes + require_og_confirmed 409 gate (gate now has manager bypass)
provides:
  - wd_type Literal['advisor', 'manager'] typed field on WorkDescription, WDCreateRequest, WDPatchRequest (co-update)
  - require_og_confirmed intrinsic bypass for manager-track WDs (getattr-safe)
  - DRAFT watermark ('DRAFT — PENDING CLASSIFICATION') inserted at DOCX index 0 for manager exports
  - userRole state slice hydrated from jd-builder-v2-role localStorage (NEVER in WD model — D-28-01/D-28-03)
  - RoleSelector first-load screen (data-testid='role-selector'/role-advisor/role-manager)
  - MANAGER_SKIP_STEPS filter on isStepVisible / getVisibleSteps (additive optional userRole param)
  - stepIndex resume-by-last-answered honours MANAGER_SKIP_STEPS in manager mode
  - wd_type sent in every POST/PATCH body (advisor↔manager routing at server)
  - exportAs client guard bypassed for manager (no OG required for export)
affects:
  - 28-02 (Wave 2 UI suppression: ClassifyBadge, Classification Sec, ReviewState audit panel — will use userRole + wd_type for conditional rendering)
  - 29-structured-export-enhanced-poster (JSON/CSV routes will need wd_type routing — same require_og_confirmed bypass applies)

# Tech tracking
tech-stack:
  added: []  # No new dependencies; uses existing python-docx (already a project dep via build_accessible_template.py)
  patterns:
    - "userRole as OPTIONAL param on isStepVisible/getVisibleSteps (additive — undefined default preserves advisor behavior at every existing call site)"
    - "wd_type co-update rule: model + WDCreateRequest + WDPatchRequest + create_wd wiring all in the same commit (mirrors Phase 26/27 pattern)"
    - "getattr(wd, 'wd_type', 'advisor') for forward-compat with WD rows serialized before the field existed"
    - "Watermark applied INSIDE generate_wd_docx (intrinsic — client cannot suppress it)"
    - "localStorage-only role storage: D-28-01/D-28-03 contract; backend WDPatchRequest has no user_role field; extra='ignore' silently drops it (test_user_role_dropped_from_patch is the regression guard)"

key-files:
  created: []
  modified:
    - v2/backend/app/models/work_description.py
    - v2/backend/app/api/wd.py
    - v2/backend/app/services/classification_gate.py
    - v2/backend/app/services/export_service.py
    - v2/backend/tests/test_wd.py
    - v2/backend/tests/test_export.py
    - v2/frontend/src/data.jsx
    - v2/frontend/src/app.jsx
    - v2/frontend/src/app.test.jsx
    - v2/frontend/src/conversation.test.jsx

key-decisions:
  - "userRole declared BEFORE stepIndex useState (lazy initializer reads it via closure; TDZ-free)"
  - "MANAGER_SKIP_STEPS filter on isStepVisible as FIRST line of function body (before sector gate) — guarantees manager mode hides the 4 classification steps even if answers accidentally trigger them"
  - "stepIndex resume reduce gets the manager-skip guard as the FIRST line of the callback — preserves resume invariant: walk through STEPS skipping MANAGER_SKIP_STEPS, then find last answered by record key"
  - "Watermark post-processes rendered DOCX bytes via python-docx (insert_paragraph_before on doc.paragraphs[0]) — works on the existing wd_accessible_template.docx without rebuilding the template"
  - "Watermark styling: bold, dark red (RGBColor 0xC0,0x00,0x00), centered, 14pt — visually unmissable but not destructive to document layout"
  - "Reset role-storage bug fix: resetStorage() in app.test.jsx was clearing a different _store Map than the one globalThis.localStorage uses (vitest.setup.js installs its own InMemoryStorage). Switched to globalThis.localStorage.clear() — operates on the same Map the app reads from"

patterns-established:
  - "Pattern: TDD-within-task for v4.0 vertical slices (test stubs RED first, then co-update implementation, then verify GREEN). Mirrors Phase 26 Plan 02 / Phase 27 Plan 01"
  - "Pattern: WDPatchRequest co-update rule (Phase 26 onward) — every new advisor-patchable WD field MUST land on WorkDescription + WDCreateRequest + WDPatchRequest + create_wd in the same commit, with a round-trip test gating merge"
  - "Pattern: Optional userRole param for STEPS filter — additive signature, all existing call sites that don't pass it continue to work"
  - "Pattern: localStorage key suffix convention — jd-builder-v2-{key} for state slices (record, wd-id, role); userRole follows the same naming"
  - "Pattern: data-testid convention for first-load screens — {screen-name} on the root container, {role}-{choice} on each option button (mirrors SJD browser panel testid pattern)"

requirements-completed: [MGR-01, MGR-03]

# Metrics
duration: 49min
completed: 2026-06-24
---

# Phase 28 Plan 01: Manager-Track Foundation Vertical Slice

**Role selector + wd_type co-update + require_og_confirmed manager bypass + DRAFT watermark, locked behind a single localStorage-only `userRole` slice (never in the WD model).**

## Performance

- **Duration:** 49 min (2959s)
- **Started:** 2026-06-24T17:01:44Z
- **Completed:** 2026-06-24T17:51:03Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments

- MGR-01: RoleSelector renders on first load (localStorage empty); selecting a role persists to `jd-builder-v2-role` and launches the matching track; refresh does not re-show the selector (userRole hydrates on mount); `user_role` is NEVER sent in PATCH/POST body (D-28-03 guard test asserts the drop).
- MGR-03: `wd_type: Literal['advisor', 'manager'] = 'advisor'` co-update on WorkDescription + WDCreateRequest + WDPatchRequest + create_wd wiring (same commit); manager-track STEPS variant skips `{noc_confirm, og_confirm, og_level_questions, og_level}`; stepIndex resume-by-last-answered works in manager mode; `require_og_confirmed` bypasses for `wd.wd_type=='manager'` (getattr-safe); manager DOCX export has "DRAFT — PENDING CLASSIFICATION" watermark as the first paragraph; advisor WDs still 409 without OG (regression guard).
- Co-update rule enforced: model + WDCreateRequest + WDPatchRequest + create_wd wiring all in commit `e7e3d0b` (single commit per plan rule).

## Task Commits

Each task was committed atomically:

1. **Task 1: wd_type field on WorkDescription + WDCreateRequest + WDPatchRequest + create_wd co-update + user_role rejection guard** - `e7e3d0b` (feat)
2. **Task 2: require_og_confirmed manager bypass + DRAFT watermark in generate_wd_docx** - `93b1a1e` (feat)
3. **Task 3: Frontend role selector + userRole state + manager STEPS variant + wd_type in POST/PATCH + exportAs bypass** - `49b51e4` (feat)

## Files Created/Modified

- `v2/backend/app/models/work_description.py` — added `Literal` import + `wd_type: Literal["advisor","manager"] = "advisor"` field on WorkDescription (default preserves all existing WD rows)
- `v2/backend/app/api/wd.py` — added `wd_type` to WDCreateRequest (default advisor), WDPatchRequest (Optional), and `wd_type=body.wd_type` to `create_wd` constructor; user_role intentionally absent (D-28-03 contract)
- `v2/backend/app/services/classification_gate.py` — `require_og_confirmed` early-returns when `getattr(wd, "wd_type", "advisor") == "manager"`; getattr default keeps old WD rows behaving as advisor
- `v2/backend/app/services/export_service.py` — new `_apply_draft_watermark(file_bytes: bytes) -> bytes` helper (python-docx inserts bold dark-red centered "DRAFT — PENDING CLASSIFICATION" at index 0); applied inside `generate_wd_docx` after `_render_docx` when `wd.wd_type == 'manager'`
- `v2/backend/tests/test_wd.py` — 4 new tests: `test_patch_wd_type_round_trip`, `test_patch_wd_type_default_advisor`, `test_user_role_dropped_from_patch` (regression guard), `test_patch_wd_type_manager_preserved`
- `v2/backend/tests/test_export.py` — 3 new tests: `test_export_docx_manager_bypasses_409`, `test_export_docx_manager_has_draft_watermark`, `test_export_docx_advisor_still_409_without_og` (regression guard)
- `v2/frontend/src/data.jsx` — new `MANAGER_SKIP_STEPS = new Set(['noc_confirm','og_confirm','og_level_questions','og_level'])` constant; `isStepVisible(step, answers, userRole)` and `getVisibleSteps(steps, answers, userRole)` extended with optional `userRole` param (additive — undefined default preserves advisor behavior); `MANAGER_SKIP_STEPS` exported
- `v2/frontend/src/app.jsx` — imported `MANAGER_SKIP_STEPS`; declared `userRole` state BEFORE `stepIndex` (TDZ-free closure); stepIndex reduce skips MANAGER_SKIP_STEPS in manager mode; activeStepIndex useMemo passes userRole; `wdPayload.wd_type = userRole === 'manager' ? 'manager' : 'advisor'`; exportAs guard bypassed for manager; new `RoleSelector` component (data-testid='role-selector'/role-advisor/role-manager); main render wrapped with role gate (returns `<RoleSelector>` when userRole is null, main shell otherwise)
- `v2/frontend/src/app.test.jsx` — 3 new MGR-01 tests (userRole hydration, role selector when absent, selecting manager persists + launches manager track); 4 existing tests seeded `jd-builder-v2-role='advisor'` in beforeEach so they exercise the advisor path (not the new RoleSelector screen); 1 Rule 1 fix to `resetStorage()` (was clearing a different _store Map — see deviations)
- `v2/frontend/src/conversation.test.jsx` — 3 new MGR-03 tests (manager mode hides 4 classification-internal steps; manager mode is strictly shorter with spot checks on the 3 NEW skips; advisor mode unchanged with explicit userRole='advisor' — additive signature regression guard); CONVO-02 jumpToExchange and OGX-04 round 3 sectors loop seed the role in their setup

## Decisions Made

- **userRole useState declared BEFORE stepIndex useState** — the stepIndex lazy initializer closes over userRole to skip MANAGER_SKIP_STEPS in manager mode. Without this ordering, JavaScript's TDZ throws and the initializer's `catch { return 0; }` silently masks the error (caught during Task 3 — test `stepIndex resume` got `idx=0` instead of advancing past title).
- **MANAGER_SKIP_STEPS filter as FIRST line of isStepVisible function body** — runs before the existing sector-gate switch, so manager mode hides the 4 classification-internal steps regardless of sector answer. Robust to any future gate changes.
- **stepIndex resume reduce gets the manager-skip guard as the FIRST line of the callback** — the existing STEP_RECORD_KEY lookup is unchanged; the guard only affects whether the reduce considers the step at all. Preserves the resume invariant from Phase 26.
- **Watermark is applied INSIDE generate_wd_docx, not in the export route** — intrinsic to wd_type, no caller can suppress it. T-28-01 mitigation: a malicious advisor setting wd_type='manager' to bypass the OG gate still gets a clearly-labelled DRAFT DOCX. Self-documenting abuse surface.
- **Watermark uses python-docx post-processing (insert_paragraph_before on doc.paragraphs[0])** — works on the existing wd_accessible_template.docx without rebuilding the binary template. Insert at index 0 places the watermark above all template content (Section 1 header, signature blocks, etc.) — the classification team sees the DRAFT marker immediately on opening the file.
- **resetStorage() now calls globalThis.localStorage.clear() instead of `_store.clear()`** — vitest.setup.js installs its own InMemoryStorage with a different closure-bound _store than app.test.jsx's. The original resetStorage was clearing the wrong Map, causing the new MGR-01 role-selector tests to fail when run after the hydration test (state leaked via the setup's _store). The fix uses the public clear() API to operate on the same Map the app reads.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Moved userRole useState BEFORE stepIndex useState**
- **Found during:** Task 3 (frontend implementation)
- **Issue:** Plan suggested adding `userRole` state "near the top of App()", but the stepIndex resume-by-last-answered lazy initializer closes over userRole (manager-skip guard reads it). If userRole is declared after stepIndex, the lazy initializer runs while userRole is in TDZ — JavaScript throws ReferenceError, the `catch { return 0; }` swallows it, and the resume lands on step 0 instead of advancing past the last answered step.
- **Fix:** Moved `const [userRole, setUserRole] = useState(...)` to immediately after the `answers` declaration, before the `stepIndex` declaration. Added a comment block explaining the TDZ constraint so future maintainers don't accidentally reorder it.
- **Files modified:** v2/frontend/src/app.jsx
- **Verification:** `stepIndex resume: initialises past step 0 when record has answered fields` test now passes (idx > 0 as expected)
- **Committed in:** `49b51e4` (Task 3 commit)

**2. [Rule 1 - Bug] Fixed resetStorage() clearing the wrong _store Map**
- **Found during:** Task 3 (frontend test execution)
- **Issue:** `app.test.jsx` defines its own `_store = new Map()` at module scope plus an InMemoryStorage class. But `vitest.setup.js` already installs `globalThis.localStorage = new InMemoryStorage()` with ITS OWN `_store` (different closure). The test file's check `if (typeof globalThis.localStorage?.clear !== 'function')` never replaces it (clear IS a function), so `globalThis.localStorage` is the setup's instance. The original `resetStorage() { _store.clear(); }` cleared the test file's UNUSED Map, not the setup's actual one — `userRole` from the previous MGR-01 test leaked into subsequent tests in the same describe block.
- **Fix:** Changed `resetStorage() { _store.clear(); }` to `resetStorage() { globalThis.localStorage.clear(); }` so it operates on the same Map the app reads from.
- **Files modified:** v2/frontend/src/app.test.jsx
- **Verification:** All 3 MGR-01 role-selector tests now pass when run together (previously 2 failed). The fix is non-invasive — `globalThis.localStorage.clear()` is the documented public API for the in-memory storage shim.
- **Committed in:** `49b51e4` (Task 3 commit)

**3. [Rule 1 - Bug] Stricter manager-shorter spot-check test (replace weak count assertion)**
- **Found during:** Task 3 (frontend test execution)
- **Issue:** Initial test asserted `expect(managerVisible.length).toBe(advisorVisible.length - 4)` — but `og_level_questions` is already hidden in advisor mode (gated by `answers.og_confirm` being a level-description group; with `answers = {}` the gate returns false). So manager mode only adds 3 NEW skips (noc_confirm, og_confirm, og_level), not 4. Total: 15 - 3 = 12 (got 12, expected 11).
- **Fix:** Replaced the exact-count assertion with `expect(managerVisible.length).toBeLessThan(advisorVisible.length)` plus explicit spot-checks on the 3 NEW skips (noc_confirm + og_confirm + og_level: visible in advisor, hidden in manager). The contract is now robust to any future gate changes that might overlap with MANAGER_SKIP_STEPS.
- **Files modified:** v2/frontend/src/conversation.test.jsx
- **Verification:** Test now passes (12 < 15, plus all 6 spot-check assertions pass)
- **Committed in:** `49b51e4` (Task 3 commit)

**4. [Rule 2 - Missing Critical] Seeded jd-builder-v2-role='advisor' in 4 existing test setups**
- **Found during:** Task 3 (frontend test execution)
- **Issue:** Plan noted: "If the existing app.test.jsx tests that render `<App />` now see the role selector (because localStorage is empty), update them to seed `localStorage.setItem('jd-builder-v2-role', 'advisor')` in their setup so they exercise the advisor path." This turned out to affect 5 tests across 2 files (FE-04 FE-05 WD-PATCH describe blocks in app.test.jsx; CONVO-02 jumpToExchange and OGX-04 round 3 sectors loop in conversation.test.jsx) — more than anticipated.
- **Fix:** Added `globalThis.localStorage.setItem('jd-builder-v2-role', 'advisor')` to the relevant beforeEach blocks (5 of them). The OGX-04 round 3 sectors loop clears localStorage at the start of each iteration (existing Phase 26 Rule 1 fix to prevent stepIndex resume leak); added the role reseed immediately after the clear.
- **Files modified:** v2/frontend/src/app.test.jsx, v2/frontend/src/conversation.test.jsx
- **Verification:** All previously-passing tests continue to pass after seeding (76 frontend GREEN, was 70 pre-existing + 5 new + 1 stricter = 76)
- **Committed in:** `49b51e4` (Task 3 commit)

---

**Total deviations:** 4 auto-fixed (2 Rule 1 bug fixes, 1 Rule 2 missing critical, 1 Rule 3 blocking ordering constraint)
**Impact on plan:** All auto-fixes necessary for correctness, test isolation, and TDZ safety. No scope creep — all deviations are within the existing plan's task boundaries.

## Issues Encountered

- **TDZ on userRole access from stepIndex lazy initializer** — JavaScript const declarations are hoisted but in TDZ until the declaration line is reached. The plan didn't anticipate the closure dependency; the fix (reorder declarations) was straightforward and documented inline.

- **Dual _store Map bug in vitest test shim** — vitest.setup.js installs an InMemoryStorage using a setup-file-closure-bound _store. app.test.jsx's check `if (typeof globalThis.localStorage?.clear !== 'function')` was a defensive guard for a non-existent failure mode, and as a side effect left the test file's _store unused. The fix uses the public clear() API — same Map, no closure dependency.

- **Existing test setup updates more invasive than expected** — Plan said "update them to seed `localStorage.setItem('jd-builder-v2-role', 'advisor')` in their setup" without enumerating which tests needed the seed. The actual count was 5 tests (across 2 files). All updates were mechanical beforeEach additions; no logic changes.

## User Setup Required

None - no external service configuration required. All changes are local to the existing SPA + FastAPI backend.

## Next Phase Readiness

**Phase 28-02 (Wave 2 MGR-02 UI suppression)** can now build on:
- `userRole` state slice (read-only access for conditional rendering)
- `record.wd_type` (mirrored from `userRole` at every commit; serves as a stable signal in document preview even after a role-switch edge case)
- `MANAGER_SKIP_STEPS` filter (already hides classification-internal steps in STEPS; the UI suppression layer needs to hide OG/JES/CBA strings in the rendered document preview Secs and ReviewState)

**Phase 29 (Structured Export)** can now route JSON/CSV exports via the same `require_og_confirmed` bypass (manager WDs will produce valid exports with `[ADVISOR TO COMPLETE]` placeholders for un-set classification fields).

**Potential concern:** the new `userRole` state is read from localStorage on mount and not synced with subsequent PATCH/POST cycles. If the user picks "manager" then switches tabs and the WD persists with wd_type='advisor' (unlikely but possible via manual JSON edit), the role selector won't re-appear. This is acceptable for v4.0; a "Switch role" affordance in the Header is deferred per the agent's discretion note in CONTEXT.md.

---

## Self-Check

PASSED — all created/modified files exist, all commits exist in git log.

```
$ ls v2/backend/app/models/work_description.py v2/backend/app/api/wd.py \
       v2/backend/app/services/classification_gate.py v2/backend/app/services/export_service.py \
       v2/frontend/src/data.jsx v2/frontend/src/app.jsx \
       v2/backend/tests/test_wd.py v2/backend/tests/test_export.py \
       v2/frontend/src/app.test.jsx v2/frontend/src/conversation.test.jsx
[all present]

$ git log --oneline e7e3d0b 93b1a1e 49b51e4
e7e3d0b feat(28-01): add wd_type field co-update + user_role rejection guard
93b1a1e feat(28-01): require_og_confirmed manager bypass + DRAFT watermark
49b51e4 feat(28-01): RoleSelector + userRole state + manager STEPS variant + wd_type in POST/PATCH + exportAs bypass

Test counts:
- Backend: 179 passed (172 pre-existing + 4 Task 1 + 3 Task 2)
- Frontend: 76 passed (70 pre-existing + 3 MGR-01 + 3 MGR-03)
```

*Phase: 28-manager-track-ux*
*Completed: 2026-06-24*
## Self-Check: PASSED

All created/modified files exist; all 3 task commits exist in git log.
