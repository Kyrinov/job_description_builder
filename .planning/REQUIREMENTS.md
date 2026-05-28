# Requirements: JD Builder

**Defined:** 2026-05-28
**Core Value:** An HR advisor can describe work in plain language and receive a legally defensible, fully traceable job description — grounded in NOC, collective agreement, and TBS classification policy — in minutes instead of hours.

---

## v1 Requirements

### Data Pipeline

- [ ] **PIPE-01**: Developer can run an ingest pipeline that loads NOC 2021 unit group profiles, producing an FTS5 full-text index and a sqlite-vec embedding index (nomic-embed-text), with a content hash and version label recorded per source document
- [ ] **PIPE-02**: Developer can run an ingest pipeline that processes collective agreement JSON files, extracting restriction/scope/exclusion clauses per OG using the configured local generation model (`gemma4:31b` by default), storing them as structured records in a queryable index keyed by OG code
- [ ] **PIPE-03**: Developer can run an ingest pipeline that parses JES documents per OG, producing structured factor objects (og_code, factor_name, degree_descriptors, point_range) stored in SQLite
- [ ] **PIPE-04**: Every source document ingested records a content hash and version label; every derived record stores the source document version hash it was derived from
- [ ] **PIPE-05**: On startup, the system asserts the embedding model name in the vector index metadata matches the currently configured model — the app refuses to serve queries on mismatch

### Core Data Model

- [ ] **DATA-01**: The WorkDescription Pydantic model and SQLite schema are finalized before any service code is written — includes all TBS-required WD fields (position title, number, OG/level, supervisor info, review date, organizational context), a `wd_audit_log` table, and a `ProvenanceTag` type that every content element carries
- [ ] **DATA-02**: All runtime configuration is loaded from environment variables with startup validation — missing required variables cause an immediate startup failure with a descriptive error message
- [ ] **DATA-03**: The application pre-warms the Ollama connection and confirms the required models are available at startup, failing loudly if any model is missing

### NL→NOC Mapping

- [ ] **MAP-01**: Advisor can describe work to be performed in natural language; the system runs a three-stage pipeline — FTS5 keyword shortlist → nomic-embed-text embedding rerank → configured local generation model structured justification — and returns ranked NOC unit group candidates
- [ ] **MAP-02**: Each NOC candidate returned includes the NOC code, unit group title, TEER level, and the specific NOC duty statements from the source profile that best match the described work

### OG Classification

- [ ] **CLASS-01**: For the advisor-confirmed NOC match, the system presents the top 3 occupational group candidates side-by-side — each showing OG code, name, definition excerpt, relevant inclusions, and relevant exclusions, cited from TBS source documents
- [ ] **CLASS-02**: Advisor confirms an occupational group and level before JD content generation proceeds — this is a hard workflow gate; no generation starts without explicit OG confirmation
- [ ] **CLASS-03**: For positions where the work description contains policy-related duties, the system surfaces the AS vs. EC distinction explicitly — showing the TBS definition test (internal departmental guidance → AS; shaping policy for the Canadian public → EC), with the relevant inclusion/exclusion statements from the applicable OG definitions cited verbatim; this logic runs before OG confirmation and must be grounded in `data/directive_on_classification.txt`

### JD Content Generation

- [ ] **JD-01**: System drafts key duties/activities for the confirmed NOC and OG by selecting verbatim text from NOC profile statements stored in the database — the LLM ranks and selects from indexed records, it does not generate free-form duty text
- [ ] **JD-02**: Every duty and content element in the WD carries a structured ProvenanceTag: source type, NOC code, section name, statement text, and source document version hash
- [ ] **JD-03**: Any content added by the advisor that has no source record is tagged "advisor-added / not from authoritative source" in the data model and rendered with a distinct visual indicator in the export
- [ ] **JD-04**: After duties are drafted, the system runs an orphan statement check — scanning each duty against a pre-indexed set of functional authority rules (e.g., "provides HR advice" is reserved to PE positions per DAOD/functional authority) and flagging any duty that contradicts the established authority for that OG; each flag cites the source rule by document and article

### JES Scoring

- [ ] **JES-01**: System generates a JES scoring sheet for the confirmed OG by making one configured local generation model call per JES factor — with the full factor descriptor and degree definitions injected fresh per call — returning a structured scoring object validated by Pydantic via `instructor` (max 3-attempt retry)

