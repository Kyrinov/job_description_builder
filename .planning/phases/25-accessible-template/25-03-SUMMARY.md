---
phase: 25-accessible-template
plan: 03
subsystem: export
tags: [export, accessible-template, factor-category-map, docxtpl, jes-bucketing, tbs-retirement, acc-02, acc-03, acc-04]
dependency_graph:
  requires:
    - phase: 25-accessible-template (Plan 01)
      provides: "4 JES-shape fixture helpers + 6 RED tests in v2/backend/tests/test_export.py locking the Accessible-template contract (ACC-01/02/04)"
    - phase: 25-accessible-template (Plan 02)
      provides: "v2/backend/scripts/build_accessible_template.py + committed wd_accessible_template.docx binary with 29/29 required Jinja2 vars self-verified"
  provides:
    - "v2/backend/app/services/export_service.py: _factor_category_map helper, _ADVISOR_PLACEHOLDER constant, rewritten _build_wd_context producing all 29 Accessible-template Jinja2 vars"
    - "POST /api/wd/{id}/export/docx now renders wd_accessible_template.docx via _resolve_template_path"
    - "TBS template + build script retired (v2/backend/app/templates/wd_template.docx, v2/backend/scripts/build_wd_template.py deleted)"
  affects: []
tech-stack:
  added: []
  patterns:
    - "Factor category derived fresh from constants.py via _factor_category_map() — never trusts wd.jes_scores[i]['category'] (EC path omits the key)"
    - "SW/ED sub-group routing-code resolution replicated from jes_service.score_jes_v2 (SW-SCW/SW-CHA, ED-EDS/ED-LAT/ED-EST) — routing_code is the key into JES_FACTORS_BY_GROUP"
    - "Category-bucketed JES factors: effort_factors / working_conditions_factors / responsibility_factors lists + effort_placeholder / wc_placeholder / responsibilities_text strings"
    - "Placeholder convention: 'or _ADVISOR_PLACEHOLDER' idiom on every scalar that could be blank — empty string only allowed for effort_placeholder/wc_placeholder when factors ARE present (template renders the table instead of the placeholder paragraph)"
    - "docxtpl {%tr for %} / {%tr endfor %} loops with for/endfor each alone in their own row (preserved verbatim from build_wd_template.py — greedy patch_xml pitfall)"
key-files:
  created: []
  modified:
    - v2/backend/app/services/export_service.py
  deleted:
    - v2/backend/app/templates/wd_template.docx
    - v2/backend/scripts/build_wd_template.py
decisions:
  - "Extended the existing 'from app.data.constants import NON_EC_STANDARD_NAMES' line into a parenthesized multi-line import (EC_JES_ELEMENTS, JES_FACTORS_BY_GROUP, NON_EC_STANDARD_NAMES) so the import-shape test_standard_names_import_from_constants (line 413) still matches its 'from app.data.constants import' substring check"
  - "Replicated SW/ED sub-group routing-code resolution (sub_group from confirmed_sub_group attribute) verbatim from jes_service.py score_jes_v2 lines 192-217 — routing_code is the key into JES_FACTORS_BY_GROUP, not raw og_code"
  - "Added _ADVISOR_PLACEHOLDER module-level constant (one occurrence, 25 chars) — referenced ~12 times in _build_wd_context for the 6 unmapped Part 1 fields, supervisor_classification, the 3 JES placeholders, client_service_results, and education/experience fallbacks"
  - "education_text and experience_text use 'or _ADVISOR_PLACEHOLDER' so a WD with no qualification and no record.quals still renders the Skills section with the placeholder string (not an empty cell) — keeps ACC-04 content-presence green for all 4 fixtures"
  - "responsibility_factors text formatted as 'factor_name: rationale' (with trailing ': ' stripped when rationale is empty) — joined with newlines, or _ADVISOR_PLACEHOLDER when no Responsibility factors present"
  - "All 4 deliverable acceptance criteria verified against the spec: EC test sees Effort heading + 3 factor names; FB test sees Effort heading + 4 factor names; MT and AS tests see [To be completed by advisor] for the 3 JES placeholders; content_presence test sees no {{ or None or %} leaks AND sees the seeded client_service_results text in the new Client service results section; structure_headings test sees all 7 Part 2 Heading-2 names + Part 1/Part 2 markers"
metrics:
  duration_minutes: 12
  completed_date: 2026-06-16
  task_count: 2
  file_count: 3  # 1 modified + 2 deleted
requirements-completed: [ACC-02, ACC-03, ACC-04]
---

# Phase 25 Plan 03: Accessible Template Export Path + TBS Retirement Summary

