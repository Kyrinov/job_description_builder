# Roadmap: JD Builder

## Milestones

- ✅ **v1.0 MVP** — Phases 1–9 incl. 8.1 (shipped 2026-06-03)
- 🚀 **v2.0 Real Guided Conversation** — Phases 10–20 (in progress, 2026-06-03)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1–9 incl. 8.1) — SHIPPED 2026-06-03</summary>

- [x] Phase 1: Project Foundation (3/3 plans) — completed 2026-05-28
- [x] Phase 2: NOC Data Pipeline (4/4 plans) — completed 2026-05-28
- [x] Phase 3: CA + JES Data Pipeline (4/4 plans) — completed 2026-06-01
- [x] Phase 4: NL→NOC Mapping (4/4 plans) — completed 2026-06-02
- [x] Phase 5: OG Classification (4/4 plans) — completed 2026-06-02
- [x] Phase 6: JD Generation (4/4 plans) — completed 2026-06-02
- [x] Phase 7: JES Scoring (4/4 plans) — completed 2026-06-02
- [x] Phase 8: Export (4/4 plans) — completed 2026-06-02
- [x] Phase 8.1: JES Advisor Override & Per-Factor Retry (3/3 plans) — completed 2026-06-03
- [x] Phase 9: DND DRF Integration (4/4 plans) — completed 2026-06-03

Full phase details: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

</details>

### 🚀 v2.0 Real Guided Conversation (Phases 10–20)

v2.0 ports v1.0's production NOC + OG classification + JES engine into a conversational React SPA backed by corrected authoritative data. The Claude Design prototype at `Job Description Builder/jd-builder/` is the UX source of truth; its hardcoded work-type picker and simplified classification are replaced by v1.0's evidence-based engine. Original Phases 11–19 scrapped 2026-06-03; new phases 11–20 defined below.

- [x] **Phase 10: Project Scaffold** — FastAPI skeleton + Pydantic v2 models + SQLite schema + Vite + React 18 project + Vite proxy. (API-01, API-05, FE-02) (completed 2026-06-03)
- [x] **Phase 11: Data Foundation** — Fix OG level ranges from rates_of_pay CSVs; encode CAF rank→civilian OG equivalence table. (DATA-01, DATA-02) (completed 2026-06-04)
- [x] **Phase 12: Socratic Question Bank** — Design and encode question bank artifact (JSON/Python constant) driving Socratic classification; each entry maps to OG candidates + JES factor hints. (QUES-01, QUES-02, QUES-03) (completed 2026-06-04)
- [x] **Phase 13: Frontend SPA Shell** — Port 5 JSX files + styles.css into Vite; brand typography; useState/useMemo architecture; localStorage crash-recovery. (FE-01, FE-03, FE-04, FE-05) (completed 2026-06-04)
- [x] **Phase 14: NOC Pipeline** — Port three-stage NL→NOC pipeline (FTS5 → embedding rerank → LLM justification) into FastAPI backend; expose POST `/api/noc/map`; display candidates + advisor confirmation. (NOC-01, NOC-02, API-04) (completed 2026-06-04)
- [x] **Phase 15: Conversational UX** — 6-phase interview with question bank-driven classification and duty steps; revisit, phase chips, per-step input controls, keyboard shortcuts; WD CRUD persistence. (CONVO-01, CONVO-02, CONVO-03, CONVO-04, CONVO-05, API-02) (completed 2026-06-05)
- [x] **Phase 16: OG Classification** — Evidence-based OG classification from confirmed NOC + work description; AS/EC disambiguation; level selection from corrected OG ranges; hard gate; CAF rank advisory; canonical data endpoints. (CLASS-01, CLASS-02, CLASS-03, CLASS-04, CLASS-05, API-06, API-03) (completed 2026-06-05)
- [ ] **Phase 17: JES Scoring** — EC JES 2017 9-factor scoring with per-factor retry + advisor override; non-EC approximate totals; JES scorecard in live preview; POST `/api/jes/score`. (JES-01, JES-02, JES-03, JES-04, API-07)
- [ ] **Phase 18: JD Composition & Live Preview** — Verbatim NOC duty selection with provenance; advisor-added duties; orphan check; live document preview with ghost placeholders, composed overview, section click-to-edit, provenance footer. (JD-01, JD-02, JD-03, JD-04, DOC-01, DOC-02, DOC-03, DOC-04, DOC-05)
- [ ] **Phase 19: Qualifications & Amendments** — OG-matched qual standard defaults; editable textareas with validation; EQ section render; manager amendment notes per section; DOCX appendix for amendments. (QUAL-01, QUAL-02, QUAL-03, AMEND-01, AMEND-02)
- [ ] **Phase 20: Export** — DOCX WD export (docxtpl, provenance citations, version manifest); job poster DOCX; PDF export via WeasyPrint (ARM64 gate); POST `/api/wd/{id}/export/docx` + `/poster`. (EXP-01, EXP-02, EXP-03, API-08, API-09)

