---
phase: 10-project-scaffold
plan: 04
subsystem: backend+frontend
tags: [fastapi, lifespan, vite-proxy, dev-script, verify-script, scaffold-integration, fe-02, api-01]

# Dependency graph
requires:
  - phase: 10-project-scaffold
    plan: 02
    provides: "app.config.Settings + app.db.get_connection + app.db.create_schema + 5 Pydantic v2 models"
  - phase: 10-project-scaffold
    plan: 03
    provides: "Vite 5 + React 18 SPA + /api proxy to http://localhost:8000"
provides:
  - "v2/backend/app/main.py — FastAPI app factory + asynccontextmanager lifespan that calls get_connection + create_schema on startup"
  - "v2/backend/app/api/__init__.py — APIRouter aggregator including health.router"
  - "v2/backend/app/api/health.py — GET /api/health returns {'status': 'ok'} (turns test_health_returns_200 SKIP → PASS)"
  - "v2/README.md — top-level quick start + Phase 10 success criteria"
  - "v2/backend/README.md — backend-specific run + test + env docs"
  - "v2/scripts/dev.sh — one-shot launcher, starts backend (:8000) + frontend (:5173) concurrently, Ctrl-C tears down both"
  - "v2/scripts/verify.sh — 5-criteria verification (7 checks, all pass, exit 0)"
affects: [11-frontend-port, 12-conversation-ux, 13-document-composition, 14-classification-engine, 15-jes-scoring, 16-duty-management, 17-qualifications, 18-backend-api-service, 19-docx-export]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FastAPI app factory (create_app) + module-level app instance for `uvicorn app.main:app`"
    - "asynccontextmanager lifespan — startup runs get_connection + create_schema + con.close; shutdown is a no-op (sqlite3 closes on GC)"
    - "API prefix mounting — all routers under /api so the Vite proxy is a simple pass-through (no rewrite, no CORS)"
    - "Bash trap cleanup on EXIT — verify.sh kills any leftover uvicorn/vite on entry AND on exit so it is self-contained"
    - "nohup + disown backgrounding in verify.sh — child processes survive the script's bash session and can be killed by PID"

key-files:
  created:
    - v2/backend/app/main.py
    - v2/backend/app/api/__init__.py
    - v2/backend/app/api/health.py
    - v2/README.md
    - v2/backend/README.md
    - v2/scripts/dev.sh
    - v2/scripts/verify.sh

key-decisions:
  - "Mount all FastAPI routes under /api (not /) — Vite proxy is a simple pass-through with no rewrite; eliminates an entire class of CORS/dev-server bugs (PITFALL-10-02)"
  - "Use FastAPI app factory pattern (create_app) + module-level app instance — testable without relying on module-level state, and `uvicorn app.main:app` works out of the box"
  - "Close SQLite connection explicitly after schema creation in lifespan — keeps the connection lifetime scoped to startup; FastAPI's thread-local connections (Phase 18) can re-open as needed"
  - "verify.sh pre-cleans leftover uvicorn/vite processes at start — the script is self-contained and does not require a clean port state from the caller (Rule 3 auto-fix)"
  - "verify.sh uses nohup + disown for backgrounded uvicorn/vite — child processes survive the script's bash session so subsequent `kill $PID` works reliably"
  - "dev.sh uses `wait` to block on whichever child exits first — Ctrl-C trap cleans up both, exit 0 for clean teardown"

requirements-completed: [API-01, FE-02]

# Metrics
duration: ~8min
completed: 2026-06-03T17:42:00Z
tasks: 2
files: 7
test_state:
  config_passed: 2
  db_passed: 2
  health_passed: 1
  models_passed: 5
  total: "10/10 passed (was 9 passed + 1 skipped in Plan 02; this plan turns the skip into a pass)"
verify_state:
  criterion_1_health: "2/2 (200 + body)"
  criterion_2_vite: "2/2 (serves on :5173 + 'JD Builder' title)"
  criterion_3_proxy: "1/1 (Vite proxies /api/health → :8000)"
  criterion_4_db: "1/1 (work_descriptions + audit_log tables)"
  criterion_5_models: "1/1 (all 5 models importable)"
  total: "7/7 passed, exit 0"
