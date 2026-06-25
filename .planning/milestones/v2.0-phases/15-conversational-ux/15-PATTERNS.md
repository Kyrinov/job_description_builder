# Phase 15: Conversational UX — Pattern Map

**Mapped:** 2026-06-04
**Files analyzed:** 7
**Analogs found:** 7 / 7

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `v2/frontend/src/data.jsx` | config/data | transform | self (modify existing) | exact |
| `v2/frontend/src/app.jsx` | store/controller | event-driven | self (modify existing) | exact |
| `v2/frontend/src/conversation.jsx` | component | request-response | self (verify wiring) | exact |
| `v2/frontend/src/components.jsx` | component | request-response | self (modify existing) | exact |
| `v2/backend/app/api/wd.py` | controller | CRUD | `v2/backend/app/api/noc_mapping.py` | role-match |
| `v2/backend/app/main.py` | config | request-response | self (modify existing) | exact |
| `v2/backend/tests/test_wd.py` | test | CRUD | `v2/backend/tests/test_health.py` + `test_db.py` | role-match |

---

## Pattern Assignments

### `v2/frontend/src/data.jsx` (config/data, transform)

**Analog:** self — file already exists at `/home/charles/job_description_builder/v2/frontend/src/data.jsx`

**Existing exports pattern** (lines 309-312):
```javascript
export {
  I, STEPS, PHASES, DRF, WORK_TYPES, DUTY_SUGGESTIONS, QUAL_DEFAULT,
  EC_ELEMENTS, computeClassification, refineDuty, ecFactors
};
```

**STEPS entry shape to copy** (lines 220-230 — `supervises` step, choices type with apply/transcript):
```javascript
{ id: 'supervises', phase: 0, icon: I.user,
  q: 'Will this person supervise or lead others?',
  helper: 'This helps us gauge the level of responsibility.',
  input: { type: 'choices', options: [
    { id: 'none', title: 'No — individual contributor' },
    ...
  ]},
  apply: (r, a) => ({ supervises: a.title }),
  transcript: a => a.title },
```

**STEPS entry shape with signals** (new pattern per RESEARCH.md Pattern 1):
```javascript
{ id: 'qb_work_output_type', phase: 1, icon: I.list,
  q: 'What best describes the main type of output this person produces?',
  helper: 'Think about what they actually deliver — not their title.',
  input: { type: 'choices', options: [
    { id: 'analysis_advice', title: 'Analysis, options, or recommendations for decision-makers',
      signals: { og_candidates: ['EC'], jes_factor_hints: ['Research & analysis', 'Decision making'] } },
    ...
  ]},
  apply: (r, a) => ({ qb_work_output_type: a.id }),
  transcript: a => a.title },
```
NOTE: `apply` must NOT write `_signals` or `a.signals` into record — signals are computed via `accumulateSignals(answers)` as a pure derived function, never persisted.

**PHASES constant to replace** (line 307):
```javascript
// CURRENT (6 entries, old names):
const PHASES = ['Role', 'Focus', 'Level', 'Duties', 'Mission', 'Review'];

// NEW (6 entries, Phase 15 names):
const PHASES = ['Role', 'Work Type', 'Classification', 'Duties', 'Qualifications', 'Review'];
```

**New export additions needed:**
```javascript
export {
  I, STEPS, PHASES, DRF, WORK_TYPES, DUTY_SUGGESTIONS, QUAL_DEFAULT,
  EC_ELEMENTS, computeClassification, refineDuty, ecFactors,
  accumulateSignals   // NEW: pure function, no side-effects
};
```

**`accumulateSignals` function to add** (pure, no side effects — source: RESEARCH.md Code Examples):
```javascript
function accumulateSignals(answers) {
  const qbStepIds = ['qb_work_output_type', 'qb_work_audience', 'qb_knowledge_specialization', 'qb_policy_interpretation'];
  const tally = {};
  for (const stepId of qbStepIds) {
    const ans = answers[stepId];
    if (!ans || !ans.signals) continue;
    for (const ogCode of (ans.signals.og_candidates || [])) {
      tally[ogCode] = (tally[ogCode] || 0) + 1;
    }
  }
  const sorted = Object.entries(tally).sort((a, b) => b[1] - a[1]);
  return sorted.length > 0 ? { dominant: sorted[0][0], tally } : null;
}
```

