---
phase: 25-accessible-template
verified: 2026-06-16T16:30:00Z
status: human_needed
score: 11/11 must-haves verified
overrides_applied: 0
requirements_covered: [ACC-01, ACC-02, ACC-03, ACC-04]
requirements_satisfied: 4/4
roadmap_scs_verified: 4/4
test_evidence:
  backend_pytest_full: 150/150 passed
  export_tests: 19/19 passed (6 RED tests from Plan 25-01 now GREEN)
  build_accessible_template: prints "Accessible template OK", 29/29 required Jinja2 vars declared
  end_to_end_render: 37,758 bytes DOCX with all 7 Part 2 headings + Part 1/2 markers, no Jinja2/None leaks
deferred: []
human_verification:
  - test: "Open a rendered DOCX in Word/LibreOffice and inspect visual layout"
    expected: "Part 1: 17-field position table is correctly formatted (Light Grid Accent 1 style); 3 signature blocks render with print-and-sign lines; Part 2 headings match GoC reference document order and styling; Effort/Working-conditions tables render with Factor/Degree/Points columns"
    why_human: "python-docx text extraction confirms text content but cannot evaluate table gridlines, paragraph spacing, font choices, or section page breaks"
  - test: "Verify signature blocks contain NO Jinja2-rendered text"
    expected: "Each of the 3 signature blocks shows literal 'Name: ____', 'Signature: ____', 'Date: ____' print-and-sign lines (no field labels, no data binding)"
    why_human: "Word's edit-pane view confirms the blocks are plain text, not auto-generated fields"
  - test: "Visual check of {%tr for %} loops in Effort and Working conditions tables"
    expected: "Tables correctly expand/contract based on factor count; empty tables show only header row + placeholder paragraph; tables with factors show header + N data rows (no empty rows, no garbled for/endfor tags visible)"
    why_human: "Loop expansion behaviour under different factor counts is best inspected interactively"
  - test: "Verify the 'Source Document Version Manifest' section at end of DOCX"
    expected: "Heading 1 'Source Document Version Manifest' followed by one paragraph per source (NOC 4163, JES standard, OG, QUAL) with format 'SOURCE_TYPE - source_id (vsource_version, retrieved DATE)'"
    why_human: "Section is appended after the Part 2 content; visual ordering needs human confirmation"
  - test: "Verify the amendments appendix is hidden when no amendments exist"
    expected: "For a WD with no manager amendments, the 'Appendix: Manager Amendments for Review' Heading 1 should NOT appear in the document"
    why_human: "The {%p if amendments|length > 0 %} gate is in place; need visual confirmation no empty appendix renders"
  - test: "Open a DOCX exported for an MT (or level-description) WD and confirm placeholder"
    expected: "Effort and Working conditions sections show '[To be completed by advisor]' placeholder text; tables are empty (just header row)"
    why_human: "Visual confirmation of placeholder text rendering vs empty cell"
  - test: "Run the export path from the SPA and confirm download works end-to-end"
    expected: "Clicking 'Word document (.docx)' in the Review screen triggers a file download with a slugified filename like 'policy-analyst-work-description.docx' and the file opens correctly in Word"
    why_human: "Browser download + Word render is a complete UI flow that requires interactive testing"
  - test: "Confirm the poster export is unaffected by the template path swap"
    expected: "POST /api/wd/{id}/export/poster still renders poster_template.docx with bilingual headers, OG/level, quals, and 3-5 duties - same output as before Phase 25"
    why_human: "poster_template.docx was untouched, but a visual diff confirms parity"
  - test: "Open the DOCX in Word and use 'Inspect Document' to confirm no embedded data leaks"
    expected: "No hidden fields, no personal metadata, no template-internal variables leaking into output"
    why_human: "Word's document inspector catches issues python-docx text extraction misses"
---

# Phase 25: Accessible Template - Verification Report

**Phase Goal:** The exported DOCX uses the Accessible JD format with both parts fully populated - including Effort and Working Conditions derived from JES factor scores - and every template variable resolves to a non-empty string for a completed WD.

**Verified:** 2026-06-16T16:30:00Z
**Status:** human_needed
**Verification mode:** initial (no prior VERIFICATION.md existed; only 25-VALIDATION.md which is the validation strategy, not a verification report)
**Verifier:** gsd-verifier (auto)

