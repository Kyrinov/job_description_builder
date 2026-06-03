---
phase: 09-dnd-drf-integration
plan: 03
subsystem: api
tags: [fastapi, htmx, docxtpl, drf, export, router]

# Dependency graph
requires:
  - "09-01 (WorkDescription.is_dnd_position + drf_linkages fields; drf_rows table)"
  - "09-02 (drf_service.get_drf_candidates + confirm_drf_linkages; ingest_drf.py)"
provides:
  - "app/api/drf_integration.py with 3 routes (GET candidates, POST confirm, POST flag-dnd) — HTMX dual-path on get + confirm"
  - "drf_integration router mounted in app/main.py"
  - "/wizard/drf GET route (placeholder HTML until 09-04 ships step_drf.html)"
  - "export_service._build_context() returns drf_linkages + is_dnd_position keys"
  - "export_service.build_version_manifest() emits a ProvenanceTag per confirmed DRF linkage"
  - "DOCX template (Section 6: DRF Linkages) gated by {%p if is_dnd_position %}, table-row for/data/endfor loop"
affects: [09-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HTMX dual-path pattern (request.headers.get('HX-Request')) reused from jes_scoring/export for drf_integration routes"
    - "Flag/toggle route pattern: load WD via asyncio.to_thread, model_copy, save via asyncio.to_thread — never advances stage"
    - "Docxtpl {%p if is_dnd_position %} paragraph-level gate for the whole DRF section"
    - "ProvenanceTag synthesized at manifest emission time (source_type='DRF', source_version='DND DRF Dataset 2021-2022')"
    - "Build script self-asserts contract variables (drf_linkages, is_dnd_position) at rebuild time, not at first export"

key-files:
  created:
    - app/api/drf_integration.py
  modified:
    - app/main.py
    - app/services/export_service.py
    - scripts/build_docx_template.py
    - templates/docx/work_description_template.docx

key-decisions:
  - "DRF router uses the same _map_value_error idiom as jes_scoring (404 for 'not found', 422 for other ValueErrors) — keeps IDOR handling uniform across phase routers"
  - "flag-dnd route does not advance stage (annotation, not workflow transition — same principle as the DRF service layer)"
  - "DRF section in DOCX is gated by paragraph-level {%p if is_dnd_position %} so the entire Section 6 disappears for non-DND positions without an empty table shell"
  - "Manifest emits a ProvenanceTag per confirmed DRF linkage with source_version='DND DRF Dataset 2021-2022' — matches the dataset's published vintage"
  - "build_docx_template.py adds a runtime assertion (required_new_vars <= declared vars) so a missing section is caught at rebuild time, not at first export"

requirements-completed: [DRF-01]

# Metrics
duration: 15min
completed: 2026-06-03
---

# Phase 9 Plan 03: DND DRF API + Export Integration Summary

**DRF HTTP layer (GET candidates / POST confirm / POST flag-dnd with HTMX dual-path) wired into main.py; export_service extended with drf_linkages context + DRF ProvenanceTag emission; DOCX template rebuilt with a DND-gated Section 6 (DRF Linkages) and 14 declared variables**

## Performance

- **Duration:** 15 min
- **Started:** 2026-06-03T12:54:09Z
- **Completed:** 2026-06-03T13:09:00Z
- **Tasks:** 3
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments

- `app/api/drf_integration.py` (151 lines, new): 3 routes — `GET /api/drf-links/{wd_id}` returns candidates (HTMX partial or JSON), `POST /api/drf-links/{wd_id}/confirm` stores confirmed linkages (HTMX partial or JSON), `POST /api/drf-links/{wd_id}/flag-dnd` toggles `is_dnd_position` (HTMX partial or JSON). All three use `_map_value_error` (404 for missing WD, 422 for other errors) matching the `jes_scoring` router convention.
- `app/main.py` extended: `from app.api import drf_integration`, `app.include_router(drf_integration.router)`, and a new `wizard_drf` route at `/wizard/drf` that loads `is_dnd_position` + `drf_linkages` from the WD and falls back to placeholder HTML if `templates/wizard/step_drf.html` is not yet shipped (plan 09-04's job).
- `app/services/export_service.py` extended: `_build_context()` now returns `drf_linkages` (filtered to confirmed linkages on DND positions) and `is_dnd_position`. `build_version_manifest()` emits a `ProvenanceTag` per confirmed DRF linkage with `source_type='DRF'`, `source_version='DND DRF Dataset 2021-2022'`, and `provenance_source_id` of the form `DRF/{row_id}`. New imports: `date` from datetime, `ProvenanceTag` from the model.
- `scripts/build_docx_template.py` extended: Section 6 ("Departmental Results Framework Linkages") with a 3-column table (Core Responsibility | Departmental Result | Fiscal Year) and the for/data/endfor in separate rows pattern. Gated by a paragraph-level `{%p if is_dnd_position %}` so the whole section is suppressed for non-DND positions. Build script self-asserts that `drf_linkages` + `is_dnd_position` are declared template variables.
- `templates/docx/work_description_template.docx` rebuilt (37,636 bytes): 14 declared template variables (was 12); added `drf_linkages` and `is_dnd_position`. End-to-end render smoke test against `_build_context` output produces 37,426 bytes — non-empty, valid DOCX.

## Task Commits

Each task was committed atomically:

1. **Task 1:** `app/api/drf_integration.py` — `7114951` (feat)
2. **Task 2:** `app/main.py` (router + wizard route) — `98291d7` (feat)
3. **Task 3:** `app/services/export_service.py` + `scripts/build_docx_template.py` + DOCX template — `8433edb` (feat)

## Files Created/Modified

- `app/api/drf_integration.py` (new, 151 lines) — Router with `_map_value_error` helper, `Jinja2Templates` (shared with siblings), and 3 routes mirroring the HTMX dual-path pattern from `app/api/jes_scoring.py`. Imports: `get_drf_candidates`, `confirm_drf_linkages` (service), `load_work_description` + `save_work_description` (store), `get_connection` (db).
- `app/main.py` (modified) — Added `from app.api import drf_integration` (alphabetical after `export`), `app.include_router(drf_integration.router)` after the `export` mount, and the `wizard_drf` route at `/wizard/drf` (49 new lines). Placeholder HTML rendered via `jinja2.TemplateNotFound` catch.
- `app/services/export_service.py` (modified) — Two new constructs: (1) `drf_linkages` list construction in `_build_context` filtered to `is_dnd_position` + `confirmed` linkages; (2) DRF ProvenanceTag emission in `build_version_manifest` after the JES factor loop. Added `date` to datetime import and `ProvenanceTag` to model import.
- `scripts/build_docx_template.py` (modified) — Module docstring updated with the new Section 6 description and two new Jinja variables. Section 6 added after the manifest table; uses the for/data/endfor in separate rows pattern with 3 columns. Build script's self-verify step extended with a hard assertion on `drf_linkages` + `is_dnd_position` presence.
- `templates/docx/work_description_template.docx` (modified, binary) — Regenerated by `scripts/build_docx_template.py`. 37,636 bytes, 14 declared variables (added `drf_linkages`, `is_dnd_position`).

## Decisions Made

- **Same `_map_value_error` idiom as `jes_scoring`.** Both routers share the same IDOR-handling contract: 404 for "not found" + 422 for other errors. Keeps HTTP error semantics uniform across phase routers; no new mapping policy introduced for DRF.
- **flag-dnd is an annotation, not a stage transition.** Loading the WD, toggling `is_dnd_position`, saving — and never advancing `wd.stage`. This matches the plan's note about the DRF service layer not advancing stage (PLAN 09-02 deviation narrative), and keeps the wizard step ordering flexible.
- **Docxtpl paragraph-level `{%p if is_dnd_position %}` gate.** Whole Section 6 is inside a single `{%p if %}/{%p endif %}` pair around all the new content (heading + intro + table). For non-DND positions, the section is fully suppressed — no empty table shell, no leftover heading. The same pattern is already used inside Section 3 for the advisor marker.
- **DRF ProvenanceTag emission in `build_version_manifest`.** Synthesized at emission time (not stored on the WD) because the WD's drf_linkages list already carries `provenance_source_id` and `core_responsibility` / `departmental_result` fields. The manifest entry shape (`source_type`, `source_id`, `source_version`, `retrieved_date`) is what Section 5 of the template renders, so DRF linkages now flow into the same provenance table as NOC/JES/CA/OG/QUAL sources.
- **Build script asserts the new contract.** `required_new_vars = {"drf_linkages", "is_dnd_position"}` and the script raises `AssertionError` if either is missing from `get_undeclared_template_variables()`. This catches a forgotten tag at rebuild time — without it, the missing variable would only surface at first export (post-deploy).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Importing `ProvenanceTag` and `date` for the DRF manifest emission**

- **Found during:** Task 3 Part B — adding the DRF ProvenanceTag emission to `build_version_manifest`.
- **Issue:** The plan's <action> block specified `ProvenanceTag(...)` and `date.today()` calls in the new code, but the existing `export_service.py` imports only `WorkDescription` from the model and `datetime` from stdlib. The `ProvenanceTag` import and `date` import were not explicit in the plan's "imports to add" bullet.
- **Fix:** Added `ProvenanceTag` to the model import and `date` to the datetime import. Verified with the plan's verification command (build_version_manifest + WorkDescription with is_dnd_position=True + drf_linkages) — passes.
- **Files modified:** `app/services/export_service.py`
- **Verification:** `python -c "from app.services.export_service import build_version_manifest; print('OK')"` exits 0; verification command in plan passes (`ALL OK`).
- **Committed in:** `8433edb` (Task 3 commit)

No other deviations — plan executed as written for Tasks 1, 2, and the DOCX template section. All acceptance criteria (grep counts, route presence, DOCX variable presence, verification command exit) pass.

## Issues Encountered

None.

## Known Stubs

The HTMX partial templates referenced by the new router routes — `templates/partials/drf_candidates.html`, `templates/partials/drf_confirmed.html`, `templates/partials/drf_flag.html`, and `templates/wizard/step_drf.html` — are **intentionally deferred to plan 09-04**. The router code references them, but the routes also have a non-HTMX JSON path that is fully functional. If an HTMX client hits these routes before 09-04 ships the partials, `Jinja2Templates.TemplateResponse` will raise `TemplateNotFound` and the FastAPI default 500 error will surface.

This is by design: the plan's <action> explicitly says "Falls back to a placeholder if the template has not yet shipped" and "The full template will be added in Plan 09-04." The non-HTMX path (curl, Postman, `requests`) returns JSON correctly, so the API contract is testable today.

Tracking: the 09-04 plan owns these partials. No fix needed in 09-03.

## Threat Model Compliance

- **T-09-07 (IDOR on GET /api/drf-links/{wd_id}):** Mitigated by `get_drf_candidates` raising `ValueError("not found")` for missing WD; `_map_value_error` maps to 404. No stack trace leak.
- **T-09-08 (Tampering on POST confirm row_ids):** Mitigated by the route's `token.isdigit()` filter and the service's SELECT-by-PK (unknown ids silently skipped with `logger.warning`). Both layers of defense — the route never sends garbage to the service.
- **T-09-09 (Tampering on POST flag-dnd is_dnd):** Accepted in the plan (boolean toggle on a single-user local app, no auth layer in v1 scope). The route uses FastAPI's `bool = Form(...)` which deserializes `"true"`/`"false"` strings — no injection vector.
- **T-09-10 (DOCX template path):** N/A — this plan doesn't change `_resolve_template_path()`; the same hardcoded relative path from `__file__` is used.

## User Setup Required

None — no external service configuration required. The DRF integration is purely additive: existing flows (NOC mapping, OG classification, JD generation, JES scoring, export) are unchanged.

## Next Phase Readiness

- **09-04 (DRF wizard step + partials + CSS)** is unblocked:
  - `templates/wizard/step_drf.html` — extends the wizard at `/wizard/drf` (placeholder currently rendered)
  - `templates/partials/drf_candidates.html`, `drf_confirmed.html`, `drf_flag.html` — the HTMX swap targets the router expects
  - CSS for the DRF section (likely a Layer 13 in `app/static/css/main.css`)
  - 9 still-skipping test stubs in `tests/test_drf.py` (TestGetDRFLinks, TestConfirmDRFLinks, TestDRFExport, TestDRFWizardStep) flip to active with the templates shipped

Full suite: 186 passed, 9 skipped (was 186 + 9, unchanged), 0 regressions. The 9 skipped tests are the DRF surface that 09-02/09-03/09-04 collectively owns.

---
*Phase: 09-dnd-drf-integration*
*Completed: 2026-06-03*

## Self-Check: PASSED

- `.planning/phases/09-dnd-drf-integration/09-03-SUMMARY.md` exists
- `7114951` (Task 1 — drf_integration router) commit exists
- `98291d7` (Task 2 — main.py mount + /wizard/drf route) commit exists
- `8433edb` (Task 3 — export_service + DOCX template rebuild) commit exists
- `app/api/drf_integration.py` exports `router` with exactly 3 routes (GET, POST confirm, POST flag-dnd)
- `_map_value_error` used 5 times in drf_integration.py (helper definition + 2 route uses)
- `HX-Request` header check present 6 times in drf_integration.py (3 routes × 2 contexts: get+flag-dnd both check; confirm has same pattern; covers all dual-path points)
- `app/main.py` imports + mounts drf_integration (lines 24, 113)
- `/wizard/drf` route defined (lines 305-306)
- `app/services/export_service.py` has 7 references to `drf_linkages` and 2 references to `is_dnd_position`
- `app/services/export_service.py` has `ProvenanceTag` and `date` imports for the new manifest emission
- `scripts/build_docx_template.py` has 5 references to `drf_linkages`
- `templates/docx/work_description_template.docx` is 37,636 bytes (regenerated)
- `python -c "from app.api.drf_integration import router"` exits 0
- `python -c "from app.main import app"` exits 0 (with assert_ollama_ready patched)
- `python -c "from app.services.export_service import _build_context, build_version_manifest"` exits 0
- `python scripts/build_docx_template.py` exits 0 with `DRF contract: ['drf_linkages', 'is_dnd_position'] declared ✓`
- Plan verification command (DRF context + DRF manifest entry) returns `ALL OK`
- Full suite: 186 passed, 9 skipped, 0 regressions
