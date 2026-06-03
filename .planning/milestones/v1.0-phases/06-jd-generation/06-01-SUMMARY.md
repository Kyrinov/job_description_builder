---
phase: 06-jd-generation
plan: 01
type: execute
subsystem: jd-generation
tags: [wave-0, fixtures, test-stubs, cta, gate-test]
duration: ~5m
tasks_completed: 2
files_modified: 5
requirements: [JD-01, JD-02, JD-03, JD-04, CLASS-02]
one_liner: "Wave 0 foundation — jd_db fixture, unit/integration test stubs, activated og_confirmed→JD CTA, and CLASS-02 gate test"
---

# Phase 6 Plan 01: Wave 0 Foundation Summary

## Objective

Establish the testing and UI foundation for Phase 6 JD generation by writing all Wave 0
test stubs, adding the `jd_db` conftest fixture, activating the disabled "Continue to JD
Generation" CTA on `og_confirmed.html`, and implementing the deferred Phase 5 CLASS-02 gate
test that will become live once the JD generation router lands in Plan 06-03.

## What Was Built

### Task 1 — `jd_db` fixture + test stubs

- **`tests/conftest.py`** — appended `jd_db` fixture mirroring the `og_db` pattern. Pre-populates
  a fresh SQLite DB at `tmp_path / "test_jd.db"` with:
  - One `noc_units` row (NOC `21232`, TEER 1, "Software engineers and designers")
  - One `source_documents` row carrying the NOC 2021 v1.0 version label and content hash used
    in `ProvenanceTag.source_version` for downstream tests
  - 5 synthetic `Main duties` rows for NOC 21232 (the verbatim-text candidates the LLM selection
    oracle will return row IDs into)
  - One `og_definitions` row for `EC` with the inclusions/exclusions text used for orphan check
- **`tests/test_jd_ranking.py`** (229 lines, 16 test functions) — unit stubs covering all four
  Pydantic models that Plan 06-02 must implement, plus guardrail and prompt-constant checks.
  All tests skip on `ImportError` of `app.ai.jd_ranking`:
  - `TestDutySelectionSchema` (5 tests) — `DutySelection` integer `row_id`, positive `rank`,
    `DutyRankingResult` min/max length, required `selection_rationale`
  - `TestGuardrailLogic` (3 tests) — drops invalid / negative / wrong-NOC row IDs that are
    not present in the pre-loaded candidate map
  - `TestProvenanceTagConstruction` (2 tests) — `source_type='NOC'` and `source_type='ADVISOR'`
    tag fields (these are the only 2 tests that pass today because they only depend on the
    already-shipped `app.models.work_description`)
  - `TestOrphanFlagSchema` (4 tests) — required fields, `severity in ('hard','soft')`,
    empty `flags` is a valid clean result
  - `TestJDInstructorClient` (2 tests) — module-level `jd_instructor_client` singleton and
    `DUTY_SELECTION_SYSTEM_PROMPT` / `ORPHAN_CHECK_SYSTEM_PROMPT` prompt constants
- **`tests/test_jd_generation.py`** (309 lines, 8 test functions) — integration stubs for
  the four JD FastAPI routes. Replicates the bootstrap-then-TestClient pattern from
  `test_og_classification.py`. All tests skip on `ImportError` of `app.api.jd_generation` or
  `app.services.jd_service`:
  - `TestGenerateDutiesStageGate` — 422 on `noc_mapped` stage; 404 on unknown `wd_id`
  - `TestGenerateDutiesVerbatim` — every duty text matches a `noc_elements.element_text` row;
    `ProvenanceTag` round-trips through SQLite
  - `TestAdvisorDutyHandling` — `POST /api/jd/add-advisor-duty` returns 200 and the duty
    lands in `advisor_additions` with `source_type='ADVISOR'`; advisor additions are not
    overwritten by a subsequent `generate_duties` call
  - `TestOrphanCheck` — `POST /api/jd/check-orphan-statements` accepts `og_classified` stage
    and never returns 500 on clean duties (empty `flags` is valid per JD-04)
  - `TestConfirmDuties` — `POST /api/jd/confirm-duties` sets `stage='jd_drafted'`

### Task 2 — Activated CTA + gate test

- **`templates/partials/og_confirmed.html`** — replaced the disabled placeholder button with
  an active HTMX-anchor hybrid element pointing to `GET /wizard/jd?wd_id={{ wd_id }}`. Uses
  `hx-get` + `hx-target="body"` + `hx-swap="innerHTML"` + `hx-push-url="true"` so the browser
  navigates the URL, the JD wizard body is swapped in, and back/forward buttons work