---

## Goal Achievement

### Observable Truths - Roadmap Success Criteria

| #   | Success Criterion                                                                                                                                  | Status     | Evidence                                                                                                                                                                                                                                                                                                                                                                                          |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | POST `/api/wd/{id}/export/docx` produces a DOCX structured per the Accessible JD format: Part 1 (position ID + 3 signature blocks) and Part 2 (Org Context, Client Service Results, Key Activities, Skills, Effort, Responsibilities, Working Conditions) | VERIFIED   | `v2/backend/app/services/export_service.py:524` calls `_resolve_template_path("wd_accessible_template.docx")`; `v2/backend/app/templates/wd_accessible_template.docx` (37,872 B) is the rendered template; end-to-end render of an EC WD produces a 37,758 B DOCX with 35 paragraphs + 3 tables (17-row position table, effort table, working-conditions table) + 3 print-and-sign signature blocks; all 7 Part 2 headings present in rendered text |
| 2   | Effort and Working Conditions sections are populated from JES factor scores for OG groups whose JES standard defines those factors; sections show "[To be completed by advisor]" only where the OG's JES does not define them | VERIFIED   | `_factor_category_map()` (lines 220-244) merges `EC_JES_ELEMENTS` + `JES_FACTORS_BY_GROUP` into a 31-entry `{factor_name: category}` dict. Behavioral spot-check: EC WD bucketed `Physical effort` + `Sensory effort` to effort_factors (2 items), `Working conditions` to working_conditions_factors (1 item), effort_placeholder=''; FB WD bucketed 2 effort + 2 conditions factors; MT (no effort/conditions factors) and AS (level-description) - 0 factors in either list, both placeholders = `"[To be completed by advisor]"`; tests `test_accessible_effort_ec_populated`, `test_accessible_effort_fb_populated`, `test_accessible_effort_no_factor_group_placeholder`, `test_accessible_effort_level_description_placeholder` all PASS |
| 3   | A content-presence test opens the rendered DOCX via python-docx and confirms every non-placeholder template variable resolves to a non-empty string for a fully-completed WD | VERIFIED   | `test_accessible_content_presence` (test_export.py:547-576) PASSES - uses `_docx_text` helper (line 444) to read back `resp.content` via `docx.Document(io.BytesIO(content))`, asserts `"{{" not in text`, `"\nNone\n" not in text` (wrapped), `"%}" not in text`, plus `"Citizens receive timely" in text` (positive content check for `record.client_service_results`). End-to-end render also confirmed: no `{{`, no `%}`, no `\nNone\n` leaks in the rendered DOCX |
| 4   | The previous TBS WD template is retired; all existing export tests pass with assertions updated to the Accessible format structure; the poster DOCX template is unchanged | VERIFIED   | `v2/backend/app/templates/wd_template.docx` and `v2/backend/scripts/build_wd_template.py` deleted in commit `baa0440` (verified by `git log --all` showing the delete commit; both files absent from `ls`); `grep -rn "wd_template.docx" v2/backend --include="*.py"` returns 0 hits; `v2/backend/app/templates/poster_template.docx` last modified `Jun 9 15:08` and last git-touched in `97dae22` (Phase 20); `v2/backend/scripts/build_poster_template.py` last modified `Jun 9 15:05` and unchanged; all 19/19 export tests pass |

**Roadmap SCs:** 4/4 verified

---

## Per-Plan Must-Have Coverage

### Plan 25-01 (Wave 0 RED Baseline)

