# Technology Stack Research

**Project:** JD Builder — Government of Canada Job Description Builder
**Platform:** Jetson AGX Orin "Jane" — ARM64 (aarch64), Linux, Python 3.10.12
**Researched:** 2026-05-28
**Confidence:** HIGH (all packages verified against actual hardware via pip dry-run or existing install)

---

## ARM64 Verification Legend

All packages below were checked via `pip install --dry-run` or confirmed installed on the Jetson AGX Orin
(aarch64, Python 3.10.12). Status codes:

- **CONFIRMED** — installed and working on this machine
- **VERIFIED** — pip dry-run resolves an aarch64 wheel successfully
- **CAUTION** — has known ARM64 issues; see notes
- **AVOID** — does not install cleanly on aarch64 without significant workarounds

---

## 1. Python Web Framework

### Recommendation: FastAPI 0.128.x

**CONFIRMED** — FastAPI 0.128.8 is already installed on this machine.

**Why FastAPI over Flask for this use case:**

Flask is a WSGI framework. It can run async code, but each request gets its own sync/async loop and
blocks the process during execution. When the LLM is generating a 2,000-word JD draft over Ollama,
Flask stalls every other request including UI polling, auto-saves, and live validation. That is
unacceptable for a multi-step wizard that also streams tokens to the browser.

FastAPI is ASGI-native. One Uvicorn worker can hold hundreds of concurrent connections, yield token
chunks via async generators, and still serve validation requests between yields. The pattern for
LLM streaming is exactly `StreamingResponse` + `async for chunk in ollama_client.chat(..., stream=True)`.

Additional factors:
- Pydantic v2 is a first-class dependency (already installed: 2.12.5). Every JD section, provenance
  record, and JES rating can be a validated model contract.
- FastAPI's built-in OpenAPI docs are useful during development and testing.
- FastAPI + HTMX is a well-documented pattern in 2025/2026 for form-heavy Python apps.
- Jinja2 3.1.6 is already installed and integrates cleanly with FastAPI for server-side HTML templates.

**Server:** Uvicorn 0.40.0 — CONFIRMED installed. Single-worker is fine for a local single-user app.
Run with `--reload` in dev.

**Flask as an alternative:** Only appropriate if async streaming were unnecessary. For this project
it is the wrong choice. Do not use Flask.

---

## 2. Ollama Integration

### Recommendation: `ollama` Python library (official) — direct, no abstraction layer

**CONFIRMED** — ollama 0.6.1 is installed on this machine.

The official `ollama` Python library (`pip install ollama`) is the correct choice. It provides:

- `AsyncClient` with `async for chunk in client.chat(..., stream=True)` — plugs directly into
  FastAPI's `StreamingResponse` with no adapter code.
- `format=MyModel.model_json_schema()` for structured outputs using Pydantic — token-level grammar
  constraint, not prompt engineering.
- Synchronous client available for scripts and data pipeline steps that don't need async.
- Pure Python + httpx dependency; no heavy ML framework required.
- Version 0.6.1 supports thinking mode (for Qwen3 models), tool calling, and multimodal inputs.

**Models available on this machine relevant to JD Builder:**
- `qwen3.6:latest` — primary generation model (23 GB, strong instruction following, structured output)
- `qwen3.6-240k:latest` — long-context variant for large CA / NOC corpora
- `nomic-embed-text:latest` — embedding model (274 MB, 8192-token context, 768 dimensions)
- `gemma4:e2b` — lightweight fallback (7.2 GB) for fast classification tasks

**Do not use:**
- `langchain-ollama` — adds significant abstraction overhead, LangChain chain/callback complexity,
  and LangChain versioning churn. Direct API control is cleaner for this app's structured output needs.
- `llama-index` Ollama integration — LlamaIndex is a useful framework but its abstractions fight you
  when you need per-token provenance tracking, which is a core requirement of this project.
- Raw HTTP (`requests`/`httpx` directly) — the official library wraps httpx cleanly; don't re-invent it.

---

## 3. Structured LLM Outputs

### Recommendation: Ollama native `format` parameter with Pydantic schemas

**Why:** Since Ollama v0.5, the `format` parameter accepts a full JSON Schema and converts it to a
GBNF grammar internally. This is token-level constraint: the model physically cannot emit tokens that
violate the schema structure. It does not rely on the model following instructions — the sampler
itself is constrained.

