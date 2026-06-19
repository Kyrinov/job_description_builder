# Phase 26: Org Context Conversational Step - Research

**Researched:** 2026-06-19
**Domain:** React SPA + FastAPI + docxtpl — new typed WD field, 4-part Socratic step, document preview section, DOCX export
**Confidence:** HIGH

---

## Summary

Phase 26 is the foundation phase for v4.0. It adds `org_context: Optional[str]` as a typed root field on `WorkDescription` (and `WDPatchRequest` in the same commit), introduces a 4-part Socratic step into the frontend `STEPS` array, renders the assembled text in the document preview above the Client Service Results section, and populates the `{{ organizational_context_text }}` variable in the Accessible JD DOCX template.

The phase has three pre-conditions that must land before the new STEPS entry is inserted. First, the `stepIndex` resume mechanism must change from a raw integer (currently always 0 on refresh) to a derivation from `STEPS.findLastIndex(s => record[...] !== undefined)` — because `record` IS persisted to localStorage but `answers` and `stepIndex` are NOT. Without this fix, inserting a new step shifts all existing integer indices by 1, silently landing existing sessions on the wrong step. Second, the co-update rule (WorkDescription field + WDPatchRequest field in the same git commit) must be enforced with a PATCH round-trip test. Third, the document preview currently does NOT render client_service_results despite that step existing in STEPS since Phase 23 — Phase 26 must also add the preview section for client_service_results alongside the new org_context section.

The export side is straightforward: `wd_accessible_template.docx` already has `{{ organizational_context_text }}` at paragraph 15 (Heading 2: "Organizational context"), and `_build_organizational_context_text()` in `export_service.py` already synthesizes a fallback from `record.branch`/`record.reports`/`record.summary`. Phase 26 changes this so the typed `wd.org_context` field is used FIRST when populated, with the synthesized fallback only when `org_context is None`.

**Primary recommendation:** Four deliverables in one phase — (1) stepIndex regression fix, (2) WorkDescription + WDPatchRequest co-update, (3) 4-part Socratic step + document preview, (4) DOCX export path update. These must land in this order within the wave to prevent regressions.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| org_context field persistence | API / Backend | Database | Typed root field on WorkDescription; persisted to SQLite work_descriptions.data JSON column |
| WDPatchRequest co-update | API / Backend | — | Pydantic model field; extra="ignore" drops unknown keys silently — must be explicit field |
| stepIndex resume fix | Browser / Client | — | Pure frontend state derived from persisted localStorage record |
| 4-part Socratic step (OrgContextInput) | Browser / Client | — | New StepInput type in components.jsx; dispatched by StepInput via step.input.type |
| STEPS insertion | Browser / Client | — | data.jsx STEPS array; new step inserted before client_service_results at phase 3 |
| Document preview rendering | Browser / Client | — | document.jsx DocumentPane adds new Sec above Client Service Results |
| DOCX export (org_context population) | API / Backend | — | export_service.py _build_wd_context reads wd.org_context; falls back to synthesized text |

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ORG-01 | 4-part Socratic step (work stream, organizational placement, reporting relationship, additional context); responses assembled into `org_context: Optional[str]` on WorkDescription; WDPatchRequest updated same commit | STEPS pattern in data.jsx; new `org_context` step inserts before `client_service_results`; assembly in step.apply; WDPatchRequest co-update enforced by PATCH round-trip test |
| ORG-02 | org_context renders in document live preview above Client Service Results | document.jsx Sec pattern; new section added above existing (not yet rendered) client_service_results section; both sections need preview rendering |
| ORG-03 | org_context populates Part 2 Organizational Context section of Accessible JD DOCX export | `{{ organizational_context_text }}` at template line 15; `_build_wd_context` in export_service.py reads `wd.org_context` first, synthesized fallback when None |
</phase_requirements>

---

## Standard Stack

