# Phase 4: NL→NOC Mapping — Pattern Map

**Mapped:** 2026-06-01
**Files analyzed:** 11 new/modified files
**Analogs found:** 10 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/ai/noc_ranking.py` | model/service | request-response | `app/models/work_description.py` + AI-SPEC patterns | role-match (Pydantic models) |
| `app/services/noc_mapper.py` | service | request-response | `scripts/ingest_noc.py` (SQLite + asyncio.to_thread pattern) | partial-match |
| `app/services/wd_store.py` | service | CRUD | `app/db.py` (connection factory + schema helpers) | role-match |
| `app/api/noc_mapping.py` | controller | request-response | `app/api/health.py` | exact |
| `app/models/noc.py` | model | request-response | `app/models/work_description.py` | exact |
| `templates/partials/noc_results.html` | component | request-response | `app/templates/base.html` (Jinja2 block structure) | partial-match |
| `templates/wizard/step_noc.html` | component | request-response | `app/templates/base.html` | role-match |
| `scripts/rebuild_noc_vectors.py` | utility | batch | `scripts/ingest_noc.py` | exact |
| `tests/test_noc_mapping.py` | test | request-response | `tests/test_health.py` + `tests/test_noc_ingest.py` | exact |
| `tests/test_noc_ranking.py` | test | request-response | `tests/test_noc_ingest.py` | exact |
| `tests/conftest.py` (update) | config | — | `tests/conftest.py` (existing) | exact |

---

## Pattern Assignments

### `app/ai/noc_ranking.py` (model + service, request-response)

**Analogs:** `app/models/work_description.py` (Pydantic patterns), AI-SPEC Section 4b (instructor client)

**Imports pattern** — copy from `app/models/work_description.py` lines 1–14 and extend:
```python
from __future__ import annotations

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, field_validator

from app.config import settings
```

**Pydantic model pattern** — copy `NOCCandidate` and `NOCRankingResult` from AI-SPEC Section 4b verbatim. The field_validator pattern mirrors `app/models/work_description.py` where `ProvenanceTag` and `NOCMatch` use `Field(ge=0.0, le=1.0)` constraints (lines 43–49):
```python
class NOCCandidate(BaseModel):
    noc_code: str = Field(..., pattern=r"^\d{5}$", description="5-digit NOC 2021 unit group code")
    title: str = Field(..., min_length=3)
    teer: int = Field(..., ge=0, le=5, description="TEER level 0-5")
    rank: int = Field(..., ge=1, le=10)
    matched_duties: list[str] = Field(..., min_length=1, description="Verbatim duty statements...")
    justification: str = Field(..., min_length=30)

    @field_validator("noc_code")
    @classmethod
    def noc_code_all_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError(f"noc_code must be all digits, got: {v!r}")
        return v

    @field_validator("matched_duties")
    @classmethod
    def duties_not_blank(cls, v: list[str]) -> list[str]:
        if any(not s.strip() for s in v):
            raise ValueError("matched_duties must not contain blank strings")
        return v


class NOCRankingResult(BaseModel):
    candidates: list[NOCCandidate] = Field(..., min_length=1, max_length=5)

    @field_validator("candidates")
    @classmethod
    def ranks_are_sequential(cls, v: list[NOCCandidate]) -> list[NOCCandidate]:
        ranks = sorted(c.rank for c in v)
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError(f"candidate ranks must be 1..N with no gaps or duplicates, got: {ranks}")
        return v
```

**Module-level singleton pattern** — this is the ONLY new pattern in the project; no existing analog. Copy from AI-SPEC Section 4b lines 540–548:
```python
instructor_client = instructor.from_openai(
    AsyncOpenAI(
        base_url=settings.ollama_base_url.rstrip("/") + "/v1",
        api_key="ollama",
    ),
    mode=instructor.Mode.JSON,
)
```

**Critical:** `settings` is imported from `app.config` — same singleton pattern used in `app/api/health.py` line 10 (`from app.config import settings`).

---

### `app/services/noc_mapper.py` (service, request-response)

**Analog:** `scripts/ingest_noc.py` — provides the asyncio.to_thread + SQLite lambda pattern; `app/api/health.py` — provides the `OllamaAsyncClient` usage pattern.

**Imports pattern** — synthesized from ingest_noc.py lines 27–35 and AI-SPEC Section 4:
```python
from __future__ import annotations

import asyncio
import hashlib
import sqlite3

