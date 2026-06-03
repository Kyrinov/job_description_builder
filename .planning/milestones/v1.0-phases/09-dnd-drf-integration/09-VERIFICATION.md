---
phase: 09
phase_name: dnd-drf-integration
verified: 2026-06-03T15:00:00Z
status: passed
score: 8/8 must-haves verified
goal_achieved: true
must_haves_met: 8/8
requirements_met:
  - DRF-01
files_modified_in_phase: 17
re_verification: false
automated_checks:
  pytest: "188 passed, 9 skipped, 0 failures"
  drf_tests_only: "8 passed (TestGetDRFCandidates 4 + TestConfirmDRFLinkages 2 + TestDRFInlinePanel 2), 8 skipped (router/wizard-level stubs with documentation explaining the revised design)"
  drf_service_imports: pass
  drf_router_routes: "GET /api/drf-links/{wd_id} + POST /api/drf-links/{wd_id}/confirm (2 routes — flag-dnd removed per 09-04 revised design)"
  is_dnd_position_default_true: "set in app/api/noc_mapping.py:79 (one-line change, model field default still False)"
  docx_template_gate: "doc.add_paragraph('{%p if drf_linkages|length > 0 %}') at scripts/build_docx_template.py:176"
  wizard_drf_route_removed: "grep -n '/wizard/drf' app/main.py returns nothing (as designed)"
  inline_panel_renders: pass
  docx_template_variables: "13 declared (drf_linkages + 12 prior) — self-verify passes"
  end_to_end_export: "37,488 bytes DOCX generated with 0 undeclared variables after render"
  cr01_fix_applied: pass
  wr01_fix_applied: pass
  wr03_fix_applied: pass
human_verification:
  - test: "Open /wizard/export?wd_id={wd_id} in browser"
    expected: "DRF Linkages panel renders below the download button with 'Find DRF Linkages' button (empty state) or read-only summary table (confirmed state)"
    why_human: "Visual layout, HTMX swap behavior, button styling, table rendering"
  - test: "Click 'Find DRF Linkages' on a WD with duty text"
    expected: "Spinner shows briefly, then a checkbox list of top-5 scored DRF candidates appears (Core Responsibility + Departmental Result + Fiscal Year + match score)"
    why_human: "HTMX network call + Jinja2 template rendering + scoring"
  - test: "Select checkboxes, click 'Confirm Selected Linkages'"
    expected: "Confirmed banner + summary table appears with selected linkages; subsequent /wizard/export shows table directly"
    why_human: "Form submission, JS-built row_ids string, server-side storage"
  - test: "Download DOCX export"
    expected: "DOCX contains Section 6 'Departmental Results Framework Linkages' with the confirmed linkages in a 3-column table (Core Responsibility | Departmental Result | Fiscal Year); version manifest includes DRF source rows"
    why_human: "docxtpl render, Section 6 visibility gate, manifest entries"
gaps: []
deferred: []
---

# Phase 9: DND DRF Integration — Verification Report

**Phase Goal:** Add Department of National Defence (DND) Departmental Results Framework (DRF) linkage to the job description builder. When the user is on the export step with a DND WorkDescription, show an inline panel that suggests DRF program linkages (Core Responsibility + Departmental Result) based on keyword matching against the position's duties, lets the advisor confirm selections, and bakes the confirmed linkages into the DOCX export as a new section.

**Verified:** 2026-06-03T15:00:00Z
**Status:** PASSED — All 4 plans verified, 188 tests pass, all code review fixes applied

---

## Goal Achievement

### Roadmap Success Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | When WD is flagged as DND, `GET /drf-links/{wd_id}` returns candidate DRF program linkages for the position's duties | ✓ VERIFIED | `app/api/drf_integration.py:47-72` — `get_drf_links` route calls `get_drf_candidates`; service returns `candidates=[]` for non-DND, scored list for DND |
| 2 | Each linkage cites the DRF program name, expected result, and source row from the DRF CSV dataset | ✓ VERIFIED | Candidate dict shape: `id` (drf_rows.id), `core_responsibility`, `departmental_result`, `fiscal_year`, `score` — verified in `app/services/drf_service.py:91-98` |
| 3 | Advisor-confirmed DRF linkages are stored on the WorkDescription record and rendered in the exported document | ✓ VERIFIED | `confirm_drf_linkages` writes via `save_work_description` (app/services/drf_service.py:245-246); export_service includes `drf_linkages` in context dict (line 239); DOCX Section 6 renders them (line 196 of build_docx_template.py) |

