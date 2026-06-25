---
phase: 29-structured-export-enhanced-poster
plan: 02
subsystem: api
tags: [export, json, csv, docxtpl, manager-track, seven-elements]

# Dependency graph
requires:
  - phase: 27-responsibilities-narrative-completeness-audit
    provides: build_seven_elements(wd) helper + DraftDuty Pydantic model
  - phase: 28-manager-track-ux
    provides: wd_type field on WorkDescription + manager-bypass pattern for export gates
  - phase: 26-org-context-conversational-step
    provides: wd.org_context typed root field
provides:
  - POST /api/wd/{id}/export/json route — SEXP-01, 7-element analytics JSON
  - POST /api/wd/{id}/export/csv route — SEXP-02, UTF-8-BOM CSV (Excel-safe)
  - _build_json_export / _build_csv_export private helpers
  - _MANAGER_PLACEHOLDER constant for manager-track classification gaps
  - Enhanced poster with "About the Organization" section — POST-01
  - org_context key in _build_poster_context()
  - Regenerated poster_template.docx with {{ org_context }} Jinja2 variable
affects: [plan-29-03-frontend-buttons, plan-30-workforce-analytics]

# Tech tracking
tech-stack:
  added: []
  patterns: [manager-track-export-bypass, utf-8-bom-csv-for-excel, advisor-placeholder-for-missing-classification]

key-files:
  created: []
  modified:
    - v2/backend/app/api/export.py
    - v2/backend/app/services/export_service.py
    - v2/backend/scripts/build_poster_template.py
    - v2/backend/app/templates/poster_template.docx

key-decisions:
  - "JSON/CSV routes deliberately OMIT require_og_confirmed(wd) — manager-track WDs (wd_type='manager') deliberately never have confirmed_og; bypassing the 409 gate lets their analytics exports succeed while classification metadata is replaced with [ADVISOR TO COMPLETE] so the gap is explicit"
  - "[ADVISOR TO COMPLETE] string literal (not None) for manager-track og_level / jes_total_points / og_name — analytics consumers see the gap explicitly instead of inferring 'no classification' from null"
  - "CSV uses encode('utf-8-sig') on the StringIO output to prepend the \xef\xbb\xbf BOM byte sequence — Excel auto-detects UTF-8 on open; no formula-injection sanitization (internal HR tool, T-29-02-03 disposition)"
  - "DraftDuty attribute access (.text, .provenance_noc_code) — NOT dict subscript — consistent with Phase 27 build_seven_elements return shape"

patterns-established:
  - "Pattern: Structured export routes use build_seven_elements(wd) as the single source of truth — JSON wraps the 7 keys + element_status dict + classification metadata + provenance + export_date; CSV flattens to one row per duty with scalar context columns"
  - "Pattern: Manager-track export preserves filename from wd.record.title (slugified) — same as existing docx/poster/pdf routes; no special manager naming convention"

requirements-completed: [SEXP-01, SEXP-02, POST-01]

# Metrics
duration: ~5min
completed: 2026-06-25
---

# Phase 29 Plan 02: Structured Export + Enhanced Poster Wave 1 GREEN

**JSON + UTF-8-BOM CSV export routes with manager-track bypass + poster "About the Organization" section — 184/184 backend tests GREEN, all 5 Wave 0 RED stubs turned GREEN**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-25T12:22:17Z
- **Completed:** 2026-06-25T12:27:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- **JSON export route (SEXP-01)** — POST /api/wd/{id}/export/json returns 200 with all 7 Part 2 element keys (organizational_context, client_service_results, key_activities, skills, effort, responsibility, working_conditions), per-element status dict, complete_count/total, classification metadata block, deduplicated provenance list, wd_type, export_date. Manager-track WDs (wd_type='manager') bypass the require_og_confirmed gate and return og_level="[ADVISOR TO COMPLETE]" so analytics consumers see the gap explicitly.
- **CSV export route (SEXP-02)** — POST /api/wd/{id}/export/csv returns 200 with UTF-8-BOM bytes (\xef\xbb\xbf prefix so Excel auto-detects UTF-8), one row per key activity (duty) plus a single sentinel row when no duties exist. 12 columns: duty_text, duty_noc_code, organizational_context, client_service_results, skills_status, effort_status, responsibility, working_conditions_status, og_level, jes_total_points, complete_count, total.
- **Enhanced poster (POST-01)** — "About the Organization / À propos de l'organisation" section added between Branch and Key Duties; _build_poster_context returns org_context key with `[To be provided / À fournir]` fallback when blank; poster_template.docx regenerated (37,004 bytes) with `{{ org_context }}` Jinja2 variable.
- **All 5 Wave 0 RED stubs GREEN**: test_export_json_returns_all_seven_keys, test_export_json_metadata_and_provenance, test_export_csv_utf8_bom_one_row_per_duty, test_export_json_manager_no_409, test_poster_org_context_section.
- **Test count: 37 passed in test_export.py (32 pre-existing + 5 Wave 0 stubs); 184 passed in full backend suite (147 in other test files + 37 in test_export.py). 0 regressions.**

## Task Commits

Each task was committed atomically:

1. **Task 1: Add JSON and CSV route handlers to export.py** - `e344c2b` (feat)
2. **Task 2: Extend _build_poster_context and update build_poster_template.py; regenerate poster_template.docx** - `d89d30e` (feat)
3. **Chore: Sync regenerated poster_template.docx to match fresh build** - `7bdc194` (chore)

## Files Created/Modified

