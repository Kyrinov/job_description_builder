---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 09
current_plan: 4
status: milestone_complete
last_updated: "2026-06-03T14:22:52.000Z"
progress:
  total_phases: 10
  completed_phases: 10
  total_plans: 38
  completed_plans: 37
  percent: 100
---

# Project State

**Status:** Milestone complete
**Current phase:** 9
**Current Plan:** Not started
**Total Plans in Phase:** 4
**Last updated:** 2026-06-03
**Next action:** Run `/gsd-complete-milestone` to start the v1.0 readiness review

---

## Phase Status

| # | Phase | Status |
|---|-------|--------|
| 1 | Project Foundation | Complete (3/3 plans verified) |
| 2 | NOC Data Pipeline | Complete (4/4 plans verified) |
| 3 | CA + JES Data Pipeline | Complete (4/4 plans verified) |
| 4 | NL→NOC Mapping | Complete (4/4 plans verified, UAT passed 2026-06-02) |
| 5 | OG Classification | Complete (4/4 plans executed; 114 tests pass; 1 skipped — Phase 6 gate) |
| 6 | JD Generation | Complete (4/4 plans verified) |
| 7 | JES Scoring | Complete (4/4 plans verified) |
| 8 | Export | Complete (4/4 plans verified) |
| 8.1 | JES Advisor Override & Per-Factor Retry | Complete (3/3 plans verified) |
| 9 | DND DRF Integration | Complete (4/4 plans verified — 09-01 + 09-02 + 09-03 + 09-04 with revised inline-panel design) |

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
- Phase 9 router convention: drf_integration reuses jes_scoring's _map_value_error (404 for not found, 422 for other ValueErrors) for uniform IDOR handling across phase routers
- Phase 9 export pattern: DRF ProvenanceTag is synthesized at build_version_manifest emission time (not stored on WD) — drf_linkages list already carries provenance_source_id and core/departmental_result fields
- Phase 9 docxtpl pattern: paragraph-level {%p if is_dnd_position %} gate suppresses the entire DRF section (heading + intro + table) for non-DND positions — no empty table shell
- Phase 9 inline-panel pattern (revised Plan 09-04): DRF UI is a panel on /wizard/export, not a separate /wizard/drf step. The prototype is DND-only so is_dnd_position is no longer a UI affordance — it defaults to True on every new WD (set in /api/noc/map) and there is no toggle in any template
- Phase 9 DOCX gate moved from is_dnd_position to drf_linkages|length > 0 — a DND WD may be exported before the advisor confirms any linkages; an empty Section 6 is noise
- Phase 9 drf_service top-5 cap: _score_drf_rows returns candidates[:5] — 42 unique DRF rows is too many for a single inline panel; top-5 by score (ties broken by id) keeps the wizard step scannable

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
| Phases total | 10 (incl. 8.1) |
| Phases complete | 9 (incl. 8.1) |
| Requirements mapped | 21/21 |
| Tests passing | 188 |

| Phase | Duration | Tasks | Files |
|-------|----------|-------|-------|
| Phase 9 P1 | 15min | 3 tasks | 4 files |
| Phase 9 P2 | 15min | 1 task (TDD) | 2 files |
| Phase 09 P02 | 00:12:00 | 2 tasks | 3 files |
| Phase 09-dnd-drf-integration P03 | 7min | 3 tasks | 5 files |
| Phase 09-dnd-drf-integration P04 | 22min | 7 commits (2 reverts + 5 forward) | 9 files |

---

## Session Continuity

**Next action:** `/gsd-complete-milestone` to start the v1.0 readiness review (Phase 9 is now the last unverified phase; all 4 plans complete)

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

---

## Update 2026-06-03T13:02:00Z — Plan 09-03 complete

