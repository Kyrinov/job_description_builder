---
phase: 08-export
plan: 02
subsystem: export
tags: [docxtpl, export, jes-validation, version-manifest, stage-advance, asyncio, sha256]

# Dependency graph
requires:
  - phase: 08-export
    provides: "export_db fixture, make_exported_wd helper, 6 contract tests in tests/test_export.py, committed docxtpl TBS Work Description template (37KB binary artifact with 12 Jinja2 contract variables)"
  - phase: 07-jes-scoring
    provides: "WorkDescription.jes_scores + jes_total_points fields + JESFactorScore with level/points/provenance; jes_service.py:76-77 silent-zero bug needing the D-02 fix"
  - phase: 06-jd-generation
    provides: "WorkDescription.draft_duties + advisor_additions + DraftDuty with provenance + advisor_modified"
  - phase: 05-og-classification
    provides: "WorkDescription.og_recommendation + OGRecommendation with cited_articles + confirmed_og/confirmed_level"
  - phase: 04-nl-noc-mapping
    provides: "WorkDescription.confirmed_noc + NOCMatch with provenance"
provides:
  - "validate_export_readiness(wd) -> list[str] pre-export gate (D-01/D-02)"
  - "build_version_manifest(wd) -> list[dict] deduplicated version manifest (D-07)"
  - "async generate_export(wd_id, db_path) -> dict DOCX render + stage advance to 'exported' (D-03/D-05/D-06)"
  - "_build_context(wd) + _resolve_template_path() docxtpl context builders"
affects:
  - 08-03 (export.py router mounts /export/{wd_id}/docx and /export/{wd_id}/pdf and consumes the service)
  - 08-04 (wizard step + HTMX partial invoke the service built here)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pre-export validation gate (D-01/D-02) raises BEFORE any rendering, so blocked exports never advance the stage"
    - "docxtpl render in asyncio.to_thread + BytesIO (no temp files on disk) keeps the FastAPI event loop unblocked"
    - "D-03 stage-advancement guard: empty file_bytes aborts before model_copy(\"stage\": \"exported\")"
    - "ProvenanceTag-driven context dict — no prose citations in code, advisor marker derived from d.advisor_modified or provenance.source_type == \"ADVISOR\""
    - "First-seen-order deduplication of (source_type, source_id, source_version) tuples via seen-set (D-07)"

key-files:
  created:
    - app/services/export_service.py
  modified:
    - tests/test_export.py

key-decisions:
  - "Used `from tests.conftest import make_exported_wd` rather than converting the helper into a fixture — preserves its factory-style signature (complete=True/False) and matches the existing per-test isolation pattern"
  - "is_advisor = bool(d.advisor_modified or d.provenance.source_type == \"ADVISOR\") — captures both ways advisor content can land on a DraftDuty: explicit flag (post-modification) and source_type semantics (provenance side)"
  - "Renamed the JES loop variable to `f` (not `s`) to match what the committed template emits — {%tr for f in jes_scores %}. Same `m` for manifest and `duty` for duties. Service keys must match the committed template exactly."
  - "D-03 stage advancement only happens after `if not file_bytes: raise ValueError(...)` — empty-bytes failure aborts BEFORE the model_copy, so the WD never has stage='exported' with no actual file"
  - "D-02: validate_export_readiness blocks on `s.points is None` even when s.level is valid — this directly fixes the Phase 7 silent-zero bug at jes_service.py:76-77 where a missing point_values dict entry would otherwise contribute 0 to the total"

patterns-established:
  - "Service module that ships 3 functions: 2 sync helpers (validator, manifest builder) and 1 async entry point (render + stage advance). Validators are pure and unit-testable; the async function only does I/O and orchestration."
  - "Reuse pattern: build_version_manifest is called from both the standalone test and from inside _build_context — single source of truth for the manifest"
  - "Pre-export gate pattern: run validate_export_readiness AFTER the stage check but BEFORE any I/O expensive work (template load, docxtpl render) — fail fast on bad data"

requirements-completed: [EXP-01]

# Metrics
duration: 7min
completed: 2026-06-02
---

# Phase 8 Plan 02: Export Service Summary

**docxtpl DOCX export with ProvenanceTag-driven citations, advisor marker, SHA-256 export_hash, and stage-advance gate fixing the Phase 7 silent-zero points=None bug**

## Performance

- **Duration:** 7 min
- **Started:** 2026-06-02T21:19:35Z
- **Completed:** 2026-06-02T21:26:39Z
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- `validate_export_readiness(wd)` returns a list of human-readable error
  messages for any JES factor with `level==-1` or `points is None` (D-01/D-02).
  Empty list for a complete WD. This is the structural fix for the Phase 7
  silent-zero bug at `jes_service.py:76-77` — even if the LLM returns a degree
  identifier that does not map to a value in the point_values dict, the export
  gate refuses to ship a DOCX with an incomplete JES total.
- `build_version_manifest(wd)` walks every ProvenanceTag on the WD (NOC match,
  OG recommendation + cited articles, organizational context, every DraftDuty
  in `draft_duties` + `advisor_additions`, every JESFactorScore) and emits one
  dict per unique `(source_type, source_id, source_version)` tuple, first-seen
  order preserved. Dedupe via seen-set (D-07).
- `async generate_export(wd_id, db_path)` mirrors `jes_service.score_jes`
  structure exactly: `conn` via `asyncio.to_thread`, stage gate (not found /
  not 'jes_scored' both raise `ValueError`), pre-export gate runs BEFORE any
  rendering, context dict built from WD scalars + a combined `duties` list
  carrying the `is_advisor` marker (D-06), render in `asyncio.to_thread`
  with `BytesIO` (no temp files), D-03 guard on empty bytes,
  `export_hash = hashlib.sha256(file_bytes).hexdigest()`, model_copy advance
  to `stage="exported"`, finally `conn.close`.
