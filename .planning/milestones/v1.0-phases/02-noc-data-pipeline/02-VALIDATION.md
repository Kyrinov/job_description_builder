---
phase: 2
slug: noc-data-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-28
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/test_noc_ingest.py tests/test_noc_startup.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds (all mocked; no Ollama needed) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_noc_ingest.py tests/test_noc_startup.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 0 | PIPE-01 | — | N/A | unit | `pytest tests/test_noc_ingest.py::test_relational_tables_populated -x` | ❌ Wave 0 | ⬜ pending |
| 2-01-02 | 01 | 0 | PIPE-04 | — | N/A | unit | `pytest tests/test_noc_ingest.py::test_source_documents_hash_and_label -x` | ❌ Wave 0 | ⬜ pending |
| 2-01-03 | 01 | 0 | PIPE-04 | — | N/A | unit | `pytest tests/test_noc_ingest.py::test_derived_records_store_source_hash -x` | ❌ Wave 0 | ⬜ pending |
| 2-01-04 | 01 | 0 | PIPE-04 | — | N/A | unit | `pytest tests/test_noc_ingest.py::test_elements_store_source_hash -x` | ❌ Wave 0 | ⬜ pending |
| 2-01-05 | 01 | 1 | PIPE-01 | T-2-01 | Path injection via --db-path: `Path(db_path).resolve()` with project root guard | integration | `pytest tests/test_noc_ingest.py::test_fts5_query_returns_results -x` | ❌ Wave 0 | ⬜ pending |
| 2-01-06 | 01 | 1 | PIPE-01 | — | N/A | integration | `pytest tests/test_noc_ingest.py::test_vec0_knn_returns_results -x` | ❌ Wave 0 | ⬜ pending |
| 2-01-07 | 01 | 1 | PIPE-01 | — | N/A | integration | `pytest tests/test_noc_ingest.py::test_ingest_idempotent -x` | ❌ Wave 0 | ⬜ pending |
| 2-02-01 | 02 | 1 | PIPE-05 | — | N/A | unit | `pytest tests/test_noc_startup.py::test_model_mismatch_raises_runtime_error -x` | ❌ Wave 0 | ⬜ pending |
| 2-02-02 | 02 | 1 | PIPE-05 | — | N/A | unit | `pytest tests/test_noc_startup.py::test_missing_index_metadata_no_error -x` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_noc_ingest.py` — stubs for PIPE-01, PIPE-04, SC-4 (idempotency)
- [ ] `tests/test_noc_startup.py` — stubs for PIPE-05 (model mismatch assertion)
- [ ] `tests/conftest.py` — add `noc_db` fixture: in-memory SQLite with NOC schema + sqlite_vec loaded

*All test files are new; none exist yet. Use pre-computed mock embeddings (`[0.1] * 768`) — tests must NOT require Ollama to be running.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `python scripts/ingest_noc.py` runs to completion on real data | PIPE-01 | Requires Ollama running + ~5–11 min ingest | Run `python scripts/ingest_noc.py --db-path app.db --embed-model nomic-embed-text`; verify exit 0 and non-zero row counts in `noc_units`, `noc_elements`, `noc_fts`, `noc_chunks_vec` |
| FTS5 query against real data | PIPE-01 | Requires real ingest to have run | `sqlite3 app.db "SELECT noc_code, title FROM noc_fts WHERE noc_fts MATCH 'software developer' LIMIT 5"` returns rows |
| vec0 KNN against real data | PIPE-01 | Requires Ollama + real ingest | Run Phase 4 query against populated DB |
| Re-run ingest on unchanged files | PIPE-04 | Requires real DB state | Run ingest twice; row counts and hashes identical on second run |
| App startup fails on model mismatch | PIPE-05 | Requires running app | Set `OLLAMA_EMBED_MODEL=wrong-model` in .env; start app; verify startup error names the mismatch |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