**FLASH map to update** (app.jsx line 11-13 — maps step ids to doc pane flash targets):
The `workType`, `scopeDirection`, `scopeAdvises`, `scopeImpact` keys must be replaced with the new step ids (`qb_work_output_type`, etc.). Copy the FLASH object pattern from app.jsx lines 10-14 and update keys.

---

### `v2/frontend/src/app.jsx` (store/controller, event-driven)

**Analog:** self — file already exists at `/home/charles/job_description_builder/v2/frontend/src/app.jsx`

**State slice pattern to copy for new slices** (lines 59-74 — all useState declarations):
```javascript
const [record, setRecord] = useState(() => {
  try {
    const raw = localStorage.getItem('jd-builder-v2-record');
    return raw ? JSON.parse(raw) : {};
  } catch { return {}; }
});
const [answers, setAnswers] = useState({});
const [stepIndex, setStepIndex] = useState(0);
const [draft, setDraft] = useState(() => initialAnswer(STEPS[0], {}));
const [reviewing, setReviewing] = useState(false);
const [editingReturn, setEditingReturn] = useState(false);
```

**New state slices to add (follow same pattern):**
```javascript
const [wd_id, setWdId] = useState(() => {
  try { return localStorage.getItem('jd-builder-v2-wd-id') || null; } catch { return null; }
});
const [nocCandidates, setNocCandidates] = useState([]);
const [nocLoading, setNocLoading] = useState(false);
```

**localStorage persistence pattern** (lines 82-88 — useEffect for record):
```javascript
useEffect(() => {
  try {
    localStorage.setItem('jd-builder-v2-record', JSON.stringify(record));
  } catch {
    // storage quota exceeded — degrade gracefully, do not throw
  }
}, [record]);
```
Copy this pattern for `wd_id` persistence (separate `useEffect` watching `wd_id`).

**`commit()` function — full body** (lines 116-138):
```javascript
function commit() {
  if (!answerValid(step, draft)) return;
  const patch = step.apply(record, draft) || {};
  const newRecord = { ...record, ...patch };
  if (step.id === 'quals') newRecord.qualsVisited = true;
  setRecord(newRecord);
  setAnswers(prev => ({ ...prev, [step.id]: draft }));
  flash(FLASH[step.id]);

  if (editingReturn) {
    setEditingReturn(false);
    setReviewing(true);
    return;
  }
  const next = stepIndex + 1;
  if (next >= STEPS.length) {
    setReviewing(true);
  } else {
    setStepIndex(next);
    const ns = STEPS[next];
    setDraft(answers[ns.id] !== undefined ? answers[ns.id] : initialAnswer(ns, newRecord));
  }
}
```
Phase 15 inserts three new blocks into `commit()`:
1. **WD persistence block** — before the `editingReturn` check: if `!wd_id` call `POST /api/wd` and store id; else call `PATCH /api/wd/{wd_id}`.
2. **NOC trigger block** — after WD PATCH, if `step.id === 'summary'`: set `nocLoading(true)`, call `POST /api/noc/map`, then `setNocCandidates(result.candidates)`, `setNocLoading(false)`.
3. **NOC invalidation block** — if `editingReturn && step.phase === 1`: clear `nocCandidates` and remove `noc_confirm` from `answers` before returning to review.

**`editStep()` and `jumpToExchange()` — no changes needed** (lines 148-163). These already work; do not touch.

**ActiveQuestion render — cfg injection pattern** (lines 195-199):
```javascript
<ActiveQuestion
  step={step} record={record} draft={draft} setDraft={setDraft}
  onCommit={commit} onBack={goBack}
  canBack={stepIndex > 0 && !editingReturn}
  isLast={stepIndex === STEPS.length - 1}
/>
```
Phase 15 change: when `step.input.type === 'noc_confirm'`, inject candidates into cfg:
```javascript
const stepCfg = step.input.type === 'noc_confirm'
  ? { ...step.input, candidates: nocCandidates, loading: nocLoading }
  : step.input;
// pass stepCfg to ActiveQuestion instead of step directly, or override cfg on the step object inline
```
The cleanest approach: pass a `cfgOverride` prop to `ActiveQuestion` and use it in `StepInput`. Alternatively, spread onto the step object inline (simpler, no component change required).

