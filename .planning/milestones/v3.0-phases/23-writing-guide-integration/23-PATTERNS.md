# Phase 23: Writing Guide Integration — Pattern Map

**Mapped:** 2026-06-15
**Files analyzed:** 8 (2 new, 6 modified)
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `v2/backend/app/services/duty_validator.py` | service | transform | `v2/backend/app/api/wd.py::_duty_contradicts_og` (inline) | role-match |
| `v2/backend/tests/test_writing_guide.py` | test | request-response | `v2/backend/tests/test_amendments.py` | exact |
| `v2/backend/app/api/wd.py` (MODIFY) | controller | request-response | `v2/backend/app/api/wd.py::run_orphan_check` (same file) | exact |
| `v2/backend/app/data/constants.py` (MODIFY) | config | — | `v2/backend/app/data/constants.py::QUESTION_BANK` (same file) | exact |
| `v2/frontend/src/app.jsx` (MODIFY) | provider/store | event-driven | `v2/frontend/src/app.jsx::orphan_check useEffect` (same file) | exact |
| `v2/frontend/src/components.jsx` (MODIFY) | component | request-response | `v2/frontend/src/document.jsx::OrphanBadge` | exact |
| `v2/frontend/src/data.jsx` (MODIFY) | config | — | `v2/frontend/src/data.jsx::OG_LEVELS` constant + `STEPS` array | exact |
| `v2/frontend/src/styles.css` (MODIFY) | config | — | `v2/frontend/src/styles.css::.orphan-badge` block | exact |

---

## Pattern Assignments

### `v2/backend/app/services/duty_validator.py` (NEW — service, transform)

**Analog:** `v2/backend/app/api/wd.py` lines 248–259 (`_duty_contradicts_og`) and the inline pattern used throughout `orphan_check`.

The validator is a pure function module — no FastAPI, no DB. The only existing in-project service analogs are inlined in `wd.py`. Model the module structure on the pattern below.

**Module header / imports pattern** (copy from `v2/backend/app/api/wd.py` lines 1–6, strip to stdlib only):
```python
"""
app/services/duty_validator.py — WG-01 structural duty validation.

Four deterministic text rules. No LLM. Called only from POST /api/wd/{id}/validate-duties.
"""
from __future__ import annotations

import re
```

**Core transform pattern** (copy logic shape from `_duty_contradicts_og`, lines 248–259):
```python
def _duty_contradicts_og(duty_lower: str, exclusions_text: str) -> bool:
    """Keyword check: True if any exclusion keyword appears in duty text."""
    exclusion_keywords = [
        phrase.strip().lower()
        for phrase in exclusions_text.replace(';', ',').split(',')
        if len(phrase.strip()) > 4
    ]
    return any(kw in duty_lower for kw in exclusion_keywords)
```

Apply the same list-comprehension + `any()` shape for the NO_DUPLICATE check. Use `first = words[0].rstrip(',;') if words else ''` to avoid compound-verb false positives (RESEARCH.md Pitfall 1).

**Return shape to match:** `list[dict]` — each dict is `{"duty_id": str, "rules_failed": list[dict]}`. Mirrors the `orphan_check` return shape `{"flagged": list[dict]}` but with a list of rule dicts per finding instead of a single rationale string.

---

### `v2/backend/tests/test_writing_guide.py` (NEW — test, request-response)

**Analog:** `v2/backend/tests/test_amendments.py` (full file, lines 1–137)

**Module header + pytestmark pattern** (lines 1–14 of `test_amendments.py`):
```python
"""
test_writing_guide.py — Phase 23: WG-01/WG-02/WG-03/WG-04 requirements tests.

...
"""
import json
import pytest

pytestmark = pytest.mark.asyncio
```

**Helper: create WD** (lines 17–23 of `test_amendments.py`):
```python
async def _create_wd(client) -> str:
    resp = await client.post(
        "/api/wd",
        json={"record": {"title": "Test Role"}, "answers": {}, "step_index": 1},
    )
    assert resp.status_code == 201
    return resp.json()["id"]
```

