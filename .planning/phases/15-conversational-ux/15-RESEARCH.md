# Phase 15: Conversational UX — Research

**Researched:** 2026-06-04
**Domain:** React 18 SPA conversation flow + FastAPI WD CRUD
**Confidence:** HIGH — all findings verified by direct codebase inspection

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONVO-01 | 6-phase interview (Role → Work Type → Classification → Duties → Qualifications → Review); Work Type and Classification phases use question bank-driven steps | STEPS array currently has 12 linear steps with prototype's `workType` choice card; must replace Phase 2 + Phase 3 with QUESTION_BANK-driven steps |
| CONVO-02 | Advisor can click any answered exchange to revisit + re-answer; re-answering a classification step re-runs downstream pipeline | `jumpToExchange` + `editStep` already exist in app.jsx; need `noc_candidates` invalidation trigger when a work-type-adjacent answer changes |
| CONVO-03 | Phase chips in convo header: active / done / pending states | `Header` component already renders `PHASES` array with `is-active` / `is-done` CSS classes; `phaseIdx` is set from `step.phase`; works today for the prototype phases — will work for new phase numbering with no code change |
| CONVO-04 | Per-step input control: text, textarea, choices-with-icons, duty builder, qual editor, NOC confirm card, OG confirm card | All types except `og_confirm` are already in `StepInput` dispatcher in components.jsx; need to add `og_confirm` type (Phase 16 will flesh it out, but the dispatcher stub belongs in Phase 15) |
| CONVO-05 | Enter to continue, Cmd/Ctrl+Enter for textarea, Back button on step 2+, auto-scroll | All implemented in current codebase; `TextInput` handles Enter/Ctrl+Enter; `ActiveQuestion` renders Back button when `canBack`; `useEffect` scrolls `threadRef` — verified working |
| API-02 | WD CRUD: POST `/api/wd`, GET `/api/wd/{id}`, PATCH `/api/wd/{id}` | `WorkDescription` Pydantic model exists; `work_descriptions` table exists in SQLite; zero CRUD routes exist yet — all three must be created |

</phase_requirements>

---

## Summary

Phase 15 is primarily a **wiring phase** — the heavy lifting for both the SPA shell (Phase 13) and the question bank (Phase 12) and NOC pipeline (Phase 14) is done. The central task is replacing the prototype's hardcoded `workType` choice step with the 4-entry QUESTION_BANK from `constants.py`, inserting the NOC pipeline wiring (the `NocConfirmList` component already exists), and building the three WD CRUD endpoints in FastAPI.

The existing conversation state machine in `app.jsx` handles revisiting (`jumpToExchange`, `editStep`, `editingReturn`) and is functionally complete for Phase 15. The `Header` component already renders phase chips with `is-active`/`is-done` CSS. `StepInput` dispatches to every needed control except `og_confirm` (needed as a stub for Phase 16). The only new SPA component needed is a `QuestionBankStep` renderer that surfaces QUESTION_BANK entries as `choices` inputs and accumulates signal totals, plus a step for the NOC pipeline trigger.

On the backend, `WorkDescription`, the SQLite schema (`work_descriptions` table), and `get_connection()` are all in place. The missing piece is `app/api/wd.py` with POST/GET/PATCH routes and a thin service layer that serialises/deserialises `WorkDescription` to JSON in the `data` column.

**Primary recommendation:** Build in four waves — (1) test stubs, (2) QUESTION_BANK-driven STEPS in data.jsx + NocConfirmList wiring in app.jsx, (3) WD CRUD API, (4) integration smoke test.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 6-phase interview step flow | Frontend (React) | — | Entirely client-side state machine; no round-trip needed per step |
| Question bank rendering | Frontend (React) | Backend (data source) | QUESTION_BANK lives in Python constants; SPA can either fetch it via API or have a JS copy in data.jsx — see Open Questions |
| Phase chip display | Frontend (React) | — | Derived from `step.phase` integer; purely presentational |
| Revisit / re-answer | Frontend (React) | — | `editStep` / `jumpToExchange` manage state; no backend call until commit |
| Step commit & persistence | Frontend → Backend | — | Each commit calls PATCH /api/wd/{id}; first commit calls POST /api/wd |
| WD CRUD | Backend (FastAPI) | SQLite | Routes in app/api/wd.py; WorkDescription serialised to JSON in data column |
| NOC pipeline trigger | Frontend → Backend | — | `summary` answer committed → SPA calls POST /api/noc/map → renders NocConfirmList |
| Keyboard shortcuts | Frontend (React) | — | Already in TextInput.onKeyDown; scope is to verify nothing is missing |

