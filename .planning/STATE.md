---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Classification Depth & Document Quality
current_phase: 24
status: ready_to_execute
last_updated: "2026-06-15T00:00:00.000Z"
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 21
  completed_plans: 17
  percent: 80
---

# Project State

**Status:** Ready to plan
**Current phase:** 24
**Last updated:** 2026-06-15
**Next action:** Phase 23 complete (4/4 plans) — pending human UAT for 23-04 frontend duty hints + OG tips. Plan 23-04 complete: dutyHints state, validate-duties POST trigger, editingReturn clear, og_tip + duty_hints cfgOverride, .duty-hint + .og-duty-tip CSS; client_service_results step in STEPS; OG_DUTY_TIPS constant for 22 OG groups; conversation.test.jsx visible-step count 12 → 13. 231.58 kB JS / 70.63 kB gzip build; 60/60 frontend + 134/134 backend tests GREEN.

---

## Phase Status

| Phase | Name | Status |
|-------|------|--------|
| 21 | OG Expansion + Preview Fix | All 9 plans complete (incl. 21-09 gap-closure); 60/60 frontend tests; JES-LEV-01 + OGX-07 closed |
| 22 | SJD Library | Plans 22-01 + 22-02 + 22-03 + 22-04 complete (RED baseline + SJD_LIBRARY constant with OG normalization + GET /api/sjd endpoints + router registration + DraftDuty.source="sjd" extension + WorkDescription.sjd_source + POST /api/wd/{id}/sjd-start endpoint + _build_sjd_seed_duties helper + _build_v2_manifest SJD provenance + fetchSjds/fetchSjdDetail helpers + Browse SJDs panel + sjd-start frontend call + SJD-03 warning); 10/10 test_sjd.py GREEN; 125/125 backend suite GREEN; 60/60 frontend tests GREEN; 4 plans of 4 done; pending 9-step human UAT |
| 23 | Writing Guide Integration | Plans 23-01 + 23-02 + 23-03 + 23-04 complete (RED baseline + duty_validator.py 4-rule implementation + POST /api/wd/{id}/validate-duties endpoint + dutyHints state + OG_DUTY_TIPS constant + client_service_results step + .duty-hint + .og-duty-tip CSS); 9/9 test_writing_guide.py GREEN; 134/134 backend suite GREEN; 60/60 frontend tests GREEN; 4 plans of 4 done; pending 4-step human UAT |
| 24 | Risk Audit | Ready to execute — 4 plans planned (24-01 through 24-04) |
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
| DraftDuty.source Literal extended to {noc,advisor,sjd} additively (Phase 22 Plan 03) | Backward compatible via `ConfigDict(extra='ignore')`; existing DB rows deserialize without error |
| WorkDescription.sjd_source is dict (not nested Pydantic model) (Phase 22 Plan 03) | Minimal schema; readable in raw DB JSON; full SJDEntry dataclass lives only in app/data/sjd_library.py |
| _SJD_DUTY_SUGGESTIONS constant in wd.py keeps text parity with frontend data.jsx (Phase 22 Plan 03) | Single source of truth pattern: backend's _SJD_DUTY_SUGGESTIONS mirrors frontend's DUTY_SUGGESTIONS; avoids drift |
| sjd-start endpoint returns updated WorkDescription (not dict) (Phase 22 Plan 03) | One round-trip for SPA to mirror state; matches `patch_wd` return pattern |
| sjd_number validated by lookup against static SJD_LIBRARY (Phase 22 Plan 03 / T-22-01) | No eval, no path construction, no SQL string interpolation; 404 on miss |
| SJD-03 toast comparison: `og_code` only, not `og_level` (Phase 22 Plan 04) | A same-OG level change leaves the warning inert; matches the "departing from the SJD classification" semantics (classification = og_code, not level) |
| SJD browser panel rendered as modal overlay (Phase 22 Plan 04) | Non-blocking surface that doesn't disrupt the conversation flow; clicking outside or ✕ dismisses |
| fetchSjds / fetchSjdDetail co-located with data layer (Phase 22 Plan 04) | Keeps fetch logic next to other data utilities (matches v2 pattern of data.jsx owning backend data shape) |

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
| Phase 22 P01 | 180 | 1 tasks | 1 files |
| Phase 22 P02 | 7 | 2 tasks | 3 files |
| Phase 22 P02 | 7min | 2 tasks | 3 files |
| Phase 22 P03 | 5 | 2 tasks | 4 files |
| Phase 22 P04 | 6min | 2 tasks | 4 files |

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
