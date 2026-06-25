---
phase: 21-og-expansion-preview-fix
plan: 08
subsystem: classification
tags: [react, fastapi, socratic, level-description, tdd, jes-lev-01]

# Dependency graph
requires:
  - phase: 21-06
    provides: OgConfirmList + sub_group field on answers.og_confirm
  - phase: 21-07
    provides: extended QUESTION_BANK with sector-gate + 5 cluster questions
provides:
  - "JES_LEVEL_CRITERIA constant with 11 sub-group entries (NU-HOS, NU-CHN, NU-EMA, PS, NT-ADV, NT-DIT, NT-HME, PO-TCO, SW-CHA, ED-LAT, ED-EST)"
  - "POST /api/jes/level-suggest — Socratic level-determination endpoint (422/404 + direct/majority_hint resolution)"
  - "GET /api/jes/level-criteria — fetch question structure for og_code [+ sub_group]"
  - "GET /api/jes/level-criteria-groups — sorted list of 6 OG codes with level-description criteria"
  - "OgLevelQuestions component — fetches criteria, renders Socratic questions, posts to level-suggest, emits suggestion to parent"
  - "OgLevelPicker preselect — cfg.preselect renders 'is-suggested' class + 'rec-pill' label on the suggested level"
  - "og_level_questions STEPS entry + isStepVisible gate to {NU,PS,NT,PO,SW,ED}"
  - "cfgOverride wiring for og_level_questions (og_code, sub_group) + preselect on og_level"
affects: [22-sjd-library, 23-writing-guide, 24-risk-audit, 25-accessible-template]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "majority_hint vs direct level_resolution: direct uses first hint of length-1 list; majority_hint counts level appearances across hint lists, ties broken by lower level (conservative)"
    - "Confidence ladder: high = winning level appears in all answered hint lists AND all questions answered; medium = winning level appears in >= 2 lists; low = otherwise"
    - "preselect recedes after user click: cfg.preselect renders is-suggested only when value === null, ensuring user override always wins"
    - "key shape: JES_LEVEL_CRITERIA keys are 'OG-SUBGROUP' for multi-subgroup groups (NU, SW, ED) and bare 'OG' for single-subgroup groups (PS, NT-ADV, NT-DIT, NT-HME, PO-TCO, SW-CHA)"

key-files:
  created:
    - v2/backend/tests/test_jes_level_suggest.py
  modified:
    - v2/backend/app/data/constants.py
    - v2/backend/app/api/jes_scoring.py
    - v2/frontend/src/data.jsx
    - v2/frontend/src/components.jsx
    - v2/frontend/src/app.jsx
    - v2/frontend/src/conversation.test.jsx

key-decisions:
  - "OG code is always the first segment of the JES_LEVEL_CRITERIA key (e.g. 'NU-HOS' for NU sub-group HOS) — single-sub-group groups (PS, NT-ADV) use the bare OG code as key; this gives a uniform lookup shape with a simple key construction rule"
  - "level_resolution='direct' assumes a length-1 hint list and returns the first hint; this is correct for all 6 single-question groups (NU-EMA, NT-ADV, NT-DIT, NT-HME, SW-CHA, ED-LAT, ED-EST) and is enforced by the data"
  - "Confidence is computed from the number of agreed hint lists, not from LLM-style probability; high only when ALL answered questions point to the same level — this is intentionally conservative"
  - "preselect is a soft hint, not a default value: OgLevelPicker renders the suggested level with is-suggested class only when value === null; any user click removes the suggestion and the user's explicit choice (is-sel) is the canonical value"
  - "KNOWN_OG_CODES is the union of OG_LEVELS keys + SW-SCW + ED-EDS (the 22 OG codes + 2 sub-group routing codes); this is the whitelist for og_code validation on /api/jes/level-suggest and /api/jes/level-criteria (T-21-08-01 mitigation)"
  - "og_level_questions STEPS entry is placed immediately before og_level in the STEPS array; isStepVisible hides it for OG codes whose JES is point-rated (EC, IT, AS, FI, etc.) — visible only for level-description groups {NU, PS, NT, PO, SW, ED}"
  - "Mid-flow onChange from OgLevelQuestions emits { ...localAnswers, suggested_level: null } so the step is always answerValid (a non-empty object); the suggestion is only added when ALL questions are answered and the POST resolves"