- `app/api/drf_integration.py` shipped (151 lines): 3 routes — `GET /api/drf-links/{wd_id}` (candidates), `POST /api/drf-links/{wd_id}/confirm` (store linkages), `POST /api/drf-links/{wd_id}/flag-dnd` (toggle is_dnd_position). HTMX dual-path on get + confirm + flag-dnd returns partials; non-HTMX returns JSON. `_map_value_error` (404/422) mirrors `app/api/jes_scoring.py` for uniform IDOR handling. `row_ids` form field parsed via `isdigit()` filter — non-integers never reach the service.
- `app/main.py` extended: `from app.api import drf_integration` (alphabetical after export), `app.include_router(drf_integration.router)` after the export mount, and a new `wizard_drf` route at `/wizard/drf` that loads `is_dnd_position` + `drf_linkages` from the WD. `jinja2.TemplateNotFound` catch renders a placeholder until `templates/wizard/step_drf.html` ships in plan 09-04.
- `app/services/export_service.py` extended: `_build_context()` returns `drf_linkages` (filtered to confirmed linkages on DND positions) and `is_dnd_position`. `build_version_manifest()` emits a `ProvenanceTag` per confirmed DRF linkage with `source_type='DRF'`, `source_version='DND DRF Dataset 2021-2022'`. New imports: `date` (datetime), `ProvenanceTag` (model).
- `scripts/build_docx_template.py` extended: Section 6 ("Departmental Results Framework Linkages") with a 3-column table and the for/data/endfor in separate rows pattern. Gated by a paragraph-level `{%p if is_dnd_position %}` so the whole section disappears for non-DND positions. Build script self-asserts `drf_linkages` + `is_dnd_position` are declared template variables.
- `templates/docx/work_description_template.docx` regenerated (37,636 bytes): 14 declared template variables (was 12). Render smoke test against `_build_context` output produces 37,426 bytes — non-empty, valid DOCX.
- 3 task commits: `7114951` (router), `98291d7` (main.py mount + wizard route), `8433edb` (export_service + DOCX template).
- Auto-fix (Rule 2): added `from datetime import date` and `from app.models.work_description import ProvenanceTag` imports in `export_service.py` — the plan's action block referenced both symbols but the existing imports only covered `datetime` and `WorkDescription`.
- Full suite: 186 passed + 9 skipped (was 186 + 9, unchanged), 0 regressions. The 9 skips are the DRF surface that 09-02/09-03/09-04 collectively owns.
- Plan 09-04 (HTMX wizard templates + CSS Layer 13 + step_export DRF CTA + human verify) is next.

---

## Update 2026-06-03T14:22:52Z — Plan 09-04 complete (revised inline-panel design)

The user redirected the UI design mid-checkpoint: the prototype is DND-only, so `is_dnd_position` should default to `True` on every WD with no UI affordance, and the DRF candidate selection should live inline on `/wizard/export` rather than on a separate `/wizard/drf` route. Plan 09-04 was rewritten to ship this revised design.

**Reverts first (clean history, no `git reset --hard`):**
- `bd404a3` — revert `8ffa967` (drop `templates/wizard/step_drf.html` + 3 DRF partials + old CSS Layer 13)
- `e5075f2` — revert `c130b6a` (drop the DRF notice block in `templates/wizard/step_export.html` + the `is_dnd_position`/`confirmed_drf_count` context additions to `wizard_export`)

**Forward commits (5):**
- `ccd38f8` — `feat(09-04): default is_dnd_position=True on WD creation` — sets `is_dnd_position=True` in `/api/noc/map` (the only production WD creation site). Model field default stays `False` so existing model tests pass; per-WD default behavior is set at the API layer.
- `641f9b9` — `feat(09-04): add inline DRF linkage panel to step_export.html + CSS Layer 14` — added the inline panel with empty/confirmed states, HTMX-wired to the existing `GET /api/drf-links/{wd_id}` + `POST /confirm` endpoints; new `templates/partials/drf_candidates.html` (checkbox form) + `templates/partials/drf_confirmed.html` (summary table); CSS Layer 14 (renumbered from 13) with `.drf-inline-panel`, `.drf-linkages-table`, `.drf-candidate-list`, `.drf-confirmed-banner`, `.drf-score-badge`, `.drf-fiscal-year`. Also removed the now-dead `/wizard/drf` route from `app/main.py` and capped `drf_service._score_drf_rows` to top-5 candidates.
- `ec7a7d5` — `feat(09-04): remove POST /flag-dnd route` — the field is no longer a UI affordance; the route is dead code. Router is now a strict 2-endpoint contract.
- `3c89c02` — `feat(09-04): DOCX Section 6 — gate on drf_linkages|length > 0` — moved the gate from `is_dnd_position` to the linkage count. A DND WD can still be exported before confirming any linkages, and an empty Section 6 in the DOCX is noise. `build_docx_template.py` self-verify assertion now only requires `drf_linkages`.
- `437f160` — `test(09-04): add inline DRF panel rendering tests` — added 2 active tests in `TestDRFInlinePanel` (uses FastAPI TestClient to GET `/wizard/export` and assert the panel HTML in both empty and confirmed states). The 4 still-skipping test classes (TestGetDRFLinks, TestConfirmDRFLinks, TestDRFExport, TestDRFWizardStep) get a brief header comment explaining why they remain skipping in the revised design.

**Backend from 09-01/02/03 stays untouched:** `drf_service.py`, `drf_integration.py` router (now 2 routes after flag-dnd removal), DOCX Section 6.

**Full suite: 188 passed, 9 skipped** (was 186 + 9; +2 active tests in `TestDRFInlinePanel`, 0 regressions). Phase 9 is now complete: all 4 plans verified. `/gsd-complete-milestone` is the next action to start the v1.0 readiness review.
