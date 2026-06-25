# Phase 21: OG Expansion + Preview Fix — Pattern Map

**Mapped:** 2026-06-10
**Files analyzed:** 10 (8 backend, 2 frontend)
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `v2/backend/app/data/constants.py` | config/data | CRUD | itself (extension) | exact |
| `v2/backend/app/api/og_classification.py` | controller | request-response | itself (extension) | exact |
| `v2/backend/app/services/jes_service.py` | service | request-response | itself (extension) | exact |
| `v2/backend/app/services/export_service.py` | service | file-I/O | itself (consolidation) | exact |
| `v2/backend/tests/test_constants.py` | test | CRUD | itself (extension) | exact |
| `v2/backend/tests/test_og_classification.py` | test | request-response | itself (extension) | exact |
| `v2/backend/tests/test_jes_scoring.py` | test | request-response | itself (extension) | exact |
| `v2/frontend/src/data.jsx` | config/data | CRUD | itself (extension) | exact |
| `v2/frontend/src/styles.css` | config | — | itself (one-liner fix) | exact |
| `v2/frontend/src/components.jsx` | component | request-response | itself (extension) | exact |

---

## Pattern Assignments

### `v2/backend/app/data/constants.py` (config/data, CRUD)

**Analog:** itself — extend existing constant blocks

**Existing OG_LEVELS structure** (lines 36–51):
```python
OG_LEVELS: dict[str, list[int]] = {
    "EC": list(range(1, 9)),   # EC-01 to EC-08 — EC_rates.csv
    "IT": list(range(1, 6)),   # IT-01 to IT-05 — IT_CS_rates.csv
    "AS": list(range(1, 9)),   # AS-1 to AS-8 — PA_rates.csv
    "FI": list(range(1, 5)),   # FI-01 to FI-04 — CT_FI_rates.csv
    "CR": list(range(1, 8)),   # CR-1 to CR-7 — PA_rates.csv
    "PM": list(range(1, 8)),   # PM-1 to PM-7 — PA_rates.csv
    "GT": list(range(1, 9)),   # GT-1 to GT-8 — TC_rates.csv
    "EL": list(range(1, 10)),  # EL-01 to EL-09 — EL_rates.csv
    "FB": list(range(1, 9)),   # FB-1 to FB-8 — FB_rates.csv
    "FS": list(range(1, 5)),   # FS-01 to FS-04 — FS_rates.csv
    "AI": list(range(1, 8)),   # AI-01 to AI-07 — AI_rates.csv
    "AU": list(range(1, 7)),   # AU-01 to AU-06 — CT_FI_rates.csv
}
```

**New entries to append** (derived from RESEARCH.md, rates CSV verified):
```python
    # Phase 21 additions — all 10 new groups:
    "ED": list(range(1, 5)),   # ED-01 to ED-04 — EB_rates.csv
    "LC": list(range(1, 5)),   # LC-01 to LC-04 — JES point boundaries
    "LP": list(range(1, 6)),   # LP-01 to LP-05 — JES point boundaries
    "MT": list(range(1, 8)),   # MT-01 to MT-07 — SP_AP_rates.csv (NOT 9 — see Pitfall 1)
    "NT": list(range(1, 5)),   # NT-01 to NT-04 — NT JES level descriptions
    "NU": list(range(1, 9)),   # NU-01 to NU-08 — SH_rates.csv HOS/CHN broadest range
    "PO": list(range(1, 5)),   # PO-01 to PO-04 — PO_rates.csv TCO-01 to TCO-04
    "PS": list(range(1, 6)),   # PS-01 to PS-05 — SH_rates.csv
    "SW": list(range(1, 6)),   # SW-01 to SW-05 — SH_rates.csv (SCW 1-5 is broadest)
    "WP": list(range(1, 7)),   # WP-01 to WP-06 — PA_rates.csv
```

