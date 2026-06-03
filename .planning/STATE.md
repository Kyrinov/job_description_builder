---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 09
current_plan: 4
status: executing
last_updated: "2026-06-03T12:48:12.754Z"
progress:
  total_phases: 10
  completed_phases: 8
  total_plans: 38
  completed_plans: 35
  percent: 92
---

# Project State

**Status:** Ready to execute
**Current phase:** 09
**Current Plan:** 4
**Total Plans in Phase:** 4
**Last updated:** 2026-06-03
**Next action:** Run `/gsd-execute-phase 9` to execute Phase 9 plans

---

## Phase Status

| # | Phase | Status |
|---|-------|--------|
| 1 | Project Foundation | Complete (3/3 plans verified) |
| 2 | NOC Data Pipeline | Complete (4/4 plans verified) |
| 3 | CA + JES Data Pipeline | Complete (4/4 plans verified) |
| 4 | NL→NOC Mapping | Complete (4/4 plans verified, UAT passed 2026-06-02) |
| 5 | OG Classification | Complete (4/4 plans executed; 114 tests pass; 1 skipped — Phase 6 gate) |
| 6 | JD Generation | Not started |
| 7 | JES Scoring | Ready to execute (4/4 plans verified) |
| 8 | Export | Plans 08-01 + 08-02 + 08-03 + 08-04 Tasks 1+2 complete (router + templates + CTA + CSS Layer 11); 08-04 Task 3 (human-verify) next |
| 9 | DND DRF Integration | In progress (Plans 09-01 + 09-02 complete: model + DDL + ingest script + keyword matching service; 09-03 next) |

---

## Project Reference

See: `.planning/PROJECT.md`

**Core value:** An HR advisor can describe work in plain language and receive a legally defensible, fully traceable job description — grounded in NOC, collective agreement, and TBS classification policy — in minutes instead of hours.

**Architecture non-negotiables (do not change without a phase transition):**

- ProvenanceTag on every domain object — set at write time, rendered at export
- WorkDescription Pydantic model finalized in Phase 1 before any service code
- One configured local generation model call per JES factor (no array-collapse), instructor retry, Pydantic validation
- LLM selects duty text from indexed records — never generates free-form duty text
- CA restriction clauses pre-extracted at ingest, not loaded from full CA at validation time
- Startup assertion: embedding model name in index metadata must match configured model

---

## Accumulated Context

### Decisions Made

| Decision | Rationale |
|----------|-----------|
| FastAPI over Flask | LLM streaming via `StreamingResponse`; Flask WSGI blocks during Ollama calls |
| HTMX 2.x + Alpine.js 3.x | No build step; ~29KB combined; server-rendered wizard pattern |
| DuckDB 1.5.3 (pinned) | aarch64 wheels broken in 1.4.x |
| nomic-embed-text via Ollama | Already resident; eliminates 500MB sentence-transformers cold-start problem |
| instructor over raw Ollama format | Mandatory retry wrapper for local model structured output edge cases |
| Fresh codebase (not fork) | 25 phases of prototype debt; clean slate |
| SQLite + sqlite-vec (not DuckDB) for app state | App state and vector search co-located; DuckDB for parquet pipeline transforms only |
| DashScope qwen3.7-max for Stage 3 LLM | Cloud inference via dashscope-intl.aliyuncs.com; local gemma4:31b too slow (6 min/request) |
| docxtpl table-row loops use for/data/endfor in separate rows | docxtpl patch_xml regex is greedy — matches the LAST {%tr %} tag in a row, so co-locating for+endfor with data eats the for tag. Separate marker rows above/below the data row is the standard convention. |
| Phase 8 template is a committed binary artifact + reproducible build script | .docx loads deterministically at runtime; build script self-verifies via DocxTemplate.get_undeclared_template_variables() on every run |
| Phase 9 WorkDescription extended with is_dnd_position + drf_linkages (additive-optional, schema_version stays at 1) | Backward compatibility with existing rows in work_descriptions.data (JSON) — no migration of legacy data needed |
| drf_rows has UNIQUE(fiscal_year, core_responsibility, departmental_result) + search_text denormalized at ingest | Avoid FTS5 dependency for Phase 9 — keyword overlap against precomputed search_text is sufficient for ~5k rows |
| test_drf.py uses _drf_app_bootstrapped module global | Each per-phase test module owns its own rebootstrap flag — prevents module-level global races when pytest runs them in one process |

