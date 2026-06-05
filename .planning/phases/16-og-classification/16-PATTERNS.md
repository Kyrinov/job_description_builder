# Phase 16: OG Classification — Pattern Map

**Mapped:** 2026-06-05
**Files analyzed:** 11 new/modified files
**Analogs found:** 11 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `v2/backend/app/data/constants.py` | config | transform | same file (OG_LEVELS block) | exact |
| `v2/backend/app/api/og_classification.py` | route | request-response | `v2/backend/app/api/noc_mapping.py` | role-match |
| `v2/backend/app/services/og_service.py` / `classification_gate.py` | service/utility | transform | `v2/backend/app/api/noc_mapping.py` (inline logic) | partial |
| `v2/backend/app/models/work_description.py` | model | CRUD | same file (confirmed_noc field pattern) | exact |
| `v2/backend/app/api/wd.py` | route | CRUD | same file (WDPatchRequest + patch_wd) | exact |
| `v2/backend/app/api/__init__.py` | config | — | same file (health/noc_mapping/wd registration) | exact |
| `v2/backend/tests/test_og_classification.py` | test | request-response | `v2/backend/tests/test_wd.py` + `test_noc_pipeline.py` | role-match |
| `v2/frontend/src/data.jsx` | config/data | transform | same file (noc_confirm STEP + OG_LEVELS constant) | exact |
| `v2/frontend/src/components.jsx` | component | request-response | same file (NocConfirmList + ChoiceList) | exact |
| `v2/frontend/src/app.jsx` | component | event-driven | same file (nocCandidates cfgOverride pattern) | exact |
| `v2/frontend/src/conversation.test.jsx` | test | — | same file (CONVO-04 stub structure) | exact |

---

## Pattern Assignments

### `v2/backend/app/data/constants.py` — add OG_DEFINITIONS, QUAL_STANDARDS, ASEC_DISAMBIGUATION

**Analog:** Same file, OG_LEVELS and CAF_RANK_OG_EQUIVALENCE blocks (lines 1–152)

**Existing block header pattern** (lines 24–51):
```python
# ---------------------------------------------------------------------------
# OG_LEVELS
# Correct OG level ranges derived from data/rates_of_pay/ CSV files.
# Key: OG group code (string). Value: list of level integers (1-indexed).
#
# V1.0 bugs corrected here:
#   EC: was range(1, 8) = [1..7], now range(1, 9) = [1..8]  (EC-01 to EC-08)
# ---------------------------------------------------------------------------

OG_LEVELS: dict[str, list[int]] = {
    "EC": list(range(1, 9)),   # EC-01 to EC-08 — EC_rates.csv
    ...
}
```

**New constant shape to copy:**
```python
# ---------------------------------------------------------------------------
# OG_DEFINITIONS
# Verbatim group definitions for OG classification. Source: data/Job_evaluation/
# EC definition VERIFIED from EC Economics and Social Science Services - Job
# Evaluation Standard 2017.txt. AS/IT/FI sourced from TBS OCHRO group definitions.
# Key: OG code (string). Value: dict with og_name, definition, inclusions, exclusions.
# ---------------------------------------------------------------------------

OG_DEFINITIONS: dict[str, dict] = {
    "EC": {
        "og_name": "Economics and Social Science Services",
        "definition": "The EC Group comprises positions primarily involved in the conduct of surveys, studies and projects in the social sciences; the identification, description and organization of archival, library, museum and gallery materials; the editing of legislation or the provision of advice on legal problems in specific fields; and the application of a comprehensive knowledge of economics, sociology or statistics to the conduct of economic, socio-economic and sociological research, studies, forecasts and surveys.",
        "inclusions": "...",   # verbatim from EC JES 2017 — must be sourced in Wave 0
        "exclusions": "...",   # verbatim from EC JES 2017 — must be sourced in Wave 0
    },
    "AS": { ... },
    "IT": { ... },
    "FI": { ... },
    # stub entries for all OG_LEVELS codes not in focus groups
}

# ---------------------------------------------------------------------------
# ASEC_DISAMBIGUATION
# Displayed verbatim when both AS and EC appear in the top-3 OG candidates.
# Sourced from OG_DEFINITIONS EC + AS definition excerpts.
# ---------------------------------------------------------------------------

ASEC_DISAMBIGUATION: dict = {
    "disambiguation_text": "...",   # EC + AS group definition excerpt + distinction guidance
    "citation": "TBS OCHRO Occupational Group Definitions",
}

# ---------------------------------------------------------------------------
# QUAL_STANDARDS
# Default qualification standard text per OG group. Source: TBS Qualification
# Standards reference. Minimum coverage: EC, AS, IT, FI.
# ---------------------------------------------------------------------------

QUAL_STANDARDS: dict[str, dict] = {
    "EC": {
        "education": "...",
        "experience": "...",
        "source": "TBS Qualification Standard for EC",
    },
    "AS": { ... },
    "IT": { ... },
    "FI": { ... },
}
```