### Core (all verified in codebase)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React 18 (JSX) | 18.x [VERIFIED: package.json] | SPA frontend — state, rendering, events | Established in v2.0 |
| Vite + Vitest | 4.x/4.1.8 [VERIFIED: npm test output] | Frontend build and test runner | Established in v2.0 |
| FastAPI | (installed) [VERIFIED: backend exists] | Python REST API for WD CRUD | Established in v2.0 |
| Pydantic v2 | 2.x [VERIFIED: model_config, ConfigDict usage] | WorkDescription and WDPatchRequest model validation | Established in v2.0 |
| docxtpl | (installed) [VERIFIED: export_service.py] | Jinja2-templated DOCX rendering | Established in Phase 25 |
| python-docx | (installed) [VERIFIED: test_export.py] | Reading back rendered DOCX in tests | Established in Phase 25 |
| SQLite | (system) | WD persistence via work_descriptions.data JSON column | Established in v2.0 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | 0.24.0 [VERIFIED: test session output] | Async test runner for backend coroutines | All backend test files |
| @testing-library/react | (installed) [VERIFIED: conversation.test.jsx] | Render + fireEvent for frontend component tests | All frontend unit tests |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `org_context` typed root field on WorkDescription | Storing in `record` dict blob | Typed field is required: export pipeline and completeness audit read typed fields directly; record blob is freeform and unreliable per STATE.md locked decision |
| 4-part step assembled client-side in step.apply | Server-side assembly endpoint | Client-side is consistent with existing multi-field steps (og_level_questions pattern); no new API route needed |

---

## Architecture Patterns

### System Architecture Diagram

```
[STEPS array (data.jsx)]
    |
    | new step: id='org_context', input.type='org_context_input'
    | phase: 3 (before client_service_results)
    |
    v
[OrgContextInput component (components.jsx)]
    | 4 sub-questions → assembled string → onChange(assembled)
    |
    v
[app.jsx commit()]
    | step.apply(record, draft) → { org_context: assembled_string }
    | → record.org_context persisted to localStorage
    | → PATCH /api/wd/{id} with { org_context: assembled_string }
    |
    +---> [Backend: PATCH handler (wd.py)]
    |         WDPatchRequest.org_context → wd.org_context = value
    |         SQLite: UPDATE work_descriptions SET data = wd.model_dump_json()
    |
    +---> [DocumentPane (document.jsx)]
              Sec "Organizational Context" renders record.org_context
              Sec "Client Service Results" renders record.client_service_results
              (both above Key Responsibilities)
    |
    v
[Export: POST /api/wd/{id}/export/docx]
    _build_wd_context(wd) → organizational_context_text:
        wd.org_context if org_context is not None
        else _build_organizational_context_text(wd) [synthesized fallback]
    → docxtpl render → {{ organizational_context_text }} in template line 15
```

### Recommended Project Structure

No new directories. All changes to existing files:

```
v2/backend/
  app/models/work_description.py    # +org_context: Optional[str] = None
  app/api/wd.py                     # WDPatchRequest +org_context: Optional[str]
  app/services/export_service.py    # _build_wd_context: read wd.org_context first
  tests/test_wd.py                  # +PATCH round-trip test for org_context
  tests/test_export.py              # +org_context populated test (RED Wave 0)

v2/frontend/src/
  data.jsx                          # +org_context step in STEPS; stepIndex fix
  components.jsx                    # +OrgContextInput; +StepInput dispatch; +answerValid
  document.jsx                      # +Sec org_context + Sec client_service_results
  app.jsx                           # +stepIndex resume fix; +FLASH entry for org_context
  conversation.test.jsx             # +tests for new step shape and resume behaviour
  document.test.jsx                 # +tests for org_context section rendering
```

### Pattern 1: STEPS Array — Step Object Shape

**What:** Every conversational step is an object in the `STEPS` array in `data.jsx`. The step has `id`, `phase`, `icon`, `q`, `helper`, `input` (with `type` key), `apply`, and `transcript`.

**When to use:** Add the org_context step here following the exact same shape as existing steps.

```jsx
// Source: v2/frontend/src/data.jsx (verified in codebase)
{ id: 'org_context', phase: 3, icon: I.org,
  q: 'Tell me about the organizational context for this position.',
  helper: 'Answer the questions below about where this position fits.',
  input: { type: 'org_context_input' },
  apply: (r, a) => ({ org_context: a }),       // a is the assembled string
  transcript: a => a ? a.slice(0, 60) + (a.length > 60 ? '...' : '') : 'Pending' }
```

**CRITICAL — insertion position:** The new step goes BEFORE `client_service_results` in STEPS. The current STEPS order at Phase 3 is: `og_level` → `client_service_results` → `duties` → `quals`. The new order after insertion: `og_level` → `org_context` → `client_service_results` → `duties` → `quals`.

### Pattern 2: Multi-Part Socratic Input Component (OgLevelQuestions precedent)

**What:** The closest existing pattern is `OgLevelQuestions` in `components.jsx` — a component that shows multiple sub-questions, accumulates local answers, then emits a single assembled value via `onChange`. The `og_level_questions` step uses this to display per-group criteria and emit `{ ...answers, suggested_level }`.

