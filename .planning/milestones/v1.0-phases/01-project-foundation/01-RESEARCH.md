# Phase 1: Project Foundation — Research

**Researched:** 2026-05-28
**Domain:** FastAPI skeleton + Pydantic data models + SQLite schema + environment config + Ollama pre-warm
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | WorkDescription Pydantic model and SQLite schema finalized — TBS WD fields, wd_audit_log table, ProvenanceTag on every content element | Model design patterns in Architecture Patterns section; SQLite schema in Code Examples |
| DATA-02 | Runtime config from env vars with startup validation — missing vars cause immediate failure with descriptive error | pydantic-settings 2.14.1 confirmed installed; startup validation pattern in Code Examples |
| DATA-03 | App pre-warms Ollama connection and confirms required models present at startup — fail loudly if missing | Ollama 0.6.1 confirmed; model list verified on hardware; lifespan pattern in Code Examples |

</phase_requirements>

---

## Summary

Phase 1 establishes the skeleton that every subsequent phase builds on. No feature code, no pipelines — just the structural contracts that make the rest of the project possible: a FastAPI app that starts cleanly, validates its environment, pre-warms its LLM dependency, and exposes the finalized data models that every service will write to.

The entire tech stack is already installed on the Jetson AGX Orin (FastAPI 0.128.8, Pydantic 2.12.5, Uvicorn 0.40.0, Ollama 0.6.1, instructor 1.15.1, pydantic-settings 2.14.1). One notable gap: `sqlite-vec` is not installed — it must be added in Phase 1 (`pip install sqlite-vec`) because the SQLite schema will reference it and Phase 2 needs it. The Ollama service is running with the required models present (`qwen3.6:latest`, `nomic-embed-text:latest`).

The two design decisions with the most downstream impact are (1) the shape of `ProvenanceTag` and `WorkDescription` — every service in Phases 3–8 writes to these; changing them later is expensive — and (2) the startup validation sequence, which must cover env vars, Ollama reachability, and model presence before the app begins serving requests.

**Primary recommendation:** Use `pydantic-settings` with a `Settings` class for env validation, FastAPI's `lifespan` async context manager for startup/shutdown hooks (Ollama pre-warm + model check), and define `ProvenanceTag` + `WorkDescription` in a single `app/models/work_description.py` file that is imported by everything else. Schema is never re-derived — it is the source of truth.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Environment config validation | API / Backend | — | All config loaded server-side at startup; no client-side config |
| Ollama pre-warm + model check | API / Backend | — | Ollama runs as a local service; backend makes the health call |
| WorkDescription / ProvenanceTag models | API / Backend | — | Pydantic models are server-side contracts; exported to client as JSON schema only |
| SQLite schema creation | Database / Storage | — | DDL runs once at startup via `app.db.py`; no client involvement |
| Health endpoint | API / Backend | — | `GET /health` returns JSON; HTMX/browser is a consumer |
| Static assets (HTMX, Alpine.js) | CDN / Static | Frontend Server | Loaded from CDN in templates; no build step |

---

## Standard Stack

### Core (Phase 1 scope)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| FastAPI | 0.128.8 | ASGI web framework, StreamingResponse, OpenAPI | CONFIRMED installed |
| Uvicorn | 0.40.0 | ASGI server (`uvicorn app.main:app --reload`) | CONFIRMED installed |
| Pydantic | 2.12.5 | Data validation, model contracts, LLM output schemas | CONFIRMED installed |
| pydantic-settings | 2.14.1 | Settings from env vars with validation + `.env` file support | CONFIRMED installed |
| ollama (official) | 0.6.1 | Ollama Python client — AsyncClient for streaming, sync for startup checks | CONFIRMED installed |
| instructor | 1.15.1 | Retry wrapper for structured LLM outputs (not used in Phase 1, but declared in requirements.txt) | CONFIRMED installed |
| Jinja2 | 3.1.6 | HTML template rendering for FastAPI (`Jinja2Templates`) | CONFIRMED installed |
| sqlite-vec | 0.1.9 | SQLite vector search extension — not yet installed; must be added in Phase 1 | NOT YET INSTALLED |

