---
phase: 27-responsibilities-narrative-completeness-audit
plan: 01
subsystem: ui
tags: [responsibilities-narrative, conversational-step, co-update-rule, document-preview, docxtpl, asvs-v5, react, fastapi, accessibility]

# Dependency graph
requires:
  - phase: 27-responsibilities-narrative-completeness-audit
    provides: Plan 27-01 Wave 1 GREEN — 5 stub tests gate this plan's tasks; each task's done criterion is a specific stub turning GREEN
  - phase: 26-org-context-conversational-step
    provides: org_context typed field + WDPatchRequest co-update + stepIndex resume-by-last-answered + DocumentPane conditional Sec with dynamic n++ + export priority pattern — RESP vertical slice mirrors this exactly
  - phase: 25-accessible-template
    provides: Accessible DOCX export pipeline (_build_wd_context + _ADVISOR_PLACEHOLDER + wd_accessible_template.docx) that the RESP-03 export priority change rides on; responsibilities_text is the Part 2 Responsibility Jinja2 variable
  - phase: 23-writing-guide-integration
    provides: client_service_results step + client_service_results TextArea pattern (RESP-01 mirrors it — single free-text textarea, no new component)
provides:
  - responsibilities_narrative: Optional[str] typed root field on WorkDescription + matching WDPatchRequest field (co-update rule enforced, max_length=4000 per ASVS V5 T-27-01)
  - Free-text responsibilities_narrative conversational step in STEPS (textarea, no new component, R-RESP-01 simplification)
  - Responsibilities Sec in DocumentPane (conditional, above Key Responsibilities, dynamic n++ renumbering)
  - FLASH + SECTION_NAMES + STEP_RECORD_KEY entries for responsibilities_narrative / resp_narrative (stepIndex resume inherits for free)
  - export_service._build_wd_context sources responsibilities_text from wd.responsibilities_narrative (narrative or _ADVISOR_PLACEHOLDER, NOT JES-derived factors)
  - wdPayload mirror list extended to include responsibilities_narrative (mirrors org_context) so PATCH /api/wd persists the typed root field on every commit
affects:
  - 27-02-completeness-audit (uses responsibilities_narrative in build_seven_elements + validate-elements R-ELEM-01c)
  - 28-manager-track-ux (responsibilities_narrative step appears in both advisor and manager flows)
  - 29-structured-export (responsibilities_narrative is one of the 7 Part 2 elements surfaced via JSON/CSV export)

# Tech tracking
tech-stack:
  added: []  # Plan 27-01 adds no libraries
  patterns:
    - "Co-update rule enforced via test gate (RESP-01): test_patch_<field>_round_trip stays RED until both WorkDescription.<field> and WDPatchRequest.<field> ship in the same git commit (extra='ignore' would silently drop unknown keys with HTTP 200)."
    - "max_length=4000 on WDPatchRequest.responsibilities_narrative (T-27-01, mirrors T-26-01 for org_context): Pydantic rejects strings over 4000 chars with HTTP 422 — ASVS V5 DoS mitigation."
    - "Free-text textarea step (RESP-01): no new component needed; the existing 'textarea' input type already drives StepInput, answerValid, and initialAnswer. apply() writes a single typed string to record.responsibilities_narrative. Mirrors the client_service_results TextArea step from Phase 23."
    - "DocumentPane conditional Sec with dynamic n++ (RESP-02): wrap each new Sec's n++ inside `if (r.responsibilities_narrative)` so downstream sections (Key Responsibilities, Classification, Qualifications, DRF) renumber transparently when the optional Sec is hidden."
    - "Export priority idiom (RESP-03 / R-RESP-03): `responsibilities_text = (wd.responsibilities_narrative or '').strip() or _ADVISOR_PLACEHOLDER` — REPLACES the JES-derived responsibility factor block (which was the previous source but had no test guarding it). When the advisor has not populated responsibilities_narrative, the section renders the advisor placeholder, NOT a {{template leak}} and NOT synthesized text."
    - "wdPayload mirror list: app.jsx commit() mirrors classification-level fields (confirmed_noc, confirmed_og, og_level, reports_to_military, jes_scores, jes_total_points, org_context, responsibilities_narrative) to the PATCH payload so the stored WD has the data the export layer reads."

