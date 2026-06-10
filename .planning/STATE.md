---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Classification Depth & Document Quality
current_phase: 21 (ready to execute)
status: planned
last_updated: "2026-06-10T20:00:00.000Z"
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 6
  completed_plans: 0
---

# Project State

**Status:** Phase 21 planned — ready to execute (6 plans, 4 waves)
**Current phase:** 21 (ready to execute)
**Last updated:** 2026-06-10
**Next action:** `/gsd-execute-phase 21`

---

## Phase Status

| Phase | Name | Status |
|-------|------|--------|
| 21 | OG Expansion + Preview Fix | Ready to execute (6 plans) |
| 22 | SJD Library | Not started |
| 23 | Writing Guide Integration | Not started |
| 24 | Risk Audit | Not started |
| 25 | Accessible Template | Not started |

---

## Project Reference

See: `.planning/PROJECT.md`

**Core value:** An HR advisor can describe work in plain language and receive a legally defensible, fully traceable job description — grounded in NOC, collective agreement, and TBS classification policy — in minutes instead of hours.

**Architecture non-negotiables (do not change without a phase transition):**

- ProvenanceTag on every exported content element — set at write time, rendered at export
- Every content element in the exported DOCX/PDF must trace to an authoritative source citation
- Evidence-based classification (NOC pipeline + OG ranker + JES scoring) — deterministic in the main flow
- Socratic constraint: manager never selects OG directly; OG is derived from accumulated answer signals

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

### Active Blockers

- (none)

### Roadmap Evolution

- v1.0 closed 2026-06-03: Phases 1–9 (incl. 8.1), 188 tests, 21/21 requirements
- v2.0 closed 2026-06-10: Phases 10–20, 299 tests (80 backend + 31 frontend + 188 v1), 52/52 requirements
- v3.0 started 2026-06-10: Phases 21–25, 24 requirements, roadmap defined

---

## Performance Metrics

### v1.0 (archived)

| Metric | Value |
|--------|-------|
| Phases total | 10 (incl. 8.1) |
| Requirements delivered | 21/21 |
| Tests passing at ship | 188 |
| Timeline | 7 days (2026-05-27 → 2026-06-03) |

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
| Tests passing (inherited) | 299 |
