# Phase 18: JD Composition & Live Preview — Pattern Map

**Mapped:** 2026-06-08
**Files analyzed:** 11
**Analogs found:** 10 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `v2/backend/app/models/draft_duty.py` | model | CRUD | `v2/backend/app/models/work_description.py` | role-match |
| `v2/backend/app/api/noc_mapping.py` | router | request-response | `v2/backend/app/api/og_classification.py` | exact |
| `v2/backend/app/api/wd.py` | router | CRUD | `v2/backend/app/api/wd.py` (self — add new route) | exact |
| `v2/backend/tests/test_jd_composition.py` | test | request-response | `v2/backend/tests/test_wd.py` + `test_og_classification.py` | exact |
| `v2/backend/tests/conftest.py` | test config | CRUD | `v2/backend/tests/conftest.py` (self — add fixture) | exact |
| `v2/frontend/src/components.jsx` | component | request-response | `v2/frontend/src/app.jsx` (fetch pattern) | role-match |
| `v2/frontend/src/document.jsx` | component | CRUD | `v2/frontend/src/document.jsx` (self — Sec/Ghost pattern) | exact |
| `v2/frontend/src/styles.css` | config | — | `v2/frontend/src/styles.css` (self — add class) | exact |
| `v2/frontend/src/data.jsx` | utility | — | `v2/frontend/src/data.jsx` (self — add icon key) | exact |
| `v2/frontend/src/app.jsx` | controller | request-response | `v2/frontend/src/app.jsx` (existing pipeline triggers) | exact |
| `v2/backend/app/data/constants.py` | config | — | read-only reference, no change | — |

---

## Pattern Assignments

### `v2/backend/app/models/draft_duty.py` (model, CRUD)

**Analog:** `v2/backend/app/models/work_description.py` (Pydantic model with Optional fields + ConfigDict)

**Current file** (`v2/backend/app/models/draft_duty.py`, lines 1–25):
```python
from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

class DraftDuty(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    text: str
    plain_trigger: Optional[str] = None
    source: Literal["suggested", "advisor"]
    source_index: Optional[int] = None
    refined_at: Optional[datetime] = None
```

**Extension pattern** — add provenance fields after `refined_at`. Copy the `Optional[str] = None` idiom from `WorkDescription`:
```python
# WorkDescription lines 46-52 — Optional field idiom with defaults
confirmed_og: Optional[dict] = None
og_level: Optional[int] = Field(default=None, ge=1)
reports_to_military: Optional[bool] = None
jes_scores: list[dict] = Field(default_factory=list)
jes_total_points: Optional[int] = None
```

**Required additions to `DraftDuty`** (replace `source: Literal["suggested", "advisor"]` with new Literal, append fields):
```python
source: Literal["noc", "advisor"]           # "suggested" → "noc" for Phase 18
# ProvenanceTag fields (JD-02, JD-03)
provenance_noc_code: Optional[str] = None
provenance_section: str = "Main duties"
provenance_hash: Optional[str] = None
advisor: bool = False
orphan: bool = False
orphan_rationale: Optional[str] = None
```

**Note:** `extra="ignore"` (already present) ensures old records with `source="suggested"` load without errors. All new fields are Optional — no DB migration.

---

### `v2/backend/app/api/noc_mapping.py` (router, request-response)

**Analog:** `v2/backend/app/api/og_classification.py` — stateless GET read endpoint, same router pattern.

**Imports pattern** (`og_classification.py` lines 1–25):
```python
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.data.constants import ASEC_DISAMBIGUATION, OG_DEFINITIONS, OG_LEVELS, QUAL_STANDARDS

router = APIRouter()
```

For the new duty route, the imports are:
```python
from app.config import get_settings
from app.db import get_noc_connection
```
The `router` object already exists in `noc_mapping.py` (line 19). Add the new route to the same file alongside `POST /noc/map`.