key-files:
  created: []
  modified:
    - v2/backend/app/models/work_description.py
    - v2/backend/app/api/wd.py
    - v2/backend/app/services/export_service.py
    - v2/frontend/src/data.jsx
    - v2/frontend/src/app.jsx
    - v2/frontend/src/document.jsx
    - v2/backend/tests/test_wd.py
    - v2/backend/tests/test_export.py
    - v2/frontend/src/conversation.test.jsx
    - v2/frontend/src/document.test.jsx

key-decisions:
  - "Both WorkDescription.responsibilities_narrative and WDPatchRequest.responsibilities_narrative committed in the SAME git commit (Task 1, 3a9cdcb) per the v4.0 co-update rule. extra='ignore' on WDPatchRequest would silently drop an unknown PATCH key with HTTP 200 — the round-trip test gates the merge."
  - "max_length=4000 on WDPatchRequest.responsibilities_narrative (T-27-01): ASVS V5 DoS mitigation, mirrors T-26-01 for org_context. Companion test test_patch_responsibilities_narrative_rejects_over_length guards the constraint — a regression removing it would not otherwise be caught."
  - "RESP-01 simplification: responsibilities_narrative is a single free-text textarea (R-RESP-01 from CONTEXT.md), NOT a 4-part assembly like OrgContextInput. The existing 'textarea' input type is already fully supported by StepInput / answerValid / initialAnswer — no new component, no new dispatch lines. The plan's WDPatchRequest co-update rule is the only mandatory backend change; the 4-part pattern from Phase 26 is intentionally NOT reused."
  - "STEPS insertion position (RESP-01): responsibilities_narrative sits at phase 3 AFTER duties (line 679) and BEFORE quals (line 703). Conversation reads: Org Context → Client Service Results → Key Activities → Responsibilities narrative → Qualifications. The DOCX element order is fixed by the template; the step order is conversational — these can differ."
  - "stepIndex resume-by-last-answered inherits for free: only the STEP_RECORD_KEY entry is added (responsibilities_narrative: 'responsibilities_narrative'). The STEPS.reduce logic is untouched — Phase 26's invariant carries the new step without any further wiring."
  - "DocumentPane conditional Sec pattern (RESP-02): Responsibilities Sec renders with dynamic n++ inside `if (r.responsibilities_narrative)`. When the advisor skips the step, downstream sections (Key Responsibilities, Classification, DRF, Qualifications) renumber transparently. No hard-coded section numbers in the JSX."
  - "R-RESP-03 export priority (RESP-03): responsibilities_text = (wd.responsibilities_narrative or '').strip() or _ADVISOR_PLACEHOLDER REPLACES the previous JES-derived factor list (`if responsibility_factors: ... else: _ADVISOR_PLACEHOLDER`). Verified safe: no existing test asserted the JES-derived responsibilities_text — only a docstring mentioned it. The responsibility_factors variable is removed (now unused; was only consumed by the deleted block)."
  - "Empty responsibilities_narrative -> 'missing' status belongs to Plan 27-02 (R-ELEM-01a); this plan does NOT add any not_applicable logic. The export placeholder behavior (RESP-03) is purely an export-layer concern; the completeness audit (Plan 27-02) reads wd.responsibilities_narrative and decides the per-element status."
  - "wdPayload mirror list extended: app.jsx commit() mirrors 'responsibilities_narrative' to the PATCH payload (alongside org_context) so the typed root field persists on every commit. This is the same CR-01 fix from Phase 26 (commit() mirror list was previously missing org_context, causing silent data-loss on SPA->export)."

