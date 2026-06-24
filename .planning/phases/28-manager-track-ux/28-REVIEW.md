---
status: flagged
phase: 28-manager-track-ux
reviewed_at: 2026-06-24T20:30:00Z
reviewer: gsd-code-reviewer
files_reviewed: 11
files_reviewed_list:
  - v2/backend/app/models/work_description.py
  - v2/backend/app/api/wd.py
  - v2/backend/app/services/classification_gate.py
  - v2/backend/app/services/export_service.py
  - v2/frontend/src/data.jsx
  - v2/frontend/src/app.jsx
  - v2/frontend/src/document.jsx
  - v2/frontend/src/conversation.jsx
  - v2/backend/tests/test_wd.py
  - v2/backend/tests/test_export.py
  - v2/frontend/src/app.test.jsx
  - v2/frontend/src/conversation.test.jsx
  - v2/frontend/src/document.test.jsx
findings:
  critical: 0
  major: 1
  minor: 3
  total: 4
---

# Phase 28: Code Review Report

**Reviewed:** 2026-06-24
**Depth:** standard
**Files Reviewed:** 13 (10 source + 3 test, per the file-list above)
**Status:** flagged

## Summary

Phase 28 (Manager-Track UX) is implemented cleanly across the 11 source files modified in Plans 28-01 and 28-02. The wd_type co-update rule (model + WDCreateRequest + WDPatchRequest + create_wd wiring in the same commit, per D-28-04) is correctly enforced; the user_role drop guard (D-28-03) is verified by `test_user_role_dropped_from_patch`; the `require_og_confirmed` bypass uses `getattr(wd, "wd_type", "advisor") == "manager"` (intrinsic to wd_type with forward-compat default); the DRAFT watermark is hardcoded (no user input reaches it); localStorage role storage follows D-28-01; the manager STEPS variant uses an additive `userRole` parameter (additive signature preserves all existing advisor-mode call sites); the MGR-02 UI suppression layer is gated at the call site (app.jsx) for `ClassifyBadge` and at the component for `DocumentPane`/`ReviewState` (each with a `'advisor'` default); and the TDD-within-task pattern produced comprehensive regression guards (179 backend + 85 frontend GREEN per SUMMARYs).

**One major finding**: the manager-track bypass of `require_og_confirmed` is wired into `classification_gate.py` (intrinsic to wd_type, correct), but the documented T-28-05 mitigation (DRAFT watermark as the "self-documenting abuse surface") is **only applied inside `generate_wd_docx`** — not in `generate_poster_docx` or in the PDF rendering path. A user who flips `wd_type` to `manager` can export a poster or PDF that bypasses the OG gate AND ships without the DRAFT marker. This is the same attack surface the SUMMARY explicitly calls out, with the mitigation only half-applied.

