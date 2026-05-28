# JD Builder

## What This Is

A DND-first Government of Canada job description builder for HR advisors and classification specialists. An advisor describes the work to be performed in plain language; the system maps that description to authoritative NOC profiles, suggests an occupational group and level, and generates a fully traced job description grounded in NOC, collective agreements, job evaluation standards, and TBS policy. V1 targets HR advisors; the north star is a manager-facing experience once the authoritative data layer is proven.

## Core Value

An HR advisor can describe work in plain language and receive a legally defensible, fully traceable job description — grounded in NOC, collective agreement, and TBS classification policy — in minutes instead of hours.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **INPUT-01**: Advisor can describe work to be performed in natural language (free text, variably structured) and receive a ranked list of matching NOC unit groups with supporting rationale
- [ ] **INPUT-02**: System maps described work to NOC nomenclature — duties, activities, skills — reflecting the underlying data relationships rather than user's raw words
- [ ] **CLASS-01**: System suggests an occupational group (OG) and level based on described work and NOC mapping; advisor reviews and confirms before JD is generated
- [ ] **CLASS-02**: OG suggestion cites the relevant TBS OG definition, inclusions, and exclusions as evidence
- [ ] **JD-01**: System drafts key duties/activities grounded in matched NOC profile statements, with each statement linked to its source (NOC code, section, version)
- [ ] **JD-02**: System generates a position overview paragraph from NOC profile and described context; advisor can edit and system validates edits against source data
- [ ] **JES-01**: System produces a Job Evaluation Standard scoring sheet for the confirmed OG, with AI-drafted factor ratings and rationale traceable to the duties and NOC source data
- [ ] **JES-02**: Advisor can adjust JES factor ratings; system flags where adjustment diverges from AI-suggested rating with a brief explanation
- [ ] **QUAL-01**: System surfaces the applicable Qualification Standard for the confirmed OG, pre-populating education and experience fields; advisor fills position-specific requirements
- [ ] **COMP-01**: System suggests Key Leadership Competencies appropriate to the confirmed level; advisor selects and may add position-specific competencies
- [ ] **CA-01**: After JD is drafted, system validates content against the applicable collective agreement — flags any duties that conflict with CA article restrictions or fall outside OG scope
- [ ] **CA-02**: Validation produces a traceable report: which CA articles were checked, which passed, which flagged, and why
- [ ] **DRF-01**: For DND positions, system surfaces DND Departmental Results Framework links — connecting position duties to the DRF program and expected results the position supports
- [ ] **EXPORT-01**: Export to DOCX and PDF includes: position information, duties with NOC source citations, JES scoring with rationale, qualification standard, competencies, CA validation summary, provenance metadata (data sources, versions, date produced, advisor)
- [ ] **PROV-01**: Every piece of content in the exported JD has a traceable origin: NOC code + section + date, CA article + OG + date, JES factor + standard version, or explicit "advisor-added / not from authoritative source"

### Out of Scope

- Manager-facing UI — V2 goal; managers require much more hand-holding and guardrails than V1 advisor workflow can provide
- Multi-user / multi-tenant deployment — single-user local app for V1; authentication, isolation, and audit logging deferred
- OpenAI or external LLM as primary AI — Ollama-first on ARM64 hardware; no external API dependency for core functionality
- Live OASIS scraping as primary data source — lesson from prototype: HTML fragility broke the app repeatedly; local authoritative files only
- Real-time collective agreement updates — static dataset updated manually; automated sync is out of scope
- Staffing/competition workflow — JD builder only; downstream use in competitions, merit criteria, or Psych profiling is out of scope
- Pay band calculation — rates of pay are reference data for context; automated compensation recommendation is out of scope

## Context

**Prior work (JD-Builder-Lite prototype):**
- 25+ phases of iteration, full Flask + vanilla JS SPA, occupational group classification engine
- Lessons: OASIS scraping was fragile; hardcoded paths killed portability; semantic matcher (500MB) caused 30-60s cold starts on first request; no tests meant bugs surfaced only in UAT; SSL verification was disabled (critical issue)
- What worked: provenance-first design, Pydantic model contracts, medallion data architecture (Bronze→Silver→Gold parquet), JES scoring concept (planned but never fully built), PDF/DOCX export with compliance metadata

