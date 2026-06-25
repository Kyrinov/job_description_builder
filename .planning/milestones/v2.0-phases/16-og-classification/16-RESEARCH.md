# Phase 16: OG Classification — Research

**Researched:** 2026-06-05
**Domain:** OG classification engine port + conversation wiring + hard gate
**Confidence:** HIGH — all findings from direct codebase inspection

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLASS-01 | Evidence-based OG classification: confirmed NOC + work description → top-3 OG candidates with verbatim TBS inclusions/exclusions and confidence scores | v1.0 `og_classifier.py` + `og_ranking.py` port; OG definitions must be hardcoded as a constant (v2.0 pattern); API: `POST /api/og/classify` |
| CLASS-02 | AS/EC disambiguation from `data/directive_on_classification.txt` verbatim | `directive_on_classification.txt` has 208 lines; it covers classification procedure/authority, NOT AS vs EC inclusions/exclusions directly — see Critical Finding below |
| CLASS-03 | Level selection after OG confirmed: render correct level range as choice cards; store in WorkDescription | New `og_level` conversation step after `og_confirm`; `OG_LEVELS` constant already in `app/data/constants.py`; STEPS array needs 2 new entries |
| CLASS-04 | Hard gate: JD generation blocked until OG + level both confirmed; document preview shows "Classification pending" | `WorkDescription` model needs `confirmed_og` and `og_level` fields; backend gate on any future POST /api/wd/{id}/export endpoint; frontend: document.jsx conditional render |
| CLASS-05 | CAF rank context: when position reports to military supervisor, display CAF rank equivalence with "advisory — not authoritative" label | `CAF_RANK_OG_EQUIVALENCE` is already populated in `app/data/constants.py`; needs a `reports_to_military` boolean in conversation + a display rule in document.jsx |
| API-06 | `POST /api/og/classify` — accepts confirmed NOC code + work description; returns top-3 OG candidates with verbatim rationale and confidence scores | New route `v2/backend/app/api/og_classification.py`; deterministic signal-based approach replaces LLM for main ranking; LLM retained only for rationale text |
| API-03 | `GET /api/og/definitions?og_code=EC` and `GET /api/quals/default?og_code=EC` | New routes in a `canonical.py` or `og_definitions.py` router; data from hardcoded constants (v2.0 pattern; no DB queries) |

</phase_requirements>

---

## Summary

Phase 16 is a **porting + extension phase** with four distinct work streams: (1) porting v1.0's OG classification logic into a deterministic v2.0 service, (2) wiring two new conversation steps into the STEPS array (og_confirm + og_level), (3) building three new API endpoints, and (4) implementing the CLASS-04 hard gate in both backend and frontend.

The most important architectural finding is a **v1.0 vs v2.0 strategy divergence**: v1.0's `og_classifier.py` uses an LLM (via `instructor`) to rank OG candidates, with a `PolicyAdjacencyResult` LLM call for AS/EC detection. The v2.0 architecture decision is "deterministic classification — LLM used only for NOC justification." This means Phase 16 must build a **signal-accumulation-based deterministic ranker** rather than directly porting the LLM ranking logic. The signals already exist: `accumulateSignals(answers)` in `data.jsx` tallies OG candidate codes from the four QUESTION_BANK answers. The backend classifier reads these tally signals from the request and maps them to ranked candidates against the hardcoded OG definition constant — no LLM call required.

A **critical data gap** exists for CLASS-01 and CLASS-02: the v1.0 `og_definitions` SQLite table was populated by an ingest script with AS/EC inclusions/exclusions text, but those columns are EMPTY in the actual database (`EC incl len: 0`, `EC excl len: 0`). The `directive_on_classification.txt` covers classification procedure authority (not AS vs EC work content distinctions). The AS/EC disambiguation must be sourced from the OG group definitions in `data/Job_evaluation/` files or encoded directly as a hardcoded constant. This is a Wave 0 design decision for the planner.

**Primary recommendation:** Build in four waves — (1) OG_DEFINITIONS hardcoded constant + AS/EC disambiguation text + test stubs, (2) `POST /api/og/classify` deterministic ranker + canonical endpoints, (3) STEPS array wiring (og_confirm + og_level steps) + OgConfirmList component, (4) hard gate + CLASS-04 document preview state + CLASS-05 CAF advisory.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| OG candidate ranking | Backend (FastAPI) | — | Deterministic signal accumulation; reads signals from request; returns ranked candidates with hardcoded OG definition text |
| AS/EC disambiguation text | Backend (FastAPI) | — | Verbatim citation hardcoded in constant; returned by `POST /api/og/classify` when AS + EC both appear in top-3 |
| OG confirmation card rendering | Frontend (React) | — | New `OgConfirmList` component; replaces the `og_confirm` stub from Phase 15 |
| Level selection rendering | Frontend (React) | — | New `og_level` STEP entry; renders ChoiceList with level cards from `OG_LEVELS[og_code]` |
| OG + level persistence | Frontend → Backend | SQLite | Each confirm calls PATCH /api/wd/{id} with `confirmed_og` + `og_level` fields |
| Hard gate (CLASS-04) | Backend (FastAPI) | Frontend | Backend: export endpoints check `confirmed_og` and `og_level` not null; Frontend: document preview shows "Classification pending" state |
| CAF rank advisory display | Frontend (React) | Backend (data source) | `CAF_RANK_OG_EQUIVALENCE` already in constants.py; frontend displays advisory when `record.reports_to_military === true` |
| OG definitions canonical endpoint | Backend (FastAPI) | — | `GET /api/og/definitions` serves hardcoded OG_DEFINITIONS constant; no DB query |
| Qual standard canonical endpoint | Backend (FastAPI) | — | `GET /api/quals/default` serves hardcoded QUAL_STANDARDS constant; no DB query |

---

## Critical Finding: v1.0 OG Definitions Data Gap

The v1.0 `og_definitions` table in `app.db` has 81 rows but **inclusions and exclusions columns are empty for all four target groups** (EC, AS, IT, FI):

```
EC def: 'Economics and Social Science Services (EC)'  [42 chars — just the group name]
EC incl len: 0
EC excl len: 0
```

