---
phase: 14-noc-pipeline
plan: 01
subsystem: testing
tags: [pytest, nist-nyquist, noc, sqlite-vec, instructor, ollama, fts5, red-stubs]

# Dependency graph
requires:
  - phase: 10
    provides: v2 backend scaffold (FastAPI + Pydantic v2 + SQLite) with conftest.py tmp_db_path + env_with_db fixtures
  - phase: 11
    provides: v2.0 data foundation (OG_LEVELS, CAF_RANK_OG_EQUIVALENCE) so subsequent NOC pipeline knows the target taxonomy
provides:
  - "Test infrastructure gate: noc_mapping_db fixture with NOC schema (noc_units, noc_elements, noc_fts FTS5, noc_chunks_vec FLOAT[768], index_metadata) — runs without Ollama"
  - "Updated env_with_db fixture that monkeypatches NOC_DB_PATH, OLLAMA_BASE_URL, OLLAMA_GENERATION_MODEL, OLLAMA_EMBED_MODEL on top of DB_PATH/PROJECT_ROOT"
  - "12 RED stub tests in test_noc_pipeline.py covering NOC-01 (3-stage pipeline + verbatim guardrails), API-04 (POST /api/noc/map), and NOC-02 (NOCCandidate/NOCCandidateResult schema)"
  - "Three pinned production dependencies in requirements.txt: sqlite-vec==0.1.9, instructor==1.15.1, ollama==0.6.1"
affects: [14-02, 14-03, 14-04, 15, 16, 17, 18, 19, 20]

# Tech tracking
tech-stack:
  added:
    - "sqlite-vec==0.1.9 (vec0 extension for embedding KNN, FLOAT[768])"
    - "instructor==1.15.1 (structured LLM output with retry semantics)"
    - "ollama==0.6.1 (async embed + generation client for local LLM)"
  patterns:
    - "RED stub test pattern: pytest.importorskip at body start so tests skip before modules exist"
    - "Inline sqlite-vec loading in fixture (sv.load + enable_load_extension) so fixture works without get_noc_connection() factory"
    - "Explicit noc_db_path parameter on map_work_description (vs implicit env var) for testability"
    - "Test-only env var monkeypatching via env_with_db + per-test overrides in test bodies"

key-files:
  created:
    - v2/backend/tests/test_noc_pipeline.py
  modified:
    - v2/backend/tests/conftest.py
    - v2/backend/requirements.txt

key-decisions:
  - "Pinned all three NOC pipeline deps at exact versions (==0.1.9, ==1.15.1, ==0.6.1) so Plan 02-04 can rely on reproducible installs"
  - "noc_mapping_db fixture creates vec0 table at FLOAT[768] (matching nomic-embed-text output) — not FLOAT[1024] from v1.0 DDL — so KNN distance math is correct for the embed model we use"
  - "noc_mapping_db fixture is self-contained (sqlite3.connect + sv.load inline) rather than going through get_noc_connection() which Plan 02 will create — keeps this plan free of Plan-02 coupling"
  - "Signature uses explicit noc_db_path param (not implicit env var) so map_work_description is testable in isolation and doesn't require Settings to be loaded"
  - "12 stubs (exceeds the 10-stub minimum) to give Plan 02-04 richer coverage: 7 NOC-01 + 2 API-04 + 3 NOC-02"
  - "Tests use AsyncMock + MagicMock + patch() to mock OllamaAsyncClient and instructor_client so they run without any local LLM runtime"

patterns-established:
  - "Pattern: NOC pipeline test stubs use pytest.importorskip at the top of the test body (not module-level) so collection succeeds but the test body skips if app.services.noc_mapper / app.ai.noc_ranking don't exist yet"
  - "Pattern: NOC schema fixture includes index_metadata row with embedding_model='nomic-embed-text:latest' so the startup-assertion function (assert_noc_index_model) passes without a real ingest"
  - "Pattern: env_with_db monkeypatches ALL env vars needed by Settings in one place — every new env var is added here, not ad-hoc in test bodies — keeps Settings tests in lockstep with config"
  - "Pattern: plan metadata commit separates SUMMARY.md from per-task commits so verifier can audit task commits independently"

requirements-completed: [NOC-01, NOC-02, API-04]

# Metrics
duration: 4min
completed: 2026-06-04
---

# Phase 14 Plan 01: NOC Pipeline Wave 0 Test Infrastructure Summary

**Wave 0 test-infrastructure gate for the NOC pipeline: 12 RED stub tests, noc_mapping_db fixture, and three pinned production dependencies (sqlite-vec, instructor, ollama) that collect with 0 failures and skip gracefully before Plan 02 lands production code.**

## Performance

