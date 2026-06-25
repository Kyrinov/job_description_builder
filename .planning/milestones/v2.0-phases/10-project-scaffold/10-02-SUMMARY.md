---
phase: 10-project-scaffold
plan: 02
subsystem: backend
tags: [pydantic-v2, pydantic-settings, sqlite, fastapi-foundation, tdd-green, model-layer]

# Dependency graph
requires:
  - phase: 10-project-scaffold
    plan: 01
    provides: "v2/backend/ tree + Wave 0 test stubs (4 test files, 10 RED-state items)"
provides:
  - "app/config.py — pydantic-settings Settings class (db_path, project_root, required fields with min_length=1 validation)"
  - "app/db.py — get_connection factory (check_same_thread=False, Row factory, FK pragma) + create_schema with work_descriptions and audit_log DDL (idempotent)"
  - "app/models/{work_description, draft_duty, classification, jes_factor, qualification_standard}.py — 5 Pydantic v2 models"
  - "app/models/__init__.py — re-exports all 5 models including JESFactor (re-export contract)"
affects: [10-04, 11, 18, 19]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pydantic-settings BaseSettings with SettingsConfigDict (env_file + case_sensitive=False + extra=ignore)"
    - "SQLite connection factory with check_same_thread=False (FastAPI thread safety) + Row factory + foreign_keys PRAGMA"
    - "Idempotent schema creation via CREATE TABLE IF NOT EXISTS in executescript"
    - "Pydantic v2 ConfigDict(extra='ignore') for all domain models — forward-compatible with future field additions"
    - "Co-located JESFactor + Classification (one only makes sense as the other) + re-export shim for dedicated import path"
    - "Field(... min_length=1) for required string fields (rejects empty strings with ValidationError)"

key-files:
  created:
    - v2/backend/app/__init__.py
    - v2/backend/app/config.py
    - v2/backend/app/db.py
    - v2/backend/app/models/__init__.py
    - v2/backend/app/models/work_description.py
    - v2/backend/app/models/draft_duty.py
    - v2/backend/app/models/classification.py
    - v2/backend/app/models/jes_factor.py
    - v2/backend/app/models/qualification_standard.py
  modified: []

key-decisions:
  - "Use Field(..., min_length=1) on db_path and project_root — pydantic v2 does NOT reject empty strings by default for `str`; the test contract `test_missing_db_path_raises` requires it"
  - "Co-locate JESFactor with Classification (one only makes sense as part of the other) + add a re-export shim in app/models/jes_factor.py — supports the `from app.models.jes_factor import JESFactor` import path that the 10-01 conftest acknowledges"
  - "Use ConfigDict(extra='ignore') on all domain models — forward-compatible: future schema additions (e.g., a new optional field on Classification) won't break stored JSON documents in work_descriptions.data"
  - "Use Foreign Keys PRAGMA = ON at connection level even though v2.0 has no FK constraints yet — future-proofs the schema for Phase 18 service-layer work that may add WD ↔ audit_log relations"
  - "Add `parent.mkdir(parents=True, exist_ok=True)` to get_connection() — the plan's must_haves specify that DB_PATH's parent must be created automatically on startup"

requirements-completed: [API-01, API-05]

# Metrics
duration: 150s
completed: 2026-06-03T18:58:24Z
tasks: 2
files: 9
test_state:
  config_passed: 2
  db_passed: 2
  models_passed: 5
  health_skipped: 1
  health_failed: 0
  total: "9 passed, 1 skipped (test_health awaiting Plan 03 / Plan 04)"
---

# Phase 10 Plan 02: Backend Foundation + 5 Pydantic Models Summary

**Settings (pydantic-settings) + SQLite schema DDL + 5 Pydantic v2 models — turns 9 of 10 Wave 0 RED tests GREEN (test_health remains skipped for Plan 04)**

## Performance

- **Duration:** 2 min 30 s (150 s)
- **Started:** 2026-06-03T18:55:54Z
- **Completed:** 2026-06-03T18:58:24Z
- **Tasks:** 2
- **Files created:** 9
- **Tests passing:** 9 passed + 1 skipped (was 9 failed + 1 skipped)

## Accomplishments

