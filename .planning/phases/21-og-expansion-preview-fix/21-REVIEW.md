---
phase: 21-og-expansion-preview-fix
reviewed: 2026-06-11T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - v2/backend/app/api/jes_scoring.py
  - v2/backend/app/api/og_classification.py
  - v2/backend/app/api/wd.py
  - v2/backend/app/data/constants.py
  - v2/backend/app/models/work_description.py
  - v2/backend/app/services/export_service.py
  - v2/backend/app/services/jes_service.py
  - v2/backend/tests/test_jes_level_suggest.py
  - v2/backend/tests/test_question_bank.py
  - v2/frontend/src/app.jsx
  - v2/frontend/src/components.jsx
  - v2/frontend/src/conversation.test.jsx
  - v2/frontend/src/data.jsx
  - v2/frontend/src/styles.css
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 21: Code Review Report

**Reviewed:** 2026-06-11
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Phase 21 adds 12 new OG groups to the classification engine, wires sub-group disambiguation for NU/SW/ED, adds a Socratic level-determination mini-interview (JES-LEV-01 Plan 08), and fixes the sector-gate visibility regression. The implementation is well-structured and the threat-model annotations are thorough. Three warnings and four info-level items were identified; no security vulnerabilities or data-loss risks were found.

The most impactful issue is a latent `AttributeError` crash in `wd.py`'s orphan-check handler (WR-01): the `else` branch of the `confirmed_og` shape-check calls `.og_code` as an attribute on a string, which will throw at runtime whenever `confirmed_og` is stored as a bare string code. The second warning (WR-02) is a level-range mismatch between the frontend `OG_LEVELS` constant and the JES factor scales for FB: the picker offers Level 08 but scoring silently clamps to max degree 7. WR-03 flags parameter mutation in `jes_service.py` that makes the audit trail misleading when level clamping fires.

---

## Warnings

### WR-01: AttributeError crash in orphan_check when confirmed_og is a bare string

**File:** `v2/backend/app/api/wd.py:197`

**Issue:** The orphan-check handler branches on `isinstance(wd.confirmed_og, dict)`. The `else` branch calls `wd.confirmed_og.og_code` as an attribute access. `WorkDescription.confirmed_og` is typed as `Optional[Union[str, dict]]`, and the noc_confirm step stores a bare string code. When that shape is in the DB, the else branch executes `(some_string).og_code` and raises `AttributeError: 'str' object has no attribute 'og_code'`. The identical helper `_og_code_from(wd)` in `export_service.py` handles both shapes correctly with `wd.confirmed_og or ""` and should be reused here.

**Fix:**
```python
og_code = (
    wd.confirmed_og.get("og_code")
    if isinstance(wd.confirmed_og, dict)
    else wd.confirmed_og or ""   # bare string — use directly
)
```
Or better, extract and reuse `_og_code_from`:
```python
# import from export_service or duplicate the two-line helper inline
from app.services.export_service import _og_code_from
og_code = _og_code_from(wd)
```

---

### WR-02: Frontend OG_LEVELS for FB offers Level 08 but JES scoring clamps to max degree 7

**File:** `v2/frontend/src/data.jsx:39`

**Issue:** `data.jsx` defines `FB: [1,2,3,4,5,6,7,8]` (8 levels). The backend `OG_LEVELS` constant also has 8 levels for FB. However, every factor in `JES_FACTORS_BY_GROUP["FB"]` has a maximum degree of 7 or less (the highest-degree factor, `"Decision making"`, goes to degree 7). The `score_jes_v2` point-rating path at `jes_service.py:235` silently clamps `degree = min(og_level, max_degree)`. A user who selects Level 8 will see "FB-08" in the document but receive a JES total computed at Level 7 with no warning. The mismatch is not surfaced anywhere in the UI.

**Fix:** Cap FB to 7 levels in both constants so the picker never offers an unreachable level:
```python
# constants.py
"FB": list(range(1, 8)),   # FB-01 to FB-07 — matches JES factor max degree
```
```javascript
// data.jsx
FB: [1,2,3,4,5,6,7],
```
If Level 8 is genuinely needed, add degree-8 entries to every FB factor in `JES_FACTORS_BY_GROUP["FB"]`.

---

### WR-03: og_level parameter mutated in place in score_jes_v2, making log/audit trail misleading

**File:** `v2/backend/app/services/jes_service.py:277`

