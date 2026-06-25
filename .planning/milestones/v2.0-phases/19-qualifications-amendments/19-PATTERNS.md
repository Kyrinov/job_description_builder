# Phase 19: Qualifications & Amendments — Pattern Map

**Mapped:** 2026-06-09
**Files analyzed:** 8 (5 modified, 1 new backend module, 2 new test files)
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `v2/frontend/src/data.jsx` | utility/data | transform | `v2/frontend/src/data.jsx` (OG_LEVELS static map pattern) | exact — same file, same static-map export shape |
| `v2/frontend/src/components.jsx` | component | request-response | `v2/frontend/src/components.jsx` (QualEditor, initialAnswer) | exact — same file, extending existing component |
| `v2/frontend/src/document.jsx` | component | request-response | `v2/frontend/src/document.jsx` (Sec, DocumentPane) | exact — same file, extending existing component and prop contract |
| `v2/frontend/src/app.jsx` | provider/store | event-driven | `v2/frontend/src/app.jsx` (orphan_check useEffect, toast pattern) | exact — same file, adding parallel useState + useEffect |
| `v2/frontend/src/styles.css` | config | — | `v2/frontend/src/styles.css` (existing .cls-block, .amend-btn tokens) | exact — same file, new CSS classes following existing token rhythm |
| `v2/backend/app/api/amendments.py` | controller | CRUD | `v2/backend/app/api/jes_scoring.py` (override route + audit_log write) | exact — same role, same data flow, same audit_log table |
| `v2/backend/app/api/__init__.py` | config | — | `v2/backend/app/api/__init__.py` | exact — one-line router include |
| `v2/backend/tests/test_amendments.py` | test | CRUD | `v2/backend/tests/test_jes_scoring.py` (audit_log assertion pattern) | exact — identical test structure for audit_log endpoint |

---

## Pattern Assignments

### `v2/frontend/src/data.jsx` — Replace QUAL_DEFAULT with QUAL_DEFAULTS map

**Analog:** `v2/frontend/src/data.jsx` lines 29–42 (OG_LEVELS static map) and lines 289–293 (current QUAL_DEFAULT)

**Current QUAL_DEFAULT export** (lines 289–293):
```js
const QUAL_DEFAULT = {
  education: 'Graduation with a degree from a recognized post-secondary institution with specialization in environmental science...',
  experience: 'Significant* experience in environmental program or policy analysis...'
};
```

**OG_LEVELS pattern to copy** (lines 29–42) — keyed constant, no API call:
```js
const OG_LEVELS = {
  EC: [1,2,3,4,5,6,7,8],
  IT: [1,2,3,4,5],
  AS: [1,2,3,4,5,6,7,8],
  // ...
};
```

**Export line** (line 419–423) — must export both old name and new additions:
```js
export {
  I, STEPS, PHASES, OG_LEVELS, DRF, WORK_TYPES, DUTY_SUGGESTIONS, QUAL_DEFAULT,
  EC_ELEMENTS, computeClassification, refineDuty, ecFactors,
  accumulateSignals, getDutySuggestions,
};
```

**Target shape for Phase 19:**
```js
// Replace QUAL_DEFAULT definition with keyed map + lookup function
const QUAL_DEFAULTS = {
  EC: {
    education: 'A degree from a recognized post-secondary institution, with acceptable specialization in economics, sociology or statistics, or a field of study related to the duties of the position (environmental science, public policy, or a natural or social science field).',
    experience: 'Significant experience in policy analysis, economic research, or program evaluation relevant to the duties of the position.'
  },
  AS: {
    education: 'A secondary school diploma or an acceptable combination of education, training and/or experience.',
    experience: 'Experience in administrative, financial, or operational support functions relevant to the duties of the position.'
  },
  IT: {
    education: 'Successful completion of two years of an acceptable post-secondary educational program in computer science, information technology, information management or another specialty relevant to the position.',
    experience: 'Experience in information technology functions relevant to the duties of the position.'
  },
  FI: {
    education: "A bachelor's degree from a recognized post-secondary institution with a specialization in accounting, finance or a related field.",
    experience: 'Significant experience in financial management, financial analysis, or accounting relevant to the duties of the position.'
  },
  default: {
    education: 'A degree or diploma from a recognized post-secondary institution in a field relevant to the duties of the position, or an equivalent combination of education and experience.',
    experience: 'Experience performing duties relevant to the position.'
  }
};

function getQualDefault(og_code) {
  return QUAL_DEFAULTS[og_code] || QUAL_DEFAULTS['default'];
}

// Keep QUAL_DEFAULT as alias so existing consumers (document.jsx line 5,
// components.jsx line 5) do not break before their imports are updated.
const QUAL_DEFAULT = QUAL_DEFAULTS['default'];

// Export line — add QUAL_DEFAULTS and getQualDefault, keep QUAL_DEFAULT for compat:
export {
  I, STEPS, PHASES, OG_LEVELS, DRF, WORK_TYPES, DUTY_SUGGESTIONS, QUAL_DEFAULT,
  QUAL_DEFAULTS, getQualDefault,
  EC_ELEMENTS, computeClassification, refineDuty, ecFactors,
  accumulateSignals, getDutySuggestions,
};
```

