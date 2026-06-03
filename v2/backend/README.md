# JD Builder v2.0 — Backend

FastAPI + Pydantic v2 + SQLite.

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Test

```bash
python -m pytest tests/ -x -q
```

## Environment

See `.env.example`. Required vars:
- `DB_PATH` — SQLite file path (default: `./data/jd_builder.db`)
- `PROJECT_ROOT` — Project root for path validation

The parent directory of `DB_PATH` is created automatically on first
startup if missing.

## API

- `GET /api/health` — liveness probe (Phase 10)
- `POST /api/wd` — create WD (Phase 18)
- `GET /api/wd/{id}` — load WD (Phase 18)
- `PATCH /api/wd/{id}` — update draft (Phase 18)
- `GET /api/work-types` — canonical work-types (Phase 18)
- `GET /api/duties` — 7 suggested duties (Phase 18)
- `GET /api/quals/default` — EC-05 default quals (Phase 18)
- `POST /api/classify` — classification service (Phase 18)