---

### `v2/frontend/src/conversation.jsx` (component, request-response)

**Analog:** self — file already exists at `/home/charles/job_description_builder/v2/frontend/src/conversation.jsx`

**Header component — no changes needed** (lines 9-36). It already renders phase chips using `PHASES.map` and applies `is-active` / `is-done` CSS based on `phaseIdx`. The only required change is that `PHASES` in `data.jsx` must be updated to the new 6-phase names — `Header` consumes it automatically.

**Phase chip render pattern** (lines 24-32):
```javascript
{PHASES.map((p, i) => (
  <div
    key={p}
    className={`phase${i === phaseIdx ? ' is-active' : ''}${i < phaseIdx ? ' is-done' : ''}`}
  >
    <div className="phase__bar"><i /></div>
    <div className="phase__label">{p}</div>
  </div>
))}
```

**`ActiveQuestion` cfg pass-through** (lines 76-84 — `StepInput` usage):
```javascript
<StepInput
  cfg={step.input}
  value={draft}
  onChange={setDraft}
  onSubmit={() => { if (valid) onCommit(); }}
  record={record}
/>
```
If app.jsx passes a `cfgOverride` prop down, `ActiveQuestion` should prefer it: `cfg={cfgOverride || step.input}`. This is the only change needed in conversation.jsx for Phase 15.

---

### `v2/frontend/src/components.jsx` (component, request-response)

**Analog:** self — file already exists at `/home/charles/job_description_builder/v2/frontend/src/components.jsx`

**`StepInput` dispatcher — current body** (lines 283-293):
```javascript
function StepInput(props) {
  const t = props.cfg.type;
  if (t === 'text' || t === 'textarea') return <TextInput {...props} />;
  if (t === 'choices') return <ChoiceList {...props} />;
  if (t === 'scale') return <ScaleInput {...props} />;
  if (t === 'duties') return <DutyBuilder {...props} />;
  if (t === 'drf') return <DrfPicker {...props} />;
  if (t === 'quals') return <QualEditor {...props} />;
  if (t === 'noc_confirm') return <NocConfirmList {...props} />;
  return null;
}
```
Phase 15 adds one line before `return null`:
```javascript
  if (t === 'og_confirm') return <NocConfirmList {...props} />; // stub — Phase 16 replaces with OgConfirmList
```

**`NocConfirmList` — no changes needed** (lines 195-225). Already accepts `cfg.candidates` array and `value`/`onChange`. Phase 15 wires data into it from app.jsx; the component itself is complete.

**`answerValid` — verify `noc_confirm` branch** (lines 303-310):
```javascript
function answerValid(step, value) {
  ...
  if (t === 'noc_confirm') return typeof value === 'string' && value.length > 0;
  return !!value;
}
```
`og_confirm` will fall through to `return !!value` which is correct for a stub. No change needed.

**`initialAnswer` — may need `noc_confirm` case** (lines 296-301):
```javascript
function initialAnswer(step, record) {
  const c = step.input;
  if (c.type === 'text' || c.type === 'textarea') return c.preset || '';
  if (c.type === 'duties') return [];
  if (c.type === 'quals') return QUAL_DEFAULT;
  return null;  // ← noc_confirm/og_confirm fall here → null is correct (no selection)
}
```
No change needed — `null` is the correct initial answer for choice-type steps.

---

### `v2/backend/app/api/wd.py` (controller, CRUD)

**Analog:** `v2/backend/app/api/noc_mapping.py`

**Imports pattern** (noc_mapping.py lines 1-19 — copy this structure):
```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.models.work_description import WorkDescription
# wd.py will also need:
from uuid import uuid4
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Optional
from app.db import get_connection
```

**Router declaration pattern** (noc_mapping.py line 19):
```python
router = APIRouter()
```

**Route handler pattern** (noc_mapping.py lines 22-51):
```python
@router.post("/noc/map", response_model=NocMapResponse)
async def map_noc(body: WorkDescriptionRequest) -> NocMapResponse:
    settings = get_settings()
    try:
        result = await map_work_description(...)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    ...
    return NocMapResponse(candidates=candidates_out)
```

