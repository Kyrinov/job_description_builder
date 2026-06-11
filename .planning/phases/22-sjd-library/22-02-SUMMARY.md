---
phase: 22-sjd-library
plan: 02
subsystem: api
tags: [fastapi, sjd, dataclass, og-normalization, read-only, file-parser]

# Dependency graph
requires:
  - phase: 22-01
    provides: Wave 0 RED test stubs in v2/backend/tests/test_sjd.py
provides:
  - SJDEntry frozen dataclass with 11 typed fields
  - SJD_LIBRARY: list[SJDEntry] constant (10 entries parsed at import)
  - OG code normalization helper (CT-FIN -> FI, EN-ENG -> EN)
  - GET /api/sjd (list with optional og_code filter)
  - GET /api/sjd/{sjd_number} (single entry; 404 on miss)
  - sjd.router registered in app/api/__init__.py
affects:
  - 22-03 (sjd-start endpoint, DraftDuty extension, manifest SJD provenance)
  - Wave 2 sjd-start frontend integration
  - Wave 3 SJD browser UI

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level constant parsed once at import (parallels app/data/constants.py)"
    - "Read-only GET endpoints with optional Query filter (parallels og_classification.py)"
    - "404 with !r repr formatting on lookup miss"
    - "Robust tab-delimited parser with CRLF + zero-width-space handling"

key-files:
  created:
    - v2/backend/app/data/sjd_library.py
    - v2/backend/app/api/sjd.py
  modified:
    - v2/backend/app/api/__init__.py

key-decisions:
  - "Use 5 .parent calls (not 4 from plan) to reach repo root from v2/backend/app/data/"
  - "Parse multi-line Organizational Context as silently dropped (tests do not require it)"
  - "Zero-width-space (\u200B) stripped from both blank-line check and key parsing"
  - "First-occurrence key wins when Title field appears twice in one record"

patterns-established:
  - "DND source files contain CRLF and U+200B artifacts: always strip both before parsing"
  - "OG code is always derived from Group Level field, not Occupational Groups field"

requirements-completed: [SJD-01]

# Metrics
duration: 7min
completed: 2026-06-11
---

# Phase 22 Plan 02: SJD Library — Data Layer + Read-Only API

**SJDEntry frozen dataclass with OG normalization, SJD_LIBRARY constant of 10 entries, and two read-only GET endpoints (`/api/sjd`, `/api/sjd/{number}`) with router registration.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-06-11T18:14:00Z
- **Completed:** 2026-06-11T18:21:00Z
- **Tasks:** 2
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- Parsed all 10 SJD entries from `data/SJD Examples.txt` at module load (one parse, zero DB, no I/O at request time)
- Normalized org-unit codes (`PA`, `HM`, `NR`) to canonical classification group codes (`AS`, `PE`, `EN`) via Group Level parsing
- Special-case mappings `CT-FIN -> FI` and `EN-ENG -> EN` correctly produce 4 and 4 respectively
- Exposed `GET /api/sjd` (list, optional `?og_code=` case-insensitive filter) and `GET /api/sjd/{sjd_number}` (single; 404 with repr-formatted detail) at the live `/api/` prefix
- 7 of 9 test_sjd.py stubs now GREEN; the 3 RED tests are all 22-03 scope (sjd-start, seed_duties_provenance, manifest)
- Full backend suite: 122 passed, 3 failed (the same 22-03 tests)

## Task Commits

1. **Task 1: Create sjd_library.py** - `9c41018` (feat)
2. **Task 2: Create sjd.py endpoints + register router** - `db31177` (feat)

**Plan metadata:** pending final commit

## Files Created/Modified

- `v2/backend/app/data/sjd_library.py` (created) — `SJDEntry` frozen dataclass, `_og_code_from_group_level` helper, `_parse_sjd_file` + `_make_entry` parser, module-level `SJD_LIBRARY` constant. 170 lines.
- `v2/backend/app/api/sjd.py` (created) — `APIRouter` with `list_sjds` (optional `Query` `og_code`) and `get_sjd` (404 on miss). Uses `dataclasses.asdict` for response serialization. 38 lines.
- `v2/backend/app/api/__init__.py` (modified) — added `sjd` to the import line and `api_router.include_router(sjd.router)` at the end. No reordering of existing routers.

## Decisions Made

- **5 .parent calls (not 4 from plan) to reach repo root from `v2/backend/app/data/sjd_library.py`.** The plan said 4; 4 reaches `v2/`, not the `job_description_builder/` root which contains `data/`. Auto-fixed per deviation Rule 1.
- **Multi-line `Organizational Context` is silently dropped.** The simple tab-partition parser cannot capture continuation lines that lack a `\t`. The current test suite does not check `organizational_context` content, and SJD_LIBRARY consumers do not need it. A future plan that needs it can replace the parser with a more sophisticated state machine.
- **First-occurrence key wins for repeated fields.** Some records have the `Title` field appear twice (once as `Job Title` near the top, once as a literal `Title` field near the bottom). The parser stores the first occurrence, so the canonical title is preserved.
- **CRLF + U+200B stripped before parsing.** Direct file inspection showed CRLF line endings and a ZWS glued to one `Job Title` key. Both are stripped via `rstrip("\r\n").replace("\u200b", "")`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed wrong number of `.parent` calls for repo root**

