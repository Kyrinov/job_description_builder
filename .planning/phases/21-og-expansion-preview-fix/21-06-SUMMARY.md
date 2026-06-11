---
phase: 21-og-expansion-preview-fix
plan: 06
subsystem: classification
tags: [fastapi, pydantic, react, css, sub-group-disambiguation, t-21-01, bugfix]

# Dependency graph
requires:
  - phase: 21-03
    provides: SUBGROUP_DISAMBIGUATIONS constant + SUBGROUP_DISAMBIGUATIONS dict
  - phase: 21-04
    provides: confirmed_sub_group field on WorkDescription + jes_service routing
  - phase: 21-05
    provides: extended QUESTION_BANK with sector-gate + cluster questions
provides:
  - SubGroupAlert Pydantic model
  - subgroup_alert field on OGClassifyResponse
  - confirmed_og field on OGClassifyRequest
  - ALLOWED_SUBGROUPS frozenset for T-21-01 input validation
  - POST /api/wd/{wd_id}/confirm-subgroup endpoint (T-21-01 secured)
  - .asec-alert CSS block (closes pre-existing Phase 16 gap)
  - OgConfirmList sub-group picker (OGX-07)
  - Sector/cluster question gating by qb_sector_gate answer (OGX-04 fix)
  - isStepVisible / getVisibleSteps helpers in data.jsx
affects: [22-sjd-library, 23-writing-guide, 24-risk-audit, 25-accessible-template]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ALLOWED_SUBGROUPS frozenset validation pattern for sub-group inputs (T-21-01)"
    - "Sub-group picker in OgConfirmList reuses .asec-alert CSS pattern"
    - "Local state for sub-group selection with useState + useEffect reset on OG change"
    - "Self-contained component fetch: OgConfirmList re-calls /api/og/classify with confirmed_og in the body when value.og_code is NU/SW/ED"
    - "isStepVisible step predicate pattern for Socratic-question gating"
    - "activeStepIndex derived from stepIndex + answers — never land on invisible step"

key-files:
  created: []
  modified:
    - v2/backend/app/api/og_classification.py
    - v2/frontend/src/components.jsx
    - v2/frontend/src/styles.css
    - v2/frontend/src/app.jsx
    - v2/frontend/src/data.jsx
    - v2/frontend/src/conversation.test.jsx

key-decisions:
  - "Confirmed sub_group validation: ALLOWED_SUBGROUPS frozenset lookup is O(1) and immutable"
  - "Picker only renders after OG is selected (selectedCode && in [NU, SW, ED])"
  - "Group-specific title text guarded by unique sub-group code marker (HOS/SCW/EDS) to prevent wrong-title bleeding"
  - "Local state is source of truth for sub-group UI; API call is fire-and-forget with cfg.wd_id"
  - "Sub-group alert is fetched inside OgConfirmList (not in app.jsx) so the picker renders during the og_confirm step, not after commit"
  - "Cluster questions are gated on the qb_sector_gate answer — only the cluster matching the selected sector is asked"
  - "activeStepIndex is derived from stepIndex + answers so the user never lands on an invisible step even after editing a prior answer"
  - "answeredSteps is filtered to only include steps with answers (OGX-04 round 3) — preserves the original STEPS index for jumpToExchange correctness"

patterns-established:
  - "Pattern: API sub-group validation — return 422 with detail={error, message, allowed_values} for invalid sub_group"
  - "Pattern: Reuse .asec-alert CSS for both OG (ASEC) and sub-group (NU/SW/ED) alerts — no new component"
  - "Pattern: Reset local state on parent state change via useEffect([selectedCode])"
  - "Pattern: Component fetches its own dynamic data when value-derived state changes (subGroupAlert re-fetch in OgConfirmList)"
  - "Pattern: isStepVisible predicate for Socratic question gating — return false when upstream answer makes the step irrelevant"
  - "Pattern: When gating steps, also filter the answered-exchanges list to drop skipped (unanswered) steps — otherwise their transcripts throw on undefined and unmount the React tree"

requirements-completed:
  - OGX-07
  - OGX-04

# Metrics
duration: 105min
completed: 2026-06-11
---
# Phase 21 Plan 06: Sub-Group Disambiguation Alert + Confirm Endpoint Summary

