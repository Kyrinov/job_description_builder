---
phase: 16-og-classification
plan: 04
subsystem: document-preview
tags: [frontend, document-pane, class-04-gate-frontend, class-05-caf-advisory, human-uat]
requires: [16-03]
provides: [classification-pending-state, caf-rank-advisory, getCafEquivalence-helper, CLASS-04-frontend, CLASS-05-frontend]
affects: [17-jes-scoring, 18-jd-composition]
tech-stack:
  added: []
  patterns: [frontend-hard-gate-ux, conditional-caf-advisory, inline-caf-lookup-helper]
key-files:
  created: []
  modified:
    - v2/frontend/src/document.jsx
key-decisions:
  - "Classification & Evaluation section ALWAYS renders (was conditional on cls.status === 'resolved'); driven by record.confirmed_og + record.og_level (v2.0 evidence-based) instead of legacy workType-based cls"
  - "Classification metaItem in Position Identification also uses the new v2.0 fields first, falls back to legacy cls.code for prototype compatibility"
  - "CAF_EQUIV lookup is a static JS dict embedded in document.jsx (not imported from data.jsx) — keeps the helper co-located with its only consumer and avoids bloating data.jsx"
  - "Fallback 'See TBS advisory tables' shown when no CAF rank match found for the og_code+og_level combination — no error thrown, no UX failure"
  - "CAF advisory placement: inside Position Identification section, immediately after the metaItem block, so it's beside the 'Reports to' field as the plan specifies"
requirements-completed:
  - CLASS-04
  - CLASS-05
duration: ~3 min
completed: 2026-06-05T09:25:00Z
---

# Phase 16 Plan 04: Document Preview + CAF Advisory Summary

Wave 3 of 4 for Phase 16 (the final plan). Delivers the document preview's frontend hard gate (CLASS-04) and CAF rank advisory (CLASS-05). All 11 verification steps await human UAT.

## One-liner

Classification & Evaluation section now shows "Classification pending" until OG + level confirmed (CLASS-04 frontend gate); CAF rank advisory block displays beside Reports to when reports_to_military is true (CLASS-05).

## Tasks completed

- **Task 1 (document.jsx)**: Added `getCafEquivalence(ogCode, ogLevel)` helper with a compact CAF_EQUIV lookup covering CR/AS/EC/IT/FI groups. Updated Position Identification section to display the CAF advisory block conditionally. Replaced the `if (cls.status === 'resolved')` gate on Classification & Evaluation with a conditional that always renders the section — shows "Classification pending" when `!r.confirmed_og || !r.og_level`, shows the resolved classification (OG code, name, level) when both are set. Updated the Classification metaItem in Position Identification to prefer the new v2.0 fields.

## Test results

- `npm run build` — exits 0, bundle 195.65 kB (gzip 61.40 kB; +1.66 kB from 193.99 kB baseline)
- `npm test` — 19/19 tests PASS (no test changes; document.jsx changes don't affect unit tests)
- `python -m pytest -q` (backend) — 50/50 PASS, no regressions

## Deviations from Plan

None. Plan executed as written. The 11 verification steps require browser UAT (per the `checkpoint:human-verify` task) which is presented as a checkpoint to the user below.

## UAT Checkpoint

The plan's Task 2 is a `checkpoint:human-verify` gate. All 11 verification steps need to be run in a browser to confirm visual output. The steps are:

1. Start backend: `cd v2/backend && uvicorn app.main:app --reload --port 8000`
2. Start frontend: `cd v2/frontend && npm run dev`
3. Open http://localhost:5173
4. Verify document preview shows "Classification pending" initially
5. Verify `reports_to_military` step appears in Phase 0
6. Verify `og_confirm` step appears in Phase 2 with OG cards + AS/EC alert
7. Verify `og_level` step appears with correct number of level buttons
8. Verify Classification & Evaluation section unlocks after OG + level confirmed
9. Verify CAF rank advisory displays when reports_to_military = "Yes"
10. Verify backend API works (curl checks)
11. Verify full test suite is GREEN

User should type "approved" or describe which steps failed.
