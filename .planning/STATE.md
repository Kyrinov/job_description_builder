---
gsd_state_version: 1.0
milestone: v4.0
milestone_name: Seven-Elements Conversational Architecture
current_phase: 28
status: executing
last_updated: "2026-06-24T18:05:25.800Z"
progress:
  total_phases: 9
  completed_phases: 8
  total_plans: 30
  completed_plans: 30
  percent: 100
---

# Project State

**Status:** Executing Phase 28 (Plans 01 + 02 complete; awaiting phase verification)
**Current phase:** 28
**Last updated:** 2026-06-24
**Next action:** Phase 28 verification by orchestrator (Plan 02 complete; MGR-01/02/03 all closed)

---

## Phase Status

| Phase | Name | Status |
|-------|------|--------|
| 21 | OG Expansion + Preview Fix | Complete (9 plans incl. 21-09 gap-closure); 60/60 frontend tests; JES-LEV-01 + OGX-07 closed |
| 22 | SJD Library | Complete (4 plans); 10/10 test_sjd.py GREEN; 125/125 backend suite GREEN; 60/60 frontend tests GREEN; pending 9-step human UAT |
| 23 | Writing Guide Integration | Complete (4 plans); 9/9 test_writing_guide.py GREEN; 134/134 backend suite GREEN; 60/60 frontend tests GREEN; pending 4-step human UAT |
| 24 | Risk Audit | Complete (4 plans) |
| 25 | Accessible Template | Complete (3 plans); 19/19 test_export.py + 150/150 full backend suite green; wd_accessible_template.docx live (37,872 bytes, 3 tables, 14 headings, 7 Part 2 subsections); TBS template + build script retired; poster unchanged; ACC-01/02/03/04 closed; pending 9-step human UAT |
| 26 | Org Context Conversational Step | **Complete** — Plan 01 (Wave 0 RED baseline) + Plan 02 (Wave 1 GREEN) both done; 8/8 RED stubs GREEN; 153/153 backend + 65/65 frontend GREEN; ORG-01/02/03 closed |
| 27 | Responsibilities Narrative + Completeness Audit | Complete (Plan 01 RESP vertical slice + Plan 02 ELEM completeness audit); 172 backend + 70 frontend GREEN; RESP-01/02/03 + ELEM-01/02/03 closed |
| 28 | Manager-Track UX | Plan 01 + Plan 02 both complete (MGR-01 + MGR-02 + MGR-03 all closed); 179 backend + 85 frontend GREEN; awaiting phase verification |
| 29 | Structured Export + Enhanced Poster | Not started |

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
- WDPatchRequest co-update rule (v4.0 addition): every new WorkDescription field that is advisor-patchable must have a corresponding WDPatchRequest field added in the same git commit, with a roundtrip test gating merge

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

### v4.0 Key Decisions (to be populated as phases execute)