**GET endpoint pattern** (add after the existing `map_noc` route):
```python
@router.get("/noc/{noc_code}/duties")
async def get_noc_duties(noc_code: str) -> dict:
    # NOC DB — use get_noc_connection, not get_connection (different DB files)
    if not noc_code or len(noc_code) < 3:
        raise HTTPException(status_code=422, detail="noc_code must be at least 3 characters")
    settings = get_settings()
    con = get_noc_connection(settings.noc_db_path)
    try:
        rows = con.execute(
            "SELECT id, element_text, source_hash FROM noc_elements "
            "WHERE noc_code = ? AND element_type = 'Main duties' "
            "ORDER BY id",
            (noc_code,),
        ).fetchall()
    finally:
        con.close()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No Main duties found for NOC {noc_code!r}")
    return {
        "noc_code": noc_code,
        "duties": [
            {"id": row["id"], "text": row["element_text"], "source_hash": row["source_hash"] or None}
            for row in rows
        ],
    }
```

**Error handling pattern** (from `noc_mapping.py` lines 31–38 — ValueError → 422):
```python
except ValueError as exc:
    raise HTTPException(status_code=422, detail=str(exc))
```

**try/finally pattern** for connection (from `wd.py` lines 69–85 — always close in `finally`):
```python
con = get_connection(settings.db_path)
try:
    con.execute(...)
    con.commit()
finally:
    con.close()
```

---

### `v2/backend/app/api/wd.py` — `WDPatchRequest` + orphan check route (router, CRUD)

**Analog:** self — existing `patch_wd` and `get_wd` routes in the same file.

**WDPatchRequest extension** (lines 34–50) — add one field using the existing `Optional[...]` pattern:
```python
class WDPatchRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # ... existing fields ...
    jes_total_points: Optional[int] = None        # last existing field
    duties: Optional[list[dict]] = None           # NEW — Phase 18
```

**patch_wd handler** — add duties merge after the existing `for field, val` loop (lines 117–119):
```python
# Existing merge pattern (lines 117-119):
for field, val in body.model_dump(exclude_unset=True).items():
    setattr(wd, field, val)

# Add duties validation before setattr for the duties field:
if body.duties is not None:
    from app.models.draft_duty import DraftDuty as DD
    wd.duties = [DD(**d) for d in body.duties[:20]]  # cap at 20 (DoS mitigation)
```

**Orphan check route pattern** (add to `wd.py`, same router, same WD DB read pattern as `get_wd` lines 89–102):
```python
@router.post("/wd/{wd_id}/orphan_check")
async def run_orphan_check(wd_id: str) -> dict:
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
    if not wd.confirmed_og:
        raise HTTPException(status_code=422, detail="OG not confirmed — orphan check requires confirmed OG")
    og_code = wd.confirmed_og.get("og_code") if isinstance(wd.confirmed_og, dict) else wd.confirmed_og.og_code
    defn = OG_DEFINITIONS.get(og_code, {})
    exclusions_text = defn.get("exclusions", "")
    flagged = []
    for duty in wd.duties:
        duty_lower = duty.text.lower()
        if exclusions_text and _duty_contradicts_og(duty_lower, exclusions_text):
            flagged.append({
                "duty_id": duty.id,
                "orphan_rationale": f"This duty may fall outside the {og_code} functional authority: {exclusions_text[:200]}"
            })
    return {"wd_id": wd_id, "flagged": flagged}
```

**Private helper** (add above the route):
```python
def _duty_contradicts_og(duty_lower: str, exclusions_text: str) -> bool:
    """Keyword check: True if any exclusion keyword appears in duty text.

    EC exclusions are empty — will always return False for EC positions.
    IT exclusions contain keywords like 'business analysis', 'administrative programs'.
    """
    exclusion_keywords = [
        phrase.strip().lower()
        for phrase in exclusions_text.replace(';', ',').split(',')
        if len(phrase.strip()) > 4
    ]
    return any(kw in duty_lower for kw in exclusion_keywords)
```

---

### `v2/backend/tests/test_jd_composition.py` (test, request-response) — NEW FILE

**Analog:** `v2/backend/tests/test_wd.py` (CRUD flow tests) + `v2/backend/tests/test_og_classification.py` (stateless endpoint tests)

**File header and marker** (from `test_wd.py` lines 1–10):
```python
"""
test_jd_composition.py — Phase 18: JD composition backend contract.
Covers JD-01..04: duty fetch, provenance model, orphan check.
"""
import pytest

pytestmark = pytest.mark.asyncio
```