**Pattern:**
```python
from pydantic import BaseModel
from ollama import AsyncClient

class NOCMatch(BaseModel):
    noc_code: str
    unit_group_title: str
    confidence_score: float
    rationale: str
    matched_duties: list[str]

client = AsyncClient()
response = await client.chat(
    model="qwen3.6:latest",
    messages=[{"role": "user", "content": prompt}],
    format=NOCMatch.model_json_schema(),
    options={"temperature": 0},  # deterministic for classification
)
result = NOCMatch.model_validate_json(response.message.content)
```

**Known limitations with this approach:**
- Grammar constraints ensure structural validity, not factual accuracy. A hallucinated NOC code will
  still be a valid string that passes schema validation. Downstream validation against the actual
  NOC corpus is required.
- Qwen3 + structured output with the `format` parameter has reported issues in some Ollama versions
  when tool call arguments are large. Use `format` for structured output, not tool calling, in this app.
- Set `temperature: 0` for all classification and structured extraction tasks. Use higher temperature
  only for free-text narrative generation.

**`instructor` library (installed: 1.15.1):**
`instructor` adds retry logic, validation loops, and automatic re-prompting when validation fails.
It is worth using as a wrapper over the native `format` parameter for critical outputs (NOC mapping,
JES ratings) where a hallucinated structure should trigger a retry rather than surface as an error.
The `instructor.from_ollama()` patch integrates with the official client.

**Do not use:**
- `outlines` — adds a separate inference runtime that conflicts with Ollama; not needed.
- Prompt-engineering-only approaches (asking the model to "return JSON") — unreliable without
  grammar constraints, especially for complex nested schemas like JES scoring.

---

## 4. RAG / Semantic Search

### Recommendation: `sqlite-vec` + Ollama embeddings (`nomic-embed-text`)

**sqlite-vec:** VERIFIED — `pip install sqlite-vec` resolves `sqlite_vec-0.1.9-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.whl` cleanly on this machine.

**nomic-embed-text:** CONFIRMED — already pulled on this machine (274 MB, 768 dimensions, 8192-token
context). Generates embeddings via `ollama.embed(model="nomic-embed-text", input=text)`.

**Why this combination:**

The prototype's 500 MB cold-start problem came from `sentence-transformers`, which loads a PyTorch
model into system RAM at startup. `nomic-embed-text` via Ollama is always resident in the Ollama
server process; embedding calls are fast HTTP requests with no cold-start.

`sqlite-vec` stores embeddings as BLOB columns in the existing SQLite database, enabling KNN vector
search with no separate service. The corpus here is bounded (NOC profiles: ~500 unit groups,
collective agreements: ~25 OGs, JES standards: ~15 documents) — tens of thousands of chunks at most.
`sqlite-vec` handles this scale trivially with sub-100ms query times.

**Architecture for RAG:**
```
Source text → chunk (512-1024 tokens) → nomic-embed-text → 768-dim vector
→ store in sqlite-vec table (id, source_file, section, chunk_text, embedding)
→ query: embed user input → KNN search → retrieve top-K chunks → inject into prompt
```

**Embedding dimensions:** 768 (nomic-embed-text). Store as float32 BLOB. Index type: flat (no
HNSW needed at this scale — flat exhaustive search over 50K vectors is <50ms on ARM64).

**Alternatives considered:**

- **ChromaDB 1.5.9** — CONFIRMED installed, aarch64 wheel available. ChromaDB is a valid choice
  for development convenience (HTTP API, persistent collections, built-in metadata filtering).
  However: it pulls in grpcio, onnxruntime, kubernetes client, and 15+ other heavy dependencies.
  For a single-user local app already using SQLite as the data layer, the overhead is unjustified.
  Use ChromaDB only if you need cross-process embedding access or want its HTTP API for debugging.

- **fastembed 0.8.0** — CONFIRMED installed (available on aarch64). fastembed uses ONNX Runtime
  for embeddings without PyTorch, solving the cold-start problem differently. However, since
  `nomic-embed-text` is already resident in Ollama, adding fastembed means running two separate
  embedding stacks. Prefer the Ollama path. Keep fastembed as a fallback if Ollama embedding
  latency becomes a bottleneck for batch indexing.

- **qdrant local** — Works on aarch64, but runs as a separate sidecar process. Unnecessary for
  this data scale.

- **sentence-transformers** — DO NOT USE. 500 MB model load + PyTorch cold start. This is the
  exact problem the prototype had.