- **`app/config.py`** — `Settings(BaseSettings)` with required `db_path` + `project_root` (Field `min_length=1`); reads `DB_PATH` + `PROJECT_ROOT` from env (or `.env` file). Module-level `get_settings()` singleton accessor.
- **`app/db.py`** — `get_connection()` factory (creates parent dir, `check_same_thread=False`, Row factory, FK PRAGMA ON). `create_schema()` runs the SCHEMA_DDL via `executescript` + `commit`. `work_descriptions` and `audit_log` tables + 3 indexes, all `IF NOT EXISTS` (idempotent).
- **`app/models/work_description.py`** — WD entity with 16 fields: `id, title, record, answers, step_index, draft, reviewing, editing_return, classification, duties, qualification, drf_id, schema_version, created_at, last_modified`. Required: `id, created_at, last_modified`. All others default.
- **`app/models/draft_duty.py`** — Per-duty: `id, text, plain_trigger, source` (Literal `suggested`|`advisor`), `source_index, refined_at`.
- **`app/models/classification.py`** — Co-located `JESFactor` (4 categories × degrees 1-7) and `Classification` (work_type Literal EC|FI|IT|AS|EN + 3 scope ints 1-3 + resolved code/group/level/points/factors/rationale/confidence).
- **`app/models/jes_factor.py`** — Re-export shim `from .classification import JESFactor`.
- **`app/models/qualification_standard.py`** — `education, experience, source` (Literal `EC-05 default`|`advisor-edited`), `last_modified`.
- **`app/models/__init__.py`** — Re-exports all 5 models. `__all__ = [WorkDescription, DraftDuty, Classification, JESFactor, QualificationStandard]`.

## Test State Transition (Wave 0 RED → Plan 02 GREEN)

| Test file | Before Plan 02 | After Plan 02 |
|-----------|----------------|---------------|
| `test_config.py` (2 tests) | 2 FAILED (ModuleNotFoundError) | **2 PASSED** |
| `test_db.py` (2 tests) | 2 FAILED (ModuleNotFoundError) | **2 PASSED** |
| `test_models.py` (5 tests) | 5 FAILED (ModuleNotFoundError) | **5 PASSED** |
| `test_health.py` (1 test) | 1 SKIPPED (`pytest.importorskip("app.main")`) | 1 SKIPPED (awaiting Plan 04) |
| **Total** | 9 failed + 1 skipped | **9 passed + 1 skipped** |

```
$ cd v2/backend && python -m pytest tests/ -x -q
tests/test_config.py ..                  [ 20%]
tests/test_db.py ..                      [ 40%]
tests/test_health.py s                   [ 50%]
tests/test_models.py .....               [100%]
========================= 9 passed, 1 skipped in 0.23s =========================
```

## Key Links Verified

| Contract | Verification |
|----------|--------------|
| `class Settings(BaseSettings)` in app/config.py | ✓ line 14 |
| `db_path` and `project_root` as required fields | ✓ both are `Field(..., min_length=1)` |
| `get_connection` uses `sqlite3.connect` with `check_same_thread=False` | ✓ line 27 |
| `create_schema` is idempotent | ✓ all DDL uses `IF NOT EXISTS`; called twice in tests + smoke test, no error |
| `work_descriptions` has columns: id, title, data, schema_version, created_at, last_modified | ✓ verified via `PRAGMA table_info` |
| `audit_log` has columns: id, wd_id, event, actor, detail, created_at | ✓ verified via `PRAGMA table_info` |
| `from app.models import JESFactor` works | ✓ `app.models.classification.JESFactor` |
| `from app.models.jes_factor import JESFactor` works (shim) | ✓ identity `A is B is C` (same class object) |
| `from app.config import Settings` raises on `db_path=""` | ✓ `pydantic.ValidationError: String should have at least 1 character` |
| v1.0 `app/`, `data/`, `scripts/` unchanged | ✓ `git diff --stat app/ data/ scripts/` returns empty |

## Task Commits

Each task committed atomically:

1. **Task 1: Settings (app/config.py) + connection factory + schema (app/db.py)** — `ae9ef97` (feat)
2. **Task 2: 5 Pydantic v2 models (app/models/*)** — `1d6b761` (feat)

Plan metadata: see below for docs commit.

## Files Created

- `v2/backend/app/__init__.py` — empty package marker
- `v2/backend/app/config.py` — pydantic-settings `Settings` + `get_settings()` singleton
- `v2/backend/app/db.py` — `get_connection()` + `SCHEMA_DDL` + `create_schema()`
- `v2/backend/app/models/__init__.py` — re-exports the 5 models
- `v2/backend/app/models/work_description.py` — `WorkDescription` (16 fields, `populate_by_name=True`)
- `v2/backend/app/models/draft_duty.py` — `DraftDuty` (Literal source)
- `v2/backend/app/models/classification.py` — `Classification` + co-located `JESFactor`
- `v2/backend/app/models/jes_factor.py` — re-export shim (`from .classification import JESFactor`)
- `v2/backend/app/models/qualification_standard.py` — `QualificationStandard` (Literal source)

## Decisions Made

- **Field `min_length=1` on required strings** (auto-fix, see Deviations). pydantic v2 default `str` validation accepts `""`; the test contract `test_missing_db_path_raises` requires rejection, so `Field(..., min_length=1)` is the standard pydantic v2 pattern.
- **JESFactor co-location + shim**: The plan's 10-01 conftest and the test_models.py stubs all import `from app.models import JESFactor`. Since JESFactor only makes sense as part of a Classification (it's only rendered for EC groups), it's defined in `classification.py` and re-exported from `__init__.py` AND a dedicated `jes_factor.py` shim — satisfying both the contract and architectural intent.
- **`ConfigDict(extra="ignore")` on all domain models**: Stored JSON in `work_descriptions.data` may have extra fields from earlier schema versions or future client additions. `extra="ignore"` ensures forward compatibility without silent data loss in the canonical model.
- **`populate_by_name=True` on `WorkDescription`**: Lets clients send either `drf_id` or `drfId` (camelCase) and the aliasing still works. Phase 11 (frontend) will use camelCase; Phase 18 (API) will use snake_case.
- **`Path(db_path).parent.mkdir(parents=True, exist_ok=True)` in `get_connection`**: The plan's must_haves specify "DB_PATH's parent must be created automatically on startup" — this is a small but important detail for the first-run UX when the user hasn't yet created `v2/backend/data/`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Critical] Added `min_length=1` constraint on Settings fields**
- **Found during:** Task 1 verification (running `pytest tests/test_config.py`)
- **Issue:** The plan's draft `Settings` class declares `db_path: str` and `project_root: str` without default values, which makes them "required" by pydantic. However, pydantic v2's default `str` validator accepts the empty string `""` as a valid value. The test `test_missing_db_path_raises` explicitly passes `db_path=""` and expects `pytest.raises(Exception)`. Without additional constraint, the test fails with `Failed: DID NOT RAISE <class 'Exception'>`.
- **Fix:** Imported `Field` from pydantic and changed the two field declarations to `db_path: str = Field(..., min_length=1)` and `project_root: str = Field(..., min_length=1)`. The `...` (Ellipsis) preserves the "no default" behavior (required field), and `min_length=1` rejects empty strings with `pydantic.ValidationError: String should have at least 1 character`.
- **Files modified:** `v2/backend/app/config.py`
- **Verification:** `pytest tests/test_config.py tests/test_db.py` → 4 passed; `Settings(_env_file=None, db_path="")` now raises `pydantic.ValidationError`.
- **Committed in:** `ae9ef97` (Task 1 commit)
- **Why this is Rule 2 (missing critical functionality), not a behavior change:** The plan's test contract explicitly requires `Settings(db_path="")` to raise. The plan's "no default" annotation was insufficient under pydantic v2 defaults — adding `min_length=1` is the standard pydantic v2 way to express "non-empty required string" and matches the contract's intent. This is the smallest possible deviation that satisfies the test without changing the API surface (callers still pass `db_path` positionally or by keyword).

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Minimal. The deviation is necessary for the test contract to pass and uses the standard pydantic v2 idiom. No scope creep.

## Issues Encountered

None — implementation followed plan verbatim aside from the `min_length=1` auto-fix.

## User Setup Required

None — no external service configuration required for this plan. The Settings class reads from env (or `.env` file) which is set up by Plan 01's `.env.example` (with `DB_PATH=./data/jd_builder.db` and `PROJECT_ROOT=../..`).

## Next Phase Readiness

**Ready for Plan 10-03 (or 10-04 depending on wave ordering):**
- `app.config`, `app.db`, `app.models` are all importable
- 9 of 10 tests pass; the 1 skip (`test_health_returns_200`) is the `pytest.importorskip("app.main")` contract marker — once Plan 03/04 implements `app.main` (FastAPI instance) and `GET /api/health`, that test will turn GREEN
- Phase 11 (Frontend Port), Phase 18 (Backend API Service), and Phase 19 (DOCX Export) all import from `app.config`, `app.db`, and `app.models`

**For the orchestrator:**
- `app.config.Settings` and `app.db.get_connection` are now the canonical config + DB entry points
- The 5 Pydantic models are the canonical data shape — later phases should `from app.models import X` (not redefine locally)
- `work_descriptions.data` will store the JSON-serialized `WorkDescription.model_dump_json()` from Phase 18 onward

---

*Phase: 10-project-scaffold*
*Plan: 02*
*Completed: 2026-06-03T18:58:24Z*
*Commits: `ae9ef97` (Task 1), `1d6b761` (Task 2)*

## Self-Check: PASSED

- All 9 expected files present (8 app/ + 1 SUMMARY.md)
- Both commit hashes (`ae9ef97` Task 1, `1d6b761` Task 2) verified in git log
- `pytest tests/ -x -q` → 9 passed, 1 skipped (test_health awaiting Plan 04)
- v1.0 `app/`, `data/`, `scripts/` untouched (`git diff --stat` empty)