**Stateless endpoint test pattern** (from `test_og_classification.py` lines 14–21):
```python
async def test_og_classify_returns_candidates(client):
    response = await client.post("/api/og/classify", json={...})
    assert response.status_code == 200
    data = response.json()
    assert "candidates" in data
```

**404 test pattern** (from `test_og_classification.py` lines 66–69):
```python
async def test_og_definitions_404_for_unknown_code(client):
    response = await client.get("/api/og/definitions?og_code=ZZ")
    assert response.status_code == 404
```

**PATCH + POST chain test pattern** (from `test_og_classification.py` lines 86–104):
```python
async def test_patch_wd_confirmed_og_persists(client):
    create_resp = await client.post("/api/wd", json={...})
    wd_id = create_resp.json()["id"]
    patch_resp = await client.patch(f"/api/wd/{wd_id}", json={...})
    assert patch_resp.status_code == 200
```

**Phase 18 test stubs to implement** (Wave 0 RED stubs):
```python
async def test_get_noc_duties_returns_main_duties(client, noc_duties_db):
    ...  # GET /api/noc/{noc_code}/duties returns list with text + source_hash

async def test_get_noc_duties_404_for_unknown_noc(client, noc_duties_db):
    ...  # GET /api/noc/99999/duties → 404

async def test_draft_duty_provenance_fields(client):
    ...  # DraftDuty model accepts provenance_noc_code + provenance_hash

async def test_orphan_check_ec_no_flags(client, noc_duties_db):
    ...  # POST /api/wd/{id}/orphan_check with EC og → flagged: []

async def test_orphan_check_404_for_unknown_wd(client):
    ...  # POST /api/wd/does-not-exist/orphan_check → 404

async def test_patch_wd_duties_persists(client):
    ...  # PATCH /api/wd/{id} with duties[] → WD.duties populated
```

---

### `v2/backend/tests/conftest.py` — add `noc_duties_db` fixture

**Analog:** `noc_mapping_db` fixture (lines 91–189 of conftest.py) — same pattern, lighter (no vec table).

**noc_mapping_db fixture pattern** (lines 91–114, condensed):
```python
@pytest.fixture
def noc_mapping_db(tmp_path) -> str:
    import sqlite3
    import sqlite_vec as sv

    db_path = str(tmp_path / "test_noc.db")
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.enable_load_extension(True)
    sv.load(con)
    con.enable_load_extension(False)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS noc_units (...);
        CREATE TABLE IF NOT EXISTS noc_elements (...);
        ...
    """)
    con.execute("INSERT OR IGNORE INTO noc_elements(...) VALUES (...)")
    con.commit()
    con.close()
    return db_path
```

**New fixture** (lighter — no vec0 table, no FTS5 needed for duty fetch):
```python
@pytest.fixture
def noc_duties_db(tmp_path, monkeypatch) -> str:
    """Lightweight NOC DB with noc_elements rows for duty fetch tests.

    No vec0 table needed — GET /api/noc/{noc_code}/duties only reads noc_elements.
    Sets NOC_DB_PATH env var so Settings.noc_db_path resolves to this file.
    """
    import sqlite3
    import sqlite_vec as sv

    db_path = str(tmp_path / "test_noc_duties.db")
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.enable_load_extension(True)
    sv.load(con)
    con.enable_load_extension(False)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS noc_elements (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            noc_code     TEXT NOT NULL,
            element_type TEXT NOT NULL,
            element_text TEXT NOT NULL,
            source_hash  TEXT NOT NULL DEFAULT ''
        );
    """)
    con.execute(
        "INSERT INTO noc_elements(noc_code, element_type, element_text, source_hash) "
        "VALUES (?, ?, ?, ?)",
        ("21232", "Main duties", "Develop and maintain application software.", "fakehash_v1"),
    )
    con.commit()
    con.close()
    monkeypatch.setenv("NOC_DB_PATH", db_path)
    return db_path
```

**Note:** The `monkeypatch.setenv` is required so `get_settings().noc_db_path` resolves to the fixture DB. The existing `_settings_env_defaults` autouse fixture sets a default `NOC_DB_PATH`; monkeypatch overrides it for tests that request `noc_duties_db`.

---

### `v2/frontend/src/components.jsx` — DutyBuilder rewire (component, request-response)

**Analog:** `v2/frontend/src/app.jsx` — `useEffect` + `useState` fetch pattern for `nocLoading`/`ogLoading` (lines 84–87, 193–207).