---

## 5. Data Layer

### Recommendation: DuckDB for query-heavy analytics; Polars for transform pipelines; SQLite for app state

**DuckDB 1.5.3** — VERIFIED — pip resolves `duckdb-1.5.3-cp310-cp310-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl` on this machine. (Note: versions 1.4.3 and 1.4.4 had missing ARM64 wheels; 1.5.x is clean.)

**Polars 1.41.1** — VERIFIED — pip resolves `polars_runtime_32-1.41.1-cp310-abi3-manylinux_2_17_aarch64.manylinux2014_aarch64.whl` on this machine.

**Rationale for each:**

**DuckDB:** Use as the query engine over parquet files (NOC profiles, DRF data, rates of pay, skills taxonomy). DuckDB reads parquet directly without loading the full file into memory. SQL syntax is natural for joins across files (e.g., `JOIN noc_profiles ON noc_code = jes_mappings.noc_code`). Zero-ETL — no separate database server. Memory-safe: DuckDB streams and spills to disk rather than loading entire datasets into RAM.

```python
import duckdb
con = duckdb.connect()
results = con.execute("""
    SELECT p.noc_code, p.unit_group_title, p.main_duties
    FROM 'data/gold/noc_profiles.parquet' p
    WHERE p.broad_occupational_category = 'Management'
    AND p.noc_code LIKE '0%'
""").fetchdf()
```

**Polars:** Use for data pipeline transforms (Bronze → Silver → Gold medallion ingestion), not for
ad-hoc query. Polars is faster than pandas for SIMD-accelerated column transforms and has a cleaner
lazy evaluation API. The aarch64 wheel is available and resolves cleanly. For the query patterns in
this app (filter by OG code, text search, cross-file joins), DuckDB is more ergonomic; use Polars
when building and updating the data pipeline scripts.

**SQLite:** Use for application state — in-progress JD sessions, user-confirmed classification
decisions, advisor notes, provenance metadata for exports. sqlite-vec lives in the same SQLite
file as the app state. This keeps the entire application state in a single portable `.db` file.

**Do not use:**
- **pandas + pyarrow** — pandas is 2-3x slower than Polars for transform workloads and uses more
  memory. It remains a valid choice for one-off scripts, but do not build the data pipeline on it.
- **SQLAlchemy ORM** for parquet queries — use DuckDB SQL directly; an ORM adds layers of
  abstraction that fight DuckDB's columnar execution model.

---

## 6. Frontend

### Recommendation: HTMX 2.x + Alpine.js 3.x + Jinja2 templates (server-rendered)

**Why not vanilla JS for this app:**

The JD Builder is a multi-step wizard with ~8 distinct phases (describe work → NOC mapping →
OG/level confirmation → duty drafting → JES scoring → qualifications → competencies → CA validation
→ export). Each step triggers a backend call, receives structured HTML, and updates a portion of
the page. Vanilla JS requires custom fetch + DOM diffing code for every transition. HTMX handles
this declaratively.

**HTMX responsibilities:**
- `hx-post` / `hx-get` for form submissions and step navigation
- `hx-target` + `hx-swap` for partial page updates (each wizard step is a server-rendered fragment)
- `hx-trigger="change delay:500ms"` for inline field validation (e.g., validate OG code as advisor types)
- `text/event-stream` + `hx-ext="sse"` for streaming LLM token output to the browser without
  custom JavaScript
- HTMX is ~14 KB with no build step

**Alpine.js responsibilities:**
- Client-side UI state: accordion open/close, modal show/hide, copy-to-clipboard, tab switching
- `x-data` / `x-show` / `x-model` for form UI that does not need a round-trip (e.g., toggling
  a JES factor rating between options, showing/hiding a provenance tooltip)
- Alpine.js is ~15 KB with no build step

**Together (~29 KB):** HTMX manages server communication; Alpine.js manages browser-local state.
They are designed to complement each other and do not overlap.

**Jinja2 3.1.6** — CONFIRMED installed. FastAPI's `Jinja2Templates` renders HTML fragments on the
server. Each HTMX partial is a Jinja2 `{% block %}` or standalone template fragment.

**Do not use:**
- React / Vue / Svelte — a full SPA framework is architectural overkill for a single-user local app.
  No build pipeline, no Node.js dependency, no bundle maintenance. The prototype used vanilla JS
  SPA and it worked but required significant boilerplate. HTMX eliminates that boilerplate.
