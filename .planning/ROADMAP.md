# Roadmap: JD Builder

## Milestones

- ✅ **v1.0 MVP** — Phases 1–9 incl. 8.1 (shipped 2026-06-03)
- 🚀 **v2.0 Guided Conversation** — Phases 10–19 (in progress, 2026-06-03)

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

### 🚀 v2.0 Guided Conversation (Phases 10–19)

v2.0 is a full rewrite of v1.0 around a conversational React SPA + FastAPI JSON API. The React prototype at `Job Description Builder/jd-builder/` is the UX design source of truth and the starting point for the build. v2.0 ports that prototype into a real Vite-built SPA with persistence and DOCX export.

- [ ] **Phase 10: Project Scaffold** — FastAPI skeleton + Pydantic v2 models + SQLite schema + Vite + React 18 project + Vite proxy. (API-01, API-05, FE-02)
- [ ] **Phase 11: Frontend Port** — Port the 5 JSX files + styles.css into Vite; brand typography (Hanken Grotesk, Spectral, Spline Sans Mono); preserve useState/useMemo architecture; add localStorage crash-recovery. (FE-01, FE-03, FE-04, FE-05)
- [ ] **Phase 12: Conversation UX** — 6-phase interview with 12 steps, input controls per step, click-to-revisit, phase chips header, keyboard shortcuts + auto-scroll. (CONVO-01, CONVO-02, CONVO-03, CONVO-04, CONVO-05)
- [ ] **Phase 13: Document Composition** — Live document preview fills as answers come in; composed position overview; ghost shimmer placeholders; section click-to-edit in review; provenance footer with tags. (DOC-01, DOC-02, DOC-03, DOC-04, DOC-05)
- [ ] **Phase 14: Classification Engine** — Work-type select (6 options: EC, FI, IT, AS, EN); 3 scope questions on 3-point scale; deterministic group+level resolution; live classification badge with confidence ring; plain-English rationale. (CLASS-01, CLASS-02, CLASS-03, CLASS-04, CLASS-05)
- [ ] **Phase 15: JES Scoring** — EC JES 2017 9-element table; degree vectors for EC-04/05/06; non-EC approximate point totals (FI/IT/AS/EN); per-factor scorecard render. (JES-01, JES-02, JES-03, JES-04)
- [ ] **Phase 16: Duty Management** — 7 suggested duty cards; advisor-added capture with remove; live refinement preview; verb-mapping rules; visual distinction in preview. (DUTY-01, DUTY-02, DUTY-03, DUTY-04, DUTY-05)
- [ ] **Phase 17: Qualifications** — Pre-filled EC-05 default (education + experience); editable textareas with validation; Essential Qualifications section render. (QUAL-01, QUAL-02, QUAL-03)
- [ ] **Phase 18: Backend API Service** — WD CRUD endpoints (POST/GET/PATCH); canonical data endpoints (work-types, duties, quals default); classification service endpoint (POST /api/classify); SQLite persistence; Vite proxy integration. (API-02, API-03, API-04)
- [ ] **Phase 19: DOCX Export** — docxtpl TBS WD template (binary artifact + reproducible build script); version manifest with source hashes; export endpoint consumes classification service; advisor downloads .docx. (EXP-01)

**Coverage:** 38/38 v2.0 requirements mapped · 10 phases · 0 unmapped · 0 orphans

---

## Phase Details

### Phase 10: Project Scaffold

**Goal:** Developer can run both the FastAPI backend and the Vite dev server, with the SPA loading and proxying API calls to the backend; SQLite schema is in place.

**Depends on:** Nothing (first v2.0 phase)

**Requirements:** API-01, API-05, FE-02

**Success criteria:**
1. Developer can start the FastAPI app with `uvicorn` and see `/health` return 200 OK
2. Developer can start the Vite dev server with `npm run dev` and see the SPA load at `localhost:5173` with a placeholder page
3. Vite proxies `/api/*` requests to FastAPI on a configured port
4. SQLite single-file database is created on app startup with the `work_descriptions` and `audit_log` tables present
5. Pydantic v2 models are defined: `WorkDescription`, `DraftDuty`, `Classification`, `JESFactor`, `QualificationStandard`

**Plans:** TBD

---

### Phase 11: Frontend Port

**Goal:** The React 18 prototype at `Job Description Builder/jd-builder/` is ported into the Vite project; the SPA renders the full conversational UX from local canonical data, with localStorage crash-recovery and brand typography.

**Depends on:** Phase 10

**Requirements:** FE-01, FE-03, FE-04, FE-05