### Why sqlite-vec must be installed in Phase 1

The `app/db.py` schema creation function will run `CREATE VIRTUAL TABLE ... USING vec0(...)` DDL at startup once sqlite-vec is registered. If the extension is not installed when the schema is first created, the table is missing and Phase 2 ingest cannot write embeddings. Install now; create the table now.

**Installation:**
```bash
pip install sqlite-vec
```

### Not in Phase 1 scope but will appear in requirements.txt

DuckDB 1.5.3, Polars 1.41.1, python-docx, docxtpl, WeasyPrint — declared as dependencies now so the venv is complete, but not exercised until their phases.

### Alternatives Considered

| Standard | Alternative | Why Standard Wins |
|----------|-------------|-------------------|
| pydantic-settings | python-decouple, dynaconf, raw `os.environ` | pydantic-settings integrates natively with Pydantic v2; Settings class validates types and reports missing vars with field names |
| FastAPI lifespan | `@app.on_event("startup")` | `on_event` is deprecated in FastAPI 0.93+; lifespan is the current pattern |
| SQLite stdlib + sqlite-vec | SQLAlchemy + Alembic | No ORM needed for this schema; direct sqlite3 gives full control over DDL and schema versioning |

---

## Architecture Patterns

### System Architecture Diagram

```
[Environment / .env file]
        |
        v
[pydantic-settings Settings]  ←  Fails loudly on missing required vars
        |
        v
[FastAPI lifespan startup]
   ├── check Ollama reachable (GET /api/tags)
   ├── assert required models present (qwen3.6, nomic-embed-text)
   ├── create SQLite schema (work_descriptions, wd_audit_log, vec tables)
   └── app ready → BEGIN SERVING
        |
        v
[GET /health]  →  {"status": "ok", "ollama_models": [...], "missing_models": []}
        |
        v
[app/models/work_description.py]
   ├── ProvenanceTag  (imported by every service in Phases 3–8)
   ├── WorkDescription  (the accumulator entity; persisted as JSON to SQLite)
   └── Sub-models: NOCMatch, DraftDuty, OGRecommendation, JESFactorScore, ...
```

### Recommended Project Structure

```
app/
├── main.py              # FastAPI app, lifespan, route registration
├── config.py            # pydantic-settings Settings class
├── db.py                # SQLite connection, schema creation, sqlite-vec registration
├── models/
│   └── work_description.py  # ProvenanceTag, WorkDescription, all sub-models
├── api/
│   └── health.py        # GET /health route
├── templates/
│   └── base.html        # Jinja2 base template (HTMX + Alpine.js CDN links)
└── static/              # empty — CSS lives here when added
tests/
├── conftest.py          # pytest fixtures (test app, temp DB)
├── test_config.py       # env validation tests
├── test_models.py       # WorkDescription + ProvenanceTag unit tests
└── test_health.py       # /health endpoint smoke tests
requirements.txt
.env.example             # documents all required env vars with example values
```

### Pattern 1: pydantic-settings for Environment Validation

**What:** Declare all required config as a Pydantic `Settings` class; missing or invalid vars raise `ValidationError` at import time.
**When to use:** Every runtime config value — model names, file paths, Ollama URL.

```python
# Source: pydantic-settings docs + verified installed 2.14.1
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_generation_model: str = Field(..., description="Required: e.g. qwen3.6:latest")
    ollama_embed_model: str = Field(..., description="Required: e.g. nomic-embed-text:latest")

    # Database
    db_path: str = Field(..., description="Required: e.g. /home/charles/job_description_builder/app.db")

    # Data paths
    data_dir: str = Field(..., description="Required: absolute path to data/ directory")

settings = Settings()  # Fails at import if required fields are missing
```

**Why `Field(...)` with no default:** Pydantic raises `ValidationError` immediately, naming the missing field. The error is surfaced before Uvicorn begins serving — the process exits with a clear message.