---

# Phase 10 Plan 04: FastAPI Integration + Dev/Verify Scripts Summary

**FastAPI app (lifespan + /api/health) + run docs (v2/README.md, backend/README.md) + dev.sh one-shot launcher + verify.sh 5-criteria verification — all 10 tests GREEN, verify.sh exits 0 with 7/7 checks passing.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-06-03T17:34:00Z
- **Completed:** 2026-06-03T17:42:00Z
- **Tasks:** 2 / 2
- **Files created:** 7 (matching plan's `files_modified`)
- **Tests passing:** 10/10 (was 9 passed + 1 skipped)
- **verify.sh checks:** 7/7 pass, exit 0

## Accomplishments

### Task 1 — FastAPI app (main.py) + /api/health endpoint

- **`v2/backend/app/main.py`** — FastAPI app factory + asynccontextmanager lifespan. On startup: `settings = get_settings(); con = get_connection(settings.db_path); create_schema(con); con.close()`. Yields. Shutdown is a no-op (sqlite3 closes on GC). Mounts `api_router` under `/api`.
- **`v2/backend/app/api/__init__.py`** — `APIRouter()` aggregator that includes `health.router`. Re-exports `api_router` for main.py to mount.
- **`v2/backend/app/api/health.py`** — `@router.get("/health") async def health() -> dict: return {"status": "ok"}` — minimal liveness probe for Phase 10; Phase 18 will add `/api/wd`, `/api/work-types`, `/api/duties`, `/api/quals/default`, `/api/classify`.
- **Test transition:** `test_health_returns_200` went from SKIP (waiting for `app.main`) to PASS. All 10 tests now GREEN.
- **No CORS middleware** (PITFALL-10-02) — the Vite proxy is a same-origin pass-through; cross-origin headers are unnecessary.

### Task 2 — Run docs + dev launcher + verify script

- **`v2/README.md`** — top-level quick start: two terminals (backend + frontend), verify with `./scripts/verify.sh`, layout tree, Phase 10 success criteria. Documents the dev workflow so a new dev can pick up the project without reading the plans.
- **`v2/backend/README.md`** — backend-specific: `pip install`, `uvicorn`, `pytest`, env vars (`DB_PATH`, `PROJECT_ROOT`), API endpoints (Phase 10 + Phase 18 roadmap).
- **`v2/scripts/dev.sh`** — one-shot launcher. `cd backend && uvicorn app.main:app --reload --port 8000` + `cd frontend && npm run dev` in two background subshells. `trap cleanup INT TERM` kills both on Ctrl-C and exits 0.
- **`v2/scripts/verify.sh`** — 5-criteria verification, 7 checks, all pass:
  1. **Criterion 1** (Backend /api/health): `GET /api/health` returns 200 + `{"status":"ok"}`
  2. **Criterion 2** (Vite dev server): serves on :5173, returns HTML with "JD Builder" title
  3. **Criterion 3** (Vite proxy): `GET http://localhost:5173/api/health` matches `GET http://localhost:8000/api/health` (FE-02)
  4. **Criterion 4** (SQLite schema): `work_descriptions` + `audit_log` tables created
  5. **Criterion 5** (Pydantic models): all 5 models importable from `app.models`
- Both scripts `chmod +x`. Exit 0 on all-pass, exit 1 on any fail.

## Verification — Key Links Confirmed

| Contract | Verification |
|----------|--------------|
| `main.py` contains `lifespan` (async context manager) | ✓ line 21 |
| `main.py` does `app.include_router(api_router, prefix="/api")` | ✓ line 39 |
| `main.py` lifespan calls `create_schema(get_connection(settings.db_path))` | ✓ lines 24-27 |
| `main.py` lifespan uses `get_settings()` | ✓ line 24 |
| `health.py` has `@router.get("/health")` | ✓ line 11 |
| `verify.sh` hits `curl :5173/api/health` | ✓ line 100 |
| `dev.sh` has `uvicorn` and `npm run dev` | ✓ lines 23, 28 |
| `GET /api/health` returns 200 + `{"status":"ok"}` | ✓ live curl test: `{"status":"ok"} HTTP 200` |
| SQLite created at DB_PATH on first startup | ✓ `/tmp/test-final.db` (32768 bytes) |
| `v2/scripts/verify.sh` exits 0 with 7/7 checks | ✓ "=== Result: 7 passed, 0 failed ===" |
| v1.0 `app/`, `data/`, `Job Description Builder/` unchanged | ✓ `git diff --stat` empty for those paths |

## Test State Transition (Plan 02 → Plan 04)

| Test file | Before Plan 04 | After Plan 04 |
|-----------|----------------|---------------|
| `test_config.py` (2 tests) | 2 PASSED | 2 PASSED |
| `test_db.py` (2 tests) | 2 PASSED | 2 PASSED |
| `test_models.py` (5 tests) | 5 PASSED | 5 PASSED |
| `test_health.py` (1 test) | 1 SKIPPED (waiting for `app.main`) | **1 PASSED** |
| **Total** | 9 passed + 1 skipped | **10/10 PASSED** |

```
$ cd v2/backend && python -m pytest tests/ -x -q
tests/test_config.py ..                                                  [ 20%]
tests/test_db.py ..                                                      [ 40%]
tests/test_health.py .                                                   [ 50%]
tests/test_models.py .....                                               [100%]
============================== 10 passed in 0.52s ==============================
```

## verify.sh Output

```
=== Phase 10 verification ===

[Criterion 4: SQLite schema]
  ✓ DB_PATH is created on startup

[Criterion 5: Pydantic models]
  ✓ 5 models importable from app.models

[Criterion 1: Backend /api/health]
  ✓ GET /api/health returns 200
  ✓ GET /api/health body is {status: ok}

[Criterion 2: Vite dev server]
  ✓ Vite serves on :5173
  ✓ Vite serves index.html with 'JD Builder' title

[Criterion 3: Vite proxy /api -> :8000]
  ✓ Vite proxies /api/health to backend

=== Result: 7 passed, 0 failed ===
```

## Task Commits

Each task was committed atomically:

1. **Task 1: FastAPI app (main.py) + /api/health endpoint — make test_health pass + 5-criteria integration** — `734d9ed` (feat)
2. **Task 2: Run docs (v2/README.md, backend/README.md) + dev launcher (dev.sh) + verification script (verify.sh)** — `b7ce298` (feat)

## Files Created

- `v2/backend/app/main.py` — FastAPI app factory + lifespan + `/api` router mount
- `v2/backend/app/api/__init__.py` — APIRouter aggregator (`api_router` includes `health.router`)
- `v2/backend/app/api/health.py` — `GET /api/health` returning `{"status": "ok"}`
- `v2/README.md` — top-level quick start + Phase 10 success criteria
- `v2/backend/README.md` — backend-specific run + test + env docs
- `v2/scripts/dev.sh` — one-shot launcher (backend + frontend, Ctrl-C tears down)
- `v2/scripts/verify.sh` — 5-criteria verification (7 checks, all pass, exit 0)

## Decisions Made

- **Mount all routes under `/api`** (not `/`): Vite proxy is a simple pass-through with no rewrite, eliminating an entire class of CORS/dev-server bugs (PITFALL-10-02 from 10-RESEARCH.md). The same `/api/health` URL works whether the browser hits `http://localhost:5173/api/health` (proxied) or `http://localhost:8000/api/health` (direct).
- **App factory + module-level instance** (`create_app()` + `app = create_app()`): the factory is testable without module-level state side effects; the module-level `app` instance is what `uvicorn app.main:app` references. This is the canonical FastAPI pattern.
- **Close SQLite connection after schema creation in lifespan**: keeps the connection lifetime scoped to startup. Phase 18 will use thread-local request handlers and can re-open per-request connections (or use a connection pool).
- **`create_app()` returns the fully-configured app**: the lifespan is set via the constructor (`lifespan=lifespan`), so by the time `app` is returned, the app already knows to run `create_schema` on startup. No lazy initialization needed.
- **`verify.sh` pre-cleans at start** (Rule 3 auto-fix, see Deviations): kills any leftover `uvicorn`/`vite` from prior sessions so the script is self-contained — a fresh run on a polluted port state still passes.
- **`verify.sh` uses `nohup ... < /dev/null &` + `disown`**: child processes survive the script's bash session; subsequent `kill $PID` works reliably on the captured PID.
- **`dev.sh` uses `wait` (not individual waits)**: blocks on whichever child exits first; if either process dies, the other gets the cleanup signal too. Ctrl-C trap kills both.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added pre-cleanup at start of verify.sh**

- **Found during:** Task 2 verification (first run of `v2/scripts/verify.sh`)
- **Issue:** The plan's `verify.sh` only had a cleanup trap on EXIT. When I ran it the first time, a leftover `uvicorn app.main:app --port 8000` from an earlier interactive session (during Task 1's manual smoke test) was holding port 8000. The Criterion 3 "Vite proxies /api/health to backend" step started a new uvicorn on :8000, which failed to bind (port held) and exited silently (log empty). The curl to `:5173/api/health` got nothing from the backend, and the check failed.
- **Symptom:** `6 passed, 1 failed` — only the Vite proxy check failed.
- **Fix:** Added a `cleanup` invocation immediately after `trap cleanup EXIT`, so the script kills any stale uvicorn/vite processes BEFORE running its checks. Now the script is self-contained and works regardless of port state.
- **Files modified:** `v2/scripts/verify.sh` (added lines 37-39: `cleanup` + blank line + section header)
- **Verification:** Re-ran `v2/scripts/verify.sh` → `7 passed, 0 failed`, exit 0. Subsequent runs (with or without leftover processes) all pass.
- **Committed in:** `b7ce298` (Task 2 commit)
- **Why this is Rule 3 (blocking issue), not a behavior change:** The script's contract is "exits 0 with all 5 success criteria passing on a fresh checkout." Without pre-cleanup, the script fails on a polluted port state — making it flaky and dependent on the user's prior actions. Adding a pre-cleanup is a single `cleanup` line call that runs the same `pkill` commands as the EXIT trap, satisfying the contract for any initial state. No user-facing behavior change for the test itself.

