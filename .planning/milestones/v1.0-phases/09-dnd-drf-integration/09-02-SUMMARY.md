---
phase: 09-dnd-drf-integration
plan: 02
subsystem: drf-service
tags: [tdd, async, sqlite, keyword-matching, drf]

# Dependency graph
requires:
  - "09-01 (DRF_SCHEMA_DDL + drf_rows table + WorkDescription.is_dnd_position + drf_linkages fields)"
  - "scripts/ingest_drf.py (Task 1, same plan — populates drf_rows)"
provides:
  - "app/services/drf_service.py with get_drf_candidates + confirm_drf_linkages (keyword overlap, no LLM)"
  - "STOPWORDS frozenset + _tokenize helper for re.findall(r'[a-z]+', text) matching"
  - "6 active tests in tests/test_drf.py (TestGetDRFCandidates + TestConfirmDRFLinkages) replacing the 1 skipping TestDRFMatchingService stub"
affects: [09-03, 09-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "asyncio.to_thread for all DB calls (10 sites) — mirrors jd_service.py / jes_service.py"
    - "Late-binding closure capture via default-arg (lambda rid=row_id: ...) inside per-row loops"
    - "TDD: failing tests committed first (RED), then implementation (GREEN) — git log shows the gate"
    - "Token overlap with stopword filtering — no FTS5, no embeddings, no LLM"

key-files:
  created:
    - app/services/drf_service.py
  modified:
    - tests/test_drf.py

key-decisions:
  - "Keyword matching via re.findall(r'[a-z]+', text) — alphabetic-only tokens, no digits, no punctuation; matches all other tokenization in the codebase (jd_service, og_classifier)"
  - "STOPWORDS frozenset of 32 high-frequency English words — reduces noise so overlap reflects domain vocabulary (operations, procurement, capabilities) not grammar (of, the, and)"
  - "Idempotent re-confirm: confirm_drf_linkages REPLACES wd.drf_linkages rather than appending; calling confirm with the same row_ids twice produces the same state"
  - "Unknown row_ids are silently skipped with a logger.warning (T-09-06 threat mitigation) — never raises; the form POST may contain stale ids from a previous session"
  - "Stage is NOT advanced by either function — DRF linkage is an annotation on the existing stage, not a workflow transition (per plan's <action> notes)"
  - "provenance_source_id format: 'DRF/' + str(drf_rows.id) — consistent with the codebase's {source_type}/{source_id} pattern (e.g., 'EC/Decision making')"

requirements-completed: [DRF-01]

# Metrics
duration: 15min
completed: 2026-06-03
---

# Phase 9 Plan 02: DND DRF Service Layer Summary

**DRF CSV → drf_rows ingest pipeline (scripts/ingest_drf.py) + keyword-based candidate matching + confirmation service (app/services/drf_service.py) — all 4 Task-2 service behaviors now pass, no regressions**

## Performance

- **Duration:** 15 min
- **Started:** 2026-06-03T12:30:00Z
- **Completed:** 2026-06-03T12:45:00Z
- **Tasks:** 1 (TDD = RED + GREEN) — Task 1 (ingest script) was pre-committed as `d5c4fea`
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- `scripts/ingest_drf.py` (Task 1, pre-committed): reads `data/departmental_results_framework/dnd_drf_dataset.csv` with UTF-8-sig BOM guard + cp1252 fallback, INSERT OR IGNORE into `drf_rows`, idempotent across re-runs. End-to-end run on `app.db` produced 42 unique rows out of 132 CSV rows (90 duplicates skipped).
- `app/services/drf_service.py` (Task 2, this run): 241 lines, public API `get_drf_candidates(wd_id, db_path)` + `confirm_drf_linkages(wd_id, row_ids, db_path)`. Token-overlap algorithm (no LLM, no embeddings) with 32-word STOPWORDS filter. All DB calls go through `asyncio.to_thread` (10 sites).
- `tests/test_drf.py` extended: `TestDRFMatchingService` (1 wrong-name stub) replaced with two proper test classes — `TestGetDRFCandidates` (4 tests) + `TestConfirmDRFLinkages` (2 tests). All 6 active tests pass.
- End-to-end smoke test against real data (42 drf_rows): a DND position with duties mentioning "operations, procurement of capabilities, and protect cyber infrastructure" returns 34 candidates; top matches are scored by token overlap count; `confirm_drf_linkages` persists 2 linkages with `provenance_source_id='DRF/12'` and `DRF/14'`.

## Task Commits

Each task was committed atomically (TDD gate visible in git log):

1. **Task 1 (already done at session start):** `d5c4fea` feat(09-02) — `scripts/ingest_drf.py` CSV → drf_rows ingest pipeline
2. **Task 2 TDD RED:** `0d0b5c1` test(09-02) — failing tests for `get_drf_candidates` + `confirm_drf_linkages` (ModuleNotFoundError confirmed)
3. **Task 2 TDD GREEN:** `213735d` feat(09-02) — `app/services/drf_service.py` implementation; 4/4 new tests now pass

## Files Created/Modified

- `app/services/drf_service.py` (new, 241 lines) — Public API: `get_drf_candidates`, `confirm_drf_linkages`. Private helpers: `_tokenize`, `_collect_duty_text`, `_score_drf_rows`, `STOPWORDS` constant.
- `tests/test_drf.py` (modified) — Replaced `TestDRFMatchingService` stub (wrong function name `find_drf_candidates`) with `TestGetDRFCandidates` (4 tests) and `TestConfirmDRFLinkages` (2 tests). New helpers: `_make_dnd_wd(db_path, *, is_dnd, duty_texts, advisor_duty_texts, stage)`, `_seed_drf_rows(db_path, rows)`.

## Decisions Made

- **Keyword matching, not LLM/embeddings.** The DRF dataset is small (~42 unique rows post-dedup), duties are short, and the matching needs to be deterministic + free of model inference latency. Token overlap with stopword filtering is sufficient for the candidate set; advisor review (plan 09-04) is the final selection step.
- **`re.findall(r'[a-z]+', text)` tokenization.** Alphabetic-only (no digits, no punctuation) — consistent with how `jd_service.py` and `og_classifier.py` tokenize. Lowercased before tokenization so case-insensitive matching falls out for free.
- **`asyncio.to_thread` everywhere, including the connection close.** The pattern in `jes_service.py:163, 270` and `jd_service.py:89, 205` is `get_connection` opens with `asyncio.to_thread` and `conn.close` closes with `asyncio.to_thread` in `finally`. Both `get_drf_candidates` and `confirm_drf_linkages` follow this pattern (10 `asyncio.to_thread` calls total across the file).
- **Default-arg closure capture for per-row loops.** The `for row_id in row_ids` loop in `confirm_drf_linkages` does `lambda rid=row_id: ...` to avoid Python's late-binding closure trap. Without it, every SELECT would use the loop's final `row_id` value.
- **Re-confirm is idempotent (replaces, not appends).** Calling `confirm_drf_linkages` with the same `row_ids` twice produces the same `wd.drf_linkages` state — the plan's <action> section specifies "Replaces any existing drf_linkages (idempotent re-confirm)". Advisor workflows that re-submit (e.g., after editing) don't accumulate stale linkages.
- **provenance_source_id format `DRF/{id}`.** The DRF source_type is one of the enum values on `ProvenanceTag` (line 29 of `app/models/work_description.py`); `DRF/{row_id}` follows the codebase's `{source_type}/{source_id}` convention seen in `ProvenanceTag` for JES factors (`"EC/Decision making"`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test stub had wrong function name (`find_drf_candidates` instead of `get_drf_candidates`)**

- **Found during:** Task 2 RED — reading `tests/test_drf.py` to add new tests
- **Issue:** `TestDRFMatchingService.test_drf_matching_uses_duty_text_keywords` referenced `from app.services.drf_service import find_drf_candidates` — this function name does not exist in the plan. The plan's <action> section clearly names the function `get_drf_candidates`.
- **Fix:** Removed the entire `TestDRFMatchingService` class (1 test) and replaced it with two new test classes (`TestGetDRFCandidates` + `TestConfirmDRFLinkages`) that use the correct function names from the plan. Net: -1 skipping test, +6 active tests, +5 net coverage.
- **Files modified:** `tests/test_drf.py`
- **Commit:** `0d0b5c1` (TDD RED)

No other deviations — plan executed as written for the service implementation. All 4 plan behavior specs (returns empty for non-DND, raises for missing WD, finds overlapping rows, candidate dict has required keys + saves linkages + raises for missing WD on confirm) are covered by the 6 active tests.

## Issues Encountered

None.

## TDD Gate Compliance

Verified in git log:

- `0d0b5c1` (test) — RED gate: 4 tests fail with `ModuleNotFoundError: No module named 'app.services.drf_service'`
- `213735d` (feat) — GREEN gate: all 4 new tests now pass; 0 regressions
- No REFACTOR commit needed (implementation is straightforward; helpers extracted for testability but no duplication to clean up)

## Threat Model Compliance

- **T-09-04 (CSV path tampering):** Ingest script takes the CSV path as a CLI arg; no web runtime path. Mitigated by design.
- **T-09-05 (wd_id spoofing → info disclosure):** `get_drf_candidates` raises `ValueError("not found")` for missing WD. Confirmed by `test_raises_for_missing_wd`. The route handler (plan 09-03) maps this to 404 with no stack trace leak.
- **T-09-06 (row_id tampering):** `confirm_drf_linkages` does a SELECT-by-PK for each row_id; unknown ids are skipped with `logger.warning` rather than inserted as garbage. Mitigated by design.

## User Setup Required

None — no external service configuration required. Running the ingest script is one CLI command (per the plan's verification step):

```bash
python scripts/ingest_drf.py app.db    # populates drf_rows
```

## Next Phase Readiness

- **09-03 (API router + export_service extension)** is unblocked: `get_drf_candidates` and `confirm_drf_linkages` are importable, both have the exact async signatures the router will wrap. The candidate dict shape (id, core_responsibility, departmental_result, fiscal_year, score) and linkage dict shape (core_responsibility, departmental_result, fiscal_year, row_index, confirmed, provenance_source_id) are stable contracts.
- **09-04 (wizard step + DOCX section)** is unblocked: `wd.drf_linkages` now has a concrete shape for the export service to render; the `provenance_source_id` format `DRF/{id}` is what the export template will cite.

Full suite: 186 passed (was 180, +6), 9 skipped (was 10, -1 — removed `TestDRFMatchingService` stub), 0 regressions.

---
*Phase: 09-dnd-drf-integration*
*Completed: 2026-06-03*

## Self-Check: PASSED

- `.planning/phases/09-dnd-drf-integration/09-02-SUMMARY.md` exists
- `d5c4fea` (Task 1 ingest script) — pre-existing commit
- `0d0b5c1` (test) — RED gate commit exists
- `213735d` (feat) — GREEN gate commit exists
- `app/services/drf_service.py` exists with `async def get_drf_candidates` and `async def confirm_drf_linkages`
- `STOPWORDS` constant present in service file
- `asyncio.to_thread` count: 10 (acceptance criterion: ≥ 2)
- `python -c "from app.services.drf_service import get_drf_candidates, confirm_drf_linkages"` exits 0
- Full suite: 186 passed, 9 skipped, 0 regressions
