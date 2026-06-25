---
phase: 20-export
plan: 01
subsystem: export
tags: [docxtpl, weasyprint, jinja2, pytest, docx-templates]

# Dependency graph
requires: []
provides:
  - 7 RED test stubs defining the export endpoint contract (EXP-01/02/03, API-08/09)
  - WeasyPrint 69.0 install in venv + requirement pinned
  - wd_template.docx committed binary with 15 undeclared variables matching contract
  - poster_template.docx committed binary with 8 undeclared variables matching contract
  - Reproducible build scripts (build_wd_template.py, build_poster_template.py) with self-verify
affects: [phase-20-plan-02, phase-20-plan-03, frontend-app-exportAs, frontend-conversation-export-buttons]

# Tech tracking
tech-stack:
  added:
    - weasyprint==69.0 (PDF rendering; ARM64 smoke test passes)
  patterns:
    - docxtpl self-verify via get_undeclared_template_variables() at build time
    - paragraph-level {%p for %} and table-row {%tr for %} loops in committed .docx templates
    - {%p if X|length > 0 %} gate for optional sections (amendments appendix)
    - reproducible build scripts run from repo root, output to app/templates/*.docx

key-files:
  created:
    - v2/backend/tests/test_export.py
    - v2/backend/scripts/build_wd_template.py
    - v2/backend/scripts/build_poster_template.py
    - v2/backend/app/templates/wd_template.docx
    - v2/backend/app/templates/poster_template.docx
  modified:
    - v2/backend/requirements.txt

key-decisions:
  - "Appended weasyprint==69.0 to end of requirements.txt — plan said 'alphabetical order' but the existing list is not strictly alphabetical; append is unambiguous"
  - "Used appended 'Appendix:' heading for amendments (not renumbering Sections 1-6) to preserve citation stability per 20-RESEARCH.md open question #1"
  - "Bilingual title placeholder in poster is {{ bilingual_title_fr }} (empty string by default) — French translation is out of scope per REQUIREMENTS.md"
  - "Build scripts output to repo-root-relative paths so the same .docx is reproducible regardless of CWD when called correctly"
  - "Both build scripts use _set_cell_text helper copied verbatim from v1.0 (avoids drift in cell-clearing logic)"

requirements-completed: [EXP-01-stub, EXP-02-stub, EXP-03-stub, API-08-stub, API-09-stub]

# Metrics
duration: 8min
completed: 2026-06-09
---

# Phase 20 Plan 01: Export Foundation Summary

**Wave 0 foundation for Phase 20: 7 RED test stubs, WeasyPrint 69.0 install, and committed docxtpl WD + poster template binaries with reproducible build scripts.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-09T18:02:48Z
- **Completed:** 2026-06-09T18:10:35Z
- **Tasks:** 2
- **Files modified:** 5 (1 modified, 4 created)

## Accomplishments

- Established the export test contract with 7 RED stubs (`@pytest.mark.skip` — unblock in Plan 02) covering EXP-01 (DOCX bytes), EXP-01 (manifest rendered), EXP-01/AMEND-02 (amendments appendix), EXP-02 (poster bytes), EXP-03 (PDF 501 gate), and 404 guards for both API-08 and API-09 endpoints
- Installed WeasyPrint 69.0 in the venv — ARM64 smoke test (`weasyprint.HTML(string='<p>x</p>').write_pdf()`) passes; pinned in `requirements.txt`
- Built and committed `wd_template.docx` (37,616 bytes) with 6 sections + amendments appendix — 15 undeclared Jinja2 variables match the contract asserted by `build_wd_template.py`
- Built and committed `poster_template.docx` (36,968 bytes) with bilingual header, OG/level, branch, duties loop, qualifications, and How to Apply placeholder — 8 undeclared variables match the contract asserted by `build_poster_template.py`
- Both build scripts self-verify at build time via `get_undeclared_template_variables()` and raise `AssertionError` on missing required variables — contract violations caught at build, not at first export
- Sanity-rendered both templates with realistic sample context dicts (duties loop, JES table loop, manifest loop, amendments loop all expanded) — render OK
- Backend suite maintained GREEN: 73 passed, 7 skipped (the 7 new stubs), 0 failed — no regression from Phase 19 baseline

## Task Commits

Each task was committed atomically:

1. **Task 1: Install WeasyPrint + RED stubs** - `377f768` (test)
2. **Task 2: Build scripts + .docx binaries** - `634aaa9` (feat)

## Files Created/Modified

- `v2/backend/requirements.txt` — added `weasyprint==69.0` (was 10 lines, now 11)
- `v2/backend/tests/test_export.py` — 7 skipped RED stubs with `_create_wd` + `_create_wd_with_jes_scores` helpers (127 lines)
- `v2/backend/scripts/build_wd_template.py` — TBS Work Description template builder (227 lines)
- `v2/backend/scripts/build_poster_template.py` — Bilingual job poster template builder (130 lines)
- `v2/backend/app/templates/wd_template.docx` — committed binary artifact (37,616 bytes)
- `v2/backend/app/templates/poster_template.docx` — committed binary artifact (36,968 bytes)

## Decisions Made

- **weasyprint position in requirements.txt:** Plan body said "alphabetical order" but also "after the last existing line" — these are contradictory since the existing list is not strictly alphabetical (it's web-framework → pydantic → test → db → ai). Appended to end, which is unambiguous and matches the second instruction.
- **Amendments appendix heading:** Used "Appendix: Manager Amendments for Review" (unnumbered) after Section 6 (Manifest) rather than renumbering Sections 1-6. This preserves citation stability for downstream reviewers and follows the v1.0 pattern (DRF-01 unnumbered appendix).
- **Bilingual poster handling:** `bilingual_title_fr` is a placeholder variable (empty string by default) — actual French translation is flagged-only per REQUIREMENTS.md. Bilingual header text is hardcoded; only the position title's French translation is a variable.
- **Build script paths:** Output paths are repo-root-relative (e.g., `v2/backend/app/templates/wd_template.docx`). Scripts are invoked from the repo root with `python v2/backend/scripts/build_<name>.py` — matches the run command in the plan and ensures the committed .docx is in the expected location.
- **Cell helper copy verbatim:** `_set_cell_text` from v1.0 `scripts/build_docx_template.py` was copied verbatim into both v2 build scripts rather than refactored to a shared helper. This avoids creating a new module dependency for a 13-line function and matches the v1.0 pattern.
- **JES table column count:** WD template's JES table has 3 columns (Factor/Degree/Points); v1.0 had 4 (with Source column). Since v2.0 doesn't carry `f.source_id`/`f.source_version` on JES factors (per RESEARCH.md mapping table), the 4th column was dropped. The `factor.source_id` is not in the v2 context dict.

## Deviations from Plan

None. Plan executed exactly as specified.

**Note on plan's grep acceptance criteria:**

The plan's acceptance criteria says:
> `grep -c "pytest.mark.skip" v2/backend/tests/test_export.py` outputs 7

The actual count is 8 — 7 are the `@pytest.mark.skip` decorators, and 1 is the literal text in the docstring (line 10: "Remove @pytest.mark.skip when the router is live."). This is a minor discrepancy in the plan's expected grep count, not a code issue. The 7 actual RED stubs are present and correct (verified with `grep -c "^@pytest.mark.skip"` → 7 and `grep -c "^async def test_export"` → 7). The test_export.py content matches the plan's `<action>` block verbatim, including the docstring.

## Issues Encountered

None. Both build scripts ran cleanly on the first attempt, the smoke test for WeasyPrint passed (system libs for libpango/libcairo are present on this ARM64 host), and the backend test suite stayed GREEN throughout.

## Next Phase Readiness

- **Wave 2 (Plan 20-02) is unblocked:** Can now build `app/services/export_service.py` + `app/api/export.py` against the test contract in `test_export.py`, the variable contract in both build scripts, and the committed .docx binaries.
- **Frontend (Plan 20-03) is unblocked:** The blob-download pattern in conversation.jsx export buttons can be wired against the new POST `/api/wd/{id}/export/{docx,poster,pdf}` endpoints.
- **No blockers for Wave 2** — the only dependency is the export router module which Wave 2 owns.
- **Note for Wave 2:** When unskipping the 7 RED stubs, remove the `@pytest.mark.skip` decorator at the top of each test (keep the `pytestmark = pytest.mark.asyncio` at module level). The `_create_wd_with_jes_scores` helper patches the WD with `confirmed_og`, `og_level`, `jes_total_points`, `jes_scores`, and `duties` — these are the minimum required for `require_og_confirmed(wd)` and the export render to succeed.

## Self-Check: PASSED

**Created files (5/5 present):**
- v2/backend/tests/test_export.py ✓
- v2/backend/scripts/build_wd_template.py ✓
- v2/backend/scripts/build_poster_template.py ✓
- v2/backend/app/templates/wd_template.docx ✓ (37,616 bytes)
- v2/backend/app/templates/poster_template.docx ✓ (36,968 bytes)

**Modified files (1/1 present):**
- v2/backend/requirements.txt ✓ (weasyprint==69.0 added)

**Commits (2/2 present):**
- 377f768 — test(20-01): add export RED stubs + WeasyPrint 69.0 to requirements ✓
- 634aaa9 — feat(20-01): build wd/poster docx template binaries + reproducible build scripts ✓

**Acceptance criteria (7/7 met):**
1. `grep "weasyprint==69.0" v2/backend/requirements.txt` → 1 match ✓
2. `python -c "import weasyprint; print('ok')"` → ok (version 69.0) ✓
3. `grep -c "pytest.mark.skip" v2/backend/tests/test_export.py` → 8 (7 decorators + 1 docstring mention; the 7 actual RED stubs are present) ✓
4. 7 test_export_* function names present ✓
5. Backend suite: 73 passed, 7 skipped, 0 failed ✓
6. Both .docx binaries > 4000 bytes (37,616 and 36,968) ✓
7. `get_undeclared_template_variables` in each build script → 1 match ✓

---

*Phase: 20-export*
*Completed: 2026-06-09*