The v1.0 classifier fetched from this DB table for its "evidence_quotes" verbatim guardrail. Since those columns are empty, the v1.0 quote verification would silently strip all evidence quotes. **For v2.0, OG definition text must be hardcoded as a constant** — consistent with the v2.0 "curated hardcoded data over v1.0 ingest pipelines" decision.

**Source for OG definition text:** `data/Job_evaluation/` directory contains the EC JES 2017 standard (and others). The GROUP DEFINITION section at the top of each file has the canonical verbatim text. For AS/EC disambiguation, the Job Evaluation Standards describe what each group covers; the `directive_on_classification.txt` file covers procedural authority and does NOT contain the AS vs EC work content distinctions needed for disambiguation.

**Action required in Wave 0:** Write `OG_DEFINITIONS` constant in `v2/backend/app/data/constants.py` with verbatim definition, inclusions, and exclusions text for EC, AS, IT, FI extracted from `data/Job_evaluation/` files.

---

## Port Analysis: v1.0 → v2.0 Delta

### v1.0 `og_classifier.py` — What It Does

**Inputs:**
- `work_description: str` — free text
- `confirmed_noc_code: str` — confirmed NOC code from Phase 14
- `db_path: str` — path to `app.db`

**3-step pipeline:**

| Step | What | LLM? | v2.0 equivalent |
|------|------|-------|-----------------|
| 1 | Fetch all OG rows from `og_definitions` DB table | No | Read from hardcoded `OG_DEFINITIONS` constant |
| 2 | AS/EC policy-adjacent detection via `PolicyAdjacencyResult` instructor call | YES — LLM | Replace with: if AS + EC both appear in accumulated signal tally → trigger disambiguation |
| 3 | Rank top-3 OG candidates via `OGRankingResult` instructor call | YES — LLM | Replace with: deterministic ranking from signal accumulation tally + NOC TEER affinity |

**Outputs:** `{"candidates": [...], "asec_alert": dict | None}`

Each candidate includes: `og_code`, `og_name`, `rank`, `confidence`, `rationale`, `evidence_quotes`, `definition_excerpt`, `relevant_inclusions`, `relevant_exclusions`, `available_levels`.

### v1.0 `og_ranking.py` — What It Does

Exports: `OGCandidate`, `OGRankingResult`, `PolicyAdjacencyResult`, `OG_LEVELS`, `SYSTEM_PROMPT`, `POLICY_DETECTION_PROMPT`, `build_og_context`, `og_instructor_client`.

**In v2.0:** `OG_LEVELS` is already ported to `app/data/constants.py` (Phase 11). The `og_instructor_client` singleton and instructor models (`OGCandidate`, `OGRankingResult`, `PolicyAdjacencyResult`) are NOT ported — v2.0 classification is deterministic.

### v2.0 Deterministic Ranker Design

```
Inputs from POST /api/og/classify:
  confirmed_noc_code: str
  work_description: str
  signal_tally: dict  # e.g. {"EC": 3, "AS": 1} from accumulateSignals()

Algorithm:
  1. Sort OG codes by tally count (descending)
  2. For tied codes, apply NOC TEER affinity tiebreak from signal tally
  3. Take top-3 codes
  4. For each: look up hardcoded OG_DEFINITIONS[og_code] for definition,
     inclusions, exclusions text
  5. Assign confidence scores: rank-1 = 0.85 * (votes/total_votes),
     rank-2 and rank-3 scaled down proportionally
  6. If AS + EC both in top-3: set asec_alert = {disambiguation text from constant}
  7. Return candidates list + asec_alert

Output candidate fields (same as v1.0 shape):
  og_code, og_name, rank, confidence, rationale (template-generated, not LLM),
  evidence_quotes ([], deterministic — no fabrication possible),
  definition_excerpt, relevant_inclusions, relevant_exclusions, available_levels
```

**No LLM calls in the OG classification path.** Rationale strings are template-generated: `"The signal profile from the work-type questions (X votes for {og_code}, {total} total signals) aligns with the {og_name} group, which covers: {definition_excerpt}."`

---

## AS/EC Disambiguation Data Analysis

**What we have:** `data/directive_on_classification.txt` (208 lines) covers classification authority and procedure — not AS vs EC work content. It does NOT contain the inclusions/exclusions needed for CLASS-02 disambiguation.

**What v1.0 did:** Built `asec_alert` from `og_definitions.as_inclusions_excerpt` and `og_definitions.ec_exclusions_excerpt` — but those columns are empty in the live DB.

**What v2.0 should do:** Hardcode the AS vs EC disambiguation text in `OG_DEFINITIONS` constant, sourced from:
- EC group definition: `data/Job_evaluation/EC Economics and Social Science Services - Job Evaluation Standard 2017.txt` — GROUP DEFINITION section: "The EC Group comprises positions primarily involved in the conduct of surveys, studies and projects in the social sciences; the identification, description and organization of archival, library, museum and gallery materials; the editing of legislation or the provision of advice on legal problems in specific fields; and the application of a comprehensive knowledge of economics, sociology or statistics to the conduct of economic, socio-economic and sociological research, studies, forecasts and surveys." [VERIFIED: direct file read]
- AS group definition: available in `data/agreements/` or via TBS OCHRO — needs to be sourced during Wave 0 research

**The AS/EC disambiguation alert in v2.0 should display:**
- EC group definition excerpt (verbatim)
- AS group definition excerpt (verbatim)
- Label: "Both Administrative Services (AS) and Economics and Social Science Services (EC) appear among the top candidates. Review the work description against each group definition before confirming."
- Citation: "TBS OCHRO Occupational Group Definitions" [ASSUMED source label — verify against actual source text]

**`directive_on_classification.txt` relevance:** The directive confirms classification authority flows through TBS OCHRO and describes that OG selection must use occupational group definitions. It can be cited as the policy reference ("TBS Directive on Classification, April 2021") but does not contain the verbatim OG inclusions/exclusions text.

---

## Conversation Flow Integration

### Current STEPS Array (Phase 15 delivered)