---

**Total deviations:** 1 auto-fixed (1 blocking issue)
**Impact on plan:** Minimal. The deviation is necessary for the script to satisfy its "exit 0 on a fresh checkout" contract on a polluted port state.

## Issues Encountered

- **Shell hangs after `pkill`**: When the verify.sh script killed the vite process via `pkill -f "vite"`, the bash tool's session sometimes hung waiting for the orphaned process group to reap. Workaround: use `kill $PID` (specific PID captured from `$!`) instead of `pkill -f`, and the script now uses nohup + disown so the process is fully detached. This was a local environment quirk, not a script bug.
- **Plan 02 left over an uvicorn on port 8000**: An interactive test I ran during Task 1 to verify `/api/health` started a uvicorn that I then killed, but a child python process was reparented to PID 1 and kept the port open. This is what triggered the pre-cleanup auto-fix. The final `kill -9` of that PID at the end of Task 1 verification finally freed port 8000.

## v1.0 Untouched

- `app/` — no changes
- `data/` — no changes
- `Job Description Builder/jd-builder/` — no changes
- `v2/frontend/` (Plan 03) — no changes (Wave parallelism preserved)
- `v2/backend/app/{config.py, db.py, models/}` (Plan 02) — no changes (only `main.py` and `api/` were added)