**Issue:** When the requested `og_level` has no entry in `NON_EC_TOTALS[routing_code]`, the code rebinds the function parameter: `og_level = clamped`. From that point forward, the variable `og_level` holds the clamped value. The WD's `og_level` field (stored separately on the record) still carries the original value, so after scoring the advisor sees "Level selected: 9" on the WD but a JES total that was computed for Level 8. The discrepancy is silent.

**Fix:** Use a separate variable to avoid shadowing the caller-supplied value:
```python
effective_level = og_level
if og_level not in NON_EC_TOTALS[routing_code]:
    available = sorted(NON_EC_TOTALS[routing_code].keys())
    effective_level = min(available, key=lambda lv: abs(lv - og_level))
    logger.warning(
        "No JES totals for og_code=%r at level %r; using nearest level %r",
        routing_code, og_level, effective_level,
    )
total_points = NON_EC_TOTALS[routing_code][effective_level]
```

---

## Info

### IN-01: Three new level-suggest endpoints are synchronous while all other endpoints in the file are async

**File:** `v2/backend/app/api/jes_scoring.py:314,339,360`

**Issue:** `level_suggest`, `level_criteria`, and `level_criteria_groups` are defined with `def` (synchronous). All other endpoints in `jes_scoring.py` use `async def`. FastAPI runs sync path functions in a threadpool so there is no correctness issue, but the inconsistency is confusing and will silently break if a future change adds `await` inside these functions without converting the signature.

**Fix:** Convert all three to `async def`:
```python
@router.post("/jes/level-suggest")
async def level_suggest(req: LevelSuggestRequest) -> dict:
    ...

@router.get("/jes/level-criteria")
async def level_criteria(og_code: str, sub_group: str | None = None) -> dict:
    ...

@router.get("/jes/level-criteria-groups")
async def level_criteria_groups() -> list[str]:
    ...
```

---

### IN-02: `import logging` placed inside function body in wd.py

**File:** `v2/backend/app/api/wd.py:117`

**Issue:** `import logging` is placed inside the `patch_wd` function body rather than at module level. Python caches imports so there is no runtime cost, but the placement hides the dependency from linters and is inconsistent with the rest of the codebase.

**Fix:** Move to the top of the file alongside other stdlib imports:
```python
import logging
```

---

### IN-03: No end-to-end test for NT sub-group level-suggest paths

**File:** `v2/backend/tests/test_jes_level_suggest.py`

**Issue:** `EXPECTED_OG_CODES_WITH_CRITERIA` includes `NT-ADV`, `NT-DIT`, `NT-HME` and the `test_level_criteria_groups_returns_six_og_codes` test asserts NT is present in the groups list. However there is no `test_level_suggest_nt_*` test that exercises the actual suggestion path for any NT sub-group. If a data entry for an NT key is misconfigured (e.g. mismatched option ID), the failure would not be caught until runtime.

**Fix:** Add at least one NT test mirroring the NU-EMA pattern (which also uses `level_resolution="direct"`):
```python
@pytest.mark.asyncio
async def test_level_suggest_nt_adv_direct_national(client, env_with_db):
    response = await client.post(
        "/api/jes/level-suggest",
        json={"og_code": "NT", "sub_group": "ADV",
              "answers": {"nt_adv_scope": "national"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["suggested_level"] == 3
    assert data["confidence"] == "high"
```

---

### IN-04: OgLevelQuestions component can freeze the step if criteria has zero questions

**File:** `v2/frontend/src/components.jsx:543`

**Issue:** The render guard `if (!criteria)` handles the null/loading case. If the API returns a valid response with `questions: []`, `criteria` is truthy and `questions.length` is 0. The component renders an empty container, `handleAnswer` is never called, `onChange` is never called, and `answerValid` (which checks `Object.keys(value).length > 0`) returns false — freezing the step permanently with no way to proceed.

This cannot happen with the current data (all 11 `JES_LEVEL_CRITERIA` entries have at least one question), but it is a latent UI dead-end for future additions.

**Fix:** Add a guard that emits the `_criteria_unavailable` sentinel when questions are empty, matching the existing error-path pattern at line 505:
```jsx
if (!criteria) return <p className="step-loading">Level criteria not available for this group.</p>;
if (questions.length === 0) {
  // Auto-emit sentinel: no questions defined, let user proceed to level picker
  onChange({ _criteria_unavailable: true });
  return <p className="step-loading">No level questions available — proceed to the level picker.</p>;
}
```

---

_Reviewed: 2026-06-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
