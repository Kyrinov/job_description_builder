---
phase: 08-export
plan: 01
subsystem: testing
tags: [docxtpl, export, contract-tests, pytest-fixtures, jinja2]

# Dependency graph
requires:
  - phase: 07-jes-scoring
    provides: WorkDescription.jes_scores + jes_total_points fields + JESFactorScore with level/points/provenance
  - phase: 06-jd-generation
    provides: WorkDescription.draft_duties + advisor_additions + DraftDuty with provenance
  - phase: 05-og-classification
    provides: WorkDescription.og_recommendation + OGRecommendation with cited_articles
provides:
  - export_db pytest fixture and make_exported_wd helper (complete/incomplete modes)
  - 6 skipping contract tests for validator + manifest + DOCX export
  - docxtpl TBS Work Description template (work_description_template.docx) with 12 Jinja2 variables
  - Reproducible scripts/build_docx_template.py generator with self-verification
affects:
  - 08-02 (export_service.py implements the contract; uses the template)
  - 08-03 (export.py router mounts the endpoints the tests reference)
  - 08-04 (wizard step + HTMX partial invoke the service built against these contracts)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Defer-import + try/except ImportError -> pytest.skip convention (mirrors test_jes_scoring.py)"
    - "Temp SQLite + create_schema fixture pattern (mirrors jes_db/jd_db/og_db fixtures)"
    - "docxtpl table-row loop with for/data/endfor in separate rows (the patch_xml regex is greedy)"
    - "Reproducible binary-artifact generation via Python script committed to scripts/"

key-files:
  created:
    - tests/test_export.py
    - scripts/build_docx_template.py
    - templates/docx/work_description_template.docx
  modified:
    - tests/conftest.py

key-decisions:
  - "Template uses 12 stable Jinja2 variables as the contract for the 08-02 service (position_title, position_number, og_level, supervisor_title, supervisor_position_number, review_date, organizational_context_text, organizational_context_source, duties, jes_scores, jes_total_points, manifest)"
  - "make_exported_wd uses a complete/incomplete bool switch — complete=True builds a full JES sheet; complete=False sets the second factor to the D-01 failed-factor sentinel (level=-1, points=None) to exercise the export-blocking path"
  - "For docxtpl table-row loops, the for tag and endfor tag each live in their OWN row (above and below the data row) — co-locating them with the data row would be eaten by docxtpl's greedy patch_xml regex"
  - "Duties loop is paragraph-level ({%p for %}) with the advisor marker as a conditional paragraph; JES and manifest loops are table-row ({%tr for %})"
  - "The .docx is committed as a binary artifact (not regenerated at app startup) so the export service can load it deterministically; build_docx_template.py is run when the template structure changes"

patterns-established:
  - "Wave 0 interface-first foundation: fixture + helper + contract tests + template artifact established before any service code in the phase (mirrors the pattern from Phases 4-7)"
  - "tests/ defer-import + pytest.skip keeps the suite green when downstream modules don't exist yet — new tests start in skip state, flip to passing as the service lands in 08-02"

requirements-completed: [EXP-01]

# Metrics
duration: 21min
completed: 2026-06-02
---

# Phase 8 Plan 01: Export Scaffold Summary

**Export test scaffold (export_db fixture, 6 contract tests) and reproducible docxtpl TBS Work Description template with 12 Jinja2 contract variables**

## Performance

- **Duration:** 21 min
- **Started:** 2026-06-02T20:58:34Z
- **Completed:** 2026-06-02T21:20:00Z
- **Tasks:** 3
- **Files modified:** 4 (3 created, 1 modified)

## Accomplishments

- `export_db` pytest fixture and `make_exported_wd(db_path, *, complete=True)` helper
  added to `tests/conftest.py`, mirroring the `jes_db` fixture pattern. The
  helper builds a complete `WorkDescription` in `stage="jes_scored"` with
  full `ProvenanceTag` coverage on NOC match, OG recommendation,
  organizational context, draft duties, advisor additions, and JES scores.
  `complete=False` mode sets the second JES factor to the D-01 failed-factor
  sentinel (level=-1, points=None) so tests can exercise the export-blocking
  path.