**When to use:** Build `OrgContextInput` following this exact pattern: local state for each sub-answer, assemble into single string on complete, call `onChange(assembled_string)`.

```jsx
// Source: v2/frontend/src/components.jsx (verified — OgLevelQuestions pattern)
function OrgContextInput({ value, onChange, cfg }) {
  const [parts, setParts] = useState({
    work_stream: '',
    org_placement: '',
    reporting_relationship: '',
    additional_context: '',
  });

  function handleChange(key, val) {
    const updated = { ...parts, [key]: val };
    setParts(updated);
    // Assemble all 4 parts into a single string
    const assembled = assembleOrgContext(updated);
    onChange(assembled);   // emits non-empty string → answerValid passes
  }
  // ... render 4 TextInput fields
}

function assembleOrgContext({ work_stream, org_placement, reporting_relationship, additional_context }) {
  // Combine into readable prose; non-empty parts only
  const lines = [work_stream, org_placement, reporting_relationship, additional_context]
    .filter(Boolean).join(' ');
  return lines;
}
```

**answerValid extension:**
```jsx
// Source: v2/frontend/src/components.jsx (verified — answerValid pattern)
if (t === 'org_context_input') return !!(value && typeof value === 'string' && value.trim());
```

**initialAnswer extension:**
```jsx
// Source: v2/frontend/src/components.jsx (verified — initialAnswer pattern)
if (c.type === 'org_context_input') return '';
```

### Pattern 3: WorkDescription + WDPatchRequest Co-Update Rule

**What:** Every new advisor-patchable field on `WorkDescription` requires a corresponding field on `WDPatchRequest` in the same git commit. `WDPatchRequest` has `model_config = ConfigDict(extra="ignore")` which silently drops unknown keys with HTTP 200 — this is the exact failure mode that caused UAT regressions in prior phases.

```python
# Source: v2/backend/app/api/wd.py (verified in codebase)
# WorkDescription (work_description.py) — add:
org_context: Optional[str] = None

# WDPatchRequest (wd.py) — add in SAME commit:
org_context: Optional[str] = None
```

**PATCH handler:** The existing `patch_wd` loop (`for field, val in body_dump.items(): setattr(wd, field, val)`) already handles any field that appears in both the request and the model. No special-case logic needed — adding the field to `WDPatchRequest` is sufficient.

### Pattern 4: stepIndex Regression Fix — Resume-by-Last-Answered

**What:** The current `stepIndex` initialises to `0` always. `record` IS persisted to localStorage; `answers` is NOT. When a new step is inserted into STEPS, any existing session's integer step index points to the wrong step.

**Fix (STATE.md locked decision):** Derive stepIndex on init from `record` using `STEPS.findLastIndex`:

```jsx
// Source: v2/frontend/src/app.jsx (current pattern + fix described in STATE.md)
// BEFORE:
const [stepIndex, setStepIndex] = useState(0);

// AFTER:
const [stepIndex, setStepIndex] = useState(() => {
  try {
    const raw = localStorage.getItem('jd-builder-v2-record');
    if (!raw) return 0;
    const rec = JSON.parse(raw);
    // Map step id → record key (mirrors apply() functions in STEPS)
    const STEP_RECORD_KEY = {
      title: 'title', branch: 'branch', reports: 'reports',
      reports_to_military: 'reports_to_military', supervises: 'supervises',
      summary: 'summary', qb_work_output_type: 'qb_work_output_type',
      qb_work_audience: 'qb_work_audience', qb_knowledge_specialization: 'qb_knowledge_specialization',
      qb_policy_interpretation: 'qb_policy_interpretation', qb_sector_gate: 'qb_sector_gate',
      qb_health_social_cluster: 'qb_health_social_cluster', qb_legal_cluster: 'qb_legal_cluster',
      qb_technical_cluster: 'qb_technical_cluster', qb_education_cluster: 'qb_education_cluster',
      qb_programme_admin_cluster: 'qb_programme_admin_cluster',
      noc_confirm: 'confirmed_noc', og_confirm: 'confirmed_og',
      og_level_questions: 'og_level_questions', og_level: 'og_level',
      org_context: 'org_context',                         // NEW Phase 26 field
      client_service_results: 'client_service_results',
      duties: 'duties', quals: 'quals',
    };
    const lastAnswered = STEPS.reduce((best, s, i) => {
      const key = STEP_RECORD_KEY[s.id];
      const answered = key && rec[key] !== undefined && rec[key] !== null;
      return answered ? i : best;
    }, -1);
    return lastAnswered < 0 ? 0 : Math.min(lastAnswered + 1, STEPS.length - 1);
  } catch { return 0; }
});
```

