---
status: pending-retest
phase: 17-jes-scoring
source: [17-04-PLAN.md, 17-04-SUMMARY.md, 17-04-SUMMARY.md]
created: 2026-06-08
updated: 2026-06-08
priority: medium
subsystem: jes-frontend-render
tags: [uat-deferred, browser-rendering, jes-04, fixes-applied]
---

# Phase 17 — Human UAT Items (deferred, fixes applied)

> **Update 2026-06-08:** A follow-up debug session identified the actual
> root cause — the render gate in `document.jsx:293` was `r.jes_scores &&
> r.jes_scores.length > 0`, which fails for non-EC groups (backend returns
> `factors: []` by design for FI/IT/AS/EN). The gate was changed to
> `r.jes_total_points != null` in commit `723f3d8`, with 2 regression tests
> added to `document.test.jsx` (24/24 frontend tests green). The three
> fixes in place (commits `7ad3568`, `a8b1c8e`, `723f3d8`) address all
> identified root causes. Visual browser retest is still pending at user
> request; phase 17 is proceeding to completion per user direction.

# Phase 17 — Human UAT Items (deferred)

## Context

Phase 17 automated test gate is GREEN (58 backend + 22 frontend tests passing; `npm run build` exits 0). All four plans (17-01 through 17-04) executed and committed on `master`.

The browser-based visual UAT (Plan 17-04 Task 2) could not be completed by the user across two attempts after two commits (`7ad3568`, `a8b1c8e`) addressing:
1. WD PATCH payload missing root-level `confirmed_og` / `og_level` (causing 409 on `require_og_confirmed`)
2. Race condition where the JES fetch could fire before the main WD PATCH committed

The user is deferring the UAT for a future review session.

## Outstanding Test Items

### Test A — EC JES scorecard render (DEFERRED)
- Walk through: title → branch → reports → supervises → summary → 4 Socratic Qs → NOC confirm → OG confirm → OG level (EC-05) → duties → quals → Finish & review
- **Expected (Section 4 — Classification & Evaluation, right preview pane):**
  - Static classification block at top of section with **EC-05 badge** (small dark box) + "Economics and Social Science Services — Occupational group EC at level 05..."
  - **JES scorecard below the static block** with 9 per-factor rows: name / `D{degree}` / `{points}`
  - **Totals row at bottom**: "Total — EC JES 2017" + total points
- **Actual (user report, 2026-06-05):** No badge, no scorecard rows, no totals.

### Test B — non-EC totals line (DEFERRED)
- Walk through with IT work type → IT OG → level 4
- **Expected (Section 4):** Single totals line "Evaluated under the IT Job Evaluation Standard | 480 pts" (no per-factor rows)
- **Actual:** Not tested yet (Test A blocked first).

### Test C — Override UI for failed factor (DEFERRED)
- Manually set a factor's `degree` to `-1` in the network response and confirm the number input renders in place of the `D{n}` span
- **Expected:** Override number input visible for the degree=-1 factor
- **Actual:** Not tested yet.

## What was verified

- Backend test suite: 58/58 passing (50 prior + 8 new JES tests)
- Frontend test suite: 22/22 passing (19 prior + 2 ClassBlock render + 1 regression test for the WD PATCH root-level mirror fix)
- Build: `npm run build` exits 0, bundle 199.37 kB / 62.29 kB gzipped
- End-to-end API: `POST /api/jes/score` with `og_code=EC` returns 200 with 9 factors (verified via curl during debug session)

## Hypotheses for the browser render failure (untested)

1. **Stale browser tab** — Vite HMR should pick up the change, but a hard refresh was not confirmed.
2. **Dev environment not actually restarted** between commits — old code may still be serving.
3. **Backend not running on the port the frontend expects** — `fetch('/api/...')` is relative; if the dev server proxies to a different port, calls could 404 silently.
4. **State issue in `record.confirmed_og` shape** — if it's a string instead of an OGCandidate object, `r.confirmed_og.og_code` would be `undefined` and the static block would silently not render.
5. **CSS / hidden element** — the scorecard might be rendered but invisible due to a layout issue (less likely; no test in the area would have caught this).

## Next Steps for Future Review

1. Start with a **clean restart**: `pkill -f uvicorn; pkill -f vite`, then start both fresh.
2. **Hard refresh** the browser (Ctrl+Shift+R / Cmd+Shift+R).
3. Walk through Test A. If still no scorecard:
   - Open dev tools → Network tab → verify `PATCH /api/wd/{id}` body includes `confirmed_og` and `og_level` at root
   - Open dev tools → Network tab → verify `POST /api/jes/score` returns 200 with `factors: [...]`
   - Open dev tools → Console → paste any red errors
4. If the API calls succeed but the scorecard doesn't render, the issue is in `document.jsx` Section 4 render path (lines 257-312). Likely candidates: `r.confirmed_og` shape mismatch, or `r.jes_scores` not propagating to `liveRecord`/`record` props passed to `DocumentPane`.

## Tests

- `total: 3`
- `passed: 0`
- `issues: 0`
- `pending: 3`
- `skipped: 0`
- `blocked: 0`

## Gaps

| # | Description | Status |
|---|-------------|--------|
| 1 | Test A — EC JES scorecard render (no badge, no rows, no totals) | open |
| 2 | Test B — non-EC single totals line | not-started |
| 3 | Test C — Override UI for failed factor | not-started |