**Data already collected (in `data/` and `webscrapes/`):**
- Collective agreements: 25+ OGs (AI, AO, CP_AV, CT_FI, CX, EB, EC, EL, FB, FS, IT_CS, LP_LA, NR, PA, PO, RE, RM, RO, SH, SO, SP_AP, SRC, SRE, SRW, SV, TC, TR, UT) — JSON + TXT
- Job Evaluation Standards: CT, EC, ED, EX, FB, FS, IT, LC, LP, MT, NU, PO, PS, SW, WP — TXT
- Rates of pay: most OGs — CSV
- DND Departmental Results Framework dataset — CSV
- ESDC Skills and Competencies Taxonomy 2025 v6.0 — CSV
- Public Service Employment Act — TXT
- Data model ERD + source-of-truth architecture diagram

**Data gaps to fill before or during build:**
| Dataset | Source | Priority |
|---------|--------|----------|
| TBS Qualification Standards (per OG) | Canada.ca/TBS | HIGH — required for QUAL-01 |
| TBS Directive on Classification (2021) | Canada.ca/TBS | HIGH — legal anchor for all classification |
| TB Secretariat Allocation Guide | Canada.ca/TBS | HIGH — OG allocation methodology |
| OCHRO OG Definitions with inclusions/exclusions | Canada.ca/TBS | HIGH — required for CLASS-02 |
| NOC 2021 unit group profiles | ESDC OASIS or parquet | HIGH — core data source for duties |
| Key Leadership Competencies framework | OCHRO/Canada.ca | MEDIUM — required for COMP-01 |
| OCHRO Competency Dictionary (behavioural indicators) | OCHRO/Canada.ca | MEDIUM — required for COMP-01 |
| Values and Ethics Code for the Public Sector | TBS | MEDIUM — referenced in JDs |
| DND DAODs relevant to HR classification | DND DAOD registry | LOW — DND-specific constraints |

**Hardware and runtime:**
- Jetson AGX Orin "Jane" — ARM64, Linux
- Ollama already running locally with available models
- $30/month API budget — Claude API available as optional enhancement, not primary dependency

**Architecture target:**
- Python backend (Flask or FastAPI) + local parquet/SQLite data layer
- Ollama for local LLM inference (classification, draft generation, CA validation)
- Optional Claude API for higher-quality drafts when advisor opts in
- Vanilla JS or lightweight frontend — no heavy framework
- Data follows medallion pattern: raw source files → parsed structured JSON/parquet → indexed for query

## Constraints

- **Hardware**: ARM64 (Jetson AGX Orin) — all dependencies must have ARM64 wheels; no x86-only packages; no models requiring >16GB VRAM
- **AI runtime**: Ollama-first — no external API required to run the app; Claude API is an optional enhancement
- **Data sources**: Local files only as primary source — no live scraping in production data paths; scraping tools exist for data refresh only
- **Policy compliance**: Output must satisfy TBS Directive on Classification requirements for a legally defensible work description
- **Traceability**: Every content element exported must have a machine-readable source citation — this is non-negotiable for legal defensibility
- **Fresh codebase**: Do not fork JD-Builder-Lite; borrow patterns and lessons, not code
- **DND context**: DRF integration and DND-specific data are first-class features, not afterthoughts

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Ollama-first AI | ARM64 hardware, no external API dependency, $30/month budget constraint, operational independence | — Pending |
| Fresh codebase (not fork) | Prototype had 25 phases of accumulated debt; clean slate allows better architecture from day 1 | — Pending |
| Natural language input → NOC mapping | More intuitive than browse-NOC approach; aligns with north star (manager UX); forces the system to do the domain translation work | — Pending |
| Collective agreements as validation layer | Hard enforcement during drafting would make the tool too restrictive for V1; post-draft validation surfaces issues without blocking flow | — Pending |
| System suggests OG, advisor confirms | Classification is legally consequential; advisor must retain authority; system provides evidence-based recommendation, not a mandate | — Pending |
| Full JES scoring in V1 export | Legally defensible JD requires JES scoring; deferring it would mean the V1 output is incomplete for real use | — Pending |
| Local parquet files as primary data source | Prototype proved OASIS scraping fragile; all critical data already collected locally; parquet enables fast, reliable, offline-capable queries | — Pending |

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
*Last updated: 2026-05-28 after initialization*
