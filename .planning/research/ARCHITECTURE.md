# Architecture Research — v4.0 Seven-Elements Conversational Architecture

**Project:** JD Builder v4.0
**Date:** 2026-06-19
**Based on:** v3.0 complete codebase at Phase 25
**Confidence:** HIGH — based on direct codebase read, not WebSearch inference

---

## Existing Architecture Baseline (Phase 25 state)

```
v2/backend/app/
├── api/               — 8 routers: health, wd, noc_mapping, og_classification,
│                         jes_scoring, amendments, export, sjd
├── ai/                — jes_scoring.py, noc_ranking.py
├── data/constants.py  — OG_LEVELS (22 groups), QUESTION_BANK, OG_DEFINITIONS,
│                         QUAL_STANDARDS, EC_JES_ELEMENTS, JES_FACTORS_BY_GROUP
├── models/            — WorkDescription, DraftDuty, Classification, JESFactor,
│                         NOCMatch, QualificationStandard
├── services/          — export_service.py, jes_service.py, noc_mapper.py,
│                         classification_gate.py, duty_validator.py, risk_auditor.py
├── templates/         — wd_accessible_template.docx, poster_template.docx
└── main.py            — App factory with lifespan schema creation

v2/frontend/src/
├── app.jsx            — Root; ~15 state slices; commit()/exportAs() flow
├── data.jsx           — STEPS (28 entries), PHASES, OG_LEVELS, QUAL_DEFAULTS,
│                         accumulateSignals(), isStepVisible(), getVisibleSteps()
├── conversation.jsx   — Exchange, ActiveQuestion, ReviewState components
├── document.jsx       — DocumentPane, ClassBlock, Sec, OrphanBadge, buildOverview()
├── components.jsx     — Icon, initialAnswer, answerValid, NocConfirmList, OgConfirmList
└── styles.css

SQLite: work_descriptions (id, title, data JSON, schema_version, created_at, last_modified)
        audit_log (id, wd_id, event, actor, detail, created_at)
```

WorkDescription fields as of Phase 25:
- id, title, schema_version, created_at, last_modified
- record: dict (committed answers blob)
- answers: dict (per-step answer history)
- step_index: int, draft: Optional[dict], reviewing: bool, editing_return: bool
- classification: Optional[Classification]
- duties: list[DraftDuty]
- qualification: Optional[QualificationStandard]
- drf_id: Optional[str]
- noc_candidates: list[NOCMatch], confirmed_noc: Optional[Union[str, NOCMatch, dict]]
- confirmed_og: Optional[Union[str, dict]], confirmed_sub_group: Optional[str]
- og_level: Optional[int]
- sjd_source: Optional[dict]
- reports_to_military: Optional[bool]
- jes_scores: list[dict], jes_total_points: Optional[int]

model_config = ConfigDict(extra="ignore") — unknown fields silently discarded on load.

---

## Question 1: Where does user_role live?

**Decision: React state in app.jsx, persisted to localStorage.**

### Rationale

`user_role` is a session-level UX preference, not a WorkDescription property. Three options:

**Option A: WorkDescription field (backend)**
- Con: WD is a document artifact, not a session preference. A single WD could be started by an advisor and amended by a manager — encoding role into the WD conflates session and document concerns.
- Con: Requires a PATCH on every session start before any work begins.
- Con: The 7-element structured data export must work regardless of which role created the WD; role should not gate data availability.

**Option B: React state only (ephemeral)**
- Con: A page refresh clears the role selection, dropping the user back to the role picker on every reload.

**Option C: React state + localStorage (recommended)**
- Matches the existing pattern for `record` (localStorage key `jd-builder-v2-record`) and `wd_id` (`jd-builder-v2-wd-id`).
- Add a third key: `jd-builder-v2-role` storing `"advisor"` or `"manager"`.
- On app boot, lazy-initialize `userRole` from localStorage via the same `useState(() => { try { return localStorage.getItem(...) } catch { return null } })` pattern.
- Clearing the localStorage key (new session button) resets both role and WD.

