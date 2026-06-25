---
phase: 21-og-expansion-preview-fix
status: paused-for-planning-handoff
created: 2026-06-10
handoff_target: claude-planning-session
---

# Phase 21 Handoff — Planning Decisions Needed

## Current State (2026-06-10)

**Phase 21 OG Expansion + Preview Fix** is functionally complete across 6 plans and 4 waves, with 3 rounds of user-verified bugfixes applied. The user has paused execution to take planning decisions to a separate Claude planning session.

## What's Complete (17 commits on `master`)

### Plans Executed (6/6)

| Plan | Wave | Status | Commits |
|------|------|--------|---------|
| 21-01 Wave 0 test scaffolding | 1 | Complete | 3 |
| 21-02 CSS preview fix + NON_EC_STANDARD_NAMES consolidation | 1 | Complete | 3 |
| 21-03 Atomic constant extension for 16 OG groups | 2 | Complete | 3 |
| 21-04 JES service routing (point-rating + level-description) | 3 | Complete | 1 |
| 21-05 Sector-gate + cluster questions | 3 | Complete | 3 |
| 21-06 Sub-group disambiguation API + frontend | 4 | Complete + 3 bugfix rounds | 9 |

### Bugfix Rounds Applied to Plan 21-06

**Round 1** (post-execution): Sub-group picker didn't render in the running app
- Root cause: `cfgOverride` in `app.jsx` did not pass `subgroup_alert` to `OgConfirmList`, and the `/api/og/classify` call at `noc_confirm` did not include `confirmed_og` in the body
- Fix: Made `OgConfirmList` self-contained with local `useEffect` that re-calls the API with `confirmed_og` in the body
- Commits: `f6ae8c7`, `ca44700`, `9f53187`

**Round 2** (post-execution): Sector/cluster questions were asked regardless of context
- Root cause: The 4 cluster questions were always in the linear STEPS array with no gating
- Fix: Added `isStepVisible(step, answers)` predicate that gates cluster questions on the `qb_sector_gate` answer. `getVisibleSteps(STEPS, answers)` filters the array.
- Commits: `f6ae8c7`, `ca44700`, `9f53187`

**Round 3** (post-execution): Screen went blank after selecting "patient care"
- Root cause: `answeredSteps = STEPS.slice(0, stepIndex)` included invisible cluster questions. Transcripts `a => a.title` threw TypeError when `answer === undefined`. React unmounted the whole tree → blank screen.
- Fix: Filter `answeredSteps` to only include steps with `answers[step.id] !== undefined`. Preserves original `STEPS` index in `originalIndex`.
- Commits: `44153ee`, `3754921`, `bc45416`

### Test Status

- **Backend:** 103/103 tests pass (no regression across 3 bugfix rounds)
- **Frontend:** 43/43 tests pass (was 31, +12 new regression tests across bugfix rounds)
- **Build:** Clean (216.17 kB JS / 24.86 kB CSS, gzip 66.46 kB / 5.50 kB)

## Known Planning Gap (User-Flagged)

### Issue: Original 4 Socratic Questions are too narrow

**User's words (verbatim):**
> "The prior selections in the socratic questions are too narrow. Are these addressed in future phases or is this a failure of planning, the questions are still largely holdovers from the EC/AS/IT/EX only phase."

**Root cause analysis:**

- **Phase 12** (v2.0, completed 2026-06-04) authored the original Socratic question bank with **4 Socratic work-type entries covering only EC, AS, IT, FI** (14 answer options total). This was deliberately narrow because v2.0 was the "minimum viable" conversational shell.
- **Phase 15** (v2.0) reshaped the conversation flow but kept the same 4 Socratic questions.
- **Plan 21-05** (this phase) added a **sector-gate + 4 cluster questions** (healthcare, legal, education, technical) to expand coverage for the 12 new OG groups. That's a **structural addition**, not a rewrite of the original 4 questions.
- **Phase 23** (Writing Guide Integration) is the **scheduled** phase to fully reshape the Socratic questions per `data/AI Docs/Job Description Writing Guide.docx`. That's where the original 4 questions get broadened to cover all 16 OG groups with duty-language appropriate to each.

**Assessment:** This is a **legitimate planning gap**. The v3.0 milestone is shipping OG expansion (16 groups) but the Socratic question content was not fully expanded alongside. The original 4 Socratic questions are still EC/AS/IT/FI-focused, and only the sector/cluster overlay added by 21-05 expands coverage structurally. A user classifying a position in NT, PO, WP, LC, LP, MT, FS, or FB still has a narrow conversational path because the original 4 Socratic questions are unchanged.