- 6 of 6 contract tests in `tests/test_export.py` now pass (no longer skip):
  `test_generate_export_returns_file_bytes`,
  `test_export_advances_stage_to_exported`,
  `test_export_blocked_on_incomplete_jes`,
  `test_export_blocked_does_not_advance_stage`,
  `test_validate_export_returns_failed_factor_names`,
  `test_version_manifest_includes_all_sources`.

## Task Commits

Each task was committed atomically:

1. **Pre-task — fix pre-existing missing import in test_export.py** - `b514467` (chore)
2. **Task 1: Implement validate_export_readiness and build_version_manifest** - `5fcad54` (feat)
3. **Task 2: Implement async generate_export with docxtpl render + stage advancement** - `c7c23cb` (feat)

## Files Created/Modified

- `app/services/export_service.py` (created) — service module exposing
  `validate_export_readiness`, `build_version_manifest`, `async generate_export`.
  Module docstring documents Public API + Architecture + Direct analog.
  Imports mirror `jes_service.py`: `asyncio`, `hashlib`, `io`, `logging`, `os`,
  `datetime`, `docxtpl.DocxTemplate`, `app.config.settings`, `app.db.get_connection`,
  `app.models.work_description.WorkDescription`,
  `app.services.wd_store.{load,save}_work_description`.
- `tests/test_export.py` (modified) — added `from tests.conftest import make_exported_wd`
  to fix pre-existing missing import that was masked in 08-01 by the test
  module's `ImportError -> pytest.skip` boilerplate.

## Decisions Made

- **is_advisor detection via OR of two flags.** A DraftDuty is advisor-marked
  if either `d.advisor_modified == True` (advisor edited it post-generation) OR
  `d.provenance.source_type == "ADVISOR"` (advisor entered it from scratch).
  Both paths must render the D-06 marker so the exported DOCX never shows
  advisor content without the visible "advisor-added / not from authoritative
  source" label.
- **Reuse build_version_manifest from inside _build_context.** Single source
  of truth: the manifest rendered into the DOCX template is the same list
  returned by the standalone helper. Test for the standalone helper and
  the rendered DOCX are the same data.
- **D-03 guard: `if not file_bytes: raise ValueError(...)` before
  model_copy.** The empty-bytes case aborts stage advancement. The model_copy
  is the only place `stage="exported"` is written; the guard guarantees no WD
  ever lands in stage='exported' without a valid file.
- **Template path resolved via `os.path.dirname(...)` three levels up.** No
  hard-coded absolute paths, no reliance on CWD. The service lives at
  `app/services/export_service.py`; the template lives at
  `templates/docx/work_description_template.docx`. The resolve walks up
  `services -> app -> project root -> templates/docx/`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pre-existing missing import in tests/test_export.py**
- **Found during:** Task 1 (running the validator + manifest tests)
- **Issue:** The 08-01 contract tests reference `make_exported_wd(...)` (a
  module-level helper in `tests/conftest.py`) without importing it. The bug
  was masked in 08-01 because the test bodies wrapped imports in
  `try/except ImportError -> pytest.skip("export_service not yet
  implemented")` — the function call was never reached. Now that the
  service lands in 08-02 and the ImportError is gone, the tests execute and
  hit `NameError: name 'make_exported_wd' is not defined`.
- **Fix:** Added `from tests.conftest import make_exported_wd` at the top of
  the test module. The `tests/` directory is a package (has `__init__.py`),
  so package-relative import works.
- **Files modified:** `tests/test_export.py`
- **Verification:** `python -m pytest tests/test_export.py -q` — 6 passed
- **Committed in:** `b514467` (separate chore commit so the per-task feat
  commits are clean)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Single-line test fix, no scope creep. The fix is a
prerequisite for the Task 1 verify command to actually run.

## Issues Encountered

- **Import style for conftest helper.** `from conftest import make_exported_wd`
  fails with `ModuleNotFoundError` because conftest.py is a special pytest
  file, not a regular importable module. The working alternative is
  `from tests.conftest import make_exported_wd` — the `tests/` package's
  `__init__.py` makes the package-relative import resolve. Diagnosed by
  `python -c "import conftest"` (fails) followed by
  `python -c "from tests.conftest import make_exported_wd"` (works).

## Next Phase Readiness

- Plan 08-03 (export.py router) can now mount:
  - `GET /export/{wd_id}/docx` — calls `await generate_export(...)`, returns
    `Response(content=result["file_bytes"], media_type="application/vnd.openxmlformats-...")`
    for non-HTMX requests and a TemplateResponse for HTMX
  - `GET /export/{wd_id}/pdf` — returns 501 with D-08 message
- Plan 08-04 (wizard step + HTMX partial) can render
  `templates/wizard/step_export.html` and `templates/partials/export_result.html`
  against the service.
- 6 contract tests pass; full suite at 155 passed + 1 pre-existing skip, no regressions.
- No new blockers.

## Self-Check: PASSED

All claimed files and commits verified:
- `app/services/export_service.py` — created, 304 lines
- `tests/test_export.py` — modified (import fix)
- `b514467` — chore: pre-existing missing import in test_export.py
- `5fcad54` — feat: validate_export_readiness + build_version_manifest
- `c7c23cb` — feat: async generate_export with docxtpl render
- All 6 contract tests pass; full suite: 155 passed, 1 pre-existing skip

---
*Phase: 08-export*
*Completed: 2026-06-02*
