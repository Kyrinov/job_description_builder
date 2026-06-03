# Requirements: JD Builder

**Defined:** 2026-06-03
**Revised:** 2026-06-03 — v2.0 replanned; original Phases 11–19 scrapped; real v2.0 built on v1.0 data engine
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

v2.0 ("Real Guided Conversation") ports v1.0's production NOC + OG classification + JES engine into a
conversational React SPA, fixes the OG levels data gap, adds a Socratic question bank, CAF rank context,
manager amendment space, and job poster generation. The Claude Design prototype's visual design and
conversation flow are preserved; its hardcoded work-type picker and simplified classification are replaced.

### DATA — Data correctness

- [ ] **DATA-01**: System encodes correct OG level ranges for all groups extracted from `data/rates_of_pay/`
  (EC: 01–08, IT: 01–05, FI: 01–04, AS: 01–08 and all other active groups); the `OG_LEVELS` dict in
  `app/ai/og_ranking.py` is replaced with the corrected full set derived from the rates CSVs
- [ ] **DATA-02**: System encodes a CAF rank→civilian OG equivalence table (hardcoded constant) derived by
  pay-band comparison from `data/CAF pay grades`; table maps NCM and officer ranks to approximate civilian
  OG-level ranges; flagged "advisory — not authoritative" in all surfaces

### QUES — Socratic question bank

- [ ] **QUES-01**: A hardcoded question bank artifact (JSON or Python constant) encodes interview questions
  derived from OG definition signals, JES factor descriptors, and NOC TEER levels; covers AS, EC, IT, FI
  work types at minimum; each question entry includes: question text, answer options, and classification
  signal mapping (OG candidate codes + JES factor hints)
- [ ] **QUES-02**: The question bank enforces the Socratic constraint: the manager never selects an OG
  directly — they answer work-description questions; signals from answers are accumulated and matched to
  OG candidates by the classification engine
- [ ] **QUES-03**: Question bank entries drive the classification-focused steps in the conversation flow;
  the CONVO "Work Type" phase renders question bank entries and routes answers to the NOC pipeline and
  OG classifier

### NOC — NL→NOC pipeline

- [ ] **NOC-01**: Three-stage NL→NOC pipeline runs in the FastAPI backend: FTS5 shortlist → embedding
  rerank → LLM justification; ported from `app/services/noc_mapper.py` and its dependencies
  (sqlite-vec, Ollama); exposed via POST `/api/noc/map`
- [ ] **NOC-02**: NOC candidates returned include code, title, TEER level, and verbatim duty matches from
  the FTS5-indexed NOC 2021 dataset; the SPA displays candidates and waits for advisor confirmation
  before classification proceeds

### CONVO — Conversational UX

- [ ] **CONVO-01**: Advisor progresses through a 6-phase interview (Role → Work Type → Classification →
  Duties → Qualifications → Review); the Work Type and Classification phases use question bank-driven
  steps rather than fixed work-type choice cards
- [ ] **CONVO-02**: Advisor can click any answered exchange in the transcript to revisit and re-answer that
  step without losing prior answers; re-answering a classification step re-runs the downstream pipeline
- [ ] **CONVO-03**: Conversation pane header shows 6 phase chips with active / done / pending states as
  the advisor advances
- [ ] **CONVO-04**: Each step renders the appropriate input control: text input, textarea, choice cards
  with icons, duty builder, qualification editor, NOC candidate confirmation card, OG candidate
  confirmation card
- [ ] **CONVO-05**: Advisor can press Enter to continue (Cmd/Ctrl+Enter for textarea), use Back button on
  step 2+; active question auto-scrolls into view

### CLASS — OG classification

- [ ] **CLASS-01**: Evidence-based OG classification: confirmed NOC code + work description → top-3 OG
  candidates with verbatim TBS inclusions/exclusions and confidence scores; ported from
  `app/services/og_classifier.py` and `app/ai/og_ranking.py`
- [ ] **CLASS-02**: AS/EC disambiguation surfaced from `data/directive_on_classification.txt` verbatim
  citations when both AS and EC appear in the top-3 candidates; disambiguation rationale displayed to
  the advisor
- [ ] **CLASS-03**: Level determination: after OG is confirmed, advisor selects a level from the confirmed
  OG's corrected level range (DATA-01); level selection rendered as a choice step in the conversation
- [ ] **CLASS-04**: Hard gate: JD generation blocked until OG + level are both confirmed and stored in the
  WorkDescription model; the document preview shows a "Classification pending" state until confirmed
- [ ] **CLASS-05**: CAF rank context: when the position reports to a military supervisor (captured in org
  context step), the system displays the approximate civilian OG equivalent from DATA-02 beside the
  reporting relationship in the conversation; labelled "advisory — not authoritative"

### JES — Job Evaluation Standard

- [ ] **JES-01**: Per-factor JES scoring for EC group (9 elements verbatim from EC JES 2017): Decision
  making, Leadership & operational mgmt, Communication, Knowledge of specialized fields, Contextual
  knowledge, Research & analysis, Physical effort, Sensory effort, Working conditions; ported from
  `app/services/jes_service.py` with instructor retry wrapper (max 3 retries per factor)
