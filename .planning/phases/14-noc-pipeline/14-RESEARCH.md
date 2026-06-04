# Phase 14: NOC Pipeline - Research

**Researched:** 2026-06-04
**Domain:** FastAPI backend porting, sqlite-vec ARM64, instructor/Ollama integration, React NOC confirmation UI
**Confidence:** HIGH — all critical claims verified by direct codebase inspection and live system probes

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NOC-01 | Three-stage NL→NOC pipeline (FTS5 → embedding rerank → LLM justification) in FastAPI backend, ported from `app/services/noc_mapper.py`; exposed via POST `/api/noc/map` | Pipeline logic fully read; all dependencies confirmed available on ARM64; porting path is direct copy-and-adapt with import path changes |
| NOC-02 | NOC candidates include code, title, TEER, verbatim duty matches; SPA displays candidates and waits for advisor confirmation before classification proceeds | Response model (`NOCCandidate`) already defined in v1.0; v2 WorkDescription model needs NOC fields added; SPA needs new input control type `noc_confirm` |
| API-04 | POST `/api/noc/map` — free-text work description → top-3 NOC candidates via three-stage pipeline | v1.0 route is a direct model; v2 uses pure JSON API (no HTMX), simplifying the route significantly |
</phase_requirements>

---

## Summary

Phase 14 ports the production-proven NL→NOC three-stage pipeline from `app/services/noc_mapper.py` into the v2 backend. The pipeline (FTS5 shortlist → sqlite-vec embedding rerank → instructor/Ollama LLM justification) is complete and battle-tested in v1.0. The port is a **direct copy-and-adapt** — import paths change from `app.*` to `v2/backend/app.*`, the v1.0 HTMX dual-path route is replaced with a clean JSON-only FastAPI endpoint, and the NOC database from v1.0 (`app.db`) becomes a second database file pointed to by a new `NOC_DB_PATH` setting.

The two critical blockers flagged in STATE.md are resolved: sqlite-vec 0.1.9 is **already installed and working** on this ARM64 machine (verified with a live vec0 round-trip), and gemma4:31b is **available** in Ollama. The v1.0 `app.db` (83 MB) is the indexed NOC database: 516 `noc_units`, 43,999 `noc_elements`, 6,119 `noc_chunks_vec` rows, 768-dim embeddings built with `nomic-embed-text:latest`.

The frontend work for NOC-02 is scoped to a new `noc_confirm` input control type in `components.jsx` and a corresponding handler in `app.jsx` state. The full conversation flow wiring (which step renders the NOC card) lands in Phase 15 — Phase 14 only delivers the API endpoint and the reusable UI component.

**Primary recommendation:** Port `noc_mapper.py` and `noc_ranking.py` verbatim (changing import prefixes), add `NOC_DB_PATH` + Ollama fields to v2 `Settings`, create `app/api/noc_mapping.py` as a JSON-only route, extend the v2 `WorkDescription` model with `noc_candidates`/`confirmed_noc` fields, and add the `NocConfirmCard` component to the frontend.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| FTS5 keyword shortlist (Stage 1) | API / Backend | — | Requires SQLite FTS5 query against NOC database; cannot run in browser |
| Embedding rerank (Stage 2) | API / Backend | — | Requires sqlite-vec + Ollama embed model; server-only dependency |
| LLM justification (Stage 3) | API / Backend | — | Requires instructor + Ollama generation model; server-only |
| Verbatim fidelity guardrail | API / Backend | — | DB lookup to confirm duties exist; server-only |
| TEER correction guardrail | API / Backend | — | DB lookup against noc_units; server-only |
| NOC candidate display | Browser / Client | — | SPA renders confirmation cards from JSON response |
| Advisor confirmation (select NOC) | Browser / Client | API / Backend | SPA sends confirmed selection; backend stores it on WorkDescription |

---

## Standard Stack

