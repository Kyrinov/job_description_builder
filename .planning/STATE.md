---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Real Guided Conversation
current_phase: 13
current_plan: 02
status: executing
last_updated: "2026-06-04T14:01:30Z"
progress:
  total_phases: 11
  completed_phases: 3
  total_plans: 11
  completed_plans: 9
  percent: 73
---

# Project State

**Status:** Executing Phase 13 Plan 02 (Plan 01 complete)
**Current phase:** 13
**Last updated:** 2026-06-04
**Next action:** Execute Plan 13-02 (Wave 1: data.jsx + components.jsx + styles.css + index.html + main.jsx)

---

## Phase Status

| # | Phase | Status |
|---|-------|--------|
| 10 | Project Scaffold | ✅ Complete (2026-06-03) |
| 11 | Data Foundation | ✅ Complete (2026-06-04) |
| 12 | Socratic Question Bank | Ready to execute (2 plans) |
| 13 | Frontend SPA Shell | In progress (1/3 plans complete) |
| 14 | NOC Pipeline | Not started |
| 15 | Conversational UX | Not started |
| 16 | OG Classification | Not started |
| 17 | JES Scoring | Not started |
| 18 | JD Composition & Live Preview | Not started |
| 19 | Qualifications & Amendments | Not started |
| 20 | Export | Not started |

---

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-06-03)

**Core value:** An HR advisor can describe work in plain language and receive a legally defensible, fully traceable job description — grounded in NOC, collective agreement, and TBS classification policy — in minutes instead of hours.

**Architecture non-negotiables (do not change without a phase transition):**

- ProvenanceTag on every exported content element — set at write time, rendered at export
- Every content element in the exported DOCX/PDF must trace to an authoritative source citation
- The conversational design is the UX source of truth — see `Job Description Builder/jd-builder/`
- Evidence-based classification (NOC pipeline + OG ranker + JES scoring) replaces the hardcoded work-type picker from the prototype
- Deterministic classification in the main flow — LLM used only for NOC justification (local via Ollama)
- Socratic constraint: manager never selects OG directly; OG is derived from accumulated answer signals

---

## Accumulated Context

### Decisions Made (v2.0)

| Decision | Rationale |
|----------|-----------|
| v2.0 React 18 SPA over HTMX | Conversational UX needs client-side state (live preview, edit-and-revisit, clickable sections); HTMX's request-response model doesn't fit a persistent document that updates as the user types |
| v2.0 evidence-based classification (v1.0 NOC + OG + JES engine) over prototype's hardcoded work-type picker | The prototype's 3-question classifier was the wrong simplification. v1.0's pipeline is production-proven and legally traceable |
| v2.0 Socratic question bank (design artifact first) | Questions must be designed before conversation UX is built; entries drive which input controls render in which steps |
| v2.0 hardcoded EC JES table over LLM scoring | EC JES 2017 is a published standard with fixed degree/point scales. Hardcoding is correct, auditable, and faster than LLM. FI/IT/AS/EN use approximate totals |
| v2.0 verb-mapping duty refinement over LLM | The refineDuty function covers common cases. Edge cases fall back to "Performs duties related to X" rather than LLM generation |
| v2.0 PDF in scope (no 501 unless ARM64 libs missing) | The conversational UX is complete at review time; exporting to PDF is a direct template render |
| v2.0 curated hardcoded data over v1.0 ingest pipelines | NOC/OG/JES data is small enough to live in code as constants. Eliminates ingest script complexity and embedding-model-version drift |
| v2.0 phase numbering continues from Phase 10 | Keeps a single linear history. v1.0 phases 1–9 (incl. 8.1) are archived but not renumbered |
| v2.0 drops original Phases 11–19 (scrapped 2026-06-03) | Those phases were built around the prototype's hardcoded work-type picker and simplified 3-question classifier — the wrong architecture |

### Active Blockers

- (none)

### Todos

- WeasyPrint ARM64 Pango/Cairo feasibility check on Jane before Phase 20 begins (EXP-03)
- Confirm sqlite-vec ARM64 wheel available for v2.0 NOC pipeline (Phase 14 dependency)

### Roadmap Evolution

