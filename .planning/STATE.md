---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Real Guided Conversation
current_phase: 17
status: ready_to_plan
last_updated: "2026-06-05T16:48:09.936Z"
progress:
  total_phases: 11
  completed_phases: 8
  total_plans: 27
  completed_plans: 23
  percent: 73
---

# Project State

**Status:** Ready to plan
**Current phase:** 18
**Last updated:** 2026-06-05
**Next action:** Execute Phase 17 — `/gsd-execute-phase 17`

---

## Phase Status

| # | Phase | Status |
|---|-------|--------|
| 10 | Project Scaffold | ✅ Complete (2026-06-03) |
| 11 | Data Foundation | ✅ Complete (2026-06-04) |
| 12 | Socratic Question Bank | Plans complete (2/2) — verified |
| 13 | Frontend SPA Shell | ✅ Complete (2026-06-04) |
| 14 | NOC Pipeline | ✅ Complete (2026-06-04) |
| 15 | Conversational UX | ✅ Complete (2026-06-04) |
| 16 | OG Classification | ✅ Complete (2026-06-05) |
| 17 | JES Scoring | Plans complete (4/4) — ready to execute |
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
| v2.0 OG classification is deterministic (no LLM in /api/og/classify) | OG ranking is purely signal-based; confidence capped at 0.9. LLM only used in Phase 14 NOC pipeline. Avoids hallucinated OG justifications |
| v2.0 AS/EC disambiguation via `ogAlert` state | Both AS and EC appear in top-3 frequently (both broad group definitions). The disambiguation alert is derived from OG_DEFINITIONS excerpts at API layer; frontend surfaces it via `asec_alert: ogAlert` cfgOverride |
| v2.0 OG_LEVELS duplicated as JS constant in data.jsx | Avoids API round-trip for static reference data (the levels array is used in og_level cfgOverride). Source of truth is the Python constant |

### Active Blockers

- (none)

### Todos

- WeasyPrint ARM64 Pango/Cairo feasibility check on Jane before Phase 20 begins (EXP-03)
- Confirm sqlite-vec ARM64 wheel available for v2.0 NOC pipeline (Phase 14 dependency — already validated in Phase 14)
- **Phase 19 (Qualifications) backlog**: replace `v2/frontend/src/data.jsx` `QUAL_DEFAULT` with OG-group-keyed defaults (EC/FI/IT/AS) + `getQualDefault(answers)` function. Hardcoded EC-05 environmental text is a Phase 13 prototype port. Surfaces in Phase 15 UAT — user opted to defer to Phase 19 (strict scope) rather than land the fix now.
- **Phase 17 forward**: `require_og_confirmed` hard gate ready in `app/services/classification_gate.py` for Phase 17/18/20 to import

### Roadmap Evolution

- v1.0 closed 2026-06-03 with Phase 9 (DND DRF Integration) complete; 10 phases (1–9 incl. 8.1), 38 plans, 188 tests passing, 0 regressions
- v2.0 Phase 10 (Project Scaffold) complete 2026-06-03; original Phases 11–19 scrapped same day
- v2.0 replanned 2026-06-03: 10 new phases (11–20) defined; 52 requirements (49 active + 3 validated in Phase 10); 100% coverage
- v2.0 Phases 10–16 complete 2026-06-05; 7 phases, 19 plans, 50/50 v2 backend tests + 19/19 vitest tests + 188 v1 backend tests GREEN

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
| Phases complete | 7 (10, 11, 13, 14, 15, 16) — Phase 12 plans complete (2/2) but not yet verified in this session |
| Requirements total | 52 |
| Requirements validated | 12 (5 prior + CLASS-01..05 + API-06) |
| Requirements active | 40 |
| Tests passing | 50 v2 backend (10+8+9+12+7+4 = 50) + 19 vitest tests (Phase 13 9 + Phase 15 7 + Phase 16 3) + 188 v1 backend (9 skipped) |

---

## Session Continuity

**v2.0 "Real Guided Conversation" milestone replanned 2026-06-03:**

- Original Phases 11–19 scrapped — hardcoded work-type picker / simplified classifier architecture was wrong
- New Phases 11–20 defined around v1.0's production NOC + OG + JES engine
- 52 requirements across 13 categories (DATA, QUES, NOC, CONVO, CLASS, JES, JD, DOC, QUAL, AMEND, EXP, API, FE)
- 11 phases (10–20); Phases 10, 11, 13, 14, 15, 16 complete as of 2026-06-05
- 100% requirement coverage; 0 unmapped; 0 orphans
- DRF integration deferred to v2.1 (DOC-01 notes Defence Results Linkage deferred)