### Pattern 2: FastAPI lifespan for Startup Validation

**What:** Async context manager that runs pre-serve checks (Ollama reachability, model presence, SQLite schema) before the app accepts requests.
**When to use:** Any startup-time assertion that must block serving if it fails.

```python
# Source: FastAPI docs — lifespan pattern (on_event deprecated in 0.93+)
from contextlib import asynccontextmanager
from fastapi import FastAPI
import ollama

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    await assert_ollama_ready()
    create_schema()
    yield
    # --- shutdown ---
    pass

async def assert_ollama_ready():
    """Fail loudly if Ollama is not reachable or required models are absent."""
    client = ollama.AsyncClient(host=settings.ollama_base_url)
    try:
        response = await client.list()
        available = {m.model for m in response.models}
    except Exception as e:
        raise RuntimeError(
            f"Ollama is not reachable at {settings.ollama_base_url}. "
            f"Ensure the Ollama service is running. Error: {e}"
        ) from e

    required = {settings.ollama_generation_model, settings.ollama_embed_model}
    missing = required - available
    if missing:
        raise RuntimeError(
            f"Required Ollama models are not present: {missing}. "
            f"Run: ollama pull <model> for each missing model."
        )

app = FastAPI(lifespan=lifespan)
```

**Key decision:** `raise RuntimeError` (not a warning, not a log). Uvicorn treats an unhandled exception in lifespan as a startup failure and exits with a non-zero code. This is the "loud failure" DATA-03 requires.

### Pattern 3: SQLite Schema + sqlite-vec Registration

**What:** Register the sqlite-vec extension then run DDL once at startup (idempotent with `IF NOT EXISTS`).
**When to use:** Phase 1 startup.

```python
# Source: sqlite-vec README (verified 0.1.9 aarch64 wheel)
import sqlite3
import sqlite_vec

def get_connection(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    return con

def create_schema(con: sqlite3.Connection) -> None:
    con.executescript("""
        CREATE TABLE IF NOT EXISTS work_descriptions (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            data JSON NOT NULL,
            created_at TEXT NOT NULL,
            last_modified TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS wd_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wd_id TEXT NOT NULL,
            event TEXT NOT NULL,
            actor TEXT NOT NULL,
            detail JSON,
            timestamp TEXT NOT NULL
        );

        -- Vec tables added in Phase 2 when embeddings are indexed
        -- Placeholder to validate sqlite-vec loads cleanly:
        CREATE TABLE IF NOT EXISTS _vec_health_check (id INTEGER PRIMARY KEY);
    """)
    con.commit()
```

**Note on vec tables:** The full `CREATE VIRTUAL TABLE noc_chunks_vec USING vec0(...)` DDL belongs in Phase 2 when the embedding dimensions are fixed. Phase 1 only validates that sqlite-vec loads without error.

### Pattern 4: WorkDescription + ProvenanceTag Model

**What:** The canonical data model. Finalized here; never changed without a migration.