**Existing OG_DEFINITIONS dict entry pattern** (lines 370–386):
```python
OG_DEFINITIONS: dict[str, dict] = {
    "EC": {
        "og_name": "Economics and Social Science Services",
        "definition": (
            "The EC Group comprises positions primarily involved in ..."
        ),
        "inclusions": "",
        "exclusions": "",
    },
    # ... repeat pattern for each new group
}
```
Every new group needs the same four keys: `og_name`, `definition`, `inclusions`, `exclusions`. Text sourced verbatim from `data/Job_evaluation/` text files.

**Existing QUAL_STANDARDS dict entry pattern** (lines 507–534):
```python
QUAL_STANDARDS: dict[str, dict] = {
    "EC": {
        "education": "A degree from a recognized university ...",
        "experience": "Significant and recent experience ...",
        "source": "TBS Qualification Standard for Economics and Social Science Services (EC)",
    },
    # ... repeat pattern for each new group
    "default": {
        "education": "A degree or diploma ...",
        "experience": "Experience performing duties ...",
        "source": "TBS Qualification Standards (general fallback)",
    },
}
```

**Existing NON_EC_TOTALS dict entry pattern** (lines 582–590):
```python
NON_EC_TOTALS: dict[str, dict[int, int]] = {
    "FI": {1: 220, 2: 300, 3: 385, 4: 470, 5: 560, 6: 660},
    "IT": {1: 215, 2: 300, 3: 390, 4: 480, 5: 575},
    "AS": {1: 195, 2: 265, 3: 345, 4: 430, 5: 510, 6: 600, 7: 690, 8: 790},
    "EN": {4: 500, 5: 600, 6: 720},
}
```
New level-description groups (NU, PS, NT, PO, WP, SW-CHA, ED sub-groups) get entries here. Point-rating groups (FB, FS, LP, MT, LC, SW-SCW) do NOT — they use JES_FACTORS_BY_GROUP instead.

**Existing NON_EC_STANDARD_NAMES dict entry pattern** (lines 600–605):
```python
NON_EC_STANDARD_NAMES: dict[str, str] = {
    "FI": "FI / CT Job Evaluation Standard (2023)",
    "IT": "IT Job Evaluation Standard",
    "AS": "AS / PA Job Evaluation Standard",
    "EN": "EN Job Evaluation Standard",
}
```
All 16 groups need an entry here (plus EC). This is the authoritative copy — the local copy in `export_service.py` lines 50–55 must be deleted (OGX-02).

**New JES_FACTORS_BY_GROUP constant** — mirrors EC_JES_ELEMENTS structure (lines 546–556):
```python
EC_JES_ELEMENTS: list[dict] = [
    {"name": "Decision making",                 "category": "Responsibility", "pts": {1:5, 2:15, 3:35, 4:60, 5:90, 6:125, 7:165, 8:210}},
    {"name": "Leadership & operational mgmt",   "category": "Responsibility", "pts": {1:5, 2:20, 3:50, 4:90, 5:140}},
    # ... 9 total
]
```
The new constant uses identical structure, keyed by OG code:
```python
JES_FACTORS_BY_GROUP: dict[str, list[dict]] = {
    "FB": [
        {"name": "<factor name from FB JES>", "category": "<category>", "pts": {1: ..., 2: ..., ...}},
        # ... all FB factors
    ],
    "FS": [...],
    "LP": [...],
    "MT": [...],
    "LC": [...],
    # SW-SCW handled via confirmed_sub_group routing, keyed as "SW-SCW"
}
```
Factor names, categories, and degree→point values must be authored from `data/Job_evaluation/*.txt` files — not generated.

