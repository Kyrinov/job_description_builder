# JD Builder

## What This Is

A DND-first Government of Canada job description builder for HR advisors and classification specialists. An advisor describes the work in a guided conversation; the system captures the role, scope, duties, classification and qualifications, and generates a fully traced job description grounded in NOC, collective agreements, job evaluation standards, and TBS policy.

v1.0 (MVP, HTMX wizard) shipped 2026-06-03 and is archived. v2.0 ("Guided Conversation") is a full rewrite around a conversational React single-page application with a live document preview, deterministic rule-based classification, and DOCX + PDF export with full provenance.

## Current State

- **v1.0 (archived):** FastAPI + HTMX 2.x + SQLite + sqlite-vec + Ollama. ~15,539 LOC Python, 188 tests passing. Reference: `.planning/milestones/v1.0-ROADMAP.md` and `.planning/milestones/v1.0-REQUIREMENTS.md`.
- **v2.0 (active):** React 18 conversational SPA + JSON API backend. The React prototype at `Job Description Builder/jd-builder/` is **NOT a throwaway** — it is the starting point. ~900 LOC JSX + ~1,100 LOC CSS, all working in the browser. v2.0 completes it: Vite build pipeline, FastAPI backend, DOCX export, SQLite persistence, API integration. Deterministic classification (no LLM in main flow).
- **Phase 10 (Project Scaffold) complete** — `v2/backend/` (FastAPI + Pydantic v2 + SQLite) and `v2/frontend/` (Vite + React 18 + proxy) wired together. 10/10 tests pass; `v2/scripts/verify.sh` exits 0 with 7/7 checks. The placeholder SPA loads at `localhost:5173` and proxies `/api/*` to FastAPI on `:8000`. Conversational UX port lands in Phase 11.

## Current Milestone: v2.0 Guided Conversation

**Goal:** Replace the v1.0 multi-step HTMX wizard with a conversational React SPA that produces a live document preview, using deterministic rule-based classification (no LLM in the main flow), and ship DOCX + PDF export with full provenance.

**Target features:**
- Conversational left pane — 6-phase interview (Role → Focus → Level → Duties → Mission → Review)
- Live document preview — right pane fills as user answers; sections are clickable to edit
- Deterministic classification — work-type (EC/FI/IT/AS/EN) + 3 scope questions → group + level
- Built-in EC JES — hardcoded 9-element scale with degree vectors for EC-04/05/06
- Duty refinement — verb-mapping rules; advisor-added duties distinguished in provenance
- DND DRF picker — 6 hardcoded core responsibilities with indicators
- Qualification standard editor — default text pre-filled, editable
- Export — DOCX, PDF, clipboard
- JSON API backend (FastAPI) — replaces HTML routes; React SPA consumes it
- Brand refresh — "JD Builder — National Defence" with Hanken Grotesk + Spectral typography

## Core Value

An HR advisor can describe work in plain language and receive a legally defensible, fully traceable job description — grounded in NOC, collective agreement, and TBS classification policy — in minutes instead of hours.

## Requirements

### Validated (v1.0)

