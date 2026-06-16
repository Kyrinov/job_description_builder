---
phase: 25-accessible-template
plan: 01
type: tdd
subsystem: export
tags: [tdd, red-baseline, acc-01, acc-02, acc-04, accessible-template, fixture-helpers, fixture-helpers-RED, RED-baseline]
dependency_graph:
  requires: []
  provides:
    - "ACC-01/02/04 RED test baseline in v2/backend/tests/test_export.py"
    - "4 JES-shape fixture helpers (_create_wd_ec, _create_wd_point_rating_with_effort, _create_wd_point_rating_no_effort, _create_wd_level_description)"
    - "_docx_text helper for python-docx read-back of rendered DOCX"
  affects:
    - "Plans 25-02 and 25-03 (turn these RED tests GREEN)"
tech-stack:
  added: []
  patterns:
    - "python-docx read-back of docxtpl-rendered output for content-presence assertions"
    - "JES-shape fixture helper pattern (4 variants covering EC, point-rating-with-effort, point-rating-without-effort, level-description)"
    - "Capital-letter disambiguation: 'Effort' (heading) vs 'effort' (lowercase in factor_name) to distinguish Accessible section from JES Factor column"
key-files:
  created: []
  modified:
    - v2/backend/tests/test_export.py
decisions:
  - "Added 'source' and 'last_modified' fields to _QUAL_SEED — QualificationStandard Pydantic model requires them; default _QUAL_SEED in plan omitted these and would have caused 500 on PATCH (Rule 3 auto-fix)"
  - "Added 3 extra assertions beyond plan-specified minimum to make all 6 tests RED (vs. the 3/3 RED/GREEN state of the plan's literal test bodies). Deviations: 'Effort' heading check on EC/FB tests; 'Citizens receive timely' check on content_presence test. Both assertions are designed to PASS once the new Accessible template lands"
  - "Pinned 4 JES-shape fixtures to the exact factor_name strings from constants.py (Physical effort, Sensory effort, Working conditions, Risk to health, Work environment, Knowledge, Decision making, Communication) — category lookups in Plan 02's _factor_category_map will resolve correctly"
metrics:
  duration_minutes: 7
  completed_date: 2026-06-16
  task_count: 2
  file_count: 1
---

# Phase 25 Plan 01: Accessible Template RED Baseline Summary

RED TDD baseline for the GoC Accessible JD format. Adds 4 JES-shape fixture helpers and 6 RED test functions to `v2/backend/tests/test_export.py` that pin the ACC-01 (structure), ACC-02 (Effort/Working-Conditions bucketing), and ACC-04 (content-presence) contracts before any implementation. Existing 13 export tests continue to pass; the 6 new tests fail as expected against the current TBS Work Description template. Plans 25-02 and 25-03 will turn these RED tests GREEN by building `wd_accessible_template.docx` and rewriting `_build_wd_context`.

**One-liner:** 4 JES-shape fixture helpers + 6 RED tests (4 for ACC-02 bucketing, 1 for ACC-04 content-presence, 1 for ACC-01 structure) pin the Accessible-template contract.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add 4 JES-shape fixture helpers | `9d1b007` | `v2/backend/tests/test_export.py` |
| 2 | Add 6 RED tests (ACC-02 + ACC-04 + ACC-01) | `ab8ed77` | `v2/backend/tests/test_export.py` |

## Test Results

```
$ cd v2/backend && python -m pytest tests/test_export.py -q
=================== 6 failed, 13 passed, 1 warning in 7.49s ===================
```

**RED tests (6 — pin the Accessible-template contract):**
- `test_accessible_effort_ec_populated` — Fails on missing "Effort" heading (TBS has no Effort section)
- `test_accessible_effort_fb_populated` — Fails on missing "Effort" heading for FB
- `test_accessible_effort_no_factor_group_placeholder` — Fails on missing "[To be completed by advisor]" placeholder
- `test_accessible_effort_level_description_placeholder` — Fails on missing placeholder for AS
- `test_accessible_content_presence` — Fails on missing "Citizens receive timely" (client_service_results not rendered in TBS)
- `test_accessible_structure_headings` — Fails on missing 7 Part 2 subsection headings + Part 1/2 markers