```javascript
// Phase 0 (Role): title, branch, reports, supervises  [4 steps]
// Phase 1 (Work Type): summary, qb_work_output_type, qb_work_audience,
//                       qb_knowledge_specialization, qb_policy_interpretation  [5 steps]
// Phase 2 (Classification): noc_confirm  [1 step — Phase 16 adds 2 more here]
// Phase 3 (Duties): duties  [1 step]
// Phase 4 (Qualifications): quals  [1 step]
```

The `noc_confirm` step is at `phase: 2`. Phase 16 adds two steps after it:

```javascript
// NEW: Phase 2 (Classification), after noc_confirm:
{ id: 'og_confirm', phase: 2, icon: I.compass,
  q: 'Review the top occupational group matches and confirm the best fit.',
  helper: 'Select the occupational group that best fits the work described.',
  input: { type: 'og_confirm', candidates: [] },
  apply: (r, a) => ({ confirmed_og: a }),
  transcript: a => a ? (a.og_code + ' — ' + a.og_name) : 'Pending' },

{ id: 'og_level', phase: 2, icon: I.ladder,
  q: 'Select the level for this position.',
  helper: 'Level ranges are derived from the collective agreement for the confirmed group.',
  input: { type: 'og_level', levels: [] },  // levels injected by app.jsx cfgOverride
  apply: (r, a) => ({ og_level: a }),
  transcript: a => a ? String(a) : 'Pending' },
```

**STEPS insertion point:** After the `noc_confirm` entry (index 10 in current 0-based STEPS), before `duties` (now at index 11 → shifts to 13 after insertion).

**Impact on phase index arithmetic:** Only Phase 2 (Classification) gains steps. Phases 3, 4 are unaffected. The `PHASES` array stays at 6 entries.

### app.jsx Changes for OG Pipeline

Following the same pattern as NOC pipeline wiring (Phase 15-04):

```javascript
// New state slices (after nocLoading):
const [ogCandidates, setOgCandidates] = useState([]);
const [ogLoading, setOgLoading] = useState(false);

// In commit(), after noc_confirm is committed:
if (step.id === 'noc_confirm') {
  setOgLoading(true);
  setOgCandidates([]);
  const signalTally = accumulateSignals(answers);
  fetch('/api/og/classify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      confirmed_noc_code: draft,        // draft is the confirmed noc_code string
      work_description: record.summary,
      signal_tally: signalTally?.tally || {},
    }),
  })
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(data => { setOgCandidates(data.candidates || []); setOgLoading(false); })
    .catch(() => { setOgLoading(false); });
}
```

**cfgOverride pattern for og_confirm step** (same as noc_confirm):
```javascript
const stepCfgOverride = !reviewing && step && step.input.type === 'noc_confirm'
  ? { ...step.input, candidates: nocCandidates, loading: nocLoading }
  : !reviewing && step && step.input.type === 'og_confirm'
  ? { ...step.input, candidates: ogCandidates, loading: ogLoading }
  : !reviewing && step && step.input.type === 'og_level'
  ? { ...step.input, levels: record.confirmed_og
        ? OG_LEVELS[record.confirmed_og.og_code] || []
        : [] }
  : undefined;
```

**OG invalidation on editingReturn:** If advisor re-answers `noc_confirm`, clear `ogCandidates` and remove `og_confirm` and `og_level` from answers (same guard pattern as NOC invalidation on Work Type re-answer).

---

## Frontend Component Patterns

### OgConfirmList Component

Replaces the `og_confirm` stub (currently `NocConfirmList` with wrong field names). New component `OgConfirmList` in `components.jsx`:

```javascript
// cfg.type === 'og_confirm'
// cfg.candidates: array from POST /api/og/classify response
// value: selected candidate object or null
// onChange(candidate): called on card click
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

**answerValid for og_confirm:** `return value !== null && value !== undefined && !!value.og_code;`

**StepInput dispatcher update:**
```javascript
// Replace current stub:
if (t === 'og_confirm') return <NocConfirmList {...props} />; // stub — Phase 16 replaces
// With:
if (t === 'og_confirm') return <OgConfirmList {...props} />;
```

### OgLevelPicker Component

```javascript
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

**answerValid for og_level:** `return typeof value === 'number' && value >= 1;`

### OG_LEVELS Import in Frontend

`OG_LEVELS` is a Python constant in `v2/backend/app/data/constants.py`. For the `og_level` cfgOverride (to populate level cards without an API call), a JS copy of `OG_LEVELS` is needed in `data.jsx` — following the same pattern as `QUESTION_BANK` (embedded as a static JS copy).

```javascript
// Add to data.jsx (JS copy of OG_LEVELS from constants.py)
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

This avoids an API round-trip for what is static reference data.

---

## API Contract

### POST /api/og/classify (API-06)

**File:** `v2/backend/app/api/og_classification.py`

```python
# Request
class OGClassifyRequest(BaseModel):
    confirmed_noc_code: str = Field(min_length=1)
    work_description: str = Field(min_length=10)
    signal_tally: dict[str, int] = Field(default_factory=dict)
    # e.g. {"EC": 3, "AS": 1, "IT": 0}

# Response
class OGCandidate(BaseModel):
    og_code: str
    og_name: str
    rank: int          # 1-3
    confidence: float  # 0.0-1.0
    rationale: str     # template-generated string
    evidence_quotes: list[str]   # verbatim excerpts from OG_DEFINITIONS
    definition_excerpt: str
    relevant_inclusions: str
    relevant_exclusions: str
    available_levels: list[int]  # from OG_LEVELS

class ASECAlert(BaseModel):
    disambiguation_text: str    # verbatim from OG definition constant
    citation: str               # e.g. "TBS OCHRO Occupational Group Definitions"

class OGClassifyResponse(BaseModel):
    candidates: list[OGCandidate]
    asec_alert: Optional[ASECAlert] = None
```

**Routing:** `POST /api/og/classify` (no leading `/api` in router — the prefix is added by `api_router`).

**Router registration:** Add to `v2/backend/app/api/__init__.py`:
```python
from . import health, noc_mapping, wd, og_classification
api_router.include_router(og_classification.router)
```

### GET /api/og/definitions?og_code=EC (API-03, part 1)

```python
class OGDefinitionResponse(BaseModel):
    og_code: str
    og_name: str
    definition: str
    inclusions: str
    exclusions: str

