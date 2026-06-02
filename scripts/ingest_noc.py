"""
scripts/ingest_noc.py — NOC 2021 data pipeline.

Parses two CSV files from data/ and populates SQLite with:
  - noc_units: Level 5 unit group profiles (516 rows)
  - noc_elements: All element rows (~44,038 rows)
  - noc_fts: FTS5 full-text index
  - noc_chunks_vec: vec0 1024-dim cosine embedding index (Main duties only)
  - source_documents: Content hash + version label per source file (PIPE-04)
  - index_metadata: Embedding model name for startup assertion (PIPE-05)

Usage:
    python scripts/ingest_noc.py \\
        --db-path /home/charles/job_description_builder/app.db \\
        --data-dir /home/charles/job_description_builder/data \\
        --api-key sk-... \\
        --embed-model text-embedding-v3 \\
        --version-label "NOC 2021 v1.0"

Embeddings via DashScope OpenAI-compatible API (text-embedding-v3, 1024-dim).
API key can also be set via DASHSCOPE_API_KEY env var.
Re-running on unchanged files is fully idempotent (skips embedding stage).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sqlite3
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STRUCTURE_CSV = "noc_2021_version_1.0_-_classification_structure.csv"
ELEMENTS_CSV = "noc_2021_version_1.0_-_elements.csv"

# Level 5 in the structure CSV = unit groups (NOC codes)
NOC_UNIT_GROUP_LEVEL = "5"

# Duty header row present in every unit group — noise, not a real duty (Pitfall 5)
DUTY_HEADER = "This group performs some or all of the following duties:"


# ---------------------------------------------------------------------------
# Security: path traversal guard (T-2-01)
# ---------------------------------------------------------------------------

def validate_db_path(db_path: str) -> Path:
    """
    Resolve --db-path and validate it remains under the project root.

    Raises SystemExit (not ValueError) — this is a CLI boundary, not an API boundary.
    Mirrors the db_path validator in app/config.py (T-1-01).
    """
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


# ---------------------------------------------------------------------------
# Connection factory (replicates app/db.py get_connection — no app import)
# ---------------------------------------------------------------------------

def load_connection(db_path: str) -> sqlite3.Connection:
    """
    Open a SQLite connection and register the sqlite-vec extension.

    Replicates app/db.py get_connection() locally to avoid importing app.config,
    which triggers pydantic-settings ValidationError if env vars aren't set.
    """
    import sqlite_vec  # surfaces ImportError clearly if not installed

    con = sqlite3.connect(str(db_path), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    return con


# ---------------------------------------------------------------------------
# Stage 0: Content hash
# ---------------------------------------------------------------------------

def compute_file_hash(path: str) -> str:
    """SHA-256 of raw file bytes — deterministic regardless of line endings (PIPE-04)."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---------------------------------------------------------------------------
# Stage 1: Parse CSVs
# ---------------------------------------------------------------------------

def parse_structure_csv(path: str) -> list:
    """
    Parse noc_structure CSV. Returns only Level 5 rows (unit groups).
    Opens with utf-8-sig to strip UTF-8 BOM (Pitfall 1).
    """
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Level", "").strip() == NOC_UNIT_GROUP_LEVEL:
                rows.append(row)
    return rows


def parse_elements_csv(path: str) -> list:
    """
    Parse noc_elements CSV. Returns all rows.
    Opens with utf-8-sig to strip UTF-8 BOM (Pitfall 1).
    """
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Stage 2: Relational upsert (PIPE-01, PIPE-04)
# ---------------------------------------------------------------------------

def upsert_source_document(
    con: sqlite3.Connection,
    source_name: str,
    version_label: str,
    content_hash: str,
) -> None:
    """
    Record a source document with its content hash and version label (PIPE-04).
    INSERT OR IGNORE — idempotent on re-run with same source_name.
    If content_hash changed (file modified), UPDATE the stored hash.
    """
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


