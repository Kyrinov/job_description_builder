---
phase: 25-accessible-template
plan: 02
subsystem: export
tags: [docxtpl, accessible-jd, template-build, jinja2, jd-export]

# Dependency graph
requires:
  - phase: 25-accessible-template (Plan 01)
    provides: "4 JES-shape fixture helpers + 6 RED tests in v2/backend/tests/test_export.py locking the Accessible-template contract (ACC-01/02/04)"
provides:
  - "v2/backend/scripts/build_accessible_template.py — self-verifying python-docx + docxtpl skeleton builder (29 declared Jinja2 vars, 17-field position table, 3 static signature blocks, 7 Part 2 Heading-2 subsections + Effort/Working-conditions {%tr for %} tables with placeholder fallback)"
  - "v2/backend/app/templates/wd_accessible_template.docx — committed binary artifact (4 tables, 14 headings, 43 paragraphs) ready for Plan 25-03's _build_wd_context rewrite to fill"
  - "ACC-01 satisfied: build script self-verifies all required Jinja2 variables are declared at build time, not at first export"
affects: [25-accessible-template (Plan 03 — _build_wd_context rewrite + template path swap)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "GoC Accessible JD format: Part 1 (17-field position table + 3 static signature blocks) + Part 2 (7 Heading-2 subsections)"
    - "docxtpl {%tr for %} / {%tr endfor %} loops with `for` and `endfor` each alone in their own row (preserved verbatim from build_wd_template.py; greedy patch_xml pitfall)"
    - "effort_placeholder / wc_placeholder fallback pattern: always-rendered paragraph carries the placeholder string, {%tr for %} loop renders nothing when the group has no factors in that category"
    - "print-and-sign signature blocks: 3 Heading-2 + 3 plain 'Name: __' / 'Signature: __' / 'Date: __' paragraphs each, zero Jinja2 variables (locked decision 3)"

key-files:
  created:
    - v2/backend/scripts/build_accessible_template.py
    - v2/backend/app/templates/wd_accessible_template.docx
  modified: []

key-decisions:
  - "Replicated build_wd_template.py's full structure (imports, _set_cell_text copied verbatim, OUTPUT_PATH, self-verify tail) — confirmed convention that build scripts are independent of each other rather than sharing helpers (PATTERNS.md: 'duplicating it a third time is the established convention, not an anti-pattern here')"
  - "Included the amendments {%tr for a in amendments %} loop and the {%p if amendments|length > 0 %} gate in the new template verbatim from build_wd_template.py — the export_service's existing _get_amendments contract is preserved unchanged so Plan 25-03's _build_wd_context rewrite can use the same call site"
  - "Used {%p for entry in manifest %} paragraph-level loop (not the {%tr for m in manifest %} table-row loop that build_wd_template.py uses) — the Accessible reference document does not have a numbered manifest table; this is a more natural fit for the GoC Accessible format. Plan 25-03 binds manifest via the existing _build_v2_manifest helper"

patterns-established:
  - "Build script template self-verify tail: build() → DocxTemplate(OUTPUT_PATH) → get_undeclared_template_variables() → required-set subset assertion. Catches malformed template tags at build time, not at first export. Now established as a 3-script convention (build_wd_template.py, build_poster_template.py, build_accessible_template.py)"
  - "Jinja2 variable contract: the 29-var required set is the source of truth for which context keys Plan 25-03's _build_wd_context MUST produce"

requirements-completed: [ACC-01]

# Metrics
duration: 7min
completed: 2026-06-16
---

# Phase 25 Plan 02: Accessible Template Build Script + DOCX Artifact

**Self-verifying docxtpl skeleton builder producing the GoC Accessible JD template — 17-field position table, 3 static signature blocks, 7 Part 2 subsections with Effort/Working-conditions {%tr for %} loops and placeholder fallback.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-06-16T18:59:32Z
- **Completed:** 2026-06-16T19:06:00Z
- **Tasks:** 2 (both auto, both committed atomically)
- **Files modified:** 2 (1 script + 1 binary artifact)

## Accomplishments

- **build_accessible_template.py** mirrors build_wd_template.py's full idiom: same imports, `_set_cell_text` copied verbatim, `OUTPUT_PATH` pointing at the new artifact, `if __name__ == "__main__":` self-verify tail asserting all 29 required Jinja2 vars are declared via `get_undeclared_template_variables()`. Module docstring documents the full variable contract (Part 1 17 vars + Part 2 9 vars + manifest/amendments 3 vars).
- **wd_accessible_template.docx** committed binary: 4 tables (position 17-row, effort 4-row, working-conditions 4-row, amendments 4-row), 14 Heading 1/2 paragraphs, 43 total paragraphs. All 7 Part 2 subsection headings (Organizational context, Client service results, Key activities, Skills, Effort, Responsibilities, Working conditions) present in the correct order.
- **Signature blocks are static print-and-sign text** (per locked decision 3): 3 Heading-2 sections × 3 plain "Name: __" / "Signature: __" / "Date: __" paragraphs each, zero Jinja2 variables. Verified: `grep -A4 'Employee statement' build_accessible_template.py | grep -c '{{'` returns 0.
- **6 unmapped position-identification fields** (Job Code, Office code, Language requirements, Linguistic profile, Communications requirements, Security requirements) all bound to Jinja2 vars per locked decision 2 — Plan 25-03's `_build_wd_context` will compute `[To be completed by advisor]` fallbacks at render time.
- **Existing 6 RED tests from Plan 25-01 remain RED** (confirmed: `pytest tests/test_export.py` → "6 failed, 13 passed") — this plan does NOT touch `export_service.py`; the template artifact is committed but the export path still renders the old TBS template/context. Plan 25-03 is the data-binding half that turns those RED tests GREEN.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write build_accessible_template.py skeleton (Part 1 + Part 2 structure + Jinja2 tags)** - `5d60638` (feat)
2. **Task 2: Add self-verify block, run the script, commit the .docx artifact** - `38630a9` (feat)

**Plan metadata:** committed as part of this final SUMMARY.

_Note: Task 2's self-verify block was authored as part of the Task 1 file write (build_wd_template.py's `if __name__ == "__main__":` block was so structurally simple it was natural to include from the start), then Task 2 was the script run + .docx commit. Both were atomic commits, no incremental work between them._

