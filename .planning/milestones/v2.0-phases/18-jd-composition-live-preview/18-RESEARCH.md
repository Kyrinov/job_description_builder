# Phase 18: JD Composition & Live Preview — Research

**Researched:** 2026-06-08
**Domain:** React SPA (document.jsx, components.jsx, app.jsx) + FastAPI backend (noc_mapping.py, wd.py) — duty selection, provenance tagging, orphan check, live document preview
**Confidence:** HIGH

---

## Summary

Phase 18 adds verbatim NOC duty selection with provenance tagging, an orphan statement checker, and the complete live document preview with ghost shimmer placeholders, a composed overview, clickable section headers, and a live provenance footer. The work is split roughly 60/40 frontend/backend.

The frontend already has all the visual building blocks — `DutyBuilder`, `.duty-sug`, `.doc-duty`, `Ghost`, `Sec`, `.prov`/`.prov__tag`, `.sec--editable` — all defined and styled in `components.jsx`, `document.jsx`, and `styles.css`. Phase 18 primarily rewires `DutyBuilder` to fetch verbatim duties from a new `GET /api/noc/{noc_code}/duties` endpoint instead of reading from the static `DUTY_SUGGESTIONS` constant, upgrades the duty data model to carry structured `ProvenanceTag` fields, and adds the orphan check trigger and badge rendering in review state.

The backend needs one new stateless read endpoint (`GET /api/noc/{noc_code}/duties`) and one new compute endpoint (`POST /api/wd/{id}/orphan_check`). The NOC FTS5 database is already present and queryable via `get_noc_connection()` — the duty fetch simply reads `noc_elements WHERE noc_code = ? AND element_type = 'Main duties'`. The orphan check uses `OG_DEFINITIONS` (already in `app/data/constants.py`) to test each duty verb against the OG's inclusions/exclusions using keyword matching — no LLM required (v1.0 used LLM for this; v2.0 must not).

The `WorkDescription` Pydantic model and the `DraftDuty` model need extensions: `DraftDuty` must gain `provenance_noc_code`, `provenance_section`, `provenance_hash`, and `is_advisor` fields (or a nested `ProvenanceTag` object). The `WDPatchRequest` must accept a `duties` field so duty commits persist to the backend.

**Primary recommendation:** Implement in 4 waves: Wave 0 (RED test stubs + model extensions), Wave 1 (backend endpoints GREEN), Wave 2 (frontend DutyBuilder rewire + document.jsx updates), Wave 3 (orphan badge in review + full suite green gate + UAT).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Fetch verbatim NOC duties for a code | API/Backend | — | NOC FTS5 DB lives server-side; client has no direct DB access |
| ProvenanceTag content hash | API/Backend | — | Hash must be computed server-side from the authoritative source record |
| Orphan check (verb vs. OG functional authority) | API/Backend | — | Requires OG_DEFINITIONS constant + keyword matching logic; not client-side |
| DutyBuilder UI — card selection, toggle, count | Browser/Frontend | — | Purely client-side interaction state; no server round-trip until submit |
| Advisor-added duty entry + refineDuty | Browser/Frontend | — | refineDuty is a pure client-side verb-mapper; runs entirely in browser |
| Live preview Section 3 ghost/fill | Browser/Frontend | — | Derived from `record.duties` which is in-memory React state |
| Ghost shimmer placeholders | Browser/Frontend | — | Pure CSS animation on `.ph-line`; no server involvement |
| Orphan badge rendering in review state | Browser/Frontend | API/Backend | Badge content comes from backend orphan_check response; rendering is frontend |
| Provenance footer tag list | Browser/Frontend | — | Derived from `record.duties` presence in `DocumentPane`; already implemented |
| Section click-to-edit (DOC-04) | Browser/Frontend | — | `editing = reviewing` state gate; already implemented in `Sec` component |
| Position Overview composition (DOC-02) | Browser/Frontend | — | `buildOverview()` already implemented in document.jsx; no change needed |
| Duties persistence to DB | API/Backend | Browser (WD PATCH) | Duties stored in `WorkDescription.duties` via `PATCH /api/wd/{id}` |

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| JD-01 | Duty builder presents FTS5 matches for confirmed NOC code as selectable cards; selected duties are verbatim NOC text; no LLM duty generation | `GET /api/noc/{noc_code}/duties` reads `noc_elements WHERE noc_code = ? AND element_type = 'Main duties'`; DutyBuilder rewired with `noc_code` prop |
| JD-02 | Every selected duty carries a structured ProvenanceTag (source type "NOC", NOC code, section reference, content hash) | DraftDuty model extended with provenance fields; hash = `hashlib.sha256(element_text)` from noc_elements.source_hash |
| JD-03 | Advisor-added duties tagged source type "advisor-added" with distinct visual marker | DraftDuty `advisor: true` field + `.is-advisor` CSS class already exists; tag label changes to "advisor-added" |
| JD-04 | Orphan check at review time flags duties contradicting OG functional authority; warning shown with citation | `POST /api/wd/{id}/orphan_check` uses `OG_DEFINITIONS[og_code]` inclusions/exclusions; returns `{flags: [{duty_id, orphan_rationale}]}`; badge rendered only in review state |
| DOC-01 | Live preview shows 5 sections in order; each appears as advisor starts that step | Sections 1-4 already rendered in document.jsx; Section 5 (EQ) needs ghost-only wrapper added; section order is correct |
| DOC-02 | Position Overview composed from answers | `buildOverview()` in document.jsx already implements the formula; no change needed |
| DOC-03 | Unfilled sections show ghost shimmer (3 prose lines, 2 duty lines) with hint note | Ghost component and `.ph-line` shimmer already exist; Section 3 ghost copy changes per UI-SPEC |
| DOC-04 | In review state, section headers clickable to jump to conversation step | `Sec` component already has `editable` / `onEdit` props; `editStep()` in app.jsx; only Section 3 duties mapping needs confirming (`onEditStep('duties')`) |
| DOC-05 | Document footer shows provenance tags updating live | provTags array in `DocumentPane` already tracks `hasDuties` / advisor duties; `src` pill on Section 3 header needs "· refined" suffix removed |
</phase_requirements>

