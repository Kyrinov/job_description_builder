---
phase: 14-noc-pipeline
plan: 03
subsystem: backend
tags: [fastapi, pydantic-v2, api-route, json-only, threat-model]

# Dependency graph
requires:
  - phase: 14
    plan: 01
    provides: "NOC pipeline test infrastructure gate — noc_mapping_db fixture, env_with_db, 12 RED stub tests in test_noc_pipeline.py, 3 pinned production deps (sqlite-vec, instructor, ollama)"
  - phase: 14
    plan: 02
    provides: "Three-stage NL→NOC pipeline ported to v2 (app/services/noc_mapper.py: map_work_description) + NOCMatch Pydantic model + noc_ranking.py: NOCRankingResult + get_noc_connection() factory"
provides:
  - "WorkDescriptionRequest, NocCandidateOut, NocMapResponse Pydantic v2 models in app/models/noc.py — request validates work_description with min_length=10; response decoupled from internal NOCCandidate (clean API boundary)"
  - "POST /api/noc/map JSON-only FastAPI route in app/api/noc_mapping.py — calls map_work_description() via DI on settings.noc_db_path, maps pipeline ValueError → HTTP 422"
  - "api_router updated to include noc_mapping.router (after health.router) — full route is reachable at /api/noc/map"
  - "2 previously-RED stub tests now GREEN: test_api_route_200 and test_empty_fts_result_raises_422"

affects: [14-04, 15, 16, 17, 18, 19, 20]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "API/response-model separation: NocCandidateOut is a distinct Pydantic model from internal NOCCandidate (noc_ranking.py). Keeps the API contract independent of pipeline internals — a v2 FastAPI architectural standard."
    - "Pipeline ValueError → HTTP 422 mapping in the route layer (not in the service). Service raises domain-specific ValueError; route translates to HTTP. Standard FastAPI two-tier error pattern."
    - "JSON-only v2 route (no HTMX dual-path, no Jinja2 TemplateResponse, no HX-Request header branch). Clean React SPA contract."

key-files:
  created:
    - v2/backend/app/models/noc.py
    - v2/backend/app/api/noc_mapping.py
  modified:
    - v2/backend/app/api/__init__.py

key-decisions:
  - "NocCandidateOut mirrors the internal NOCCandidate fields (noc_code, title, teer, rank, matched_duties, justification) but is a SEPARATE Pydantic model. This decouples the API contract from pipeline internals — if Stage 3 (LLM justification) is replaced or refactored, the route response shape can be preserved independently."
  - "Pipeline ValueError is the route's only error translation point. Pydantic-level min_length=10 validation is handled by FastAPI's automatic 422 response (no manual raise needed in the route body)."
  - "Route uses settings.noc_db_path (read from get_settings()) — not a function parameter. Production code paths always go through Settings; the test mocks app.api.noc_mapping.map_work_description directly so the DB path is irrelevant to the test."

patterns-established:
  - "Pattern: separate response model (NocCandidateOut) for API + separate internal model (NOCCandidate) for pipeline. Future endpoints should follow the same decoupling."
  - "Pattern: route module sits in app/api/<name>.py with `router = APIRouter()` and a single route handler. Mount via api_router.include_router(<name>.router) in app/api/__init__.py. No prefixes on the route itself — main.py applies /api prefix globally."

requirements-completed: [API-04, NOC-01]

# Metrics
duration: 2min
completed: 2026-06-04
---

# Phase 14 Plan 03: POST /api/noc/map API Route Summary

**JSON-only FastAPI route for the three-stage NOC pipeline exposed at POST /api/noc/map, with decoupled request/response Pydantic models and pipeline-ValueError → HTTP 422 translation — 12/12 NOC pipeline tests GREEN, 39/39 total tests passing, 0 regressions.**

## Performance