**Critical pitfall:** `components.jsx` line 5 imports `QUAL_DEFAULT` by name. The export alias above keeps that import alive. The planner must update `components.jsx` import in the same wave as the `data.jsx` export change.

---

### `v2/frontend/src/components.jsx` — QualEditor inline validation + initialAnswer OG threading

**Analog:** `v2/frontend/src/components.jsx` (self — existing QualEditor lines 423–448, initialAnswer lines 466–472, StepInput lines 451–463)

**Current import line** (line 5):
```js
import { I, WORK_TYPES, DUTY_SUGGESTIONS, DRF, QUAL_DEFAULT, refineDuty } from './data.jsx';
```

**Target import line (Phase 19):**
```js
import { I, WORK_TYPES, DUTY_SUGGESTIONS, DRF, QUAL_DEFAULT, getQualDefault, refineDuty } from './data.jsx';
```

**Current QualEditor** (lines 423–448) — no touched state, no validation:
```jsx
function QualEditor({ value, onChange }) {
  const v = value || QUAL_DEFAULT;
  return (
    <div className="quals">
      <label className="qual-field">
        <span className="qual-k">Education</span>
        <textarea
          className="tf"
          rows={3}
          value={v.education}
          onChange={e => onChange({ ...v, education: e.target.value })}
        />
      </label>
      <label className="qual-field">
        <span className="qual-k">Experience</span>
        <textarea
          className="tf"
          rows={3}
          value={v.experience}
          onChange={e => onChange({ ...v, experience: e.target.value })}
        />
      </label>
    </div>
  );
}
```

**Target QualEditor — add og_code prop + touched state + onBlur + qual-error** (pattern from UI-SPEC.md Section C, mirroring existing useState usage in the file):
```jsx
function QualEditor({ value, onChange, og_code }) {
  const v = value || getQualDefault(og_code);
  const [touched, setTouched] = useState({ education: false, experience: false });
  return (
    <div className="quals">
      <label className="qual-field">
        <span className="qual-k">Education</span>
        <textarea
          className="tf"
          rows={3}
          value={v.education}
          onChange={e => onChange({ ...v, education: e.target.value })}
          onBlur={() => setTouched(t => ({ ...t, education: true }))}
        />
        {touched.education && !v.education && (
          <p className="qual-error" role="alert">
            <Icon path={I.warn} size={12} />
            Education field is required.
          </p>
        )}
      </label>
      <label className="qual-field">
        <span className="qual-k">Experience</span>
        <textarea
          className="tf"
          rows={3}
          value={v.experience}
          onChange={e => onChange({ ...v, experience: e.target.value })}
          onBlur={() => setTouched(t => ({ ...t, experience: true }))}
        />
        {touched.experience && !v.experience && (
          <p className="qual-error" role="alert">
            <Icon path={I.warn} size={12} />
            Experience field is required.
          </p>
        )}
      </label>
    </div>
  );
}
```

**StepInput dispatcher** (lines 451–463) — pass og_code through for quals type only:
```jsx
function StepInput(props) {
  const t = props.cfg.type;
  // ...
  if (t === 'quals') return <QualEditor {...props} og_code={props.record?.confirmed_og?.og_code} />;
  // ...
}
```