---

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React 18 | 18.x | Component rendering, useState, useMemo | Existing SPA stack |
| FastAPI | current | Backend endpoints | Existing API stack |
| Pydantic v2 | current | Request/response models | Existing validation stack |
| SQLite (stdlib) | 3.x | NOC FTS5 DB read + WD DB write | Already used; `get_noc_connection()` opens with sqlite-vec |
| hashlib (stdlib) | stdlib | SHA-256 for ProvenanceTag content hash | No new dep needed |
| pytest + httpx | current | Backend tests | Existing test infrastructure |
| Vitest + jsdom | current | Frontend component tests | Existing test infrastructure |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlite_vec | current | Already loaded via `get_noc_connection()` | Only relevant for noc_mapper; duties endpoint uses plain `get_noc_connection()` which loads sqlite-vec as a side effect |

**No new package installs required for Phase 18.**

---

## Architecture Patterns

### System Architecture Diagram

```
Advisor clicks "duties" step
        |
        v
DutyBuilder mounts
  → GET /api/noc/{noc_code}/duties
  → noc_elements WHERE noc_code=? AND element_type='Main duties'
  → returns [{id, text, source_hash}]
        |
        v
Advisor selects / adds duties
  → DutyBuilder holds selection as [{id, plain, polished, advisor, noc_code, source_hash}]
        |
        v
"Add to description" clicked
  → commit() in app.jsx
  → PATCH /api/wd/{id} with duties[] carrying ProvenanceTag fields
  → Section 3 in DocumentPane fills with freshWash animation
        |
        v
Advisor reaches review state
  → POST /api/wd/{id}/orphan_check
  → OG_DEFINITIONS[confirmed_og.og_code] inclusions/exclusions loaded
  → Each duty verb-phrase checked against exclusions
  → Returns {flagged: [{duty_id, orphan_rationale}]}
  → OrphanBadge rendered on flagged .doc-duty items
```

### Recommended Project Structure

No new directories. Changes are localized to:

```
v2/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── noc_mapping.py        ← add GET /noc/{noc_code}/duties route
│   │   │   └── wd.py                 ← add POST /wd/{id}/orphan_check + duties to WDPatchRequest
│   │   ├── models/
│   │   │   └── draft_duty.py         ← extend DraftDuty with provenance fields
│   │   └── data/
│   │       └── constants.py          ← no change (OG_DEFINITIONS already present)
│   └── tests/
│       └── test_jd_composition.py    ← new test file for Phase 18
├── frontend/
│   └── src/
│       ├── components.jsx            ← DutyBuilder: add noc_code prop, fetch logic, ProvenanceTag tag
│       ├── document.jsx              ← Section 3: verbatim duty render, orphan badge, src pill fix
│       ├── app.jsx                   ← duty commit: include provenance fields in PATCH payload
│       └── styles.css                ← add .orphan-badge class (per UI-SPEC)
```

### Pattern 1: Stateless NOC Duty Fetch Endpoint

`GET /api/noc/{noc_code}/duties` — reads verbatim duty strings for a NOC code from the existing NOC FTS5 database. No LLM, no vector search — pure SQL.

```python
# Source: [VERIFIED: noc_mapper.py line 107-113] — same query pattern used in jd_service.py v1
@router.get("/noc/{noc_code}/duties")
async def get_noc_duties(noc_code: str) -> dict:
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
        raise HTTPException(status_code=404, detail=f"No duties found for NOC {noc_code!r}")
    return {
        "noc_code": noc_code,
        "duties": [
            {"id": row["id"], "text": row["element_text"], "source_hash": row["source_hash"]}
            for row in rows
        ]
    }
```

**Key details:**
- Use `get_noc_connection()` (not `get_connection()`) — it loads sqlite-vec and opens the NOC DB at `settings.noc_db_path`
- `element_type = 'Main duties'` is the correct filter — confirmed in both noc_mapper.py and jd_service.py (v1) [VERIFIED: codebase]
- `source_hash` from `noc_elements` is the pre-computed SHA-256 of the source record — use this as the `provenance_hash` in ProvenanceTag [VERIFIED: v1.0 ingest scripts + models]
- The endpoint is stateless — does not write to WD DB

### Pattern 2: ProvenanceTag Extension to DraftDuty

The current `DraftDuty` model (v2.0) has fields `id`, `text`, `plain_trigger`, `source` (Literal["suggested", "advisor"]), `source_index`, `refined_at`. It lacks the structured ProvenanceTag required by JD-02.

**Required extension:**

```python
# Source: [VERIFIED: app/models/draft_duty.py + v1.0 app/models/work_description.py]
class DraftDuty(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    text: str                              # verbatim NOC text (NOC duties) or refined text (advisor)
    plain_trigger: Optional[str] = None    # original plain text (advisor-added only)
    source: Literal["noc", "advisor"]      # ← change: "suggested" → "noc" for Phase 18
    # Phase 18 additions — ProvenanceTag fields (JD-02, JD-03)
    provenance_noc_code: Optional[str] = None    # e.g. "21232" — NOC duties only
    provenance_section: str = "Main duties"      # always "Main duties" for NOC duties
    provenance_hash: Optional[str] = None        # source_hash from noc_elements row
    advisor: bool = False                         # True for advisor-added duties (JD-03)
    orphan: bool = False                          # set by orphan_check response (JD-04)
    orphan_rationale: Optional[str] = None       # citation text from orphan_check
    # Legacy fields (keep for backward compat with existing records)
    source_index: Optional[int] = None
    refined_at: Optional[datetime] = None
```