```python
# Source: ARCHITECTURE.md design + DATA-01 requirements
from __future__ import annotations
from typing import Literal, Optional
from datetime import date, datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class ProvenanceTag(BaseModel):
    """Carries the authoritative source for every content element in a WorkDescription."""
    source_type: Literal[
        "NOC",           # NOC 2021 unit group profile
        "CA",            # Collective agreement article
        "JES",           # Job Evaluation Standard factor
        "TBS_OG_DEF",    # TBS OCHRO OG definition / inclusions / exclusions
        "TBS_DIRECTIVE", # TBS Directive on Classification
        "QUAL_STD",      # TBS Qualification Standard
        "DRF",           # DND Departmental Results Framework
        "ADVISOR",       # Entered directly by advisor — no authoritative source
        "AI_GENERATED",  # AI-generated text with no verbatim source match
    ]
    source_id: str        # "21232", "AI CA 2026 Article 5.02", "CT JES 2023 Skill L3"
    source_version: str   # "NOC 2021", "AI CA 2026-2029", "CT JES 2023"
    source_url: Optional[str] = None
    retrieved_date: date
    model_name: Optional[str] = None      # if AI_GENERATED
    prompt_version: Optional[str] = None  # if AI_GENERATED
    modified_by_advisor: bool = False

class NOCMatch(BaseModel):
    noc_code: str
    noc_title: str
    teer_level: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    matched_duty_statements: list[str] = Field(default_factory=list)
    provenance: ProvenanceTag

class DraftDuty(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    text: str
    provenance: ProvenanceTag
    advisor_modified: bool = False
    advisor_modified_text: Optional[str] = None

class OGRecommendation(BaseModel):
    og_code: str
    og_name: str
    level: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    evidence_quotes: list[str] = Field(default_factory=list)
    cited_articles: list[ProvenanceTag] = Field(default_factory=list)
    confirmed_by_advisor: bool = False

class JESFactorScore(BaseModel):
    factor_name: str
    level: int
    points: Optional[int] = None
    rationale: str
    evidence_quotes: list[str] = Field(default_factory=list)
    provenance: ProvenanceTag
    advisor_adjusted: bool = False
    advisor_adjusted_level: Optional[int] = None
    advisor_adjustment_rationale: Optional[str] = None

class DraftText(BaseModel):
    """Any AI-generated or sourced text block with provenance."""
    text: str
    provenance: ProvenanceTag

class WorkDescription(BaseModel):
    """
    Central entity. Created at first advisor input, persisted to SQLite after
    every state transition. Export renders directly from this — no reconstruction.
    """
    id: UUID = Field(default_factory=uuid4)
    session_id: str

    # TBS-required header fields (DATA-01)
    position_title: Optional[str] = None
    position_number: Optional[str] = None
    og_level: Optional[str] = None           # "EC-04"
    supervisor_title: Optional[str] = None
    supervisor_position_number: Optional[str] = None
    review_date: Optional[date] = None
    organizational_context: Optional[DraftText] = None

    # Stage: NL input
    raw_input: str
    input_timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Stage: NOC mapping
    noc_candidates: list[NOCMatch] = Field(default_factory=list)
    confirmed_noc: Optional[NOCMatch] = None

    # Stage: OG classification
    og_recommendation: Optional[OGRecommendation] = None
    confirmed_og: Optional[str] = None
    confirmed_level: Optional[str] = None

    # Stage: JD content
    draft_duties: list[DraftDuty] = Field(default_factory=list)
    advisor_additions: list[DraftDuty] = Field(default_factory=list)  # ADVISOR provenance

    # Stage: JES scoring
    jes_scores: list[JESFactorScore] = Field(default_factory=list)
    jes_total_points: Optional[int] = None

    # Metadata
    stage: Literal[
        "input", "noc_mapped", "og_classified",
        "jd_drafted", "jes_scored", "exported"
    ] = "input"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_modified: datetime = Field(default_factory=datetime.utcnow)
    export_hash: Optional[str] = None
    exported_at: Optional[datetime] = None
```

**Critical rule:** `advisor_additions` uses `source_type="ADVISOR"` provenance. When the advisor types free text with no source match, it is stored here — never mixed into `draft_duties` with a fabricated provenance. The export renders advisor additions with a distinct visual indicator.

### Anti-Patterns to Avoid

