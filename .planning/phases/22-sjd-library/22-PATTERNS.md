# Phase 22: SJD Library - Pattern Map

**Mapped:** 2026-06-11
**Files analyzed:** 10 (3 new, 7 modified)
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `v2/backend/app/data/sjd_library.py` | data/constant | transform (parse-at-import) | `v2/backend/app/data/constants.py` | role-match |
| `v2/backend/app/api/sjd.py` | controller | request-response (read-only GET) | `v2/backend/app/api/og_classification.py` | exact |
| `v2/backend/tests/test_sjd.py` | test | request-response | `v2/backend/tests/test_og_classification.py` + `test_wd.py` | exact |
| `v2/backend/app/api/wd.py` | controller | CRUD (POST mutation) | `v2/backend/app/api/wd.py` — `orphan_check` + `confirm-subgroup` | exact |
| `v2/backend/app/models/draft_duty.py` | model | — | self (extend existing) | exact |
| `v2/backend/app/models/work_description.py` | model | — | self (extend existing) | exact |
| `v2/backend/app/services/export_service.py` | service | transform | self — `_build_v2_manifest` | exact |
| `v2/backend/app/main.py` / `app/api/__init__.py` | config/router | — | `v2/backend/app/api/__init__.py` | exact |
| `v2/frontend/src/app.jsx` | component | request-response + state | self (extend commit/toast patterns) | exact |
| `v2/frontend/src/data.jsx` | utility | request-response | self — existing exports block | exact |

---

## Pattern Assignments

### `v2/backend/app/data/sjd_library.py` (data constant, transform)

**Analog:** `v2/backend/app/data/constants.py` (module-level constant, no DB, parse-at-import)

**Module-level constant pattern** (`constants.py` lines 1–20):
```python
# Source: verified against <data source>
"""
app/data/sjd_library.py — description of what lives here.
"""
from __future__ import annotations
```

**Data file location convention:** The raw data file (`data/SJD Examples.txt`) is accessed by path relative to the project root. Use `pathlib.Path(__file__).parent.parent.parent.parent / "data" / "SJD Examples.txt"` — four parents up from `app/data/` reaches the repo root alongside the `data/` directory. Verify with `os.path.exists` at module load and raise `FileNotFoundError` if absent.

**Dataclass pattern** (from RESEARCH.md Code Examples — use `dataclass(frozen=True)` for immutable constant entries):
```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class SJDEntry:
    sjd_number: str          # e.g. "DND-PA-57047"
    job_code: str
    title: str
    og_code: str             # normalized: "AS", "FI", "EC", "IT", "EN", "PE", "WP"
    og_level: int            # bare integer: 1, 3, 7, 4, 2, 5, 4, 3, 4, 3
    group_level_str: str     # original: "AS-01"
    supervisory: bool
    noc_code: str
    salary_range: str
    organizational_context: str
    streams: str

SJD_LIBRARY: list[SJDEntry] = _parse_sjd_file(_SJD_FILE_PATH)
```

**OG normalization helper** (RESEARCH.md Code Examples — VERIFIED pattern):
```python
def _og_code_from_group_level(group_level: str) -> tuple[str, int]:
    gl = group_level.strip()
    if gl.startswith("CT-FIN-"):
        return ("FI", int(gl.split("-")[-1]))
    if gl.startswith("EN-ENG-"):
        return ("EN", int(gl.split("-")[-1]))
    parts = gl.split("-")
    if len(parts) >= 2:
        return (parts[0], int(parts[-1]))
    return (gl, 1)
```

---

### `v2/backend/app/api/sjd.py` (controller, request-response, read-only GET)

**Analog:** `v2/backend/app/api/og_classification.py`

**Imports pattern** (`og_classification.py` lines 22–41):
```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.data.sjd_library import SJD_LIBRARY, SJDEntry

router = APIRouter()
```

**Read-only GET with query filter pattern** (`og_classification.py` lines 224–239 — `get_og_definition` / `get_qual_default`):
```python
@router.get("/og/definitions")
async def get_og_definition(og_code: str) -> OGDefinitionResponse:
    if og_code not in OG_DEFINITIONS:
        raise HTTPException(status_code=404, detail=f"OG code {og_code!r} not found")
    defn = OG_DEFINITIONS[og_code]
    return OGDefinitionResponse(...)
```

**Apply this pattern to SJD GET endpoints:**
```python
@router.get("/sjd")
def list_sjds(og_code: str = Query(default=None)):
    entries = SJD_LIBRARY
    if og_code:
        entries = [e for e in entries if e.og_code.upper() == og_code.upper()]
    import dataclasses
    return [dataclasses.asdict(e) for e in entries]

@router.get("/sjd/{sjd_number}")
def get_sjd(sjd_number: str):
    entry = next((e for e in SJD_LIBRARY if e.sjd_number == sjd_number), None)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"SJD {sjd_number!r} not found")
    import dataclasses
    return dataclasses.asdict(entry)
```