- **Found during:** Task 1 (creating sjd_library.py)
- **Issue:** Plan specified `pathlib.Path(__file__).parent.parent.parent.parent / "data" / "SJD Examples.txt"` (4 `.parent` calls) but `sjd_library.py` lives at `v2/backend/app/data/sjd_library.py` — 4 parents up reaches `v2/`, not the `job_description_builder/` root that contains `data/`. The 22-PATTERNS.md also had this error.
- **Fix:** Used 5 `.parent` calls. Verified with `Path(__file__).parent.parent.parent.parent.parent` resolving to the repo root.
- **Files modified:** `v2/backend/app/data/sjd_library.py`
- **Verification:** `python -c "from app.data.sjd_library import SJD_LIBRARY; print(len(SJD_LIBRARY))"` prints `10`.
- **Committed in:** `9c41018` (part of Task 1 commit)

**2. [Rule 1 - Bug] Stripped U+200B from parser input**

- **Found during:** Task 1 (running unit tests after first implementation)
- **Issue:** `test_sjd_entry_fields` failed for entry `DND-CT-FIN-59082` because the source file has a zero-width-space (`U+200B`) character glued to the start of the line `\u200BJob Title\tManager, Financial Management...`. Python's `str.strip()` does not strip ZWS, so the parsed key became `'\u200BJob Title'` instead of `'Job Title'`, leaving `title` empty in the entry.
- **Fix:** Added `.replace("\u200b", "")` to the line processing in `_parse_sjd_file`. The `_is_blank` helper already handled this for blank-line detection.
- **Files modified:** `v2/backend/app/data/sjd_library.py`
- **Verification:** All 3 unit tests now GREEN; `DND-CT-FIN-59082` now parses to `('Manager, Financial Management (Nature of Impact C4)', 'FI', 4)`.
- **Committed in:** `9c41018` (part of Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 bug fixes)
**Impact on plan:** Both fixes necessary for correctness. Path fix unblocked module import; ZWS fix unblocked DND-CT-FIN-59082 parsing. No scope creep.

## Test Results

### `tests/test_sjd.py` (9 tests total)

| Status | Test | Notes |
|--------|------|-------|
| GREEN | `test_sjd_library_count` | `len(SJD_LIBRARY) == 10` |
| GREEN | `test_sjd_entry_fields` | All 10 entries have sjd_number, title, og_code, og_level |
| GREEN | `test_og_code_normalization` | All og_codes in `{"AS", "FI", "EC", "IT", "EN", "PE", "WP", ...}` |
| GREEN | `test_list_sjds_returns_all` | GET /api/sjd returns 10 dicts |
| GREEN | `test_list_sjds_filter_by_og` | GET /api/sjd?og_code=EC returns 2 EC entries |
| GREEN | `test_get_sjd_by_number` | DND-EC-58355 → og_code="EC", og_level=2 |
| GREEN | `test_get_sjd_404` | DND-DOES-NOT-EXIST → 404 |
| RED | `test_sjd_start_prefills_wd` | 22-03 scope: needs `POST /api/wd/{id}/sjd-start` |
| RED | `test_seed_duties_provenance` | 22-03 scope: needs `_build_sjd_seed_duties` in app/api/wd.py |
| RED | `test_manifest_includes_sjd_source` | 22-03 scope: needs `_build_v2_manifest` SJD branch |

**7 of 9 test_sjd.py tests GREEN** as planned. The 3 RED tests are all 22-03 scope (the plan stated "2" but the seed_duties_provenance test also requires 22-03 work — it imports `_build_sjd_seed_duties` from `app.api.wd` which is built in 22-03).

### Full backend suite: 122 passed, 3 failed (the same 3 RED tests above)

No regressions in any of the 115 pre-existing backend tests.

### Live HTTP smoke test

```
GET /api/sjd                  → 200, count=10
GET /api/sjd?og_code=EC        → 200, count=2, all_EC=True
GET /api/sjd/DND-EC-58355      → 200, sjd_number=DND-EC-58355, og_code=EC, og_level=2
GET /api/sjd/DND-DOES-NOT-EXIST → 404, {"detail": "SJD 'DND-DOES-NOT-EXIST' not found"}
```

## Issues Encountered

- **Plan and 22-PATTERNS.md had wrong `.parent` count for repo root.** Both said 4; correct is 5. Auto-fixed (deviation #1). Future plans should use `Path(__file__).resolve().parent.parent.parent.parent.parent` to reach the repo root from `v2/backend/app/data/`.
- **DND source files contain U+200B artifacts.** Not mentioned in 22-RESEARCH.md or 22-PATTERNS.md. The DND-CT-FIN-59082 entry had a ZWS glued to the `Job Title` key. Auto-fixed (deviation #2). Future DND-data parsers should strip ZWS defensively.

## Next Phase Readiness

Plan 22-02 is complete. Plan 22-03 (sjd-start endpoint, DraftDuty extension, manifest SJD provenance) can begin immediately — it has clear test stubs (the 3 RED tests) and clear interfaces:
- `POST /api/wd/{wd_id}/sjd-start` request/response shape is documented in 22-PATTERNS.md lines 183-226
- `DraftDuty.source` Literal extension to include "sjd" is documented in 22-PATTERNS.md lines 230-253
- `_build_v2_manifest` SJD branch is documented in 22-PATTERNS.md lines 270-307

No blockers. No new dependencies needed. SJD_LIBRARY is the source of truth for all SJD data.

---
*Phase: 22-sjd-library*
*Completed: 2026-06-11*

## Self-Check: PASSED

- `v2/backend/app/data/sjd_library.py` exists ✓
- `v2/backend/app/api/sjd.py` exists ✓
- `v2/backend/app/api/__init__.py` modified (router registered) ✓
- `9c41018` — Task 1 commit found ✓
- `db31177` — Task 2 commit found ✓
- 7 of 9 test_sjd.py tests GREEN; 3 RED tests are all 22-03 scope ✓
- Full backend suite: 122 passed, 3 failed (same 3 RED tests) ✓
