# Phase 26: Org Context Conversational Step - Pattern Map

**Mapped:** 2026-06-23
**Files analyzed:** 10 (7 modified + 3 test files)
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `v2/backend/app/models/work_description.py` | model | CRUD | self (additive field) | exact |
| `v2/backend/app/api/wd.py` | controller | request-response | self (WDPatchRequest additive field) | exact |
| `v2/backend/app/services/export_service.py` | service | transform | self (`_build_wd_context` modification) | exact |
| `v2/backend/tests/test_wd.py` | test | request-response | `tests/test_wd.py` existing `test_patch_wd_updates_step_index` | exact |
| `v2/backend/tests/test_export.py` | test | transform | `tests/test_export.py` existing `_create_wd_ec` + `test_accessible_content_presence` | exact |
| `v2/frontend/src/data.jsx` | config/data | event-driven | `data.jsx` `client_service_results` step (lines 657-662) | exact |
| `v2/frontend/src/components.jsx` | component | event-driven | `OgLevelQuestions` (lines 501-597), `StepInput` (713-725), `answerValid`/`initialAnswer` (729-751) | exact |
| `v2/frontend/src/document.jsx` | component | request-response | `Sec` component (lines 99-161), existing section rendering pattern | exact |
| `v2/frontend/src/app.jsx` | store/controller | event-driven | `FLASH` dict (lines 10-25), `stepIndex` useState (line 79), `SECTION_NAMES` (lines 604-611) | exact |
| `v2/frontend/src/conversation.test.jsx` | test | event-driven | existing conversation test patterns | role-match |

---

## Pattern Assignments

### `v2/backend/app/models/work_description.py` (model, CRUD)

**Analog:** self — additive `Optional[str]` field following the `sjd_source` precedent at line 55.

**Field addition pattern** (lines 53-61, verbatim current state):
```python
# Source: v2/backend/app/models/work_description.py lines 53-61
confirmed_sub_group: Optional[str] = None  # Phase 21: NU/SW/ED sub-group
og_level: Optional[int] = Field(default=None, ge=1)
sjd_source: Optional[dict] = None  # Phase 22: {sjd_number, title, og_code, og_level}
reports_to_military: Optional[bool] = None
jes_scores: list[dict] = Field(default_factory=list)
jes_total_points: Optional[int] = None
schema_version: int = 1
created_at: datetime
last_modified: datetime

# ADD Phase 26 — ORG-01 (same commit as WDPatchRequest):
org_context: Optional[str] = None
```

**Import pattern** (lines 20-29 — already sufficient, no new imports needed):
```python
from __future__ import annotations
from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, ConfigDict, Field
```

**Co-update rule:** `org_context` MUST be added to both `WorkDescription` AND `WDPatchRequest` in the same git commit. The `extra="ignore"` config on `WDPatchRequest` silently drops unknown keys with HTTP 200 — the confirmed failure mode from prior phases.

---

### `v2/backend/app/api/wd.py` (controller, request-response)

**Analog:** self — additive field on `WDPatchRequest` (lines 123-148).

**WDPatchRequest field addition** (current block lines 123-148, showing where to insert):
```python
# Source: v2/backend/app/api/wd.py lines 123-148
class WDPatchRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")   # <- silent drop on unknown fields

    record: Optional[dict] = None
    answers: Optional[dict] = None
    step_index: Optional[int] = None
    draft: Optional[dict] = None
    reviewing: Optional[bool] = None
    editing_return: Optional[bool] = None
    confirmed_noc: Optional[Union[str, dict]] = None
    confirmed_og: Optional[Union[str, dict]] = None
    confirmed_sub_group: Optional[str] = None
    og_level: Optional[int] = None
    reports_to_military: Optional[bool] = None
    jes_scores: Optional[list[dict]] = None
    jes_total_points: Optional[int] = None
    duties: Optional[list[dict]] = None
    qualification: Optional[dict] = None
    # ADD Phase 26 — ORG-01 co-update (same commit as WorkDescription):
    org_context: Optional[str] = None
```