### Core (already installed on system — verified)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sqlite-vec | 0.1.9 | vec0 KNN cosine rerank in SQLite | Production-proven in v1.0; ARM64 wheel confirmed working |
| instructor | 1.15.1 | Structured LLM output via Pydantic | Used in v1.0; singleton pattern established |
| ollama | 0.6.1 | Embed + generation via local Ollama | Used in v1.0; models confirmed present |
| fastapi | 0.128.8 | API framework | Already in v2 requirements.txt |
| pydantic | 2.12.5 | Response validation + NOCCandidate model | Already in v2; v1.0 models are Pydantic v2 |

### New dependencies to add to v2 `requirements.txt`

| Library | Version | Purpose | When to Add |
|---------|---------|---------|-------------|
| sqlite-vec | 0.1.9 | vec0 extension loading | Wave 0 (required for test fixture) |
| instructor | 1.15.1 | Structured LLM output | Wave 1 (noc_ranking.py port) |
| ollama | 0.6.1 | Embed + generation client | Wave 1 (noc_mapper.py port) |
| openai | (instructor dep) | AsyncOpenAI client for instructor | Wave 1 (transitive; pinned by instructor) |

**Installation:**
```bash
pip install sqlite-vec==0.1.9 instructor==1.15.1 ollama==0.6.1
```

**Version verification:** [VERIFIED: direct pip show on Jane ARM64 system 2026-06-04]

---

## Architecture Patterns

### System Architecture Diagram

```
Browser (React SPA)
  │  POST /api/noc/map {"work_description": "..."}
  ▼
FastAPI (v2/backend)
  └─ app/api/noc_mapping.py
       │  calls
       ▼
  app/services/noc_mapper.py :: map_work_description()
       │
       ├─ Stage 1: FTS5 keyword shortlist ──► noc_fts MATCH query
       │            (noc_db: app.db)               ▼
       │                                   up to 30 NOC codes
       │
       ├─ Stage 2: sqlite-vec rerank ──────► noc_chunks_vec KNN (cosine)
       │            (Ollama embed call)             ▼
       │                                   top 10 by vector distance
       │
       └─ Stage 3: LLM justification ──────► instructor_client (gemma4:31b)
                    (app/ai/noc_ranking.py)          ▼
                                           NOCRankingResult (1–5 candidates)
                                                     │
                                        ┌────────────┤ online guardrails
                                        │  - verbatim fidelity check (DB lookup)
                                        │  - TEER correction (noc_units lookup)
                                        └────────────┘
                                                     │
  FastAPI returns ◄───────────────────────────────── NocMapResponse JSON
  {"candidates": [...], "wd_id": "..."}
  │
  ▼
Browser renders NocConfirmCard per candidate
  │  advisor selects one → PATCH /api/wd/{id} with confirmed_noc
  ▼
WorkDescription.confirmed_noc set → Phase 15 classification step unblocked
```

### Recommended Project Structure additions

```
v2/backend/
├── app/
│   ├── ai/
│   │   └── noc_ranking.py       # NEW — ported from app/ai/noc_ranking.py
│   ├── services/
│   │   └── noc_mapper.py        # NEW — ported from app/services/noc_mapper.py
│   ├── api/
│   │   └── noc_mapping.py       # NEW — JSON-only POST /api/noc/map
│   ├── models/
│   │   └── noc.py               # NEW — WorkDescriptionRequest + NocMapResponse
│   ├── config.py                # MODIFY — add NOC_DB_PATH, OLLAMA_* fields
│   └── db.py                    # MODIFY — add get_noc_connection() factory
│
v2/frontend/src/
│   └── components.jsx           # MODIFY — add NocConfirmCard component
│
v2/backend/tests/
    ├── test_noc_pipeline.py     # NEW — adapted from tests/test_noc_mapping.py
    └── conftest.py              # MODIFY — add noc_mapping_db fixture
```

### Pattern 1: Two-Database Architecture

**What:** v2 backend uses TWO SQLite databases — the v2 WD database (`DB_PATH`, created fresh in Phase 10) and the existing v1.0 NOC database (`NOC_DB_PATH`, pointing at `app.db`).

**When to use:** The NOC database contains the FTS5 and vec0 indexes built by v1.0 ingest scripts. Re-ingesting is out of scope for Phase 14. The v2 app reads from `app.db` for NOC queries only.