**Sub-group disambiguation alert (NU/SW/ED) wired into OG classification API and frontend, with frozenset-validated confirm-subgroup endpoint (T-21-01), and continuation fixes for the two bugs the user surfaced after the initial automated completion (sub-group picker not rendering, sector/cluster questions asked on every pass).**

## Performance

- **Duration:** 90 min total (60 min initial implementation + 30 min continuation bugfixes)
- **Started:** 2026-06-10T20:54:36Z
- **Completed:** 2026-06-11T09:22:31Z
- **Tasks completed:** 3 of 3 (Tasks 1-2 implementation, Task 3 human-verify → continuation fix branch)
- **Files modified:** 6 (1 backend, 4 frontend, 1 test)
- **Commits:** 4 (2 feat initial + 2 fix continuation)

## Accomplishments

### Initial Implementation (Tasks 1-2, automated)

- All 5 OGX-07 tests GREEN: `test_nu_disambiguation_alert_fires`, `test_sw_disambiguation_alert_fires`, `test_ed_disambiguation_alert_fires`, `test_confirmed_og_outside_subgroup_set_returns_no_alert`, `test_confirmed_sub_group_invalid_value_returns_422` (T-21-01 security test)
- SubGroupAlert Pydantic model, `confirmed_og` request field, `subgroup_alert` response field, and `ALLOWED_SUBGROUPS` frozenset map added to `og_classification.py`
- `POST /api/wd/{wd_id}/confirm-subgroup` endpoint with T-21-01 validation: 422 + `allowed_values` list on invalid input
- `.asec-alert` CSS block authored in `styles.css` (closes pre-existing Phase 16 gap — the JSX has been using this class since Phase 16 with no defined style)
- OgConfirmList extended with sub-group picker: group-specific title text, choice cards with code+name + full description, `useState`/`useEffect` for selection state, fires `POST /api/wd/{id}/confirm-subgroup` when `cfg.wd_id` is set
- Full backend test suite GREEN: 103/103 tests
- Full frontend vitest suite GREEN: 31/31 tests
- Frontend build clean: 214.85 kB JS / 24.86 kB CSS (gzip 66.09 kB / 5.50 kB)

### Continuation Fixes (Task 3 — bugs reported after manual UI verification)

The user surfaced two bugs after the automated tests passed:

1. **Bug 1: Sub-group picker did not render in the running app**
   - **Symptom:** No `.asec-alert` block appeared when the user confirmed NU/SW/ED as the OG
   - **Root cause:** `cfgOverride` in `app.jsx` did not pass `subgroup_alert` to `OgConfirmList`, AND the `/api/og/classify` call at `noc_confirm` commit time did not include `confirmed_og` in the request body. The API returns `subgroup_alert` only when `confirmed_og` is set to NU/SW/ED; without that, the alert is always `null` regardless of which OG the user picks
   - **First fix attempt (rejected):** Added a `useEffect` in `app.jsx` that watched `record.confirmed_og` and re-called the API. This fired only AFTER `commit()` updated `record.confirmed_og`, which is too late — the picker needs to appear during `og_confirm` (after the user picks NU in the draft but before clicking Continue)
   - **Final fix:** Made `OgConfirmList` self-contained. When the user picks a sub-group-bearing OG in the draft (value.og_code in NU/SW/ED), the component fires a local `useEffect` that re-calls `/api/og/classify` with `confirmed_og` populated. The picker renders as soon as the API responds. The `app.jsx` `cfgOverride` now passes `work_description`, `confirmed_noc_code`, and `wd_id` so the re-fetch has enough context and the picker can persist selections

2. **Bug 2: Sector/cluster questions fired on every pass regardless of context**
   - **Symptom:** The healthcare/legal/education/technical cluster questions were posed to the user even when the sector-gate answer was for a different cluster
   - **Root cause:** The 5 sector/cluster question steps added in Plan 05 (`qb_sector_gate`, `qb_health_social_cluster`, `qb_legal_cluster`, `qb_technical_cluster`, `qb_education_cluster`) are all unconditionally in the linear `STEPS` array. There was no gating logic to skip cluster questions whose sector wasn't selected
   - **Fix:** Added `isStepVisible(step, answers)` predicate to `data.jsx` that gates each cluster question on the corresponding `qb_sector_gate` answer. `getVisibleSteps(STEPS, answers)` filters the STEPS array. In `app.jsx`:
     - `activeStepIndex` is now derived from `stepIndex + answers` so the user never lands on an invisible step
     - `commit()` advances to the next visible step (walking past any invisible ones)
     - `goBack()` walks backward past invisible steps

