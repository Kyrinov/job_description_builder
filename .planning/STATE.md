---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 8
status: executing
last_updated: "2026-06-02T21:20:00.000Z"
progress:
  total_phases: 9
  completed_phases: 6
  total_plans: 31
  completed_plans: 27
  percent: 84
---

# Project State

**Status:** Executing Phase 8
**Current phase:** 8
**Last updated:** 2026-06-02
**Next action:** `/gsd-execute-phase 07`

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
| 8 | Export | Plan 08-01 complete (3/4 plans executed; scaffold + template + contract tests committed) |
| 9 | DND DRF Integration | Not started |

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

### Decisions Locked

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

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases total | 9 |
| Phases complete | 5 |
| Requirements mapped | 21/21 |
| Tests passing | 114 |

---

## Session Continuity

**Next action:** `/gsd-execute-phase 8` continues with Plan 08-02 (export_service.py)

**Context for next session:**

- Phase 5 complete (2026-06-02): OG classification pipeline live; 81 OG rows in og_definitions; /api/og/classify and /api/og/confirm with stage gates and verbatim guardrail; AS/EC alert + directive citation working; full Phase 5 UI in templates/partials/og_*.html and templates/wizard/step_og.html; CSS layer 8 with .asec-alert warning tokens; 114 tests pass; 1 skip (deferred Phase 6 gate test)
- WorkDescription now carries `confirmed_og`, `confirmed_level` (e.g. "EC-04"), and `og_recommendation: OGRecommendation`; `stage="og_classified"` after Phase 5 confirm flow
- og_definitions table is the source of truth for CLASS-01 verbatim citations — all 33 OG groups + 48 subgroups loaded from TBS-OCHRO-OG.txt (81 unique og_codes)
- CLASS-03 disambiguation: `_fetch_directive_citation` runs FTS on policy_fts for `directive_on_classification`; returns verbatim chunk as authority citation
- CLASS-02 gate: both /api/og/classify and /api/og/confirm return 422 if `stage != "noc_mapped"`; Phase 6 JD generation can rely on `stage="og_classified"` as its prerequisite
- All architecture decisions in "Decisions Locked" above are non-negotiable
- **Phase 8 Plan 08-01 complete (2026-06-02):** Export scaffold + template artifact + 6 contract tests
  - `tests/conftest.py`: `export_db` fixture + `make_exported_wd(db_path, *, complete=True)` helper (incomplete=True produces the D-01 sentinel factor)
  - `tests/test_export.py`: 6 skipping tests for `generate_export`, `validate_export_readiness`, `build_version_manifest`
  - `scripts/build_docx_template.py`: reproducible generator; loads generated template via docxtpl and self-verifies
  - `templates/docx/work_description_template.docx`: 37KB committed artifact; 12 Jinja2 variables (position_title, position_number, og_level, supervisor_title, supervisor_position_number, review_date, organizational_context_text, organizational_context_source, duties, jes_scores, jes_total_points, manifest); TBS WD format (D-04)
  - docxtpl table-row loops use for/data/endfor in separate rows (patch_xml regex is greedy)
- 149 tests pass; 7 skip (including 6 new export contract tests)

**Planned Phase:** 08 (Export) — Plan 08-02 next (export_service.py implements the contract)