- 6 skipping contract tests in `tests/test_export.py` define the export
  service contract: `generate_export` returns non-empty `.docx` bytes with a
  64-char hex SHA-256, advances stage to "exported" on success, blocks with a
  named `ValueError` on incomplete JES scoring, leaves stage untouched on a
  blocked attempt; `validate_export_readiness` returns a list naming the
  failed factor for an incomplete WD and `[]` for a complete one;
  `build_version_manifest` returns a deduplicated list of
  `(source_type, source_id, source_version)` dicts covering NOC, JES,
  TBS_OG_DEF, and ADVISOR sources. All 6 skip cleanly because
  `app.services.export_service` does not yet exist.
- `scripts/build_docx_template.py` (with self-verification) generates
  `templates/docx/work_description_template.docx` — a 37KB committed binary
  artifact with the TBS Work Description format (D-04): position
  identification table, organizational context, duties loop with advisor
  marker (D-06), JES scoring loop, and version manifest loop. The script
  loads the generated template with `DocxTemplate` and prints the
  undeclared-variables list on every run to catch malformed tags at build
  time, not at first export.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add export_db fixture and make_exported_wd helper to conftest.py** - `15c2a70` (test)
2. **Task 2: Write Phase 8 contract tests in test_export.py** - `c33f7bf` (test)
3. **Task 3: Build the docxtpl TBS WD template via a reproducible script** - `8078910` (feat)

## Files Created/Modified

- `tests/conftest.py` — Added `export_db(tmp_path)` fixture and
  `make_exported_wd(db_path, *, complete=True)` module-level helper
- `tests/test_export.py` — 6 skipping contract tests + module docstring
- `scripts/build_docx_template.py` — Reproducible generator using python-docx
  with self-verification via docxtpl
- `templates/docx/work_description_template.docx` — Rendered DOCX artifact
  with 12 Jinja2 contract variables

## Decisions Made

- **For/data/endfor in separate rows for table-row loops.** docxtpl's
  `patch_xml` regex
  (`<w:tr[ >](?:(?!<w:tr[ >]).)*({%tr xxx %})...</w:tr>`) is a tempered greedy
  match — it matches the LAST `{%tr %}` tag in a row. Co-locating
  `{%tr for %}` and `{%tr endfor %}` in the same row as the data cells caused
  the for tag to be consumed by the regex and the data to be lost. The
  fix — used in both the JES table and the manifest table — is to put the
  for tag in its own row above the data row, and the endfor tag in its own
  row below. The data row is then duplicated once per item by the loop, and
  the marker rows are removed. Verified by rendering a sample context: the
  rendered DOCX has the right row count (header + N factor rows; header + N
  source rows).
- **Duties loop uses paragraph-level `{%p for %}` not table-row.** A duty is
  a paragraph (text + source citation + optional advisor marker), not a
  table row, so `{%p for duty in duties %}` is the right primitive. The
  advisor marker is a separate `{%p if %}` block so the marker text only
  appears when the duty is advisor-added.
- **Template is a committed binary artifact, not a runtime-generated one.**
  The 37KB .docx is committed alongside the build script. The export
  service in 08-02 will load the committed file directly. Re-run the build
  script only when the template structure changes (new sections, new
  variables).
- **Contract test names match the proposed service API exactly.** Test
  names reference `generate_export`, `validate_export_readiness`, and
  `build_version_manifest` (all to be implemented in Plan 08-02). Test
  bodies wrap the imports in `try/except ImportError -> pytest.skip("export_service
  not yet implemented")` so the suite stays green as the service lands.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing docxtpl + python-docx + pytest-asyncio packages**
- **Found during:** Pre-task environment check (Task 3 verify step)
- **Issue:** `docxtpl==0.18.0` and `python-docx==1.1.2` were listed in
  `requirements.txt` but not yet installed in the active venv. Importing
  them failed. `pytest-asyncio` had also been upgraded to 1.3.0
  (incompatible with the `@pytest.mark.asyncio` pattern).
- **Fix:** Ran
  `pip install docxtpl==0.18.0 python-docx==1.1.2 pytest-asyncio==0.25.3`
  to match the pinned versions in `requirements.txt`. pytest was
  auto-downgraded from 9.0.2 to 8.4.2 to satisfy pytest-asyncio 0.25.3's
  constraint.