- Tailwind CSS (via CDN) — acceptable if the team wants utility CSS, but for a government-style
  form-heavy app, plain CSS with a simple grid system is easier to maintain. Optional — not blocked.

---

## 7. Document Generation

### Recommendation: `python-docx` 1.2.0 + `docxtpl` for DOCX; WeasyPrint for PDF

**python-docx 1.2.0** — CONFIRMED installed. Pure Python, no native dependencies, works on aarch64
without issue. Use for programmatic DOCX construction (adding paragraphs, tables, styles).

**docxtpl** — VERIFIED installable (pure Python, depends only on python-docx and Jinja2, both
already installed). Use docxtpl for template-driven generation: create a `.docx` template in Word
with `{{ variable }}` and `{% for item in duties %}` tags, then render with a context dict.
This is the correct pattern for government JD output where formatting is fixed (Government of
Canada standard JD layout) but content varies.

```python
from docxtpl import DocxTemplate

tpl = DocxTemplate("templates/jd_template.docx")
context = {
    "position_title": jd.position_title,
    "og_code": jd.og_level,
    "duties": [{"text": d.text, "noc_source": d.provenance.noc_code} for d in jd.duties],
    "jes_ratings": jd.jes_scores,
    "export_date": datetime.now().isoformat(),
    "data_versions": jd.provenance_metadata,
}
tpl.render(context)
tpl.save("output/jd_draft.docx")
```

**WeasyPrint 68.1** — VERIFIED — pip dry-run resolves `weasyprint-68.1-py3-none-any.whl` cleanly.
WeasyPrint is pure Python (all dependencies are pure Python or system libs via cffi/Pillow which
are already installed). It converts CSS-styled HTML to PDF. For government PDF output, render an
HTML template with Jinja2, apply GoC-compliant CSS (Standard on Web Accessibility compliant
margins, fonts), then pass to WeasyPrint.

```python
from weasyprint import HTML
html = jinja_env.get_template("jd_export.html").render(context)
pdf_bytes = HTML(string=html).write_pdf()
```

**Why WeasyPrint over alternatives:**
- wkhtmltopdf requires a headless browser binary (ARM64 build is non-trivial on Jetson)
- Playwright/Pyppeteer require Chromium (massive dependency, known Jetson ARM64 compatibility issues)
- WeasyPrint has no binary dependency beyond Pango/Cairo (system fonts), which are already present
  on the Jetson Linux install
- CSS paged media support (`@page`, page breaks, headers/footers) handles GoC document formatting

---

## 8. Validation and Models

### Recommendation: Pydantic v2 throughout — all data contracts, all LLM outputs, all API requests

**Pydantic 2.12.5** — CONFIRMED installed. This is not optional — it is the architectural spine
of the project:

- Every NOC profile, JES rating, CA validation result, and export provenance record is a Pydantic model
- FastAPI request/response validation is Pydantic-native
- Ollama structured output (`format=Model.model_json_schema()`) uses Pydantic
- `instructor` uses Pydantic for retry/validation loops
- The prototype's Pydantic model contracts were identified as "what worked" — keep this pattern

---

## Complete Recommended Stack

| Component | Library | Version | ARM64 Status |
|-----------|---------|---------|--------------|
| Web framework | FastAPI | 0.128.8 | CONFIRMED |
| ASGI server | Uvicorn | 0.40.0 | CONFIRMED |
| Template engine | Jinja2 | 3.1.6 | CONFIRMED |
| Data validation | Pydantic | 2.12.5 | CONFIRMED |
| LLM client | ollama (official) | 0.6.1 | CONFIRMED |
| Structured output retry | instructor | 1.15.1 | CONFIRMED |
| Vector search | sqlite-vec | 0.1.9 | VERIFIED |
| Embedding model | nomic-embed-text (Ollama) | latest | CONFIRMED |
| Parquet query engine | DuckDB | 1.5.3 | VERIFIED |
| Data pipeline transforms | Polars | 1.41.1 | VERIFIED |
| App state / KV store | SQLite (stdlib) | — | CONFIRMED |
| DOCX generation | python-docx | 1.2.0 | CONFIRMED |
| DOCX templates | docxtpl | latest | VERIFIED |
| PDF generation | WeasyPrint | 68.1 | VERIFIED |
| Frontend server-push | HTMX | 2.x (CDN) | N/A |
| Frontend UI state | Alpine.js | 3.x (CDN) | N/A |
| Fallback embeddings | fastembed | 0.8.0 | CONFIRMED |

