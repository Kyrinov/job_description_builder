---
phase: 26-org-context-conversational-step
plan: 02
subsystem: ui
tags: [org-context, conversational-step, co-update-rule, stepindex-resume, export-priority, react, fastapi, docxtpl, asvs-v5]

# Dependency graph
requires:
  - phase: 26-org-context-conversational-step
    provides: Plan 26-01 Wave 0 RED baseline — 8 stubs (3 backend + 5 frontend) gate this plan's tasks; each task's done criterion is a specific stub turning GREEN
  - phase: 25-accessible-template
    provides: Accessible DOCX export pipeline (_build_wd_context + _build_organizational_context_text + wd_accessible_template.docx) that the ORG-03 export priority change rides on
  - phase: 23-writing-guide-integration
    provides: client_service_results step + record field captured via the WG-03 conversational question (preview rendering was missing — added here as ORG-02 prerequisite)
provides:
  - org_context typed root field on WorkDescription + matching WDPatchRequest field (co-update rule enforced, max_length=4000 per ASVS V5)
  - 4-part OrgContextInput Socratic step in STEPS (work_stream / org_placement / reporting / additional → assembled string)
  - stepIndex resume-by-last-answered lazy useState initialiser (replaces integer useState(0); resilient to STEPS growth)
  - Organizational Context + Client Service Results Secs in DocumentPane (conditional, above Key Responsibilities)
  - export_service._build_wd_context prefers wd.org_context over synthesized fallback (no {{template leak}} when None)
  - FLASH + SECTION_NAMES entries for the new section keys (org_ctx, csr)
affects:
  - 27-responsibilities-narrative (uses the same WDPatchRequest co-update pattern + stepIndex resume invariant)
  - 28-manager-track-ux (org_context step appears in both advisor and manager flows)
  - 29-structured-export (org_context is one of the 7 Part 2 elements surfaced via JSON/CSV export)

# Tech tracking
tech-stack:
  added: []  # Plan 26-02 adds no libraries
  patterns:
    - "stepIndex resume-by-last-answered: STEPS.reduce walking STEP_RECORD_KEY[step.id] -> rec[key] !== undefined to find last answered index, then +1 (clamped to STEPS.length - 1). Replaces fragile integer useState(0) that broke on STEPS insertions."
    - "Co-update rule enforced via test gate: test_patch_<field>_round_trip stays RED until both WorkDescription.<field> and WDPatchRequest.<field> ship in the same git commit (extra='ignore' would silently drop unknown keys)."
    - "OrgContextInput 4-part assembly: local useState for sub-fields, handlePart re-assembles non-empty parts joined by single spaces, emits the assembled string via onChange. Parent step.apply writes a single typed string to record.org_context."
    - "DocumentPane conditional Sec numbering: n++ inside each `if (r.field)` block so downstream sections renumber dynamically when an optional section is hidden."
    - "Export priority idiom: `(wd.typed_field if wd.typed_field is not None else synthesized_fallback(wd))` — keeps the fallback path as a regression guard against {{template leak}}."

key-files:
  created: []
  modified:
    - v2/backend/app/models/work_description.py
    - v2/backend/app/api/wd.py
    - v2/backend/app/services/export_service.py
    - v2/frontend/src/app.jsx
    - v2/frontend/src/data.jsx
    - v2/frontend/src/components.jsx
    - v2/frontend/src/document.jsx
    - v2/frontend/src/app.test.jsx
    - v2/frontend/src/conversation.test.jsx

key-decisions:
  - "stepIndex resume fix landed FIRST (Task 1 Step A) before the STEPS org_context insertion (Task 2) — matches the critical implementation order in PATTERNS.md. Without the resume fix, a prior session persisted at integer stepIndex=20 (e.g. og_level) would land on the wrong step after Phase 26 inserts org_context at index 20."
  - "WD.org_context and WDPatchRequest.org_context committed in the SAME git commit (Task 1) per the v4.0 co-update rule. The Plan 26-01 executor had discovered the WIP backend edits uncommitted in the working tree; this plan picked them up verbatim and paired them with the matching app.jsx stepIndex + FLASH + SECTION_NAMES work."
  - "OrgContextInput NOT added to the components.jsx export initially per the plan, but the conversation.test.jsx stub imported it directly — added it to the export to make the test GREEN (matches Rule 1 fix from Wave 0: the placeholder required the import to exist)."
  - "stepIndex placeholder test in app.test.jsx rewritten with a real DOM assertion (data-testid=`jump-${stepIndex}` on the ActiveQuestion root .ask div) — verifies resume > 0 when localStorage has title + og_level answered. Avoids coupling to specific step text or visibility gates."
  - "OrgContextInput test uses container.querySelectorAll('textarea') instead of `screen` — `screen` is not in conversation.test.jsx's import block and adding it would touch the file's import surface unnecessarily. Pattern matches the existing fillInput helper in the same file."
  - "DocumentPane Secs numbered via dynamic n++ inside each conditional — when org_context OR csr is null, downstream sections (Key Responsibilities, Classification, DRF, Qualifications) renumber transparently. No hard-coded section numbers in the JSX."