**initialAnswer function** (lines 466–472) — use getQualDefault keyed on og_code:
```js
function initialAnswer(step, record) {
  const c = step.input;
  if (c.type === 'text' || c.type === 'textarea') return c.preset || '';
  if (c.type === 'duties') return [];
  if (c.type === 'quals') return getQualDefault(record?.confirmed_og?.og_code);
  return null;
}
```

---

### `v2/frontend/src/document.jsx` — Sec prop additions + qual-sub-k + amendment panel

**Analog:** `v2/frontend/src/document.jsx` — Sec component (lines 99–118), DocumentPane (lines 191+), Section 5 qual render (lines 355–388)

**Current Sec component** (lines 99–118):
```jsx
function Sec({ n, title, src, ghost, fresh, editable, onEdit, children }) {
  return (
    <section
      className={`sec${ghost ? ' is-ghost' : ''}${editable ? ' sec--editable' : ''}`}
      onClick={editable ? onEdit : undefined}
    >
      <div className="sec__h">
        {n && <span className="n">{n}</span>}
        <span>{title}</span>
        {src && (
          <span className="src">
            <i style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--accent)', display: 'inline-block' }} />
            {src}
          </span>
        )}
      </div>
      <div className={fresh ? 'fresh' : ''}>{children}</div>
    </section>
  );
}
```

**Target Sec — add amendmentNote, amendmentPanel, onAmendSave, onAmendToggle props:**
```jsx
function Sec({ n, title, src, ghost, fresh, editable, onEdit, children,
               sectionKey, amendmentNote, amendmentPanel, onAmendToggle, onAmendSave, reviewing }) {
  const panelOpen = amendmentPanel?.open;
  const savedNote = amendmentPanel?.saved;
  const panelText = amendmentPanel?.text ?? '';

  return (
    <section
      className={`sec${ghost ? ' is-ghost' : ''}${editable ? ' sec--editable' : ''}`}
      onClick={(!panelOpen && editable) ? onEdit : undefined}
    >
      <div className="sec__h">
        {n && <span className="n">{n}</span>}
        <span>{title}</span>
        {src && (
          <span className="src">
            <i style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--accent)', display: 'inline-block' }} />
            {src}
          </span>
        )}
        {reviewing && sectionKey && (
          <>
            <button
              className={`amend-btn${panelOpen ? ' is-active' : ''}`}
              aria-label={`Add amendment note for ${title}`}
              aria-expanded={!!panelOpen}
              onClick={e => { e.stopPropagation(); onAmendToggle(sectionKey); }}
            >
              <Icon path='<path d="M14 3l3 3-9 9H5v-3L14 3z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>' size={13} />
            </button>
            {savedNote && (
              <span className="amend-indicator" aria-label="Amendment note exists" />
            )}
          </>
        )}
      </div>
      {panelOpen && (
        <div className="amend-panel" style={{ animation: 'rise 0.3s ease both' }}>
          <span className="amend-panel__label">Note for: {title}</span>
          <textarea
            className="tf"
            value={panelText}
            placeholder="Enter a note for the advisor or reviewing manager…"
            onChange={e => onAmendToggle(sectionKey, e.target.value)}
          />
          <div className="amend-panel__actions">
            <button
              className="btn--primary"
              disabled={!panelText.trim()}
              onClick={() => onAmendSave(sectionKey, panelText)}
            >Save note</button>
            <button
              className="btn--ghost"
              onClick={() => onAmendToggle(sectionKey, null)}
            >Discard note</button>
            <span className="amend-count">{panelText.length} characters</span>
          </div>
        </div>
      )}
      <div className={fresh ? 'fresh' : ''}>{children}</div>
    </section>
  );
}
```

**Current Section 5 inline style** (lines 373–384) — the pattern to replace with `.qual-sub-k`:
```jsx
<b style={{ fontFamily: 'var(--mono)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--ink-faint)', display: 'block', marginBottom: 4 }}>
  Education
</b>
```

**Target Section 5 with `.qual-sub-k` class:**
```jsx
<span className="qual-sub-k">EDUCATION</span>
```