**New sub-group disambiguation constants** — mirrors ASEC_DISAMBIGUATION (lines 487–497):
```python
ASEC_DISAMBIGUATION: dict = {
    "disambiguation_text": (
        "Economics and Social Science Services (EC): "
        + OG_DEFINITIONS["EC"]["definition"][:300]
        + " ... "
        "Administrative Services (AS): "
        + OG_DEFINITIONS["AS"]["definition"][:300]
        + " Review the position's primary work content..."
    ),
    "citation": "TBS OCHRO Occupational Group Definitions",
}
```
New constants for NU, SW, ED follow this shape with `subgroups` list and `descriptions` dict added:
```python
NU_SUBGROUP_DISAMBIGUATION: dict = {
    "subgroups": ["HOS", "CHN", "EMA"],
    "descriptions": {"HOS": "...", "CHN": "...", "EMA": "..."},
    "disambiguation_text": "...",
    "citation": "TBS OCHRO — Nursing (NU) Job Evaluation Standard",
}
```

---

### `v2/backend/app/api/og_classification.py` (controller, request-response)

**Analog:** itself — extend existing disambiguation pattern

**Existing imports** (lines 16–23):
```python
from app.data.constants import ASEC_DISAMBIGUATION, OG_DEFINITIONS, OG_LEVELS, QUAL_STANDARDS
```
Phase 21 adds: `NU_SUBGROUP_DISAMBIGUATION, SW_SUBGROUP_DISAMBIGUATION, ED_SUBGROUP_DISAMBIGUATION` (or a single `SUBGROUP_DISAMBIGUATIONS` dict).

**Existing ASECAlert model** (lines 51–53):
```python
class ASECAlert(BaseModel):
    disambiguation_text: str
    citation: str
```
New `SubGroupAlert` model mirrors this shape but adds sub-group option fields:
```python
class SubGroupAlert(BaseModel):
    subgroups: list[str]
    descriptions: dict[str, str]
    disambiguation_text: str
    citation: str
```

**Existing OGClassifyResponse model** (lines 56–58):
```python
class OGClassifyResponse(BaseModel):
    candidates: list[OGCandidate]
    asec_alert: Optional[ASECAlert] = None
```
Phase 21 adds `subgroup_alert: Optional[SubGroupAlert] = None`.

**Existing ASEC disambiguation trigger** (lines 148–151):
```python
asec_alert = None
og_codes_in_top3 = {c.og_code for c in candidates}
if "AS" in og_codes_in_top3 and "EC" in og_codes_in_top3:
    asec_alert = ASECAlert(**ASEC_DISAMBIGUATION)
```
New sub-group disambiguation triggers unconditionally when confirmed OG is NU, SW, or ED. The trigger fires on the confirmed OG (not on top-3 overlap), so it must receive the `confirmed_og` field from the request body. The request model needs `confirmed_og: Optional[str] = None` added:
```python
# New: fire unconditionally when confirmed_og is in sub-group groups
subgroup_alert = None
SUBGROUP_OGS = {"NU", "SW", "ED"}
if body.confirmed_og in SUBGROUP_OGS:
    subgroup_alert = SubGroupAlert(**SUBGROUP_DISAMBIGUATIONS[body.confirmed_og])
```

---

### `v2/backend/app/services/jes_service.py` (service, request-response)

**Analog:** itself — extend non-EC routing branch

**Existing imports** (lines 36–43):
```python
from app.data.constants import (
    EC_JES_ELEMENTS,
    NON_EC_STANDARD_NAMES,
    NON_EC_TOTALS,
)
```
Phase 21 adds `JES_FACTORS_BY_GROUP` to this import.

**Existing non-EC routing gate** (lines 183–207):
```python
if og_code != "EC":
    if og_code not in NON_EC_TOTALS:
        raise ValueError(f"Unknown og_code {og_code!r}")
    if og_level not in NON_EC_TOTALS[og_code]:
        available = sorted(NON_EC_TOTALS[og_code].keys())
        clamped = min(available, key=lambda lv: abs(lv - og_level))
        og_level = clamped
    total_points = NON_EC_TOTALS[og_code][og_level]
    standard_name = NON_EC_STANDARD_NAMES[og_code]
    scorecard = {
        "wd_id": wd_id, "og_code": og_code, "is_ec": False,
        "factors": [], "total_points": total_points,
        "standard_name": standard_name, "has_failed_factors": False,
    }
    _persist_jes_scorecard(con, wd, scorecard)
    return scorecard
```

