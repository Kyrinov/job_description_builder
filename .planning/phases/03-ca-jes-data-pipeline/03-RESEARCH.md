# Phase 3: CA + JES Data Pipeline - Research

**Researched:** 2026-05-29
**Domain:** SQLite schema extension, LLM-based clause extraction, structured text parsing, TBS policy FTS5 indexing
**Confidence:** HIGH

---

## Summary

Phase 3 adds two ingest scripts and a policy-doc indexer that extend the existing SQLite schema
with four new tables (`ca_clauses`, `jes_factors`, `policy_chunks`, `policy_fts`). All follow
the same hash-check idempotency pattern established in Phase 2 (`ingest_noc.py`).

**CA data** lives in `data/agreements/{OG}/{OG}_full.json` — 28 OG directories, each with a
structured JSON (keys: `title`, `url`, `preamble`, `sections`, `tables`, `index_record`).
Sections vary wildly by CA: some have individual article sections (EC: 73 sections), others roll
multiple articles into top-level parts (IT_CS: 23 sections, PA: 9 parts). Because of this
structural inconsistency, LLM extraction (gemma4:31b via Ollama) is the correct approach for
extracting restriction/scope/exclusion clauses — regex cannot handle the variation reliably.
Each CA JSON file is hashed and recorded in `source_documents` before LLM extraction runs.

**JES data** lives in `data/Job_evaluation/` — 18 TXT files, each covering one OG. The EC JES
is highly structured (explicit RATING SCALE tables, degree points listed inline); the IT JES is
more narrative but still has clear element-section headings. LLM extraction is used for
consistency: extract `(og_code, factor_name, factor_definition, degree_descriptors, point_values,
max_points)` per element. This produces the structured factor objects queryable by
`(og_code, factor_name)` as required by PIPE-03.

**TBS policy docs** (`data/directive_on_classification.txt`,
`data/policy_on_people_management.txt`) are FTS5-indexed in a `policy_fts` virtual table so
Phase 5 OG Classification can run targeted queries (e.g. "AS vs EC test" from CLASS-03).

All three scripts run independently. Suggested execution order: `ingest_policy.py` (no LLM,
fast), then `ingest_jes.py` (18 LLM calls), then `ingest_ca.py` (28 LLM calls, heaviest).
Each script is fully idempotent on unchanged source files.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-02 | CA ingest pipeline extracting restriction/scope/exclusion clauses per OG, stored as structured records indexed by OG code | 28 CA JSONs confirmed present; LLM extraction via gemma4:31b; `ca_clauses` table design verified against data |
| PIPE-03 | JES ingest pipeline producing structured factor objects (og_code, factor_name, degree_descriptors, point_range) in SQLite | 18 JES TXTs confirmed; EC+IT format examined; `jes_factors` table design verified against data |
| CA-01 | Pre-extract restriction/scope/exclusion clauses at ingest time, indexed by OG code | Same as PIPE-02 — fulfilled by `ingest_ca.py` + `ca_clauses` table |
| PIPE-04 (partial) | Every source document records content hash + version label; every derived record stores source hash | SHA-256 of raw file bytes → `source_documents`; `source_hash` FK on `ca_clauses` and `jes_factors` |
</phase_requirements>

---

## Data Inventory

### CA JSONs — `data/agreements/`

28 OG directories confirmed. Each contains `{OG}_full.json` and `{OG}_full.txt`.

| OG Dir | Notes |
|--------|-------|
| AI, AO, CX, EB, EC, EL, FB, FS, NR, PA, PO, RE, RM, RO, SH, SO, SRC, SRE, SRW, SV, TC, TR, UT | Single-OG CAs |
| CT_FI | Two OGs: CT (EAV/FIN/IAU subgroups) and FI |
| IT_CS | Two OGs: IT and CS |
| LP_LA | Two OGs: LP and LA |
| SP_AP | Two OGs: SP and AP (subgroups: AC, AG, BI, CH, FO, MT, PC, SG-PAT, SG-SRE) |

JSON schema (consistent across all 28):
```
{
  "title": str,
  "url": str,
  "preamble": str,
  "sections": [{"id": str, "title": str, "text": str, "tables": [...]}],
  "tables": [...],
  "index_record": {
    "abbreviation": "(EC)",
    "group": "Economics...",
    "group_subgroup": "...",
    "code": "231",
    "union": "...",
    "signing_date": "YYYY-MM-DD",
    "expiry_date": "YYYY-MM-DD",
    "url": str
  }
}
```

