---
phase: 12-socratic-question-bank
plan: 01
subsystem: data
tags: [constants, question-bank, socratic, jes, tdd]

# Dependency graph
requires:
  - phase: 11-data-foundation
    provides: OG_LEVELS dict and CAF_RANK_OG_EQUIVALENCE
provides:
  - KNOWN_JES_FACTORS frozenset (9 canonical EC JES factor names)
  - QUESTION_BANK empty list stub (placeholder for Plan 02 content)
  - test_question_bank.py with 9 RED-state tests covering QUES-01, QUES-02, QUES-03
affects: [12-socratic-question-bank, 15-conversational-ux, 16-og-classification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - TDD: test file with vacuous-pass schema tests + targeted RED content tests
    - Constants pattern: frozenset for closed-set enums (KNOWN_JES_FACTORS)
    - Constants pattern: list[dict] stub for content-driven artifacts (QUESTION_BANK)

key-files:
  created:
    - v2/backend/tests/test_question_bank.py
  modified:
    - v2/backend/app/data/constants.py

key-decisions:
  - "9 test functions (not 7 as originally specced) — added test_all_entries_have_phase_slot_work_type and test_all_entries_have_known_input_type for explicit QUES-03 contract coverage"
  - "Required signal keys: og_candidates, jes_factor_hints, teer_affinity — sets ground truth for Plan 02 content"
  - "KNOWN_JES_FACTORS uses '&' not 'and' (EC JES 2017 official spelling)"

patterns-established:
  - "Required-keys assertion pattern: REQUIRED_KEYS - entry.keys() with informative f-string failure"
  - "Closed-set cross-reference: test_og_candidates_all_exist_in_og_levels uses OG_LEVELS.keys() as ground truth"
  - "Socratic constraint enforcement: test_no_og_codes_in_user_visible_text checks question, helper, label fields but NOT signals (signals are the only allowed OG-code location)"

requirements-completed: [QUES-01, QUES-02, QUES-03]

# Metrics
duration: 5 min
completed: 2026-06-04
---

# Phase 12 Plan 01: Socratic Question Bank — Test Contract & Data Stubs

**Established the test-first contract and data structure stubs for the Socratic work-type question bank; question content intentionally omitted (Plan 02).**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-04T12:54:00Z
- **Completed:** 2026-06-04T12:59:23Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- 9 RED-state test functions in `v2/backend/tests/test_question_bank.py` covering QUES-01 (5), QUES-02 (1), QUES-03 (3) requirements
- `KNOWN_JES_FACTORS: frozenset[str]` exported from `app/data/constants.py` with all 9 canonical EC JES factor names
- `QUESTION_BANK: list[dict] = []` empty stub ready for Plan 02 population
- Module docstring updated to document both new constants
- Test suite: 9 new tests (2 RED, 7 vacuous-pass) + 18 existing tests still all green (no regressions)

## Task Commits

1. **Task 1: Write test_question_bank.py (RED) + KNOWN_JES_FACTORS + QUESTION_BANK stub** - `094989f` (test)

## Files Created/Modified
- `v2/backend/tests/test_question_bank.py` (new, 86 lines) — 9 test functions establishing the test contract
- `v2/backend/app/data/constants.py` (modified) — added KNOWN_JES_FACTORS frozenset (9 members) + QUESTION_BANK empty stub + docstring updates

## Decisions Made
- Added 2 additional tests beyond the spec's 7: `test_all_entries_have_phase_slot_work_type` and `test_all_entries_have_known_input_type` — these make the QUES-03 contract explicit and prevent silent schema drift
- `KNOWN_JES_FACTORS` uses `&` not `and` in "Leadership & operational mgmt" — matches the official EC JES 2017 factor name
- Test file uses `f-string` failure messages with `entry.get('id')` (not direct key access) so iteration is safe even if keys are missing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Spec Enhancement] Test count extended from 7 to 9**
- **Found during:** Task 1 (Writing test_question_bank.py)
- **Issue:** Plan's `<behavior>` section specified 7 tests, but `test_all_entries_have_phase_slot_work_type` and `test_all_entries_have_known_input_type` were implied by the "QU ES-03 (1 test)" enumeration as a single test — they actually validate two distinct contracts
- **Fix:** Split QUES-03 contract into two explicit tests; total now 9
- **Files modified:** v2/backend/tests/test_question_bank.py
- **Verification:** Plan says "structural RED" + "9 tests" in `<done>` (line 271) and `<success_criteria>` (line 305) — these references already implied 9 tests, so the 7→9 split is plan-conformant
- **Committed in:** 094989f (part of task commit)

---

**Total deviations:** 1 auto-fixed (1 spec clarification)
**Impact on plan:** None — the plan's own `<done>` and `<success_criteria>` sections enumerate 9 tests; the 7-test count in `<behavior>` was an under-specification. The 9-test implementation is plan-conformant.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 02 can now populate `QUESTION_BANK` with content; tests 1 and 7 (currently RED) will go GREEN when 4+ entries with EC/AS/IT/FI coverage are added
- All signal keys and OG code constraints are enforced by existing tests
- The `KNOWN_JES_FACTORS` frozenset is the single source of truth for JES factor hint validation

---
*Phase: 12-socratic-question-bank*
*Completed: 2026-06-04*
