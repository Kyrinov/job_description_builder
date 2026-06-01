# Phase 4: NL→NOC Mapping — Research

**Researched:** 2026-06-01
**Domain:** FastAPI + instructor + Ollama + FTS5 + sqlite-vec — three-stage retrieval pipeline
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MAP-01 | Advisor describes work in natural language; system runs FTS5 → embedding rerank → LLM justification pipeline and returns ranked NOC candidates | Full pipeline pattern verified against live DB; query shapes confirmed; embedding rebuild prerequisite identified |
| MAP-02 | Each NOC candidate includes NOC code, unit group title, TEER level, and specific NOC duty statements from source profile that best match | `noc_units.teer_level` (TEXT, must be cast to int) + `noc_elements.element_text` (Main duties) verified; WorkDescription.noc_candidates uses NOCMatch model |

</phase_requirements>

---

## Summary

Phase 4 implements the three-stage NL→NOC mapping pipeline (FTS5 keyword shortlist → sqlite-vec embedding rerank → instructor/gemma4:31b structured justification) and wires it into a FastAPI endpoint with an HTMX wizard step. The AI-SPEC is fully locked and the framework pattern is already proven in the project (instructor + Ollama is the same pattern as JES-01 in Phase 7).

**There is one blocking prerequisite before Phase 4 code can run:** the `noc_chunks_vec` table was built with `text-embedding-v3` (DashScope, 1024-dim) but the application is configured to use `nomic-embed-text` (Ollama, 768-dim). The startup assertion in `app/db.py::assert_noc_index_model()` will raise `RuntimeError` and block all startup until this is resolved. `scripts/ingest_noc.py` must be modified to support Ollama-native embedding so the index can be rebuilt with the correct model and dimensions. This is a Wave 0 task.

**The AI-SPEC pipeline queries contain a schema error:** Section 4 of the AI-SPEC uses `SELECT noc_code, title, teer, main_duties FROM noc_fts` — but `noc_fts` has no `teer` or `main_duties` columns. The correct pattern is `SELECT DISTINCT f.noc_code, u.title, u.teer_level FROM noc_fts f JOIN noc_units u ON u.noc_code = f.noc_code WHERE noc_fts MATCH ?`. The planner must use the corrected query shapes from this research, not the AI-SPEC verbatim.

The WorkDescription model in Phase 1 already has `noc_candidates: list[NOCMatch]` and `confirmed_noc: Optional[NOCMatch]` — Phase 4 writes into these fields. No schema migration is needed.

**Primary recommendation:** Four plans — (1) Wave 0 test stubs + ingest rebuild, (2) `app/ai/noc_ranking.py` Pydantic models + instructor client, (3) `app/services/noc_mapper.py` three-stage pipeline + `app/api/noc_mapping.py` FastAPI router, (4) HTMX wizard step + WD confirm endpoint + full suite green.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| FTS5 keyword shortlist | Database / Storage | API / Backend | SQLite BM25 query; runs synchronously in `asyncio.to_thread()` inside FastAPI route |
| sqlite-vec embedding rerank | Database / Storage | Ollama service | KNN cosine query on noc_chunks_vec; embedding generated via OllamaAsyncClient |
| Instructor LLM justification | Ollama service | API / Backend | gemma4:31b via instructor; awaited inside FastAPI coroutine |
| Online guardrails (verbatim check, TEER check) | API / Backend | Database | Post-pipeline DB check; < 2 ms; runs before returning to client |
| NOC candidate result display | Browser / Client | Frontend Server (SSR) | HTMX partial swap; server renders ranked candidate list fragment |
| NOC confirmation (advisor selects) | Frontend Server (SSR) | Database | HTMX POST; server updates WorkDescription.confirmed_noc |
| Pipeline caching | Database / Storage | — | SHA-256-keyed result cache in SQLite; optional Wave 2+ |

---

## Standard Stack