**404 error pattern** — use `!r` repr formatting, same as `og_classification.py` line 231:
```python
raise HTTPException(status_code=404, detail=f"SJD {sjd_number!r} not found")
```

---

### `v2/backend/tests/test_sjd.py` (test, request-response)

**Analog:** `v2/backend/tests/test_og_classification.py` (GET endpoint tests) + `v2/backend/tests/test_wd.py` (POST mutation tests with DB fixture)

**File header + pytestmark pattern** (`test_og_classification.py` lines 1–11):
```python
"""
test_sjd.py — SJD-01 / SJD-02 requirements tests.
"""
import pytest

pytestmark = pytest.mark.asyncio
```

**GET endpoint test pattern** (`test_og_classification.py` lines 14–28):
```python
async def test_og_definitions_returns_ec_definition(client):
    response = await client.get("/api/og/definitions?og_code=EC")
    assert response.status_code == 200
    data = response.json()
    assert data["og_code"] == "EC"
    assert len(data["definition"]) > 20

async def test_og_definitions_404_for_unknown_code(client):
    response = await client.get("/api/og/definitions?og_code=ZZ")
    assert response.status_code == 404
```

**POST with DB setup pattern** (`test_wd.py` lines 12–56 — create WD first, then test mutation):
```python
async def test_patch_wd_updates_step_index(client):
    create_resp = await client.post("/api/wd", json={...})
    wd_id = create_resp.json()["id"]
    patch_resp = await client.patch(f"/api/wd/{wd_id}", json={"step_index": 3})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["step_index"] == 3
```

**Test fixture:** All tests use the shared `client` fixture from `conftest.py`. No additional fixtures are needed — `sjd-start` tests create a WD first using `POST /api/wd`.

**Unit test for SJD_LIBRARY constant** (no `client` needed — direct import):
```python
def test_sjd_library_count():
    from app.data.sjd_library import SJD_LIBRARY
    assert len(SJD_LIBRARY) >= 9
    assert all(hasattr(e, 'sjd_number') for e in SJD_LIBRARY)
```

---

### `v2/backend/app/api/wd.py` — Add `POST /api/wd/{id}/sjd-start` (controller, CRUD mutation)

**Analog:** `run_orphan_check` (`wd.py` lines 173–212) and `confirm_subgroup` (`og_classification.py` lines 259–336) — both are POST actions on an existing WD that read-modify-write the SQLite row.

**Request body model pattern** (`og_classification.py` lines 121–127):
```python
class SubGroupConfirmRequest(BaseModel):
    sub_group: str = Field(min_length=1, max_length=10)
```

Apply:
```python
class SJDStartRequest(BaseModel):
    sjd_number: str
```

**Read-modify-write pattern** (`og_classification.py` lines 268–336, full `confirm_subgroup`):
```python
@router.post("/wd/{wd_id}/confirm-subgroup")
async def confirm_subgroup(wd_id: str, body: SubGroupConfirmRequest) -> dict:
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Work description {wd_id!r} not found")
        wd = WorkDescription.model_validate_json(row["data"])
        # ... mutate wd fields ...
        wd.last_modified = datetime.now(timezone.utc)
        con.execute(
            "UPDATE work_descriptions SET data = ?, last_modified = ? WHERE id = ?",
            (wd.model_dump_json(), wd.last_modified.isoformat(), wd_id),
        )
        con.commit()
    finally:
        con.close()
    return {"status": "ok", ...}
```

**Return type:** `sjd-start` should return the updated `WorkDescription` (not `dict`) so the SPA can update its local state in one round-trip — follow the `patch_wd` return pattern (`wd.py` line 156: `return wd`).

**Import placement:** Import `SJD_LIBRARY` inside the function body (lazy import), same as `from app.data.constants import OG_DEFINITIONS` inside `run_orphan_check` (line 180).

---

### `v2/backend/app/models/draft_duty.py` — Extend `source` + add `sjd_number` (model, extend)

**Analog:** Self (`draft_duty.py` lines 1–33 — full file, already read)

**Current source Literal** (`draft_duty.py` line 22):
```python
source: Literal["noc", "advisor"]
```
Extend to:
```python
source: Literal["noc", "advisor", "sjd"]
```

**Add new Optional field** — follow `provenance_noc_code` pattern (`draft_duty.py` line 26):
```python
provenance_noc_code: Optional[str] = None
```
Add after `source_index`:
```python
sjd_number: Optional[str] = None  # e.g. "DND-PA-57047" — set when source="sjd"
```

**Backward compatibility note:** `ConfigDict(extra="ignore")` on line 17 means existing DB rows with `source="noc"/"advisor"` continue to deserialize without error. The Literal extension is additive-only.