**Coverage:** 52/52 v2.0 requirements mapped · 11 phases (10–20) · 0 unmapped · 0 orphans

---

## Phase Details

### Phase 10: Project Scaffold

**Goal:** Developer can run both the FastAPI backend and the Vite dev server, with the SPA loading and proxying API calls to the backend; SQLite schema is in place.

**Depends on:** Nothing (first v2.0 phase)

**Requirements:** API-01, API-05, FE-02

**Success criteria:**
1. Developer can start the FastAPI app with `uvicorn` and see `/api/health` return 200 OK
2. Developer can start the Vite dev server with `npm run dev` and see the SPA load at `localhost:5173` with a placeholder page
3. Vite proxies `/api/*` requests to FastAPI on a configured port with `changeOrigin: true`
4. SQLite single-file database is created on app startup with the `work_descriptions` and `audit_log` tables present
5. Pydantic v2 models are defined: `WorkDescription`, `DraftDuty`, `Classification`, `JESFactor`, `QualificationStandard`

**Plans:** 4/4 plans complete

Plans:
- [x] 10-01-PLAN.md — Backend Wave 0: project scaffold + test stubs (Wave 1)
- [x] 10-02-PLAN.md — Backend impl: Settings + SQLite + 5 Pydantic models (Wave 2)
- [x] 10-03-PLAN.md — Frontend scaffold: Vite + React 18 placeholder + /api proxy (Wave 1)
- [x] 10-04-PLAN.md — Integration: main.py + /api/health + verify.sh (Wave 3)

---

### Phase 11: Data Foundation

**Goal:** The system encodes correct OG level ranges for all active groups and a CAF rank-to-civilian equivalence table, so every downstream classification and advisory display has accurate authoritative data.

**Depends on:** Phase 10

**Requirements:** DATA-01, DATA-02

**Success criteria:**
1. The `OG_LEVELS` constant covers all active groups with correct min–max level ranges derived from `data/rates_of_pay/` CSVs (e.g. EC: 01–08, IT: 01–05, FI: 01–04, AS: 01–08)
2. A hardcoded CAF rank→civilian OG equivalence table maps NCM and officer ranks to approximate civilian OG-level ranges using pay-band comparison from `data/CAF pay grades`
3. Both constants are importable from a single module (e.g. `app/data/constants.py`); unit tests confirm the shape and spot-check key entries against the source files
4. The CAF table is annotated "advisory — not authoritative" in code comments and in any surface that displays it

**Plans:** 2/2 plans complete

Plans:
- [x] 11-01-PLAN.md — Wave 0 test stubs + package marker + OG_LEVELS constant + v1.0 og_ranking.py fix (Wave 1)
- [x] 11-02-PLAN.md — CAF_RANK_OG_EQUIVALENCE table (verify/populate) + DATA-02 tests GREEN (Wave 1)

---

### Phase 12: Socratic Question Bank

**Goal:** A hardcoded question bank artifact encodes interview questions derived from OG definitions, JES factors, and NOC TEER levels; the bank enforces the Socratic constraint that managers never select OG directly; entries drive the classification steps in the conversation flow.

**Depends on:** Phase 11 (DATA-01 provides correct OG level ranges; question bank references OG candidates)

**Requirements:** QUES-01, QUES-02, QUES-03

**Success criteria:**
1. The question bank artifact (JSON or Python constant) contains entries covering AS, EC, IT, and FI work types at minimum; each entry has: question text, answer options, and a classification signal mapping (OG candidate codes + JES factor hints)
2. No question entry asks the manager to name or select an OG group directly; all OG candidates are derived by accumulating answer signals through the classification engine
3. A standalone test or script imports the question bank and validates structure: every entry has required keys; every OG candidate code in signal mappings exists in `OG_LEVELS`; every JES factor hint references a known factor name