| Must-Have | Type | Status | Evidence |
| --- | --- | --- | --- |
| 4 JES-shape fixture helpers covering EC, point-rating-with-Effort (FB), point-rating-without-Effort (MT), level-description (AS) | truth | VERIFIED | `test_export.py:94-198` - `_create_wd_ec` (line 94), `_create_wd_point_rating_with_effort` (line 123), `_create_wd_point_rating_no_effort` (line 152), `_create_wd_level_description` (line 178). Each PATCHes duties, record, qualification in a single call. |
| Fixture helpers use exact factor_name strings from constants.py | truth | VERIFIED | EC fixture uses `Physical effort`, `Sensory effort`, `Working conditions`, `Communication` (all match `EC_JES_ELEMENTS`). FB fixture uses `Physical effort`, `Sensory effort`, `Risk to health`, `Work environment`, `Knowledge` (all match `JES_FACTORS_BY_GROUP["FB"]`). |
| 6 RED `test_accessible_*` test functions exist | truth | VERIFIED | `grep -c "async def test_accessible" v2/backend/tests/test_export.py` = 6: `test_accessible_effort_ec_populated`, `test_accessible_effort_fb_populated`, `test_accessible_effort_no_factor_group_placeholder`, `test_accessible_effort_level_description_placeholder`, `test_accessible_content_presence`, `test_accessible_structure_headings`. |
| `_docx_text` helper exists at module level | truth | VERIFIED | `test_export.py:444-456` - `def _docx_text(content: bytes) -> str` reads back DOCX via `docx.Document(io.BytesIO(content))`, concatenates paragraphs + table-cell text. |
| Existing 13 tests unaffected by new helpers | truth | VERIFIED | 19 tests now pass in `tests/test_export.py` (13 original + 6 new). The 6 RED tests from this plan are now GREEN in `25-03`'s run. |
| `v2/backend/tests/test_export.py` with helpers + tests | artifact | VERIFIED | 596 lines. Imports `io`, `docx`. All 4 fixture helpers present. `_DUTY_SEED`, `_RECORD_SEED`, `_QUAL_SEED` constants defined. |

**Plan 25-01 must-haves:** 6/6 verified

### Plan 25-02 (Build Script + DOCX Artifact)

| Must-Have | Type | Status | Evidence |
| --- | --- | --- | --- |
| `v2/backend/scripts/build_accessible_template.py` regenerates `wd_accessible_template.docx` and self-verifies | truth | VERIFIED | `python v2/backend/scripts/build_accessible_template.py` prints "Accessible template OK" and exits 0. The script writes the DOCX then reloads with `DocxTemplate(OUTPUT_PATH)` and calls `get_undeclared_template_variables()` to assert all 29 required vars are declared. |
| Template has Part 1 (17-field position table + 3 signature blocks) and all 7 Part 2 subsection headings | truth | VERIFIED | `build_accessible_template.py:110-150` creates 17-row position table with 17 (label, value) pairs; lines 140-150 emit 3 static signature blocks (Employee statement, Supervisor statement, Manager authorization) each with 3 plain "Name: __" / "Signature: __" / "Date: __" paragraphs (NO Jinja2 vars). Lines 158-235 create all 7 Part 2 Heading-2 subsections. End-to-end render confirms all 7 headings present in rendered DOCX. |
| `get_undeclared_template_variables()` confirms every required Jinja2 variable is declared | truth | VERIFIED | Build script output: `Accessible template variables (29): [amendments, client_service_results_text, communications_requirements, ...]`. Self-verify asserts `required - set(undeclared) == empty`; passes. |
| `v2/backend/scripts/build_accessible_template.py` | artifact | VERIFIED | 306 lines. Module docstring documents the full Jinja2 variable contract. `_set_cell_text` helper copied verbatim from `build_wd_template.py`. `OUTPUT_PATH = "v2/backend/app/templates/wd_accessible_template.docx"`. |
| `v2/backend/app/templates/wd_accessible_template.docx` | artifact | VERIFIED | 37,872 bytes (initial commit), regenerated to same shape on re-run. `python -c "import docx; d=docx.Document('v2/backend/app/templates/wd_accessible_template.docx')"` shows 3 tables (17-row position, effort, working-conditions). |

**Plan 25-02 must-haves:** 5/5 verified

### Plan 25-03 (Export Path Swap + TBS Retirement)