| Decision | Rationale |
|----------|-----------|
| org_context and responsibilities_narrative as typed root fields on WorkDescription (not in record dict) | Export pipeline reads typed fields directly; record blob is freeform and unreliable for structured export |
| WDPatchRequest co-update rule enforced in Phases 26 and 27 | Silent PATCH drop (extra="ignore" swallows unknown keys with HTTP 200) has caused UAT regressions in prior phases |
| stepIndex regression fix must land in Phase 26 before any STEPS insertion | Resume by STEPS.findLastIndex(s => answers[s.id] !== undefined) instead of integer position; existing sessions must survive STEPS growth |
| user_role in localStorage only — never in WD model or answers dict | Role is session preference, not document data; sending it in PATCH body would write it to work_descriptions.data |
| build_seven_elements(wd) -> dict shared helper in export_service.py | Single source of truth for 7-element data; consumed by JSON route, CSV route, and completeness audit |
| require_og_confirmed bypassed for manager-track WDs via wd_type field on WorkDescription | Manager WDs deliberately never have confirmed_og; bypass enables export without breaking the advisor gate |
| Completeness audit reads wd.org_context (typed field), not derived fallback text | _build_organizational_context_text() returns non-empty synthesized string even when advisor skipped the step — would produce false positive in audit |
| Wave 0 RED baseline plan shape for v4.0 conversation steps (Phase 26 Plan 01) | 8 stubs (3 backend, 5 frontend) gate the implementation plan; each Wave 1 task references a specific stub as its done criterion; pre-existing 150 backend + 60 frontend must stay GREEN as a contract |
| OrgContextInput test uses expect(true).toBe(false) placeholder per plan fallback rule (Phase 26 Plan 01) | OrgContextInput is not yet exported from components.jsx; an eager import would surface as ReferenceError (crash, not assertion). Placeholder documents the real assertion to wire when Plan 26-02 Task 2 adds the export |
| Wave 0 marks NO requirements complete — ORG-01/02/03 stay Pending until Plan 26-02 turns RED → GREEN (Phase 26 Plan 01) | Wave 0 delivers tests, not user-facing functionality; marking requirements complete pre-implementation would misrepresent milestone progress |
| stepIndex resume-by-last-answered replaces useState(0) as the canonical initialiser (Phase 26 Plan 02) | STEP_RECORD_KEY map + STEPS.reduce walks record keys to find last answered step + 1; resilient to STEPS growth — every future step insertion (Phase 27/28/29) inherits the resume invariant for free |
| OrgContextInput 4-part assembly pattern for multi-sub-field conversational steps (Phase 26 Plan 02) | Local useState per sub-field, handlePart re-assembles non-empty parts joined by spaces, emits single typed string via onChange; reusable template for any future step whose persisted value is an assembled string (e.g. Phase 27 responsibilities_narrative if it captures decision-impact + delegation-scope) |
| DocumentPane conditional Sec with dynamic n++ (Phase 26 Plan 02) | Wrap each new Sec's n++ inside `if (r.field)` so downstream sections renumber transparently when optional sections are hidden; canonical template for Phase 27/28/29 Part 2 additions |
| Export priority idiom preserves synthesized fallback as regression guard (Phase 26 Plan 02) | `wd.org_context if wd.org_context is not None else _build_organizational_context_text(wd)` keeps the fallback path live so blank advisor input still renders without {{template leak}}; test_org_context_fallback_in_export stays GREEN indefinitely as a guard |

### Active Blockers

None. v3.0 complete (Phase 25 done). v4.0 roadmap ready. Phase 26 unblocked.

### Roadmap Evolution

- v1.0 closed 2026-06-03: Phases 1–9 (incl. 8.1), 188 tests, 21/21 requirements
- v2.0 closed 2026-06-10: Phases 10–20, 299 tests (80 backend + 31 frontend + 188 v1), 52/52 requirements
- v3.0 closed 2026-06-16: Phases 21–25, 150 backend + 60 frontend tests, 24/24 requirements
- v4.0 started 2026-06-19: Phases 26–29, 16 requirements, roadmap defined

---

## Performance Metrics

### v1.0 (archived)

| Metric | Value |
|--------|-------|
| Phases total | 10 (incl. 8.1) |
| Requirements delivered | 21/21 |
| Tests passing at ship | 188 |
| Timeline | 7 days (2026-05-27 → 2026-06-03) |
| Phase 26 P02 | 14min | 3 tasks | 9 files |
| Phase 28 P02 | 378 | 2 tasks | 5 files |

### v2.0 (complete)

| Metric | Value |
|--------|-------|
| Phases total | 11 (10–20) |
| Requirements delivered | 52/52 |
| Tests passing at ship | 299 (80 backend + 31 frontend + 188 v1) |
| Timeline | 7 days (2026-06-03 → 2026-06-10) |

### v3.0 (complete)

| Metric | Value |
|--------|-------|
| Phases total | 5 (21–25) |
| Requirements delivered | 24/24 |
| Tests passing at ship | 150 backend + 60 frontend |
| Timeline | 2026-06-10 → 2026-06-16 |

### v4.0 (active)