**PATCH loop pattern** (lines 227-228 — no change needed; loop handles new field automatically):
```python
# Source: v2/backend/app/api/wd.py lines 227-228
for field, val in body_dump.items():
    setattr(wd, field, val)
```
No special-case handling needed — the generic setattr loop picks up `org_context` once the field exists in both models.

---

### `v2/backend/app/services/export_service.py` (service, transform)

**Analog:** self — `_build_wd_context` function, line 392.

**Current pattern** (line 392, to be replaced):
```python
# Source: v2/backend/app/services/export_service.py line 392 — BEFORE
"organizational_context_text": _build_organizational_context_text(wd),
```

**Replacement pattern** (Phase 26 change):
```python
# Source: v2/backend/app/services/export_service.py line 392 — AFTER
"organizational_context_text": (
    wd.org_context
    if wd.org_context is not None
    else _build_organizational_context_text(wd)
),
```

**Fallback function** (lines 252-278, unchanged — becomes fallback only):
```python
# Source: v2/backend/app/services/export_service.py lines 252-278
def _build_organizational_context_text(wd: WorkDescription) -> str:
    """Compose the organizational-context paragraph from record fields.
    Phase 26: This becomes the fallback when wd.org_context is None."""
    record = wd.record or {}
    branch = (record.get("branch") or "").strip()
    supervisor = (record.get("reports") or "").strip()
    title = (record.get("title") or "").strip() or "incumbent"
    summary = (record.get("summary") or "performs duties as assigned").strip()
    summary = summary[0].lower() + summary[1:] if summary else "performs duties as assigned"
    if branch and supervisor:
        return (f"Located within {branch}, and reporting to the {supervisor}, "
                f"the {title} {summary}.")
    if branch:
        return f"Located within {branch}, the {title} {summary}."
    if supervisor:
        return f"Reporting to the {supervisor}, the {title} {summary}."
    return f"The {title} {summary}."
```

---

### `v2/backend/tests/test_wd.py` (test, request-response)

**Analog:** `test_patch_wd_updates_step_index` (lines 40-50) — same POST→PATCH→GET pattern.

**Existing PATCH round-trip test pattern** (lines 40-50):
```python
# Source: v2/backend/tests/test_wd.py lines 40-50
async def test_patch_wd_updates_step_index(client):
    """PATCH /api/wd/{id} must persist updated fields."""
    create_resp = await client.post(
        "/api/wd",
        json={"record": {}, "answers": {}, "step_index": 0},
    )
    wd_id = create_resp.json()["id"]

    patch_resp = await client.patch(f"/api/wd/{wd_id}", json={"step_index": 3})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["step_index"] == 3
```

**New test to add** (ORG-01 RED — copy pattern exactly):
```python
# New test for v2/backend/tests/test_wd.py — ORG-01
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

---

### `v2/backend/tests/test_export.py` (test, transform)

**Analog:** `_create_wd_ec` fixture (lines 94-120) and `test_accessible_content_presence` (lines 547-582).

**Fixture pattern for creating a seeded WD** (lines 94-120):
```python
# Source: v2/backend/tests/test_export.py lines 94-120
async def _create_wd_ec(client) -> str:
    wd_id = await _create_wd(client)
    resp = await client.patch(
        f"/api/wd/{wd_id}",
        json={
            "confirmed_og": {"og_code": "EC", "og_name": "Economics and Social Science Services"},
            "og_level": 4,
            "jes_total_points": 43,
            "jes_scores": [...],
            "duties": [_DUTY_SEED],
            "record": _RECORD_SEED,
            "qualification": _QUAL_SEED,
        },
    )
    assert resp.status_code == 200
    return wd_id
```

**New tests to add** (ORG-03 RED — two tests):
```python
# Test 1: org_context typed field appears in DOCX output
async def test_org_context_in_export(client, env_with_db):
    """ORG-03: When org_context is set, the typed value appears in the DOCX."""
    wd_id = await _create_wd_ec(client)
    # PATCH the org_context field
    patch_resp = await client.patch(
        f"/api/wd/{wd_id}", json={"org_context": "Test org context text for export"}
    )
    assert patch_resp.status_code == 200

    export_resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert export_resp.status_code == 200
    doc = Document(BytesIO(export_resp.content))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Test org context text for export" in full_text