**Plans:** 2/2 plans complete

Plans:
- [x] 12-01-PLAN.md — TDD stubs: test_question_bank.py (RED) + KNOWN_JES_FACTORS + QUESTION_BANK stub
- [x] 12-02-PLAN.md — Populate QUESTION_BANK (4 entries, all 9 tests GREEN)

---

### Phase 13: Frontend SPA Shell

**Goal:** The React 18 SPA is ported into the Vite project with brand typography, correct client-side state architecture, and localStorage crash-recovery; the full prototype structure is in place as a foundation for UX feature phases.

**Depends on:** Phase 10

**Requirements:** FE-01, FE-03, FE-04, FE-05

**Success criteria:**
1. `npm run build` produces a clean Vite production bundle in `dist/` with no TypeScript or ESLint errors
2. Multi-file structure mirrors the prototype: `app.jsx`, `data.jsx`, `conversation.jsx`, `document.jsx`, `components.jsx`, `styles.css` under `v2/frontend/src/`
3. Brand typography renders in the SPA: Hanken Grotesk (UI text), Spectral (body prose), Spline Sans Mono (eyebrow / labels); CSS is scoped to `.app`, `.convo`, `.preview`, `.doc` etc. matching the prototype
4. Client-side state uses `useState` + `useMemo` only — no Redux or Zustand; state shape includes `record`, `answers`, `stepIndex`, `draft`, `reviewing`, `editingReturn`, `flashes`
5. After answering several questions and refreshing the browser, the in-progress WD is restored from localStorage (draft persisted on every step commit)

**Plans:** 3/3 plans complete

Plans:
- [x] 13-01-PLAN.md — Wave 0: Vitest + jsdom setup + app.test.jsx stubs (FE-04, FE-05)
- [x] 13-02-PLAN.md — Wave 1: data.jsx + components.jsx + styles.css + index.html + main.jsx (FE-01, FE-03)
- [x] 13-03-PLAN.md — Wave 2: conversation.jsx + document.jsx + app.jsx + localStorage + tests GREEN (FE-01, FE-04, FE-05)

**UI hint**: yes

---

### Phase 14: NOC Pipeline

**Goal:** Advisor can submit a free-text work description and receive top-3 NOC candidates (code, title, TEER, verbatim duty matches) from the three-stage pipeline; confirming a candidate unblocks the classification step.

**Depends on:** Phase 11 (NOC data must be indexed), Phase 12 (question bank drives the work-type step that precedes NOC lookup)

**Requirements:** NOC-01, NOC-02, API-04

**Success criteria:**
1. `POST /api/noc/map` accepts a free-text work description and returns top-3 NOC candidates with code, title, TEER level, and verbatim duty matches from the FTS5-indexed NOC 2021 dataset
2. The three stages run in sequence: FTS5 shortlist → embedding rerank → LLM justification; each stage is traceable in the response (e.g. `stage` field or log line)
3. The SPA displays the NOC candidates as confirmation cards; the advisor selects one to confirm; the confirmed NOC code is stored in the `WorkDescription` model before classification proceeds
4. The pipeline is ported from `app/services/noc_mapper.py` and its sqlite-vec + Ollama dependencies; existing unit tests from v1.0 are adapted and pass in the v2.0 test suite

**Plans:** 4/4 plans complete

Plans:
- [x] 14-01-PLAN.md — Wave 0: test infrastructure stubs + noc_mapping_db fixture + requirements.txt deps (completed 2026-06-04)
- [x] 14-02-PLAN.md — Wave 2: noc_ranking.py + noc_mapper.py port + Settings/db/NOCMatch extensions (completed 2026-06-04)
- [x] 14-03-PLAN.md — Wave 2: POST /api/noc/map route + request/response models (completed 2026-06-04)
- [x] 14-04-PLAN.md — Wave 3: NocConfirmList frontend component + UAT checkpoint (completed 2026-06-04)

---

### Phase 15: Conversational UX

**Goal:** Advisor can complete the full 6-phase interview end-to-end using question bank-driven steps, revisit any prior answer, and have each step's response persisted to the backend.

