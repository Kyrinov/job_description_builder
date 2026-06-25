# Plan 15-03 Summary — Frontend data.jsx rewrite (STEPS, PHASES, accumulateSignals)

## What was built
- `v2/frontend/src/data.jsx` rewritten: STEPS array replaced with 12 entries spanning 5 phases (0-4), PHASES constant replaced with the 6 v2.0 phase names, `accumulateSignals` pure function added and exported.
- `levelFromScope` and `computeClassification` retained (referenced by app.jsx for legacy badge render; will be removed when Phase 16 lands OgConfirmList).

## New STEPS phase layout
| Phase | Name | Step IDs |
|-------|------|----------|
| 0 | Role | title, branch, reports, supervises |
| 1 | Work Type | summary, qb_work_output_type, qb_work_audience, qb_knowledge_specialization, qb_policy_interpretation |
| 2 | Classification | noc_confirm |
| 3 | Duties | duties |
| 4 | Qualifications | quals |
| 5 | Review | (no STEPS; setReviewing(true) is the trigger) |

The 4 QUESTION_BANK entries carry `signals: { og_candidates, jes_factor_hints, teer_affinity }` on each option, but `apply()` stores only `a.id` (not signals) into record — signals are derived client-side by `accumulateSignals` and never persisted.

## Verification
- `npm run build` → exit 0, bundle 182.79 kB (gzip 58.00 kB, +2.37 kB from Phase 13's 179.71 kB due to new step entries)
- `npm test` → 16 passed, 2 failed
  - 6/8 conversation.test.jsx tests PASS (CONVO-01 qb_work_output_type phase check, CONVO-01 workType removed, CONVO-03 PHASES, CONVO-05 answerValid choices, CONVO-02 accumulateSignals empty, CONVO-02 accumulateSignals EC tally)
  - 9/9 app.test.jsx tests PASS (no regressions)
  - 2/8 conversation tests FAIL: CONVO-04 og_confirm stub (Plan 04) and CONVO-02 jumpToExchange (Plan 04)

## Deviations
None. Plan executed exactly as specified. The 2 remaining conversation.test.jsx failures are the expected ones for Plan 04.

## Impact on subsequent plans
- Plan 04 will add the og_confirm stub to StepInput (turns CONVO-04 GREEN), wire WD CRUD + NOC trigger in app.jsx (CONVO-02 jumpToExchange), and add Enter key handler in components.jsx (CONVO-05 Enter key).