- --phase
- --phase
- --phase

### Active Blockers

- ~~NOC 2021 unit group profiles not yet acquired~~ — RESOLVED
- ~~TBS OCHRO OG definitions not yet collected~~ — RESOLVED: `data/TBS-OCHRO-OG.txt` (33 OG definitions, 3259 lines, scraped from Canada.ca 2026-06-02)

### Todos

- ~~Collect TBS OCHRO OG definitions with inclusions/exclusions (Phase 5 hard blocker)~~ — RESOLVED
- Collect TBS Qualification Standards per OG (v2 blocker, QUAL-01)
- Verify WeasyPrint Pango/Cairo system libs present on Jane (Jetson AGX Orin)
- Plan end-to-end Ollama unified memory test after Phase 7 completes
- Fix `noc_fts` DDL in `app/db.py` (UNINDEXED + content='' bug — deferred from Phase 4)
- Address Starlette `TemplateResponse` deprecation warning (deferred from Phase 4)

### Roadmap Evolution

- Phase 08.1 inserted after Phase 8: "Advisor override and per-factor retry for incomplete JES scoring" (URGENT) — closed the gap that left a blocked export with no recovery path; 3 plans (service / API / UI) added 2026-06-02

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases total | 9 |
| Phases complete | 5 |
| Requirements mapped | 21/21 |
| Tests passing | 186 |

---
| Phase 9 P1 | 15min | 3 tasks | 4 files |
| Phase 9 P2 | 15min | 1 task (TDD) | 2 files |
| Phase 09 P02 | 00:12:00 | 2 tasks | 3 files |

## Session Continuity

**Next action:** `/gsd-execute-phase 9` continues with Plan 09-03 (DRF API router + export_service extension + DOCX template rebuild)

**Context for next session:**

- Phase 5 complete (2026-06-02): OG classification pipeline live; 81 OG rows in og_definitions; /api/og/classify and /api/og/confirm with stage gates and verbatim guardrail; AS/EC alert + directive citation working; full Phase 5 UI in templates/partials/og_*.html and templates/wizard/step_og.html; CSS layer 8 with .asec-alert warning tokens; 114 tests pass; 1 skip (deferred Phase 6 gate test)
- WorkDescription now carries `confirmed_og`, `confirmed_level` (e.g. "EC-04"), `og_recommendation: OGRecommendation`, **and** `is_dnd_position` + `drf_linkages` (Phase 9, additive-optional); `stage="og_classified"` after Phase 5 confirm flow
- og_definitions table is the source of truth for CLASS-01 verbatim citations — all 33 OG groups + 48 subgroups loaded from TBS-OCHRO-OG.txt (81 unique og_codes)
- CLASS-03 disambiguation: `_fetch_directive_citation` runs FTS on policy_fts for `directive_on_classification`; returns verbatim chunk as authority citation
- CLASS-02 gate: both /api/og/classify and /api/og/confirm return 422 if `stage != "noc_mapped"`; Phase 6 JD generation can rely on `stage="og_classified"` as its prerequisite
- All architecture decisions in "Decisions Locked" above are non-negotiable
- **Phase 9 Plan 09-01 complete (2026-06-03):** DND DRF foundation
  - `app/models/work_description.py`: `is_dnd_position: bool = False` + `drf_linkages: list[dict] = Field(default_factory=list)` appended after `exported_at` (additive-optional, no schema_version bump)
  - `app/db.py`: `DRF_SCHEMA_DDL` constant + `drf_rows` (id, fiscal_year, core_responsibility, departmental_result, search_text, source_file, ingested_at) with UNIQUE(fiscal_year, core_responsibility, departmental_result) and `idx_drf_rows_cr` index; `create_schema()` registers it after `NOC_MAPPING_SCHEMA_DDL`
  - `tests/conftest.py`: `drf_db` fixture mirrors the `export_db` pattern
  - `tests/test_drf.py`: 9 skipping test stubs across 5 test classes (TestGetDRFLinks, TestConfirmDRFLinks, TestDRFMatchingService, TestDRFExport, TestDRFWizardStep) — rebootstrap uses `_drf_app_bootstrapped` global to avoid collision
  - 180 tests pass + 10 skipped (was 1 pre-existing skip; 9 new DRF stubs), 0 regressions
