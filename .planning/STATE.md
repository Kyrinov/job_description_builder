---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 06
status: executing
last_updated: "2026-06-02T00:00:00.000Z"
progress:
  total_phases: 9
  completed_phases: 5
  total_plans: 27
  completed_plans: 18
  percent: 78
---

# Project State

**Status:** Phase 06 planned (4 plans) — ready to execute
**Current phase:** 06
**Last updated:** 2026-06-02
**Next action:** `/gsd-execute-phase 06`

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
| 7 | JES Scoring | Not started |
| 8 | Export | Not started |
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

**Next action:** `/gsd-discuss-phase 6` (or `/gsd-plan-phase 6` to skip discussion)

**Context for next session:**

- Phase 5 complete (2026-06-02): OG classification pipeline live; 81 OG rows in og_definitions; /api/og/classify and /api/og/confirm with stage gates and verbatim guardrail; AS/EC alert + directive citation working; full Phase 5 UI in templates/partials/og_*.html and templates/wizard/step_og.html; CSS layer 8 with .asec-alert warning tokens; 114 tests pass; 1 skip (deferred Phase 6 gate test)
- WorkDescription now carries `confirmed_og`, `confirmed_level` (e.g. "EC-04"), and `og_recommendation: OGRecommendation`; `stage="og_classified"` after Phase 5 confirm flow
- og_definitions table is the source of truth for CLASS-01 verbatim citations — all 33 OG groups + 48 subgroups loaded from TBS-OCHRO-OG.txt (81 unique og_codes)
- CLASS-03 disambiguation: `_fetch_directive_citation` runs FTS on policy_fts for `directive_on_classification`; returns verbatim chunk as authority citation
- CLASS-02 gate: both /api/og/classify and /api/og/confirm return 422 if `stage != "noc_mapped"`; Phase 6 JD generation can rely on `stage="og_classified"` as its prerequisite
- All architecture decisions in "Decisions Locked" above are non-negotiable
- Human verify for Phase 5 UI (Plan 05-04) is pending — start uvicorn and run the wizard to confirm AS/EC alert renders, OG cards display verbatim TBS citations, level select + confirm flow reaches og_confirmed.html