**How it's configured:**
```python
# v2/backend/app/config.py — add these fields
noc_db_path: str = Field(..., description="Path to v1.0 NOC SQLite DB (app.db)")
ollama_base_url: str = "http://localhost:11434"
ollama_generation_model: str = Field(..., description="e.g. gemma4:31b")
ollama_embed_model: str = Field(..., description="e.g. nomic-embed-text:latest")
cloud_api_key: str | None = None
cloud_model: str = "MiniMax-M3"
cloud_base_url: str = "https://api.minimax.io/v1"

@property
def generation_model(self) -> str:
    return self.cloud_model if self.cloud_api_key else self.ollama_generation_model
```

**v2/.env additions:**
```
NOC_DB_PATH=/home/charles/job_description_builder/app.db
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_GENERATION_MODEL=gemma4:31b
OLLAMA_EMBED_MODEL=nomic-embed-text:latest
```

### Pattern 2: NOC DB Connection Factory

**What:** `get_noc_connection()` is a separate factory that opens the NOC DB (with sqlite-vec loaded). The v2 `get_connection()` for the WD DB does NOT need sqlite-vec.

**Why separate:** The v2 WD database (`DB_PATH`) has no vec0 tables. Loading sqlite-vec on every WD connection is wasted work and would fail in unit tests that use in-memory temp DBs without the NOC schema.

```python
# Source: v1.0 app/db.py — adapted for v2
def get_noc_connection(noc_db_path: str) -> sqlite3.Connection:
    """Open the NOC database with sqlite-vec registered."""
    import sqlite_vec
    con = sqlite3.connect(noc_db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    return con
```

### Pattern 3: noc_ranking.py — Module-Level Singleton

**What:** `instructor_client` is built once at import time, not per-request. This is a hard architectural non-negotiable from v1.0.

**Why:** `instructor.from_openai(AsyncOpenAI(...))` creates an httpx connection pool. Constructing per-request leaks open file descriptors.

**The port:** `app/ai/noc_ranking.py` in v2 is nearly verbatim from v1.0 with two import changes:
- `from app.config import settings` → `from app.config import get_settings; settings = get_settings()`
- The `Settings` singleton pattern in v2 uses `get_settings()` (lazy load) rather than module-level `settings = Settings()` (eager). The noc_ranking module must call `get_settings()` at module import time for the singleton to behave correctly.

### Pattern 4: v2 WorkDescription Model Extension

**What:** The v2 `WorkDescription` model needs `noc_candidates` and `confirmed_noc` fields added.

**Current state (Phase 13):** `v2/backend/app/models/work_description.py` has no NOC fields.

**Fields to add:**

```python
# Add to WorkDescription in v2/backend/app/models/work_description.py
# Requires a new v2/backend/app/models/noc_match.py (or inline here)

from .noc_match import NOCMatch  # new file

class WorkDescription(BaseModel):
    # ... existing fields ...
    noc_candidates: list["NOCMatch"] = Field(default_factory=list)
    confirmed_noc: Optional["NOCMatch"] = None
```

**NOCMatch for v2** — simpler than v1.0 (no ProvenanceTag required at this layer):

```python
# v2/backend/app/models/noc_match.py
class NOCMatch(BaseModel):
    noc_code: str
    noc_title: str
    teer: int
    matched_duties: list[str]
    justification: str
    rank: int
```

The v1.0 `NOCMatch` carries a `ProvenanceTag` (complex). For v2, the NOC pipeline result can be stored with a simplified model because ProvenanceTag attachment happens downstream in the duty-selection step (Phase 18, JD-02). Keeping v2's NOCMatch lean avoids importing v1.0's ProvenanceTag model into v2 early.

### Pattern 5: v2 Route — JSON Only (no HTMX)

**What:** The v1.0 route had HTMX dual-path (TemplateResponse for HTML, NocMapResponse for JSON). The v2 route is JSON-only.

**Why:** v2 backend is a pure JSON API; the SPA is a React client (not HTMX). The Jinja2 template and `HX-Request` branch are dropped entirely.