Section counts: EC=73, PA=9 (parts), IT_CS=23. Structural variety mandates LLM extraction.

**Multi-OG parsing rule**: `index_record.abbreviation` contains `(OG1)(OG2)` for combined CAs.
Strip parens and split on `)(` to get list of OG codes: `"(IT)(CS)"` → `["IT", "CS"]`.

### JES TXTs — `data/Job_evaluation/`

18 files. OGs covered: CT, EC, ED, EX, FB (x2: standard + guidelines), FS (x2), IT, LC, LP, MT, NT, NU, PO, PS, SW, WP. Note: AS, CS, CR, PM and others use the Universal Classification Standard (UCS) — no JES TXT for those OGs, which is expected.

File format: raw scraped HTML-to-text. Structure:
- Header block: SOURCE url, TITLE, EFFECTIVE DATE
- Group definition paragraph
- TYPE OF STANDARD line
- ELEMENTS list (numbered, e.g. "1. Decision making (Responsibility) - 21% - max 210 pts")
- POINT BOUNDARIES table (level ranges)
- RATING SCALE table (element/degree/points matrix)
- ELEMENT DEFINITIONS section with per-element degree narratives

EC JES example (highly structured):
```
Element 1 - Decision making: D1=5, D2=15, D3=35, D4=60, D5=90, D6=125, D7=165, D8=210

ELEMENT 1 - DECISION MAKING (RESPONSIBILITY):
Measures latitude applied and impact of decision making...
- D1 (5 pts): Issue-specific, impact on own work unit...
- D2 (15 pts): ...
```

IT JES has more narrative prose per degree but same element-heading structure.

**OG code extraction from filename**: `"EC Economics and Social Science Services - Job Evaluation Standard 2017.txt"` → first word = `"EC"`. Consistent across all 18 files.

### TBS Policy Docs

| File | Size estimate | Purpose in Phase 5 |
|------|--------------|---------------------|
| `data/directive_on_classification.txt` | ~50KB | AS vs. EC disambiguation test (CLASS-03) |
| `data/policy_on_people_management.txt` | ~30KB | General classification policy context |

Chunk size recommendation: 500-character overlapping chunks (50-char overlap) — small enough for precise FTS5 recall, large enough to preserve sentence context.

---

## Architectural Responsibility Map

| Capability | Owner | Notes |
|------------|-------|-------|
| CA clause extraction | `scripts/ingest_ca.py` | LLM call per OG CA; writes `ca_clauses` |
| JES factor extraction | `scripts/ingest_jes.py` | LLM call per JES TXT; writes `jes_factors` |
| Policy doc FTS5 indexing | `scripts/ingest_policy.py` | No LLM; writes `policy_chunks` + `policy_fts` |
| Schema DDL | `app/db.py` CA_JES_SCHEMA_DDL | Follows NOC_SCHEMA_DDL pattern; called from `create_schema()` |
| Content hashing | All 3 scripts | SHA-256 of raw file bytes → `source_documents` |
| OG code resolution (multi-OG) | `ingest_ca.py` | Parse `(IT)(CS)` abbreviation; insert one row per OG code |
| Startup assertion (Phase 5+) | `app/main.py` | No new assertion needed — Phase 3 tables are query-only at startup |

---

## SQLite Schema Additions (app/db.py)

Add `CA_JES_SCHEMA_DDL` constant, append to `create_schema()` after `NOC_SCHEMA_DDL`:

```sql
-- CA restriction/scope/exclusion clauses (PIPE-02, CA-01)
CREATE TABLE IF NOT EXISTS ca_clauses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    og_code      TEXT NOT NULL,
    clause_type  TEXT NOT NULL,   -- 'restriction' | 'scope' | 'exclusion' | 'definition'
    article_ref  TEXT NOT NULL,   -- e.g. "Article 1" or "Part I"
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
    degree_descriptors  TEXT NOT NULL,   -- JSON: [{"degree": "D1", "text": "...", "points": 5}, ...]
    point_values        TEXT NOT NULL,   -- JSON: {"D1": 5, "D2": 15, ...}
    max_points          INTEGER NOT NULL,
    source_hash         TEXT NOT NULL,
    UNIQUE(og_code, factor_name)
);

CREATE INDEX IF NOT EXISTS idx_jes_factors_og ON jes_factors(og_code);

-- TBS policy doc chunks (FTS5 source table)
CREATE TABLE IF NOT EXISTS policy_chunks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_name     TEXT NOT NULL,   -- 'directive_on_classification' | 'policy_on_people_management'
    chunk_index  INTEGER NOT NULL,
    chunk_text   TEXT NOT NULL,
    source_hash  TEXT NOT NULL,
    UNIQUE(doc_name, chunk_index)
);

-- FTS5 index over policy chunks
CREATE VIRTUAL TABLE IF NOT EXISTS policy_fts USING fts5(
    doc_name     UNINDEXED,
    chunk_text,
    content='',
    tokenize='porter ascii'
);
```