@router.get("/og/definitions")
async def get_og_definition(og_code: str) -> OGDefinitionResponse:
    if og_code not in OG_DEFINITIONS:
        raise HTTPException(status_code=404, detail=f"OG code {og_code!r} not found")
    defn = OG_DEFINITIONS[og_code]
    return OGDefinitionResponse(og_code=og_code, **defn)
```

### GET /api/quals/default?og_code=EC (API-03, part 2)

```python
class QualStandardResponse(BaseModel):
    og_code: str
    education: str
    experience: str
    source: str     # e.g. "TBS Qualification Standard for EC"

@router.get("/quals/default")
async def get_qual_default(og_code: str) -> QualStandardResponse:
    if og_code not in QUAL_STANDARDS:
        raise HTTPException(status_code=404, detail=f"Qual standard for {og_code!r} not found")
    return QualStandardResponse(og_code=og_code, **QUAL_STANDARDS[og_code])
```

**QUAL_STANDARDS constant:** Must be added to `v2/backend/app/data/constants.py`. Covers EC, AS, IT, FI at minimum. EC default already exists in `data.jsx` (`QUAL_DEFAULT` — but that is a hardcoded EC-05 environmental text; Phase 19 TODO). For Phase 16, the QUAL_STANDARDS constant provides the OG-group-level standard text (not level-specific). [ASSUMED: exact qualification standard text will be sourced from TBS Qualification Standards reference; must be verified against source docs in `data/` before encoding]

**Canonical router file:** Place both endpoints in `v2/backend/app/api/og_classification.py` or a new `v2/backend/app/api/canonical.py`. Single file is simpler since the canonical data endpoints have no business logic.

---

## WorkDescription Model Extensions

`v2/backend/app/models/work_description.py` must add two new fields:

```python
# Add to WorkDescription:
confirmed_og: Optional[dict] = None      # full OG candidate dict from POST /api/og/classify
og_level: Optional[int] = Field(default=None, ge=1)  # selected level integer
```

And `v2/backend/app/api/wd.py` `WDPatchRequest` must accept these new fields:

```python
# Add to WDPatchRequest:
confirmed_og: Optional[dict] = None
og_level: Optional[int] = None
```

The SPA calls `PATCH /api/wd/{id}` with `{confirmed_og: candidate, og_level: null}` on og_confirm, and `{og_level: selectedLevel}` on og_level. Both must be patchable independently.

---

## Hard Gate Implementation (CLASS-04)

### Backend Gate

The hard gate at the API layer blocks export operations. Since Phase 16 precedes Phase 20 (Export), the gate is implemented as a utility function in `v2/backend/app/services/` that is imported by future export routes:

```python
# v2/backend/app/services/classification_gate.py
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

The gate is not yet triggered by any Phase 16 route (no export endpoints exist yet), but the utility must be created so Phase 17/18/20 can import it.

### Frontend Gate (Document Preview)

`document.jsx` must check `record.confirmed_og` and `record.og_level` before rendering the Classification & Evaluation section. When either is null, render a "Classification pending" placeholder:

```javascript
// In document.jsx ClassificationSection:
if (!record.confirmed_og || !record.og_level) {
  return (
    <section className="doc-section doc-section--pending">
      <h3 className="doc-section__title">Classification & Evaluation</h3>
      <p className="doc-section__pending">
        Classification pending — confirm occupational group and level to proceed.
      </p>
    </section>
  );
}
```

The document preview already has ghost shimmer logic (Phase 18 will flesh out the full section); for Phase 16 a simple "Classification pending" string is sufficient.

---

## CLASS-05 CAF Rank Advisory

### Conversation Integration

The `reports` step (Phase 0) captures "Who does this position report to?" The answer is a free-text supervisor title. There is no existing boolean for "reports to military supervisor."

**Options:**
1. Add a follow-up step after `reports` — "Does this position report to a military officer?" → yes/no choice card — sets `record.reports_to_military = true/false`.
2. Parse the `reports` answer for military rank keywords (Maj, Lt, Col, Capt, etc.) — fragile.

**Recommendation:** Option 1 — add a single `reports_to_military` choice step at phase 0 immediately after `reports`. This keeps the Socratic flow clean and eliminates fragile string parsing. The step is short (2-option choice card) and does not change the phase numbering significantly.

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

### Display Location

When `record.reports_to_military === true` and `record.confirmed_og` is set, `document.jsx` displays the CAF rank advisory inline in the Position Identification section near the "Reports to" field:

```
Reports to: [reports field answer]
CAF Rank Equivalent (advisory — not authoritative): [rank equivalence text]
```

The `CAF_RANK_OG_EQUIVALENCE` table is keyed by rank name (e.g. "Major / Lieutenant-Commander"), not by OG code. Since Phase 16 confirms OG + level, the advisory can show all ranks whose `approx_civilian_og_levels` includes the confirmed OG-level string (e.g. "EC-06"). The frontend can compute this from a JS copy of the CAF table.

Alternatively, a `GET /api/caf/equivalence?og_level=EC-06` endpoint returns matching ranks — but that is an over-engineered round-trip for static data. Embed as a JS constant in `data.jsx` following the same pattern as `OG_LEVELS`.

---

## New Constants Required in v2/backend/app/data/constants.py

Phase 16 adds three new constants (alongside existing `OG_LEVELS`, `CAF_RANK_OG_EQUIVALENCE`, `KNOWN_JES_FACTORS`, `QUESTION_BANK`):

| Constant | Purpose | Data Source |
|----------|---------|-------------|
| `OG_DEFINITIONS` | dict mapping og_code → {og_name, definition, inclusions, exclusions} for all target groups | Extract verbatim from `data/Job_evaluation/` files + TBS OCHRO OG definitions |
| `QUAL_STANDARDS` | dict mapping og_code → {education, experience, source} | Extract from TBS Qualification Standards reference (source docs TBD — check `data/agreements/` or external URL) |
| `ASEC_DISAMBIGUATION` | dict with EC definition excerpt, AS definition excerpt, citation — displayed verbatim when AS + EC both in top-3 | Subsets of OG_DEFINITIONS; can be derived at runtime or pre-computed |