Wires the Accessible-format template (built in Plan 25-02) into the live export path with correct JES-derived Effort/Working-Conditions bucketing, retires the TBS template and its build script, and turns the 6 RED tests from Plan 25-01 GREEN. ACC-02/03/04 closed.

**One-liner:** `_factor_category_map` + rewritten `_build_wd_context` + template path swap + TBS retirement — 6 RED tests now GREEN, 150/150 full backend suite green, zero regressions.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add `_factor_category_map` helper + rewrite `_build_wd_context` for Accessible fields | `9de26fd` | `v2/backend/app/services/export_service.py` |
| 2 | Switch export template path, update test assertions, retire TBS template | `baa0440` | `v2/backend/app/services/export_service.py` (path swap) + `v2/backend/app/templates/wd_template.docx` (deleted) + `v2/backend/scripts/build_wd_template.py` (deleted) |

## Test Results

```
$ cd v2/backend && python -m pytest tests/test_export.py -q
======================== 19 passed, 1 warning in 6.89s =========================

$ cd v2/backend && python -m pytest -q
====================== 150 passed, 21 warnings in 10.33s ======================
```

**Before (Plan 25-01 baseline):** 6 failed, 13 passed in `test_export.py`
**After Plan 25-03:** 19 passed, 0 failed in `test_export.py`; 150 passed, 0 failed in full suite.

**Newly GREEN tests (6 — all 6 RED tests from Plan 25-01):**
- `test_accessible_effort_ec_populated` — EC fixture: "Physical effort" / "Sensory effort" / "Working conditions" all in rendered DOCX, plus the new "Effort" Heading-2
- `test_accessible_effort_fb_populated` — FB fixture: "Physical effort" / "Sensory effort" / "Risk to health" / "Work environment" all in rendered DOCX, plus "Effort" Heading-2
- `test_accessible_effort_no_factor_group_placeholder` — MT fixture: "[To be completed by advisor]" present (from `effort_placeholder` + `wc_placeholder` since MT has no Effort/Conditions factors)
- `test_accessible_effort_level_description_placeholder` — AS fixture: same placeholder path (empty `jes_scores` → all 3 placeholders set)
- `test_accessible_content_presence` — EC fixture: no `{{`, no `\nNone\n`, no `%}` leaks; "Citizens receive timely" appears in the new "Client service results" Part 2 subsection (from `record.client_service_results`)
- `test_accessible_structure_headings` — EC fixture: all 7 Part 2 subsection headings present (Organizational context, Client service results, Key activities, Skills, Effort, Responsibilities, Working conditions) + "Part 1" / "Part 2" markers

**Existing tests (13) still GREEN:**
- 7 original Phase 20 export tests (`test_export_wd_docx_returns_bytes`, `test_export_wd_docx_manifest`, `test_export_wd_docx_amendments_appendix`, `test_export_poster_returns_bytes`, `test_export_pdf_501_when_weasyprint_absent`, `test_export_docx_404`, `test_export_poster_404`)
- 4 Phase 21 amendments/record-fallback tests (`test_export_pdf_501_when_weasyprint_probe_fails`, `test_export_docx_409_without_og`, `test_export_poster_409_without_og`, `test_export_docx_self_heals_jes_scores`, `test_export_docx_uses_record_duties_fallback`)
- 1 OGX-02 import-shape test (`test_standard_names_import_from_constants` — the new parenthesized multi-line import still contains both required substrings)

## Acceptance Criteria Verification

### Task 1 (export_service.py rewrite)