- ✓ **PIPE-01** — NOC 2021 FTS5 + sqlite-vec ingest with content hashes — v1.0
- ✓ **PIPE-02** — CA ingest: restriction/scope/exclusion clauses per OG — v1.0
- ✓ **PIPE-03** — JES ingest: factor descriptors per og_code + factor_name — v1.0
- ✓ **PIPE-04** — Content hash + version label on all ingested docs; derived records linked to source hash — v1.0
- ✓ **PIPE-05** — Startup assertion: embedding model name in index metadata must match configured model — v1.0
- ✓ **DATA-01** — WorkDescription + ProvenanceTag Pydantic model finalized before service code; SQLite schema + wd_audit_log — v1.0
- ✓ **DATA-02** — pydantic-settings config with immediate startup failure on missing env var — v1.0
- ✓ **DATA-03** — Ollama pre-warm at startup with loud failure on missing models — v1.0
- ✓ **MAP-01** — Three-stage NL→NOC pipeline (FTS5 → embedding rerank → LLM justification) — v1.0
- ✓ **MAP-02** — NOC candidates include code, title, TEER, verbatim duty matches — v1.0
- ✓ **CLASS-01** — Top-3 OG candidates with verbatim TBS definition/inclusions/exclusions — v1.0
- ✓ **CLASS-02** — Hard gate: JD generation blocked until OG confirmed — v1.0
- ✓ **CLASS-03** — AS/EC disambiguation from directive_on_classification.txt verbatim citations — v1.0
- ✓ **JD-01** — Duties are verbatim NOC text selected from indexed records (no free-form LLM output) — v1.0
- ✓ **JD-02** — Every duty carries structured ProvenanceTag (source type, NOC code, section, hash) — v1.0
- ✓ **JD-03** — Advisor-added content tagged "advisor-added" in model + visually marked in export — v1.0
- ✓ **JD-04** — Orphan statement check flags duties contradicting OG functional authority — v1.0
- ✓ **JES-01** — Per-factor JES scoring via instructor (max 3 retries); per-factor retry + advisor override for failed factors — v1.0 + Phase 8.1
- ✓ **CA-01** — CA restriction/scope/exclusion clauses pre-extracted at ingest, indexed per OG — v1.0
- ✓ **EXP-01** — DOCX export with ProvenanceTags as citations, version manifest; PDF deferred (501) — v1.0
- ✓ **DRF-01** — DRF linkages surfaced on /wizard/export for DND positions; confirmed linkages in DOCX Section 6 — v1.0

### Validated (v2.0)

- ✓ **API-01** — FastAPI app with 5 Pydantic v2 models (WorkDescription, DraftDuty, Classification, JESFactor, QualificationStandard) — validated in Phase 10 (Project Scaffold, completed 2026-06-03)
- ✓ **API-05** — Single-file SQLite at `DB_PATH` with `work_descriptions` and `audit_log` tables (idempotent `create_schema` on lifespan startup) — validated in Phase 10 (Project Scaffold, completed 2026-06-03)
- ✓ **FE-02** — Vite dev server proxies `/api/*` to FastAPI on a separate port (8000) with `changeOrigin: true` — validated in Phase 10 (Project Scaffold, completed 2026-06-03)

### Active (v2.0)

See `.planning/REQUIREMENTS.md` for scoped requirements with REQ-IDs. v2.0 is being defined in the current milestone cycle; the 8–10 target features above will be translated into REQ-IDs in step 9 of the new-milestone workflow.

### Out of Scope

| Feature | Reason |
|---------|--------|
| Manager-facing UI | Deferred — single-user advisor app for v2.0; multi-role UX is a later milestone |
| Multi-user / multi-tenant deployment | Single-user local app; auth, isolation deferred |
| OpenAI or external LLM as primary | v2.0 classification is deterministic; LLM may return as an optional enhancement later but is not in the main flow |
| Live OASIS scraping as primary data source | v1.0 data pipelines are archived; v2.0 uses curated, hardcoded authoritative content |
| Real-time CA update sync | Static curated dataset; manual update only |
| Staffing / competition workflow | JD builder only; downstream competition tooling is separate |
| Pay band calculation | Rates of pay are reference data only |
| Bilingualism enforcement | Flag only; blocking on French translation is out of scope |
| Grievance management workflow | This tool creates defensible WDs; it does not manage disputes |
| WeasyPrint PDF export on Jane | TBD — PDF export is a v2.0 target; ARM64 Pango/Cairo feasibility must be verified before committing to WeasyPrint vs docx2pdf vs server-side rendering |
| **QUAL-01** (v1.0 candidate: pre-populate Qual Standard) | Dropped — drafted for v1.0 wizard; v2.0 uses pre-filled editable defaults instead of dataset-driven population |
| **CA-02/03** (v1.0 candidate: CA active validation per duty) | Dropped — drafted for v1.0 wizard; v2.0 does not have a CA restriction-clause check in the main flow |
| **JES-02/03/04** (v1.0 candidate: factor traceability + validator + advisor divergence) | Dropped — drafted for v1.0 LLM-driven JES; v2.0 uses hardcoded EC JES degree vectors, not LLM scoring |
| **EXP-02/03** (v1.0 candidate: pre-export completeness + sign-off audit) | Dropped — drafted for v1.0 wizard with multi-step export gate; v2.0 has a single review step + checklist, not a pre-export gate |
| **MAP-03** (v1.0 candidate: NOC manual override) | Dropped — drafted for v1.0 NOC mapping; v2.0 has no NOC mapping step (work-type + scope is the entry point) |
| **JD-05** (v1.0 candidate: AI organizational context drafting) | Dropped — drafted for v1.0 LLM-driven JD; v2.0 builds the overview paragraph from advisor answers directly (no LLM) |

