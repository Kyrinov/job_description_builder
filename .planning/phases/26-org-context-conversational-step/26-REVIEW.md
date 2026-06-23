---
phase: 26-org-context-conversational-step
reviewed: 2026-06-23T16:30:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - v2/backend/app/api/wd.py
  - v2/backend/app/models/work_description.py
  - v2/backend/app/services/export_service.py
  - v2/backend/tests/test_export.py
  - v2/backend/tests/test_wd.py
  - v2/frontend/src/app.jsx
  - v2/frontend/src/app.test.jsx
  - v2/frontend/src/components.jsx
  - v2/frontend/src/conversation.test.jsx
  - v2/frontend/src/data.jsx
  - v2/frontend/src/document.jsx
  - v2/frontend/src/document.test.jsx
findings:
  critical: 1
  warning: 1
  info: 4
  total: 6
status: issues_found
---

# Phase 26: Code Review Report

**Reviewed:** 2026-06-23T16:30:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Phase 26 adds an `org_context` conversational step (backend root field + co-update on PATCH, 4-part OrgContextInput component, export priority over synthesized fallback, new DocumentPane Secs, stepIndex resume-by-last-answered). The frontend rendering, model layer, and export priority logic are well-structured and XSS-safe (React text-node rendering; no `dangerouslySetInnerHTML`).

However, tracing the data path from SPA → PATCH → export reveals **one Critical bug**: the frontend persists `org_context` only nested inside `record.org_context`, but `export_service._build_wd_context` reads the **root** `wd.org_context` field — which the SPA never mirrors up. The backend tests PATCH the root field directly (and pass), masking the integration gap. As shipped, every DOCX export silently falls back to the synthesized `_build_organizational_context_text(wd)` paragraph, ignoring the advisor's typed input.

A secondary Warning: `OrgContextInput` initializes its 4 sub-fields to empty strings and never reads the `value` prop, so when an advisor clicks "Edit" on the Organizational Context section during review, the previously committed text does not repopulate the textareas.

No security issues found: `max_length=4000` is enforced at the Pydantic layer (DoS mitigation), React auto-escapes all org_context/CSR rendering, and SQL queries are parameterized throughout.

## Critical Issues

### CR-01: org_context committed to `record.*` but export reads root `wd.org_context` — feature silently broken on export

**File:** `v2/frontend/src/app.jsx:294-302` (commit payload construction)
**Issue:**
The `org_context` step's `apply` writes the assembled string into the record dict (`apply: (r, a) => ({ org_context: a })` in `data.jsx:668`). The `commit()` function then sends `record: newRecord` in the PATCH payload, but the classification-root mirror list at `app.jsx:299-302` does NOT include `org_context`:

```javascript
['confirmed_noc', 'confirmed_og', 'og_level', 'reports_to_military',
 'jes_scores', 'jes_total_points'].forEach(k => {
  if (k in newRecord) wdPayload[k] = newRecord[k];
});
```

As a result, the backend receives `record.org_context` (nested) but never receives a top-level `org_context` field. The WD is stored with `wd.record['org_context'] = "..."` but `wd.org_context` (root) stays `None`.

The export pipeline reads ONLY the root field:

```python
# export_service.py:397-401
"organizational_context_text": (
    wd.org_context
    if wd.org_context is not None
    else _build_organizational_context_text(wd)
),
```

So every export silently falls back to the synthesized text built from `record.branch`/`reports`/`summary` — the advisor's typed organizational context is **never rendered in the DOCX**.

The existing backend tests (`test_org_context_in_export`, `test_patch_org_context_round_trip`) PATCH the root field directly (`json={"org_context": "..."}`) and pass, which masks the integration gap because they don't exercise the actual SPA data path. Contrast with `client_service_results`, which works correctly because both the SPA and `export_service` read it from `record.*`.

**Impact:** Data loss on export. The feature appears functional in the live preview (which reads `record.org_context` via `liveRecord`) but silently fails in the deliverable DOCX.

**Fix:** Add `org_context` to the mirror list so it is promoted to the root field on PATCH:

```javascript
// v2/frontend/src/app.jsx — inside commit()
['confirmed_noc', 'confirmed_og', 'og_level', 'reports_to_military',
 'jes_scores', 'jes_total_points', 'org_context'].forEach(k => {
  if (k in newRecord) wdPayload[k] = newRecord[k];
});
```

Additionally, add an integration-style test that drives the SPA `commit()` path (or mirrors its payload shape: `{record: {org_context: "..."}, ...}` WITHOUT a root `org_context`) and asserts the rendered DOCX contains the advisor's text. The current `test_org_context_in_export` test should be kept (it pins the backend contract) but supplemented with one that reflects the frontend's actual payload.

## Warnings

### WR-01: OrgContextInput ignores the `value` prop — editing the step loses previously committed context

**File:** `v2/frontend/src/components.jsx:723-735`
**Issue:**
`OrgContextInput` initializes `parts` to four empty strings and only ever updates them via `handlePart`. The `value` prop is accepted but never read:

```javascript
function OrgContextInput({ value, onChange }) {
  const [parts, setParts] = useState({
    work_stream: '', org_placement: '', reporting: '', additional: '',
  });
  // ... value is never referenced again
}
```