- **Using `@app.on_event("startup")`:** Deprecated in FastAPI 0.93+. Use `lifespan`. [VERIFIED: FastAPI docs]
- **Storing settings in module-level `os.environ` calls:** Race conditions in async startup; no type validation. Use `pydantic-settings` Settings class.
- **Creating the vec tables before sqlite-vec is loaded:** Extension must be registered before any DDL that references `vec0`. Register in `get_connection()`, not as a one-time call.
- **Defining ProvenanceTag differently in multiple files:** One definition, one import. The ARCHITECTURE.md pattern of "provenance as a field on every domain object" only works if the type is canonical.
- **Deferring TBS-required WD fields to a later phase:** DATA-01 requires the full model before any service code. Fields like `supervisor_title`, `review_date`, and `organizational_context` must be in the schema now even though they are populated in later phases.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env var loading with defaults + validation | Custom `os.environ.get()` chains | `pydantic-settings` BaseSettings | Type coercion, `.env` file support, ValidationError with field names — already installed |
| Startup lifecycle hooks | `atexit`, threading events | FastAPI `lifespan` context manager | Async-native, integrated with Uvicorn shutdown signals |
| Ollama model list check | Raw `httpx` GET to `/api/tags` | `ollama.AsyncClient().list()` | Official client returns typed `ListResponse`; handles auth headers and base URL |
| SQLite connection with extension loading | Raw `ctypes` loading of `.so` | `sqlite_vec.load(con)` | Extension handles platform-specific `.so` path resolution on ARM64 |
| JSON serialization of Pydantic models to SQLite | Custom `json.dumps` | `model.model_dump_json()` / `Model.model_validate_json()` | Pydantic v2 handles UUID, date, datetime, Literal serialization correctly |

---

## Common Pitfalls

### Pitfall 1: Missing Required Env Vars Don't Name the Missing Field

**What goes wrong:** Using `os.environ["VAR"]` raises `KeyError: 'VAR'` — correct behavior, but the error message in production logs is minimal. Startup logs may not preserve the exception detail.

**Why it happens:** Default Python env handling has no context about which vars are required vs. optional.

**How to avoid:** Use `pydantic-settings` `Field(...)` — the ValidationError includes field name, expected type, and "field required" in a structured format that Uvicorn logs will capture.

**Warning signs:** Any env var loaded with `os.environ.get("X")` with `None` as default when `X` is actually required.

---

### Pitfall 2: Ollama lifespan Check Succeeds but Wrong Model Name String

**What goes wrong:** `settings.ollama_generation_model = "qwen3.6"` (no `:latest` tag). Ollama model names are `name:tag`. The list check compares `"qwen3.6"` against `"qwen3.6:latest"` — they don't match — startup fails even though the model is present.

**Why it happens:** Ollama normalizes model names to `name:tag` format in `ollama list` output. The configured name must match exactly.

**How to avoid:** Default values in `.env.example` must include the tag: `OLLAMA_GENERATION_MODEL=qwen3.6:latest`. Add a normalization step: if the configured name has no `:`, append `:latest` before comparison.

**Warning signs:** Startup failure on a machine where `ollama list` shows the model.

---

### Pitfall 3: sqlite-vec Extension Not Loaded Before Schema Creation

**What goes wrong:** `create_schema()` is called before `sqlite_vec.load(con)`. The `CREATE VIRTUAL TABLE ... USING vec0(...)` DDL (added in Phase 2) fails with "no such module: vec0".

**Why it happens:** SQLite extensions must be registered per-connection. A new connection without `sqlite_vec.load()` is missing the extension even if it was loaded on a previous connection.

**How to avoid:** Always call `sqlite_vec.load(con)` in the `get_connection()` factory. Never create a bare `sqlite3.connect()` without going through the factory.

**Warning signs:** "no such module: vec0" at schema creation or query time.

---

### Pitfall 4: WorkDescription Schema Change After Phase 2 Services Write to It

**What goes wrong:** A field is renamed or a sub-model is restructured after Phase 2 has code that serializes WorkDescription to JSON in SQLite. Existing rows can't be deserialized because the JSON structure no longer matches the Pydantic model.

**Why it happens:** SQLite stores the WD as `data JSON` — it's a blob. Schema changes in the Pydantic model are not automatically reflected in stored rows.

**How to avoid:** Finalize the model in Phase 1. Any change after Phase 2 begins requires a migration script (`UPDATE work_descriptions SET data = ...`) and a version bump in the `stage` field or a new `schema_version` column.

**Warning signs:** `ValidationError` when loading a stored WD from the database.

---

### Pitfall 5: Ollama Model Name in List Uses Full Digest vs. Configured Tag