import sqlite_vec
from ollama import AsyncClient as OllamaAsyncClient

from app.ai.noc_ranking import instructor_client, NOCRankingResult, NOCCandidate
from app.config import settings
from app.db import get_connection
from app.models.work_description import NOCMatch, ProvenanceTag
```

**Connection lifecycle pattern** — copy from `scripts/ingest_noc.py` `load_connection()` (lines 82–96), adapted for async + per-request usage per RESEARCH.md Pattern 3:
```python
conn = await asyncio.to_thread(lambda: get_connection(settings.db_path))
try:
    # ... all SQLite calls ...
finally:
    await asyncio.to_thread(conn.close)
```

**Stage 1 FTS5 query** — use RESEARCH.md Pattern 1 (not the AI-SPEC query — it has wrong columns). The `asyncio.to_thread(lambda: ...)` pattern mirrors `scripts/ingest_noc.py` line 334 (`recreate_vec_table_if_needed`):
```python
fts_rows = await asyncio.to_thread(
    lambda: conn.execute(
        """
        SELECT DISTINCT f.noc_code, u.title,
               CAST(u.teer_level AS INTEGER) AS teer,
               u.definition
        FROM noc_fts f
        JOIN noc_units u ON u.noc_code = f.noc_code
        WHERE noc_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (work_description, fts_limit),
    ).fetchall()
)
if not fts_rows:
    raise ValueError("FTS5 shortlist empty — work description has no lexical overlap with NOC corpus")
```

**Stage 2 sqlite-vec KNN query** — copy from RESEARCH.md Pattern 2. The `sqlite_vec.serialize_float32()` usage mirrors `scripts/ingest_noc.py` line 393:
```python
embed_resp = await OllamaAsyncClient(host=settings.ollama_base_url).embed(
    model=settings.ollama_embed_model,
    input=work_description,
)
query_vec: list[float] = embed_resp.embeddings[0]

fts_codes = [row[0] for row in fts_rows]
placeholders = ",".join("?" * len(fts_codes))

vec_rows = await asyncio.to_thread(
    lambda: conn.execute(
        f"""
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
        (sqlite_vec.serialize_float32(query_vec), *fts_codes, rerank_limit),
    ).fetchall()
)
```

**Stage 3 instructor call** — copy from AI-SPEC Section 4 lines 382–411 (the `instructor_client.chat.completions.create()` block). Uses the module-level `instructor_client` singleton from `app/ai/noc_ranking.py`.

**Verbatim guardrail** — copy from RESEARCH.md `_check_verbatim_fidelity()` function (lines 482–517). The `asyncio.to_thread(lambda: conn.execute(...))` pattern matches Stage 1/2 above.

**NOCMatch mapping** — copy from RESEARCH.md Pattern 4 `to_noc_match()` function (lines 255–270). References `app/models/work_description.py` `NOCMatch` and `ProvenanceTag` (lines 17–49).

---

### `app/services/wd_store.py` (service, CRUD)

**Analog:** `app/db.py` `get_connection()` and `create_schema()` patterns (lines 131–189).

**Imports pattern:**
```python
from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from app.db import get_connection
from app.models.work_description import WorkDescription
```

**Read pattern** — `app/db.py` uses `con.execute(...).fetchone()` + `sqlite3.Row` factory (line 140 `con.row_factory = sqlite3.Row`):
```python
def load_work_description(conn: sqlite3.Connection, wd_id: str) -> WorkDescription | None:
    row = conn.execute(
        "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
    ).fetchone()
    if row is None:
        return None
    return WorkDescription.model_validate_json(row["data"])