- [ ] **JES-02**: Per-factor retry + advisor override: if a factor score fails after 3 retries, advisor
  can manually enter a degree value (1–N per factor scale); override stored as an audit_log entry with
  type="jes_override"; ported from v1.0 Phase 8.1
- [ ] **JES-03**: Approximate point totals for non-EC groups (FI, IT, AS, EN) at the confirmed level;
  displayed as a single totals line with the applicable JES standard name cited (e.g. "CT JES 2023" for
  FI, "IT JES" for IT, "UCS" for AS)
- [ ] **JES-04**: JES scorecard rendered in the Classification & Evaluation section of the live document
  preview: per-factor rows (element name, degree, points) for EC groups; single totals line for non-EC

### JD — Job description composition

- [ ] **JD-01**: Duties are verbatim NOC text selected from the FTS5-indexed NOC 2021 dataset; no
  free-form LLM duty generation; the duty builder step presents FTS5 matches for the confirmed NOC code
- [ ] **JD-02**: Every selected duty carries a structured ProvenanceTag (source type: "NOC", NOC code,
  section reference, content hash of the source record)
- [ ] **JD-03**: Advisor-added duties (free-text, not from NOC index) are tagged source type: "advisor-added"
  in the WorkDescription model and rendered with a distinct visual marker in the document preview
- [ ] **JD-04**: Orphan statement check runs at review time: flags any duty whose verb-mapped action
  contradicts the confirmed OG's functional authority inclusions/exclusions; flagged duties shown with a
  warning indicator and rationale citation

### DOC — Document composition

- [ ] **DOC-01**: Live document preview fills as advisor answers; sections appear in order — Position
  Identification, Position Overview, Key Responsibilities, Classification & Evaluation, Essential
  Qualifications; Defence Results Linkage section deferred to v2.1
- [ ] **DOC-02**: Position Overview paragraph is composed from answers: "Located within {branch}, and
  reporting to the {reports}, the {title} {summary-lowercased}." plus a supervises sentence mapped
  from the supervises answer
- [ ] **DOC-03**: Unfilled sections show ghost shimmer placeholders (3 shimmer lines for prose, 2 for
  duties) with a hint note; sections become active as soon as the advisor starts the relevant step
- [ ] **DOC-04**: In review state, each section header is clickable to jump back to the corresponding
  conversation step; sections are non-interactive outside review state
- [ ] **DOC-05**: Document footer shows provenance tags (NOC 2021, EC JES 2017, TBS OG Definitions,
  TBS Qualification Standard, Advisor-added) updating live as sections populate

### QUAL — Qualification standard

- [ ] **QUAL-01**: System pre-fills the Essential Qualifications section with a default text matched to
  the confirmed OG: EC default (degree in environmental science / economics / public policy; significant
  experience in policy/analysis); AS default; IT default; FI default — drawn from TBS Qualification
  Standards reference text
- [ ] **QUAL-02**: Both education and experience textareas are directly editable; empty values in either
  field block the Finish button (inline validation)
- [ ] **QUAL-03**: Essential Qualifications section renders in the document preview with Education /
  Experience sub-labels in monospace caps; provenance tag "TBS Qualification Standard"

### AMEND — Manager amendment space

- [ ] **AMEND-01**: In review state, advisor can add a manager amendment note per JD section (section
  reference + free-text comment); each note is stored as an audit_log entry with
  type="manager_amendment", section, comment, and timestamp