**v2.0 Phase 16 (OG Classification) complete 2026-06-05:** 4 plans (16-01 through 16-04). Wave 0 (16-01) added OG_DEFINITIONS + ASEC_DISAMBIGUATION + QUAL_STANDARDS constants (verbatim source: EC JES 2017, IT JES, TBS OCHRO for AS/FI), extended WorkDescription + WDPatchRequest with confirmed_og/og_level/reports_to_military, 7 RED backend test stubs + 2 frontend stubs. Wave 1 (16-02) implemented POST /api/og/classify (deterministic signal-based ranker, no LLM, AS/EC alert when both in top-3), GET /api/og/definitions, GET /api/quals/default, classification_gate.require_og_confirmed 409 hard gate. Wave 2 (16-03) added 3 STEPS (reports_to_military, og_confirm, og_level), OgConfirmList + OgLevelPicker components, OG_LEVELS JS constant, app.jsx pipeline wiring with ogAlert state for AS/EC disambiguation end-to-end via cfgOverride, extended NOC/OG invalidation + restart. Wave 3 (16-04) added Classification pending state (CLASS-04 frontend gate) and CAF rank advisory (CLASS-05) in document.jsx. **Phase 16 verified** (status: passed, 4/4 plans, 7/7 requirements: CLASS-01, CLASS-02, CLASS-03, CLASS-04, CLASS-05, API-06, API-03). 50/50 backend tests GREEN; 19/19 frontend tests GREEN; bundle 195.65 kB (gzip 61.40 kB); clean build. Code review clean (0 critical/high, 3 low — all advisory). Human UAT approved. 1 minor deviation: AS/FI definitions sourced from TBS OCHRO standard (PA and CT-FI collective agreements cover the groups but do not contain the group definition text itself).

**v2.0 Phase 15 (Conversational UX) complete 2026-06-04:** 4 plans (15-01 through 15-04). Wave 0 added WD CRUD endpoints (POST/GET/PATCH /api/wd) and frontend CONVO-01..05 RED stubs. Wave 1 added frontend STEPS + PHASES + accumulateSignals. Wave 2 wired app.jsx WD CRUD + NOC trigger + og_confirm stub. Wave 3 added OG-group-keyed duty suggestions (CONVO-01, CONVO-03). **Phase 15 verified** (4/4 plans, 7/7 requirements: CONVO-01..05, API-02, FE-04/05 deferred to Phase 13). 39 v2 backend + 9 vitest tests GREEN at completion.

**Next action:** Execute Phase 17 — `/gsd-execute-phase 17`

**v2.0 design source of truth:** `Job Description Builder/jd-builder/` — React 18 prototype (5 .jsx files + styles.css + JD Builder.html). Visual design and conversation flow preserved; classification backing replaced by v1.0 engine.

**v2.0 build order (new phases):**

- Phase 11: Data Foundation — fix OG_LEVELS, encode CAF rank table — DATA-01, DATA-02 ✅
- Phase 12: Socratic Question Bank — question bank artifact (design-first) — QUES-01, QUES-02, QUES-03 ✅
- Phase 13: Frontend SPA Shell — port 5 JSX files, brand styles, state, localStorage — FE-01 ✅, FE-03 ✅, FE-04 ✅, FE-05 ✅ ✅
- Phase 14: NOC Pipeline — FTS5 → embedding rerank → LLM justification + POST /api/noc/map + NocConfirmList SPA — NOC-01 ✅, NOC-02 ✅, API-04 ✅ ✅
- Phase 15: Conversational UX — 6-phase interview, question bank steps, revisit, phase chips, WD CRUD — CONVO-01..05 ✅, API-02 ✅ ✅
- Phase 16: OG Classification — OG ranker, AS/EC disambiguation, level selection, hard gate, CAF advisory — CLASS-01..05 ✅, API-06 ✅, API-03 ✅ ✅
- Phase 17: JES Scoring — EC JES 2017 9-factor scoring with per-factor retry + advisor override; non-EC approximate totals; JES scorecard in live preview; POST `/api/jes/score`. (JES-01, JES-02, JES-03, JES-04, API-07)
- Phase 18: JD Composition & Live Preview — Verbatim NOC duty selection with provenance; advisor-added duties; orphan check; live document preview with ghost placeholders, composed overview, section click-to-edit, provenance footer. (JD-01, JD-02, JD-03, JD-04, DOC-01, DOC-02, DOC-03, DOC-04, DOC-05)
- Phase 19: Qualifications & Amendments — OG-matched qual standard defaults; editable textareas with validation; EQ section render; manager amendment notes per section; DOCX appendix for amendments. (QUAL-01, QUAL-02, QUAL-03, AMEND-01, AMEND-02)
- Phase 20: Export — DOCX WD export (docxtpl, provenance citations, version manifest); job poster DOCX; PDF export via WeasyPrint (ARM64 gate); POST `/api/wd/{id}/export/docx` + `/poster`. (EXP-01, EXP-02, EXP-03, API-08, API-09)

**v1.0 reference:** `.planning/milestones/v1.0-ROADMAP.md`, `.planning/milestones/v1.0-REQUIREMENTS.md`. v1.0 code is preserved in `app/` and may be referenced for porting but not extended.