## User Setup Required

None — no external service configuration required for this plan. The Settings class reads from env (or `.env` file) which is set up by Plan 01's `.env.example` (with `DB_PATH=./data/jd_builder.db` and `PROJECT_ROOT=../..`).

## Phase 10 Success Criteria — All 5 Verified

| # | Criterion | Status | Verified by |
|---|-----------|--------|-------------|
| 1 | `uvicorn app.main:app` starts and `GET /api/health` returns 200 with `{"status": "ok"}` | ✓ | `verify.sh` Criterion 1 (2 checks: 200 + body) |
| 2 | `npm run dev` starts Vite and the SPA loads at localhost:5173 | ✓ | `verify.sh` Criterion 2 (2 checks: 200 + 'JD Builder' title) |
| 3 | Vite proxies `/api/*` to FastAPI on :8000 | ✓ | `verify.sh` Criterion 3 (1 check: Vite-proxied `/api/health` matches backend) |
| 4 | SQLite single-file DB at `DB_PATH` with `work_descriptions` + `audit_log` | ✓ | `verify.sh` Criterion 4 (1 check: tables present) |
| 5 | Pydantic v2 models: `WorkDescription`, `DraftDuty`, `Classification`, `JESFactor`, `QualificationStandard` | ✓ | `verify.sh` Criterion 5 (1 check: all 5 importable) |

