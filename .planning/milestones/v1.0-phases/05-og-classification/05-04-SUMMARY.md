---
phase: 05-og-classification
plan: 04
subsystem: ui
tags: [jinja2, htmx, css, og-classification, asec-alert, og-confirmed]

# Dependency graph
requires:
  - phase: 05-og-classification
    plan: 03
    provides: og_classification router, /api/og/classify and /api/og/confirm endpoints
provides:
  - templates/partials/og_results.html — 3 OG candidate cards + AS/EC alert
  - templates/partials/og_confirmed.html — success state with disabled JD CTA
  - templates/wizard/step_og.html — full wizard step extending base.html
  - app/static/css/main.css layer 8 — .og-candidates, .og-card, .asec-alert, .og-confirmed-banner
  - Warning CSS custom properties (--color-warning-bg/text/border)
affects: [06-jd-generation]

# Tech tracking
tech-stack:
  added: []
  patterns: [blockq uote + cite for verbatim TBS source attribution, .asec-alert amber banner with 1fr/1fr responsive comparison, .og-confirmed-banner matches .confirmation-banner pattern, CSS custom properties for warning tokens]

key-files:
  modified:
    - templates/partials/og_results.html
    - templates/partials/og_confirmed.html
    - templates/wizard/step_og.html
    - app/static/css/main.css

key-decisions:
  - "AS/EC alert uses CSS warning tokens (--color-warning-bg #FFF8E1) defined in :root for consistent future reuse"
  - "og_candidates grid uses auto-fit minmax(280px, 1fr) — adapts to viewport without media queries"
  - "Each OG card has independent level select and Confirm form — supports advisor reviewing multiple options before deciding"
  - "og_confirmed.html has a disabled 'Continue to JD Generation' button — placeholder for Phase 6 wiring (avoids broken link UX)"
  - "Step 5 wizard template uses hx-target=#og-results with hx-swap=innerHTML (partial in-place swap, not outerHTML — preserves form state)"

patterns-established:
  - "Verbatim citation pattern: <blockquote>{{ source_text }}</blockquote><cite>{{ source_name }}</cite>"
  - "OG level select uses {{ '%02d'|format(level) }} — zero-padded level numbers match TBS notation (e.g., EC-04 not EC-4)"

requirements-completed: [CLASS-01, CLASS-02, CLASS-03]

# Metrics
duration: 3min
completed: 2026-06-02
---

# Phase 5 Plan 04 Summary

**Phase 5 HTMX templates (og_results, og_confirmed, step_og) and CSS layer 8 — full OG classification UI with AS/EC alert and per-card level select + confirm flow**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-02
- **Completed:** 2026-06-02
- **Tasks:** 2/2
- **Files modified:** 4 (3 modified, 1 created: step_og.html)

## Accomplishments

- `templates/partials/og_results.html` — 3 OG candidate cards (definition + inclusions + exclusions as blockquote + cite) with optional AS/EC alert banner (2-column AS vs EC comparison + directive authority citation) and independent per-card level select + Confirm form
- `templates/partials/og_confirmed.html` — success state with OG code/name/level and disabled "Continue to JD Generation" CTA placeholder
- `templates/wizard/step_og.html` — full wizard step extending `base.html` with HTMX form (hx-target=og-results, hx-swap=innerHTML)
- `app/static/css/main.css`:
  - Added `--color-warning-bg/text/border` to `:root`
  - Layer 8: `.og-candidates` grid, `.og-card`, `.og-card-header`, `.og-card-section`, `.og-level-select`, `.asec-alert` (amber warning), `.asec-comparison` (1fr/1fr responsive), `.asec-card`, `.asec-directive-authority`, `.og-confirmed-banner`
  - Updated top comment from "Phase 4 only" to "Phase 4 + Phase 5 components"

## Task Commits

1. **Task 1: Templates + CSS** — `debea3d` (feat)
2. **Task 2: Human verify (deferred to interactive session)** — pending

## Files Created/Modified

