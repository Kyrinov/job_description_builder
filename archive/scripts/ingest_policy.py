"""
scripts/ingest_policy.py — TBS policy doc FTS5 indexing (Phase 5 CLASS-03 prereq).

Reads data/directive_on_classification.txt and data/policy_on_people_management.txt,
chunks each on paragraph boundaries with a 500-char max and 50-char overlap, upserts
into policy_chunks, then rebuilds the contentless policy_fts virtual table.

Usage:
    python scripts/ingest_policy.py \\
        --db-path /home/charles/job_description_builder/app.db \\
        --data-dir /home/charles/job_description_builder/data \\
        --version-label "TBS Policy v1.0"
"""
from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Policy files (filename stem -> doc_name in DB)
# ---------------------------------------------------------------------------

POLICY_FILES: dict[str, str] = {
    "directive_on_classification.txt": "directive_on_classification",
    "policy_on_people_management.txt": "policy_on_people_management",
}


# ---------------------------------------------------------------------------
# Security: path traversal guard (T-3-01)
# ---------------------------------------------------------------------------

def validate_db_path(db_path: str) -> Path:
    resolved = Path(db_path).resolve()
    project_root = Path(__file__).resolve().parent.parent
    try:
        resolved.relative_to(project_root)
        return resolved
    except ValueError:
        print(
            f"Error: --db-path must be under the project root ({project_root}).\n"
            f"Got: {resolved!r}\nPath traversal is not permitted.",
            file=sys.stderr,
        )
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Connection factory
# ---------------------------------------------------------------------------