---

## Script Architecture

### `scripts/ingest_ca.py`

Pattern mirrors `ingest_noc.py`. Stages:
1. **Hash check** — `SHA-256(CA_JSON_bytes)` → `source_documents`. If hash unchanged and `ca_clauses` rows exist for this OG: skip LLM call.
2. **OG code resolution** — parse `index_record.abbreviation` to get list of OG codes.
3. **Section selection** — concatenate text of sections matching keywords: scope, purpose, application, restriction, definition, duties, statement of duties. This reduces LLM input size (~3–8 sections vs 73).
4. **LLM extraction** — one Ollama call per CA (not per section). Prompt asks for JSON list of `{clause_type, article_ref, clause_text}`. instructor + Pydantic validation with up to 3 retries.
5. **Upsert** — `INSERT OR IGNORE` into `ca_clauses` with `UNIQUE(og_code, clause_type, article_ref, clause_text)`.
6. **Multi-OG duplication** — for combined CAs (IT_CS, CT_FI, LP_LA, SP_AP), insert clauses for each OG code with same data.

CLI args (matching `ingest_noc.py` style):
```
python scripts/ingest_ca.py \
    --db-path app.db \
    --data-dir data \
    --model gemma4:31b \
    --version-label "CA 2023-2026 v1.0"
```

### `scripts/ingest_jes.py`

Stages:
1. **Hash check** — `SHA-256(JES_TXT_bytes)` → `source_documents`. If hash unchanged and `jes_factors` rows exist for this OG: skip.
2. **OG code extraction** — first word of filename = OG code.
3. **LLM extraction** — one Ollama call per JES TXT. Prompt asks for JSON list of `{factor_name, factor_definition, degree_descriptors, point_values, max_points}`. Pydantic validation + 3 retries.
4. **Upsert** — `INSERT OR IGNORE` into `jes_factors` with `UNIQUE(og_code, factor_name)`.

**Note on FB**: Two files (`FB Border Services - Job Evaluation Standard 2005.txt` and `FB Border Services - Application Guidelines 2005.txt`). Ingest only the "Job Evaluation Standard" file; skip Application Guidelines (metadata, not factor data).

CLI args:
```
python scripts/ingest_jes.py \
    --db-path app.db \
    --data-dir data/Job_evaluation \
    --model gemma4:31b \
    --version-label "JES v1.0"
```

### `scripts/ingest_policy.py`

No LLM needed — deterministic text chunking.

Stages:
1. **Hash check** — `SHA-256(TXT_bytes)` → `source_documents`.
2. **Chunk** — split on paragraph boundaries (double newline), with 500-char max per chunk, 50-char overlap.
3. **Upsert** — `INSERT OR IGNORE` into `policy_chunks`.
4. **FTS5 rebuild** — `INSERT INTO policy_fts(policy_fts) VALUES('rebuild')` after all chunks inserted.

CLI args:
```
python scripts/ingest_policy.py \
    --db-path app.db \
    --data-dir data \
    --version-label "TBS Policy v1.0"
```

---

## Standard Stack

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| ollama (Python) | 0.6.1 | LLM calls for clause/factor extraction | Already installed (Phase 2) |
| instructor | latest | Pydantic-validated LLM output + retry | Need to verify installed |
| pydantic | 2.x | Output model validation | Already installed (Phase 1) |
| hashlib | stdlib | SHA-256 content hashing | No install |
| pathlib | stdlib | Path manipulation | No install |
| json | stdlib | Serialize degree_descriptors + point_values | No install |
| sqlite3 | stdlib | SQLite upsert | No install |

Check instructor:
```bash
pip3 show instructor 2>/dev/null || echo "NEEDS INSTALL"
```

---

## TDD Strategy (following Phase 2 pattern)

Wave 0 test stubs before any implementation:

**`tests/test_ca_ingest.py`** stubs:
- `test_ca_ingest_creates_source_document_row` — after ingest, `source_documents` has row for `EC_full.json`
- `test_ca_ingest_creates_clause_rows` — `SELECT COUNT(*) FROM ca_clauses WHERE og_code='EC'` >= 1
- `test_ca_ingest_idempotent` — second run produces identical row count
- `test_ca_ingest_multi_og_ca` — IT_CS ingest creates rows for both `og_code='IT'` and `og_code='CS'`