**Adapted WD CRUD route pattern** (from RESEARCH.md Pattern 2):
```python
# POST /wd — create
@router.post("/wd", status_code=201)
async def create_wd(body: WDCreateRequest):
    settings = get_settings()
    wd = WorkDescription(
        id=str(uuid4()),
        record=body.record,
        answers=body.answers,
        step_index=body.step_index,
        created_at=datetime.now(timezone.utc),
        last_modified=datetime.now(timezone.utc),
    )
    con = get_connection(settings.db_path)
    try:
        con.execute(
            "INSERT INTO work_descriptions (id, title, data, schema_version, created_at, last_modified) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (wd.id, wd.title, wd.model_dump_json(),
             wd.schema_version, wd.created_at.isoformat(), wd.last_modified.isoformat())
        )
        con.commit()
    finally:
        con.close()
    return {"id": wd.id}

# GET /wd/{wd_id} — read
@router.get("/wd/{wd_id}")
async def get_wd(wd_id: str):
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
    return WorkDescription.model_validate_json(row["data"])

# PATCH /wd/{wd_id} — update
@router.patch("/wd/{wd_id}")
async def patch_wd(wd_id: str, body: WDPatchRequest):
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Work description not found")
        wd = WorkDescription.model_validate_json(row["data"])
        # merge patch fields onto wd
        for field, val in body.model_dump(exclude_unset=True).items():
            setattr(wd, field, val)
        wd.last_modified = datetime.now(timezone.utc)
        con.execute(
            "UPDATE work_descriptions SET data=?, last_modified=? WHERE id=?",
            (wd.model_dump_json(), wd.last_modified.isoformat(), wd_id)
        )
        con.commit()
    finally:
        con.close()
    return wd
```

**Request model pattern** (follows Pydantic v2 BaseModel with `exclude_unset` support):
```python
class WDCreateRequest(BaseModel):
    record: dict = Field(default_factory=dict)
    answers: dict = Field(default_factory=dict)
    step_index: int = 0
    draft: Optional[dict] = None
    reviewing: bool = False
    editing_return: bool = False

class WDPatchRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    record: Optional[dict] = None
    answers: Optional[dict] = None
    step_index: Optional[int] = None
    confirmed_noc: Optional[dict] = None
    # add other patchable fields as needed
```

**SQLite connection pattern** (db.py lines 17-30 — always use `get_connection`, always close in `finally`):
```python
con = get_connection(settings.db_path)
try:
    con.execute("...", (...))
    con.commit()
finally:
    con.close()
```

---

### `v2/backend/app/main.py` (config, request-response)

**Analog:** self — file already exists at `/home/charles/job_description_builder/v2/backend/app/main.py`

**`api/__init__.py` router registration pattern** (api/__init__.py lines 1-22):
```python
from . import health, noc_mapping

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(noc_mapping.router)
```
Phase 15 change is in `api/__init__.py`, NOT in `main.py`:
```python
from . import health, noc_mapping, wd   # add wd

api_router.include_router(wd.router)    # add after noc_mapping
```
`main.py` itself does not change — it mounts `api_router` which auto-includes `wd.router`.

---

### `v2/backend/tests/test_wd.py` (test, CRUD)

**Analog:** `v2/backend/tests/test_health.py` (structure) + `v2/backend/tests/test_db.py` (fixture usage)

**File header + pytestmark pattern** (test_health.py lines 1-9):
```python
"""
test_wd.py — contract for POST /api/wd, GET /api/wd/{id}, PATCH /api/wd/{id}.
"""
import pytest

pytestmark = pytest.mark.asyncio
```

**Async client test pattern** (test_health.py lines 12-16):
```python
async def test_health_returns_200(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Adapted WD CRUD test pattern:**
```python
async def test_create_wd_returns_201_with_id(client):
    """POST /api/wd must return 201 with an id field."""
    response = await client.post("/api/wd", json={"record": {"title": "Test Role"}, "answers": {}, "step_index": 1})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert isinstance(data["id"], str)

async def test_get_wd_returns_work_description(client):
    """GET /api/wd/{id} must return the WorkDescription that was POSTed."""
    create_resp = await client.post("/api/wd", json={"record": {"title": "Test Role"}, "answers": {}, "step_index": 1})
    wd_id = create_resp.json()["id"]
    response = await client.get(f"/api/wd/{wd_id}")
    assert response.status_code == 200
    assert response.json()["id"] == wd_id