**Key conventions observed in the file (apply to all new blocks):**
- `from __future__ import annotations` at top (line 11)
- Block separator: 75-dash comment line
- Block header comment: source file, verification date, key/value description
- Type annotations on dict constants: `dict[str, dict]`, `dict[str, list[int]]`
- No imports from external packages — pure Python stdlib + `__future__`

---

### `v2/backend/app/api/og_classification.py` — new route file

**Analog:** `v2/backend/app/api/noc_mapping.py` (lines 1–51)

**Docstring + imports pattern** (lines 1–18):
```python
"""
app/api/noc_mapping.py — POST /api/noc/map — NL→NOC mapping endpoint.

JSON-only (no HTMX). Accepts a free-text work description, runs the three-stage
pipeline (FTS5 → sqlite-vec rerank → LLM justification), and returns top candidates.

The route does NOT persist candidates to the WD database — that happens in Phase 15
when the advisor commits the NOC step via PATCH /api/wd/{id}. This endpoint is
stateless: call it, get candidates, SPA handles selection.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.models.noc import NocCandidateOut, NocMapResponse, WorkDescriptionRequest
from app.services.noc_mapper import map_work_description

router = APIRouter()
```

**New file adapts to:**
```python
"""
app/api/og_classification.py — OG classification endpoints.

POST /api/og/classify — deterministic signal-based OG ranking (no LLM).
GET /api/og/definitions — returns verbatim OG definition from OG_DEFINITIONS constant.
GET /api/quals/default — returns TBS qual standard text from QUAL_STANDARDS constant.

All classification is deterministic: signal_tally from frontend QUESTION_BANK answers
is the ranking mechanism. No instructor, no Ollama calls in this module.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.data.constants import OG_LEVELS, OG_DEFINITIONS, ASEC_DISAMBIGUATION, QUAL_STANDARDS

router = APIRouter()
```

**Route handler pattern** (noc_mapping.py lines 22–51):
```python
@router.post("/noc/map", response_model=NocMapResponse)
async def map_noc(body: WorkDescriptionRequest) -> NocMapResponse:
    """Run the three-stage NL→NOC pipeline and return top candidates."""
    settings = get_settings()
    try:
        result = await map_work_description(
            work_description=body.work_description,
            noc_db_path=settings.noc_db_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    ...
    return NocMapResponse(candidates=candidates_out)
```

**New route pattern for og_classification.py:**
```python
@router.post("/og/classify")
async def classify_og(body: OGClassifyRequest) -> OGClassifyResponse:
    ranked = _rank_og_candidates(body.signal_tally, body.confirmed_noc_code)
    candidates = []
    for rank_idx, (og_code, confidence) in enumerate(ranked, start=1):
        defn = OG_DEFINITIONS.get(og_code, {})
        candidates.append(OGCandidate(
            og_code=og_code,
            og_name=defn.get("og_name", og_code),
            rank=rank_idx,
            confidence=confidence,
            rationale=_build_rationale(og_code, body.signal_tally, defn),
            evidence_quotes=[],
            definition_excerpt=defn.get("definition", "")[:400],
            relevant_inclusions=defn.get("inclusions", "")[:400],
            relevant_exclusions=defn.get("exclusions", "")[:300],
            available_levels=OG_LEVELS.get(og_code, []),
        ))
    asec_alert = None
    og_codes_in_top3 = {c.og_code for c in candidates}
    if "AS" in og_codes_in_top3 and "EC" in og_codes_in_top3:
        asec_alert = ASECAlert(**ASEC_DISAMBIGUATION)
    return OGClassifyResponse(candidates=candidates, asec_alert=asec_alert)

@router.get("/og/definitions")
async def get_og_definition(og_code: str) -> OGDefinitionResponse:
    if og_code not in OG_DEFINITIONS:
        raise HTTPException(status_code=404, detail=f"OG code {og_code!r} not found")
    defn = OG_DEFINITIONS[og_code]
    return OGDefinitionResponse(og_code=og_code, **defn)

@router.get("/quals/default")
async def get_qual_default(og_code: str) -> QualStandardResponse:
    if og_code not in QUAL_STANDARDS:
        raise HTTPException(status_code=404, detail=f"Qual standard for {og_code!r} not found")
    return QualStandardResponse(og_code=og_code, **QUAL_STANDARDS[og_code])
```

**Pydantic model pattern** (from wd.py WDCreateRequest, lines 23–32):
```python
class WDCreateRequest(BaseModel):
    """Mutable fields for creating a new WD. Server generates id and timestamps."""
    record: dict = Field(default_factory=dict)
    answers: dict = Field(default_factory=dict)
    step_index: int = 0
    draft: Optional[dict] = None
    reviewing: bool = False
    editing_return: bool = False
```