| Must-Have | Type | Status | Evidence |
| --- | --- | --- | --- |
| `_factor_category_map()` helper exists and is used for category bucketing | truth | VERIFIED | `export_service.py:220-244` - merges `EC_JES_ELEMENTS` + `JES_FACTORS_BY_GROUP` into `{factor_name: category}`. Called at line 341. Behavioral spot-check: returns 31 entries; `Physical effort`->`Effort`, `Working conditions`->`Conditions`, `Risk to health`->`Conditions`, `Knowledge`->`Skill`, `Decision making`->`Responsibility`. |
| `_build_wd_context` rewritten to produce all 29 Accessible fields with correct bucketing and placeholders | truth | VERIFIED | `export_service.py:281-413`. Behavioral spot-check: EC WD produces 2 effort_factors + 1 working_conditions_factor + 0 responsibility_factors; effort_placeholder='' (factors present); FB WD produces 2+2; MT/AS WD produce 0+0 with both placeholders = `"[To be completed by advisor]"`. All 29 required keys present, no None values, no extra keys. |
| POST `/api/wd/{id}/export/docx` renders the Accessible template | truth | VERIFIED | `export_service.py:524` - `template_path = _resolve_template_path("wd_accessible_template.docx")` (was `wd_template.docx` in Phase 20). End-to-end render of an EC WD returns a 37,758-byte DOCX with all 7 Part 2 headings + Part 1/2 markers + EC factor names + client_service_results text. |
| EC-scored WDs correctly populate Effort/Conditions despite missing `category` key on persisted dict | truth | VERIFIED | Category is derived via `cat_map.get(s.get("factor_name", ""))` (lines 343-345) - never reads `s.get("category")` from the persisted dict. The EC scoring path omits the `category` field, so this is the correct fix. Implementation explicitly documents this in the docstring (lines 222-237). |
| Every non-placeholder variable resolves to non-empty string | truth | VERIFIED | Behavioral spot-check across EC, FB, MT, AS contexts: no `None` values; empty strings only on `effort_placeholder`/`wc_placeholder` (intentional - when factors are present the table fills the section visually). All 17 Part 1 fields use the `or _ADVISOR_PLACEHOLDER` idiom (line 374-390) so blank WDs never render `None` or `""` in the table. `test_accessible_content_presence` PASSES. |
| Previous TBS template + build script retired; poster unchanged | truth | VERIFIED | Commit `baa0440` deleted `v2/backend/app/templates/wd_template.docx` and `v2/backend/scripts/build_wd_template.py` via `git rm`. `ls` confirms absence. `grep -rn "wd_template.docx" v2/backend --include="*.py"` returns 0 hits. `poster_template.docx` (36,968 B) and `build_poster_template.py` (5,930 B) last modified `Jun 9` and last git-touched in `97dae22` (Phase 20). |
| `v2/backend/app/services/export_service.py` with `_factor_category_map` and rewritten `_build_wd_context` | artifact | VERIFIED | 577 lines. `_factor_category_map` at line 220. `_ADVISOR_PLACEHOLDER` constant at line 61. `_build_wd_context` rewritten to 132 lines (281-413). Template path in `generate_wd_docx` swapped at line 524. |
| export_service.py -> wd_accessible_template.docx | key_link | WIRED | Line 524: `template_path = _resolve_template_path("wd_accessible_template.docx")`. End-to-end render proves the wiring (37,758 B DOCX produced with all 7 Part 2 headings). |
| _build_wd_context -> EC_JES_ELEMENTS + JES_FACTORS_BY_GROUP | key_link | WIRED | Lines 36-40 import both constants. Line 220-244 builds the category map. Lines 343-345 bucket `wd.jes_scores` using the map. Behavioral spot-check confirms correct bucketing for EC, FB, MT, AS. |

**Plan 25-03 must-haves:** 9/9 verified

---

## Requirement-by-Requirement Verification