```python
# Source: adapted from app/api/noc_mapping.py — HTMX path removed
@router.post("/noc/map", response_model=NocMapResponse)
async def map_noc(body: WorkDescriptionRequest):
    settings = get_settings()
    try:
        result = await map_work_description(
            work_description=body.work_description,
            noc_db_path=settings.noc_db_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return NocMapResponse(candidates=result.candidates)
```

Note: v2 API-04 does NOT require persisting `noc_candidates` to the WD database — that's Phase 15's job when the SPA sends the full record on step commit. The route simply returns the ranked candidates. The confirmed NOC is set when the SPA PATCHes the WD (Phase 15 API-02).

### Pattern 6: NocConfirmCard Frontend Component

**What:** A new input control type `noc_confirm` for `StepInput` in `components.jsx`. Renders each NOC candidate as a selectable card with code, title, TEER badge, and matched duties.

**When to use:** In the Phase 15 conversation step that fires the NOC pipeline. Phase 14 delivers the component; Phase 15 wires it into the STEPS array.

**Component contract:**
```jsx
// cfg.type === 'noc_confirm'
// cfg.candidates: array of { noc_code, noc_title, teer, matched_duties }
// value: selected noc_code string (or null)
// onChange(noc_code): called on card click
function NocConfirmList({ value, onChange, cfg }) {
  return (
    <div className="choices">
      {cfg.candidates.map(c => (
        <button
          key={c.noc_code}
          type="button"
          className={'choice' + (value === c.noc_code ? ' is-sel' : '')}
          onClick={() => onChange(c.noc_code)}
        >
          <span className="choice__main">
            <span className="choice__title">{c.noc_code} — {c.noc_title}</span>
            <span className="choice__desc">TEER {c.teer}</span>
          </span>
          <ul>{c.matched_duties.slice(0,2).map((d,i) => <li key={i}>{d}</li>)}</ul>
        </button>
      ))}
    </div>
  );
}
```

The `StepInput` switch in `components.jsx` grows one new branch:
```jsx
if (t === 'noc_confirm') return <NocConfirmList {...props} />;
```

The `answerValid` function grows a case: `if (c.type === 'noc_confirm') return !!value;`

### Anti-Patterns to Avoid

- **Constructing instructor_client per-request:** Creates httpx pool leak; build once at module import time.
- **Opening NOC DB connection at module level:** Connections are per-request; the NOC DB path is read from settings which may not be set at import time.
- **Passing sqlite-vec serialized vector as Python list:** Stage 2 must call `sqlite_vec.serialize_float32(query_vec)` before passing to the SQL query. Passing a raw Python list raises `InterfaceError`.
- **Embedding dimension mismatch:** The v1.0 NOC DB uses 768-dim embeddings (nomic-embed-text:latest). The vec0 table is declared as `FLOAT[1024]` in the v1.0 DDL (historical artifact — was DashScope 1024), but the actual stored vectors are 768-dim from nomic-embed-text. The `assert_noc_index_model` check in v1.0 guards this. Phase 14 must NOT recreate the vec0 table — it reads the existing one from `app.db`.
- **Replicating HTMX dual-path in v2:** v2 is JSON-only; the `HX-Request` branch and Jinja2 templates are dead code in the v2 context.
- **Adding ProvenanceTag to NOCMatch in Phase 14:** ProvenanceTag attachment is Phase 18's responsibility. Doing it here creates v1.0 model coupling before the rest of the v2 model hierarchy is in place.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured LLM output with retry | Custom JSON parsing + retry loop | `instructor.from_openai(...)` with `response_model=NOCRankingResult` | Handles Pydantic v2 validation, retries on parse failure, JSON mode for Ollama |
| Embedding-space KNN search | Manual cosine similarity in Python | sqlite-vec `vec0` with `vec_distance_cosine` | Handles serialization, index scan, cosine distance in C extension |
| Verbatim duty verification | LLM-in-LLM check | `instr(element_text, duty) > 0` SQL query against `noc_elements` | DB lookup is exact, fast, zero LLM cost |
| TEER correction | Trust LLM output | DB lookup against `noc_units` | LLM occasionally hallucinates TEER; authoritative value is always in DB |

