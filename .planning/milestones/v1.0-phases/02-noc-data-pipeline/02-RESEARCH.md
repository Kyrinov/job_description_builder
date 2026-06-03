# Phase 2: NOC Data Pipeline - Research

**Researched:** 2026-05-28
**Domain:** SQLite FTS5, sqlite-vec vec0, Ollama embedding, CSV ingestion pipeline
**Confidence:** HIGH

---

## Summary

Phase 2 ingests two NOC 2021 CSV files already present in `data/` into three SQLite structures:
a relational `noc_units`/`noc_elements` table for structured access, a FTS5 virtual table for
keyword search, and a `vec0` virtual table for semantic embedding search. A `source_documents`
table records a SHA-256 content hash and version label per source file, and every derived record
stores the hash of the source document it came from. On app startup, a new assertion in
`app/main.py` checks the embedding model name stored in `index_metadata` against the configured
`settings.ollama_embed_model` and refuses to start on mismatch.

All three libraries (sqlite-vec 0.1.9, FTS5, Ollama 0.6.1) are already installed and verified
working on the target machine. The ingest script is a standalone Python script in `scripts/`,
not part of the FastAPI app. Idempotency is achieved via `INSERT OR IGNORE` keyed on source
file name, plus a hash check before re-embedding: if the stored hash matches the computed hash,
the script skips embedding entirely.

The key architectural decision for chunking: embed individual duty statements (not full unit
group profiles), enabling the Phase 4 FTS5 → embedding rerank pipeline to surface specific
NOC duty statements as evidence for a NOC match. Estimated: ~6,656 embeddings total (~19 MB
of float32 vectors), which will take 5–11 minutes on the Jetson AGX Orin at ingest time (one-time
cost, fully skipped on re-run if source unchanged).

**Primary recommendation:** One ingest script (`scripts/ingest_noc.py`) with four sequential
stages: (1) parse CSVs with `csv.DictReader` + `utf-8-sig` encoding, (2) upsert relational
rows, (3) rebuild FTS5, (4) embed duty statements and upsert into vec0. Idempotency is
controlled by the source hash stored in `source_documents`.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-01 | Developer can run ingest pipeline producing FTS5 + sqlite-vec indices with content hash and version label per source doc | FTS5 `CREATE VIRTUAL TABLE USING fts5(...)` verified; vec0 KNN query verified; SHA-256 content hash via `hashlib` verified |
| PIPE-04 | Every source document records content hash + version label; every derived record stores source version hash | `source_documents` table with `content_hash`; `noc_units.source_hash` FK pattern verified |
| PIPE-05 | Startup assertion: embedding model name in index metadata matches configured model — app refuses to serve on mismatch | `index_metadata` table + RuntimeError pattern verified; fits existing lifespan startup hook in `app/main.py` |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CSV parsing + relational upsert | Script (CLI) | — | One-time ingest; not part of request path |
| FTS5 index population | Script (CLI) | — | Populated at ingest time; queried by API |
| Vector embedding + vec0 upsert | Script (CLI) | Ollama service | Embedding is CPU/GPU-bound; never done per-request |
| Startup model assertion | FastAPI lifespan | `app/db.py` | Fits existing `assert_ollama_ready` pattern in `app/main.py` |
| FTS5 query (Phase 4+) | API tier | — | `SELECT ... FROM noc_fts WHERE noc_fts MATCH ?` |
| vec0 KNN query (Phase 4+) | API tier | — | `SELECT rowid, distance FROM noc_chunks_vec WHERE embedding MATCH ? AND k=N` |
| Provenance recording | Script + API | — | ProvenanceTag.source_version = content hash at write time |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sqlite-vec | 0.1.9 | vec0 virtual table for KNN embedding search | [VERIFIED: pip3] Already installed; project-locked |
| FTS5 | built-in SQLite | Full-text search over NOC text | [VERIFIED: sqlite3 test] Built into Python's sqlite3; no install needed |
| ollama (Python) | 0.6.1 | Batch embedding via `AsyncClient.embed()` | [VERIFIED: pip3] Already installed; project decision |
| hashlib | stdlib | SHA-256 content hashing | [VERIFIED: stdlib] No install; deterministic |
| csv (stdlib) | stdlib | Parse NOC CSV files (BOM-aware `utf-8-sig`) | [VERIFIED: csv test] BOM confirmed present in both NOC files |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pandas | 2.3.3 | CSV reading fallback if csv.DictReader too verbose | [VERIFIED: pip3] Available globally; use for complex transforms |
| duckdb | pinned 1.5.3 | Parquet transforms | [VERIFIED: requirements.txt] Not installed globally; use only if parquet step needed |