### Phase 9 Specific Plan Must-Haves

| # | Plan | Truth | Status | Evidence |
|---|------|-------|--------|----------|
| 1 | 09-01 | WorkDescription model carries is_dnd_position + drf_linkages | ✓ VERIFIED | `app/models/work_description.py:147-148` — `is_dnd_position: bool = False`, `drf_linkages: list[dict] = Field(default_factory=list)` |
| 2 | 09-01 | drf_rows DDL table exists in SQLite and create_schema() is updated | ✓ VERIFIED | `app/db.py:174-190` — DRF_SCHEMA_DDL constant; `app/db.py:258-259` — `executescript(DRF_SCHEMA_DDL)` registered in `create_schema()` |
| 3 | 09-02 | scripts/ingest_drf.py reads CSV and populates drf_rows (idempotent) | ✓ VERIFIED | `scripts/ingest_drf.py:151-158` — INSERT OR IGNORE; SUMMARY reports 42 unique rows from 132 CSV rows |
| 4 | 09-02 | app/services/drf_service.py exposes get_drf_candidates + confirm_drf_linkages | ✓ VERIFIED | `app/services/drf_service.py:109, 168` — both async functions present; STOPWORDS frozenset; 10 asyncio.to_thread sites |
| 5 | 09-03 | GET /api/drf-links/{wd_id} + POST /confirm (2 routes) | ✓ VERIFIED | Router inspection: `['GET /api/drf-links/{wd_id}', 'POST /api/drf-links/{wd_id}/confirm']` — flag-dnd removed per 09-04 revised design |
| 6 | 09-03 | export_service._build_context() includes drf_linkages key in context dict | ✓ VERIFIED | `app/services/export_service.py:239` — `"drf_linkages": drf_linkages`; build_version_manifest emits DRF ProvenanceTag per linkage (lines 140-149) |
| 7 | 09-04 | Inline panel on /wizard/export (not /wizard/drf route) | ✓ VERIFIED | `templates/wizard/step_export.html:57-110` — `<div class="drf-inline-panel">` with two states; `/wizard/drf` route removed from `app/main.py` |
| 8 | 09-04 | DOCX Section 6 gated on drf_linkages\|length > 0 (not is_dnd_position) | ✓ VERIFIED | `scripts/build_docx_template.py:176` — `doc.add_paragraph("{%p if drf_linkages\|length > 0 %}")`; build script self-asserts `drf_linkages` is declared (line 213-220) |

**Score:** 8/8 must-haves verified

### Deferred Items