- **Phase 9 Plan 09-02 complete (2026-06-03):** DND DRF service layer + ingest script (TDD RED + GREEN)
  - `scripts/ingest_drf.py` (Task 1, pre-committed as `d5c4fea`): reads `data/departmental_results_framework/dnd_drf_dataset.csv` (utf-8-sig with cp1252 fallback for stray 0x92 bytes); INSERT OR IGNORE into `drf_rows`; idempotent; CLI args `db_path` (positional, default `$DB_PATH` or `app.db`) and `--csv` (default relative to project root). End-to-end run: 42 unique rows from 132 CSV rows.
  - `app/services/drf_service.py` (Task 2, GREEN commit `213735d`): 241 lines, public async API `get_drf_candidates(wd_id, db_path)` + `confirm_drf_linkages(wd_id, row_ids, db_path)`. Keyword matching via `re.findall(r'[a-z]+', text)` + 32-word `STOPWORDS` frozenset. All DB calls use `asyncio.to_thread` (10 sites); default-arg closure capture in per-row loops. `provenance_source_id` format `DRF/{row_id}`.
  - `tests/test_drf.py` (RED commit `0d0b5c1`): replaced `TestDRFMatchingService` stub (wrong function name) with `TestGetDRFCandidates` (4 tests) + `TestConfirmDRFLinkages` (2 tests). New helpers `_make_dnd_wd` + `_seed_drf_rows`. All 6 active tests pass.
  - 186 tests pass + 9 skipped (was 180 + 10; +6 active tests, -1 stub), 0 regressions. `requirements.mark-complete DRF-01` succeeded.
- **Phase 8 Plan 08-01 complete (2026-06-02):** Export scaffold + template artifact + 6 contract tests
  - `tests/conftest.py`: `export_db` fixture + `make_exported_wd(db_path, *, complete=True)` helper (incomplete=True produces the D-01 sentinel factor)
  - `tests/test_export.py`: 6 skipping tests for `generate_export`, `validate_export_readiness`, `build_version_manifest`
  - `scripts/build_docx_template.py`: reproducible generator; loads generated template via docxtpl and self-verifies
  - `templates/docx/work_description_template.docx`: 37KB committed artifact; 12 Jinja2 variables (position_title, position_number, og_level, supervisor_title, supervisor_position_number, review_date, organizational_context_text, organizational_context_source, duties, jes_scores, jes_total_points, manifest); TBS WD format (D-04)
  - docxtpl table-row loops use for/data/endfor in separate rows (patch_xml regex is greedy)
- 149 tests pass; 7 skip (including 6 new export contract tests)

**Planned Phase:** 09 (DND DRF Integration) — Plans 09-01 + 09-02 complete; 09-03 (DRF API router + export_service extension + DOCX template rebuild) next

---

## Update 2026-06-02T21:50:00Z — Plan 08-04 Tasks 1+2 complete