### Continuation Test Results

- 10 new frontend tests (8 OGX-04 gating + 2 OGX-07 picker)
- Frontend: 41/41 tests pass (was 31/31)
- Backend: 103/103 tests pass (no regression)
- Frontend build clean: 216.05 kB JS / 24.86 kB CSS (gzip 66.40 kB / 5.50 kB) — ~1.2 kB increase from the two extra useEffects + helpers

### Bugfix Round 3 (after round-2 verification surfaced a screen-blank bug)

After the round-2 fixes, the user ran manual verification again and reported a critical regression: "After selection of patient care, the screen goes blank." This was a runtime error that the automated tests had not caught because no test drove the App end-to-end through the cluster step.

3. **Bug 3: Screen went blank after picking a cluster option**
   - **Symptom:** After picking "Direct patient care" (nursing_hospital) in `qb_health_social_cluster` and clicking Continue, the entire React tree unmounted and the screen went blank
   - **Root cause:** When the user picks a cluster option, `commit()` advances `stepIndex` from 11 → 15 (skipping 3 invisible cluster steps at indices 12, 13, 14 — `qb_legal_cluster`, `qb_technical_cluster`, `qb_education_cluster`). The previous fix made the gate correctly skip those steps in the navigation flow. **However**, `answeredSteps = STEPS.slice(0, stepIndex)` was still being passed unmodified to the answered-exchanges renderer, so it included those 3 invisible cluster questions. The `<Exchange>` component then called `step.transcript(answer, record)` — and the cluster transcripts are `a => a.title`. With `answer === undefined` (the user never answered them), this threw `TypeError: Cannot read properties of undefined (reading 'title')`. React unmounted the whole tree → blank screen
   - **Why automated tests missed it:** The 8 OGX-04 gating tests in round 2 only tested `isStepVisible()` and `getVisibleSteps()` as pure functions. They did not drive the App component through the full conversation flow to the cluster step. The bug was an integration bug — the gate logic was correct, but `answeredSteps` was still pulling from the unfiltered `STEPS` array
   - **Fix:** Filter `answeredSteps` in `app.jsx` to only include steps that were actually answered (`answers[step.id] !== undefined`). Preserve the original `STEPS` index in `originalIndex` so `jumpToExchange(originalIndex)` still navigates to the correct step (the array index in the filtered list would be wrong otherwise)
   - **Files modified:** `v2/frontend/src/app.jsx`
   - **Tests added:** 2 new frontend tests in `conversation.test.jsx` — one walks the full App from `title` through `qb_health_social_cluster` (pick "Direct patient care") to `noc_confirm` and asserts the next active question renders; the other is a smoke test that exercises the other 3 sector routes (legal, technical, education) end-to-end, asserting that none of them blank the screen
   - **Verification:** Tests fail RED before the fix with the exact TypeError (matching the user's report); tests pass GREEN after the fix
   - **Committed in:** `44153ee`

### Continuation Test Results (after round 3)

- 12 new frontend tests total (8 OGX-04 gating + 2 OGX-07 picker + 2 OGX-04 round-3 regression)
- Frontend: 43/43 tests pass (was 31/31, then 41/41 after round 2)
- Backend: 103/103 tests pass (no regression)
- Frontend build clean: 216.17 kB JS / 24.86 kB CSS (gzip 66.46 kB / 5.50 kB) — +0.12 kB JS from the answeredSteps filter

## Task Commits

Each task was committed atomically:

1. **Task 1: Add SubGroupAlert model, request/response fields, and confirm-subgroup endpoint** - `680cf12` (feat)
2. **Task 2: Author .asec-alert CSS and extend OgConfirmList with sub-group picker** - `e10917a` (feat)
3. **Continuation fix 1: Sector/cluster question gating (OGX-04)** - `f6ae8c7` (fix)
4. **Continuation fix 2: Sub-group picker render during og_confirm step (OGX-07)** - `ca44700` (fix)
5. **Continuation fix 3: Filter unanswered cluster steps from answered list (OGX-04 round 3)** - `44153ee` (fix)

## Files Created/Modified

### Initial Implementation

- `v2/backend/app/api/og_classification.py` - Added `SUBGROUP_DISAMBIGUATIONS` import, `ALLOWED_SUBGROUPS` constant, `SubGroupAlert` model, `SubGroupConfirmRequest` model, `confirmed_og` field on `OGClassifyRequest`, `subgroup_alert` field on `OGClassifyResponse`, subgroup_alert trigger logic in `classify_og`, and new `POST /api/wd/{wd_id}/confirm-subgroup` endpoint with T-21-01 frozenset validation and 422 response
- `v2/frontend/src/styles.css` - Authored `.asec-alert`, `.asec-alert__title`, `.asec-alert__body`, `.asec-alert__cite` CSS block (30 lines) per UI-SPEC color/typography contract
- `v2/frontend/src/components.jsx` - Extended `OgConfirmList` to extract `cfg.subgroup_alert`, hold `selectedSubGroup` local state, reset on OG change via `useEffect`, render the sub-group picker conditionally (only when selected OG is NU/SW/ED), and POST sub-group selection to `/api/wd/{id}/confirm-subgroup`

### Continuation Fixes

- `v2/frontend/src/data.jsx` - Added `isStepVisible(step, answers)` predicate that gates the 4 cluster questions on the corresponding `qb_sector_gate` answer; added `getVisibleSteps(STEPS, answers)` helper that filters STEPS by the predicate
- `v2/frontend/src/app.jsx` - Imported `getVisibleSteps, isStepVisible` from data.jsx. Added `activeStepIndex` derived from `stepIndex + answers` so the user never lands on an invisible step. Updated `commit()` to advance to the next visible step (walking past any invisible ones). Updated `goBack()` to walk backward past invisible steps. Updated `cfgOverride` for `og_confirm` to pass `work_description`, `confirmed_noc_code`, and `wd_id` so the re-fetch has enough context
- `v2/frontend/src/components.jsx` - Refactored `OgConfirmList` to fetch its own `subgroup_alert` when the user picks a sub-group-bearing OG in the draft. The local `useEffect` re-calls `/api/og/classify` with `confirmed_og` in the body; the picker renders as soon as the API responds. Uses `AbortController` for clean cancellation when the user changes the OG pick
- `v2/frontend/src/conversation.test.jsx` - Added 10 new tests: 8 OGX-04 gating tests (sector → cluster, default-gating, all-cluster-hidden-when-no-sector) + 2 OGX-07 picker tests (renders for NU with mocked API, hidden for EC, fetch payload contains confirmed_og)

## Decisions Made

### Initial Implementation

- **ALLOWED_SUBGROUPS is module-level constant in `og_classification.py`** rather than in `constants.py` — keeps the T-21-01 validation rule colocated with the endpoint that uses it, and `constants.py` already exposes `SUBGROUP_DISAMBIGUATIONS` (for the alert payload) which is the data counterpart
- **Confirmed sub_group validation uses `frozenset` membership check** — O(1) lookup and the set is immutable, preventing accidental mutation from the API layer
- **Picker renders AFTER the candidate list, not before** — UX: the user picks an OG first, then the sub-group picker appears as a sub-step within the same `og_confirm` step
- **Sub-group choice card title format is `<code> — <short name>` (e.g., "HOS — Hospital Nursing")** per UI-SPEC copywriting contract, with full description in `choice__desc`
- **Group-specific title text guarded by unique sub-group code marker** — `'HOS'` for NU, `'SCW'` for SW, `'EDS'` for ED. Avoids wrong-title bleeding if a future refactor consolidates the rendering
- **Local state is source of truth for sub-group UI** — `setSelectedSubGroup(sg)` updates state immediately, the API call is fire-and-forget. The user sees the selection reflected instantly; the 422 path only triggers if `SUBGROUP_DISAMBIGUATIONS` is bypassed server-side (which our test suite guards against)
- **`useEffect([selectedCode])` resets `selectedSubGroup` when user changes the OG pick** — prevents stale sub-group from showing when the user switches from NU to EC

### Continuation Fixes

- **Sub-group alert is fetched inside `OgConfirmList` (not in app.jsx)** — the picker must appear during the `og_confirm` step, which means it must react to the DRAFT (value) changing, not the committed `record.confirmed_og`. Putting the fetch inside the component keeps the data flow local to the picker and avoids the timing race in the previous app-level useEffect
- **The re-fetch includes `confirmed_og: selectedCode` in the body** — this is the original API contract; the API returns `subgroup_alert` only when `confirmed_og` is set to NU/SW/ED. By re-calling with the picked OG, the picker gets the right data for the picked group
- **`AbortController` cancels in-flight requests when the user changes the OG pick** — prevents a stale response (e.g., from NU) from overriding the current selection (e.g., SW). The cancel is silent; no error is shown to the user
- **Cluster questions are hidden when the sector answer is missing** — the linear flow guarantees the user encounters the sector question first (answerValid blocks Continue without an answer), so cluster questions are never shown in the linear path until the sector matches. This is the gating that prevents the "questions fire on every pass" bug
- **`activeStepIndex` is derived, not stored** — keeps `stepIndex` as the single source of truth for "where the user is in the linear flow", while `activeStepIndex` is the render-time view that respects visibility. The user can edit a prior answer without their position in the flow being corrupted by stale derived state

**5. [Rule 1 - Bug] Screen went blank after picking a cluster option (round 3)**
- **Found during:** Post-round-2 user verification — user reported "After selection of patient care, the screen goes blank"
- **Issue:** `answeredSteps = STEPS.slice(0, stepIndex)` included 3 invisible cluster questions (legal/technical/education) that the OGX-04 visibility gate had skipped. The user never answered them, so `answer === undefined`. The `<Exchange>` component called `transcript(undefined, record)` — and the cluster transcripts are `a => a.title`, which throws `TypeError: Cannot read properties of undefined (reading 'title')`. React's error boundary then unmounts the entire tree → blank screen
- **Fix:** Filter `answeredSteps` in `app.jsx` to only include steps that have an answer (`answers[step.id] !== undefined`). Preserve the original `STEPS` index in `originalIndex` so `jumpToExchange(originalIndex)` still navigates to the right step. The filter is in a `useMemo` keyed on `[stepIndex, answers]` so the rendered list re-computes correctly when the user revisits answers
- **Files modified:** `v2/frontend/src/app.jsx`
- **Verification:** 2 new frontend tests cover (a) the full App walkthrough from `title` through `qb_health_social_cluster` (pick "Direct patient care") to `noc_confirm` with screen-blank assertion, (b) smoke test for the other 3 sector routes (legal, technical, education). Both tests fail RED before the fix with the exact TypeError; both pass GREEN after
- **Committed in:** `44153ee`

---

## Deviations from Plan

### Auto-fixed Issues (Initial Implementation)

**1. [Rule 1 - Pre-existing code reuse] Part B (WorkDescription.confirmed_sub_group) was a no-op**
- **Found during:** Task 1 (verification of pre-existing state)
- **Issue:** The plan called for adding `confirmed_sub_group: Optional[str] = None` to the `WorkDescription` model in `v2/backend/app/models/work_description.py`. The field already exists at line 53 with the comment `# Phase 21: NU/SW/ED sub-group (e.g. "SCW", "CHA", "EDS")` — it was added in Plan 04's commit `eefcfd8` as part of the `WDPatchRequest` model extension (the WDPatchRequest on `wd.py` line 53 already has this field too).
- **Fix:** No code change needed; documented the prior addition in the Task 1 commit message so the audit trail is clear
- **Files modified:** none
- **Verification:** `grep "confirmed_sub_group" v2/backend/app/models/work_description.py` returns 1 match (line 53); same grep against `v2/backend/app/api/wd.py` returns 1 match (line 53)
- **Committed in:** noted in `680cf12` (Task 1 commit) commit message; no separate commit needed

**2. [Rule 3 - Blocking] TDD RED state was pre-existing in the test file**
- **Found during:** Task 1 setup (test verification)
- **Issue:** The plan called for TDD with separate RED → GREEN commits. The 5 OGX-07 tests already existed in `test_og_classification.py` (lines 181–277), authored in Plan 03 and Plan 04. Running them against the pre-implementation code showed 4 of 5 already failing (the 5th passed by default because `subgroup_alert` defaulted to `None`).
- **Fix:** Skipped the redundant RED commit; ran tests once to confirm RED state (4 failed, 1 passed), then proceeded directly to GREEN implementation. A single `feat` commit captures the RED→GREEN transition
- **Files modified:** none
- **Verification:** Pre-implementation: 4 failed, 12 passed. Post-implementation: 16 passed in `test_og_classification.py`
- **Committed in:** `680cf12` (Task 1 commit)

### Auto-fixed Issues (Continuation Fixes)

**3. [Rule 1 - Bug] Sub-group picker did not render**
- **Found during:** Task 3 (human-verify checkpoint) — user feedback after manual UI testing
- **Issue:** Even with passing automated tests, the sub-group picker never appeared in the running app. Two root causes: (a) `cfgOverride` did not pass `subgroup_alert` to `OgConfirmList`; (b) the API call at `noc_confirm` commit did not include `confirmed_og` in the body, so the API always returned `subgroup_alert: null`
- **First fix attempt:** Added an app-level `useEffect` watching `record.confirmed_og` to re-call the API. This was rejected during code review because the picker must appear DURING the `og_confirm` step (after the user picks NU in the draft), not after `commit()` updates `record.confirmed_og`
- **Final fix:** Made `OgConfirmList` self-contained — added a local `useEffect` that watches `selectedCode` (from `value.og_code`) and re-calls the API with `confirmed_og` in the body. The picker renders as soon as the API responds. `app.jsx` `cfgOverride` updated to pass `work_description`, `confirmed_noc_code`, and `wd_id` so the re-fetch has enough context
- **Files modified:** `v2/frontend/src/components.jsx`, `v2/frontend/src/app.jsx`
- **Verification:** 2 new frontend tests cover (a) picker renders when value is NU + API returns alert, (b) picker does NOT render when value is EC. All 41 frontend tests pass
- **Committed in:** `ca44700`

**4. [Rule 1 - Bug] Sector/cluster questions fired on every pass**
- **Found during:** Task 3 (human-verify checkpoint) — user feedback
- **Issue:** All 5 sector/cluster questions in the linear `STEPS` array were asked on every pass, even when the sector-gate answer was for a different cluster. This forced the user to choose duties for groups that didn't apply, violating the Socratic intent ("manager never asked questions irrelevant to their OG")
- **Fix:** Added `isStepVisible(step, answers)` predicate to `data.jsx` that gates each cluster question on the corresponding `qb_sector_gate` answer. `getVisibleSteps(STEPS, answers)` filters the STEPS array. In `app.jsx`, derived `activeStepIndex` from `stepIndex + answers` and updated `commit()` / `goBack()` to walk past invisible steps
- **Files modified:** `v2/frontend/src/data.jsx`, `v2/frontend/src/app.jsx`, `v2/frontend/src/conversation.test.jsx`
- **Verification:** 8 new frontend tests cover the 4 cluster-gating cases (each sector routes to its matching cluster), the default-gating case (no sector answer → all clusters hidden), the always-visible case (other steps are not gated), and the `getVisibleSteps` integration (legal_sector omits 3 non-matching clusters, returns 16 visible steps with no sector answer)
- **Committed in:** `f6ae8c7`

---

**Total deviations:** 5 auto-fixed (2 initial: pre-existing code reuse + RED-state pre-existing; 3 continuation: sub-group picker not rendering + sector/cluster gating missing + screen-blank after cluster commit)
**Impact on plan:** The 2 initial deviations eliminated redundant work. The 3 continuation fixes are real bugs that the automated tests didn't catch — the tests verified the component contract (picker renders when given the data) but not the integration (app.jsx correctly passes the data, and the answered-exchanges list doesn't include unanswered steps). The continuation fixes are minimal and targeted, preserving the original architecture while closing the user-visible gaps.

