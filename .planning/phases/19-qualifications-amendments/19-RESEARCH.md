# Phase 19: Qualifications & Amendments — Research

**Researched:** 2026-06-09
**Domain:** React 18 SPA data layer + FastAPI audit_log endpoint + document preview rendering
**Confidence:** HIGH

---

## Summary

Phase 19 has two distinct capability clusters. The first (QUAL-01..03) is primarily a
**data-layer fix with minimal UI change**: replace the hardcoded EC-05 `QUAL_DEFAULT`
constant in `data.jsx` with an OG-group-keyed map + `getQualDefault(og_code)` lookup
function, thread that function into `initialAnswer()` and `QualEditor`, and add
`touched`-gated inline validation. The backend `GET /api/quals/default` endpoint and
`QUAL_STANDARDS` constant already exist (Phase 16) and return correct values for EC,
AS, IT, FI, and a `default` fallback — the frontend just ignores them at present.

The second cluster (AMEND-01..02) is a **new backend endpoint + frontend state slice**:
`POST /api/wd/{id}/amendments` writes an `audit_log` row with
`event="manager_amendment"`, keyed by section. The frontend adds two `useState` objects
(`amendmentNotes` / `amendmentPanels`), renders a `.amend-btn` inside every section
header in review state, and manages an inline expandable panel. The DOCX appendix for
AMEND-02 is deferred to Phase 20 (docxtpl rendering) but the data must be stored now.

The `audit_log` table already exists in the schema. The `jes_service.py` override
function provides the canonical write pattern. Document preview `Sec` component and
`.sec__h` markup is established in Phase 18 and will be available when Phase 19
executes.

**Primary recommendation:** Implement in wave order — Wave 0 RED stubs, Wave 1
OG-keyed qual defaults + inline validation (QUAL-01..03), Wave 2 amendment panel
+ backend endpoint (AMEND-01), Wave 3 integration + full suite green gate.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| OG-keyed qual defaults | Frontend (data.jsx) | Backend (QUAL_STANDARDS) | Backend has the data; frontend derives prefill from it via `getQualDefault`. API call not required — values are static constants. |
| Inline validation on QualEditor | Frontend (components.jsx) | — | Pure client-side — `touched` state, `onBlur` handler, conditional render. |
| Section 5 sub-labels in preview | Frontend (document.jsx) | — | CSS class extraction from inline style — no new data needed. |
| Amendment note persistence | Backend (audit_log table) | Frontend (amendmentNotes state) | `audit_log` already exists; new endpoint writes to it; frontend caches saved note text. |
| Amendment panel UI | Frontend (document.jsx + app.jsx) | — | Inline expandable panel; all UI state is local to DocumentPane / app.jsx. |
| Amendment retrieval on load | Backend (GET audit_log query) | Frontend (hydration) | Saved notes must survive page refresh; backend must expose them via GET or WD load. |

---

## Standard Stack

### Core (all verified in codebase)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React 18 | 18.x | SPA state + rendering | Project non-negotiable (STATE.md) |
| FastAPI | current | REST endpoints | Project non-negotiable |
| Pydantic v2 | 2.x | Request/response models | Project non-negotiable |
| SQLite3 (stdlib) | — | audit_log writes | Already in schema (db.py) |
| Vitest + jsdom | current | Frontend unit tests | Already configured (vite.config.js) |
| pytest-asyncio | current | Backend async tests | Already in conftest.py |
| httpx | current | Backend test client | Already in conftest.py |

**No new library installations needed for Phase 19.** [VERIFIED: codebase inspection]

---

## Architecture Patterns

### System Architecture Diagram

