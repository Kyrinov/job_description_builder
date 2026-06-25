---
phase: 22-sjd-library
plan: 03
subsystem: backend
tags: [sjd, model, api, manifest, sjd-01, sjd-02, wd]
provides:
  - DraftDuty.source Literal extended to accept "sjd"
  - DraftDuty.sjd_number field for SJD provenance
  - WorkDescription.sjd_source dict (set by sjd-start)
  - POST /api/wd/{id}/sjd-start mutation endpoint
  - _build_sjd_seed_duties helper
  - _build_v2_manifest SJD provenance entry
requires:
  - 22-01 (RED test stubs)
  - 22-02 (SJD_LIBRARY + GET /api/sjd + SJDEntry dataclass)
affects:
  - frontend 22-04 (sjd-start UI call)
  - export DOCX manifest template (new SJD row possible)
tech-stack:
  added: []
  patterns:
    - Read-modify-write on work_descriptions.data (parameterized SQL)
    - Static constant lookup for SJD entry validation
    - Optional dict fields for provenance metadata
key-files:
  created: []
  modified:
    - v2/backend/app/models/draft_duty.py
    - v2/backend/app/models/work_description.py
    - v2/backend/app/api/wd.py
    - v2/backend/app/services/export_service.py
decisions:
  - "DraftDuty.source Literal extended to {noc,advisor,sjd} (additive — backward compatible with extra='ignore')"
  - "WorkDescription.sjd_source is dict (not nested Pydantic model) — minimal schema, easy to read in DB"
  - "_SJD_DUTY_SUGGESTIONS constant lives in wd.py (3 duties per OG group for AS/FI/EC/IT/EN/PE/WP, default=EC fallback) — duty text sourced from frontend data.jsx for parity"
  - "sjd_start endpoint returns updated WorkDescription (not dict) so SPA can mirror state in one round-trip"
  - "sjd_number validated by lookup against static SJD_LIBRARY; 404 on miss (T-22-01 mitigation)"
  - "Manifest SJD entry uses source_id=sjd_number (per-SJD granularity, not library-wide) so multiple SJD-derived WDs each get their own manifest row"
metrics:
  duration: 5min
  completed_date: "2026-06-11T18:30:00Z"
  tasks: 2
  files_modified: 4
  tests_added: 0
  tests_now_green: 3
  total_tests: 10
  full_suite_tests: 125
---

# Phase 22 Plan 03: SJD Model Extensions + sjd-start Endpoint + Manifest SJD Provenance Summary

Extended the model layer to accept SJD source duties, added the writable `POST /api/wd/{id}/sjd-start` mutation endpoint with seed-duty helper, and wired SJD provenance into the DOCX version manifest. The 3 RED tests in `test_sjd.py` (`test_sjd_start_prefills_wd`, `test_seed_duties_provenance`, `test_manifest_includes_sjd_source`) are now GREEN; all 10 SJD tests pass and the full backend suite remains green at 125/125.

## What Was Built

### Task 1: Model extensions (`3b27a3d`)

**`v2/backend/app/models/draft_duty.py`** — `DraftDuty.source` Literal extended from `{"noc", "advisor"}` to `{"noc", "advisor", "sjd"}`; added `sjd_number: Optional[str] = None` field (e.g. `"DND-PA-57047"`). `ConfigDict(extra="ignore")` makes this fully backward compatible.

**`v2/backend/app/models/work_description.py`** — added `sjd_source: Optional[dict] = None` after `og_level` (stores `{sjd_number, title, og_code, og_level}` after sjd-start).

### Task 2: sjd-start endpoint + manifest (`bbb05f2`)

**`v2/backend/app/api/wd.py`** — added:
- `_SJD_DUTY_SUGGESTIONS` constant (3 polished duties per OG group: AS/FI/EC/IT/EN/PE/WP, plus `default` → EC fallback). Text sourced from frontend `DUTY_SUGGESTIONS` in `data.jsx` for parity.
- `_build_sjd_seed_duties(entry) -> list[DraftDuty]` helper that returns DraftDuty items with `source="sjd"` and `sjd_number` propagated from the SJD entry.
- `SJDStartRequest` Pydantic model (just `sjd_number: str`).
- `POST /api/wd/{wd_id}/sjd-start` endpoint that:
  1. Validates `sjd_number` against static `SJD_LIBRARY` → 404 on miss (T-22-01).
  2. Reads the WD from SQLite (parameterized `WHERE id = ?`, T-22-03).
  3. Sets `confirmed_og={"og_code","og_name"}`, `og_level`, `duties=seed_duties`, `sjd_source={sjd_number,title,og_code,og_level}`.
  4. Updates `last_modified` and persists via the read-modify-write pattern (matches `confirm_subgroup` in `og_classification.py`).

**`v2/backend/app/services/export_service.py`** — added an `if wd.sjd_source:` guard after the qualification block in `_build_v2_manifest` that emits `{source_type: "SJD", source_id: sjd_number, source_version: "DND SJD Library"}` entries. Deduplication via existing `seen` set.

## Verification Results

- `python -m pytest tests/test_sjd.py -v` → **10/10 PASSED** (was 7/9 RED, now 10/10 GREEN)
- `python -m pytest tests/ -q` → **125 passed, 0 regressions**
- `python -c "from app.api.wd import _build_sjd_seed_duties"` → importable
- `python -c "DraftDuty(id='x', text='t', source='sjd', sjd_number='DND-EC-58355')"` → no ValidationError
- Grep checks all match: `sjd-start` route, `_build_sjd_seed_duties` function, `sjd_source` guard, `DND SJD Library` version string

## Deviations from Plan

None. Plan executed exactly as written.

## Threat Mitigations Applied

- **T-22-01 (Tampering — sjd_number):** Validated by lookup against static `SJD_LIBRARY`; unknown → 404 `HTTPException`. No eval, no path construction, no SQL interpolation.
- **T-22-03 (Tampering — wd_id):** Used only as parameterized SQL parameter `WHERE id = ?`; SQLite injection not possible.
- **T-22-04 (DoS — duty list):** Seed duties are fixed-length (3 per OG group from static constant); no user-controlled list size; ≤ 7 OG groups × 3 = 21 max, but the `_SJD_DUTY_SUGGESTIONS` constant has only 7 groups populated, so the actual maximum is exactly 3 duties per call.

## Next Plan Dependencies

- **Plan 22-04 (SJD frontend browse + sjd-start UI call)** — depends on this plan's `POST /api/wd/{id}/sjd-start` endpoint and `sjd_source` field. The `data.jsx` `fetchSjds`/`fetchSjdDetail` helpers from `22-PATTERNS.md` (lines 432–438) can now be implemented.

## Self-Check: PASSED

All claimed files exist, all commits present in `git log`. Test counts verified.

## Commits

- `3b27a3d` — feat(22-03): add SJD source type to DraftDuty and sjd_source to WorkDescription
- `bbb05f2` — feat(22-03): add POST /api/wd/{id}/sjd-start endpoint and SJD manifest entry