Phase 21 replaces this block with a three-way branch:
```python
POINT_RATING_GROUPS = frozenset({"FB", "FS", "LP", "MT", "LC"})
# SW-SCW: route via confirmed_sub_group from WD

if og_code != "EC":
    # Resolve effective routing code (handles SW sub-group split)
    routing_code = og_code
    if og_code == "SW" and wd.confirmed_sub_group == "SCW":
        routing_code = "SW-SCW"
    elif og_code == "SW":
        routing_code = "SW-CHA"  # CHA uses NON_EC_TOTALS

    if routing_code in POINT_RATING_GROUPS or routing_code == "SW-SCW":
        # NEW: point-rating non-EC path — loop JES_FACTORS_BY_GROUP, no LLM
        factors_def = JES_FACTORS_BY_GROUP[routing_code]
        # ... hardcoded degree-vector lookup, same factor dict shape as EC path
        # factors list uses same _build_factor_score / _compute_total helpers
        pass
    else:
        # EXISTING: level-description path — NON_EC_TOTALS lookup
        if routing_code not in NON_EC_TOTALS:
            raise ValueError(f"Unknown og_code {og_code!r}")
        # ... existing level-clamp + scorecard build
```

**Existing EC per-factor loop pattern** (lines 219–248) — copy this loop structure for point-rating groups, removing the LLM call. The degree for each factor comes from a hardcoded degree-vector table (authored from JES benchmark positions), not from `jes_instructor_client`. The `_build_factor_score`, `_compute_total`, and `_persist_jes_scorecard` helpers are reused unchanged.

---

### `v2/backend/app/services/export_service.py` (service, file-I/O)

**Analog:** itself — consolidation only

**Local dict to DELETE** (lines 50–55):
```python
NON_EC_STANDARD_NAMES: dict[str, str] = {
    "FI": "CT JES 2023",
    "IT": "IT JES",
    "AS": "UCS",
    "EN": "EN JES",
}
```

**Replace with import** — add to the existing `app.db` / `app.models` import block:
```python
from app.data.constants import NON_EC_STANDARD_NAMES
```
No other changes to this file. The local dict at lines 50–55 must be fully deleted (not commented out) in the same commit.

---

### `v2/backend/tests/test_constants.py` (test, CRUD)

**Analog:** itself — extend existing test module

**Existing test module header** (lines 1–12):
```python
"""
tests/test_constants.py — Unit tests for app/data/constants.py.

DATA-01 (6 tests): OG_LEVELS correct level counts, contiguous int lists, no CS key.
DATA-02 (2 tests): CAF_RANK_OG_EQUIVALENCE advisory flag + OG code cross-reference.
"""
from app.data.constants import OG_LEVELS, CAF_RANK_OG_EQUIVALENCE
```

**Existing test pattern** (lines 34–43):
```python
def test_og_levels_all_groups_are_lists_of_ints():
    for code, levels in OG_LEVELS.items():
        assert isinstance(levels, list), f"{code} levels must be a list"
        assert all(isinstance(n, int) for n in levels), f"{code} levels must be ints"
        assert levels == list(range(levels[0], levels[-1] + 1)), \
            f"{code} levels must be contiguous starting at {levels[0]}"
```

**Two new tests to add** — match the module's existing assert-with-f-string style:

```python
# OGX-01 completeness test
def test_og_constants_completeness():
    """OGX-01 — every key in OG_LEVELS is present in all other 5 constants."""
    from app.data.constants import (
        OG_LEVELS, OG_DEFINITIONS, QUAL_STANDARDS,
        NON_EC_TOTALS, NON_EC_STANDARD_NAMES, JES_FACTORS_BY_GROUP
    )
    POINT_RATING_GROUPS = {"FB", "FS", "LP", "MT", "LC"}
    for og_code in OG_LEVELS:
        assert og_code in OG_DEFINITIONS, f"{og_code} missing from OG_DEFINITIONS"
        assert og_code in QUAL_STANDARDS or "default" in QUAL_STANDARDS, \
            f"{og_code} missing from QUAL_STANDARDS"
        assert og_code in NON_EC_STANDARD_NAMES, \
            f"{og_code} missing from NON_EC_STANDARD_NAMES"
        if og_code in POINT_RATING_GROUPS:
            assert og_code in JES_FACTORS_BY_GROUP, \
                f"{og_code} missing from JES_FACTORS_BY_GROUP"
        elif og_code not in ("EC",):
            assert og_code in NON_EC_TOTALS, \
                f"{og_code} missing from NON_EC_TOTALS"


# OGX-03 parity test — written as FAILING test before new group text is authored
def test_qual_defaults_parity():
    """OGX-03 — QUAL_STANDARDS (backend) must have an entry for every key
    in the frontend QUAL_DEFAULTS constant (16 groups + default at phase close)."""
    from app.data.constants import QUAL_STANDARDS
    EXPECTED_GROUPS = {
        "EC", "AS", "IT", "FI",
        "ED", "FB", "FS", "LC", "LP", "MT", "NT", "NU", "PO", "PS", "SW", "WP",
        "default",
    }
    missing = EXPECTED_GROUPS - set(QUAL_STANDARDS.keys())
    assert not missing, f"QUAL_STANDARDS missing keys: {missing}"
```

---

### `v2/backend/tests/test_og_classification.py` (test, request-response)

**Analog:** itself — extend existing async test module

**Existing test module header** (lines 1–12):
```python
"""
test_og_classification.py — Phase 16 OG classification API tests.
"""
import pytest
pytestmark = pytest.mark.asyncio
```

**Existing POST /api/og/classify test pattern** (lines 14–28):
```python
async def test_og_classify_returns_candidates(client):
    response = await client.post(
        "/api/og/classify",
        json={
            "confirmed_noc_code": "41402",
            "work_description": "...",
            "signal_tally": {"EC": 3, "AS": 1},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["candidates"][0]["og_code"] == "EC"
```

**New tests to add** — mirror existing pattern, add `confirmed_og` field once the request model is extended:

```python
# OGX-04 per-group signal routing
async def test_per_group_signal_routing_nu(client):
    """OGX-04 — signal_tally dominated by NU returns NU as top candidate."""
    response = await client.post(
        "/api/og/classify",
        json={
            "confirmed_noc_code": "31301",
            "work_description": "Provides nursing care in a hospital setting",
            "signal_tally": {"NU": 4},
        },
    )
    assert response.status_code == 200
    assert response.json()["candidates"][0]["og_code"] == "NU"


# OGX-07 sub-group disambiguation
async def test_nu_disambiguation_alert_fires(client):
    """OGX-07 — confirmed_og=NU returns subgroup_alert in response."""
    response = await client.post(
        "/api/og/classify",
        json={
            "confirmed_noc_code": "31301",
            "work_description": "Provides nursing care in a hospital setting",
            "signal_tally": {"NU": 4},
            "confirmed_og": "NU",      # new field on OGClassifyRequest
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("subgroup_alert") is not None
    assert "subgroups" in data["subgroup_alert"]
```

---

### `v2/backend/tests/test_jes_scoring.py` (test, request-response)

**Analog:** itself — extend existing async test module

