# JD Builder v2.0

Conversational React 18 SPA + FastAPI JSON API for building legally
defensible Government of Canada work descriptions.

## Phase 10 status

Scaffold complete: FastAPI + Pydantic v2 + SQLite + Vite + React 18.
Conversational UX (Phase 11) and API endpoints (Phase 18) are not yet
wired. The placeholder SPA shows "JD Builder — v2.0 scaffold".

## Quick start (development)

Two terminals — backend and frontend.

**Terminal 1 — backend:**
```bash
cd v2/backend
pip install -r requirements.txt
cp .env.example .env  # Optional — defaults are fine
uvicorn app.main:app --reload --port 8000
```

The backend creates `v2/backend/data/jd_builder.db` on first startup
and serves `/api/*` on http://localhost:8000.

**Terminal 2 — frontend:**
```bash
cd v2/frontend
npm install
npm run dev
```

The frontend serves the React 18 SPA on http://localhost:5173.
`/api/*` requests are proxied to the backend on :8000.

## Verify the scaffold

```bash
./scripts/verify.sh
```

Runs the 5 Phase 10 success criteria checks and exits 0 on pass.

## Layout

```
v2/
├── backend/     # FastAPI + Pydantic v2 + SQLite
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── models/
│   │   └── api/
│   ├── tests/
│   ├── data/    # SQLite file (gitignored)
│   └── requirements.txt
├── frontend/    # Vite + React 18 SPA
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── scripts/
│   ├── dev.sh
│   └── verify.sh
└── README.md    # this file
```

## Phase 10 success criteria

1. `uvicorn app.main:app` starts and `GET /api/health` returns 200
2. `npm run dev` starts Vite and the SPA loads at localhost:5173
3. Vite proxies `/api/*` to FastAPI on :8000
4. SQLite single-file DB at `DB_PATH` with `work_descriptions` + `audit_log`
5. Pydantic v2 models: `WorkDescription`, `DraftDuty`, `Classification`, `JESFactor`, `QualificationStandard`
