---
phase: 27-responsibilities-narrative-completeness-audit
plan: 02
subsystem: api
tags: [build-seven-elements, validate-elements, completeness-audit, react, fastapi, soft-gate, accessibility, ROADMAP-criterion-3-4-5]

# Dependency graph
requires:
  - phase: 27-responsibilities-narrative-completeness-audit
    provides: "Plan 01's responsibilities_narrative typed field on WorkDescription (RESP-01) is read by build_seven_elements.responsibility element status (R-ELEM-01a)"
  - phase: 26-org-context-conversational-step
    provides: "org_context typed field on WorkDescription + WD-PATCH round-trip co-update. build_seven_elements.organizational_context reads wd.org_context (typed root) per ROADMAP #4 audit guard"
  - phase: 24-risk-audit
    provides: "Soft-gate pattern (audit panel is informational, not blocking). The completeness badge follows the same pattern (ROADMAP #5)"
  - phase: 23-writing-guide-integration
    provides: "client_service_results step + record.client_service_results storage. build_seven_elements.client_service_results reads record.client_service_results"
  - phase: 20-export-pipeline
    provides: "validate-duties endpoint pattern (wd.py line 306). validate-elements mirrors the load-WD-by-id + 404 guard + return-dict shape"
provides:
  - "build_seven_elements(wd) shared helper in export_service.py — single source of truth for the 7 Part 2 elements + per-element status (populated|derived|missing)"
  - "POST /api/wd/{wd_id}/validate-elements endpoint — returns {wd_id, elements[7], complete_count, total=7} (ELEM-01)"
  - "ReviewState completeness prop + 'Completeness: N/7 elements populated or derived' badge in checklist (data-testid='completeness-badge') — soft gate, export buttons stay enabled at any count (ELEM-02)"
  - "app.jsx completeness state + useEffect that POSTs /api/wd/{id}/validate-elements when reviewing becomes true — mirrors orphan_check / amendment_notes useEffect pattern"
affects:
  - "27-03 (if any) — none planned; Phase 27 has 2 plans only"
  - "29-structured-export (Phase 29 SEXP-01/02 JSON/CSV value-export routes will reuse build_seven_elements as the single source of truth)"

# Tech tracking
tech-stack:
  added: []  # Plan 27-02 adds no libraries — pure logic + UI surface
  patterns:
    - "Shared helper as single source of truth: build_seven_elements(wd) lives in export_service.py (next to _build_wd_context) and is consumed by both validate-elements endpoint (this plan) and Phase 29's JSON/CSV export routes. Adding the JSON/CSV value-export routes later does NOT touch the helper — they call it."
    - "Status enum contract: populated|derived|missing. NEVER 'not_applicable' for Responsibility (R-ELEM-01a / ROADMAP #3 — the field is open to all positions, so empty means missing, not not_applicable). Effort and Working Conditions use 'derived' when jes_total_points is set (R-ELEM-01b), else 'missing'."
    - "Typed-field-only audit (ROADMAP #4): build_seven_elements.organizational_context reads wd.org_context (typed root field) and ignores _build_organizational_context_text's synthesized fallback. A WD with record.branch/reports but wd.org_context=None must report 'missing' — otherwise the audit would be a false positive."
    - "Soft-gate UI pattern (ROADMAP #5): the completeness badge is INFORMATIONAL. Export buttons (DOCX / PDF / Copy) stay enabled at any completeness count. The guard test renders ReviewState with complete_count=2/7 and asserts all three export buttons lack `disabled` — preventing a future regression from wiring completeness to button enablement."
    - "Review-hydration useEffect pattern (reused): app.jsx adds a sibling useEffect to the existing orphan_check (~line 207) and amendment_notes (~line 235) that POSTs /api/wd/{wd_id}/validate-elements when reviewing becomes true. Silent on failure (the badge simply does not appear)."