**Note on duties:** `rec.duties` is an array; `rec.duties !== null && rec.duties !== undefined` is always true for `[]`, so the check should be `rec.duties && rec.duties.length > 0` for the duties step.

**Critical:** This fix must land BEFORE the org_context step is added to STEPS. In the same plan or an earlier plan within Phase 26.

### Pattern 5: Document Preview Sec Rendering

**What:** Each document section in the right pane is a `<Sec>` component. The section pattern is identical across all existing sections.

**When to use:** Two new Sec entries needed in `document.jsx` DocumentPane — one for org_context (new) and one for client_service_results (capture existed since Phase 23 WG-03 but was never rendered in the preview).

```jsx
// Source: v2/frontend/src/document.jsx (verified — Sec pattern)
// INSERT before Key Responsibilities section (currently section 3):

// NEW: Org Context (ORG-02) — renders above Client Service Results
if (r.org_context) {
  n++;
  sections.push(
    <Sec
      key="org_ctx" n={String(n)} title="Organizational Context"
      src="Advisor-provided" fresh={isFresh('org_context')}
      editable={reviewing} onEdit={() => onEditStep('org_context')}
    >
      <p className="prose">{r.org_context}</p>
    </Sec>
  );
}

// NEW: Client Service Results (already in STEPS since Phase 23; preview was missing)
if (r.client_service_results) {
  n++;
  sections.push(
    <Sec
      key="csr" n={String(n)} title="Client Service Results"
      src="Advisor-provided" fresh={isFresh('client_service_results')}
      editable={reviewing} onEdit={() => onEditStep('client_service_results')}
    >
      <p className="prose">{r.client_service_results}</p>
    </Sec>
  );
}
```

**Document section order after Phase 26:**
1. Position Identification
2. Position Overview
3. Organizational Context (NEW)
4. Client Service Results (NEW preview rendering — data existed)
5. Key Responsibilities
6. Classification & Evaluation
7. DRF Linkage (conditional)
8. Essential Qualifications

**FLASH map extension needed** (app.jsx):
```jsx
// Add to FLASH dict:
org_context: 'org_context',           // flashes org_context Sec
client_service_results: 'csr',        // flashes client_service_results Sec
```
Wait — `FLASH` keys map step.id to the Sec `key`. Since the Sec keys are 'org_ctx' and 'csr', FLASH entries should be:
```jsx
org_context: 'org_ctx',
client_service_results: 'csr',
```

### Pattern 6: Export Service — org_context Field Priority

**What:** `_build_wd_context` in `export_service.py` currently uses `_build_organizational_context_text(wd)` for `organizational_context_text` — a synthesized fallback from branch/reports/summary. Phase 26 changes this to prefer the typed `wd.org_context` field.

```python
# Source: v2/backend/app/services/export_service.py (verified — current at line 392)
# BEFORE:
"organizational_context_text": _build_organizational_context_text(wd),

# AFTER:
"organizational_context_text": (
    wd.org_context
    if wd.org_context is not None
    else _build_organizational_context_text(wd)
),
```

**Template variable:** `{{ organizational_context_text }}` at paragraph 15 in `wd_accessible_template.docx` (heading: "Organizational context"). No template change needed — only the context builder changes.

### Anti-Patterns to Avoid

- **Adding org_context to WDPatchRequest in a separate commit from WorkDescription:** Silent drop via extra="ignore" will cause UAT failures — confirmed pattern from prior phases.
- **Persisting answers to localStorage:** Do NOT start persisting the `answers` object — it's large, not serialisable cleanly (has function-derived values), and the resume fix using `record` is the established solution.
- **Using record.org_context (dict blob) instead of wd.org_context (typed field):** The export pipeline and Phase 27 completeness audit both read the typed field. The record blob is for SPA display; the typed field is for structured data operations.
- **Inserting the new STEP before the stepIndex regression fix lands:** If stepIndex fix is not in place first, existing users with progress saved will land on the wrong step.
- **Rendering org_context section when `r.org_context` is falsy:** Use conditional rendering (`if (r.org_context)`) consistent with the DRF section pattern — ghost state is not needed here.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-part sub-question component | Custom state machine | Follow OgLevelQuestions pattern in components.jsx | The pattern of local state + assembled emit is already established and tested |
| DOCX Organizational Context section | New template variable | `{{ organizational_context_text }}` is already in wd_accessible_template.docx line 15 | Template was built in Phase 25 with all 7 Part 2 sections |
| Text assembly from 4 sub-answers | Dedicated API endpoint | Client-side `assembleOrgContext()` in OrgContextInput | No LLM or server-side logic needed; simple string concatenation |
| stepIndex persistence | Separate localStorage key for stepIndex | Derive from existing `jd-builder-v2-record` key via `findLastIndex` | record is already persisted; don't add new localStorage keys |