**Note on `source` field rename:** The current value "suggested" is prototype-era. Phase 18 introduces "noc" as the correct source type for FTS5-selected verbatim duties. Keep "advisor" as-is. The Pydantic model uses `extra="ignore"` so old records with `source="suggested"` will not break — they just store an unexpected string.

**Alternative approach:** Use a nested `ProvenanceTag` object. The v1.0 model had this pattern. However, the v2.0 approach of flat fields on `DraftDuty` is simpler given the single-source model (one NOC per WD), avoids a new model class, and aligns with how duties are sent in the JS PATCH payload (flat object with `advisor`, `id`, `plain`, `polished`). Flat fields are recommended.

### Pattern 3: WDPatchRequest Duties Field

The current `WDPatchRequest` (in `wd.py`) does not include a `duties` field. The frontend currently stores duties only in `record.duties` (client-side), not persisting them to the backend. Phase 18 must persist duties with ProvenanceTag to the backend.

**Required addition to `WDPatchRequest`:**

```python
# Source: [VERIFIED: app/api/wd.py WDPatchRequest + models/draft_duty.py]
class WDPatchRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # ... existing fields ...
    duties: Optional[list[dict]] = None   # list of DraftDuty-compatible dicts
```

In the `patch_wd` handler, when `duties` is provided, validate each item against `DraftDuty` before storing:

```python
if body.duties is not None:
    wd.duties = [DraftDuty(**d) for d in body.duties]
```

**Frontend PATCH payload — duty shape:**
The frontend currently sends duties as `{id, plain, polished, advisor}`. Phase 18 must extend this to include `{id, text, plain_trigger, source, provenance_noc_code, provenance_section, provenance_hash, advisor}`. The `text` field should hold the verbatim NOC text (same as `plain` for NOC duties). The frontend constructs this from the `GET /api/noc/{noc_code}/duties` response.

### Pattern 4: Orphan Check Endpoint

`POST /api/wd/{id}/orphan_check` — deterministic verb-keyword check against `OG_DEFINITIONS`. No LLM (v2.0 constraint: LLM only in NOC pipeline).

```python
# Source: [VERIFIED: app/data/constants.py OG_DEFINITIONS structure]
# Algorithm: check duty text against OG exclusions keywords
@router.post("/wd/{wd_id}/orphan_check")
async def run_orphan_check(wd_id: str) -> dict:
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute("SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)).fetchone()
    finally:
        con.close()
    if not row:
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
        # Simple keyword extraction from exclusions
        if exclusions_text and _duty_contradicts_og(duty_lower, exclusions_text):
            flagged.append({
                "duty_id": duty.id,
                "orphan_rationale": f"This duty may fall outside the {og_code} functional authority: {exclusions_text[:200]}"
            })
    return {"wd_id": wd_id, "flagged": flagged}
```

**Algorithm for `_duty_contradicts_og()`:** Extract action verbs and key nouns from the duty text. Cross-check against the OG's exclusion clause keywords. For IT exclusions: flag duties with "administrative programs" / "business analysis" / "information management" (non-IT context). For EC: no exclusions defined in current `OG_DEFINITIONS`. This is a lightweight deterministic check — the v1.0 LLM approach is not ported.

**Important:** The v1.0 `check_orphan_statements` used an LLM (jd_ranking.py). Phase 18 must NOT use an LLM for this check — the v2.0 decision is deterministic classification throughout. The orphan check is advisory (no blocking gate). [VERIFIED: STATE.md decisions + REQUIREMENTS.md JD-04]

### Pattern 5: DutyBuilder Rewire for NOC FTS5

The `DutyBuilder` component in `components.jsx` currently reads from `cfg.suggestions` (injected by app.jsx via `getDutySuggestions(answers)` → OG-keyed `DUTY_SUGGESTIONS` static arrays). Phase 18 replaces this with a fetch:

```jsx
// Source: [VERIFIED: components.jsx DutyBuilder + UI-SPEC interaction model]
function DutyBuilder({ value, onChange, cfg }) {
  const list = value || [];
  const [text, setText] = useState('');
  const [nocDuties, setNocDuties] = useState(null); // null=loading, []=[]=empty/error, [...]=fetched
  const inputRef = useRef(null);

  const noc_code = cfg && cfg.noc_code;

  useEffect(() => {
    if (!noc_code) return;
    setNocDuties(null); // trigger shimmer
    fetch(`/api/noc/${encodeURIComponent(noc_code)}/duties`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => setNocDuties(data.duties || []))
      .catch(() => setNocDuties([])); // error: empty array + toast
  }, [noc_code]);

  // ... rest of component
}
```

**app.jsx cfgOverride for duties step:**

```javascript
// Source: [VERIFIED: app.jsx stepCfgOverride block]
// Change: was { ...step.input, suggestions: getDutySuggestions(answers) }
// Now:
: step.id === 'duties'
  ? { ...step.input, noc_code: record.confirmed_noc
        ? (typeof record.confirmed_noc === 'string'
            ? record.confirmed_noc
            : record.confirmed_noc.noc_code)
        : null }
  : undefined
```

### Pattern 6: Section 3 Verbatim Duty Render

Current `document.jsx` line 243 renders `d.polished` for each duty. Phase 18 changes this to `d.text` (verbatim NOC text). The distinction:
- Before Phase 18: `d.polished` = LLM-refined duty statement from `refineDuty()`
- After Phase 18: `d.text` = verbatim NOC element_text from FTS5 DB (NOC duties); `d.polished` = `refineDuty(d.plain_trigger)` only for advisor-added duties

The `src` pill on Section 3 changes from `'NOC 2021 · refined'` to `'NOC 2021'` (remove "· refined" since text is now verbatim). [VERIFIED: UI-SPEC Section D]