**Depends on:** Phase 12 (question bank), Phase 13 (SPA shell), Phase 14 (NOC pipeline for the Work Type phase)

**Requirements:** CONVO-01, CONVO-02, CONVO-03, CONVO-04, CONVO-05, API-02

**Success criteria:**
1. Advisor progresses through 6 phases (Role → Work Type → Classification → Duties → Qualifications → Review); the Work Type and Classification phases render question bank entries rather than fixed work-type choice cards
2. Clicking any answered exchange in the transcript scrolls back to that step and re-activates it; re-answering a classification step triggers re-run of the downstream NOC/OG pipeline without losing other answers
3. The conversation pane header shows 6 phase chips with active / done / pending states that update as the advisor advances
4. Each step renders the correct input control: text input, textarea, choice cards with icons, NOC candidate confirmation card, OG candidate confirmation card, duty builder, qualification editor
5. Pressing Enter on a text input submits; Cmd/Ctrl+Enter on a textarea submits; Back button is available on step 2+; the active question auto-scrolls into view
6. `POST /api/wd` creates a WD on first step commit; `PATCH /api/wd/{id}` updates it on each subsequent commit; `GET /api/wd/{id}` can restore an in-progress session

**Plans:** 4/4 plans complete

Plans:
- [x] 15-01-PLAN.md — Wave 1: Test stubs (RED) — test_wd.py + conversation.test.jsx
- [x] 15-02-PLAN.md — Wave 2: WD CRUD routes (POST/GET/PATCH /api/wd)
- [x] 15-03-PLAN.md — Wave 2: data.jsx QUESTION_BANK STEPS + PHASES + accumulateSignals
- [x] 15-04-PLAN.md — Wave 3: app.jsx + components.jsx wiring + UAT checkpoint

**UI hint**: yes

---

### Phase 16: OG Classification

**Goal:** After NOC is confirmed, the system returns top-3 OG candidates with verbatim rationale, surfaces AS/EC disambiguation when applicable, guides the advisor through level selection from the correct range, and hard-gates JD generation until OG + level are confirmed; CAF rank context displays as an advisory.

**Depends on:** Phase 14 (confirmed NOC code required), Phase 15 (OG classification step is embedded in the conversation flow)

**Requirements:** CLASS-01, CLASS-02, CLASS-03, CLASS-04, CLASS-05, API-06, API-03

**Success criteria:**
1. `POST /api/og/classify` accepts a confirmed NOC code + work description and returns top-3 OG candidates with verbatim TBS inclusions/exclusions and confidence scores; the SPA renders these as confirmation cards
2. When both AS and EC appear in the top-3, the disambiguation rationale from `data/directive_on_classification.txt` is displayed verbatim alongside the candidates
3. After the advisor confirms an OG group, a level-selection step renders the correct level range from DATA-01 (e.g. EC 01–08) as choice cards; the selected level is stored in `WorkDescription`
4. The document preview shows a "Classification pending" state until both OG group and level are confirmed; JD generation is blocked at the API layer (`CLASS-04` hard gate)
5. When the position reports to a military supervisor (captured in the org context step), the CAF rank equivalence from DATA-02 is displayed beside the reporting relationship with the label "advisory — not authoritative"
6. `GET /api/og/definitions?og_code=EC` returns the OG definition, inclusions, and exclusions for display; `GET /api/quals/default?og_code=EC` returns the OG-matched qualification standard text

**Plans:** 4/4 plans complete

Plans:
- [x] 16-01-PLAN.md — Wave 0: OG_DEFINITIONS + QUAL_STANDARDS + ASEC_DISAMBIGUATION constants + model extensions + test stubs RED
- [x] 16-02-PLAN.md — Wave 1: POST /api/og/classify + GET /api/og/definitions + GET /api/quals/default + classification_gate.py
- [x] 16-03-PLAN.md — Wave 2: OgConfirmList + OgLevelPicker components + data.jsx STEPS wiring + app.jsx OG pipeline
- [x] 16-04-PLAN.md — Wave 3: document.jsx Classification pending + CAF advisory + UAT checkpoint

**UI hint**: yes

---

### Phase 17: JES Scoring

**Goal:** After OG + level are confirmed, the Classification & Evaluation section renders a full JES scorecard — per-factor for EC groups, single totals line for non-EC groups — with per-factor retry and advisor override for failed factors.