---

### `v2/backend/app/models/work_description.py` — Add `sjd_source` field (model, extend)

**Analog:** Self (`work_description.py` lines 1–61 — full file, already read)

**Optional field pattern** — follow `confirmed_sub_group` (`work_description.py` line 53):
```python
confirmed_sub_group: Optional[str] = None  # Phase 21: NU/SW/ED sub-group
```
Add after `og_level`:
```python
sjd_source: Optional[dict] = None  # Phase 22: {sjd_number, title, og_code, og_level}
```

---

### `v2/backend/app/services/export_service.py` — Extend `_build_v2_manifest` (service, transform)

**Analog:** Self (`export_service.py` lines 149–199 — `_build_v2_manifest`)

**`_add` helper pattern** (`export_service.py` lines 164–176):
```python
def _add(source_type: str, source_id: str, source_version: str) -> None:
    key = (source_type, source_id, source_version)
    if key in seen:
        return
    seen.add(key)
    manifest.append({
        "source_type": source_type,
        "source_id": source_id,
        "source_version": source_version,
        "retrieved_date": str(date.today()),
    })
```

**Existing guard pattern** (`export_service.py` lines 192–197):
```python
if wd.confirmed_og:
    _add("OG", "TBS OG Definitions", "TBS OG Definitions 2024")
if wd.qualification:
    _add("QUAL", "TBS Qualification Standard", "TBS Qualification Standard 2024")
```

Add after these existing guards:
```python
if wd.sjd_source:
    sjd_num = wd.sjd_source.get("sjd_number", "")
    if sjd_num:
        _add("SJD", sjd_num, "DND SJD Library")
```

**Deduplication is already handled** by the `seen` set — multiple duties from the same SJD will not produce duplicate manifest entries.

---

### `v2/backend/app/api/__init__.py` — Register `sjd` router (config)

**Analog:** `v2/backend/app/api/__init__.py` lines 1–27 (full file, already read)

**Router registration pattern** (`__init__.py` lines 16–25):
```python
from . import health, noc_mapping, wd, og_classification, jes_scoring, amendments, export

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(noc_mapping.router)
api_router.include_router(wd.router)
api_router.include_router(og_classification.router)
api_router.include_router(jes_scoring.router)
api_router.include_router(amendments.router)
api_router.include_router(export.router)
```

Extend the import line and add one `include_router` call:
```python
from . import health, noc_mapping, wd, og_classification, jes_scoring, amendments, export, sjd
# ...
api_router.include_router(sjd.router)
```

`app/main.py` does not need modification — it imports `api_router` from `app.api` which already aggregates all routers.

---

### `v2/frontend/src/app.jsx` — Add Browse SJDs action + SJD-03 warning (component)

**Analog:** Self (`app.jsx`) — extend existing `commit()` and `toast` patterns

**Toast pattern** (`app.jsx` lines 84, 440–441, 464–465):
```javascript
const [toast, setToast] = useState(null);
// ...
setToast('Job description copied to clipboard');
setTimeout(() => setToast(null), 2600);
// For longer messages:
setToast('Complete the OG group and level steps before exporting.');
setTimeout(() => setToast(null), 5000);
```

**SJD-03 warning** — insert inside `commit()` after `const newRecord = { ...record, ...patch }` (around line 196), before the WD persistence block:
```javascript
// SJD-03: warn if confirmed_og changes after an SJD pre-fill
if (step.id === 'og_confirm' && record.sjd_source) {
  const newOgCode = typeof patch.confirmed_og === 'object'
    ? patch.confirmed_og?.og_code
    : patch.confirmed_og;
  const sjdOgCode = record.sjd_source?.og_code;
  if (newOgCode && sjdOgCode && newOgCode !== sjdOgCode) {
    setToast('Departing from the SJD classification turns this into a new evaluation — the SJD decision no longer applies');
    setTimeout(() => setToast(null), 7000);
  }
}
```

**API call pattern** (`app.jsx` lines 237–255 — POST/PATCH WD):
```javascript
fetch('/api/wd', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(wdPayload),
})
  .then(r => r.ok ? r.json() : Promise.reject(r.status))
  .then(data => { /* update state */ })
```

Apply for sjd-start call (inside Browse SJDs handler):
```javascript
fetch(`/api/wd/${wd_id}/sjd-start`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ sjd_number: selectedEntry.sjd_number }),
})
  .then(r => r.ok ? r.json() : Promise.reject(r))
  .then(updatedWd => {
    setRecord(updatedWd.record || {});
    // mirror sjd_source, confirmed_og, og_level back into record
    setRecord(prev => ({
      ...prev,
      sjd_source: updatedWd.sjd_source,
      confirmed_og: updatedWd.confirmed_og,
      og_level: updatedWd.og_level,
      duties: updatedWd.duties,
    }));
  })
  .catch(() => setToast('Could not load SJD — try again.'));
```