**Key insight:** The three-stage pipeline is valuable precisely because it combines cheap exact-match (FTS5) with semantic rerank (vec) and structured reasoning (LLM) — none of the stages should be collapsed or replaced.

---

## Common Pitfalls

### Pitfall 1: sqlite-vec ARM64 — Confirmed NOT a blocker

**What goes wrong:** STATE.md flagged "Confirm sqlite-vec ARM64 wheel available" as a todo.

**Status:** RESOLVED. sqlite-vec 0.1.9 is already installed (`pip show sqlite-vec` confirms) and was verified with a live ARM64 round-trip test (vec0 table create, insert, KNN query). [VERIFIED: live probe on Jane 2026-06-04]

**What the planner must do:** Mark the STATE.md todo as resolved. No installation or workaround needed.

### Pitfall 2: Embedding Dimension — 768 not 1024

**What goes wrong:** The v1.0 DDL schema in `app/db.py` declares `noc_chunks_vec USING vec0(embedding FLOAT[1024])`, but the v1.0 ingest actually stored 768-dim vectors (nomic-embed-text:latest produces 768 dims). The test fixture also recreates the table as `FLOAT[768]`.

**Root cause:** The v1.0 schema was written anticipating a DashScope 1024-dim model, then the actual ingest used nomic-embed-text at 768 dims. The production DB (`app.db`) has 768-dim vectors. [VERIFIED: live probe on Jane, `len(json.loads(vec_to_json(embedding))) == 768`]

**How to avoid:** The v2 `noc_mapper.py` test fixture must create `noc_chunks_vec` as `FLOAT[768]`. The production path reads existing `app.db` — correct by default.

### Pitfall 3: Settings singleton pattern difference between v1 and v2

**What goes wrong:** v1.0 uses `settings = Settings()` at module level in `app/config.py`. v2 uses a lazy `get_settings()` factory. If `noc_ranking.py` is ported verbatim and still calls `from app.config import settings` (module-level singleton), it will fail in v2 tests that use monkeypatch env overrides (the Settings instance is already locked before the test sets env vars).

**How to avoid:** In v2, `noc_ranking.py` must call `get_settings()` at the point of use (inside the `if settings.cloud_api_key:` block), not at import time. Or the module-level singleton must be replaced with a factory function that returns a new instructor client when called.

**Recommended pattern:**
```python
# v2/backend/app/ai/noc_ranking.py
def make_instructor_client() -> instructor.Instructor:
    settings = get_settings()
    if settings.cloud_api_key:
        _client = AsyncOpenAI(base_url=settings.cloud_base_url, api_key=settings.cloud_api_key)
    else:
        _client = AsyncOpenAI(base_url=settings.ollama_base_url.rstrip("/") + "/v1", api_key="ollama")
    return instructor.from_openai(_client, mode=instructor.Mode.JSON)

# Module-level — called once at import time; settings must be configured before import
instructor_client = make_instructor_client()
```

This mirrors the v1.0 architecture but calls `get_settings()` internally. Tests that need to control the client mock `app.services.noc_mapper.instructor_client` directly (same pattern as v1.0 tests).

### Pitfall 4: Two-database path confusion in tests

**What goes wrong:** v2 conftest uses `tmp_db_path` for the WD database. NOC pipeline tests need a SECOND fixture `noc_db_path` that creates a SQLite file with the NOC schema, synthetic FTS5 data, and 768-dim fake vec rows.

**How to avoid:** Add a `noc_mapping_db` fixture to `v2/backend/tests/conftest.py` modeled exactly on the v1.0 `noc_mapping_db` fixture in `tests/conftest.py`. The NOC DB fixture is entirely separate from `tmp_db_path`.

### Pitfall 5: asyncio.to_thread wrapping

**What goes wrong:** sqlite3 connections are not thread-safe. The v1.0 pipeline wraps every blocking DB call in `asyncio.to_thread(lambda: conn.execute(...).fetchall())`. If this wrapping is removed (tempting for simplicity), FastAPI's async event loop will block on SQLite I/O.