**Depends on:** Phase 16 (confirmed OG + level required before JES scoring)

**Requirements:** JES-01, JES-02, JES-03, JES-04, API-07

**Success criteria:**
1. `POST /api/jes/score` accepts OG code + level + duties and returns the JES scorecard; for EC the response includes all 9 factor rows (element name, degree, points, category); for non-EC it returns a single totals line with the applicable JES standard name cited (e.g. "CT JES 2023" for FI, "IT JES" for IT, "UCS" for AS)
2. EC JES 2017 scoring covers all 9 elements: Decision making, Leadership & operational mgmt, Communication, Knowledge of specialized fields, Contextual knowledge, Research & analysis, Physical effort, Sensory effort, Working conditions; degree vectors are verified against the 2017 published standard for at least EC-04, EC-05, EC-06
3. When a factor score fails after 3 retries (instructor retry wrapper), the SPA prompts the advisor to manually enter a degree value (1–N per factor scale); the override is stored as an `audit_log` entry with `type="jes_override"`
4. The Classification & Evaluation section of the live document preview renders per-factor rows (name, D{degree}, points) and a totals row for EC; non-EC renders a single totals line; the scorecard populates as soon as the classification step is confirmed

**Plans:** 4 plans

Plans:
- [ ] 17-01-PLAN.md — Wave 0: JES constants + model extensions + RED test stubs
- [ ] 17-02-PLAN.md — Wave 2: ai/jes_scoring.py + services/jes_service.py + POST /api/jes/score + POST /api/jes/override
- [ ] 17-03-PLAN.md — Wave 3: app.jsx JES trigger + document.jsx Section 4 scorecard + ClassBlock tests GREEN
- [ ] 17-04-PLAN.md — Wave 4: full suite green gate + UAT checkpoint

**UI hint**: yes

---

### Phase 18: JD Composition & Live Preview

**Goal:** Advisor selects verbatim NOC duties, adds their own, triggers the orphan check at review, and sees a live document preview fill section by section with ghost placeholders, a composed overview, clickable section headers, and a provenance footer.

**Depends on:** Phase 14 (confirmed NOC code drives duty FTS5 lookup), Phase 15 (duty builder is a step in the conversation flow), Phase 16 (confirmed OG needed for orphan check functional authority)

**Requirements:** JD-01, JD-02, JD-03, JD-04, DOC-01, DOC-02, DOC-03, DOC-04, DOC-05

**Success criteria:**
1. The duty builder step presents FTS5 matches for the confirmed NOC code as selectable cards; selected duties are verbatim NOC text; no free-form LLM duty generation
2. Every selected duty carries a structured `ProvenanceTag` with source type "NOC", NOC code, section reference, and content hash; advisor-added duties carry source type "advisor-added" and are rendered with a distinct visual marker in the document preview
3. At review time, the orphan statement check flags any duty whose verb-mapped action contradicts the confirmed OG's functional authority inclusions/exclusions; flagged duties show a warning indicator with a citation rationale
4. The live document preview shows 5 sections in order: Position Identification, Position Overview, Key Responsibilities, Classification & Evaluation, Essential Qualifications; each section appears as soon as the advisor starts the relevant step
5. Unfilled sections show ghost shimmer placeholders (3 lines for prose, 2 for duties) with a hint note; the Position Overview paragraph is composed from answers as "Located within {branch}, and reporting to the {reports}, the {title} {summary-lowercased}." plus a supervises sentence
6. In review state, each section header is clickable to jump back to the corresponding conversation step; outside review state sections are non-interactive; the document footer shows provenance tags updating live as sections populate

**Plans:** TBD

**UI hint**: yes

---

### Phase 19: Qualifications & Amendments

**Goal:** The Essential Qualifications section is pre-filled with OG-matched defaults and is directly editable; in review state the advisor can attach manager amendment notes per section that are stored in the audit log and included as a DOCX appendix.

**Depends on:** Phase 16 (confirmed OG drives qual standard defaults), Phase 18 (amendment notes are per JD section; review state must exist)

**Requirements:** QUAL-01, QUAL-02, QUAL-03, AMEND-01, AMEND-02