### Core (all already installed — no pip install needed)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| instructor | 1.15.1 | Structured LLM output via Pydantic + retry | [VERIFIED: pip3 show] installed |
| openai (Python SDK) | 2.37.0 | AsyncOpenAI client pointing at Ollama /v1 | [VERIFIED: pip3 show] installed; AsyncOpenAI import confirmed working |
| ollama (Python SDK) | 0.6.1 | OllamaAsyncClient for nomic-embed-text embeddings | [VERIFIED: pip3 show] installed |
| FastAPI | 0.128.8 | APIRouter for POST /api/noc/map + GET confirm | [VERIFIED: pip3 show] installed |
| sqlite-vec | 0.1.9 | vec0 cosine KNN query on noc_chunks_vec | [VERIFIED: pip3 show] installed |
| Pydantic | 2.12.5 | NOCCandidate / NOCRankingResult validation | [VERIFIED: pip3 show] installed |
| Jinja2 | 3.1.6 | HTMX partial template rendering | [VERIFIED: pip3 show] installed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | 1.3.0 | Async test support (asyncio_mode=auto already set) | All tests touching async pipeline code |
| httpx | 0.28.1 | TestClient for FastAPI integration tests | FastAPI route tests |
| anyio | 4.12.1 | Async primitives (transitive dep via httpx/openai) | No direct use needed |

### Eval Tools (NOT yet installed — Wave 0 install task if using)

| Tool | Status | Install |
|------|--------|---------|
| arize-phoenix | NOT installed | `pip install arize-phoenix opentelemetry-sdk opentelemetry-exporter-otlp` |
| promptfoo | NOT installed | `npx promptfoo` (no global install needed) |

**Note on eval tools:** The AI-SPEC calls for arize-phoenix instrumentation. For v1 Phase 4, the online guardrails (verbatim check, TEER check, empty shortlist guard) are the minimum viable safety layer. Arize-phoenix instrumentation can be added as a stretch task in the final plan — it is not required for MAP-01/MAP-02 acceptance.

**Installation required before Phase 4:**
```bash
# No new packages needed for core pipeline.
# If adding phoenix: pip install arize-phoenix opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
```

---

## Architecture Patterns

### System Architecture Diagram

```
Advisor submits work description (POST /api/noc/map)
         |
         v
[FastAPI route handler — async def]
         |
         v
[noc_mapper.map_work_description()]
         |
         +--- Stage 1: FTS5 keyword shortlist ------------------+
         |    asyncio.to_thread(conn.execute,                   |
         |      SELECT DISTINCT f.noc_code, u.title,            |
         |             u.teer_level, u.definition               |
         |      FROM noc_fts f                                  |
         |      JOIN noc_units u ON u.noc_code = f.noc_code     |
         |      WHERE noc_fts MATCH ? ORDER BY rank LIMIT 30)   |
         |    → up to 30 noc_codes                              |
         |                                                       |
         +--- Stage 2: sqlite-vec embedding rerank -------------+
         |    await OllamaAsyncClient.embed(                    |
         |        model="nomic-embed-text", input=work_desc)    |
         |    → 768-dim query vector                            |
         |    asyncio.to_thread(KNN cosine query restricted to  |
         |        Stage 1 noc_codes via noc_chunks_vec JOIN     |
         |        noc_elements JOIN noc_units, LIMIT 10)        |
         |    → 10 full profiles (noc_code, title, teer,        |
         |        aggregated main_duties, distance)             |
         |                                                       |
         +--- Stage 3: instructor LLM justification -----------+
              await instructor_client.chat.completions.create(
                  model="gemma4:31b",
                  response_model=NOCRankingResult,
                  messages=[system_prompt, user_prompt_with_profiles],
                  max_retries=3, temperature=0.0,
                  extra_body={"options": {"num_ctx": 32768}})
              → NOCRankingResult (validated Pydantic)
                  |
         +--------+--------+
         |                 |
  Online guardrails      Return to
  (verbatim check,       FastAPI route
   TEER check,          → JSON response
   empty shortlist)       OR
                        HTTP 422 if guardrail fires
```

### Recommended Project Structure

```
app/
├── ai/
│   └── noc_ranking.py        # instructor client singleton + NOCCandidate + NOCRankingResult
├── services/
│   └── noc_mapper.py         # map_work_description() three-stage pipeline + guardrails
├── api/
│   └── noc_mapping.py        # FastAPI router: POST /api/noc/map, POST /api/noc/confirm
├── models/
│   └── noc.py                # WorkDescriptionRequest (input) + NocMapResponse (output)
│   └── work_description.py   # EXISTING — NOCMatch, WorkDescription (already has noc_candidates)
templates/
├── partials/
│   └── noc_results.html      # HTMX partial: ranked candidate cards
└── wizard/
    └── step_noc.html         # Full wizard step (extends base.html)
tests/
├── test_noc_mapping.py       # Integration: full 3-stage pipeline + FastAPI route
└── test_noc_ranking.py       # Unit: Pydantic validators, retry/guardrail logic
```

