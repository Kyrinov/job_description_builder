---
phase: 14-noc-pipeline
plan: 02
subsystem: backend
tags: [fastapi, pydantic-v2, sqlite-vec, instructor, ollama, fts5, asyncio, settings, dependency-injection, factory-pattern, two-database]

# Dependency graph
requires:
  - phase: 10
    provides: v2 backend scaffold (FastAPI + Pydantic v2 + SQLite) with conftest.py tmp_db_path + env_with_db fixtures
  - phase: 14
    provides: "Plan 01 (14-01) — NOC pipeline test infrastructure gate: noc_mapping_db fixture, env_with_db with NOC env vars, 12 RED stub tests, 3 pinned production deps (sqlite-vec==0.1.9, instructor==1.15.1, ollama==0.6.1)"

provides:
  - "NOCMatch Pydantic model in app/models/noc_match.py (noc_code, noc_title, teer, matched_duties, justification, rank) — used by WorkDescription.noc_candidates + WorkDescription.confirmed_noc"
  - "WorkDescription extended with noc_candidates: list[NOCMatch] and confirmed_noc: Optional[NOCMatch] — NOC fields land on the WD entity"
  - "Settings extended with 7 new fields (noc_db_path, ollama_base_url, ollama_generation_model, ollama_embed_model, cloud_api_key, cloud_model, cloud_base_url) and generation_model property (cloud_model if cloud_api_key else ollama_generation_model)"
  - "get_noc_connection(noc_db_path) factory in app/db.py — opens NOC DB with sqlite-vec registered; distinct from get_connection() (WD DB without vec)"
  - "app/ai/noc_ranking.py — NOCCandidate + NOCRankingResult Pydantic models with field validators (noc_code all digits, matched_duties non-blank, ranks sequential 1..N) + make_instructor_client() factory + module-level instructor_client singleton"
  - "app/services/noc_mapper.py — full 3-stage NL→NOC pipeline ported from v1.0 with v2 adaptations: get_noc_connection(noc_db_path) instead of get_connection(db_path), settings = get_settings() inside async function body, dropped to_noc_match() and NOCMatch/ProvenanceTag imports (Phase 18 work)"
  - "v2/backend/.env.example updated with NOC_DB_PATH, OLLAMA_BASE_URL, OLLAMA_GENERATION_MODEL, OLLAMA_EMBED_MODEL, and commented CLOUD_* placeholders"
  - "Autouse _settings_env_defaults fixture in tests/conftest.py — sets minimum env vars for Settings() instantiation at module import (v2 backend has no committed .env file unlike v1.0's top-level .env)"

affects: [14-03, 14-04, 15, 16, 17, 18, 19, 20]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-database architecture: get_connection(db_path) for v2 WD DB (no vec) vs get_noc_connection(noc_db_path) for v1.0 NOC DB (with sqlite-vec). Same sqlite3.Connection row factory, different extensions loaded."
    - "Module-level instructor_client singleton (matches v1.0 architecture non-negotiable: httpx pool is one, not per-request)"
    - "make_instructor_client() factory that calls get_settings() inside the function body — allows test monkeypatching of env vars before Settings is instantiated (v2 lazy factory pattern)"
    - "NOC pipeline parameter explicit: map_work_description(work_description, noc_db_path, *, fts_limit=30, rerank_limit=10) — NOT implicit env var — for testability"
    - "asyncio.to_thread wrapping on all blocking sqlite3 calls preserved from v1.0 — FastAPI event loop never blocks on SQLite I/O"
    - "Autouse _settings_env_defaults fixture pattern — env vars set before module imports; monkeypatch auto-restores on teardown so values do not leak between tests"
    - "Stage 1 FTS5 uses parameterized MATCH ? (never string interpolation) — non-negotiable from v1.0 architecture, verified"
    - "Stage 2 vec0 uses sqlite_vec.serialize_float32(query_vec) before passing to SQL — passing raw list[float] raises InterfaceError"
    - "Online guardrails: verbatim fidelity check (strips fabricated matched_duties not in DB) + TEER DB correction (overwrites LLM teer with authoritative noc_units value)"