## Context

**v1.0 delivered (2026-06-03, archived):**
15,539 lines Python. Full HTMX wizard from NL input to DOCX export. All 21 v1 requirements delivered. 188 tests passing. NOC 2021 FTS5 + sqlite-vec pipeline; CA / JES / policy data pipelines; LLM-driven classification via Ollama (local) + DashScope (cloud Stage 3). Full archive at `.planning/milestones/v1.0-`.

**v2.0 design source of truth:**
`Job Description Builder/jd-builder/` — a static HTML + React 18 prototype. 6 .jsx files (~900 LOC) + ~1,100 LOC CSS. Demonstrates the full conversational UX, classification engine, and live document preview. All data is hardcoded; no backend. The v2.0 build ports this design into a real React SPA + FastAPI JSON API.

**v1.0 → v2.0 architectural pivot:**
- Frontend: server-rendered HTMX wizard → React 18 single-page app
- Classification: LLM-driven (Ollama + DashScope) → deterministic rule-based (work-type + 3 scope questions)
- JES scoring: per-factor LLM call with instructor retry → hardcoded EC JES 9-element table with degree vectors
- NOC mapping: FTS5 + embedding rerank + LLM justification → not in v2.0 (work-type is the entry point)
- Data: SQLite + sqlite-vec + ingest pipelines → curated hardcoded authoritative content
- Export: DOCX only (PDF 501) → DOCX + PDF + clipboard

**Prior work (JD-Builder-Lite prototype):**
25+ phases of iteration, full Flask + vanilla JS SPA. Lessons: OASIS scraping fragile; hardcoded paths; semantic matcher (500MB) caused 30-60s cold starts; no tests; SSL verification disabled. What worked: provenance-first design, Pydantic model contracts, medallion data architecture. v1.0 applied these lessons.

**Hardware and runtime:**
- Jetson AGX Orin "Jane" — ARM64, Linux
- Local inference is optional in v2.0 (deterministic flow runs offline; LLM enhancements may be added later)
- Claude API available as optional enhancement for any future LLM-driven features

**v1.0 technical debt — not carried into v2.0:**
- noc_fts DDL bug (UNINDEXED + content='' — deferred from Phase 4) — irrelevant; v1.0 DB archived
- Starlette TemplateResponse deprecation warning (deferred from Phase 4) — irrelevant; v2.0 is a React SPA
- 02-02-SUMMARY.md not written — v1.0 archive gap; v2.0 will write all phase summaries

## Constraints

