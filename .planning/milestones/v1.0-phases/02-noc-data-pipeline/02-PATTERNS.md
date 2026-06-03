# Phase 2: NOC Data Pipeline - Pattern Map

**Mapped:** 2026-05-28
**Files analyzed:** 6 (3 new, 3 modified)
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `scripts/ingest_noc.py` | utility/script | batch + file-I/O | `scripts/qwen_watchdog.py` | role-match (CLI structure, argparse, `__main__` guard) |
| `app/db.py` | config/schema | CRUD | `app/db.py` itself (Phase 1) | exact (extend, same file) |
| `app/main.py` | config/startup | request-response | `app/main.py` itself (Phase 1) | exact (extend, same file) |
| `tests/test_noc_ingest.py` | test | batch | `tests/test_db.py` | exact (same role: schema + data operations, no fixtures, `from app.db import`) |
| `tests/test_noc_startup.py` | test | request-response | `tests/test_startup.py` | exact (same role: lifespan RuntimeError assertions, asyncio, monkeypatch) |
| `tests/conftest.py` | test config | — | `tests/conftest.py` itself (Phase 1) | exact (extend, same file) |

---

## Pattern Assignments

### `scripts/ingest_noc.py` (utility/script, batch + file-I/O)

**Analog:** `scripts/qwen_watchdog.py`

**Imports pattern** (lines 1-17 of qwen_watchdog.py):
```python
#!/usr/bin/env python3
"""[One-line description of what the script does.]"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sqlite3
import sqlite_vec
from pathlib import Path
```

**argparse + `__main__` guard pattern** (lines 198-225 of qwen_watchdog.py):
```python
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="[Script description]"
    )
    parser.add_argument("--db-path", required=True, help="Path to SQLite database file")
    parser.add_argument("--embed-model", default="nomic-embed-text:latest",
                        help="Ollama embedding model name")
    parser.add_argument("--data-dir", required=True, help="Path to data/ directory")
    parser.add_argument("--version-label", default="NOC 2021",
                        help="Version label for source_documents")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    # ... stage execution ...
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Note on app.config import avoidance:** Per RESEARCH.md Pitfall 6, the ingest script
must NOT import `from app.config import settings`. Use `argparse` CLI args (`--db-path`,
`--embed-model`) instead. This eliminates the pydantic-settings ValidationError at import
time when env vars aren't set.

**DB connection pattern** — copy directly from `app/db.py` lines 14-28 (the sqlite-vec
extension loading bracket). The ingest script replicates this locally rather than importing
`app.db.get_connection()` to avoid the FastAPI dependency chain:
```python
def load_connection(db_path: str) -> sqlite3.Connection:
    import sqlite_vec  # surfaces ImportError clearly if not installed
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    return con
```

**Path validation pattern** (mirrors `app/config.py` lines 61-81):
```python
from pathlib import Path

def validate_db_path(db_path: str) -> Path:
    """Security: resolve path and validate it stays under project root."""
    resolved = Path(db_path).resolve()
    project_root = Path(__file__).resolve().parent.parent
    try:
        resolved.relative_to(project_root)
        return resolved
    except ValueError:
        raise SystemExit(
            f"--db-path must be under the project root ({project_root}). "
            f"Got: {resolved!r}. Path traversal is not permitted."
        )
```

**Error handling pattern** (from qwen_watchdog.py — bare `except Exception` is acceptable
for diagnostic scripts; ingest script should use specific exceptions):
```python
try:
    result = stage_function(con, args)
except Exception as exc:
    print(f"Stage failed: {exc}", file=sys.stderr)
    return 1
```

---

### `app/db.py` — extend with NOC schema DDL + `assert_noc_index_model()` (schema, CRUD)

**Analog:** `app/db.py` Phase 1 (same file, extend)

**Existing pattern to follow** — `create_schema()` uses a single `con.executescript()`
with `CREATE TABLE IF NOT EXISTS` for idempotency. Extend by appending `NOC_SCHEMA_DDL`
to the existing `executescript` call, or call `con.executescript(NOC_SCHEMA_DDL)` as a
second call at the end of `create_schema()`.

**Current `create_schema` pattern** (lines 31-66 of app/db.py):
```python
def create_schema(con: sqlite3.Connection) -> None:
    """
    Create all Phase 1 tables. Idempotent — safe to call on every startup.
    ...
    """
    con.executescript("""
        CREATE TABLE IF NOT EXISTS work_descriptions (
            ...
        );
        ...
    """)
    con.commit()