```
                         QUALIFICATION PREFILL FLOW
                         ─────────────────────────────
  app.jsx (record.confirmed_og.og_code)
      │
      ▼
  initialAnswer(step, record) in components.jsx
      │
      └─► getQualDefault(og_code)  ←─── data.jsx (QUAL_DEFAULTS map)
              │                              │
              │                    EC / AS / IT / FI / default
              ▼
        QualEditor receives
        value = { education, experience }
              │
              │  user edits
              ▼
        onCommit → record.quals = value
              │
              ▼
        DocumentPane Section 5 renders quals.education + quals.experience
        with .qual-sub-k labels and "TBS Qualification Standard" src pill


                         AMENDMENT NOTE FLOW
                         ─────────────────────────────
  User (review state) clicks .amend-btn on any section header
              │
              ▼
  amendmentPanels[sectionKey].open = true  (app.jsx local state)
              │
  User types text → amendmentPanels[sectionKey].text updates live
              │
  "Save note" → POST /api/wd/{id}/amendments
              │                │
              │                ▼
              │       audit_log INSERT
              │       event="manager_amendment"
              │       detail=json({ section, comment, timestamp })
              │
              ▼
  amendmentNotes[sectionKey] = text  (app.jsx state)
  gold .amend-indicator dot appears in section header
  toast: "Note saved for {section name}."
```

### Recommended File Changes

```
v2/frontend/src/
├── data.jsx          # Replace QUAL_DEFAULT export with QUAL_DEFAULTS map
│                     #   + getQualDefault(og_code) function
├── components.jsx    # QualEditor: add touched state + onBlur + .qual-error
│                     # initialAnswer: call getQualDefault(record.confirmed_og?.og_code)
│                     # answerValid: unchanged (already gates on education && experience)
│                     # StepInput: unchanged
├── document.jsx      # Extract .qual-sub-k CSS class (inline style → className)
│                     # Sec component: accept amendmentNote + onAmendSave props
│                     # Render .amend-btn in .sec__h when reviewing===true
│                     # Render .amend-panel below header when panel.open===true
├── app.jsx           # Add: const [amendmentNotes, setAmendmentNotes] = useState({})
│                     # Add: const [amendmentPanels, setAmendmentPanels] = useState({})
│                     # Pass both to DocumentPane
└── styles.css        # Add: .qual-sub-k, .qual-error, .amend-btn, .amend-indicator,
                      #       .amend-panel, .amend-panel__label,
                      #       .amend-panel__actions, .amend-count

v2/backend/app/
├── api/amendments.py # New: POST /api/wd/{id}/amendments
│                     #       GET  /api/wd/{id}/amendments  (for page-refresh hydration)
├── api/__init__.py   # Include amendments router
└── models/           # No new model needed; request body is inline Pydantic model
```

### Pattern 1: Qualified Defaults Map (QUAL-01)

**What:** Replace static `QUAL_DEFAULT` with a keyed map and a lookup function.
**When to use:** On `initialAnswer()` for `type === 'quals'` steps.

```jsx
// Source: UI-SPEC.md Section A + existing data.jsx structure [VERIFIED: codebase]
const QUAL_DEFAULTS = {
  EC: {
    education: 'A degree from a recognized post-secondary institution, with acceptable specialization...',
    experience: 'Significant experience in policy analysis, economic research, or program evaluation...'
  },
  AS: {
    education: 'A secondary school diploma or an acceptable combination of education, training and/or experience.',
    experience: 'Experience in administrative, financial, or operational support functions...'
  },
  IT: {
    education: 'Successful completion of two years of an acceptable post-secondary educational program...',
    experience: 'Experience in information technology functions relevant to the duties of the position.'
  },
  FI: {
    education: 'A bachelor\'s degree from a recognized post-secondary institution with a specialization...',
    experience: 'Significant experience in financial management, financial analysis, or accounting...'
  },
  default: {
    education: 'A degree or diploma from a recognized post-secondary institution in a field relevant...',
    experience: 'Experience performing duties relevant to the position.'
  }
};

function getQualDefault(og_code) {
  return QUAL_DEFAULTS[og_code] || QUAL_DEFAULTS['default'];
}

export { ..., QUAL_DEFAULTS, getQualDefault };
```

The `QUAL_DEFAULT` name (singular) must remain exported for backward-compat until all
consumers are updated. The planner should either rename references atomically or export
both names temporarily.

### Pattern 2: Touched-Gated Inline Validation (QUAL-02)

**What:** Show validation error only after the user has blurred an empty field.
**When to use:** `QualEditor` only.

```jsx
// Source: UI-SPEC.md Section C [VERIFIED]
function QualEditor({ value, onChange, record }) {
  const og_code = record?.confirmed_og?.og_code;
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
      {/* Experience field mirrors above */}
    </div>
  );
}
```