- [ ] **AMEND-02**: Manager amendments render in the DOCX export as an appendix section ("Manager
  Amendments for Review") listing each note with its section reference and a provenance tag
  "Manager-proposed — pending advisor ratification"

### EXP — Export

- [ ] **EXP-01**: Advisor can export the completed WD to a `.docx` via docxtpl (TBS WD template);
  provenance tags appear as citations; source data hashes appear in a version manifest section;
  template is a committed binary artifact with a reproducible build script; mirrors v1.0 Phase 8 pattern
- [ ] **EXP-02**: Advisor can export a job poster to a second `.docx` via a separate docxtpl template;
  poster includes bilingual headers, OG/level, key qualifications, and 3–5 duties; accessible via
  POST `/api/wd/{id}/export/poster`
- [ ] **EXP-03**: PDF export via WeasyPrint (ARM64 Pango/Cairo feasibility confirmed on Jane before
  implementation); if ARM64 system libs are not available, the endpoint returns 501 Not Implemented
  with a diagnostic message

### API — Backend JSON service

- [x] **API-01**: FastAPI app with Pydantic v2 models for WorkDescription, DraftDuty, Classification,
  JESFactor, QualificationStandard — validated in Phase 10
- [ ] **API-02**: WD CRUD: POST `/api/wd` (create WD from answers), GET `/api/wd/{id}` (load WD),
  PATCH `/api/wd/{id}` (update draft)
- [ ] **API-03**: Canonical data endpoints: GET `/api/quals/default?og_code=EC` (OG-matched qual standard
  text); GET `/api/og/definitions?og_code=EC` (OG definition, inclusions, exclusions for display)
- [ ] **API-04**: POST `/api/noc/map` — accepts free-text work description; returns top-3 NOC candidates
  (code, title, TEER, verbatim duty matches) via three-stage FTS5 → embedding rerank → LLM pipeline
- [x] **API-05**: SQLite single-file at `DB_PATH` with `work_descriptions` and `audit_log` tables;
  idempotent `create_schema` on lifespan startup — validated in Phase 10
- [ ] **API-06**: POST `/api/og/classify` — accepts confirmed NOC code + work description; returns
  top-3 OG candidates with verbatim rationale and confidence scores; includes AS/EC disambiguation
  when applicable
- [ ] **API-07**: POST `/api/jes/score` — accepts OG code + level + duties; returns JES factor scorecard
  (EC: per-factor with degrees and points; non-EC: single totals line with JES standard name)
- [ ] **API-08**: POST `/api/wd/{id}/export/docx` — renders the TBS WD DOCX template from saved WD data;
  returns `.docx` file
- [ ] **API-09**: POST `/api/wd/{id}/export/poster` — renders the job poster DOCX template from saved
  WD data; returns `.docx` file

### FE — Frontend SPA

- [ ] **FE-01**: React 18 SPA built with Vite; multi-file structure mirrors the Claude Design prototype:
  `app.jsx`, `data.jsx`, `conversation.jsx`, `document.jsx`, `components.jsx`, `styles.css`
- [x] **FE-02**: Vite dev server proxies `/api/*` to FastAPI on a separate port with `changeOrigin: true`
  — validated in Phase 10
- [ ] **FE-03**: Brand styling: Hanken Grotesk (UI text), Spectral (body prose), Spline Sans Mono
  (eyebrow / labels); layered CSS scoped to `.app`, `.convo`, `.preview`, `.doc`, etc.; visual fidelity
  to the Claude Design prototype is required
- [ ] **FE-04**: Client-side state: `useState` + `useMemo` only; record (committed answers), answers
  (per-step), stepIndex, draft, reviewing, editingReturn, flashes; no Redux/Zustand
- [ ] **FE-05**: Persist draft WD to localStorage on every step commit; restore most recent in-progress
  WD on reload; provides crash-recovery for the single-user local app

## Future Requirements (v2.1+)

### DRF — DND Departmental Results Framework integration

- **DRF-01**: Hardcoded 6-row DRF dataset (from `data/departmental_results_framework/dnd_drf_dataset.csv`):
  Operations, Ready Forces, Defence Team, Sustainable Bases (recommended), Procurement of Capabilities,
  Future Force Design; each row has CR title, result statement, and 1–3 indicators
- **DRF-02**: Single-select DRF choice cards in the conversation flow (icon, CR title, result description,
  "suggested" pill on the recommended row)
- **DRF-03**: Defence Results Linkage section in the document preview and DOCX export: CR title, result
  statement, bulleted indicators; provenance tag "DND Departmental Results Framework"

### EXP — Additional export formats

- **EXP-04**: Clipboard copy — copy the WD as plain text or markdown to the system clipboard

### AMEND — Enhanced amendment workflow

- **AMEND-03**: Manager-facing review link — generate a time-limited read-only URL for the manager to
  review the WD and submit amendments directly (requires multi-user/auth infrastructure)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Manager-facing UI (separate login) | Single-user advisor app for v2.0; multi-role UX with auth is a later milestone |
| Multi-user / multi-tenant deployment | Single-user local app; auth and isolation deferred |
| OpenAI or external LLM as primary | Classification is evidence-based; LLM used only for NOC justification (local via Ollama) |
| Live OASIS scraping as primary data source | v2.0 uses curated data files in `data/`; live scraping is unreliable |
| Real-time CA update sync | Static curated dataset; manual update only |
| Staffing / competition workflow | JD builder only; downstream competition tooling is separate |
| Pay band calculation | Rates of pay are reference data only |
| Bilingualism enforcement | Flag only; blocking on French translation is out of scope |
| Grievance management workflow | This tool creates defensible WDs; it does not manage disputes |
| DND SJD library feature | `data/SJD Examples.txt` is reference only — used to understand JD structure, not to build a lookup UI |
| DRF integration | Deferred to v2.1 (see Future Requirements) |
| v1.0-drafted candidates (QUAL-01 dataset-driven, CA-02/03, JES-02/03/04, EXP-02/03, MAP-03, JD-05) | Drafted for the v1.0 wizard; the conversational design has different priorities |
| Original v2.0 Phases 11–19 (scrapped 2026-06-03) | Built around hardcoded work-type picker and simplified scope-question classifier; replaced by v1.0 engine |

## Traceability

*To be filled in by gsd-roadmapper after roadmap creation.*

| Requirement | Phase | Status |
|-------------|-------|--------|
| API-01 | Phase 10 | Complete |
| API-05 | Phase 10 | Complete |
| FE-02 | Phase 10 | Complete |

**Coverage:**
- v2 requirements: 44 total (3 validated in Phase 10, 41 active)
- Mapped to phases: TBD (roadmapper)
- Unmapped: TBD

---
*Requirements revised: 2026-06-03 — v2.0 replanned from Phases 11–19 scrapped plan*