**Integration test pattern — happy path** (lines 26–38 of `test_amendments.py`):
```python
async def test_save_amendment_creates_audit_row(client, env_with_db):
    """AMEND-01 — POST /api/wd/{id}/amendments returns 201; writes audit_log row."""
    wd_id = await _create_wd(client)
    resp = await client.post(
        f"/api/wd/{wd_id}/amendments",
        json={"section": "du", "comment": "This duty seems outside scope."},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["saved"] is True
```

**Integration test pattern — 404 guard** (lines 79–85 of `test_amendments.py`):
```python
async def test_save_amendment_404(client, env_with_db):
    """AMEND-01 — POST returns 404 for non-existent WD."""
    resp = await client.post(
        "/api/wd/does-not-exist/amendments",
        json={"section": "du", "comment": "Note"},
    )
    assert resp.status_code == 404
```

**Unit test pattern (no HTTP client)** (lines 17–42 of `test_sjd.py`):
```python
def test_sjd_library_count():
    """SJD-01: SJD_LIBRARY has exactly 10 entries."""
    from app.data.sjd_library import SJD_LIBRARY
    assert len(SJD_LIBRARY) == 10

def test_sjd_entry_fields():
    """SJD-01: Every SJDEntry has all required fields."""
    from app.data.sjd_library import SJD_LIBRARY
    for entry in SJD_LIBRARY:
        assert entry.sjd_number, f"Missing sjd_number on entry {entry}"
```

Apply the same module-level `pytestmark = pytest.mark.asyncio` pattern. Unit tests (WG-01 validator rules, WG-03 STEPS check, WG-04 OG_DEFINITIONS coverage) do NOT need `client` or `env_with_db` fixtures — plain `def` functions suffice. Integration tests (WG-02 endpoint) require both.

---

### `v2/backend/app/api/wd.py` — ADD `POST /api/wd/{id}/validate-duties` (MODIFY)

**Analog:** `run_orphan_check` in the same file, lines 262–301.

**Exact model to copy** (lines 262–301):
```python
@router.post("/wd/{wd_id}/orphan_check")
async def run_orphan_check(wd_id: str) -> dict:
    """Deterministic orphan check: verb-keyword match against OG_DEFINITIONS.exclusions."""
    from app.data.constants import OG_DEFINITIONS
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
    # ... business logic ...
    return {"wd_id": wd_id, "flagged": flagged}
```

Key differences from `orphan_check`:
- Import `from app.services.duty_validator import validate_duties` (not `OG_DEFINITIONS`)
- No `wd.confirmed_og` guard (validate-duties is unconditional — always runs on any duties list)
- Return shape: `{"wd_id": wd_id, "findings": findings}` (not `"flagged"`)
- Insert the new endpoint AFTER `run_orphan_check` in the file (maintain reading order)

---

### `v2/backend/app/data/constants.py` — ADD `OG_DEFINITIONS` content (MODIFY)

**Analog:** The existing `QUESTION_BANK` list in the same file (lines 208 onward).

`OG_DEFINITIONS` is already present in `constants.py` (referenced in `orphan_check` via `from app.data.constants import OG_DEFINITIONS`). No new constant needs to be created — the planner must verify the structure already has `definition`, `inclusions`, `exclusions` keys on each entry.

If a `client_service_results` entry is added to `QUESTION_BANK` (per WG-03 open question), copy the entry dict shape from lines 208–253:
```python
{
    "id": "work_output_type",
    "phase_slot": "work_type",
    "question": "What best describes the main type of output...",
    "helper": "Think about what they actually deliver — not their title.",
    "input_type": "choices",
    "options": [
        {
            "id": "analysis_advice",
            "label": "Analysis, options, or recommendations for decision-makers",
            "signals": {
                "og_candidates": ["EC"],
                "jes_factor_hints": ["Research & analysis", "Decision making"],
                "teer_affinity": [1, 2],
            },
        },
        ...
    ],
},
```