**Implementation:**
```jsx
// app.jsx — new state slice
const [userRole, setUserRole] = useState(() => {
  try { return localStorage.getItem('jd-builder-v2-role') || null; } catch { return null; }
});

// Persist on change
useEffect(() => {
  try { if (userRole) localStorage.setItem('jd-builder-v2-role', userRole); } catch {}
}, [userRole]);
```

**Role selector gate:** when `userRole === null`, render a role-selection screen before the STEPS flow. This is a single conditional render on `<App>` body, not a new STEPS entry — role selection precedes WD creation and should not be in the conversation transcript.

**STEPS conditionality:** pass `userRole` as a prop to `<ReviewState>`, `<DocumentPane>`, and the classification components. Manager mode suppresses OG/JES/CBA panels in the review pane. This is a display filter on existing components — no new routing.

---

## Question 2: Adding org_context and responsibilities to WorkDescription

**Decision: New Optional fields on WorkDescription model; captured in record dict; no DB migration.**

### Backward compatibility

`model_config = ConfigDict(extra="ignore")` means existing rows with no `org_context` or `responsibilities_narrative` field will simply load without those fields present — they default to `None`. No migration script, no schema version bump required. New fields only appear in the `data` JSON blob when a new-flow WD is saved.

### Field placement strategy

Two fields need to be added. The key question is whether they live at the **WorkDescription root** or only inside **record dict**.

Existing precedent in the codebase:
- Fields the export pipeline reads directly → stored at WD root (e.g. `confirmed_og`, `og_level`, `duties`, `qualification`, `jes_scores`)
- Fields only the live preview reads → stored in `record` dict (e.g. `branch`, `reports`, `title`, `summary`, `client_service_results`)

`org_context` and `responsibilities_narrative` are needed by:
1. The export pipeline (`_build_wd_context` in `export_service.py`) — for the seven-elements structured export and for the Enhanced Job Poster
2. The `POST /api/wd/{id}/validate-elements` completeness audit
3. The document preview (`document.jsx`)

Because they are consumed by the backend export pipeline AND the completeness audit endpoint, they must be readable from the stored `WorkDescription` object without parsing the `record` dict. Store them at the WD root.

**WorkDescription additions:**
```python
# app/models/work_description.py
org_context: Optional[str] = None          # Phase 26: Organizational Context step
responsibilities_narrative: Optional[str] = None  # Phase 27: Responsibilities Narrative step
```

**WDPatchRequest additions:**
```python
# app/api/wd.py — WDPatchRequest
org_context: Optional[str] = None
responsibilities_narrative: Optional[str] = None
```

**STEPS additions:**
```js
// data.jsx — two new entries
{ id: 'org_context', phase: 0, icon: I.org,
  q: 'Describe the organizational context for this position.',
  helper: 'Where does this position fit in the organization? What is its mandate?',
  input: { type: 'textarea', placeholder: 'e.g. The position is located in the ...' },
  apply: (r, a) => ({ org_context: a }),
  transcript: a => a ? a.slice(0, 60) + '...' : 'Pending' },

{ id: 'responsibilities_narrative', phase: 3, icon: I.ladder,
  q: 'Describe the decision-making authority and delegation scope.',
  helper: 'Applicable to supervisory or senior individual-contributor positions.',
  input: { type: 'textarea', placeholder: 'e.g. The incumbent has authority to...' },
  // Gate: only show for supervisory/senior roles
  visible: (answers) => ['few','team','many'].includes(answers.supervises?.id),
  apply: (r, a) => ({ responsibilities_narrative: a }),
  transcript: a => a ? a.slice(0, 60) + '...' : 'Pending' },
```

**commit() mirroring:** following the existing pattern where `confirmed_og`, `og_level`, etc. are mirrored from `record` up to the PATCH root:
```js
// app.jsx commit() — extend the mirror list
['confirmed_noc', 'confirmed_og', 'og_level', 'reports_to_military',
 'jes_scores', 'jes_total_points',
 'org_context', 'responsibilities_narrative'].forEach(k => {
  if (k in newRecord) wdPayload[k] = newRecord[k];
});
```

