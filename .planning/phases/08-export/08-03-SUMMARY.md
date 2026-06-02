---
phase: 08-export
plan: 03
subsystem: api
tags: [fastapi, router, docx, pdf-501, htmx, htms-dual-path, testclient, valueerror-mapping, threat-model]

# Dependency graph
requires:
  - phase: 08-export
    provides: "export_service.generate_export (async DOCX render) + export_db fixture + make_exported_wd helper + 6 service contract tests (08-01 + 08-02)"
provides:
  - "GET /export/{wd_id}/docx — HTMX dual-path route: non-HTMX streams DOCX with Content-Disposition: attachment; HX-Request returns templates/partials/export_result.html"
  - "GET /export/{wd_id}/pdf — 501 Not Implemented stub with D-08 deferred-PDF message (WeasyPrint ARM64 deferred)"
  - "ValueError → 404 (not found) / 422 (blocked / wrong stage) error mapping"
  - "export.router mounted in app.main + /wizard/export route with jinja2.TemplateNotFound fallback (D-09 placeholder until 08-04 ships the real template)"
  - "4 router-level tests in tests/test_export.py: 501 PDF, 404 unknown wd, 422 blocked, 200 streams file with attachment"
affects:
  - 08-04 (wizard step_export.html + partials/export_result.html invoked by /wizard/export and the HTMX branch of /docx)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Direct analog of app/api/jes_scoring.py — same imports, same templates_dir resolution, same ValueError → HTTPException mapping (line-for-line mirror with one route added)"
    - "HTMX dual-path pattern: `if request.headers.get(\"HX-Request\"):` chooses between TemplateResponse (HX) and raw Response with Content-Disposition: attachment (non-HX)"
    - "T-08-12 mitigation: filename is the server-set constant `work_description.docx` from the service result, never derived from user input — no header injection surface"
    - "D-08 501 short-circuit: /pdf returns immediately with no WeasyPrint render path reachable, eliminating the ARM64 render risk (T-08-14)"
    - "D-09 placeholder pattern: /wizard/export uses jinja2.TemplateNotFound fallback to render a minimal HTML body until 08-04 ships templates/wizard/step_export.html"

key-files:
  created:
    - app/api/export.py
  modified:
    - app/main.py
    - tests/test_export.py

key-decisions:
  - "Replicated jes_scoring.py structure line-for-line (router skeleton, templates_dir os.path.join three levels up, ValueError → 404/422 mapping). Diverged only where the route body required it: added the HX-Request branch and the binary Response branch."
  - "Wrapped the ValueError → HTTPException mapping in a single `if \"not found\" in msg: 404 else 422` block, identical to jes_scoring.py. The service raises the human-readable domain message, the route just translates — no message rewriting in the API layer."
  - "Made test_pdf_route_returns_501 seed a complete=True WD even though the route short-circuits. This mirrors the plan's action and keeps the test self-documenting (the WD is export-ready; the /pdf endpoint refuses anyway)."
  - "Used the per-test rebootstrap pattern (_set_env + _clear_app_modules + from app.main import app + TestClient(app)) in all 4 router tests. The autouse _bootstrap_app_modules fixture is a one-shot and would otherwise bind settings.db_path to the FIRST service test's export_db — rebootstrap ensures each router test sees its own DB."
  - "Used `if \"not found\" in msg` substring test (not exact-match) for the 404 mapping — same pattern as jes_scoring.py and tolerates the service's full domain message (\"WorkDescription <id> not found\") which may include the wd_id."

patterns-established:
  - "Router test pattern: per-test rebootstrap (env set + module clear + app import + TestClient) is the standard for any test that exercises a real DB path. Documented in the section header of the new tests in tests/test_export.py."
  - "Binary-content assertion: `response.headers[\"content-type\"].startswith(\"application/vnd.openxmlformats...\")` + `len(response.content) > 0` + `\"attachment\" in response.headers.get(\"content-disposition\", \"\")` — three checks cover the file identity, payload, and download semantics."

requirements-completed: [EXP-01]

# Metrics
duration: 5min
completed: 2026-06-02
---

# Phase 8 Plan 03: Export Routes Summary

