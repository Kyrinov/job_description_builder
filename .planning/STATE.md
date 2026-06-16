---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Classification Depth & Document Quality
current_phase: 25
current_plan: 03 (_factor_category_map + _build_wd_context rewrite + template path swap + TBS retirement complete)
status: executing
last_updated: "2026-06-16T19:21:43.581Z"
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 24
  completed_plans: 24
  percent: 100
---

# Project State

**Status:** Executing Phase 25 Plan 03 (Accessible template export path + TBS retirement complete)
**Current phase:** 25
**Current plan:** 03 (_factor_category_map + _build_wd_context rewrite + template path swap + TBS retirement complete)
**Last updated:** 2026-06-16
**Next action:** Plan 25-03 complete (_factor_category_map + rewritten _build_wd_context + wd_accessible_template.docx path swap + wd_template.docx/build_wd_template.py retired; 6 RED tests from Plan 25-01 now GREEN; 19/19 test_export.py passing; 150/150 full backend suite green; ACC-02/03/04 closed). Phase 25 structurally complete. Pending: 9-step human UAT of the Accessible-format DOCX.

---

## Phase Status

| Phase | Name | Status |
|-------|------|--------|
| 21 | OG Expansion + Preview Fix | All 9 plans complete (incl. 21-09 gap-closure); 60/60 frontend tests; JES-LEV-01 + OGX-07 closed |
| 22 | SJD Library | Plans 22-01 + 22-02 + 22-03 + 22-04 complete (RED baseline + SJD_LIBRARY constant with OG normalization + GET /api/sjd endpoints + router registration + DraftDuty.source="sjd" extension + WorkDescription.sjd_source + POST /api/wd/{id}/sjd-start endpoint + _build_sjd_seed_duties helper + _build_v2_manifest SJD provenance + fetchSjds/fetchSjdDetail helpers + Browse SJDs panel + sjd-start frontend call + SJD-03 warning); 10/10 test_sjd.py GREEN; 125/125 backend suite GREEN; 60/60 frontend tests GREEN; 4 plans of 4 done; pending 9-step human UAT |
| 23 | Writing Guide Integration | Plans 23-01 + 23-02 + 23-03 + 23-04 complete (RED baseline + duty_validator.py 4-rule implementation + POST /api/wd/{id}/validate-duties endpoint + dutyHints state + OG_DUTY_TIPS constant + client_service_results step + .duty-hint + .og-duty-tip CSS); 9/9 test_writing_guide.py GREEN; 134/134 backend suite GREEN; 60/60 frontend tests GREEN; 4 plans of 4 done; pending 4-step human UAT |
| 24 | Risk Audit | Ready to execute — 4 plans planned (24-01 through 24-04) |
| 25 | Accessible Template | Plans 25-01 + 25-02 + 25-03 complete (RED baseline + build_accessible_template.py + wd_accessible_template.docx with 29/29 vars self-verified + _factor_category_map helper + rewritten _build_wd_context producing all 29 Accessible Jinja2 vars + template path swap + wd_template.docx/build_wd_template.py retired; 6 RED tests now GREEN; 19/19 test_export.py passing; 150/150 full backend suite green; ACC-01/02/03/04 closed). Pending: 9-step human UAT |

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
| Accessible RED baseline uses 4 JES-shape fixtures (Phase 25 Plan 01) | EC + point-rating-with-Effort + point-rating-without-Effort + level-description exhausts the effort/conditions bucketing branches in _factor_category_map |
| _QUAL_SEED must include 'source' and 'last_modified' for QualificationStandard (Phase 25 Plan 01) | Pydantic model requires these; without them, PATCH /api/wd/{id} returns 500 — plan's default _QUAL_SEED omitted both |
| Capital-letter disambiguation: 'Effort' (heading) vs 'effort' (factor_name) (Phase 25 Plan 01) | Stable signal to distinguish Accessible section heading from TBS Factor column without parsing XML/heading styles |
| Strengthened 3 of 6 RED tests beyond plan-specified minimum to achieve 6/6 RED state (Phase 25 Plan 01) | Plan-specified test bodies (e.g., 'assert "Physical effort" in text') all PASS against current TBS template because JES Factor column already renders factor names. Added 1 extra assertion per test to make them meaningful RED gates |
| Accessible manifest uses {%p for entry in manifest %} paragraph loop, not build_wd_template.py's {%tr for m in manifest %} table loop (Phase 25 Plan 02) | The GoC Accessible reference document has no numbered manifest table; prose format matches reference. Plan 25-03 binds manifest via the existing _build_v2_manifest helper unchanged |
| Accessible build script duplicates _set_cell_text rather than refactoring to shared helper (Phase 25 Plan 02) | Followed established project convention (build_wd_template.py + build_poster_template.py also duplicate this 12-line helper). PATTERNS.md guidance: 'duplicating it a third time is the established convention, not an anti-pattern here' |
| wd_template.docx + build_wd_template.py retirement deferred to Plan 25-03 (Phase 25 Plan 02) | Avoids leaving the export route pointing at a deleted file mid-wave. Plan 25-03 swaps the path in _resolve_template_path call site FIRST, then deletes the old template after the 6 RED tests turn GREEN |

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
| Phase 25 P01 | 7 | 2 tasks | 1 files |
| Phase 25 P02 | 7min | 2 tasks | 2 files |
| Phase 25 P02 | 7min | 2 tasks | 2 files |
| Phase 25 P03 | 12 | 2 tasks | 3 files |

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
| Tests passing (after Phase 25) | 150 backend + 60 frontend (19 in test_export.py: 13 prior + 6 newly GREEN); 19 total export tests all GREEN |

