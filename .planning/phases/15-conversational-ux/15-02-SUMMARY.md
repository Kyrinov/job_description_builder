# Plan 15-02 Summary — Backend WD CRUD routes

## What was built
- `v2/backend/app/api/wd.py` (new): POST /api/wd (201, returns {id}), GET /api/wd/{id} (200 or 404), PATCH /api/wd/{id} (200 or 404; merges fields, updates last_modified). All queries use parameterized form.
- `v2/backend/app/api/__init__.py` (updated): imports + includes `wd.router` in `api_router`.

## Verification
- `python -m pytest tests/test_wd.py -v` → 4/4 PASSED
- `python -m pytest -v` → 43/43 PASSED (39 prior + 4 new test_wd.py)

## Deviations
**Latent test-infra bug fixed in conftest.py**: httpx 0.27.2's `ASGITransport` does NOT trigger FastAPI's `lifespan` event. The 39 prior tests passed without schema creation because none of them touched the `work_descriptions` table. The new `test_wd.py` exposes this bug. Fix: explicitly call `create_schema(get_connection(settings.db_path))` inside the `test_app` fixture after importing `app.main`. This is a 6-line addition that makes schema setup deterministic regardless of whether lifespan is triggered. The fix is also more correct in production: an explicit `create_schema` call is a no-op (idempotent) on a DB that already has the schema.

## API-02 satisfied
- POST /api/wd creates a row, returns 201 + {id}
- GET /api/wd/{id} returns the WorkDescription, 404 if missing
- PATCH /api/wd/{id} merges fields, updates last_modified, 404 if missing

## Impact on subsequent plans
- Plan 04 will wire app.jsx to call these routes on each step commit (first commit POSTs, subsequent PATCH).