CAUTION: `test_question_bank.py` validates that every entry has an `options` key. A `client_service_results` freetext entry would require a new `input_type` supported by the test. Per RESEARCH.md Assumption A1 and Pitfall 2, the safe path is adding `client_service_results` only to the frontend `STEPS` array, not to `QUESTION_BANK`. Confirm with the planner before touching `QUESTION_BANK`.

---

### `v2/frontend/src/app.jsx` — ADD `dutyHints` state + `validate-duties` `useEffect` (MODIFY)

**Analog:** The orphan check `useEffect` and JES scoring trigger in the same file.

**State declaration pattern** (lines 88–100 — copy adjacent to `orphanFlags` declaration):
```javascript
const [orphanFlags, setOrphanFlags] = useState([]);
// ADD BELOW:
const [dutyHints, setDutyHints] = useState([]);
```

**Orphan check useEffect — exact pattern to mirror** (lines 139–158):
```javascript
useEffect(() => {
  if (!reviewing || !wd_id || !record.duties?.length || !record.confirmed_og) return;
  fetch(`/api/wd/${wd_id}/orphan_check`, { method: 'POST' })
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(data => {
      if (data.flagged && data.flagged.length > 0) {
        setRecord(prev => ({ ... }));
      }
      setOrphanFlags(data.flagged || []);
    })
    .catch(() => {}); // silent on failure — orphan check is advisory only
}, [reviewing, wd_id]);
```

**JES scoring post-duties trigger pattern** (lines 324–364) — the `validate-duties` call chains off `wdPromise` the same way:
```javascript
if (step.id === 'duties') {
  // ... existing JES code ...
  wdPromise
    .then((id) => fetch('/api/jes/score', { ... }))
    ...
}
```

**New validate-duties trigger to add inside the same `if (step.id === 'duties')` block, after JES:**
```javascript
// WG-02: non-blocking duty validation (chains off wdPromise like JES scoring)
wdPromise
  .then(id => fetch(`/api/wd/${id}/validate-duties`, { method: 'POST' }))
  .then(r => r.ok ? r.json() : Promise.reject(r.status))
  .then(data => setDutyHints(data.findings || []))
  .catch(() => {}); // non-blocking; silent on failure
```

**Clear dutyHints on re-entry pattern** (lines 366–411 — `editingReturn` block):
Add `setDutyHints([])` alongside the existing state clears when `step.id === 'duties'` and `editingReturn` is true. The exact location is in the `if (editingReturn)` block after line 366.

**WG-04 OG tip: pass tip text via cfgOverride** (lines 707–744 — `stepCfgOverride` block):
The `duties` step override block is at line 738:
```javascript
: step.id === 'duties'
  ? { ...step.input, noc_code: record.confirmed_noc ? ... : null }
  : undefined)
```
Extend this to also inject `og_tip` and `duty_hints`:
```javascript
: step.id === 'duties'
  ? {
      ...step.input,
      noc_code: record.confirmed_noc ? ... : null,
      og_tip: (() => {
        const ogCode = typeof record.confirmed_og === 'object'
          ? record.confirmed_og?.og_code
          : record.confirmed_og || '';
        return OG_DUTY_TIPS[ogCode] || null;
      })(),
      duty_hints: dutyHints,
    }
  : undefined)
```

---

### `v2/frontend/src/components.jsx` — ADD `.duty-hint` rendering in `DutyBuilder` (MODIFY)

**Analog:** `OrphanBadge` in `v2/frontend/src/document.jsx` lines 41–55.

**OrphanBadge pattern to mirror** (lines 41–55 of `document.jsx`):
```jsx
function OrphanBadge({ rationale }) {
  return (
    <div className="orphan-badge">
      <span className="orphan-badge__icon">
        <Icon path={I.warn} size={13} />
      </span>
      <span className="orphan-badge__body">
        <span className="orphan-badge__label">Orphan Warning</span>
        <span className="orphan-badge__cite">{rationale}</span>
      </span>
    </div>
  );
}
```

