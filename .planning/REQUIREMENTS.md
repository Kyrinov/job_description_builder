# Requirements: JD Builder

**Defined:** 2026-06-03
**Core Value:** An HR advisor can describe work in plain language and receive a legally defensible, fully traceable job description — grounded in NOC, collective agreement, and TBS classification policy — in minutes instead of hours.

## v1 Requirements (Validated — Shipped 2026-06-03)

All 21 v1.0 requirements shipped and are archived. Full traceability at `.planning/milestones/v1.0-REQUIREMENTS.md`.

| Category | Count | Highlights |
|----------|------:|------------|
| PIPE — Data pipeline | 5 | NOC 2021 FTS5 + sqlite-vec, CA, JES, content hashing, embedding model assertion |
| DATA — Domain models & config | 3 | WorkDescription + ProvenanceTag, pydantic-settings, Ollama pre-warm |
| MAP — NL→NOC mapping | 2 | Three-stage pipeline (FTS5 → embedding rerank → LLM justification) |
| CLASS — OG classification | 3 | Top-3 candidates, hard gate, AS/EC disambiguation |
| JD — Job description generation | 4 | Verbatim NOC duties, structured ProvenanceTag, advisor-added tag, orphan check |
| JES — JES scoring | 1 | Per-factor instructor with retry + per-factor override (Phase 8.1) |
| CA — Collective agreement | 1 | Restriction/scope/exclusion clauses pre-extracted per OG |
| EXP — Export | 1 | DOCX with provenance citations + version manifest (PDF 501) |
| DRF — DND DRF integration | 1 | Inline panel on /wizard/export + DOCX Section 6 |

## v2 Requirements (Active)

v2.0 ("Guided Conversation") is a full rewrite around a conversational React SPA + FastAPI JSON API. The React prototype at `Job Description Builder/jd-builder/` is the UX design source of truth and the starting point for the build. v2.0 ports that prototype into a real Vite-built SPA with persistence and DOCX export.

### CONVO — Conversation UX

- [ ] **CONVO-01**: Advisor progresses through a 6-phase interview (Role → Focus → Level → Duties → Mission → Review) with 12 total steps
- [ ] **CONVO-02**: Advisor can click any answered exchange in the transcript to revisit and re-answer that step without losing prior answers
- [ ] **CONVO-03**: Conversation pane header shows 6 phase chips with active / done / pending states as the advisor advances
- [ ] **CONVO-04**: Each step renders the appropriate input control: text input, textarea, single-select choice cards (with icons and descriptions), 3-point scale (ends + options), duty builder, DRF picker, qualification editor
- [ ] **CONVO-05**: Advisor can press Enter to continue (Cmd/Ctrl+Enter for textarea), use the Back button on step 2+, and the active question auto-scrolls into view

### CLASS — Classification engine

- [ ] **CLASS-01**: Advisor selects one of 6 work-type options: EC (policy/research/analysis, program/project delivery), FI (financial management), IT (IT/data), AS (admin/coordination), EN (engineering/technical). Each option carries a group, group name, and applicable JES standard
- [ ] **CLASS-02**: Advisor answers 3 scope questions (day-to-day direction, advice reach, scope of impact) on a 3-point scale; each answer is a 1–3 integer
- [ ] **CLASS-03**: System resolves group + level deterministically from work-type + scope answers: scope sum ≤ 4 → level 4; ≤ 7 → level 5; else level 6. Code is `<group>-0<level>`. EC group yields full 9-element factor scorecard; FI/IT/AS/EN use approximate point totals
- [ ] **CLASS-04**: Document preview header shows a live classification badge with the resolved group/level, point total, and a confidence ring (0.61 group-only baseline, up to 0.96 with low-spread scope answers)
- [ ] **CLASS-05**: When resolved, the system produces a plain-English rationale string describing the scope profile and why it maps to the chosen group/level; rendered in the Classification & Evaluation section

### JES — Job Evaluation Standard scoring

- [ ] **JES-01**: System encodes the EC JES 2017 9-element table verbatim: Decision making, Leadership & operational mgmt, Communication, Knowledge of specialized fields, Contextual knowledge, Research & analysis, Physical effort, Sensory effort, Working conditions. Each element has a degree→points scale and a category (Responsibility / Skill / Effort / Conditions)
- [ ] **JES-02**: System carries pre-defined degree vectors for EC-04, EC-05, EC-06 (one degree per element per level); selecting the level yields the full factor scorecard instantly
- [ ] **JES-03**: System uses approximate point totals for non-EC groups at levels 4/5/6 (FI: 470/560/660, IT: 480/575/690, AS: 430/510/600, EN: 500/600/720); rendered as a single Total line, not a factor breakdown
- [ ] **JES-04**: Classification & Evaluation section renders per-factor rows for EC (name, D{degree}, points) and a totals row; non-EC groups render only the totals line with the applicable JES standard cited