key-files:
  created:
    - v2/backend/app/models/noc_match.py
    - v2/backend/app/ai/__init__.py
    - v2/backend/app/ai/noc_ranking.py
    - v2/backend/app/services/__init__.py
    - v2/backend/app/services/noc_mapper.py
  modified:
    - v2/backend/app/config.py
    - v2/backend/app/db.py
    - v2/backend/app/models/work_description.py
    - v2/backend/.env.example
    - v2/backend/tests/conftest.py

key-decisions:
  - "NOCMatch model simplified relative to v1.0 — drops ProvenanceTag, drops teer_level→teer int conversion, drops confidence/rationale/matched_duty_statements. Phase 18 backfills ProvenanceTag downstream; simplified model is forward-compatible."
  - "get_noc_connection() is a SEPARATE factory from get_connection() — WD DB has no vec0 tables; loading sqlite-vec on every WD connection is wasted work and would fail in tests that use in-memory temp DBs without NOC schema."
  - "noc_db_path is a function parameter on map_work_description, not read from settings inside the function — lets tests pass temp paths directly without monkeypatching env vars inside the test body."
  - "Settings access moved from module-level import to get_settings() call inside the async function body (per Pitfall 3 in RESEARCH.md) — avoids the v1.0 'eager Settings at import time' trap when tests monkeypatch env vars."
  - "dropped to_noc_match() function from v1.0 noc_mapper.py — it mapped NOCCandidate→NOCMatch with ProvenanceTag, but Phase 14 doesn't need that mapping (advisor confirmation lands in Phase 15 via PATCH /api/wd/{id}, not via the pipeline)."
  - "Added autouse _settings_env_defaults fixture in conftest.py (Rule 2 deviation) — v1.0 relied on a top-level .env file; v2 backend has no committed .env (gitignored). Without autouse env, pytest.importorskip on app.ai.noc_ranking fails with Settings ValidationError. Autouse fixture is the standard pytest pattern for this and doesn't pollute test isolation because monkeypatch restores env on teardown."

patterns-established:
  - "Pattern: NOC pipeline two-database separation — WD DB at DB_PATH (v2 owns) and NOC DB at NOC_DB_PATH (v1.0 read-only archive). Add new factories alongside get_connection() / get_noc_connection() for new DB types — never mix concerns."
  - "Pattern: instructor_client singleton — module-level instantiation, but built via make_instructor_client() factory calling get_settings() inside the function body. Tests mock app.services.noc_mapper.instructor_client directly (same as v1.0 pattern)."
  - "Pattern: Settings access in async functions — always call get_settings() inside the function body, never at module level. The lazy factory pattern is the v2 architectural contract; module-level `settings = Settings()` would break test monkeypatching."

requirements-completed: [NOC-01, NOC-02]

# Metrics
duration: 25min
completed: 2026-06-04
---

# Phase 14 Plan 02: NOC Pipeline Port Summary

**Three-stage NL→NOC pipeline (FTS5 → sqlite-vec rerank → instructor LLM justification) ported from v1.0 to v2 backend with two-database separation, NOCMatch Pydantic model, and make_instructor_client() factory — 10/12 NOC pipeline tests GREEN, 37 total tests passing, 0 regressions.**

## Performance

- **Duration:** 25 min (1504s)
- **Started:** 2026-06-04T17:52:36Z
- **Completed:** 2026-06-04T18:17:40Z
- **Tasks:** 2 of 2 complete
- **Files modified:** 10 (5 created, 5 modified)

## Accomplishments