**Trade-offs to discuss in planning:**

1. **Defer to Phase 23 (current plan):** Accept that v3.0 ships with partially-narrow questions; Phase 23 will do a full rewrite per the Writing Guide. Risk: the OG expansion feature in v3.0 is not fully usable for 8 of the 12 new OG groups until Phase 23.

2. **Plan a Phase 21.1 gap-closure phase:** Add a fix-up phase to broaden the 4 original Socratic questions + add new ones for the underserved groups. ~3-4 hours of work, ~3-4 plans. Risk: defers the v3.0 milestone by a sprint.

3. **Expand in this continuation:** Have the executor broaden the questions now. Risk: the expansion may conflict with the planned Phase 23 rewrite.

## Files & Locations

### Key Source Files
- `v2/frontend/src/app.jsx` — App component, `commit()`, `activeStepIndex`, `getVisibleSteps`
- `v2/frontend/src/data.jsx` — STEPS array, QUESTION_BANK mirror, QUAL_DEFAULTS
- `v2/frontend/src/components.jsx` — OgConfirmList with sub-group picker
- `v2/backend/app/data/constants.py` — QUESTION_BANK, OG_DEFINITIONS, NON_EC_TOTALS, JES_FACTORS_BY_GROUP, SUBGROUP_DISAMBIGUATIONS
- `v2/backend/app/api/og_classification.py` — SubGroupAlert, confirm-subgroup endpoint
- `v2/backend/app/services/jes_service.py` — 3-way routing (EC, point-rating, level-description)
- `v2/frontend/src/styles.css` — `.asec-alert` block, `.doc-scroll` align-items

### Phase Artifacts
- `.planning/phases/21-og-expansion-preview-fix/21-01-PLAN.md` through `21-06-PLAN.md`
- `.planning/phases/21-og-expansion-preview-fix/21-01-SUMMARY.md` through `21-06-SUMMARY.md` (303 lines, includes all 3 bugfix rounds)
- `.planning/phases/21-og-expansion-preview-fix/21-RESEARCH.md`
- `.planning/phases/21-og-expansion-preview-fix/21-UI-SPEC.md`
- `.planning/phases/21-og-expansion-preview-fix/21-VALIDATION.md`
- `.planning/phases/21-og-expansion-preview-fix/21-PATTERNS.md`

### Requirements
- OGX-01 through OGX-07 — all 7 OG expansion requirements
- UI-01 — document preview fix

## Recommended Next Steps (for Claude planning session)

1. **Decide on the question-breadth gap** (the planning decision the user is bringing to you):
   - Option A: Defer to Phase 23 (current roadmap)
   - Option B: Insert Phase 21.1 gap-closure (new phase)
   - Option C: Expand in this continuation (would require another execution round)

2. **If Option A (defer):** Run `code-review` and `verify-phase-goal` for Phase 21 to confirm completion despite the question-narrowness known issue. Update `PROJECT.md` to document the gap as a known limitation.

3. **If Option B (Phase 21.1):** Plan the new phase using `/gsd-plan-phase 21.1 --gaps` after VERIFICATION.md is generated. The plan should broaden the 4 original Socratic questions and add 4-6 new ones for the 8 underserved groups (NT, PO, WP, LC, LP, MT, FS, FB).

4. **If Option C (expand now):** Re-execute the continuation agent with broader scope. Be aware that this will conflict with the planned Phase 23 rewrite.

5. **After the question-breadth decision is made,** continue with the post-execution gates:
   - Code review (auto-invoked)
   - Regression gate (skip if no prior phases' tests apply)
   - Schema drift gate (skip if no schema changes)
   - Phase verification (gsd-verifier)
   - Roadmap update and phase completion

## Open Issues / Notes

- The user has explicitly stated they want to make the planning decision elsewhere, not in this execution session
- The screen-blank bug is now fixed; the user should re-verify before phase is formally closed
- The 4 original Socratic questions are unchanged from Phase 12/15; the sector/cluster overlay (plan 21-05) is a structural addition, not a content rewrite
- Phase 23 (Writing Guide Integration) is the scheduled phase for the full Socratic question reshape per `data/AI Docs/Job Description Writing Guide.docx`

---

**Handoff prepared by:** orchestrator session
**For:** Claude planning session
**Date:** 2026-06-10
**Resume command (when ready):** `/gsd-execute-phase 21` (will re-verify Phase 21 after planning decision)