### CA Validation Infrastructure

- [ ] **CA-01**: The data pipeline pre-extracts restriction, scope, and exclusion clauses from collective agreements per OG at ingest time, storing them as structured records indexed by OG code — foundation for active CA checking in v2

### Export

- [ ] **EXP-01**: User can export the completed WD to DOCX (docxtpl) and PDF (WeasyPrint) — every content element's source citation is rendered from its ProvenanceTag object; the export includes a version manifest of all source documents used; no prose citations are written directly into the template

### DND Integration

- [ ] **DRF-01**: For DND positions, the system surfaces Departmental Results Framework program linkages connecting the position's duties to DRF expected results, sourced from the DRF dataset in `data/`

---

## v2 Requirements

### JES Enhancements

- **JES-02**: Each JES factor rating cites specific duties by verbatim quote as evidence — factor-to-duty traceability (the #1 grievance protection; deferred to v2 to keep v1 scope bounded)
- **JES-03**: A deterministic point-range validator checks AI-generated point totals fall within valid range for each degree
- **JES-04**: Advisor can adjust JES factor ratings; system flags divergence from AI-suggested rating with explanation

### CA Active Validation

- **CA-02**: Each draft duty is checked against the applicable CA restriction clause index; flagged items cite the CA article by number
- **CA-03**: CA validation summary included in the exported WD with pass/flag status per duty

### Export Hardening

- **EXP-02**: Pre-export completeness validator blocks export if mandatory TBS WD elements are absent (financial authorities, supervisory responsibilities, physical conditions, freedom to act, contacts)
- **EXP-03**: Advisor review checklist with per-element sign-off timestamps stored in `wd_audit_log` — prevents rubber-stamping

### JD Generation Enhancements

- **JD-05**: AI drafts an organizational context / position overview paragraph; advisor edits with modification tracking
- **JD-06**: Duties include relative time/importance weighting as required by some collective agreements

### Search UX

- **MAP-03**: Advisor can override or correct the system's NOC suggestion with a manual search before confirming
- **MAP-04**: NOC candidates display full rationale in an expandable comparison UI

### Manager-Facing Workflow

- **MGR-01**: Simplified manager-facing workflow with more guided input, less classification vocabulary — V2 north star
- **MGR-02**: Manager drafts, HR advisor reviews and finalizes — dual-role workflow

### Bilingualism

- **LANG-01**: WDs destined for bilingual regions or bilingual imperative positions are flagged — French translation required before staffing use

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Manager-facing UI | V2 goal; requires significantly more UX work and guardrails |
| Multi-user / multi-tenant deployment | Single-user local app for V1; auth, isolation, audit logging deferred |
| OpenAI or external LLM as primary | Ollama-first; no external API dependency for core functionality |
| Live OASIS scraping as primary data source | Proven fragile in prototype; local authoritative files only |
| Real-time CA update sync | Static dataset updated manually; automated sync out of scope |
| Staffing / competition workflow | JD builder only; downstream use in competitions is separate tooling |
| Pay band calculation | Rates of pay are reference data; automated compensation recommendation out of scope |
| Bilingualism enforcement | Flag only in v2; blocking on French translation is out of scope |
| Grievance management workflow | Out of scope — this tool creates defensible WDs, it does not manage disputes |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PIPE-01 | Phase 2 | Pending |
| PIPE-02 | Phase 3 | Pending |
| PIPE-03 | Phase 3 | Pending |
| PIPE-04 | Phase 2, 3 | Pending |
| PIPE-05 | Phase 2 | Pending |
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| MAP-01 | Phase 4 | Pending |
| MAP-02 | Phase 4 | Pending |
| CLASS-01 | Phase 5 | Pending |
| CLASS-02 | Phase 5 | Pending |
| CLASS-03 | Phase 5 | Pending |
| JD-01 | Phase 6 | Pending |
| JD-02 | Phase 6 | Pending |
| JD-03 | Phase 6 | Pending |
| JD-04 | Phase 6 | Pending |
| JES-01 | Phase 7 | Pending |
| CA-01 | Phase 3 | Pending |
| EXP-01 | Phase 8 | Pending |
| DRF-01 | Phase 9 | Pending |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 21/21
- Unmapped: 0

---
*Requirements defined: 2026-05-28*
*Last updated: 2026-05-28 after roadmap creation (19/19 requirements mapped)*