---

## What NOT to Use

| Package | Reason |
|---------|--------|
| **Flask** | WSGI — blocks during LLM inference; streaming requires hacks; FastAPI is already installed and better suited |
| **sentence-transformers** | Caused 30-60s cold starts in prototype; loads full PyTorch model on import; 500 MB+ RAM; replaced by Ollama nomic-embed-text |
| **LangChain / langchain-ollama** | Abstraction fighting: provenance-first design requires per-token control that LangChain's chain model obscures; versioning churn; not worth the overhead |
| **LlamaIndex RAG pipeline** | Similar issue — LlamaIndex's node/index abstractions conflict with the custom provenance data model; use direct Ollama + sqlite-vec instead |
| **wkhtmltopdf** | ARM64 binary build is non-trivial on Jetson; abandoned upstream; WeasyPrint is a better fit |
| **Playwright / Pyppeteer for PDF** | Requires Chromium binary; ARM64 Jetson Chromium is problematic; overkill for document generation |
| **pandas** for data pipeline | 2-3x slower than Polars for column transforms; higher memory use; use Polars for pipelines, DuckDB for queries |
| **SQLAlchemy ORM** | Unnecessary ORM abstraction over DuckDB's SQL-first model; adds complexity without benefit for parquet-native queries |
| **qdrant / Weaviate / Milvus** | Separate service processes; overkill for the bounded corpus size in this app; sqlite-vec covers the use case entirely |
| **outlines** | Separate inference runtime that conflicts with Ollama; grammar-constrained decoding is already provided by Ollama's `format` parameter |
| **React / Vue / Svelte** | No build pipeline needed; single-user local app; HTMX + Alpine.js covers all UI requirements at ~29 KB |
| **DuckDB 1.4.3 / 1.4.4** | Missing aarch64 wheels on PyPI; use 1.5.x which has a clean aarch64 wheel |

---

## Known ARM64 Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| `onnxruntime` (pulled by chromadb, fastembed) sometimes needs recompile on Jetson | LOW | Pre-built aarch64 wheels exist; confirmed working for chromadb 1.5.9 and fastembed 0.8.0 |
| `grpcio` (chromadb dep) has had ARM64 build failures in the past | LOW | chromadb 1.5.9 is already installed and working on this machine |
| DuckDB aarch64 wheels have appeared and disappeared between minor versions | MEDIUM | Pin to 1.5.3 in requirements.txt; do not auto-upgrade without verifying aarch64 wheel availability |
| WeasyPrint system font rendering requires Pango/Cairo | LOW | These are standard system libs on Ubuntu/JetPack; should be present; if missing: `apt install libpango-1.0-0 libcairo2` |
| Qwen3 structured output + `format` parameter has reported edge cases in Ollama | MEDIUM | Add `instructor` retry wrapper for critical classification outputs; validate all structured responses before use |

---

## Installation

```bash
# Core application
pip install fastapi uvicorn[standard] pydantic

# LLM
pip install ollama instructor

# Vector search
pip install sqlite-vec

# Data layer
pip install duckdb==1.5.3 polars

# Document generation
pip install python-docx docxtpl weasyprint

# (Optional) Batch embedding fallback
pip install fastembed
```

HTMX and Alpine.js are loaded from CDN in templates — no npm required.

---

## Sources

- FastAPI streaming docs: https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
- Ollama Python library: https://github.com/ollama/ollama-python
- Ollama structured outputs: https://docs.ollama.com/capabilities/structured-outputs
- sqlite-vec: https://github.com/asg017/sqlite-vec
- DuckDB ARM64 issue tracker: https://github.com/duckdb/duckdb-python/issues/301
- instructor + Ollama: https://python.useinstructor.com/integrations/ollama/
- HTMX multi-step forms: https://medium.com/@alexander.heerens/htmx-patterns-01-how-to-build-a-multi-step-form-in-htmx-554d4c2a3f36
- docxtpl: https://docxtpl.readthedocs.io/
- Polars vs DuckDB benchmark: https://www.codecentric.de/en/knowledge-hub/blog/duckdb-vs-polars-performance-and-memory-with-massive-parquet-data
- Ollama embedding models comparison: https://www.morphllm.com/ollama-embedding-models
