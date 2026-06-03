---
phase: 02-noc-data-pipeline
plan: 03
summary_date: "2026-05-28"
summary_author: executor
---

## Plan 02-03 Complete: NOC Ingest Script

### Overview

Created `scripts/ingest_noc.py` — a standalone 5-stage NOC data pipeline ingest script.

### What was built

- **Stage 0**: `compute_file_hash()` — SHA-256 content hashing for provenance
- **Stage 1**: `parse_structure_csv()` + `parse_elements_csv()` — BOM-aware CSV parsing
- **Stage 2**: `upsert_source_document()`, `upsert_noc_units()`, `upsert_noc_elements()` — relational upsert with source_hash tracking
- **Stage 3**: `rebuild_fts5()` — contentless FTS5 rebuild
- **Stage 4**: `embed_and_upsert_vec0()` — duty statement embedding with batch ollama support
- **Stage 5**: `write_index_metadata()` — model name persistence

### Files modified/created

| File | Action |
|------|--------|
| `scripts/ingest_noc.py` | Created (477 lines) |

### Key decisions

- CLI-only entry point with `--db-path`, `--embed-model`, `--data-dir`, `--version-label` args
- No `app.config` import to avoid pydantic-settings at import time
- `validate_db_path()` guards against path traversal (T-2-01)
- `is_duty_header()` filters duty header noise before embedding (Pitfall 5)
- All SQL uses parameterized queries (T-2-02 mitigation)

### Test results

- `pytest tests/test_noc_ingest.py` — 7/7 passed
- `pytest tests/` — full suite passes (pending Plan 02-04)

### Deviations from plan

None.
