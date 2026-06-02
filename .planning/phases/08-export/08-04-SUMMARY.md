---
phase: 08-export
plan: 04
subsystem: ui
tags: [jinja2, htmx, css, wizard, export, docx, d-09, d-10]

# Dependency graph
requires:
  - phase: 08-export
    provides: "export_service.generate_export (async DOCX render) + app/api/export.py (HTMX dual-path /docx + 501 /pdf stub) + wizard_export route with TemplateNotFound fallback (08-01 + 08-02 + 08-03)"
provides:
  - "templates/wizard/step_export.html — D-09 terminal wizard step with hidden wd_id input, version manifest preview note, HTMX-driven Download DOCX CTA (plain href retained for non-HTMX download), and PDF-501 copy"
  - "templates/partials/export_result.html — HTMX success partial showing Export Complete, SHA-256 export_hash, and a re-download link (consumed by /export/{wd_id}/docx when HX-Request is set)"
  - "templates/partials/jes_scores.html — activated 'Continue to Export' CTA (no aria-disabled, button--primary) — closes the Phase 7→8 wizard handoff that previously left the link disabled"
  - "app/static/css/main.css — CSS Layer 11 (Export components): .export-result, .export-hash, .export-errors, .export-error-card, .export-error-card--blocking with existing CSS custom properties + literal fallbacks"
  - "app/static/css/main.css — header layer-index comment extended to register Layer 11"
affects:
  - 08-04 (next plan; this plan is the final Phase 8 plan pending human verify)
  - Phase 9 (DND DRF Integration) — will inherit the export pipeline + style conventions

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HTMX-on-anchor pattern: anchor with both `href` and `hx-get` so the same element works for direct file download (no JS) AND for the HTMX-driven inline partial swap (with target/indicator). Plan's interface comment notes this preserves the non-HTMX download path."
    - "HTMX success partial lives at templates/partials/ and is rendered by the export router when the HX-Request header is set — mirror of the jes_scores.html pattern from 08-03"
    - "CSS token + literal-fallback pattern extended: every Layer 11 rule uses `var(--color-X, #hex)` so the rule renders correctly even if the design-token layer is stripped. Matches Layer 10 (.jes-*) style."
    - "Wizard template stays a single static page: validation_errors and full manifest are NOT server-rendered into the page on GET; the step is intentionally minimal and the export router's 422 carries the named factors to the user via the HTMX response (per 08-03 interface note)"

key-files:
  created:
    - templates/wizard/step_export.html
    - templates/partials/export_result.html
  modified:
    - templates/partials/jes_scores.html
    - app/static/css/main.css

key-decisions:
  - "Made the Download DOCX anchor a hybrid hx-get + href: HTMX requests swap the success partial into #export-result; non-HTMX clicks still stream the binary file directly via the existing /export/{wd_id}/docx binary branch. This satisfies D-10 (re-export allowed) and the D-09 'Download DOCX button' UI requirement without forcing a JS-only path."
  - "Chose `button--primary` (not `button--secondary`) for the now-active 'Continue to Export' CTA — visually signals the export step is the wizard's terminal goal, not a secondary action. Removed the `title='Available in Phase 8'` tooltip alongside `aria-disabled` since both were phase-deferral affordances with no meaning once the destination exists."
  - "Kept the wizard step minimal: no server-side rendering of validation_errors, jes_total_points, or full manifest into step_export.html. The plan's interface note explicitly says 'Keep the page simple — no extra service call from main.py is in scope; the Download CTA surfaces the block via the HTMX response.' The version-manifest preview is a static explanatory paragraph, not a data table, because the manifest is rendered into the DOCX by the service (08-02 build_version_manifest)."
  - "Layer 11 styled .export-error-card + .export-error-card--blocking defensively even though no current template renders the per-factor error card inline. The classes are immediately available when a future plan adds inline error rendering (D-01 visual treatment). No dead code — the .export-errors <ul> block is the stylesheet's natural target for any server-rendered 422 response."
  - "Did NOT add the layers 9 and 10 entries to the header layer-index comment — the plan only required adding Layer 11. Adding the missing 9/10 entries would be a scope expansion outside the plan's file_modified list and outside the task's <action> block. The pre-existing drift is a known-but-deferred issue."

patterns-established:
  - "Wizard step hybrid HTMX anchor: both hx-get AND href, targeting a swap div by id, with an indicator span. The same idiom applies to any future 'click-to-trigger' terminal wizard action (download, submit, finalize)."
  - "Continue-to-next-step CTA activation is a one-line edit: drop aria-disabled + title, promote to button--primary. This is the canonical close-the-handoff pattern for any cross-phase wizard transition."

requirements-completed: [EXP-01]

# Metrics
duration: 5min
completed: 2026-06-02
---
# Phase 8 Plan 04: Export UI Summary