- `templates/wizard/step_export.html` shipped (D-09): hybrid `href` + `hx-get` anchor so non-HTMX clicks still download the DOCX directly while HTMX clients get the success partial swapped into `#export-result`. Hidden `wd_id` input, static version-manifest preview note, `hx-target`/`hx-swap`/`hx-indicator` matched to `export-spinner`, and the D-08 PDF-501 copy as a secondary note.
- `templates/partials/export_result.html` shipped: HTMX success partial with `id="export-result"`, `role="status"`, `.export-result` class. Renders the SHA-256 `{{ export_hash }}` from `app/services/export_service.py` inside `<code>` plus a re-download anchor (T-08-15 XSS mitigated by Jinja2 autoescape — `export_hash` is hex, `filename` is server-set constant).
- `templates/partials/jes_scores.html` edited: activated "Continue to Export" CTA at lines 27-28 — removed `aria-disabled="true"`, removed `title="Available in Phase 8"`, promoted `button--secondary` to `button--primary`. Closes the Phase 7→8 wizard handoff that 07-04 left disabled.
- `app/static/css/main.css` extended: CSS Layer 11 (Export) appended at the end of the file with `.export-result`, `.export-hash`, `.export-errors`, `.export-errors li`, `.export-error-card`, `.export-error-card--blocking`. All rules use existing CSS custom properties with literal hex fallbacks (matches Layer 10's style). Header layer-index comment extended to register Layer 11.
- Task 1 commit `0d04df9` (feat); Task 2 commit `3be5c1e` (feat). 159 tests pass + 1 pre-existing skip, 0 regressions.
- Task 3 (human-verify checkpoint) pending — orchestrator spawns the verify step next.

---

## Update 2026-06-02T21:26:39Z — Plan 08-02 complete

- `app/services/export_service.py` shipped: `validate_export_readiness` (D-01/D-02), `build_version_manifest` (D-07), `async generate_export` (D-03/D-05/D-06)
- Pre-export gate treats `s.points is None` as blocking — fixes the Phase 7 silent-zero bug at `jes_service.py:76-77` (LLM returned a degree that did not map to a value in the point_values dict)
- DOCX render in `asyncio.to_thread` + `BytesIO` (no temp files); stage advance to `exported` only after confirmed non-empty file bytes; SHA-256 export_hash
- D-06 advisor marker derived from `d.advisor_modified or d.provenance.source_type == "ADVISOR"` — captures both ways advisor content can land on a DraftDuty
- 6/6 contract tests in `tests/test_export.py` pass; full suite 155 passed + 1 pre-existing skip, no regressions
- Auto-fix (Rule 1): pre-existing missing `from tests.conftest import make_exported_wd` in `tests/test_export.py` — masked in 08-01 by the `ImportError -> pytest.skip` boilerplate, surfaced in 08-02
- Plan 08-03 (export.py router + main.py mount + /wizard/export route) is next
- 155 tests pass; 1 skip

---

## Update 2026-06-02T21:39:54Z — Plan 08-03 complete

- `app/api/export.py` shipped (77 lines): `GET /export/{wd_id}/docx` (HTMX dual-path: binary Response for non-HTMX, TemplateResponse for `HX-Request`) and `GET /export/{wd_id}/pdf` (D-08 501 short-circuit, exact message "PDF export is not yet available — download DOCX and convert locally."). ValueError → 404 (not found) / 422 (blocked) mapping mirrors `app/api/jes_scoring.py` line-for-line.
- `app/main.py` modified: `from app.api import export`, `app.include_router(export.router)` after the `jes_scoring` mount, and `wizard_export` route with `jinja2.TemplateNotFound` fallback (D-09 placeholder until 08-04 ships `templates/wizard/step_export.html`).
- `tests/test_export.py` extended: 4 router-level tests appended (`test_pdf_route_returns_501`, `test_docx_route_404_for_unknown_wd`, `test_docx_route_422_when_blocked`, `test_docx_route_streams_file`) using the per-test rebootstrap pattern from `test_jes_scoring.py` (`_set_env` + `_clear_app_modules` + `from app.main import app` + `TestClient(app)`). The rebootstrap is required because the autouse `_bootstrap_app_modules` fixture is a one-shot and would otherwise bind `settings.db_path` to the FIRST service test's export_db.
- All 10 tests in `tests/test_export.py` pass (6 service + 4 router); full suite 159 passed + 1 pre-existing skip, 0 regressions.
- T-08-12 mitigated by design: Content-Disposition filename is the server-set constant `work_description.docx` from the service result, never derived from user input.
- T-08-14 mitigated by the D-08 501 short-circuit: no WeasyPrint render path reachable from the route, eliminating ARM64 risk.
- Plan 08-04 (wizard step_export.html + partials/export_result.html + CSS layer 11 + human verify) is next.