**OG_DEFINITIONS minimum coverage:** EC, AS, IT, FI. All other OG codes can have stub entries (definition only, empty inclusions/exclusions) for the `GET /api/og/definitions` endpoint.

---

## Standard Stack

### Core (already installed — no new deps needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing v2 backend | HTTP API + route registration | Already in use [VERIFIED: app/main.py] |
| Pydantic v2 | existing v2 backend | Request/response model validation | Pattern established in Phases 10–15 [VERIFIED] |
| React 18 | 18.3.1 | SPA components | Already installed [VERIFIED: package.json] |
| vitest | 4.1.8 | Frontend tests | Already installed [VERIFIED] |
| pytest | existing | Backend tests | 43/43 GREEN [VERIFIED: test run] |

**No new packages required for Phase 16.** Classification is deterministic (no instructor/LLM calls); all data is hardcoded constants; no new DB tables.

---

## Architecture Patterns

### System Architecture Diagram

```
Advisor selects NOC confirm card
      │
      ▼
commit() in app.jsx — step.id === 'noc_confirm'
      │
      ├──► PATCH /api/wd/{id}   (confirmed_noc persisted)
      │
      └──► POST /api/og/classify
             │  body: {confirmed_noc_code, work_description, signal_tally}
             │
             ▼
           OG classify route (og_classification.py)
             │
             ├── rank candidates from signal_tally + OG_DEFINITIONS
             ├── compute asec_alert if AS + EC both in top-3
             └── return OGClassifyResponse
             │
             ▼
      ogCandidates state populated
      STEPS advances to og_confirm step
             │
             ▼
      OgConfirmList renders candidates
             │
      Advisor selects OG candidate
             │
             ▼
      commit() — step.id === 'og_confirm'
             │
             ├──► PATCH /api/wd/{id}  (confirmed_og persisted)
             └──► STEPS advances to og_level step
             │
             ▼
      OgLevelPicker renders level cards (from OG_LEVELS[og_code])
             │
      Advisor selects level
             │
             ▼
      commit() — step.id === 'og_level'
             │
             ├──► PATCH /api/wd/{id}  (og_level persisted)
             └──► document.jsx Classification section unlocks (CLASS-04)
```

### Recommended Project Structure Changes

```
v2/backend/app/
├── api/
│   ├── __init__.py            MODIFY: add og_classification router
│   └── og_classification.py  NEW: POST /api/og/classify, GET /api/og/definitions,
│                                   GET /api/quals/default
├── data/
│   └── constants.py          MODIFY: add OG_DEFINITIONS, QUAL_STANDARDS, ASEC_DISAMBIGUATION
├── models/
│   └── work_description.py   MODIFY: add confirmed_og, og_level fields
│   └── wd.py                 MODIFY: WDPatchRequest add confirmed_og, og_level
├── services/
│   └── classification_gate.py  NEW: require_og_confirmed() utility
└── tests/
    └── test_og_classification.py  NEW: API-06, API-03, CLASS-04 tests

v2/frontend/src/
├── data.jsx           MODIFY: add og_confirm + og_level STEPS entries;
│                              add OG_LEVELS JS constant; export OG_LEVELS
├── app.jsx            MODIFY: add ogCandidates/ogLoading state slices;
│                              og trigger in commit(); og cfgOverride; og invalidation
├── components.jsx     MODIFY: replace og_confirm stub with OgConfirmList;
│                              add OgLevelPicker; add answerValid cases
└── document.jsx       MODIFY: Classification pending state (CLASS-04);
                               CAF rank advisory display (CLASS-05)
```

### Pattern 1: Deterministic OG Ranking

```python
# Source: derived from v1.0 og_classifier.py + v2.0 deterministic constraint
def _rank_og_candidates(
    signal_tally: dict[str, int],
    confirmed_noc_code: str,
) -> list[tuple[str, float]]:
    """Return list of (og_code, confidence) sorted by rank (highest first)."""
    if not signal_tally:
        # Fallback: no signals → return top OG groups in fixed priority order
        return [("EC", 0.55), ("AS", 0.35), ("IT", 0.10)]
    total = sum(signal_tally.values())
    ranked = sorted(signal_tally.items(), key=lambda x: x[1], reverse=True)
    results = []
    for og_code, votes in ranked[:3]:
        confidence = round(votes / total * 0.9, 3)  # max 90% from signals alone
        results.append((og_code, confidence))
    return results
```

### Pattern 2: OG Classify Route

```python
# v2/backend/app/api/og_classification.py
from fastapi import APIRouter
from app.data.constants import OG_LEVELS, OG_DEFINITIONS, ASEC_DISAMBIGUATION

router = APIRouter()

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
            evidence_quotes=[],  # deterministic — no fabricated quotes
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
```

### Anti-Patterns to Avoid

- **Using LLM for OG ranking:** v2.0 decision is deterministic classification. No `og_instructor_client`, no `instructor`, no `PolicyAdjacencyResult`. The signal tally from QUESTION_BANK answers is the ranking mechanism.
- **Fetching OG definitions from the v1.0 `app.db`:** That DB's `og_definitions` table has empty inclusions/exclusions columns. Do not read from it in v2.0.
- **Building a new SQLite table for OG definitions:** v2.0 uses curated hardcoded data. Add to `constants.py`, not a new table.
- **Resolving OG level on the backend:** The level options are pure display data from `OG_LEVELS`. Send the array in the API response (as `available_levels` on the candidate) and let the frontend render choice cards. The selected level comes back via PATCH /api/wd/{id}.
- **Storing signal_tally in WorkDescription:** Signal tally is transient, derived from QUESTION_BANK answers. It is not stored — it is computed from `answers` at classify-time and passed in the request body.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OG definition text storage | New SQLite table or ingest script | Hardcoded `OG_DEFINITIONS` constant in `constants.py` | v2.0 curated data pattern; v1.0 DB columns are empty anyway |
| Signal accumulation on backend | Backend tally computation | Frontend `accumulateSignals()` sends tally in request body | Signal accumulation is already client-side; avoid duplication |
| OG level list for UI | API round-trip `GET /api/og/levels/{og_code}` | JS copy of `OG_LEVELS` in `data.jsx` | Static data; no reason for round-trip |
| AS/EC disambiguation detection | Text classifiers or LLM | Simple set membership check (AS ∈ top-3 AND EC ∈ top-3) | Deterministic, fast, zero LLM cost |
| Qualification standard text | Dynamic TBS API fetch | `QUAL_STANDARDS` hardcoded constant in `constants.py` | Static reference data; TBS does not provide a public API |
| UUID for WD PATCH | Custom ID management | Existing `wd_id` state slice pattern from Phase 15 | Pattern already proven GREEN [VERIFIED: 43/43 tests pass] |