**Three minor findings**: the `restart()` function does not reset `userRole` (deferred per CONTEXT D-28-XX, but worth recording); no audit trail of wd_type at export time (mitigation is the watermark itself, which is incomplete — see major); and pre-Phase-28 users with in-progress WDs will be forced through the RoleSelector on next visit (deliberate new onboarding, but unflagged in SUMMARY's "Issues Encountered").

No secrets, PII, or injection vectors were identified. The `extra='ignore'` config on `WDPatchRequest` correctly drops `user_role` (and any other unknown field). The `Literal["advisor", "manager"]` type constraint on `wd_type` rejects arbitrary strings with 422. The SQL queries use parameterised statements (pre-existing). The watermark constant is a hardcoded string with no user-input interpolation (T-28-05 mitigation is correctly applied **inside** `_apply_draft_watermark`).

---

## Major Issues

### MAJ-01: Poster and PDF exports bypass `require_og_confirmed` for manager WDs without the DRAFT watermark

**Files:**
- `v2/backend/app/api/export.py:100` (poster endpoint)
- `v2/backend/app/api/export.py:138` (PDF endpoint)
- `v2/backend/app/services/export_service.py:611-636` (watermark helper, only called from DOCX)
- `v2/backend/app/services/export_service.py:676-677` (watermark application site)

**Issue:** The `require_og_confirmed` bypass for manager WDs is correctly intrinsic to wd_type (single point in `classification_gate.py:38`), so every caller — `export.py` DOCX, poster, and PDF — inherits the bypass. However, the DRAFT watermark (T-28-05 mitigation) is only applied **inside `generate_wd_docx`** (export_service.py:676-677):

```python
# export_service.py (line 676-677, inside generate_wd_docx)
if getattr(wd, "wd_type", "advisor") == "manager":
    file_bytes = _apply_draft_watermark(file_bytes)
```

The poster endpoint (export.py:100-106) calls `generate_poster_docx`, which does not apply the watermark. The PDF endpoint (export.py:109-203) bypasses `generate_wd_docx` entirely — it builds its own HTML inline (line 183-190) and renders via WeasyPrint directly. Both routes call `require_og_confirmed(wd)` (lines 100, 138) which the manager WD bypasses, so:

1. A user (or anyone who can call the API) sets `wd_type='manager'` on a WD that has no confirmed_og
2. POSTs `/api/wd/{id}/export/poster` or `/api/wd/{id}/export/pdf`
3. The 409 gate is bypassed, the export succeeds, and the output **has no DRAFT marker**

The SUMMARY's `key-decisions` and `Decisions Made` document the watermark as the explicit T-28-05 mitigation ("a malicious advisor setting wd_type='manager' to bypass the OG gate still gets a clearly-labelled DRAFT DOCX. Self-documenting abuse surface"). The mitigation only covers the DOCX path; poster and PDF exports undermine it.

**Fix:** Apply the watermark in `generate_poster_docx` and in the PDF rendering path. Cleanest fix is to push the watermark logic into the service layer:

```python
# export_service.py — modify generate_poster_docx (line 696)
async def generate_poster_docx(wd_id, db_path):
    # ...existing render...
    if getattr(wd, "wd_type", "advisor") == "manager":
        file_bytes = _apply_draft_watermark(file_bytes)
    # ...rest unchanged...
```

For PDF, the cleanest fix is to add a "DRAFT — PENDING CLASSIFICATION" banner to the HTML template (line 183-190) when `wd.wd_type == 'manager'`, OR generate the PDF from the watermarked DOCX bytes (render DOCX via `_render_docx`, watermark, then convert DOCX to PDF — though this requires a different toolchain).

Tests should be added mirroring the existing `test_export_docx_manager_has_draft_watermark`:
- `test_export_poster_manager_has_draft_watermark`
- `test_export_pdf_manager_has_draft_marker` (asserts the rendered text appears in the PDF byte stream via pdfplumber or similar)

---

## Minor Issues

### MIN-01: `restart()` does not reset `userRole` state — only `wd_id`

**File:** `v2/frontend/src/app.jsx:679-685`

**Issue:** The `restart()` function clears all in-memory state and removes `jd-builder-v2-wd-id` from localStorage, but does NOT call `setUserRole(null)` and does NOT remove `jd-builder-v2-role` from localStorage. After "Start a new description", the user remains in whichever role they selected (advisor or manager). To switch roles mid-session, they must manually clear `jd-builder-v2-role` via browser dev tools.

The SUMMARY acknowledges this as deferred ("a 'Switch role' affordance in the Header is deferred per the agent's discretion note in CONTEXT.md"), but the simpler fix would be to force the RoleSelector on next "Start a new description":

```jsx
function restart() {
  setRecord({}); setAnswers({}); setStepIndex(0);
  setDraft(initialAnswer(STEPS[0], {})); setReviewing(false); setEditingReturn(false);
  setWdId(null); setNocCandidates([]); setNocLoading(false);
  setOgCandidates([]); setOgLoading(false); setOgAlert(null);
  setUserRole(null);  // <-- force role selector on next mount
  try {
    localStorage.removeItem('jd-builder-v2-wd-id');
    localStorage.removeItem('jd-builder-v2-role');
  } catch {}
}
```

This is recorded as a minor observation — explicitly deferred per CONTEXT. Optional fix.

### MIN-02: No audit trail of `wd_type` at export time — wd_type can be toggled to bypass and silently revert

**Files:**
- `v2/backend/app/services/export_service.py:644-693` (generate_wd_docx)
- `v2/backend/app/api/export.py:55-203` (all export routes)
- `v2/backend/app/services/classification_gate.py:21-53`

**Issue:** `wd_type` is mutable post-creation via PATCH. A user (or attacker) can:
1. Create a WD as advisor with no confirmed_og → 409 on export
2. PATCH `wd_type='manager'` to bypass the gate
3. Export (gets watermark for DOCX, but **no marker for poster/PDF — see MAJ-01**)
4. PATCH `wd_type='advisor'` to revert the record
5. No forensic trail of the bypass

The `audit_log` table records `risk_audit_finding`, `risk_audit_decision`, and `manager_amendment` events but nothing for `wd_type` changes or manager-track exports. For incident response, a record of "this export was performed with wd_type='manager'" would be valuable.

The T-28-01 mitigation is the watermark itself, which is the primary signal. This finding is a secondary recommendation — adding `INSERT INTO audit_log (wd_id, event='manager_track_export', actor='system', detail={wd_type, filename}, created_at)` inside `generate_wd_docx` (and equivalents) when `wd.wd_type == 'manager'` would close the audit gap without changing user-facing behavior.

Severity: minor — informational; watermark is the primary mitigation and is correctly applied to DOCX.

### MIN-03: Pre-Phase-28 users with in-progress WDs will see the RoleSelector on next visit

**File:** `v2/frontend/src/app.jsx:134-136`

**Issue:** The `userRole` lazy initializer reads `jd-builder-v2-role` from localStorage, which is a new key introduced in Phase 28. Any user with an in-progress WD from before Phase 28 (no role key) will see the RoleSelector on next visit. This forces them through the role gate even though they're mid-task.

The SUMMARY's `Issues Encountered` section describes the test-setup work (5 existing tests had to be seeded with `jd-builder-v2-role='advisor'` in beforeEach) but doesn't flag the equivalent real-user impact. This is a deliberate new onboarding step (the role concept didn't exist before Phase 28), so the behaviour is by design — but it would be friendlier to backfill the role key for existing users with in-progress WDs:

```jsx
const [userRole, setUserRole] = useState(() => {
  try {
    const role = localStorage.getItem('jd-builder-v2-role');
    if (role) return role;
    // Backwards-compat: existing users with in-progress WDs default to advisor
    const record = localStorage.getItem('jd-builder-v2-record');
    if (record) {
      const parsed = JSON.parse(record);
      if (parsed && parsed.title) return 'advisor';
    }
    return null;
  } catch { return null; }
});
```

This would default existing users (who have a `title` set in `jd-builder-v2-record`) to the advisor track — matching their pre-Phase-28 behaviour — while still showing the RoleSelector to genuinely new users. Optional fix.

---

## Regression-Risk Notes (advisor track)

The following surfaces were verified to preserve advisor-mode behaviour:

- **`isStepVisible(step, answers, userRole)`** — manager filter is the first line; the existing sector-gate + level-description switches fire unchanged when `userRole !== 'manager'`. The `userRole` parameter is additive — passing `undefined` (or `'advisor'`) yields identical results to the pre-Phase-28 function. Locked by `getVisibleSteps advisor mode unchanged when userRole passed explicitly` (conversation.test.jsx:964).

- **`require_og_confirmed(wd)`** — manager bypass is a single early-return line. The `getattr(wd, "wd_type", "advisor") == "manager"` default `"advisor"` keeps old WD rows (serialised before Phase 28) behaving as advisor. The Pydantic `Literal["advisor", "manager"]` type on `WorkDescription.wd_type` defaults to `"advisor"`. Locked by `test_export_docx_advisor_still_409_without_og` (test_export.py:355).

- **`DocumentPane` and `ReviewState` signatures** — `userRole = 'advisor'` default on both signatures. All 76 pre-Phase-28 test fixtures that don't pass `userRole` continue to render the full advisor UI. The conditional gates use `userRole !== 'manager'` (positive check), so `undefined` AND `'advisor'` both render the full UI.

- **`ClassifyBadge`** — gated at the call site in app.jsx (`{userRole !== 'manager' && <ClassifyBadge cls={cls} />}`), not inside the component. The component itself is role-agnostic. Indirectly tested by the DocumentPane inspection tests asserting no `EC-04` etc. in manager mode.

- **`WDPatchRequest`** — `user_role` is intentionally absent. The `extra='ignore'` config silently drops unknown fields, including `user_role`. Locked by `test_user_role_dropped_from_patch` (test_wd.py:193).

- **TDZ constraint** — `userRole` useState is declared BEFORE `stepIndex` useState (app.jsx:134 before line 137) so the stepIndex lazy initializer can close over `userRole` without a ReferenceError. Documented in the comment block above the useState; verified by the stepIndex resume test (`stepIndex resume: initialises past step 0 when record has answered fields`).

- **`onAmendSave` prop** — the SUMMARY's deviation #2 (false alarm) recorded that `onAmendSave` was being passed `amendmentNotes` (data) instead of `onAmendSave` (handler). Verified that all 9 Sec call sites in document.jsx correctly pass `onAmendSave={onAmendSave}`. No fix needed.

- **`record-fallback` paths** — `_build_wd_context` and `build_seven_elements` use `record.get("duties")` / `record.get("quals")` / `record.get("client_service_results")` fallbacks. These pre-date Phase 28 and remain unchanged. Manager WD exports that lack classification will render with the placeholder text and `[To be completed by advisor]` strings (R-RESP-03 / R-ELEM-01a semantics).

---

## Test Coverage Notes

- **Backend wd_type co-update**: 4 tests (round-trip, default, drop guard, manager preserved). Strong coverage of the co-update invariant.
- **Backend manager bypass**: 3 tests (bypass 409, watermark present, advisor regression). Missing: poster/PDF watermark tests (see MAJ-01).
- **Frontend RoleSelector**: 3 tests (hydration, absent, click persists). Missing: text-content assertion (only data-testid is asserted). Minor gap.
- **Frontend manager STEPS variant**: 3 tests (skips 4 classification-internal steps, strictly shorter than advisor, advisor regression). Strong.
- **Frontend MGR-02 DocumentPane**: 3 functional tests + 2 inspection tests (OG codes absent, JES factor names absent). Strong contract coverage.
- **Frontend MGR-02 ReviewState**: 3 functional tests + 1 inspection test (no classification codes, no CBA citations). Strong.
- **Total**: 17 new tests across Phase 28 (4 backend wd_type + 3 backend export + 3 frontend MGR-01 + 3 frontend MGR-03 + 3 frontend MGR-02 DocPane + 3 frontend MGR-02 ReviewState + 1 frontend MGR-02 inspection).

---

## What Was NOT Flagged (skipped per scope)

- **Performance**: out of v1 scope per the reviewer's scope definition.
- **Empty `.catch(() => {})` patterns** (app.jsx:276, 288, 304, 419, 515, 709, 804): pre-existing intentional fire-and-forget patterns with explanatory comments. Not a Phase 28 regression.
- **`safeCls.code` fall-through in document.jsx:256-258**: pre-existing pattern; manager branch (line 254-255) short-circuits before reaching this code in manager mode. No Phase 28 regression risk.
- **`confirmed_og` string-shape handling**: `confirmed_og: Optional[Union[str, dict]]` means the frontend `r.confirmed_og.og_code` access in document.jsx:257 would crash if `confirmed_og` is a string. The backend `_og_code_from` helper (export_service.py:148) explicitly handles both shapes; the frontend doesn't. **Pre-existing**, not introduced by Phase 28 — flagged for future hardening but not a regression.
- **HTML escaping in PDF export** (export.py:174-190): correctly uses `html.escape()` on user-supplied data (title, og_str, duty text). XSS-safe. Pre-existing pattern.

---

_Reviewed: 2026-06-24T20:30:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_