**New Pydantic models for og_classification.py:**
```python
class OGClassifyRequest(BaseModel):
    confirmed_noc_code: str = Field(min_length=1)
    work_description: str = Field(min_length=10, max_length=2000)
    signal_tally: dict[str, int] = Field(default_factory=dict)

class OGCandidate(BaseModel):
    og_code: str
    og_name: str
    rank: int
    confidence: float
    rationale: str
    evidence_quotes: list[str]
    definition_excerpt: str
    relevant_inclusions: str
    relevant_exclusions: str
    available_levels: list[int]

class ASECAlert(BaseModel):
    disambiguation_text: str
    citation: str

class OGClassifyResponse(BaseModel):
    candidates: list[OGCandidate]
    asec_alert: Optional[ASECAlert] = None

class OGDefinitionResponse(BaseModel):
    og_code: str
    og_name: str
    definition: str
    inclusions: str
    exclusions: str

class QualStandardResponse(BaseModel):
    og_code: str
    education: str
    experience: str
    source: str
```

---

### `v2/backend/app/services/classification_gate.py` — new utility file

**No direct analog** — closest is the error raise pattern in `noc_mapping.py` line 38:
```python
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
```

**New file pattern** (from RESEARCH.md):
```python
"""
app/services/classification_gate.py — Hard gate for CLASS-04.

Imported by future export routes (Phase 17/18/20). Raises 409 Conflict if
OG group and level are not yet confirmed on the WorkDescription.
"""
from __future__ import annotations

from fastapi import HTTPException
from app.models.work_description import WorkDescription


def require_og_confirmed(wd: WorkDescription) -> None:
    """Raises 409 Conflict if OG + level are not yet confirmed."""
    if not wd.confirmed_og or wd.og_level is None:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "classification_pending",
                "message": "OG group and level must be confirmed before generating a job description.",
            },
        )
```

---

### `v2/backend/app/models/work_description.py` — add confirmed_og + og_level fields

**Analog:** Same file, `confirmed_noc` and `noc_candidates` fields (lines 46–47):
```python
    noc_candidates: list[NOCMatch] = Field(default_factory=list)
    confirmed_noc: Optional[NOCMatch] = None
```

**New fields to add (after confirmed_noc, line 47):**
```python
    confirmed_og: Optional[dict] = None      # full OG candidate dict from POST /api/og/classify
    og_level: Optional[int] = Field(default=None, ge=1)  # selected level integer
    reports_to_military: Optional[bool] = None  # CLASS-05: CAF rank advisory trigger
```

**Model conventions observed** (lines 29–50):
- `model_config = ConfigDict(extra="ignore", populate_by_name=True)` — apply to all models
- All optional fields use `Optional[T] = None`, never `T | None`
- Lists use `Field(default_factory=list)`, not `= []`
- Import `Optional` from `typing`, not `T | None` syntax

---

### `v2/backend/app/api/wd.py` — add fields to WDPatchRequest

**Analog:** Same file, WDPatchRequest class (lines 34–46):
```python
class WDPatchRequest(BaseModel):
    """Partial update fields. Only provided fields are merged onto the stored WD."""

    model_config = ConfigDict(extra="ignore")

    record: Optional[dict] = None
    answers: Optional[dict] = None
    step_index: Optional[int] = None
    draft: Optional[dict] = None
    reviewing: Optional[bool] = None
    editing_return: Optional[bool] = None
    confirmed_noc: Optional[dict] = None
```

**New fields to add to WDPatchRequest (after confirmed_noc, line 46):**
```python
    confirmed_og: Optional[dict] = None
    og_level: Optional[int] = None
    reports_to_military: Optional[bool] = None
```

**PATCH handler pattern** (lines 100–123) — no changes needed to the handler body because it already uses `body.model_dump(exclude_unset=True)` which auto-patches any new field present in WDPatchRequest:
```python
@router.patch("/wd/{wd_id}")
async def patch_wd(wd_id: str, body: WDPatchRequest) -> WorkDescription:
    ...
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(wd, field, val)
    wd.last_modified = datetime.now(timezone.utc)
    ...
```

---

### `v2/backend/app/api/__init__.py` — add og_classification router

**Analog:** Same file (lines 16–21):
```python
from . import health, noc_mapping, wd

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(noc_mapping.router)
api_router.include_router(wd.router)
```

**New lines (add og_classification import and include_router call):**
```python
from . import health, noc_mapping, wd, og_classification

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(noc_mapping.router)
api_router.include_router(wd.router)
api_router.include_router(og_classification.router)
```

---

### `v2/backend/tests/test_og_classification.py` — new test file

**Primary analog:** `v2/backend/tests/test_wd.py` (lines 1–57) — async client-based integration tests.
**Secondary analog:** `v2/backend/tests/test_noc_pipeline.py` (lines 236–278) — API route 200/422 tests.

**File header + pytestmark pattern** (test_wd.py lines 1–11):
```python
"""
test_wd.py — contract for POST /api/wd, GET /api/wd/{id}, PATCH /api/wd/{id}.

Wave 0 stub: fails because app/api/wd.py does not exist yet.
Plan 02 implements the routes and these tests must pass.
"""
import pytest

pytestmark = pytest.mark.asyncio
```