**Where to render** (line 319 of `document.jsx` — render after duty text, inside `li`):
```jsx
{d.orphan && reviewing && <OrphanBadge rationale={d.orphan_rationale} />}
```

For `.duty-hint` in `DutyBuilder` (inside `components.jsx`), render inline in the selected-duty `div` at lines 235–251, after the existing `duty-sug__tag` span:
```jsx
{/* WG-02: duty-hint badge if this duty has validation findings */}
{cfg.duty_hints && cfg.duty_hints.find(h => h.duty_id === d.id)?.rules_failed.length > 0 && (
  <span className="duty-hint">
    {cfg.duty_hints.find(h => h.duty_id === d.id).rules_failed.map(r => r.detail).join('; ')}
  </span>
)}
```

**WG-04 OG tip rendering** — render ABOVE the duty list inside `DutyBuilder`'s returned `<div className="duties">`:
```jsx
{cfg.og_tip && cfg.og_tip.length > 80 && (
  <div className="og-duty-tip">
    <Icon path={I.flag} size={12} />
    <span>{cfg.og_tip.slice(0, 200)}</span>
  </div>
)}
```

---

### `v2/frontend/src/data.jsx` — ADD `client_service_results` step + `OG_DUTY_TIPS` constant (MODIFY)

**Analog:** Existing `STEPS` entries at lines 472–644, and `OG_LEVELS` constant at lines 30–54.

**STEPS insertion target** (lines 629–635 — the `duties` step):
```javascript
/* ----- Phase 3: Duties ----- */
{ id: 'duties', phase: 3, icon: I.list,
  q: 'Here are the responsibilities managers usually pick for a role like this.',
  ...
```

The `client_service_results` step goes immediately BEFORE this block. Copy the `textarea` step shape from line 489 (`summary`):
```javascript
{ id: 'summary', phase: 1, icon: I.spark,
  q: 'Describe the primary work of this position in your own words.',
  helper: 'A few sentences is enough.',
  input: { type: 'textarea', placeholder: 'e.g. Develops and coordinates...' },
  apply: (r, a) => ({ summary: a }),
  transcript: a => a },
```

New step:
```javascript
{ id: 'client_service_results', phase: 3, icon: I.flag,
  q: 'What client service results does this position deliver?',
  helper: 'Describe the outcomes this role produces for clients or stakeholders. This will appear in the work description context section.',
  input: { type: 'textarea', placeholder: 'e.g. Clients receive timely, accurate advice on...' },
  apply: (r, a) => ({ client_service_results: a }),
  transcript: a => a ? a.slice(0, 60) + (a.length > 60 ? '...' : '') : 'Pending' },
```

**OG_DUTY_TIPS constant** — embed after `OG_LEVELS` (lines 30–54), mirroring its exact format:
```javascript
// JS copy of OG_DEFINITIONS tip text from v2/backend/app/data/constants.py.
// Uses inclusions if non-empty, else definition. Capped at 200 chars at render time.
// Groups with thin content (<80 chars) have empty string — tip is suppressed in DutyBuilder.
const OG_DUTY_TIPS = {
  EC: "...",  // from OG_DEFINITIONS["EC"]["inclusions"] or ["definition"]
  IT: "...",
  // ... all 16 groups
};
```

Export `OG_DUTY_TIPS` in the `export { ... }` line at line 674 of `data.jsx`.

---

### `v2/frontend/src/styles.css` — ADD `.duty-hint` and `.og-duty-tip` rules (MODIFY)

**Analog:** `.orphan-badge` block at lines 749–780.