### Pattern 1: Corrected FTS5 Stage 1 Query

The AI-SPEC Section 4 query is WRONG for the actual schema. `noc_fts` does not have `teer` or `main_duties` columns. Use this corrected form:

```python
# Source: verified against live app.db schema [VERIFIED: sqlite3 PRAGMA]
fts_rows = await asyncio.to_thread(
    lambda: conn.execute(
        """
        SELECT DISTINCT f.noc_code, u.title, u.teer_level, u.definition
        FROM noc_fts f
        JOIN noc_units u ON u.noc_code = f.noc_code
        WHERE noc_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (work_description, fts_limit),
    ).fetchall()
)
```

**Why:** `noc_fts` is a virtual FTS5 table with columns `(noc_code, title, definition, element_type, element_text)`. Duty text lives in `noc_elements.element_text` and is aggregated in Stage 2, not Stage 1. `teer_level` is a column on `noc_units` (TEXT, requires `int()` cast for Pydantic).

### Pattern 2: Corrected Stage 2 sqlite-vec KNN Query

Stage 2 must aggregate duty statements per NOC code, since the vec index is keyed on individual `noc_elements` rows (one row per duty statement, not one row per unit group):

```python
# Source: verified against live noc_chunks_vec + noc_elements schema [VERIFIED: sqlite3]
fts_codes = [row[0] for row in fts_rows]
placeholders = ",".join("?" * len(fts_codes))

# embed the work description with nomic-embed-text (768-dim after index rebuild)
ollama_client = OllamaAsyncClient(host=settings.ollama_base_url)
embed_resp = await ollama_client.embed(
    model=settings.ollama_embed_model,   # "nomic-embed-text:latest"
    input=work_description,
)
query_vec: list[float] = embed_resp.embeddings[0]

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

**Critical details:**
1. `noc_chunks_vec.rowid = noc_elements.id` — this is the join key [VERIFIED: live DB]
2. `noc_units.teer_level` is TEXT, must be `CAST(... AS INTEGER)` for Pydantic `teer: int`
3. `GROUP_CONCAT` aggregates all main duty statements per NOC code into one text block
4. Filter `element_type = 'Main duties'` to exclude non-duty embeddings
5. After index rebuild with nomic-embed-text, the vec table will be FLOAT[768] (not FLOAT[1024])

### Pattern 3: Connection Lifecycle in AsyncIO Context

The existing `app/db.py::get_connection()` uses `check_same_thread=False` which is correct for thread-pool usage. However, for the pipeline, a connection per-request is the safest pattern since SQLite connections are not thread-safe by default:

```python
# app/services/noc_mapper.py
# Correct: open connection in thread, use it, close it
conn = await asyncio.to_thread(
    lambda: get_connection(settings.db_path)
)
try:
    # ... all SQLite calls wrapped in asyncio.to_thread ...
finally:
    await asyncio.to_thread(conn.close)
```

**Do NOT** open the connection at module import time — this would hold the connection open for the application lifetime and conflict with test fixtures that use temp databases.

### Pattern 4: NOCMatch Mapping

The `WorkDescription.noc_candidates` field holds `list[NOCMatch]` (from `app/models/work_description.py`). The pipeline returns `NOCRankingResult` (from `app/ai/noc_ranking.py`). A mapping step is needed:

```python
# NOCRankingResult.candidates → list[NOCMatch]
from app.models.work_description import NOCMatch, ProvenanceTag
from datetime import date

def to_noc_match(candidate: NOCCandidate) -> NOCMatch:
    return NOCMatch(
        noc_code=candidate.noc_code,
        noc_title=candidate.title,
        teer_level=str(candidate.teer),
        confidence=1.0 - (candidate.rank / 10.0),   # synthetic confidence from rank
        rationale=candidate.justification,
        matched_duty_statements=candidate.matched_duties,
        provenance=ProvenanceTag(
            source_type="NOC",
            source_id=candidate.noc_code,
            source_version="NOC 2021 v1.0",
            retrieved_date=date.today(),
            model_name=settings.ollama_generation_model,
        ),
    )
```

### Pattern 5: HTMX Wizard Step

The project uses HTMX 2.0.4 + Alpine.js 3.14.8 (loaded in `base.html`). The NOC mapping step posts via HTMX and swaps in the results partial:

```html
<!-- In step_noc.html: POST work description, swap in results -->
<form hx-post="/api/noc/map"
      hx-target="#noc-results"
      hx-swap="innerHTML"
      hx-indicator="#spinner">
    <textarea name="work_description" rows="6"></textarea>
    <button type="submit">Find NOC Candidates</button>
    <div id="spinner" class="htmx-indicator">Searching...</div>