**Async test with `client` fixture pattern** (test_wd.py lines 12–20):
```python
async def test_create_wd_returns_201_with_id(client):
    """POST /api/wd must return 201 with an id field."""
    response = await client.post(
        "/api/wd",
        json={"record": {"title": "Test Role"}, "answers": {}, "step_index": 1},
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
```

**Create-then-patch pattern** (test_wd.py lines 41–48):
```python
async def test_patch_wd_updates_step_index(client):
    create_resp = await client.post(
        "/api/wd",
        json={"record": {}, "answers": {}, "step_index": 0},
    )
    wd_id = create_resp.json()["id"]
    patch_resp = await client.patch(f"/api/wd/{wd_id}", json={"step_index": 3})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["step_index"] == 3
```

**New test file structure** (all stubs from RESEARCH.md):
```python
"""
test_og_classification.py — Phase 16 OG classification API tests.

Wave 0 stubs: RED until og_classification.py route + og_service logic is implemented.
Tests use the shared `client` fixture from conftest.py (AsyncClient against test_app).
"""
import pytest

pytestmark = pytest.mark.asyncio


async def test_og_classify_returns_candidates(client):
    """POST /api/og/classify returns top-3 OG candidates."""
    response = await client.post(
        "/api/og/classify",
        json={
            "confirmed_noc_code": "41402",
            "work_description": "Develops environmental policy and advises senior management",
            "signal_tally": {"EC": 3, "AS": 1},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "candidates" in data
    assert len(data["candidates"]) >= 1
    assert data["candidates"][0]["og_code"] == "EC"


async def test_og_classify_asec_alert_when_both_present(client):
    response = await client.post(
        "/api/og/classify",
        json={
            "confirmed_noc_code": "11109",
            "work_description": "Coordinates policy and administrative support",
            "signal_tally": {"EC": 2, "AS": 2},
        },
    )
    assert response.status_code == 200
    assert response.json().get("asec_alert") is not None


async def test_og_classify_no_asec_alert_when_only_ec(client):
    response = await client.post(
        "/api/og/classify",
        json={
            "confirmed_noc_code": "41401",
            "work_description": "Pure policy and economic research",
            "signal_tally": {"EC": 4},
        },
    )
    assert response.status_code == 200
    assert response.json().get("asec_alert") is None


async def test_og_definitions_returns_ec_definition(client):
    response = await client.get("/api/og/definitions?og_code=EC")
    assert response.status_code == 200
    data = response.json()
    assert data["og_code"] == "EC"
    assert len(data["definition"]) > 20


async def test_og_definitions_404_for_unknown_code(client):
    response = await client.get("/api/og/definitions?og_code=ZZ")
    assert response.status_code == 404


async def test_quals_default_returns_ec_text(client):
    response = await client.get("/api/quals/default?og_code=EC")
    assert response.status_code == 200
    data = response.json()
    assert "education" in data
    assert len(data["education"]) > 10


async def test_patch_wd_confirmed_og_persists(client):
    create_resp = await client.post(
        "/api/wd",
        json={"record": {"title": "Policy Analyst"}, "answers": {}, "step_index": 0},
    )
    wd_id = create_resp.json()["id"]
    patch_resp = await client.patch(
        f"/api/wd/{wd_id}",
        json={"confirmed_og": {"og_code": "EC", "og_name": "Economics..."}, "og_level": 5},
    )
    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert body["confirmed_og"]["og_code"] == "EC"
    assert body["og_level"] == 5
```

---

### `v2/frontend/src/data.jsx` — add STEPS entries + OG_LEVELS constant

**Analog:** Same file — noc_confirm STEP entry (lines 351–357) and accumulateSignals constant (lines 279–294).

**noc_confirm STEP pattern** (lines 351–357):
```javascript
{ id: 'noc_confirm', phase: 2, icon: I.compass,
  q: 'Review the top NOC matches and confirm the best fit for this role.',
  helper: 'Select the NOC code that best describes the work.',
  input: { type: 'noc_confirm', candidates: [] },
  apply: (r, a) => ({ confirmed_noc: a }),
  transcript: a => a ? (a.noc_code + ' — ' + a.title) : 'Pending' },
```

**New STEPS entries to insert immediately after noc_confirm:**
```javascript
{ id: 'og_confirm', phase: 2, icon: I.compass,
  q: 'Review the top occupational group matches and confirm the best fit.',
  helper: 'Select the occupational group that best fits the work described.',
  input: { type: 'og_confirm', candidates: [] },
  apply: (r, a) => ({ confirmed_og: a }),
  transcript: a => a ? (a.og_code + ' — ' + a.og_name) : 'Pending' },

{ id: 'og_level', phase: 2, icon: I.ladder,
  q: 'Select the level for this position.',
  helper: 'Level ranges are derived from the collective agreement for the confirmed group.',
  input: { type: 'og_level', levels: [] },
  apply: (r, a) => ({ og_level: a }),
  transcript: a => a ? String(a) : 'Pending' },
```

