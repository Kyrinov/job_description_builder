---
phase: 10-project-scaffold
plan: 01
subsystem: backend
tags: [scaffold, wave-0, tdd-red, fastapi, pydantic, sqlite, pytest]
requires: []
provides:
  - "v2/backend/ directory tree (FastAPI + Pydantic v2 + SQLite workspace)"
  - "Pinned dependency surface (FastAPI 0.128.8, Pydantic 2.12.5, pydantic-settings 2.6.1, httpx 0.27.2, pytest 8.3.4, pytest-asyncio 0.24.0)"
  - "Wave 0 test contract — 10 RED-state items across 4 files"
  - "Test fixture scaffolding (tmp_db_path, env_with_db, test_app, client)"
affects: [10-02, 10-03, 10-04]
tech-stack:
  added:
    - fastapi==0.128.8
    - uvicorn[standard]==0.40.0
    - pydantic==2.12.5
    - pydantic-settings==2.6.1
    - httpx==0.27.2
    - pytest==8.3.4
    - pytest-asyncio==0.24.0
  patterns:
    - "pydantic-settings env-driven Settings (DB_PATH, PROJECT_ROOT)"
    - "ASGITransport-based in-process httpx.AsyncClient (no live server)"
    - "pytest.importorskip as Wave 0 contract marker for not-yet-implemented app.main"
key-files:
  created:
    - v2/backend/pyproject.toml
    - v2/backend/requirements.txt
    - v2/backend/.env.example
    - v2/backend/.gitignore
    - v2/backend/tests/__init__.py
    - v2/backend/tests/conftest.py
    - v2/backend/tests/test_health.py
    - v2/backend/tests/test_config.py
    - v2/backend/tests/test_db.py
    - v2/backend/tests/test_models.py
  modified: []
decisions:
  - "Use pydantic-settings 2.6.1 (per plan) not 2.14.1 (v1.0 pin) — plan-specified exact pin"
  - "Use pytest.importorskip in test_app fixture per plan's recommended pattern — causes 1 SKIP (test_health) in Wave 0; the skip is the contract marker, not a failure"
  - "env_with_db derives PROJECT_ROOT from tmp_db_path's parent (os.path.dirname) rather than tmp_path directly — fixed bug where original draft referenced tmp_path inside the fixture body, causing NameError on fixture setup"
  - "Stick to plan's verbatim pyproject.toml (no asyncio_default_fixture_loop_scope pin) — out of plan scope, deprecation warning only"
metrics:
  duration: 250s
  completed_date: "2026-06-03T18:43:53Z"
  task_count: 2
  file_count: 10
---

# Phase 10 Plan 01: Backend Wave 0 Scaffold + Test Stubs Summary

**One-liner:** Established the v2/backend/ project tree with pinned FastAPI 0.128.x / Pydantic 2.12.x / pydantic-settings / pytest deps, and 10 RED-state test stubs across 4 files that Plan 02 will turn GREEN by implementing app.config / app.db / app.models / app.main.

## What Was Built

### Task 1 — Project config (4 files, commit `4c9e5c0`)

- **`v2/backend/pyproject.toml`** — minimal pytest config (`testpaths = ["tests"]`, `asyncio_mode = "auto"`, `addopts = "-v --tb=short"`); build-system stub for future packaging.
- **`v2/backend/requirements.txt`** — 7 pinned deps, no v1.0 LLM/ingest carryover (no ollama, instructor, sqlite-vec, duckdb, polars, docxtpl, weasyprint).
- **`v2/backend/.env.example`** — documents `DB_PATH=./data/jd_builder.db` (under v2/backend/data/) and `PROJECT_ROOT=../..` as the Settings contract.
- **`v2/backend/.gitignore`** — excludes venv, pyc, .env, data/, caches, build artifacts.

### Task 2 — Wave 0 test stubs (6 files, commit `1f9966e`)

