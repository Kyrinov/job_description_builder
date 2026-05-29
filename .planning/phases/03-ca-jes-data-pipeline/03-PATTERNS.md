# Phase 3: CA + JES Data Pipeline - Pattern Map

**Mapped:** 2026-05-29
**Files analyzed:** 8
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/db.py` | config/schema | batch | `app/db.py` (existing NOC_SCHEMA_DDL block) | exact — extend in place |
| `scripts/ingest_ca.py` | script/pipeline | batch + LLM | `scripts/ingest_noc.py` | role-match |
| `scripts/ingest_jes.py` | script/pipeline | batch + LLM | `scripts/ingest_noc.py` | role-match |
| `scripts/ingest_policy.py` | script/pipeline | batch (no LLM) | `scripts/ingest_noc.py` | role-match |
| `tests/test_ca_ingest.py` | test | CRUD | `tests/test_noc_ingest.py` | exact |
| `tests/test_jes_ingest.py` | test | CRUD | `tests/test_noc_ingest.py` | exact |
| `tests/test_policy_ingest.py` | test | CRUD | `tests/test_noc_ingest.py` | role-match |
| `tests/conftest.py` | test config | N/A | `tests/conftest.py` (existing `noc_db` fixture) | exact — extend in place |

---

## Pattern Assignments

### `app/db.py` — add `CA_JES_SCHEMA_DDL`, extend `create_schema()`

**Analog:** `app/db.py` lines 12–65 (`NOC_SCHEMA_DDL`) and lines 85–122 (`create_schema`)

**DDL constant pattern** (lines 12–14, 65, 121–122):
```python
NOC_SCHEMA_DDL = """
    -- ... all DDL as a single triple-quoted string
"""
```
Copy this pattern verbatim for `CA_JES_SCHEMA_DDL`. The constant holds the full DDL block including `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, and `CREATE VIRTUAL TABLE IF NOT EXISTS` statements.

**`create_schema()` extension pattern** (lines 85–122):
```python
def create_schema(con: sqlite3.Connection) -> None:
    con.executescript("""
        -- Phase 1 tables ...
    """)
    con.commit()
    con.executescript(NOC_SCHEMA_DDL)
    con.commit()
```
Add one more block after the existing `NOC_SCHEMA_DDL` call:
```python
    con.executescript(CA_JES_SCHEMA_DDL)
    con.commit()
```
Do NOT alter existing DDL or the `NOC_SCHEMA_DDL` call. Append only.

---

### `scripts/ingest_ca.py` (script, batch + LLM)

**Analog:** `scripts/ingest_noc.py`

**Imports pattern** (lines 22–30):
```python
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
```
Add `instructor` and `pydantic` imports for LLM extraction:
```python
import instructor
import ollama
from pydantic import BaseModel
```

**Path traversal guard pattern** (lines 50–69):
```python
def validate_db_path(db_path: str) -> Path:
    resolved = Path(db_path).resolve()
    project_root = Path(__file__).resolve().parent.parent
    try:
        resolved.relative_to(project_root)
        return resolved
    except ValueError:
        print(
            f"Error: --db-path must be under the project root ({project_root}).\n"
            f"Got: {resolved!r}\n"
            "Path traversal is not permitted.",
            file=sys.stderr,
        )
        raise SystemExit(1)
```
Copy this function unchanged into `ingest_ca.py`, `ingest_jes.py`, and `ingest_policy.py`.

**Connection factory pattern** (lines 76–90):
```python
def load_connection(db_path: str) -> sqlite3.Connection:
    import sqlite_vec
    con = sqlite3.connect(str(db_path), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    return con
```
Copy unchanged. Purpose: avoids importing `app.config` which requires env vars.

**Content hash pattern** (lines 97–100):
```python
def compute_file_hash(path: str) -> str:
    """SHA-256 of raw file bytes — deterministic regardless of line endings (PIPE-04)."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
```
Copy unchanged into all three ingest scripts.

**`upsert_source_document` pattern** (lines 138–167):
```python
def upsert_source_document(
    con: sqlite3.Connection,
    source_name: str,
    version_label: str,
    content_hash: str,
) -> None:
    existing = con.execute(
        "SELECT content_hash FROM source_documents WHERE source_name = ?",
        [source_name],
    ).fetchone()

    if existing is None:
        con.execute(
            """INSERT INTO source_documents(source_name, version_label, content_hash, ingested_at)
               VALUES (?, ?, ?, datetime('now'))""",
            [source_name, version_label, content_hash],
        )
    elif existing["content_hash"] != content_hash:
        con.execute(
            """UPDATE source_documents
               SET content_hash = ?, version_label = ?, ingested_at = datetime('now')
               WHERE source_name = ?""",
            [content_hash, version_label, source_name],
        )
    con.commit()
```
Copy unchanged into all three ingest scripts.