**What goes wrong:** `ollama.AsyncClient().list()` returns model names including digest prefixes for some locally-modified models (e.g., `qwen3.6-planner:latest` exists on this machine as a custom modelfile). The comparison logic must check exact name match, not prefix match.

**Why it happens:** This machine has custom role-specific modelfiles (`qwen3.6-planner`, `qwen3.6-implementer`, etc.). The check should only care about `qwen3.6:latest` and `nomic-embed-text:latest`, not those custom variants.

**How to avoid:** Use exact set membership check: `required = {settings.ollama_generation_model, settings.ollama_embed_model}; missing = required - available`. This is the pattern shown in Pattern 2.

---

## Code Examples

### Health Endpoint

```python
# app/api/health.py
from fastapi import APIRouter
from app.config import settings
import ollama

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Returns 200 if app started cleanly (Ollama reachable + models present).
    Returns model availability status for observability.
    """
    try:
        client = ollama.AsyncClient(host=settings.ollama_base_url)
        response = await client.list()
        available_models = [m.model for m in response.models]
        required = [settings.ollama_generation_model, settings.ollama_embed_model]
        missing = [m for m in required if m not in available_models]
        return {
            "status": "ok" if not missing else "degraded",
            "ollama_url": settings.ollama_base_url,
            "required_models": required,
            "missing_models": missing,
            "all_available_models": available_models,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}
```

### Env Validation — Missing Var Behavior

```python
# Demonstrates the startup failure behavior for DATA-02
# Run: OLLAMA_GENERATION_MODEL="" python3 -c "from app.config import settings"
# Expected output includes field name in ValidationError
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    ollama_generation_model: str = Field(..., description="Required Ollama generation model name with tag")
    # ValidationError if missing:
    # 1 validation error for Settings
    # ollama_generation_model
    #   Field required [type=missing, input_value={}, input_url=...]
```

### ProvenanceTag Usage at Retrieval Time