**FastAPI router for /export/{wd_id}/docx (HTMX dual-path) and /export/{wd_id}/pdf (501 stub), mounted in app/main.py with a /wizard/export placeholder route — D-08 PDF deferral, D-09 wizard placeholder, and 4 router-level tests covering 200/404/422/501 paths**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-02T21:35:00Z
- **Completed:** 2026-06-02T21:39:54Z
- **Tasks:** 3 (Tasks 1+2 from prior executor, Task 3 completed in this session)
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- **`app/api/export.py`** — Router exposing two routes:
  - `GET /export/{wd_id}/docx` — calls `await generate_export(wd_id, db_path=settings.db_path)`, maps `ValueError("not found")` → 404 and any other `ValueError` → 422. On success, branches on `request.headers.get("HX-Request")`:
    - HTMX: renders `partials/export_result.html` with `{wd_id, export_hash, filename}`
    - non-HTMX: returns `Response(content=file_bytes, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": f'attachment; filename="{filename}"'})`
  - `GET /export/{wd_id}/pdf` — short-circuits to `HTTPException(status_code=501, detail="PDF export is not yet available — download DOCX and convert locally.")` per D-08. No WeasyPrint render path reachable, eliminating T-08-14 ARM64 risk.
- **`app/main.py`** — Added `from app.api import export` to the router import block, `app.include_router(export.router)` after the existing `jes_scoring.router` mount, and a new `@app.get("/wizard/export", response_class=HTMLResponse) async def wizard_export(...)` route that tries `templates/wizard/step_export.html` and falls back to a minimal HTML body on `jinja2.TemplateNotFound` (D-09 placeholder; Plan 08-04 ships the real template).
- **`tests/test_export.py`** — Appended 4 router-level tests using `TestClient(app)` with the per-test rebootstrap pattern from `test_jes_scoring.py`. All 10 tests in the file pass (6 service + 4 router); full suite: 159 passed, 1 pre-existing skip, 0 regressions.

## Task Commits

Each task was committed atomically (Tasks 1+2 from prior executor, Task 3 this session):

1. **Task 1: Create app/api/export.py with /docx and /pdf routes** - `58011f5` (feat)
2. **Task 2: Mount export router and add /wizard/export route in app/main.py** - `c9a98a8` (feat)
3. **Task 3: Add router-level tests (501 PDF, 404, 422 blocked) to test_export.py** - `6b53702` (test)

**Plan metadata:** committed alongside Task 3 in this session (docs: 08-03-SUMMARY.md + STATE.md + ROADMAP.md updates)

## Files Created/Modified

- `app/api/export.py` (created, 77 lines) — FastAPI router for the two /export routes.
  Module docstring documents D-08 (PDF deferral) and the direct analog relationship
  to `app/api/jes_scoring.py`. Imports mirror the interface block from the PLAN
  (`Response` from `fastapi.responses`, `Jinja2Templates` for the HTMX branch, the
  service via `from app.services.export_service import generate_export`).
- `app/main.py` (modified) — Three additions, all surgical:
  1. `from app.api import export` added to the router import block (line 24)
  2. `app.include_router(export.router)` added after the `jes_scoring.router` mount (line 111)
  3. `wizard_export` route added after `wizard_jes` (lines 186-206) with the
     `jinja2.TemplateNotFound` fallback pattern
- `tests/test_export.py` (modified, +94/-4 lines) — Replaced the stale "Deferrals"
  comment with a new "Router contract (Plan 08-03)" section containing 4 tests.
  Each test does per-test rebootstrap: `_set_env(monkeypatch, str(export_db), tmp_path)`
  + `_clear_app_modules()` + `from app.main import app` (in try/except ImportError
  for graceful skip) + `TestClient(app)`.

## Decisions Made

- **Line-for-line analog of jes_scoring.py.** The router skeleton, imports block,
  templates_dir resolution, and ValueError → HTTPException mapping all mirror
  `app/api/jes_scoring.py`. The only divergences are route-body content: the HX-Request
  branch, the binary Response branch, and the 501 stub. This keeps the codebase
  consistent and means anyone who understands one router understands the other.
- **T-08-12 (filename injection) mitigated by design.** The Content-Disposition
  `filename` comes from `result["filename"]` which the service produces as the
  server-set constant `"work_description.docx"` — never derived from user input.
  The 4th test asserts `"attachment" in response.headers.get("content-disposition", "")`
  to lock this contract in.