**reports_to_military STEP to insert after `reports` (Phase 0, index 3):**
```javascript
{ id: 'reports_to_military', phase: 0, icon: I.shield,
  q: 'Does this position report to a military officer?',
  helper: 'This determines whether we show CAF rank equivalence information.',
  input: { type: 'choices', options: [
    { id: 'yes', title: 'Yes — reports to a military officer' },
    { id: 'no', title: 'No — reports to a civilian supervisor' },
  ] },
  apply: (r, a) => ({ reports_to_military: a.id === 'yes' }),
  transcript: a => a.title },
```

**JS constant pattern** (existing OG_LEVELS in constants.py, JS copy):
```javascript
// JS copy of OG_LEVELS from v2/backend/app/data/constants.py
// Avoids API round-trip for static reference data.
const OG_LEVELS = {
  EC: [1,2,3,4,5,6,7,8],
  IT: [1,2,3,4,5],
  AS: [1,2,3,4,5,6,7,8],
  FI: [1,2,3,4],
  CR: [1,2,3,4,5,6,7],
  PM: [1,2,3,4,5,6,7],
  GT: [1,2,3,4,5,6,7,8],
  EL: [1,2,3,4,5,6,7,8,9],
  FB: [1,2,3,4,5,6,7,8],
  FS: [1,2,3,4],
  AI: [1,2,3,4,5,6,7],
  AU: [1,2,3,4,5,6],
};
```

**Export line update** (line 378–382):
```javascript
// Add OG_LEVELS to the export list
export {
  I, STEPS, PHASES, OG_LEVELS, DRF, WORK_TYPES, DUTY_SUGGESTIONS, QUAL_DEFAULT,
  EC_ELEMENTS, computeClassification, refineDuty, ecFactors,
  accumulateSignals, getDutySuggestions,
};
```

---

### `v2/frontend/src/components.jsx` — OgConfirmList + OgLevelPicker + dispatcher update

**Primary analog:** NocConfirmList component (lines 196–230):
```javascript
/* ---- NOC CONFIRM LIST ---------------------------------------- */
// cfg.type === 'noc_confirm'
// cfg.candidates: array of { noc_code, noc_title (or title), teer, matched_duties }
// value: selected noc_code string or null
// onChange(noc_code): called on card click
function NocConfirmList({ value, onChange, cfg }) {
  const candidates = cfg.candidates || [];
  return (
    <div className="choices">
      {candidates.map(c => {
        const sel = value === c.noc_code;
        const duties = c.matched_duties || [];
        return (
          <button
            key={c.noc_code}
            type="button"
            className={'choice choice--noc' + (sel ? ' is-sel' : '')}
            onClick={() => onChange(c.noc_code)}
          >
            <span className="choice__main">
              <span className="choice__title">
                {c.noc_code} — {c.noc_title || c.title}
              </span>
              <span className="choice__desc">TEER {c.teer}</span>
            </span>
            ...
          </button>
        );
      })}
    </div>
  );
}
```

**Secondary analog for level picker:** ChoiceList component (lines 48–77):
```javascript
function ChoiceList({ value, onChange, cfg }) {
  const opts = cfg.source === 'workTypes' ? WORK_TYPES : cfg.options;
  return (
    <div className={'choices' + (grid ? ' choices--grid' : '')}>
      {opts.map(o => {
        const sel = value && value.id === o.id;
        return (
          <button key={o.id} type="button"
            className={'choice' + (sel ? ' is-sel' : '')}
            onClick={() => onChange(o)}
          >
            ...
          </button>
        );
      })}
    </div>
  );
}
```

**New OgConfirmList component (insert after NocConfirmList, before DrfPicker):**
```javascript
/* ---- OG CONFIRM LIST ----------------------------------------- */
// cfg.type === 'og_confirm'
// cfg.candidates: array from POST /api/og/classify response
// cfg.asec_alert: { disambiguation_text, citation } or null
// value: selected candidate object or null
// onChange(candidate): called on card click — stores full candidate object
function OgConfirmList({ value, onChange, cfg }) {
  const candidates = cfg.candidates || [];
  const alert = cfg.asec_alert || null;
  return (
    <div>
      {alert && (
        <div className="asec-alert">
          <p className="asec-alert__title">
            Both Administrative Services (AS) and Economics and Social Science
            Services (EC) appear in the top candidates.
          </p>
          <p className="asec-alert__body">{alert.disambiguation_text}</p>
          <span className="asec-alert__cite">{alert.citation}</span>
        </div>
      )}
      <div className="choices">
        {candidates.map(c => {
          const sel = value && value.og_code === c.og_code;
          return (
            <button key={c.og_code} type="button"
              className={'choice choice--og' + (sel ? ' is-sel' : '')}
              onClick={() => onChange(c)}>
              <span className="choice__main">
                <span className="choice__title">{c.og_code} — {c.og_name}</span>
                <span className="choice__desc">{Math.round(c.confidence * 100)}% match</span>
                {c.definition_excerpt && (
                  <span className="choice__excerpt">{c.definition_excerpt}</span>
                )}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
```

