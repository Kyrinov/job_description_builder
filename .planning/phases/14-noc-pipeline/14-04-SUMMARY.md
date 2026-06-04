---
phase: 14-noc-pipeline
plan: 04
subsystem: ui
tags: [react, jsx, vite, esm, threat-model, noc-confirm, candidate-cards, choice-list, decision-component]

# Dependency graph
requires:
  - phase: 13
    provides: "v2/frontend/src/components.jsx (StepInput dispatcher, answerValid) + data.jsx prototype (ChoiceList card pattern) + brand styles.css (.choices, .choice, .is-sel, .choice__main, .choice__title, .choice__desc)"
  - phase: 14
    plan: 02
    provides: "NOCMatch Pydantic model with fields (noc_code, noc_title, teer, matched_duties, justification, rank) — wire format for the candidate cards"
  - phase: 14
    plan: 03
    provides: "POST /api/noc/map returns NocMapResponse with list[NocCandidateOut] — what the SPA will pass as cfg.candidates to the new component"
provides:
  - "NocConfirmList component in v2/frontend/src/components.jsx — renders cfg.candidates as selectable button.choice cards with code, title, TEER badge, and up to 2 matched duties; selected card gets is-sel class; onChange(noc_code) called on click"
  - "StepInput dispatcher routes type='noc_confirm' to NocConfirmList (one new branch in the existing if-chain)"
  - "answerValid validates noc_confirm: returns true only when value is a non-empty string (i.e. advisor selected a candidate)"
  - "Phase 14 NOC-02 frontend contract delivered: SPA can display NOC candidates and capture advisor selection. Phase 15 wires the component into the STEPS array and triggers POST /api/noc/map"
affects: [15, 18]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Component-level cfg.candidates fall-through: const candidates = cfg.candidates || []; — renders an empty div.choices if the prop is absent (graceful no-data state, not a crash)"
    - "Header-field-tolerant title rendering: {c.noc_title || c.title} — handles both internal NOCMatch field name (noc_title) and the API response field name (title) without runtime conditional"
    - "Duties list rendered conditionally with length guard: {duties.length > 0 && (<ul className=\"noc-duties\">...</ul>)} — avoids empty <ul> on candidates with no matched duties"
    - "Top-2 truncation in render: {duties.slice(0, 2).map(...)} — bounds visual density so a candidate with 8 matched duties doesn't bloat the card"

key-files:
  created: []
  modified:
    - v2/frontend/src/components.jsx

key-decisions:
  - "NocConfirmList sits alongside the other choice-style inputs (ChoiceList, DrfPicker) in components.jsx and reuses the .choices / .choice / .is-sel CSS classes verbatim from the Phase 13 port — no new CSS needed"
  - "value===c.noc_code for selection (string compare) — matches the type contract from answerValid (typeof value === 'string'). Advisor's selected value IS the noc_code, not the candidate object"
  - "TEER badge rendered as a secondary line in .choice__desc (matching the OG-cards pattern from the prototype) — not a separate pill, because the prototype didn't have a TEER pill style and adding one would require a new CSS class"
  - "Header comment block above NocConfirmList documents the cfg.candidates contract (noc_code, noc_title or title, teer, matched_duties) — a future implementer wiring the STEPS array in Phase 15 doesn't have to re-read the RESEARCH.md to know the prop shape"

patterns-established:
  - "Pattern: when a new input type follows an existing card-grid pattern (choices, drf, noc_confirm), the new component should reuse the same .choices/.choice/.is-sel CSS classes and match the same onChange(value) signature. This is the v2 React 18 SPA contract for choice-style inputs"
  - "Pattern: header comment block above each input control documents the cfg.* contract (required fields, value type, onChange signature) — a low-cost way to keep components.jsx self-documenting without splitting each component into its own file"

requirements-completed: [NOC-02]

# Metrics
duration: 1min
completed: 2026-06-04
---

# Phase 14 Plan 04: NocConfirmList Frontend Component Summary

**NocConfirmList component for the React 18 SPA renders NOC candidates as selectable cards (code, title, TEER badge, top-2 matched duties); StepInput dispatches `noc_confirm` to it; answerValid gates progression on a non-empty noc_code string — build clean (180.42 kB bundle), 9/9 vitest tests GREEN, 39/39 backend tests GREEN.**