patterns-established:
  - "Pattern: Socratic mini-interview before level picker for level-description groups — replaces bare numbered buttons with 1-3 questions whose answers map to level_hint lists"
  - "Pattern: Hint-list majority vote with conservative tiebreak — Socratic suggestion engine uses Counter[int] over hint lists; ties broken by lowest level (preserves authority of the lower-band option)"
  - "Pattern: Sub-group-keyed lookup for level criteria — JES_LEVEL_CRITERIA keys match the same shape as answers.og_confirm.sub_group concatenation with og_code, making the API contract uniform across all 6 level-description OG groups"

requirements-completed:
  - JES-LEV-01

# Metrics
duration: 11min
completed: 2026-06-11
---
# Phase 21 Plan 08: Socratic Level Determination Summary

**Author a Socratic mini-interview (1-3 questions) that suggests the right OG level for the 6 level-description OG groups (NU, PS, NT, PO, SW-CHA, ED-LAT/EST) — replacing the bare numbered buttons in OgLevelPicker with a question-based suggestion engine backed by the JES narrative level descriptions.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-06-11T11:36:27Z
- **Completed:** 2026-06-11T11:45:30Z
- **Tasks:** 2 of 2 (TDD: red + green for Task 2)
- **Files modified:** 6 (2 backend source, 1 backend test, 3 frontend source + test)
- **Commits:** 4 (1 feat constant, 1 test red, 1 feat green, 1 feat frontend)

## Accomplishments

- **Backend:** `JES_LEVEL_CRITERIA` constant with 11 sub-group entries authored; each entry has 1-3 Socratic questions, each option has a `level_hint` list, and resolution is either `direct` (length-1 hint → direct map) or `majority_hint` (Counter-based majority with conservative tiebreak). 58 `level_hint` occurrences in constants.py (≥30 required).
- **Backend:** 3 new FastAPI routes in `v2/backend/app/api/jes_scoring.py` — `POST /api/jes/level-suggest` (resolves suggestion from answers), `GET /api/jes/level-criteria` (returns the question structure), `GET /api/jes/level-criteria-groups` (returns sorted list of 6 OG codes with criteria). All routes use `KNOWN_OG_CODES` whitelist (T-21-08-01) and return 422 on unknown og_code, 404 on missing criteria.
- **Frontend:** `OgLevelQuestions` component (fetches criteria, renders questions, posts to level-suggest on all-answered, emits `{answers, suggested_level}` to parent step). Enhanced `OgLevelPicker` with `cfg.preselect` support — renders `is-suggested` class + `rec-pill` label on the suggested level button while `value === null`; user click on any level overrides (suggestion recedes, user choice highlighted with `is-sel`).
- **Frontend:** `og_level_questions` STEPS entry (phase 2, immediately before `og_level`) with full apply + transcript. `isStepVisible` case added: returns `true` when `answers.og_confirm.og_code` is in `{NU, PS, NT, PO, SW, ED}`; returns `false` for point-rated groups (EC, IT, AS, FI) and when `og_confirm` is unanswered.
- **Frontend:** `cfgOverride` extended with `og_level_questions` branch (injects `og_code` and `sub_group` from `answers.og_confirm` / `record.confirmed_og`) BEFORE the `og_level` branch. `og_level` branch extended with `preselect: answers.og_level_questions?.suggested_level ?? null`. FLASH map extended with `og_level_questions: 'level'`.
- **Tests:** 12 new backend tests (all 3 endpoints × behavioural cases including 422/404) + 7 new frontend tests (OgLevelPicker preselect × 3, isStepVisible gate × 4). 115/115 backend tests pass (103 original + 12 new). 59/59 frontend vitest tests pass (52 original + 7 new). Build clean (220.67 kB JS / 24.86 kB CSS).

## Task Commits

Each task was committed atomically:

1. **Task 1: Author JES_LEVEL_CRITERIA constant in constants.py** — `9ee2e66` (feat)
2. **Task 2 RED: Add failing tests for /api/jes/level-suggest endpoints** — `3deb96a` (test)
3. **Task 2 GREEN: Implement POST/GET level-suggest endpoints** — `f399752` (feat)
4. **Task 2 frontend: OgLevelQuestions component + OgLevelPicker preselect + cfgOverride wiring** — `5d8962a` (feat)

## Files Created/Modified