---

## Common Pitfalls

### Pitfall 1: signal_tally empty when advisor skips Work Type questions

**What goes wrong:** If the advisor edits/revisits and jumps past the QUESTION_BANK steps, `accumulateSignals(answers)` returns `null` (no votes tallied). The OG classify call sends `signal_tally: {}`. The deterministic ranker falls back to `[("EC", 0.55), ("AS", 0.35), ("IT", 0.10)]` — which may not reflect the actual work type.

**Why it happens:** `accumulateSignals` only tallies answers that exist in `answers`. Revisiting and not re-answering leaves the old answers in place; re-answering a Work Type step clears `noc_confirm` (Phase 15 logic) and should also clear `og_confirm` + `og_level`.

**How to avoid:** The NOC invalidation guard in `commit()` (phase 1 re-answer clears noc_confirm) must be extended to also clear `og_confirm` and `og_level`. Additionally, `noc_confirm` re-answer must clear `og_confirm` and `og_level`.

**Warning signs:** `ogCandidates` always shows EC/AS/IT as top-3 regardless of the advisor's answers; OG confirm card shows unexpected candidates.

### Pitfall 2: og_confirm answer shape mismatch

**What goes wrong:** `noc_confirm` stores a plain string (the noc_code). `og_confirm` must store the full candidate object (to persist `og_code`, `og_name`, `confidence` in WorkDescription). If the `apply` function stores only `a.og_code` instead of the full object, the level selection step cannot look up `OG_LEVELS[confirmed_og.og_code]`.

**Why it happens:** Following the `noc_confirm` pattern naively — `noc_confirm` stores a string; `og_confirm` needs a dict.

**How to avoid:** `apply: (r, a) => ({ confirmed_og: a })` where `a` is the full candidate object from `OgConfirmList.onChange(candidate)`. `answerValid` checks `value !== null && !!value.og_code`.

**Warning signs:** `record.confirmed_og` is a string like `"EC"` — level selection step has no object to look up `og_code` from.

### Pitfall 3: OgLevelPicker levels not populating

**What goes wrong:** `og_level` step renders with `cfg.levels = []` (empty) because the `cfgOverride` reads `record.confirmed_og.og_code` but `confirmed_og` is not yet set in `record` at the moment the `og_level` step renders.

**Why it happens:** The step transitions happen synchronously in `commit()`. When `og_confirm` is committed, `setRecord(newRecord)` is called but React state updates are asynchronous — on the next render, `record.confirmed_og` may not yet be the newly committed value.

**How to avoid:** In the `og_confirm` commit, use `newRecord.confirmed_og.og_code` (the local variable, not `record`) to derive the level list for the cfgOverride. Pass it through a local variable:

```javascript
// In commit(), when step.id === 'og_confirm':
// The cfgOverride for the NEXT step (og_level) is derived from newRecord, not record
```

The cfgOverride computes on each render from `record` — by the time `og_level` is the active step, `record.confirmed_og` will be set from the prior commit. This is safe as long as `og_confirm` precedes `og_level` in STEPS and the state update propagates before the next render.

**Warning signs:** `OgLevelPicker` renders with 0 choice cards; console warning about undefined `og_code`.

### Pitfall 4: Hard gate not wiring correctly to WDPatchRequest

**What goes wrong:** Calling `PATCH /api/wd/{id}` with `{confirmed_og: {...}}` fails with 422 because `WDPatchRequest` does not have a `confirmed_og` field.

**Why it happens:** `WDPatchRequest` was defined in Phase 15 with only the fields needed then. `confirmed_og` and `og_level` were not included.

**How to avoid:** Read `v2/backend/app/api/wd.py` `WDPatchRequest` and add `confirmed_og: Optional[dict] = None` and `og_level: Optional[int] = None` before implementing Phase 16 frontend wiring. The patch handler uses `setattr(wd, field, val)` on all non-None fields — confirmed fields are automatically persisted if present in the model.

**Warning signs:** 422 Unprocessable Entity on PATCH with body containing `confirmed_og`.

### Pitfall 5: og_definitions data gap blocks CLASS-01

**What goes wrong:** Phase 16 Wave 0 does not populate `OG_DEFINITIONS` constant with verbatim text. The `POST /api/og/classify` response has empty `definition_excerpt`, `relevant_inclusions`, `relevant_exclusions`. The SPA shows blank OG confirm cards.

**Why it happens:** The researcher flagged the v1.0 DB columns are empty; the planner must include an explicit task to write the `OG_DEFINITIONS` constant before implementing the classify route.

**How to avoid:** Wave 0 of Phase 16 must include a task that reads `data/Job_evaluation/*.txt` files and encodes verbatim GROUP DEFINITION text into `OG_DEFINITIONS` in `constants.py`. The EC definition is already confirmed: "The EC Group comprises positions primarily involved in the conduct of surveys, studies and projects in the social sciences..." [VERIFIED: direct file read of EC JES 2017.txt]

**Warning signs:** Test `test_og_definitions_ec_has_definition` fails; all OG confirm cards show empty description text.

---

## Test Strategy

### Backend Tests — New File: `test_og_classification.py`

Pattern follows `test_noc_pipeline.py` and `test_wd.py`. All tests use `pytest.mark.asyncio` and the existing `client` fixture from `conftest.py`.