- `templates/partials/og_results.html` — REPLACED stub with full implementation (113 lines)
- `templates/partials/og_confirmed.html` — REPLACED stub with full implementation (12 lines)
- `templates/wizard/step_og.html` — NEW (24 lines)
- `app/static/css/main.css` — added warning tokens to :root + appended layer 8 (~145 lines)

## Decisions Made

- AS/EC alert uses CSS warning tokens (`--color-warning-bg` `#FFF8E1`) for consistency and future reuse
- og_candidates grid uses `auto-fit minmax(280px, 1fr)` — adapts to viewport without media queries
- Each OG card has independent level select and Confirm form — supports advisor reviewing multiple options before deciding
- og_confirmed.html has disabled "Continue to JD Generation" button — placeholder for Phase 6 (avoids broken link UX)
- OG level select uses `{{ '%02d'|format(level) }}` — zero-padded level numbers match TBS notation (EC-04 not EC-4)

## Deviations from Plan

None - plan executed as written. CSS comment update and warning tokens added as specified.

## Issues Encountered

None. All Jinja2 templates parsed and rendered cleanly under the test smoke check. pytest suite: 114 passed, 1 skipped (deferred Phase 6 gate).

## Human Verification (deferred to interactive session)

This plan is `autonomous: false` (checkpoint:human-verify). The CLI cannot perform the 11-point browser verification (server start, browser interaction, screenshot of AS/EC alert, etc.). All template rendering and route integration is verified via the test suite and Jinja2 smoke checks. When the user runs the app in a browser:

1. Start: `cd /home/charles/job_description_builder && uvicorn app.main:app --reload`
2. Open http://localhost:8000, enter policy-related work description
3. Submit through NOC mapping → confirm a NOC → click "Continue to OG Classification"
4. Verify: AS/EC alert banner (amber #FFF8E1) appears, 3 OG cards with verbatim blockquotes render
5. Select a level, click Confirm → og_confirmed.html renders
6. Repeat with non-policy description to verify AS/EC alert does NOT appear

## Post-Execution Bug Fixes (advisor UAT, 2026-06-02)

Three issues surfaced during interactive testing of the Phase 5 wizard and were fixed immediately. **Phase 6 planner should be aware of these patterns to avoid repeating them.**

### Fix 1: TEER display bug — `9f341a6`
**Symptom:** All 516 NOC units showed "TEER 5" in the browser.
**Root cause:** `scripts/ingest_noc.py` (Phase 2) was storing the structure CSV `Level` column (NOC hierarchy depth, always 5 for unit groups) as `teer_level`. The correct TEER is the **second digit of the NOC code** per NOC 2021 v1.0 spec (Major Group 10–14 definitions).
**Lesson for Phase 6:** Ingest scripts that map a "natural" CSV column to a domain field can silently store the wrong data when the column meanings collide (NOC hierarchy `Level` vs TEER classification). Always spot-check rendered values against a known reference (e.g., NOC 21232 Software developers should be TEER 1, not TEER 5).
**Files:** `scripts/ingest_noc.py` (added `derive_teer_from_code()`), new `scripts/fix_teer_levels.py` (one-shot migration for existing DBs), `tests/conftest.py` (`noc_mapping_db` fixture TEER for 21232 corrected from "2" to "1"). `app.db` rows updated in place (471 of 516 fixed; new distribution TEER 0/1/2/3/4/5 = 48/97/162/69/95/45).

### Fix 2: OG select "nothing happens" — `9f341a6`
**Symptom:** Clicking the level `<select>` dropdown did nothing visible.
**Root cause:** The dropdown correctly sets a value, but the form only submits when the user clicks **Confirm [OG]**. No visual cue tied the dropdown state to the button state.
**Lesson for Phase 6:** When using a `<select required>` + submit button pattern, the submit button should be disabled until a non-empty value is chosen. Confirms intent and prevents HTML5 validation tooltip confusion.
**Files:** `templates/partials/og_results.html` — added `onchange="this.form.querySelector('button[type=submit]').disabled = !this.value"` and initial `disabled` attribute on the Confirm button. The confirm form is functional via direct API call (test `test_classify_og_returns_3_candidates` etc.); the change is purely UX.

### Fix 3: "Continue to OG Classification" silently 404'd — `31a2f69`
**Symptom:** Clicking the button caused the page to "glitch to centre" with no response.
**Root cause:** `/api/noc/confirm` (Phase 4 route) was rendering `partials/noc_confirmed.html` for HTMX requests but the template context was missing `wd_id`. The hidden input `<input type="hidden" name="wd_id" value="">` rendered empty. When the user clicked Continue, the form posted with `wd_id=""` to `/api/og/classify`, which looked up the WD, found nothing, and returned 404. HTMX swallows 4xx responses by default (no swap), so the page appeared to do nothing.
**Lesson for Phase 6:** HTMX dual-path routes must pass ALL form-required variables to the template context, not just the visible data. JSON and HTML response paths can drift apart silently — write a regression test that asserts the hidden inputs are non-empty in the HTML response. The added test `test_confirm_noc_htmx_renders_wd_id_in_continue_form` catches this exact bug.
**Files:** `app/api/noc_mapping.py:138` (added `"wd_id": wd_id` to template context), `tests/test_noc_mapping.py` (new regression test).

## Phase 6 (JD Generation) Handoff Notes

What's ready on `WorkDescription` for Phase 6:

| Field | Set by | Value (example) |
|-------|--------|-----------------|
| `wd.confirmed_noc` | Phase 4 | `NOCMatch(noc_code="21232", teer_level="1", ...)` |
| `wd.confirmed_og` | Phase 5 | `"EC"` |
| `wd.confirmed_level` | Phase 5 | `"EC-04"` |
| `wd.og_level` | Phase 5 | `"EC-04"` (same value; TBS header field) |
| `wd.og_recommendation` | Phase 5 | `OGRecommendation(og_code="EC", evidence_quotes=[...], cited_articles=[ProvenanceTag, ...], confirmed_by_advisor=True, level="EC-04")` |
| `wd.stage` | Phase 5 → Phase 6 | `"og_classified"` — Phase 6 must gate on this |

Patterns Phase 6 should reuse from Phase 5:

1. **Stage gate at API layer** — Both `/api/og/classify` and `/api/og/confirm` return 422 with descriptive detail when `wd.stage != expected`. Phase 6's `/api/jd/generate` must do the same: 422 if `wd.stage != "og_classified"`.
2. **Verbatim guardrail** — `_strip_fabricated_quotes(quotes, og_full_text)` returns only entries that are substrings of the source text. Phase 6's duty selection must apply the same pattern: any duty text that isn't verbatim from `noc_elements` must be flagged with `source_type="ADVISOR"`.
3. **Pure-function helpers** — `_build_asec_alert(og_rows)` is a pure function (no DB access) — it takes data and returns data. Phase 6's `orphan_statement_check()` and `cite_provenance_for_duty()` should follow the same pattern for testability.
4. **ProvenanceTag fields actually used** — `source_type`, `source_id`, `source_version`, `retrieved_date=date.today()`, `model_name=settings.generation_model`. NOT `source_text` or `ingested_at` (they don't exist in the model — this was a deviation noted in 05-03-SUMMARY.md).
5. **Instructor singleton pattern** — `og_instructor_client` is module-level, never constructed per-request. Phase 6 should add its own instructor client (e.g., `duty_selection_client`) in `app/ai/duty_selection.py` following the same pattern.

## Next Phase Readiness

- Phase 5 is functionally complete: backend pipeline, routes, templates, and CSS all in place
- Phase 6 (JD Generation) can proceed — confirmed_og and confirmed_level are now persisted on WorkDescription
- CLASS-02 stage gate is enforced — JD generation will get 422 if OG is not confirmed
- Human verification pending: will surface in `/gsd-progress` until advisor runs the wizard in browser

---
*Phase: 05-og-classification*
*Completed: 2026-06-02*
