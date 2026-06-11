---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Classification Depth & Document Quality
current_phase: 22
status: ready_to_execute
last_updated: "2026-06-11T00:00:00.000Z"
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 13
  completed_plans: 9
  percent: 40
---

# Project State

**Status:** Ready to plan
**Current phase:** 22
**Last updated:** 2026-06-11
**Next action:** Run full verification for Phase 21 (21-09 gap-closure plan complete; 60/60 frontend tests passing)

---

## Phase Status

| Phase | Name | Status |
|-------|------|--------|
| 21 | OG Expansion + Preview Fix | All 9 plans complete (incl. 21-09 gap-closure); 60/60 frontend tests; JES-LEV-01 + OGX-07 closed |
| 22 | SJD Library | Ready to execute — 4 plans (waves 0-2) |
| 23 | Writing Guide Integration | Not started |
| 24 | Risk Audit | Not started |
| 25 | Accessible Template | Not started |

---

## Plan 06 Continuation Notes (2026-06-11)

After the user ran manual UI verification, two bugs were surfaced that the
automated tests didn't catch:

1. **Sub-group picker did not render** — fixed by making `OgConfirmList`
   self-contained: when the user picks NU/SW/ED in the draft, a local
   `useEffect` re-calls `/api/og/classify` with `confirmed_og` in the body.

2. **Sector/cluster questions fired on every pass** — fixed by adding
   `isStepVisible(step, answers)` predicate that gates the 4 cluster
   questions on the corresponding `qb_sector_gate` answer.

10 new frontend tests cover the regressions. 41/41 frontend + 103/103
backend tests green. Build clean (216.05 kB JS / 24.86 kB CSS).

---

## Project Reference

See: `.planning/PROJECT.md`

**Core value:** An HR advisor can describe work in plain language and receive a legally defensible, fully traceable job description — grounded in NOC, collective agreement, and TBS classification policy — in minutes instead of hours.

**Architecture non-negotiables (do not change without a phase transition):**

- ProvenanceTag on every exported content element — set at write time, rendered at export
- Every content element in the exported DOCX/PDF must trace to an authoritative source citation
- Evidence-based classification (NOC pipeline + OG ranker + JES scoring) — deterministic in the main flow
- Socratic constraint: manager never selects OG directly; OG is derived from accumulated answer signals
- Socratic intent (extended in Phase 21 Plan 06 fix): manager is only asked questions relevant to their selected sector; cluster questions are gated on the sector-gate answer

---

## Accumulated Context

### Decisions Carried from v2.0

| Decision | Rationale |
|----------|-----------|
| React 18 SPA + FastAPI JSON API | Client-side state needed for conversational UX; established in v2.0 |
| Deterministic OG classification (no LLM in main flow) | Correct, auditable, offline; LLM used only for NOC justification |
| Hardcoded JES tables over LLM scoring | Published standards with fixed scales; faster and auditable |
| Phase numbering continues (v3.0 starts at Phase 21) | Single linear history; v1.0 phases 1–9, v2.0 phases 10–20 archived |
| docxtpl for DOCX export | Python-native, ARM64 compatible, Jinja2 template model |

### v3.0 Key Decisions

| Decision | Rationale |
|----------|-----------|
| Phase 21 opens with UI-01 CSS fix (1-line) | Immediate visible win; no risk to data work that follows |
| NON_EC_STANDARD_NAMES consolidated in constants.py (OGX-02) | Eliminates v2.0 dual-copy drift between constants.py and export_service.py |
| QUAL_DEFAULTS/QUAL_STANDARDS parity test written before new group text is authored (OGX-03) | Failing test first prevents the AS content-drift pattern from recurring for 12 new groups |
| All v3.0 audit and validation rules are deterministic | No LLM in audit, duty validation, or CBA matching — keeps output reproducible and offline |
| Accessible Template replaces TBS WD template entirely (not an optional format) | Single export path simplifies maintenance; Accessible format is the current GoC standard |
| Sub-group picker fetches its own data inside `OgConfirmList` (Phase 21 Plan 06 fix) | Picker must react to the DRAFT (value.og_code), not the committed `record.confirmed_og`; component-level fetch avoids timing race |
| Cluster questions gated on `qb_sector_gate` answer (Phase 21 Plan 06 fix) | Socratic intent: manager is only asked questions relevant to their selected sector |

### Active Blockers

None. Phase 21 gap closed by Plan 21-09 (2026-06-11). Sub_group propagation fixed for all 6 sub-group-bearing OG groups. 60/60 frontend tests passing.

### Roadmap Evolution

- v1.0 closed 2026-06-03: Phases 1–9 (incl. 8.1), 188 tests, 21/21 requirements
- v2.0 closed 2026-06-10: Phases 10–20, 299 tests (80 backend + 31 frontend + 188 v1), 52/52 requirements
- v3.0 started 2026-06-10: Phases 21–25, 24 requirements, roadmap defined
- Phase 21: 8 plans complete (21-01 through 21-08). 174 tests (115 backend + 59 frontend). OG expansion live for all 16 OG groups; Socratic mini-interview suggests JES level for NU/PS/NT/PO/SW/ED.

---

## Performance Metrics

### v1.0 (archived)

| Metric | Value |
|--------|-------|
| Phases total | 10 (incl. 8.1) |
| Requirements delivered | 21/21 |
| Tests passing at ship | 188 |
| Timeline | 7 days (2026-05-27 → 2026-06-03) |
| Phase 21 P09 | 5 | 3 tasks | 2 files |

### v2.0 (complete)

| Metric | Value |
|--------|-------|
| Phases total | 11 (10–20) |
| Requirements delivered | 52/52 |
| Tests passing at ship | 299 (80 backend + 31 frontend + 188 v1) |
| Timeline | 7 days (2026-06-03 → 2026-06-10) |

### v3.0 (active)

| Metric | Value |
|--------|-------|
| Phases total | 5 (21–25) |
| Requirements total | 24 |
| Tests passing (after Phase 21) | 174 (115 backend + 59 frontend); 12 new tests for level-suggest endpoints; 7 new tests for OgLevelQuestions + preselect |