**New OgLevelPicker component (insert after OgConfirmList):**
```javascript
/* ---- OG LEVEL PICKER ----------------------------------------- */
// cfg.type === 'og_level'
// cfg.levels: array of integers from OG_LEVELS[og_code]
// value: selected level integer or null
// onChange(level): called on button click
function OgLevelPicker({ value, onChange, cfg }) {
  const levels = cfg.levels || [];
  return (
    <div className="choices">
      {levels.map(lv => {
        const sel = value === lv;
        return (
          <button key={lv} type="button"
            className={'choice' + (sel ? ' is-sel' : '')}
            onClick={() => onChange(lv)}>
            <span className="choice__main">
              <span className="choice__title">Level {lv < 10 ? '0' + lv : lv}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
```

**StepInput dispatcher** (lines 288–298) — replace og_confirm stub, add og_level:
```javascript
// Current (line 297):
if (t === 'og_confirm') return <NocConfirmList {...props} />; // stub — Phase 16 replaces

// Replace with:
if (t === 'og_confirm') return <OgConfirmList {...props} />;
if (t === 'og_level') return <OgLevelPicker {...props} />;
```

**answerValid update** (lines 309–316) — add og_confirm + og_level cases:
```javascript
function answerValid(step, value) {
  const t = step.input.type;
  if (t === 'text' || t === 'textarea') return !!(value && value.trim());
  if (t === 'duties') return Array.isArray(value) && value.length > 0;
  if (t === 'quals') return !!(value && value.education && value.experience);
  if (t === 'noc_confirm') return typeof value === 'string' && value.length > 0;
  // Phase 16 additions:
  if (t === 'og_confirm') return value !== null && value !== undefined && !!value.og_code;
  if (t === 'og_level') return typeof value === 'number' && value >= 1;
  return !!value;
}
```

---

### `v2/frontend/src/app.jsx` — ogCandidates state + OG pipeline wiring

**Primary analog:** Same file — nocCandidates state + NOC pipeline trigger (lines 80–81, 168–197).

**nocCandidates state pattern** (lines 80–81):
```javascript
const [nocCandidates, setNocCandidates] = useState([]);
const [nocLoading, setNocLoading] = useState(false);
```

**New state slices to add immediately after nocLoading (line 81):**
```javascript
const [ogCandidates, setOgCandidates] = useState([]);
const [ogLoading, setOgLoading] = useState(false);
```

**NOC pipeline trigger pattern** (lines 168–182):
```javascript
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

**New OG pipeline trigger to add immediately after NOC trigger block:**
```javascript
if (step.id === 'noc_confirm') {
  setOgLoading(true);
  setOgCandidates([]);
  const signalTally = accumulateSignals(answers);
  fetch('/api/og/classify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      confirmed_noc_code: draft,        // draft is the confirmed noc_code string
      work_description: newRecord.summary,
      signal_tally: signalTally?.tally || {},
    }),
  })
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(data => { setOgCandidates(data.candidates || []); setOgLoading(false); })
    .catch(() => { setOgLoading(false); });
}
```

**NOC invalidation pattern** (lines 184–195) — extend to also clear OG state:
```javascript
// Current (lines 184–195):
if (editingReturn) {
  if (step.phase === 1) {
    setNocCandidates([]);
    setNocLoading(false);
    setAnswers(prev => {
      const updated = { ...prev };
      delete updated['noc_confirm'];
      return updated;
    });
  }
  ...
}

// Extended for Phase 16 — also clear og state when phase 1 is re-answered,
// AND clear og state when noc_confirm is re-answered:
if (editingReturn) {
  if (step.phase === 1) {
    setNocCandidates([]);
    setNocLoading(false);
    setOgCandidates([]);
    setOgLoading(false);
    setAnswers(prev => {
      const updated = { ...prev };
      delete updated['noc_confirm'];
      delete updated['og_confirm'];
      delete updated['og_level'];
      return updated;
    });
  }
  if (step.id === 'noc_confirm') {
    setOgCandidates([]);
    setOgLoading(false);
    setAnswers(prev => {
      const updated = { ...prev };
      delete updated['og_confirm'];
      delete updated['og_level'];
      return updated;
    });
  }
  ...
}
```

**cfgOverride pattern** (lines 253–259):
```javascript
const stepCfgOverride = !reviewing && step
  ? (step.input.type === 'noc_confirm'
      ? { ...step.input, candidates: nocCandidates, loading: nocLoading }
      : step.id === 'duties'
        ? { ...step.input, suggestions: getDutySuggestions(answers) }
        : undefined)
  : undefined;
```

**Extended cfgOverride to add og_confirm + og_level cases:**
```javascript
const stepCfgOverride = !reviewing && step
  ? (step.input.type === 'noc_confirm'
      ? { ...step.input, candidates: nocCandidates, loading: nocLoading }
      : step.input.type === 'og_confirm'
        ? { ...step.input, candidates: ogCandidates, loading: ogLoading }
        : step.input.type === 'og_level'
          ? { ...step.input, levels: record.confirmed_og
                ? OG_LEVELS[record.confirmed_og.og_code] || []
                : [] }
          : step.id === 'duties'
            ? { ...step.input, suggestions: getDutySuggestions(answers) }
            : undefined)
  : undefined;