**Note:** `polars` is in `requirements.txt` but NOT installed globally on this machine. `pandas` IS available globally. The ingest script must use `csv.DictReader` (stdlib) or `pandas` — not `polars` — unless a `pip install polars` step is added to Wave 0.

**Installation:** All required libraries are already installed. No `pip install` needed for
stdlib (`csv`, `hashlib`) or already-installed packages (`sqlite-vec`, `ollama`, `pandas`).

**Version verification:** [VERIFIED: pip3 show]
- `sqlite-vec`: 0.1.9 (2025-era)
- `ollama`: 0.6.1
- `pandas`: 2.3.3

---

## Architecture Patterns

### System Architecture Diagram

```
data/ CSVs (noc_structure.csv, noc_elements.csv)
        │
        ▼
scripts/ingest_noc.py
        │
        ├─[Stage 1: Parse]──► csv.DictReader (utf-8-sig) → rows
        │
        ├─[Stage 2: Relational upsert]
        │         │
        │         ├─► source_documents (INSERT OR IGNORE by name + hash check)
        │         ├─► noc_units (upsert: noc_code, title, definition, teer, source_hash)
        │         └─► noc_elements (upsert: noc_code, element_type, text, source_hash)
        │
        ├─[Stage 3: FTS5 rebuild]
        │         │
        │         └─► noc_fts (DELETE + INSERT from noc_units + noc_elements WHERE type='Main duties')
        │
        ├─[Stage 4: Embed + vec0 upsert] ──► Ollama nomic-embed-text (batch)
        │         │                               │
        │         │         ◄─ embeddings[N][768] ┘
        │         └─► noc_chunks_vec (vec0, rowid JOIN to noc_elements)
        │
        └─[Stage 5: Write index_metadata]
                  └─► index_metadata['embedding_model'] = settings.ollama_embed_model


app/main.py lifespan (startup)
        │
        └─[assert_noc_index_model]
                  │
                  ├─► READ index_metadata['embedding_model']
                  ├─► COMPARE to settings.ollama_embed_model
                  └─► raise RuntimeError on mismatch (PIPE-05)


Phase 4+ API request path:
  NL query
     │
     ├─► FTS5 shortlist: SELECT noc_code FROM noc_fts WHERE noc_fts MATCH ?
     │
     ├─► Embed query: ollama.embed(model, [query_text])
     │
     └─► vec0 KNN rerank:
             SELECT c.noc_code, c.chunk_text, v.distance
             FROM noc_chunks_vec v JOIN noc_elements c ON c.id = v.rowid
             WHERE v.embedding MATCH ? AND k = 20
             ORDER BY distance
```

### Recommended Project Structure

```
scripts/
└── ingest_noc.py        # standalone ingest script — no FastAPI import

app/
├── db.py                # extended: add NOC schema DDL + assert_noc_index_model()
├── main.py              # extended: lifespan calls assert_noc_index_model()
└── models/
    └── work_description.py   # untouched (finalized Phase 1)

tests/
├── test_noc_ingest.py   # unit tests for ingest logic
└── test_noc_startup.py  # unit test for model mismatch RuntimeError
```

### Pattern 1: Source Document Content Hash + Idempotency

**What:** Compute SHA-256 of the raw file bytes at ingest time; store in `source_documents`.
On re-run, compare stored hash to freshly computed hash — skip all downstream stages if equal.
**When to use:** Every source file ingest entry point.

```python
# Source: [VERIFIED: hashlib stdlib test]
import hashlib

def compute_file_hash(path: str) -> str:
    """SHA-256 of raw file bytes — deterministic regardless of line endings."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def is_source_unchanged(con, source_name: str, current_hash: str) -> bool:
    """Return True if the stored hash matches — safe to skip re-ingest."""
    row = con.execute(
        "SELECT content_hash FROM source_documents WHERE source_name = ?",
        [source_name]
    ).fetchone()
    return row is not None and row["content_hash"] == current_hash
```

### Pattern 2: FTS5 Table with Porter Tokenizer (NOC text search)

