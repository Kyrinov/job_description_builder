---
phase: 18-jd-composition-live-preview
plan: 02
type: execute
wave: 1
autonomous: true
files_modified:
  - v2/backend/app/models/draft_duty.py
  - v2/backend/app/api/noc_mapping.py
  - v2/backend/app/api/wd.py
  - v2/backend/tests/test_jd_composition.py
  - v2/backend/tests/conftest.py
---

# Plan 18-02 — Backend implementation (Wave 1)

## What was built

- **`DraftDuty` model** (`v2/backend/app/models/draft_duty.py`): source Literal updated from `["suggested", "advisor"]` to `["noc", "advisor"]`; appended provenance fields (`provenance_noc_code`, `provenance_section: "Main duties"`, `provenance_hash`), `advisor: bool = False`, and orphan check fields (`orphan: bool = False`, `orphan_rationale: Optional[str]`). Pydantic `extra="ignore"` ensures old records with `source="suggested"` still load without error.
- **`GET /api/noc/{noc_code}/duties`** (`v2/backend/app/api/noc_mapping.py`): reads verbatim "Main duties" rows from `noc_elements` via `get_noc_connection()` (NOT `get_connection()`); returns `{noc_code, duties: [{id, text, source_hash}]}`; 404 when no rows; min-length 3 validation on noc_code.
- **`WDPatchRequest.duties`** (`v2/backend/app/api/wd.py`): new `duties: Optional[list[dict]] = None` field; `patch_wd` handler validates each entry against `DraftDuty` and caps at 20 (DoS mitigation).
- **`POST /api/wd/{wd_id}/orphan_check`** (`v2/backend/app/api/wd.py`): deterministic keyword match against `OG_DEFINITIONS[og_code].exclusions`; no LLM (per v2.0 policy); 404 on missing WD, 422 when OG not confirmed; EC always returns `flagged: []` (no exclusions defined).
- **`_duty_contradicts_og()` helper** (`v2/backend/app/api/wd.py`): module-level keyword matcher; extracts phrases >4 chars from `exclusions_text` (split on `,` or `;`).
- **Test file**: replaced 6 RED stubs with real test implementations.

## Threat model coverage

- T-18-01 (SQL injection): parameterized query `WHERE noc_code = ?`
- T-18-02 (DoS via oversized duties list): `raw_duties[:20]` cap
- T-18-03 (invalid wd_id): 404 / 422 HTTPException
- T-18-04 (information disclosure): `exclusions_text[:200]` echoes public OG definition text; no PII

## Verification

- `cd v2/backend && python -m pytest tests/test_jd_composition.py -v` → **6 passed**
- `cd v2/backend && python -m pytest -x` → **64 passed** (58 prior + 6 Phase 18). 0 regressions.

## Acceptance criteria

- All 6 test_jd_composition.py tests GREEN
- DraftDuty has all provenance + orphan fields with correct defaults
- WDPatchRequest.duties field + 20-item cap
- GET /api/noc/{noc_code}/duties uses `get_noc_connection()` (verified in code)
- POST /api/wd/{id}/orphan_check returns `flagged: []` for EC (verified by test)
- Full backend suite: 0 failures

## Deviations

None. All plan acceptance criteria met.