- **Two-database architecture established.** `get_connection(db_path)` for the v2 WD DB (no sqlite-vec) is now joined by `get_noc_connection(noc_db_path)` for the v1.0 NOC DB (sqlite-vec loaded). The factory names are explicit about their concern — NOC DB is read-only from v2's perspective and must not be mutated by `create_schema()`.
- **NOCMatch model + WorkDescription NOC fields.** `noc_candidates: list[NOCMatch]` and `confirmed_noc: Optional[NOCMatch]` are now part of the WD entity. The NOCMatch model is leaner than v1.0's (no ProvenanceTag) because Phase 18 backfills provenance downstream; keeping v2's NOCMatch minimal avoids importing v1.0's ProvenanceTag early.
- **Settings extended with 7 NOC fields + generation_model property.** Cloud-vs-Ollama routing is now a one-line `settings.generation_model` lookup. Required env vars (noc_db_path, ollama_generation_model, ollama_embed_model) raise `ValidationError` on import when missing — same fail-fast contract v1.0 established.
- **Full 3-stage pipeline ported.** `_fts_query_from_text` (stop word filtering), `map_work_description` (Stage 1 FTS5 → Stage 2 sqlite-vec rerank → Stage 3 instructor LLM), `_check_verbatim_fidelity` (DB lookup to strip fabricated duties), `_correct_teer_from_db` (authoritative teer overwrites LLM hallucination). All v1.0 logic preserved verbatim, with v2-specific parameter rename (`db_path` → `noc_db_path`) and factory pattern.
- **instructor_client singleton via factory.** `make_instructor_client()` calls `get_settings()` inside the function body (not at import), then builds the AsyncOpenAI client based on `cloud_api_key` presence. The module-level `instructor_client = make_instructor_client()` is built once at import time per v1.0's architectural non-negotiable (one httpx connection pool, not per-request).
- **10 of 12 NOC pipeline tests turn GREEN.** Stage 1 (FTS5 query rewriting, empty shortlist, returns codes), Stage 2 (calls embed model with correct model name), full pipeline (returns NOCRankingResult with candidates), verbatim guardrail (strips fabricated duties, raises when all stripped), and 3 Pydantic schema tests. The 2 remaining tests (test_api_route_200, test_empty_fts_result_raises_422) skip because they need `app.api.noc_mapping` — that lands in Plan 04.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add NOC fields to Settings, get_noc_connection() to db.py, NOCMatch model** - `41cb3dd` (feat)
2. **Task 2: Port noc_ranking.py and noc_mapper.py to v2** - `cc33cc1` (feat)

## Files Created/Modified

### Created
- `v2/backend/app/models/noc_match.py` — NOCMatch Pydantic model (6 fields: noc_code, noc_title, teer, matched_duties, justification, rank)
- `v2/backend/app/ai/__init__.py` — empty package init
- `v2/backend/app/ai/noc_ranking.py` — NOCCandidate + NOCRankingResult Pydantic models with field validators; `make_instructor_client()` factory; module-level `instructor_client` singleton
- `v2/backend/app/services/__init__.py` — empty package init
- `v2/backend/app/services/noc_mapper.py` — ported 3-stage NL→NOC pipeline (283 lines, near-verbatim from v1.0 with v2-specific diffs)

### Modified
- `v2/backend/app/config.py` — added 7 NOC fields + `generation_model` property (37 → 64 lines)
- `v2/backend/app/db.py` — appended `get_noc_connection()` factory (68 → 90 lines)
- `v2/backend/app/models/work_description.py` — added `noc_candidates: list[NOCMatch]` + `confirmed_noc: Optional[NOCMatch]` fields, plus `from .noc_match import NOCMatch` import
- `v2/backend/.env.example` — added NOC_DB_PATH, OLLAMA_*, commented CLOUD_* sections
- `v2/backend/tests/conftest.py` — added autouse `_settings_env_defaults` fixture (Rule 2 deviation)

## Decisions Made