patterns-established:
  - "WDPatchRequest co-update rule pattern: every new WorkDescription typed field that is advisor-patchable must have a corresponding WDPatchRequest field added in the same git commit, with a round-trip test gating merge. The co-update pair must share a single commit. Reinforced for Phase 28 (manager-track fields)."
  - "Free-text conversational step pattern: textarea + apply writes a single typed string to record. Reusable for any future step whose persisted value is a single string. (Distinct from the 4-part assembly pattern from Phase 26, which captured multi-sub-field decisions.)"
  - "Export placeholder priority pattern: `(wd.<typed_field> or '').strip() or _ADVISOR_PLACEHOLDER` for any Part 2 element where the advisor-authored value is the authoritative source and the fallback is a non-sensitive advisor-visible placeholder. Distinct from the org_context priority pattern (`wd.<field> if wd.<field> is not None else _build_<field>_text(wd)`), which keeps a synthesized fallback as a regression guard."
  - "Removal of unused intermediate variables when refactoring export_service blocks: responsibility_factors was removed because the deleted block was its only consumer. Avoid leaving dead code in the export pipeline."

requirements-completed:
  - RESP-01
  - RESP-02
  - RESP-03

# Metrics
duration: 12min
completed: 2026-06-24
---
# Phase 27 Plan 01: Responsibilities Narrative Vertical Slice — Summary

**Free-text responsibilities_narrative textarea step + typed WorkDescription root field with WDPatchRequest co-update (max_length=4000) + DocumentPane Responsibilities Sec with dynamic n++ + DOCX Part 2 Responsibility content driven by advisor narrative (or _ADVISOR_PLACEHOLDER) — RESP-01/02/03 GREEN**

## Performance