```

**`assert_noc_index_model` function to add** (new function, modeled after
`assert_ollama_ready` in `app/main.py` lines 40-67):
```python
def assert_noc_index_model(con: sqlite3.Connection, configured_model: str) -> None:
    """
    Raise RuntimeError if the NOC vector index was built with a different model.

    Called from lifespan after create_schema. If index_metadata has no
    embedding_model row (ingest hasn't run yet), returns silently — never blocks
    a fresh install (PIPE-05, open question 2).
    """
    row = con.execute(
        "SELECT value FROM index_metadata WHERE key = 'embedding_model'"
    ).fetchone()
    if row is None:
        return  # Index not yet built — soft pass
    stored = row["value"]
    # Normalize both sides: Ollama appends :latest if no tag present
    def _normalize(name: str) -> str:
        return name if ":" in name else f"{name}:latest"
    if _normalize(stored) != _normalize(configured_model):
        raise RuntimeError(
            f"NOC vector index was built with embedding model {stored!r} "
            f"but OLLAMA_EMBED_MODEL is configured as {configured_model!r}. "
            f"Re-run `python scripts/ingest_noc.py` to rebuild the index."
        )
```

**Note on `_normalize_model_name`:** The normalization helper already exists in
`app/main.py` (line 35-37). `assert_noc_index_model` lives in `app/db.py`, so it
must either duplicate the two-line helper inline or the planner must decide to import it.
Simplest: inline it in `assert_noc_index_model` since it's two lines.

---

### `app/main.py` — extend lifespan to call `assert_noc_index_model()` (startup, request-response)

**Analog:** `app/main.py` Phase 1 (same file, extend)

**Existing lifespan pattern to extend** (lines 70-96 of app/main.py):
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # --- startup ---
    await assert_ollama_ready()
    con = get_connection(settings.db_path)
    create_schema(con)
    con.close()                   # <-- extend here, before close()

    yield

    # --- shutdown ---
```

**Extension — add one call between `create_schema` and `con.close()`:**
```python
    con = get_connection(settings.db_path)
    create_schema(con)
    assert_noc_index_model(con, settings.ollama_embed_model)  # PIPE-05
    con.close()
```

**Import to add at top of main.py** (mirrors existing `from app.db import create_schema, get_connection`
on line 22):
```python
from app.db import assert_noc_index_model, create_schema, get_connection
```

---

### `tests/test_noc_ingest.py` (test, batch)

**Analog:** `tests/test_db.py`

**Imports + fixture usage pattern** (lines 1-6 of test_db.py):
```python
"""[Description of what these tests cover (PIPE-01, PIPE-04, SC-4).]"""
import pytest
import sqlite3


def test_relational_tables_populated(noc_db):
    """After ingest, noc_units and noc_elements must have rows."""
    from tests.conftest import run_ingest_on_fixture_db  # or inline ingest call
    ...
```

**Schema inspection pattern** (lines 22-23 of test_db.py — use for table/column checks):
```python
tables = {row[0] for row in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()}
assert "noc_units" in tables
```

**Column inspection pattern** (lines 47-54 of test_db.py):
```python
info = con.execute("PRAGMA table_info(noc_units)").fetchall()
col_names = {row[1] for row in info}
required = {"id", "noc_code", "teer_level", "title", "definition", "source_hash"}
assert required.issubset(col_names), f"Missing columns: {required - col_names}"
```

**Idempotency test pattern** (lines 37-41 of test_db.py):
```python
def test_ingest_idempotent(noc_db):
    """Running ingest twice on the same fixture data must not raise or duplicate rows."""
    ingest(noc_db, ...)
    count_before = noc_db.execute("SELECT COUNT(*) FROM noc_units").fetchone()[0]
    ingest(noc_db, ...)  # second run
    count_after = noc_db.execute("SELECT COUNT(*) FROM noc_units").fetchone()[0]
    assert count_before == count_after
```

**Ollama mock pattern** (from test_startup.py lines 30-34 — use `unittest.mock.patch`
or pass a mock `embed_fn` into the ingest function):
```python
from unittest.mock import patch, MagicMock

def test_vec0_knn_returns_results(noc_db):
    mock_embeddings = [[0.1] * 768] * 3  # pre-computed; no Ollama needed
    with patch("scripts.ingest_noc.embed_batch", return_value=mock_embeddings):
        ...
```

---

### `tests/test_noc_startup.py` (test, request-response)

**Analog:** `tests/test_startup.py` (exact match — same pattern: async lifespan, RuntimeError, monkeypatch)

**Imports + env setup pattern** (lines 1-18 of test_startup.py):
```python
"""Tests for NOC index model mismatch assertion (PIPE-05)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _set_valid_env(monkeypatch, temp_db_path, tmp_path):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "gemma4:31b")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    monkeypatch.setenv("DB_PATH", temp_db_path)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))


def _clear_app_modules():
    import sys
    for key in list(sys.modules.keys()):
        if key.startswith("app."):
            del sys.modules[key]
```

**RuntimeError assertion pattern** (lines 23-38 of test_startup.py):
```python
@pytest.mark.asyncio
async def test_model_mismatch_raises_runtime_error(monkeypatch, temp_db_path, tmp_path):
    """assert_noc_index_model must raise RuntimeError on embedding model mismatch."""
    _set_valid_env(monkeypatch, temp_db_path, tmp_path)
    _clear_app_modules()

    # Arrange: write a mismatched model name into index_metadata
    from app.db import get_connection, create_schema, assert_noc_index_model
    con = get_connection(temp_db_path)
    create_schema(con)
    con.execute(
        "INSERT INTO index_metadata(key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ["embedding_model", "some-other-model:latest"]
    )
    con.commit()

    with pytest.raises(RuntimeError, match="NOC vector index was built with"):
        assert_noc_index_model(con, "nomic-embed-text:latest")
    con.close()
```