**Exact analog to copy and adapt** (lines 749–780):
```css
/* Phase 18 — Orphan warning badge (JD-04) */
.orphan-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-family: var(--mono);
  font-size: 11px;
  line-height: 1.4;
  color: oklch(0.58 0.14 35);
  background: oklch(0.97 0.035 50);
  border: 1px solid oklch(0.88 0.07 42);
  border-radius: var(--radius-sm);
  padding: 4px 8px;
}
.orphan-badge__label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}
.orphan-badge__cite {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  font-weight: 400;
  color: oklch(0.50 0.10 35);
}
```

**New `.duty-hint` rule** — same color family (amber/orange), inline display, smaller:
```css
/* Phase 23 — Duty structural validation hint (WG-02) */
.duty-hint {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  line-height: 1.4;
  color: oklch(0.58 0.14 35);
  background: oklch(0.97 0.035 50);
  border: 1px solid oklch(0.88 0.07 42);
  border-radius: var(--radius-sm);
  padding: 3px 7px;
  font-family: var(--mono);
}
```

**New `.og-duty-tip` rule** — blue/teal to distinguish from amber warning (informational, not a warning):
```css
/* Phase 23 — Per-OG duty tip box (WG-04) */
.og-duty-tip {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 12px;
  padding: 8px 12px;
  font-size: 12px;
  line-height: 1.5;
  color: oklch(0.42 0.10 240);
  background: oklch(0.96 0.025 240);
  border: 1px solid oklch(0.84 0.055 240);
  border-radius: var(--radius-sm);
}
```

Insert both blocks immediately after the existing `.orphan-badge` block (after line 780).

---

## Shared Patterns

### DB Load Pattern
**Source:** `v2/backend/app/api/wd.py` lines 262–280 (`run_orphan_check`)
**Apply to:** `validate_duties_endpoint` in `wd.py`
```python
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
```

### Non-blocking `fetch` + silent catch
**Source:** `v2/frontend/src/app.jsx` lines 139–157 (orphan_check useEffect)
**Apply to:** `validate-duties` trigger in `commit()` function
```javascript
fetch(url, { method: 'POST' })
  .then(r => r.ok ? r.json() : Promise.reject(r.status))
  .then(data => setState(data.field || []))
  .catch(() => {}); // non-blocking; silent on failure
```

### `wdPromise`-chained trigger
**Source:** `v2/frontend/src/app.jsx` lines 324–364 (JES scoring)
**Apply to:** `validate-duties` trigger (must chain off `wdPromise` so duties are persisted before the POST fires)
```javascript
wdPromise
  .then(id => fetch(`/api/wd/${id}/endpoint`, { method: 'POST' }))
  .then(r => r.ok ? r.json() : Promise.reject(r.status))
  .then(data => setSomeState(data.field || []))
  .catch(() => {});
```

### JS constant mirroring backend data
**Source:** `v2/frontend/src/data.jsx` lines 27–54 (`OG_LEVELS`)
**Apply to:** `OG_DUTY_TIPS` constant in `data.jsx`
```javascript
// JS copy of [BackendConstant] from v2/backend/app/data/constants.py.
// Avoids an API round-trip for static reference data.
const OG_DUTY_TIPS = {
  EC: "...",
  // ... all 16 entries
};
```

### Icon + warn badge component
**Source:** `v2/frontend/src/document.jsx` lines 41–55 (`OrphanBadge`)
**Apply to:** Inline `.duty-hint` rendering in `DutyBuilder` (components.jsx)
```jsx
<span className="orphan-badge__icon">
  <Icon path={I.warn} size={13} />
</span>
```

---

## No Analog Found

All 8 files have direct analogs. No research-only patterns required.

---

## Metadata

**Analog search scope:** `v2/backend/` and `v2/frontend/src/`
**Files scanned:** `wd.py`, `constants.py`, `app.jsx`, `components.jsx`, `data.jsx`, `document.jsx`, `styles.css`, `test_amendments.py`, `test_sjd.py`, `conftest.py`
**Pattern extraction date:** 2026-06-15
