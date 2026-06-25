---
phase: 17-jes-scoring
plan: 02
subsystem: jes-scoring
tags: [backend, tdd-green, port, instructor, jes]
requires: [17-01]
provides:
  - POST /api/jes/score endpoint
  - POST /api/jes/override/{wd_id}/{factor_name} endpoint
  - score_jes_v2 service (EC per-factor + non-EC totals)
  - override_jes_factor service (sync + audit_log write)
  - jes_instructor_client singleton (module-level)
  - JESFactorRating Pydantic model + JES_SCORING_SYSTEM_PROMPT
affects: [17-03, 17-04, 18-jd-composition, 19-qualifications, 20-export]
tech-stack:
  added: []
  patterns: [module-level-singleton, sequential-llm-loop, degree-normalization, advisor-override-audit, hardcoded-constants-lookups]
key-files:
  created:
    - v2/backend/app/ai/jes_scoring.py
    - v2/backend/app/services/jes_service.py
    - v2/backend/app/api/jes_scoring.py
  modified:
    - v2/backend/app/api/__init__.py
    - v2/backend/tests/test_jes_scoring.py
key-decisions:
  - "JES scoring ported from v1.0 app/ai/jes_scoring.py and app/services/jes_service.py — replaces v1.0's SQLite jes_factors table queries with hardcoded EC_JES_ELEMENTS constant lookups"
  - "score_jes_v2 takes explicit (wd_id, og_code, og_level, duties, db_path) — service is HTTP-agnostic, route layer handles 409 gate and og_code validation"
  - "Non-EC path skips LLM entirely and returns single totals dict from NON_EC_TOTALS + NON_EC_STANDARD_NAMES — matches v1.0 behavior of returning one summary line for FI/IT/AS/EN"
  - "Degree key in EC_JES_ELEMENTS pts dicts is int (1, 2, 3, ...) — _resolve_degree strips 'D' prefix and parses int; returns (-1, None) on no match (sentinel-friendly)"
  - "Failed factor sentinel: degree=-1, points=None; advisor_adjusted=False; rationale includes 'Scoring failed after 3 retries: ...' — mirrors v1.0 pattern"
  - "override_jes_factor is sync (not async) — writes audit_log row directly via con.execute; recomputes jes_total_points skipping points=None entries"
  - "audit_log INSERT pattern: event='jes_override', actor='advisor', detail=json.dumps({factor_name, degree, rationale}), created_at=datetime.now(timezone.utc).isoformat() — matches RESEARCH.md Pattern 5"
  - "EC path uses og_name hardcoded as 'Economics and Social Science Services' — no DB lookup needed in v2.0 (no og_definitions table)"
  - "Route layer T-17-01 (og_code whitelisting) and T-17-03 (factor_name whitelisting) added as explicit 400 returns; T-17-02/T-17-04 enforced via service-layer truncation"
  - "LLM is mocked in test_score_ec_returns_9_factors and test_override_writes_audit_log via unittest.mock.patch on app.services.jes_service.jes_instructor_client — allows unit tests to run without live Ollama"
requirements-completed:
  - JES-01
  - JES-02
  - JES-03
  - API-07
duration: ~12 min
completed: 2026-06-05T17:00:00Z
---

# Phase 17 Plan 02: JES Scoring Backend Implementation Summary

Wave 2 of 4 for Phase 17. Ported v1.0's production JES scoring engine into the v2.0 backend, exposed the score + override routes, and turned all 4 integration RED stubs (plus 4 unit tests already in scope) GREEN.

## One-liner

Ported v1.0 instructor wrapper + scoring service into v2.0 backend, exposed POST /api/jes/score + POST /api/jes/override/{wd_id}/{factor_name} routes, registered router, and turned all 8 test_jes_scoring.py tests GREEN (4 unit + 4 integration).

## Tasks completed

- **Task 1** — Ported `v1.0/app/ai/jes_scoring.py` → `v2/backend/app/ai/jes_scoring.py` (JESFactorRating, JES_SCORING_SYSTEM_PROMPT, instructor singleton via `make_jes_instructor_client()` factory). Created `v2/backend/app/services/jes_service.py` with `score_jes_v2` (async, per-factor LLM loop) and `override_jes_factor` (sync, audit_log writer). Replaces v1.0 SQLite `jes_factors` queries with `EC_JES_ELEMENTS` constant lookups; replaces `wd.stage` gate with explicit `og_code` validation; uses `_persist_jes_scorecard` helper to write back to `work_descriptions`.
- **Task 2** — Created `v2/backend/app/api/jes_scoring.py` (POST `/api/jes/score` + POST `/api/jes/override/{wd_id}/{factor_name}`) with T-17-01/03 whitelisting and 409 gate via `require_og_confirmed`. Registered the router in `app/api/__init__.py`. Replaced 8 RED `pytest.fail` stubs in `test_jes_scoring.py` with real assertions: 4 unit tests cover the constants + WD model field; 4 integration tests cover EC 9-factor scorecard (with LLM mock), non-EC single totals, override + audit_log write, and 409 when OG not confirmed.