**Hash-check skip pattern** — derive from `upsert_source_document`: after calling it, query whether derived rows already exist for this source. If `content_hash` matches stored hash AND derived table has rows for this OG, skip LLM call:
```python
existing = con.execute(
    "SELECT content_hash FROM source_documents WHERE source_name = ?",
    [source_name],
).fetchone()
ca_count = con.execute(
    "SELECT COUNT(*) FROM ca_clauses WHERE og_code = ?", [og_code]
).fetchone()[0]
if existing and existing["content_hash"] == file_hash and ca_count > 0:
    print(f"  [{og_code}] Unchanged — skipping LLM extraction")
    continue
```

**`INSERT OR IGNORE` upsert pattern** (lines 190–195, `upsert_noc_units`):
```python
con.execute(
    """INSERT OR IGNORE INTO ca_clauses(og_code, clause_type, article_ref, clause_text, source_hash)
       VALUES (?, ?, ?, ?, ?)""",
    [og_code, clause["clause_type"], clause["article_ref"], clause["clause_text"], source_hash],
)
con.commit()
```
Use `INSERT OR IGNORE` — the `UNIQUE(og_code, clause_type, article_ref, clause_text)` constraint makes this idempotent.

**`argparse` CLI pattern** (lines 391–411):
```python
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="...")
    parser.add_argument("--db-path", required=True, help="...")
    parser.add_argument("--data-dir", required=True, help="...")
    parser.add_argument("--model", default="gemma4:31b", help="...")
    parser.add_argument("--version-label", default="CA 2023-2026 v1.0", help="...")
    return parser.parse_args()
```

**`main()` structure pattern** (lines 414–473):
```python
def main() -> int:
    args = parse_args()
    db_path = validate_db_path(args.db_path)
    # ... validate data dirs exist ...
    print(f"[1/N] Connecting to {db_path} ...")
    con = load_connection(str(db_path))
    from app.db import create_schema
    create_schema(con)
    # ... numbered stages with print() progress ...
    con.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

---

### `scripts/ingest_jes.py` (script, batch + LLM)

**Analog:** `scripts/ingest_noc.py` — identical structural pattern to `ingest_ca.py`.

All shared helpers (`validate_db_path`, `load_connection`, `compute_file_hash`, `upsert_source_document`) are copy-identical from `ingest_noc.py`.

**OG code extraction from filename** — unique to JES, no analog in ingest_noc.py:
```python
def extract_og_code(filename: str) -> str:
    """First word of filename is the OG code. E.g. 'EC Economics...' -> 'EC'."""
    return Path(filename).stem.split()[0]
```

**Skip Application Guidelines** — unique to JES, no analog:
```python
def is_application_guidelines(filename: str) -> bool:
    return "Application Guidelines" in filename or "Application_Guidelines" in filename