```python
# The pattern every Phase 3–8 service follows:
# ProvenanceTag is attached at retrieval, not post-hoc.
from app.models.work_description import ProvenanceTag, DraftDuty
from datetime import date
from uuid import uuid4

def build_draft_duty_from_noc(row: dict) -> DraftDuty:
    """
    Called when a NOC duty statement row is retrieved from the database.
    ProvenanceTag is populated from the row's source metadata — never inferred later.
    """
    return DraftDuty(
        id=uuid4(),
        text=row["statement_text"],
        provenance=ProvenanceTag(
            source_type="NOC",
            source_id=row["noc_code"],
            source_version=row["noc_version"],   # "NOC 2021"
            source_url=row.get("source_url"),
            retrieved_date=date.today(),
        )
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `lifespan` async context manager | FastAPI 0.93 (2023) | `on_event` still works but deprecated; use lifespan |
| `python-dotenv` + `os.environ` | `pydantic-settings` BaseSettings | Pydantic v2 release (2023) | Type-validated settings with clear error messages |
| `format="json"` in Ollama | `format=Model.model_json_schema()` | Ollama v0.5 (2024) | Token-level grammar constraint vs. prompt engineering |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| FastAPI | Web framework | Yes | 0.128.8 | — |
| Uvicorn | ASGI server | Yes | 0.40.0 | — |
| Pydantic | Data models | Yes | 2.12.5 | — |
| pydantic-settings | Env config | Yes | 2.14.1 | — |
| ollama (Python) | LLM client | Yes | 0.6.1 | — |
| instructor | Structured output retry | Yes | 1.15.1 | — |
| Jinja2 | Templates | Yes | 3.1.6 | — |
| sqlite-vec | SQLite vector extension | **No** | 0.1.9 target | No fallback — must install |
| Ollama service | Model inference | Yes | Running | — |
| qwen3.6:latest | Generation model | Yes | Confirmed in `ollama list` | — |
| nomic-embed-text:latest | Embedding model | Yes | Confirmed in `ollama list` | — |
| pytest | Test framework | Yes | 9.0.2 | — |

**Missing dependencies with no fallback:**
- `sqlite-vec` is not installed. `pip install sqlite-vec` is a Wave 0 task for Phase 1. The 0.1.9 aarch64 wheel resolves cleanly (verified in STACK.md).

**Missing dependencies with fallback:**
- None for Phase 1 scope.

**Note on Ollama model names:** This machine has custom role-specific modelfiles (`qwen3.6-planner:latest`, `qwen3.6-implementer:latest`, etc.). The app config should target `qwen3.6:latest` (the base model), not the role variants. Verify `.env.example` documents this explicitly.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` or `pytest.ini` — Wave 0 creates this |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | WorkDescription model instantiates with all TBS fields | unit | `pytest tests/test_models.py::test_work_description_instantiation -x` | Wave 0 |
| DATA-01 | ProvenanceTag required on every content sub-model | unit | `pytest tests/test_models.py::test_provenance_tag_required -x` | Wave 0 |
| DATA-01 | SQLite schema creates work_descriptions and wd_audit_log tables | unit | `pytest tests/test_db.py::test_schema_creation -x` | Wave 0 |
| DATA-01 | sqlite-vec loads and _vec_health_check table is created | unit | `pytest tests/test_db.py::test_sqlite_vec_loads -x` | Wave 0 |
| DATA-02 | Missing OLLAMA_GENERATION_MODEL raises ValidationError at settings import | unit | `pytest tests/test_config.py::test_missing_required_var_raises -x` | Wave 0 |
| DATA-02 | ValidationError message names the missing field | unit | `pytest tests/test_config.py::test_missing_var_error_names_field -x` | Wave 0 |
| DATA-03 | `/health` returns 200 with Ollama model status | smoke | `pytest tests/test_health.py::test_health_endpoint_200 -x` | Wave 0 |
| DATA-03 | App startup raises RuntimeError when Ollama unreachable | integration | `pytest tests/test_startup.py::test_startup_fails_ollama_unreachable -x` | Wave 0 |
| DATA-03 | App startup raises RuntimeError when required model missing | integration | `pytest tests/test_startup.py::test_startup_fails_missing_model -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/conftest.py` — shared fixtures: test FastAPI app, temp SQLite DB path, mock Ollama client
- [ ] `tests/test_models.py` — WorkDescription + ProvenanceTag unit tests
- [ ] `tests/test_config.py` — env validation tests (uses `monkeypatch.delenv`)
- [ ] `tests/test_db.py` — schema creation tests
- [ ] `tests/test_health.py` — health endpoint smoke test
- [ ] `tests/test_startup.py` — lifespan startup failure tests (mock Ollama)
- [ ] `pyproject.toml` — pytest config, testpaths, asyncio mode for FastAPI lifespan tests
- [ ] Framework install: already installed (pytest 9.0.2)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Single-user local app; no auth in Phase 1 |
| V3 Session Management | No | No session tokens in Phase 1 |
| V4 Access Control | No | No roles or permissions in Phase 1 |
| V5 Input Validation | Yes | pydantic-settings validates all config inputs at startup |
| V6 Cryptography | No | No secrets or encryption in Phase 1 |

### Known Threat Patterns for Phase 1 Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `db_path` env var | Tampering | Validate `db_path` is under the project directory in Settings validator |
| Ollama base URL pointing to external host | Elevation of Privilege | Document in `.env.example` that `OLLAMA_BASE_URL` must be localhost; no auth token for external hosts |
| SSL verification disabled (prototype anti-pattern) | Spoofing | Never `verify=False`; ollama Python client uses httpx with SSL on by default |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `qwen3.6:latest` is the correct model name to configure as the generation model (not `qwen3.6-planner:latest` or another role variant) | Standard Stack / Environment Availability | Startup model check fails; need to update `.env` |
| A2 | sqlite-vec 0.1.9 wheel resolves cleanly via `pip install sqlite-vec` on this machine (verified in STACK.md via dry-run, but not yet actually installed) | Standard Stack | Install may fail; fallback is manual wheel or compiling from source |
| A3 | The `ollama.AsyncClient().list()` response `.models[n].model` attribute returns the full `name:tag` string (e.g., `"qwen3.6:latest"`) | Code Examples | Model name comparison in lifespan check breaks; need to inspect actual response object |