---

## Standard Stack

### Core (already installed — no new deps needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.3.1 | SPA component model | Already installed [VERIFIED: package.json] |
| Vite | 5.4.10 | Build/dev server | Already installed [VERIFIED: package.json] |
| FastAPI | (v2 backend) | HTTP API | Already in use [VERIFIED: app/main.py] |
| Pydantic v2 | (v2 backend) | Model validation | WorkDescription already defined [VERIFIED: app/models/work_description.py] |
| SQLite / sqlite3 | stdlib | WD persistence | Schema already created [VERIFIED: app/db.py] |

### Supporting (test — already installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| vitest | 4.1.8 | Frontend unit tests | All SPA tests [VERIFIED: package.json] |
| @testing-library/react | 16.3.2 | React render tests | Component-level assertions [VERIFIED: package.json] |
| pytest | (backend) | Backend tests | All API tests [VERIFIED: conftest.py] |

**No new packages need to be installed for Phase 15.** All dependencies are satisfied.

---

## Architecture Patterns

### System Architecture Diagram

```
Advisor keystroke
      │
      ▼
TextInput.onKeyDown (Enter → onSubmit)
      │
      ▼
ActiveQuestion.onCommit → app.jsx commit()
      │                        │
      │              answers[step.id] = draft
      │              record = { ...record, ...patch }
      │              localStorage.setItem(...)
      │                        │
      │              ┌─────────┴─────────┐
      │         first commit?       subsequent commit?
      │              │                    │
      │         POST /api/wd         PATCH /api/wd/{id}
      │              │                    │
      │         wd_id stored        WorkDescription updated
      │         in React state      in SQLite data column
      │
      ▼
stepIndex advances → next STEPS[stepIndex] renders
      │
      ▼  (if step.id === 'summary')
POST /api/noc/map with record.summary
      │
      ▼
NocConfirmList renders candidates
      │
      ▼  (advisor selects NOC card)
answers['noc_confirm'] = noc_code
PATCH /api/wd/{id} with confirmed_noc
      │
      ▼
Phase 3 steps (Classification) begin
```

### Recommended Project Structure Changes

Phase 15 adds:
```
v2/backend/app/
├── api/
│   ├── __init__.py      # add wd router
│   └── wd.py            # NEW: POST/GET/PATCH /api/wd
v2/frontend/src/
├── data.jsx             # MODIFY: replace workType step + scope steps with QUESTION_BANK steps + noc_trigger step
├── app.jsx              # MODIFY: add wd_id state, api calls on commit, noc fetch on summary commit
└── components.jsx       # MODIFY: add og_confirm stub to StepInput dispatcher
```

### Pattern 1: QUESTION_BANK Steps in data.jsx

**What:** Replace the prototype's single `workType` choice step and three `scopeDirection/scopeAdvises/scopeImpact` scale steps with 4 QUESTION_BANK-driven `choices` steps followed by a `noc_trigger` step that fires `POST /api/noc/map`.

**When to use:** Whenever the data.jsx STEPS array needs to surface server-side data (the question bank lives in the Python constants).

