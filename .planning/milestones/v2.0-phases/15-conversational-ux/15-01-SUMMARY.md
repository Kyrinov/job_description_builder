# Plan 15-01 Summary — Wave 0 RED test stubs

## What was built
- `v2/backend/tests/test_wd.py` (4 async tests, RED): contract for POST /api/wd, GET /api/wd/{id}, PATCH /api/wd/{id}, 404 case.
- `v2/frontend/src/conversation.test.jsx` (8 tests, 7 RED / 1 pre-existing-pass): contract for CONVO-01 (qb_work_output_type step at phase 1, workType removed), CONVO-02 (accumulateSignals pure function + jumpToExchange reset), CONVO-03 (PHASES = 6 new phase names), CONVO-04 (StepInput og_confirm stub renders), CONVO-05 (answerValid for choices + Enter key submits text input).

## Verification
- `python -m pytest tests/test_wd.py` → 1 failed (404 vs 201, route does not exist) — RED for the right reason
- `python -m pytest --ignore=tests/test_wd.py` → 39 passed (no regressions)
- `npm test` → conversation.test.jsx 7 failed (RED for missing exports / wrong STEPS), app.test.jsx 9 passed (no regressions)

## Deviations
None — plan 01 executed exactly as specified. Wave 0 stubs define the contract that plans 02/03/04 must satisfy.

## Impact on subsequent plans
- Plan 02 (WD CRUD backend) must turn all 4 test_wd.py tests GREEN
- Plan 03 (data.jsx rewrite) must turn 5/8 conversation tests GREEN (CONVO-04 needs Plan 04's og_confirm stub)
- Plan 04 (app.jsx + components.jsx + conversation.jsx) must turn the remaining 3 conversation tests GREEN (CONVO-04 og_confirm, CONVO-02 jumpToExchange, CONVO-05 Enter key)
