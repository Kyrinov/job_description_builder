# JD Builder

## What This Is

A DND-first Government of Canada job description builder for HR advisors and classification specialists. An advisor describes the work in a guided conversation; the system captures the role, scope, duties, classification and qualifications, and generates a fully traced job description grounded in NOC, collective agreements, job evaluation standards, and TBS policy.

v1.0 (MVP, HTMX wizard) shipped 2026-06-03 and is archived. v2.0 ("Real Guided Conversation") replans the original v2.0 scope: the Claude Design prototype's conversational UX form is right but its hardcoded simplified classification was wrong. v2.0 ports v1.0's production NOC + OG + JES engine into a conversational React SPA, fixes the OG levels data gap, adds a Socratic question bank, DND SJD library, CAF rank context, manager amendment space, and job poster generation.

## Current State

- **v1.0 (archived):** FastAPI + HTMX 2.x + SQLite + sqlite-vec + Ollama. ~15,539 LOC Python, 188 tests passing. Reference: `.planning/milestones/v1.0-ROADMAP.md` and `.planning/milestones/v1.0-REQUIREMENTS.md`.
- **v2.0 (active — replanned 2026-06-03):** React 18 conversational SPA + FastAPI JSON API. Phase 10 scaffold complete. Phases 11–19 (original plan) scrapped — they were built around the Claude Design prototype's hardcoded work-type picker and simplified scope-question classifier. v2.0 is being replanned around v1.0's production NOC + OG + JES engine. The React prototype at `Job Description Builder/jd-builder/` remains the UX design source of truth (visual design, conversation flow, live preview) but its classification logic is replaced.
- **Phase 10 (Project Scaffold) complete** — `v2/backend/` (FastAPI + Pydantic v2 + SQLite) and `v2/frontend/` (Vite + React 18 + proxy) wired together. 10/10 tests pass; `v2/scripts/verify.sh` exits 0 with 7/7 checks. The placeholder SPA loads at `localhost:5173` and proxies `/api/*` to FastAPI on `:8000`. Conversational UX port lands in Phase 11.
- **Phase 11 (Data Foundation) complete** — `OG_LEVELS` corrected (EC 1-8, IT 1-5, CS merged into IT) and `CAF_RANK_OG_EQUIVALENCE` populated from `data/CAF pay grades` (14 CAF rank entries, advisory-flagged). 8 new tests; 18/18 green.
- **Phase 12 (Socratic Question Bank) complete** — `QUESTION_BANK` constant with 4 Socratic work-type entries (14 answer options total) covering EC, AS, IT, FI without naming any OG group in user-visible text. `KNOWN_JES_FACTORS` frozenset (9 canonical EC JES factor names). 9 new tests; 27/27 green, 0 regressions. Phase 15 conversational UX and Phase 16 OG ranker are unblocked.
- **Phase 13 (Frontend SPA Shell) complete 2026-06-04** — Ported 5 JSX files (app, data, conversation, document, components) + styles.css from the Claude Design prototype into the Vite project as ES modules. React 18 SPA with `useState`/`useMemo`/`useRef`/`useEffect` (zero Redux/Zustand). 8 state slices (record, answers, stepIndex, draft, reviewing, editingReturn, flashes, toast). Brand typography: Hanken Grotesk (variable range 300..800), Spectral, Spline Sans Mono via Google Fonts. localStorage crash-recovery via lazy `useState` init + `useEffect` persistence on `jd-builder-v2-record` key. 9 vitest tests GREEN (FE-04 + FE-05); 27/27 backend regression tests still pass. `npm run build` produces 179.71 kB JS bundle (57.52 kB gzip). 2 manual UAT items remain (visual font render, end-to-end localStorage restore); tracker at `13-HUMAN-UAT.md`. Code review surfaced 1 major bug (toast icon `path={'check'}` → `path={I.check}`) which was fixed before verification. Phase 14 NOC pipeline is unblocked.
- **Phase 14 (NOC Pipeline) complete 2026-06-04** — Ported v1.0's production three-stage NL→NOC pipeline (FTS5 shortlist → sqlite-vec embedding rerank → instructor/Ollama LLM justification) into v2 backend. Created `app/services/noc_mapper.py` (265 lines) and `app/ai/noc_ranking.py` (105 lines); added `get_noc_connection()` factory loading sqlite-vec; extended `Settings` with `NOC_DB_PATH` and Ollama model env vars; added `NOCMatch` storage model with `noc_candidates`/`confirmed_noc` on `WorkDescription`; created `POST /api/noc/map` JSON-only FastAPI route (min_length=10 validation, ValueError→422 translation). SPA side: added `NocConfirmList` component rendering candidates as cards with code/title/TEER badge/up-to-2 matched duties. 12 new tests (NOC pipeline); 39/39 backend total, 9/9 frontend vitest. Code review clean (0 critical, 5 warning, 7 info). 2 human UAT items (live browser render, live Ollama execution) deferred to Phase 15 STEPS wiring per phase boundary. Phase 15 Conversational UX is unblocked.
- **Phase 15 (Conversational UX) complete 2026-06-05** — Replaced the prototype's hardcoded work-type picker + scope-scale questions with a 6-phase Socratic interview backed by `QUESTION_BANK`. New STEPS array (12 entries across 5 numbered phases) drives 6 PHASES (Role, Work Type, Classification, Duties, Qualifications, Review). `accumulateSignals(answers)` pure function tallies `og_candidates` from the 4 Socratic answers to derive the dominant OG group. `WDCreateRequest`/`WDPatchRequest` Pydantic models + `POST/GET/PATCH /api/wd` routes (parameterized SQL) persist each step commit to `work_descriptions.data` as a JSON-encoded `WorkDescription`. `app.jsx` commit() now fires the WD CRUD call on every commit and triggers `POST /api/noc/map` after the summary step; NOC invalidation path on Work Type revisits clears `nocCandidates` and `noc_confirm` answer. Duty suggestions are now OG-group-keyed (EC, FI, IT, AS, default) via `getDutySuggestions(answers)`. 4 backend WD tests + 8 frontend CONVO tests added; 43/43 backend + 18/18 frontend total GREEN. Code review clean (0 critical, 0 high, 0 medium, 2 low, 3 info). Schema drift clean. UAT approved. 6 requirements validated: CONVO-01..05, API-02. QUAL_DEFAULT environmental hardcode noted in STATE.md as Phase 19 backlog. Phase 16 OG Classification is unblocked.
- **Phase 19 (Qualifications & Amendments) complete 2026-06-09** — Replaced the EC-only `QUAL_DEFAULT` constant with an OG-keyed `QUAL_DEFAULTS` map (EC/AS/IT/FI/default) in `data.jsx` plus a matching `QUAL_STANDARDS` dict in backend `constants.py`; `getQualDefault(og_code)` function selects the right prefill. `QualEditor` now accepts an `og_code` prop, tracks per-field `touched` state, and renders inline `.qual-error` ("Education field is required." / "Experience field is required.") on blur; `answerValid()` still blocks submission. Section 5 of the document preview now renders EDUCATION/EXPERIENCE sub-labels as `<span className="qual-sub-k">` (uppercase, monospace) instead of inline `<b style=...>`. Manager amendment notes (AMEND-01): new `v2/backend/app/api/amendments.py` exposes `POST/GET /api/wd/{id}/amendments` storing notes as `audit_log` rows with `event='manager_amendment'`; GET deduplicates by `MAX id` per section. Frontend `App()` adds `amendmentNotes` + `amendmentPanels` state with `handleAmendToggle`/`handleAmendSave` handlers and a hydration `useEffect` keyed on `[wd_id, reviewing]`. `Sec` component in `document.jsx` extends with `sectionKey`/`amendmentNote`/`amendmentPanel` props and renders an `.amend-btn` pencil icon, an `.amend-panel` with textarea/Save/Discard, and an `.amend-indicator` gold dot. `ReviewState` checklist shows "N amendment note(s) attached" when count > 0. Backend: 67→73 passed (3 qual + 6 amendment tests GREEN); frontend: 30→31 passed (QUAL-03 stub now GREEN); Vite build clean (201.76 kB / 62.91 kB gzip). Code review flagged 1 High content-drift issue (backend `QUAL_STANDARDS` and frontend `QUAL_DEFAULTS` texts differ for EC/AS/FI; AS differs materially) — advisory, non-blocking; recommend a content-parity test in Phase 19.1 or Phase 20 prep. UAT approved by human across 7 browser scenarios. 5 requirements validated: QUAL-01/02/03, AMEND-01, AMEND-02 (data path; appendix render scoped to Phase 20). Phase 20 (Export) is unblocked.
- **Phase 20 (Export) complete 2026-06-10 — v2.0 MILESTONE COMPLETE** — Three plans (20-01 RED stubs + WeasyPrint 69.0 + .docx templates, 20-02 export_service.py + export.py router, 20-03 frontend exportAs wire-up) plus 6 UAT fix commits (surface real HTTP status in toast, unwrap object detail, OG/level pre-check, gate falls back to wd.record, Pydantic Union[str,dict] for confirmed_noc/og, self-healing JES scoring at export time, export falls back to record.duties/quals, quals persist + JES re-triggers, duties/quals record-fallback). DOCX WD export with provenance + version manifest, poster DOCX with bilingual headers, PDF via WeasyPrint with ARM64 501 gate. 80/80 backend + 31/31 frontend tests GREEN. Code review: 2 critical (CR-01 string-shape AttributeError, CR-02 HTML injection in WeasyPrint) both fixed pre-close; 11 warning + 10 info carried as advisory open items. UAT approved by human. All 52 v2.0 requirements validated. v2.0 "Real Guided Conversation" milestone **complete** at 100%.
- **Phase 21 (OG Expansion + Preview Fix) complete 2026-06-11** — 9 plans covering all 16 GC occupational groups end-to-end: CSS overflow fix (UI-01); NON_EC_STANDARD_NAMES consolidation (OGX-02); atomic constant extension for all 6 constants × 16 OGs (OGX-01, OGX-03); JES routing for point-rating + level-description paths (OGX-05, OGX-06); sector-gate + cluster QUESTION_BANK (OGX-04); sub-group disambiguation API + frontend picker for NU/SW/ED (OGX-07); Socratic mini-interview for level-description groups (JES-LEV-01); sub_group propagation fix via onChange (gap closure plan 21-09). 115 backend + 60 frontend tests GREEN. Requirements OGX-01..07, UI-01, JES-LEV-01 validated.

