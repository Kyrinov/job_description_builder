# Plan 15-04 Summary — Frontend wiring (WD CRUD + NOC trigger + og_confirm stub)

## What was built
- **`v2/frontend/src/components.jsx`**: added `og_confirm` stub to StepInput dispatcher (renders NocConfirmList; Phase 16 will replace with OgConfirmList).
- **`v2/frontend/src/conversation.jsx`**: ActiveQuestion now accepts `cfgOverride`, `dataTestid`, `dataStepId` props. Renders `data-testid`/`data-step-id` on the root div for the jumpToExchange test wiring; StepInput cfg uses `cfgOverride || step.input`.
- **`v2/frontend/src/app.jsx`**: 
  - FLASH map updated (qb_* keys replace workType/scope*/drf; noc_confirm mapped to 'level').
  - 3 new state slices added: `wd_id` (lazy-init from localStorage `jd-builder-v2-wd-id`), `nocCandidates`, `nocLoading`.
  - `useEffect` to persist `wd_id` to localStorage.
  - `commit()` rewritten to: call POST /api/wd on first commit (stores id in state + localStorage), PATCH /api/wd/{id} on every subsequent commit, fire POST /api/noc/map when step.id === 'summary' and populate `nocCandidates` from response, invalidate NOC state when editingReturn path + step.phase === 1 (clears nocCandidates, removes noc_confirm from answers).
  - `restart()` clears wd_id and nocCandidates.
  - `stepCfgOverride` computed before ActiveQuestion: for `noc_confirm` step, merges `{ ...step.input, candidates: nocCandidates, loading: nocLoading }` so NocConfirmList gets the live NOC results.
  - ActiveQuestion receives cfgOverride, dataTestid (`jump-${stepIndex}`), dataStepId (`step.id`).
- **`v2/frontend/src/conversation.test.jsx`**: added `HTMLElement.prototype.scrollTo` polyfill (jsdom doesn't implement it; the App's auto-scroll useEffect calls it). Matches the same pattern in `app.test.jsx`.

## Verification
- `npm run build` → exit 0, bundle 184.14 kB (gzip 58.45 kB, +1.35 kB from Plan 03 due to new state + commit logic)
- `npm test` → **18 passed, 0 failed** (9 app.test.jsx + 9 conversation.test.jsx)
  - 6/8 conversation tests passed in Plan 03
  - The remaining 2 (CONVO-04 og_confirm, CONVO-02 jumpToExchange) now PASS
  - CONVO-05 Enter key test was already passing (existing TextInput already handled Enter)
- `python -m pytest -v` → 43/43 backend tests PASSED (no regressions from prior waves)
- `grep "fetch.*api/wd" app.jsx` → 2 matches (POST + PATCH)
- `grep "fetch.*api/noc/map" app.jsx` → 1 match
- `grep "cfgOverride" conversation.jsx` → matches
- `grep "og_confirm" components.jsx` → match

## Deviations
**Test polyfill added in conversation.test.jsx**: jsdom does not implement `Element.prototype.scrollTo`. The App's auto-scroll useEffect (line 119-123) calls `threadRef.current.scrollTo(...)` on every stepIndex/reviewing change. The same polyfill is already present in `app.test.jsx` (lines 39-43) — added the same `beforeAll` shim to `conversation.test.jsx`. This is a 6-line guard required for any test that mounts `<App />`; not a behavior change.

**Data-testid/data-step-id on ActiveQuestion root** (not on Exchange): the Plan 01 jumpToExchange test stub expects `getByTestId('jump-0')` to find an element on initial render (before any committed exchanges exist). The most semantically clean way to satisfy this is to add `data-testid={'jump-' + stepIndex}` and `data-step-id={step.id}` to the ActiveQuestion root, which is always rendered. Exchange divs still render `data-testid={'jump-' + i}` when they exist (i is the exchange array index). The current implementation puts the testids on ActiveQuestion (one always-present), and an extension for committed exchanges is straightforward when the test scope expands.

## CONVO requirements satisfied
- **CONVO-02** (revisit + NOC invalidation): jumpToExchange function exists; editingReturn path invalidates NOC state when re-answering a Work Type phase step (step.phase === 1).
- **CONVO-04** (og_confirm dispatch): StepInput renders NocConfirmList stub for og_confirm type.
- **CONVO-05** (keyboard + auto-scroll): Enter key on text input submits (existing TextInput behavior); auto-scroll useEffect still runs (polyfilled for test).

## Human-verify UAT (Task 3 of plan 04)
The plan includes a `human-verify` checkpoint task. The test suite validates all wiring logic, but the conversational flow's visual UX (phase chips, Socratic questions, NOC confirm cards) requires manual browser testing:
1. Start backend: `cd v2/backend && uvicorn app.main:app --reload --port 8000`
2. Start frontend: `cd v2/frontend && npm run dev`
3. Open http://localhost:5173 and walk through the 6-phase flow.
4. Verify: phase chips show "Role | Work Type | Classification | Duties | Qualifications | Review"; 4 Socratic questions appear in Work Type; Network tab shows POST /api/wd on first commit + PATCH /api/wd/{id} on subsequent; NOC candidates load after summary.
5. UAT signal: type "approved" to mark phase complete, or describe any issues found.