**SJD pre-fill for org_context:** when `POST /api/wd/{id}/sjd-start` is called, the SJD entry's `organizational_context` text (already parsed into `SJDEntry` in Phase 22) pre-fills `wd.org_context` on the backend. The frontend should also pre-populate the `org_context` draft answer after the `sjd-start` response returns, using the same pattern as the existing record-update on sjd-start.

---

## Question 3: Structured data export — field mapping

The seven Part 2 elements and their sources in the existing data model:

| Element | Source field | Path | Notes |
|---------|-------------|------|-------|
| Organizational Context | `wd.org_context` | WD root (new) | Falls back to `_build_organizational_context_text(wd)` computed from branch/reports/summary |
| Client Service Results | `wd.record.get('client_service_results')` | record dict | Existing Phase 23 STEPS entry |
| Key Activities | `wd.duties` | WD root list[DraftDuty] | Each DraftDuty has `.text`, `.provenance_noc_code`, `.advisor` |
| Skills (Qualifications) | `wd.qualification.education` + `wd.qualification.experience` | WD root | Falls back to `wd.record.get('quals')` |
| Effort | `wd.jes_scores` filtered by category=='Effort' | WD root | Via `_factor_category_map()` + `JES_FACTORS_BY_GROUP` |
| Responsibility | `wd.responsibilities_narrative` (new) + JES responsibility factors | WD root (new) | New field; can also derive from JES responsibility-category scores as supplementary |
| Working Conditions | `wd.jes_scores` filtered by category=='Conditions' | WD root | Via `_factor_category_map()` |

**Transformations needed for structured export:**

1. **Organizational Context** — use `wd.org_context` directly (new field). If blank, fall back to `_build_organizational_context_text(wd)`. No transformation needed — it's a plain text string.

2. **Client Service Results** — read from `wd.record.get('client_service_results', '')`. Plain text, no transformation.

3. **Key Activities** — transform `list[DraftDuty]` into:
   ```python
   [{"text": d.text, "noc_code": d.provenance_noc_code or None, "source": "sjd" if d.source == "sjd" else ("advisor" if d.advisor else "noc")} for d in wd.duties]
   ```
   For CSV: flatten to one row per duty with columns `duty_text`, `noc_code`, `source`.

4. **Skills** — merge education and experience into a dict:
   ```python
   qual = wd.qualification or QualificationStandard(**((wd.record or {}).get('quals') or {}))
   {"education": qual.education, "experience": qual.experience}
   ```
   For CSV: two columns `skills_education`, `skills_experience`.

5. **Effort** — use `_factor_category_map()` to bucket `wd.jes_scores`:
   ```python
   cat_map = _factor_category_map()
   effort = [s for s in wd.jes_scores if cat_map.get(s.get('factor_name', '')) == 'Effort']
   # Each s is {"factor_name": ..., "degree": ..., "points": ..., "rationale": ...}
   ```
   For CSV: flatten to `effort_factor`, `effort_degree`, `effort_points`.

6. **Responsibility** — prefer `wd.responsibilities_narrative` (new free-text field). Supplement with JES responsibility factors as machine-readable signals:
   ```python
   responsibility_factors = [s for s in wd.jes_scores if cat_map.get(s.get('factor_name', '')) == 'Responsibility']
   {"narrative": wd.responsibilities_narrative or "", "jes_factors": responsibility_factors}
   ```
   For CSV: `responsibility_narrative` column plus `responsibility_jes_factors` as a JSON string.

7. **Working Conditions** — same pattern as Effort:
   ```python
   wc = [s for s in wd.jes_scores if cat_map.get(s.get('factor_name', '')) == 'Conditions']
   ```