## Issues Encountered

- **Initial fix for Bug 1 (sub-group picker) was wrong** — the first attempt added an app-level useEffect watching `record.confirmed_og`. This fired too late (after commit), so the picker would never appear during the og_confirm step. The fix was rejected during self-review and replaced with a self-contained component-level useEffect watching the DRAFT (value.og_code)
- **Test mismatch when refactoring Bug 1** — the original test passed `cfg.subgroup_alert` directly, but the new self-contained approach fetches it from the API. The test was updated to mock `fetch` and assert the API call payload contains `confirmed_og: 'NU'`
- **No backend test changes were required for the continuation fixes** — the backend API contract was already correct (subgroup_alert returned when confirmed_og is in the SUBGROUP_DISAMBIGUATIONS map). The bugs were entirely in the frontend integration

## Checkpoint Status

### Task 3: `checkpoint:human-verify` (gate=blocking) — ✅ COMPLETED via continuation fix branch

The original plan's Task 3 was a `type="checkpoint:human-verify"` task with `gate="blocking"`. The user ran the manual verification, surfaced two bugs, and the orchestrator spawned a continuation agent to fix them. Both bugs are now fixed and verified by 10 new automated tests.

**What was built (Tasks 1 and 2 initial automated work):**
- Sub-group disambiguation API: `POST /api/og/classify` returns `subgroup_alert` when `confirmed_og` is NU, SW, or ED
- `POST /api/wd/{id}/confirm-subgroup` endpoint with T-21-01 frozenset validation (422 + `allowed_values` on invalid)
- Frontend sub-group picker in `OgConfirmList` (renders after OG selection, uses `.asec-alert` CSS, group-specific title text, sub-group choice cards)
- `.asec-alert` CSS block (background `var(--accent-soft)`, border `var(--accent-line)`, BEM children for title/body/cite)
- `.doc-scroll` already has `align-items: flex-start` from Plan 02 (UI-01 fix)