- **Hardware**: ARM64 (Jetson AGX Orin) — all Python and Node dependencies must have ARM64 wheels; no x86-only packages
- **AI runtime**: Deterministic in v2.0 — no external API required to run the app; LLM may return as an optional enhancement but the main flow runs fully offline
- **Data sources**: Curated, hardcoded authoritative content for v2.0 (NOC summaries, DRF rows, JES tables, Qualification Standard defaults); v1.0 ingest pipelines are archived
- **Policy compliance**: Output must satisfy TBS Directive on Classification requirements for a legally defensible work description
- **Traceability**: Every content element exported must have a machine-readable source citation — non-negotiable for legal defensibility; the v2.0 design encodes this in the `prov__tag` footer of the document preview
- **DND context**: DRF integration and DND-specific data are first-class features
- **Frontend framework**: React 18 SPA, no SSR; consumes a JSON API
- **Backend stack**: FastAPI (Pydantic v2 models) with JSON endpoints; no HTML rendering
- **Design fidelity**: The v2.0 React app must match the prototype in `Job Description Builder/jd-builder/` (conversation pane, live preview, classification badge, brand typography)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastAPI over Flask | LLM streaming via StreamingResponse; Flask WSGI blocks during Ollama calls | ✓ Good — no blocking issues in v1.0 production |
| HTMX 2.x + Alpine.js 3.x (v1.0) | No build step; ~29KB combined; server-rendered wizard pattern | ✓ Good for v1.0 — wizard delivered in 9 phases. Superseded by React 18 SPA in v2.0 |
| SQLite + sqlite-vec for app state (v1.0) | App state and vector search co-located; eliminates DuckDB runtime dependency | ✓ Good for v1.0 — single file, zero infra. Archived in v2.0 |
| DashScope qwen3-max for Stage 3 (v1.0) | Local gemma4:31b too slow (6 min/request); cloud inference at $30/month budget | ✓ Good for v1.0 — acceptable latency. v2.0 doesn't need it |
| instructor over raw Ollama format (v1.0) | Mandatory retry wrapper for local model structured output edge cases | ✓ Good for v1.0 — Phase 8.1 proved this essential. Archived |
| Fresh codebase (not fork) for v1.0 | 25 phases of prototype debt; clean slate allows better architecture | ✓ Good for v1.0 — zero legacy surprises. v2.0 also starts fresh |
| ProvenanceTag on every domain object (v1.0) | Set at write time, rendered at export — legal defensibility core invariant | ✓ Good for v1.0 — held throughout all 9 phases. v2.0 carries this forward in the `prov__tag` footer pattern |
| docxtpl for DOCX export (v1.0) | Python-native, ARM64 compatible, Jinja2 template model | ✓ Good for v1.0 — template committed as binary artifact + reproducible build script. v2.0 will use the same approach |
| **v2.0 React 18 SPA over HTMX** | Conversational UX needs client-side state (live preview, edit-and-revisit, clickable sections); HTMX's request-response model doesn't fit a persistent document that updates as the user types | — Pending v2.0 |
| **v2.0 deterministic classification over LLM** | The work-type + 3-scope-question model is interpretable, instant, offline, and reproducible. The LLM-driven NOC/OG pipeline was a research bet that the conversational UX replaces | — Pending v2.0 |
| **v2.0 hardcoded EC JES table over LLM scoring** | EC JES 2017 is a published standard with fixed degree/point scales. Hardcoding is correct, auditable, and faster than LLM. FI/IT/AS/EN use approximate totals for v2.0 | — Pending v2.0 |
| **v2.0 verb-mapping duty refinement over LLM** | The refineDuty function covers the common cases (clean up → Remediates, advise → Advises). Edge cases fall back to "Performs duties related to X" rather than LLM generation | — Pending v2.0 |
| **v2.0 PDF in scope (no 501)** | The conversational UX is complete at review time; exporting to PDF is a direct template render, not blocked on classification ambiguity | — Pending v2.0 |
| **v2.0 curated hardcoded data over v1.0 ingest pipelines** | NOC/OG/JES data is small enough to live in code as constants. Eliminates ingest script complexity, FTS5 indexing, and embedding-model-version drift | — Pending v2.0 |
| **v2.0 phase numbering continues from Phase 10** | Keeps a single linear history. v1.0 phases 1–9 (incl. 8.1) are archived but not renumbered | — Pending v2.0 |
| **v2.0 drops 10 v1.0-drafted v2 candidates (QUAL-01, CA-02/03, JES-02/03/04, EXP-02/03, MAP-03, JD-05)** | These were drafted for the v1.0 wizard. The conversational design has different priorities; carrying them forward would be a cargo-cult | — Pending v2.0 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-03 after Phase 10 (Project Scaffold) completion*