- **D-08 message exact-match in the 501 test.** The assertion is
  `"PDF export is not yet available" in response.text` — substring match, not full
  message equality, so future copy edits to the detail don't break the test, but
  the leading "PDF export is not yet available" phrase is locked.
- **D-01 substring check for the 422 test.** The assertion is
  `"Communication" in response.text` — the route passes the service's full
  ValueError message through as the 422 detail, which names the failed factor
  (Communication is the sentinel in the `complete=False` WD). Substring match
  tolerates the rest of the message changing.
- **404 test seeds nothing.** The test hits `/export/nonexistent-id/docx` against
  the per-test export_db (which is empty). The service's `load_work_description`
  raises `ValueError("...not found...")` which the route maps to 404. This
  exercises both the not-found branch of the service AND the 404 branch of the
  route mapping in a single test.
- **200 docx test does NOT use HX-Request header.** This is the file-download
  path. A separate (deferred-to-08-04) test would add an `HX-Request: true`
  header to exercise the partial-render path; that test depends on the
  `templates/partials/export_result.html` template that 08-04 will commit.
- **Per-test rebootstrap over a session-scoped fixture.** The autouse
  `_bootstrap_app_modules` fixture is intentionally a one-shot (to avoid the
  cost of re-importing the entire app stack on every test). The router tests
  each pay the rebootstrap cost individually because they need `settings.db_path`
  bound to their own per-test `export_db`. Documented in the section header of
  the new tests so the next agent understands the constraint.

## Deviations from Plan

None — plan executed exactly as written. The 4 router tests follow the
per-test rebootstrap pattern from the prompt's "important_constraints"
verbatim: `_set_env(monkeypatch, str(export_db), tmp_path)` + `_clear_app_modules()`
+ `from app.main import app` (wrapped in try/except ImportError → pytest.skip)
+ `TestClient(app)`. The D-08 message check, the D-01 factor name check, and
the 200 docx assertions all match the plan's action block.

## Issues Encountered

None — the 4 router tests passed on first run after being appended. The
per-test rebootstrap pattern works because `_clear_app_modules()` removes
`app.main` from `sys.modules` and the subsequent `from app.main import app`
re-reads the just-set `DB_PATH` env var, binding `settings.db_path` to the
per-test `export_db` (a fresh `tmp_path / "test_export.db"` per test).

## Next Phase Readiness

- Plan 08-04 (wizard step_export.html, export_result.html partial, CSS layer 11,
  human verify) can now proceed:
  - Templates: `templates/wizard/step_export.html` (consumed by
    `app.main.wizard_export` — the TemplateNotFound fallback will be replaced)
    and `templates/partials/export_result.html` (consumed by
    `app/api/export.py:export_docx` when `HX-Request` is set)
  - Route hooks: `/wizard/export?wd_id=<id>` renders the step, the step's
    HTMX form posts to `/export/{wd_id}/docx` with `HX-Request: true`
  - The D-09 placeholder HTML body in `wizard_export` becomes dead code once
    08-04 ships the real template; the `try/except jinja2.TemplateNotFound`
    stays as a safety net.
- 10 tests in `test_export.py` pass; full suite at 159 passed + 1 pre-existing
  skip, 0 regressions.
- No new blockers.

## Self-Check: PASSED

All claimed files and commits verified:
- `app/api/export.py` — created, 77 lines, contains `async def export_docx`, `async def export_pdf`, `status_code=501`, `PDF export is not yet available — download DOCX and convert locally.`, `from app.services.export_service import generate_export`, `if "not found" in msg`
- `app/main.py` — contains `from app.api import export`, `app.include_router(export.router)`, `@app.get("/wizard/export"`, `wizard/step_export.html`
- `tests/test_export.py` — contains `def test_pdf_route_returns_501`, `status_code == 501`, `TestClient`, all 10 tests pass
- `58011f5` — feat(08-03): add /export/{wd_id}/docx and /pdf routes
- `c9a98a8` — feat(08-03): mount export router and add /wizard/export route
- `6b53702` — test(08-03): add router-level tests for /export routes
- Full suite: 159 passed, 1 skipped, 0 regressions

---
*Phase: 08-export*
*Completed: 2026-06-02*