**Key nuance:** `QualEditor` currently receives `value` and `onChange` as props from
`StepInput`. The `record` prop is NOT currently threaded through `StepInput`. The
planner must add `record` to the `StepInput` prop pass-through, or pass `og_code`
directly.

Simpler alternative: pass the prefill value into `initialAnswer()` via the existing
`step.input.preset` mechanism — set `preset` to the result of `getQualDefault()` when
building `STEPS`. This avoids modifying `StepInput`'s prop contract. [ASSUMED]

### Pattern 3: Audit Log Write (AMEND-01)

**What:** New endpoint follows the exact pattern used by `override_jes_factor`.
**When to use:** POST `/api/wd/{id}/amendments`.

```python
# Source: v2/backend/app/services/jes_service.py lines 354-365 [VERIFIED: codebase]
con.execute(
    "INSERT INTO audit_log (wd_id, event, actor, detail, created_at) VALUES (?, ?, ?, ?, ?)",
    (
        wd_id,
        "manager_amendment",          # type field from AMEND-01 spec
        "advisor",
        json.dumps({"section": section, "comment": comment, "timestamp": now.isoformat()}),
        now.isoformat(),
    ),
)
con.commit()
```

**audit_log schema (existing):** [VERIFIED: v2/backend/app/db.py]
```sql
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    wd_id       TEXT NOT NULL,
    event       TEXT NOT NULL,
    actor       TEXT NOT NULL,
    detail      TEXT,           -- JSON string
    created_at  TEXT NOT NULL
);
```

AMEND-01 specifies storing `type="manager_amendment"`, `section`, `comment`,
`timestamp`. Mapping to schema: `event = "manager_amendment"`,
`detail = json({ section, comment })`, `created_at` = timestamp.

### Pattern 4: Amendment Retrieval on Page Refresh

**What:** `amendmentNotes` in frontend state must survive page refresh.
**Approach options:**

A. **Load from audit_log on GET /api/wd/{id}/amendments** — endpoint queries
   `audit_log WHERE wd_id=? AND event='manager_amendment'` and returns the latest
   per-section note. Frontend calls this on WD load (similar to how orphan_check is
   triggered when `reviewing` becomes true). [RECOMMENDED — ASSUMED: cleanest, no WD
   model change needed]

B. **Store amendment notes in WD model** — add `amendment_notes: dict[str, str]` to
   `WorkDescription`. Simpler to load; requires WD model change. [ASSUMED]

C. **localStorage cache** — store `amendmentNotes` in localStorage alongside the
   record. No backend change, but out of step with the "audit trail" spirit of AMEND-01.
   Loses notes if localStorage is cleared.

Recommendation: Option A. It stays consistent with the audit_log ownership model and
requires no WD model change. The planner must include a `GET /api/wd/{id}/amendments`
endpoint in the plan.

### Anti-Patterns to Avoid

- **Fetching `GET /api/quals/default` on every QualEditor mount** — `QUAL_STANDARDS`
  data is static; hitting the API per-mount adds a round-trip for no benefit. Put the
  defaults in the JS constant exactly as done with `OG_LEVELS`. [VERIFIED: pattern in
  data.jsx OG_LEVELS]
- **Putting amendment panel state in document.jsx** — `amendmentPanels` and
  `amendmentNotes` must live in `app.jsx` so they survive section re-renders and can be
  passed to `ReviewState` (for the checklist item count). Document.jsx should receive
  them as props.
- **Using the `qualification` field on `WorkDescription` for quals storage** — the
  backend `WorkDescription.qualification` field is `Optional[QualificationStandard]` but
  the frontend stores quals in `record.quals` (a plain dict in `PATCH /api/wd/{id}` via
  the `record` field). Don't bypass the established WD patch flow.
- **Mutating `QUAL_DEFAULT` name import in components.jsx** — `QUAL_DEFAULT` is
  currently imported in `components.jsx` line 5. Any rename must update that import
  simultaneously. Phase 19 Wave 0 should update the export shape before the import.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Toast notifications | Custom toast component | Existing `.toast` / `is-show` / `setToast` pattern in app.jsx | Already implemented; Phase 17 uses it for JES override confirmation |