| Metric | Value |
|--------|-------|
| Phases total | 4 (26–29) |
| Requirements total | 16 |
| Tests passing at start | 150 backend + 60 frontend |
| Started | 2026-06-19 |

**Completed Plan:** 26 Plan 02 (Org Context Wave 1 GREEN implementation) — 2026-06-23T19:04Z

- 7 production files + 2 test files modified across 3 atomic task commits (strict sequence):
  - Task 1 (`c7266db` feat): stepIndex resume-by-last-answered lazy initialiser in app.jsx (STEP_RECORD_KEY + STEPS.reduce); FLASH + SECTION_NAMES entries for org_ctx + csr; org_context: Optional[str] = None on WorkDescription; org_context: Optional[str] = Field(default=None, max_length=4000) on WDPatchRequest (co-update rule — same commit); app.test.jsx stepIndex placeholder rewritten with real DOM assertion
  - Task 2 (`f81753b` feat): OrgContextInput component (4-part local state, assembled emit); StepInput dispatch + answerValid + initialAnswer extensions; org_context step in STEPS before client_service_results; OrgContextInput added to components.jsx export; conversation.test.jsx placeholder rewritten with real render + fireEvent + onChange assertion
  - Task 3 (`1d49574` feat): DocumentPane Secs for Organizational Context (key='org_ctx') + Client Service Results (key='csr') above Key Responsibilities with dynamic n++ renumbering; export_service._build_wd_context prefers wd.org_context over synthesized fallback (fallback retained as regression guard)
- All 8 Wave 0 RED stubs are GREEN: 3 backend (test_patch_org_context_round_trip, test_org_context_in_export, test_org_context_fallback_in_export) + 5 frontend (stepIndex resume, STEPS shape, OrgContextInput assembly, Organizational Context Sec, Client Service Results Sec)
- Backend suite: 153 passed, 0 failed (150 pre-existing + 3 Wave 0 stubs all GREEN)
- Frontend suite: 65 passed, 0 failed (60 pre-existing + 5 Wave 0 stubs all GREEN)
- Deviations: 4 Rule 1 auto-fixes — (1) stepIndex placeholder test rewritten with real assertion (required by plan's done criterion), (2) OrgContextInput placeholder rewritten + added to components.jsx export (required by plan's done criterion), (3) getVisibleSteps expected count updated from 13 to 14 (STEPS grew by 1 after org_context insertion), (4) OGX-04 loop test "also handles the other 3 sectors" needed localStorage.clear() between iterations (Task 1 resume fix interacted with stale localStorage from prior iteration)
- ORG-01/02/03 marked complete in REQUIREMENTS.md (Wave 1 delivers user-visible functionality: 4-part Socratic step, document preview Secs, DOCX export priority)
- Phase 26 structurally complete; Phase 27 (Responsibilities Narrative + Completeness Audit) is unblocked — will reuse WDPatchRequest co-update pattern, stepIndex resume invariant, DocumentPane conditional Sec template, and possibly OrgContextInput 4-part assembly pattern

**Completed Plan:** 26 Plan 01 (Org Context Wave 0 RED baseline) — 2026-06-23T18:44Z

- 8 RED test stubs added across 5 existing test files (no production code touched):
  - Backend (3): test_patch_org_context_round_trip (test_wd.py, KeyError — gates WDPatchRequest co-update for ORG-01), test_org_context_in_export + test_org_context_fallback_in_export (test_export.py, gates ORG-03 export priority change)
  - Frontend (5): stepIndex resume (app.test.jsx, placeholder), STEPS org_context shape + OrgContextInput assembly (conversation.test.jsx), Organizational Context Sec + Client Service Results Sec (document.test.jsx)
