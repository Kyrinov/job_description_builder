# Phase 10 Research — Project Scaffold (v2.0)

**Phase:** 10 — Project Scaffold
**Researched:** 2026-06-03
**Mode:** Ecosystem + Feasibility
**Status:** Ready for planning

---

## Phase Boundary

Phase 10 establishes the v2.0 development environment: FastAPI JSON API backend + Vite-built React 18 SPA + SQLite persistence + Vite dev server proxy. This is the foundation every later v2.0 phase builds on. No business logic ships in this phase — only the scaffold that proves "both processes start, talk to each other, and persist data."

## Why Existing Research Doesn't Apply

The `.planning/research/` directory (STACK.md, ARCHITECTURE.md, PITFALLS.md, FEATURES.md, SUMMARY.md) is from v1.0 — a HTMX + FastAPI + SQLite + sqlite-vec + Ollama + LLM-driven pipeline architecture. v2.0 is a full rewrite:

| v1.0 (archived) | v2.0 (active) |
|-----------------|---------------|
| HTMX 2.x + Alpine.js 3.x + Jinja2 templates | React 18 SPA + Vite |
| FastAPI + Jinja2 server-rendered HTML | FastAPI JSON API only |
| SQLite + sqlite-vec + FTS5 | SQLite single-file (no sqlite-vec, no FTS5) |
| Ollama + DashScope LLM | Deterministic (no LLM in main flow) |
| Multiple data pipelines (NOC/CA/JES) | Curated hardcoded data in frontend |
| LLM-driven NOC mapping, JES scoring | Hardcoded EC JES table, verb-map duty refinement |

The Phase 10 research is therefore focused on the new stack, not the old one. Several v1.0 lessons still apply (Pydantic-first model contracts, sqlite-vec not needed for v2.0, single-user local app, document export pattern), but the technology choices are different.

---

## Recommended Stack (Phase 10 scope)

### Backend: FastAPI 0.128.x + Pydantic v2 + SQLite

**FastAPI 0.128.8** — CONFIRMED installed on this machine (v1.0 era). Reuse the same version for v2.0 to avoid introducing a new FastAPI version during the rewrite.

**Pydantic 2.12.x** — CONFIRMED installed. v2.0 models use Pydantic v2 syntax throughout (`model_config = ConfigDict(...)`, `Field(default_factory=...)`, `Annotated[..., Field(...)]` for validation).

**SQLite (stdlib `sqlite3`)** — CONFIRMED built-in. v2.0 uses single-file SQLite at `v2/backend/data/jd_builder.db`. No sqlite-vec, no FTS5, no DuckDB, no Polars — v2.0 is a single-user local app and the prototype data fits in JSON-encoded rows.

**Uvicorn 0.40.x** — CONFIRMED installed. Single-worker is fine for a local single-user app. Run with `--reload` in dev.

**pydantic-settings 2.x** — Required for `Settings(BaseSettings)` with `model_config = SettingsConfigDict(env_file=".env")`. Reuse the v1.0 `.env` pattern: required env vars fail loudly at startup.

### Frontend: Vite 5/6/7 + React 18 + plain CSS

**Vite 5+** (latest stable) — Use Vite 5 or 6 (LTS) for the dev server + bundler. The dev server's built-in `server.proxy` is exactly what we need to forward `/api/*` to FastAPI on `http://localhost:8000` without CORS configuration in dev.

**React 18.x** — Latest stable. Use `createRoot().render()` API (not the deprecated `ReactDOM.render`). For Phase 10, the SPA is a single `<App />` component rendering "JD Builder — Phase 10 scaffold." Multi-file structure, brand styles, and full conversational UX port over in Phase 11.

**Plain CSS** (not Tailwind, not CSS-in-JS) — `Job Description Builder/jd-builder/styles.css` is the source of truth. Phase 11 ports it verbatim. Phase 10 just needs an `index.css` with minimal reset so the placeholder page is readable.

**No state library** — Per FE-04: "useState + useMemo is sufficient; no Redux/Zustand." Phase 10 doesn't need state at all (placeholder page). This decision is enforced in Phase 11.

### Vite Dev Server Proxy