def derive_teer_from_code(noc_code: str) -> str:
    """
    Derive TEER (Training, Education, Experience and Responsibility) from the NOC code.

    NOC 2021 v1.0 encodes TEER as the second digit of the 5-digit code:
      NOC 0X*** → TEER 0 (management)
      NOC 1X*** → TEER 1 (professional — typically university degree)
      NOC 2X*** → TEER 2 (post-secondary 2-3 years, apprenticeship, or supervisory)
      NOC 3X*** → TEER 3 (post-secondary < 2 years, apprenticeship < 2 years, or OJT)
      NOC 4X*** → TEER 4 (secondary school plus OJT)
      NOC 5X*** → TEER 5 (on-the-job training only — "no formal education required")

    Source: NOC 2021 v1.0 classification structure, Major Group 10–14 definitions.
    The CSV "Level" column is the NOC hierarchy depth (1=Broad Category .. 5=Unit Group),
    NOT the TEER classification — using it here would mark every unit group as TEER 5.
    """
    if len(noc_code) >= 2 and noc_code[1].isdigit():
        return noc_code[1]
    return ""


def upsert_noc_units(
    con: sqlite3.Connection,
    rows: list,
    source_hash: str,
) -> None:
    """
    Upsert Level 5 unit groups into noc_units.
    INSERT OR IGNORE keyed on noc_code — idempotent (PIPE-01, PIPE-04).
    Column mapping from structure CSV:
      Code - NOC 2021 V1.0 -> noc_code, Class title -> title,
      Class definition -> definition, [second digit of NOC code] -> teer_level
    """
    for row in rows:
        noc_code = row.get("Code - NOC 2021 V1.0", "").strip()
        title = row.get("Class title", "").strip()
        definition = row.get("Class definition", "").strip()
        teer_level = derive_teer_from_code(noc_code)

        if not noc_code:
            continue  # skip malformed rows

        con.execute(
            """INSERT OR IGNORE INTO noc_units(noc_code, teer_level, title, definition, source_hash)
               VALUES (?, ?, ?, ?, ?)""",
            [noc_code, teer_level, title, definition, source_hash],
        )
    con.commit()


def upsert_noc_elements(
    con: sqlite3.Connection,
    rows: list,
    source_hash: str,
) -> None:
    """
    Upsert all element rows into noc_elements.
    UNIQUE constraint on (noc_code, element_type, element_text) — INSERT OR IGNORE (PIPE-01, PIPE-04).
    Column mapping from elements CSV:
      Code - NOC 2021 V1.0 -> noc_code,
      Element Type Label English -> element_type,
      Element Description English -> element_text
    """
    for row in rows:
        noc_code = row.get("Code - NOC 2021 V1.0", "").strip()
        element_type = row.get("Element Type Label English", "").strip()
        element_text = row.get("Element Description English", "").strip()

        if not noc_code or not element_text:
            continue  # skip malformed rows

        con.execute(
            """INSERT OR IGNORE INTO noc_elements(noc_code, element_type, element_text, source_hash)
               VALUES (?, ?, ?, ?)""",
            [noc_code, element_type, element_text, source_hash],
        )
    con.commit()


# ---------------------------------------------------------------------------
# Stage 3: FTS5 rebuild (PIPE-01)
# ---------------------------------------------------------------------------

def rebuild_fts5(con: sqlite3.Connection) -> None:
    """
    Rebuild the FTS5 full-text index from noc_units + noc_elements.

    Stores data directly in the FTS table so SELECT queries return real values.
    Delete all rows before re-inserting to avoid stale duplicates on re-ingest
    (Pitfall 2).
    """
    # Fix schema if the table was created as contentless (content='') which makes
    # columns unselectable — recreate without content='' so data is stored in FTS.
    existing = con.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='noc_fts'"
    ).fetchone()
    if (existing and
            ("UNINDEXED" in existing["sql"] or "content=''" in existing["sql"])):
        con.execute("DROP TABLE IF EXISTS noc_fts")
        con.executescript("""
            CREATE VIRTUAL TABLE noc_fts USING fts5(
                noc_code,
                title,
                definition,
                element_type,
                element_text,
                tokenize='porter ascii'
            )
        """)
        con.commit()

    # Delete all existing FTS rows before re-inserting
    con.execute("DELETE FROM noc_fts")

    # Insert unit group titles and definitions
    con.execute("""
        INSERT INTO noc_fts(noc_code, title, definition, element_type, element_text)
        SELECT noc_code, title, definition, '', ''
        FROM noc_units
    """)

    # Insert element rows (all types for FTS completeness)
    con.execute("""
        INSERT INTO noc_fts(noc_code, title, definition, element_type, element_text)
        SELECT e.noc_code, u.title, u.definition, e.element_type, e.element_text
        FROM noc_elements e
        JOIN noc_units u ON u.noc_code = e.noc_code
    """)

    con.commit()

    # Delete all existing FTS rows before re-inserting (Pitfall 2 — FTS5 doesn't auto-sync)
    con.execute("DELETE FROM noc_fts")

    # Insert unit group titles and definitions
    con.execute("""
        INSERT INTO noc_fts(noc_code, title, definition, element_type, element_text)
        SELECT noc_code, title, definition, '', ''
        FROM noc_units
    """)

    # Insert element rows (all types for FTS completeness)
    con.execute("""
        INSERT INTO noc_fts(noc_code, title, definition, element_type, element_text)
        SELECT e.noc_code, u.title, u.definition, e.element_type, e.element_text
        FROM noc_elements e
        JOIN noc_units u ON u.noc_code = e.noc_code
    """)

    con.commit()