- **Files modified:** (site-packages only — not in repo)
- **Verification:** `python -c "import docxtpl"` and
  `python -c "import docx"` succeed.
- **Committed in:** n/a (environment install, not a code change)

**2. [Rule 2 - Missing Critical] Self-verification step in build_docx_template.py**
- **Found during:** Task 3 verify command
- **Issue:** The plan's verify command (`python scripts/build_docx_template.py
  && python -c "from docxtpl import DocxTemplate; ..."`) required a
  separate one-liner to confirm the template's Jinja2 variables. If a future
  edit breaks the template (e.g., a typo in a `{%tr %}` tag), the build
  script would still write a malformed .docx silently.
- **Fix:** Added a self-verification block at the end of
  `build_docx_template.py` that loads the generated template with
  `DocxTemplate` and prints the undeclared-variables list. Catches
  malformed template tags at build time, not at first export.
- **Files modified:** `scripts/build_docx_template.py`
- **Verification:** Run `python scripts/build_docx_template.py` — exits 0
  and prints `Template variables (12): [...]`.
- **Committed in:** `8078910` (part of Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical)
**Impact on plan:** Both auto-fixes necessary for the build environment to
work and for the template to self-validate. No scope creep — no new tasks
added, no new files created beyond what the plan specified.

## Issues Encountered

- **docxtpl `patch_xml` regex is greedy.** Initial implementation put the
  `{%tr for %}` tag in the first cell of the data row and the
  `{%tr endfor %}` tag in the last cell (the convention shown in the
  docxtpl README). This caused the regex to match the LAST `{%tr` tag in
  the row (the endfor), eating the for tag and losing the data. Diagnosed
  by inspecting the patched XML directly: `<w:tbl>...{% endfor %}</w:tbl>`.
  Resolved by using the for/data/endfor in separate rows pattern. This is
  the standard docxtpl convention for templates created programmatically
  with python-docx (rather than hand-edited in MS Word, where the
  paragraph/run structure differs subtly).
- **Advisor `{%p if %}` and `{%p endif %}` in the same paragraph failed
  parsing.** docxtpl's docs explicitly state "Do not use `{%p` twice in
  the same paragraph". Initial draft had `{%p if ... %}[marker]{%p endif %}`
  in one paragraph. Resolved by putting each tag in its own paragraph
  with the marker text in a third paragraph between them.

## Next Phase Readiness

Plan 08-02 (export_service.py) can now be written against this scaffold:
- 12 stable Jinja2 variable names in the template are the context-dict
  contract.
- 6 contract tests in `test_export.py` define what `generate_export`,
  `validate_export_readiness`, and `build_version_manifest` must do.
- `make_exported_wd(complete=False)` exercises the D-01/D-02 export
  blocking path with a deterministic sentinel.
- Pre-export validator must return a `list[str]` of error messages (test
  asserts `any("Communication" in e for e in errors)`).
- `generate_export` must return a dict with `file_bytes` (non-empty
  bytes), `filename` (ending in `.docx`), and `export_hash` (64-char hex
  SHA-256).
- Stage advancement to `"exported"` only after confirmed non-empty bytes
  per D-03; blocked export must NOT advance stage.
- The `test_pdf_route_returns_501` is intentionally NOT in this plan — it
  belongs in 08-03 (router) where the actual `/export/{wd_id}/pdf`
  endpoint will be mounted.

No blockers for 08-02.

## Self-Check: PASSED

All claimed files and commits verified:
- `.planning/phases/08-export/08-01-SUMMARY.md` — created
- `tests/conftest.py` — modified (export_db fixture + make_exported_wd helper)
- `tests/test_export.py` — created (6 contract tests)
- `scripts/build_docx_template.py` — created (reproducible generator)
- `templates/docx/work_description_template.docx` — created (37KB binary)
- `15c2a70` — Task 1 commit (test: export_db fixture + helper)
- `c33f7bf` — Task 2 commit (test: 6 contract tests)
- `8078910` — Task 3 commit (feat: build script + template)

---
*Phase: 08-export*
*Completed: 2026-06-02*
