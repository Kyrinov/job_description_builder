---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Guided Conversation
current_phase: 10
status: ready_to_plan
last_updated: "2026-06-03T18:37:08.305Z"
progress:
  total_phases: 10
  completed_phases: 1
  total_plans: 4
  completed_plans: 0
  percent: 10
---

# Project State

**Status:** Ready to plan
**Current phase:** 11
**Last updated:** 2026-06-03
**Next action:** `/gsd-discuss-phase 10` (or `/gsd-plan-phase 10` to skip discussion)

---

## Phase Status

| # | Phase | Status |
|---|-------|--------|
| 10 | Project Scaffold | Pending |
| 11 | Frontend Port | Pending |
| 12 | Conversation UX | Pending |
| 13 | Document Composition | Pending |
| 14 | Classification Engine | Pending |
| 15 | JES Scoring | Pending |
| 16 | Duty Management | Pending |
| 17 | Qualifications | Pending |
| 18 | Backend API Service | Pending |
| 19 | DOCX Export | Pending |

v1.0 phases 1–9 (incl. 8.1) are archived. See `.planning/milestones/v1.0-ROADMAP.md`.

---

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-06-03)

**Core value:** An HR advisor can describe work in plain language and receive a legally defensible, fully traceable job description — grounded in NOC, collective agreement, and TBS classification policy — in minutes instead of hours.

**Architecture non-negotiables (do not change without a phase transition):**

- ProvenanceTag on every exported content element — set at write time, rendered at export
- Every content element in the exported DOCX/PDF must trace to an authoritative source citation
- The conversational design is the UX source of truth — see `Job Description Builder/jd-builder/`
- Deterministic classification in the main flow — no LLM dependency required to run the app

---

## Accumulated Context

### Decisions Made (v2.0)

| Decision | Rationale |
|----------|-----------|
| v2.0 React 18 SPA over HTMX | Conversational UX needs client-side state (live preview, edit-and-revisit, clickable sections); HTMX's request-response model doesn't fit a persistent document that updates as the user types |
| v2.0 deterministic classification over LLM | The work-type + 3-scope-question model is interpretable, instant, offline, and reproducible. The LLM-driven NOC/OG pipeline was a research bet that the conversational UX replaces |
| v2.0 hardcoded EC JES table over LLM scoring | EC JES 2017 is a published standard with fixed degree/point scales. Hardcoding is correct, auditable, and faster than LLM. FI/IT/AS/EN use approximate totals |
| v2.0 verb-mapping duty refinement over LLM | The refineDuty function covers common cases. Edge cases fall back to "Performs duties related to X" rather than LLM generation |
| v2.0 PDF in scope (no 501) | The conversational UX is complete at review time; exporting to PDF is a direct template render |
| v2.0 curated hardcoded data over v1.0 ingest pipelines | NOC/OG/JES data is small enough to live in code as constants. Eliminates ingest script complexity and embedding-model-version drift |
| v2.0 phase numbering continues from Phase 10 | Keeps a single linear history. v1.0 phases 1–9 (incl. 8.1) are archived but not renumbered |
| v2.0 drops 10 v1.0-drafted v2 candidates (QUAL-01, CA-02/03, JES-02/03/04, EXP-02/03, MAP-03, JD-05) | These were drafted for the v1.0 wizard. The conversational design has different priorities |

### Active Blockers

- (none)

### Todos

- Define v2.0 requirements with REQ-IDs (step 9 of new-milestone workflow)
- Create v2.0 roadmap via gsd-roadmapper (step 10 of new-milestone workflow)
- Verify WeasyPrint Pango/Cairo system libs present on Jane (v2.0 PDF export)
- Fix `noc_fts` DDL in `app/db.py` (v1.0 deferred debt — not carried into v2.0, archive as-is)
- Address Starlette `TemplateResponse` deprecation warning (v1.0 deferred debt — not carried into v2.0)
- Write v1.0 phase 02-02-SUMMARY.md (v1.0 archive gap — not blocking v2.0)

### Roadmap Evolution

- v1.0 closed 2026-06-03 with Phase 9 (DND DRF Integration) complete; 10 phases (1–9 incl. 8.1), 38 plans, 188 tests passing, 0 regressions
- v2.0 begins Phase 10 (TBD) — see `.planning/ROADMAP.md` after roadmap creation

---

## Performance Metrics

### v1.0 (archived)

| Metric | Value |
|--------|-------|
| Phases total | 10 (incl. 8.1) |
| Phases complete | 10 |
| Requirements delivered | 21/21 |
| Tests passing at ship | 188 |
| Regressions | 0 |
| Phase insertions | 1 (8.1) |
| Timeline | 7 days (2026-05-27 → 2026-06-03) |

### v2.0 (active)

| Metric | Value |
|--------|-------|
| Phases total | TBD (defined in roadmap) |
| Phases complete | 0 |
| Requirements | TBD (defined in step 9) |
| Tests passing | TBD |

---

## Session Continuity

**v2.0 "Guided Conversation" milestone initialized 2026-06-03:**

- 38 requirements across 9 categories (CONVO, CLASS, JES, DUTY, QUAL, DOC, EXP, API, FE)
- 10 phases (10–19) defined
- 100% requirement coverage; 0 unmapped; 0 orphans
- DRF, PDF export, clipboard, and review-state checklist deferred to v2.1+

**Next action:** `/gsd-discuss-phase 10` (or `/gsd-plan-phase 10` to skip discussion)

**v2.0 design source of truth:** `Job Description Builder/jd-builder/` — React 18 prototype (5 .jsx files + styles.css + JD Builder.html). All data hardcoded (DRF, WORK_TYPES, EC_ELEMENTS, DUTY_SUGGESTIONS, QUAL_DEFAULT). Classification engine: `computeClassification()` in data.jsx. Duty refinement: `refineDuty()` verb map. Live preview: document.jsx.

**v2.0 phase numbering:** Continues from v1.0 (Phase 9 / 8.1) → v2.0 starts at Phase 10.

**v1.0 reference:** `.planning/milestones/v1.0-ROADMAP.md`, `.planning/milestones/v1.0-REQUIREMENTS.md`. v1.0 code is preserved in `app/` and may be referenced but not extended.

**v2.0 build order (from ROADMAP.md):**

- Phase 10: Project Scaffold (FastAPI + Vite + Pydantic + SQLite + Vite proxy) — API-01, API-05, FE-02
- Phase 11: Frontend Port (port 5 JSX files + styles.css into Vite, brand styles, state, localStorage) — FE-01, FE-03, FE-04, FE-05
- Phase 12: Conversation UX (6-phase interview, inputs, revisit, phase header, keyboard) — CONVO-01..05
- Phase 13: Document Composition (live preview, position overview, ghosts, section edit, provenance) — DOC-01..05
- Phase 14: Classification Engine (work-type, 3 scope, group+level, badge, rationale) — CLASS-01..05
- Phase 15: JES Scoring (EC JES table, degree vectors, non-EC totals, scorecard) — JES-01..04
- Phase 16: Duty Management (suggested duties, advisor capture, live refinement, verb map, visual mark) — DUTY-01..05
- Phase 17: Qualifications (pre-filled defaults, editable, EQ section) — QUAL-01..03
- Phase 18: Backend API Service (WD CRUD, canonical data, classification service, SQLite) — API-02, API-03, API-04
- Phase 19: DOCX Export (docxtpl template, version manifest, export endpoint) — EXP-01
