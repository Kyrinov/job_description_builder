---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: Phase 4 — NL→NOC Mapping
status: ready_to_execute
last_updated: "2026-06-01T00:00:00.000Z"
progress:
  total_phases: 9
  completed_phases: 3
  total_plans: 15
  completed_plans: 11
  percent: 73
---

# Project State

**Status:** Phase 4 planned — ready to execute (4 plans, 4 waves)
**Current phase:** Phase 4 — NL→NOC Mapping
**Last updated:** 2026-06-01

**Pre-phase-4 prerequisite:** Re-run `scripts/ingest_noc.py` — app.db was rebuilt during Phase 3 and NOC tables (noc_elements, noc_units, noc_fts) are empty.

---

## Phase Status

| # | Phase | Status |
|---|-------|--------|
| 1 | Project Foundation | Complete (3/3 plans verified) |
| 2 | NOC Data Pipeline | Complete (4/4 plans verified) |
| 3 | CA + JES Data Pipeline | Complete (4/4 plans verified) |
| 4 | NL→NOC Mapping | Ready to execute (4 plans) |
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
| Phases complete | 3 |
| Requirements mapped | 21/21 |
| Plans created | 11 (Phase 1: 3 complete, Phase 2: 4 complete, Phase 3: 4 ready) |
| **Plans executed** | **15 (Phase 3: 4/4 complete)** |

---

## Session Continuity

**Next action:** `/gsd-plan-phase 4`

**Context for next session:**

- Phase 3 complete: 578 ca_clauses (33 OGs), 105 jes_factors (16 OGs), 190 policy_chunks, 75 tests green
- app.db NOC tables empty — re-run `python scripts/ingest_noc.py` before Phase 4 real-data run
- Phase 4 goal: `POST /map-to-noc` with plain-language work description → ranked NOC candidates via FTS5 → embedding rerank → LLM justification (3-stage pipeline)
- Phase 4 depends on Phase 2 (NOC data) and Phase 3 (policy chunks for AS-vs-EC context)
- Requirements: MAP-01 (NOC shortlist), MAP-02 (embedding rerank + LLM justification)
- All architecture decisions in "Decisions Locked" above are non-negotiable
