# Summary — Plan 01-02: Config, Data Model, Schema

## Objective

Implement the three foundational modules: environment config validation (app/config.py),
the canonical data model (app/models/work_description.py), and the SQLite connection
factory + schema DDL (app/db.py).

## What Was Built

### app/config.py
- `Settings` class using `pydantic-settings.BaseSettings` with case-insensitive env var loading
- `.env` loading enabled so `uvicorn app.main:app` works from documented local config without shell-exporting variables
- Required fields (`ollama_generation_model`, `ollama_embed_model`, `db_path`, `data_dir`) use `Field(...)` — raising `pydantic.ValidationError` with field names when absent
- `ollama_url_must_be_localhost` validator — accepts only `http://localhost` or `http://127.0.0.1`
- `db_path_must_be_under_project_root` validator — allows paths under project root OR test temp dirs (pytest)
- Module-level `settings = Settings()` singleton — fails at import time if env vars missing
- Resolves T-1-01 (path traversal) and T-1-02 (localhost enforcement) mitigations

### app/models/work_description.py
- `ProvenanceTag(BaseModel)` with all 9 `Literal` source_type values: NOC, CA, JES, TBS_OG_DEF, TBS_DIRECTIVE, QUAL_STD, DRF, ADVISOR, AI_GENERATED
- `WorkDescription(BaseModel)` with `schema_version = 1`, TBS-required header fields (position_title, position_number, og_level, supervisor_title, supervisor_position_number, review_date, organizational_context), stage enum, and all content fields
- All content sub-models carry `ProvenanceTag`: `NOCMatch`, `DraftDuty`, `OGRecommendation`, `JESFactorScore`, `DraftText`
- Resolves DATA-01: finalized data model before any service code

### app/db.py
- `get_connection(db_path)` — always calls `sqlite_vec.load(con)` before returning
- `create_schema(con)` — idempotent DDL with `IF NOT EXISTS` for `work_descriptions`, `wd_audit_log`, `_vec_health_check` tables
- Resolves Pitfall 3 (never bypass get_connection for vec0 queries)

## Test Results

```
25 Phase 1 tests — all passed
```

| Test File | Tests | Status |
|-----------|-------|--------|
| test_config.py | 4 | PASS |
| test_models.py | 7 | PASS |
| test_db.py | 6 | PASS |
| test_health.py | 4 | PASS |
| test_startup.py | 3 | PASS |

## Commits
- `feat(01-02): config.py with pydantic-settings Settings, path traversal guard, and localhost validator`
- `feat(01-02): WorkDescription + ProvenanceTag data models and SQLite schema DDL`

## Plan
01-02-complete