**DocumentPane import** (line 5) — add getQualDefault:
```js
import { I, QUAL_DEFAULT, getQualDefault } from './data.jsx';
```

**DocumentPane function signature** (line 191) — add amendment props:
```jsx
function DocumentPane({ record: r, cls, flashes, reviewing, onEditStep, onJesOverride,
                        amendmentNotes, amendmentPanels, onAmendToggle, onAmendSave }) {
```

**Section 5 Sec call** (lines 359–362) — add amendment props:
```jsx
<Sec
  key="q" n={String(n)} title="Essential Qualifications"
  src={qualsGhost ? null : "TBS Qualification Standard"} ghost={qualsGhost} fresh={isFresh('quals')}
  editable={reviewing} onEdit={() => onEditStep('quals')}
  sectionKey="q" reviewing={reviewing}
  amendmentNote={amendmentNotes?.q} amendmentPanel={amendmentPanels?.q}
  onAmendToggle={onAmendToggle} onAmendSave={onAmendSave}
>
```

---

### `v2/frontend/src/app.jsx` — amendmentNotes + amendmentPanels state + hydration useEffect

**Analog:** `v2/frontend/src/app.jsx` — existing useState declarations (lines 74–90), orphan_check useEffect (lines 115–134), toast pattern (lines 80, 386–390, 506–509)

**Existing useState pattern to mirror** (lines 74–90):
```js
const [answers, setAnswers] = useState({});
const [stepIndex, setStepIndex] = useState(0);
// ...
const [orphanFlags, setOrphanFlags] = useState([]);
```

**Existing orphan_check useEffect pattern to mirror** (lines 115–134):
```js
useEffect(() => {
  if (!reviewing || !wd_id || !record.duties?.length || !record.confirmed_og) return;
  fetch(`/api/wd/${wd_id}/orphan_check`, { method: 'POST' })
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(data => { /* update state */ })
    .catch(() => {});
}, [reviewing, wd_id]);
```

**Existing toast pattern** (lines 386–390, 506–509):
```js
// Fire:
function exportAs(kind) {
  setToast(msg);
  setTimeout(() => setToast(null), 2600);
}
// Render:
<div className={`toast${toast ? ' is-show' : ''}`}>
  <span>{toast || ''}</span>
</div>
```

**New state additions for Phase 19:**
```js
const [amendmentNotes, setAmendmentNotes] = useState({});    // { [sectionKey]: string } — saved notes from API
const [amendmentPanels, setAmendmentPanels] = useState({});  // { [sectionKey]: { open, text, saved } } — UI state only
```

**Amendment hydration useEffect — mirrors orphan_check useEffect:**
```js
useEffect(() => {
  if (!wd_id || !reviewing) return;
  fetch(`/api/wd/${wd_id}/amendments`)
    .then(r => r.ok ? r.json() : null)
    .then(data => {
      if (data?.notes) setAmendmentNotes(data.notes);
    })
    .catch(() => {});
}, [wd_id, reviewing]);
```

**handleAmendToggle — manages panel open/close/text; mirrors handleJesOverride function shape (lines 401–430):**
```js
function handleAmendToggle(sectionKey, textOrNull) {
  setAmendmentPanels(prev => {
    const cur = prev[sectionKey] || { open: false, text: '', saved: null };
    if (textOrNull === null) {
      // Discard — close and reset to saved
      return { ...prev, [sectionKey]: { ...cur, open: false, text: cur.saved || '' } };
    }
    if (typeof textOrNull === 'string' && cur.open) {
      // Text update while open
      return { ...prev, [sectionKey]: { ...cur, text: textOrNull } };
    }
    // Toggle open/close
    return { ...prev, [sectionKey]: { ...cur, open: !cur.open, text: cur.saved || '' } };
  });
}
```