- v1.0 closed 2026-06-03 with Phase 9 (DND DRF Integration) complete; 10 phases (1–9 incl. 8.1), 38 plans, 188 tests passing, 0 regressions
- v2.0 Phase 10 (Project Scaffold) complete 2026-06-03; original Phases 11–19 scrapped same day
- v2.0 replanned 2026-06-03: 10 new phases (11–20) defined; 52 requirements (49 active + 3 validated in Phase 10); 100% coverage

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
| Phases total | 11 (10–20) |
| Phases complete | 2 (Phases 10, 11) |
| Requirements total | 52 |
| Requirements validated | 5 (API-01, API-05, FE-02, DATA-01, DATA-02) |
| Requirements active | 47 |
| Tests passing | 18 (10 Phase 10 + 8 Phase 11) + 11 vitest todo stubs (Phase 13 Plan 01, RED) |

---

## Session Continuity

**v2.0 "Real Guided Conversation" milestone replanned 2026-06-03:**

- Original Phases 11–19 scrapped — hardcoded work-type picker / simplified classifier architecture was wrong
- New Phases 11–20 defined around v1.0's production NOC + OG + JES engine
- 52 requirements across 13 categories (DATA, QUES, NOC, CONVO, CLASS, JES, JD, DOC, QUAL, AMEND, EXP, API, FE)
- 11 phases (10–20); Phases 10 & 11 complete; Phase 12 next
- 100% requirement coverage; 0 unmapped; 0 orphans
- DRF integration deferred to v2.1 (DOC-01 notes Defence Results Linkage deferred)
- v2.0 Phase 11 (Data Foundation) complete 2026-06-04: 2 plans, 8 new tests, 0 regressions; 18 tests passing total in v2 backend

**Next action:** `/gsd-discuss-phase 12` (Socratic Question Bank — question bank artifact)

**v2.0 Phase 13 (Frontend SPA Shell) Plan 01 complete 2026-06-04:** Wave 0 test infrastructure gate. Installed vitest 4.1.8 + jsdom 29.1.1 + @testing-library/react 16.3.2 + @testing-library/user-event 14.6.1 as devDependencies. Added `test: { environment: 'jsdom', globals: true, setupFiles: [] }` block to `v2/frontend/vite.config.js`. Created `v2/frontend/src/app.test.jsx` with 11 RED `.todo` stubs covering FE-04 (8 state slice tests) and FE-05 (3 localStorage tests). `npx vitest run src/app.test.jsx` exits 0 with "11 todo (11), 0 failures". FE-04 and FE-05 are validated at the test-infrastructure level; real GREEN assertions land in Plan 03 when `app.jsx` is ported.

**v2.0 design source of truth:** `Job Description Builder/jd-builder/` — React 18 prototype (5 .jsx files + styles.css + JD Builder.html). Visual design and conversation flow preserved; classification backing replaced by v1.0 engine.

**v2.0 build order (new phases):**

- Phase 11: Data Foundation — fix OG_LEVELS, encode CAF rank table — DATA-01, DATA-02 ✅
- Phase 12: Socratic Question Bank — question bank artifact (design-first) — QUES-01, QUES-02, QUES-03 (NEXT)
- Phase 13: Frontend SPA Shell — port 5 JSX files, brand styles, state, localStorage — FE-01, FE-03, FE-04, FE-05
- Phase 14: NOC Pipeline — FTS5 → embedding rerank → LLM justification + POST /api/noc/map — NOC-01, NOC-02, API-04
- Phase 15: Conversational UX — 6-phase interview, question bank steps, revisit, phase chips, WD CRUD — CONVO-01..05, API-02
- Phase 16: OG Classification — OG ranker, AS/EC disambiguation, level selection, hard gate, CAF advisory — CLASS-01..05, API-06, API-03
- Phase 17: JES Scoring — EC 9-factor scoring, non-EC totals, override, scorecard render — JES-01..04, API-07
- Phase 18: JD Composition & Live Preview — verbatim duties, provenance, orphan check, live preview, ghost placeholders — JD-01..04, DOC-01..05
- Phase 19: Qualifications & Amendments — OG-matched defaults, editable EQ, amendment notes, DOCX appendix — QUAL-01..03, AMEND-01, AMEND-02
- Phase 20: Export — DOCX WD + poster + PDF, version manifest, export endpoints — EXP-01, EXP-02, EXP-03, API-08, API-09

**v1.0 reference:** `.planning/milestones/v1.0-ROADMAP.md`, `.planning/milestones/v1.0-REQUIREMENTS.md`. v1.0 code is preserved in `app/` and may be referenced for porting but not extended.