**Prior tests (13 — all still green):**
- 7 original Phase 20 export tests
- 4 Phase 21 amendments / record-fallback tests
- 2 WR-09 classification-pending tests
- 1 OGX-02 source-shape test (test_standard_names_import_from_constants)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `_QUAL_SEED` missing required Pydantic fields**
- **Found during:** Task 2 — first test run failed with `pydantic_core._pydantic_core.ValidationError: source / last_modified: Field required`
- **Issue:** The plan's `_QUAL_SEED = {"education": ..., "experience": ...}` would fail QualificationStandard Pydantic validation in `app/api/wd.py:236` (`wd.qualification = QS(**raw_qualification)`)
- **Fix:** Added `"source": "EC-05 default"` and `"last_modified": "2026-06-16T00:00:00Z"` to `_QUAL_SEED` — values match what the SPA would send after a default-qual assignment
- **Files modified:** `v2/backend/tests/test_export.py`
- **Commit:** `ab8ed77` (included in Task 2 commit)

### Plan enhancements (intentional, documented)

**2. [Plan enhancement] Strengthened 3 tests to achieve 6/6 RED state**
- **Plan expectation:** "6 RED test_accessible_* tests are failing as expected" (success criteria)
- **Plan-specified test bodies issue:** The literal test bodies in the plan's `<action>` section (e.g., `assert "Physical effort" in text and "Sensory effort" in text and "Working conditions" in text`) all pass against the current TBS template because the JES Factor column already renders factor names. Initial implementation produced **3 RED + 3 GREEN**, not 6 RED.
- **Enhancement:** Added one extra assertion to each of 3 tests to make them meaningfully RED:
  - `test_accessible_effort_ec_populated`: Added `assert "Effort" in text` (capital E — distinguishes Accessible "Effort" section heading from "Physical effort"/"Sensory effort" factor names with lowercase 'e' in TBS Factor column)
  - `test_accessible_effort_fb_populated`: Same `assert "Effort" in text` for FB
  - `test_accessible_content_presence`: Added `assert "Citizens receive timely" in text` to verify `record.client_service_results` is actually rendered in the new "Client service results" Part 2 subsection (the seeded text in `_RECORD_SEED`)
- **Result:** 6 failed, 13 passed — matches plan success criteria
- **Justification:** These additions implement the plan's *behavior spec* (e.g., "in the Working Conditions section") more strictly than the literal test bodies. The added assertions are designed to PASS once Plan 02 builds the Accessible template with the new Effort section and Client service results subsection.

## Acceptance Criteria Verification

| Criterion | Status | Notes |
|-----------|--------|-------|
| All 4 fixture helpers exist | ✓ | `_create_wd_ec`, `_create_wd_point_rating_with_effort`, `_create_wd_point_rating_no_effort`, `_create_wd_level_description` |
| "Physical effort" appears ≥2 times | ✓ | 2 (EC + FB fixtures) |
| "client_service_results" appears ≥1 time | ✓ | 1 (`_RECORD_SEED` constant) |
| 6 `test_accessible_*` async test functions | ✓ | `grep -c "async def test_accessible"` → 6 |
| `_docx_text` helper exists | ✓ | Line 444 |
| "To be completed by advisor" appears ≥2 times | ✓ | 7 occurrences (constant + assertions + error messages) |
| 6 RED tests fail, 13 prior tests pass | ✓ | Final pytest result: "6 failed, 13 passed" |
| No `pytest.mark.skip` used | ✓ | All 6 tests are active RED gates |
| Fixture helpers use exact factor_name strings from constants.py | ✓ | Verified against `EC_JES_ELEMENTS` (lines 1366-1376) and `JES_FACTORS_BY_GROUP["FB"]` (lines 1409-1420) |
| 4 fixtures PATCH duties, record, qualification | ✓ | All 4 helpers include `_DUTY_SEED`, `_RECORD_SEED`, `_QUAL_SEED` |

## Files Modified