**Export wizard step + HTMX success partial + activated JES→Export CTA + CSS Layer 11 — completes the Phase 8 export surface from the advisor's perspective; human verify still pending.**

> **Note:** This plan contains three tasks. The executor ran Tasks 1 and 2 (the two `type="auto"` tasks) and stopped before Task 3 (`type="checkpoint:human-verify"`). Task 3 — the end-to-end browser verification of DOCX download, advisor markers, version manifest, and 501 PDF — is **pending** and will be executed by the orchestrator when the human reviews the built flow.

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-02T21:44:08Z
- **Completed:** 2026-06-02T21:49:00Z
- **Tasks:** 2 of 3 complete (Task 3 = human-verify, executed by orchestrator)
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- **`templates/wizard/step_export.html`** — D-09 terminal wizard step. Hidden `wd_id` input, static version-manifest preview note, HTMX-driven Download DOCX anchor (both `href` AND `hx-get` to the same `/export/{wd_id}/docx` URL), `hx-target="#export-result"`, `hx-swap="innerHTML"`, `hx-indicator="#export-spinner"`, and a D-08 PDF note matching the 501 message verbatim. Extends `app/templates/base.html` and follows the `step_jes.html` / `step_og.html` block structure exactly.
- **`templates/partials/export_result.html`** — HTMX success partial. `id="export-result"`, `role="status"`, `.export-result` class. Renders `<h2>Export Complete</h2>`, the `{{ export_hash }}` SHA-256 hex wrapped in `<code>`, and a re-download anchor. Consumed by `app/api/export.py:export_docx` when `HX-Request` is set.
- **`templates/partials/jes_scores.html`** — activated the "Continue to Export" CTA at lines 27-28: removed `aria-disabled="true"`, removed `title="Available in Phase 8"`, and promoted from `button--secondary` to `button--primary`. Closes the Phase 7→8 wizard handoff left disabled in `07-04`.
- **`app/static/css/main.css`** — appended CSS Layer 11 with `.export-result` (bordered card), `.export-hash` (muted monospace-friendly SHA-256 line with `word-break: break-all`), `.export-errors` (D-01 blocking-error list — red border + tinted background), `.export-errors li` (red text), `.export-error-card` (3px left rule for per-factor cards), and `.export-error-card--blocking` (red-tinted variant). All rules use the existing CSS custom properties with literal hex fallbacks, matching Layer 10's style. Header layer-index comment extended to register Layer 11.
- **Verification** — both task `verify` commands pass:
  - `grep -q "/export/{{ wd_id }}/docx" templates/wizard/step_export.html && grep -q "export-result" templates/partials/export_result.html && ! grep -q "aria-disabled" templates/partials/jes_scores.html && echo OK` → **OK**
  - `grep -q "Layer 11" app/static/css/main.css && grep -q ".export-result" app/static/css/main.css && grep -q ".export-errors" app/static/css/main.css && echo OK` → **OK**