**Success criteria:**
1. The qualification step pre-fills education and experience textareas with defaults matched to the confirmed OG (EC default: degree in environmental science / economics / public policy; AS default; IT default; FI default — from TBS Qualification Standards reference text)
2. Both textareas are directly editable; submitting the step with either field empty is blocked with inline validation; the Finish button remains disabled until both fields are non-empty
3. The Essential Qualifications section renders in the document preview with Education / Experience sub-labels in monospace caps and a provenance tag "TBS Qualification Standard"
4. In review state, the advisor can open an amendment note panel for any JD section, enter a free-text comment, and save it; each saved note is stored as an `audit_log` entry with `type="manager_amendment"`, `section`, `comment`, and `timestamp`
5. When a WD with amendment notes is exported to DOCX, an appendix section "Manager Amendments for Review" lists each note with its section reference and a provenance tag "Manager-proposed — pending advisor ratification"

**Plans:** TBD

**UI hint**: yes

---

### Phase 20: Export

**Goal:** Advisor can download the completed WD as a DOCX with full provenance and version manifest, download a job poster DOCX, and export to PDF (with a graceful 501 fallback if ARM64 system libs are absent).

**Depends on:** Phase 17 (JES scorecard in DOCX), Phase 18 (duties + provenance in DOCX), Phase 19 (qualifications + amendment appendix in DOCX)

**Requirements:** EXP-01, EXP-02, EXP-03, API-08, API-09

**Success criteria:**
1. `POST /api/wd/{id}/export/docx` renders the TBS WD docxtpl template from saved WD data and returns a `.docx` file; provenance tags appear as inline citations; source data hashes appear in a version manifest section at the end of the document
2. The DOCX template follows the TBS Work Description format (D-04) and is committed as a binary artifact with a reproducible build script that self-verifies via `DocxTemplate.get_undeclared_template_variables()`; the pattern mirrors v1.0 Phase 8
3. `POST /api/wd/{id}/export/poster` returns a second `.docx` via a separate docxtpl template; the poster includes bilingual headers, OG/level, key qualifications, and 3–5 duties
4. `POST /api/wd/{id}/export/pdf` (or equivalent endpoint) renders to PDF via WeasyPrint after confirming ARM64 Pango/Cairo system libs are present on Jane; if libs are absent the endpoint returns 501 Not Implemented with a diagnostic message
5. The advisor can trigger all three export formats from the review screen in the SPA; each download starts immediately with the correct MIME type and filename

**Plans:** TBD

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Project Foundation | v1.0 | 3/3 | Complete | 2026-05-28 |
| 2. NOC Data Pipeline | v1.0 | 4/4 | Complete | 2026-05-28 |
| 3. CA + JES Data Pipeline | v1.0 | 4/4 | Complete | 2026-06-01 |
| 4. NL→NOC Mapping | v1.0 | 4/4 | Complete | 2026-06-02 |
| 5. OG Classification | v1.0 | 4/4 | Complete | 2026-06-02 |
| 6. JD Generation | v1.0 | 4/4 | Complete | 2026-06-02 |
| 7. JES Scoring | v1.0 | 4/4 | Complete | 2026-06-02 |
| 8. Export | v1.0 | 4/4 | Complete | 2026-06-02 |
| 8.1. JES Advisor Override | v1.0 | 3/3 | Complete | 2026-06-03 |
| 9. DND DRF Integration | v1.0 | 4/4 | Complete | 2026-06-03 |
| **10. Project Scaffold** | **v2.0** | **4/4** | **Complete** | **2026-06-03** |
| **11. Data Foundation** | **v2.0** | **0/2** | **Not started** | — |
| **12. Socratic Question Bank** | **v2.0** | **0/2** | **Not started** | — |
| **13. Frontend SPA Shell** | **v2.0** | **3/3** | **Complete** | **2026-06-04** |
| **14. NOC Pipeline** | **v2.0** | **4/4** | **Complete** | **2026-06-04** |
| **15. Conversational UX** | **v2.0** | **0/?** | **Not started** | — |
| **16. OG Classification** | **v2.0** | **0/?** | **Not started** | — |
| **17. JES Scoring** | **v2.0** | **0/?** | **Not started** | — |
| **18. JD Composition & Live Preview** | **v2.0** | **0/?** | **Not started** | — |
| **19. Qualifications & Amendments** | **v2.0** | **0/?** | **Not started** | — |
| **20. Export** | **v2.0** | **0/?** | **Not started** | — |
