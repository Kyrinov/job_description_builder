---
slug: phase-17-jes-scorecard-not-vis
status: resolved
trigger: "Phase 17 UAT: JES scorecard is not visible. The minimax m3 implementer has attempted fixes multiple times and failed. Need systematic root cause analysis and a working fix."
created: 2026-06-08
updated: 2026-06-08
---

## Symptoms

- **Expected:** JES scorecard renders with scoring data after submitting a work description
- **Actual:** Scorecard section is completely absent — no UI element appears at all
- **Errors:** No errors visible in browser console, network tab, or server logs
- **Timeline:** Never worked — broke from the start of phase 17 (never rendered correctly)
- **Reproduction:** Run the app, submit a work description — scorecard should appear but doesn't
- **Prior attempts:** Minimax m3 implementer attempted multiple fixes, all failed

## Current Focus

hypothesis: CONFIRMED — render gate in DocumentPane used jes_scores.length > 0 but backend returns factors:[] for non-EC groups; jes_total_points is the correct gate for both EC and non-EC
test: 2 new regression tests in document.test.jsx — GREEN
expecting: scorecard renders for all OG groups (EC and non-EC) after og_level is committed
next_action: DONE — fix applied, all 24 tests green
reasoning_checkpoint: The bug is in document.jsx line 293. The render gate `r.jes_scores && r.jes_scores.length > 0` fails for non-EC groups because the backend intentionally returns `factors: []` for FI/IT/AS/EN. Changed gate to `r.jes_total_points != null` which is set for both EC and non-EC after scoring completes.
tdd_checkpoint:

## Evidence

- timestamp: 2026-06-08T08:07
  file: v2/frontend/src/document.jsx
  line: 293
  observation: render gate was `r.jes_scores && r.jes_scores.length > 0` — fails for non-EC because backend returns factors:[]

- timestamp: 2026-06-08T08:07
  file: v2/backend/app/services/jes_service.py
  line: 192-203
  observation: non-EC path returns `"factors": []` (empty list) — by design; total_points is set; no factors array

- timestamp: 2026-06-08T08:07
  file: v2/frontend/src/app.jsx
  line: 255
  observation: frontend stores `jes_scores: data.factors || []` — for non-EC this stores an empty array, which then fails the length > 0 gate

## Eliminated

- Backend API error (409 or other): eliminated — prior fix already chained JES fetch off WD persistence promise
- EC group scoring: eliminated — would work correctly if jes_scores has 9 factors; bug primarily affects non-EC
- Missing state update: eliminated — setRecord with jes_scores/jes_total_points fires correctly on success

## Resolution

root_cause: DocumentPane render gate in document.jsx line 293 used `r.jes_scores && r.jes_scores.length > 0` but the backend returns `factors: []` for non-EC OG groups (FI, IT, AS, EN). The scorecard was therefore invisible for all non-EC groups, which are the majority of test cases.
fix: Changed render gate from `r.jes_scores && r.jes_scores.length > 0` to `r.jes_total_points != null`. `jes_total_points` is set for both EC and non-EC after scoring completes, and is absent/null before. Also added 2 regression tests in document.test.jsx to prevent reversion.
verification: 24/24 vitest tests pass (was 22/22 before; 2 new regression tests added)
files_changed:
  - v2/frontend/src/document.jsx (line 293: render gate changed)
  - v2/frontend/src/document.test.jsx (2 new DocumentPane render gate regression tests added)