key-files:
  created: []
  modified:
    - v2/backend/app/services/export_service.py
    - v2/backend/app/api/wd.py
    - v2/frontend/src/conversation.jsx
    - v2/frontend/src/app.jsx
    - v2/backend/tests/test_export.py
    - v2/backend/tests/test_wd.py
    - v2/frontend/src/conversation.test.jsx

key-decisions:
  - "build_seven_elements returns value=None for skills / effort / working_conditions (Phase 29 SEXP-01/02 will populate structured values). The status enum is what Plan 27-02 needs; the value is for downstream JSON/CSV routes."
  - "Org context audit guard is a separate, explicit test (test_build_seven_elements_org_context_reads_typed_field) that constructs a WD with wd.org_context=None AND record={branch,reports,summary,title} — proves the audit reads the typed field, not the synthesized fallback. This is the single test that pins ROADMAP #4 in the helper."
  - "Responsibility never 'not_applicable' test (test_build_seven_elements_responsibility_missing_not_notapplicable): a WD with no responsibilities_narrative asserts status=='missing' AND status != 'not_applicable'. The explicit != guard prevents a future regression from introducing not_applicable logic — ROADMAP #3 frames the original REQUIREMENTS.md wording as a bug to correct."
  - "Effort and Working Conditions share the 'derived' signal (jes_total_points is not None) — they always move together in the helper. The test asserts both. This is intentional: the JES scoring runs once and produces both category outputs together; the helper does not re-score."
  - "validate-elements endpoint is POST (not GET) — mirrors validate-duties, orphan_check, audit, and run_jes endpoints (all POST). The endpoint takes no body; it loads the WD by id and reads stored data. Consistent with the existing read-only-audit endpoint family."
  - "Soft-gate guard test (the second frontend test) renders ReviewState with complete_count=2/7 and asserts every .btn--export inside .export-row lacks a `disabled` attribute. This is a regression guard: a future refactor that wires `disabled={completeness.complete_count < completeness.total}` to the export buttons would block exports for partially-complete WDs (forbidden by ROADMAP #5)."
  - "validate-elements uses POST /api/wd/{id}/validate-elements (no body), loads WD from DB, calls build_seven_elements, returns the result. 404 on missing WD mirrors validate-duties / orphan_check / audit. Never errors on incomplete data — returns 'missing' statuses for the elements the advisor hasn't populated."

patterns-established:
  - "Shared service-function-as-audit-source-of-truth: when an audit needs to evaluate stored data, define a single pure function (here: build_seven_elements(wd)) that the HTTP endpoint calls AND future consumers (Phase 29 JSON/CSV) will reuse. The endpoint stays thin (load WD + call + return)."
  - "ROADMAP-criterion-as-a-separate-explicit-test: each criterion that drives an audit decision gets its own named test (test_build_seven_elements_org_context_reads_typed_field for ROADMAP #4; test_build_seven_elements_responsibility_missing_not_notapplicable for ROADMAP #3). The test name encodes the criterion so the regression guard is searchable."
  - "Sibling useEffect for Review-phase hydration: when adding a new review-phase data source (completeness badge), add a sibling useEffect that mirrors the existing pattern (orphan_check / amendment_notes). Same dependency array ([reviewing, wd_id]), same silent-on-failure contract."

requirements-completed:
  - ELEM-01
  - ELEM-02
  - ELEM-03

# Metrics
duration: 18min
completed: 2026-06-24
---
# Phase 27 Plan 02: Seven-Elements Completeness Audit — Summary

**build_seven_elements(wd) shared helper + POST /api/wd/{id}/validate-elements endpoint + Review-phase N/7 completeness badge (soft gate) — ELEM-01/02/03 GREEN at the data-structure + UI surface level**

## Performance