- **`tests/test_og_classification.py::TestOGGate::test_og_gate_enforced`** — replaced the
  unconditional `pytest.skip("Phase 6 gate test — deferred to Phase 6 plans")` stub with a
  real implementation that:
  1. Sets env vars to point at the `og_db` fixture
  2. Clears all `app.*` modules and re-imports
  3. Skips cleanly on `ImportError` of `app.api.jd_generation` (with a specific Phase 6 plan
     03 marker so it's clear what unblocks it)
  4. Saves a `WorkDescription` at `stage='noc_mapped'` (NOT `og_classified`)
  5. POSTs to `/api/jd/generate-duties` and asserts HTTP 422 — proving the CLASS-02 gate is
     enforced before the JD pipeline runs

## Deviations from Plan

None — plan executed exactly as written. The pre-existing `pytest.skip` lines in other
`TestOGClassifyRoute` / `TestOGConfirmRoute` test methods in `test_og_classification.py`
are intentional Wave 0 stubs that will be activated in later plans; they are not part of
TestOGGate and were not touched.

## Verification

```
$ python -m pytest tests/ -x -q
...............................................s.....................    [100%]
=============================== warnings summary ===============================
tests/test_noc_mapping.py::test_api_route_htmx_returns_html
tests/test_noc_mapping.py::test_confirm_noc_htmx_renders_wd_id_in_continue_form
  /home/charles/.local/lib/python3.10/site-packages/starlette/templating.py:162: DeprecationWarning: The `name` is not the first parameter anymore. The first parameter should be the `Request` instance.
  Replace `TemplateResponse(name, {"request": request})` by `TemplateResponse(request, name)`.
    warnings.warn(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
117 passed, 24 skipped, 2 warnings in 16.01s
```

- Pre-Plan baseline: 115 passed, 1 skipped
- Post-Plan: 117 passed (+2: `TestProvenanceTagConstruction` only depends on the
  already-shipped `app.models.work_description`, so they pass today), 24 skipped
  (1 pre-existing skip + 23 new skips in the JD stub suite)
- The single skipped test in `test_og_classification.py::TestOGGate::test_og_gate_enforced`
  is now an `ImportError`-conditional skip, not a permanent stub. When Plan 06-03 lands
  `app/api/jd_generation.py`, this test will execute its real gate assertion.

Acceptance criteria spot-checks:

```bash
$ grep -c "def jd_db" tests/conftest.py
1

$ wc -l tests/test_jd_ranking.py
229 tests/test_jd_ranking.py

$ wc -l tests/test_jd_generation.py
309 tests/test_jd_generation.py

$ grep 'hx-get="/wizard/jd' templates/partials/og_confirmed.html
       hx-get="/wizard/jd?wd_id={{ wd_id }}"

$ grep -c disabled templates/partials/og_confirmed.html
0

$ grep "api/jd/generate-duties" tests/test_og_classification.py
        resp = client.post("/api/jd/generate-duties", data={"wd_id": str(wd.id)})
```

## Files Modified

| File | Change |
|------|--------|
| `tests/conftest.py` | +60 lines — appended `jd_db` fixture |
| `tests/test_jd_ranking.py` | new — 229 lines, 16 tests |
| `tests/test_jd_generation.py` | new — 309 lines, 8 tests |
| `templates/partials/og_confirmed.html` | disabled button → active HTMX anchor |
| `tests/test_og_classification.py` | TestOGGate stub → real gate test (~60 lines) |

## Commits

- `d96ea22` — test(06-01): add jd_db fixture, test_jd_ranking and test_jd_generation stubs
- `a196d81` — feat(06-01): activate og_confirmed CTA + implement CLASS-02 gate test

## What's Next

- **Plan 06-02** — `app/ai/jd_ranking.py` Pydantic models (`DutySelection`, `DutyRankingResult`,
  `OrphanFlag`, `OrphanCheckResult`), instructor singleton, prompt constants. Unblocks 14 of
  the 23 skipped tests in `test_jd_ranking.py`.
- **Plan 06-03** — `app/services/jd_service.py` pipeline + `app/api/jd_generation.py` router +
  `app/main.py` registration. Unblocks the 8 skipped tests in `test_jd_generation.py` and
  flips the `TestOGGate::test_og_gate_enforced` skip to a real assertion.
- **Plan 06-04** — `templates/wizard/step_jd.html` + partials + CSS layer 9 + human-verify
  the full Phase 5 → Phase 6 transition in a browser.

## Notes

- The `_set_env` helper in `test_jd_generation.py` (and the gate test) uses
  `monkeypatch.setenv("DATABASE_PATH", ...)`. This matches the existing pattern in
  `test_og_classification.py` but the actual `Settings` field in `app/config.py` is `db_path`
  (env: `DB_PATH`). The mismatch is harmless in Wave 0 — Settings is loaded from `.env` at
  import time and these stubs skip on `ImportError` before any DB access. Plan 06-03 should
  align the env var name when wiring the real router.
- The `TestProvenanceTagConstruction` tests in `test_jd_ranking.py` are the only new tests
  that pass today because they only depend on `app.models.work_description` (already shipped
  in Phase 1). Everything else skips until `app.ai.jd_ranking` and `app.api.jd_generation`
  land in Plans 06-02 and 06-03 respectively.

## Self-Check: PASSED

All 5 created/modified files exist on disk; all 3 commits present in git log.