- Baseline verified: 150/150 pre-existing backend GREEN + 2/3 new backend RED (test_org_context_fallback_in_export already GREEN per commit 05ad815 — retained as regression guard); 60/60 pre-existing frontend GREEN + 5/5 new frontend RED with AssertionErrors
- Commits: 05ad815 (Task 1: backend stubs), d015227 (Task 2: frontend stubs), edfc9ba (Rule 1 fix: OrgContextInput placeholder per plan fallback rule)
- Deviations: 1 Rule 1 fix (OrgContextInput stub originally failed with ReferenceError instead of AssertionError — plan's done criterion violated; rewrote with expect(true).toBe(false) placeholder pattern that the plan explicitly sanctions for non-exported identifiers)
- Out-of-scope discovery: working tree had Wave 1 production WIP uncommitted (org_context field on WorkDescription + WDPatchRequest); stashed for clean RED verification, restored untouched — belongs to Plan 26-02 Task 1
- ORG-01/02/03 left Pending in REQUIREMENTS.md (Wave 0 delivers tests, not user-visible functionality)
- Next: Plan 26-02 (Wave 1 implementation) turns the 8 RED stubs GREEN; implementation order from PATTERNS.md §"Critical Implementation Order" must be respected (stepIndex resume fix FIRST, then WD co-update, then STEPS, then document Secs, then export priority)

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

**Planned Phase:** 28 (Manager-Track UX) — 2 plans — 2026-06-24T16:42:00.020Z

**Completed Plan:** 28 Plan 01 (Manager-Track Foundation Vertical Slice — MGR-01 + MGR-03) — 2026-06-24T17:51Z

- 3 atomic task commits (strict TDD-within-task sequence):
  - Task 1 (`e7e3d0b` feat): wd_type co-update — `WorkDescription.wd_type: Literal['advisor','manager']='advisor'` (typing.Literal added to imports) + `WDCreateRequest.wd_type` (default advisor) + `WDPatchRequest.wd_type: Optional[...] = None` (user_role intentionally ABSENT — D-28-03 contract) + `create_wd(wd_type=body.wd_type, ...)` wiring — ALL 4 land in the same commit (co-update rule)
  - Task 2 (`93b1a1e` feat): require_og_confirmed manager bypass (getattr-safe, default 'advisor' preserves old WD rows) + `_apply_draft_watermark(file_bytes)` helper (python-docx inserts bold dark-red centered 'DRAFT — PENDING CLASSIFICATION' at DOCX index 0) + generate_wd_docx applies it when `getattr(wd, 'wd_type', 'advisor') == 'manager'`; advisor WDs untouched
  - Task 3 (`49b51e4` feat): MANAGER_SKIP_STEPS filter on isStepVisible / getVisibleSteps (additive optional userRole param) + exported; RoleSelector first-load screen (data-testid='role-selector'/role-advisor/role-manager); userRole useState declared BEFORE stepIndex (TDZ-free closure for resume reduce); userRole hydrates from `jd-builder-v2-role` localStorage; stepIndex resume reduce skips MANAGER_SKIP_STEPS in manager mode; activeStepIndex useMemo passes userRole; `wdPayload.wd_type = userRole === 'manager' ? 'manager' : 'advisor'`; exportAs guard bypassed for manager (no OG required for manager export); main render wrapped with role gate (returns `<RoleSelector>` when userRole is null, main shell otherwise)
- Tests: 179 backend GREEN (172 pre-existing + 4 wd_type round-trip / default-advisor / user_role-dropped guard / manager-preserved + 3 manager-bypass / DRAFT-watermark / advisor-still-409) + 76 frontend GREEN (70 pre-existing + 3 MGR-01 role-selector + 3 MGR-03 manager-STEPS-variant)
- Deviations: 4 Rule 1/2/3 auto-fixes — (1) userRole useState moved BEFORE stepIndex (TDZ constraint — lazy initializer closes over userRole for manager-skip guard in resume reduce), (2) resetStorage() now calls globalThis.localStorage.clear() instead of _store.clear() (vitest.setup.js installs its own InMemoryStorage with a different closure-bound _store; the test file's _store was unused), (3) manager-shorter test assertion relaxed to `toBeLessThan` with explicit spot-checks on the 3 NEW skips (og_level_questions is already hidden by the level-description gate when answers.og_confirm is empty, so manager mode adds 3 not 4), (4) seeded jd-builder-v2-role='advisor' in 5 existing test setups (more than anticipated by plan)
- MGR-01 + MGR-03 marked complete in REQUIREMENTS.md (Plan 01 delivers user-visible functionality: role selector, manager STEPS variant, manager DOCX export without 409); MGR-02 stays Pending (Plan 02 scope — UI suppression layer)
- Phase 28 Plan 02 (Wave 2 MGR-02) is unblocked — will reuse userRole state slice, record.wd_type, and MANAGER_SKIP_STEPS for conditional ClassifyBadge / Classification Sec / ReviewState audit panel rendering

**Completed Plan:** 28 Plan 02 (Manager-Mode UI Suppression — MGR-02) — 2026-06-24T18:04Z

- 2 atomic task commits (strict TDD-within-task sequence):
  - Task 1 (`4090f38` feat): MGR-02 UI suppression — `userRole = 'advisor'` added to DocumentPane + ReviewState signatures (10th + 11th additive prop, preserves all 76 pre-existing advisor-mode call sites); DocumentPane Classification Sec gets a new `if (userRole === 'manager')` branch placed FIRST (before the existing `!r.confirmed_og || !r.og_level` check) that pushes a Sec with src="To be completed by classification team" + a classification-team placeholder body; Position Identification Sec's `classificationValue` becomes `'To be completed'` literal in manager mode + CAF rank advisory wrapped in `{userRole !== 'manager' && (...)}` (both are classification internals); ReviewState `checks` array built with conditional spread (manager mode drops the "Classified as {code} · {points} pts" line entirely); entire audit panel (button + clean-findings + findings list) wrapped in `{userRole !== 'manager' && (<>...</>)}` fragment; ClassifyBadge gated at app.jsx call site with `{userRole !== 'manager' && <ClassifyBadge cls={cls} />}` (component itself stays role-agnostic)
  - Task 2 (`b6e6071` feat): MGR-02 systematic inspection tests — 3 new tests (2 DocumentPane + 1 ReviewState) render a fully-populated record (confirmed_og=EC, og_level=4, jes_total_points=250, jes_scores with Decision making + Knowledge of specialized fields) in manager mode and assert ABSENCE of every known classification string (OG code, JES factor names, "Classified as", "Occupational group", "CBA", "article 32.01", "Run compliance audit", "Compliance Findings"). Tests turn GREEN immediately because Task 1 suppression layer is in place; the tests LOCK the MGR-02 contract against any future regression
- Tests: 179 backend GREEN (unchanged from Plan 01) + 85 frontend GREEN (76 pre-Plan-28 + 6 Plan 01 + 3 DocumentPane MGR-02 + 3 ReviewState MGR-02 + 3 MGR-02 inspection); 9 new tests in Plan 02 (4 RED stubs + 2 advisor regression guards + 3 inspection tests)
- Deviations: 1 Rule 2 auto-fix — Position Identification Sec's Classification metaItem also gated in manager mode (initial Task 1 implementation only suppressed the Classification & Evaluation Sec; the inspection test "no OG-code classification string" caught the second surface — the metaItem was rendering "EC-04" in the position metadata table). Fixed by extending the manager branch in DocumentPane to cover both surfaces (Classification Sec + Position Identification Sec metaItem + CAF rank advisory wrap)
- MGR-02 marked complete in REQUIREMENTS.md (Plan 02 delivers user-visible functionality: manager-mode UI never shows OG codes, JES factor names, or CBA citations — locked by automated inspection tests)
- Phase 28 is structurally complete (Plans 01 + 02 both done; MGR-01/02/03 all closed). Phase 29 (Structured Export + Enhanced Poster) is unblocked — will reuse the userRole conditional render pattern (Manager-mode JSON/CSV exports will be similarly filtered) and the MGR-02 inspection test pattern (any new visible UI element that could leak classification internals should add a corresponding `not.toMatch` assertion)