**New service function** in `export_service.py`:
```python
def build_seven_elements(wd: WorkDescription) -> dict:
    """Map WorkDescription fields to the 7 Part 2 elements."""
    cat_map = _factor_category_map()
    scores = wd.jes_scores or []
    record = wd.record or {}

    qual = wd.qualification
    if qual is None:
        rq = record.get('quals') or {}
        qual_education = rq.get('education', '')
        qual_experience = rq.get('experience', '')
    else:
        qual_education = qual.education
        qual_experience = qual.experience

    return {
        "organizational_context": wd.org_context or _build_organizational_context_text(wd),
        "client_service_results": (record.get('client_service_results') or '').strip(),
        "key_activities": [
            {"text": d.text, "noc_code": d.provenance_noc_code or None,
             "source": "sjd" if d.source == "sjd" else ("advisor" if d.advisor else "noc")}
            for d in (wd.duties or [])
        ],
        "skills": {"education": qual_education, "experience": qual_experience},
        "effort": [s for s in scores if cat_map.get(s.get('factor_name', '')) == 'Effort'],
        "responsibility": {
            "narrative": wd.responsibilities_narrative or '',
            "jes_factors": [s for s in scores if cat_map.get(s.get('factor_name', '')) == 'Responsibility'],
        },
        "working_conditions": [s for s in scores if cat_map.get(s.get('factor_name', '')) == 'Conditions'],
    }
```

**JSON export endpoint:**
```python
@router.post("/wd/{wd_id}/export/json")
async def export_json(wd_id: str) -> Response:
    wd = _load_wd(wd_id, get_settings().db_path)
    payload = build_seven_elements(wd)
    payload["wd_id"] = wd_id
    payload["exported_at"] = datetime.utcnow().isoformat()
    return Response(
        content=json.dumps(payload, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{wd_id}-elements.json"'}
    )
```

**CSV export endpoint:**
```python
import csv, io

@router.post("/wd/{wd_id}/export/csv")
async def export_csv(wd_id: str) -> Response:
    wd = _load_wd(wd_id, get_settings().db_path)
    elements = build_seven_elements(wd)
    # One row per duty (key_activities), side-by-side with scalar fields
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=[
        'wd_id', 'organizational_context', 'client_service_results',
        'duty_text', 'duty_noc_code', 'duty_source',
        'skills_education', 'skills_experience',
        'effort_factors_json', 'responsibility_narrative',
        'responsibility_jes_factors_json', 'working_conditions_json',
    ])
    writer.writeheader()
    duties = elements['key_activities'] or [{}]
    for duty in duties:
        writer.writerow({
            'wd_id': wd_id,
            'organizational_context': elements['organizational_context'],
            'client_service_results': elements['client_service_results'],
            'duty_text': duty.get('text', ''),
            'duty_noc_code': duty.get('noc_code', ''),
            'duty_source': duty.get('source', ''),
            'skills_education': elements['skills']['education'],
            'skills_experience': elements['skills']['experience'],
            'effort_factors_json': json.dumps(elements['effort']),
            'responsibility_narrative': elements['responsibility']['narrative'],
            'responsibility_jes_factors_json': json.dumps(elements['responsibility']['jes_factors']),
            'working_conditions_json': json.dumps(elements['working_conditions']),
        })
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{wd_id}-elements.csv"'}
    )
```

---

## Question 4: Build order

Feature dependency graph:

```
Feature 1: org_context field + STEPS entry
Feature 2: responsibilities_narrative field + gated STEPS entry
Feature 3: Seven-Elements Completeness Audit endpoint
Feature 4: Manager-Track UX (role selector)
Feature 5: Enhanced Job Poster (consumes new fields)
Feature 6: Structured Data Export JSON+CSV (consumes new fields)
```

Dependencies:
- Feature 3 reads `org_context` + `responsibilities_narrative` → depends on Features 1 and 2
- Feature 5 reads `org_context` → depends on Feature 1
- Feature 6 reads `org_context` + `responsibilities_narrative` → depends on Features 1 and 2
- Feature 4 is UX-only (state + display filter) with no model dependencies → independent

**Recommended build order:**

### Phase 26: org_context (Feature 1)
Lowest risk, highest leverage. Adds one new WorkDescription field + one STEPS entry + SJD pre-fill hook. Unlocks all downstream features.