| Audit trail timestamps | Custom timestamp generation | `datetime.now(timezone.utc).isoformat()` | Same as jes_service.py override write |
| Section-key-to-name mapping | Custom string lookup | Existing section header titles in document.jsx | All 6 section names are already defined as string literals in section renders |
| Input validation gating | Disable button on empty | Existing `answerValid()` + `disabled` prop pattern | `answerValid` for `quals` already checks `education && experience` |

---

## Common Pitfalls

### Pitfall 1: `getQualDefault` called before `record.confirmed_og` is set

**What goes wrong:** On `initialAnswer()` call for a fresh WD that hasn't reached OG
confirmation, `record.confirmed_og` is `undefined`, causing `og_code` to be `undefined`,
causing `getQualDefault` to fall through to `default`. The user sees the generic default
rather than their OG-matched text.

**Why it happens:** The quals step is Phase 4 (index 11+) but the `initialAnswer()`
function is called at step mount, which might be before OG is confirmed.

**How to avoid:** `getQualDefault(undefined)` must fall back gracefully to
`QUAL_DEFAULTS['default']` — not throw. Confirm the fallback path is tested.

**Warning signs:** QualEditor shows generic "A degree or diploma..." text on a
non-default OG session.

### Pitfall 2: `QUAL_DEFAULT` import in components.jsx breaks if only export is renamed

**What goes wrong:** `data.jsx` line 420 exports `QUAL_DEFAULT` (singular). `components.jsx`
line 5 imports it. If the planner renames the export without updating the import,
`components.jsx` will import `undefined` — silent failure, QualEditor renders empty.

**Why it happens:** Named imports in JS modules fail silently if the export name
doesn't exist; no runtime error until the value is dereferenced.

**How to avoid:** Wave 0 or Wave 1 must touch `data.jsx` export line AND `components.jsx`
import line atomically. Export both `QUAL_DEFAULT` (pointing to the default entry) and
`getQualDefault` for the transition period.

### Pitfall 3: Amendment panel open state keyed incorrectly

**What goes wrong:** Multiple sections share the same panel state object key. If the
planner uses a numeric index (`0`, `1`, `2`) as the key, a section rendered at
different index positions across re-renders gets the wrong panel open/text.

**Why it happens:** Section order in document.jsx can vary (DRF section is conditional).

**How to avoid:** Use the semantic section key strings (`'id'`, `'ov'`, `'du'`, `'cls'`,
`'q'`, `'drf'`) as the amendmentPanels dict key — exactly as specified in UI-SPEC.md
Section D State model. [VERIFIED: UI-SPEC.md]

### Pitfall 4: audit_log rows read back without deduplication

**What goes wrong:** A user saves an amendment note for a section, then saves again.
`audit_log` now has 2 rows for that section. `GET /api/wd/{id}/amendments` returns both.
The frontend displays the wrong (first) note.

**Why it happens:** `audit_log` is an append-only log; there is no UPDATE path.

**How to avoid:** `GET /api/wd/{id}/amendments` must return **only the latest row per
section** — use `SELECT * FROM audit_log WHERE wd_id=? AND event='manager_amendment'`
ordered by `id DESC` and pick the first per section. Or use a `GROUP BY` + `MAX(id)`
strategy. [ASSUMED: correct deduplication approach]

### Pitfall 5: Vitest `jsdom` environment — `document is not defined`

**What goes wrong:** The 23 frontend tests currently have 23 failures with
`ReferenceError: document is not defined`. This was observed in the live test run.

**Why it happens:** The test files import from `document.jsx` which has a module-level
side effect or the jsdom environment isn't loading correctly. (Phase 18 introduced
`document.jsx` exports like `OrphanBadge` that may import from React; the test
environment `globals: true` config may not fully initialise the DOM before assertions.)

**How to avoid:** Wave 0 must investigate and fix the jsdom test failure before adding
new Phase 19 tests. This is a Wave 0 blocker — the test suite is currently non-green
on the frontend. The fix is likely a `setupFiles` entry in `vite.config.js` that imports
`@testing-library/react/pure` or sets `window` globals. [ASSUMED: root cause; confirmed:
symptom observed]

**Confirmed state:** 64/64 backend tests GREEN. 7/30 frontend tests GREEN; 23 failing
with jsdom error. Phase 19 Wave 0 must fix the frontend baseline before adding new tests.

