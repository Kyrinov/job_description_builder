---
phase: 03-ca-jes-data-pipeline
plan: 03
state: complete
started: 2026-05-29T00:00:00Z
completed: 2026-05-29T00:10:00Z
wave: 2
requirements: [PIPE-02, PIPE-03, CA-01, PIPE-04]
tests:
  automated:
    test_ca_ingest: PASS (6/6)
    test_jes_ingest: PASS (6/6)
    test_policy_ingest: PASS (7/7)
    full_suite: PASS (63 total)
  manual: []
---

# Plan 03-03 — Ingest Scripts (Complete)

## What Was Built

Three standalone ingest scripts that walk source corpora, perform structured extraction (LLM for CA/JES, deterministic chunking for policy), and upsert into the Phase 3 schema tables.

## Key Files Created

| File | Lines | Purpose |
|------|-----|---------|
| scripts/ingest_ca.py | ~300 | 7-stage CA pipeline — section selection, instructor/Pydantic extraction, multi-OG support, hash-check idempotency |
| scripts/ingest_jes.py | ~280 | 7-stage JES pipeline — filename OG extraction, Application Guidelines filter, factor/degree extraction |
| scripts/ingest_policy.py | ~240 | 6-stage policy pipeline — paragraph chunking (500/50), INSERT OR IGNORE chunks, drop+recreate contentless FTS5 |

## Notable Design Decisions

1. **Contentless FTS5 must be dropped+recreated** — SQLite does not allow DELETE from `content=''` FTS5 tables. Fixed in scripts/ingest_policy.py::rebuild_policy_fts() by replacing DELETE with DROP TABLE IF EXISTS + CREATE VIRTUAL TABLE.
2. **No app.config imports** — all three scripts are standalone CLI tools runnable without .env.
3. **Path-traversal guard** — validated before any I/O on all three scripts.
4. **Parameterized SQL only** — zero f-string SQL across all three scripts.

## Verification

- All 19 Phase 3 stub tests pass (6+6+7)
- All 44 Phase 1+2 test pass (full suite: 63 tests, 0 failures)
- Schema integrity verified (13 tables after create_schema)
