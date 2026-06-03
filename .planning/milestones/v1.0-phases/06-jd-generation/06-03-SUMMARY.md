# Plan 06-03 SUMMARY — JD Service + Router + Main.py

## Result

All 2 tasks committed (`44ebe2f` — feat), CLASS-02 gate test passes, full suite green.

## Tasks Completed

### Task 1 — `app/services/jd_service.py` (323 lines)

Four async pipeline functions implemented exactly per plan spec:

| Function | Behavior | Stage gate | Guardrail |
|----------|----------|------------|-----------|
| `generate_duties(wd_id, db_path)` | 3-step: load candidates → LLM DutyRankingResult → DB reconstruction | `og_classified` | `candidate_map` filter drops LLM row_ids not in pre-loaded set |
| `check_orphan_statements(wd_id, db_path)` | LLM orphan check + fabrication guardrail | `og_classified` OR `jd_drafted` | `rule_violated` must be substring of `og_full_text` (definition + inclusions + exclusions) |
| `add_advisor_duty(wd_id, duty_text, db_path)` | Append DraftDuty with `source_type="ADVISOR"` to `advisor_additions` | `og_classified` OR `jd_drafted` | `duty_text` truncated to 500 chars |
| `confirm_duties(wd_id, db_path)` | Set `stage="jd_drafted"` + persist | `og_classified` | The ONLY function that sets this stage |

**Key invariants enforced:**
- `generate_duties()` preserves `wd.advisor_additions` (never clears on re-generate) — see lines preserving `existing_advisor_additions = wd.advisor_additions`
- `stage="jd_drafted"` is set ONLY in `confirm_duties()` — `generate_duties()` saves with stage unchanged
- `og_inclusions` fallback: `og_row["inclusions"] or og_row["definition"] or ""` — handles PE (and others with NULL inclusions)
- Empty duties short-circuits orphan check with `OrphanCheckResult(flags=[], summary="No duties to check for {og}.")` — returns HTTP 200, not 500
- LLM kwargs include `extra_body={"options": {"num_ctx": 8192}}` for local Ollama (matches og_classifier.py pattern)

### Task 2 — `app/api/jd_generation.py` (185 lines) + `app/main.py` edits

**Router:** 4 POST endpoints, each with stage gate (converted to HTTP 422/404 by router) and dual HTMX/JSON response path:

| Route | Form fields | Stage gate | HTMX template |
|-------|-------------|------------|---------------|
| `POST /api/jd/generate-duties` | `wd_id` | `og_classified` (422) | `partials/jd_duties.html` |
| `POST /api/jd/check-orphan-statements` | `wd_id` | `og_classified` or `jd_drafted` | `partials/jd_orphan_results.html` |
| `POST /api/jd/add-advisor-duty` | `wd_id`, `duty_text` | `og_classified` or `jd_drafted` | `partials/jd_duties.html` (re-rendered) |
| `POST /api/jd/confirm-duties` | `wd_id` | `og_classified` (422) | `partials/jd_confirmed.html` |

**main.py edits:**
- Import: `from app.api import jd_generation`
- Register: `app.include_router(jd_generation.router)` after og_classification
- New route: `GET /wizard/jd` returns `wizard/step_jd.html` (with `TemplateNotFound` fallback to a minimal placeholder HTML — Plan 06-04 owns the real template)

### Test environment fix

`tests/test_og_classification.py` and `tests/test_jd_generation.py` were setting `DATABASE_PATH` env var, but `app.config.Settings` reads `db_path` (env: `DB_PATH`, case-insensitive). With the wrong name, Settings loaded `db_path` from `.env` (project root app.db), causing the test route handlers to look up WorkDescriptions in the production DB instead of the test DB.

Fixed both files: `monkeypatch.setenv("DATABASE_PATH", ...)` → `monkeypatch.setenv("DB_PATH", ...)`. This was flagged in the Plan 06-01 SUMMARY as a known issue for Plan 06-03 to resolve.

## Verification

| Check | Result |
|-------|--------|
| `python -c "from app.services.jd_service import ..."` | OK |
| `python -c "from app.api.jd_generation import router"` | OK |
| `python -c "from app.main import app"` | OK — all 4 JD routes registered, `/wizard/jd` registered |
| `pytest tests/test_og_classification.py::TestOGGate -v` | 1 PASSED (was skip) |
| `pytest tests/test_jd_generation.py::TestGenerateDutiesStageGate -v` | 2 PASSED (were skip) |
| `pytest tests/ -x -q` | 141 passed, 2 warnings in 19.33s (was 131 passed, 10 skipped) |

**Net change:** +10 tests transitioned from skip to pass (1 og gate + 2 jd stage gate + 7 from `tests/test_jd_generation.py` that unblocked once the router was registered).

## Deviations

1. **Wizard route TemplateNotFound fallback** — Plan 06-04 owns `templates/wizard/step_jd.html`. The wizard route uses a `try/except jinja2.TemplateNotFound` block that returns a minimal placeholder HTML so the route can be exercised end-to-end without blocking on the template. The real template will land in Plan 06-04 and the fallback becomes dead code.

2. **Test env var rename** — `DATABASE_PATH` → `DB_PATH` in both test files. The 06-01 SUMMARY explicitly flagged this as a follow-up for Plan 06-03.

3. **Agent execution note** — The first subagent attempt to execute this plan stalled in analysis (extensive thinking, no commits). The orchestrator took over and executed the plan inline. All plan-specified code was written verbatim from the plan's `<action>` blocks; no semantic deviations.

## Issues Encountered

None during execution. The agent stall was the only issue and was handled by inline execution per the anti-loop discipline.

## Next Up

Plan 06-04 (Wave 4): HTMX templates (`step_jd.html`, `jd_duties.html`, `jd_orphan_results.html`, `jd_confirmed.html`) + CSS layer 9 + human-verify checkpoint. The `/wizard/jd` placeholder fallback will be replaced by the real template in that plan.
