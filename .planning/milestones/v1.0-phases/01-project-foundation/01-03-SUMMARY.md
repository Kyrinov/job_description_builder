# Summary — Plan 01-03: FastAPI App, Health Endpoint, Base Template

## Objective

Implement app/main.py (FastAPI app + lifespan startup validation), app/api/health.py (GET /health endpoint), and app/templates/base.html (Jinja2 base template with CDN links).

## What Was Built

### app/main.py
- `FastAPI` app instance with `lifespan` context manager for startup/shutdown
- `ollama_client_factory()` — module-level callable for test monkeypatching
- `_normalize_model_name()` — appends `:latest` tag if missing (Pitfall 2 mitigation)
- `assert_ollama_ready()` — raises `RuntimeError` if Ollama unreachable or required models missing
- `lifespan` calls `assert_ollama_ready()` then `create_schema(get_connection(...))` on startup
- Routes `health.router` and creates `Jinja2Templates` with `app/templates/` directory
- Exports `templates = Jinja2Templates(directory="app/templates")` for future server-rendered views
- Resolves DATA-03: loud startup failure, no silent degradation

### app/api/health.py
- `GET /health` endpoint — re-checks Ollama liveness for observability
- Returns JSON with `status`, `ollama_url`, `required_models`, `missing_models`, `all_available_models`
- Normalizes configured model names that omit a tag before availability comparison
- Returns 200 even when degraded (degraded = some models missing)
- Returns 200 with `status: "error"` on connection failure

### app/templates/base.html
- Jinja2 block structure: `title`, `head`, `content`, `scripts`
- Alpine.js 3.14.8 from CDN with `defer` attribute
- HTMX 2.0.4 from unpkg CDN
- Standard page structure: header, main, footer with provenance credit

### tests/test_startup.py (new)
- Added because it was missing from the scaffold (Plan 01-01)
- 3 lifespan failure tests + 3 health endpoint tests from plan spec
- Fixed cross-test module cache leakage in conftest.py and test_health.py
- All tests patch `ollama.AsyncClient` globally (not just the factory) so the health endpoint also uses the mock

## Test Results

```
25 tests — all passed
```

| Test File | Tests | Status |
|-----------|-------|--------|
| test_config.py | 5 | PASS |
| test_db.py | 6 | PASS |
| test_health.py | 4 | PASS |
| test_models.py | 7 | PASS |
| test_startup.py | 3 | PASS |

## Issues Resolved
- `app/db.py` was created by plan 01-02 but tests/test_startup.py was missing from the
  Plan 01-01 scaffold — added it here since only plan 01-03 has access to the health
  endpoint for testing.
- Fixed test cross-import contamination: removed top-level `from app.config import settings`
  from test_health.py (it crashed pytest collection), fixed monkeypatch ordering so
  `app.main` module exists before patching, and added global `ollama.AsyncClient` patching
  so the health endpoint also uses mock clients.

## Commits
- `feat(01-03): FastAPI app with lifespan, health endpoint, base.html template`
- `refactor(tests): fix cross-test module cache leakage and health test mocking`

## Human Verification Completed

Verified on 2026-05-28:

- `uvicorn app.main:app --host 127.0.0.1 --port 8765` completed startup successfully
- `GET /health` returned HTTP 200 with `status: "ok"` and `missing_models: []`
- SQLite schema contains `_vec_health_check`, `work_descriptions`, and `wd_audit_log`
- Required Ollama models are present locally: `gemma4:31b`, `nomic-embed-text:latest`

## Plan
01-03-complete