---

## Open Questions (RESOLVED)

1. **Which model should be the default generation model in `.env.example`?** [RESOLVED]
   - What we know: `qwen3.6:latest` (23 GB base), `qwen3.6-planner:latest`, and other role variants are all present
   - What's unclear: Whether the role variants have different system prompts baked in that would conflict with the app's own prompts
   - Recommendation: Use `qwen3.6:latest` as the default; document that role variants should not be used as `OLLAMA_GENERATION_MODEL`
   - **Resolution:** Plans use `qwen3.6:latest` in `.env.example`; role variants excluded from `OLLAMA_GENERATION_MODEL`

2. **Should the `WorkDescription` model include a `schema_version` field now?** [RESOLVED]
   - What we know: The WD is persisted as JSON to SQLite; Pydantic model changes after Phase 2 require migration scripts
   - What's unclear: Whether a simple integer version field is sufficient or whether a formal migration library (Alembic, yoyo) is needed
   - Recommendation: Add `schema_version: int = 1` to `WorkDescription` now; implement a `migrate_wd_json()` function stub; defer formal migration tooling to when a schema change actually occurs
   - **Resolution:** `schema_version: int = 1` added to WorkDescription in Plan 01-02; migration tooling deferred

3. **Should `wd_audit_log` track model version alongside event data?** [RESOLVED]
   - What we know: DATA-01 requires `wd_audit_log`; PITFALLS.md CRITICAL-05 requires version tracking for defensibility
   - What's unclear: Whether audit log entries need `ollama_model_version` in `detail JSON` or if that belongs only in `work_descriptions.data`
   - Recommendation: Add `model_name` to `detail JSON` for any audit event triggered by an LLM call; store it in the `ProvenanceTag` on the WD entity, not duplicated in the log
   - **Resolution:** `model_name` stored in ProvenanceTag only; `detail JSON` in audit log is unstructured — model name not duplicated

---

## Sources

### Primary (HIGH confidence)

- Stack verified on hardware: `/home/charles/job_description_builder/.planning/research/STACK.md` — all packages confirmed via pip or Ollama list
- Architecture design: `/home/charles/job_description_builder/.planning/research/ARCHITECTURE.md` — ProvenanceTag, WorkDescription, SQLite schema patterns
- Requirements: `/home/charles/job_description_builder/.planning/REQUIREMENTS.md` — DATA-01, DATA-02, DATA-03 definitions
- Decisions: `/home/charles/job_description_builder/.planning/STATE.md` — locked architecture non-negotiables
- pydantic-settings 2.14.1 confirmed installed on this machine [VERIFIED: pip show]
- ollama 0.6.1 confirmed installed; models verified via `ollama list` [VERIFIED: CLI]
- pytest 9.0.2 confirmed installed [VERIFIED: CLI]
- FastAPI lifespan pattern: https://fastapi.tiangolo.com/advanced/events/ [CITED]
- sqlite-vec aarch64 wheel availability: STACK.md prior dry-run verification [VERIFIED]

### Secondary (MEDIUM confidence)

- Ollama AsyncClient `.list()` response shape: https://github.com/ollama/ollama-python [CITED — not re-verified in this session]

### Tertiary (LOW confidence)

- None — all Phase 1 claims verified against installed packages or locked architecture decisions.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages confirmed installed; sqlite-vec only gap (install in Wave 0)
- Architecture: HIGH — derived from locked decisions in STATE.md + architecture research
- Pitfalls: HIGH — directly from PITFALLS.md prototype failures + pydantic/FastAPI verified patterns

**Research date:** 2026-05-28
**Valid until:** 2026-08-28 (90 days — stable framework stack; pydantic-settings API stable since v2)
