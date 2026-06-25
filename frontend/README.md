# JD Builder v2.0 — Frontend (React 18 SPA + Vite)

## Quick start

```bash
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

The Vite dev server proxies `/api/*` requests to the FastAPI backend
on `http://localhost:8000`. Start the backend in another terminal:

```bash
cd ../backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## What's in this scaffold (Phase 10)

- React 18 + Vite 5 dev server
- Vite proxy `/api` → `http://localhost:8000` (FE-02)
- Placeholder page: "JD Builder — v2.0 scaffold"

## What's NOT in this scaffold

- Conversational UX (6-phase interview) — ported in Phase 11 from
  `Job Description Builder/jd-builder/`
- State management — useState + useMemo only (FE-04); no Redux/Zustand
- localStorage crash-recovery (FE-05) — added in Phase 11
- Brand typography (Hanken Grotesk, Spectral, Spline Sans Mono) — added in Phase 11