- **Duration:** 18 min
- **Started:** 2026-06-24T11:48:00Z (approx)
- **Completed:** 2026-06-24T12:06:00Z (approx)
- **Tasks:** 3 (TDD with strict RED/GREEN sequence; each task's tests are written first, then implementation)
- **Files modified:** 7 (3 production + 3 test files; STATE.md modified by orchestrator centrally per workflow rule)

## Accomplishments

- **build_seven_elements(wd) shared helper in export_service.py** — single source of truth for the 7 Part 2 elements + per-element status. Returns `{elements: [7 dicts], complete_count: N, total: 7}`. Status enum: `populated | derived | missing`. Reads typed root fields directly (org_context, responsibilities_narrative) and falls back to record dict for client_service_results / record.quals. Effort + Working Conditions share the `derived` signal (`jes_total_points is not None`). This helper becomes the single source of truth that Phase 29's JSON/CSV value-export routes (SEXP-01/02) will also consume — no refactor needed when those routes land.
- **POST /api/wd/{wd_id}/validate-elements endpoint in wd.py** — mirrors validate-duties / orphan_check / audit pattern (load WD by id, 404 guard, return dict). Returns `{wd_id, elements[7], complete_count, total: 7}`. The audit guard (org_context reads the typed field ONLY) is enforced both by the helper and by an explicit test that constructs a WD with `wd.org_context=None` + record branch/reports and asserts `status == 'missing'` (NOT populated — the synthesized fallback would be a false positive).
- **Review-phase N/7 completeness badge (soft gate)** — `ReviewState` accepts a `completeness` prop and renders a `data-testid='completeness-badge'` check-row inside the existing checklist with text `Completeness: N/7 elements populated or derived`. app.jsx adds a `completeness` state and a sibling useEffect that POSTs `/api/wd/{wd_id}/validate-elements` when reviewing becomes true — mirrors the orphan_check / amendment_notes pattern (silent on failure). Export buttons (DOCX / PDF / Copy) stay enabled at any count — the soft-gate guard test asserts all three export buttons lack `disabled` when `complete_count < total`. ROADMAP #5 forbids a hard block; this guard prevents a future regression from wiring completeness to button enablement.
- **All success criteria met:** backend 172 passed (164 baseline + 5 build_seven_elements + 3 validate_elements endpoint); frontend 70 passed (68 baseline + 2 completeness badge + soft-gate guard). ELEM-01/02/03 delivered at the data-structure level (full JSON/CSV value-export routes are scoped to Phase 29 SEXP-01/02 per CONTEXT.md R-ELEM-03 scope decision).

## Task Commits

Each task was committed atomically in strict TDD RED → GREEN sequence:

1. **Task 1: build_seven_elements(wd) shared helper + 5 unit tests** — `5b12e1f` (feat) — 2 files (export_service.py + test_export.py). 5 RED tests written first (derived_effort_wc, no_jes_missing, org_context_reads_typed_field, responsibility_missing_not_notapplicable, total_seven); helper implemented; all 5 GREEN; full backend suite 169 passed (164 + 5).
2. **Task 2: POST /api/wd/{id}/validate-elements endpoint + 3 tests** — `1e29caf` (feat) — 2 files (wd.py + test_wd.py). 3 RED tests written first (returns_seven, missing_wd_404, partial); endpoint implemented mirroring validate_duties_endpoint; all 3 GREEN; full backend suite 172 passed (169 + 3).
3. **Task 3: Review-phase completeness badge (soft gate) + 2 tests** — `8606831` (feat) — 3 files (conversation.jsx + app.jsx + conversation.test.jsx). 2 RED tests written first (renders 5/7 badge, export buttons stay enabled); ReviewState extended with `completeness` prop + badge; app.jsx adds state + useEffect that POSTs validate-elements on review; both GREEN; full frontend suite 70 passed (68 + 2).

## Files Created/Modified

- `v2/backend/app/services/export_service.py` — added `build_seven_elements(wd: WorkDescription) -> dict` placed AFTER `_build_wd_context` so the reader sees the context builder first. 7-element list with status rules per R-ELEM-01a/b/c; reads typed root fields directly; skills falls back to record.quals. Does NOT refactor `_build_wd_context` (Phase 29 concern; change is additive).
- `v2/backend/app/api/wd.py` — added `validate_elements` POST endpoint at line 334 (immediately after `validate_duties_endpoint`). Loads WD by id (404 guard at line 362), calls `build_seven_elements(wd)` from export_service, returns `{wd_id, **result}`. Mirrors validate-duties / orphan_check / audit endpoint shape.
- `v2/frontend/src/conversation.jsx` — `ReviewState` extended with `completeness` prop (default `null`) and a `completenessBadge` JSX block rendered inside the existing checklist (after `checks.map`). data-testid="completeness-badge" with text "Completeness: {complete_count}/{total} elements populated or derived". Export buttons (DOCX / PDF / Copy) UNCHANGED — no completeness-dependent disabled added (ROADMAP #5 soft gate).
- `v2/frontend/src/app.jsx` — added `[completeness, setCompleteness] = useState(null)` state + sibling useEffect that POSTs `/api/wd/${wd_id}/validate-elements` when reviewing becomes true. Result feeds `<ReviewState completeness={completeness} ... />` at the render site (line 926). useEffect follows the silent-on-failure pattern from orphan_check / amendment_notes (the badge simply doesn't appear if the fetch fails).
- `v2/backend/tests/test_export.py` — added 5 unit tests for `build_seven_elements` (each test constructs a `WorkDescription` directly via `_wd_for_seven_elements(**overrides)` helper and asserts element statuses). The org_context test is the explicit ROADMAP #4 audit guard (constructs WD with org_context=None + record branch/reports, asserts organizational_context status=='missing'). The responsibility test is the explicit ROADMAP #3 audit guard (asserts status=='missing' AND status != 'not_applicable').
- `v2/backend/tests/test_wd.py` — added 3 endpoint integration tests: `test_validate_elements_returns_seven` (fully-populated WD → 200, complete_count=7), `test_validate_elements_missing_wd_404` (unknown id → 404), `test_validate_elements_partial` (duties + jes_total_points only → complete_count=3 with key_activities populated + effort/working_conditions derived + others missing). Tests follow the `validate-duties` test pattern (POST + assert JSON).
- `v2/frontend/src/conversation.test.jsx` — added 2 tests in a new `describe('Phase 27 Plan 02: ReviewState completeness badge')` block. The badge test renders `<ReviewState completeness={...} />` and asserts `data-testid='completeness-badge'` exists with text containing "5", "7", and "completeness"/"elements". The soft-gate test asserts every `.btn--export` inside `.export-row` lacks `disabled` when complete_count=2/7. ReviewState is now imported directly from `./conversation.jsx` (line 10) to enable direct rendering without the full App wrapper.

## Decisions Made

- **`build_seven_elements` is a pure function placed in `export_service.py`** (not a new module) because the underlying data reads are already there (`_build_wd_context` lines 301-367). Placing the helper near the existing context builder keeps related data reads grouped and signals that Phase 29's JSON/CSV routes should also consume from this module. The helper does NOT touch `_build_wd_context` (Phase 29 concern; the change is purely additive).
- **`value` field on `effort` / `working_conditions` / `skills` is left `None` in the helper output.** Status is what Plan 27-02 needs; the structured value-export is Phase 29 (SEXP-01/02). Locking the schema now (with `value: None`) gives Phase 29 a known shape to extend. `key_activities` carries the duty list (`value: wd.duties`) because duties are already a list — the audit consumers can use the value directly if they want.
- **Org context audit guard is a named test (`test_build_seven_elements_org_context_reads_typed_field`).** The test name encodes the ROADMAP #4 criterion so the regression guard is searchable via `grep`. The test deliberately constructs a WD with `wd.org_context=None` AND `record={branch, reports, summary, title}` to prove the helper ignores the synthesized `_build_organizational_context_text()` fallback. Without this test, a future refactor could "fix" the helper to return "populated" whenever branch+reports exist (false positive).
- **Responsibility never-not-applicable is a named test (`test_build_seven_elements_responsibility_missing_not_notapplicable`).** Explicit `assert ... != 'not_applicable'` guard prevents a future regression from re-introducing the original REQUIREMENTS.md wording that ROADMAP #3 explicitly corrects.
- **Effort + Working Conditions share the derived signal.** The JES scoring runs once and produces both category outputs together. The helper does not re-score per category. The `derived_effort_wc` test asserts both move together (status=='derived' for both when jes_total_points is set; status=='missing' for both when None).
- **validate-elements endpoint is POST with no body.** Consistent with the existing read-only-audit endpoint family (validate-duties, orphan_check, audit, run_jes). Takes only a wd_id path param. 404 guard mirrors validate-duties / orphan_check. Never errors on incomplete data — returns 'missing' statuses for elements the advisor hasn't populated.
- **Soft-gate guard test renders ReviewState directly with `complete_count: 2/7` and asserts all export buttons lack `disabled`.** This is a regression guard: a future refactor that wires `disabled={completeness.complete_count < completeness.total}` would block exports for partially-complete WDs (forbidden by ROADMAP #5). The guard test catches the regression even if the badge code is correct.
- **`completeness` state is initialized to `null` and re-fetched on every review transition.** No "start new description" reset is needed (the next review entry fetches fresh). Mirrors the orphan_check / amendment_notes useEffect pattern exactly — including the `cancelled` flag for the async fetch to prevent setState after unmount.

## Deviations from Plan

None - plan executed exactly as written. All 3 task commit messages match the plan's specified format. TDD gate commits exist (RED test writes happen inside the same atomic commit as the GREEN implementation, per the standard plan-level TDD convention; this matches the pattern used in 27-01 Task 1). All spot-check grep commands return non-empty results. All `<acceptance_criteria>` from each task pass. All `<success_criteria>` from the plan's verification section are met.

The only minor implementation detail worth flagging is that the helper uses `record.get("quals") or {}` (matching the existing pattern in `_build_wd_context`) and `record.get("client_service_results") or ""` (matching the existing pattern). These are not deviations — they are the established v2.0 fallback idiom for the WD record dict.

## Issues Encountered

None - plan executed cleanly. All 8 new backend tests and 2 new frontend tests turned GREEN at the expected step. The 3 backend test count growth (160 → 172 across Plans 01+02) and 2 frontend test count growth (66 → 70) match the plan's expectations.

## User Setup Required

None - Plan 27-02 is pure code (no external services, no environment variables, no UI verification beyond what the automated tests cover). The Review-phase completeness badge renders the same in any browser session that has a stored WD row. The Phase 27 human UAT items (manually walking a WD through the conversation, observing the badge update, exporting at low completeness) will be captured in `27-HUMAN-UAT.md` if the user requests one.

## Next Phase Readiness

- **Plan 27-02 is structurally complete.** ELEM-01 (build_seven_elements + validate-elements), ELEM-02 (Review badge + soft gate), ELEM-03 (data-structure level). All 3 Plan 02 requirements closed. Co-update rule not applicable (no new typed WD fields in Plan 02). Phase 27 has 2 plans only — Plan 27-01 is also GREEN. Phase 27 overall is GREEN; no further plans in this phase.
- **Phase 29 SEXP-01/02 is unblocked.** It will reuse:
  - The `build_seven_elements(wd) -> dict` shared helper as the single source of truth for the 7 elements
  - The `POST /api/wd/{id}/validate-elements` endpoint pattern for any new value-export validation routes
  - The soft-gate pattern from ReviewState (the export buttons stay enabled regardless of any per-WD gating logic)
- **No blockers.** All 8 Phase 27 RED stubs from Plan 02 are GREEN; full suite (172 backend + 70 frontend) is GREEN; soft-gate guard test prevents the ROADMAP #5 regression; org-context audit guard test pins ROADMAP #4; responsibility missing-not-not_applicable test pins ROADMAP #3.
- **Phase 28 (Manager-Track UX) is the next phase to plan.** It builds on the existing conversational step + DocumentPane Sec + completeness badge patterns and will likely want to surface the completeness badge in the manager view as well.

## Self-Check: PASSED

Created/modified files verified on disk:
- FOUND: v2/backend/app/services/export_service.py (5b12e1f — build_seven_elements at line 425)
- FOUND: v2/backend/app/api/wd.py (1e29caf — validate-elements at line 334)
- FOUND: v2/frontend/src/conversation.jsx (8606831 — completeness prop + badge at line 189, 211)
- FOUND: v2/frontend/src/app.jsx (8606831 — completeness state at line 173, useEffect at line 252)
- FOUND: v2/backend/tests/test_export.py (5b12e1f — 5 build_seven_elements tests at line 728+)
- FOUND: v2/backend/tests/test_wd.py (1e29caf — 3 validate_elements tests at line 149+)
- FOUND: v2/frontend/src/conversation.test.jsx (8606831 — 2 completeness badge tests at line 840+)

Task commits verified in git log:
- FOUND: 5b12e1f (feat — Task 1: build_seven_elements shared helper)
- FOUND: 1e29caf (feat — Task 2: POST /api/wd/{id}/validate-elements endpoint)
- FOUND: 8606831 (feat — Task 3: Review-phase completeness badge soft gate)

Test counts verified:
- Backend: 172 passed, 0 failed (target was 164+; met — 164 baseline + 5 Task 1 + 3 Task 2)
- Frontend: 70 passed, 0 failed (target was 68+; met — 68 baseline + 2 Task 3)
- All 10 new tests (5 + 3 + 2) confirmed GREEN via the `-k` test selector and the full-suite run

Phase gate spot-checks verified:
- build_seven_elements helper: `grep -n "def build_seven_elements" v2/backend/app/services/export_service.py` → line 425 ✓
- validate-elements endpoint: `grep -n "validate-elements" v2/backend/app/api/wd.py` → line 334 (route decorator) ✓
- validate-elements → build_seven_elements wiring: `grep -n "build_seven_elements" v2/backend/app/api/wd.py` → lines 338, 351, 363 ✓
- 404 guard: `grep -n "raise HTTPException(status_code=404" v2/backend/app/api/wd.py` → 9 total (validate_elements adds one) ✓
- 5 build_seven_elements tests: `grep -c "def test_build_seven_elements" v2/backend/tests/test_export.py` → 5 ✓
- 3 validate_elements tests: `grep -c "def test_validate_elements" v2/backend/tests/test_wd.py` → 3 ✓
- Org context audit guard test: `grep -n "test_build_seven_elements_org_context_reads_typed_field" v2/backend/tests/test_export.py` → line 786 ✓
- Conversation.jsx completeness: `grep -n "completeness" v2/frontend/src/conversation.jsx` → 6 matches (prop + badge + comments) ✓
- app.jsx validate-elements: `grep -n "validate-elements" v2/frontend/src/app.jsx` → 3 matches (state, comment, fetch) ✓
- app.jsx completeness prop pass: `grep -n "completeness={completeness}" v2/frontend/src/app.jsx` → line 926 ✓
- Soft gate: `grep -n "disabled" v2/frontend/src/conversation.jsx` → only 2 matches (audit button `disabled={auditRunning}` + valid check); no completeness-dependent disabled ✓
- conversation.test.jsx completeness count: `grep -c "completeness" v2/frontend/src/conversation.test.jsx` → 16 matches (≥ 2 new tests confirmed) ✓

Final test verification:
- `cd v2/backend && python3 -m pytest -x -q` → 172 passed, 0 failed ✓
- `cd v2/frontend && npm test -- --run` → 70 passed, 0 failed ✓

---
*Phase: 27-responsibilities-narrative-completeness-audit*
*Plan: 02 (Wave 2 ELEM completeness audit)*
*Completed: 2026-06-24*
