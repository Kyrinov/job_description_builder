"""
app/db.py — SQLite connection factory and schema DDL.

Always obtain connections via get_connection() — never call sqlite3.connect() directly.
sqlite-vec is registered per-connection in get_connection(); DDL that references vec0
will fail if this factory is bypassed.
"""
from __future__ import annotations

import sqlite3

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
        source_hash  TEXT NOT NULL
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

    -- FTS5 full-text index (populated by ingest script)
    CREATE VIRTUAL TABLE IF NOT EXISTS noc_fts USING fts5(
        noc_code,
        title,
        definition,
        element_type,
        element_text,
        tokenize='porter ascii'
    );

    -- vec0 embedding index (1024-dim cosine, rowid matches noc_elements.id)
    -- text-embedding-v3 (DashScope) produces 1024-dim vectors
    CREATE VIRTUAL TABLE IF NOT EXISTS noc_chunks_vec USING vec0(
        rowid INTEGER PRIMARY KEY,
        embedding FLOAT[1024] distance_metric=cosine
    );
"""

CA_JES_SCHEMA_DDL = """
    -- CA restriction/scope/exclusion clauses (PIPE-02, CA-01)
    CREATE TABLE IF NOT EXISTS ca_clauses (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        og_code      TEXT NOT NULL,
        clause_type  TEXT NOT NULL,   -- 'restriction' | 'scope' | 'exclusion' | 'definition'
        article_ref  TEXT NOT NULL,   -- e.g. 'Article 1' or 'Part I'
        clause_text  TEXT NOT NULL,
        source_hash  TEXT NOT NULL,
        UNIQUE(og_code, clause_type, article_ref, clause_text)
    );

    CREATE INDEX IF NOT EXISTS idx_ca_clauses_og ON ca_clauses(og_code);

    -- JES factor objects (PIPE-03)
    CREATE TABLE IF NOT EXISTS jes_factors (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        og_code             TEXT NOT NULL,
        factor_name         TEXT NOT NULL,
        factor_definition   TEXT,
        degree_descriptors  TEXT NOT NULL,   -- JSON: [{"degree":"D1","text":"...","points":5}, ...]
        point_values        TEXT NOT NULL,   -- JSON: {"D1":5,"D2":15,...}
        max_points          INTEGER NOT NULL,
        source_hash         TEXT NOT NULL,
        UNIQUE(og_code, factor_name)
    );

    CREATE INDEX IF NOT EXISTS idx_jes_factors_og ON jes_factors(og_code);

    -- JES occupational group metadata: group definition, inclusions, exclusions (PIPE-03)
    CREATE TABLE IF NOT EXISTS jes_og_metadata (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        og_code          TEXT NOT NULL UNIQUE,
        group_definition TEXT,
        inclusions       TEXT,   -- verbatim inclusions text from the standard
        exclusions       TEXT,   -- verbatim exclusions text from the standard
        methodology      TEXT,   -- e.g. 'point-rating', 'Hay Guide Chart', 'level-descriptions'
        subgroups        TEXT,   -- JSON: ["CT-IAU", "CT-FIN", "CT-EAV"] or null
        source_hash      TEXT NOT NULL
    );

    -- TBS policy doc chunks (FTS5 source table; Phase 5 CLASS-03 prereq)
    CREATE TABLE IF NOT EXISTS policy_chunks (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_name     TEXT NOT NULL,   -- 'directive_on_classification' | 'policy_on_people_management'
        chunk_index  INTEGER NOT NULL,
        chunk_text   TEXT NOT NULL,
        source_hash  TEXT NOT NULL,
        UNIQUE(doc_name, chunk_index)
    );

    CREATE INDEX IF NOT EXISTS idx_policy_chunks_doc ON policy_chunks(doc_name);

    -- FTS5 index over policy chunks (contentless — populated by ingest script)
    CREATE VIRTUAL TABLE IF NOT EXISTS policy_fts USING fts5(
        doc_name     UNINDEXED,
        chunk_text,
        content='',
        tokenize='porter ascii'
    );

    -- Full TBS OCHRO OG definitions (Phase 5, CLASS-01 verbatim citation)
    CREATE TABLE IF NOT EXISTS og_definitions (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        og_code      TEXT NOT NULL UNIQUE,
        og_name      TEXT NOT NULL,
        parent_group TEXT,
        definition   TEXT NOT NULL,
        inclusions   TEXT,
        exclusions   TEXT,
        source_file  TEXT NOT NULL,
        source_hash  TEXT NOT NULL,
        ingested_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
    );

    CREATE INDEX IF NOT EXISTS idx_og_definitions_code ON og_definitions(og_code);
    CREATE INDEX IF NOT EXISTS idx_og_definitions_parent ON og_definitions(parent_group);