## Current Milestone: v3.0 Classification Depth & Document Quality

**Goal:** Expand the classification engine to cover all GC occupational groups that have JES standards in data/, replace the export template with the Accessible JD format, wire the Job Description Writing Guide principles into every stage of duty authoring, add a CBA + jurisprudence compliance audit, seed a DND SJD library as a conversation starting point, and fix the live preview page extension.

**Target features:**
- SJD Library — seed from `data/SJD Examples.txt` + `data/AI Docs/SJD-guide.pdf`; advisor can start a conversation from an SJD or browse as reference
- Accessible JD Template — export format follows `data/AI Docs/Accessible Job Description Template (1).docx`; replaces existing TBS Work Description DOCX template
- Writing Guide integration — (a) Socratic questions reshaped per `data/AI Docs/Job Description Writing Guide.docx`; (b) inline duty-entry tips; (c) validation pass flagging duty statements that violate guide principles
- Risk Audit — explicit advisor action in Review phase; inline recommendations per JD section (Accept / Manual Edit / Skip) citing CBA clauses and Federal Court principles (`data/AI Docs/ERR_Principles_drawn_from_Federal_Court.pdf` + `Wilkonson v. Canada.pdf`)
- Broader OG classification — full Socratic interview + JES scoring for 12 new groups (ED, FB, FS, LC, LP, MT, NT, NU, PO, PS, SW, WP); best-effort approximate totals for remaining groups without JES standards in data/
- Document preview page extension — the simulated white page grows seamlessly to contain all preview content at any document length (no overflow into grey background)

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
- ✓ **DATA-01, DATA-02** — `OG_LEVELS` corrected (EC 1-8, IT 1-5, CS removed) and `CAF_RANK_OG_EQUIVALENCE` populated with 14 advisory-flagged CAF rank entries — validated in Phase 11 (Data Foundation, completed 2026-06-04)
- ✓ **QUES-01, QUES-02, QUES-03** — `QUESTION_BANK` constant with 4 Socratic work-type entries (14 options) and `KNOWN_JES_FACTORS` frozenset; OG codes appear only in `signals.og_candidates` (Socratic constraint enforced) — validated in Phase 12 (Socratic Question Bank, completed 2026-06-04)
- ✓ **FE-01, FE-03, FE-04, FE-05** — React 18 SPA port complete: 5 JSX files + styles.css as ES modules; brand typography (Hanken Grotesk variable, Spectral, Spline Sans Mono); `useState` + `useMemo` state architecture with 8 slices; localStorage crash-recovery via lazy init + useEffect — validated in Phase 13 (Frontend SPA Shell, completed 2026-06-04)
- ✓ **NOC-01, NOC-02, API-04** — Three-stage NL→NOC pipeline (FTS5 keyword shortlist → sqlite-vec embedding rerank → instructor/Ollama LLM justification) ported from v1.0 to v2 backend; `POST /api/noc/map` JSON-only route mounted; `NOCMatch` storage model with `noc_candidates`/`confirmed_noc` on `WorkDescription`; `NocConfirmList` SPA component with code/title/TEER/matched-duties cards. 12 new backend tests GREEN; 39/39 total backend, 9/9 frontend; code review clean (0 critical, 5 warning, 7 info — all non-blocking). 2 human UAT items (live browser render, live Ollama execution) deferred to Phase 15 wiring per phase boundary — validated in Phase 14 (NOC Pipeline, completed 2026-06-04)
- ✓ **CONVO-01, CONVO-02, CONVO-03, CONVO-04, CONVO-05, API-02** — 6-phase Socratic interview: STEPS array (12 entries across 5 numbered phases) with 4 QUESTION_BANK-derived steps at phase 1 (qb_work_output_type, qb_work_audience, qb_knowledge_specialization, qb_policy_interpretation); PHASES = ['Role', 'Work Type', 'Classification', 'Duties', 'Qualifications', 'Review']; `accumulateSignals(answers)` pure function tallies `og_candidates` from Socratic answers; `jumpToExchange(idx)` for revisit; `StepInput` `og_confirm` stub (Phase 16 replaces); Enter key submits text input. WD CRUD: `POST/GET/PATCH /api/wd` (parameterized SQL, Pydantic v2 validation) with WorkDescription JSON-serialised into `work_descriptions.data`. 4 backend WD tests + 8 frontend CONVO tests added; 43/43 backend + 18/18 frontend total GREEN; code review clean (0 critical/high/medium, 2 low, 3 info); schema drift clean. UAT approved by user after fixes for CWD-dependent .env, NOC card layout, cloud LLM thinking disable, OG-group-keyed duty suggestions. QUAL_DEFAULT environmental hardcode deferred to Phase 19 (in scope for that phase) — validated in Phase 15 (Conversational UX, completed 2026-06-05)
- ✓ **CLASS-01, CLASS-02, CLASS-03, CLASS-04, CLASS-05, API-03, API-06** — Evidence-based OG classification: `POST /api/og/classify` returns top-3 OG candidates ranked by signal_tally (deterministic, no LLM, confidence capped at 0.9); AS/EC disambiguation alert (built once from OG_DEFINITIONS excerpts) when both groups in top-3, surfaced to frontend via `ogAlert` state + `cfgOverride.asec_alert`; `GET /api/og/definitions?og_code=EC` and `GET /api/quals/default?og_code=EC` return verbatim source text; `require_og_confirmed` 409 hard gate in `app/services/classification_gate.py` for Phase 17/18/20 export layers. Frontend: `OgConfirmList` (OG cards with confidence % + definition excerpt + AS/EC alert block), `OgLevelPicker` (one button per level from `OG_LEVELS[og_code]` JS constant), 3 new STEPS (reports_to_military in Phase 0; og_confirm + og_level in Phase 2), document.jsx shows "Classification pending" until both fields set (frontend gate UX), `getCafEquivalence` shows CAF rank advisory labeled "advisory — not authoritative" beside Reports to when `reports_to_military=true` and OG/level confirmed. 7 new backend tests (50/50 GREEN); 2 new frontend tests (19/19 GREEN); bundle 195.65 kB (gzip 61.40 kB); clean build; manual code review clean (0 critical/high, 3 low — all advisory); human UAT approved. 1 documented deviation: AS/FI definitions sourced from TBS OCHRO standard (PA and CT-FI collective agreements cover the groups but do not contain the group definition text itself) — validated in Phase 16 (OG Classification, completed 2026-06-05)
- ✓ **JES-01, JES-02, JES-03, JES-04, API-07** — Per-factor EC JES 2017 scoring with 3-retry instructor wrapper, degree normalization (`D3`/`3`/mixed LLM output), sentinel pattern (`degree=-1, points=None` for failed factors after 3 retries), and sequential (not asyncio.gather) LLM loop to avoid Ollama OOM on ARM64. `EC_JES_ELEMENTS` (9 factors with per-degree points dicts), `EC_DEGREES` (EC-04/05/06 vectors), `NON_EC_TOTALS` (FI/IT/AS/EN level-keyed approximate totals), `NON_EC_STANDARD_NAMES` hardcoded. Non-EC path skips LLM and returns single totals dict. `WorkDescription` extended with `jes_scores: list[dict]` and `jes_total_points: Optional[int]`. `require_og_confirmed` 409 gate on the route. `POST /api/jes/score` and `POST /api/jes/override/{wd_id}/{factor_name}` (writes `audit_log` row with `event='jes_override'`). Frontend: `app.jsx` chains JES fetch off WD persistence (so the WD is fully persisted with confirmed_og + og_level at root before the JES read); `commit()` mirrors classification fields to PATCH root (WorkDescription stores them at root, not nested in `record`); `ClassBlock` exported and renders per-factor rows + totals line in Section 4, with inline number input for failed factors (`degree === -1`). Render gate uses `jes_total_points != null` (not `jes_scores.length > 0`) so non-EC groups (which return `factors: []`) also render. 8 new backend tests (58/58 GREEN); 6 new frontend tests (24/24 GREEN including 2 regression tests for the render-gate fix); bundle 199.36 kB (gzip 62.28 kB); clean build. 3 fix commits during UAT debugging: field-mirror (`7ad3568`), JES-fetch chain off wdPromise (`a8b1c8e`), render-gate (`723f3d8`). **Browser visual UAT pending user retest** — 3 items in `17-HUMAN-UAT.md` (status: pending-retest); automated gate is GREEN — validated in Phase 17 (JES Scoring, completed 2026-06-08)
- ✓ **EXP-01, EXP-02, EXP-03, API-08, API-09** — TBS Work Description DOCX export (docxtpl) with provenance citations, version manifest (NOC + JES standard + TBS OG definitions + qualification standard), amendment appendix (gated on `amendments|length > 0`); job poster DOCX with bilingual headers (English + French placeholder), top-5 duties, qualifications; PDF export via WeasyPrint (ARM64 gate via runtime probe; 501 if Pango/Cairo missing). `POST /api/wd/{id}/export/docx|poster|pdf` mounted in `app/api/export.py`. `export_service.py` provides `generate_wd_docx`/`generate_poster_docx` async (asyncio.to_thread render), `_build_wd_context`/`_build_poster_context`/`_build_v2_manifest`/`_get_amendments` helpers, NON_EC_STANDARD_NAMES for non-EC manifest entries, `_resolve_template_path` from `app/services/`. Self-healing: export endpoint re-runs `score_jes_v2` when `jes_total_points is None or all-factors-at-floor`; record-fallbacks for duties/quals when root fields are empty. Build scripts `build_wd_template.py`/`build_poster_template.py` reproduce the committed .docx binaries and self-verify via `get_undeclared_template_variables()`. Frontend `exportAs()` is async: fetch + Blob + URL.createObjectURL download; 501 diagnostic toast; `wd_id` and `confirmed_og`/`og_level` pre-checks; object `detail` unwrapping; HTML-escaped PDF render. 7 export tests (80/80 backend GREEN); 31/31 frontend GREEN. Cumulative Phase 16 Pydantic fix made `confirmed_noc`/`confirmed_og` accept string OR dict (unblocked the live flow). 2 critical review findings (CR-01 string-shape AttributeError, CR-02 HTML injection in WeasyPrint) both fixed pre-close. 11 warning + 10 info findings carried as advisory open items. UAT approved by human — validated in Phase 20 (Export, completed 2026-06-10)

### Active (v3.0)

See `.planning/REQUIREMENTS.md` for scoped requirements with REQ-IDs.

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
*Last updated: 2026-06-10 — v3.0 milestone started; v2.0 complete at 100% (52/52 requirements, 299 tests GREEN)*