- **`tests/__init__.py`** — empty (so pytest discovers tests as a package).
- **`tests/conftest.py`** — 4 fixtures: `tmp_db_path`, `env_with_db` (sets `DB_PATH` + `PROJECT_ROOT`), `test_app` (uses `pytest.importorskip("app.main")` per plan recommendation), `client` (httpx AsyncClient + ASGITransport).
- **`tests/test_health.py`** — 1 stub: `test_health_returns_200` (GET /api/health → 200 + `{"status": "ok"}`).
- **`tests/test_config.py`** — 2 stubs: `test_settings_loads_defaults`, `test_missing_db_path_raises`.
- **`tests/test_db.py`** — 2 stubs: `test_create_schema_creates_work_descriptions`, `test_create_schema_is_idempotent`.
- **`tests/test_models.py`** — 5 stubs: one per Pydantic model (WorkDescription, DraftDuty, Classification, JESFactor, QualificationStandard).

## Test State (Wave 0 RED contract established)

| Metric | Value |
|--------|-------|
| `pytest --collect-only` | **10 items collected** across 4 files (test_config=2, test_db=2, test_health=1, test_models=5) |
| `pytest` execution | **9 failed, 1 skipped** |
| Reason | All 9 failures: `ModuleNotFoundError: No module named 'app'`. The 1 skip (test_health) is the `pytest.importorskip("app.main")` contract marker per plan. |

```
$ pytest tests/ -q
FAILED tests/test_config.py::test_settings_loads_defaults        - ModuleNotFoundError: No module named 'app'
FAILED tests/test_config.py::test_missing_db_path_raises         - ModuleNotFoundError: No module named 'app'
FAILED tests/test_db.py::test_create_schema_creates_work_*       - ModuleNotFoundError: No module named 'app'
FAILED tests/test_db.py::test_create_schema_is_idempotent        - ModuleNotFoundError: No module named 'app'
FAILED tests/test_models.py::test_work_description_instantiation - ModuleNotFoundError: No module named 'app'
FAILED tests/test_models.py::test_draft_duty_instantiation       - ModuleNotFoundError: No module named 'app'
FAILED tests/test_models.py::test_classification_instantiation   - ModuleNotFoundError: No module named 'app'
FAILED tests/test_models.py::test_jes_factor_instantiation       - ModuleNotFoundError: No module named 'app'
FAILED tests/test_models.py::test_qualification_standard_instantiation - ModuleNotFoundError: No module named 'app'
SKIPPED tests/test_health.py::test_health_returns_200 - could not import 'app.main'
9 failed, 1 skipped in 0.08s
```

## Verification — Key Links Confirmed

| Check | Result |
|-------|--------|
| `pyproject.toml` contains `asyncio_mode` | ✓ (1 occurrence) |
| `pyproject.toml` contains `testpaths = ["tests"]` | ✓ |
| `requirements.txt` pins `fastapi==0.128.8` | ✓ (exact pin) |
| `requirements.txt` pins `pydantic==2.12.5` | ✓ (exact pin) |
| `requirements.txt` pins `pydantic-settings==2.6.1` | ✓ (exact pin, per plan) |
| `requirements.txt` pins `httpx==0.27.2` | ✓ (exact pin) |
| `requirements.txt` pins `pytest==8.3.4`, `pytest-asyncio==0.24.0` | ✓ (exact pins) |
| `.env.example` documents `DB_PATH=./data/jd_builder.db` | ✓ |
| `tests/conftest.py` contains `def test_app` and `ASGITransport` | ✓ |
| `tests/test_health.py` contains `test_health_returns_200` | ✓ |
| `tests/test_config.py` contains `test_settings_loads_defaults` | ✓ |
| `tests/test_db.py` contains `test_create_schema_idempotent` | ✓ (named `test_create_schema_is_idempotent` per plan) |
| `tests/test_models.py` contains `test_work_description_instantiation` | ✓ |
| `pip install -r requirements.txt` succeeds on ARM64 | ✓ (pre-existing venv conflict from docling-core/google-genai is unrelated; our 7 pins install cleanly) |
| `pytest --collect-only` shows 10 collected items | ✓ |
| `pytest` shows 9 fail + 1 skip (Wave 0 RED state) | ✓ |
| No v1.0 files (app/, data/, scripts/) modified | ✓ (git status confirms only v2/ additions) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `NameError: name 'tmp_path'` in env_with_db fixture**
- **Found during:** Task 2 verification (running `pytest tests/`)
- **Issue:** The plan's conftest.py draft (line 27) referenced `tmp_path` inside the `env_with_db` fixture body. `tmp_path` is a pytest built-in fixture, but the fixture only takes `tmp_db_path` and `monkeypatch` as arguments — so `tmp_path` was not in scope and triggered `NameError: name 'tmp_path' is not defined` at fixture setup for every test using `env_with_db`. This masked the intended RED state: tests would error in fixture setup, not in the test body with `ModuleNotFoundError`.
- **Fix:** Compute PROJECT_ROOT from `tmp_db_path`'s parent directory: `parent = os.path.dirname(tmp_db_path) or "."`, then `monkeypatch.setenv("PROJECT_ROOT", parent)`.
- **Files modified:** `v2/backend/tests/conftest.py`
- **Commit:** `1f9966e`
- **Why this is Rule 1, not a behavior change:** The plan's intent was "set PROJECT_ROOT to a valid path" (the .env.example documents `PROJECT_ROOT=../..`). Using tmp_db_path's parent achieves that — and matches the plan's semantic — without breaking the RED contract.