- **Test suite** — `python -m pytest -q` → 159 passed, 1 pre-existing skip, 0 regressions.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create step_export.html + export_result.html, activate JES CTA** — `0d04df9` (feat)
2. **Task 2: Add CSS Layer 11 (Export) to main.css** — `3be5c1e` (feat)
3. **Task 3: Human verifies the export flow end-to-end** — **PENDING** (checkpoint:human-verify, executed by orchestrator; not in this executor's scope)

**Plan metadata:** (committed alongside this SUMMARY, see final commit)

## Files Created/Modified

- `templates/wizard/step_export.html` (created, 33 lines) — D-09 terminal wizard step. Hybrid `href` + `hx-get` anchor on the Download DOCX CTA so non-HTMX browsers still get a direct file download while HTMX-aware clients swap the success partial into `#export-result`. Hidden `wd_id` input, version manifest preview note (static copy, not server-rendered), and the D-08 501 message rephrased as a secondary note for the advisor. Extends `app/templates/base.html`.
- `templates/partials/export_result.html` (created, 8 lines) — HTMX success partial. `id="export-result"`, `role="status"`, `.export-result` class. Renders the SHA-256 `{{ export_hash }}` (hex string from `app/services/export_service.py`) inside `<code>`, plus a re-download anchor. The service provides both `export_hash` and `filename` (server-set constant `work_description.docx`).
- `templates/partials/jes_scores.html` (modified, 28 lines, was 29) — lines 27-28: removed the `aria-disabled="true"` attribute, the `title="Available in Phase 8"` attribute, and changed `button--secondary` to `button--primary`. Net diff: -2 lines, 1 line changed.
- `app/static/css/main.css` (modified, +40 lines at end + 1 line in header comment) — Layer 11 added at the END after Layer 10. Six new rules + the comment block. Layer index comment updated to register Layer 11. No other CSS changed.

## Decisions Made

- **Hybrid `href` + `hx-get` on the Download anchor.** The plan specifies this in its action block (Task 1 (a)) and it preserves the existing binary-download path in `app/api/export.py` for any non-HTMX client (curl, browsers with HTMX disabled, etc.) without adding JS. Same link works in both modes; the only behavior difference is whether the result replaces `#export-result` or triggers a file save dialog.
- **`button--primary` for the activated "Continue to Export" CTA.** The deactivated version was `button--secondary` because it was a placeholder; once the destination exists, the CTA deserves the same visual weight as the other step's primary action (e.g. `classify-btn` in `step_og.html`). The export step is the terminal goal of the wizard, so the visual hierarchy is right.
- **No server-rendered `validation_errors` / `jes_total_points` / manifest table in step_export.html.** The plan's `<interfaces>` note is explicit: the wizard route only passes `wd_id`; the validation gate runs at export time and surfaces named factors through the 422 response. Adding server-side fetching of validation state would require either a new endpoint or a `main.py` service call — both out of scope for this plan. The static version-manifest preview note explains what the document will contain.
- **CSS uses literal-fallback convention.** Every Layer 11 rule declares both `var(--color-X, #hex)` and a hex literal. This matches Layer 10's style (e.g. `.jes-source` uses `var(--color-text-muted, #6b7280)`) and makes the rules degrade gracefully if the `:root` token block is ever extracted or re-ordered.
- **`.export-error-card` shipped unused.** No current template renders the per-factor error card. The classes are pre-loaded for a future plan that may add inline error rendering (D-01 visual treatment), and `.export-errors` (the `role="alert"` <ul> block) is the natural target. Documented as "available when pre-export validation errors are surfaced server-side in a future plan" in the CSS commit body.

## Deviations from Plan

None — plan executed exactly as written. Both task `<action>` blocks were followed verbatim:
- Task 1: created `step_export.html` with the exact structure (extends base, hidden wd_id input, version manifest preview, hybrid anchor + indicator + result div, PDF note), created `export_result.html` with the exact HTMX partial body, and edited `jes_scores.html` to swap the disabled `button--secondary` for the active `button--primary` (and drop `aria-disabled` + `title`).
- Task 2: appended the Layer 11 block at the END of `main.css` with the exact six rules (using CSS custom properties with fallbacks) and added the `11. Phase 8 Export components` line to the layer-index header comment.

## Issues Encountered

- **Stale git index lock on first commit attempt.** The first `git commit` failed with `Unable to create '.git/index.lock': File exists`. The lock was leftover from the prior `git add` finishing its atomic file-write before the `add` reported. Lock cleared before the next attempt; no data loss. The pre-existing `templates/docx/work_description_template.docx` binary diff is unrelated to this plan (it's a build-script regeneration drift from 08-02 — out of scope).

## Next Phase Readiness

- All Phase 8 deliverables are now in place from the code-and-templates perspective: service (08-01 + 08-02), router (08-03), and UI (this plan, 08-04). The remaining task is the human-verify checkpoint (Task 3), which the orchestrator will run.
- 159 tests pass + 1 pre-existing skip, 0 regressions.
- No new blockers. The D-08 PDF 501 message and the D-09 wizard step are now both renderable; the D-10 re-export semantic is in the router (08-03); D-01/D-02/D-05/D-06/D-07 are in the service (08-02).
- Phase 9 (DND DRF Integration) is unblocked after Phase 8 verify passes.

---

*Phase: 08-export*
*Completed: 2026-06-02 (Tasks 1+2; Task 3 = human-verify pending)*

## Self-Check: PASSED

All claimed files and commits verified:
- `templates/wizard/step_export.html` — FOUND, 33 lines, contains `extends "base.html"`, `/export/{{ wd_id }}/docx`, `hx-target="#export-result"`, `hx-indicator="#export-spinner"`, `id="export-result"`
- `templates/partials/export_result.html` — FOUND, 8 lines, contains `{{ export_hash }}`, `{{ filename }}`, `Export Complete`, `export-result`
- `templates/partials/jes_scores.html` — modified (28 lines, was 29); contains `/wizard/export?wd_id={{ wd_id }}` and `button--primary`; does NOT contain `aria-disabled` (0 matches) or `title="Available in Phase 8"` (0 matches)
- `app/static/css/main.css` — contains `Layer 11` (2 matches: header index + section comment), `.export-result` (1), `.export-hash` (3), `.export-errors` (2), `.export-error-card` (2)
- Task 1 commit `0d04df9` — FOUND
- Task 2 commit `3be5c1e` — FOUND
- Test suite: 159 passed, 1 pre-existing skip, 0 regressions
