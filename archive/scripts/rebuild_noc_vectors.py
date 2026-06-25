#!/usr/bin/env python3
"""
scripts/rebuild_noc_vectors.py

Standalone script to rebuild noc_chunks_vec as FLOAT[768] using nomic-embed-text via Ollama.

Prerequisites:
  - Ollama running locally with nomic-embed-text pulled
  - app.db contains noc_elements rows with element_type = 'Main duties'

Usage:
  python scripts/rebuild_noc_vectors.py --db-path app.db --base-url http://localhost:11434

The script:
  1. Detects noc_chunks_vec dimensions (FLOAT[1024] from Phase 2 DashScope ingest)
  2. Drops and recreates noc_chunks_vec as FLOAT[768] (nomic-embed-text dimensions)
  3. Re-embeds all noc_elements WHERE element_type = 'Main duties' via Ollama
  4. Inserts embeddings into the new FLOAT[768] table
  5. Updates index_metadata SET value='nomic-embed-text:latest' WHERE key='embedding_model'

Run this once before Phase 4 tests against the live app.db.
"""
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

_DEFAULT_DB = str(_project_root / "app.db")
_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_EMBED_MODEL = "nomic-embed-text:latest"


def validate_db_path(db_path: str) -> Path:
    """Reject --db-path outside the project root (path traversal guard)."""
    resolved = Path(db_path).resolve()
    try:
        resolved.relative_to(_project_root)
        return resolved
    except ValueError:
        print(
            f"Error: --db-path must be under the project root ({_project_root}).",
            file=sys.stderr,
        )
        raise SystemExit(1)


def load_connection(db_path: str) -> sqlite3.Connection:
    """Open SQLite connection with sqlite-vec extension registered."""
    con = sqlite3.connect(str(db_path), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    return con


def recreate_vec_table_for_nomic(con: sqlite3.Connection) -> None:
    """Drop noc_chunks_vec if FLOAT[1024] and recreate as FLOAT[768] for nomic-embed-text."""
    existing = con.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='noc_chunks_vec'"
    ).fetchone()
    if existing and "FLOAT[1024]" in (existing["sql"] or ""):
        print("  Detected FLOAT[1024] vec table — dropping and recreating as FLOAT[768].", flush=True)
        con.execute("DROP TABLE IF EXISTS noc_chunks_vec")
    elif existing and "FLOAT[768]" in (existing["sql"] or ""):
        print("  noc_chunks_vec is already FLOAT[768] — clearing rows for fresh embed.", flush=True)
        con.execute("DELETE FROM noc_chunks_vec")
    else:
        print("  noc_chunks_vec not found — creating fresh FLOAT[768] table.", flush=True)
        con.execute("DROP TABLE IF EXISTS noc_chunks_vec")
    con.executescript(
        "CREATE VIRTUAL TABLE IF NOT EXISTS noc_chunks_vec USING vec0("
        "rowid INTEGER PRIMARY KEY, embedding FLOAT[768] distance_metric=cosine)"
    )
    con.commit()


async def embed_batch(
    texts: list[str], base_url: str, model: str, batch_size: int = 50
) -> list[list[float]]:
    """Embed texts in batches using OllamaAsyncClient."""
    client = OllamaAsyncClient(host=base_url)
    all_vecs: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        for text in batch:
            resp = await client.embed(model=model, input=text)
            all_vecs.append(resp.embeddings[0])
        print(f"    Embedded {min(i + batch_size, len(texts))}/{len(texts)} rows...", flush=True)
    return all_vecs


async def main_async(db_path: str, base_url: str, embed_model: str, verify: bool) -> int:
    print(f"[1/4] Connecting to {db_path} ...", flush=True)
    resolved = validate_db_path(db_path)
    con = load_connection(str(resolved))

    # Validate assumption A2: all teer_level values are numeric
    non_numeric = con.execute(
        "SELECT teer_level FROM noc_units WHERE CAST(teer_level AS INTEGER) = 0 "
        "AND teer_level != '0'"
    ).fetchall()
    if non_numeric:
        print(f"  WARNING: {len(non_numeric)} noc_units rows have non-numeric teer_level.", file=sys.stderr)

    rows = con.execute(
        "SELECT id, element_text FROM noc_elements WHERE element_type = 'Main duties'"
    ).fetchall()
    if not rows:
        print("ERROR: No 'Main duties' rows in noc_elements. Run scripts/ingest_noc.py first.", file=sys.stderr)
        return 1
    print(f"  Found {len(rows)} 'Main duties' rows to embed.", flush=True)

    if verify:
        print("[verify] --verify flag set; skipping embed, exiting 0 if table exists.", flush=True)
        has_table = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='noc_chunks_vec'"
        ).fetchone()
        con.close()
        return 0 if has_table else 1

    print(f"[2/4] Rebuilding noc_chunks_vec as FLOAT[768] ...", flush=True)
    recreate_vec_table_for_nomic(con)

    print(f"[3/4] Embedding {len(rows)} rows with {embed_model} via {base_url} ...", flush=True)
    texts = [row["element_text"] for row in rows]
    vectors = await embed_batch(texts, base_url, embed_model)

    for (elem_id, _), vec in zip(rows, vectors):
        con.execute(
            "INSERT INTO noc_chunks_vec(rowid, embedding) VALUES (?, ?)",
            (elem_id, sqlite_vec.serialize_float32(vec)),
        )
    con.commit()
    print(f"  Inserted {len(vectors)} embedding rows.", flush=True)

    print(f"[4/4] Updating index_metadata ...", flush=True)
    con.execute(
        "INSERT OR REPLACE INTO index_metadata(key, value, updated_at) "
        "VALUES (?, ?, datetime('now'))",
        ("embedding_model", embed_model),
    )
    con.commit()
    con.close()
    print("Done. noc_chunks_vec rebuilt as FLOAT[768] with nomic-embed-text embeddings.", flush=True)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild noc_chunks_vec as FLOAT[768] (nomic-embed-text)")
    parser.add_argument("--db-path", default=_DEFAULT_DB, help="Path to SQLite DB (default: app.db)")
    parser.add_argument("--base-url", default=_DEFAULT_BASE_URL, help="Ollama base URL")
    parser.add_argument("--embed-model", default=_DEFAULT_EMBED_MODEL, help="Embedding model name")
    parser.add_argument("--verify", action="store_true", help="Check table exists without re-embedding")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(main_async(args.db_path, args.base_url, args.embed_model, args.verify))


if __name__ == "__main__":
    raise SystemExit(main())