### DUTY — Duty management

- [ ] **DUTY-01**: Advisor sees 7 pre-written suggested duties as togglable cards; selecting a duty shows its plain trigger and polished formal statement; selected cards show a "refined for the description" tag
- [ ] **DUTY-02**: Advisor can add a duty in plain words via a free-text input; the duty is appended to the list with a remove button and is rendered with the "advisor" flag in the document
- [ ] **DUTY-03**: As the advisor types a free-text duty, a live preview shows the refined formal statement below the input ("Will read as: Remediates contaminated sites.")
- [ ] **DUTY-04**: System applies built-in verb-mapping rules to refine plain-text duties (clean up → Remediates, advise → Advises, write → Prepares, lead → Leads, etc.); unrecognized leading verbs fall back to "Performs duties related to X."
- [ ] **DUTY-05**: Document preview visually marks advisor-added duties (distinct class) so the source is obvious in the export

### QUAL — Qualification standard

- [ ] **QUAL-01**: System pre-fills the Essential Qualifications section with a default EC-05 text (degree in environmental science / economics / public policy / relevant discipline; significant experience in policy/analysis including advice to management, *Significant ≈ 3 years)
- [ ] **QUAL-02**: Advisor can edit both education and experience textareas directly; empty values block the Finish button (validation)
- [ ] **QUAL-03**: Essential Qualifications section renders in the document preview with Education / Experience sub-labels in monospace caps; provenance tag "TBS Qualification Standard"

### DOC — Document composition

- [ ] **DOC-01**: Right-pane document preview fills as the advisor answers; sections appear in order — Position Identification, Position Overview, Key Responsibilities, Classification & Evaluation (if resolved), Defence Results Linkage (if selected), Essential Qualifications (if visited)
- [ ] **DOC-02**: Position Overview paragraph is composed from answers — "Located within {branch}, and reporting to the {reports}, the {title} {summary-lowercased}." — plus a supervises sentence mapped from the supervises choice
- [ ] **DOC-03**: Unfilled sections show ghost shimmer lines (3 lines for prose, 2 lines for duties) with a hint note ("Your responsibilities will appear here, formally worded."); sections appear as soon as the advisor starts typing
- [ ] **DOC-04**: In review state, each section header is clickable to jump back to the corresponding step; outside review, sections are non-interactive so the advisor can read without accidentally editing
- [ ] **DOC-05**: Document footer carries a "Every element is traceable to its source" label and provenance tags (NOC 2021, EC JES 2017, TBS OG Definitions, DND DRF, TBS Qualification Standard, Advisor-added); tag list updates as sections populate

### EXP — Export

- [ ] **EXP-01**: Advisor can export the assembled work description to a .docx via docxtpl (Pydantic-driven context). Provenance tags appear as citations; source data hashes appear in a version manifest section. Mirrors v1.0's TBS WD template pattern. PDF export and clipboard copy are deferred to v2.1+.

### API — Backend JSON service

- [ ] **API-01**: FastAPI app with Pydantic v2 models for WorkDescription, DraftDuty, Classification, JESFactor, QualificationStandard. JSON endpoints serve canonical data and accept WD submissions from the React SPA
- [ ] **API-02**: WD CRUD endpoints: POST /api/wd (create WD from answers), GET /api/wd/{id} (load WD), PATCH /api/wd/{id} (update draft), POST /api/wd/{id}/export (render DOCX)
- [ ] **API-03**: Canonical data endpoints: GET /api/work-types (EC/FI/IT/AS/EN list), GET /api/duties (7 suggested duties), GET /api/quals/default (EC-05 default quals text). Static curated data exposed as JSON
- [ ] **API-04**: POST /api/classify (work-type + 3 scope answers → {code, group, level, points, factors, rationale, confidence}) — server-side mirror of the React computeClassification function; used to validate the client-side result and to drive the export
- [ ] **API-05**: SQLite (single-file) storage for WD records and audit log. No sqlite-vec, no FTS5; v2.0 is single-user local app

### FE — Frontend SPA

