# JD Builder

## What This Is

A DND-first Government of Canada job description builder for HR advisors and classification specialists. An advisor describes the work to be performed in plain language; the system maps that description to authoritative NOC profiles, suggests an occupational group and level, and generates a fully traced job description grounded in NOC, collective agreements, job evaluation standards, and TBS policy — all in a local, offline-capable HTMX wizard running on ARM64 hardware.

v1.0 (MVP) shipped 2026-06-03. The full NL→NOC → OG → JD → JES → Export wizard is working end-to-end. V2 north star is a manager-facing experience and CA active validation once the authoritative data layer is proven.

## Current State (v1.0)

- **Stack:** FastAPI + HTMX 2.x + SQLite + sqlite-vec + Ollama (local) + DashScope qwen3-max (cloud Stage 3)
- **LOC:** ~15,539 Python, 773 HTML, 1,138 CSS
- **Tests:** 188 passing, 9 skipped
- **Hardware:** Jetson AGX Orin "Jane" (ARM64)
- **Data indexed:** NOC 2021 profiles (FTS5 + sqlite-vec), CA clauses per OG, JES factors per og_code, TBS Directive on Classification + Policy on People Management, DRF dataset (42 rows)

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

### Active (v2 targets)

- [ ] **QUAL-01**: System surfaces applicable Qualification Standard for confirmed OG; pre-populates education + experience fields — requires TBS Qualification Standards dataset
- [ ] **CA-02**: Each draft duty checked against applicable CA restriction clause; flagged items cite CA article number
- [ ] **CA-03**: CA validation summary in exported WD (pass/flag per duty)
- [ ] **JES-02**: Each JES factor rating cites specific duties by verbatim quote as evidence (factor-to-duty traceability)
- [ ] **JES-03**: Deterministic point-range validator checks AI-generated totals fall within valid range per degree
- [ ] **JES-04**: Advisor can adjust JES factor ratings; system flags divergence from AI suggestion with explanation
- [ ] **EXP-02**: Pre-export completeness validator blocks export if mandatory TBS WD elements absent
- [ ] **EXP-03**: Advisor review checklist with per-element sign-off timestamps in wd_audit_log
- [ ] **MAP-03**: Advisor can override/correct NOC suggestion with manual search before confirming
- [ ] **JD-05**: AI drafts organizational context / position overview paragraph with edit tracking

### Out of Scope

| Feature | Reason |
|---------|--------|
| Manager-facing UI | V2 goal; managers require significantly more UX work and guardrails |
| Multi-user / multi-tenant deployment | Single-user local app for V1; auth, isolation deferred |
| OpenAI or external LLM as primary | Ollama-first; no external API dependency for core functionality |
| Live OASIS scraping as primary data source | Fragile in prototype; local authoritative files only |
| Real-time CA update sync | Static dataset updated manually |
| Staffing / competition workflow | JD builder only; downstream use in competitions is separate tooling |
| Pay band calculation | Rates of pay are reference data only |
| Bilingualism enforcement | Flag only in v2; blocking on French translation is out of scope |
| Grievance management workflow | This tool creates defensible WDs; it does not manage disputes |
| WeasyPrint PDF export | PDF endpoint returns 501; ARM64 Pango/Cairo untested on Jane; DOCX is primary v1 output |

## Context

**v1.0 delivered (2026-06-03):**
15,539 lines Python. Full HTMX wizard from NL input to DOCX export. All 21 v1 requirements delivered. 188 tests passing.

**Prior work (JD-Builder-Lite prototype):**
25+ phases of iteration, full Flask + vanilla JS SPA. Lessons: OASIS scraping fragile; hardcoded paths; semantic matcher (500MB) caused 30-60s cold starts; no tests; SSL verification disabled. What worked: provenance-first design, Pydantic model contracts, medallion data architecture.

**Hardware and runtime:**
- Jetson AGX Orin "Jane" — ARM64, Linux
- Ollama running locally (nomic-embed-text for vectors; gemma4:31b or similar for local inference)
- DashScope qwen3-max used for Stage 3 NL→NOC justification (cloud inference)
- $30/month API budget; Claude API available as optional enhancement

**Known technical debt entering v2:**
- noc_fts DDL bug (UNINDEXED + content='' mismatch — deferred from Phase 4)
- Starlette TemplateResponse deprecation warning (deferred from Phase 4)
- 02-02-SUMMARY.md never written

## Constraints

- **Hardware**: ARM64 (Jetson AGX Orin) — all dependencies must have ARM64 wheels; no x86-only packages
- **AI runtime**: Ollama-first — no external API required to run the app; DashScope/Claude API are optional enhancements
- **Data sources**: Local files only as primary source — no live scraping in production data paths
- **Policy compliance**: Output must satisfy TBS Directive on Classification requirements for a legally defensible work description
- **Traceability**: Every content element exported must have a machine-readable source citation — non-negotiable for legal defensibility
- **DND context**: DRF integration and DND-specific data are first-class features, not afterthoughts

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastAPI over Flask | LLM streaming via StreamingResponse; Flask WSGI blocks during Ollama calls | ✓ Good — no blocking issues in production |
| HTMX 2.x + Alpine.js 3.x | No build step; ~29KB combined; server-rendered wizard pattern | ✓ Good — wizard delivered in 9 phases with no JS framework overhead |
| SQLite + sqlite-vec for app state | App state and vector search co-located; eliminates DuckDB runtime dependency | ✓ Good — single file, zero infra |
| DashScope qwen3-max for Stage 3 | Local gemma4:31b too slow (6 min/request); cloud inference at $30/month budget | ✓ Good — acceptable latency; stays within budget |
| instructor over raw Ollama format | Mandatory retry wrapper for local model structured output edge cases | ✓ Good — Phase 8.1 proved this essential |
| Fresh codebase (not fork) | 25 phases of prototype debt; clean slate allows better architecture | ✓ Good — zero legacy surprises |
| ProvenanceTag on every domain object | Set at write time, rendered at export — legal defensibility core invariant | ✓ Good — held throughout all 9 phases |
| docxtpl for DOCX export | Python-native, ARM64 compatible, Jinja2 template model | ✓ Good — template committed as binary artifact + reproducible build script |
| Phase 8.1 insertion | Export blocked with no recovery path when LLM produced malformed JES output | ✓ Good — retry + override closed the gap without redesigning the scoring architecture |
| Phase 9 inline-panel design | DND-only prototype; separate /wizard/drf step was over-engineered for the use case | ✓ Good — simpler, less navigation, DRF visible at export decision point |
| DRF DOCX gate on linkage count (not is_dnd_position) | Empty Section 6 is noise; advisor may export before confirming linkages | ✓ Good — gate is meaningful, not bureaucratic |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each milestone:**
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-03 after v1.0 milestone*