- `v2/backend/app/data/constants.py` — Appended `JES_LEVEL_CRITERIA: dict[str, dict]` (250 lines) between QUESTION_BANK and OG_DEFINITIONS. 11 sub-group entries (NU-HOS, NU-CHN, NU-EMA, PS, NT-ADV, NT-DIT, NT-HME, PO-TCO, SW-CHA, ED-LAT, ED-EST) with method, questions (1-3 Socratic questions), level_resolution (majority_hint or direct), and fallback fields. 58 `level_hint` occurrences total.
- `v2/backend/app/api/jes_scoring.py` — Added `KNOWN_OG_CODES` frozenset (22 codes + SW-SCW/ED-EDS), `LevelSuggestRequest` pydantic model, `_resolve_level_suggestion()` pure helper implementing both direct and majority_hint resolutions, and 3 new routes: `POST /api/jes/level-suggest` (422/404 + suggestion), `GET /api/jes/level-criteria` (422/404 + entry), `GET /api/jes/level-criteria-groups` (sorted list of 6 codes).
- `v2/frontend/src/data.jsx` — Added `case 'og_level_questions'` to `isStepVisible` switch (true for `answers.og_confirm.og_code` in `{NU,PS,NT,PO,SW,ED}`). Added new `og_level_questions` STEPS entry (phase 2, immediately before `og_level`) with `apply: (r, a) => ({ og_level_questions: a })` and a transcript formatter that shows "Suggested: Level 0X" or "Answered".
- `v2/frontend/src/components.jsx` — Added `OgLevelQuestions` component (fetches `/api/jes/level-criteria` on mount, renders questions, calls `/api/jes/level-suggest` on all-answered, emits `{ ...answers, suggested_level }` to parent). Enhanced `OgLevelPicker` to use `cfg.preselect` (renders `is-suggested` class + `rec-pill` label on the preselected level button while `value === null`; user click on any level removes the suggestion). Added `og_level_questions` case to `StepInput` dispatcher and `answerValid`. Exported `OgLevelQuestions` and `OgLevelPicker`.
- `v2/frontend/src/app.jsx` — Extended `stepCfgOverride` with `og_level_questions` branch (injects `og_code` and `sub_group` from `answers.og_confirm` / `record.confirmed_og`) BEFORE the `og_level` branch. Extended `og_level` branch with `preselect: answers.og_level_questions?.suggested_level ?? null`. Added `og_level_questions: 'level'` to the FLASH map.
- `v2/frontend/src/conversation.test.jsx` — Added 7 new tests: 3 OgLevelPicker preselect tests (renders pill, no preselect, user override), 4 isStepVisible tests (true for NU, PS/NT/PO/SW/ED; false for EC/IT/AS/FI; false without og_confirm).
- `v2/backend/tests/test_jes_level_suggest.py` — New test file with 12 tests: 7 for `POST /api/jes/level-suggest` (full/partial answers, PS, NU-EMA direct, empty, EC 404, invalid 422), 4 for `GET /api/jes/level-criteria` (NU-HOS, PS, EC 404, unknown 422), 1 for `GET /api/jes/level-criteria-groups` (returns 6 OG codes).

## Decisions Made