**Success criteria:**
1. Developer can `npm run build` and see a Vite production bundle in `dist/`
2. Opening the SPA shows the full 6-phase interview starting with "What's the role you're hiring for?"
3. Brand typography renders: Hanken Grotesk (UI), Spectral (body prose), Spline Sans Mono (eyebrow / labels)
4. After answering several questions, refreshing the browser restores the in-progress WD from localStorage
5. Multi-file structure mirrors the prototype: `app.jsx`, `data.jsx`, `conversation.jsx`, `document.jsx`, `components.jsx`, `styles.css`
6. State architecture uses `useState` + `useMemo` only (no Redux/Zustand)

**Plans:** TBD

**UI hint:** yes

---

### Phase 12: Conversation UX

**Goal:** Advisor can complete the 6-phase interview end-to-end, revisit any answered step, and use the input controls and keyboard shortcuts appropriate to each step.

**Depends on:** Phase 11

**Requirements:** CONVO-01, CONVO-02, CONVO-03, CONVO-04, CONVO-05

**Success criteria:**
1. Advisor progresses through 12 total steps in 6 phases (Role → Focus → Level → Duties → Mission → Review) and lands on the review screen
2. Clicking any answered exchange in the transcript scrolls back to that step; re-answering updates the live preview without losing other answers
3. Phase chips at the top of the conversation pane show active / done / pending states
4. Each step renders the correct input control: text input, textarea, single-select choice cards (with icons and descriptions), 3-point scale (ends + options), duty builder, qualification editor
5. Pressing Enter on a text input continues; Cmd/Ctrl+Enter on a textarea continues; Back button works on step 2+; auto-scroll keeps the active question in view

**Plans:** TBD

**UI hint:** yes

---

### Phase 13: Document Composition

**Goal:** Advisor sees a live, complete document preview that fills as they answer, with ghost placeholders for unfilled sections, a composed position overview, and a provenance footer.

**Depends on:** Phase 12

**Requirements:** DOC-01, DOC-02, DOC-03, DOC-04, DOC-05

**Success criteria:**
1. Right-pane document preview shows 6 sections in order: Position Identification, Position Overview, Key Responsibilities, Classification & Evaluation, Defence Results Linkage (if selected), Essential Qualifications (if visited)
2. Position Overview paragraph is composed as "Located within {branch}, and reporting to the {reports}, the {title} {summary-lowercased}." plus a supervises sentence
3. Unfilled sections show 3 ghost shimmer lines (or 2 for duties) with a hint note; they populate the moment the advisor starts typing
4. In review state, each section header is clickable to jump back to the corresponding step; outside review, sections are non-interactive
5. Document footer shows provenance tags (NOC 2021, EC JES 2017, TBS OG Definitions, DND DRF, TBS Qualification Standard, Advisor-added) updating as sections populate

**Plans:** TBD

**UI hint:** yes

---

### Phase 14: Classification Engine

**Goal:** Advisor selects a work-type and answers 3 scope questions, and the system deterministically resolves a group + level with a live classification badge and plain-English rationale.

**Depends on:** Phase 12

**Requirements:** CLASS-01, CLASS-02, CLASS-03, CLASS-04, CLASS-05

**Success criteria:**
1. Work-type step shows 6 single-select choice cards (EC, FI, IT, AS, EN) with icon, title, and description; selecting one populates the canonical answer
2. Each scope question (day-to-day direction, advice reach, scope of impact) renders as a 3-point scale with end labels and 3 option labels
3. After all 3 scope questions are answered, the classification resolves to `<group>-0<level>` per the sum rule (≤4 → 4, ≤7 → 5, else 6)
4. Document preview header shows a live classification badge with the resolved group/level, point total, and a confidence ring (0.61 group-only baseline, up to 0.96 with low-spread scope answers)
5. When resolved, a plain-English rationale string describes the scope profile and why it maps to the chosen group/level; rendered in the Classification & Evaluation section

**Plans:** TBD

**UI hint:** yes

---

### Phase 15: JES Scoring

**Goal:** The Classification & Evaluation section renders a full factor scorecard for EC groups (9 elements with degrees and points) and an approximate-total line for non-EC groups.

**Depends on:** Phase 14

**Requirements:** JES-01, JES-02, JES-03, JES-04

**Success criteria:**
1. EC JES 2017 9-element table is encoded: Decision making, Leadership & operational mgmt, Communication, Knowledge of specialized fields, Contextual knowledge, Research & analysis, Physical effort, Sensory effort, Working conditions — each with degree→points scale and category
2. Selecting EC-04 / EC-05 / EC-06 yields the correct degree vector per element (verified against the 2017 standard)
3. Non-EC groups (FI, IT, AS, EN) use the approximate point totals: FI 470/560/660, IT 480/575/690, AS 430/510/600, EN 500/600/720 for levels 4/5/6
4. Classification & Evaluation section renders per-factor rows (name, D{degree}, points) and a totals row for EC; non-EC groups render a single totals line with the applicable JES standard cited