def load_connection(db_path: str) -> sqlite3.Connection:
    import sqlite_vec
    con = sqlite3.connect(str(db_path), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    return con


# ---------------------------------------------------------------------------
# Stage 0: Content hash (PIPE-04)
# ---------------------------------------------------------------------------

def compute_file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---------------------------------------------------------------------------
# Stage 1: Text chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, max_chars: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text on paragraph boundaries (double newline), packing paragraphs into chunks
    that stay under max_chars. When a chunk would exceed max_chars, emit the current
    chunk and start a new one carrying the last `overlap` chars of the previous chunk.

    Long single paragraphs that exceed max_chars are hard-split.
    """
    if not text or not text.strip():
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    def _flush():
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
        current = ""

    for para in paragraphs:
        # Hard-split paragraphs longer than max_chars
        if len(para) > max_chars:
            _flush()
            for i in range(0, len(para), max_chars - overlap if overlap < max_chars else max_chars):
                chunks.append(para[i:i + max_chars].strip())
            continue

        candidate = (current + "\n\n" + para).strip() if current else para
        if len(candidate) <= max_chars:
            current = candidate
        else:
            _flush()
            tail = chunks[-1][-overlap:] if chunks and overlap else ""
            current = (tail + " " + para).strip() if tail else para

    _flush()
    return [c for c in chunks if c]


# ---------------------------------------------------------------------------
# Stage 2: source_documents upsert (PIPE-04)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Stage 3: policy_chunks upsert (INSERT OR IGNORE on (doc_name, chunk_index))
# ---------------------------------------------------------------------------

def upsert_policy_chunks(
    con: sqlite3.Connection,
    doc_name: str,
    chunks: list[str],
    source_hash: str,
) -> None:
    """
    Insert chunks for one policy document. UNIQUE(doc_name, chunk_index) makes this idempotent.
    On re-ingest with the same chunk count, INSERT OR IGNORE skips existing rows.
    On re-ingest with a different chunk count (file changed), old rows for indices beyond
    the new length are deleted so policy_fts rebuild stays consistent.
    """
    # Delete rows for this doc with chunk_index >= new length (covers shortened files)
    con.execute(
        "DELETE FROM policy_chunks WHERE doc_name = ? AND chunk_index >= ?",
        [doc_name, len(chunks)],
    )
    for i, chunk in enumerate(chunks):
        con.execute(
            """INSERT INTO policy_chunks(doc_name, chunk_index, chunk_text, source_hash)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(doc_name, chunk_index) DO UPDATE SET
                   chunk_text  = excluded.chunk_text,
                   source_hash = excluded.source_hash""",
            [doc_name, i, chunk, source_hash],
        )
    con.commit()


# ---------------------------------------------------------------------------
# Stage 4: policy_fts rebuild (contentless FTS5)
# ---------------------------------------------------------------------------

def rebuild_policy_fts(con: sqlite3.Connection) -> None:
    """
    Repopulate the contentless policy_fts virtual table from policy_chunks.
    Contentless FTS5 doesn't auto-sync or support DELETE; drop and recreate is the pattern.
    """
    con.execute("DROP TABLE IF EXISTS policy_fts")
    con.execute("""
        CREATE VIRTUAL TABLE policy_fts USING fts5(
            doc_name     UNINDEXED,
            chunk_text,
            content='',
            tokenize='porter ascii'
        )
    """)
    con.execute("""
        INSERT INTO policy_fts(rowid, doc_name, chunk_text)
        SELECT id, doc_name, chunk_text FROM policy_chunks
    """)
    con.commit()


# ---------------------------------------------------------------------------
# Stage 5: per-file processing
# ---------------------------------------------------------------------------

def process_one_policy(
    con: sqlite3.Connection,
    policy_path: Path,
    doc_name: str,
    version_label: str,
) -> int:
    """Returns number of chunks indexed (or 0 if skipped)."""
    file_hash = compute_file_hash(str(policy_path))
    source_name = policy_path.name

    upsert_source_document(con, source_name, version_label, file_hash)

    existing = con.execute(
        "SELECT content_hash FROM source_documents WHERE source_name = ?",
        [source_name],
    ).fetchone()
    existing_chunks = con.execute(
        "SELECT COUNT(*) FROM policy_chunks WHERE doc_name = ?", [doc_name]
    ).fetchone()[0]
    if existing and existing["content_hash"] == file_hash and existing_chunks > 0:
        print(f"  [{doc_name}] Unchanged — skipping chunking", flush=True)
        return 0

    with open(policy_path, encoding="utf-8") as f:
        text = f.read()
    chunks = chunk_text(text, max_chars=500, overlap=50)
    upsert_policy_chunks(con, doc_name, chunks, file_hash)
    return len(chunks)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest TBS policy TXT files into policy_chunks + policy_fts.",
    )
    parser.add_argument("--db-path", required=True,
                        help="SQLite database path (must be under project root)")
    parser.add_argument("--data-dir", required=True,
                        help="Project data directory (contains the two TBS .txt files)")
    parser.add_argument("--version-label", default="TBS Policy v1.0",
                        help="Version label stored in source_documents")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = validate_db_path(args.db_path)

    data_dir = Path(args.data_dir).resolve()
    if not data_dir.is_dir():
        print(f"Error: data directory not found: {data_dir}", file=sys.stderr)
        return 1

    print(f"[1/4] Connecting to {db_path} ...", flush=True)
    con = load_connection(str(db_path))
    from app.db import create_schema
    create_schema(con)

    print(f"[2/4] Discovering policy files under {data_dir} ...", flush=True)
    targets = []
    for filename, doc_name in POLICY_FILES.items():
        p = data_dir / filename
        if p.is_file():
            targets.append((p, doc_name))
        else:
            print(f"  WARNING: {p} not found — skipping", flush=True)
    print(f"  Found {len(targets)} policy files")

    print(f"[3/4] Chunking + upserting policy_chunks ...", flush=True)
    total_chunks = 0
    for path, doc_name in targets:
        count = process_one_policy(con, path, doc_name, args.version_label)
        total_chunks += count
        print(f"  [{doc_name}] {count} chunks", flush=True)

    print(f"[4/4] Rebuilding policy_fts ...", flush=True)
    rebuild_policy_fts(con)

    chunk_total = con.execute("SELECT COUNT(*) FROM policy_chunks").fetchone()[0]
    fts_total = con.execute("SELECT COUNT(*) FROM policy_fts").fetchone()[0]
    print(
        f"\nIngest complete:\n"
        f"  policy_chunks: {chunk_total:,} rows\n"
        f"  policy_fts:    {fts_total:,} rows\n",
        flush=True,
    )

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