**Existing fetch-with-loading pattern** (`app.jsx` lines 84–87 + 193–207):
```javascript
const [nocCandidates, setNocCandidates] = useState([]);
const [nocLoading, setNocLoading] = useState(false);
...
if (step.id === 'summary') {
  setNocLoading(true);
  setNocCandidates([]);
  fetch('/api/noc/map', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ work_description: newRecord.summary }),
  })
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(data => {
      setNocCandidates(data.candidates || []);
      setNocLoading(false);
    })
    .catch(() => { setNocLoading(false); });
}
```

**DutyBuilder: add state + useEffect** (after existing `const [preview, setPreview]` on line 111):
```javascript
const [nocDuties, setNocDuties] = useState(null); // null=loading, []=empty/error, [...]=fetched
const noc_code = cfg && cfg.noc_code;

useEffect(() => {
  if (!noc_code) return;
  setNocDuties(null); // trigger shimmer
  fetch(`/api/noc/${encodeURIComponent(noc_code)}/duties`)
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(data => setNocDuties(data.duties || []))
    .catch(() => setNocDuties([])); // error: empty array
}, [noc_code]);
```

**DutyBuilder: update toggle function** — change duty object shape from `{id, plain, polished, advisor}` to `{id, plain, text, source, provenance_noc_code, provenance_section, provenance_hash, advisor}`:
```javascript
// Old (line 120):
onChange([...list, { id: 'sug-' + s.plain, plain: s.plain, polished: s.polished, advisor: false }]);

// New (NOC duty toggle):
const newDuty = {
  id: `noc-${d.id}`,
  plain: d.text,
  text: d.text,
  source: 'noc',
  advisor: false,
  provenance_noc_code: noc_code,
  provenance_section: 'Main duties',
  provenance_hash: d.source_hash || null,
};
onChange([...list, newDuty]);
```

**DutyBuilder: update advisor-added duty** (line 126):
```javascript
// Old:
onChange([...list, { id: 'adv-' + Date.now(), plain: raw, polished, advisor: true }]);

// New:
onChange([...list, {
  id: `adv-${Date.now()}`,
  plain: raw,
  text: polished,         // refineDuty(raw) result lives in text field
  source: 'advisor',
  advisor: true,
  provenance_noc_code: null,
  provenance_section: null,
  provenance_hash: null,
}]);
```

**DutyBuilder: rendering** — replace `suggestions.map(s => ...)` block with `nocDuties` when `noc_code` is present. Shimmer state: render `<Ghost lines={3} />` when `nocDuties === null`. Tag copy: `'NOC 2021 · ' + noc_code` (not "refined for the description").

**Advisor-added tag copy** — line 149: change `refined from your words` to `advisor-added`.

**DUTY_PLACEHOLDER constant** — line 7: change to `'Describe a duty not listed above…'`.

---

### `v2/frontend/src/document.jsx` — Section 3 + Section 5 updates (component, CRUD)

**Analog:** self — existing `Sec`, `Ghost`, section render pattern.

**Section 3 current state** (lines 232–255):
```jsx
<Sec
  key="du" n={String(n)} title="Key Responsibilities"
  src={hasDuties ? 'NOC 2021 · refined' : null} ghost={!hasDuties} fresh={isFresh('duties')}
  editable={reviewing} onEdit={() => onEditStep('duties')}
>
  {hasDuties
    ? (
      <ul className="doc-duties">
        {r.duties.map(d => (
          <li key={d.id} className={`doc-duty${d.advisor ? ' is-advisor' : ''}`}>
            {d.polished}
          </li>
        ))}
      </ul>
    )
    : (
      <div>
        <Ghost lines={2} />
        <p className="ghost-note">Your responsibilities will appear here, formally worded.</p>
      </div>
    )}
</Sec>
```

**Section 3 Phase 18 changes:**
1. `src` pill: `'NOC 2021 · refined'` → `'NOC 2021'` (remove "· refined")
2. Duty render: `{d.polished}` → `{d.text}` (verbatim NOC text)
3. Ghost note copy: `"Your responsibilities will appear here, formally worded."` → `"Select duties from the NOC list — they will appear here, verbatim and traceable."`
4. Orphan badge (review only): add inside `<li>` after duty text:
```jsx
{d.orphan && reviewing && <OrphanBadge rationale={d.orphan_rationale} />}
```