| REQ-ID | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| **ACC-01** | 25-02 | `build_accessible_template.py` builds and self-verifies `app/templates/wd_accessible_template.docx`; Part 1: position ID + 3 signature blocks; Part 2: subsections; `get_undeclared_template_variables()` confirms all template variables are declared | SATISFIED | Build script runs cleanly, prints "Accessible template OK", 29/29 required Jinja2 vars declared. Note: REQUIREMENTS.md says "6 subsections" but actual implementation is **7** (matches ROADMAP SC #1 and the GoC reference document). The 7th is "Working conditions". This is a documentation discrepancy, not an implementation gap. |
| **ACC-02** | 25-03 | `_build_wd_context()` populates all Part 2 fields; Effort and Working Conditions map from JES factor scores where the OG's JES defines them; placeholder where the JES does not define them | SATISFIED | Lines 281-413 of `export_service.py` populate all 29 fields. Lines 343-345 bucket factors via `_factor_category_map()`. Lines 351-360 set placeholders to `""` when factors present, `[To be completed by advisor]` when absent. Behavioral spot-check: EC/FB populate; MT/AS show placeholder. All 4 `test_accessible_effort_*` tests pass. |
| **ACC-03** | 25-03 | POST `/api/wd/{id}/export/docx` produces the Accessible format; previous TBS WD template retired; poster DOCX template unchanged; all existing export tests pass | SATISFIED | `export_service.py:524` calls `wd_accessible_template.docx`. TBS files deleted in commit `baa0440`. `poster_template.docx` unchanged. All 19/19 export tests pass (13 original + 6 new). The 13 original tests only asserted MIME/bytes (no TBS-specific text), so they pass unchanged. The 6 NEW tests assert the Accessible structure. |
| **ACC-04** | 25-01, 25-03 | Content-presence test opens rendered DOCX via python-docx and asserts every non-placeholder template variable resolves to non-empty string for fully-completed WD | SATISFIED | `test_accessible_content_presence` (test_export.py:547-576) passes. Uses `_docx_text` helper (line 444) for python-docx readback. Asserts `"{{" not in text`, `"\nNone\n" not in text`, `"%}" not in text` (3 leak guards) plus `"Citizens receive timely" in text` (positive content check). End-to-end behavioral render confirms. |

**Requirements satisfied:** 4/4 (all ACC-* requirements)

### Note on REQUIREMENTS.md accuracy

Two minor documentation discrepancies in REQUIREMENTS.md (not blocking - implementation is correct):
1. **ACC-01** text says "6 subsections" but ROADMAP SC #1 + implementation + tests all confirm **7** subsections. The 7th is "Working conditions" (the 6 in the requirement text omits it). The 7-heading structure matches the GoC Accessible Job Description reference document.
2. **ACC-02** and **ACC-03** are still marked `[ ]` (unchecked) in REQUIREMENTS.md, but all evidence shows they are complete (tests pass, code is in place, TBS retired). The Phase 25 SUMMARY correctly lists them as `requirements-completed: [ACC-02, ACC-03, ACC-04]`. The orchestrator should update REQUIREMENTS.md to mark these as complete.

---

## Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `v2/backend/app/services/export_service.py` | `_factor_category_map` helper + rewritten `_build_wd_context` + Accessible template path | VERIFIED | 577 lines. `_factor_category_map` at line 220, `_ADVISOR_PLACEHOLDER` at line 61, rewritten `_build_wd_context` at lines 281-413, template path swap at line 524. No `TODO`/`FIXME`/`return None`/`return []`/`return {}` anti-patterns. |
| `v2/backend/app/templates/wd_accessible_template.docx` | Committed Accessible-format DOCX template | VERIFIED | 37,872 bytes. Self-verified by `build_accessible_template.py`: 29 required Jinja2 vars declared. End-to-end render: 3 tables (17-row position + effort + working-conditions), 35 paragraphs, 7 Part 2 Heading-2 subsections, 3 print-and-sign signature blocks. |
| `v2/backend/scripts/build_accessible_template.py` | Self-verifying python-docx + docxtpl skeleton builder | VERIFIED | 306 lines. `_set_cell_text` helper duplicated from `build_wd_template.py` per project convention. Self-verify tail calls `get_undeclared_template_variables()` against a 29-key required set. Prints "Accessible template OK" on success. |
| `v2/backend/tests/test_export.py` | 19 export tests (13 original + 6 new) all passing | VERIFIED | 596 lines. 4 fixture helpers + 13 original tests + 6 new `test_accessible_*` tests. All 19 pass. |
| `v2/backend/app/templates/wd_template.docx` | DELETED (TBS retired) | DELETED | Deleted in commit `baa0440`. `ls` confirms absence. `grep -rn "wd_template.docx" v2/backend --include="*.py"` returns 0 hits. |
| `v2/backend/scripts/build_wd_template.py` | DELETED (TBS retired) | DELETED | Deleted in commit `baa0440`. `ls` confirms absence. |
| `v2/backend/app/templates/poster_template.docx` | UNCHANGED | UNCHANGED | 36,968 bytes. Last modified `Jun 9 15:08`. Last git-touched in `97dae22` (Phase 20). `poster_template.docx` and `build_poster_template.py` are untouched by Phase 25. |
| `v2/backend/scripts/build_poster_template.py` | UNCHANGED | UNCHANGED | 5,930 bytes. Last modified `Jun 9 15:05`. |

---

## Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `v2/backend/app/services/export_service.py` (`generate_wd_docx`) | `v2/backend/app/templates/wd_accessible_template.docx` | `_resolve_template_path("wd_accessible_template.docx")` at line 524 | WIRED | End-to-end render of EC WD produces 37,758 B DOCX with all 7 Part 2 headings - proves the wiring. |
| `_build_wd_context` effort/conditions bucketing | `EC_JES_ELEMENTS` + `JES_FACTORS_BY_GROUP` categories | `_factor_category_map().get(score['factor_name'])` at lines 343-345 | WIRED | Behavioral spot-check: EC WD produces 2 effort_factors + 1 working_conditions_factor using constants.py as source of truth. |
| `build_accessible_template.py` | `wd_accessible_template.docx` | `doc.save(OUTPUT_PATH)` then `DocxTemplate(OUTPUT_PATH).get_undeclared_template_variables()` | WIRED | Script runs successfully, writes 37,872 B DOCX, self-verifies 29/29 required vars. |
| `test_export.py` (test_accessible_effort_ec_populated etc.) | `POST /api/wd/{id}/export/docx` | `client.post(...)` then `docx.Document(io.BytesIO(resp.content))` | WIRED | All 6 `test_accessible_*` tests pass. |
| `export_service.py` constants import | `app.data.constants` (EC_JES_ELEMENTS, JES_FACTORS_BY_GROUP, NON_EC_STANDARD_NAMES) | Parenthesized multi-line import at lines 36-40 | WIRED | `test_standard_names_import_from_constants` (line 401) passes - asserts the import is from `app.data.constants` and `NON_EC_STANDARD_NAMES` is in the import list, NOT defined locally. |

---

## Data-Flow Trace (Level 4)

For the central contract: EC WD -> rendered DOCX with Effort factors populated.

| Step | Source | Variable | Populated By | Real Data? |
| --- | --- | --- | --- | --- |
| 1. WD stored in DB | `work_descriptions.data` (JSON) | `wd.jes_scores` | PATCH endpoint (test fixture seeds 4 factors) | Real fixture data (4 EC factors) |
| 2. `_build_wd_context` reads WD | `wd.jes_scores` | `scores = wd.jes_scores or []` (line 342) | Direct field read | Real data |
| 3. Factor category lookup | `app/data/constants.py` | `cat_map = _factor_category_map()` (line 341) | List comprehension over `EC_JES_ELEMENTS` + `JES_FACTORS_BY_GROUP` (lines 238-244) | Real data: 31 entries (e.g., `Physical effort`->`Effort`) |
| 4. Effort bucketing | `scores` + `cat_map` | `effort_factors = [s for s in scores if cat_map.get(s.get("factor_name", "")) == "Effort"]` (line 343) | List comprehension | Real data: EC WD produces 2 effort factors (Physical, Sensory) |
| 5. Working conditions bucketing | `scores` + `cat_map` | `working_conditions_factors = ... == "Conditions"` (line 344) | List comprehension | Real data: EC WD produces 1 working-conditions factor |
| 6. Placeholder logic | `effort_factors` | `effort_placeholder = "" if effort_factors else _ADVISOR_PLACEHOLDER` (line 351) | Conditional | Real: EC has factors -> `""`; MT/AS have none -> `"[To be completed by advisor]"` |
| 7. Context dict returned | All 29 keys | dict at lines 369-413 | `return {...}` | All 29 keys present, no None values |
| 8. Template render | context dict | `DocxTemplate(template_path).render(context)` at line 465 | docxtpl | Real: 37,758 B DOCX rendered |
| 9. python-docx readback | `resp.content` | `docx.Document(io.BytesIO(content))` in test | Test reads back | Real: text contains "Physical effort", "Sensory effort", "Working conditions", "Effort" heading |

**Data-flow status:** FLOWING - every step in the chain uses real data, not hardcoded/empty/static values. The EC test asserts both the negative guards (no `{{`/`None`/`%}`) and positive content (`"Citizens receive timely" in text`), proving the data path is fully wired.

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Export endpoint renders DOCX | `cd v2/backend && python -m pytest tests/test_export.py -q` | `19 passed, 1 warning in 7.28s` | PASS |
| Full backend suite green | `cd v2/backend && python -m pytest -q` | `150 passed, 21 warnings in 10.76s` | PASS |
| Build script self-verifies | `python v2/backend/scripts/build_accessible_template.py` | Prints "Accessible template OK", 29/29 required Jinja2 vars declared | PASS |
| EC factor bucketing (constants lookup) | Manual: `_factor_category_map()["Physical effort"]` | Returns `"Effort"` (31-entry dict) | PASS |
| EC effort_factors populated | Manual: `_build_wd_context` on EC WD | 2 factors (Physical, Sensory), effort_placeholder=`""` | PASS |
| MT placeholder fallback | Manual: `_build_wd_context` on MT WD | effort_factors=`[]`, effort_placeholder=`"[To be completed by advisor]"` | PASS |
| AS placeholder fallback (level-description) | Manual: `_build_wd_context` on AS WD with `jes_scores=[]` | effort_factors=`[]`, working_conditions_factors=`[]`, both placeholders=placeholder string, responsibilities_text=placeholder | PASS |
| End-to-end render: Part 1/2 markers | Manual: render EC WD, read back via python-docx | "Part 1" and "Part 2" both present | PASS |
| End-to-end render: 7 Part 2 headings | Manual: render EC WD, read back | All 7 headings present | PASS |
| End-to-end render: EC factors in DOCX | Manual: render EC WD, read back | "Physical effort", "Sensory effort", "Working conditions" all present | PASS |
| End-to-end render: no Jinja2 leaks | Manual: render EC WD, read back | `"{{"` not in text; `"%}"` not in text; `"\nNone\n"` not in wrapped text | PASS |
| End-to-end render: client_service_results | Manual: render EC WD, read back | "Citizens receive timely, accurate policy guidance." present | PASS |
| TBS template retired | `ls v2/backend/app/templates/wd_template.docx` | "No such file or directory" | PASS |
| TBS build script retired | `ls v2/backend/scripts/build_wd_template.py` | "No such file or directory" | PASS |
| TBS references in code | `grep -rn "wd_template.docx" v2/backend --include="*.py"` | 0 hits | PASS |
| Poster template unchanged | `git log --oneline -- v2/backend/app/templates/poster_template.docx` | Last commit: `97dae22 chore(20): refresh .docx template timestamps` (Phase 20, Jun 10) | PASS |
| All 29 context keys produced | Manual: `_build_wd_context` returns 29 keys, no missing/extra | All 29 required keys present | PASS |
| No anti-patterns in export_service.py | `grep -c "TODO\|FIXME\|return None\|return \[\]\|return {}"` | 0 matches | PASS |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| (none) | - | - | - | - |

**Scan results:** 0 `TODO`, 0 `FIXME`, 0 `return None`, 0 `return []`, 0 `return {}` in `export_service.py` source.

---

## Deferred Items

None. The phase goal and all 4 requirement IDs (ACC-01..04) are addressed by the phase's 3 plans (25-01, 25-02, 25-03).

---

## Gaps Summary

No automated gaps. All 11 must-haves verified (4 roadmap SCs + 4 requirement IDs + 3 plan-level contracts). All 19 export tests pass; full 150/150 backend suite green; build script self-verifies; end-to-end DOCX render produces correct content with no Jinja2/None leaks.

The phase is `human_needed` (not `passed`) because the ROADMAP explicitly notes "pending 9-step human UAT" for Phase 25, and the verifier decision tree requires `human_needed` when visual DOCX quality (table gridlines, paragraph spacing, font choices, page breaks) cannot be verified programmatically. The implementation is complete and all automated gates pass; the human UAT is the final acceptance step.

---

_Verified: 2026-06-16T16:30:00Z_
_Verifier: gsd-verifier (auto)_

