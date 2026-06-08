---
phase: 18-jd-composition-live-preview
plan: 01
type: execute
wave: 0
autonomous: true
files_modified:
  - v2/backend/tests/test_jd_composition.py (NEW)
  - v2/backend/tests/conftest.py
  - v2/frontend/src/document.test.jsx
---

# Plan 18-01 — RED test stubs (Wave 0)

## What was built

Nyquist-compliance RED test stubs for Phase 18:

- **`v2/backend/tests/test_jd_composition.py`** (NEW): 6 backend test stubs covering JD-01 (GET /api/noc/{noc_code}/duties success + 404), JD-02 (DraftDuty provenance fields), JD-03 (advisor duty source type), JD-04 (orphan check EC no flags), and patch persistence.
- **`v2/backend/tests/conftest.py`**: appended `noc_duties_db` fixture (lighter than `noc_mapping_db` — no vec/FTS5, just `noc_elements` with `element_type='Main duties'`); added singleton reset in autouse `_settings_env_defaults` so per-test tmp_path is honored; `noc_duties_db` resets the Settings singleton after setting NOC_DB_PATH.
- **`v2/frontend/src/document.test.jsx`**: appended 6 Phase 18 RED stubs covering DOC-01 (Section 5 ghost), DOC-03 (Section 3 ghost note), DOC-04 (Section 3 click-to-edit), DOC-05 (src pill wording), orphan badge, and JD-01 frontend fetch.

## Verification

- `cd v2/backend && python -m pytest tests/test_jd_composition.py` → 6 failed
- `cd v2/frontend && npm run test` → 6 new stubs failed, 24 prior pass
- No regressions in prior test suites (58 backend, 24 frontend)

## Acceptance criteria

- 6 backend RED stubs in test_jd_composition.py (all FAILED, none SKIPPED or ERROR)
- `noc_duties_db` fixture in conftest.py with `monkeypatch.setenv("NOC_DB_PATH", ...)` and singleton reset
- 6 frontend RED stubs appended to document.test.jsx (existing Phase 17 tests untouched)
- No modifications to existing conftest.py fixtures
- 58 backend + 24 frontend prior tests still GREEN