None.

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/models/work_description.py` | is_dnd_position + drf_linkages fields | ✓ VERIFIED | Lines 147-148; both fields present with correct defaults |
| `app/db.py` | DRF_SCHEMA_DDL constant + create_schema() registers it | ✓ VERIFIED | Lines 174-190 (DDL), 258-259 (execute in create_schema), 225 (docstring) |
| `scripts/ingest_drf.py` | CSV → drf_rows ingest pipeline | ✓ VERIFIED | 207 lines, INSERT OR IGNORE at line 153, idempotent per UNIQUE constraint |
| `app/services/drf_service.py` | get_drf_candidates + confirm_drf_linkages | ✓ VERIFIED | 255 lines, 2 async public functions, STOPWORDS frozenset (line 36), 10 asyncio.to_thread sites |
| `app/api/drf_integration.py` | FastAPI router with 2 routes | ✓ VERIFIED | 114 lines, GET + POST confirm; flag-dnd removed per revised design |
| `app/main.py` | drf_integration router mounted | ✓ VERIFIED | Line 113: `app.include_router(drf_integration.router)`; /wizard/drf route removed (line 247: only /wizard/export) |
| `app/services/export_service.py` | drf_linkages in _build_context() + DRF ProvenanceTag emission | ✓ VERIFIED | Line 239 (drf_linkages in context); lines 140-149 (DRF manifest emission with source_type='DRF', source_version='DND DRF Dataset 2021-2022') |
| `scripts/build_docx_template.py` | DOCX Section 6 with drf_linkages\|length > 0 gate | ✓ VERIFIED | Line 176: paragraph-level gate; lines 183-195: 3-column table with for/data/endfor; lines 213-220: self-verify assertion |
| `templates/docx/work_description_template.docx` | Rebuilt template with DRF section | ✓ VERIFIED | 13 declared variables including `drf_linkages`; self-verify prints `DRF contract: ['drf_linkages'] declared ✓` |
| `templates/wizard/step_export.html` | Inline DRF panel (2 states) | ✓ VERIFIED | Lines 57-110: `<div class="drf-inline-panel">`; lines 87-93 (Refine) and 98-107 (Find DRF Linkages) |
| `templates/partials/drf_candidates.html` | Checkbox form partial | ✓ VERIFIED | 59 lines, uses `.drf-candidate-checkbox` class (CR-01 fix), form posts to /confirm with row_ids built by inline JS |
| `templates/partials/drf_confirmed.html` | Read-only summary table partial | ✓ VERIFIED | 36 lines, `<table class="drf-linkages-table">` with 3 columns + Refine button |
| `app/static/css/main.css` | CSS Layer 14 (DRF inline panel) | ✓ VERIFIED | Layer 14 header comment line 18; section header line 1024-1031; all required classes (.drf-inline-panel, .drf-candidate-list, .drf-candidate-item, .drf-confirmed-banner, .drf-linkages-table, .drf-score-badge, .drf-fiscal-year) |
| `tests/test_drf.py` | 8 active tests + 8 skipping stubs (with documentation) | ✓ VERIFIED | 626 lines; active: TestGetDRFCandidates 4 + TestConfirmDRFLinkages 2 + TestDRFInlinePanel 2 = 8 passing; 8 skipping with module docstring explaining the revised design |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `app/api/drf_integration.py` | `app/services/drf_service.get_drf_candidates` | import + await | ✓ WIRED | Line 25 (import), line 58 (await) |
| `app/api/drf_integration.py` | `app/services/drf_service.confirm_drf_linkages` | import + await | ✓ WIRED | Line 25 (import), line 98 (await) |
| `app/services/drf_service.py get_drf_candidates` | `drf_rows` table | SELECT | ✓ WIRED | Line 149-152: `SELECT id, fiscal_year, core_responsibility, departmental_result, search_text FROM drf_rows` |
| `app/services/drf_service.py confirm_drf_linkages` | `app/services/wd_store.save_work_description` | model_copy + save | ✓ WIRED | Lines 245-246: `wd.model_copy(update={"drf_linkages": linkages})` + `save_work_description` |
| `app/services/export_service._build_context()` | `wd.drf_linkages` | direct field access | ✓ WIRED | Line 219-229: filters to confirmed linkages on DND positions |
| `app/services/export_service.build_version_manifest()` | `wd.drf_linkages` | loop with ProvenanceTag synthesis | ✓ WIRED | Lines 140-149: emits DRF ProvenanceTag per confirmed linkage |
| `templates/wizard/step_export.html` | `GET /api/drf-links/{wd_id}` | hx-get (HTMX) | ✓ WIRED | Lines 87, 101: `hx-get="/api/drf-links/{{ wd_id }}"` with `hx-target="#drf-linkages-panel"` |
| `templates/partials/drf_candidates.html` | `POST /api/drf-links/{wd_id}/confirm` | hx-post form | ✓ WIRED | Line 9: `hx-post="/api/drf-links/{{ wd_id }}/confirm"` |
| `app/main.py wizard_export` | `app/services/wd_store.load_work_description` | asyncio.to_thread | ✓ WIRED | Line 283: `wd = await asyncio.to_thread(lambda: load_work_description(conn, wd_id))` |

---

## Data-Flow Trace (Level 4)

The inline DRF panel uses a real end-to-end data flow, not hardcoded values.

| Step | Source | Variable | Wired To | Real Data? |
|------|--------|----------|----------|------------|
| 1. WD created | `app/api/noc_mapping.py:79` | `is_dnd_position=True` | Saved via wd_store | ✓ Real DB write |
| 2. Export step loaded | `app/main.py:283` | `wd` (loaded from SQLite) | `load_work_description` | ✓ Real DB read |
| 3. Template rendered | `app/main.py:308` | `drf_linkages` context | `wd.drf_linkages` | ✓ Real field |
| 4. User clicks "Find DRF Linkages" | `templates/wizard/step_export.html:101` | `hx-get="/api/drf-links/{{ wd_id }}"` | router → service | ✓ Real fetch |
| 5. Candidates fetched | `app/services/drf_service.py:148-152` | `SELECT * FROM drf_rows` | SQLite query | ✓ Real DB query |
| 6. Scored by token overlap | `_score_drf_rows` (line 71) | Overlap score | duty tokens ∩ row tokens | ✓ Real computation |
| 7. User selects checkboxes | `drf_candidates.html:39-41` | JS builds row_ids | `<input name="row_ids">` | ✓ Real client JS |
| 8. Confirm posts | `drf_candidates.html:9` | `hx-post="/confirm"` | router → service | ✓ Real HTMX POST |
| 9. Service persists | `drf_service.py:245-246` | `wd.model_copy(update=...)` | `save_work_description` | ✓ Real DB write |
| 10. DOCX export | `export_service._build_context` | `drf_linkages` | docxtpl render | ✓ Real template |
| 11. Section 6 gate | `build_docx_template.py:176` | `{%p if drf_linkages\|length > 0 %}` | Template | ✓ Real gate |

**End-to-end smoke test result:** Created a WD with DRF linkages, ran `generate_export`, got 37,488 bytes DOCX, `get_undeclared_template_variables()` returns `[]` (all template variables satisfied).

---

## Code Review Fix Verification

All 3 issues from `09-REVIEW.md` are addressed in the current code:

| ID | Severity | Issue | Status | Evidence |
|----|----------|-------|--------|----------|
| CR-01 | CRITICAL | CSS selector broken in drf_candidates.html confirm form | ✓ FIXED | Line 20: `class="drf-candidate-checkbox"` added; line 39: `document.querySelectorAll('.drf-candidate-checkbox:checked')` (class-based, not name-based) |
| WR-01 | WARNING | `class="muted"` had no global CSS rule | ✓ FIXED | `app/static/css/main.css` has global `.muted { color: var(--color-text-muted, #555555); font-size: 0.875rem; }` rule |
| WR-03 | WARNING | Empty `row_ids` wipes existing linkages (silent data loss) | ✓ FIXED | `app/services/drf_service.py:204-214`: `if not row_ids: return existing` (no-op, not a wipe) |

Commit that addressed all 3: `9937d99` (per the user's note about the code review fix).

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| **DRF-01** | 09-01 → 09-04 | For DND positions, system surfaces DRF program linkages connecting position duties to departmental expected results | ✓ SATISFIED | Inline panel on /wizard/export (step_export.html:57-110); keyword-based candidate matching (drf_service._score_drf_rows); confirmed linkages stored on WD (drf_linkages list); DOCX Section 6 with table (build_docx_template.py:177-196); manifest emission (export_service.py:140-149) |

DRF-01 is fully covered end-to-end:
1. ✓ WD model carries the field (`is_dnd_position`, `drf_linkages`)
2. ✓ Data pipeline (scripts/ingest_drf.py populates drf_rows from CSV)
3. ✓ Service layer (keyword matching + confirmation)
4. ✓ API layer (2 routes: GET candidates + POST confirm)
5. ✓ UI layer (inline panel on /wizard/export with 2 states)
6. ✓ Export layer (DOCX Section 6 + version manifest entry)

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | — |

Scanned all Phase 9 files for TODO/FIXME/XXX/HACK/PLACEHOLDER — zero matches. No empty implementations, no console.log stubs, no hardcoded empty props at the call site.

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite | `python -m pytest --no-header -q` | 188 passed, 9 skipped, 0 failures | ✓ PASS |
| DRF service imports | `python -c "from app.services.drf_service import get_drf_candidates, confirm_drf_linkages"` | `imports OK` | ✓ PASS |
| DRF router routes | `python -c "from app.api.drf_integration import router; print(...)"` | `GET /api/drf-links/{wd_id}` + `POST /confirm` (2 routes) | ✓ PASS |
| DRF-01 contract: no `/wizard/drf` route | `grep '/wizard/drf' app/main.py` | No matches | ✓ PASS |
| Default `is_dnd_position=True` | `grep 'is_dnd_position = True' app/main.py app/services/wd_store.py` | Match in main.py (line 279 comment) | ✓ PASS |
| `is_dnd_position=True` set on WD creation | `grep 'is_dnd_position' app/api/noc_mapping.py` | Line 79: `is_dnd_position=True` | ✓ PASS |
| DOCX Section 6 gate | `grep 'drf_linkages\|length' scripts/build_docx_template.py` | Line 176: `doc.add_paragraph("{%p if drf_linkages\|length > 0 %}")` | ✓ PASS |
| `drf-candidate-checkbox` class | `grep 'class="drf-candidate-checkbox"' templates/partials/drf_candidates.html` | Match (line 20) | ✓ PASS |
| `.drf-linkages-table` in confirmed partial | `grep 'drf-linkages-table' templates/partials/drf_confirmed.html` | Match (line 7) | ✓ PASS |
| `#drf-linkages-panel` swap target | `grep 'drf-linkages-panel' templates/wizard/step_export.html` | Match (line 61) | ✓ PASS |
| CSS Layer 14 | `grep 'Layer 14' app/static/css/main.css` | Match in header comment + section header | ✓ PASS |
| End-to-end DOCX render | `python ... generate_export(...)` | 37,488 bytes, 0 undeclared vars | ✓ PASS |
| Build script self-verify | `python scripts/build_docx_template.py` | `DRF contract: ['drf_linkages'] declared ✓` | ✓ PASS |

---

## Human Verification Required

While all automated checks pass, the following behaviors are best validated by a human running the app in a browser:

1. **Visual layout** — Open `/wizard/export?wd_id=...` and confirm the DRF panel renders below the Download DOCX button with the correct "Find DRF Linkages" / "Refine Linkages" button states.

2. **HTMX swap behavior** — Click "Find DRF Linkages" with a WD that has duty text. The spinner should show briefly, then the checkbox list of top-5 candidates should appear.

3. **End-to-end flow** — Select checkboxes, click "Confirm Selected Linkages". The page should swap to the confirmed table; subsequent visits to /wizard/export should show the table directly.

4. **DOCX export** — Download the DOCX export. The file should contain Section 6 with the 3-column table of confirmed linkages and the version manifest should include DRF source rows.

---

## Gaps Summary

No gaps. The phase goal is fully achieved.

The 8 skipping tests in `tests/test_drf.py` are intentionally skipping because the revised Plan 09-04 design (inline panel instead of separate route) changed which behaviors are appropriate to test at the router/wizard level. The 8 active tests cover:
- Service-layer contract (4 + 2 tests for get/confirm)
- Wizard-layer contract (2 tests for the inline panel HTML in both states)

The 9-skip total project-wide (vs. 8 DRF skips) is unchanged from before this phase — all 8 DRF skips are documented in the test file's module docstring.

---

## Deviations From Plan

The user's note flagged one important deviation: **Plan 09-04 was redirected mid-execution**. The original plan used a separate `/wizard/drf` URL with a DND toggle. The user redirected to an inline panel inside `/wizard/export`, with `is_dnd_position=True` defaulted on every WD (no toggle). The original 09-04 commits (`8ffa967` + `c130b6a`) were reverted with `git revert`, and the new design was committed on top. This deviation is documented in the SUMMARY and STATE files and the implementation matches the redirected design.

The phase goal is still achieved with the revised design (inline panel meets the same end-user requirement of "show an inline panel that suggests DRF program linkages" — the inline location on /wizard/export is arguably better UX than a separate /wizard/drf step for a DND-only prototype).

---

_Verified: 2026-06-03T15:00:00Z_
_Verifier: the agent (gsd-verifier)_