**OrphanBadge component** (new, add near top of file after `Ghost`):
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

Note: `Icon` is imported from `components.jsx` (line 6 of document.jsx already has this import). `I` is imported from `data.jsx` — add `I` to the existing import on line 5.

**Section 5 (Essential Qualifications) — DOC-01 fix** (lines 337–362):
Change from conditional `if (r.qualsVisited)` to always render with ghost state:
```jsx
// OLD (line 337):
if (r.qualsVisited) {
  n++;
  sections.push(<Sec key="q" n={String(n)} ...>...</Sec>);
}

// NEW:
n++;
sections.push(
  <Sec
    key="q" n={String(n)} title="Essential Qualifications"
    src="TBS Qualification Standard" ghost={!r.qualsVisited} fresh={isFresh('quals')}
    editable={reviewing} onEdit={() => onEditStep('quals')}
  >
    {r.qualsVisited
      ? <div>...</div>   // existing qual content
      : <Ghost lines={3} />}
  </Sec>
);
```

**Export `OrphanBadge`** — add to the existing named exports at the bottom of document.jsx so tests can import it directly.

---

### `v2/frontend/src/styles.css` — add `.orphan-badge` (config)

**Analog:** existing `.prov__tag` and `.duty-sug__tag` classes — same monospace 11px font, same `border-radius: var(--radius-sm)`, same inline-flex layout.

**New class to append** (exact spec from UI-SPEC Section B):
```css
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
.orphan-badge__icon { flex: 0 0 auto; }
.orphan-badge__body {}
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
  letter-spacing: 0;
  text-transform: none;
  color: oklch(0.50 0.10 35);
}
```

Append after the existing `.prov` / `.prov__tag` block.

---

### `v2/frontend/src/data.jsx` — add `warn` icon (utility)

**Analog:** existing `I` object (lines 9–24) — same inline SVG path string pattern.

**Icon object pattern** (lines 9–11):
```javascript
const I = {
  spark: '<path d="..." fill="currentColor"/>',
  check: '<path d="..." fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
  ...
```

**Add `warn` key** (insert after `shield` on line 23):
```javascript
warn: '<path d="M10 3L18 17H2L10 3z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><line x1="10" y1="9" x2="10" y2="13" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="10" cy="15" r="0.8" fill="currentColor"/>',
```

Note: `I` is declared with `const` on line 9 but is not exported at the module level — it is used within `data.jsx` directly and re-exported via named exports at the bottom. Confirm the existing export pattern before adding `warn`.

---

### `v2/frontend/src/app.jsx` — wire orphan check + duties in PATCH (controller, request-response)

**Analog:** self — existing pipeline triggers in `commit()` (lines 192–275) and `stepCfgOverride` (lines 404–416).

**cfgOverride for duties step** (lines 413–415) — replace static suggestions injection:
```javascript
// OLD (line 413-415):
: step.id === 'duties'
  ? { ...step.input, suggestions: getDutySuggestions(answers) }
  : undefined

// NEW:
: step.id === 'duties'
  ? { ...step.input, noc_code: record.confirmed_noc
        ? (typeof record.confirmed_noc === 'string'
            ? record.confirmed_noc
            : record.confirmed_noc?.noc_code || null)
        : null }
  : undefined
```

**duties in PATCH payload** — in `commit()` after the `wdPayload` construction (lines 159–167), add duties to the hoisted fields:
```javascript
// Existing hoisted fields (line 164-166):
['confirmed_noc', 'confirmed_og', 'og_level', 'reports_to_military',
 'jes_scores', 'jes_total_points'].forEach(k => {
  if (k in newRecord) wdPayload[k] = newRecord[k];
});

// Also hoist duties when committing the duties step:
if (step.id === 'duties' && newRecord.duties) {
  wdPayload.duties = newRecord.duties;
}
```

