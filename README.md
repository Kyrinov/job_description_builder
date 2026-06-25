# JD Builder

A DND-first Government of Canada job description builder for HR advisors and
classification specialists. An advisor describes the work in a guided
conversation; the system captures the role, scope, duties, classification and
qualifications, and generates a fully traced work description grounded in NOC,
collective agreements, job evaluation standards, and TBS policy.

Conversational React 18 SPA + FastAPI JSON API. Current milestone: **v4.0 —
Seven-Elements Conversational Architecture** (complete).

## Layout

```
backend/      FastAPI + Pydantic v2 + SQLite JSON API
  app/        main, config, db, api/, services/, models/, data/, ai/
  tests/      pytest suite (184 tests)
  scripts/    docx template build scripts
frontend/     Vite + React 18 SPA (vitest, 87 tests)
scripts/      verify.sh (scaffold check), dev.sh (run both servers)
data/         reference data + noc.db (read-only NOC database, 83 MB)
docs/         design docs, prototype, screenshots
archive/      legacy v1.0 (HTMX MVP) — not part of the live system
.planning/    GSD planning; milestones/ holds archived v1.0–v3.0 phases
```

## Quick start (development)

Two terminals — or use `./scripts/dev.sh` to run both at once.

**Backend** (http://localhost:8000):
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # then adjust paths/models for your machine
uvicorn app.main:app --reload --port 8000
```
Creates `backend/data/jd_builder.db` on first startup and serves `/api/*`.
The NOC pipeline reads `data/noc.db` (set `NOC_DB_PATH` in `.env`) and uses
Ollama locally (Stage 2 embed + Stage 3 generation), or a cloud LLM when
`CLOUD_API_KEY` is set.

**Frontend** (http://localhost:5173):
```bash
cd frontend
npm install
npm run dev
```
`/api/*` is proxied to the backend on :8000.

## Tests & checks

```bash
cd backend && pytest          # 184 backend tests
cd backend && ruff check app  # lint
cd frontend && npm test       # 87 frontend tests
./scripts/verify.sh           # end-to-end scaffold check (boots both + proxy)
```

CI runs the same gates on push/PR — see `.github/workflows/ci.yml`.

## Configuration

`backend/.env` (see `backend/.env.example`):

| Var | Purpose |
|-----|---------|
| `DB_PATH` | Work-descriptions SQLite file (under `backend/data/`) |
| `PROJECT_ROOT` | Repo root (`..` from `backend/`) |
| `NOC_DB_PATH` | Read-only NOC database (`data/noc.db`) |
| `OLLAMA_BASE_URL` / `OLLAMA_GENERATION_MODEL` / `OLLAMA_EMBED_MODEL` | Local LLM + embeddings |
| `CLOUD_API_KEY` / `CLOUD_MODEL` / `CLOUD_BASE_URL` | Optional cloud LLM for Stage 3 generation |