**How to avoid:** Copy the `asyncio.to_thread` pattern verbatim — do not simplify it to direct awaits.

### Pitfall 6: `extra="ignore"` missing on v2 Settings

**What goes wrong:** v2 `Settings` already has `extra="ignore"` (confirmed in `config.py`). Adding new fields (`noc_db_path`, `ollama_*`) to Settings is safe as long as the `.env` file provides them. Tests that don't provide these vars will raise `ValidationError` immediately at import time.

**How to avoid:** Update `v2/backend/.env` and `v2/backend/.env.example` with the new required fields. Update `conftest.py`'s `env_with_db` fixture to also monkeypatch `NOC_DB_PATH`, `OLLAMA_GENERATION_MODEL`, `OLLAMA_EMBED_MODEL`.

---

## Code Examples

### Stage 1 FTS5 Query Construction

```python
# Source: app/services/noc_mapper.py (v1.0) — port verbatim
def _fts_query_from_text(text: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    keywords = [t for t in tokens if t not in _FTS_STOP_WORDS and len(t) >= 3]
    seen: set[str] = set()
    deduped: list[str] = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            deduped.append(kw)
    return " OR ".join(deduped)
```

### Stage 2 — sqlite-vec Serialization

```python
# Source: app/services/noc_mapper.py (v1.0)
# CRITICAL: query_vec must be serialized before passing to SQL
import sqlite_vec
serialized_vec = sqlite_vec.serialize_float32(query_vec)  # list[float] → bytes

vec_rows = conn.execute(
    """
    SELECT u.noc_code, u.title, CAST(u.teer_level AS INTEGER) as teer,
           GROUP_CONCAT(e.element_text, char(10)) AS main_duties,
           MIN(vec_distance_cosine(v.embedding, ?)) AS dist
    FROM noc_chunks_vec v
    JOIN noc_elements e ON e.id = v.rowid
    JOIN noc_units u ON u.noc_code = e.noc_code
    WHERE e.noc_code IN ({placeholders})
      AND e.element_type = 'Main duties'
    GROUP BY u.noc_code
    ORDER BY dist ASC
    LIMIT ?
    """,
    (serialized_vec, *fts_codes, rerank_limit),
).fetchall()
```

### Test Fixture — noc_mapping_db (768-dim)

