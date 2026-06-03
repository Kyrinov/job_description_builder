---
phase: 1
slug: project-foundation
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-28
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` — Wave 0 creates this |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | DATA-01 | — | N/A | unit | `pytest tests/test_models.py::test_work_description_instantiation -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 0 | DATA-01 | — | N/A | unit | `pytest tests/test_models.py::test_provenance_tag_required -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 0 | DATA-01 | — | N/A | unit | `pytest tests/test_db.py::test_schema_creation -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 0 | DATA-01 | — | N/A | unit | `pytest tests/test_db.py::test_sqlite_vec_loads -x` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 0 | DATA-02 | T-path-traversal | `db_path` validated under project dir | unit | `pytest tests/test_config.py::test_missing_required_var_raises -x` | ❌ W0 | ⬜ pending |
| 1-01-06 | 01 | 0 | DATA-02 | — | N/A | unit | `pytest tests/test_config.py::test_missing_var_error_names_field -x` | ❌ W0 | ⬜ pending |
| 1-01-07 | 01 | 1 | DATA-03 | — | N/A | smoke | `pytest tests/test_health.py::test_health_endpoint_200 -x` | ❌ W0 | ⬜ pending |
| 1-01-08 | 01 | 1 | DATA-03 | — | N/A | integration | `pytest tests/test_startup.py::test_startup_fails_ollama_unreachable -x` | ❌ W0 | ⬜ pending |
| 1-01-09 | 01 | 1 | DATA-03 | — | N/A | integration | `pytest tests/test_startup.py::test_startup_fails_missing_model -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures: test FastAPI app, temp SQLite DB path, mock Ollama client
- [ ] `tests/test_models.py` — WorkDescription + ProvenanceTag unit test stubs
- [ ] `tests/test_config.py` — env validation tests (uses `monkeypatch.delenv`)
- [ ] `tests/test_db.py` — schema creation and sqlite-vec load test stubs
- [ ] `tests/test_health.py` — health endpoint smoke test stub
- [ ] `tests/test_startup.py` — lifespan startup failure test stubs (mock Ollama)
- [ ] `pyproject.toml` — pytest config, testpaths, asyncio mode for FastAPI lifespan tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `uvicorn app.main:app` starts without error | DATA-03 | Requires live Ollama service | Run `uvicorn app.main:app` and observe no startup error; `curl localhost:8000/health` returns 200 |
| Startup fails loudly when Ollama model absent | DATA-03 | Requires actual Ollama manipulation | Run `ollama rm nomic-embed-text:latest`, start app, confirm RuntimeError in logs; restore model |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-28