**Orphan check trigger** — add a new `useEffect` (after the `wd_id` persistence effect, around line 106):
```javascript
// Orphan check: fire automatically when reviewing becomes true AND duties + confirmed_og present
const [orphanFlags, setOrphanFlags] = useState([]);

useEffect(() => {
  if (!reviewing || !wd_id || !record.duties?.length || !record.confirmed_og) return;
  fetch(`/api/wd/${wd_id}/orphan_check`, { method: 'POST' })
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(data => {
      if (data.flagged && data.flagged.length > 0) {
        // Merge orphan flags into record.duties
        setRecord(prev => ({
          ...prev,
          duties: (prev.duties || []).map(d => {
            const flag = data.flagged.find(f => f.duty_id === d.id);
            return flag ? { ...d, orphan: true, orphan_rationale: flag.orphan_rationale } : d;
          }),
        }));
      }
      setOrphanFlags(data.flagged || []);
    })
    .catch(() => {});
}, [reviewing, wd_id]);
```

**Existing pipeline trigger pattern to copy** (`app.jsx` lines 209–231 — OG pipeline):
```javascript
if (step.id === 'noc_confirm') {
  setOgLoading(true);
  setOgCandidates([]);
  setOgAlert(null);
  fetch('/api/og/classify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({...}),
  })
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(data => {
      setOgCandidates(data.candidates || []);
      setOgAlert(data.asec_alert || null);
      setOgLoading(false);
    })
    .catch(() => { setOgLoading(false); });
}
```

**Pass orphan data down to DocumentPane** — `DocumentPane` already receives `record` as a prop; since orphan flags are merged into `record.duties`, no new prop is needed. The `reviewing` prop already flows through.

---

## Shared Patterns

### Connection Factory Selection
**Source:** `v2/backend/app/db.py` lines 17–87
**Apply to:** `noc_mapping.py` new route, `wd.py` orphan check route

```python
# WD DB (work_descriptions table):
con = get_connection(settings.db_path)

# NOC DB (noc_elements table) — MUST use this, not get_connection():
con = get_noc_connection(settings.noc_db_path)
```

Always close in `finally` block. Never use `get_noc_connection` for WD reads or vice versa.

### Backend Error Handling
**Source:** `v2/backend/app/api/wd.py` lines 89–102, `og_classification.py` lines 150–160
**Apply to:** all new backend routes

```python
# 404 pattern:
if row is None:
    raise HTTPException(status_code=404, detail="Work description not found")

# Validation error pattern:
raise HTTPException(status_code=422, detail="...")

# try/finally connection close (never omit the finally):
con = get_connection(settings.db_path)
try:
    row = con.execute(...).fetchone()
finally:
    con.close()
```

### Frontend Fetch with Loading State
**Source:** `v2/frontend/src/app.jsx` lines 84–87, 193–207
**Apply to:** `DutyBuilder` in `components.jsx`, orphan check `useEffect` in `app.jsx`

```javascript
// State pair:
const [data, setData] = useState(null);  // null = loading
const [loading, setLoading] = useState(false);

// useEffect fetch:
useEffect(() => {
  if (!trigger) return;
  setData(null);  // reset to shimmer state
  fetch(url)
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(d => setData(d))
    .catch(() => setData([]));
}, [trigger]);
```

### Pydantic Model Extension (extra="ignore" + Optional defaults)
**Source:** `v2/backend/app/models/work_description.py` lines 29–55
**Apply to:** `DraftDuty` extension, `WDPatchRequest` extension

```python
class Model(BaseModel):
    model_config = ConfigDict(extra="ignore")  # old records load without error
    # New optional fields always have defaults:
    new_field: Optional[str] = None
    new_bool: bool = False
```

### Test Structure (async, pytestmark, client fixture)
**Source:** `v2/backend/tests/test_wd.py` lines 1–10, `test_og_classification.py` lines 1–10
**Apply to:** `test_jd_composition.py`

```python
"""module docstring"""
import pytest

pytestmark = pytest.mark.asyncio

async def test_something(client):
    response = await client.get("/api/...")
    assert response.status_code == 200
    data = response.json()
    assert "field" in data
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `_duty_contradicts_og()` helper | utility | transform | No existing keyword-matching utility in the codebase; straightforward to implement from scratch per RESEARCH.md Pattern 4 |

---

## Metadata

**Analog search scope:** `v2/backend/app/`, `v2/backend/tests/`, `v2/frontend/src/`
**Files scanned:** 14
**Pattern extraction date:** 2026-06-08