**What:** External-content FTS5 virtual table backed by `noc_units` + `noc_elements`. Porter
stemmer handles inflected English ("managing" → "manag", "manages" → "manag").
**When to use:** Any FTS5 query over NOC titles, definitions, or duty statements.

```sql
-- Source: [VERIFIED: sqlite3 FTS5 test on this machine]
CREATE VIRTUAL TABLE IF NOT EXISTS noc_fts USING fts5(
    noc_code UNINDEXED,
    title,
    definition,
    element_type UNINDEXED,
    element_text,
    content='',
    tokenize='porter ascii'
);
```

**Note:** Using `content=''` (contentless FTS5) avoids duplicate storage. Rows are inserted
directly into `noc_fts` from the relational tables. On re-ingest, delete all FTS rows for
affected codes and re-insert.

**FTS5 query:**
```sql
-- MATCH syntax; BM25 ranking via ORDER BY rank
SELECT noc_code, title, rank
FROM noc_fts
WHERE noc_fts MATCH :query
ORDER BY rank
LIMIT 20;
```

### Pattern 3: vec0 Table for Semantic Search

**What:** sqlite-vec `vec0` virtual table storing 768-dim float32 vectors. Each row is keyed
to a `noc_elements` row by rowid. Cosine distance is appropriate for nomic-embed-text output.
**When to use:** Semantic search over duty statement embeddings.

```sql
-- Source: [VERIFIED: sqlite_vec vec0 test on this machine]
CREATE VIRTUAL TABLE IF NOT EXISTS noc_chunks_vec USING vec0(
    rowid INTEGER PRIMARY KEY,
    embedding FLOAT[768] distance_metric=cosine
);
```

**Insert:**
```python
# Source: [VERIFIED: sqlite_vec.serialize_float32 test]
import sqlite_vec

def insert_embedding(con, rowid: int, embedding: list[float]) -> None:
    vec = sqlite_vec.serialize_float32(embedding)
    con.execute(
        "INSERT OR REPLACE INTO noc_chunks_vec(rowid, embedding) VALUES (?, ?)",
        [rowid, vec]
    )
```

**KNN query (Phase 4 consumer):**
```python
query_vec = sqlite_vec.serialize_float32(query_embedding)
rows = con.execute("""
    SELECT c.noc_code, c.element_type, c.element_text, v.distance
    FROM noc_chunks_vec v
    JOIN noc_elements c ON c.id = v.rowid
    WHERE v.embedding MATCH ? AND k = 20
    ORDER BY v.distance
""", [query_vec]).fetchall()
```

### Pattern 4: Index Metadata + Startup Model Assertion (PIPE-05)

**What:** `index_metadata` table stores key/value pairs written at ingest time. The app
lifespan reads `embedding_model` and raises `RuntimeError` if it mismatches `settings.ollama_embed_model`.
This fits the existing `assert_ollama_ready()` pattern in `app/main.py`.
**When to use:** Any time the embedding model or index structure changes.

```python
# Written by ingest script:
con.execute(
    "INSERT OR REPLACE INTO index_metadata(key, value, updated_at) VALUES (?, ?, datetime('now'))",
    ["embedding_model", settings_embed_model]
)

# Called in app/main.py lifespan (new function):
def assert_noc_index_model(con: sqlite3.Connection, configured_model: str) -> None:
    """Raise RuntimeError if index was built with a different embedding model."""
    row = con.execute(
        "SELECT value FROM index_metadata WHERE key = 'embedding_model'"
    ).fetchone()
    if row is None:
        return  # Index not yet built — no assertion (ingest hasn't run)
    stored = row["value"]
    if stored != configured_model:
        raise RuntimeError(
            f"NOC vector index was built with embedding model {stored!r} "
            f"but OLLAMA_EMBED_MODEL is configured as {configured_model!r}. "
            f"Re-run `python scripts/ingest_noc.py` to rebuild the index."
        )
```

### Pattern 5: Batch Embedding with Ollama

**What:** `ollama.embed(model, input=[list of strings])` accepts a `Sequence[str]` — batch
all duty statements for one unit group per call to reduce round-trip overhead.
**When to use:** Any embedding call in the ingest script (synchronous context).

```python
# Source: [VERIFIED: ollama.embed signature inspection]
import ollama

def embed_batch(texts: list[str], model: str) -> list[list[float]]:
    """Embed a batch of texts. Returns list of 768-dim vectors."""
    response = ollama.embed(model=model, input=texts)
    return response.embeddings  # list[list[float]], len == len(texts)
```