**Plans:** TBD

**UI hint:** yes

---

### Phase 16: Duty Management

**Goal:** Advisor selects from 7 suggested duties, adds their own in plain words, sees a live preview of the refined statement, and the document preview visually distinguishes advisor-added duties.

**Depends on:** Phase 13

**Requirements:** DUTY-01, DUTY-02, DUTY-03, DUTY-04, DUTY-05

**Success criteria:**
1. Duty step shows 7 pre-written suggested duties as togglable cards; selecting one shows its plain trigger and polished formal statement with a "refined for the description" tag
2. Advisor can type a free-text duty and add it; the new duty is appended to the list with a remove button
3. As the advisor types in the free-text input, a live preview shows the refined formal statement ("Will read as: Remediates contaminated sites.")
4. Verb-mapping rules refine common leading verbs: clean up → Remediates, advise → Advises, write → Prepares, lead → Leads, etc.; unrecognized verbs fall back to "Performs duties related to X."
5. In the document preview, advisor-added duties carry a distinct visual marker so the source is obvious in the export

**Plans:** TBD

**UI hint:** yes

---

### Phase 17: Qualifications

**Goal:** The Essential Qualifications section is pre-filled with the EC-05 default, the advisor can edit both fields, and the document preview renders the section with provenance.

**Depends on:** Phase 13

**Requirements:** QUAL-01, QUAL-02, QUAL-03

**Success criteria:**
1. Qualification step pre-fills education (degree in environmental science / economics / public policy / relevant discipline) and experience (significant experience in policy/analysis including advice to management, *Significant ≈ 3 years)
2. Both textareas are editable; the Finish button is disabled if either field is empty
3. Essential Qualifications section renders in the document preview with Education / Experience sub-labels in monospace caps; provenance tag "TBS Qualification Standard"

**Plans:** TBD

**UI hint:** yes

---

### Phase 18: Backend API Service

**Goal:** FastAPI exposes WD CRUD, canonical data, and classification service endpoints; SQLite persists WDs and audit log; the Vite dev server proxies the SPA to the API.

**Depends on:** Phase 10 (backend exists; ports use the prototype's local data until this phase ships)

**Requirements:** API-02, API-03, API-04

**Success criteria:**
1. `POST /api/wd` creates a WD from answers and returns a WD id; `GET /api/wd/{id}` loads it; `PATCH /api/wd/{id}` updates the draft
2. `GET /api/work-types` returns the 6 work-types; `GET /api/duties` returns the 7 suggested duties; `GET /api/quals/default` returns the EC-05 default
3. `POST /api/classify` accepts work-type + 3 scope answers and returns `{code, group, level, points, factors, rationale, confidence}` — server-side mirror of the React `computeClassification` function
4. SQLite persists WD records and audit log entries (per-step commit, advisor-modified, export)
5. Vite dev server proxies `/api/*` to FastAPI; the SPA can call `fetch('/api/...')` and get a real response

**Plans:** TBD

---

### Phase 19: DOCX Export

**Goal:** Advisor can export the assembled work description to a .docx with provenance tags as citations and source data hashes in a version manifest.

**Depends on:** Phase 18

**Requirements:** EXP-01

**Success criteria:**
1. The export endpoint `POST /api/wd/{id}/export` accepts a WD id, runs the classification service against the saved answers, and returns a .docx file
2. The .docx template follows the TBS Work Description format (D-04): Position Identification, Position Overview, Key Responsibilities, Classification & Evaluation, Essential Qualifications
3. Every duty carries structured provenance: source type (NOC, advisor), NOC code if applicable, and the section reference
4. A version manifest section at the end of the .docx lists source data hashes (e.g. EC JES table version, Qualification Standard text hash)
5. The template is a committed binary artifact with a reproducible build script that self-verifies via `DocxTemplate.get_undeclared_template_variables()` (mirrors v1.0's pattern)

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
| **10. Project Scaffold** | **v2.0** | **0/?** | **Pending** | — |
| **11. Frontend Port** | **v2.0** | **0/?** | **Pending** | — |
| **12. Conversation UX** | **v2.0** | **0/?** | **Pending** | — |
| **13. Document Composition** | **v2.0** | **0/?** | **Pending** | — |
| **14. Classification Engine** | **v2.0** | **0/?** | **Pending** | — |
| **15. JES Scoring** | **v2.0** | **0/?** | **Pending** | — |
| **16. Duty Management** | **v2.0** | **0/?** | **Pending** | — |
| **17. Qualifications** | **v2.0** | **0/?** | **Pending** | — |
| **18. Backend API Service** | **v2.0** | **0/?** | **Pending** | — |
| **19. DOCX Export** | **v2.0** | **0/?** | **Pending** | — |