**handleAmendSave — POST /api/wd/{id}/amendments; toast on success/failure (mirrors fetch pattern lines 199–218):**
```js
function handleAmendSave(sectionKey, text) {
  if (!wd_id || !text.trim()) return;
  fetch(`/api/wd/${wd_id}/amendments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ section: sectionKey, comment: text }),
  })
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(() => {
      setAmendmentNotes(prev => ({ ...prev, [sectionKey]: text }));
      setAmendmentPanels(prev => ({
        ...prev,
        [sectionKey]: { open: false, text, saved: text }
      }));
      const sectionNames = { id: 'Position Identification', ov: 'Position Overview', du: 'Key Responsibilities', cls: 'Classification & Evaluation', q: 'Essential Qualifications', drf: 'Defence Results Linkage' };
      setToast(`Note saved for ${sectionNames[sectionKey] || sectionKey}.`);
      setTimeout(() => setToast(null), 3500);
    })
    .catch(() => {
      setToast('Could not save note. Try again.');
      setTimeout(() => setToast(null), 3500);
    });
}
```

---

### `v2/backend/app/api/amendments.py` — New file: POST + GET /api/wd/{id}/amendments

**Analog:** `v2/backend/app/api/jes_scoring.py` — module-level docstring, router setup, Pydantic request model, audit_log write pattern via `v2/backend/app/services/jes_service.py` lines 354–366

**File header + imports** (copy from `jes_scoring.py` lines 1–30):
```python
"""
app/api/amendments.py — Amendment note routes (v2.0).

Routes:
    POST /api/wd/{wd_id}/amendments — save a manager amendment note to audit_log
    GET  /api/wd/{wd_id}/amendments — retrieve latest note per section for page-refresh hydration

Security:
    Section key validated against known set via Literal type.
    Comment max_length=2000 (same cap as T-16-03 work_description field).
    WD existence checked before INSERT (404 guard — same as jes_override).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.db import get_connection

router = APIRouter()
```

**Pydantic request model** (copy shape from `JESOverrideRequest` in jes_scoring.py lines 73–76):
```python
class AmendmentRequest(BaseModel):
    section: Literal['id', 'ov', 'du', 'cls', 'q', 'drf'] = Field(...)
    comment: str = Field(min_length=1, max_length=2000)
```

**POST route** (audit_log INSERT pattern from `jes_service.py` lines 354–366, 404 guard from `wd.py` lines 112–116):
```python
@router.post("/wd/{wd_id}/amendments", status_code=201)
async def save_amendment(wd_id: str, body: AmendmentRequest) -> dict:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT id FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Work description not found")
        con.execute(
            "INSERT INTO audit_log (wd_id, event, actor, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                wd_id,
                "manager_amendment",
                "advisor",
                json.dumps({"section": body.section, "comment": body.comment}),
                now.isoformat(),
            ),
        )
        con.commit()
    finally:
        con.close()
    return {"wd_id": wd_id, "section": body.section, "saved": True}
```

**GET route** (audit_log SELECT pattern from `jes_service.py`, deduplication by first-row-per-section wins):
```python
@router.get("/wd/{wd_id}/amendments")
async def get_amendments(wd_id: str) -> dict:
    """Return latest amendment note per section. ORDER BY id DESC; first occurrence per section wins."""
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        rows = con.execute(
            "SELECT detail, created_at FROM audit_log "
            "WHERE wd_id = ? AND event = 'manager_amendment' "
            "ORDER BY id DESC",
            (wd_id,),
        ).fetchall()
    finally:
        con.close()
    notes = {}
    for row in rows:
        detail = json.loads(row["detail"])
        section = detail.get("section")
        if section and section not in notes:
            notes[section] = detail.get("comment", "")
    return {"wd_id": wd_id, "notes": notes}
```

---

### `v2/backend/app/api/__init__.py` — Include amendments router

**Analog:** `v2/backend/app/api/__init__.py` (self — lines 16–23)

**Current** (lines 16–23):
```python
from . import health, noc_mapping, wd, og_classification, jes_scoring

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(noc_mapping.router)
api_router.include_router(wd.router)
api_router.include_router(og_classification.router)
api_router.include_router(jes_scoring.router)
```

**Target — add amendments:**
```python
from . import health, noc_mapping, wd, og_classification, jes_scoring, amendments

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(noc_mapping.router)
api_router.include_router(wd.router)
api_router.include_router(og_classification.router)
api_router.include_router(jes_scoring.router)
api_router.include_router(amendments.router)
```

---

### `v2/backend/tests/test_amendments.py` — New file: AMEND-01 + AMEND-02 backend tests

**Analog:** `v2/backend/tests/test_jes_scoring.py` — audit_log assertion pattern (lines 141–200), `v2/backend/tests/test_wd.py` — create/get/404 pattern (lines 12–57)

**File header + fixture reuse** (copy from `test_jes_scoring.py` lines 1–16, `test_wd.py` lines 1–10):
```python
"""
test_amendments.py — Phase 19: Amendment note endpoint tests.

