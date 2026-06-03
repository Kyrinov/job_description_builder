# Phase 02 Plan 01 Summary: NOC Data Pipeline Wave 0 Test Stubs

**Substantive one-liner:** Pre-written falsifiable test stubs for NOC ingest pipeline and startup model-check assertions — RED phase of TDD with 11 tests before any implementation code exists.

## Plan Metadata

| Field | Value |
|-------|--------|
| Phase | 02-noc-data-pipeline |
| Plan | 01 (Wave 0) |
| Type | execute (TDD RED) |
| Date | 2026-05-28 |
| Status | Complete |

## One-Liner

Pre-written 11 falsifiable test stubs for NOC vector-index ingest pipeline (PIPE-01, PIPE-04, SC-4) and startup model-mismatch assertion (PIPE-05) — RED phase of TDD with pytest collection at 0 SyntaxErrors before any implementation exists.

## Key Decisions

1. **noc_db uses temp-file path, not `:memory:`** — sqlite-vec vec0 virtual tables have known issues with in-memory databases on some builds; temp-file matches production behavior.
2. **Mock embeddings pre-computed `[0.1] * 768`** — no Ollama dependency; stubs test SQL layer (tables, FTS5, vec0) not embedding quality.
3. **test_noc_startup.py uses synchronous tests** — `assert_noc_index_model` is sync; asyncio_mode="auto" is set in pyproject.toml but doesn't apply to sync functions. Pattern matches Phase 1 test_startup.py helper functions.
4. **ImportError expected on collection** — `scripts.ingest_noc` and `app.db.assert_noc_index_model` don't exist yet; tests are stubs, not runnable. SyntaxError would be unacceptable.

## Deviations from Plan

None — plan executed exactly as written.

## Auth Gates

None

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| `scripts.ingest_noc` import | `test_noc_ingest.py` | 197 | Module not implemented yet (Plans 02-03-04) |
| `app.db.assert_noc_index_model` import | `test_noc_startup.py` (x4) | 73, 98, 123, 150 | Function not implemented yet (Plan 02-02) |

All stubs are intentional — this is Wave 0 (RED phase). Tests will produce ImportError until corresponding implementation plans execute.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: import | `tests/test_noc_ingest.py` | Imports `scripts.ingest_noc` which will introduce new network calls to Ollama (mitigated by mock in tests) |
| threat_flag: import | `tests/test_noc_startup.py` | Imports `app.db` which will expose `assert_noc_index_model` (test-safe, no network calls) |

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| noc_db fixture in conftest.py | ✅ Line 57: `def noc_db(tmp_path)` |
| Phase 1 fixtures intact | ✅ `_clean_module_state`(24), `temp_db_path`(30), `valid_env`(36), `mock_healthy_ollama`(42) |
| test_noc_ingest.py has 7 test functions | ✅ All 7 names match VALIDATION.md |
| test_noc_startup.py has 4 test functions | ✅ All 4 names match VALIDATION.md |
| pytest --collect-only: 0 SyntaxErrors | ✅ 11 tests collected, 0 SyntaxErrors |

## Per-Task Summary

### Task 1: Extend tests/conftest.py with noc_db fixture
- **Status:** Complete
- **Commit:** `df3bdb7`
- **Files:** `tests/conftest.py` (+17 lines)
- **Verification:** `grep -n "def noc_db" tests/conftest.py` → line 57

### Task 2: Write test stub files
- **Status:** Complete
- **Commit:** `891f265`
- **Files:** `tests/test_noc_ingest.py` (7 tests, 9217 bytes), `tests/test_noc_startup.py` (4 tests, 4863 bytes)
- **Verification:** `pytest --collect-only` → 11 collected, 0 SyntaxErrors

## Duration

Started: ~2026-05-28T17:47:00Z
Completed: ~2026-05-28T17:48:00Z