- **Duration:** 4 min (219s)
- **Started:** 2026-06-04T17:42:58Z
- **Completed:** 2026-06-04T17:46:37Z
- **Tasks:** 3 of 3 complete
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- **Test infrastructure established before any production code.** `python -m pytest tests/test_noc_pipeline.py -q` collects 12 items and exits 0 with all 12 skipped — zero failures, zero errors. Nyquist rule satisfied: every automated test has a runnable command before implementation begins.
- **`noc_mapping_db` fixture is self-contained.** Creates a tmp SQLite with the full NOC schema (`noc_units`, `noc_elements`, `noc_fts` FTS5, `noc_chunks_vec` FLOAT[768] cosine, `index_metadata`) plus synthetic data (NOC 21232 "Software engineers and designers", TEER 1, Main duties element, fake 768-dim vector, `embedding_model='nomic-embed-text:latest'`). Runs without Ollama — uses inline `sqlite3.connect + sv.load` so it doesn't depend on the `get_noc_connection()` factory that Plan 02 will create.
- **`env_with_db` is now the canonical env-var shim.** Monkeypatches all six required env vars (`DB_PATH`, `PROJECT_ROOT`, `NOC_DB_PATH`, `OLLAMA_BASE_URL`, `OLLAMA_GENERATION_MODEL`, `OLLAMA_EMBED_MODEL`) in one place so any new test can opt into the full v2 + NOC pipeline env surface by depending on `env_with_db`.
- **Three production dependencies pinned at exact versions** (`sqlite-vec==0.1.9`, `instructor==1.15.1`, `ollama==0.6.1`). Subsequent plans can `pip install -r requirements.txt` reproducibly.
- **Zero regressions on prior v2 backend tests.** Full suite `python -m pytest tests/ -q` shows 27 passed + 12 skipped (39 total). Phase 10 (10), 11 (8), 12 (9) — all green.

## Task Commits

Each task was committed atomically:

1. **Task 1: Pin new dependencies in requirements.txt** - `568e38e` (feat)
2. **Task 2: Add noc_mapping_db fixture and update env_with_db in conftest.py** - `3f404e5` (feat)
3. **Task 3: Create test_noc_pipeline.py with 12 RED stubs** - `9fb4fc6` (feat)

**Plan metadata:** (committed in final docs commit below)

## Files Created/Modified

- `v2/backend/requirements.txt` — Added 3 new pinned deps (sqlite-vec, instructor, ollama). 7 → 10 lines.
- `v2/backend/tests/conftest.py` — Updated `env_with_db` to monkeypatch 4 new env vars (NOC_DB_PATH, OLLAMA_BASE_URL, OLLAMA_GENERATION_MODEL, OLLAMA_EMBED_MODEL). Appended new `noc_mapping_db` fixture (~107 lines) creating NOC schema + synthetic 768-dim data without Ollama.
- `v2/backend/tests/test_noc_pipeline.py` — 12 RED stub tests (331 lines). Coverage: 7 NOC-01 (pipeline + guardrails), 2 API-04 (HTTP), 3 NOC-02 (Pydantic schema).

## Decisions Made

- **Pinned exact versions for all three new deps.** Rationale: v1.0 hit a content-hash drift bug because embed-model versions changed silently. Pinned `==0.1.9 / 1.15.1 / 0.6.1` so the Wave 1/2/3 plans get reproducible installs.
- **vec0 at FLOAT[768] not FLOAT[1024].** Rationale: `nomic-embed-text` output is 768-dim; using 1024 would force the embed model to be swapped mid-pipeline. The v1.0 conftest had a comment about this drift.
- **Explicit `noc_db_path` parameter, not implicit env var.** Rationale: Plan 03's `map_work_description(work_description, noc_db_path)` signature lets tests pass the temp path directly, avoiding Settings-coupling in the test body. The `NOC_DB_PATH` env var is still monkeypatched via `env_with_db` so `Settings` construction in production code paths works.
- **Inline sqlite-vec loading in the fixture, not a helper.** Rationale: Plan 02 creates `get_noc_connection()` with its own vec-loading logic. Keeping the fixture independent prevents the Wave 0 gate from depending on a factory that doesn't exist yet.
- **12 stubs (exceeded the 10-stub minimum).** Rationale: added 2 extra schema tests (TestNOCCandidateSchema::{test_noc_candidate_schema, test_teer_is_integer, test_ranks_are_sequential}) to lock down Pydantic validators that are easy to drift.
- **Used `pytest.importorskip` inside the test body, not at module level.** Rationale: module-level importorskip fails at collection time, which would mask the Wave 0 success criterion that the file *collects* without errors. Body-level skip means collection succeeds and the test reports `skipped`.

## Deviations from Plan

None - plan executed exactly as written.

**Total deviations:** 0

## Issues Encountered