Integration tests for POST /api/wd/{id}/amendments and GET /api/wd/{id}/amendments.
Covers AMEND-01 (audit_log write), AMEND-02 (correct fields), deduplication, and 404 guard.
"""
import json
import pytest

pytestmark = pytest.mark.asyncio
```

**Helper to create a WD** (copy shape from `test_jes_scoring.py` lines 77–98):
```python
async def _create_wd(client) -> str:
    resp = await client.post(
        "/api/wd",
        json={"record": {"title": "Test Role"}, "answers": {}, "step_index": 1},
    )
    assert resp.status_code == 201
    return resp.json()["id"]
```

**test_save_amendment_creates_audit_row** (copy audit_log assertion from `test_jes_scoring.py` lines 183–199):
```python
async def test_save_amendment_creates_audit_row(client, env_with_db):
    """AMEND-01 — POST /api/wd/{id}/amendments returns 201 and writes audit_log row."""
    from app.config import get_settings
    from app.db import get_connection

    wd_id = await _create_wd(client)
    resp = await client.post(
        f"/api/wd/{wd_id}/amendments",
        json={"section": "du", "comment": "This duty seems outside scope."},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["saved"] is True
    assert body["section"] == "du"

    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        rows = con.execute(
            "SELECT event, actor, detail FROM audit_log WHERE wd_id = ? AND event = 'manager_amendment'",
            (wd_id,),
        ).fetchall()
    finally:
        con.close()

    assert len(rows) == 1
    assert rows[0]["event"] == "manager_amendment"
    assert rows[0]["actor"] == "advisor"
    detail = json.loads(rows[0]["detail"])
    assert detail["section"] == "du"
    assert detail["comment"] == "This duty seems outside scope."
```

**test_get_amendments_latest_per_section** (deduplication test):
```python
async def test_get_amendments_latest_per_section(client, env_with_db):
    """AMEND-01 — GET /api/wd/{id}/amendments returns only the latest note per section."""
    wd_id = await _create_wd(client)
    # Save note twice for same section — GET must return only the second (latest)
    await client.post(f"/api/wd/{wd_id}/amendments",
                      json={"section": "ov", "comment": "First version"})
    await client.post(f"/api/wd/{wd_id}/amendments",
                      json={"section": "ov", "comment": "Updated version"})

    resp = await client.get(f"/api/wd/{wd_id}/amendments")
    assert resp.status_code == 200
    data = resp.json()
    assert data["notes"]["ov"] == "Updated version"
```

**test_save_amendment_404** (copy 404 guard from `test_wd.py` lines 53–56):
```python
async def test_save_amendment_404(client, env_with_db):
    """AMEND-01 — POST returns 404 for non-existent WD."""
    resp = await client.post(
        "/api/wd/does-not-exist/amendments",
        json={"section": "du", "comment": "Note"},
    )
    assert resp.status_code == 404
```

---

### `v2/frontend/src/styles.css` — New CSS classes

**Analog:** `v2/frontend/src/styles.css` — existing `.cls-block` (padding/border-radius rhythm), `.jes__row` (flex layout rhythm), `.ghost-note` (mono label rhythm)

**New classes to append** (exact values from UI-SPEC.md Sections B, C, D):
```css
/* QUAL-03: Section 5 Education/Experience sub-label */
.qual-sub-k {
  font-family: var(--mono);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--ink-faint);
  font-weight: 600;
  display: block;
  margin-bottom: 4px;
}

/* QUAL-02: Inline validation error in QualEditor */
.qual-error {
  font-family: var(--ui);
  font-size: 12.5px;
  font-weight: 500;
  color: oklch(0.58 0.14 25);
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* AMEND-01: Amendment note trigger button in .sec__h */
.amend-btn {
  margin-left: 8px;
  flex: 0 0 auto;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--ink-faint);
  display: grid;
  place-items: center;
  transition: all 0.15s;
}
.amend-btn:hover,
.amend-btn.is-active {
  border-color: var(--accent-line);
  color: var(--accent-deep);
  background: var(--accent-soft);
}

/* Gold dot indicator when a saved note exists for a section */
.amend-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--gold);
  flex: 0 0 auto;
  margin-left: 4px;
}

/* Inline amendment panel — renders between section header and body */
.amend-panel {
  margin-top: 8px;
  margin-bottom: 12px;
  padding: 12px 16px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
}
.amend-panel__label {
  font-family: var(--mono);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--ink-soft);
  font-weight: 600;
  margin-bottom: 8px;
  display: block;
}
.amend-panel textarea.tf {
  min-height: 72px;
}
.amend-panel__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
.amend-count {
  margin-left: auto;
  font-family: var(--mono);
  font-size: 9.5px;
  color: var(--ink-faint);
  letter-spacing: 0.02em;
}
```

---

## Shared Patterns

### audit_log INSERT
**Source:** `v2/backend/app/services/jes_service.py` lines 354–366
**Apply to:** `amendments.py` POST handler
```python
con.execute(
    "INSERT INTO audit_log (wd_id, event, actor, detail, created_at) VALUES (?, ?, ?, ?, ?)",
    (
        wd_id,
        "manager_amendment",
        "advisor",
        json.dumps({"section": section, "comment": comment}),
        datetime.now(timezone.utc).isoformat(),
    ),
)
con.commit()
```

### 404 Guard Before DB Write
**Source:** `v2/backend/app/api/wd.py` lines 112–116
**Apply to:** `amendments.py` POST handler
```python
row = con.execute("SELECT id FROM work_descriptions WHERE id = ?", (wd_id,)).fetchone()
if row is None:
    raise HTTPException(status_code=404, detail="Work description not found")
```

### try/finally con.close()
**Source:** `v2/backend/app/api/wd.py` lines 110–133; `v2/backend/app/api/jes_scoring.py` lines 113–124
**Apply to:** `amendments.py` both handlers
```python
con = get_connection(settings.db_path)
try:
    # ... DB operations ...
finally:
    con.close()
```

### Frontend fetch + toast on success/failure
**Source:** `v2/frontend/src/app.jsx` lines 196–218 (WD persist) and lines 386–390 (toast)
**Apply to:** `handleAmendSave` in `app.jsx`
```js
fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
  .then(r => r.ok ? r.json() : Promise.reject(r.status))
  .then(data => { /* update state */ setToast(msg); setTimeout(() => setToast(null), 3500); })
  .catch(() => { setToast('Could not save note. Try again.'); setTimeout(() => setToast(null), 3500); });
```

### Conditional useEffect with early return guard
**Source:** `v2/frontend/src/app.jsx` lines 115–134 (orphan_check useEffect)
**Apply to:** amendment hydration useEffect in `app.jsx`
```js
useEffect(() => {
  if (!wd_id || !reviewing) return;
  fetch(url)
    .then(r => r.ok ? r.json() : null)
    .then(data => { if (data?.notes) setAmendmentNotes(data.notes); })
    .catch(() => {});
}, [wd_id, reviewing]);
```

### Backend integration test structure
**Source:** `v2/backend/tests/test_jes_scoring.py` lines 141–200, `v2/backend/tests/test_wd.py` lines 12–57
**Apply to:** `test_amendments.py`
- `pytestmark = pytest.mark.asyncio` at module level
- `client` and `env_with_db` fixtures from `conftest.py` (no new fixtures needed)
- Create WD first, then call the endpoint under test
- Assert HTTP status + JSON body + direct DB inspection via `get_connection(settings.db_path)`

---

## No Analog Found

All Phase 19 files have close analogs in the codebase. No file requires falling back to RESEARCH.md-only patterns.

---

## Metadata

**Analog search scope:** `v2/frontend/src/`, `v2/backend/app/api/`, `v2/backend/app/services/`, `v2/backend/tests/`
**Files read:** 14 source files
**Pattern extraction date:** 2026-06-09