- [ ] **FE-01**: React 18 SPA (no SSR) built with Vite for fast dev + build. Multi-file structure mirrors the prototype: app.jsx, data.jsx, conversation.jsx, document.jsx, components.jsx, styles.css
- [ ] **FE-02**: Vite dev server proxies /api to FastAPI on a separate port (e.g. 8000). Production build emits static files in dist/ that FastAPI serves
- [ ] **FE-03**: Brand styling: Hanken Grotesk (UI), Spectral (body prose), Spline Sans Mono (eyebrow / labels). Layered CSS in styles.css, scoped to .app, .convo, .preview, .doc, .ask, .scale, .choices, .duties, .quals, .drf, .jes, .prov. Visual fidelity to the prototype is required
- [ ] **FE-04**: Client-side state: record (committed answers), answers (per-step), stepIndex, draft (in-progress answer), reviewing, editingReturn, flashes (for fresh-section animations). useState + useMemo is sufficient; no Redux/Zustand
- [ ] **FE-05**: Persist draft WD to localStorage on every step commit. On reload, restore the most recent in-progress WD. Provides crash-recovery for the single-user local app

## Future Requirements (v2.1+)

### DRF — DND Departmental Results Framework integration

- **DRF-01**: Hardcoded 6-row dataset matching the prototype: Operations, Ready Forces, Defence Team, Sustainable Bases (recommended), Procurement of Capabilities, Future Force Design. Each row has CR, result statement, and 1–3 indicators
- **DRF-02**: Single-select choice cards with icon, CR title, result description, and "suggested" pill on the recommended row
- **DRF-03**: Defence Results Linkage section in the document preview: CR title, result statement, bulleted indicators. Provenance tag "DND Departmental Results Framework"

### EXP — Additional export formats

- **EXP-02**: PDF export — render the assembled WD to a .pdf. WeasyPrint is the candidate; ARM64 Pango/Cairo feasibility must be verified on Jane. Fallback options: docx2pdf (Microsoft Word dependency) or a JS-side renderer (jsPDF / pdfmake)
- **EXP-03**: Clipboard copy — copy the WD as plain text or markdown to the system clipboard. Lightweight path independent of the DOCX/PDF render
- **EXP-04**: Review-state checklist — done-card with a checklist of completion criteria (position identified, classified, N duties, DRF linked, qualifications reviewed) and the 3 export buttons in a single review pane

## Out of Scope

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
| WeasyPrint PDF export on Jane | TBD — feasibility check is v2.1+ work; the v2.0 build will not assume WeasyPrint on ARM64 |
| v1.0-drafted v2 candidates (QUAL-01 dataset-driven, CA-02/03, JES-02/03/04, EXP-02/03, MAP-03, JD-05) | Dropped — drafted for the v1.0 wizard; the conversational design has different priorities. Carrying them forward would be a cargo-cult |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| API-01 | Phase 10 | Pending |
| API-05 | Phase 10 | Pending |
| FE-02 | Phase 10 | Pending |
| FE-01 | Phase 11 | Pending |
| FE-03 | Phase 11 | Pending |
| FE-04 | Phase 11 | Pending |
| FE-05 | Phase 11 | Pending |
| CONVO-01 | Phase 12 | Pending |
| CONVO-02 | Phase 12 | Pending |
| CONVO-03 | Phase 12 | Pending |
| CONVO-04 | Phase 12 | Pending |
| CONVO-05 | Phase 12 | Pending |
| DOC-01 | Phase 13 | Pending |
| DOC-02 | Phase 13 | Pending |
| DOC-03 | Phase 13 | Pending |
| DOC-04 | Phase 13 | Pending |
| DOC-05 | Phase 13 | Pending |
| CLASS-01 | Phase 14 | Pending |
| CLASS-02 | Phase 14 | Pending |
| CLASS-03 | Phase 14 | Pending |
| CLASS-04 | Phase 14 | Pending |
| CLASS-05 | Phase 14 | Pending |
| JES-01 | Phase 15 | Pending |
| JES-02 | Phase 15 | Pending |
| JES-03 | Phase 15 | Pending |
| JES-04 | Phase 15 | Pending |
| DUTY-01 | Phase 16 | Pending |
| DUTY-02 | Phase 16 | Pending |
| DUTY-03 | Phase 16 | Pending |
| DUTY-04 | Phase 16 | Pending |
| DUTY-05 | Phase 16 | Pending |
| QUAL-01 | Phase 17 | Pending |
| QUAL-02 | Phase 17 | Pending |
| QUAL-03 | Phase 17 | Pending |
| API-02 | Phase 18 | Pending |
| API-03 | Phase 18 | Pending |
| API-04 | Phase 18 | Pending |
| EXP-01 | Phase 19 | Pending |

**Coverage:**
- v2 requirements: 38 total
- Mapped to phases: 38
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-03 for v2.0 "Guided Conversation"*
*Last updated: 2026-06-03 after roadmap creation*
