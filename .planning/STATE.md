# Project State

**Status:** Phase 2 complete — Phase 3 ready to execute
**Current phase:** Phase 3 — CA + JES Data Pipeline
**Last updated:** 2026-05-29

---

## Phase Status

| # | Phase | Status |
|---|-------|--------|
| 1 | Project Foundation | Complete (3/3 plans verified) |
| 2 | NOC Data Pipeline | Complete (4/4 plans verified) |
| 3 | CA + JES Data Pipeline | Ready to execute (4 plans) |
| 4 | NL→NOC Mapping | Not started |
| 5 | OG Classification | Not started |
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

**Critical data prerequisite (must resolve before Phase 2):**
- NOC 2021 unit group profiles (parquet or JSON) — hard blocker for Phases 2–6
- TBS OCHRO OG Definitions with inclusions/exclusions — hard blocker for Phase 5

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

### Active Blockers
- ~~NOC 2021 unit group profiles not yet acquired~~ — RESOLVED: CSVs present in `data/nationa_occupational_competencies/` (516 unit groups, 44k element rows)
- TBS OCHRO OG definitions not yet collected — resolve before planning Phase 5

### Todos
- Acquire NOC 2021 data before Phase 2 kickoff
- Collect TBS OCHRO OG definitions with inclusions/exclusions
- Collect TBS Qualification Standards per OG (v2 blocker, QUAL-01)
- Verify WeasyPrint Pango/Cairo system libs present on Jane (Jetson AGX Orin)
- Plan end-to-end Ollama unified memory test after Phase 7 completes

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases total | 9 |
| Phases complete | 2 |
| Requirements mapped | 21/21 |
| Plans created | 11 (Phase 1: 3 complete, Phase 2: 4 complete, Phase 3: 4 ready) |
| **Plans executed** | **12 (Phase 3: 1/4 complete via 03-01)** |

---

## Session Continuity

**Next action:** `/gsd-execute-phase 3`

**Context for next session:**
- Phase 2 complete: 28 CA JSONs + 18 JES TXTs + 2 TBS policy docs confirmed present
- Phase 3 planned: 4 plans (Wave 0→3), LLM extraction via gemma4:31b + instructor retry
- Phase 3 plan structure: Wave 0 test stubs → Wave 1 schema DDL → Wave 2 ingest scripts → Wave 3 real-data run + human spot-check
- CA data: data/agreements/{OG}/{OG}_full.json (consistent JSON schema across all 28 OGs); multi-OG CAs: IT_CS, CT_FI, LP_LA, SP_AP
- JES data: data/Job_evaluation/*.txt (18 files; skip FB Application Guidelines file; extract first word of filename for og_code)
- New tables: ca_clauses, jes_factors, policy_chunks, policy_fts — added to app/db.py via CA_JES_SCHEMA_DDL
- All architecture decisions in "Decisions Locked" above are non-negotiable