</form>
<div id="noc-results"></div>
```

```html
<!-- In noc_results.html partial: rendered by server after pipeline -->
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

### Anti-Patterns to Avoid

- **Using the AI-SPEC Stage 1 query verbatim** — `noc_fts` has no `teer` or `main_duties` columns. The query will raise `OperationalError`. Use the corrected JOIN pattern (Pattern 1 above).
- **Opening the instructor client per request** — it creates an httpx connection pool on every call. Use the module-level singleton from `app/ai/noc_ranking.py`.
- **Using `asyncio.run()` inside a FastAPI route handler** — raises `RuntimeError: event loop already running`. All route handlers must be `async def` and `await` the pipeline coroutine directly.
- **Embedding the work description with the old DashScope/text-embedding-v3 API** — Phase 4 uses `OllamaAsyncClient.embed(model="nomic-embed-text")`. The DashScope client in `ingest_noc.py` is for ingest only.
- **Querying noc_chunks_vec before the index is rebuilt** — the existing index is 1024-dim (text-embedding-v3). Passing a 768-dim nomic-embed-text vector will either silently return garbage similarity scores or raise a dimension mismatch error. The rebuild must complete before any pipeline test runs against the real DB.
- **Calling `work_description.stage` as an enum** — it is a `Literal[...]` type in the Pydantic model, not a Python Enum. Set it as a plain string: `wd.stage = "noc_mapped"`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured LLM output with retry | Custom JSON parsing + retry loop | `instructor` (already installed) | Handles ValidationError retry, retry count logging, and schema injection; re-implementing this is the canonical instructor anti-pattern |
| Pydantic validation error recovery | `try/except ValidationError` inside the route | `instructor max_retries=3` | instructor appends the exact validation error to the conversation — the model self-corrects more reliably than a re-prompt from scratch |
| TEER value correction after LLM output | Post-processing to infer TEER | Query `noc_units.teer_level` after pipeline returns and overwrite | The database is authoritative; the LLM should not be trusted to output TEER independently |
| Result caching | In-memory dict | SHA-256-keyed `noc_mapping_cache` SQLite table (per AI-SPEC) | Survives restarts; co-located with other data; deterministic at temperature=0.0 |
| FTS5 synonym expansion | Custom synonym table | Not needed in Phase 4 — defer to v2 (MAP-03) | The three-stage funnel already partially mitigates FTS5 terminology gaps via semantic rerank |

**Key insight:** The only genuinely novel code in Phase 4 is the `_format_candidates()` function and the guardrail checks. Everything else assembles proven patterns already in the project.

---

## Runtime State Inventory

> Phase 4 is not a rename/refactor phase. This section is not applicable.

---

## Common Pitfalls

### Pitfall 1: Embedding Model Mismatch Blocks Startup

**What goes wrong:** App raises `RuntimeError` at startup: "NOC vector index was built with embedding model 'text-embedding-v3' but OLLAMA_EMBED_MODEL is configured as 'nomic-embed-text:latest'."

**Why it happens:** `app/db.py::assert_noc_index_model()` reads `index_metadata WHERE key='embedding_model'` and compares against `settings.ollama_embed_model`. The current DB has `text-embedding-v3` (1024-dim) from Phase 2 ingest, but `.env` configures `nomic-embed-text:latest` (768-dim).

**How to avoid:** Wave 0 task: modify `scripts/ingest_noc.py` to accept `--embed-backend ollama` (or add a companion script `scripts/rebuild_noc_vectors.py`) that calls `OllamaAsyncClient.embed(model="nomic-embed-text")`, drops the 1024-dim `noc_chunks_vec` table, recreates it as FLOAT[768], re-embeds all ~6,000 Main duties rows, and updates `index_metadata` with `nomic-embed-text:latest`. Run this before any Phase 4 code touches the DB.

**Warning signs:** `RuntimeError` in pytest startup, `pytest tests/test_startup.py` fails.

### Pitfall 2: FTS5 Query Returns Wrong Columns

**What goes wrong:** `OperationalError: no such column: teer` when running Stage 1.