- **Duration:** 2 min (146s)
- **Started:** 2026-06-04T18:23:04Z
- **Completed:** 2026-06-04T18:25:30Z
- **Tasks:** 2 of 2 complete
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- **Clean API contract surface.** `WorkDescriptionRequest` validates `work_description` with `min_length=10` (Pydantic auto-422), `NocCandidateOut` is a separate response model decoupled from internal `NOCCandidate`, `NocMapResponse` wraps `list[NocCandidateOut]`. All three use `extra="ignore"` for forward-compat.
- **POST /api/noc/map route is JSON-only.** No HTMX dual-path, no Jinja2 `TemplateResponse`, no `HX-Request` header check. The route accepts a JSON body, calls the three-stage pipeline via `map_work_description(work_description, settings.noc_db_path)`, translates pipeline `ValueError` → `HTTPException(422, detail=str(exc))`, and returns `NocMapResponse`.
- **api_router is properly wired.** `noc_mapping.router` is included in `api_router` after `health.router`, so the full mount path resolves to `/api/noc/map` (verified via FastAPI route introspection).
- **2 previously-RED stub tests turn GREEN.** `test_api_route_200` confirms POST returns 200 with candidates JSON. `test_empty_fts_result_raises_422` confirms pipeline `ValueError` translates to HTTP 422 with the original error message in the `detail` field.
- **Zero regressions.** Full suite `python -m pytest tests/ -q` shows 39 passed (up from 37 in Plan 02 — the 2 newly-GREEN tests). No prior test broken.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create app/models/noc.py with three Pydantic models** - `6100eef` (feat)
2. **Task 2: Create app/api/noc_mapping.py route + wire into api_router** - `68792f6` (feat)

**Plan metadata:** (committed in final docs commit below)

## Files Created/Modified

### Created
- `v2/backend/app/models/noc.py` (43 lines) — `WorkDescriptionRequest` (with `min_length=10` validator), `NocCandidateOut` (response model with 6 fields), `NocMapResponse` (wraps `list[NocCandidateOut]`). All three use `ConfigDict(extra="ignore")`.
- `v2/backend/app/api/noc_mapping.py` (50 lines) — `router = APIRouter()` + `@router.post("/noc/map", response_model=NocMapResponse) async def map_noc(body: WorkDescriptionRequest) -> NocMapResponse`. Calls `map_work_description` from `app.services.noc_mapper`. Maps `ValueError` → `HTTPException(422, detail=str(exc))`.

### Modified
- `v2/backend/app/api/__init__.py` (21 → 22 lines) — added `noc_mapping` to the `from . import ...` line and added `api_router.include_router(noc_mapping.router)`.

## Decisions Made

- **NocCandidateOut is a separate model from internal NOCCandidate.** Same six fields, but a different Pydantic class. The decoupling means pipeline refactors (e.g., adding `confidence` to `NOCCandidate`) don't propagate to the API response. Future-proofs the route against pipeline changes.
- **No `max_length` on WorkDescriptionRequest.work_description** (Threat T-14-03-02 accepted). Single-user local app; the pipeline's FTS5 stage is bounded by `fts_limit=30` and the embedding stage by `rerank_limit=10`, so absurdly long inputs are bounded downstream. If the app becomes hosted, add `max_length=5000`.
- **No NOC DB persistence in the route.** The endpoint is stateless — the SPA calls it, gets candidates, displays them, and persists `confirmed_noc` via `PATCH /api/wd/{id}` in Phase 15. This is Phase 14's contract per API-04 ("returns top-3 NOC candidates"). Persistence is Phase 15's responsibility.
- **Route uses `settings.noc_db_path`, not a function parameter.** Production paths always go through Settings; the route signature is intentionally minimal. The test mocks `app.api.noc_mapping.map_work_description` directly so the DB path is irrelevant to test execution.

## Deviations from Plan

None - plan executed exactly as written.

**Total deviations:** 0

## Issues Encountered

- **Settings ValidationError when running `python -c` route-mount check outside pytest.** The plan's verification command `python -c "from app.main import app; routes = [r.path for r in app.routes]; print([r for r in routes if 'noc' in r])"` fails with `pydantic_core._pydantic_core.ValidationError: 5 validation errors for Settings` because `make_instructor_client()` is called at module import time and tries to instantiate `Settings()` without env vars. The autouse `_settings_env_defaults` fixture (added in Plan 02) handles this for pytest, but a bare `python -c` does not. Resolved by setting env vars inline before the command: `NOC_DB_PATH=... OLLAMA_BASE_URL=... ... python -c "..."`. Output: `['/api/noc/map']` — route is correctly mounted.
- **Pytest-asyncio 0.24 deprecation warning at pytest startup** (`asyncio_default_fixture_loop_scope is unset`). Pre-existing on all v2 backend runs (also visible in Plan 01 and 02 runs). Not in scope to fix per deviation scope boundary; will be resolved in a future housekeeping plan.