### Anti-Patterns to Avoid

- **Using `get_connection()` instead of `get_noc_connection()` for duty fetch:** `get_connection()` opens the WD database, not the NOC database. The `noc_elements` table is in `settings.noc_db_path`. Always use `get_noc_connection(settings.noc_db_path)` for NOC reads.
- **LLM duty generation:** JD-01 is explicit: no free-form LLM duty generation. The duty builder presents FTS5 verbatim matches only.
- **LLM orphan check:** v2.0 uses deterministic keyword matching against `OG_DEFINITIONS`. The v1.0 `jd_ranking.py` LLM approach is NOT ported.
- **Blocking orphan check gate:** JD-04 says flagged duties show a warning indicator — the advisor can still proceed. Do not add a hard gate on orphan-flagged duties.
- **Fetching duties on every render:** Use `useEffect([noc_code])` so the fetch fires once when `noc_code` changes, not on every render cycle.
- **Sending `d.polished` as the duty text for NOC duties:** NOC duties must use `d.text` (verbatim). `d.polished` is only for advisor-added duties that went through `refineDuty()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SHA-256 content hash | Custom hash function | `hashlib.sha256(text.encode()).hexdigest()` | Already used in v1.0 ingest scripts; stdlib |
| NOC duty fetch | Custom DB query layer | `get_noc_connection()` + parameterized SQL | Connection factory already handles sqlite-vec load and row_factory |
| React fetch with loading state | Custom hook | Inline `useEffect` + `useState` | Matches existing codebase pattern (see `nocLoading`/`ogLoading` in app.jsx) |
| Shimmer loading state | Custom animation | `.ph-line` class already in styles.css | Pre-existing CSS animation |
| Orphan badge CSS | Inline styles | `.orphan-badge` class per UI-SPEC spec | UI-SPEC provides exact CSS; write it once in styles.css |

---

## Key Research Findings — 10 Questions Answered

### Q1: NOC FTS5 Setup — How to Query Verbatim Duties

**Finding:** [VERIFIED: app/services/noc_mapper.py + app/services/jd_service.py]

The NOC database is opened via `get_noc_connection(settings.noc_db_path)`. The relevant tables:
- `noc_units(id, noc_code, teer_level, title, definition, source_hash)` — one row per NOC unit
- `noc_elements(id, noc_code, element_type, element_text, source_hash)` — elements of each unit

To get verbatim duties for a NOC code:
```sql
SELECT id, element_text, source_hash
FROM noc_elements
WHERE noc_code = ? AND element_type = 'Main duties'
ORDER BY id
```

The `source_hash` column already holds a SHA-256 hash of the source record, computed at ingest time. Use it directly as `provenance_hash` — no recomputation needed.

A new `GET /api/noc/{noc_code}/duties` route goes in `app/api/noc_mapping.py` alongside the existing `POST /api/noc/map` route on the same router.

### Q2: DutyBuilder Current Interface

**Finding:** [VERIFIED: components.jsx lines 108-193]

Current props:
- `value`: `list[{id, plain, polished, advisor}]` — selected duties
- `onChange(value)`: called with updated list on toggle or add
- `cfg`: step config object; `cfg.suggestions` is injected by app.jsx via `getDutySuggestions(answers)` → OG-keyed `DUTY_SUGGESTIONS` arrays

Phase 18 change: `cfg.suggestions` is replaced by `cfg.noc_code` (the confirmed NOC code). The component fetches duties internally via `useEffect`. The `suggestions` prop pathway is removed for the duties step (it still exists in the component but `noc_code` takes precedence when present).

The internal duty shape must change to carry verbatim text + provenance:
- Currently: `{id: 'sug-{plain}', plain, polished, advisor: false}`
- After Phase 18: `{id: 'noc-{element_id}', plain: element_text, text: element_text, source: 'noc', provenance_noc_code, provenance_section: 'Main duties', provenance_hash, advisor: false}`
- Advisor-added (unchanged): `{id: 'adv-{timestamp}', plain, text: refineDuty(plain), source: 'advisor', advisor: true}`

### Q3: ProvenanceTag Schema

**Finding:** [VERIFIED: app/models/draft_duty.py + app/models/work_description.py (v1 reference)]

v2.0 `DraftDuty` currently has no ProvenanceTag. v1.0 had a separate `ProvenanceTag` Pydantic model with `source_type`, `source_id`, `source_version`, `retrieved_date`. Phase 18 adds flat provenance fields directly to `DraftDuty` (simpler, avoids a new model, aligns with the JS payload shape):

```
provenance_noc_code: Optional[str]   — NOC code (e.g. "21232")
provenance_section: str               — always "Main duties"
provenance_hash: Optional[str]        — SHA-256 from noc_elements.source_hash
```

No new Pydantic model class needed. The JS payload from the frontend includes these as flat fields on each duty object.

### Q4: WorkDescription Model — Current Duties Field

**Finding:** [VERIFIED: app/models/work_description.py]

Current `WorkDescription` has:
```python
duties: list[DraftDuty] = Field(default_factory=list)
```

The `DraftDuty` model is imported from `app/models/draft_duty.py`. Phase 18 extends `DraftDuty` (as above) — the `WorkDescription.duties` field does not change name or type, only the DraftDuty model itself gains new optional fields.

The `work_descriptions` SQLite table stores the full `WorkDescription` as JSON in the `data` column — no schema migration needed. Pydantic's `extra="ignore"` + all new fields being `Optional` ensures old records load cleanly.

### Q5: Orphan Check Logic

**Finding:** [VERIFIED: app/data/constants.py OG_DEFINITIONS; CITED: STATE.md v2.0 decisions]

v2.0 uses `OG_DEFINITIONS` (in-memory Python constant, already present in `app/data/constants.py`). The relevant fields per OG:
- `EC`: `inclusions=""`, `exclusions=""` — no exclusions defined; orphan check will flag nothing for EC [VERIFIED]
- `IT`: has a substantial `exclusions` string listing activities that belong to other OGs (business analysis, administrative programs, etc.)
- `AS`, `FI`: no exclusions defined in current constants

Algorithm:
1. Load `OG_DEFINITIONS[og_code]` from in-memory constant
2. Extract the `exclusions` text
3. For each duty, check if the duty text contains keywords from the exclusions
4. Flag = True if any exclusion keyword matches

The v1.0 approach used LLM (`jd_ranking.py → ORPHAN_CHECK_SYSTEM_PROMPT`). Phase 18 must NOT use LLM. The deterministic keyword approach is sufficient for the v2.0 advisory warning (non-blocking).

**Practical implication:** For EC group (the primary v2.0 target), no exclusions are defined, so the orphan check will always return 0 flags for EC. IT has real exclusions. This is correct behavior and should be documented in code comments.

### Q6: document.jsx Current State of Section 3

**Finding:** [VERIFIED: document.jsx lines 231-254]

Current Section 3 (Key Responsibilities):
- `src` pill: `hasDuties ? 'NOC 2021 · refined' : null` → Phase 18 changes to `hasDuties ? 'NOC 2021' : null`
- Ghost: `<Ghost lines={2} />` + `<p className="ghost-note">Your responsibilities will appear here, formally worded.</p>` → Phase 18 changes ghost-note copy per UI-SPEC
- Duty render: `r.duties.map(d => <li>{d.polished}</li>)` → Phase 18 changes to `d.text` (verbatim)
- Orphan badge: absent → Phase 18 adds `{d.orphan && reviewing && <OrphanBadge rationale={d.orphan_rationale} />}`

`buildOverview()` (DOC-02): already fully implemented, no changes needed. [VERIFIED: document.jsx lines 9-27]

Section 5 (Essential Qualifications): currently rendered conditionally on `r.qualsVisited`. DOC-01 requires it always appear with ghost state. Phase 18 must change the condition: render Section 5 always, with ghost when `!r.qualsVisited`. The section number `n` counter logic must be updated accordingly.

**Note:** The current document.jsx also has a Section 5 "DND Results Linkage" that appears conditionally on `r.drf`. Per DOC-01, Defence Results Linkage is deferred to v2.1. The DRF section may remain as-is (conditional on `r.drf`) since it won't appear unless a DRF step exists in the flow. The Essential Qualifications section must be the last rendered section, always present with ghost.

### Q7: New API Endpoints — Request/Response Shapes

**Finding:** [VERIFIED: existing API pattern from noc_mapping.py + og_classification.py + wd.py]

**`GET /api/noc/{noc_code}/duties`**
- Path param: `noc_code` (str)
- Response: `{"noc_code": str, "duties": [{"id": int, "text": str, "source_hash": str}]}`
- 404 if no rows found for noc_code
- No request body; stateless read

**`POST /api/wd/{id}/orphan_check`**
- Path param: `wd_id` (str)
- No request body (reads WD from DB)
- Response: `{"wd_id": str, "flagged": [{"duty_id": str, "orphan_rationale": str}]}`
- 404 if WD not found; 422 if OG not confirmed

The orphan check route goes in `app/api/wd.py` alongside the existing WD CRUD routes (same router, same WD domain).

### Q8: SQLite Schema — Does work_descriptions Need Migration?

**Finding:** [VERIFIED: app/db.py SCHEMA_DDL + app/models/work_description.py]

No schema migration needed. The `work_descriptions` table stores the full `WorkDescription` as JSON in the `data TEXT NOT NULL` column. All new `DraftDuty` fields (`provenance_noc_code`, `provenance_section`, `provenance_hash`, `advisor`, `orphan`, `orphan_rationale`) are `Optional` with defaults. Old records without these fields deserialize correctly via Pydantic's `extra="ignore"` and default values.

The `WDPatchRequest` needs a new `duties: Optional[list[dict]] = None` field added.

### Q9: ProvenanceTag Content Hash

**Finding:** [VERIFIED: noc_mapper.py conftest.py — source_hash stored in noc_elements at ingest time]

The `source_hash` column in `noc_elements` already holds the SHA-256 hash of the source record, computed by the v1.0 ingest script. For Phase 18, use `noc_elements.source_hash` directly as `provenance_hash` — there is no need to recompute it. The frontend receives `source_hash` from the `GET /api/noc/{noc_code}/duties` response and includes it in the PATCH payload.

If the ingest script did not populate `source_hash` for some rows (possible for older DB state), it will be an empty string `""`. Handle gracefully: use `source_hash or None`.

### Q10: Test Infrastructure

**Finding:** [VERIFIED: v2/backend/tests/conftest.py + v2/frontend/src/app.test.jsx]

**Backend:** pytest + httpx AsyncClient + ASGITransport pattern. Key fixtures:
- `tmp_db_path`: fresh SQLite per test
- `env_with_db`: env vars including `NOC_DB_PATH`
- `test_app`: FastAPI app with schema initialized
- `client`: AsyncClient bound to test_app
- `noc_mapping_db`: synthetic NOC DB with `noc_units`, `noc_elements`, `noc_fts`, `noc_chunks_vec`

Phase 18 tests need a `noc_duties_db` fixture (lighter than `noc_mapping_db` — no vec table needed for duty fetch tests) that creates `noc_elements` rows with `element_type = 'Main duties'`.

**Frontend (Vitest + jsdom):** Tests in `app.test.jsx`, `conversation.test.jsx`, `document.test.jsx`. Pattern: import component, render with `render()`, fire events, assert on DOM. `vi.fn()` for mocks. `global.fetch` must be mocked for any component that calls `fetch`.

---

## Common Pitfalls

### Pitfall 1: `get_connection()` vs `get_noc_connection()` Confusion

**What goes wrong:** Using `get_connection(settings.db_path)` in the duty fetch endpoint opens the WD database, which has no `noc_elements` table. The query silently returns 0 rows and the endpoint returns 404 for all NOC codes.

**Why it happens:** The two connection factories look similar and both are in `app/db.py`. The NOC database is a separate file (`settings.noc_db_path`).

**How to avoid:** Always use `get_noc_connection(settings.noc_db_path)` for `noc_elements` queries. Add a comment in the new route: `# NOC DB — use get_noc_connection, not get_connection`.