When an advisor clicks the editable "Organizational Context" section in review (`document.jsx:309` → `onEditStep('org_context')` → `editStep` sets `draft = answers['org_context']`, the previously committed assembled string), the component remounts with `value=<assembled string>` but renders four empty textareas. The advisor must re-enter all context from scratch. Any interim commit overwrites the prior value with the new (possibly empty) draft.

This does not affect first-time entry (internal `parts` state is the source of truth and works correctly during a single mount). It only manifests on re-edit.

**Fix:** Either hydrate `parts` from `value` on mount (parsing the assembled string back into parts is lossy, so prefer the option below), or restructure the draft to carry the parts object rather than an assembled string. The simplest minimal fix that preserves the assembled-string contract is to display the prior value as a read-only reference and let the advisor re-enter:

```javascript
function OrgContextInput({ value, onChange }) {
  const [parts, setParts] = useState(() => {
    // On mount, if a prior value exists we cannot reliably split it back into
    // the 4 sub-fields (assembly is lossy). Surface it as a read-only
    // reference below the inputs instead of pretending we can round-trip.
    return { work_stream: '', org_placement: '', reporting: '', additional: '' };
  });
  // ... existing handlePart logic ...
  // Render prior value read-only when present and no sub-field has been touched:
  {value && !Object.values(parts).some(v => v.trim()) && (
    <div className="org-context-input__prior">
      <span>Current value (will be replaced when you type below):</span>
      <p>{value}</p>
    </div>
  )}
}
```

A cleaner long-term fix is to change the step `apply` to store the parts object directly (`apply: (r, a) => ({ org_context: a })` where `a` is the parts object), update `answerValid` to check `Object.values(value).some(v => v.trim())`, and update `export_service` to join the parts. This preserves round-trip fidelity.

## Info

### IN-01: Export priority treats empty string as "populated" — renders blank section instead of fallback

**File:** `v2/backend/app/services/export_service.py:397-401`
**Issue:**
The priority check uses `is not None`, so an empty-string `wd.org_context` short-circuits the fallback and renders an empty Organizational Context section in the DOCX:

```python
"organizational_context_text": (
    wd.org_context
    if wd.org_context is not None   # "" passes this check
    else _build_organizational_context_text(wd)
),
```

The SPA's `answerValid` (`components.jsx:807`) prevents committing an empty string (`value.trim()` must be non-empty), so this path is unreachable from the UI. However, a direct API caller could PATCH `{"org_context": ""}` and produce an empty section in the export. Defense-in-depth: prefer truthiness.

**Fix:**
```python
"organizational_context_text": (
    wd.org_context
    if (wd.org_context or "").strip()
    else _build_organizational_context_text(wd)
),
```

### IN-02: No test for `max_length=4000` enforcement on `org_context` PATCH

**File:** `v2/backend/tests/test_wd.py:63-78`
**Issue:**
`test_patch_org_context_round_trip` verifies the happy-path round-trip but does not exercise the `max_length=4000` DoS mitigation declared on `WDPatchRequest.org_context` (`wd.py:149`). A regression that removes the `Field(...)` constraint would not be caught.

**Fix:** Add a test asserting 422 on over-length input:
```python
async def test_patch_org_context_rejects_over_length(client):
    """ORG-01: PATCH org_context > 4000 chars returns 422 (ASVS V5 DoS mitigation)."""
    create_resp = await client.post("/api/wd", json={"record": {}, "answers": {}, "step_index": 0})
    wd_id = create_resp.json()["id"]
    resp = await client.patch(f"/api/wd/{wd_id}", json={"org_context": "x" * 4001})
    assert resp.status_code == 422
```

### IN-03: stepIndex resume clamps to `STEPS.length - 1` — completed users land on last step, not review

**File:** `v2/frontend/src/app.jsx:128`
**Issue:**
`Math.min(lastAnswered + 1, STEPS.length - 1)` correctly prevents an out-of-bounds index, but when the advisor has answered every step (including `quals`), they resume on the last step rather than in the `reviewing` state. They must click Continue once to enter review. Not a regression (the prior `useState(0)` was worse), and non-destructive, but worth noting.

**Fix (optional):** If `lastAnswered === STEPS.length - 1`, consider initializing `reviewing` to true as well. This requires coordinating the `reviewing` initializer with the same localStorage read — defer unless it surfaces as user feedback.

### IN-04: OrgContextInput silently drops `cfg`, `onSubmit`, `record` props spread by StepInput

**File:** `v2/frontend/src/components.jsx:780, 723`
**Issue:**
`StepInput` dispatches via `<OrgContextInput {...props} />`, but `OrgContextInput` only destructures `{ value, onChange }`. The extra props (`cfg`, `onSubmit`, `record`) are accepted by React but ignored. Harmless (no runtime error), but inconsistent with peer components (e.g. `QualEditor`, `DutyBuilder`) which consume `cfg`. If `org_context_input` ever needs configuration (per-OG placeholders, character counters, etc.), the wiring is already in place but the component signature would need updating.

**Fix:** No action required now. If future config is needed, destructure `cfg` explicitly: `function OrgContextInput({ value, onChange, cfg })`.

---

_Reviewed: 2026-06-23T16:30:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