**Key insight:** The export template already has the variable binding. The backend model just needs the field. The frontend needs the step and the preview section. These are all additive changes to existing patterns.

---

## Runtime State Inventory

This is not a rename/refactor phase — omitted per instructions.

---

## Common Pitfalls

### Pitfall 1: WDPatchRequest Silent Field Drop
**What goes wrong:** Developer adds `org_context` to `WorkDescription` but forgets `WDPatchRequest`. PATCH returns HTTP 200. `extra="ignore"` silently drops the field. GET returns `org_context: null`. UAT fails.
**Why it happens:** `WDPatchRequest` has `model_config = ConfigDict(extra="ignore")` — this is intentional for forward compatibility but creates the silent drop pattern.
**How to avoid:** Co-update rule — both models in the same git commit. Write the PATCH round-trip test (PATCH with org_context → GET → assert non-None) BEFORE implementing.
**Warning signs:** PATCH returns 200 but GET shows `org_context: null`.

### Pitfall 2: stepIndex Points to Wrong Step After STEPS Insertion
**What goes wrong:** Existing user session has `stepIndex = 14` (og_level). After inserting org_context step at position 14, their session now starts at the NEW step instead of og_level. If they click Continue, they skip og_level entirely.
**Why it happens:** `stepIndex` initialises to 0 (not from localStorage) but `record` IS restored from localStorage. The integer is meaningless after STEPS changes size.
**How to avoid:** Implement the resume-by-last-answered fix BEFORE adding the new step. Use `STEPS.findLastIndex` over the record key map.
**Warning signs:** A test that checks "existing session with stepIndex in record resumes at the correct step" fails.

### Pitfall 3: client_service_results Still Not Rendering in Preview
**What goes wrong:** Advisor enters org_context in conversation. ORG-02 says org_context appears "above Client Service Results." But if client_service_results itself has no Sec in document.jsx, the requirement is technically satisfied with no CSR section at all — but Phase 27 success criteria will fail because it expects the preview structure to match the 7-element structure.
**Why it happens:** client_service_results step was added in Phase 23 (WG-03) as a data-capture question but the preview rendering was never added.
**How to avoid:** Add BOTH the org_context Sec AND the client_service_results Sec to document.jsx in Phase 26.
**Warning signs:** document.test.jsx for CSR section renders no CSR section in the preview.

### Pitfall 4: FLASH Map Miss for New Steps
**What goes wrong:** User commits org_context answer. No visual flash on the right pane. No UX confirmation that the preview updated.
**Why it happens:** `FLASH` map in app.jsx must map step.id → Sec key. Missing entry means no flash.
**How to avoid:** Add `org_context: 'org_ctx'` and `client_service_results: 'csr'` to FLASH when adding the new Sec keys to document.jsx.