- `v2/backend/app/api/export.py` — Added `import csv`, `import io`, `import json`, `from datetime import date`; added `_MANAGER_PLACEHOLDER` constant; imported `build_seven_elements` and `_build_v2_manifest` from export_service; added `_build_json_export()` and `_build_csv_export()` private helpers; added `export_wd_json` and `export_wd_csv` POST route handlers (both deliberately omit require_og_confirmed per SEXP-04 SC-4 manager-bypass pattern).
- `v2/backend/app/services/export_service.py` — Added `"org_context": (wd.org_context or "").strip() or "[To be provided / À fournir]"` key to the _build_poster_context() return dict. No other changes (build_seven_elements, _build_v2_manifest, _og_code_from, _og_level_str, _slugify_title all unchanged).
- `v2/backend/scripts/build_poster_template.py` — Inserted "About the Organization / À propos de l'organisation" section after Branch block (org_head bold paragraph + `{{ org_context }}` template body paragraph); added `"org_context"` to the required set in the self-verify block.
- `v2/backend/app/templates/poster_template.docx` — Regenerated binary (37,004 bytes); contains the new `{{ org_context }}` Jinja2 variable. Verified via `python v2/backend/scripts/build_poster_template.py` self-verify: "Poster template variables (9): ... org_context ... ✓" and "Poster template OK".

## Decisions Made

None - followed plan as specified. The plan's interfaces section documented existing helper signatures (build_seven_elements, _build_v2_manifest, _og_code_from, _og_level_str, _slugify_title), the existing `_load_wd` pattern, the manager-bypass contract, the BOM encoding requirement, and the DraftDuty attribute access idiom. Every code block in the plan was inserted as written.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Committed a third "chore" commit to capture the freshly regenerated poster_template.docx binary**
- **Found during:** Post-Task 2 verification (running build_poster_template.py a second time)
- **Issue:** python-docx-generated docx files contain non-deterministic metadata (creation/modification timestamps, ZIP entry ordering) so a fresh build produces a binary that differs from the originally committed one even though the semantic content (Jinja2 vars, headings, body text) is identical. The Task 2 commit captured the first-regen binary; running the build script again (e.g., as part of any future CI verification or local sanity check) produces a fresh binary that differs at the byte level from HEAD, leaving a dirty git status even though nothing functionally changed.
- **Fix:** Ran the build script once more after Task 2 commit, captured the freshly regenerated binary, committed it as a separate `chore(29-02)` commit so HEAD's binary matches what a fresh build produces. Future runs of `python v2/backend/scripts/build_poster_template.py` from repo root leave git status clean (modulo the same non-determinism that python-docx itself introduces, which is a pre-existing condition).
- **Files modified:** `v2/backend/app/templates/poster_template.docx`
- **Verification:** `git diff --stat` shows 0 insertions / 0 deletions (size unchanged at 37004 bytes); semantic content verified by self-verify script's `Poster contract: ... 'org_context' ... ✓` line.
- **Committed in:** `7bdc194` (chore commit, separate from Task 2's `d89d30e`)

---

**Total deviations:** 1 auto-fixed (Rule 3 — committing the non-determinism-corrected binary)

**Impact on plan:** Chore commit is hygiene-only; no behavioral or test-visible change. Task 1 (`e344c2b`) and Task 2 (`d89d30e`) both delivered exactly per plan.

## Issues Encountered

None — plan execution proceeded smoothly. All 4 JSON/CSV tests passed after Task 1; the final poster test passed after Task 2; full backend suite (184 tests) remained GREEN throughout.

## User Setup Required

None - no external service configuration required. All changes are backend-only; Plan 29-03 (frontend) wires the Export JSON / Export CSV buttons in ReviewState and does not require manual setup.

## Next Phase Readiness

- **Plan 29-03 (Wave 2 frontend)** is unblocked — gates the 2 frontend RED stubs (`Export JSON` button in ReviewState, `Export CSV` button in ReviewState). Implementation pattern from Phase 28: existing export buttons in `.export-row` already POST to `/api/wd/{id}/export/docx|poster|pdf`; the 2 new buttons follow the same `fetchAsBlob` pattern with no completeness-soft-gate interaction (Phase 27 invariant: export buttons stay enabled at any complete_count value).
- **Requirements SEXP-01/02 + POST-01 closed** in REQUIREMENTS.md traceability. SEXP-03 (frontend buttons) and SEXP-04 (manager-track bypass — backend half verified by `test_export_json_manager_no_409`, frontend half is Plan 29-03) remain pending.
- **`build_seven_elements(wd)` is the contract for both routes** — any future element addition (e.g., a hypothetical 8th element) requires updating build_seven_elements first, then the JSON/CSV helpers inherit the new key automatically (the CSV `fieldnames` list is the only manual sync point).
- **Manager-track bypass pattern is now established** as a 2-route precedent (JSON + CSV) — if Phase 30 adds more analytics endpoints, they should follow the same pattern (no require_og_confirmed + `[ADVISOR TO COMPLETE]` placeholder) rather than re-deriving the manager contract.

---

*Phase: 29-structured-export-enhanced-poster*
*Completed: 2026-06-25*

## Self-Check: PASSED

- All 4 modified files exist at expected paths
- All 3 task commits present in git log (`e344c2b`, `d89d30e`, `7bdc194`)
- test_export.py: 37 passed, 0 failed (32 pre-existing + 5 Wave 0 GREEN)
- Full backend suite: 184 passed, 0 failed
- `python v2/backend/scripts/build_poster_template.py` exits 0 with "Poster template OK"