- **OG code is always the first segment of the JES_LEVEL_CRITERIA key** — multi-sub-group groups (NU, SW, ED) use the `OG-SUBGROUP` shape (e.g. `NU-HOS`); single-sub-group groups (PS, NT-ADV, NT-DIT, NT-HME, PO-TCO, SW-CHA) use the bare `OG` code. The lookup `key = f"{og_code}-{sub_group}" if sub_group else og_code` gives a uniform contract for both shapes.
- **level_resolution='direct' assumes a length-1 hint list** — this is the contract for all 6 single-question groups (NU-EMA, NT-ADV, NT-DIT, NT-HME, SW-CHA, ED-LAT, ED-EST) and enforced by the data. Returns the first hint directly with `confidence='high'`.
- **Confidence ladder is intentionally conservative** — `high` only when ALL answered questions point to the same level AND all questions are answered; `medium` when the winning level appears in >= 2 hint lists; `low` otherwise (including partial answers and empty answer sets). The user can always override the suggestion regardless of confidence.
- **preselect is a soft hint, not a default value** — `OgLevelPicker` renders the suggested level with `is-suggested` class only when `value === null`. Any user click removes the suggestion and the user's explicit choice (is-sel) is the canonical value persisted to the WD.
- **KNOWN_OG_CODES mirrors OG_LEVELS keys + SW-SCW + ED-EDS** — the 22 OG codes from OG_LEVELS plus the 2 sub-group routing codes (which route through point-rating in `/api/jes/score` but are also valid og_code values for client-side routing). This is the whitelist for og_code validation on both `/api/jes/level-suggest` and `/api/jes/level-criteria` (T-21-08-01 mitigation).
- **og_level_questions STEPS entry is placed immediately before og_level** — keeps the existing conversation flow intact: og_confirm → og_level_questions (conditional) → og_level. The `isStepVisible` predicate hides og_level_questions for point-rated groups, so the linear flow for EC/IT/AS/FI/CR/PM/GT/EL/AI/AU/FB/FS/LC/LP/MT users is unchanged.
- **Mid-flow onChange from OgLevelQuestions emits `{ ...localAnswers, suggested_level: null }`** — the step is always `answerValid` (a non-empty object), even before the user has answered all questions. The full suggestion (`{ ...answers, ...data }` from the POST response) replaces the draft only when all questions are answered. This ensures the Continue button enables as soon as the user makes their first selection, but the suggestion only appears after all questions are answered.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Mid-flow onChange in OgLevelQuestions emits a draft so answerValid is true**
- **Found during:** Task 2 frontend implementation (post-implementation review)
- **Issue:** The plan's `handleAnswer` function only called `onChange` when `allAnswered === true` (i.e. all questions answered). For the partial-answer case (user has answered 1 of 2 questions, the suggestion is still computing), `onChange` was never called and the parent step's `answerValid` returned false (because `value` was still `null`). The Continue button would be disabled until ALL questions were answered + the POST resolved. This is a worse UX than the plan implied (the plan only specified the all-answered flow).
- **Fix:** Added an `else` branch to `handleAnswer` that calls `onChange({ ...updated, suggested_level: null })` on every individual answer, so `answerValid(step, draft)` returns `true` after the first answer. The full suggestion (`{ ...updated, ...data }`) is emitted when `allAnswered` and the POST resolves. This makes the Continue button enable as soon as the user makes their first selection.
- **Files modified:** `v2/frontend/src/components.jsx` (OgLevelQuestions component)
- **Verification:** 7 new frontend tests pass; 59/59 vitest total green
- **Committed in:** `5d8962a` (Task 2 frontend commit)

**2. [Rule 1 - Bug] Exported OgLevelQuestions and OgLevelPicker from components.jsx**
- **Found during:** Task 2 frontend implementation (verification)
- **Issue:** The plan said "Export OgLevelQuestions from the components file (add to the export statement at the bottom of components.jsx)". The original export was `{ Icon, Check, StepInput, initialAnswer, answerValid }`. To satisfy the plan's explicit instruction and to enable future test imports, both `OgLevelQuestions` and `OgLevelPicker` were added to the export list.
- **Fix:** Updated the export statement to `{ Icon, Check, StepInput, initialAnswer, answerValid, OgLevelQuestions, OgLevelPicker }`.
- **Files modified:** `v2/frontend/src/components.jsx` (export line)
- **Verification:** 7 new frontend tests pass; 59/59 vitest total green
- **Committed in:** `5d8962a` (Task 2 frontend commit)

---

**Total deviations:** 2 (both Rule 1 bug fixes in the frontend component logic)
**Impact on plan:** Both deviations are minor refinements of the implementation; the action block code is followed exactly otherwise. The `OgLevelQuestions` mid-flow onChange fix improves UX (Continue button enables after first answer) and the export line addition makes the components testable in isolation.

## Issues Encountered