**Warning signs:** `GET /api/noc/{noc_code}/duties` returning 404 for a known-good NOC code like `21232`.

### Pitfall 2: `d.polished` vs `d.text` in document.jsx

**What goes wrong:** Section 3 renders `d.polished` (refined duty text from `refineDuty()`). For verbatim NOC duties, `d.polished` is undefined/empty because verbatim duties bypass `refineDuty()`. The section renders blank duty bullets.

**Why it happens:** The existing DutyBuilder creates `{plain, polished}` pairs for suggested duties and puts the `polished` version in the document. Phase 18 replaces suggested duties with verbatim NOC duties that have no polished version.

**How to avoid:** Phase 18 uses `d.text` in the document render. `d.text` holds verbatim NOC text for NOC duties and `refineDuty(d.plain_trigger)` for advisor-added duties.

### Pitfall 3: EC Group Has No Exclusions — Orphan Check Always Returns 0 Flags for EC

**What goes wrong:** Advisor runs orphan check for an EC position and sees nothing flagged. This is correct but may appear to be a broken feature.

**Why it happens:** `OG_DEFINITIONS["EC"]["exclusions"]` is `""` (empty string). The current constants.py has no exclusions defined for EC, AS, or FI — only IT has exclusions.

**How to avoid:** The orphan check endpoint must handle empty exclusions gracefully (return `flagged: []`). Document the expected behavior in code comments and test it explicitly.