**Existing non-EC test pattern** (lines 203–228):
```python
@pytest.mark.asyncio
async def test_score_non_ec_returns_totals(client, env_with_db):
    """JES-03 — POST /api/jes/score for non-EC (IT) returns single totals line."""
    wd_id = await _create_wd_with_og(client, og_code="IT", og_level=4)
    response = await client.post(
        "/api/jes/score",
        json={"wd_id": wd_id, "og_code": "IT", "og_level": 4, "duties": ["..."]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_ec"] is False
    assert data["total_points"] == 480
    assert "IT Job Evaluation Standard" in data["standard_name"]
    assert data["factors"] == []
    assert data["has_failed_factors"] is False
```

**New tests to add** — copy this pattern, one per new group type:

```python
# OGX-06 level-description group (NU)
@pytest.mark.asyncio
async def test_score_nu_returns_totals(client, env_with_db):
    """OGX-06 — POST /api/jes/score for NU returns jes_scores=[] + total from NON_EC_TOTALS."""
    wd_id = await _create_wd_with_og(client, og_code="NU", og_level=3)
    response = await client.post(
        "/api/jes/score",
        json={"wd_id": wd_id, "og_code": "NU", "og_level": 3, "duties": ["Provides nursing care"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_ec"] is False
    assert data["factors"] == []
    assert isinstance(data["total_points"], int)


# OGX-05 point-rating group (FB)
@pytest.mark.asyncio
async def test_score_fb_returns_per_factor_rows(client, env_with_db):
    """OGX-05 — POST /api/jes/score for FB returns per-factor rows (no LLM)."""
    wd_id = await _create_wd_with_og(client, og_code="FB", og_level=4)
    response = await client.post(
        "/api/jes/score",
        json={"wd_id": wd_id, "og_code": "FB", "og_level": 4, "duties": ["Inspects borders"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_ec"] is False
    assert len(data["factors"]) > 0      # per-factor rows, not empty list
    assert data["has_failed_factors"] is False
```

---

### `v2/frontend/src/data.jsx` (config/data, CRUD)

**Analog:** itself — extend three structures

**Existing OG_LEVELS JS object** (lines 29–42):
```javascript
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
Append 10 new entries in the same integer-array format, mirroring `constants.py` OG_LEVELS exactly.

**Existing QUAL_DEFAULTS object** (lines 293–314):
```javascript
const QUAL_DEFAULTS = {
  EC: { education: '...', experience: '...' },
  AS: { education: '...', experience: '...' },
  IT: { education: '...', experience: '...' },
  FI: { education: '...', experience: '...' },
  default: { education: '...', experience: '...' }
};
```
Add one `{ education, experience }` entry per new OG group. Text must mirror `QUAL_STANDARDS` in `constants.py` so the parity test (`test_qual_defaults_parity`) passes.

**Existing STEPS QUESTION_BANK option structure** (lines 365–406):
```javascript
{ id: 'qb_work_output_type', phase: 1, icon: I.list,
  q: '...',
  helper: '...',
  input: { type: 'choices', options: [
    { id: 'analysis_advice', title: 'Analysis, options, or recommendations for decision-makers',
      signals: { og_candidates: ['EC'], jes_factor_hints: ['Research & analysis', 'Decision making'], teer_affinity: [1, 2] } },
    // ... more options
  ] },
  apply: (r, a) => ({ qb_work_output_type: a.id }),
  transcript: a => a.title },
