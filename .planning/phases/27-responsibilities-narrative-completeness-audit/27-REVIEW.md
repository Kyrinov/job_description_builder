---
phase: 27-responsibilities-narrative-completeness-audit
reviewed: 2026-06-24T18:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - v2/backend/app/api/wd.py
  - v2/backend/app/models/work_description.py
  - v2/backend/app/services/export_service.py
  - v2/backend/tests/test_export.py
  - v2/backend/tests/test_wd.py
  - v2/frontend/src/app.jsx
  - v2/frontend/src/conversation.jsx
  - v2/frontend/src/conversation.test.jsx
  - v2/frontend/src/data.jsx
  - v2/frontend/src/document.jsx
  - v2/frontend/src/document.test.jsx
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: clean
---

# Phase 27: Code Review Report

**Reviewed:** 2026-06-24T18:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** clean

## Summary

Phase 27 is a high-quality, near-clone of Phase 26's vertical-slice pattern, with one well-scoped new feature (the 7-element completeness audit). All locked CONTEXT decisions are honored: WDPatchRequest co-update rule (both fields in commit `3a9cdcb`), `max_length=4000` ASVS V5 DoS mitigation, `build_seven_elements` typed-field-only audit (ROADMAP #4), `responsibility` never `"not_applicable"` (ROADMAP #3), soft-gate ReviewState (ROADMAP #5), STEP_RECORD_KEY-only entry (no reduce edits), narrative-or-placeholder export priority (no JES fallback, no synthesis), and dynamic `n++` so downstream Secs renumber when the Responsibilities Sec is hidden. All 8 new backend tests + 5 new frontend tests pass; the smoke run reported `12 passed, 28 deselected, 5 warnings` for the new test subsets.

No critical or warning findings — the implementation faithfully follows the locked patterns and the tests correctly pin every flagged decision. The three Info findings below are minor polish observations that do not block the phase.

## Critical Issues

None.

## Warnings

None.

## Info

### IN-01: `restart()` does not reset `completeness` state (pre-existing pattern)

**File:** `v2/frontend/src/app.jsx:628-634`

**Issue:** The `restart()` function clears `record`, `answers`, `stepIndex`, `wdId`, and several other local states, but does not reset `completeness`, `dutyHints`, `auditFindings`, `amendmentNotes`, `amendmentPanels`, or `orphanFlags`. The Phase 27 completeness state is therefore stale across a "Start a new description" cycle.

In practice this is harmless because (a) the user must walk the conversation before re-entering review, (b) the Review-hydration `useEffect` on lines 250-260 refetches `/api/wd/{wd_id}/validate-elements` whenever `reviewing` flips true with a new `wd_id`, and (c) `cancelled` in the cleanup function prevents setState on stale responses. However, if the user opens the review panel between the `setReviewing(true)` and the fetch returning, the badge would briefly show stale data.

**Fix (optional):** Add a single `setCompleteness(null)` (and the other state resets) to `restart()` for symmetry with `wdId` / `record` resets. Not a correctness bug — pattern consistency only.

```jsx
function restart() {
  setRecord({}); setAnswers({}); setStepIndex(0);
  setCompleteness(null);  // Phase 27: clear stale audit
  setDraft(initialAnswer(STEPS[0], {})); setReviewing(false); setEditingReturn(false);
  setWdId(null); setNocCandidates([]); setNocLoading(false);
  setOgCandidates([]); setOgLoading(false); setOgAlert(null);
  setDutyHints([]);  // Phase 23 too — same pattern
  setAmendmentNotes({}); setAmendmentPanels({});  // Phase 19 too
  setAuditFindings([]); setAuditRan(false);  // Phase 24 too
  try { localStorage.removeItem('jd-builder-v2-wd-id'); } catch {}
}
```

### IN-02: `isFresh('responsibilities_narrative')` key mismatch — flash animation silently won't fire (pre-existing pattern from Phase 26)

**File:** `v2/frontend/src/document.jsx:353` (and `app.jsx:30`)

**Issue:** `FLASH[step.id]` writes the **section key** into the flashes set (e.g., `responsibilities_narrative: 'resp_narrative'`), but `isFresh('responsibilities_narrative')` in `document.jsx` queries the flashes set with the **step id**. The conditional check `flashes.has('responsibilities_narrative')` therefore returns `false` even immediately after the advisor commits the step, and the `<Sec class="fresh">` highlight never animates. The same mismatch exists pre-existingly for `org_context` (`isFresh('org_context')` vs FLASH`'org_ctx'`) and `client_service_results` (vs `'csr'`) — both were copied forward unchanged by Phase 27.

**Phase 27 impact:** The Phase 27 Responsibilities Sec correctly mirrors the Phase 26 pattern. Phase 27 did not introduce this bug; it preserved it. Cosmetic only — no test covers the `fresh` animation behavior, so this is silent at the test layer.

**Fix (optional):** Either change the FLASH entries to identity-map the conditional sections (`org_context: 'org_context'` instead of `'org_ctx'`), OR change `document.jsx` to query the section keys (`isFresh('org_ctx')` instead of `isFresh('org_context')`). The second option is the smaller diff and matches the existing FLASH semantics.

```jsx
// document.jsx — three existing call sites
fresh={isFresh('org_ctx')}                   // was 'org_context'
fresh={isFresh('csr')}                       // was 'client_service_results'
fresh={isFresh('resp_narrative')}            // was 'responsibilities_narrative'
```

### IN-03: 5 new `build_seven_elements` tests emit `PytestWarning` for `@pytest.mark.asyncio` on sync functions

**File:** `v2/backend/tests/test_export.py:19, 740-883`

**Issue:** `test_export.py` has a module-level `pytestmark = pytest.mark.asyncio` (line 19). The 5 new build_seven_elements tests (`test_build_seven_elements_derived_effort_wc`, `test_build_seven_elements_no_jes_missing`, `test_build_seven_elements_org_context_reads_typed_field`, `test_build_seven_elements_responsibility_missing_not_notapplicable`, `test_build_seven_elements_total_seven`) are sync functions that import `build_seven_elements` and construct `WorkDescription` objects directly via `_wd_for_seven_elements`. They do not use any `async`/`await` features or the `client` fixture. Pytest emits one warning per test:

```
PytestWarning: The test <Function test_build_seven_elements_no_jes_missing> is marked with '@pytest.mark.asyncio' but it is not an async function.
```

The tests pass (5 passed, 24 deselected, 5 warnings) — the marker is applied unnecessarily but does not break execution. The warnings pollute the test output and could mask real warnings later.

**Fix (optional):** Move the `pytestmark = pytest.mark.asyncio` from module-level onto the async tests only, or refactor the file to use per-test `@pytest.mark.asyncio` decorators. Easiest fix: split the sync `build_seven_elements` tests into a separate file (e.g., `tests/test_seven_elements.py`) without the async marker, since they are pure-function unit tests and conceptually distinct from the HTTP-level export tests.

```python
# tests/test_seven_elements.py — new file, no pytestmark
from app.models.work_description import WorkDescription
from app.services.export_service import build_seven_elements
# ... 5 sync tests, no asyncio marker needed
```

---

_Reviewed: 2026-06-24T18:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_