**What was fixed (continuation work):**
- **Bug 1 (sub-group picker):** Self-contained `useEffect` in `OgConfirmList` re-calls `/api/og/classify` with `confirmed_og` in the body when the user picks NU/SW/ED in the draft. The picker now renders as soon as the API responds
- **Bug 2 (sector/cluster gating):** `isStepVisible` predicate in `data.jsx` gates the 4 cluster questions on the corresponding `qb_sector_gate` answer. `getVisibleSteps` filters the STEPS array. `app.jsx` derives `activeStepIndex` from `stepIndex + answers` so the user never lands on an invisible step

## Next Phase Readiness

- OGX-07 + OGX-04 (continuation) complete. All Phase 21 plans (21-01 through 21-06) executed
- Phase 22 (SJD Library) is unblocked — can start
- No blockers or concerns
- The 5 OGX-07 tests committed in Plan 03/04/06 + 10 new OGX-04/OGX-07 tests in the continuation fix are all green
- Frontend test suite grew from 31 → 41 (10 new tests cover the bug regressions)
- Backend test suite unchanged at 103 (no backend changes were needed for the continuation fixes)

## Self-Check: PASSED

- `.planning/phases/21-og-expansion-preview-fix/21-06-SUMMARY.md` exists
- `v2/backend/app/api/og_classification.py` exists (modified)
- `v2/frontend/src/components.jsx` exists (modified — sub-group picker + self-contained fetch)
- `v2/frontend/src/styles.css` exists (modified — `.asec-alert` CSS block)
- `v2/frontend/src/app.jsx` exists (modified — `activeStepIndex`, gated navigation, `cfgOverride` updates, `answeredSteps` filter)
- `v2/frontend/src/data.jsx` exists (modified — `isStepVisible`, `getVisibleSteps`)
- `v2/frontend/src/conversation.test.jsx` exists (modified — 12 new tests)
- Commit `680cf12` (initial Task 1) exists in git log
- Commit `e10917a` (initial Task 2) exists in git log
- Commit `f6ae8c7` (continuation: sector/cluster gating) exists in git log
- Commit `ca44700` (continuation: sub-group picker render) exists in git log
- Commit `44153ee` (continuation: screen-blank fix — answeredSteps filter) exists in git log
- All 5 OGX-07 backend tests PASSED
- All 103 backend tests PASSED (no regressions)
- All 43 frontend vitest tests PASSED (12 new tests added across 3 bugfix rounds)
- Frontend build clean (216.17 kB JS / 24.86 kB CSS, gzip 66.46 kB / 5.50 kB)

---

*Phase: 21-og-expansion-preview-fix*
*Plan: 06*
*Completed: 2026-06-10 (initial) / 2026-06-11 (continuation rounds 1-3)*
*Status: All tasks complete including continuation bugfixes (3 rounds)*