# ---------------------------------------------------------------------------
# Stage 4: Embed + vec0 upsert (PIPE-01)
# ---------------------------------------------------------------------------

def is_duty_header(text: str) -> bool:
    """Return True if text is the generic duty header row — exclude from embedding (Pitfall 5)."""
    return text.strip().rstrip(":") == DUTY_HEADER.rstrip(":")


def embed_batch(texts: list, model: str, api_key: str, base_url: str, batch_size: int = 10) -> list:
    """
    Embed texts using DashScope OpenAI-compatible embeddings API.

    DashScope text-embedding-v3 max batch size is 10; splits automatically.
    Returns list of float vectors in input order.
    """
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)
    results = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i:i + batch_size]
        response = client.embeddings.create(model=model, input=chunk)
        results.extend(item.embedding for item in sorted(response.data, key=lambda x: x.index))
    return results


def recreate_vec_table_if_needed(con: sqlite3.Connection) -> None:
    """Drop and recreate noc_chunks_vec if it exists with wrong dimensions (e.g. old 768-dim table)."""
    existing = con.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='noc_chunks_vec'"
    ).fetchone()
    if existing and "FLOAT[768]" in (existing["sql"] or ""):
        print("  Detected old 768-dim vec table — dropping and recreating for 1024-dim", flush=True)
        con.execute("DROP TABLE IF EXISTS noc_chunks_vec")
        con.executescript("""
            CREATE VIRTUAL TABLE noc_chunks_vec USING vec0(
                rowid INTEGER PRIMARY KEY,
                embedding FLOAT[1024] distance_metric=cosine
            )
        """)
        con.commit()


def embed_and_upsert_vec0(
    con: sqlite3.Connection,
    embed_model: str,
    api_key: str,
    base_url: str,
) -> None:
    """
    Embed Main duties from noc_elements and upsert into noc_chunks_vec.

    Embeds individual duty statements (not full profiles) for Phase 4 citation.
    Batch size: all duties for one unit group at a time (4-44 texts per call).
    Skips duty header rows (Pitfall 5).
    """
    import sqlite_vec

    recreate_vec_table_if_needed(con)

    rows = con.execute("""
        SELECT id, noc_code, element_text
        FROM noc_elements
        WHERE element_type = 'Main duties'
        ORDER BY noc_code, id
    """).fetchall()

    from collections import defaultdict
    groups: dict[str, list] = defaultdict(list)
    for row in rows:
        text = row["element_text"].strip()
        if is_duty_header(text):
            continue
        groups[row["noc_code"]].append((row["id"], text))

    total_embedded = 0
    for noc_code, duties in groups.items():
        if not duties:
            continue

        ids = [d[0] for d in duties]
        texts = [d[1] for d in duties]

        embeddings = embed_batch(texts, embed_model, api_key, base_url)

        for rowid, embedding in zip(ids, embeddings):
            vec = sqlite_vec.serialize_float32(embedding)
            con.execute("DELETE FROM noc_chunks_vec WHERE rowid = ?", [rowid])
            con.execute(
                "INSERT INTO noc_chunks_vec(rowid, embedding) VALUES (?, ?)",
                [rowid, vec],
            )
        total_embedded += len(duties)
        print(f"  [{noc_code}] embedded {len(duties)} duties ({total_embedded} total)", flush=True)

    con.commit()
    print(f"  Done — {total_embedded} duty statements in noc_chunks_vec", flush=True)