patterns-established:
  - "Resume-by-last-answered is the canonical stepIndex initialiser from v4.0 onward — every future STEPS insertion (Phase 27 responsibilities_narrative, Phase 28 manager-track steps) inherits the resume invariant for free."
  - "4-part conversational sub-field component pattern (OrgContextInput): useState for sub-fields + assembled emit via onChange. Reusable for any future step whose persisted value is a single typed string assembled from multiple UI inputs (e.g. responsibilities_narrative may follow the same shape)."
  - "Sec conditional rendering with dynamic n++ — the canonical DocumentPane pattern for optional Part 2 sections. Phases 27/28/29 can add new Secs following this template without renumbering downstream sections."

requirements-completed:
  - ORG-01
  - ORG-02
  - ORG-03

# Metrics
duration: 14min
completed: 2026-06-23
---

# Phase 26 Plan 02: Org Context Conversational Step — Wave 1 GREEN Summary

**4-part OrgContextInput Socratic step + typed org_context field (WD + WDPatchRequest co-update, max_length=4000 per ASVS V5) + stepIndex resume-by-last-answered fix + DocumentPane Secs + export priority over synthesized fallback — all 8 Wave 0 RED stubs GREEN**

## Performance

- **Duration:** 14 min
- **Started:** 2026-06-23T18:50:37Z
- **Completed:** 2026-06-23T19:04:51Z
- **Tasks:** 3 (strict sequence; each task's output was a prerequisite for the next)
- **Files modified:** 9 (7 production + 2 test files where the Wave 0 placeholder had to be rewritten with a real assertion)

## Accomplishments
- All 8 RED stubs from Plan 26-01 are GREEN: `test_patch_org_context_round_trip` (backend WD co-update), `test_org_context_in_export` + `test_org_context_fallback_in_export` (backend export priority), `stepIndex resume` (frontend app.jsx), `STEPS contains org_context step` + `OrgContextInput calls onChange` (frontend components/data), `renders Organizational Context section` + `renders Client Service Results section` (frontend document.jsx)
- 4-part OrgContextInput component renders 4 labelled textareas (work_stream / org_placement / reporting / additional) and assembles them into a single typed string emitted via onChange; the assembled string flows through STEPS.apply → record.org_context → PATCH /api/wd → WorkDescription.org_context (typed root field) → export_service organizational_context_text
- stepIndex lazy initialiser replaces `useState(0)` with a STEP_RECORD_KEY-driven reduce over localStorage; existing sessions now resume at the step AFTER the last answered one instead of an integer position that drifts when STEPS grows
- DocumentPane renders Organizational Context + Client Service Results Secs above Key Responsibilities (conditional on the respective record fields; section number renumbers dynamically when either is hidden)
- export_service._build_wd_context prefers `wd.org_context` over `_build_organizational_context_text(wd)`; the synthesized fallback stays as a regression guard so a blank org_context still renders without a {{template leak}}
- Backend suite: 153 passed (150 pre-existing + 3 Wave 0 stubs all GREEN); Frontend suite: 65 passed (60 pre-existing + 5 Wave 0 stubs all GREEN); 0 failures

## Task Commits

Each task was committed atomically in strict sequence:

1. **Task 1: stepIndex resume fix + WorkDescription/WDPatchRequest co-update** — `c7266db` (feat) — 4 files (app.jsx + app.test.jsx + work_description.py + wd.py) in ONE commit per the co-update rule
2. **Task 2: OrgContextInput + STEPS org_context insertion** — `f81753b` (feat) — 3 files (components.jsx + data.jsx + conversation.test.jsx)
3. **Task 3: DocumentPane Secs + export_service org_context priority** — `1d49574` (feat) — 2 files (document.jsx + export_service.py)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `v2/backend/app/models/work_description.py` — added `org_context: Optional[str] = None` typed root field on WorkDescription (Phase 26 — ORG-01)
- `v2/backend/app/api/wd.py` — added `org_context: Optional[str] = Field(default=None, max_length=4000)` on WDPatchRequest (co-update rule; max_length per ASVS V5 DoS mitigation T-26-01)
- `v2/backend/app/services/export_service.py` — `_build_wd_context` now returns `wd.org_context if wd.org_context is not None else _build_organizational_context_text(wd)` for the `organizational_context_text` Jinja2 var (Phase 26 — ORG-03)
- `v2/frontend/src/app.jsx` — stepIndex lazy initialiser (STEP_RECORD_KEY map + STEPS.reduce resume-by-last-answered); FLASH entries for org_context + client_service_results; SECTION_NAMES entries for org_ctx + csr
- `v2/frontend/src/data.jsx` — new STEPS entry `{ id: 'org_context', phase: 3, icon: I.org, input: { type: 'org_context_input' }, apply: (r, a) => ({ org_context: a }) }` inserted BEFORE client_service_results
- `v2/frontend/src/components.jsx` — OrgContextInput component (4-part local state + assembled emit); StepInput dispatch for 'org_context_input'; answerValid requires non-empty trimmed string; initialAnswer returns ''; OrgContextInput added to export block
- `v2/frontend/src/document.jsx` — two conditional Secs in DocumentPane: Organizational Context (key='org_ctx') + Client Service Results (key='csr'), both rendered above Key Responsibilities with full amendment props
- `v2/frontend/src/app.test.jsx` — replaced Wave 0 stepIndex placeholder with real DOM assertion against data-testid=`jump-${stepIndex}` on the ActiveQuestion root
- `v2/frontend/src/conversation.test.jsx` — added OrgContextInput import; replaced Wave 0 placeholder with real render + fireEvent.change + onChange assertion

## Decisions Made
- **Critical implementation order followed verbatim from PATTERNS.md §"Critical Implementation Order"**: (1) stepIndex resume fix FIRST, (2) WD + WDPatchRequest co-update SAME commit, (3) STEPS org_context entry, (4) document.jsx Secs, (5) export priority. Each step's output was a prerequisite for the next.
- **OrgContextInput added to components.jsx export block**: Wave 0 placeholder test (Rule 1 fix in commit edfc9ba) documented that the real assertion required `OrgContextInput` to be importable from `./components.jsx`. Task 2 honoured this by adding it to the export line alongside OgLevelQuestions and OgLevelPicker.
- **OrgContextInput test uses container pattern, not screen**: `screen` was not in conversation.test.jsx's import block. Adding it would have expanded the file's import surface unnecessarily. `container.querySelectorAll('textarea')` returns the same NodeList and matches the existing fillInput helper's idiom in the same file.
- **DocumentPane Sec numbering is dynamic**: each new Sec wraps its `n++` inside the `if (r.field)` block so downstream sections renumber transparently when org_context or csr is null. Phases 27/28/29 can add new conditional Secs following this template without renumbering anything downstream.
- **Export priority preserves the fallback path**: `_build_organizational_context_text(wd)` is intentionally NOT removed — it stays as the synthesized fallback when `wd.org_context is None`. The fallback test (`test_org_context_fallback_in_export`) from Wave 0 was already GREEN and stays GREEN as a regression guard against accidental {{template leak}}.
- **`act()` warnings in conversation.test.jsx are pre-existing**: React's "update to App inside a test was not wrapped in act(...)" warning fires for the OGX-04 bugfix round 3 tests. These existed before Phase 26 and are out of scope (Scope Boundary: pre-existing warnings are not auto-fixed).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] stepIndex resume test left as `expect(true).toBe(false)` placeholder after the resume fix landed**
- **Found during:** Task 1 verification (frontend suite after app.jsx + work_description.py + wd.py commit)
- **Issue:** Wave 0 wrote the stepIndex resume test as a placeholder (`expect(true).toBe(false)`) because the implementation didn't exist yet. After Task 1 added the lazy initialiser, the placeholder still failed — but for the wrong reason (assertion error, not the resume logic). The plan's done criterion ("stepIndex stub in app.test.jsx now passes") required a real assertion.
- **Fix:** Replaced the placeholder with a real DOM assertion: render `<App />` after seeding localStorage with `{ title, og_level: 3 }`, query the ActiveQuestion root via `[data-testid^="jump-"]`, parse the stepIndex from the testid, assert `idx > 0`. Uses the existing `dataTestid={\`jump-${stepIndex}\`}` prop already wired through ActiveQuestion (conversation.jsx line 64).
- **Files modified:** `v2/frontend/src/app.test.jsx`
- **Verification:** `npm test -- --run app.test.jsx` — 11/11 GREEN including stepIndex resume.
- **Committed in:** `c7266db` (Task 1 commit — included with the implementation since the test asserts the implementation's behaviour)

**2. [Rule 1 - Bug] OrgContextInput test placeholder required the named export to exist**
- **Found during:** Task 2 verification (conversation.test.jsx after OrgContextInput implementation)
- **Issue:** Wave 0 wrote the OrgContextInput test as `expect(true).toBe(false)` because importing a non-exported name would have surfaced as ReferenceError. Task 2 added the component but the plan said "OrgContextInput does NOT need to be added to the export line". The placeholder still failed because the real assertion required the import.
- **Fix:** Added OrgContextInput to the components.jsx export block (alongside OgLevelQuestions, OgLevelPicker). Replaced the placeholder with a real assertion: render `<OrgContextInput value="" onChange={onChange} />`, query textareas via `container.querySelectorAll('textarea')`, fire change on the first, assert `onChange.toHaveBeenCalledWith(expect.stringContaining('Strategic Policy program'))`. Uses `container` pattern instead of `screen` (which is not in the file's import block).
- **Files modified:** `v2/frontend/src/components.jsx` (export line), `v2/frontend/src/conversation.test.jsx` (import + test body)
- **Verification:** `npm test -- --run conversation.test.jsx` — 41/41 GREEN including OrgContextInput assembly.
- **Committed in:** `f81753b` (Task 2 commit)

**3. [Rule 1 - Bug] getVisibleSteps expected STEPS.length === 22; now 23 after org_context insertion**
- **Found during:** Task 2 verification (full frontend suite after STEPS insertion)
- **Issue:** `conversation.test.jsx` had a hardcoded count `expect(visible.length).toBe(13)` derived from `22 STEPS - 9 gated cluster steps = 13 visible`. After Phase 26 inserted the unconditional org_context step, STEPS grew to 23 → visible grew to 14.
- **Fix:** Updated the expected count from 13 to 14 and the test name from `(22 - 9 = 13)` to `(23 - 9 = 14)`. Added a comment explaining the Phase 26 cause. The test's structural assertions (which steps are hidden) are unchanged — only the count drifted.
- **Files modified:** `v2/frontend/src/conversation.test.jsx`
- **Verification:** `npm test -- --run conversation.test.jsx` — getVisibleSteps test GREEN.
- **Committed in:** `f81753b` (Task 2 commit)

**4. [Rule 1 - Bug] OGX-04 loop test "also handles the other 3 sectors" failed because resume-by-last-answered hydrated from stale localStorage**
- **Found during:** Task 2 verification (full frontend suite after STEPS insertion)
- **Issue:** The test loops through 3 sectors, rendering `<App />` 3 times in one `it()` block. There is no `localStorage.clear()` between iterations. After Task 1 added the resume-by-last-answered initialiser, the second iteration's render hydrated App with the first iteration's persisted record — App resumed past step 0 and the `fillInput(container, 'Worker')` call at the start of the loop body threw "input not found" (the active step wasn't a text input).
- **Fix:** Added `globalThis.localStorage.clear()` at the start of each loop iteration so every render starts at the Title step (matches the test's intent of walking the conversation from scratch for each sector).
- **Files modified:** `v2/frontend/src/conversation.test.jsx`
- **Verification:** `npm test -- --run conversation.test.jsx` — loop test GREEN for all 3 sectors.
- **Committed in:** `f81753b` (Task 2 commit)

---

**Total deviations:** 4 auto-fixed (4 Rule 1 bugs — all direct consequences of this plan's changes; 3 were placeholder-test rewrites required by the plan's done criteria, 1 was a stale-state interaction between Task 1's resume fix and a pre-existing loop test)
**Impact on plan:** All auto-fixes necessary to satisfy the plan's done criteria ("stepIndex stub in app.test.jsx now passes", "OrgContextInput assembly test GREEN", "all 60 pre-existing frontend tests remain GREEN"). No scope creep. No production code beyond what the plan specified.

## Issues Encountered
- **WIP backend changes from prior session verified, not redone:** At executor start, the working tree contained uncommitted modifications to `v2/backend/app/models/work_description.py` and `v2/backend/app/api/wd.py` (exactly the Task 1 Steps B + C edits). Per the prompt's `<important_notes>`, these were left untouched and committed as-is in Task 1's co-update commit alongside the new app.jsx work.
- **Pre-existing `act()` warnings in conversation.test.jsx:** React warns "An update to App inside a test was not wrapped in act(...)" for the OGX-04 bugfix round 3 tests (app.jsx:196). These warnings existed before Phase 26 and are unrelated to this plan's changes. Out of scope (Scope Boundary rule).

## User Setup Required

None — Plan 26-02 is pure code (no external services, no environment variables, no UI verification beyond what the automated tests cover). The Phase 26 human UAT items (rendering the org_context step in a live browser, downloading an Accessible JD DOCX with org_context populated) will be captured in a `26-HUMAN-UAT.md` if the user requests one.

## Next Phase Readiness
- **Phase 26 is structurally complete.** Both plans done: 26-01 (Wave 0 RED baseline) + 26-02 (Wave 1 GREEN). ORG-01/02/03 requirements delivered.
- **Phase 27 (Responsibilities Narrative + Completeness Audit) is unblocked.** It will reuse:
  - The WDPatchRequest co-update pattern (responsibilities_narrative will be a new typed root field with a matching PATCH round-trip test)
  - The stepIndex resume-by-last-answered invariant (a new STEPS entry inherits resume for free)
  - The DocumentPane conditional Sec pattern with dynamic n++ (a new Sec for responsibilities_narrative will follow the org_ctx template)
  - The OrgContextInput 4-part assembly pattern if responsibilities_narrative also captures multiple sub-fields (decision-impact, delegation-scope, etc.)
- **No blockers.** All 8 Wave 0 stubs are GREEN; full suite (153 backend + 65 frontend) is GREEN; co-update rule is enforced; stepIndex resume works correctly across STEPS insertions.

## Self-Check: PASSED

Created/modified files verified on disk:
- FOUND: v2/backend/app/models/work_description.py
- FOUND: v2/backend/app/api/wd.py
- FOUND: v2/backend/app/services/export_service.py
- FOUND: v2/frontend/src/app.jsx
- FOUND: v2/frontend/src/data.jsx
- FOUND: v2/frontend/src/components.jsx
- FOUND: v2/frontend/src/document.jsx
- FOUND: v2/frontend/src/app.test.jsx
- FOUND: v2/frontend/src/conversation.test.jsx

Task commits verified in git log:
- FOUND: c7266db (feat — Task 1: stepIndex + co-update)
- FOUND: f81753b (feat — Task 2: OrgContextInput + STEPS)
- FOUND: 1d49574 (feat — Task 3: DocumentPane Secs + export priority)

Test counts verified:
- Backend: 153 passed, 0 failed (target was 153+; met)
- Frontend: 65 passed, 0 failed (target was 65+; met)
- All 8 Phase 26 RED stubs from Plan 26-01 confirmed GREEN via verbose test reporter

Phase gate spot-checks verified:
- Co-update rule: `org_context` present in BOTH work_description.py and wd.py ✓
- STEPS order: `org_context` (line 664) appears BEFORE `client_service_results` (line 671) in data.jsx ✓
- Document preview order: `key="org_ctx"` (line 307) → `key="csr"` (line 328) → `key="du"` (line 346) in document.jsx ✓
- Export priority: `wd.org_context` appears in export_service.py inside `_build_wd_context` ✓
- max_length=4000 on WDPatchRequest.org_context (T-26-01 mitigation) ✓

---
*Phase: 26-org-context-conversational-step*
*Plan: 02 (Wave 1 GREEN implementation)*
*Completed: 2026-06-23*