```python
# Source: tests/conftest.py (v1.0) — adapt for v2
@pytest.fixture
def noc_mapping_db(tmp_path) -> str:
    """Temp NOC DB with synthetic FTS5 + 768-dim vec rows. No Ollama required."""
    import sqlite_vec as sv
    from app.db import get_noc_connection

    db_path = str(tmp_path / "test_noc.db")
    # Must create NOC schema manually (not v2 WD schema)
    con = get_noc_connection(db_path)
    # Create NOC tables + FTS5 + vec0(FLOAT[768]) ...
    # Insert synthetic noc_units, noc_elements, populate noc_fts, noc_chunks_vec
    con.close()
    return db_path
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HTMX dual-path route (HTML + JSON) | JSON-only FastAPI route | v2.0 (Phase 14) | Removes Jinja2 templates, cleaner SPA integration |
| Module-level `settings = Settings()` | `get_settings()` lazy factory | v2.0 (Phase 10) | Tests can monkeypatch env before Settings is instantiated |
| Confirm endpoint (separate POST /api/noc/confirm) | Confirmation via PATCH /api/wd/{id} (Phase 15) | v2.0 | NOC confirmation is part of WD step commit, not a separate endpoint |

**Deprecated in v2:**
- `POST /api/noc/confirm` as a separate route: v1.0 had this; v2.0 stores `confirmed_noc` when the advisor commits the NOC step via `PATCH /api/wd/{id}` (Phase 15 API-02). Phase 14 does not need to implement confirm persistence — the API-04 spec only requires the mapping endpoint.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| sqlite-vec | Stage 2 embedding rerank | ✓ | 0.1.9 | None — required |
| Ollama | Stage 2 + Stage 3 | ✓ (running) | — | Cloud API (CLOUD_API_KEY) |
| nomic-embed-text:latest | Stage 2 embed model | ✓ | present in Ollama | nomic-embed-text:32k also present |
| gemma4:31b | Stage 3 LLM justification | ✓ | present in Ollama | Cloud API (MiniMax-M3) |
| app.db (NOC database) | Stages 1, 2, 3 guardrails | ✓ | 83 MB, 516 noc_units, 43999 noc_elements | None — must exist |

[VERIFIED: live probes on Jane ARM64, 2026-06-04]

**Missing dependencies with no fallback:** None.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 14 does NOT implement confirm persistence (that's Phase 15 PATCH /api/wd/{id}) | Architecture Patterns, Pattern 5 | If Phase 15 depends on Phase 14 persisting confirmed_noc, Phase 15 would have a missing dependency; review Phases 14/15 boundary carefully |
| A2 | v2 NOCMatch model can be simpler than v1.0 (no ProvenanceTag) because ProvenanceTag attachment is Phase 18's job | Pattern 4 | If Phase 18 cannot backfill provenance onto already-stored NOCMatch, data integrity risk; the simpler model must be forward-compatible |

---

## Open Questions

1. **Does POST /api/noc/map need to persist candidates in the WD database, or just return them?**
   - What we know: API-04 spec says "returns top-3 NOC candidates." NOC-02 says "SPA displays candidates and waits for advisor confirmation." The confirm step is part of Phase 15's step-commit flow.
   - What's unclear: If the SPA loses state (page refresh) between the map call and the confirm, are the candidates lost?
   - Recommendation: For Phase 14, return-only is correct (simpler, testable in isolation). Phase 15's localStorage crash-recovery (FE-05, already shipped) handles the re-query case. If the planner disagrees, persisting candidates is a small addendum — add a `noc_candidates` JSON column to `work_descriptions` and store them on map.

2. **Which embedding dimension does the conftest fixture use?**
   - What we know: Production `app.db` has 768-dim vectors. v1.0 conftest creates `FLOAT[768]` fixtures explicitly.
   - What's unclear: Nothing — this is confirmed. Use 768.
   - Recommendation: Fixture uses `FLOAT[768]`, embed mock returns `[0.1] * 768`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 + pytest-asyncio 0.24.0 |
| Config file | `v2/backend/pyproject.toml` (asyncio_mode = "auto") |
| Quick run command | `cd v2/backend && python -m pytest tests/test_noc_pipeline.py -q` |
| Full suite command | `cd v2/backend && python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NOC-01 | Stage 1 FTS5 returns NOC codes | unit | `pytest tests/test_noc_pipeline.py::test_fts5_stage_returns_noc_codes -x` | ❌ Wave 0 |
| NOC-01 | Stage 2 calls embed model | unit | `pytest tests/test_noc_pipeline.py::test_stage2_calls_embed_model -x` | ❌ Wave 0 |
| NOC-01 | Full 3-stage pipeline returns NOCRankingResult | integration | `pytest tests/test_noc_pipeline.py::test_pipeline_returns_candidates -x` | ❌ Wave 0 |
| NOC-01 | Verbatim guardrail strips fabricated duties | unit | `pytest tests/test_noc_pipeline.py::test_verbatim_guardrail_strips_fabricated -x` | ❌ Wave 0 |
| NOC-01 | Verbatim guardrail raises when all stripped | unit | `pytest tests/test_noc_pipeline.py::test_verbatim_guardrail_raises_when_all_stripped -x` | ❌ Wave 0 |
| NOC-01 | _fts_query_from_text strips stop words | unit | `pytest tests/test_noc_pipeline.py::test_fts5_query_rewriting_strips_stop_words -x` | ❌ Wave 0 |
| NOC-01 | Empty work description raises 422 | unit | `pytest tests/test_noc_pipeline.py::test_fts5_query_empty_after_filtering_raises -x` | ❌ Wave 0 |
| API-04 | POST /api/noc/map returns 200 with candidates | integration | `pytest tests/test_noc_pipeline.py::test_api_route_200 -x` | ❌ Wave 0 |
| API-04 | POST /api/noc/map with empty shortlist returns 422 | integration | `pytest tests/test_noc_pipeline.py::test_empty_fts_result_raises_422 -x` | ❌ Wave 0 |
| NOC-02 | NOCCandidate schema validates noc_code, teer, matched_duties | unit | `pytest tests/test_noc_pipeline.py::TestNOCCandidateSchema -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd v2/backend && python -m pytest tests/test_noc_pipeline.py -q`
- **Per wave merge:** `cd v2/backend && python -m pytest tests/ -q`
- **Phase gate:** Full suite green (27 existing + ~10 new) before `/gsd-verify-work 14`

