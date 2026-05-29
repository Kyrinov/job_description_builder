---
phase: 03-ca-jes-data-pipeline
plan: 01
subsystem: testing
tags: [pytest, tdd, red-phase, sqlite, ingest, CA, JES, policy]

# Dependency graph
requires:
  - phase: 02-noc-data-pipeline
    provides: app.db.get_connection, app.db.create_schema, NOC schema DDL
provides:
  - PIPE-02 stub tests (CA clauses CRUD & query)
  - PIPE-03 stub tests (JES factors CRUD & query)
  - PIPE-04 stub tests (source_documents, source_hash provenance)
  - CA-01 stub tests (clause extraction targets)
  - CLASS-03 prereq tests (policy chunking + FTS5 indexing)
affects: [03-02-schema-ddl, 03-03-ingest-scripts, 03-04-real-data-run]

# Tech tracking
tech-stack:
  added: []
  patterns: [RED-phase TDD, lazy import for stub collection, synthetic data injection, INSERT OR IGNORE idempotency, tmp_path fixture isolation]

key-files:
  created:
    - tests/test_ca_ingest.py
    - tests/test_jes_ingest.py
    - tests/test_policy_ingest.py
  modified:
    - tests/conftest.py

key-decisions:
  - "Lazy imports in helpers (not module-level) to keep pytest collection passing despite missing scripts"
  - "Synthetic clause/factor data injected directly — no Ollama, no mock_healthy_ollama needed"
  - "ca_jes_db fixture uses temp-file (not :memory:) for sqlite-vec vec0 compatibility"
  - "Separate db_path (test_ca_jes.db) from noc_db (test_noc.db) to prevent cross-test state leakage"

patterns-established:
  - "Red-phase stubs: functions exist at import time as targets; assertions verified after implementation"
  - "Idempotency via INSERT OR IGNORE with UNIQUE constraints"
  - "Content hash provenance (PIPE-04): 64-char SHA-256 hex on every source row and derived rows"
  - "Multi-OG support pattern: same function call with multiple og_codes produces one row set per OG"

requirements-completed: [PIPE-02, PIPE-03, CA-01]

# Metrics
duration: 3min
completed: 2026-05-29
---

# Phase 3 Plan 01 Summary

**Wave 0 RED-phase test stubs: 19 pytest tests across CA, JES, and Policy ingest modules — all collecting with 0 SyntaxErrors, all failing at runtime with ImportError until implementation scripts exist**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-29
- **Completed:** 2026-05-29
- **Tasks:** 2/2
- **Files modified:** 4 (3 created, 1 modified)

## Accomplishments
- Created `ca_jes_db` pytest fixture for isolated temp-file SQLite testing with full schema
- Wrote 6 test stubs for CA ingest covering PIPE-02, CA-01, PIPE-04
- Wrote 6 test stubs for JES ingest covering PIPE-03, PIPE-04
- Wrote 7 test stubs for Policy ingest covering chunking, FTS5 indexing, and PIPE-04
- All 19 tests collected via `pytest --collect-only` with 0 SyntaxErrors
- Imports from `scripts.ingest_*` deferred to helper functions (lazy import) so collection passes; runtime ImportError is expected RED state

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend conftest.py with ca_jes_db fixture** - `b061c9b` (feat)
2. **Task 2: Write three test stub files** - `d288aaf` (feat)

**Plan metadata:** execution complete

## Files Created/Modified
- `tests/conftest.py` — appended `ca_jes_db` fixture after `noc_db`, all prior fixtures intact
- `tests/test_ca_ingest.py` — 6 PIPE-02/CA-01/PIPE-04 stub tests with synthetic CA clause data
- `tests/test_jes_ingest.py` — 6 PIPE-03/PIPE-04 stub tests with synthetic JES factor data
- `tests/test_policy_ingest.py` — 7 CLASS-03 prereq stub tests (chunking + FTS5 + provenance)

## Decisions Made
- Lazy imports in `_run_*` helpers (not module-level) keeps pytest collection passing; ImportError surfaces at runtime (expected RED)
- Synthetic data injected directly into `_run_*` helpers — no Ollama mock needed, no `mock_healthy_ollama` fixture dependency
- Temp-file db_path (`test_ca_jes.db`) not in-memory for sqlite-vec vec0 compatibility
- Separate db_path from `noc_db` fixture to prevent cross-test state leakage

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all files compiled cleanly, 0 SyntaxErrors at collection. ImportError on `scripts.ingest_ca`, `scripts.ingest_jes`, `scripts.ingest_policy` is expected RED state.

## Next Phase Readiness
- Plan 03-02 (Wave 1: CA_JES_SCHEMA_DDL DDL extension) can proceed — fixture foundation ready
- Plan 03-03 (Wave 2: ingest scripts with LLM extraction) can proceed — 19 validated test targets exist
- All test stubs keyed to PIPE-02, PIPE-03, CA-01, PIPE-04, and CLASS-03 requirements

---
*Phase: 03-ca-jes-data-pipeline*
*Completed: 2026-05-29*