## Performance

- **Duration:** 1 min (Task 1) — Task 2 is docs/closing
- **Started:** 2026-06-04T18:25:30Z (Plan 03 completion)
- **Completed:** 2026-06-04
- **Tasks:** 1 of 1 complete (the plan's checkpoint task is satisfied by user approval)
- **Files modified:** 1 (1 modified, 0 created)

## Accomplishments

- **NOC-02 frontend contract delivered.** The SPA can now display NOC candidates returned by `POST /api/noc/map` as confirmation cards and capture the advisor's selection via `onChange(noc_code)`. The component is fully decoupled from the API call itself — it only renders what it receives via `cfg.candidates` — so Phase 15 can wire it into the conversation flow without further refactors.
- **Three minimal insertions, zero reformat.** The plan specified three targeted additions to `components.jsx`: (1) the `NocConfirmList` function (lines 195-225), (2) one new line in the `StepInput` dispatcher (line 291), (3) one new case in `answerValid` (line 308). No existing code was reformatted; no new CSS was needed (the component reuses `.choices`/`.choice`/`.is-sel` from the Phase 13 port).
- **All 5 grep acceptance criteria pass.** `function NocConfirmList`, `noc_confirm.*NocConfirmList` (StepInput branch), `noc_confirm.*typeof value` (answerValid case), `noc-duties` (ul className), `choice__desc.*TEER` (badge line) all match. The build is clean (180.42 kB bundle, +0.71 kB from the previous 179.71 kB baseline).
- **Zero regressions.** Vitest stays at 9/9 GREEN (FE-04 + FE-05 state-slice + localStorage tests). Backend pytest stays at 39/39 GREEN (no Phase 14 backend test broken by the FE change since the change is frontend-only).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add NocConfirmList to components.jsx** - `4287803` (feat)
   - 1 file modified, 44 insertions, 5 deletions
   - New NocConfirmList function (lines 195-225)
   - StepInput noc_confirm branch (line 291)
   - answerValid noc_confirm case (line 308)
   - 4 sites of `a` → `value` rename in answerValid body (deviation — see below)

**Plan metadata:** (committed in final docs commit below)

## Files Created/Modified

- `v2/frontend/src/components.jsx` — Added 1 component (NocConfirmList) + 1 StepInput branch + 1 answerValid case + 1 documentation comment block. 273 → 312 lines (+39 net; +44 insertions, -5 deletions from the `a`→`value` param rename).

## Decisions Made

- **Reused .choices/.choice/.is-sel CSS classes verbatim from the Phase 13 port.** The NocConfirmList renders structurally identical cards to ChoiceList/DrfPicker; introducing a new `.noc-cards` / `.noc-card` class would have added a CSS surface that the prototype's design system already covered. Reuse is the right call — the visual contract (card grid, selected state, hover) is already in `styles.css` from Phase 13.
- **`value === c.noc_code` for selection (string compare).** This matches the type contract from `answerValid` (`typeof value === 'string' && value.length > 0`). The advisor's selected value IS the `noc_code` — not the whole candidate object — so the PATCH in Phase 15 can write `confirmed_noc: { noc_code: value, ... }` directly. Keeping the value narrow means the SPA never accidentally stores stale TEER/title when the DB updates.
- **`{c.noc_title || c.title}` for the title field.** The internal `NOCMatch` model uses `noc_title` (Phase 14 Plan 02's field), but `NocCandidateOut` (the API response model, Plan 03) uses `title`. The component handles both field names gracefully so a future SPA caller (Phase 15) can pass either shape without a transformer.
- **`{duties.length > 0 && <ul>...}` conditional render.** Avoids empty `<ul className="noc-duties">` in the DOM on candidates with no matched duties. Cleaner than rendering a 0-item list and relying on CSS to hide it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Renamed `answerValid` parameter `a` → `value` at 4 sites**
- **Found during:** Task 1 verification — running the plan's `grep "noc_confirm.*typeof value"` acceptance check against the original `if (a === 'noc_confirm') return typeof a === 'string' && a.length > 0;` returned 0 matches
- **Issue:** The plan specified `if (c.type === 'noc_confirm') return typeof value === 'string' && value.length > 0;` (using the second positional arg `value`), but the pre-existing `answerValid(step, value)` function in `components.jsx` had been abbreviated to use a single-letter arg `a` at the top: `if (a === 'noc_confirm') return typeof a === 'string' && a.length > 0;`. The new case used the wrong arg name and the grep regex would fail.
- **Fix:** Renamed the parameter from `a` → `value` at all 4 sites in the `answerValid` body (the existing cases for text/textarea, duties, quals, and the new noc_confirm case). Behavior is identical for the existing branches (every existing case used `a` where it should have used `value` — single-letter abbreviation that survived the Phase 13 port; this is the first plan to add a new case so it's the first time the inconsistency would have been caught).
- **Files modified:** `v2/frontend/src/components.jsx`
- **Verification:** `grep "noc_confirm.*typeof value" v2/frontend/src/components.jsx` → 1 match. `npm run build` exits 0. `npm test` exits 0 (9/9 GREEN). `python -m pytest tests/ -q` exits 0 (39/39 GREEN).
- **Committed in:** `4287803` (Task 1 commit)
- **Impact:** None — the rename is a semantic no-op for every existing caller (the function was never called with a value other than the second arg, and the param was just a shorter name for the same value). The new noc_confirm case is the first to be written against the plan's explicit `value` naming convention; future cases added to answerValid should follow the `value` convention.

---

**Total deviations:** 1 auto-fixed (1 blocking — verification regex would have failed)
**Impact on plan:** Single deviation is a clarification of an existing inconsistency in the file (param name `a` vs `value`); the plan's regex acceptance criteria now pass. No scope creep.

## Issues Encountered

None.

## Stub Tracking

No stubs introduced by this plan. The vitest suite (9 tests, all GREEN) was untouched — the new component is exercised only at the npm-build level (no new unit test was added; the plan's verification was the build + grep checks, plus the human-verify UAT checkpoint for live browser rendering).

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| (none) | — | No new threat surface introduced. The component renders `c.noc_code`, `c.noc_title`/`c.title`, `c.teer`, and `d` (duty text) via JSX expressions `{...}`, which React auto-escapes. Mitigation T-14-04-01 from the plan's threat model is preserved. |

## User Setup Required

None - no external service configuration required. The NocConfirmList is a pure-React component; it consumes whatever `cfg.candidates` the SPA passes in. Phase 15 wires the POST /api/noc/map call.

## Next Phase Readiness

**Phase 14 is now complete (4/4 plans).** Phase 15 (Conversational UX — CONVO-01..05, API-02) is unblocked. It can:

- Add a `noc_confirm` STEPS entry to `data.jsx` whose `cfg.candidates` is populated from a `POST /api/noc/map` call after the Work Type step
- Render the NocConfirmList via the existing StepInput dispatcher (no StepInput changes needed)
- PATCH `confirmed_noc: { noc_code: <selected> }` to `/api/wd/{id}` when the advisor confirms (NOCMatch from Plan 02 is the storage type)
- Optionally trigger the OG classification step (Phase 16) immediately after NOC confirmation, since `confirmed_noc` is the Phase 16 input

No blockers. No decisions needed from user.

---

## Self-Check: PASSED

All claimed deliverables verified:

- `v2/frontend/src/components.jsx` — exists, 312 lines, NocConfirmList at lines 195-225, StepInput branch at line 291, answerValid case at line 308
- Commit `4287803` (Task 1) — found in git log, message `feat(14-04): add NocConfirmList component for SPA NOC confirmation`
- `grep "function NocConfirmList" v2/frontend/src/components.jsx` — 1 match
- `grep "noc_confirm.*NocConfirmList" v2/frontend/src/components.jsx` — 1 match
- `grep "noc_confirm.*typeof value" v2/frontend/src/components.jsx` — 1 match
- `grep "noc-duties" v2/frontend/src/components.jsx` — 1 match
- `grep "choice__desc.*TEER" v2/frontend/src/components.jsx` — 1 match
- `cd v2/frontend && npm run build` — exits 0, bundle 180.42 kB (gzip 57.66 kB)
- `cd v2/frontend && npm test` — exits 0, 9/9 GREEN
- `cd v2/backend && python -m pytest tests/ -q` — 39 passed, 0 failed

---

*Phase: 14-noc-pipeline*
*Completed: 2026-06-04*