# Test 2: when org_context is None, synthesized fallback is used
async def test_org_context_fallback_in_export(client, env_with_db):
    """ORG-03: When org_context is None, synthesized fallback (branch/reports/summary) is used."""
    wd_id = await _create_wd_ec(client)
    # _create_wd_ec does NOT set org_context — uses _RECORD_SEED with branch/reports/summary
    export_resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert export_resp.status_code == 200
    doc = Document(BytesIO(export_resp.content))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    # The fallback synthesizes from record.branch / record.reports / record.summary
    # Assert the section heading is present (no {{template leak}})
    assert "{{" not in full_text
    assert "organizational_context_text" not in full_text
```

---

### `v2/frontend/src/data.jsx` (config/data, event-driven)

**Analog:** `client_service_results` step (lines 657-662) and `og_level_questions` step (lines 643-648) — same step object shape.

**Closest existing step shape** (lines 657-662):
```jsx
// Source: v2/frontend/src/data.jsx lines 657-662
{ id: 'client_service_results', phase: 3, icon: I.flag,
  q: 'What client service results does this position deliver?',
  helper: 'Describe the outcomes this role produces for clients or stakeholders.',
  input: { type: 'textarea', placeholder: 'e.g. Clients receive timely, accurate advice on...' },
  apply: (r, a) => ({ client_service_results: a }),
  transcript: a => a ? a.slice(0, 60) + (a.length > 60 ? '...' : '') : 'Pending' },
```

**New step to add** (BEFORE `client_service_results` in STEPS array — currently at index 17):
```jsx
// INSERT before client_service_results in v2/frontend/src/data.jsx
{ id: 'org_context', phase: 3, icon: I.org,
  q: 'Tell me about the organizational context for this position.',
  helper: 'Answer the questions below about where this position fits.',
  input: { type: 'org_context_input' },
  apply: (r, a) => ({ org_context: a }),          // a is the assembled string
  transcript: a => a ? a.slice(0, 60) + (a.length > 60 ? '...' : '') : 'Pending' },