## Files Created/Modified

- `v2/backend/scripts/build_accessible_template.py` — 306 lines. Self-verifying docxtpl builder. Replicates build_wd_template.py idioms; OUTPUT_PATH = "v2/backend/app/templates/wd_accessible_template.docx"; _set_cell_text duplicated verbatim per PATTERNS.md guidance; 17-row position table + 3 static signature blocks + 7 Part 2 subsections + Effort/Working-conditions {%tr for %} loops with placeholder fallback + manifest paragraph loop + amendments {%p if %} gate.
- `v2/backend/app/templates/wd_accessible_template.docx` — 37,872 bytes. Committed binary. 4 tables, 14 headings, 43 paragraphs. All 29 Jinja2 variables self-declared.

## Decisions Made

- **Replicated build_wd_template.py's full structure rather than refactoring into a shared helper** — the project's convention (build_wd_template.py + build_poster_template.py both duplicate `_set_cell_text`) treats these as one-off codegen scripts, not a library. Following the convention keeps the diff small and the scripts independently testable.
- **Manifest uses {%p for entry in manifest %} paragraph loop, not the {%tr for m in manifest %} table-row loop that build_wd_template.py uses** — the GoC Accessible reference document does not have a numbered manifest table. Plan 25-03 binds manifest via the existing `_build_v2_manifest` helper that already returns a flat list of source entries; the paragraph format (one line per entry) matches the reference document's prose style.
- **All 6 unmapped position-identification fields bound to Jinja2 vars, not omitted from the table** — keeps the template visually identical to the GoC reference (locked decision 2 from RESEARCH.md). Plan 25-03's `_build_wd_context` will compute `[To be completed by advisor]` for these at render time, which matches ACC-02's stated placeholder-fallback pattern for Effort/Working Conditions.

## Deviations from Plan

### Plan Heuristic Miscalibration (informational, not a fix)

**1. `grep -c '%tr for'` returned 8, not 2 (plan acceptance check)**
- **Found during:** Task 1 verification
- **Issue:** The plan's acceptance check "grep -c '%tr for' returns 2 (effort + working conditions tables)" expected only 2 Jinja2 tag occurrences, but the script also includes the amendments `{%tr for a in amendments %}` table-row loop copied verbatim from build_wd_template.py (per the plan's own "amendments appendix `{%p if amendments|length > 0 %}` gate verbatim" instruction). Plus 5 comment/docstring references to the pattern. The actual Jinja2 tag count is 3 (effort + working_conditions + amendments), not 2.
- **Fix:** No fix needed — the plan's "2" was a miscount by the planner. The substantive contract (effort and working-conditions tables both have {%tr for %} loops) is met; the amendments loop is a plan-prescribed additive element.
- **Impact:** Zero. The acceptance criterion's intent (verify the {%tr for %} pattern is present in both new tables) is satisfied. The third tag is the plan's own requirement.

## Issues Encountered

None.

## Auth Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 25-03 is unblocked: it must (1) add `_factor_category_map` + routing-code-aware fallback in `export_service._build_wd_context`, (2) swap the template path call site from `wd_template.docx` to `wd_accessible_template.docx`, (3) retire `wd_template.docx` + `build_wd_template.py` (ACC-03).
- The 29-var `required` set in `build_accessible_template.py`'s self-verify is the source of truth for which context keys `_build_wd_context` MUST produce. Plan 25-03's CONTEXT contract should mirror this list.
- The 6 RED tests from Plan 25-01 are the gate: they will turn GREEN once Plan 25-03 is complete and `pytest tests/test_export.py` returns "0 failed, 19 passed".

---
*Phase: 25-accessible-template*
*Completed: 2026-06-16*

## Self-Check: PASSED
- v2/backend/scripts/build_accessible_template.py exists (306 lines)
- v2/backend/app/templates/wd_accessible_template.docx exists (37,872 bytes)
- Task 1 commit 5d60638 exists in git log
- Task 2 commit 38630a9 exists in git log
- Self-verify ran clean: 29/29 required Jinja2 variables declared, "Accessible template OK" printed, exit 0
- python-docx readback confirmed: 4 tables, 14 headings, 43 paragraphs, 17-row position table
- 6 RED tests from Plan 25-01 still RED (6 failed, 13 passed) — expected, Plan 25-03 will turn them GREEN