```

**Write pattern** — mirrors `app/db.py` upsert pattern (INSERT OR REPLACE) from `scripts/ingest_noc.py` `write_index_metadata()` (lines 411–416):
```python
def save_work_description(conn: sqlite3.Connection, wd: WorkDescription) -> None:
    now = datetime.utcnow().isoformat()
    conn.execute(
        """INSERT OR REPLACE INTO work_descriptions(id, session_id, stage, data, created_at, last_modified)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(wd.id), wd.session_id, wd.stage, wd.model_dump_json(), now, now),
    )
    conn.commit()
```

**No async needed:** These are synchronous helpers called inside `asyncio.to_thread()` at the service layer — same pattern as `scripts/ingest_noc.py` stage functions (lines 144–173).

---

### `app/api/noc_mapping.py` (controller, request-response)

**Analog:** `app/api/health.py` — exact match. Copy the APIRouter pattern.

**Imports pattern** — copy `app/api/health.py` lines 1–12, replace imports:
```python
from fastapi import APIRouter, HTTPException
from app.services.noc_mapper import map_work_description
from app.config import settings
from app.models.noc import WorkDescriptionRequest, NocMapResponse
```

**Router setup** — copy `app/api/health.py` line 13:
```python
router = APIRouter()
```

**Route handler pattern** — copy `app/api/health.py` `health_check()` async structure (lines 21–47). The try/except wrapping ValueError → HTTPException is the standard pattern:
```python
@router.post("/api/noc/map", response_model=NocMapResponse)
async def map_noc(body: WorkDescriptionRequest) -> NocMapResponse:
    try:
        result = await map_work_description(
            work_description=body.work_description,
            db_path=settings.db_path,
        )
        return NocMapResponse(candidates=result.candidates)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
```

**Router registration** — copy `app/main.py` lines 98–99 pattern:
```python
# In app/main.py — add after existing health.router include:
from app.api import noc_mapping
app.include_router(noc_mapping.router)
```

---

### `app/models/noc.py` (model, request-response)

**Analog:** `app/models/work_description.py` — exact match for Pydantic BaseModel pattern.

**Imports pattern** — copy `app/models/work_description.py` lines 1–13 (simplified):
```python
from __future__ import annotations

from pydantic import BaseModel, Field
from app.ai.noc_ranking import NOCCandidate
```

**Model pattern** — copy `NOCMatch` from `app/models/work_description.py` lines 42–49 as structural reference:
```python
class WorkDescriptionRequest(BaseModel):
    work_description: str = Field(..., min_length=10)
    wd_id: str | None = None


class NocMapResponse(BaseModel):
    candidates: list[NOCCandidate] = Field(..., min_length=1, max_length=5)
```

---

### `templates/partials/noc_results.html` (component, request-response)

**Analog:** `app/templates/base.html` — provides the Jinja2 template syntax and HTMX attribute style.

**HTMX partial pattern** — this is a fragment, not a full page; does NOT extend `base.html`. Copy HTMX attribute style from RESEARCH.md Pattern 5 (lines 296–309):
```html
{% for candidate in candidates %}
<div class="noc-card">
    <h3>[{{ candidate.noc_code }}] {{ candidate.noc_title }} (TEER {{ candidate.teer_level }})</h3>
    <ul>
    {% for duty in candidate.matched_duty_statements %}
        <li>{{ duty }}</li>
    {% endfor %}
    </ul>
    <form hx-post="/api/noc/confirm"
          hx-target="#wizard-step"
          hx-swap="outerHTML">
        <input type="hidden" name="wd_id" value="{{ wd_id }}">
        <input type="hidden" name="noc_code" value="{{ candidate.noc_code }}">
        <button type="submit">Confirm this NOC</button>
    </form>
</div>
{% endfor %}
```

**Note:** `base.html` loads HTMX at end of body (line 28) and Alpine.js with `defer` in head (line 9). Partials inherit these — no script re-import needed.

---

### `templates/wizard/step_noc.html` (component, request-response)

**Analog:** `app/templates/base.html` — extends this file. Copy block extension pattern.

**Template extension pattern** — copy `base.html` block structure (lines 11–30). The `{% extends %}` + `{% block content %}` pattern is the only Jinja2 inheritance pattern in the project:
```html
{% extends "base.html" %}

{% block title %}NOC Mapping — JD Builder{% endblock %}

{% block content %}
<section id="wizard-step">
    <h2>Step: Identify NOC Unit Group</h2>
    <form hx-post="/api/noc/map"
          hx-target="#noc-results"
          hx-swap="innerHTML"
          hx-indicator="#spinner">
        <textarea name="work_description" rows="6"
                  placeholder="Describe the work in plain language..."></textarea>
        <button type="submit">Find NOC Candidates</button>
        <div id="spinner" class="htmx-indicator">Searching...</div>
    </form>
    <div id="noc-results"></div>
</section>
{% endblock %}
```

---

### `scripts/rebuild_noc_vectors.py` (utility, batch)

**Analog:** `scripts/ingest_noc.py` — exact structural match. Copy the argparse CLI pattern, `validate_db_path()`, `load_connection()`, and staged print output.

**Imports pattern** — copy `scripts/ingest_noc.py` lines 27–35:
```python
from __future__ import annotations

import argparse
import asyncio
import sqlite3
import sys
from pathlib import Path

import sqlite_vec
from ollama import AsyncClient as OllamaAsyncClient

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
```

**Path traversal guard** — copy `scripts/ingest_noc.py` `validate_db_path()` verbatim (lines 56–75). This is a security control (T-2-01) that must appear in every script.

**Connection factory** — copy `scripts/ingest_noc.py` `load_connection()` verbatim (lines 82–96). Do NOT import `app.config` — scripts avoid triggering pydantic-settings ValidationError when env vars are absent.

**Vec table rebuild pattern** — copy `scripts/ingest_noc.py` `recreate_vec_table_if_needed()` (lines 333–347) but invert the dimension check: detect FLOAT[1024] and recreate as FLOAT[768]:
```python
def recreate_vec_table_for_nomic(con: sqlite3.Connection) -> None:
    """Drop noc_chunks_vec if FLOAT[1024] and recreate as FLOAT[768] for nomic-embed-text."""
    existing = con.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='noc_chunks_vec'"
    ).fetchone()
    if existing and "FLOAT[1024]" in (existing["sql"] or ""):
        print("  Detected 1024-dim vec table — dropping and recreating for 768-dim", flush=True)
        con.execute("DROP TABLE IF EXISTS noc_chunks_vec")
        con.executescript("""
            CREATE VIRTUAL TABLE noc_chunks_vec USING vec0(
                rowid INTEGER PRIMARY KEY,
                embedding FLOAT[768] distance_metric=cosine
            )
        """)
        con.commit()
```

**Ollama async embed pattern** — copy `app/api/health.py` `OllamaAsyncClient` usage (lines 31–33), adapted for batch embedding:
```python
async def embed_with_ollama(texts: list[str], base_url: str, model: str) -> list[list[float]]:
    client = OllamaAsyncClient(host=base_url)
    results = []
    for text in texts:
        resp = await client.embed(model=model, input=text)
        results.append(resp.embeddings[0])
    return results
```

**Staged print output** — copy `scripts/ingest_noc.py` `main()` numbered stage pattern (lines 474–516):
```python
print(f"[1/3] Connecting to {db_path} ...")
print("[2/3] Rebuilding noc_chunks_vec as FLOAT[768] ...")
print("[3/3] Writing index_metadata ...")
```

**write_index_metadata** — copy `scripts/ingest_noc.py` `write_index_metadata()` verbatim (lines 411–416). Update value to `"nomic-embed-text:latest"`.

**CLI entrypoint** — copy `scripts/ingest_noc.py` `parse_args()` and `if __name__ == "__main__": raise SystemExit(main())` pattern (lines 423–522, simplified).

---

### `tests/test_noc_mapping.py` (test, request-response)

**Analog:** `tests/test_health.py` for FastAPI route tests; `tests/test_noc_ingest.py` for SQLite fixture + mock pattern.

**Imports pattern** — copy `tests/test_health.py` lines 1–4:
```python
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
```

**FastAPI test client pattern** — copy `tests/test_health.py` `test_health_endpoint_200` (lines 22–37) replacing route and body:
```python
@pytest.mark.asyncio
async def test_api_route_200(monkeypatch, noc_mapping_db, tmp_path):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "gemma4:31b")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    monkeypatch.setenv("DB_PATH", str(noc_mapping_db))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))

    with patch("app.services.noc_mapper.OllamaAsyncClient") as mock_embed, \
         patch("app.ai.noc_ranking.instructor_client") as mock_instructor, \
         patch("app.main.ollama_client_factory", return_value=_make_mock_ollama()):
        # ... setup mocks, call /api/noc/map ...
```

**Mock pattern** — copy `tests/test_health.py` `_make_mock_client()` (lines 7–18) as template for `_make_mock_ollama()` and `_make_mock_instructor()`.

**SQLite fixture usage** — copy `tests/test_noc_ingest.py` `_run_ingest()` helper pattern (lines 55–60) for database setup in integration tests.

**Async test pattern** — all tests are `async def` because `asyncio_mode = "auto"` is set in `pyproject.toml`. Copy `tests/test_health.py` — no `@pytest.mark.asyncio` decorator needed per RESEARCH.md Validation Architecture.

---

### `tests/test_noc_ranking.py` (test, request-response)

**Analog:** `tests/test_noc_ingest.py` for unit test structure; `tests/test_models.py` if present for Pydantic validation tests.

**Imports pattern** — copy `tests/test_noc_ingest.py` lines 1–14:
```python
from __future__ import annotations

import pytest
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock, patch
```

**Pydantic validation test pattern** — validate that field constraints fire correctly. Copy `tests/test_noc_ingest.py` synthetic data approach (lines 22–52) for fixture construction:
```python
def test_noc_candidate_schema():
    """NOCCandidate must accept valid data and reject invalid noc_code."""
    from app.ai.noc_ranking import NOCCandidate
    # valid
    c = NOCCandidate(noc_code="21232", title="Software engineers", teer=2,
                     rank=1, matched_duties=["Develop software."], justification="x" * 30)
    assert c.noc_code == "21232"
    # invalid — non-digit noc_code
    with pytest.raises(ValidationError):
        NOCCandidate(noc_code="ABCDE", title="X", teer=2, rank=1,
                     matched_duties=["x"], justification="x" * 30)
```

**Mock embedding vector size** — use `[0.1] * 768` (NOT 1024) after vec rebuild. Compare `tests/test_noc_ingest.py` line 48 (`[[0.1] * 1024]`) — update dimension.

---

### `tests/conftest.py` (update — add `noc_mapping_db` fixture)

**Analog:** `tests/conftest.py` existing `noc_db` fixture (lines 56–67).

**New fixture pattern** — copy `noc_db` (lines 56–67) and extend with synthetic NOC data + 768-dim fake vectors:
```python
@pytest.fixture
def noc_mapping_db(tmp_path):
    """
    Temp SQLite DB with NOC schema, synthetic FTS5 data, and 768-dim fake vec rows.
    Used by test_noc_mapping.py integration tests — does NOT require Ollama to be running.
    """
    from app.db import get_connection, create_schema
    import sqlite_vec

    db_path = str(tmp_path / "test_noc_mapping.db")
    con = get_connection(db_path)
    create_schema(con)

    # Insert synthetic noc_units row
    con.execute(
        "INSERT OR IGNORE INTO noc_units(noc_code, teer_level, title, definition, source_hash) "
        "VALUES (?, ?, ?, ?, ?)",
        ("21232", "2", "Software engineers and designers",
         "Design and develop software systems.", "fakehash"),
    )

    # Insert synthetic noc_elements (Main duties)
    con.execute(
        "INSERT OR IGNORE INTO noc_elements(noc_code, element_type, element_text, source_hash) "
        "VALUES (?, ?, ?, ?)",
        ("21232", "Main duties", "Develop and maintain application software.", "fakehash"),
    )

    # Rebuild FTS5 index from inserted data
    con.execute("DELETE FROM noc_fts")
    con.execute(
        "INSERT INTO noc_fts(noc_code, title, definition, element_type, element_text) "
        "SELECT noc_code, title, definition, '', '' FROM noc_units"
    )
    con.execute(
        "INSERT INTO noc_fts(noc_code, title, definition, element_type, element_text) "
        "SELECT e.noc_code, u.title, u.definition, e.element_type, e.element_text "
        "FROM noc_elements e JOIN noc_units u ON u.noc_code = e.noc_code"
    )

    # Drop old 1024-dim vec table, recreate as 768-dim, insert fake vector
    con.execute("DROP TABLE IF EXISTS noc_chunks_vec")
    con.executescript(
        "CREATE VIRTUAL TABLE noc_chunks_vec USING vec0("
        "rowid INTEGER PRIMARY KEY, embedding FLOAT[768] distance_metric=cosine)"
    )
    elem_id = con.execute(
        "SELECT id FROM noc_elements WHERE noc_code = '21232' LIMIT 1"
    ).fetchone()["id"]
    fake_vec = sqlite_vec.serialize_float32([0.1] * 768)
    con.execute("INSERT INTO noc_chunks_vec(rowid, embedding) VALUES (?, ?)", (elem_id, fake_vec))

    # Update index_metadata so assert_noc_index_model() passes
    con.execute(
        "INSERT OR REPLACE INTO index_metadata(key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("embedding_model", "nomic-embed-text:latest"),
    )
    con.commit()

    yield str(db_path)
    con.close()
```

**Note:** The fixture yields `str(db_path)` (not the connection) because `noc_mapper.map_work_description()` opens its own per-request connection via `get_connection(db_path)`. This matches RESEARCH.md Pattern 3 (connection-per-request, not a shared connection).

---

## Shared Patterns

### Connection Factory
**Source:** `app/db.py` `get_connection()` lines 131–145
**Apply to:** `app/services/noc_mapper.py`, `app/services/wd_store.py`, `scripts/rebuild_noc_vectors.py`
```python
con = sqlite3.connect(db_path, check_same_thread=False)
con.row_factory = sqlite3.Row
con.enable_load_extension(True)
sqlite_vec.load(con)
con.enable_load_extension(False)
return con
```
**Note for scripts:** Scripts copy `load_connection()` locally (see `scripts/ingest_noc.py` lines 82–96) rather than importing `app.db` — avoids triggering pydantic-settings ValidationError on missing env vars.

### Settings Access
**Source:** `app/config.py` lines 84–86; `app/api/health.py` line 10
**Apply to:** `app/ai/noc_ranking.py`, `app/services/noc_mapper.py`, `app/api/noc_mapping.py`
```python
from app.config import settings
# Use: settings.ollama_base_url, settings.ollama_embed_model, settings.ollama_generation_model, settings.db_path
```

### Path Traversal Guard (CLI scripts only)
**Source:** `scripts/ingest_noc.py` `validate_db_path()` lines 56–75
**Apply to:** `scripts/rebuild_noc_vectors.py`
```python
def validate_db_path(db_path: str) -> Path:
    resolved = Path(db_path).resolve()
    project_root = Path(__file__).resolve().parent.parent
    try:
        resolved.relative_to(project_root)
        return resolved
    except ValueError:
        print(f"Error: --db-path must be under the project root ({project_root}).", file=sys.stderr)
        raise SystemExit(1)
```

### APIRouter Pattern
**Source:** `app/api/health.py` lines 13, 21–47
**Apply to:** `app/api/noc_mapping.py`
```python
router = APIRouter()

@router.get("/health")
async def health_check():
    try:
        # ... logic ...
        return {...}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
```
Replace `Exception → ValueError` and `return error dict → raise HTTPException(status_code=422)` for the NOC mapping route.

### Lifespan Router Registration
**Source:** `app/main.py` lines 98–99
**Apply to:** `app/main.py` (add `noc_mapping` router)
```python
# Current:
app.include_router(health.router)

# After Phase 4 Plan 03:
from app.api import noc_mapping
app.include_router(noc_mapping.router)
```

### Async Test Setup with Env Vars
**Source:** `tests/test_health.py` lines 22–37
**Apply to:** `tests/test_noc_mapping.py`
```python
@pytest.mark.asyncio
async def test_...(monkeypatch, temp_db_path, tmp_path):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "gemma4:31b")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    monkeypatch.setenv("DB_PATH", str(temp_db_path))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
```

### Pydantic `from __future__ import annotations`
**Source:** `app/models/work_description.py` line 1; `app/main.py` line 1
**Apply to:** All new Python files — this is the project-wide convention for deferred annotation evaluation.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `app/ai/noc_ranking.py` (instructor client) | service | request-response | No existing instructor client in codebase — AI-SPEC Section 4b is the sole reference; pattern is proven in JES (Phase 7) but that code does not exist yet |

---

## Critical Schema Corrections (apply everywhere)

These override the AI-SPEC — the planner must use these, not the AI-SPEC Stage 1/2 queries:

1. **Stage 1 query:** `noc_fts` has no `teer` or `main_duties` columns. Must JOIN `noc_units`. Use RESEARCH.md Pattern 1.
2. **Stage 2 join key:** `noc_chunks_vec.rowid = noc_elements.id` (confirmed via live DB). Use `JOIN noc_elements e ON e.id = v.rowid`.
3. **TEER type:** `noc_units.teer_level` is TEXT — must `CAST(u.teer_level AS INTEGER)` in all queries.
4. **Vec dimensions:** After `rebuild_noc_vectors.py` runs, `noc_chunks_vec` is FLOAT[768]. All test fake vectors must be `[0.1] * 768`.
5. **stage field:** `WorkDescription.stage` is `Literal[...]`, not an enum. Set as plain string: `wd.stage = "noc_mapped"`.

---

## Metadata

**Analog search scope:** `app/`, `scripts/`, `tests/`, `app/templates/`
**Files scanned:** 11 source files read in full
**Pattern extraction date:** 2026-06-01