**Soft-pass (no index) pattern** — mirrors the `if row is None: return` branch:
```python
@pytest.mark.asyncio
async def test_missing_index_metadata_no_error(monkeypatch, temp_db_path, tmp_path):
    """assert_noc_index_model must not raise when index_metadata has no embedding_model row."""
    _set_valid_env(monkeypatch, temp_db_path, tmp_path)
    _clear_app_modules()

    from app.db import get_connection, create_schema, assert_noc_index_model
    con = get_connection(temp_db_path)
    create_schema(con)
    # No insert into index_metadata — simulates fresh install
    assert_noc_index_model(con, "nomic-embed-text:latest")  # must not raise
    con.close()
```

---

### `tests/conftest.py` — add `noc_db` fixture (test config)

**Analog:** `tests/conftest.py` Phase 1 (same file, extend)

**Existing fixture pattern to follow** (lines 29-32 of conftest.py):
```python
@pytest.fixture
def temp_db_path(tmp_path):
    """Temporary SQLite database file path for isolation."""
    return str(tmp_path / "test_app.db")
```

**New `noc_db` fixture to add** — an in-memory or temp-path SQLite connection with NOC
schema + sqlite_vec loaded (models the pattern from test_db.py lines 17-24):
```python
@pytest.fixture
def noc_db(tmp_path):
    """
    In-memory SQLite connection with NOC schema and sqlite_vec loaded.
    Used by test_noc_ingest.py tests — does NOT require Ollama.
    """
    from app.db import get_connection, create_schema
    db_path = str(tmp_path / "test_noc.db")
    con = get_connection(db_path)
    create_schema(con)
    yield con
    con.close()
```

---

## Shared Patterns

### sqlite-vec Extension Loading
**Source:** `app/db.py` lines 14-28
**Apply to:** `scripts/ingest_noc.py` (replicate locally), all test files that use `get_connection()`
```python
import sqlite_vec  # Import here to surface ImportError clearly if not installed

con = sqlite3.connect(db_path, check_same_thread=False)
con.row_factory = sqlite3.Row
con.enable_load_extension(True)
sqlite_vec.load(con)
con.enable_load_extension(False)
```

### Module Cache Clearing Between Tests
**Source:** `tests/conftest.py` lines 7-10 and `tests/test_startup.py` lines 16-19
**Apply to:** `tests/test_noc_startup.py` (imports app modules after env changes)
```python
def _clear_app_modules():
    import sys
    for key in list(sys.modules.keys()):
        if key.startswith("app."):
            del sys.modules[key]
```

### RuntimeError Startup Assertion Shape
**Source:** `app/main.py` lines 40-67 (`assert_ollama_ready`)
**Apply to:** `app/db.py::assert_noc_index_model`, `tests/test_noc_startup.py`

The pattern: function raises `RuntimeError` with a human-readable message naming the
mismatch and the remediation command. Tests assert with `pytest.raises(RuntimeError, match=...)`.

### Model Name Normalization
**Source:** `app/main.py` lines 35-37
**Apply to:** `app/db.py::assert_noc_index_model` (inline the two-line helper)
```python
def _normalize_model_name(name: str) -> str:
    """Append :latest tag if the model name has no tag (Pitfall 2 mitigation)."""
    return name if ":" in name else f"{name}:latest"
```

### `con.executescript()` + `con.commit()` DDL Idiom
**Source:** `app/db.py` lines 40-66
**Apply to:** `app/db.py` NOC schema extension

All DDL is applied in one `executescript()` block ending with `con.commit()`. New NOC
tables follow the same `CREATE TABLE IF NOT EXISTS` + `CREATE VIRTUAL TABLE IF NOT EXISTS`
idiom for idempotency.

### `__future__` annotations + module docstring
**Source:** `app/db.py` lines 1-8, `app/main.py` lines 1-11
**Apply to:** `scripts/ingest_noc.py`
```python
"""
scripts/ingest_noc.py — [one-line description].

[Usage line]
"""
from __future__ import annotations
```

### pytest `asyncio_mode = "auto"` (no explicit `@pytest.mark.asyncio` required)
**Source:** `pyproject.toml` line 9 — `asyncio_mode = "auto"`
**Apply to:** `tests/test_noc_startup.py`

`asyncio_mode = "auto"` is already set. All `async def test_*` functions are collected
automatically. The `@pytest.mark.asyncio` decorator seen in `test_startup.py` is redundant
but harmless — either style is acceptable.

---

## No Analog Found

All 6 files have analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `app/`, `tests/`, `scripts/`
**Files scanned:** 9 (app/db.py, app/main.py, app/config.py, app/models/work_description.py,
tests/conftest.py, tests/test_config.py, tests/test_db.py, tests/test_startup.py,
scripts/qwen_watchdog.py)
**Pattern extraction date:** 2026-05-28