**Example — new Phase 2 "Work Type" steps:**
```javascript
// Source: v2/backend/app/data/constants.py QUESTION_BANK (4 entries, all phase_slot='work_type')
// Each QUESTION_BANK entry maps to one STEPS entry at phase: 1
{ id: 'qb_work_output_type', phase: 1, icon: I.list,
  q: 'What best describes the main type of output this person produces?',
  helper: 'Think about what they actually deliver — not their title.',
  input: { type: 'choices', options: [
    { id: 'analysis_advice', title: 'Analysis, options, or recommendations for decision-makers',
      signals: { og_candidates: ['EC'], jes_factor_hints: ['Research & analysis', 'Decision making'] } },
    { id: 'financial_reports', title: 'Financial plans, budgets, or costing reports',
      signals: { og_candidates: ['FI'], jes_factor_hints: ['Knowledge of specialized fields'] } },
    { id: 'systems_data', title: 'Systems, applications, or digital services',
      signals: { og_candidates: ['IT'], jes_factor_hints: ['Knowledge of specialized fields'] } },
    { id: 'admin_coordination', title: 'Administrative coordination, logistics, or operational support',
      signals: { og_candidates: ['AS'], jes_factor_hints: ['Leadership & operational mgmt'] } },
  ]},
  apply: (r, a) => ({ qb_work_output_type: a.id, _signals: [...(r._signals||[]), ...(a.signals?.og_candidates||[])] }),
  transcript: a => a.title },
```

**Key insight on signal accumulation:** The four QUESTION_BANK answers accumulate `og_candidates` arrays. The dominant OG code (most appearances) is the classification signal that goes forward to Phase 16 `POST /api/og/classify`. Phase 15 does NOT resolve OG — it collects signals. A helper `accumulateSignals(record)` can compute the dominant group for display in the ClassifyBadge.

### Pattern 2: WD CRUD Routes

**What:** Three FastAPI routes that serialise/deserialise WorkDescription to the `work_descriptions.data` JSON column.

```python
# Source: v2/backend/app/db.py schema (work_descriptions table, data TEXT column)
# v2/backend/app/models/work_description.py (WorkDescription Pydantic model)

@router.post("/wd", response_model=WDOut, status_code=201)
async def create_wd(body: WDCreateRequest) -> WDOut:
    wd = WorkDescription(
        id=str(uuid4()),
        record=body.record,
        answers=body.answers,
        step_index=body.step_index,
        created_at=datetime.now(timezone.utc),
        last_modified=datetime.now(timezone.utc),
    )
    # INSERT INTO work_descriptions (id, title, data, schema_version, created_at, last_modified)
    # data = wd.model_dump_json()

@router.get("/wd/{wd_id}", response_model=WDOut)
async def get_wd(wd_id: str) -> WDOut:
    # SELECT data FROM work_descriptions WHERE id = ?
    # WorkDescription.model_validate_json(row['data'])

@router.patch("/wd/{wd_id}", response_model=WDOut)
async def patch_wd(wd_id: str, body: WDPatchRequest) -> WDOut:
    # Load existing, merge patch fields, UPDATE work_descriptions SET data=?, last_modified=?
```

**Use**: called from app.jsx on every step commit. First commit → POST; every subsequent → PATCH.

### Pattern 3: NOC Pipeline Trigger Step

**What:** After `summary` is committed, the SPA needs a step that shows a loading state while `POST /api/noc/map` runs, then transitions to NocConfirmList.

**Options:**
1. Add a `noc_trigger` STEP entry in data.jsx whose `input.type = 'noc_confirm'` and whose `cfg.candidates` is populated by app.jsx calling the API.
2. Handle the API call inside `commit()` when `step.id === 'summary'`, set candidates in state, and let a dynamic `cfg.candidates` fill the next step.

**Recommendation:** Option 2 — keep STEPS pure/static. In `commit()`, after committing `summary`, set a new state slice `nocCandidates: []` (loading), call `POST /api/noc/map`, then `setNocCandidates(result.candidates)`. The next STEP (id: `noc_confirm`) reads `nocCandidates` from a `cfg.candidates` prop injected by app.jsx before passing to `ActiveQuestion`.

### Pattern 4: editingReturn State Machine

The revisit state machine is already complete in the ported codebase:

```javascript
// Source: v2/frontend/src/app.jsx, commit() function lines 116-138
// editingReturn path:
//   1. onEdit() click on Exchange → editStep(stepId) sets editingReturn=true, stepIndex=idx
//   2. Advisor re-answers → commit() sees editingReturn=true
//   3. commit() clears editingReturn, sets reviewing=true (returns to review screen)
//   4. "Back to review without changes" button cancels edit without persisting
```

**Phase 15 addition needed:** When advisor re-answers a question bank step, clear `nocCandidates` and the `noc_confirm` answer from `answers` state (because the signal accumulation will change). This invalidation should happen in `commit()` when `editingReturn && step.phase === 1` (Work Type phase).