```

**STEPS insertion position:** Phase 3 currently starts with `client_service_results` at array index 17 (after `og_level`). New step goes at index 17; `client_service_results` shifts to 18.

**Export line** (line 708 — `I` is already exported, no new export needed):
```jsx
// Source: v2/frontend/src/data.jsx line 708
export { I, STEPS, PHASES, OG_LEVELS, ... };
// I.org already exists (line 13) — no new icon needed for org_context step
```

---

### `v2/frontend/src/components.jsx` (component, event-driven)

**Analog:** `OgLevelQuestions` (lines 501-597) for the multi-part input component pattern; `StepInput` (lines 713-725) for dispatcher; `answerValid`/`initialAnswer` (lines 729-751) for validation.

**OgLevelQuestions multi-part local-state + emit pattern** (lines 501-530, key structure):
```jsx
// Source: v2/frontend/src/components.jsx lines 501-530
function OgLevelQuestions({ value, onChange, cfg }) {
  const [localAnswers, setLocalAnswers] = useState({});
  // ... fetch-based approach for this component

  function handleAnswer(questionId, optionId) {
    const updated = { ...localAnswers, [questionId]: optionId };
    setLocalAnswers(updated);
    // ... emit assembled value via onChange
    onChange({ ...updated, suggested_level: null });
  }
  // ... render sub-questions
}
```

**New OrgContextInput component to add** (follows same local state + assembled emit pattern):
```jsx
// ADD to v2/frontend/src/components.jsx — before StepInput
function OrgContextInput({ value, onChange }) {
  const [parts, setParts] = useState({
    work_stream: '', org_placement: '', reporting: '', additional: '',
  });

  function handlePart(key, val) {
    const updated = { ...parts, [key]: val };
    setParts(updated);
    const assembled = [updated.work_stream, updated.org_placement,
                       updated.reporting, updated.additional]
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

**StepInput dispatcher** (lines 713-726, showing where to add):
```jsx
// Source: v2/frontend/src/components.jsx lines 713-726
function StepInput(props) {
  const t = props.cfg.type;
  if (t === 'text' || t === 'textarea') return <TextInput {...props} />;
  if (t === 'choices') return <ChoiceList {...props} />;
  if (t === 'scale') return <ScaleInput {...props} />;
  if (t === 'duties') return <DutyBuilder {...props} />;
  if (t === 'drf') return <DrfPicker {...props} />;
  if (t === 'quals') return <QualEditor {...props} og_code={props.record?.confirmed_og?.og_code} />;
  if (t === 'noc_confirm') return <NocConfirmList {...props} />;
  if (t === 'og_confirm') return <OgConfirmList {...props} />;
  if (t === 'og_level_questions') return <OgLevelQuestions {...props} />;
  if (t === 'og_level') return <OgLevelPicker {...props} />;
  // ADD Phase 26:
  if (t === 'org_context_input') return <OrgContextInput {...props} />;
  return null;
}
```

**answerValid extension** (lines 736-751, showing where to insert):
```jsx
// Source: v2/frontend/src/components.jsx lines 736-751
function answerValid(step, value) {
  const t = step.input.type;
  if (t === 'text' || t === 'textarea') return !!(value && value.trim());
  if (t === 'duties') return Array.isArray(value) && value.length > 0;
  if (t === 'quals') return !!(value && value.education && value.experience);
  if (t === 'noc_confirm') return typeof value === 'string' && value.length > 0;
  if (t === 'og_confirm') return value !== null && value !== undefined && !!value.og_code;
  if (t === 'og_level_questions') {
    return !!value && typeof value === 'object' && Object.keys(value).length > 0;
  }
  if (t === 'og_level') return typeof value === 'number' && value >= 1;
  // ADD Phase 26: at least one sub-field non-empty → assembled string is non-empty
  if (t === 'org_context_input') return !!(value && typeof value === 'string' && value.trim());
  return !!value;
}
```

**initialAnswer extension** (lines 729-735, showing where to insert):
```jsx
// Source: v2/frontend/src/components.jsx lines 729-735
function initialAnswer(step, record) {
  const c = step.input;
  if (c.type === 'text' || c.type === 'textarea') return c.preset || '';
  if (c.type === 'duties') return [];
  if (c.type === 'quals') return getQualDefault(record?.confirmed_og?.og_code);
  // ADD Phase 26:
  if (c.type === 'org_context_input') return '';
  return null;
}
```

**Export line** (line 753 — add `OrgContextInput`):
```jsx
// Source: v2/frontend/src/components.jsx line 753
export { Icon, Check, StepInput, initialAnswer, answerValid, OgLevelQuestions, OgLevelPicker };
// Phase 26: OrgContextInput does not need to be exported (used only inside StepInput dispatch)
```

---

### `v2/frontend/src/document.jsx` (component, request-response)

**Analog:** `Sec` component (lines 99-161) and existing conditional section rendering pattern in `DocumentPane`.

**Sec component signature** (lines 99-161):
```jsx
// Source: v2/frontend/src/document.jsx lines 99-161
function Sec({ n, title, src, ghost, fresh, editable, onEdit, children,
               sectionKey, amendmentNote, amendmentPanel, onAmendToggle, onAmendSave, reviewing }) {
  // ... renders section wrapper with optional amendment panel
  return (
    <section className={`sec${ghost ? ' is-ghost' : ''}${editable ? ' sec--editable' : ''}`} ...>
      <div className="sec__h">
        {n && <span className="n">{n}</span>}
        <span>{title}</span>
        {src && <span className="src">...</span>}
      </div>
      <div className={fresh ? 'fresh' : ''}>{children}</div>
    </section>
  );
}
```

**Two new Sec entries to add** (both before existing Key Responsibilities section):
```jsx
// ADD to DocumentPane in v2/frontend/src/document.jsx — before Key Responsibilities

// NEW: Org Context (ORG-02)
if (r.org_context) {
  n++;
  sections.push(
    <Sec
      key="org_ctx" n={String(n)} title="Organizational Context"
      src="Advisor-provided" fresh={isFresh('org_context')}
      editable={reviewing} onEdit={() => onEditStep('org_context')}
      sectionKey="org_ctx"
      amendmentNote={amendmentNotes?.org_ctx}
      amendmentPanel={amendmentPanels?.org_ctx}
      onAmendToggle={onAmendToggle} onAmendSave={onAmendSave} reviewing={reviewing}
    >
      <p className="prose">{r.org_context}</p>
    </Sec>
  );
}

// NEW: Client Service Results (data existed since Phase 23; preview was missing)
if (r.client_service_results) {
  n++;
  sections.push(
    <Sec
      key="csr" n={String(n)} title="Client Service Results"
      src="Advisor-provided" fresh={isFresh('client_service_results')}
      editable={reviewing} onEdit={() => onEditStep('client_service_results')}
      sectionKey="csr"
      amendmentNote={amendmentNotes?.csr}
      amendmentPanel={amendmentPanels?.csr}
      onAmendToggle={onAmendToggle} onAmendSave={onAmendSave} reviewing={reviewing}
    >
      <p className="prose">{r.client_service_results}</p>
    </Sec>
  );
}
```

**Section order after Phase 26:**
1. Position Identification (key: `id`)
2. Position Overview (key: `ov` / `summary`)
3. Organizational Context (key: `org_ctx`) — NEW
4. Client Service Results (key: `csr`) — NEW preview rendering
5. Key Responsibilities (key: `du`)
6. Classification & Evaluation (key: `cls`)
7. DRF Linkage (key: `drf`, conditional)
8. Essential Qualifications (key: `q`)

---

### `v2/frontend/src/app.jsx` (store/controller, event-driven)

**Analog:** self — three separate modifications: `FLASH` map (lines 10-25), `stepIndex` useState (line 79), `SECTION_NAMES` (lines 604-611).

**FLASH map** (lines 10-25, showing current state and additions):
```jsx
// Source: v2/frontend/src/app.jsx lines 10-25
const FLASH = {
  title: 'title', branch: 'title', reports: 'title',
  reports_to_military: 'title',
  supervises: 'summary',
  summary: 'summary',
  qb_work_output_type: 'level', qb_work_audience: 'level',
  qb_knowledge_specialization: 'level', qb_policy_interpretation: 'level',
  qb_sector_gate: 'level', qb_health_social_cluster: 'level',
  qb_legal_cluster: 'level', qb_technical_cluster: 'level',
  qb_education_cluster: 'level', qb_programme_admin_cluster: 'level',
  noc_confirm: 'level',
  og_confirm: 'level',
  og_level_questions: 'level',
  og_level: 'level',
  duties: 'duties', quals: 'quals',
  // ADD Phase 26 — maps step.id to Sec key prop:
  org_context: 'org_ctx',
  client_service_results: 'csr',
};
```

**stepIndex useState** (line 79, to be replaced with resume-by-last-answered):
```jsx
// Source: v2/frontend/src/app.jsx line 79 — CURRENT (to replace)
const [stepIndex, setStepIndex] = useState(0);

// REPLACE WITH Phase 26 resume fix:
const [stepIndex, setStepIndex] = useState(() => {
  try {
    const raw = localStorage.getItem('jd-builder-v2-record');
    if (!raw) return 0;
    const rec = JSON.parse(raw);
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
      org_context: 'org_context',              // Phase 26 new field
      client_service_results: 'client_service_results',
      duties: 'duties', quals: 'quals',
    };
    const lastAnswered = STEPS.reduce((best, s, i) => {
      const key = STEP_RECORD_KEY[s.id];
      // Special case: duties is array — empty array counts as unanswered
      if (key === 'duties') {
        const answered = rec[key] && rec[key].length > 0;
        return answered ? i : best;
      }
      const answered = key && rec[key] !== undefined && rec[key] !== null;
      return answered ? i : best;
    }, -1);
    return lastAnswered < 0 ? 0 : Math.min(lastAnswered + 1, STEPS.length - 1);
  } catch { return 0; }
});
```

**SECTION_NAMES map** (lines 604-611, showing current state and additions):
```jsx
// Source: v2/frontend/src/app.jsx lines 604-611
const SECTION_NAMES = {
  id: 'Position Identification',
  ov: 'Position Overview',
  du: 'Key Responsibilities',
  cls: 'Classification & Evaluation',
  q: 'Essential Qualifications',
  drf: 'Defence Results Linkage',
  // ADD Phase 26 — new sections with amendment panel support:
  org_ctx: 'Organizational Context',
  csr: 'Client Service Results',
};
```

**record localStorage restore** (lines 69-77 — unchanged; already persists `org_context` because it persists the whole record dict):
```jsx
// Source: v2/frontend/src/app.jsx lines 70-77
const [record, setRecord] = useState(() => {
  try {
    const raw = localStorage.getItem('jd-builder-v2-record');
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
});
```

---

### `v2/frontend/src/conversation.test.jsx` and `document.test.jsx` and `app.test.jsx` (tests)

**Analog:** existing test patterns in `conversation.test.jsx` (renders with `@testing-library/react` + `fireEvent`).

**Frontend test framework pattern** (from existing test setup):
```jsx
// Pattern for all new frontend tests (Wave 0 RED tests):

// conversation.test.jsx additions:
// 1. STEPS contains org_context step with phase 3 and type 'org_context_input'
// 2. OrgContextInput assembles 4 sub-fields into non-empty string

// document.test.jsx additions:
// 3. DocumentPane renders org_context Sec when record.org_context is set
// 4. DocumentPane renders csr Sec when record.client_service_results is set

// app.test.jsx additions:
// 5. stepIndex resume: existing session with last answered = og_level resumes at next step
```

---

## Shared Patterns

### Pydantic Optional Field
**Source:** `v2/backend/app/models/work_description.py` lines 53-61; `v2/backend/app/api/wd.py` lines 123-148
**Apply to:** `work_description.py` AND `wd.py` (same commit — co-update rule)
```python
org_context: Optional[str] = None
```

### PATCH Round-Trip Test
**Source:** `v2/backend/tests/test_wd.py` lines 40-50
**Apply to:** `test_wd.py` new `test_patch_org_context_round_trip`
Pattern: POST create → PATCH field → GET → assert field equals patched value.

### Conditional Sec Rendering
**Source:** `v2/frontend/src/document.jsx` existing DRF conditional section
**Apply to:** Both new `org_context` and `client_service_results` Sec entries
Pattern: `if (r.field_name) { n++; sections.push(<Sec key="..." n={String(n)} ...>) }`

### Step Object Shape
**Source:** `v2/frontend/src/data.jsx` lines 657-662 (`client_service_results` step)
**Apply to:** New `org_context` step in STEPS array
Pattern: `{ id, phase, icon, q, helper, input: { type }, apply: (r,a) => ({...}), transcript: a => ... }`

### Local State + Assembled Emit
**Source:** `v2/frontend/src/components.jsx` lines 501-597 (`OgLevelQuestions`)
**Apply to:** New `OrgContextInput` component
Pattern: `useState({})` for sub-parts → on any change, assemble and `onChange(assembled)`.

---

## No Analog Found

All files have close analogs in the codebase. No files require falling back to RESEARCH.md-only patterns.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | — |

---

## Critical Implementation Order

The RESEARCH.md mandates this sequence within Phase 26 to prevent regressions:

1. **stepIndex resume fix** (`app.jsx` useState change) — FIRST. Must land before STEPS is modified.
2. **WorkDescription + WDPatchRequest co-update** (`work_description.py` + `wd.py`) — same git commit.
3. **PATCH round-trip test** (`test_wd.py`) — RED before step 2, GREEN after.
4. **org_context STEP + OrgContextInput + StepInput dispatch** (`data.jsx` + `components.jsx`).
5. **Document preview Sec** (`document.jsx`) + **FLASH/SECTION_NAMES update** (`app.jsx`).
6. **Export service org_context priority** (`export_service.py`).
7. **Export tests** (`test_export.py`) — RED before step 6, GREEN after.

---

## Metadata

**Analog search scope:** `v2/frontend/src/`, `v2/backend/app/`, `v2/backend/tests/`
**Files scanned:** 10 primary source files fully read
**Pattern extraction date:** 2026-06-23