### Pitfall 5: 4-Part OrgContextInput answerValid Gate
**What goes wrong:** Continue button stays disabled even when advisor fills all 4 fields. Or Continue enables when only 1 field is filled.
**Why it happens:** `answerValid` in components.jsx dispatches on `step.input.type`. New type `'org_context_input'` must be added to the dispatch.
**How to avoid:** Add to `answerValid`: `if (t === 'org_context_input') return !!(value && typeof value === 'string' && value.trim());`
**Design decision:** Whether to require all 4 sub-fields or allow partial. Per ORG-01: "responses are assembled" — implies all 4 are collected. But the step should allow the advisor to leave `additional_context` blank (it's optional context). Recommend: require at least 1 of the 4 fields non-empty; assemble only non-empty fields.

### Pitfall 6: org_context export reads wd.org_context but test fixture doesn't set it
**What goes wrong:** Export test for ACC-04 content-presence passes (no `{{` leak) but the org_context text isn't present in the output — because `_create_wd_ec` fixture doesn't set `org_context` on the WD.
**Why it happens:** Phase 25 fixtures don't know about org_context. Phase 26 must add a test that explicitly PATCH-sets org_context and verifies the DOCX output.
**How to avoid:** Write a dedicated ORG-03 test: create WD → PATCH org_context="Test org context" → export → assert "Test org context" in docx text.

---

## Code Examples

### Backend: WorkDescription field addition

```python
# Source: v2/backend/app/models/work_description.py (verified — existing pattern)
class WorkDescription(BaseModel):
    # ... existing fields ...
    sjd_source: Optional[dict] = None  # Phase 22
    org_context: Optional[str] = None  # Phase 26 — ORG-01
```

### Backend: WDPatchRequest field addition (same commit)

```python
# Source: v2/backend/app/api/wd.py (verified — WDPatchRequest)
class WDPatchRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # ... existing fields ...
    org_context: Optional[str] = None  # Phase 26 — ORG-01 co-update rule
```

### Backend: Export service org_context priority

```python
# Source: v2/backend/app/services/export_service.py (verified — _build_wd_context line 392)
# Replace:
"organizational_context_text": _build_organizational_context_text(wd),
# With:
"organizational_context_text": (
    wd.org_context
    if wd.org_context is not None
    else _build_organizational_context_text(wd)
),
```

### Backend: PATCH round-trip test

```python
# Source: v2/backend/tests/test_wd.py pattern (verified — existing test_patch_wd)
async def test_patch_org_context_round_trip(client):
    """ORG-01: PATCH org_context → GET → assert org_context non-None.
    Confirms WDPatchRequest co-update (extra='ignore' would drop unknown field silently)."""
    create_resp = await client.post("/api/wd", json={"record": {}, "answers": {}, "step_index": 0})
    wd_id = create_resp.json()["id"]

    patch_resp = await client.patch(f"/api/wd/{wd_id}", json={"org_context": "Test org context text"})
    assert patch_resp.status_code == 200

    get_resp = await client.get(f"/api/wd/{wd_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["org_context"] == "Test org context text"
```

### Frontend: OrgContextInput component sketch

```jsx
// Source: components.jsx OgLevelQuestions pattern (verified)
// New component — 4 textarea fields assembling into one string
function OrgContextInput({ value, onChange }) {
  const [parts, setParts] = React.useState(() => {
    // If editing a previously committed value, we can't split it back —
    // show value in the first field (work_stream) as the assembled text.
    // This is a simplification; a richer re-edit would require storing parts separately.
    return { work_stream: '', org_placement: '', reporting: '', additional: '' };
  });

  function handlePart(key, val) {
    const updated = { ...parts, [key]: val };
    setParts(updated);
    const assembled = [updated.work_stream, updated.org_placement, updated.reporting, updated.additional]
      .filter(s => s.trim()).join(' ');
    onChange(assembled);
  }

  return (
    <div className="org-context-input">
      <div className="org-context-input__field">
        <label>Work stream or program</label>
        <textarea className="tf" rows={2} value={parts.work_stream}
          placeholder="e.g. This position sits within the Strategic Policy program area…"
          onChange={e => handlePart('work_stream', e.target.value)} />
      </div>
      <div className="org-context-input__field">
        <label>Organizational placement</label>
        <textarea className="tf" rows={2} value={parts.org_placement}
          placeholder="e.g. Located within the ADM(Policy) group, Branch X…"
          onChange={e => handlePart('org_placement', e.target.value)} />
      </div>
      <div className="org-context-input__field">
        <label>Reporting relationship</label>
        <textarea className="tf" rows={2} value={parts.reporting}
          placeholder="e.g. Reports to the Director, Policy Development…"
          onChange={e => handlePart('reporting', e.target.value)} />
      </div>
      <div className="org-context-input__field">
        <label>Additional context (optional)</label>
        <textarea className="tf" rows={2} value={parts.additional}
          placeholder="Any other relevant context about the position's role in the organization…"
          onChange={e => handlePart('additional', e.target.value)} />
      </div>
    </div>
  );
}
```

### Frontend: StepInput dispatch extension

```jsx
// Source: v2/frontend/src/components.jsx (verified — StepInput function)
function StepInput(props) {
  const t = props.cfg.type;
  // ... existing dispatches ...
  if (t === 'org_context_input') return <OrgContextInput {...props} />;
  // ...
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TBS WD template | Accessible JD template (wd_accessible_template.docx) | Phase 25 | `{{ organizational_context_text }}` already exists at heading "Organizational context" |
| org_context derived from branch/reports/summary synthesized text | org_context as typed field on WorkDescription | Phase 26 (this phase) | Completeness audit in Phase 27 must read typed field, not synthesized text |
| stepIndex starts at 0 on refresh | stepIndex derived from record key map | Phase 26 (this phase) | Existing sessions survive STEPS growth |
| client_service_results captured but not rendered in preview | Both org_context and CSR rendered in preview | Phase 26 (this phase) | Preview matches document structure |

**Deprecated/outdated:**
- `_build_organizational_context_text(wd)` as primary source: becomes the fallback (not removed; still used when `wd.org_context is None`)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | All 4 org_context sub-questions are optional except at least one must be non-empty | Pattern 5, answerValid | If requirement is "all 4 required", the answerValid check needs to verify all 4 parts filled |
| A2 | OrgContextInput should assemble all parts into a single prose string (not a structured dict) | Pattern 2 | If export or Phase 27 audit needs to read individual sub-parts, the field type must be a dict or the step must store sub-answers in record separately |
| A3 | The `client_service_results` Sec was intentionally deferred from Phase 23 (not a bug) | Pitfall 3 | If it was accidentally omitted in Phase 23, the fix should have been in Phase 23 — but it's being added here anyway, so risk is low |
| A4 | The STEP record key map for resume-by-last-answered covers all current STEPS accurately | Pattern 4 | If a step's apply function writes to a different key than expected, that step won't be detected as answered and the resume position will be off by 1 |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.
(Table is not empty — 4 assumptions flagged for planner attention.)

---

## Open Questions

1. **Should `additional_context` be optional in answerValid?**
   - What we know: ORG-01 says "4-part Socratic step (work stream, organizational placement, reporting relationship, additional context)"
   - What's unclear: Whether all 4 are required or "additional context" is optional
   - Recommendation: Treat additional_context as optional; require at least 1 of the 4 non-empty. This matches the Writing Guide philosophy of non-blocking, advisor-driven input.

2. **Should OrgContextInput store sub-parts separately so edit mode can pre-fill each field?**
   - What we know: The step `apply: (r, a) => ({ org_context: a })` stores the assembled string, not the parts. On edit, the pre-fill would be `answers['org_context']` which is the assembled string.
   - What's unclear: Whether the advisor needs to edit individual sub-fields or can re-answer all fields
   - Recommendation: For Phase 26, store as assembled string. Re-edit shows the assembled string in the work_stream field (or a single textarea for edit mode). A richer sub-part re-edit can be Phase 27+ enhancement.

3. **Does FLASH for `org_context` section need to be added to SECTION_NAMES in app.jsx?**
   - What we know: `SECTION_NAMES` in app.jsx maps section keys to display names for amendment toasts. Currently: `{ id, ov, du, cls, q, drf }`.
   - What's unclear: Whether amendment panels should be added to the new sections in Phase 26 or deferred.
   - Recommendation: Add amendment panel support to org_context Sec in Phase 26 (consistent with existing sections). Add `org_context: 'org_ctx'` to both FLASH and SECTION_NAMES.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10 | Backend tests | ✓ [VERIFIED: test session output] | 3.10.12 | — |
| pytest + pytest-asyncio | Backend tests | ✓ [VERIFIED: 150 tests collected] | 8.3.4 / 0.24.0 | — |
| Vitest | Frontend tests | ✓ [VERIFIED: 60 passed] | 4.1.8 | — |
| python-docx | DOCX content-presence tests | ✓ [VERIFIED: test_export.py import] | (installed) | — |
| docxtpl | DOCX export | ✓ [VERIFIED: export_service.py] | (installed) | — |
| wd_accessible_template.docx | Export | ✓ [VERIFIED: 37,872 bytes, all 7 Part 2 sections] | Phase 25 build | — |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (backend) | pytest 8.3.4 + pytest-asyncio 0.24.0 |
| Config file (backend) | `v2/backend/pyproject.toml` |
| Quick run command | `cd v2/backend && python -m pytest tests/test_wd.py tests/test_export.py -x -q` |
| Full suite command | `cd v2/backend && python -m pytest -x -q` |
| Framework (frontend) | Vitest 4.1.8 |
| Config file (frontend) | `v2/frontend/vitest.config.js` |
| Quick run command | `cd v2/frontend && npm test` |
| Full suite command | `cd v2/frontend && npm test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ORG-01 | PATCH org_context → GET → assert non-None (WDPatchRequest co-update) | integration | `pytest tests/test_wd.py::test_patch_org_context_round_trip -x` | ❌ Wave 0 |
| ORG-01 | STEPS contains org_context step with phase 3 | unit | `npm test` (conversation.test.jsx) | ❌ Wave 0 |
| ORG-01 | OrgContextInput assembles 4 sub-fields into non-empty string | unit | `npm test` (conversation.test.jsx) | ❌ Wave 0 |
| ORG-01 | stepIndex resume: existing session with record keys resumes at correct step | unit | `npm test` (app.test.jsx) | ❌ Wave 0 |
| ORG-02 | document.jsx renders org_context Sec when r.org_context is set | unit | `npm test` (document.test.jsx) | ❌ Wave 0 |
| ORG-02 | document.jsx renders client_service_results Sec when r.client_service_results is set | unit | `npm test` (document.test.jsx) | ❌ Wave 0 |
| ORG-03 | Export DOCX with org_context filled → "organizational_context_text" is the typed value | integration | `pytest tests/test_export.py::test_org_context_in_export -x` | ❌ Wave 0 |
| ORG-03 | Export DOCX with org_context None → uses synthesized fallback (branch/reports/summary) | integration | `pytest tests/test_export.py::test_org_context_fallback_in_export -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd v2/backend && python -m pytest tests/test_wd.py tests/test_export.py -x -q && cd ../frontend && npm test`
- **Per wave merge:** `cd v2/backend && python -m pytest -x -q && cd ../frontend && npm test`
- **Phase gate:** Full suite green (150+ backend, 60+ frontend) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `v2/backend/tests/test_wd.py` — add `test_patch_org_context_round_trip` (ORG-01 RED)
- [ ] `v2/backend/tests/test_export.py` — add `test_org_context_in_export` and `test_org_context_fallback_in_export` (ORG-03 RED)
- [ ] `v2/frontend/src/conversation.test.jsx` — add STEPS org_context shape test + OrgContextInput assembly test (ORG-01 RED)
- [ ] `v2/frontend/src/document.test.jsx` — add org_context Sec and CSR Sec rendering tests (ORG-02 RED)
- [ ] `v2/frontend/src/app.test.jsx` — add stepIndex resume test (regression fix RED)

No framework install needed — test infrastructure is complete.

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user local app |
| V3 Session Management | no | localStorage; no server sessions |
| V4 Access Control | no | Single-user local app |
| V5 Input Validation | yes | `org_context: Optional[str]` — Pydantic validates type; no max length enforcement currently |
| V6 Cryptography | no | No secrets involved |

**Known threat patterns:**

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Oversized org_context string (DoS) | Denial of Service | Add `max_length=4000` to `Optional[str]` on WDPatchRequest consistent with how amendments.py limits comment size (`max_comment_len = 5000`) |
| XSS via org_context in document preview | Tampering | React renders `{r.org_context}` as text node, not innerHTML — XSS safe by default |

---

## Sources

### Primary (HIGH confidence)

- `v2/frontend/src/data.jsx` — STEPS array (20 steps), PHASES, isStepVisible, accumulateSignals — fully read
- `v2/frontend/src/app.jsx` — App state, commit(), localStorage patterns, FLASH map — fully read
- `v2/frontend/src/document.jsx` — DocumentPane, Sec component, section ordering — fully read
- `v2/frontend/src/components.jsx` — OgLevelQuestions, StepInput, answerValid, initialAnswer — fully read
- `v2/backend/app/models/work_description.py` — WorkDescription model, all fields — fully read
- `v2/backend/app/api/wd.py` — WDPatchRequest, patch_wd handler, co-update pattern — fully read
- `v2/backend/app/services/export_service.py` — _build_wd_context, _build_organizational_context_text, _ADVISOR_PLACEHOLDER — verified lines 252-413
- `v2/backend/app/templates/wd_accessible_template.docx` — all 42 paragraphs verified via python-docx; `{{ organizational_context_text }}` at line 15
- `.planning/STATE.md` — locked decisions for v4.0 including stepIndex fix, co-update rule, org_context as typed field — fully read
- `.planning/REQUIREMENTS.md` — ORG-01, ORG-02, ORG-03 verbatim — fully read
- `v2/backend/tests/test_export.py` — ACCESSIBLE_PART2_HEADINGS, _create_wd_ec fixture, ACC-04 content-presence pattern — verified
- `v2/backend/tests/test_wd.py` — existing test patterns for PATCH round-trip — verified

### Secondary (MEDIUM confidence)

- None needed — all findings sourced from codebase directly.

### Tertiary (LOW confidence)

- None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from existing codebase, all patterns established
- Architecture: HIGH — all components exist; Phase 26 is additive
- Pitfalls: HIGH — WDPatchRequest silent drop and stepIndex regression are explicitly documented in STATE.md as known risks

**Research date:** 2026-06-19
**Valid until:** 2026-06-30 (stable codebase; no external dependencies)