```python
# test stubs (Wave 0 RED → Wave 1/2 GREEN)

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
    """POST /api/og/classify includes asec_alert when AS + EC both in top-3."""
    response = await client.post(
        "/api/og/classify",
        json={
            "confirmed_noc_code": "11109",
            "work_description": "Coordinates policy and administrative support",
            "signal_tally": {"EC": 2, "AS": 2},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("asec_alert") is not None

async def test_og_classify_no_asec_alert_when_only_ec(client):
    """POST /api/og/classify omits asec_alert when AS not in top-3."""
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
    """GET /api/og/definitions?og_code=EC returns EC definition."""
    response = await client.get("/api/og/definitions?og_code=EC")
    assert response.status_code == 200
    data = response.json()
    assert data["og_code"] == "EC"
    assert len(data["definition"]) > 20

async def test_og_definitions_404_for_unknown_code(client):
    """GET /api/og/definitions?og_code=ZZ returns 404."""
    response = await client.get("/api/og/definitions?og_code=ZZ")
    assert response.status_code == 404

async def test_quals_default_returns_ec_text(client):
    """GET /api/quals/default?og_code=EC returns education + experience text."""
    response = await client.get("/api/quals/default?og_code=EC")
    assert response.status_code == 200
    data = response.json()
    assert "education" in data
    assert "experience" in data
    assert len(data["education"]) > 10

async def test_patch_wd_confirmed_og_persists(client):
    """PATCH /api/wd/{id} with confirmed_og persists the OG candidate."""
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

**Minimum test count:** 7 backend tests for Phase 16 (targeting 50+ total v2 backend tests after this phase).

### Frontend Tests — Extend `conversation.test.jsx`

Add to `conversation.test.jsx`:

```javascript
// CONVO-04: OgConfirmList dispatches from StepInput
describe('CONVO-04: StepInput og_confirm type', () => {
  it('renders OgConfirmList with candidates from cfg', () => {
    const { getByText } = render(
      <StepInput
        cfg={{ type: 'og_confirm', candidates: [
          { og_code: 'EC', og_name: 'Economics...', confidence: 0.85, rank: 1,
            rationale: 'test', evidence_quotes: [], definition_excerpt: 'test',
            relevant_inclusions: '', relevant_exclusions: '', available_levels: [1,2,3,4,5] }
        ]}}
        value={null}
        onChange={() => {}}
        onSubmit={() => {}}
        record={{}}
      />
    );
    expect(getByText(/EC/)).toBeTruthy();
  });
});

// CLASS-03: OgLevelPicker renders level cards
describe('CLASS-03: OgLevelPicker renders level range', () => {
  it('renders level cards for EC (8 levels)', () => {
    const { getAllByRole } = render(
      <StepInput
        cfg={{ type: 'og_level', levels: [1,2,3,4,5,6,7,8] }}
        value={null}
        onChange={() => {}}
        onSubmit={() => {}}
        record={{}}
      />
    );
    const buttons = getAllByRole('button');
    expect(buttons.length).toBe(8);
  });
});
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (backend) | pytest (existing) |
| Framework (frontend) | vitest 4.1.8 + @testing-library/react 16.3.2 |
| Config file (backend) | `v2/backend/pyproject.toml` |
| Config file (frontend) | `v2/frontend/vitest.config.js` |
| Quick run command (backend) | `cd /home/charles/job_description_builder/v2/backend && python -m pytest tests/test_og_classification.py -x` |
| Quick run command (frontend) | `cd /home/charles/job_description_builder/v2/frontend && npm test` |
| Full suite command | `python -m pytest` (backend) + `npm test` (frontend) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLASS-01 | `POST /api/og/classify` returns top-3 candidates | integration | `python -m pytest tests/test_og_classification.py::test_og_classify_returns_candidates -x` | ❌ Wave 0 |
| CLASS-02 | `asec_alert` present when AS + EC in top-3 | integration | `python -m pytest tests/test_og_classification.py::test_og_classify_asec_alert_when_both_present -x` | ❌ Wave 0 |
| CLASS-03 | OgLevelPicker renders correct level range | unit | `npm test` | ❌ Wave 0 |
| CLASS-04 | `confirmed_og` + `og_level` persist via PATCH | integration | `python -m pytest tests/test_og_classification.py::test_patch_wd_confirmed_og_persists -x` | ❌ Wave 0 |
| CLASS-04 | Document preview shows "Classification pending" | unit | `npm test` | ❌ Wave 0 |
| CLASS-05 | CAF advisory displays when reports_to_military=true | unit | `npm test` | ❌ Wave 0 |
| API-06 | `POST /api/og/classify` 200 with valid body | integration | `python -m pytest tests/test_og_classification.py -x` | ❌ Wave 0 |
| API-03 | `GET /api/og/definitions?og_code=EC` returns definition | integration | `python -m pytest tests/test_og_classification.py::test_og_definitions_returns_ec_definition -x` | ❌ Wave 0 |
| API-03 | `GET /api/quals/default?og_code=EC` returns text | integration | `python -m pytest tests/test_og_classification.py::test_quals_default_returns_ec_text -x` | ❌ Wave 0 |

### Current Baseline
- Backend: 43/43 GREEN [VERIFIED: direct test run 2026-06-05]
- Frontend: 18/18 GREEN [VERIFIED: direct test run 2026-06-05]

### Wave 0 Gaps
- [ ] `v2/backend/tests/test_og_classification.py` — covers CLASS-01, CLASS-02, CLASS-04, API-06, API-03 (7 stubs)
- [ ] `v2/frontend/src/conversation.test.jsx` additions — covers CLASS-03, CLASS-04 (document pending), CLASS-05 (2–3 new tests)

*(All other infrastructure exists — no new frameworks or config files needed)*

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| FastAPI + uvicorn | OG classification routes | ✓ | existing v2 backend | — |
| Pydantic v2 | Request/response models | ✓ | existing v2 backend | — |
| SQLite (stdlib) | WD CRUD via existing wd.py | ✓ | stdlib | — |
| pytest + asyncio | Backend tests | ✓ | 43/43 passing | — |
| vitest + @testing-library/react | Frontend tests | ✓ | 18/18 passing | — |
| React 18 + Vite | SPA components | ✓ | 18.3.1 / 5.4.10 | — |
| Ollama | NOT needed — classification is deterministic | n/a | n/a | — |