**Completed Phase:** 25 Plan 03 (Accessible template export path + TBS retirement) — 2026-06-16T19:19Z

- export_service.py: import line extended to (EC_JES_ELEMENTS, JES_FACTORS_BY_GROUP, NON_EC_STANDARD_NAMES); _ADVISOR_PLACEHOLDER constant added; _factor_category_map() helper added (merges EC_JES_ELEMENTS + JES_FACTORS_BY_GROUP into {factor_name: category}); _build_wd_context rewritten to produce all 29 Accessible-template Jinja2 vars; generate_wd_docx template path swapped from wd_template.docx to wd_accessible_template.docx
- wd_template.docx (37,616 bytes TBS binary) + build_wd_template.py (249 lines TBS build script) retired via git rm
- SW/ED routing-code resolution replicated from jes_service.score_jes_v2 (lines 192-217) — routing_code is the key into JES_FACTORS_BY_GROUP
- 6 RED tests from Plan 25-01 now GREEN: test_accessible_effort_ec_populated, test_accessible_effort_fb_populated, test_accessible_effort_no_factor_group_placeholder, test_accessible_effort_level_description_placeholder, test_accessible_content_presence, test_accessible_structure_headings
- 19/19 test_export.py tests passing (13 original + 6 newly GREEN); 150/150 full backend suite green
- poster_template.docx + build_poster_template.py UNTOUCHED
- Commits: 9de26fd (Task 1: helper + rewrite), baa0440 (Task 2: path swap + retirement)
- Deviations: `grep -c 's.get("category")\|score.get("category")\|s["category"]' == 0` plan check returned 1 hit, but it's a docstring substring explaining WHY the code doesn't trust runtime category key (not actual code). The runtime code uses cat_map.get(s.get("factor_name", "")) exclusively.
- ACC-02/03/04 closed. Phase 25 is structurally complete (all 3 plans done); pending: 9-step human UAT of the Accessible-format DOCX.

**Previous Phase:** 25 Plan 02 (Accessible build script + .docx artifact) — 2026-06-16T19:06Z

- 306-line build_accessible_template.py (replicates build_wd_template.py idioms verbatim; 29/29 required Jinja2 vars self-declared)
- 37,872-byte wd_accessible_template.docx committed binary (4 tables, 14 headings, 43 paragraphs, 17-row position table in correct order, 7 Part 2 subsections)
- Self-verify tail: `python v2/backend/scripts/build_accessible_template.py` exits 0 with "Accessible template OK"
- 6 RED tests from Plan 25-01 still RED ("6 failed, 13 passed" — expected, export path not yet rewired)
- Commits: 5d60638 (Task 1: build script), 38630a9 (Task 2: .docx artifact)
- Deviations: none (plan acceptance check `grep -c '%tr for' == 2` was a miscount — 3 actual Jinja2 tags because plan's own amendments-verbatim instruction adds a 3rd; documented in SUMMARY)

**Previous Phase:** 25 Plan 01 (Accessible RED baseline) — 2026-06-16T18:54Z

- 4 fixture helpers (EC, FB-with-effort, MT-no-effort, AS-level-description)
- 6 RED tests (4 ACC-02 bucketing + 1 ACC-04 content-presence + 1 ACC-01 structure)
- Result: "6 failed, 13 passed" against current TBS template
- Commits: 9d1b007 (helpers), ab8ed77 (RED tests)
- Deviations: _QUAL_SEED needs source+last_modified (Pydantic); 3 tests strengthened beyond plan minimum for 6/6 RED state