- **Duration:** 12 min
- **Started:** 2026-06-24T11:28:00Z (approx)
- **Completed:** 2026-06-24T11:40:00Z (approx)
- **Tasks:** 3 (TDD with strict sequence; each task's output was a prerequisite for the next)
- **Files modified:** 10 (6 production + 4 test files)

## Accomplishments

- All 5 RED stubs (2 backend + 3 frontend) are GREEN: `test_patch_responsibilities_narrative_round_trip` (backend WD co-update), `test_patch_responsibilities_narrative_rejects_over_length` (backend T-27-01 ASVS V5), `test_responsibilities_narrative_in_export` (backend R-RESP-03 export priority), `test_responsibilities_narrative_placeholder_in_export` (backend placeholder fallback), STEPS shape + STEPS order (frontend data.jsx), Responsibilities Sec render (frontend document.jsx)
- `responsibilities_narrative: Optional[str] = None` typed root field on WorkDescription + `responsibilities_narrative: Optional[str] = Field(default=None, max_length=4000)` on WDPatchRequest, both in the SAME git commit (`3a9cdcb`) per the v4.0 co-update rule (T-27-01 mitigated)
- Free-text `textarea` step in STEPS at phase 3 after duties (line 679) and before quals (line 703) — no new component needed (R-RESP-01 simplification: existing StepInput dispatch already handles 'textarea' type)
- Responsibilities Sec renders conditionally in DocumentPane (key='resp_narrative', between csr Sec and Key Responsibilities Sec) with dynamic `n++` so downstream sections renumber transparently when the Sec is hidden
- FLASH + SECTION_NAMES + STEP_RECORD_KEY entries added in app.jsx (responsibilities_narrative: 'resp_narrative', resp_narrative: 'Responsibilities', responsibilities_narrative: 'responsibilities_narrative') — stepIndex resume-by-last-answered inherits the new step for free without touching the STEPS.reduce logic
- app.jsx `commit()` wdPayload mirror list extended to include `responsibilities_narrative` (alongside `org_context`) so PATCH /api/wd persists the typed root field on every commit (defense against the CR-01 class of bug from Phase 26)
- `_build_wd_context` now returns `responsibilities_text = (wd.responsibilities_narrative or '').strip() or _ADVISOR_PLACEHOLDER` — REPLACES the JES-derived responsibility factor block (R-RESP-03). When the advisor skips the step, the Part 2 Responsibility section renders the advisor placeholder, NOT a `{{template leak}}` and NOT synthesized text
- `responsibility_factors` variable removed from export_service.py (was only consumed by the deleted block; no other references)
- Backend suite: 164 passed, 0 failed (160 pre-existing + 2 Task 1 round-trip + 2 Task 3 export tests)
- Frontend suite: 68 passed, 0 failed (65 pre-existing + 3 Task 2: STEPS shape, STEPS order, Responsibilities Sec render)
- `getVisibleSteps` expected count updated from 14 to 15 (STEPS grew from 23 to 24 with the new unconditional step) — mirrors the Phase 26 STEPS-count bump pattern

## Task Commits

Each task was committed atomically in strict sequence:

1. **Task 1: WorkDescription + WDPatchRequest co-update + round-trip test** — `3a9cdcb` (feat) — 3 files (work_description.py + wd.py + test_wd.py) in ONE commit per the co-update rule
2. **Task 2: STEPS responsibilities_narrative textarea step + DocumentPane Sec + FLASH/SECTION_NAMES/STEP_RECORD_KEY** — `2446039` (feat) — 5 files (data.jsx + app.jsx + document.jsx + conversation.test.jsx + document.test.jsx)
3. **Task 3: Export responsibilities_text priority (narrative or advisor placeholder)** — `0e54d0e` (feat) — 2 files (export_service.py + test_export.py)

## Files Created/Modified

- `v2/backend/app/models/work_description.py` — added `responsibilities_narrative: Optional[str] = None` typed root field on WorkDescription (Phase 27 — RESP-01)
- `v2/backend/app/api/wd.py` — added `responsibilities_narrative: Optional[str] = Field(default=None, max_length=4000)` on WDPatchRequest (co-update rule; max_length per ASVS V5 DoS mitigation T-27-01, mirrors T-26-01 for org_context)
- `v2/backend/app/services/export_service.py` — REPLACED the JES-derived `responsibilities_text` block (lines 354-360, the `if responsibility_factors: ... else: _ADVISOR_PLACEHOLDER` block) with `responsibilities_text = (wd.responsibilities_narrative or '').strip() or _ADVISOR_PLACEHOLDER`. Removed the now-unused `responsibility_factors` variable. R-RESP-03: narrative when filled, advisor placeholder when empty — no JES-derived fallback, no `{{template leak}}`
- `v2/frontend/src/data.jsx` — new STEPS entry `{ id: 'responsibilities_narrative', phase: 3, icon: I.flag, input: { type: 'textarea', placeholder: '...' }, apply: (r, a) => ({ responsibilities_narrative: a }) }` inserted AFTER duties (line 695) and BEFORE quals (line 703)
- `v2/frontend/src/app.jsx` — FLASH entry `responsibilities_narrative: 'resp_narrative'`; SECTION_NAMES entry `resp_narrative: 'Responsibilities'`; STEP_RECORD_KEY entry `responsibilities_narrative: 'responsibilities_narrative'` (stepIndex resume inherits for free — no reduce change); `wdPayload` mirror list extended to include `'responsibilities_narrative'` (mirrors `org_context` to prevent CR-01-style silent data-loss)
- `v2/frontend/src/document.jsx` — new conditional `Sec` in DocumentPane (key='resp_narrative', title='Responsibilities', src='Advisor-provided', fresh=isFresh('responsibilities_narrative'), editable+onEdit for review-mode editing, full amendment props) rendered AFTER csr Sec and BEFORE Key Responsibilities Sec (key='du'), with dynamic n++ so downstream sections renumber transparently
- `v2/backend/tests/test_wd.py` — `test_patch_responsibilities_narrative_round_trip` (RED gate: PATCH then GET round-trip; co-update test); `test_patch_responsibilities_narrative_rejects_over_length` (RED gate: 422 on >4000 chars; T-27-01 guard)
- `v2/backend/tests/test_export.py` — `test_responsibilities_narrative_in_export` (RED gate: PATCH narrative then export; assert narrative in DOCX full_text); `test_responsibilities_narrative_placeholder_in_export` (RED gate: no narrative -> '_ADVISOR_PLACEHOLDER' in DOCX, no `{{template leak}}`, no 'responsibilities_text' literal)
- `v2/frontend/src/conversation.test.jsx` — STEPS shape test (`{ id: 'responsibilities_narrative', phase: 3, input.type: 'textarea' }`); STEPS order test (`dutiesIdx < respIdx < qualsIdx`); `getVisibleSteps` expected count updated 14 -> 15 with a Phase 27 comment explaining the STEPS growth
- `v2/frontend/src/document.test.jsx` — "renders Responsibilities section when record.responsibilities_narrative is set" test

## Decisions Made

- **Both fields in one commit (3a9cdcb):** WorkDescription.responsibilities_narrative and WDPatchRequest.responsibilities_narrative ship together. The round-trip test stays RED until both exist (extra='ignore' on WDPatchRequest would silently drop unknown keys with HTTP 200). The companion over-length test (422 on >4000 chars) guards the max_length constraint — T-27-01 ASVS V5 DoS mitigation, mirrors T-26-01.
- **Free-text textarea, no new component (R-RESP-01):** RESP-01's wording is explicit "free-text responsibilities narrative". The existing 'textarea' input type is fully supported by StepInput / answerValid / initialAnswer. We did NOT create a 4-part assembly component like OrgContextInput — that pattern was for org_context's 4 sub-fields (work_stream / org_placement / reporting / additional). responsibilities_narrative captures a single advisor-authored paragraph.
- **STEPS position (line 695):** Sits at phase 3 after duties (line 679) and before quals (line 703). The conversation reads: Org Context → Client Service Results → Key Activities → Responsibilities narrative → Qualifications. The DOCX element order is fixed by the template; the step order is conversational — these can differ.
- **stepIndex resume inherits for free:** Only the STEP_RECORD_KEY entry is added. The STEPS.reduce logic (Phase 26's invariant) walks STEP_RECORD_KEY[s.id] to find the last answered step, so the new step transparently supports resume.
- **wdPayload mirror list extended (CR-01 defense):** Following the Phase 26 fix where `commit()`'s mirror list was missing `org_context` (causing silent data-loss on SPA->export), we explicitly add `responsibilities_narrative` to the mirror list alongside `org_context`. Without this, the typed field would only be in the freeform `record` dict and not at the root of the WorkDescription, defeating the export layer.
- **Export priority REPLACES (not adds a fallback to) the JES-derived block (R-RESP-03):** The previous block `if responsibility_factors: responsibilities_text = "\n".join(...)` is deleted; the new line is `responsibilities_text = (wd.responsibilities_narrative or '').strip() or _ADVISOR_PLACEHOLDER`. No existing test asserted the JES-derived responsibilities_text — verified via grep for `responsibilities_text = "\n"` (returns 0 matches). The `responsibility_factors` variable is removed (only consumer was the deleted block). The contrast with org_context's priority (which KEEPS the synthesized fallback as a regression guard) is intentional: responsibilities_narrative is an open question (every position has one), so an empty value correctly means "missing" and the advisor placeholder is the right render. org_context can be legitimately synthesized from branch+reports data when the advisor skips the step, so its fallback is meaningful.
- **No not_applicable logic (R-ELEM-01a):** Empty responsibilities_narrative -> "missing" status belongs to Plan 27-02's completeness audit. This plan does NOT add any not_applicable logic — the export placeholder behavior is purely an export-layer concern.

## Deviations from Plan

None - plan executed exactly as written. All 3 task commit messages match the plan's specified format. Co-update rule enforced (Task 1's commit contains both model + WDPatchRequest field edits). All TDD gate commits exist (RED gate tests, then GREEN implementation). STEPS-count bump from 14 to 15 was anticipated by the plan's "Test impact: the getVisibleSteps count test expects 23 STEPS; it must become 24 after this insertion" note and the existing Phase 26 deviation comment pattern.

## Issues Encountered

None - plan executed cleanly. All 5 RED tests turned GREEN at the expected step. The `cd v2/frontend` shell error in one verification invocation was a non-issue (subsequent call from the correct directory passed).

## User Setup Required

None - Plan 27-01 is pure code (no external services, no environment variables, no UI verification beyond what the automated tests cover). The Phase 27 human UAT items (rendering the responsibilities_narrative step in a live browser, downloading an Accessible JD DOCX with narrative populated) will be captured in a `27-HUMAN-UAT.md` if the user requests one.

## Next Phase Readiness

- **Plan 27-01 is structurally complete.** RESP-01/02/03 requirements delivered. Co-update rule enforced. StepIndex resume works correctly across the new STEPS insertion. DocumentPane Sec template is ready for Phase 27-02 to add the 7-element completeness audit on top.
- **Plan 27-02 (Seven-Elements Completeness Audit) is unblocked.** It will reuse:
  - The `wd.responsibilities_narrative` typed root field (ELEM-01c: Other element statuses)
  - The `build_seven_elements(wd) -> dict` shared helper pattern from Phase 27 CONTEXT.md
  - The `POST /api/wd/{id}/validate-elements` endpoint pattern from `validate-duties` (wd.py line 306) and `run_orphan_check` (wd.py line 264)
  - The ReviewState soft-gate pattern from Phase 24 (audit panel is informational, not blocking)
- **No blockers.** All 5 RED stubs from Plan 27-01 are GREEN; full suite (164 backend + 68 frontend) is GREEN; co-update rule is enforced; document preview order (csr < resp_narrative < du) verified; export priority (narrative or _ADVISOR_PLACEHOLDER) verified.

## Self-Check: PASSED

Created/modified files verified on disk:
- FOUND: v2/backend/app/models/work_description.py
- FOUND: v2/backend/app/api/wd.py
- FOUND: v2/backend/app/services/export_service.py
- FOUND: v2/frontend/src/data.jsx
- FOUND: v2/frontend/src/app.jsx
- FOUND: v2/frontend/src/document.jsx
- FOUND: v2/backend/tests/test_wd.py
- FOUND: v2/backend/tests/test_export.py
- FOUND: v2/frontend/src/conversation.test.jsx
- FOUND: v2/frontend/src/document.test.jsx

Task commits verified in git log:
- FOUND: 3a9cdcb (feat — Task 1: WD + WDPatchRequest co-update + round-trip test)
- FOUND: 2446039 (feat — Task 2: STEPS step + DocumentPane Sec + FLASH/SECTION_NAMES/STEP_RECORD_KEY)
- FOUND: 0e54d0e (feat — Task 3: Export responsibilities_text priority)

Test counts verified:
- Backend: 164 passed, 0 failed (target was 155+; met — 160 baseline + 2 Task 1 round-trip + 2 Task 3 export)
- Frontend: 68 passed, 0 failed (target was 66+; met — 65 baseline + 3 Task 2: STEPS shape, STEPS order, Responsibilities Sec)
- All 5 Phase 27 RED stubs confirmed GREEN via verbose test reporter

Phase gate spot-checks verified:
- Co-update rule: `responsibilities_narrative` present in BOTH work_description.py (line 57) AND wd.py (line 152) ✓
- max_length=4000: 2 matches in wd.py (org_context + responsibilities_narrative) ✓
- STEPS order: duties (line 679) < responsibilities_narrative (line 695) < quals (line 703) in data.jsx ✓
- Document preview order: key="csr" (line 328) < key="resp_narrative" (line 352) < key="du" (line 370) in document.jsx ✓
- Export priority: `wd.responsibilities_narrative` appears in export_service.py inside `_build_wd_context` (line 360) ✓
- Old JES-derived block is GONE: `grep -c 'responsibilities_text = "\n"'` returns 0 ✓
- responsibility_factors variable removed (only consumer was the deleted block) ✓

---
*Phase: 27-responsibilities-narrative-completeness-audit*
*Plan: 01 (Wave 1 GREEN implementation)*
*Completed: 2026-06-24*
