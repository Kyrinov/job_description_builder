---
phase: 12-socratic-question-bank
plan: 02
subsystem: data
tags: [question-bank, socratic, og-classification, jes, tdd]

# Dependency graph
requires:
  - phase: 12-socratic-question-bank-01
    provides: KNOWN_JES_FACTORS frozenset + QUESTION_BANK stub + 9 RED test functions
  - phase: 11-data-foundation
    provides: OG_LEVELS dict (ground truth for og_candidates cross-reference)
provides:
  - "QUESTION_BANK: 4 Socratic question entries with 14 total answer options"
  - "Phase 15 conversation flow can now render work_type steps from this constant"
  - "Phase 16 OG ranker can consume signals (og_candidates, jes_factor_hints, teer_affinity) as classification input"
affects: [15-conversational-ux, 16-og-classification, 17-jes-scoring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Socratic constraint enforcement: OG codes live ONLY in signals.og_candidates (test-verified)
    - Signal-based classification: each option carries og_candidates + jes_factor_hints + teer_affinity
    - Phase-slot routing: phase_slot="work_type" enables Phase 15 step registry to filter by conversation phase

key-files:
  created: []
  modified:
    - v2/backend/app/data/constants.py

key-decisions:
  - "4 entries chosen (minimum required by QUES-01) — covers EC, AS, IT, FI without naming any in user-visible text"
  - "Each question targets a distinct classification axis: output type, audience, knowledge depth, policy relationship"
  - "teer_affinity restricted to [1, 2] for EC/FI/IT signals (analytical/specialist) vs [2, 3, 4] for AS signals (administrative)"
  - "JES factor hints span: Research & analysis, Decision making, Knowledge of specialized fields, Contextual knowledge, Communication, Leadership & operational mgmt — gives Phase 17 scorer multiple signal points"

patterns-established:
  - "Question entry schema: id, phase_slot, question, helper, input_type, options[].id, options[].label, options[].signals"
  - "Signal schema: og_candidates (list of OG_LEVELS keys), jes_factor_hints (list of KNOWN_JES_FACTORS), teer_affinity (list of NOC TEER ints)"
  - "Helper text pattern: 'Think about X — not Y.' — clarifies intent without revealing OG group"

requirements-completed: [QUES-01, QUES-02, QUES-03]

# Metrics
duration: 4 min
completed: 2026-06-04
---

# Phase 12 Plan 02: Socratic Question Bank — Populate Content

**Populated QUESTION_BANK with 4 Socratic work-type entries (14 answer options) covering EC, AS, IT, FI groups; QUES-02 Socratic constraint enforced — no OG code in any user-visible text.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-06-04T12:59:23Z
- **Completed:** 2026-06-04T13:02:14Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- QUESTION_BANK now contains 4 entries: `work_output_type`, `work_audience`, `knowledge_specialization`, `policy_interpretation`
- 14 total answer options across all entries (4 + 3 + 4 + 3)
- All 4 required OG groups (EC, AS, IT, FI) are represented in `og_candidates` signals
- QUES-02 Socratic constraint: zero OG codes in any question, helper, or option label — verified by static AST check
- All 9 test_question_bank.py tests GREEN (was 2 RED, 7 vacuous-pass after Plan 01)
- Full backend suite: 27/27 passing (18 prior + 9 new), zero regressions

## Task Commits

1. **Task 1: Populate QUESTION_BANK with 4 entries** - `1b9bbd9` (feat)

## Files Created/Modified
- `v2/backend/app/data/constants.py` (modified) — replaced empty stub with 4 fully-populated question entries (162 insertions)

## Decisions Made
- 4 questions chosen (not 5+): minimum required by QUES-01 to cover 4 OG groups, with each question targeting a distinct classification axis (output/audience/knowledge/policy)
- Question 2 (`work_audience`) has 3 options instead of 4: avoids redundancy with Q1; some audience patterns don't need explicit coverage
- `teer_affinity` ranges: [1, 2] for analytical/specialist roles (EC/FI/IT), [2, 3, 4] for administrative roles (AS) — encodes the NOC TEER intuition that admin work spans more TEER levels than specialist work
- Each option has 1-2 `jes_factor_hints`: gives Phase 17 scorer enough signal granularity to weight factors without overcommitting to a specific JES profile

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- **Known issue (not a deviation):** `v2/backend/app/models/classification.py` has `level: ge=4, le=6` which contradicts `OG_LEVELS` (EC range is 1-8, IT is 1-5, AS is 1-8, FI is 1-4). Per plan note, this is **not validated in these tests** and is a **Phase 16 fix item** (OG Classification phase). Flagging for Phase 16 to reconcile the Pydantic model with the canonical OG_LEVELS ranges.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- **Phase 13 (Frontend SPA Shell)** can begin independently — does not require QUESTION_BANK at the build level, only at runtime
- **Phase 15 (Conversational UX)** is now unblocked: can import QUESTION_BANK from `app.data.constants` and render the 4 entries as choice-card steps in the `work_type` conversation phase
- **Phase 16 (OG Classification)** can consume `signals.og_candidates` and `signals.jes_factor_hints` as classification inputs — but the Pydantic model bug noted above must be fixed before the ranker can accept OG levels outside [4, 6]
- All tests pass green, no regressions, phase deliverable complete

---
*Phase: 12-socratic-question-bank*
*Completed: 2026-06-04*