### Pitfall 4: PATCH Payload Shape Mismatch Between Frontend and Backend DraftDuty

**What goes wrong:** Frontend sends duty as `{id, plain, polished, advisor}` but backend `DraftDuty` now expects `{id, text, source, ...}`. Pydantic rejects or ignores fields silently.

**Why it happens:** The JS duty object shape and the Python DraftDuty model diverged during Phase 15's Socratic conversion. The `source` field is new in Phase 18.

**How to avoid:** Align the frontend duty object shape to match DraftDuty fields before sending the PATCH. Map: `text = plain` (for NOC duties), `source = 'noc'` or `'advisor'`. Pydantic's `extra="ignore"` means extra JS fields won't cause errors but missing required fields will.

### Pitfall 5: Section 5 Qualification Guard Condition

**What goes wrong:** DOC-01 requires Essential Qualifications section always visible with ghost state. Current code is `if (r.qualsVisited) { n++; sections.push(...) }` — the section doesn't appear until the quals step is visited.

**Why it happens:** The current document.jsx was written before DOC-01 finalized the "always show 5 sections" contract.

**How to avoid:** Change the condition to always render Section 5, but render ghost content when `!r.qualsVisited`. Move the `n++` outside the `if` block.

### Pitfall 6: orphan_check Fires Before WD Has Duties

**What goes wrong:** Orphan check called before duties are committed to the WD DB returns `flagged: []` because `wd.duties` is empty — not because the duties are clean, but because they weren't persisted.

**Why it happens:** The current commit flow in app.jsx calls PATCH to persist the record but duties may not be included in the PATCH payload until Phase 18 explicitly adds them.

**How to avoid:** Ensure the duty commit in `app.jsx commit()` includes duties in the PATCH payload (with `WDPatchRequest.duties`). The orphan check endpoint reads from the DB, not from the request body.

---

## Code Examples

### GET /api/noc/{noc_code}/duties — Full Route

```python
# Source: [VERIFIED: pattern from noc_mapping.py + jd_service.py]
@router.get("/noc/{noc_code}/duties")
async def get_noc_duties(noc_code: str) -> dict:
    """Return verbatim Main duties for a confirmed NOC code.

    Reads noc_elements WHERE element_type='Main duties' for the given noc_code.
    Returns source_hash for ProvenanceTag content hash (JD-02).
    Uses get_noc_connection() — NOT get_connection() (different DB files).
    """
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
            {
                "id": row["id"],
                "text": row["element_text"],
                "source_hash": row["source_hash"] or None,
            }
            for row in rows
        ],
    }
```

### Frontend Duty Shape for PATCH Payload

```javascript
// Source: [VERIFIED: components.jsx DutyBuilder + app.jsx commit() WD PATCH pattern]
// In DutyBuilder, when a NOC duty is toggled ON:
const newDuty = {
  id: `noc-${d.id}`,              // d.id = noc_elements.id (integer)
  plain: d.text,                   // verbatim NOC text (shown in duty card)
  text: d.text,                    // verbatim NOC text (rendered in document preview)
  source: 'noc',
  advisor: false,
  provenance_noc_code: cfg.noc_code,
  provenance_section: 'Main duties',
  provenance_hash: d.source_hash || null,
};
// When advisor-added:
const advisorDuty = {
  id: `adv-${Date.now()}`,
  plain: rawText,
  text: refineDuty(rawText),       // polished formal text
  source: 'advisor',
  advisor: true,
  provenance_noc_code: null,
  provenance_section: null,
  provenance_hash: null,
};
```

### Orphan Badge Component (New)