```

**`INSERT OR IGNORE` upsert for `jes_factors`**:
```python
con.execute(
    """INSERT OR IGNORE INTO jes_factors(
           og_code, factor_name, factor_definition,
           degree_descriptors, point_values, max_points, source_hash
       ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
    [og_code, f["factor_name"], f.get("factor_definition"),
     json.dumps(f["degree_descriptors"]), json.dumps(f["point_values"]),
     f["max_points"], source_hash],
)
con.commit()
```

---

### `scripts/ingest_policy.py` (script, batch, no LLM)

**Analog:** `scripts/ingest_noc.py` — same shared helpers. No LLM import needed.

**FTS5 `policy_fts` rebuild pattern** — derived from `rebuild_fts5` in `ingest_noc.py` (lines 229–295), adapted for contentless FTS5 population:
```python
def rebuild_policy_fts(con: sqlite3.Connection) -> None:
    """Rebuild contentless FTS5 index from policy_chunks."""
    con.execute("INSERT INTO policy_fts(policy_fts) VALUES('rebuild')")
    con.commit()
```
Note: `policy_fts` is defined as `content=''` (contentless) — use the `rebuild` command, NOT `DELETE + INSERT`. This differs from `noc_fts` which stores data directly.

**Text chunking pattern** — no analog in existing codebase; implement per research spec:
```python
def chunk_text(text: str, max_chars: int = 500, overlap: int = 50) -> list[str]:
    """Split on double-newline paragraph boundaries; enforce max_chars with overlap."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars and current:
            chunks.append(current.strip())
            current = current[-overlap:] + " " + para if overlap else para
        else:
            current = (current + "\n\n" + para).strip() if current else para
    if current:
        chunks.append(current.strip())
    return chunks
```

---

## Shared Patterns

### Content Hash (PIPE-04)
**Source:** `scripts/ingest_noc.py` lines 97–100
**Apply to:** `ingest_ca.py`, `ingest_jes.py`, `ingest_policy.py`
```python
def compute_file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
```

### Source Document Provenance (PIPE-04)
**Source:** `scripts/ingest_noc.py` lines 138–167
**Apply to:** All three ingest scripts — call once per source file before derived-row upserts.

### Path Traversal Guard (T-2-01)
**Source:** `scripts/ingest_noc.py` lines 50–69
**Apply to:** All three ingest scripts — first operation in `main()`.

### Connection Factory (no app import)
**Source:** `scripts/ingest_noc.py` lines 76–90
**Apply to:** All three ingest scripts — never import `app.config` in CLI scripts.

### Schema Initialization in main()
**Source:** `scripts/ingest_noc.py` lines 433–434
```python
from app.db import create_schema
create_schema(con)
```
**Apply to:** All three ingest scripts — call after `load_connection()` to ensure tables exist.

### `INSERT OR IGNORE` Idempotency
**Source:** `scripts/ingest_noc.py` lines 190–195, 210–219
**Apply to:** All three ingest scripts — each table has a `UNIQUE` constraint; `INSERT OR IGNORE` is the correct upsert pattern.

### Progress Printing Convention
**Source:** `scripts/ingest_noc.py` lines 429–470
```python
print(f"[1/N] Connecting to {db_path} ...")
print("[2/N] Computing content hashes ...")
# ... numbered stages, flush=True on slow operations ...
print(f"\nIngest complete:\n  table_name: {count:,} rows\n")
```
**Apply to:** All three ingest scripts.

---

## Test Patterns

### `tests/test_ca_ingest.py` and `tests/test_jes_ingest.py`

**Analog:** `tests/test_noc_ingest.py`

**`_run_ingest` helper pattern** (lines 56–93):
```python
def _run_ca_ingest(con, ca_json_data, og_codes, source_hash=None):
    """
    Helper: run ingest_ca stages directly against a fixture connection,
    bypassing file I/O and Ollama (both mocked).
    """
    from scripts.ingest_ca import (
        upsert_source_document,
        upsert_ca_clauses,
    )
    if source_hash is None:
        source_hash = hashlib.sha256(b"EC_full.json").hexdigest()
    upsert_source_document(con, "EC_full.json", "CA v1.0", source_hash)
    # LLM call mocked — inject synthetic clause list directly
    upsert_ca_clauses(con, og_codes, SYNTHETIC_CLAUSES, source_hash)
```

**Test function signature pattern** (line 99):
```python
def test_ca_ingest_creates_source_document_row(ca_jes_db):
    """After ingest, source_documents has row for EC_full.json (PIPE-04)."""
    _run_ca_ingest(ca_jes_db)
    row = ca_jes_db.execute(
        "SELECT content_hash FROM source_documents WHERE source_name = 'EC_full.json'"
    ).fetchone()
    assert row is not None
    assert len(row["content_hash"]) == 64
```

**Idempotency test pattern** (lines 195–215):
```python
def test_ca_ingest_idempotent(ca_jes_db):
    _run_ca_ingest(ca_jes_db)
    count_1 = ca_jes_db.execute("SELECT COUNT(*) FROM ca_clauses").fetchone()[0]
    _run_ca_ingest(ca_jes_db)   # second run, same hash
    count_2 = ca_jes_db.execute("SELECT COUNT(*) FROM ca_clauses").fetchone()[0]
    assert count_1 == count_2, f"ca_clauses grew on second ingest: {count_1} -> {count_2}"
```

**Ollama mock pattern** (lines 89–91):
```python
with patch("scripts.ingest_ca.extract_clauses_via_llm", return_value=SYNTHETIC_CLAUSES):
    _run_ca_ingest(ca_jes_db)
```
All tests must mock the LLM call — do NOT require Ollama running.

---

### `tests/conftest.py` — add `ca_jes_db` fixture

**Analog:** `tests/conftest.py` lines 57–67 (`noc_db` fixture):
```python
@pytest.fixture
def noc_db(tmp_path):
    """
    Temp-file SQLite connection with NOC schema and sqlite_vec loaded.
    Used by test_noc_ingest.py tests — does NOT require Ollama to be running.
    """
    from app.db import get_connection, create_schema
    db_path = str(tmp_path / "test_noc.db")
    con = get_connection(db_path)
    create_schema(con)
    yield con
    con.close()
```

Add the following fixture immediately after `noc_db`:
```python
@pytest.fixture
def ca_jes_db(tmp_path):
    """
    Temp-file SQLite connection with full schema (NOC + CA/JES) and sqlite_vec loaded.
    Used by test_ca_ingest.py, test_jes_ingest.py, test_policy_ingest.py.
    Does NOT require Ollama to be running.
    """
    from app.db import get_connection, create_schema
    db_path = str(tmp_path / "test_ca_jes.db")
    con = get_connection(db_path)
    create_schema(con)   # creates all tables including CA_JES_SCHEMA_DDL
    yield con
    con.close()
```
Key: uses a different `db_path` (`test_ca_jes.db`) to avoid sharing state with `noc_db` tests.

---

## No Analog Found

No files in Phase 3 lack an analog. All patterns are covered by `ingest_noc.py` and `test_noc_ingest.py`.

The following logic has no direct analog but is fully specified in RESEARCH.md:
- `chunk_text()` in `ingest_policy.py` — paragraph chunking with overlap
- `extract_og_code()` in `ingest_jes.py` — first-word filename parsing
- Multi-OG abbreviation parsing in `ingest_ca.py` — `"(IT)(CS)"` → `["IT", "CS"]`

---

## Metadata

**Analog search scope:** `scripts/`, `tests/`, `app/`
**Files scanned:** 4 source files read in full
**Pattern extraction date:** 2026-05-29