```

**FLASH map update** (lines 10–17) — add og entries:
```javascript
const FLASH = {
  title: 'title', branch: 'title', reports: 'title',
  reports_to_military: 'title',       // Phase 16 addition
  supervises: 'summary',
  summary: 'summary',
  qb_work_output_type: 'level', qb_work_audience: 'level',
  qb_knowledge_specialization: 'level', qb_policy_interpretation: 'level',
  noc_confirm: 'level',
  og_confirm: 'level',                // Phase 16 addition
  og_level: 'level',                  // Phase 16 addition
  duties: 'duties', quals: 'quals',
};
```

**restart() update** (lines 241–246) — clear og state:
```javascript
function restart() {
  setRecord({}); setAnswers({}); setStepIndex(0);
  setDraft(initialAnswer(STEPS[0], {})); setReviewing(false); setEditingReturn(false);
  setWdId(null); setNocCandidates([]); setNocLoading(false);
  setOgCandidates([]); setOgLoading(false);   // Phase 16 addition
  try { localStorage.removeItem('jd-builder-v2-wd-id'); } catch {}
}
```

**Import update** — add OG_LEVELS to data.jsx import (line 5):
```javascript
import { STEPS, PHASES, I, OG_LEVELS, computeClassification, accumulateSignals, getDutySuggestions } from './data.jsx';
```

---

### `v2/frontend/src/document.jsx` — CLASS-04 pending state + CLASS-05 CAF advisory

**Analog:** Same file — Ghost shimmer and Sec patterns (lines 29–61):
```javascript
function Ghost({ lines }) { ... }

function Sec({ n, title, src, ghost, fresh, editable, onEdit, children }) {
  return (
    <section className={`sec${ghost ? ' is-ghost' : ''}${editable ? ' sec--editable' : ''}`}>
      ...
    </section>
  );
}
```

**Classification pending state to add inside ClassBlock or new ClassificationSection:**
```javascript
// In document.jsx — Classification & Evaluation section:
if (!record.confirmed_og || !record.og_level) {
  return (
    <section className="doc-section doc-section--pending">
      <h3 className="doc-section__title">Classification &amp; Evaluation</h3>
      <p className="doc-section__pending">
        Classification pending — confirm occupational group and level to proceed.
      </p>
    </section>
  );
}
```

**CAF rank advisory display pattern (CLASS-05):**
```javascript
// Near the "Reports to" field in Position Identification:
{record.reports_to_military && record.confirmed_og && (
  <div className="caf-advisory">
    <span className="caf-advisory__label">
      CAF Rank Equivalent (advisory — not authoritative):
    </span>
    <span className="caf-advisory__text">
      {getCafEquivalence(record.confirmed_og.og_code, record.og_level)}
    </span>
  </div>
)}
```

---

### `v2/frontend/src/conversation.test.jsx` — add Phase 16 test stubs

**Analog:** Same file — CONVO-04 stub structure (lines 42–52):
```javascript
describe('CONVO-04: StepInput dispatches og_confirm type', () => {
  it('StepInput with type og_confirm renders something (not null)', () => {
    const cfg = { type: 'og_confirm', candidates: [] };
    const { container } = render(
      <StepInput cfg={cfg} value={null} onChange={() => {}} onSubmit={() => {}} record={{}} />
    );
    expect(container.firstChild).not.toBeNull();
  });
});
```

**New test stubs to add:**
```javascript
// Replace existing CONVO-04 stub (which was a null-render check) with OgConfirmList tests:
describe('CONVO-04: OgConfirmList renders candidates from cfg', () => {
  it('renders candidate button when candidates array is non-empty', () => {
    const cfg = { type: 'og_confirm', candidates: [
      { og_code: 'EC', og_name: 'Economics and Social Science Services',
        confidence: 0.85, rank: 1, rationale: 'test', evidence_quotes: [],
        definition_excerpt: 'test excerpt', relevant_inclusions: '',
        relevant_exclusions: '', available_levels: [1,2,3,4,5,6,7,8] }
    ]};
    const { getByText } = render(
      <StepInput cfg={cfg} value={null} onChange={() => {}} onSubmit={() => {}} record={{}} />
    );
    expect(getByText(/EC/)).toBeTruthy();
  });
});

