---
phase: 23-writing-guide-integration
plan: 03
status: complete
type: execute
wave: 2
depends_on: [23-02]
files_modified:
  - v2/backend/app/api/wd.py
requirements: [WG-02]
---

# Plan 23-03 Summary — POST /api/wd/{id}/validate-duties Endpoint

## Objective
Wired `POST /api/wd/{wd_id}/validate-duties` into `wd.py` following the exact `run_orphan_check` pattern. Turned the two WG-02 endpoint integration tests GREEN.

## Deliverable

New endpoint in `v2/backend/app/api/wd.py` (inserted between `run_orphan_check` and `sjd_start`):

```python
@router.post("/wd/{wd_id}/validate-duties")
async def validate_duties_endpoint(wd_id: str) -> dict:
    """WG-01/WG-02: Structural duty validation. Non-blocking advisory check.
    ...
    """
    from app.services.duty_validator import validate_duties as _validate_duties
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
    finally:
        con.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Work description not found")
    wd = WorkDescription.model_validate_json(row["data"])
    findings = _validate_duties(wd.duties)
    return {"wd_id": wd_id, "findings": findings}
```

## Key design decisions

- **Mirrors `run_orphan_check` exactly:** Same DB load pattern (parameterised SQL), same 404 guard, same `WorkDescription.model_validate_json(row["data"])` deserialisation.
- **No router registration needed:** Uses the existing `router` defined at the top of `wd.py`. No changes to `__init__.py` or `main.py`.
- **No persisted state:** Read-only endpoint — does not call `setRecord` or update DB. Findings are returned to the caller and discarded server-side.
- **Imports at function level:** `from app.services.duty_validator import validate_duties as _validate_duties` is deferred to runtime, matching the `run_orphan_check` import pattern. Avoids import-time circularity risk.
- **Empty duties list is valid:** A WD with no duties returns `{wd_id, findings: []}`. No special-case branch.
- **404 is the only error path:** Findings never raise an error — the endpoint is non-blocking, advisory only. 404 is reserved for the missing WD case (security boundary T-23-05: `wd_id` is the only user input; parameterised SQL prevents injection).

## Verification Results

```bash
cd v2/backend && python -m pytest tests/test_writing_guide.py -v
```

```
9 passed, 7 warnings in 4.55s
```

**All 9 test_writing_guide.py tests GREEN:**
- 5 WG-01 unit tests (validator)
- 2 WG-02 endpoint tests (validate-duties 200 + 404)
- 2 sentinel tests (OG_DEFINITIONS coverage, client_service_results step)

```bash
cd v2/backend && python -m pytest -q
```

```
134 passed, 15 warnings in 10.48s
```

**Full backend suite: 134/134 GREEN** (125 pre-existing + 9 new = 134).

## Acceptance Criteria Met

- [x] `validate_duties_endpoint` defined with `@router.post("/wd/{wd_id}/validate-duties")`
- [x] `from app.services.duty_validator import validate_duties` present
- [x] `test_validate_duties_endpoint` PASSED (200 with `findings` list and matching `wd_id`)
- [x] `test_validate_duties_404` PASSED (404 for unknown WD — now correct, not false-positive)
- [x] All 9 test_writing_guide.py tests PASSED
- [x] Full backend suite (134 tests) PASSED — zero regressions

## Next

Plan 23-04 will wire the four frontend-side changes (data.jsx, app.jsx, components.jsx, styles.css) to:
- POST to `/api/wd/{id}/validate-duties` after duties step commit
- Store findings in `dutyHints` state
- Render `.duty-hint` badges inline in DutyBuilder
- Render `.og-duty-tip` box above the duty list
- Add `client_service_results` step to the conversation
