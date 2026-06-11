---
phase: 21-og-expansion-preview-fix
plan: "09"
subsystem: frontend
tags: [bug-fix, og-confirm, sub-group, jes-level, regression-test]
dependency_graph:
  requires: [21-08]
  provides: [sub_group propagation end-to-end, OgLevelQuestions error recovery]
  affects: [v2/frontend/src/components.jsx, v2/frontend/src/conversation.test.jsx]
tech_stack:
  added: []
  patterns: [onChange sentinel pattern, synchronous onChange before async side-effect]
key_files:
  created: []
  modified:
    - v2/frontend/src/components.jsx
    - v2/frontend/src/conversation.test.jsx
decisions:
  - onChange fires synchronously in handleSubGroupSelect before setSelectedSubGroup and the API call
  - _criteria_unavailable sentinel pattern used to unblock user on fetch failure (not merged with other state)
metrics:
  duration: ~5 minutes
  completed: "2026-06-11T16:42:00Z"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 2
---

# Phase 21 Plan 09: Sub-Group Propagation Fix Summary

**One-liner:** Two surgical fixes wire sub_group from the OG picker through onChange to OgLevelQuestions, plus a regression test that would have caught the original gap.

---

## Objective

Fix the two-part frontend data-flow bug that blocked the Socratic mini-interview (JES-LEV-01) for 5 of 6 sub-group-bearing OG groups, and add a regression test that would have caught it.

---

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Fix handleSubGroupSelect — propagate sub_group via onChange | efdb4f3 | components.jsx |
| 2 | Fix OgLevelQuestions useEffect catch — emit onChange on fetch failure | 6ae3d28 | components.jsx |
| 3 | Add regression test — sub_group propagates via onChange | a3537b9 | conversation.test.jsx |

---

## What Was Done

### Task 1 — Gap 1 closure

Added `onChange({ ...value, sub_group: sg });` as the FIRST statement in `OgConfirmList.handleSubGroupSelect`, before `setSelectedSubGroup(sg)` and the `confirm-subgroup` API call. This ensures the parent draft receives `sub_group` immediately on picker click, so `cfg.sub_group` is populated when `OgLevelQuestions` mounts on the next step.

### Task 2 — Gap 2 closure

Replaced the bare `.catch(() => { setLoading(false); })` in `OgLevelQuestions.useEffect` with a handler that also emits `onChange({ _criteria_unavailable: true })`. This sentinel causes `answerValid` to return truthy, re-enabling the Continue button so the user can proceed to `OgLevelPicker` and select a level manually even when the JES criteria fetch fails (e.g., bare `/api/jes/level-criteria?og_code=NU` with no sub_group returns 404).

### Task 3 — Gap 3 closure

Added a new `describe` block at the end of `conversation.test.jsx`. The test renders `OgConfirmList` with a NU value and a fetch mock returning HOS/CHN/EMA subgroups, waits for the picker to appear, clicks the HOS button, then asserts `onChange` was called with `expect.objectContaining({ og_code: 'NU', sub_group: 'HOS' })`. Total frontend tests: 60 (was 59).

---

## Deviations from Plan

None — plan executed exactly as written. All three gaps closed with surgical changes only.

---

## Verification Results

```
grep "onChange({ ...value, sub_group: sg })" components.jsx  → line 394 (PASS)
grep "_criteria_unavailable" components.jsx                   → line 505 (PASS)
grep "calls onChange with sub_group" conversation.test.jsx    → line 725 (PASS)
npx vitest run                                                → 60/60 passed (PASS)
```

---

## Threat Model Coverage

| Threat | Disposition | Status |
|--------|-------------|--------|
| T-21-gap-01: Tampering via onChange payload | accept | sub_group validated server-side at confirm-subgroup endpoint |
| T-21-gap-02: DoS via OgLevelQuestions fetch error | mitigate | onChange({ _criteria_unavailable: true }) unblocks user on 404 |

No new security-relevant surface introduced.

---

## Known Stubs

None.

---

## Self-Check: PASSED

- `v2/frontend/src/components.jsx` — modified, fix present at lines 394 and 505
- `v2/frontend/src/conversation.test.jsx` — modified, new test at line 725
- Commit efdb4f3 — present
- Commit 6ae3d28 — present
- Commit a3537b9 — present
- 60/60 frontend tests passing