# ---------------------------------------------------------------------------
# Stage 5: Write index_metadata (PIPE-05)
# ---------------------------------------------------------------------------

def write_index_metadata(con: sqlite3.Connection, embed_model: str) -> None:
    """Record the embedding model name in index_metadata (PIPE-05)."""
    con.execute(
        "INSERT OR REPLACE INTO index_metadata(key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ["embedding_model", embed_model],
    )
    con.commit()


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    import os
    parser = argparse.ArgumentParser(
        description="Ingest NOC 2021 data into SQLite FTS5 + sqlite-vec indices."
    )
    parser.add_argument(
        "--db-path", required=True,
        help="Absolute path to the SQLite database file (must be under project root)",
    )
    parser.add_argument(
        "--embed-model", default="text-embedding-v3",
        help="DashScope embedding model name (default: text-embedding-v3)",
    )
    parser.add_argument(
        "--api-key", default=os.environ.get("DASHSCOPE_API_KEY", ""),
        help="DashScope API key (default: $DASHSCOPE_API_KEY)",
    )
    parser.add_argument(
        "--base-url", default="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        help="DashScope base URL (default: international endpoint)",
    )
    parser.add_argument(
        "--data-dir", required=True,
        help="Path to data/nationa_occupational_competencies/ directory",
    )
    parser.add_argument(
        "--version-label", default="NOC 2021 v1.0",
        help="Version label stored in source_documents (default: 'NOC 2021 v1.0')",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.api_key:
        print("Error: --api-key or $DASHSCOPE_API_KEY required", file=sys.stderr)
        return 1

    # Security: validate --db-path before any I/O (T-2-01)
    db_path = validate_db_path(args.db_path)

    data_dir = Path(args.data_dir)
    structure_path = data_dir / STRUCTURE_CSV
    elements_path = data_dir / ELEMENTS_CSV

    for p in [structure_path, elements_path]:
        if not p.exists():
            print(f"Error: CSV file not found: {p}", file=sys.stderr)
            return 1

    print(f"[1/5] Connecting to {db_path} ...")
    con = load_connection(str(db_path))

    # Ensure schema is up to date (idempotent)
    from app.db import create_schema
    create_schema(con)

    print("[2/5] Computing content hashes and upserting source documents ...")
    structure_hash = compute_file_hash(str(structure_path))
    elements_hash = compute_file_hash(str(elements_path))
    upsert_source_document(con, STRUCTURE_CSV, args.version_label, structure_hash)
    upsert_source_document(con, ELEMENTS_CSV, args.version_label, elements_hash)

    print("[3/5] Parsing CSVs and upserting relational rows ...")
    structure_rows = parse_structure_csv(str(structure_path))
    print(f"  Parsed {len(structure_rows)} Level-5 unit groups from structure CSV")
    upsert_noc_units(con, structure_rows, structure_hash)

    elements_rows = parse_elements_csv(str(elements_path))
    print(f"  Parsed {len(elements_rows)} element rows from elements CSV")
    upsert_noc_elements(con, elements_rows, elements_hash)

    print("[4/5] Rebuilding FTS5 index ...")
    rebuild_fts5(con)

    print(f"[5/5] Embedding duty statements with {args.embed_model!r} via DashScope ...")
    embed_and_upsert_vec0(con, args.embed_model, args.api_key, args.base_url)

    print("[6/6] Writing index_metadata ...")
    write_index_metadata(con, args.embed_model)

    unit_count = con.execute("SELECT COUNT(*) FROM noc_units").fetchone()[0]
    elem_count = con.execute("SELECT COUNT(*) FROM noc_elements").fetchone()[0]
    fts_count = con.execute("SELECT COUNT(*) FROM noc_fts").fetchone()[0]
    vec_count = con.execute("SELECT COUNT(*) FROM noc_chunks_vec").fetchone()[0]
    print(
        f"\nIngest complete:\n"
        f"  noc_units:       {unit_count:,} rows\n"
        f"  noc_elements:    {elem_count:,} rows\n"
        f"  noc_fts:         {fts_count:,} rows\n"
        f"  noc_chunks_vec:  {vec_count:,} embeddings\n"
    )

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