**Why it happens:** The AI-SPEC Section 4 code example uses `SELECT noc_code, title, teer, main_duties FROM noc_fts` — columns that do not exist. `noc_fts` only has `(noc_code, title, definition, element_type, element_text)`.

**How to avoid:** Use the corrected Stage 1 JOIN pattern from this research (Pattern 1). Always JOIN `noc_units` for `teer_level` and `definition`; collect main duties in Stage 2 via `GROUP_CONCAT` over `noc_elements`.

**Warning signs:** `OperationalError` in test or at runtime on first `/api/noc/map` call.

### Pitfall 3: TEER Level Type Mismatch

**What goes wrong:** Pydantic `ValidationError: teer field: int expected, got str '5'` when trying to construct a `NOCCandidate` from DB rows.

**Why it happens:** `noc_units.teer_level` is stored as TEXT (e.g., `'5'`). `NOCCandidate.teer: int = Field(ge=0, le=5)` requires an integer.

**How to avoid:** Use `CAST(u.teer_level AS INTEGER)` in the SQL query, or explicitly cast `int(row["teer_level"])` when building the context block.

**Warning signs:** Pydantic `ValidationError` containing `teer` in the message.

### Pitfall 4: asyncio.to_thread() Closure Binding

**What goes wrong:** `lambda` inside `asyncio.to_thread()` captures the wrong variable values in a loop.

**Why it happens:** Python closures bind by reference, not by value. A `lambda: conn.execute(query, params)` inside a loop where `params` changes will use the latest value of `params` at execution time.

**How to avoid:** Use `functools.partial` or default-argument binding for lambdas inside `asyncio.to_thread()`. The pipeline has no loops, so this only applies if refactoring into helper functions.

### Pitfall 5: sqlite-vec Dimension Mismatch After Rebuild

**What goes wrong:** `sqlite-vec: vector size mismatch` error on KNN query after the index is rebuilt as FLOAT[768] but `serialize_float32(query_vec)` was called with a 1024-dim vector (or vice versa).

**Why it happens:** `OllamaAsyncClient.embed(model="nomic-embed-text")` returns 768-dim vectors. The old `noc_chunks_vec` is FLOAT[1024]. After rebuild, it becomes FLOAT[768]. Any test or path that uses a hardcoded 1024-dim fake vector will fail.

**How to avoid:** Update all test fixtures that create fake embedding vectors to use `[0.1] * 768` after the rebuild. The `recreate_vec_table_if_needed` function in `ingest_noc.py` currently checks for `FLOAT[768]` to trigger rebuild (backwards from what we need) — the Wave 0 task must correct this logic to check for `FLOAT[1024]` and rebuild as `FLOAT[768]`.

### Pitfall 6: FTS5 BM25 Empty Result Set

**What goes wrong:** Pipeline raises `ValueError: FTS5 shortlist returned zero results` for inputs heavy in DND jargon or acronyms.

**Why it happens:** FTS5 uses porter stemming + ASCII tokenization. Acronyms like "DAOD", "DWAN", or "CANFORGEN" have no overlap with the NOC corpus vocabulary.

**How to avoid:** Catch the empty shortlist case explicitly and return a structured HTTP 422 with a user-friendly message (per AI-SPEC Section 6 online guardrail). Do not propagate the `ValueError` as a 500. Consider adding a pre-processing step in Wave 2 that strips acronym-like tokens and re-queries.

---

## Code Examples

### Stage 1: Corrected FTS5 Query

```python
# Source: verified against live app.db (noc_fts schema confirmed) [VERIFIED: sqlite3]
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

### Stage 2: sqlite-vec KNN With Aggregated Duties

```python
# Source: verified against live noc_chunks_vec + noc_elements (rowid=id join) [VERIFIED: sqlite3]
fts_codes = [row["noc_code"] for row in fts_rows]  # or row[0] if not using Row factory
placeholders = ",".join("?" * len(fts_codes))

embed_resp = await OllamaAsyncClient(host=settings.ollama_base_url).embed(
    model=settings.ollama_embed_model,
    input=work_description,
)
query_vec: list[float] = embed_resp.embeddings[0]  # 768-dim after rebuild