### Anti-Patterns to Avoid

- **Fetching QUESTION_BANK from the API on each render:** The question bank is a static design artifact. Embed it in data.jsx (copy from constants.py). The Python constants are the canonical source; the JS copy stays in sync manually. Avoids a loading state for static data.
- **Resolving OG in Phase 15:** Phase 15 accumulates signals; Phase 16 resolves OG. Do not call `POST /api/og/classify` from Phase 15. The ClassifyBadge can show a "signals accumulated" state using client-side `accumulateSignals()`.
- **Persisting draft per keystroke:** Only PATCH on step commit (Continue button), not on every keystroke. localStorage handles crash-recovery between commits.
- **Building a separate `wd_id` storage mechanism:** Store `wd_id` in React state and also write it to localStorage alongside `record`. This ensures the PATCH call works after a browser refresh.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WD serialization | Custom JSON encoder | `WorkDescription.model_dump_json()` / `model_validate_json()` | Pydantic v2 handles datetime, Optional, list correctly [VERIFIED: models exist] |
| UUID generation | Custom ID function | `uuid.uuid4()` | stdlib; already used in test fixtures [VERIFIED: conftest.py] |
| SQLite connection | Direct `sqlite3.connect()` | `get_connection(settings.db_path)` | Sets `check_same_thread=False`, `row_factory=sqlite3.Row`, FK pragma [VERIFIED: app/db.py] |
| Input validation | Manual `if not field:` | Pydantic Field validators on request models | Consistent 422 errors with FastAPI's default error handling |
| Auto-scroll | Custom scroll math | `threadRef.current.scrollTo({ top: scrollHeight, behavior: 'smooth' })` | Already in app.jsx useEffect — do not duplicate [VERIFIED: app.jsx line 104] |

---

## Common Pitfalls

### Pitfall 1: STEPS phase index mismatch after insertion

**What goes wrong:** QUESTION_BANK inserts 4 steps into Phase 2 (index 1), shifting the `phase` integer on every subsequent STEP. The `PHASES` array has 6 entries; `Header` renders chips using `step.phase`. If phase integers aren't updated, chips show wrong active state.

**Why it happens:** The prototype STEPS array has `phase: 0, 0, 0, 0` (Role), `phase: 1, 1` (Focus), `phase: 2, 2, 2` (Scope), etc. Inserting 3 new steps changes which steps belong to which phase.

**How to avoid:** Map the new 6-phase structure explicitly:
- Phase 0 (Role): title, branch, reports, supervises — 4 steps
- Phase 1 (Work Type): summary, qb_work_output_type, qb_work_audience, qb_knowledge_specialization, qb_policy_interpretation, noc_trigger — 6 steps
- Phase 2 (Classification): noc_confirm — 1 step (OG steps added in Phase 16)
- Phase 3 (Duties): duties — 1 step
- Phase 4 (Qualifications): quals — 1 step (Phase 19 expands)
- Phase 5 (Review): — review state, not a step

**Warning signs:** Phase chip 2 ("Work Type") lights up before the advisor reaches question bank questions; or Phase chip 3 ("Classification") activates too early.

### Pitfall 2: NocConfirmList not wired into live step flow

**What goes wrong:** NocConfirmList was delivered in Phase 14 but it was built as a component; it has no step in STEPS and no API call that populates `cfg.candidates`. Phase 14's UAT explicitly deferred "live browser rendering" to Phase 15.

**Why it happens:** The component renders correctly given `cfg.candidates`; the missing piece is the data flow (app.jsx calling `/api/noc/map` and injecting candidates into the step cfg).

**How to avoid:** In app.jsx, add:
1. `const [nocCandidates, setNocCandidates] = useState([])` state slice
2. In `commit()`, when `step.id === 'summary'`, after updating record, fire `fetch('/api/noc/map', ...)` and set `nocCandidates` with results
3. In the render, when rendering the `noc_confirm` step, pass `cfg={{ ...step.input, candidates: nocCandidates }}` to `ActiveQuestion`

**Warning signs:** NocConfirmList renders with an empty candidates array; "Continue" button never enables because `answerValid` returns `false` for an empty string.