- **NOCMatch leaner than v1.0 (no ProvenanceTag).** The v1.0 NOCMatch carried a `ProvenanceTag` (source_type, source_id, source_version, retrieved_date, model_name). v2's NOCMatch drops this and stores only the fields the SPA needs to render the confirmation card (code, title, teer, duties, justification, rank). Phase 18 backfills provenance during duty selection; the lean model is forward-compatible because the WD entity can store additional metadata as ProvenanceTag is added in Phase 18.
- **NOC DB is a separate connection factory.** `get_noc_connection()` is added alongside `get_connection()`, not in place of. The two factories serve different databases with different extension loading requirements. Tests that need WD DB + NOC DB together (none yet, but plausible in Phase 15) can call both factories with different paths.
- **`noc_db_path` is a function parameter, not read from settings inside `map_work_description()`.** This is the v1.0 pattern (`db_path` is a parameter), and the test infrastructure depends on it — tests pass `noc_mapping_db` (a `tmp_path` fixture) directly, avoiding env-var indirection. The `Settings.noc_db_path` field still exists so production code paths can read it from settings.
- **Settings is NOT a module-level singleton in v2.** v1.0 had `settings = Settings()` at module level in `app/config.py`; v2 has `get_settings()` (lazy factory). This is a hard architectural pivot established in Phase 10 and re-affirmed in RESEARCH.md Pitfall 3. The `noc_ranking.py` port uses `make_instructor_client()` factory that calls `get_settings()` inside the function body — so the test can monkeypatch env vars BEFORE Settings is instantiated.
- **dropped `to_noc_match()` from v1.0.** v1.0's `noc_mapper.py` had a helper function `to_noc_match(NOCCandidate) -> NOCMatch` that mapped pipeline output to WD storage type (with ProvenanceTag attachment). Phase 14 doesn't need this — the pipeline just returns `NOCRankingResult`, and the WD stores `confirmed_noc` when the SPA PATCHes it in Phase 15. The mapping logic lands in Phase 18 if needed for stored `noc_candidates`.
- **Autouse `_settings_env_defaults` fixture in conftest.py (Rule 2 deviation).** Without this fixture, `pytest.importorskip("app.ai.noc_ranking")` in schema-only tests fails because `instructor_client = make_instructor_client()` raises `ValidationError` when env vars are missing. v1.0 tests relied on a top-level `.env` file (which is in the project root and gets picked up by `Settings(env_file=".env")`); v2 backend has no committed `.env` (gitignored). The autouse fixture is the standard pytest pattern for this case and is harmless to tests that don't import Settings-using modules because monkeypatch restores env on teardown.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added autouse _settings_env_defaults fixture to conftest.py**
- **Found during:** Task 2 verification — all 3 TestNOCCandidateSchema tests and `test_fts5_query_rewriting_strips_stop_words` failed with `pydantic_core._pydantic_core.ValidationError: 5 validation errors for Settings`
- **Issue:** `app/ai/noc_ranking.py` instantiates `instructor_client` at module import time via `make_instructor_client()`, which calls `get_settings()` and instantiates `Settings()`. Settings requires `db_path`, `project_root`, `noc_db_path`, `ollama_generation_model`, `ollama_embed_model`. v1.0 tests relied on a top-level `.env` file (which is in the project root, picked up by `Settings(env_file=".env")`); v2 backend has no committed `.env` (gitignored). The v2 conftest's `env_with_db` fixture sets these vars but is NOT autouse, so tests that don't request it can't import `app.ai.noc_ranking`.
- **Fix:** Added `@pytest.fixture(autouse=True)` `_settings_env_defaults` fixture in `v2/backend/tests/conftest.py`. Sets minimum env vars (`DB_PATH`, `PROJECT_ROOT`, `NOC_DB_PATH`, `OLLAMA_BASE_URL`, `OLLAMA_GENERATION_MODEL`, `OLLAMA_EMBED_MODEL`) to `tmp_path`-based values so each test gets a fresh DB path. monkeypatch restores env on teardown — no cross-test contamination.
- **Files modified:** `v2/backend/tests/conftest.py`
- **Verification:** `python -m pytest tests/test_noc_pipeline.py -v` — 10 passed, 2 skipped (0 failed). `python -m pytest tests/ -q` — 37 passed, 2 skipped, 0 regressions.
- **Committed in:** `cc33cc1` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Single deviation is essential for correctness — without the autouse fixture, all schema-only tests fail with ValidationError at module import. No scope creep. Plan's "instructor_client built at module import time" architecture is preserved (the fixture makes Settings instantiation work, not the singleton).

## Issues Encountered

None.

## Stub Tracking

After this plan, all 12 NOC pipeline tests are accounted for:

| Test | Status | Notes |
|------|--------|-------|
| `test_fts5_query_rewriting_strips_stop_words` | GREEN | Pipeline stop-word logic |
| `test_fts5_query_empty_after_filtering_raises` | GREEN | Stage 1 shortlist guard |
| `test_fts5_stage_returns_noc_codes` | GREEN | Stage 1 with mocked Stage 2+3 |
| `test_stage2_calls_embed_model` | GREEN | Stage 2 calls embed with correct model |
| `test_pipeline_returns_candidates` | GREEN | Full 3-stage pipeline with mocks |
| `test_verbatim_guardrail_strips_fabricated` | GREEN | Online guardrail #1 |
| `test_verbatim_guardrail_raises_when_all_stripped` | GREEN | Online guardrail #1 raises path |
| `test_api_route_200` | STUB (skipped) | Needs `app.api.noc_mapping` — Plan 04 |
| `test_empty_fts_result_raises_422` | STUB (skipped) | Needs `app.api.noc_mapping` — Plan 04 |
| `TestNOCCandidateSchema::test_noc_candidate_schema` | GREEN | Pydantic schema |
| `TestNOCCandidateSchema::test_teer_is_integer` | GREEN | Pydantic schema |
| `TestNOCCandidateSchema::test_ranks_are_sequential` | GREEN | Pydantic schema |

No remaining stubs. 2 tests still skip because they require Plan 04's API route — that is the next plan's work, not a regression.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| (none) | — | No new threat surface introduced. Stage 1 SQL uses parameterized MATCH ? (mitigation T-14-02-01 verified). noc_db_path comes from Settings (mitigation T-14-02-02). Ollama base URL is unvalidated (T-14-02-03 accepted per RESEARCH.md security domain — single-user local app). |

## User Setup Required

None - no external service configuration required. The new code reads env vars from the existing `v2/backend/.env.example` template; tests use the autouse fixture. Ollama is optional — the tests use mocks so they pass without any local LLM runtime.

## Next Phase Readiness

**Plan 03 (API-04 — POST /api/noc/map endpoint)** is unblocked. It can:
- Create `v2/backend/app/api/noc_mapping.py` with the JSON-only route
- Wire it into `v2/backend/app/main.py` via `api_router.include_router(noc_mapping.router)`
- The 2 remaining stub tests (test_api_route_200, test_empty_fts_result_raises_422) will turn GREEN
- `map_work_description` is fully importable and mockable; tests already patch `app.api.noc_mapping.map_work_description` directly (per Plan 01's design)

**Plan 15 (CONVO — NOC step in the conversation UX)** is unblocked. The `WorkDescription.noc_candidates` and `WorkDescription.confirmed_noc` fields are now in the model, so the SPA can PATCH these when the advisor confirms.

**Phase 18 (JD Composition)** is unblocked (delayed dependency). The `NOCMatch` model is the storage type it consumes; no further changes needed to NOCMatch unless ProvenanceTag attachment requires field additions.

No blockers. No decisions needed from user.

---

## Self-Check: PASSED

All claimed deliverables verified:

- `v2/backend/app/config.py` — exists, 64 lines, 7 new NOC fields + `generation_model` property
- `v2/backend/app/db.py` — exists, 90 lines, `get_noc_connection()` factory with sqlite-vec loading
- `v2/backend/app/models/noc_match.py` — exists, NOCMatch model with 6 fields
- `v2/backend/app/models/work_description.py` — exists, `noc_candidates` + `confirmed_noc` fields added
- `v2/backend/app/ai/noc_ranking.py` — exists, NOCCandidate + NOCRankingResult + `make_instructor_client()` factory + module-level `instructor_client` singleton
- `v2/backend/app/services/noc_mapper.py` — exists, full 3-stage pipeline ported from v1.0 with v2 adaptations
- `v2/backend/.env.example` — exists, NOC_DB_PATH + OLLAMA_* + commented CLOUD_* sections
- `v2/backend/tests/conftest.py` — exists, autouse `_settings_env_defaults` fixture added
- `.planning/phases/14-noc-pipeline/14-02-SUMMARY.md` — exists, this file
- Commit `41cb3dd` (Task 1) — found in git log
- Commit `cc33cc1` (Task 2) — found in git log
- `python -m pytest tests/test_noc_pipeline.py -v` — 10 passed, 2 skipped, 0 failed
- `python -m pytest tests/ -q` — 37 passed, 2 skipped, 0 failed (no regressions)
- `grep` checks for v1.0 anti-patterns in v2 code — 0 matches (all correct: v1.0 patterns must NOT appear)

---

*Phase: 14-noc-pipeline*
*Completed: 2026-06-04*