vec_rows = await asyncio.to_thread(
    lambda: conn.execute(
        f"""
        SELECT u.noc_code,
               u.title,
               CAST(u.teer_level AS INTEGER) AS teer,
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

### Stage 3: instructor Client (module-level singleton)

```python
# Source: AI-SPEC Section 4b [VERIFIED: import test confirmed working]
# app/ai/noc_ranking.py
import instructor
from openai import AsyncOpenAI
from app.config import settings

instructor_client = instructor.from_openai(
    AsyncOpenAI(
        base_url=settings.ollama_base_url.rstrip("/") + "/v1",
        api_key="ollama",
    ),
    mode=instructor.Mode.JSON,
)
```

### Online Verbatim Guardrail

```python
# Source: AI-SPEC Section 6 [VERIFIED: instr() query pattern against live DB]
async def _check_verbatim_fidelity(
    conn: sqlite3.Connection,
    result: NOCRankingResult,
) -> NOCRankingResult:
    """Strip any matched_duties that are not verbatim substrings of the source DB record."""
    import logging
    logger = logging.getLogger(__name__)

    clean_candidates = []
    for candidate in result.candidates:
        verified_duties = []
        for duty in candidate.matched_duties:
            row = await asyncio.to_thread(
                lambda: conn.execute(
                    """
                    SELECT 1 FROM noc_elements
                    WHERE noc_code = ? AND instr(element_text, ?) > 0
                    """,
                    (candidate.noc_code, duty),
                ).fetchone()
            )
            if row:
                verified_duties.append(duty)
            else:
                logger.error(
                    "noc_guardrail=citation_fabrication noc_code=%s duty_preview=%s",
                    candidate.noc_code,
                    duty[:80],
                )
        if verified_duties:
            clean_candidates.append(candidate.model_copy(update={"matched_duties": verified_duties}))

    if not clean_candidates:
        raise ValueError("All candidates had fabricated duties — result withheld")

    return result.model_copy(update={"candidates": clean_candidates})
```

### FastAPI Router Pattern

```python
# Source: existing pattern from app/api/health.py [VERIFIED: live codebase]
# app/api/noc_mapping.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.noc_mapper import map_work_description
from app.config import settings

router = APIRouter()

class NocMapRequest(BaseModel):
    work_description: str
    wd_id: str | None = None

@router.post("/api/noc/map")
async def map_noc(body: NocMapRequest):
    try:
        result = await map_work_description(
            work_description=body.work_description,
            db_path=settings.db_path,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Ollama service | All 3 stages | Confirmed running | — | None — hard blocker |
| gemma4:31b | Stage 3 | Confirmed present | — | MiniMax M3 API (env-var swap, per AI-SPEC) |
| nomic-embed-text | Stage 2 | Confirmed present | — | None — required for index rebuild |
| sqlite-vec | All DB queries | Confirmed 0.1.9 | 0.1.9 | None — installed |
| instructor | Stage 3 | Confirmed 1.15.1 | 1.15.1 | None — installed |
| openai Python SDK | Stage 3 | Confirmed 2.37.0 | 2.37.0 | None — installed |
| arize-phoenix | Observability | NOT installed | — | Skip in v1; add as stretch task |
| promptfoo | CI eval | NOT installed | — | Skip in v1; use pytest eval suite |

**Missing dependencies with no fallback:** None for core MAP-01/MAP-02 functionality.

**Missing dependencies with fallback:** arize-phoenix and promptfoo are called for in the AI-SPEC but are not required for MAP-01/MAP-02 acceptance. Include as optional stretch tasks in the final plan.

**Blocking prerequisite (not a missing package):** `noc_chunks_vec` is FLOAT[1024] (DashScope). Must be rebuilt as FLOAT[768] (nomic-embed-text) before any Stage 2 code can run. This is a data state issue, not a missing package.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| asyncio_mode | `auto` (already set — no `@pytest.mark.asyncio` decorator needed) |
| Quick run command | `pytest tests/test_noc_mapping.py tests/test_noc_ranking.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MAP-01 | Three-stage pipeline returns candidates without error | integration | `pytest tests/test_noc_mapping.py::test_pipeline_returns_candidates -x` | Wave 0 |
| MAP-01 | FTS5 empty result raises ValueError, API returns 422 | integration | `pytest tests/test_noc_mapping.py::test_empty_fts_result_raises_422 -x` | Wave 0 |
| MAP-01 | Stage 1 FTS5 shortlist uses correct JOIN pattern | unit | `pytest tests/test_noc_mapping.py::test_fts5_stage_returns_noc_codes -x` | Wave 0 |
| MAP-01 | Stage 2 embedding rerank calls nomic-embed-text | unit (mock) | `pytest tests/test_noc_mapping.py::test_stage2_calls_embed_model -x` | Wave 0 |
| MAP-01 | Stage 3 instructor call uses Mode.JSON | unit (mock) | `pytest tests/test_noc_ranking.py::test_instructor_client_mode_json -x` | Wave 0 |
| MAP-02 | Each candidate has noc_code, title, teer, matched_duties | unit | `pytest tests/test_noc_ranking.py::test_noc_candidate_schema -x` | Wave 0 |
| MAP-02 | Verbatim guardrail strips fabricated duties | unit | `pytest tests/test_noc_mapping.py::test_verbatim_guardrail_strips_fabricated -x` | Wave 0 |
| MAP-02 | TEER field is integer from DB authoritative value | unit | `pytest tests/test_noc_ranking.py::test_teer_is_integer -x` | Wave 0 |
| MAP-01 | FastAPI POST /api/noc/map returns 200 | integration | `pytest tests/test_noc_mapping.py::test_api_route_200 -x` | Wave 0 |
| MAP-01+02 | Confirmed NOC stored on WorkDescription.confirmed_noc | integration | `pytest tests/test_noc_mapping.py::test_confirm_noc_updates_wd -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_noc_ranking.py -x` (fast unit tests, < 5 s, no Ollama needed)
- **Per wave merge:** `pytest tests/test_noc_mapping.py tests/test_noc_ranking.py -x`
- **Phase gate:** `pytest tests/ -x` full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_noc_ranking.py` — unit tests for Pydantic validators, retry logic, guardrails
- [ ] `tests/test_noc_mapping.py` — integration tests for 3-stage pipeline + FastAPI route
- [ ] `tests/conftest.py` update — add `noc_mapping_db` fixture (pre-populated with synthetic NOC data + 768-dim fake vectors; does NOT require Ollama)
- [ ] Rebuild `noc_chunks_vec` as FLOAT[768] (modify `scripts/ingest_noc.py` or write `scripts/rebuild_noc_vectors.py`)

*(Existing `noc_db` fixture in `conftest.py` creates the schema but does not populate FTS5 or vec — needs an extension that adds synthetic data for integration tests)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Yes | `NocMapRequest.work_description` validated by Pydantic; non-empty enforced at route level |
| V4 Access Control | No | Single-user local tool; no multi-user auth in v1 scope |
| V2 Authentication | No | Local tool; no auth in v1 |
| V6 Cryptography | No | SHA-256 cache key is for deduplication, not security |
| V3 Session Management | Partial | `wd_id` ties results to a WorkDescription; validated server-side before persist |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via work_description | Tampering | Pre-retrieval pipeline: LLM only sees retrieved profiles as context, not raw user input mixed into structured SQL queries |
| Path traversal via wd_id in confirm endpoint | Tampering | Validate wd_id is a valid UUID before DB lookup; `app/config.py` db_path validator already restricts to project root |
| SQLite injection via work_description in FTS5 MATCH | Tampering | Parameterized queries — `WHERE noc_fts MATCH ?` with `(work_description,)` param; FTS5 MATCH operator does not allow semicolons or DDL injection |
| LLM fabrication in matched_duties | Repudiation | Online verbatim guardrail checks every duty against DB before returning — fabricated duties stripped before response reaches advisor |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| DashScope text-embedding-v3 (Phase 2 ingest) | nomic-embed-text via Ollama (Phase 4 runtime) | Phase 4 (this research) | Index must be rebuilt; FLOAT[1024] → FLOAT[768] |
| `asyncio_mode = "auto"` via pytest-asyncio 0.25.3 (requirements.txt) | pytest-asyncio 1.3.0 installed globally | Already present | `asyncio_mode = "auto"` in pyproject.toml works with both; no change needed |

**Deprecated/outdated:**
- `@app.on_event("startup")` — replaced by `lifespan` context manager; existing code already uses lifespan correctly

---

## Open Questions

1. **noc_chunks_vec rebuild strategy**
   - What we know: `ingest_noc.py` is DashScope-only; `nomic-embed-text` is available via Ollama
   - What's unclear: Should the planner modify `ingest_noc.py` to add `--embed-backend ollama` support, or create a standalone `scripts/rebuild_noc_vectors.py`? The planner should choose based on whether ingest_noc.py is likely to be run again by another developer with DashScope access.
   - Recommendation: Write `scripts/rebuild_noc_vectors.py` (standalone, Ollama-only, ~80 lines) rather than modifying the existing ingest script — separation of concerns, simpler to test.

2. **WorkDescription persistence on NOC confirm**
   - What we know: `WorkDescription.confirmed_noc: Optional[NOCMatch]` exists; `work_descriptions` table stores `data JSON NOT NULL`
   - What's unclear: No write-to-DB helper exists yet for WorkDescription — Phase 4 needs to introduce `save_work_description(conn, wd)` and `load_work_description(conn, wd_id)` helpers. This is new code, not a blocker, but the planner should allocate a task for it.
   - Recommendation: Include `app/services/wd_store.py` with save/load helpers in Plan 04-03 alongside the mapper service.

3. **HTMX partial template scope**
   - What we know: `base.html` exists; no wizard templates exist yet
   - What's unclear: Does Phase 4 create just the NOC results partial, or also the full wizard shell (step_noc.html extending base.html)?
   - Recommendation: Create both — `templates/wizard/step_noc.html` (full page, extends base.html) and `templates/partials/noc_results.html` (HTMX swap target). Phase 4's "UI hint: yes" implies a usable advisor-facing step, not just an API endpoint.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `nomic-embed-text` produces 768-dim vectors (confirmed via live curl to Ollama) | Standard Stack, Pipeline patterns | [VERIFIED: curl] Risk is negligible |
| A2 | `CAST(teer_level AS INTEGER)` succeeds for all 516 rows in noc_units | Code Examples | If any row has non-numeric teer_level, the query will return NULL and Pydantic will fail — verify with `SELECT DISTINCT teer_level FROM noc_units` in Wave 0 |
| A3 | `GROUP_CONCAT(e.element_text, char(10))` produces text that the LLM can parse as a duty list | Code Examples | [ASSUMED] Could be tested against the live DB; if separator causes issues, use ' | ' instead |
| A4 | pytest-asyncio 1.3.0 is backward-compatible with `asyncio_mode = "auto"` in pyproject.toml | Validation Architecture | [VERIFIED: pytest --co confirmed collection works] Risk negligible |

**Verified claims**: A1, A4. **Assumed claims requiring Wave 0 validation**: A2 (one DB query), A3 (formatting choice).

---

## Sources

### Primary (HIGH confidence)

- `app/db.py` — Verified NOC schema DDL: `noc_units`, `noc_elements`, `noc_fts`, `noc_chunks_vec` column names and types [VERIFIED: grep + sqlite3 PRAGMA]
- `app/models/work_description.py` — NOCMatch, WorkDescription fields confirmed [VERIFIED: read file]
- `app/config.py` — settings.ollama_embed_model, settings.ollama_base_url, settings.db_path confirmed [VERIFIED: read file]
- `app/main.py` — lifespan pattern, router include pattern confirmed [VERIFIED: read file]
- `app/api/health.py` — existing APIRouter pattern confirmed [VERIFIED: read file]
- `tests/conftest.py` — fixture patterns (noc_db, valid_env, mock_healthy_ollama) confirmed [VERIFIED: read file]
- `pyproject.toml` — asyncio_mode = "auto" confirmed; pytest-asyncio 1.3.0 present [VERIFIED: cat + pip show]
- Live `app.db` — schema confirmed via sqlite3 queries: noc_units=516 rows, noc_elements=43999, noc_fts=44515 content rows, noc_chunks_vec=5604 FLOAT[1024] vectors, index_metadata=text-embedding-v3 [VERIFIED: sqlite3]
- Live Ollama — nomic-embed-text 768-dim confirmed via curl; gemma4:31b present [VERIFIED: curl]
- `scripts/ingest_noc.py` — DashScope-only embed path confirmed; FLOAT[1024] hardcoded [VERIFIED: grep]

### Secondary (MEDIUM confidence)

- `04-AI-SPEC.md` — Framework decision, Pydantic model shapes, pipeline parameters [CITED: .planning/phases/04-nl-noc-mapping/04-AI-SPEC.md] — AI-SPEC query shapes contain schema errors corrected in this research

### Tertiary (LOW confidence)

- `GROUP_CONCAT` separator choice for LLM readability [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified installed via pip3 show
- Schema / query patterns: HIGH — verified against live DB with sqlite3
- Architecture: HIGH — all patterns follow existing project conventions
- Pitfalls: HIGH — all confirmed against live DB state
- Eval tooling (arize-phoenix): LOW — not installed, not verified for this environment

**Research date:** 2026-06-01
**Valid until:** 2026-07-01 (stable library versions; Ollama model list is live-checked at startup)