### Pitfall 3: WD CRUD request/response model mismatch

**What goes wrong:** `WorkDescription` has `id`, `created_at`, `last_modified` as required fields (no defaults). POST /api/wd should generate these server-side, but the request body shape must not require them.

**Why it happens:** Sending `WorkDescription` directly as the request body would require the client to supply `id` and timestamps.

**How to avoid:** Define a thin `WDCreateRequest` that only contains mutable fields (`record`, `answers`, `step_index`, `draft`, `reviewing`, `editing_return`). Server generates `id=uuid4()`, `created_at=now()`, `last_modified=now()` and constructs `WorkDescription` from the combination.

**Warning signs:** 422 validation error on POST /api/wd with message `field required: id`.

### Pitfall 4: signal accumulation and `_signals` polluting record

**What goes wrong:** Storing accumulated OG signal arrays inside `record` (e.g. `record._signals`) bleeds prototype-internal state into the WD persistence model.

**Why it happens:** The `apply` function on each STEP writes into `record`. Putting intermediate signal accumulators there means they get PATCH'd to the backend and serialised into WD.data.

**How to avoid:** Compute `accumulateSignals(answers)` as a pure derived function from the answers dict — never persist it. Use `useMemo` to derive signal totals for ClassifyBadge display. The PATCH body sends `answers` (which includes the raw option selections), not accumulated signals.

### Pitfall 5: editingReturn + NOC invalidation causes infinite re-render

**What goes wrong:** Re-answering a Work Type question clears `nocCandidates` to `[]`. If the noc fetch side-effect is triggered by a `useEffect` watching `answers`, it will re-trigger after the clearing.

**Why it happens:** `useEffect` dependency arrays that include `answers` cause re-runs whenever any answer changes.

**How to avoid:** Trigger the NOC fetch imperatively inside `commit()` (not via useEffect) only when `step.id === 'summary'`. This avoids the circular dependency entirely.

---

## Code Examples

### WD CRUD — create route skeleton

```python
# Source: pattern from v2/backend/app/api/noc_mapping.py (existing working route)
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.db import get_connection
from app.config import get_settings
from app.models.work_description import WorkDescription

router = APIRouter()

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
```

### Signal accumulation (pure function, no side effects)

```javascript
// Source: derived from QUESTION_BANK structure in v2/backend/app/data/constants.py
// Place in data.jsx
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
  // Return dominant OG code (most votes), or null if no answers yet
  const sorted = Object.entries(tally).sort((a, b) => b[1] - a[1]);
  return sorted.length > 0 ? { dominant: sorted[0][0], tally } : null;
}
```

### Phase chip mapping for new 6-phase structure

```javascript
// Source: data.jsx PHASES constant + STEPS array structure
// New phase structure to use in STEPS:
// phase: 0 = Role      (title, branch, reports, supervises)
// phase: 1 = Work Type (summary, 4 × qb_*, noc_trigger)
// phase: 2 = Classification (noc_confirm)  ← Phase 16 adds og_confirm, level
// phase: 3 = Duties    (duties)
// phase: 4 = Qualifications (quals)        ← Phase 19 expands
// phase: 5 = Review    (review state only, phaseIdx set to 5 when reviewing=true)
const PHASES = ['Role', 'Work Type', 'Classification', 'Duties', 'Qualifications', 'Review'];
// NOTE: 'Focus' and 'Level' (prototype names) are replaced
// 'Mission' (DRF) is deferred to v2.1 per REQUIREMENTS.md Out of Scope
```

### Adding og_confirm stub to StepInput

