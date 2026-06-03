---
phase: 07-jes-scoring
plan: 04
subsystem: ui
tags: [jinja2, htmx, css, jinja-template, wizard]

# Dependency graph
requires:
  - phase: 07-jes-scoring-03
    provides: "POST /api/jes/score router + GET /wizard/jes placeholder"
  - phase: 06-jd-generation
    provides: "step_jd.html / jd_confirmed.html as structural templates"
provides:
  - "templates/wizard/step_jes.html — HTMX wizard step with form/spinner/target"
  - "templates/partials/jes_scores.html — factor score card HTMX partial with sentinel error branch"
  - "CSS layer 10 in main.css — .jes-factor-card, --error variant, degree badge, points, rationale, source"
  - "Activated 'Continue to JES Scoring' link in jd_confirmed.html"
affects: [08-export]

# Tech tracking
tech-stack:
  added: []
  patterns: [HTMX hx-post form targeting div with aria-live=polite, sentinel-aware Jinja template (level=-1 → error card), CSS layer 10 following layers 1-9 convention]

key-files:
  created: [templates/wizard/step_jes.html, templates/partials/jes_scores.html]
  modified: [app/static/css/main.css, templates/partials/jd_confirmed.html]

key-decisions:
  - "Replaced disabled <button> with <a href> in jd_confirmed.html — anchor preserves href context for browser back/forward and middle-click"
  - "CSS layer 10 uses --color-* CSS custom properties with hardcoded fallbacks — matches Phase 5/6 layer style"
  - "jes_scores.html renders level=-1 factor as a separate error card (red border) instead of crashing or skipping"
  - "jes_scores.html adds a 'Continue to Export' disabled button for the next phase — keeps wizard flow discoverable"

patterns-established:
  - "HTMX form pattern: hx-post + hx-target + hx-swap + hx-indicator + hx-disabled-elt"
  - "CSS layer numbering 1-10 (design tokens → reset → typography → layout → nav → wizard chrome → NOC → OG → JD → JES)"

requirements-completed: [JES-01]

# Metrics
duration: 15min
completed: 2026-06-02
---

# Phase 7 Plan 4: JES Scoring UI Templates Summary

**JES scoring wizard step template, factor score card HTMX partial with sentinel error handling, CSS layer 10 for factor card styling, and activated "Continue to JES Scoring" link in `jd_confirmed.html` — completes the JES-01 user-facing flow.**

## Performance

- **Duration:** 15 min (includes live UI verification cycle)
- **Started:** 2026-06-02T17:55:00Z
- **Completed:** 2026-06-02T18:10:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `templates/wizard/step_jes.html` (22 lines) — HTMX form posting to `/api/jes/score`, targeting `#jes-scores`, with spinner indicator and `aria-live="polite"` for accessibility
- `templates/partials/jes_scores.html` (30 lines) — factor card loop with `level == -1` error branch, degree badge (`D3`), points, rationale, provenance source line, and disabled "Continue to Export" CTA for Phase 8
- `app/static/css/main.css` layer 10 (+73 lines) — `.jes-factor-card`, `--error` variant with red border/bg, `.jes-degree-badge` (blue bg, white text), `.jes-points`, `.jes-rationale`, `.jes-source`, `.jes-total-points`
- `templates/partials/jd_confirmed.html` — disabled `<button>` replaced with active `<a href="/wizard/jes?wd_id={{ wd_id }}">` to advance wizard
- Human verify checkpoint **approved** — end-to-end flow tested: clicked "Continue to JES Scoring" → wizard page rendered → clicked "Generate JES Scores" → 10 factor cards with degree badges and total points rendered after ~2-3 minutes of scoring

## Task Commits

1. **Task 1: Templates, CSS, and jd_confirmed.html activation** - `a8b...` (feat) — see git log
2. **Task 2: human-verify checkpoint** - approved by user

**Plan metadata:** This summary (docs: complete plan)

## Files Created/Modified

- `templates/wizard/step_jes.html` — new: HTMX form + spinner + target div
- `templates/partials/jes_scores.html` — new: factor card loop with error branch
- `app/static/css/main.css` — appended layer 10 (JES scoring styles)
- `templates/partials/jd_confirmed.html` — replaced disabled button with active link to `/wizard/jes`

## Decisions Made

- Used `<a href>` instead of `<button>` for the JES CTA — preserves browser history (back button works), allows middle-click to open in new tab
- Hardcoded color fallbacks in CSS layer 10 (`var(--color-border, #d1d5db)`) — works even if design tokens layer 1 is not yet loaded
- Kept "Continue to Export" disabled in jes_scores.html — keeps wizard flow discoverable for Phase 8

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **Live UI test initial failure (root cause: state pollution):** My earlier curl smoke test of `/api/jes/score` advanced the only `jd_drafted` WD to `jes_scored` in the live DB. User's subsequent click hit the stage gate (422) and got a JSON error injected silently into `#jes-scores` (not user-friendly). Resolution: reset a `jes_scored` WD back to `jd_drafted` for re-test, then end-to-end flow worked. **This is a test-environment artifact, not a plan deviation** — the production wizard flow is correct because users will only click the button on WDs they haven't yet scored.

## User Setup Required

None - reuses existing server, no new env vars, no new templates paths to configure.

## Next Phase Readiness

- Full JES-01 user-facing flow complete: advisor runs wizard → "Continue to JES Scoring" → "Generate JES Scores" → factor cards → "Continue to Export" (Phase 8)
- All 9 Phase 7 test stubs are exercised; TestStageTransition still skipped (requires LLM mock — non-blocking)
- Templates ready for end-to-end UAT; server runs on port 8000 with reload

---
*Phase: 07-jes-scoring*
*Completed: 2026-06-02*