```jsx
// Source: [VERIFIED: UI-SPEC orphan badge CSS spec + document.jsx pattern]
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

Note: `I.warn` needs a warning triangle SVG path added to the `I` object in `data.jsx`. Suggested path: `'<path d="M10 3L18 17H2L10 3z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><line x1="10" y1="9" x2="10" y2="13" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="10" cy="15" r="0.8" fill="currentColor"/>'`

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static `DUTY_SUGGESTIONS` OG-keyed arrays (Phase 15) | FTS5-fetched verbatim NOC duties via `GET /api/noc/{noc_code}/duties` | Phase 18 | Duties are now legally traceable to NOC 2021 source |
| `d.polished` (LLM-refined text via `refineDuty()`) in document preview | `d.text` (verbatim NOC text) for NOC duties | Phase 18 | Satisfies JD-01 verbatim requirement |
| LLM orphan check (`jd_ranking.py` in v1.0) | Deterministic keyword match against `OG_DEFINITIONS[og_code].exclusions` | Phase 18 | No Ollama dependency; faster; consistent with v2.0 deterministic policy |
| `source: "suggested"` in DraftDuty | `source: "noc"` for FTS5 duties | Phase 18 | Reflects actual source type |
| Section 5 (EQ) only appears after `qualsVisited` | Section 5 always renders with ghost state | Phase 18 | Satisfies DOC-01 "5 sections always visible" |

**Deprecated/outdated in this phase:**
- `getDutySuggestions(answers)` / `DUTY_SUGGESTIONS` constant: still present in data.jsx but no longer injected for the duties step. Keep constant for now (Phase 19 may use default suggestions for qual pre-fill patterns). Do not delete.
- `'NOC 2021 · refined'` src pill text: replaced with `'NOC 2021'` in document.jsx.
- Ghost note copy `"Your responsibilities will appear here, formally worded."`: replaced with `"Select duties from the NOC list — they will appear here, verbatim and traceable."` per UI-SPEC.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `noc_elements.source_hash` is populated for all rows in the production NOC DB | Q9 (Content Hash) | If empty, `provenance_hash` will be null — provenance is incomplete but app still functions |
| A2 | `OG_DEFINITIONS["EC"]["exclusions"]` is empty string — orphan check always returns 0 flags for EC positions | Orphan Check Logic | If EC exclusions are added in future, the orphan check will start flagging without a code change needed |
| A3 | The `element_type = 'Main duties'` filter returns all verbatim duty strings for a NOC code with no other element types mixing in | Q1 (FTS5 Query) | Confirmed in noc_mapper.py and jd_service.py — HIGH confidence |
| A4 | Phase 17 is complete (JES scorecard in document.jsx); Phase 18 inherits a working JES scorecard in Section 4 | Dependencies | Phase 17 plans are 4/4 complete per STATE.md; browser UAT pending retest but code changes are committed |

---

## Open Questions (RESOLVED)

1. **Warning triangle icon path**
   - What we know: `I` object in data.jsx has spark, check, user, org, compass, etc. — no warning icon
   - What's unclear: whether a suitable warning SVG path should be added to `data.jsx` or inline in the `OrphanBadge` component
   - RESOLVED: Add `warn` key to `I` in data.jsx; keeps all icons centralized (implemented in 18-03 Task 1)

2. **Confirmed NOC code type in `record`**
   - What we know: `record.confirmed_noc` can be a string (NOC code) or a NOCMatch object `{noc_code, title, teer, ...}` depending on how the noc_confirm step stores it (see app.jsx line 383: `apply: (r, a) => ({ confirmed_noc: a })` where `a` is the full `noc_code` string from `NocConfirmList onChange`)
   - What's unclear: Is `record.confirmed_noc` always a string by Phase 18, or could it be a NOCMatch object? app.jsx line 220 extracts: `typeof confirmedNoc === 'string' ? confirmedNoc : (confirmedNoc.noc_code || '')`
   - RESOLVED: In the cfgOverride for duties, use the same pattern as the OG pipeline trigger: `typeof record.confirmed_noc === 'string' ? record.confirmed_noc : record.confirmed_noc?.noc_code || null` (implemented in 18-04 Task 1)

3. **Orphan check trigger timing in app.jsx**
   - What we know: The orphan check should run "at review time" (JD-04). App.jsx enters review state when all steps are answered OR when `editingReturn` completes.
   - What's unclear: Should orphan check fire automatically on entering review state, or only when the advisor explicitly clicks a "Check duties" action?
   - RESOLVED: Fire automatically when `reviewing` becomes `true` AND `record.duties.length > 0` AND `record.confirmed_og` is set via `useEffect([reviewing, wd_id])`. No manual trigger button needed (implemented in 18-04 Task 1)

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| NOC SQLite DB (`settings.noc_db_path`) | `GET /api/noc/{noc_code}/duties` | ✓ | v1.0 production DB (83MB, confirmed in Phase 14) | — |
| `get_noc_connection()` factory | Duty fetch | ✓ | In `app/db.py` | — |
| `OG_DEFINITIONS` constant | Orphan check | ✓ | `app/data/constants.py` | — |
| Vitest + jsdom | Frontend tests | ✓ | Current (Phase 13 setup) | — |
| pytest + httpx | Backend tests | ✓ | Current (Phase 10 setup) | — |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (backend) | pytest + httpx 0.27.2 + ASGITransport |
| Framework (frontend) | Vitest + jsdom + @testing-library/react |
| Config file (backend) | `v2/backend/pytest.ini` or `pyproject.toml` |
| Config file (frontend) | `v2/frontend/vite.config.js` |
| Quick run (backend) | `cd v2/backend && python -m pytest tests/test_jd_composition.py -x` |
| Full suite (backend) | `cd v2/backend && python -m pytest -x` |
| Quick run (frontend) | `cd v2/frontend && npm run test` |
| Full suite | `cd v2/backend && python -m pytest -x && cd ../frontend && npm run test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| JD-01 | `GET /api/noc/{noc_code}/duties` returns verbatim Main duties | integration | `pytest tests/test_jd_composition.py::test_get_noc_duties_returns_main_duties -x` | ❌ Wave 0 |
| JD-01 | DutyBuilder fetches from API when `noc_code` prop present | unit (frontend) | `npm run test -- document.test.jsx` | ❌ Wave 0 |
| JD-02 | Selected NOC duty carries `provenance_noc_code`, `provenance_section`, `provenance_hash` | unit | `pytest tests/test_jd_composition.py::test_draft_duty_provenance_fields -x` | ❌ Wave 0 |
| JD-03 | Advisor-added duty has `advisor: True`, `source: 'advisor'` | unit | `pytest tests/test_jd_composition.py::test_advisor_duty_source_type -x` | ❌ Wave 0 |
| JD-04 | `POST /api/wd/{id}/orphan_check` returns empty flags for EC (no exclusions) | integration | `pytest tests/test_jd_composition.py::test_orphan_check_ec_no_flags -x` | ❌ Wave 0 |
| JD-04 | Orphan badge rendered in document preview when `d.orphan === true` and `reviewing === true` | unit (frontend) | `npm run test -- document.test.jsx` | ❌ Wave 0 |
| DOC-01 | Section 5 (EQ) renders with ghost state even when quals not visited | unit (frontend) | `npm run test -- document.test.jsx` | ❌ Wave 0 |
| DOC-02 | `buildOverview` no change — existing tests cover | existing | `npm run test -- document.test.jsx` | ✅ existing |
| DOC-03 | Ghost note copy in Section 3 matches UI-SPEC | unit (frontend) | `npm run test -- document.test.jsx` | ❌ Wave 0 |
| DOC-04 | Section header click calls `onEditStep('duties')` in review state | unit (frontend) | `npm run test -- document.test.jsx` | ❌ Wave 0 |
| DOC-05 | Src pill on Section 3 shows "NOC 2021" (not "NOC 2021 · refined") | unit (frontend) | `npm run test -- document.test.jsx` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd v2/backend && python -m pytest tests/test_jd_composition.py -x`
- **Per wave merge:** `cd v2/backend && python -m pytest -x && cd ../frontend && npm run test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `v2/backend/tests/test_jd_composition.py` — covers JD-01..04 backend
- [ ] `noc_duties_db` fixture in conftest.py — lighter than `noc_mapping_db`; creates `noc_elements` with `element_type='Main duties'` rows only
- [ ] Frontend stubs in `document.test.jsx` — covers DOC-01, DOC-03, DOC-04, DOC-05, orphan badge

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user local app; no auth |
| V3 Session Management | no | Single-user local app; no sessions |
| V4 Access Control | no | Single-user local app; no roles |
| V5 Input Validation | yes | `noc_code` path param: min-length 3, parameterized SQL; `wd_id` path param: UUID-like, parameterized SQL |
| V6 Cryptography | no | ProvenanceTag hash uses pre-existing `source_hash` from ingest; not generating new cryptographic material |