| Criterion | Status | Notes |
|-----------|--------|-------|
| `def _factor_category_map` exists | ✓ | Line 220 |
| `EC_JES_ELEMENTS` import in constants import block | ✓ | Line 37 (in parenthesized import with `JES_FACTORS_BY_GROUP`, `NON_EC_STANDARD_NAMES`) |
| All 6 Effort/WC/Responsibilities/Client-service keys present | ✓ | 13 grep hits across the 6 keys (definitions + dict key references) |
| `_ADVISOR_PLACEHOLDER` defined | ✓ | Line 60, 1 occurrence in source |
| SW/ED `routing_code` block replicated | ✓ | Lines 308-322 (verbatim from jes_service.py score_jes_v2 lines 192-217) |
| `cat_map.get(...)` used for category bucketing | ✓ | Lines 343-345 — never reads `s.get("category")` from the persisted dict (the only `score.get("category")` substring match is a docstring explaining WHY we don't) |
| Python parse OK | ✓ | `ast.parse(...)` exits 0 |

### Task 2 (template path + retirement)

| Criterion | Status | Notes |
|-----------|--------|-------|
| `_resolve_template_path("wd_accessible_template.docx")` in `generate_wd_docx` | ✓ | Line 524 |
| `grep -rn 'wd_template.docx' v2/backend --include='*.py'` returns 0 hits | ✓ | Confirmed |
| `v2/backend/app/templates/wd_template.docx` deleted | ✓ | `git rm` succeeded; `ls` reports "No such file" |
| `v2/backend/scripts/build_wd_template.py` deleted | ✓ | `git rm` succeeded; `ls` reports "No such file" |
| `v2/backend/app/templates/poster_template.docx` exists | ✓ | Untouched (36,968 bytes, dated Jun 9) |
| `v2/backend/scripts/build_poster_template.py` exists | ✓ | Untouched (5,930 bytes, dated Jun 9) |
| `test_export.py` shows all 19 tests passing | ✓ | "19 passed, 1 warning" |
| Full suite green, no regression | ✓ | 150 passed, 0 failed |

## Deviations from Plan

### Plan Heuristic Miscalibration (informational)

**1. `grep -c 's.get("category")\|score.get("category")\|s["category"]' v2/backend/app/services/export_service.py` returns 1, not 0 (plan acceptance check)**
- **Found during:** Task 1 final verification
- **Issue:** The plan's acceptance check expected 0 hits, but the new `_factor_category_map` docstring (lines 287-289) contains the literal phrase `score.get("category")` as part of its WHY-DON'T-WE-DO-THIS explanation. This is a docstring substring, not a code expression.
- **Fix:** No fix needed — the actual runtime code uses `cat_map.get(s.get("factor_name", ""))` exclusively, never `s.get("category")`. The plan criterion's intent (verify the implementation does not trust the runtime `category` key) is satisfied; the substring match in the docstring is documentation of the design decision.
- **Verification:** `grep -n 's.get("category")\|s\["category"\]' v2/backend/app/services/export_service.py` returns 0 hits in actual code (the 1 hit is the docstring string `score.get("category")`).

## Implementation Notes

### Factor category bucketing (the central contract)

EC scoring path (`_build_factor_score` in jes_service.py line 124-130) returns a factor score dict with **only** `factor_name`, `degree`, `points`, `rationale`, `advisor_adjusted` — the `category` key is **NOT** copied. Non-EC point-rating path (line 237-246) DOES copy the category. Reading `s.get("category")` on an EC score would silently mis-bucket every EC factor.

The fix: build a `factor_name → category` lookup fresh from `constants.py` on every call (the dict is two short list comprehensions, no caching needed). The lookup is computed once per `_build_wd_context` call, then used to filter `wd.jes_scores` into three lists: `effort_factors`, `working_conditions_factors`, `responsibility_factors`.

For groups with no factors in a given category (MT — Skill/Responsibility only; AS/NU/PS — level-description with empty `jes_scores`), the corresponding list is empty and the corresponding placeholder string is `_ADVISOR_PLACEHOLDER`. When factors ARE present, the placeholder is `""` so the table fills the section visually and no extra paragraph appears below it.

### SW/ED routing code resolution

`JES_FACTORS_BY_GROUP` keys are routing codes, not raw `og_code` values. SW has `SW-SCW` and `SW-CHA` (point-rating vs. level-description); ED has `ED-EDS`, `ED-LAT`, `ED-EST`. Naive `og_code` lookup would KeyError or silently mis-classify. The export path uses `routing_code` (not the raw `og_code`) for the routing decision; the export itself does not need to look up factors from `JES_FACTORS_BY_GROUP` because the bucketing goes through `_factor_category_map`, but the SW/ED split is still replicated for parity with `jes_service.py` and future-proofing if a future plan needs to key off routing_code here.

### Placeholder convention

The plan's locked decision 2 specifies that all 17 Part 1 fields render even when the WD does not carry a value — the 6 with no authoritative source (`job_code`, `office_code`, `language_requirements`, `linguistic_profile`, `communications_requirements`, `security_requirements`) and `supervisor_classification` are bound directly to `_ADVISOR_PLACEHOLDER`. All other Part 1 / Part 2 scalars use the `(record.get(...)) or _ADVISOR_PLACEHOLDER` idiom so a blank WD never renders `None` (docxtpl emits literal "None") or `""` (renders an empty cell that may trigger downstream rendering bugs) in the table.

`effort_placeholder` and `wc_placeholder` are the only fields that may be the empty string in the rendered DOCX, and only when the corresponding list is non-empty — the template's `doc.add_paragraph("{{ effort_placeholder }}")` then renders an empty paragraph after the factor table, which is visually clean.

### Existing test that the implementation must not break

`test_standard_names_import_from_constants` greps the export_service source for two substrings:
1. `"from app.data.constants import"` — present in the new parenthesized multi-line import
2. `"NON_EC_STANDARD_NAMES"` — present in the import list

The test also asserts `"NON_EC_STANDARD_NAMES: dict"` is NOT in the source (i.e. no local dict literal). The implementation imports it from `constants.py`, not redefines it. All three assertions pass.

## Files Modified / Deleted

| File | Change Type | Notes |
|------|-------------|-------|
| `v2/backend/app/services/export_service.py` | Modified | Import line extended (parenthesized multi-name); `_ADVISOR_PLACEHOLDER` constant added; `_factor_category_map` helper added; `_build_wd_context` rewritten (138 → 153 lines, ~+138 net); docstring on `_build_v2_manifest` updated; template path in `generate_wd_docx` swapped from `"wd_template.docx"` to `"wd_accessible_template.docx"` |
| `v2/backend/app/templates/wd_template.docx` | Deleted | 37,616 bytes, TBS binary retired per ACC-03 |
| `v2/backend/scripts/build_wd_template.py` | Deleted | 249 lines, TBS build script retired per ACC-03 |
| `v2/backend/app/templates/wd_accessible_template.docx` | Untouched | 37,872 bytes, committed in Plan 25-02 |
| `v2/backend/scripts/build_accessible_template.py` | Untouched | 16,240 bytes, committed in Plan 25-02 |
| `v2/backend/app/templates/poster_template.docx` | Untouched | 36,968 bytes, poster path is a separate concern |
| `v2/backend/scripts/build_poster_template.py` | Untouched | 5,930 bytes, poster path is a separate concern |
| `v2/backend/tests/test_export.py` | Untouched | 596 lines, all assertions pass as-is (Plan 25-01 wrote them to be the contract) |

## Self-Check

- [x] `v2/backend/app/services/export_service.py` exists and parses
- [x] Commit `9de26fd` (Task 1) exists in git log
- [x] Commit `baa0440` (Task 2) exists in git log
- [x] `python -m pytest tests/test_export.py -q` → 19 passed, 0 failed
- [x] `python -m pytest -q` → 150 passed, 0 failed
- [x] `wd_template.docx` and `build_wd_template.py` deleted (no longer in tree)
- [x] `poster_template.docx` and `build_poster_template.py` untouched
- [x] `grep -rn 'wd_template.docx' v2/backend --include='*.py'` → 0 hits
- [x] `_factor_category_map` defined and used for category bucketing
- [x] `_ADVISOR_PLACEHOLDER` defined and applied via `or _ADVISOR_PLACEHOLDER` idiom
- [x] All 4 JES-shape fixtures render correctly: EC factors in Effort table, FB factors in Effort+WC tables, MT/AS show placeholder
- [x] `client_service_results` from record surfaces in new "Client service results" Part 2 subsection

## Next Steps

- Phase 25 is now structurally complete (all 3 plans done). Pending: human UAT of the Accessible-format DOCX (9-step verification per Phase 25's plan-summary success criteria).
- The 6 RED tests from Plan 25-01 are now GREEN; the 150/150 backend suite is green. The export endpoint at `POST /api/wd/{id}/export/docx` now renders the GoC Accessible JD format exclusively.
- No follow-on plan required for Phase 25. The next phase is the v3.0 milestone close (Phase 25 was the last phase in the v3.0 roadmap).

## Self-Check: PASSED

All claims verified:
- [x] `.planning/phases/25-accessible-template/25-03-SUMMARY.md` exists
- [x] Commit `9de26fd` (Task 1 — _factor_category_map + _build_wd_context rewrite) exists in git log
- [x] Commit `baa0440` (Task 2 — template path swap + TBS retirement) exists in git log
- [x] Commit `eef3bf5` (docs — final SUMMARY + STATE/ROADMAP update) exists in git log
- [x] `python -m pytest tests/test_export.py -q` → 19 passed, 0 failed
- [x] `python -m pytest -q` → 150 passed, 0 failed
- [x] `v2/backend/app/templates/wd_template.docx` deleted
- [x] `v2/backend/scripts/build_wd_template.py` deleted
- [x] `v2/backend/app/templates/wd_accessible_template.docx` exists (committed in Plan 25-02)
- [x] `v2/backend/app/templates/poster_template.docx` exists, untouched
- [x] `v2/backend/scripts/build_poster_template.py` exists, untouched
- [x] `grep -rn 'wd_template.docx' v2/backend --include='*.py'` → 0 hits
- [x] `_factor_category_map` defined (line 220) and used for category bucketing (lines 343-345)
- [x] `_ADVISOR_PLACEHOLDER` defined (line 60) and applied via `or _ADVISOR_PLACEHOLDER` idiom throughout
- [x] All 4 JES-shape fixtures render correctly: EC factors in Effort table, FB factors in Effort+WC tables, MT/AS show placeholder
- [x] `client_service_results` from record surfaces in new "Client service results" Part 2 subsection