describe('CLASS-03: OgLevelPicker renders level range', () => {
  it('renders 8 level buttons for EC (levels 1–8)', () => {
    const cfg = { type: 'og_level', levels: [1,2,3,4,5,6,7,8] };
    const { getAllByRole } = render(
      <StepInput cfg={cfg} value={null} onChange={() => {}} onSubmit={() => {}} record={{}} />
    );
    const buttons = getAllByRole('button');
    expect(buttons.length).toBe(8);
  });
});
```

---

## Shared Patterns

### Pattern 1: `from __future__ import annotations`
**Source:** All Python files — `v2/backend/app/api/noc_mapping.py` line 11, `v2/backend/app/api/wd.py` line 9, `v2/backend/app/models/work_description.py` line 17
**Apply to:** `og_classification.py`, `classification_gate.py`
```python
from __future__ import annotations
```

### Pattern 2: APIRouter instantiation
**Source:** `v2/backend/app/api/noc_mapping.py` line 19, `v2/backend/app/api/wd.py` line 21
**Apply to:** `og_classification.py`
```python
router = APIRouter()
```

### Pattern 3: 404 raise pattern for missing data
**Source:** `v2/backend/app/api/wd.py` lines 95–97
**Apply to:** `og_classification.py` GET endpoints
```python
if row is None:
    raise HTTPException(status_code=404, detail="Work description not found")
```

### Pattern 4: Pydantic Optional with None default
**Source:** `v2/backend/app/models/work_description.py` lines 39–47
**Apply to:** All new Pydantic model fields, WDPatchRequest new fields
```python
confirmed_noc: Optional[NOCMatch] = None
# Never: confirmed_noc: NOCMatch | None = None  (style convention in this codebase)
```

### Pattern 5: `pytestmark = pytest.mark.asyncio`
**Source:** `v2/backend/tests/test_wd.py` line 9
**Apply to:** `test_og_classification.py`
```python
pytestmark = pytest.mark.asyncio
```

### Pattern 6: `client` fixture (no test_app needed)
**Source:** `conftest.py` lines 82–86 — `client` depends on `test_app` which handles env + schema init
**Apply to:** `test_og_classification.py` — just request `client` as fixture, no manual setup needed
```python
async def test_og_classify_returns_candidates(client):
    response = await client.post("/api/og/classify", json={...})
```

### Pattern 7: React state slice pair (value + loading)
**Source:** `v2/frontend/src/app.jsx` lines 80–81
**Apply to:** OG pipeline state in app.jsx
```javascript
const [nocCandidates, setNocCandidates] = useState([]);
const [nocLoading, setNocLoading] = useState(false);
```

### Pattern 8: cfgOverride spread pattern
**Source:** `v2/frontend/src/app.jsx` lines 253–259
**Apply to:** og_confirm and og_level cfgOverride cases
```javascript
{ ...step.input, candidates: nocCandidates, loading: nocLoading }
```

### Pattern 9: `model_dump(exclude_unset=True)` + setattr patch
**Source:** `v2/backend/app/api/wd.py` lines 112–113
**Apply to:** No change needed — existing patch_wd handler handles new WDPatchRequest fields automatically
```python
for field, val in body.model_dump(exclude_unset=True).items():
    setattr(wd, field, val)
```

---

## No Analog Found

No files in this phase are entirely without analog — all have either exact or role-match analogs in the existing codebase.

| File | Notes |
|------|-------|
| `v2/backend/app/services/classification_gate.py` | Closest is HTTPException raise pattern in noc_mapping.py; gate utility pattern is new but trivial |
| `OG_DEFINITIONS` / `QUAL_STANDARDS` constants | No existing data with this structure in constants.py; shape is new but follows OG_LEVELS/CAF_RANK_OG_EQUIVALENCE header conventions |

---

## Critical Warnings for Planner

1. **Wave 0 data task is blocking:** `OG_DEFINITIONS` constant must be populated with verbatim text from `data/Job_evaluation/` before `POST /api/og/classify` can return meaningful definition_excerpt. EC text is verified. AS/IT/FI must be sourced.

2. **og_confirm stores full object, not string:** `noc_confirm.apply` stores a string (`confirmed_noc: a`). `og_confirm.apply` stores the full candidate dict (`confirmed_og: a`). Do not copy the noc pattern naively — the level picker needs `record.confirmed_og.og_code`.

3. **reports_to_military insertion shifts step indices:** Inserting after `reports` (currently index 2) shifts `supervises` from index 3 to index 4. FLASH map and any index-based logic must account for this. The FLASH map uses step.id (safe), but check for any index-hardcoded paths in app.jsx before inserting.

4. **og_level cfgOverride reads from record, not newRecord:** At render time when `og_level` is the active step, `record.confirmed_og` will be set from the prior commit. The cfgOverride computes from `record` on each render — this is safe because React state is set synchronously in setRecord before the next render.

5. **QUAL_STANDARDS AS/IT/FI text may be stubs:** If qualification standard text for non-EC groups cannot be located in `data/`, use placeholder stub text and flag as TODO for Phase 19. The `GET /api/quals/default` endpoint must not 500.

---

## Metadata

**Analog search scope:** `v2/backend/app/api/`, `v2/backend/app/models/`, `v2/backend/app/data/`, `v2/backend/tests/`, `v2/frontend/src/`
**Files read:** 11 source files
**Pattern extraction date:** 2026-06-05
