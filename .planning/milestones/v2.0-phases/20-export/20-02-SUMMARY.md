---
phase: 20-export
plan: 02
subsystem: export
tags: [docxtpl, weasyprint, fastapi-router, asyncio-to-thread, export-pipeline, v2.0-flat-model]

# Dependency graph
requires:
  - phase: 20-01
    provides: "7 RED test stubs defining EXP-01/02/03 + API-08/09 contract; WeasyPrint 69.0 install + smoke; wd_template.docx + poster_template.docx committed binaries"
provides:
  - export_service.py with generate_wd_docx, generate_poster_docx, _build_wd_context, _build_poster_context, _build_v2_manifest, _get_amendments, _probe_weasyprint, _resolve_template_path
  - api/export.py router with three POST endpoints (docx, poster, pdf) — all wired and live
  - export module included in api/__init__.py — backend now serves POST /api/wd/{id}/export/{docx,poster,pdf}
  - All 7 RED stubs from 20-01 unskipped and GREEN; full suite 80 passed, 0 failed
affects: [phase-20-plan-03, frontend-conversation-export-buttons, frontend-app-exportAs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "docxtpl render via asyncio.to_thread (CPU-bound sync work kept off the FastAPI event loop)"
    - "v2.0 flat-field manifest builder: walks DraftDuty.provenance_noc_code + confirms OG/JES/QUAL — no v1.0 ProvenanceTag sub-object"
    - "WeasyPrint runtime probe (write_pdf) cached module-side — pay probe cost once per process"
    - "og_level string zero-padded: f'{og_code}-{int(og_level):02d}' for TBS format compliance"
    - "amendments appendix re-queries audit_log with ORDER BY id DESC + section dedup"

key-files:
  created:
    - v2/backend/app/services/export_service.py
    - v2/backend/app/api/export.py
  modified:
    - v2/backend/app/api/__init__.py
    - v2/backend/tests/test_export.py

key-decisions:
  - "Composed organizational_context_text from record.branch/record.reports/record.title/record.summary with the same lowercased-summary pattern as the v1.0 buildOverview() logic — preserves citation stability vs the React document.jsx"
  - "Asymmetric readiness gates: DOCX requires jes_total_points (422 if missing), poster does not — matches EXP-01 vs EXP-02 contract"
  - "Single-line import in api/__init__.py (matching the plan's literal grep) — multi-line was reverted after spotting the acceptance-criterion grep checks the single-line form"
  - "Test helper in test_export.py was missing the required 'source' field on the DraftDuty fixture — patched in commit 8fb2bc5 (Rule 1 auto-fix); pre-existing test bug from Plan 01 that surfaced only when the tests ran"

patterns-established:
  - "v2.0 export context shape: {position_title, position_number, og_level (zero-padded), supervisor_title, supervisor_position_number, review_date, organizational_context_text, organizational_context_source, duties (loop), jes_scores (loop), jes_total_points, manifest (loop), amendments (loop), education_text, experience_text}"
  - "v2.0 poster context shape: {position_title, og_level (zero-padded), og_name, branch, education, experience, duties (top 5), bilingual_title_fr (empty placeholder)}"
  - "PDF endpoint renders server-side HTML from WD fields — never accepts raw HTML from the client (T-20-02-03)"

requirements-completed: [EXP-01, EXP-02, EXP-03, API-08, API-09]

# Metrics
duration: 6min
completed: 2026-06-09
---

# Phase 20 Plan 02: Export Pipeline Summary

**Backend export pipeline: DOCX + poster render via docxtpl with v2.0 flat-field context builders, WeasyPrint 501 ARM64 gate for PDF, and a 3-endpoint FastAPI router that brings the 7 RED stubs from Plan 20-01 to GREEN.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-06-09T18:24:19Z
- **Completed:** 2026-06-09T18:30:22Z
- **Tasks:** 2
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- Implemented `v2/backend/app/services/export_service.py` (433 lines) — full v2.0 export pipeline: `generate_wd_docx` + `generate_poster_docx` async entry points, `_build_wd_context` + `_build_poster_context` populating docxtpl variables from v2.0 flat fields (`provenance_noc_code`, `confirmed_og`, `wd.record`), `_build_v2_manifest` deduplicating NOC duties + JES/OG/QUAL sources, `_get_amendments` querying `audit_log` (ORDER BY id DESC + section dedup), `_render_docx` wrapping the synchronous `DocxTemplate.render` in `asyncio.to_thread`, and `_probe_weasyprint` running an actual `write_pdf()` call with module-level caching
- Implemented `v2/backend/app/api/export.py` (143 lines) — three POST endpoints with the expected gate chain: `export_wd_docx` (404 → 409 from `require_og_confirmed` → 422 if `jes_total_points is None` → 200 with DOCX bytes), `export_poster` (404 → 409 → 200 with poster bytes), `export_pdf` (404 → 501 if WeasyPrint import fails or `_probe_weasyprint()` returns False → 200 with PDF bytes from server-generated HTML)
- Wired the export module into `v2/backend/app/api/__init__.py` — `from . import … export` on line 16, `api_router.include_router(export.router)` on line 25; matches the literal grep acceptance criteria
- Removed all 7 `@pytest.mark.skip` decorators from `test_export.py` and added the missing `source: "noc"` field to the test helper's DraftDuty fixture (pre-existing Plan 01 bug, surfaced when tests ran)
- Verified end-to-end: 7/7 export tests pass, 80/80 backend suite passes, zero regressions; both DOCX renders produce 37,020–37,543 bytes (well above the 5 kB "manifest rendered" assertion in the test)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create export_service.py** - `f77f442` (feat)
2. **Task 2: Create export.py router + wire into api/__init__.py + make tests GREEN** - `8fb2bc5` (feat)

## Files Created/Modified

- `v2/backend/app/services/export_service.py` (433 lines, created) — async render entry points, flat-field context builders, version manifest, amendment query, WeasyPrint probe, template path resolution
- `v2/backend/app/api/export.py` (143 lines, created) — FastAPI router with three POST endpoints; matches `v2/backend/app/api/jes_scoring.py` pattern
- `v2/backend/app/api/__init__.py` (1-line edit) — added `export` to the `from . import …` line and `api_router.include_router(export.router)` after amendments
- `v2/backend/tests/test_export.py` (1-line edit + 7 skip removals) — removed 7 `@pytest.mark.skip` decorators; added `source: "noc"` to the DraftDuty fixture in `_create_wd_with_jes_scores` (Rule 1 auto-fix)

## Decisions Made

- **organizational_context_text composition:** Used the same `buildOverview()` pattern as the v1.0 export (and `document.jsx`): `"Located within {branch}, and reporting to the {supervisor}, the {title} {summary}."` with the first character of `summary` lowercased so it slots into a sentence. Falls back gracefully when branch or supervisor is missing. This keeps the WD DOCX readable in the same way as the live SPA preview.
- **Asymmetric JES gate:** DOCX export returns 422 when `jes_total_points is None` (EXP-01 requires it), but the poster endpoint does NOT (the poster template does not use JES scores — EXP-02 is bilingual, OG/level, branch, top 5 duties only). The plan's action block matches this asymmetry.
- **og_level zero-padding:** Used `f"{og_code}-{int(og_level_int):02d}"` everywhere — `EC-05` not `EC-5` — to match the TBS format and the docxtpl template's expected output.
- **WeasyPrint import inside the PDF handler:** Per the v1.0 pattern + RESEARCH.md Pitfall 5, the import is inside `export_pdf` (not at module level) so a missing system lib doesn't crash the whole app at startup. The runtime probe runs an actual `write_pdf()` call (not just `import weasyprint`) and caches the result module-side.
- **Single-line import in `__init__.py`:** Initially reformatted the import to a multi-line PEP-8 form, but reverted to single-line to match the plan's literal grep `from . import.*export`. Functional equivalence, but a one-line grep criterion beats a stylistic preference.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test Bug] Added missing `source: "noc"` to DraftDuty test fixture**
- **Found during:** Task 2 (unskipping tests)
- **Issue:** `_create_wd_with_jes_scores` in `v2/backend/tests/test_export.py` sent a duty dict with `id`, `text`, `provenance_noc_code`, `provenance_hash`, `advisor` — but the `DraftDuty` model (v2.0) requires the `source: Literal["noc", "advisor"]` field. With the skips removed, the WD PATCH raised `pydantic_core._pydantic_core.ValidationError: 1 validation error for DraftDuty — source: Field required`
- **Fix:** Added `"source": "noc"` to the duty dict in the test helper (1-line addition)
- **Files modified:** `v2/backend/tests/test_export.py`
- **Verification:** `python -m pytest tests/test_export.py --tb=short` → 7 passed; `python -m pytest tests/ -q --tb=no` → 80 passed, 0 failed
- **Committed in:** `8fb2bc5` (Task 2 commit)

**2. [Self-correction - Style] Reverted multi-line import in `__init__.py` to single-line**
- **Found during:** Task 2 (acceptance-criteria grep check)
- **Issue:** I initially reformatted the `from . import …` line to PEP-8 multi-line (one module per indented line). This is functionally equivalent but breaks the plan's literal grep `grep "from . import.*export" v2/backend/app/api/__init__.py` (which expects the single-line form, where `. import` and `export` appear on the same line)
- **Fix:** Reverted to the single-line form from the plan's action block
- **Files modified:** `v2/backend/app/api/__init__.py`
- **Verification:** `grep "from . import.*export"` → 1 match (returns the full line)
- **Committed in:** `8fb2bc5` (Task 2 commit, same hash as #1)

---

**Total deviations:** 2 auto-fixed (1 test bug, 1 self-correction to satisfy the literal grep criterion)
**Impact on plan:** Both fixes essential — one makes the tests pass, the other satisfies the acceptance criterion. No scope creep. The `source: "noc"` addition is a real bug fix in the Plan 01 test fixture; the multi-line → single-line import is a cosmetic alignment with the plan.

## Issues Encountered

- **`.docx` binaries show as modified in `git status` but with 0 insertions / 0 deletions.** This is a zip-metadata change (timestamps, member ordering) from how Python's zipfile module writes DOCX, not a content change. Not staged or committed — these files are out of scope for Plan 20-02 (they're committed in Plan 20-01). Documented here so the diff noise is acknowledged but not propagated into the Phase 20 commit history.

## Test Count Delta

| Phase | Status | Count |
|-------|--------|-------|
| Before Plan 20-02 | passed | 73 |
| Before Plan 20-02 | skipped | 7 |
| Before Plan 20-02 | failed | 0 |
| **After Plan 20-02** | **passed** | **80** |
| **After Plan 20-02** | **skipped** | **0** |
| **After Plan 20-02** | **failed** | **0** |
| **Delta** | **+7 passed, −7 skipped** | net +7 |

All 7 previously-skipped export stubs are now GREEN; no regressions in the 73 pre-existing tests.

## Next Phase Readiness

- **Wave 3 (Plan 20-03) is unblocked:** The frontend `exportAs` stub in `app.jsx` and the three export buttons in `ReviewState` (conversation.jsx) can now be wired against the live `POST /api/wd/{id}/export/{docx,poster,pdf}` endpoints.
- **PDF endpoint returns 501 on this ARM64 host** — the WeasyPrint runtime probe in `_probe_weasyprint()` will determine this at first call and cache the result. If Jane's ARM64 system libs are functional, the probe returns True and the endpoint serves real PDF bytes; otherwise, the 501 fallback is exercised (the test `test_export_pdf_501_when_weasyprint_absent` mocks this path).
- **No known blockers for Wave 3** — the only thing Plan 20-03 owns is the SPA wiring.

## Self-Check: PASSED

**Created files (2/2 present):**
- v2/backend/app/services/export_service.py ✓ (433 lines)
- v2/backend/app/api/export.py ✓ (143 lines)

**Modified files (2/2 present):**
- v2/backend/app/api/__init__.py ✓ (1 line added to import, 1 line added for include_router)
- v2/backend/tests/test_export.py ✓ (7 skip decorators removed, 1 line added to fix duty fixture)

**Commits (2/2 present):**
- f77f442 — feat(20-02): export_service.py — DOCX/poster context builders + render pipeline ✓
- 8fb2bc5 — feat(20-02): export.py router wired (docx/poster/pdf) + tests GREEN ✓

**Acceptance criteria (10/10 met):**
1. `python -c "from app.services.export_service import generate_wd_docx, generate_poster_docx; print('ok')"` → ok ✓
2. `grep "async def generate_wd_docx\|async def generate_poster_docx\|def _build_wd_context\|def _build_v2_manifest\|def _get_amendments\|def _probe_weasyprint\|def _resolve_template_path"` → 7 function definitions ✓
3. `grep "wd\.stage\|draft_duties\|advisor_additions\|\.provenance\."` → 0 matches (no v1.0 field accesses) ✓
4. `grep "provenance_noc_code\|confirmed_og\|wd\.record"` → 17+ matches (v2.0 fields used throughout) ✓
5. `grep "include_router(export.router)"` → 1 match ✓
6. `grep "from . import.*export"` → 1 match ✓
7. `grep -c "pytest.mark.skip"` in test_export.py → 1 (the docstring text "Remove @pytest.mark.skip when the router is live." — the 7 actual test decorators are all removed) ✓
8. `python -m pytest tests/test_export.py -x --tb=short` → 7 passed, 0 failed ✓
9. `python -m pytest tests/ -q --tb=no` → 80 passed, 0 failed ✓
10. `grep "def export_wd_docx\|def export_poster\|def export_pdf"` → 3 lines (all three routes live) ✓

---

*Phase: 20-export*
*Completed: 2026-06-09*