**Guard before showing Browse SJDs action:** `wd_id` must exist. Pattern from `app.jsx` line 444:
```javascript
if (!wd_id) {
  setToast('Save your work description first before exporting.');
  ...
  return;
}
```

**Phase detection for placement:** After Role phase (phase 0), before Work Type (phase 1). The current step's `phase` property is available as `step.phase`. Show "Browse SJDs" when `stepIndex >= 5` (first phase-1 step) and the record has the 5 phase-0 answers (`title`, `branch`, `reports`, `reports_to_military`, `supervises` in `answers`).

---

### `v2/frontend/src/data.jsx` — Add `fetchSjds()` and `fetchSjdDetail()` (utility, request-response)

**Analog:** Self — extend the existing `export { ... }` block (`data.jsx` lines 648–654)

**Export pattern** (`data.jsx` lines 648–654):
```javascript
export {
  I, STEPS, PHASES, OG_LEVELS, DRF, WORK_TYPES, DUTY_SUGGESTIONS,
  QUAL_DEFAULT, QUAL_DEFAULTS, getQualDefault,
  EC_ELEMENTS, computeClassification, refineDuty, ecFactors,
  accumulateSignals, getDutySuggestions,
  isStepVisible, getVisibleSteps,
};
```

Add two async fetch helpers — either as named exports in `data.jsx` or inline in `app.jsx` (RESEARCH.md says "or inline in app.jsx"). Prefer `data.jsx` to keep fetch logic co-located with other data functions:

```javascript
async function fetchSjds(ogCode = null) {
  const url = ogCode ? `/api/sjd?og_code=${encodeURIComponent(ogCode)}` : '/api/sjd';
  const r = await fetch(url);
  if (!r.ok) throw new Error(`fetchSjds: ${r.status}`);
  return r.json();
}

async function fetchSjdDetail(sjdNumber) {
  const r = await fetch(`/api/sjd/${encodeURIComponent(sjdNumber)}`);
  if (!r.ok) throw new Error(`fetchSjdDetail: ${r.status}`);
  return r.json();
}
```

Extend the export block:
```javascript
export {
  // ... existing exports ...
  fetchSjds, fetchSjdDetail,
};
```

And extend the import in `app.jsx` line 5:
```javascript
import { STEPS, PHASES, ..., fetchSjds, fetchSjdDetail } from './data.jsx';
```

---

## Shared Patterns

### DB Read-Modify-Write
**Source:** `v2/backend/app/api/og_classification.py` lines 268–336 (`confirm_subgroup`) and `v2/backend/app/api/wd.py` lines 114–156 (`patch_wd`)
**Apply to:** `POST /api/wd/{id}/sjd-start`
```python
settings = get_settings()
con = get_connection(settings.db_path)
try:
    row = con.execute("SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Work description not found")
    wd = WorkDescription.model_validate_json(row["data"])
    # ... mutate wd ...
    wd.last_modified = datetime.now(timezone.utc)
    con.execute(
        "UPDATE work_descriptions SET data = ?, last_modified = ? WHERE id = ?",
        (wd.model_dump_json(), wd.last_modified.isoformat(), wd_id),
    )
    con.commit()
finally:
    con.close()
return wd
```

### 404 Lookup Pattern
**Source:** `v2/backend/app/api/og_classification.py` lines 229–232
**Apply to:** Both SJD GET endpoints and `sjd-start`
```python
if code not in COLLECTION:
    raise HTTPException(status_code=404, detail=f"Item {code!r} not found")
```

### Datetime Stamping
**Source:** `v2/backend/app/api/og_classification.py` line 329 and `wd.py` line 148
**Apply to:** `sjd-start` before DB write
```python
from datetime import datetime, timezone
wd.last_modified = datetime.now(timezone.utc)
```

### Test Client Fixture
**Source:** `v2/backend/tests/conftest.py` lines 88–93
**Apply to:** All `test_sjd.py` tests — use `client` fixture as-is, no new fixtures needed
```python
@pytest_asyncio.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

### Frontend Toast
**Source:** `v2/frontend/src/app.jsx` lines 440–441, 484–485
**Apply to:** SJD-03 warning and sjd-start error handling
```javascript
setToast('message text');
setTimeout(() => setToast(null), 7000);  // use 7000ms for longer advisory messages
```

---

## No Analog Found

None. All files have a clear analog in the existing codebase.

---

## Metadata

**Analog search scope:** `v2/backend/app/api/`, `v2/backend/app/models/`, `v2/backend/app/services/`, `v2/backend/app/data/`, `v2/backend/tests/`, `v2/frontend/src/`
**Files scanned:** 14 source files read in full or by targeted range
**Pattern extraction date:** 2026-06-11