**The Phase 10 dev workflow is now:**
- Terminal 1: `cd v2/backend && uvicorn app.main:app --reload --port 8000`
- Terminal 2: `cd v2/frontend && npm run dev`
- Or: `v2/scripts/dev.sh` (one-shot, both processes, Ctrl-C tears down)
- Or: `v2/scripts/verify.sh` (regression test for the 5 success criteria)

## Next Phase Readiness

- **Phase 11 (Frontend Port)** is unblocked: the React prototype from `Job Description Builder/jd-builder/` can be copied into `v2/frontend/src/`, replacing `App.jsx`. `main.jsx`, `index.html`, and `vite.config.js` are stable entry points.
- **Phase 12-17 (Conversation UX, Document Composition, Classification, JES, Duties, Quals)** are unblocked: they build on Phase 11's ported prototype.
- **Phase 18 (Backend API Service)** is unblocked: `app/main.py` already has the `/api` prefix and lifespan pattern; Phase 18 adds new routers under `app/api/` (e.g., `wd.py`, `work_types.py`, `duties.py`, `quals.py`, `classify.py`) and includes them in `app/api/__init__.py`.
- **Phase 19 (DOCX Export)** is unblocked: builds on Phase 18's API and uses the SQLite persistence path proven in this plan.

## Notes for Verifier

- **Self-test the test suite:** `cd v2/backend && python -m pytest tests/ -x -q` → 10/10 pass.
- **Self-test the FastAPI app:** `cd v2/backend && uvicorn app.main:app --port 8000` → `curl http://localhost:8000/api/health` → `{"status":"ok"}` HTTP 200.
- **Self-test the dev launcher:** `./v2/scripts/dev.sh` → both processes start; Ctrl-C → both die cleanly.
- **Self-test the verification:** `./v2/scripts/verify.sh` → 7/7 checks pass, exit 0.
- **No v1.0 files modified:** `git diff --stat HEAD~2 HEAD -- app/ data/ 'Job Description Builder/'` returns empty.
- **No `package-lock.json` or `node_modules/` committed:** left untracked (per Plan 03's decision — lockfile is build output, not source).

---

*Phase: 10-project-scaffold*
*Plan: 04*
*Completed: 2026-06-03T17:42:00Z*
*Commits: `734d9ed` (Task 1), `b7ce298` (Task 2)*

## Self-Check: PASSED

All 7 expected files present:

- `v2/backend/app/main.py` — FOUND
- `v2/backend/app/api/__init__.py` — FOUND
- `v2/backend/app/api/health.py` — FOUND
- `v2/README.md` — FOUND
- `v2/backend/README.md` — FOUND
- `v2/scripts/dev.sh` — FOUND (executable, mode 755)
- `v2/scripts/verify.sh` — FOUND (executable, mode 755)

Both commit hashes (`734d9ed` Task 1, `b7ce298` Task 2) — FOUND in `git log`.

`pytest tests/ -x -q` → 10/10 passed.
`v2/scripts/verify.sh` → 7/7 checks pass, exit 0.
Live curl test → `{"status":"ok"}` HTTP 200, SQLite auto-created at DB_PATH.