```javascript
// Source: v2/frontend/src/components.jsx StepInput dispatcher (line 283-293)
function StepInput(props) {
  const t = props.cfg.type;
  if (t === 'text' || t === 'textarea') return <TextInput {...props} />;
  if (t === 'choices') return <ChoiceList {...props} />;
  if (t === 'scale') return <ScaleInput {...props} />;
  if (t === 'duties') return <DutyBuilder {...props} />;
  if (t === 'drf') return <DrfPicker {...props} />;
  if (t === 'quals') return <QualEditor {...props} />;
  if (t === 'noc_confirm') return <NocConfirmList {...props} />;
  if (t === 'og_confirm') return <NocConfirmList {...props} />; // stub — Phase 16 replaces with OgConfirmList
  return null;
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Prototype `workType` single choice card | 4 × QUESTION_BANK-driven `choices` steps + NOC pipeline lookup | Phase 15 | Socratic constraint enforced; no direct OG selection |
| Phase names: Role / Focus / Level / Duties / Mission / Review | Role / Work Type / Classification / Duties / Qualifications / Review | Phase 15 | DRF ("Mission") deferred to v2.1; "Focus" merged into Work Type |
| No backend persistence | WD CRUD: POST/GET/PATCH `/api/wd` | Phase 15 | Each step commit writes to SQLite via PATCH |
| Prototype scope scale questions (3 × scale) | Signal accumulation from question bank answers | Phase 15 | Classification engine now uses NOC + OG pipeline (Phase 16), not scope scores |

**Deprecated in Phase 15:**
- `workType` step in STEPS (id: 'workType') — replaced by 4 QUESTION_BANK steps
- `scopeDirection`, `scopeAdvises`, `scopeImpact` steps — retired; scope is derived by Phase 16's OG ranker
- `computeClassification()` in data.jsx — retained for the prototype build but not called in the main flow; will be removed in Phase 16 when `POST /api/og/classify` takes over
- `WORK_TYPES` constant in data.jsx — no longer drives a conversation step; still used by `ChoiceList` when `cfg.source === 'workTypes'` but that path will be unused after Phase 15

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | QUESTION_BANK entries will be embedded as a JS copy in data.jsx rather than fetched from a `/api/question-bank` endpoint | Architecture Patterns | If team prefers API-driven, add one GET route; JS copy is simpler and the data is static |
| A2 | Phase name "Mission" (DRF) is retired in Phase 15; PHASES becomes ['Role', 'Work Type', 'Classification', 'Duties', 'Qualifications', 'Review'] | Code Examples | DRF may be re-added in v2.1; the 6-slot structure is stable regardless |
| A3 | `og_confirm` step is stubbed in Phase 15 (reuses NocConfirmList component) but not populated until Phase 16 | Architecture Patterns, Code Examples | Phase 16 must replace the stub; if Phase 15 and 16 are executed in the same wave this is a non-issue |

---

## Open Questions

1. **QUESTION_BANK duplication: JS copy vs. API endpoint**
   - What we know: QUESTION_BANK is 4 entries, ~350 lines in Python constants; static, never user-editable
   - What's unclear: Whether maintaining a JS copy is acceptable or a single-source-of-truth API is preferred
   - Recommendation: JS copy in data.jsx for Phase 15 simplicity; add a note to Phase 16 to unify if needed

2. **wd_id lifecycle: created on first commit or on page load?**
   - What we know: POST /api/wd is called on "first step commit" per CONVO-01 / API-02
   - What's unclear: Should the WD be pre-created on page load (before any answer) so the ID is stable from session start?
   - Recommendation: Create on first commit (`commit()` when `step.id === 'title'`). If the user abandons before the first commit, no orphan row is created.

3. **NOC pipeline async latency during conversation**
   - What we know: `POST /api/noc/map` can take 2-10 seconds (LLM justification stage)
   - What's unclear: Whether to show a loading spinner between `summary` commit and NOC candidates arriving, or navigate to a loading step
   - Recommendation: Add a `noc_loading` boolean state slice; render an inline spinner inside the `noc_confirm` step's input zone while loading. Don't add a separate loading STEP to avoid complicating step-index arithmetic.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| React 18 + Vite | Frontend SPA | ✓ | React 18.3.1, Vite 5.4.10 | — |
| FastAPI + uvicorn | API routes | ✓ | existing v2 backend | — |
| SQLite (stdlib) | WD persistence | ✓ | stdlib | — |
| vitest + @testing-library/react | Frontend tests | ✓ | vitest 4.1.8 | — |
| pytest | Backend tests | ✓ | existing v2 backend | — |
| Ollama (for NOC map API) | POST /api/noc/map call during Phase 15 wiring | [ASSUMED] present from Phase 14 work | — | NOC step can be tested with mock candidates |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (frontend) | vitest 4.1.8 + @testing-library/react 16.3.2 |
| Framework (backend) | pytest (existing) |
| Config file (frontend) | `v2/frontend/vitest.config.js` |
| Quick run command | `cd v2/frontend && npm test` (9 tests, < 5s) |
| Full suite command | `cd v2/backend && python -m pytest` (39 tests) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONVO-01 | QUESTION_BANK steps render in phase 1 | unit | `npm test -- --reporter=verbose` | ❌ Wave 0 |
| CONVO-02 | jumpToExchange navigates to prior step | unit | `npm test` | ❌ Wave 0 |
| CONVO-03 | Phase chips show active/done/pending | unit | `npm test` | ❌ Wave 0 |
| CONVO-04 | StepInput dispatches og_confirm type | unit | `npm test` | ❌ Wave 0 |
| CONVO-05 | Enter submits text input | unit | `npm test` | ❌ Wave 0 |
| API-02 | POST /api/wd creates row in work_descriptions | integration | `python -m pytest tests/test_wd.py -x` | ❌ Wave 0 |
| API-02 | GET /api/wd/{id} returns WorkDescription | integration | `python -m pytest tests/test_wd.py -x` | ❌ Wave 0 |
| API-02 | PATCH /api/wd/{id} updates last_modified | integration | `python -m pytest tests/test_wd.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd v2/frontend && npm test` (frontend) + `cd v2/backend && python -m pytest tests/test_wd.py` (new backend tests)
- **Per wave merge:** `cd v2/backend && python -m pytest` (full 39+ suite)
- **Phase gate:** Both suites green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `v2/frontend/src/conversation.test.jsx` — covers CONVO-01 through CONVO-05
- [ ] `v2/backend/tests/test_wd.py` — covers API-02 (POST/GET/PATCH)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user local app; no auth |
| V3 Session Management | no | Single-user local app; no sessions |
| V4 Access Control | no | Single endpoint, no roles |
| V5 Input Validation | yes | Pydantic v2 on all request bodies; `model_validate` on deserialization |
| V6 Cryptography | no | No secrets in this phase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| WD ID enumeration (GET /api/wd/{id}) | Information Disclosure | Single-user local app; acceptable risk; UUID v4 is non-guessable |
| Malformed JSON in work_descriptions.data | Tampering | `WorkDescription.model_validate_json()` raises `ValidationError` → 422 |
| SQLite injection via wd_id path param | Tampering | Parameterized queries in all db.py calls — follow existing pattern in health.py |

---

## Sources

### Primary (HIGH confidence)
- `v2/frontend/src/app.jsx` — complete state machine, commit(), goBack(), editStep(), jumpToExchange() — directly read
- `v2/frontend/src/conversation.jsx` — Header, Exchange, ActiveQuestion, ReviewState — directly read
- `v2/frontend/src/components.jsx` — StepInput dispatcher, NocConfirmList, all input controls — directly read
- `v2/frontend/src/data.jsx` — STEPS (12 entries), PHASES, signal functions — directly read
- `v2/backend/app/models/work_description.py` — WorkDescription Pydantic model — directly read
- `v2/backend/app/db.py` — SQLite schema (work_descriptions table) — directly read
- `v2/backend/app/data/constants.py` — QUESTION_BANK (4 entries), OG_LEVELS, KNOWN_JES_FACTORS — directly read
- `v2/backend/app/api/noc_mapping.py` — existing route pattern to follow for wd.py — directly read
- `.planning/REQUIREMENTS.md` — CONVO-01..05, API-02 requirement text — directly read
- `.planning/ROADMAP.md` — Phase 15 success criteria — directly read

### Secondary (MEDIUM confidence)
- STATE.md session continuity block — Phase 14 completion notes confirming NocConfirmList delivered and UAT deferred

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified in package.json and requirements files
- Architecture (state machine): HIGH — code directly inspected
- Architecture (API pattern): HIGH — existing noc_mapping.py route is the direct template
- Pitfalls: HIGH — derived from direct code inspection of the existing wiring gaps
- QUESTION_BANK structure: HIGH — verified in constants.py + test_question_bank.py

**Research date:** 2026-06-04
**Valid until:** 2026-07-04 (stable stack; no fast-moving dependencies)