**2. [Rule 2 - Critical] Wave 0 contract has 1 SKIP, not all-FAIL**
- **Found during:** Task 2 verification
- **Issue:** The orchestrator's success criteria state "All 10 tests fail or error (Wave 0 RED state — expected, Plan 02 makes them pass)". However, the plan's recommended Wave 0 pattern (`pytest.importorskip("app.main")` in the `test_app` fixture) causes the 1 test that goes through that fixture (`test_health_returns_200`) to be SKIPPED rather than failed. The other 9 tests fail with `ModuleNotFoundError: No module named 'app'`. The skip is a contract marker, not a failure — the skip reason literally says "could not import 'app.main'", and once Plan 02 implements that module, the import succeeds and the test runs.
- **Decision:** Kept the plan's recommended `pytest.importorskip` pattern (the plan said "Recommended: use `pytest.importorskip`" explicitly). Documented the 1-skip behavior here so the verifier and Plan 02 executor understand why `pytest tests/` shows `9 failed, 1 skipped` instead of `10 failed`.
- **Files modified:** none (kept as plan wrote)
- **Commit:** `1f9966e`
- **Why this is Rule 2, not Rule 4:** No architectural change — the SKIP is the correct Wave 0 mechanism per the plan itself. The behavior on the ground matches the plan's recommendation; only the success criteria language ("fail or error") is slightly tighter than what the plan's own code produces.

### Pre-existing Modifications (NOT caused by this plan)

The following files were already modified in the working tree before this plan started and were not touched by 10-01:

- `.planning/PROJECT.md`, `.planning/STATE.md`, `.planning/config.json` — pre-existing edits
- `docs/JD_Builder_System_Overview.docx` — pre-existing edit
- `templates/docx/work_description_template.docx` — pre-existing edit

Plan 10-01 only adds new files under `v2/backend/`. No v1.0 files (`app/`, `data/`, `scripts/`) were modified.

## What Plan 02 Will Do

With this Wave 0 scaffold in place, Plan 02 (app.config + app.db + app.models + app.main) runs against a known-good failing-test contract:

1. Implement `app/config.py:Settings` (pydantic-settings, `db_path` + `project_root` env-driven) — turns test_config.py's 2 failures GREEN.
2. Implement `app/db.py:get_connection` + `app/db.py:create_schema` (SQLite DDL for `work_descriptions` + `audit_log`) — turns test_db.py's 2 failures GREEN.
3. Implement `app/models/{work_description,draft_duty,classification,jes_factor,qualification_standard}.py` (5 Pydantic v2 models) and re-export from `app/models/__init__.py` — turns test_models.py's 5 failures GREEN.
4. Implement `app/main.py` (FastAPI app + lifespan + `/api/health` returning `{"status": "ok"}`) — unblocks `pytest.importorskip("app.main")`, turns test_health.py's 1 skip → 1 pass.

After Plan 02: `pytest tests/` should show 10 passed.

## Commits

| Hash | Type | Message |
|------|------|---------|
| `4c9e5c0` | feat | backend project scaffold — pyproject, requirements, env, gitignore |
| `1f9966e` | feat | Wave 0 test stubs — 4 test files, 10 RED-state items |

## Self-Check: PASSED

All 11 expected files present (10 v2/backend/ files + SUMMARY.md). Both commit hashes (`4c9e5c0`, `1f9966e`) verified in git log.