Deliverables:
- `WorkDescription.org_context: Optional[str] = None`
- `WDPatchRequest.org_context: Optional[str] = None`
- `STEPS` entry `'org_context'` in Phase 0 (after branch, before reports_to_military)
- commit() mirror: add `'org_context'` to the mirror list
- `POST /api/wd/{id}/sjd-start` extended: write `wd.org_context = entry.organizational_context` when the SJD entry has it
- `_build_wd_context()` in export_service: use `wd.org_context` preferentially over the computed fallback for `organizational_context_text`
- `buildOverview()` in document.jsx: use `record.org_context` when present for the preview pane
- Tests: model round-trip, PATCH field, SJD pre-fill sets field, export context builder

### Phase 27: responsibilities_narrative + completeness audit (Features 2 + 3)
Build together — the completeness audit endpoint is trivial once the fields exist, and shipping it immediately validates the field contract.

Deliverables:
- `WorkDescription.responsibilities_narrative: Optional[str] = None`
- `WDPatchRequest.responsibilities_narrative: Optional[str] = None`
- Gated STEPS entry `'responsibilities_narrative'` in Phase 3, after duties, conditional on `supervises` answer
- `isStepVisible()` extension: case for `'responsibilities_narrative'` returns `['few','team','many'].includes(answers.supervises?.id)`
- commit() mirror: add `'responsibilities_narrative'`
- `POST /api/wd/{id}/validate-elements` endpoint:
  - Reads WD; for each of the 7 elements checks populated/derived/missing
  - Returns `{elements: [{name, status, value_preview}]}` where status is `"populated"`, `"derived"`, or `"missing"`
  - No gate — advisory badge only
- `ReviewState` completeness badge: renders element status summary (e.g. "6/7 elements complete")
- Tests: gating logic, PATCH field, validate-elements endpoint, status logic

### Phase 28: Manager-Track UX (Feature 4)
Independent of field additions. UX-only change with no backend model changes.

Deliverables:
- `userRole` state in app.jsx, persisted to `jd-builder-v2-role` localStorage key
- Role selector screen (rendered when `userRole === null`): two cards — "Classification Advisor" / "Hiring Manager"
- Manager mode: suppress OG/JES classification pane in document preview; suppress CBA audit panel in ReviewState; rename PHASES label for manager context
- Advisor mode: full existing UX, no change
- `userRole` passed as prop to `<ReviewState>`, `<DocumentPane>`, `<ClassBlock>`
- Tests: role selection renders, role persists on reload, manager mode hides classification block

### Phase 29: Enhanced Job Poster + Structured Data Export (Features 5 + 6)
Build together — both consume the same `build_seven_elements()` function and can share a single phase.

Deliverables:
- `build_seven_elements(wd)` function in `export_service.py`
- Enhanced poster: extend `_build_poster_context()` to pass `org_context`, `key_activities` (as top-5 duties), `skills`
- Update `poster_template.docx`: add "About the Organization" section consuming `org_context`, rename "Qualifications" to include skills context
- `POST /api/wd/{id}/export/json` endpoint
- `POST /api/wd/{id}/export/csv` endpoint
- Frontend: two new `exportAs('json')` and `exportAs('csv')` branches in app.jsx
- Structured export buttons in ReviewState (separate from DOCX/poster buttons)
- Tests: `build_seven_elements()` with full/partial/empty WD, JSON endpoint, CSV endpoint, poster context builder

---

## New Components

### Backend: `app/api/elements.py` (new)

Routes for the seven-elements audit and structured export:

```python
POST /api/wd/{wd_id}/validate-elements   # completeness audit (Phase 27)
POST /api/wd/{wd_id}/export/json         # JSON structured export (Phase 29)
POST /api/wd/{wd_id}/export/csv          # CSV structured export (Phase 29)
```

Mount in `main.py` alongside existing routers. No classification gate on validate-elements (advisory). JSON/CSV export require no OG confirmation — they export whatever is present.

### Frontend: Role selector screen

A pre-flow screen (not in STEPS) rendered when `userRole === null`. Single JSX block in app.jsx above the STEPS flow. Two cards: advisor / manager. On selection, sets `userRole` state + localStorage key, advances to the existing STEPS flow.

### Frontend: Completeness badge in ReviewState