---

## Code Examples

### GET /api/wd/{id}/amendments — Amendment Retrieval

```python
# Source: adapted from jes_service.py audit_log read pattern [VERIFIED: codebase]
@router.get("/wd/{wd_id}/amendments")
async def get_amendments(wd_id: str) -> dict:
    """Return latest amendment note per section for a WD."""
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
    # Deduplicate: first occurrence (highest id) per section wins
    notes = {}
    for row in rows:
        detail = json.loads(row["detail"])
        section = detail.get("section")
        if section and section not in notes:
            notes[section] = detail.get("comment", "")
    return {"wd_id": wd_id, "notes": notes}
```

### POST /api/wd/{id}/amendments — Amendment Save

```python
# Source: jes_service.py override_jes_factor write pattern [VERIFIED: codebase]
class AmendmentRequest(BaseModel):
    section: str = Field(min_length=1, max_length=50)   # e.g. 'id', 'ov', 'du', 'cls', 'q', 'drf'
    comment: str = Field(min_length=1, max_length=2000)

@router.post("/wd/{wd_id}/amendments", status_code=201)
async def save_amendment(wd_id: str, body: AmendmentRequest) -> dict:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    con = get_connection(settings.db_path)
    try:
        # Verify WD exists
        row = con.execute("SELECT id FROM work_descriptions WHERE id = ?", (wd_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Work description not found")
        con.execute(
            "INSERT INTO audit_log (wd_id, event, actor, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            (wd_id, "manager_amendment", "advisor",
             json.dumps({"section": body.section, "comment": body.comment}),
             now.isoformat()),
        )
        con.commit()
    finally:
        con.close()
    return {"wd_id": wd_id, "section": body.section, "saved": True}
```

### Frontend: Amendment Notes Hydration on WD Load

```jsx
// Source: Pattern mirrors orphan_check useEffect in app.jsx lines 113-134 [VERIFIED]
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

### CSS: New Classes for Phase 19

```css
/* Source: UI-SPEC.md Sections B and C [VERIFIED] */
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
.amend-btn { /* ... full spec in UI-SPEC.md Section D */ }
.amend-indicator { width: 8px; height: 8px; border-radius: 50%; background: var(--gold); }
.amend-panel { margin-top: 8px; padding: 12px 16px; border: 1px solid var(--line); border-radius: var(--radius-sm); }
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static `QUAL_DEFAULT` (EC-05 environmental text) | OG-group-keyed `QUAL_DEFAULTS` map + `getQualDefault(og_code)` | Phase 19 (this phase) | AS/IT/FI users see the correct qual standard, not EC policy boilerplate |
| No amendment space | `audit_log` rows with `event="manager_amendment"` + inline panel UI | Phase 19 (this phase) | Manager feedback is captured, traceable, and exportable (Phase 20) |
| Inline styles for Section 5 Education/Experience labels | `.qual-sub-k` CSS class | Phase 19 (this phase) | Removes inline style anti-pattern; no visual change |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `getQualDefault` should fall through to `QUAL_DEFAULTS['default']` when `og_code` is undefined — not call the API | Pattern 1 | Low: the fallback text is acceptable; the API path would add latency but produce correct results |
| A2 | Using semantic section key strings (`'id'`, `'ov'`, `'du'`, `'cls'`, `'q'`, `'drf'`) as `amendmentPanels` keys is the correct approach (confirmed by UI-SPEC.md) | Pitfall 3 | Low |
| A3 | `GET /api/wd/{id}/amendments` is the correct retrieval mechanism (Option A) rather than storing amendment notes in the WD model | Pattern 4 | Medium: if Phase 20 export needs amendments at DOCX render time it must read from audit_log; this is fine since audit_log is queryable |
| A4 | The 23 frontend test failures are a jsdom environment issue, not a logic regression, and can be fixed in Wave 0 | Pitfall 5 | Medium: if it's a logic regression the test baseline cannot be restored without reverting Phase 18 code |
| A5 | The simplest approach to pass `og_code` to `QualEditor` is to thread it through `StepInput` via a new `record` prop | Pattern 2 | Low: alternative is to set `preset` in STEPS definition at render time |
| A6 | AMEND-02 (DOCX appendix) data comes from `audit_log` rows read at export time — no intermediate data structure needed | Architecture | Low: confirmed by AMEND-01's requirement that notes are "stored as audit_log entries" |