"""

NOC_MAPPING_SCHEMA_DDL = """
    -- Result cache for the NL→NOC mapping pipeline (Phase 4, MAP-01/MAP-02).
    -- Keyed on a SHA-256 of (work_description, generation_model, NOC DB version).
    -- The pipeline is deterministic at temperature=0.0, so identical inputs
    -- always produce identical outputs and the cache is safe to use as a fast path.
    CREATE TABLE IF NOT EXISTS noc_mapping_cache (
        cache_key    TEXT PRIMARY KEY,
        result_json  TEXT NOT NULL,
        created_at   TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
    );

    -- Per-request flywheel metrics for the NL→NOC mapping pipeline (Phase 4).
    -- Captures shortlist sizes, instructor retry counts, guardrail firings, and
    -- sampled-for-review flags so future phases can mine production behavior.
    CREATE TABLE IF NOT EXISTS noc_mapping_log (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        wd_hash             TEXT NOT NULL,
        noc_code_rank1      TEXT,
        fts_result_count    INTEGER,
        rerank_result_count INTEGER,
        instructor_retries  INTEGER DEFAULT 0,
        pipeline_latency_ms INTEGER,
        guardrail_fired     INTEGER DEFAULT 0,
        sample_for_review   INTEGER DEFAULT 0,
        created_at          TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
    );
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Open a SQLite connection and register the sqlite-vec extension.

    Must be used for ALL connections in this application — vec0 DDL and queries
    require sqlite-vec to be registered on the connection (T-sqlite-vec-pitfall-3).
    """
    import sqlite_vec  # Import here to surface ImportError clearly if not installed

    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    return con


def create_schema(con: sqlite3.Connection) -> None:
    """
    Create all Phase 1, Phase 2, Phase 3, and Phase 4 tables. Idempotent — safe to call on every startup.

    Tables created here:
    - work_descriptions: one row per WorkDescription entity (data stored as JSON)
    - wd_audit_log: append-only audit trail for every WD state transition
    - _vec_health_check: validates sqlite-vec loaded cleanly
    - source_documents, index_metadata: provenance + model assertion (Phase 2)
    - noc_units, noc_elements, noc_fts, noc_chunks_vec: NOC data (Phase 2)
    - ca_clauses, jes_factors, jes_og_metadata: CA + JES structured records (Phase 3, PIPE-02/PIPE-03/CA-01)
    - policy_chunks, policy_fts: TBS policy doc FTS5 index (Phase 3, Phase 5 prereq)
    - og_definitions, idx_og_definitions_code, idx_og_definitions_parent: TBS OCHRO OG definitions (Phase 5, CLASS-01)
    - noc_mapping_cache: SHA-256-keyed result cache for the NL→NOC pipeline (Phase 4)
    - noc_mapping_log: per-request flywheel metrics (Phase 4)
    """
    con.executescript("""
        CREATE TABLE IF NOT EXISTS work_descriptions (
            id          TEXT PRIMARY KEY,
            session_id  TEXT NOT NULL,
            stage       TEXT NOT NULL,
            data        JSON NOT NULL,
            created_at  TEXT NOT NULL,
            last_modified TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS wd_audit_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            wd_id     TEXT NOT NULL,
            event     TEXT NOT NULL,
            actor     TEXT NOT NULL,
            detail    JSON,
            timestamp TEXT NOT NULL
        );

        -- Validates that sqlite-vec loaded without error on this startup.
        CREATE TABLE IF NOT EXISTS _vec_health_check (
            id INTEGER PRIMARY KEY
        );
    """)
    con.commit()
    con.executescript(NOC_SCHEMA_DDL)
    con.commit()
    con.executescript(CA_JES_SCHEMA_DDL)
    con.commit()
    con.executescript(NOC_MAPPING_SCHEMA_DDL)
    con.commit()


def assert_noc_index_model(con: sqlite3.Connection, configured_model: str) -> None:
    """
    Raise RuntimeError if the NOC vector index was built with a different embedding model.

    Called from app/main.py lifespan after create_schema(). If index_metadata has no
    embedding_model row (ingest has never run), returns silently — never blocks a fresh
    install (PIPE-05).

    Both model names are normalized before comparison: 'nomic-embed-text' and
    'nomic-embed-text:latest' are treated as equal (Pitfall 4 mitigation).
    """
    row = con.execute(
        "SELECT value FROM index_metadata WHERE key = 'embedding_model'"
    ).fetchone()
    if row is None:
        return  # Index not yet built — soft pass

    def _normalize(name: str) -> str:
        """Append :latest tag if the model name has no tag."""
        return name if ":" in name else f"{name}:latest"

    stored = row["value"]
    if _normalize(stored) != _normalize(configured_model):
        raise RuntimeError(
            f"NOC vector index was built with embedding model {stored!r} "
            f"but OLLAMA_EMBED_MODEL is configured as {configured_model!r}. "
            f"Re-run `python scripts/ingest_noc.py` to rebuild the index."
        )