| File | Change Type | Lines Added |
|------|-------------|-------------|
| `v2/backend/tests/test_export.py` | Add imports (`io`, `docx`) + 4 fixture helpers + `_docx_text` helper + 6 RED tests | +323 (Task 1: 139, Task 2: 184) |

## Implementation Notes

### Fixture helper design

Each fixture PATCHes a single WD in one call (no chaining), then asserts `200` and returns the `wd_id`. The PATCH body shape was derived from `app/api/wd.py:203-245` (`patch_wd` endpoint) — `record`, `duties`, and `qualification` are top-level WDPatchRequest fields, while `confirmed_og`, `og_level`, `jes_total_points`, and `jes_scores` are also top-level. This lets each fixture populate all required fields in one PATCH (faster than sequential PATCHes).

### Factor name disambiguation trick

`assert "Effort" in text` (capital E) works because:
- In TBS: factor names are `"Physical effort"`, `"Sensory effort"` (lowercase 'e'). The string `"Effort"` (capital E) does not appear in the rendered DOCX.
- In Accessible format: `"Effort"` is a Heading 2 (capital E). The string appears as a section heading.

This is a stable disambiguation signal that doesn't require parsing the XML or checking heading styles — just the flat text dump from python-docx.

### Content-presence test design

The 3 Jinja2-leak guards (`"{{"`, `"\nNone\n"`, `"%}"`) are minimal regression-detection surface. They will catch:
- A new `{{ var }}` tag added to the Accessible template that isn't provided in the context (Jinja2 UndefinedError would normally raise, but if docxtpl defaults to empty string for missing vars, the `{{` guard catches the literal tag)
- A new field passed as `None` (docxtpl uses `str(None)` → `"None"` in the rendered XML; `\nNone\n` guards against a bare line token)
- A new `{% ... %}` block tag that doesn't resolve

The `client_service_results` assertion is the "positive content" check — proves that a known seed string actually appears in the new "Client service results" subsection. This is the strongest "data path works" assertion in the test suite.

## Self-Check

- [x] `v2/backend/tests/test_export.py` exists and contains the new helpers and tests
- [x] Commit `9d1b007` (Task 1 — fixture helpers) exists in git log
- [x] Commit `ab8ed77` (Task 2 — RED tests) exists in git log
- [x] `python -m pytest tests/test_export.py -q` shows "6 failed, 13 passed"
- [x] All 4 fixture helpers present and use exact factor_name strings from constants.py
- [x] All 6 test functions present and named `test_accessible_*`
- [x] `_docx_text` helper present at module level

## Next Steps

Plans 25-02 and 25-03 will:
1. Build `v2/backend/scripts/build_accessible_template.py` (Plan 25-02) — copy `build_wd_template.py` pattern, target the 7 Part 2 subsection headings + 17-field position-identification table from the reference document
2. Add `_factor_category_map()` helper in `export_service.py` (Plan 25-03) — merge `EC_JES_ELEMENTS` + `JES_FACTORS_BY_GROUP` into one `{factor_name: category}` dict, then bucket `wd.jes_scores` into Effort vs. Working Conditions lists, with `"[To be completed by advisor]"` fallback for groups without per-factor category data (MT, SW-SCW, every level-description group)
3. Rewrite `_build_wd_context()` to surface `record.client_service_results` in the "Client service results" Part 2 subsection (Plan 25-03)
4. Update `_resolve_template_path` call site in `generate_wd_docx` to point at `wd_accessible_template.docx` (Plan 25-03)
5. Retire `wd_template.docx` and `build_wd_template.py` per ACC-03 (Plan 25-03)

After both plans land, this plan's 6 RED tests should go GREEN.

## Self-Check: PASSED

All claims verified:
- [x] `v2/backend/tests/test_export.py` exists with new helpers and tests (final line count: 540+)
- [x] Commit `9d1b007` exists in git log (Task 1 — fixture helpers)
- [x] Commit `ab8ed77` exists in git log (Task 2 — RED tests)
- [x] `python -m pytest tests/test_export.py -q` shows "6 failed, 13 passed" (verified)
- [x] All 4 fixture helpers present and use exact factor_name strings from constants.py
- [x] All 6 test functions present and named `test_accessible_*`
- [x] `_docx_text` helper present at module level