---

## Open Questions

1. **Frontend test baseline (Pitfall 5)**
   - What we know: 23/30 frontend tests fail with `ReferenceError: document is not defined`
   - What's unclear: Whether this is a Phase 18 regression or a pre-existing environment issue
   - Recommendation: Wave 0 must run `npx vitest run` with `--reporter=verbose` in the v2/frontend directory, inspect the first failing test, and add a `setupFiles` that imports `@testing-library/react` or fixes the jsdom global initialisation before adding any Phase 19 tests

2. **`record` prop threading into `QualEditor`**
   - What we know: `StepInput` in components.jsx dispatches props to input controls; `QualEditor` currently receives only `value` and `onChange`
   - What's unclear: Whether the planner should thread `record` through `StepInput` (general) or handle it specifically for the quals step
   - Recommendation: Add `record` as an optional prop on `StepInput` and pass it only when `cfg.type === 'quals'` — minimal change, no side effects on other input types

3. **Amendment note section key for Position Identification**
   - What we know: UI-SPEC.md Section Order Contract lists section `'id'` as the key for Position Identification; the amendment panel renders for all sections in review state
   - What's unclear: Whether the section key in the amendment `POST` body is validated against a whitelist
   - Recommendation: Validate section against the known set `{'id', 'ov', 'du', 'cls', 'q', 'drf'}` in the Pydantic model using a `Literal` or `validator`

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| SQLite3 (stdlib) | audit_log writes | ✓ | stdlib | — |
| React 18 + Vitest | Frontend tests | ✓ | as configured | — |
| pytest + pytest-asyncio | Backend tests | ✓ | as configured | — |

Step 2.6: No new external dependencies. All required tools are present.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (backend) | pytest + pytest-asyncio |
| Framework (frontend) | Vitest + jsdom + @testing-library/react |
| Backend config | `v2/backend/tests/conftest.py` |
| Frontend config | `v2/frontend/vite.config.js` (test block) |
| Quick run (backend) | `cd v2/backend && python -m pytest tests/ -q` |
| Quick run (frontend) | `cd v2/frontend && npx vitest run` |
| Full suite | Both of the above |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUAL-01 | `getQualDefault('EC')` returns EC education/experience strings | unit | `pytest tests/test_quals.py::test_qual_default_ec -x` | ❌ Wave 0 |
| QUAL-01 | `getQualDefault('AS')`, `getQualDefault('IT')`, `getQualDefault('FI')` return correct group text | unit | `pytest tests/test_quals.py::test_qual_default_all_groups -x` | ❌ Wave 0 |
| QUAL-01 | `getQualDefault(undefined)` returns default text without throwing | unit | vitest: `document.test.jsx::test_get_qual_default_fallback` | ❌ Wave 0 |
| QUAL-01 | QualEditor pre-fills with OG-matched text on mount | unit | vitest: `components.test.jsx::test_qual_editor_prefill_ec` | ❌ Wave 0 |
| QUAL-02 | `.qual-error` appears after field blur when empty | unit | vitest: `components.test.jsx::test_qual_error_appears_on_blur` | ❌ Wave 0 |
| QUAL-02 | `.qual-error` disappears when field has content | unit | vitest: `components.test.jsx::test_qual_error_clears_on_input` | ❌ Wave 0 |
| QUAL-03 | Section 5 renders with `.qual-sub-k` class (not inline style) | unit | vitest: `document.test.jsx::test_section5_sub_labels` | ❌ Wave 0 |
| AMEND-01 | `POST /api/wd/{id}/amendments` returns 201; audit_log row exists | integration | `pytest tests/test_amendments.py::test_save_amendment_creates_audit_row -x` | ❌ Wave 0 |
| AMEND-01 | `GET /api/wd/{id}/amendments` returns latest note per section | integration | `pytest tests/test_amendments.py::test_get_amendments_latest_per_section -x` | ❌ Wave 0 |
| AMEND-01 | 404 when WD doesn't exist | integration | `pytest tests/test_amendments.py::test_save_amendment_404 -x` | ❌ Wave 0 |
| AMEND-02 | Amendment notes stored in audit_log with correct fields | integration | `pytest tests/test_amendments.py::test_amendment_audit_log_fields -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd v2/backend && python -m pytest tests/ -q`
- **Per wave merge:** both backend and frontend suites
- **Phase gate:** Full suite green (64+ backend, 7+ frontend) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `v2/backend/tests/test_amendments.py` — covers AMEND-01, AMEND-02 (backend)
- [ ] `v2/frontend/src/components.test.jsx` — covers QUAL-01 (prefill), QUAL-02 (inline validation)
- [ ] `v2/frontend/src/document.test.jsx` — extend for QUAL-03 (sub-labels class)
- [ ] Fix jsdom test environment failure (23 tests currently failing — must be green before Phase 19 tests can run)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | single-user local app |
| V3 Session Management | no | single-user local app |
| V4 Access Control | no | single-user local app |
| V5 Input Validation | yes | Pydantic `Field(max_length=2000)` on `AmendmentRequest.comment`; section key validated against known set |
| V6 Cryptography | no | no new secrets |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Oversized amendment comment | Tampering | `Field(max_length=2000)` on `AmendmentRequest.comment` — same cap used in T-16-03 for work_description |
| Unknown section key in amendment | Tampering | Validate `section` against `Literal['id', 'ov', 'du', 'cls', 'q', 'drf']` in Pydantic model |
| WD ID injection (audit_log wd_id) | Tampering | WD existence check before INSERT (404 guard) — same pattern as jes_override |