A badge component in `conversation.jsx` — rendered in the ReviewState left pane when `elementStatuses` state is available. Shows "N/7 elements complete" with a breakdown list. Fetches `POST /api/wd/{id}/validate-elements` on review entry (same trigger as orphan check and amendment hydration).

---

## Modified Components

| Component | What changes | Why |
|-----------|-------------|-----|
| `WorkDescription` model | +`org_context`, +`responsibilities_narrative` | New fields |
| `WDPatchRequest` | +`org_context`, +`responsibilities_narrative` | New fields mirrored from frontend |
| `app/api/wd.py` patch_wd() | Mirror new fields in body_dump loop | Automatic via `setattr` loop already in place |
| `export_service._build_wd_context()` | Use `wd.org_context` for `organizational_context_text` | New field available |
| `export_service._build_poster_context()` | Add `org_context`, `key_activities` keys | Enhanced poster |
| `export_service.py` (module) | Add `build_seven_elements()` | Shared by JSON/CSV export |
| `app/api/export.py` | Add JSON + CSV routes | Structured export |
| `data.jsx STEPS` | +`org_context` entry (Phase 0), +`responsibilities_narrative` entry (Phase 3) | New conversational steps |
| `data.jsx isStepVisible()` | +case for `'responsibilities_narrative'` | Gating logic |
| `data.jsx exports` | Export new step-related helpers if needed | Standard export pattern |
| `app.jsx` | +`userRole` state, +role selector gate, +`elementStatuses` state, +`handleExportJson/Csv`, mirror new fields in commit() | New features |
| `document.jsx buildOverview()` | Use `record.org_context` as leading text when present | New field display |
| `conversation.jsx ReviewState` | +completeness badge, +manager-mode conditional rendering | Phase 27 + Phase 28 |
| `styles.css` | +role selector styles, +completeness badge styles, +manager-mode display rules | New UI |

---

## Data Flow Changes

### New commit() mirror fields (app.jsx)

```js
// Extend existing mirror list:
['confirmed_noc', 'confirmed_og', 'og_level', 'reports_to_military',
 'jes_scores', 'jes_total_points',
 'org_context', 'responsibilities_narrative'].forEach(k => { ... });
```

### New state slices (app.jsx)

```js
const [userRole, setUserRole] = useState(/* lazy localStorage */);
const [elementStatuses, setElementStatuses] = useState([]);  // Phase 27
```

### New useEffect trigger (app.jsx)

```js
// Phase 27: validate elements when review starts (same pattern as orphan check)
useEffect(() => {
  if (!reviewing || !wd_id) return;
  fetch(`/api/wd/${wd_id}/validate-elements`, { method: 'POST' })
    .then(r => r.ok ? r.json() : null)
    .then(data => { if (data?.elements) setElementStatuses(data.elements); })
    .catch(() => {});
}, [reviewing, wd_id]);
```

### Completeness audit data flow

```
User enters Review phase (reviewing = true)
  → POST /api/wd/{id}/validate-elements (automatic, non-blocking)
  → Backend: reads WD, checks 7 fields, returns {elements: [{name, status, value_preview}]}
  → Frontend: setElementStatuses(data.elements)
  → ReviewState renders completeness badge: "6/7 elements complete"
  → Clicking badge expands element breakdown list
```

### Enhanced poster data flow

```
User clicks "Export Poster" button
  → exportAs('poster') in app.jsx
  → POST /api/wd/{id}/export/poster (existing endpoint)
  → _build_poster_context(wd) now reads wd.org_context and wd.duties[:5]
  → poster_template.docx renders "About the Organization" from org_context
  → File download
```

### Structured data export data flow

```
User clicks "Export JSON" or "Export CSV" in ReviewState
  → exportAs('json') or exportAs('csv') in app.jsx
  → POST /api/wd/{id}/export/json or /export/csv
  → build_seven_elements(wd) maps all 7 fields
  → JSON: single file download, Content-Type application/json
  → CSV: one row per duty, shared scalar fields repeated
  → File download via Blob + URL.createObjectURL (same pattern as DOCX)
```

---

## Architectural Invariants to Preserve

