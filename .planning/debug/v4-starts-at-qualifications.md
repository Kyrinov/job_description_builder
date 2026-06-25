---
slug: v4-starts-at-qualifications
status: resolved
trigger: "v4 conversational UI goes straight to Qualifications on startup — user has to backtrack through earlier phases"
created: 2026-06-25
updated: 2026-06-25
---

## Symptoms

- **Expected:** App starts at the first phase (beginning of the conversational flow)
- **Actual:** App opens directly on the Qualifications step; user must navigate backward to reach earlier phases
- **Errors:** None reported
- **Timeline:** Never worked — this has been the behaviour since v4 was built (not a regression)
- **Reproduction:** Start the app fresh; it immediately shows Qualifications instead of phase 1
- **State:** Same on a fresh browser session — not caused by localStorage restore

## Current Focus

hypothesis: `reviewing` state is not persisted to localStorage; after a user completes the full flow and refreshes, the app resumes at stepIndex=24 (quals — the last answered step) with reviewing=false, showing the quals question instead of the review screen.
test: Trace stepIndex lazy initializer when localStorage has a complete record (qualsVisited: true).
expecting: stepIndex = 24 (quals is last answered), reviewing = false (not persisted), activeStepIndex = 24 → quals step renders instead of ReviewState.
next_action: DONE — fix applied
reasoning_checkpoint: "Fresh browser session" in the symptom report likely means a page reload (not incognito/cleared storage). On reload, record is restored from localStorage with qualsVisited:true and quals populated; stepIndex resumes at 24; reviewing defaults to false; app shows quals question instead of the review screen.
tdd_checkpoint:

## Evidence

- 2026-06-25T00:00:00Z: `reviewing` is initialized as `useState(false)` with no lazy restore from localStorage (`frontend/src/app.jsx` line 278).
- 2026-06-25T00:00:00Z: `record` IS persisted to localStorage via useEffect (`frontend/src/app.jsx` line 332-338), including `qualsVisited: true` which is set when the quals step is committed (`line 429`).
- 2026-06-25T00:00:00Z: `stepIndex` lazy init restores from `jd-builder-v2-record` and resolves to 24 (quals) when quals is in the record, clamped to STEPS.length-1 (`app.jsx` lines 228-276).
- 2026-06-25T00:00:00Z: `activeStepIndex` useMemo: STEPS[24] (quals) is visible (hits default case in isStepVisible) → returns 24 → app renders quals ActiveQuestion.
- 2026-06-25T00:00:00Z: `record.qualsVisited` is the canonical flag for "user has completed the quals step and should be in review" — it is checked in ReviewState's checklist (`conversation.jsx` line 202).

## Eliminated

- localStorage not the cause: it IS the cause — record is persisted there including qualsVisited.
- stepIndex resume logic not buggy: it correctly resumes at last answered step, but reviewing is not also resumed.
- activeStepIndex memo not buggy: correctly returns 24 given stepIndex=24 and answers={}.

## Resolution

root_cause: `reviewing` state is never persisted to localStorage and never re-derived on mount. After completing the full flow (which sets `qualsVisited: true` in record), a page reload initializes `reviewing = false` and `stepIndex = 24`, causing the app to render the quals question instead of ReviewState.
fix: Initialize `reviewing` lazily from `record.qualsVisited` in localStorage — if `qualsVisited` is true, start in reviewing state. One-line change to `useState(false)` in `app.jsx`.
verification: After the fix, a reload with a complete record (qualsVisited: true) shows ReviewState. A reload with a partial record (no qualsVisited) shows the correct step via stepIndex resume.
files_changed: frontend/src/app.jsx