### Known Threat Patterns for Phase 18 Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via noc_code in duty fetch | Tampering | Parameterized query `WHERE noc_code = ?` — never string interpolation |
| Fabricated duty text echoed from LLM (v1 pattern) | Tampering | Not applicable — Phase 18 uses no LLM for duties; text is always from DB row |
| Oversized duty list in PATCH | Denial of service | Truncate to first 20 duties server-side in `patch_wd` handler |
| Orphan rationale XSS in frontend | XSS | `d.orphan_rationale` rendered as text content, not `dangerouslySetInnerHTML` — safe |

---

## Sources

### Primary (HIGH confidence)

- [VERIFIED: codebase] `app/services/noc_mapper.py` — FTS5 query pattern, `element_type = 'Main duties'` filter, `get_noc_connection()` usage
- [VERIFIED: codebase] `app/services/jd_service.py` (v1.0) — duty candidate loading pattern, `noc_elements` schema, `source_hash` field
- [VERIFIED: codebase] `app/models/work_description.py`, `app/models/draft_duty.py` — current WD + DraftDuty model shape
- [VERIFIED: codebase] `app/api/wd.py` — `WDPatchRequest` fields, PATCH handler merge logic
- [VERIFIED: codebase] `app/data/constants.py` — `OG_DEFINITIONS`, `ASEC_DISAMBIGUATION`, `QUAL_STANDARDS` structure
- [VERIFIED: codebase] `v2/frontend/src/components.jsx` lines 108-193 — DutyBuilder current props and behavior
- [VERIFIED: codebase] `v2/frontend/src/document.jsx` — Section 3 current render, `buildOverview`, `Sec`, `Ghost`, provenance footer
- [VERIFIED: codebase] `v2/frontend/src/app.jsx` — cfgOverride pattern, commit flow, PATCH payload shape
- [VERIFIED: codebase] `v2/backend/tests/conftest.py` — test infrastructure fixtures, `noc_mapping_db` pattern
- [VERIFIED: codebase] `.planning/phases/18-jd-composition-live-preview/18-UI-SPEC.md` — component inventory, CSS spec, interaction contracts

### Secondary (MEDIUM confidence)

- [CITED: .planning/REQUIREMENTS.md] JD-01..04, DOC-01..05 requirement text — verbatim constraints
- [CITED: .planning/STATE.md] v2.0 decisions — no LLM for orphan check; deterministic classification policy

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project; no new dependencies
- Architecture: HIGH — all building blocks exist; research verified current state of each file
- Pitfalls: HIGH — root-caused from code inspection; not hypothetical
- Test patterns: HIGH — conftest.py fixtures verified; test file locations confirmed

**Research date:** 2026-06-08
**Valid until:** 2026-07-08 (stable codebase; no fast-moving dependencies)