## Stub Tracking

All 12 NOC pipeline tests are now GREEN — zero stubs remaining for Phase 14.

| Test | Status | Notes |
|------|--------|-------|
| `test_fts5_query_rewriting_strips_stop_words` | GREEN (Plan 02) | Pipeline stop-word logic |
| `test_fts5_query_empty_after_filtering_raises` | GREEN (Plan 02) | Stage 1 shortlist guard |
| `test_fts5_stage_returns_noc_codes` | GREEN (Plan 02) | Stage 1 with mocked Stage 2+3 |
| `test_stage2_calls_embed_model` | GREEN (Plan 02) | Stage 2 calls embed with correct model |
| `test_pipeline_returns_candidates` | GREEN (Plan 02) | Full 3-stage pipeline with mocks |
| `test_verbatim_guardrail_strips_fabricated` | GREEN (Plan 02) | Online guardrail #1 |
| `test_verbatim_guardrail_raises_when_all_stripped` | GREEN (Plan 02) | Online guardrail #1 raises path |
| `test_api_route_200` | **GREEN (Plan 03)** | API-04: POST returns 200 with candidates |
| `test_empty_fts_result_raises_422` | **GREEN (Plan 03)** | API-04: pipeline ValueError → 422 |
| `TestNOCCandidateSchema::test_noc_candidate_schema` | GREEN (Plan 02) | Pydantic schema |
| `TestNOCCandidateSchema::test_teer_is_integer` | GREEN (Plan 02) | Pydantic schema |
| `TestNOCCandidateSchema::test_ranks_are_sequential` | GREEN (Plan 02) | Pydantic schema |

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: input-validation | v2/backend/app/models/noc.py | `WorkDescriptionRequest.work_description` has `min_length=10` only (no `max_length`). Single-user local app — T-14-03-02 accepted. |
| threat_flag: ssrf | v2/backend/app/api/noc_mapping.py | `settings.ollama_base_url` is unvalidated (T-14-02-03 from Plan 02). Phase 14 inherits the same threat surface as Plan 02. |

## User Setup Required

None - no external service configuration required. Tests use the autouse `_settings_env_defaults` fixture; production reads from `v2/backend/.env.example`. Ollama is optional — the API tests mock the pipeline layer so they pass without any local LLM runtime.

## Next Phase Readiness

**Phase 14 is complete (3/4 plans).** Plan 04 (wave 3) remains if any additional NOC-related work was scoped; otherwise, **Phase 15 (Conversational UX — CONVO-01..05, API-02)** is unblocked. It can:

- Wire the React SPA to call `POST /api/noc/map` via the Vite proxy (`/api/*` → `:8000`)
- Add the NOC confirmation step to the conversation flow (uses `WorkDescription.confirmed_noc` from Plan 02)
- Implement `PATCH /api/wd/{id}` to persist `confirmed_noc` when the advisor selects a candidate
- The `NocConfirmCard` component (frontend, scoped to Phase 14) renders the candidates returned by this route

No blockers. No decisions needed from user.

---

## Self-Check: PASSED

All claimed deliverables verified:

- `v2/backend/app/models/noc.py` — exists, 43 lines, 3 Pydantic models confirmed via `grep` (4/4 patterns: `class WorkDescriptionRequest`, `class NocCandidateOut`, `class NocMapResponse`, `min_length=10`)
- `v2/backend/app/api/noc_mapping.py` — exists, 50 lines, route handler + HTTPException(422) confirmed via `grep`
- `v2/backend/app/api/__init__.py` — exists, modified, `noc_mapping` import + `include_router` confirmed via `grep`
- Commit `6100eef` (Task 1: noc models) — found in git log
- Commit `68792f6` (Task 2: route + wiring) — found in git log
- `python -m pytest tests/test_noc_pipeline.py -v` — 12 passed, 0 skipped, 0 failed (2 tests newly GREEN)
- `python -m pytest tests/ -q` — 39 passed, 0 skipped, 0 failed (no regressions; +2 from Plan 02's 37)
- Route mounted at `/api/noc/map` — confirmed via FastAPI route introspection with env vars set
- `grep -E "HX-Request|TemplateResponse|Jinja2" v2/backend/app/api/noc_mapping.py` — 0 matches (no HTMX patterns)

---

*Phase: 14-noc-pipeline*
*Completed: 2026-06-04*