**Note:** The ingest script is synchronous (not async) — use `ollama.embed` (sync), not
`ollama.AsyncClient.embed`. Batch size: embed all duties for one unit group at a time
(4–44 items per batch). This balances memory and latency.

### Anti-Patterns to Avoid

- **Embedding the full unit group profile as one blob:** Loses duty-level granularity needed for
  Phase 4 citation. Embed individual duty statements.
- **Using `INSERT OR REPLACE` on vec0 without deleting first:** vec0 may not support UPDATE;
  test on this machine confirmed `INSERT OR REPLACE` works for rowid tables. Use it.
- **Opening a raw `sqlite3.connect()` without `sqlite_vec.load()`:** vec0 DDL and queries will
  fail silently or raise obscure errors. Always use `app.db.get_connection()`.
- **Skipping the `enable_load_extension(True/False)` bracket:** Required before/after
  `sqlite_vec.load()`. Already implemented in `get_connection()` — don't bypass it.
- **FTS5 `content=` table mismatch on re-ingest:** If using external-content FTS5, the
  content table rows must be deleted before re-inserting FTS rows, or the index becomes stale.
  Safest: use contentless FTS5 (`content=''`) and manage population explicitly.
- **Asserting model mismatch when index hasn't been built yet:** The `assert_noc_index_model`
  function must handle the case where `index_metadata` has no `embedding_model` row (ingest
  hasn't run). In that case: pass silently. Only assert when a stored value exists.
- **Polars in ingest script:** `polars` is in `requirements.txt` but NOT installed on this
  machine. Use `csv.DictReader` with `encoding='utf-8-sig'` or `pandas`. [VERIFIED: module check]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| KNN vector search | Custom cosine similarity loop | sqlite-vec `vec0` + `MATCH ... AND k=N` | sqlite-vec handles index, distance metric, and result ordering in C |
| Full-text search with stemming | LIKE queries or regex | SQLite FTS5 with `tokenize='porter ascii'` | BM25 ranking, porter stemmer, phrase queries built-in |
| Embedding vectors | Custom model loader | `ollama.embed(model, input=[...])` | Model already resident in Ollama; no cold-start, no 500MB dependency |
| Content hash | Rolling CRC | `hashlib.sha256(bytes).hexdigest()` | Stdlib; cryptographically stable; 64-char hex string fits TEXT column |
| Idempotency check | `SELECT COUNT(*)` before every INSERT | `INSERT OR IGNORE` + hash comparison | Atomic; no race conditions; single SQL round trip |

**Key insight:** SQLite's FTS5 and sqlite-vec together handle both keyword and semantic search
without additional infrastructure. The entire pipeline runs against one `.db` file.

---

## Common Pitfalls

### Pitfall 1: NOC CSV BOM (Byte Order Mark)
**What goes wrong:** `csv.DictReader` on `noc_structure.csv` produces a column named
`'﻿Level'` (with BOM prefix) instead of `'Level'`, causing silent KeyError on column access.
**Why it happens:** Both NOC CSV files are UTF-8 with BOM. Python's default UTF-8 codec
preserves the BOM as a character in the first field name.
**How to avoid:** Open with `encoding='utf-8-sig'` — Python strips the BOM automatically.
**Warning signs:** `KeyError: 'Level'` or column names starting with `﻿`.

```python
# [VERIFIED: confirmed on actual NOC CSVs]
with open(path, encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
```

### Pitfall 2: FTS5 contentless table — stale index on re-ingest
**What goes wrong:** Re-running ingest without deleting FTS rows produces duplicate FTS
entries, causing inflated result counts and incorrect ranking.
**Why it happens:** Contentless FTS5 (`content=''`) doesn't auto-sync with source tables.
**How to avoid:** On re-ingest, delete all FTS rows for the affected noc_codes before
re-inserting: `DELETE FROM noc_fts WHERE noc_code = ?` or `DELETE FROM noc_fts` for full rebuild.
**Warning signs:** FTS query returns duplicate rows for the same noc_code.

### Pitfall 3: vec0 requires sqlite_vec.load() on every connection
**What goes wrong:** `OperationalError: no such module: vec0` when creating or querying the
vec0 table on a connection that didn't load the extension.
**Why it happens:** sqlite-vec is a loadable extension; it must be registered per-connection.
**How to avoid:** Always use `get_connection()` from `app/db.py`. The ingest script must also
call `sqlite_vec.load()` — use `app.db.get_connection()` or replicate the loading pattern.
**Warning signs:** `OperationalError: no such module: vec0`.

### Pitfall 4: Embedding model name normalization
**What goes wrong:** `settings.ollama_embed_model = 'nomic-embed-text'` (no tag) but Ollama
stores it as `nomic-embed-text:latest`. Mismatch assertion fires falsely.
**Why it happens:** Ollama normalizes model names by appending `:latest` if no tag is present.
The existing `_normalize_model_name()` in `app/main.py` handles this for Ollama model checks.
**How to avoid:** Apply `_normalize_model_name()` to both the stored value and the configured
value before comparing in `assert_noc_index_model()`. [VERIFIED: function exists in app/main.py]
**Warning signs:** Startup fails with model mismatch even after a correct re-ingest.

### Pitfall 5: NOC duty text "header" rows mixed with real duties
**What goes wrong:** The elements CSV contains a generic intro row for every unit group:
`"This group performs some or all of the following duties: "`. Embedding this adds noise.
**Why it happens:** It's present for 516 unit groups as the first "Main duties" row.
**How to avoid:** Filter out rows where `element_text.strip()` matches this pattern
before embedding.
**Warning signs:** All unit groups return this row as a top-k match for any query.

### Pitfall 6: ingest script imports from app.config causing env validation at import
**What goes wrong:** Importing `from app.config import settings` in the ingest script fails
if env vars aren't set (pydantic-settings raises ValidationError at module level).
**Why it happens:** `settings = Settings()` runs at import time in `app/config.py`.
**How to avoid:** Pass model name and db_path as CLI arguments, or load a `.env` file
explicitly before importing. Simplest: accept `--db-path` and `--embed-model` CLI args
using `argparse`, eliminating the dependency on `app.config` in the script.

---

## Code Examples

### SQLite Schema DDL for Phase 2 (extend app/db.py create_schema)

```python
# Source: [VERIFIED: all DDL tested on this machine with sqlite3 + sqlite_vec 0.1.9]

NOC_SCHEMA_DDL = """
    -- Source document provenance (PIPE-04)
    CREATE TABLE IF NOT EXISTS source_documents (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name   TEXT NOT NULL UNIQUE,
        version_label TEXT NOT NULL,
        content_hash  TEXT NOT NULL,
        ingested_at   TEXT NOT NULL
    );

    -- Index metadata: embedding model assertion (PIPE-05)
    CREATE TABLE IF NOT EXISTS index_metadata (
        key        TEXT PRIMARY KEY,
        value      TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    -- NOC unit groups (Level 5 in structure CSV)
    CREATE TABLE IF NOT EXISTS noc_units (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        noc_code     TEXT NOT NULL UNIQUE,
        teer_level   TEXT NOT NULL,
        title        TEXT NOT NULL,
        definition   TEXT NOT NULL,
        source_hash  TEXT NOT NULL  -- FK to source_documents.content_hash
    );

    -- NOC elements (all rows from elements CSV)
    CREATE TABLE IF NOT EXISTS noc_elements (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        noc_code     TEXT NOT NULL,
        element_type TEXT NOT NULL,
        element_text TEXT NOT NULL,
        source_hash  TEXT NOT NULL,
        UNIQUE(noc_code, element_type, element_text)
    );

    -- FTS5 full-text index (contentless — populated by ingest script)
    CREATE VIRTUAL TABLE IF NOT EXISTS noc_fts USING fts5(
        noc_code    UNINDEXED,
        title,
        definition,
        element_type UNINDEXED,
        element_text,
        content='',
        tokenize='porter ascii'
    );

    -- vec0 embedding index (768-dim cosine, rowid matches noc_elements.id)
    CREATE VIRTUAL TABLE IF NOT EXISTS noc_chunks_vec USING vec0(
        rowid INTEGER PRIMARY KEY,
        embedding FLOAT[768] distance_metric=cosine
    );
"""
```

### Ingest Script Core Logic (scripts/ingest_noc.py)

```python
# Source: [VERIFIED: patterns tested; BOM fix, hash, FTS5, vec0 all confirmed]
import argparse, csv, hashlib, sqlite3
import sqlite_vec

def compute_file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def load_connection(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    return con

def embed_batch(texts: list[str], model: str) -> list[list[float]]:
    import ollama
    response = ollama.embed(model=model, input=texts)
    return list(response.embeddings)

DUTY_HEADER = "This group performs some or all of the following duties:"

def is_duty_header(text: str) -> bool:
    return text.strip().rstrip(" :") == DUTY_HEADER.rstrip(" :")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| sentence-transformers (local) | nomic-embed-text via Ollama | Project decision | Eliminates 500MB cold-start; same quality |
| pgvector (Postgres) | sqlite-vec vec0 | Project decision | Single-file DB; no service dependency |
| FTS4 | FTS5 | SQLite 3.9+ (2015) | BM25 ranking built-in; porter tokenizer |
| `ollama.embeddings()` (deprecated) | `ollama.embed()` | ollama-python 0.4+ | `embeddings()` removed; use `embed()` |

**Deprecated/outdated:**
- `ollama.embeddings()`: Removed in recent ollama-python; the current API is `ollama.embed(model, input=[...])`. [VERIFIED: inspect on 0.6.1]
- FTS4: Superseded by FTS5; no reason to use FTS4 in new code.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | nomic-embed-text outputs 768-dim vectors | Standard Stack, vec0 DDL | vec0 table would need a different FLOAT[N] — easy to fix before ingest |
| A2 | Ingest time ~5–11 minutes on Jetson AGX Orin | Summary | Could be faster or slower depending on GPU utilization by Ollama |
| A3 | FTS5 contentless table is the right approach (vs content-table) | Pattern 2 | Content-table FTS5 could reduce DDL complexity; either works |

---

## Open Questions

1. **nomic-embed-text embedding dimension**
   - What we know: nomic-embed-text is documented as 768-dim; FLOAT[768] confirmed working in vec0 on this machine
   - What's unclear: Cannot verify by running an actual embed (Ollama not running during research)
   - Recommendation: Add a Wave 0 test that embeds one string and asserts `len(embedding) == 768`; if wrong, update the DDL before writing any vec0 rows

2. **Should assert_noc_index_model block startup if index hasn't been built?**
   - What we know: PIPE-05 says "app refuses to serve queries" on mismatch — but the index might not exist yet (fresh install)
   - What's unclear: Whether a missing index should be a hard block or a soft warning
   - Recommendation: If `index_metadata` has no `embedding_model` row, log a warning and continue (developer can run ingest before using Phase 4+). Only block if stored model ≠ configured model.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| sqlite-vec | vec0 virtual table | ✓ | 0.1.9 | — |
| FTS5 (SQLite built-in) | FTS5 full-text index | ✓ | built-in | — |
| ollama Python lib | Embedding API | ✓ | 0.6.1 | — |
| Ollama service | nomic-embed-text embeddings | ✗ (not running) | — | Must be running at ingest time; not needed for schema creation |
| pandas | CSV reading (fallback) | ✓ | 2.3.3 | csv.DictReader (stdlib) |
| polars | CSV reading (preferred per requirements.txt) | ✗ | — | Use csv.DictReader or pandas |
| duckdb | Parquet transforms | ✗ | — | Not needed for Phase 2 (CSV-only sources) |
| hashlib | Content hashing | ✓ | stdlib | — |

**Missing dependencies with no fallback:**
- Ollama service must be running at ingest time (not at schema creation time). This is expected — the ingest script is a developer tool, not a startup requirement. Document in script usage.

**Missing dependencies with fallback:**
- `polars`: Use `csv.DictReader` + `utf-8-sig` encoding. This is simpler and has no install dependency.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest tests/test_noc_ingest.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-01 | FTS5 query returns matching unit group records after ingest | integration | `pytest tests/test_noc_ingest.py::test_fts5_query_returns_results -x` | ❌ Wave 0 |
| PIPE-01 | vec0 KNN query returns results after ingest | integration | `pytest tests/test_noc_ingest.py::test_vec0_knn_returns_results -x` | ❌ Wave 0 |
| PIPE-01 | Ingest populates noc_units and noc_elements tables | unit | `pytest tests/test_noc_ingest.py::test_relational_tables_populated -x` | ❌ Wave 0 |
| PIPE-04 | Each source doc has content_hash and version_label | unit | `pytest tests/test_noc_ingest.py::test_source_documents_hash_and_label -x` | ❌ Wave 0 |
| PIPE-04 | noc_units rows store source_hash | unit | `pytest tests/test_noc_ingest.py::test_derived_records_store_source_hash -x` | ❌ Wave 0 |
| PIPE-04 | noc_elements rows store source_hash | unit | `pytest tests/test_noc_ingest.py::test_elements_store_source_hash -x` | ❌ Wave 0 |
| PIPE-05 | Model mismatch raises RuntimeError | unit | `pytest tests/test_noc_startup.py::test_model_mismatch_raises_runtime_error -x` | ❌ Wave 0 |
| PIPE-05 | No index_metadata row → no error (fresh install) | unit | `pytest tests/test_noc_startup.py::test_missing_index_metadata_no_error -x` | ❌ Wave 0 |
| SC-4 | Re-running ingest on unchanged files is idempotent | integration | `pytest tests/test_noc_ingest.py::test_ingest_idempotent -x` | ❌ Wave 0 |

**Notes on test scope:** Tests for FTS5 and vec0 queries (PIPE-01) use a small in-memory DB
with 3–5 synthetic NOC rows — do NOT require Ollama to be running. For vec0 tests, use
pre-computed mock embeddings (e.g., `[0.1] * 768`). The Ollama call is tested via mock.

### Sampling Rate

- **Per task commit:** `pytest tests/test_noc_ingest.py tests/test_noc_startup.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_noc_ingest.py` — covers PIPE-01, PIPE-04, SC-4
- [ ] `tests/test_noc_startup.py` — covers PIPE-05
- [ ] `tests/conftest.py` update — add `noc_db` fixture (in-memory DB with NOC schema + sqlite_vec loaded)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | Ingest script is developer-only CLI; no auth surface |
| V5 Input Validation | yes | NOC CSV rows validated: non-empty noc_code (5 chars), non-empty element_text |
| V6 Cryptography | no | SHA-256 used for content hash only (integrity, not secrecy) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path injection via `--db-path` CLI arg | Tampering | `Path(db_path).resolve()` and validate under project root (same guard as `config.py`) |
| Malformed CSV row causing integer overflow or SQL injection | Tampering | Parameterized queries throughout; no string concatenation into SQL |
| Ollama model name in CLI arg used in `index_metadata` | Spoofing | Model name stored as-is; compared only against `settings.ollama_embed_model` |

---

## Project Constraints (from CLAUDE.md)

- `NEVER save files to the root folder` — ingest script goes in `scripts/`, tests in `tests/`
- `NEVER proactively create documentation files (*.md)` — no README for the script
- Commit every substantive change before declaring done
- SQLite + sqlite-vec for app state (not DuckDB) — confirmed for Phase 2

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: sqlite_vec 0.1.9 on this machine] — vec0 DDL, `serialize_float32`, KNN query, cosine distance, auxiliary columns
- [VERIFIED: sqlite3 FTS5 built-in] — FTS5 virtual table creation, porter tokenizer, contentless table, MATCH query
- [VERIFIED: ollama 0.6.1 signature inspection] — `embed(model, input=Sequence[str])` batch API, `AsyncClient.embed` async variant
- [VERIFIED: csv + actual NOC CSV files] — BOM in both files, column names, Level 5 filtering, element types
- [VERIFIED: hashlib stdlib] — SHA-256 hex digest for content hash
- [VERIFIED: app/main.py reading] — `_normalize_model_name`, lifespan pattern, `assert_ollama_ready` hook to extend
- [VERIFIED: app/db.py reading] — `get_connection` extension loading pattern to reuse in ingest script
- [VERIFIED: pyproject.toml + config.json] — pytest config, nyquist_validation=true, commit_docs=true

### Secondary (MEDIUM confidence)
- [ASSUMED] nomic-embed-text dimensionality = 768 — standard for this model; cannot confirm without running Ollama

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries installed and tested on machine
- Architecture: HIGH — patterns verified with actual sqlite3/sqlite_vec calls
- Pitfalls: HIGH — BOM and embedding pitfalls discovered from actual file inspection and API testing
- Test map: HIGH — test structure mirrors existing Phase 1 test patterns

**Research date:** 2026-05-28
**Valid until:** 2026-06-28 (stable libraries; only invalidated if sqlite-vec or ollama API changes)