---

## Sources

### Primary (HIGH confidence)

- `v2/backend/app/data/constants.py` — QUAL_STANDARDS constant with verified EC/AS/IT/FI
  qualification text; already serves `GET /api/quals/default`
- `v2/backend/app/db.py` — audit_log schema (two-column indexed table)
- `v2/backend/app/services/jes_service.py` — canonical audit_log INSERT pattern
- `v2/backend/app/api/wd.py` — WD CRUD + orphan_check patterns
- `v2/frontend/src/data.jsx` — QUAL_DEFAULT (current), STEPS, PHASES export structure
- `v2/frontend/src/components.jsx` — QualEditor, initialAnswer, answerValid
- `v2/frontend/src/document.jsx` — Section 5 rendering, Sec component, Ghost component
- `v2/frontend/src/app.jsx` — reviewing state, amendmentNotes state placeholder, commit flow
- `.planning/phases/19-qualifications-amendments/19-UI-SPEC.md` — authoritative UI contract

### Secondary (MEDIUM confidence)

- Live test run output — confirmed 64 backend GREEN, 23 frontend FAILING with jsdom error

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — entire stack is fixed by prior phases
- Architecture: HIGH — patterns are directly observed in codebase
- Pitfalls: HIGH (QUAL-DEFAULT rename, section keys) / MEDIUM (jsdom root cause)
- Amendment retrieval approach (Option A vs B): MEDIUM — reasonable but not validated by a prior phase

**Research date:** 2026-06-09
**Valid until:** 2026-07-09 (30 days; stack is stable)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QUAL-01 | OG-matched qualification defaults pre-fill education + experience textareas | `QUAL_STANDARDS` constant verified in `app/data/constants.py`; `getQualDefault()` function pattern documented; `GET /api/quals/default` already serves the data |
| QUAL-02 | Editable textareas with inline validation; Finish disabled when either field empty | `answerValid()` already gates on `education && experience`; `touched`-state pattern documented; `.qual-error` CSS class specified |
| QUAL-03 | Section 5 renders Education/Experience sub-labels in monospace caps + "TBS Qualification Standard" provenance tag | `src="TBS Qualification Standard"` already coded (document.jsx line 361); inline style extraction to `.qual-sub-k` documented |
| AMEND-01 | Advisor can save amendment note per section in review state; stored as audit_log entry | `audit_log` table schema verified; INSERT pattern from `jes_service.py` documented; new `POST /api/wd/{id}/amendments` endpoint design provided |
| AMEND-02 | DOCX appendix "Manager Amendments for Review" lists notes with section ref + provenance tag | Data is in `audit_log`; this requirement's DOCX rendering surface belongs to Phase 20 (docxtpl); the audit_log write in AMEND-01 is the prerequisite |
</phase_requirements>