- **AsyncIO deprecation warning at pytest startup.** Pytest-asyncio 0.24 emits `PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.` Not an error — pre-existing on all v2 backend test runs (also visible in Phase 10–12 runs). Not in scope to fix per deviation scope boundary; will be resolved when pytest-asyncio is upgraded or the config option is explicitly set in a future housekeeping plan.

## Stub Tracking

All 12 tests in `test_noc_pipeline.py` are stub-only at Wave 0:

| Stub | File | Line | Reason |
|------|------|------|--------|
| `test_fts5_query_rewriting_strips_stop_words` | test_noc_pipeline.py | 56 | `app.services.noc_mapper` not yet created (Plan 02) |
| `test_fts5_query_empty_after_filtering_raises` | test_noc_pipeline.py | 72 | `app.services.noc_mapper` not yet created |
| `test_fts5_stage_returns_noc_codes` | test_noc_pipeline.py | 93 | `app.services.noc_mapper` not yet created |
| `test_stage2_calls_embed_model` | test_noc_pipeline.py | 113 | `app.services.noc_mapper` not yet created |
| `test_pipeline_returns_candidates` | test_noc_pipeline.py | 133 | `app.services.noc_mapper` not yet created |
| `test_verbatim_guardrail_strips_fabricated` | test_noc_pipeline.py | 158 | `app.services.noc_mapper` + `app.ai.noc_ranking` not yet created |
| `test_verbatim_guardrail_raises_when_all_stripped` | test_noc_pipeline.py | 200 | same |
| `test_api_route_200` | test_noc_pipeline.py | 236 | `app.api.noc_mapping` not yet created (Plan 04) |
| `test_empty_fts_result_raises_422` | test_noc_pipeline.py | 261 | same |
| `TestNOCCandidateSchema::test_noc_candidate_schema` | test_noc_pipeline.py | 287 | `app.ai.noc_ranking` not yet created (Plan 02) |
| `TestNOCCandidateSchema::test_teer_is_integer` | test_noc_pipeline.py | 303 | same |
| `TestNOCCandidateSchema::test_ranks_are_sequential` | test_noc_pipeline.py | 318 | same |

All 12 stubs are tracked for Plans 02–04 to convert RED → GREEN. Wave 0 success criterion is met: 0 failures, 12 skipped.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| (none) | — | No new threat surface introduced. Test fixture uses `tmp_path` (mitigation T-14-W0-01) and standard env-var monkeypatching (T-14-W0-02 accepted). |

## User Setup Required

None - no external service configuration required. The new dependencies in `requirements.txt` are local Python packages (no API keys, no cloud config). Ollama itself is optional — the tests skip without it.

## Next Phase Readiness

**Plan 02 (NOC-02 — NOCRankingResult Pydantic schema + get_noc_connection factory)** is unblocked. It can:
- Run `pip install -r requirements.txt` to install sqlite-vec + instructor + ollama
- Create `app/ai/noc_ranking.py` with `NOCCandidate` and `NOCRankingResult` models — 3 schema stubs will go GREEN immediately
- Add `get_noc_connection()` to `app/db.py` — the existing `noc_mapping_db` fixture is the reference for what it should return

**Plan 03 (NOC-01 — map_work_description pipeline)** is unblocked. It can:
- Create `app/services/noc_mapper.py` with `_fts_query_from_text`, `map_work_description`, `_check_verbatim_fidelity` — 7 NOC-01 stubs will go GREEN
- The fixture already provides the FTS5 + vec0 + index_metadata setup it needs

**Plan 04 (API-04 — POST /api/noc/map endpoint)** is unblocked. It can:
- Create `app/api/noc_mapping.py` and wire it into `app/main.py` — 2 API-04 stubs will go GREEN
- The test mocks the service-layer `map_work_description` so Plan 04 only needs the routing + 422-handling glue

No blockers. No decisions needed from user.

---

*Phase: 14-noc-pipeline*
*Completed: 2026-06-04*

## Self-Check: PASSED

All claimed deliverables verified:

- `v2/backend/requirements.txt` — exists, 10 lines, 3 new pinned deps confirmed
- `v2/backend/tests/conftest.py` — exists, `noc_mapping_db` fixture + updated `env_with_db` confirmed
- `v2/backend/tests/test_noc_pipeline.py` — exists, 12 stubs, all skip cleanly
- Commit `568e38e` (Task 1: requirements.txt) — found in git log
- Commit `3f404e5` (Task 2: conftest.py) — found in git log
- Commit `9fb4fc6` (Task 3: test_noc_pipeline.py) — found in git log
- `python -m pytest tests/test_noc_pipeline.py -q` — exits 0, 12 skipped, 0 failed
- `python -m pytest tests/ -q` — 27 passed, 12 skipped, 0 failed (no regressions)