### Wave 0 Gaps

- [ ] `tests/test_noc_pipeline.py` — all NOC-01, API-04, NOC-02 schema tests (stubs first)
- [ ] `tests/conftest.py` — add `noc_mapping_db` fixture (768-dim synthetic data)
- [ ] `requirements.txt` — add sqlite-vec, instructor, ollama

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user local app |
| V3 Session Management | no | Single-user local app |
| V4 Access Control | no | Single-user local app |
| V5 Input Validation | yes | Pydantic `min_length=10` on `work_description`; parameterized MATCH ? for FTS5 |
| V6 Cryptography | no | No cryptographic operations in this phase |

### Known Threat Patterns for SQLite + FTS5

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| FTS5 injection via work_description text | Tampering | Parameterized MATCH ? — never string interpolation (non-negotiable from v1.0 architecture) |
| Path traversal via NOC_DB_PATH | Elevation of Privilege | v2 `db_path` validator pattern should apply to `noc_db_path` too — validate it is under PROJECT_ROOT or a known allowed path |
| Ollama SSRF via `ollama_base_url` | Spoofing | v1.0's `ollama_url_must_be_localhost` validator must be ported to v2 Settings |

---

## Sources

### Primary (HIGH confidence)
- `/home/charles/job_description_builder/app/services/noc_mapper.py` — full pipeline implementation read
- `/home/charles/job_description_builder/app/ai/noc_ranking.py` — instructor singleton + NOCCandidate/NOCRankingResult models
- `/home/charles/job_description_builder/app/api/noc_mapping.py` — v1.0 route pattern
- `/home/charles/job_description_builder/app/db.py` — get_connection + sqlite-vec loading
- `/home/charles/job_description_builder/v2/backend/app/config.py` — v2 Settings pattern (lazy get_settings)
- `/home/charles/job_description_builder/v2/backend/app/db.py` — v2 WD connection factory
- `/home/charles/job_description_builder/v2/backend/app/main.py` — lifespan + router mounting
- `/home/charles/job_description_builder/v2/backend/app/models/work_description.py` — current v2 WD model (no NOC fields)
- `/home/charles/job_description_builder/v2/backend/app/models/classification.py` — v2 Classification model
- `/home/charles/job_description_builder/v2/backend/requirements.txt` — current v2 deps (missing sqlite-vec/instructor/ollama)
- `/home/charles/job_description_builder/tests/test_noc_mapping.py` — v1.0 test suite to adapt
- `/home/charles/job_description_builder/tests/test_noc_ranking.py` — v1.0 schema tests to adapt
- Live probe: `python3 -c "import sqlite_vec; sqlite_vec.load(con)..."` — ARM64 vec0 confirmed working
- Live probe: `python3 -m pip show sqlite-vec` — version 0.1.9 confirmed
- Live probe: `ollama list` — gemma4:31b + nomic-embed-text:latest confirmed present
- Live probe: `app.db` vector dimension — 768 confirmed, 6119 chunks, 516 units

### Secondary (MEDIUM confidence)
- `/home/charles/job_description_builder/v2/frontend/src/components.jsx` — existing input control patterns for NocConfirmCard design

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified installed and working on Jane ARM64
- Architecture: HIGH — source code read directly; porting path is clear
- Pitfalls: HIGH — most pitfalls identified from direct v1.0 test suite analysis
- Frontend component: MEDIUM — NocConfirmCard pattern inferred from ChoiceList; no existing NOC card in prototype

**Research date:** 2026-06-04
**Valid until:** 2026-07-04 (stable ecosystem; Ollama model availability could change)