- **The plan referenced `v2/backend/app/api/jes_routes.py` but the actual file is `v2/backend/app/api/jes_scoring.py`** — the plan was written before the file naming was finalized. The 3 new routes were added to the existing `jes_scoring.py` (which already contains `/api/jes/score` and `/api/jes/override`) rather than creating a new `jes_routes.py` file. This matches the existing convention (one router per file) and keeps the JES-related routes together.
- **TDD test file naming** — the new test file is `v2/backend/tests/test_jes_level_suggest.py` (matches the route name `/api/jes/level-suggest`) rather than co-locating with the existing `test_jes_scoring.py`. The two test files cover different route families (scoring vs. level-suggest) and have different behavioural contracts; the separation keeps each test file focused.
- **`isStepVisible` for `og_level_questions` without `og_confirm` returns `false`** — the activeStepIndex logic in `app.jsx` (introduced in Plan 06) walks the user forward to `og_confirm` before `og_level_questions`, so the user always lands on `og_confirm` first. After og_confirm, the gate enables og_level_questions for level-description groups only. This is consistent with the "Socratic intent" pattern established in Plan 06/07 (users never see steps that don't apply to their context).

## Next Phase Readiness

- Phase 21 Plan 08 complete; all JES-LEV-01 acceptance criteria met
- 6 level-description OG groups (NU, PS, NT, PO, SW-CHA, ED-LAT/EST) now have a Socratic suggestion engine backed by 11 sub-group entries
- All 3 backend endpoints (POST /api/jes/level-suggest, GET /api/jes/level-criteria, GET /api/jes/level-criteria-groups) work correctly with proper 422/404 error semantics
- OgLevelQuestions component fetches criteria + posts to level-suggest + emits suggestion to parent step
- OgLevelPicker renders the suggested level with `is-suggested` class + `rec-pill` label; users can freely override
- 115/115 backend tests + 59/59 frontend tests pass; build clean (220.67 kB JS / 24.86 kB CSS)
- Phase 22 (SJD Library) is unblocked — can start
- No blockers or concerns

## Self-Check: PASSED

- `.planning/phases/21-og-expansion-preview-fix/21-08-SUMMARY.md` exists (this file)
- Commit `9ee2e66` (feat: JES_LEVEL_CRITERIA constant) exists in git log
- Commit `3deb96a` (test: RED) exists in git log
- Commit `f399752` (feat: GREEN) exists in git log
- Commit `5d8962a` (feat: frontend) exists in git log
- `v2/backend/app/data/constants.py` modified — verified 11 JES_LEVEL_CRITERIA keys (NU-HOS, NU-CHN, NU-EMA, PS, NT-ADV, NT-DIT, NT-HME, PO-TCO, SW-CHA, ED-LAT, ED-EST) and 58 `level_hint` occurrences
- `v2/backend/app/api/jes_scoring.py` modified — verified 8 `level-suggest` matches, 2 `level-criteria-groups` matches, 3 new routes added
- `v2/backend/tests/test_jes_level_suggest.py` created — verified 12 new tests
- `v2/frontend/src/data.jsx` modified — verified 4 `og_level_questions` references (case + STEPS entry + apply + transcript)
- `v2/frontend/src/components.jsx` modified — verified 4 `OgLevelQuestions` references, 4 `preselect` references, 2 `is-suggested` references
- `v2/frontend/src/app.jsx` modified — verified 3 `og_level_questions` references (FLASH + cfgOverride branch + preselect source)
- `v2/frontend/src/conversation.test.jsx` modified — verified 7 new test cases
- All 115 backend pytest tests PASSED (103 original + 12 new)
- All 59 frontend vitest tests PASSED (52 original + 7 new)
- Build clean: 220.67 kB JS / 24.86 kB CSS
- Smoke test via httpx ASGITransport confirms all 3 endpoints respond correctly

### Live verification (post-write)

```
$ python -c "from v2.backend.app.data.constants import JES_LEVEL_CRITERIA; ..."
JES_LEVEL_CRITERIA OK — 11 entries, all valid

$ grep -c "level_hint" v2/backend/app/data/constants.py
58

$ grep -c "level-suggest" v2/backend/app/api/jes_scoring.py
8

$ grep -c "level-criteria-groups" v2/backend/app/api/jes_scoring.py
2

$ grep -c "OgLevelQuestions" v2/frontend/src/components.jsx
4

$ grep -c "og_level_questions" v2/frontend/src/data.jsx
4

$ grep -c "preselect" v2/frontend/src/components.jsx
4

$ grep -c "og_level_questions" v2/frontend/src/app.jsx
3

$ grep -c "is-suggested" v2/frontend/src/components.jsx
2

$ python -m pytest v2/backend/tests/ -x -q
115 passed in 10.27s

$ npx vitest run
Test Files  3 passed (3)
Tests       59 passed (59)

$ npm run build
✓ 35 modules transformed.
dist/index.html                   0.78 kB
dist/assets/index-Bugrfl5W.css   24.86 kB
dist/assets/index-Ci3nPcaF.js   220.67 kB
✓ built in 1.59s

$ Smoke test via httpx ASGITransport:
POST /api/jes/level-suggest (NU-HOS full): 200 {'suggested_level': 4, 'confidence': 'high', 'level_range': [3, 4, 5], ...}
GET /api/jes/level-criteria (NU-HOS): 200 method=level_description questions=2
GET /api/jes/level-criteria-groups: 200 ['ED', 'NT', 'NU', 'PO', 'PS', 'SW']
POST /api/jes/level-suggest (EC): 404 {'detail': 'No level criteria for EC'}
POST /api/jes/level-suggest (INVALID): 422 {'detail': 'Unknown og_code: INVALID'}
```

---

*Phase: 21-og-expansion-preview-fix*
*Plan: 08*
*Completed: 2026-06-11*