1. **No SQLite schema migration.** New `org_context` and `responsibilities_narrative` fields live in the JSON blob inside `work_descriptions.data`. `extra="ignore"` handles old rows gracefully.

2. **Classification gate unchanged.** `require_og_confirmed` is not applied to structured export endpoints — these export whatever is present, because a manager-track WD may never have a confirmed OG.

3. **Manager-track never mutates WD model.** `userRole` lives entirely in the browser. The same WorkDescription row is readable and exportable regardless of which role created it. Backend endpoints are role-unaware.

4. **QUES-02 constraint preserved.** No new STEPS entries expose OG codes in question text or option labels. `org_context` and `responsibilities_narrative` are free-text fields with no signal accumulation.

5. **SJD pre-fill is augmentative, not authoritative.** When org_context is pre-filled from an SJD, it appears as the default answer to the `org_context` STEPS entry — the advisor can edit it. The WD stores the advisor's final text, not a reference to the SJD.

6. **`_factor_category_map()` is the single source of truth** for bucketing JES scores into Effort/Responsibility/Conditions/Skill. `build_seven_elements()` must use it — never `score.get('category')` directly (the EC scoring path does not persist a category key on scores).

7. **Responsibilities narrative is supplementary to JES responsibility factors, not a replacement.** The Accessible Template already renders JES responsibility factors in its Responsibility section. The new `responsibilities_narrative` field adds the *human-readable* narrative that the template's `responsibilities_text` currently derives from JES factor rationale strings. These coexist.

8. **Gating logic for responsibilities_narrative must match between isStepVisible() and validate-elements endpoint.** If the STEPS entry is skipped (non-supervisory role), the completeness audit must not flag the field as "missing" — it should return "not_applicable". This prevents a false 6/7 score for individual-contributor roles.

---

## Integration Points: New vs Modified

| Feature | New files | Modified files |
|---------|-----------|----------------|
| org_context field | — | `models/work_description.py`, `api/wd.py` (WDPatchRequest), `export_service.py` (_build_wd_context, _build_poster_context), `data.jsx` (STEPS), `app.jsx` (commit mirror), `document.jsx` (buildOverview) |
| responsibilities_narrative field | — | `models/work_description.py`, `api/wd.py` (WDPatchRequest), `data.jsx` (STEPS, isStepVisible), `app.jsx` (commit mirror) |
| Seven-Elements Audit | `app/api/elements.py` | `app/main.py` (router mount), `app.jsx` (state + useEffect), `conversation.jsx` (badge) |
| Manager-Track UX | — | `app.jsx` (state + gate + role selector JSX), `conversation.jsx` (manager-mode render), `document.jsx` (manager-mode hide classification), `styles.css` |
| Enhanced Job Poster | `scripts/build_poster_template.py` (re-run to update binary) | `export_service._build_poster_context()`, `app/templates/poster_template.docx` |
| Structured Data Export | `app/api/elements.py` (json+csv routes) | `export_service.py` (build_seven_elements fn), `app.jsx` (exportAs cases), `conversation.jsx` (export buttons), `styles.css` |

Note: `app/api/elements.py` is a single new file covering three endpoints (validate-elements, export/json, export/csv) rather than splitting into separate files — the domain cohesion (seven-elements operations) justifies co-location.

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| WorkDescription model extension | HIGH | Direct read of models/work_description.py; `extra="ignore"` confirmed |
| WDPatchRequest merge behavior | HIGH | Direct read of api/wd.py patch_wd(); `setattr` loop pattern confirmed |
| user_role localStorage pattern | HIGH | Direct read of app.jsx; identical pattern already used for wd_id |
| export pipeline field mapping | HIGH | Direct read of export_service.py `_build_wd_context()` and `_factor_category_map()` |
| isStepVisible gating pattern | HIGH | Direct read of data.jsx; case-switch pattern confirmed, new case is additive |
| Poster template rebuild | MEDIUM | Pattern confirmed; actual template binary must be regenerated and tested |
| CSV schema for analytics | MEDIUM | Designed for Julian's workflow; exact column set may need adjustment after review |