async def test_patch_wd_updates_last_modified(client):
    """PATCH /api/wd/{id} must update last_modified."""
    create_resp = await client.post("/api/wd", json={"record": {}, "answers": {}, "step_index": 0})
    wd_id = create_resp.json()["id"]
    patch_resp = await client.patch(f"/api/wd/{wd_id}", json={"step_index": 2})
    assert patch_resp.status_code == 200
    patched = patch_resp.json()
    assert patched["step_index"] == 2

async def test_get_wd_404_for_unknown_id(client):
    """GET /api/wd/{id} must return 404 for a non-existent id."""
    response = await client.get("/api/wd/does-not-exist")
    assert response.status_code == 404
```

**Fixture chain to use** (conftest.py lines 17-77):
```
tmp_db_path → env_with_db → test_app → client
```
All tests receive `client` as the only fixture argument; the chain wires the tmp DB automatically.

---

## Shared Patterns

### SQLite connection management
**Source:** `v2/backend/app/db.py` lines 17-30
**Apply to:** `v2/backend/app/api/wd.py` — all three route handlers
```python
con = get_connection(settings.db_path)
try:
    # ... db operations ...
    con.commit()
finally:
    con.close()
```

### Pydantic serialization of WorkDescription
**Source:** `v2/backend/app/models/work_description.py` lines 29-51
**Apply to:** `v2/backend/app/api/wd.py` — read/write the `data` TEXT column
- Write: `wd.model_dump_json()` → store as TEXT
- Read: `WorkDescription.model_validate_json(row["data"])` → reconstruct model
- Never call `json.dumps(wd.dict())` directly — Pydantic v2 handles datetime and Optional correctly

### Settings acquisition
**Source:** `v2/backend/app/api/noc_mapping.py` line 32
**Apply to:** `v2/backend/app/api/wd.py` — inside each route handler body
```python
settings = get_settings()
```

### HTTPException for 404/422
**Source:** `v2/backend/app/api/noc_mapping.py` lines 37-38
**Apply to:** `v2/backend/app/api/wd.py` — GET and PATCH when row not found
```python
raise HTTPException(status_code=404, detail="Work description not found")
```

### localStorage lazy initialiser
**Source:** `v2/frontend/src/app.jsx` lines 59-66
**Apply to:** `wd_id` state slice in app.jsx
```javascript
const [wd_id, setWdId] = useState(() => {
  try { return localStorage.getItem('jd-builder-v2-wd-id') || null; } catch { return null; }
});
```

### answerValid choice type check
**Source:** `v2/frontend/src/components.jsx` lines 308-309
**Apply to:** `noc_confirm` and `og_confirm` steps — current code already handles noc_confirm; og_confirm falls through to `return !!value` which is correct
```javascript
if (t === 'noc_confirm') return typeof value === 'string' && value.length > 0;
```

---

## No Analog Found

No files lack a codebase analog. All 7 files either modify existing files with clear patterns, or have a direct structural template in the repo.

---

## Phase Index / Step ID Reference

Correct `phase:` integers for new STEPS array (critical — see RESEARCH.md Pitfall 1):

| phase integer | Phase label | Step ids |
|---|---|---|
| 0 | Role | `title`, `branch`, `reports`, `supervises` |
| 1 | Work Type | `summary`, `qb_work_output_type`, `qb_work_audience`, `qb_knowledge_specialization`, `qb_policy_interpretation`, `noc_trigger` (optional step or handled imperatively) |
| 2 | Classification | `noc_confirm` |
| 3 | Duties | `duties` |
| 4 | Qualifications | `quals` |
| 5 | Review | (reviewing state, not a STEP entry) |

Steps to **remove** from STEPS: `workType`, `scopeDirection`, `scopeAdvises`, `scopeImpact`, `drf`.
`drf` removal: the DRF step (phase 4 in prototype) is deferred to v2.1 per REQUIREMENTS.md Out of Scope.

---

## Metadata

**Analog search scope:** `v2/frontend/src/`, `v2/backend/app/api/`, `v2/backend/app/models/`, `v2/backend/app/`, `v2/backend/tests/`
**Files read:** 11
**Pattern extraction date:** 2026-06-04