**`tests/test_jes_ingest.py`** stubs:
- `test_jes_ingest_creates_source_document_row`
- `test_jes_ingest_creates_factor_rows` — `SELECT * FROM jes_factors WHERE og_code='EC' AND factor_name LIKE '%Decision%'` returns 1 row
- `test_jes_ingest_factor_has_degree_descriptors` — `degree_descriptors` is valid JSON list with `degree` and `points` keys
- `test_jes_ingest_idempotent`

**`tests/test_policy_ingest.py`** stubs:
- `test_policy_ingest_creates_chunks`
- `test_policy_fts_query_returns_results` — FTS5 query for 'AS classification EC' returns >= 1 hit
- `test_policy_ingest_idempotent`

---

## Validation Architecture

### Test coverage targets (Nyquist)

| Requirement | Test | Verifiable output |
|-------------|------|-------------------|
| PIPE-02: CA clauses stored per OG | `test_ca_ingest_creates_clause_rows` | `SELECT COUNT(*) FROM ca_clauses WHERE og_code='EC'` >= 1 |
| PIPE-02: queryable by OG code | `test_ca_clause_query_by_og` | Result row has `og_code`, `clause_type`, `clause_text` fields |
| PIPE-03: JES factors stored per OG | `test_jes_ingest_creates_factor_rows` | `SELECT * FROM jes_factors WHERE og_code='EC' AND factor_name LIKE '%Decision%'` = 1 row |
| PIPE-03: queryable by (og_code, factor_name) | `test_jes_factor_query` | Returns correct `max_points` value matching known EC element |
| CA-01: pre-extracted at ingest | `test_ca_ingest_creates_clause_rows` | Rows exist without app running (CLI only) |
| PIPE-04 CA: content hash recorded | `test_ca_ingest_creates_source_document_row` | `source_documents` has `EC_full.json` row with non-empty `content_hash` |
| PIPE-04 JES: content hash recorded | `test_jes_ingest_creates_source_document_row` | `source_documents` has JES file row |
| Idempotency CA | `test_ca_ingest_idempotent` | Row count unchanged after second run |
| Idempotency JES | `test_jes_ingest_idempotent` | Row count unchanged after second run |
| Multi-OG CA split | `test_ca_ingest_multi_og_ca` | Both IT and CS rows present after IT_CS ingest |
| Policy FTS | `test_policy_fts_query_returns_results` | FTS5 match on classification keyword returns rows |

---

## Key Decisions and Rationale

1. **LLM for CA extraction, not regex**: CA sections are inconsistently structured across 28 agreements. EC has 73 individual article sections; PA has 9 rolled-up parts; IT_CS has 23 mixed sections. Regex would require per-CA logic — unmaintainable. One prompt per CA with gemma4:31b is the right call (as specified in PIPE-02).

2. **LLM for JES extraction, not regex**: JES files vary — EC uses inline rating-scale tables, IT uses prose degree descriptions. Regex could handle EC but would fail on IT. Consistent LLM extraction for all 18 files is simpler than two parsers.

3. **Separate scripts (not one combined)**: CA ingest (28 LLM calls, ~5–10 min) and JES ingest (18 LLM calls, ~3–6 min) should be independently re-runnable. A combined script makes partial reruns harder.

4. **instructor for LLM output validation**: Phase 1 locked in `instructor` as mandatory retry wrapper. JES factor extraction requires validated structured output (nested JSON). Using instructor + Pydantic ensures retry on malformed output, consistent with the architecture non-negotiable.

5. **policy_chunks as regular table + contentless FTS5**: Same pattern as `noc_fts` in Phase 2. The policy doc text is immutable (no edits post-ingest), so a contentless FTS5 index is appropriate. FTS5 `MATCH` queries support phrase search (e.g., `'internal departmental guidance'`) needed for CLASS-03.

6. **source_documents rows for CA + JES files**: Phase 2 established `source_documents` for NOC CSVs. Phase 3 extends it to CA JSONs and JES TXTs. No schema change needed — same table, new rows. `version_label` comes from `index_record.signing_date` for CAs, from filename for JES.

7. **No new startup assertion**: Phase 2 added `assert_noc_index_model()` to lifespan. CA/JES tables are query-only (no embedding model dependency) — no analogous startup check is needed for Phase 3.