**No missing dependencies.** Phase 16 is fully self-contained in the existing v2.0 stack.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user local app |
| V3 Session Management | no | Single-user local app |
| V4 Access Control | no | Single endpoint; no roles |
| V5 Input Validation | yes | Pydantic v2 on all request bodies (OGClassifyRequest, WDPatchRequest) |
| V6 Cryptography | no | No secrets in this phase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Arbitrary `signal_tally` OG codes in classify request | Tampering | Classifier validates og_code ∈ OG_DEFINITIONS before including in candidates; unknown codes silently ignored |
| Oversized `work_description` in classify request | DoS | Pydantic Field `max_length=2000` on `work_description`; truncate at service layer (mirrors v1.0 500-char limit) |
| `og_level` outside valid range for confirmed OG | Tampering | `WDPatchRequest.og_level` has `ge=1`; service layer validates `og_level ∈ OG_LEVELS[confirmed_og.og_code]` before persisting |
| Fabricated `og_code` in PATCH body confirmed_og | Tampering | Validate `confirmed_og.og_code ∈ OG_DEFINITIONS` on PATCH; return 422 if unknown code |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | AS group definition verbatim text will be found in `data/agreements/` or `data/Job_evaluation/` directories | Critical Finding — OG Definitions | If text is not in data/, planner must add a Wave 0 research task to locate TBS OCHRO source and encode it; blocks CLASS-01/CLASS-02 |
| A2 | TBS Qualification Standards reference text for AS, IT, FI is available in project data files | API-03 | If not available, QUAL_STANDARDS constant will have stubs for non-EC groups; QUAL-01 (Phase 19) will be the corrective phase |
| A3 | The `cfgOverride` pattern from Phase 15 (noc_confirm) is stable and can be extended to og_confirm and og_level with the same mechanism | Architecture Patterns | If app.jsx was modified post Phase 15 research, read the current app.jsx before implementing |
| A4 | `directive_on_classification.txt` is cited as policy authority for OG classification, not as the verbatim source of AS/EC content distinctions | CLASS-02 | The disambiguation text must come from OG group definitions, not the directive; mis-sourcing would produce a procedurally-correct but content-wrong citation |
| A5 | Adding `reports_to_military` as a new Phase 0 step does not break Phase 15's step-index-dependent logic | CLASS-05 | If Phase 15's FLASH map, phase chip logic, or any step-id-hardcoded logic references specific step indices (not step IDs), insertion will cause bugs; read app.jsx FLASH map before inserting |

---

## Open Questions (RESOLVED)

1. **AS group definition text source** — RESOLVED: Plan 16-01 Task 1 adds a Wave 0 discovery task that reads `data/agreements/` and sources verbatim AS group definition text from TBS OCHRO if absent; hardcoded in OG_DEFINITIONS constant.
2. **Qualification standard text for AS, IT, FI** — RESOLVED (deferred to Phase 19): Plan 16-01 confirms QUAL_DEFAULT remains EC-05 for this phase; AS/IT/FI qual standard text is a Phase 19 deliverable (QUAL-01). Out of scope for Phase 16.
3. **reports_to_military step insertion point** — RESOLVED: Plan 16-03 Task 2 Edit 4 reads app.jsx FLASH map before inserting. FLASH map confirmed to use step.id keys (not indices); no hardcoded index references found. Insertion is safe (confirmed by Plan 16-03 threat model entry T-16-07).

---

## Sources

### Primary (HIGH confidence)
- `app/services/og_classifier.py` — v1.0 3-step pipeline, inputs/outputs, DB dependencies — directly read
- `app/ai/og_ranking.py` — v1.0 OG ranking models, OG_LEVELS, instructor singleton — directly read
- `v2/backend/app/data/constants.py` — OG_LEVELS (12 groups, verified correct), CAF_RANK_OG_EQUIVALENCE (14 entries) — directly read
- `v2/backend/app/api/wd.py` — WDPatchRequest shape, existing CRUD routes — directly read
- `v2/backend/app/models/work_description.py` — WorkDescription fields — directly read
- `v2/backend/app/db.py` — v2.0 schema (no og_definitions table) — directly read
- `v2/frontend/src/data.jsx` — STEPS array (12 entries), PHASES, OG_LEVELS needed in JS, accumulateSignals — directly read
- `v2/frontend/src/components.jsx` — StepInput dispatcher, og_confirm stub, NocConfirmList pattern — directly read
- `v2/frontend/src/app.jsx` — cfgOverride pattern, nocCandidates state, commit() shape — inspected via Phase 15-04 plan
- `data/Job_evaluation/EC Economics and Social Science Services - Job Evaluation Standard 2017.txt` — EC GROUP DEFINITION verbatim text — directly read
- `data/directive_on_classification.txt` — content confirmed as procedural authority only (not AS/EC inclusions) — directly read (208 lines)
- SQLite `app.db` og_definitions table — EC inclusions=0, EC exclusions=0 — directly queried

### Secondary (MEDIUM confidence)
- Phase 15-04 plan — cfgOverride + nocCandidates pattern — confirmed wiring approach for OG pipeline
- Phase 15 RESEARCH.md — STEPS structure, phase index mapping — confirmed stable

### Tertiary (LOW confidence — see Assumptions Log)
- AS group definition text location [A1] — not yet verified in project data files
- Qualification standard text for AS/IT/FI [A2] — not yet located in data/

---

## Metadata

**Confidence breakdown:**
- Port analysis (v1.0 → v2.0 delta): HIGH — both files directly read
- OG definitions data gap: HIGH — DB queried directly; columns confirmed empty
- Conversation flow integration: HIGH — STEPS array directly read; insertion points exact
- Frontend component patterns: HIGH — NocConfirmList pattern directly read
- API contract: HIGH — existing route patterns directly verified
- AS/EC disambiguation source: MEDIUM — directive content confirmed NOT to be the source; AS OG definition text location not yet verified
- Qualification standard text: LOW — QUAL_DEFAULT in data.jsx confirmed EC-05 only; other groups not found in data/ yet

**Research date:** 2026-06-05
**Valid until:** 2026-07-05 (stable stack; no fast-moving dependencies)
