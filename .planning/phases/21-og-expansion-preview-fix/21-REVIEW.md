---
status: issues_found
phase: 21-og-expansion-preview-fix
reviewed: 2026-06-11
depth: quick
reviewer: gsd-code-reviewer (spawned by orchestrator)
---

# Phase 21 Code Review (Wave 5: 21-07 + 21-08)

## Summary

Quick review of the source files changed in plans 21-07 (OGX-04 question bank restructure) and 21-08 (JES-LEV-01 Socratic level determination). Found **one blocker-class risk** related to the sub-group wiring for the new `og_level_questions` step, plus several minor issues. The blocker is a plan-vs-implementation gap that the executor implemented as specified; the user should decide whether to do a gap-closure plan.

## Code Map (5 source files)

| File | What was added |
|------|----------------|
| `v2/backend/app/data/constants.py` | `qb_programme_admin_cluster` to QUESTION_BANK (OGX-04); `JES_LEVEL_CRITERIA` dict with 11 sub-group entries (NU-HOS, NU-CHN, NU-EMA, PS, NT-ADV, NT-DIT, NT-HME, PO-TCO, SW-CHA, ED-LAT, ED-EST) |
| `v2/backend/app/api/jes_scoring.py` | 3 routes: `POST /jes/level-suggest`, `GET /jes/level-criteria`, `GET /jes/level-criteria-groups`. Input validation against `KNOWN_OG_CODES` (22 codes). `direct` and `majority_hint` resolution paths. |
| `v2/frontend/src/data.jsx` | `isStepVisible` cases for 4 legacy work-type questions (gated to `other_sector`), `qb_programme_admin_cluster`, `og_level_questions`. `accumulateSignals` filters by `isStepVisible`. `qb_programme_admin_cluster` STEP entry. `og_level_questions` STEP entry. |
| `v2/frontend/src/components.jsx` | `OgLevelQuestions` component (fetches criteria, posts to level-suggest). `OgLevelPicker` enhanced with `cfg.preselect` support (renders `is-suggested` class + "suggested" pill). |
| `v2/frontend/src/app.jsx` | `FLASH` map entries. `cfgOverride` branch for `og_level_questions` (injects `og_code` and `sub_group` from `answers.og_confirm` or `record.confirmed_og`). `preselect` added to `og_level` branch. |

## Findings

### Major — sub_group not propagated from OgConfirmList to answers.og_confirm (data-flow gap)

**File:** `v2/frontend/src/components.jsx:369` (OgConfirmList), `v2/frontend/src/app.jsx:646` (cfgOverride)

**Issue:** When the user picks a sub-group in OgConfirmList (`setSelectedSubGroup(sg)`), the value is held in **local component state** only. The parent step's `answers.og_confirm` is **never updated** with `sub_group`. The cfgOverride in app.jsx falls back to `record.confirmed_og?.sub_group`, but that field only populates if (a) the user already clicked Continue on the og_confirm step, AND (b) the `POST /api/wd/{id}/confirm-subgroup` async call has resolved on the server before the PATCH commit fires. There is no test or guard for this race.

**End-to-end impact for level-description groups:**
- The `cfg.sub_group` in `OgLevelQuestions` is null in most timing windows
- The fetch URL is `/api/jes/level-criteria?og_code=NU` (no `sub_group` param)
- The backend constructs the lookup key as `"NU"` (bare), which is **not** in `JES_LEVEL_CRITERIA` → **404**
- The component's catch block (`components.jsx:500`) only does `setLoading(false)` — never calls `onChange`
- `answerValid` for `og_level_questions` returns false (value is null) → **the user is stuck on the og_level_questions step**

**Affected OG groups:** NU (all 3 sub-groups), SW-CHA, ED-LAT, ED-EST, NT (all 3 sub-groups), PO-TCO. Only **PS** (which has no sub-group) works end-to-end.

**Recommended fix (gap-closure plan candidate):**
1. In `OgConfirmList.handleSubGroupSelect`, also call `onChange({ ...value, sub_group: sg })` so the parent step's draft is updated
2. Add a test that drives a full end-to-end flow: pick OG → pick sub-group → advance to og_level_questions → assert criteria loaded
3. In `OgLevelQuestions.useEffect` catch, emit a no-op `onChange({ _criteria_unavailable: true })` so `answerValid` returns true and the user can proceed

**Plan compliance:** The executor followed the plan as written. The plan's interfaces section said "sub_group: injected by cfgOverride from answers.og_confirm" — but OgConfirmList never populated `answers.og_confirm.sub_group`. This is a plan defect, not an executor defect.

### Minor — duplicate data for NU-HOS and NU-CHN

`JES_LEVEL_CRITERIA['NU-HOS']` and `['NU-CHN']` have identical `questions` arrays (lines 632-686 in constants.py). Code smell — DRY violation. Refactor to a shared `NU_QUESTIONS` constant + spread.

### Minor — KNOWN_OG_CODES comment is misleading

`jes_scoring.py:43-48` comment says "Mirrors the 22 OG codes in OG_LEVELS + SW-SCW / ED-EDS sub-group routing codes" but the actual set has only 22 codes (SW-SCW and ED-EDS are not in the set). Update the comment to match the actual content.

### Minor — `direct` resolution path doesn't validate hint list length

`jes_scoring.py:267-274`: the `direct` path assumes `hint_lists[0]` has length 1. The data invariant is not enforced. Add a defensive check or document the contract.

### Minor — `level_criteria_groups` uses `key.split("-")[0]`

`jes_scoring.py:367-370`: assumes keys are `OG` or `OG-SUBGROUP`. None of the current data has hyphens in OG codes, so this is fine for now. Worth a defensive comment.

## Verification Suggestions

1. **End-to-end manual test for each level-description group:**
   - Pick NU, select HOS → reach og_level_questions → assert 2 questions render
   - Pick SW, select CHA → reach og_level_questions → assert 1 question renders
   - Pick ED, select LAT → reach og_level_questions → assert 1 question renders
   - Pick PS (no sub-group) → reach og_level_questions → assert 3 questions render

2. **Automated:** Add a frontend test that drives the full og_confirm → og_level_questions flow with a mocked API and asserts `cfg.sub_group` is correctly resolved.

3. **Stress test the API:** Add a backend test that exercises `POST /jes/level-suggest` for each of the 11 JES_LEVEL_CRITERIA entries with both partial and complete answers.

## Next Steps

Recommend running `/gsd-code-review-fix` or opening a Phase 21.1 gap-closure plan for the **Major** finding. The Minor findings are non-blocking and can be addressed in a follow-up.

**Status:** issues_found — advisory, does not block phase execution.