Vite 5/6/7 ships with a built-in proxy powered by `http-proxy`. Configuration in `vite.config.js`:

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // No rewrite: the FastAPI routes are already mounted at /api/*
        // The Vite dev server forwards /api/health → http://localhost:8000/api/health
      }
    }
  }
})
```

**Pattern: Mount all FastAPI routes under `/api`.** The Vite proxy forwards `/api/*` to FastAPI; the SPA at `/` is served by Vite's own dev server. This matches the v2.0 spec (FE-02: "Vite dev server proxies /api to FastAPI on a separate port (e.g. 8000). Production build emits static files in dist/ that FastAPI serves"). For Phase 10, only `/api/health` exists. Later phases add `/api/wd`, `/api/work-types`, `/api/duties`, `/api/quals/default`, `/api/classify` (all under `/api`).

### Project Layout

```
job_description_builder/
├── app/                    # v1.0 backend (archived — frozen, not extended)
├── data/                   # v1.0 data (archived)
├── scripts/                # shared utility scripts
├── Job Description Builder/  # v2.0 React prototype (static design source — Phase 11 ports this)
└── v2/                     # v2.0 codebase (NEW)
    ├── backend/            # FastAPI + Pydantic v2 + SQLite
    │   ├── pyproject.toml
    │   ├── .env.example
    │   ├── app/
    │   │   ├── __init__.py
    │   │   ├── main.py          # FastAPI app + lifespan + /api/health
    │   │   ├── config.py        # pydantic-settings Settings
    │   │   ├── db.py            # SQLite connection + schema DDL
    │   │   └── models/
    │   │       ├── __init__.py
    │   │       ├── work_description.py   # WorkDescription
    │   │       ├── draft_duty.py         # DraftDuty
    │   │       ├── classification.py     # Classification
    │   │       ├── jes_factor.py         # JESFactor
    │   │       └── qualification_standard.py  # QualificationStandard
    │   ├── tests/
    │   │   ├── conftest.py
    │   │   ├── test_health.py
    │   │   ├── test_db.py
    │   │   ├── test_models.py
    │   │   └── test_config.py
    │   └── data/             # SQLite file lives here (created at startup)
    └── frontend/            # Vite + React 18 SPA
        ├── package.json
        ├── vite.config.js
        ├── index.html
        └── src/
            ├── main.jsx     # React 18 createRoot entry point
            ├── App.jsx      # Placeholder: "JD Builder — Phase 10 scaffold"
            └── index.css    # Minimal reset
```

**Why `v2/backend/` and `v2/frontend/` (not `app_v2/` and `web/`):** Groups v2.0 together so the v1.0 archive at the root stays untouched. Phase 11+ will add to `v2/frontend/src/` (port the prototype), Phase 18 will add to `v2/backend/app/api/`.

### Why Not Use `create-vite`

`npm create vite@latest` scaffolds a project with example content (Vite logo, React logo, counter component, etc.) that has to be deleted. For Phase 10 we want a minimal placeholder. Writing `package.json`, `vite.config.js`, `index.html`, and `src/main.jsx` directly is faster and produces exactly the files we need. Phase 11 will add the prototype ports.

### SQLite Schema (v2.0)

Two tables — `work_descriptions` (the WD entity as a JSON blob) and `audit_log` (per-step commit + advisor-modified + export events). The v1.0 schema is broader (source_documents, noc_units, noc_elements, noc_fts, noc_chunks_vec, etc.) — v2.0 does NOT need any of that, so we start with a clean two-table schema.

```sql
-- work_descriptions: the canonical WD entity, JSON-encoded
CREATE TABLE IF NOT EXISTS work_descriptions (
    id              TEXT PRIMARY KEY,            -- UUID4 string
    title           TEXT NOT NULL DEFAULT '',
    data            TEXT NOT NULL,               -- Full Pydantic WorkDescription JSON
    schema_version  INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL,               -- ISO 8601 UTC
    last_modified   TEXT NOT NULL                -- ISO 8601 UTC
);

CREATE INDEX IF NOT EXISTS idx_wd_created_at ON work_descriptions(created_at);

-- audit_log: per-step commit + advisor-modified + export events
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    wd_id       TEXT NOT NULL,                   -- FK to work_descriptions.id
    event       TEXT NOT NULL,                   -- 'created' | 'step_committed' | 'advisor_modified' | 'exported'
    actor       TEXT NOT NULL,                   -- 'advisor' | 'system'
    detail      TEXT,                            -- JSON: event-specific payload
    created_at  TEXT NOT NULL                    -- ISO 8601 UTC
);

CREATE INDEX IF NOT EXISTS idx_audit_wd_id ON audit_log(wd_id);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_log(event);
```

**Why JSON blob for the WD:** v2.0's WD has a conversational data shape (record, answers, stepIndex, draft, reviewing, editingReturn, flashes) that maps cleanly to JSON. Pydantic v2's `model_dump()` produces canonical JSON. Migration is a `schema_version` bump + a versioned migration function (v1.0 proved this pattern works).

### Pydantic v2 Models (v2.0)

Five models are explicitly named in the ROADMAP success criteria. Phase 10 defines them as **typed contracts** (with field types and validators) but does NOT yet wire them to a database or service layer (that's Phase 18). All models go in `v2/backend/app/models/`.

```python
# work_description.py
class WorkDescription(BaseModel):
    id: str                                # UUID4 string
    title: str = ""                        # Working title from step 1
    record: dict = Field(default_factory=dict)      # Committed answers per step id
    answers: dict = Field(default_factory=dict)     # Per-step answer history
    step_index: int = 0
    draft: dict | None = None              # In-progress answer
    reviewing: bool = False
    editing_return: bool = False
    classification: Classification | None = None    # Resolved after scope questions
    duties: list[DraftDuty] = Field(default_factory=list)
    qualification: QualificationStandard | None = None
    drf_id: str | None = None              # Selected DND core responsibility
    schema_version: int = 1
    created_at: datetime
    last_modified: datetime

# draft_duty.py
class DraftDuty(BaseModel):
    id: str                                # UUID4
    text: str                              # Formal duty statement
    plain_trigger: str | None = None       # User's plain words (if advisor-added)
    source: Literal["suggested", "advisor"]
    source_index: int | None = None        # Index into DUTY_SUGGESTIONS (if source="suggested")
    refined_at: datetime | None = None     # When verb-mapping was applied

# classification.py
class JESFactor(BaseModel):
    name: str                              # "Decision making"
    degree: int                            # 1-7
    points: int
    category: Literal["Responsibility", "Skill", "Effort", "Conditions"]

class Classification(BaseModel):
    work_type: str                         # "EC" | "FI" | "IT" | "AS" | "EN"
    work_type_name: str
    applicable_standard: str               # e.g. "EC Job Evaluation Standard (2017)"
    scope_direction: int | None = None     # 1-3
    scope_advises: int | None = None       # 1-3
    scope_impact: int | None = None        # 1-3
    code: str | None = None                # "EC-05" once resolved
    group: str | None = None               # "EC"
    level: int | None = None               # 4 | 5 | 6
    points: int | None = None              # Sum of factor points (EC) or approximate total (non-EC)
    factors: list[JESFactor] | None = None # Per-factor breakdown (EC only)
    rationale: str | None = None           # Plain-English scope profile
    confidence: float | None = None        # 0.0-1.0

# qualification_standard.py
class QualificationStandard(BaseModel):
    education: str                         # Degree text
    experience: str                        # Significant experience text
    source: Literal["EC-05 default", "advisor-edited"]
    last_modified: datetime

# (Re-export JESFactor from classification.py — single source of truth)
# Note: the success criteria lists "JESFactor" as a separate model;
#       Phase 10 places it inside classification.py for cohesion,
#       re-exported from the models package.
```

**Decision (JESFactor location):** The success criteria lists `JESFactor` as one of the 5 models to define. The cleanest place is as a sub-model of `Classification` (it's only meaningful as part of a classification). Phase 10 re-exports it from `models/__init__.py` so the import path is `from app.models import JESFactor`. The plan-level acceptance criteria assert this re-export.

---

## Anti-Patterns to Avoid

| Anti-pattern | Why it bites | v2.0 Phase 10 mitigation |
|--------------|--------------|--------------------------|
| Single Pydantic model with everything | Bloats, can't evolve, breaks tests | Five focused models + structured WD JSON |
| sqlite-vec for v2.0 | Adds dependency + 30MB RAM for no use case (no embeddings in v2.0) | Use stdlib sqlite3 only |
| Use `npm create vite@latest` for a placeholder | Produces sample files to delete | Write package.json + vite.config.js directly |
| Mount SPA routes inside FastAPI | Couples frontend to backend process, defeats Vite HMR | Vite serves SPA in dev; FastAPI serves /api/* only |
| Use CORS middleware in dev | Workaround for missing proxy; not needed | Use Vite `server.proxy` for `/api` |
| Use ESM `import` in v1.0 Python modules | v1.0 codebase has v1.0 patterns; don't migrate those | v2.0 is fresh; use Pydantic v2 + FastAPI latest |
| Hardcode DB path in code | Same hardcoded-path trap v1.0 had | Use pydantic-settings Settings with DB_PATH env var |
| Use `pydantic.BaseSettings` (v1) | Deprecated; replaced by pydantic-settings 2.x | Use `pydantic_settings.BaseSettings` |

---

## Pitfalls to Watch (Phase 10 specific)

### PITFALL-10-01: Vite proxy not forwarding to FastAPI
**Symptom:** SPA loads, but `fetch('/api/health')` returns 404 from Vite (not proxied).
**Cause:** Missing `server.proxy` config OR target port mismatch OR missing `changeOrigin: true` for non-default hosts.
**Detection:** `curl -s http://localhost:5173/api/health` should return the same as `curl -s http://localhost:8000/api/health`.
**Phase 10 mitigation:** Plan 10-03 (Integration) writes a smoke test that starts both processes, hits `/api/health` via both ports, asserts the responses match.

### PITFALL-10-02: FastAPI CORS errors in dev
**Symptom:** Browser console: "CORS policy: No 'Access-Control-Allow-Origin' header."
**Cause:** If the Vite proxy is misconfigured, the browser sees requests as cross-origin (port 5173 → port 8000).
**Phase 10 mitigation:** Vite proxy strips the cross-origin boundary. If a test fails, the fix is in vite.config.js, not in FastAPI CORS. We do NOT add `CORSMiddleware` in Phase 10.

### PITFALL-10-03: SQLite schema created twice (race)
**Symptom:** `OperationalError: table work_descriptions already exists` on concurrent startup.
**Cause:** Test suite re-imports `app.main` and the lifespan runs twice.
**Phase 10 mitigation:** All DDL uses `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`. The connection is a single sqlite3.Connection with `check_same_thread=False` for FastAPI thread safety.

### PITFALL-10-04: Vite + React 18 HMR breaks on JSX transform
**Symptom:** Browser console: "Unexpected token <" or similar JSX parse error.
**Cause:** Missing `@vitejs/plugin-react` plugin in `vite.config.js`.
**Phase 10 mitigation:** Plan 10-02 includes the plugin and verifies `npm run dev` actually serves the JSX-rendered page.

### PITFALL-10-05: Pydantic v2 vs v1 import paths
**Symptom:** `ImportError: cannot import name 'BaseSettings' from 'pydantic'`.
**Cause:** Pydantic v2 moved `BaseSettings` to the separate `pydantic-settings` package.
**Phase 10 mitigation:** `from pydantic_settings import BaseSettings` and `pydantic-settings` in requirements.

### PITFALL-10-06: `npm install` fails on ARM64
**Symptom:** Sharp, esbuild, or rollup native binary fails to install.
**Cause:** Some Node packages ship x86_64-only binaries.
**Phase 10 mitigation:** Vite + React 18 + @vitejs/plugin-react have ARM64 wheels via Node 18+ bundled prebuilt binaries. The `package.json` does NOT include any package known to have ARM64 issues (no `sharp`, no `node-sass`, no `@swc/core` with native builds).

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Vite + React 18 dev server setup | HIGH | Standard pattern; verified via Context7 docs |
| Vite proxy → FastAPI | HIGH | Built-in to Vite; verified proxy examples |
| FastAPI + Pydantic v2 + SQLite | HIGH | Same as v1.0; Pydantic v2 syntax is established |
| SQLite schema (2 tables) | HIGH | v1.0 schema pattern (work_descriptions + wd_audit_log) proven |
| React 18 createRoot API | HIGH | Stable since React 18.0 |
| ARM64 compatibility | HIGH | All Phase 10 deps are pure Python or Node-bundled-binary; no x86_64-only deps |

---

## Sources

- Vite server proxy: https://github.com/vitejs/vite/blob/main/docs/config/server-options.md
- Vite createServer + middleware mode: https://github.com/vitejs/vite/blob/main/docs/guide/api-javascript.md
- FastAPI lifespan: https://github.com/fastapi/fastapi/blob/master/docs/en/docs/release-notes.md
- FastAPI SQL databases (create_all pattern): https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/sql-databases.md
- pydantic-settings (BaseSettings moved): https://github.com/fastapi/fastapi/blob/master/docs/en/docs/advanced/settings.md
- React 18 + Vite setup guide: https://www.joshfinnie.com/blog/fastapi-and-react-in-2025
- Vite 5 getting started: https://vite.dev/guide
- v1.0 lessons: `.planning/RETROSPECTIVE.md` (Patterns Established, Key Lessons)
- v1.0 schemas: `app/db.py`, `app/models/work_description.py` (reference for Pydantic + SQLite patterns)

---
*Research: 2026-06-03 for v2.0 "Guided Conversation" Phase 10*