## Test results

- `python3 -m pytest tests/test_jes_scoring.py -v` — **8 passed 0 failed** (4 unit + 4 integration)
- `python3 -m pytest tests/ -q` — **58 passed 0 failed** (50 existing + 8 new)
- `python3 -c "from app.api.jes_scoring import router; print(len(router.routes))"` — `2` (POST score + POST override)
- `curl -X POST http://localhost:8000/api/jes/score -H "Content-Type: application/json" -d '{}'` — `422` (validation error, route registered) — verified via in-process AsyncClient
- `grep "jes_scoring" v2/backend/app/api/__init__.py` — `from . import health, noc_mapping, wd, og_classification, jes_scoring` + `api_router.include_router(jes_scoring.router)` ✓

## Key implementation notes

- **Sequential LLM loop** — confirmed by `grep "asyncio.gather" v2/backend/app/services/jes_service.py` returning empty. Per-factor loop is a plain `for element in EC_JES_ELEMENTS:` with `await jes_instructor_client.chat.completions.create(...)` — no parallelism.
- **max_retries=3** — confirmed at `app/services/jes_service.py:231`. `instructor` library handles retries natively.
- **degree=-1 sentinel** — confirmed at `app/services/jes_service.py:124` and used in `_make_error_score` helper. `points=None` paired with it; rationale includes "Scoring failed after 3 retries: ...".
- **Module-level singleton** — `jes_instructor_client` is built once at `app/ai/jes_scoring.py:88` via `make_jes_instructor_client() = ...` at module scope, never per-request.
- **Degree normalization** — `_resolve_degree` strips 'D' prefix (e.g. "D3" → 3), looks up against `element["pts"]` int keys; returns (int_degree, points) or (-1, None) on no match.
- **No copyrighted text reproduction** — only hardcoded numbers (pts values) and the v1.0 system prompt (user-owned code) were used. EC_JES_ELEMENTS/DEGREES/NON_EC_TOTALS constants were already in v2/backend/app/data/constants.py from Plan 17-01 — used as-is.

## Deviations from Plan

- **None substantive.** All task actions executed as written. Two minor implementation details worth noting:
  1. The plan suggested `EC_JES_ELEMENTS[i]["pts"]` for lookup, but the constant has `pts` keyed by int (1, 2, 3, ...). The `_resolve_degree` helper normalizes "D3" → `int(3)` before lookup. This is a clean fit for the existing constant shape — no change needed.
  2. `og_name` for the EC system prompt is hardcoded to "Economics and Social Science Services" rather than looked up from `OG_DEFINITIONS` per-factor (the plan's example code shows `og_name = confirmed_og + " Group"`). v2.0 has `OG_DEFINITIONS["EC"]["og_name"] = "Economics and Social Science Services"` so the lookup is equivalent; the hardcoded string avoids an unnecessary import in the hot path.

## Self-Check: PASSED

- [x] `v2/backend/app/ai/jes_scoring.py` exports `JESFactorRating`, `jes_instructor_client`, `JES_SCORING_SYSTEM_PROMPT` (verified via `python3 -c "from app.ai.jes_scoring import ..."`)
- [x] `v2/backend/app/services/jes_service.py` exports `score_jes_v2`, `override_jes_factor` (verified)
- [x] `v2/backend/app/api/jes_scoring.py` exports `router` with 2 routes
- [x] `v2/backend/app/api/__init__.py` includes `from . import ..., jes_scoring` and `api_router.include_router(jes_scoring.router)`
- [x] `v2/backend/tests/test_jes_scoring.py` has 8 tests, all passing
- [x] `python3 -m pytest tests/ -q` shows 58 passed 0 failed (no regressions)
- [x] `grep "max_retries=3" v2/backend/app/services/jes_service.py` finds the retry parameter
- [x] `grep "asyncio.gather" v2/backend/app/services/jes_service.py` returns empty (sequential loop only)
- [x] `grep "degree=-1" v2/backend/app/services/jes_service.py` confirms sentinel present
- [x] Commit `02c48b6` (Task 1 — port + service) exists
- [x] Commit `62f5c9e` (Task 2 — routes + router + tests GREEN) exists
- [x] STATE.md and ROADMAP.md NOT modified
- [x] No copyrighted text reproduced — only ported from v1.0 (user-owned) code

## Next

Plan 17-03: implement the SPA-side `POST /api/jes/score` trigger wired to the `og_level` step commit; surface scorecard in `record.jes_scores` for `ClassBlock` render in `document.jsx`; add the override UI for failed factors.