```
QUES-02 constraint: option `title` must not contain OG codes. OG codes go only inside `signals.og_candidates`. The `accumulateSignals()` function (lines 327–341) reads `answers[stepId].signals.og_candidates` — new step IDs must follow the `qb_` prefix convention and be added to `qbStepIds` array.

---

### `v2/frontend/src/styles.css` (config, one-liner)

**Analog:** itself — single property addition

**Current rule** (lines 548–552):
```css
.doc-scroll {
  flex: 1 1 auto; min-height: 0; overflow-y: auto;
  padding: 38px 34px 80px;
  display: flex; justify-content: center;
}
```

**Fixed rule** — add `align-items: flex-start` to the same declaration block:
```css
.doc-scroll {
  flex: 1 1 auto; min-height: 0; overflow-y: auto;
  padding: 38px 34px 80px;
  display: flex; justify-content: center; align-items: flex-start;
}
```
No other CSS changes required for this requirement.

---

### `v2/frontend/src/components.jsx` (component, request-response)

**Analog:** itself — extend OgConfirmList

**Existing OgConfirmList component** (lines 321–362):
```jsx
function OgConfirmList({ value, onChange, cfg }) {
  const candidates = cfg.candidates || [];
  const alert = cfg.asec_alert || null;
  // ...
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
        {candidates.map(c => { /* choice buttons */ })}
      </div>
    </div>
  );
}
```

**New sub-group alert rendering** — add after the existing `{alert && ...}` block, before `<div className="choices">`. The `subGroupAlert` prop comes from API response `subgroup_alert` field, passed via `cfg.subgroup_alert`:
```jsx
{subGroupAlert && (
  <div className="asec-alert">   {/* reuse existing CSS class */}
    <p className="asec-alert__title">This occupational group has sub-groups that affect classification and JES scoring.</p>
    <p className="asec-alert__body">{subGroupAlert.disambiguation_text}</p>
    <div className="asec-alert__subgroups">
      {subGroupAlert.subgroups.map(sg => (
        <button
          key={sg}
          type="button"
          className={'choice' + (selectedSubGroup === sg ? ' is-sel' : '')}
          onClick={() => onSubGroupSelect(sg)}
        >
          <span className="choice__main">
            <span className="choice__title">{sg}</span>
            <span className="choice__desc">{subGroupAlert.descriptions[sg]}</span>
          </span>
        </button>
      ))}
    </div>
    <span className="asec-alert__cite">{subGroupAlert.citation}</span>
  </div>
)}
```
The `onSubGroupSelect` callback stores `confirmed_sub_group` on the WD via PATCH `/api/wd/{id}`. The `asec-alert` CSS class is reused without modification; the new button grid inherits `choice` styles already present.

---

## Shared Patterns

### Dict Extension Pattern
**Source:** `v2/backend/app/data/constants.py` throughout
**Apply to:** All constant extensions in constants.py
- Add new keys at the END of each dict, after existing entries
- Include a comment with source CSV/file name and level verification note for every new OG_LEVELS entry
- Keep the same inline comment format: `# CODE-XX to CODE-YY — source_file.csv`

### Test Assertion Style
**Source:** `v2/backend/tests/test_constants.py` lines 34–43
**Apply to:** All new test functions in test_constants.py, test_og_classification.py, test_jes_scoring.py
- f-string in assert messages: `f"{og_code} missing from {constant_name}"`
- `@pytest.mark.asyncio` decorator on all async tests
- Helper function `_create_wd_with_og` (test_jes_scoring.py line 81) is reused for all new JES tests — do not duplicate it

### Frontend Signal Option Shape
**Source:** `v2/frontend/src/data.jsx` lines 368–373
**Apply to:** All new QUESTION_BANK option entries in data.jsx STEPS
```javascript
{ id: 'snake_case_id', title: 'Human-readable text (NO OG codes)',
  signals: { og_candidates: ['XX'], jes_factor_hints: ['...'], teer_affinity: [1, 2] } }
```

### Import Consolidation
**Source:** `v2/backend/app/services/jes_service.py` lines 36–43
**Apply to:** `export_service.py` (OGX-02) and `jes_service.py` (OGX-05)
- Single import block from `app.data.constants`
- Never import from another service file — only from `app.data.constants`

---

## No Analog Found

All files in this phase have direct analogs (they are self-extensions). No files require patterns sourced from RESEARCH.md exclusively.

---

## Metadata

**Analog search scope:** `v2/backend/app/`, `v2/backend/tests/`, `v2/frontend/src/`
**Files scanned:** 10 (all read directly; no glob search needed — all files named explicitly in RESEARCH.md)
**Pattern extraction date:** 2026-06-10
