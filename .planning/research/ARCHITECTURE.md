# Architecture Research — v3.0

**Project:** JD Builder v3.0 — Classification Depth & Document Quality
**Date:** 2026-06-10
**Based on:** v2.0 complete codebase at Phase 20

---

## Existing Architecture (baseline for all six features)

```
v2/backend/app/
├── api/               — FastAPI routers (7 modules: health, wd, noc_mapping,
│                         og_classification, jes_scoring, amendments, export)
├── ai/                — LLM wrappers (jes_scoring.py, noc_ranking.py)
├── data/constants.py  — All authoritative data constants (OG_LEVELS, QUESTION_BANK,
│                         OG_DEFINITIONS, QUAL_STANDARDS, EC_JES_ELEMENTS, etc.)
├── models/            — Pydantic v2 models (WorkDescription, DraftDuty, etc.)
├── services/          — Business logic (export_service, jes_service, noc_mapper,
│                         classification_gate)
├── templates/         — docxtpl .docx binaries (wd_template, poster_template)
└── main.py            — App factory, lifespan schema creation

v2/frontend/src/
├── app.jsx            — Root component; 8 state slices + commit()/exportAs() flow
├── data.jsx           — STEPS, PHASES, OG_LEVELS, QUAL_DEFAULTS, accumulateSignals()
├── conversation.jsx   — Exchange, ActiveQuestion, ReviewState components
├── document.jsx       — DocumentPane, ClassBlock, Sec, OrphanBadge
├── components.jsx     — Icon, initialAnswer, answerValid, NocConfirmList, OgConfirmList
└── styles.css         — Single CSS file; all component styles

SQLite: work_descriptions (id, data JSON), audit_log (id, wd_id, event, detail, created_at)
```

---

## New Components

### Backend: `app/services/audit_service.py`

Purpose: Risk audit engine. Reads the confirmed WD (duties, OG classification, qualifications) and returns structured findings keyed to source authority.

```python
# Public API
def run_risk_audit(wd: WorkDescription, og_code: str) -> list[AuditFinding]

@dataclass
class AuditFinding:
    finding_id: str          # deterministic: f"{section}_{rule_id}"
    section: str             # "duties" | "quals" | "classification" | "overview"
    severity: str            # "high" | "medium" | "low"
    rule_id: str             # e.g. "CA-SCOPE-01", "ERR-PRINCIPLE-07"
    citation: str            # verbatim clause or case name
    citation_source: str     # "CBA" | "Federal Court" | "TBS Directive"
    text: str                # human-readable description of the risk
    status: str              # "open" | "accepted" | "manual_edit" | "skipped"
```

This service is purely deterministic — no LLM. Rules are encoded as check functions against WD fields. Rule corpus is drawn from:
- `data/directive_on_classification.txt` (TBS)
- `data/AI Docs/ERR_Principles_drawn_from_Federal_Court.pdf` (Federal Court principles)
- `data/AI Docs/Wilkonson v. Canada.pdf` (specific case authority)
- Collective agreement scope/exclusion clauses already indexed in v1.0 data

Storage: audit findings are persisted in `audit_log` table with `event='risk_audit_finding'` and a JSON `detail` matching the `AuditFinding` shape. Advisor status updates (`accepted`/`skipped`/`manual_edit`) write a new row with `event='risk_audit_status'` — same deduplication-by-max-id pattern used by amendments.

### Backend: `app/api/audit.py`

```python
POST /api/wd/{id}/audit                     # trigger audit; returns list[AuditFinding]
PATCH /api/wd/{id}/audit/{finding_id}       # update status for one finding
GET  /api/wd/{id}/audit                     # retrieve current findings with status
```

Router pattern mirrors `amendments.py`: thin layer that calls `audit_service`, reads/writes `audit_log`, returns JSON.

### Backend: `app/api/sjd.py`

```python
GET  /api/sjd                   # list all SJDs (id, job_title, og_level, noc_code)
GET  /api/sjd/{id}              # full SJD record
POST /api/wd/{id}/sjd-start     # seed a WD's record fields from an SJD
```

### Backend: `app/data/sjd_library.py`

A module-level constant `SJD_LIBRARY: list[dict]` parsed at import time from the tab-delimited `data/SJD Examples.txt`. Each entry includes: `sjd_number`, `job_title`, `group_level`, `noc_code`, `supervisory`, `organizational_context`, `og_name`.

**Why a module constant and not a SQLite table:** the SJD file has 9 entries now; the whole dataset fits in ~10KB. A SQLite table adds a migration and a startup seed check with no benefit at this volume. If the dataset grows beyond ~100 entries, the same module can be converted to a seeded SQLite table with no API contract change. The `POST /api/wd/{id}/sjd-start` endpoint is the only consumer — the data access path is trivially replaceable.

### Backend: `app/services/writing_guide_service.py`

Purpose: Validates duty statement text against principles extracted from `data/AI Docs/Job Description Writing Guide.docx`. Returns a list of `DutyViolation` objects.

```python
@dataclass
class DutyViolation:
    duty_index: int     # 0-based index in the duties array
    rule_id: str        # e.g. "WG-VERB-01", "WG-PASSIVE-02"
    text: str           # human-readable hint
    severity: str       # "error" | "warning"
```

Rules are encoded as regex or string-pattern checks — no LLM. Examples from the Writing Guide pattern:
- Passive voice detection (`"is responsible for"`, `"will be"`)
- Missing action verb at sentence start
- Duty exceeds 25 words (guideline length cap)
- Vague opener words (`"performs"`, `"assists"`, `"supports"` without specific object)

### Backend: `app/api/writing_guide.py`

```python
POST /api/wd/{id}/validate-duties   # run writing guide check; returns list[DutyViolation]
```

### Backend: `scripts/build_accessible_template.py`

Build script for the new Accessible JD DOCX template. Follows the exact pattern of `scripts/build_wd_template.py`: creates a `DocxTemplate`, declares all variables, saves to `app/templates/accessible_wd_template.docx`, and self-verifies via `get_undeclared_template_variables()`. The new template adds accessibility-required structural elements (proper heading levels, alt-text for any non-text elements, bilingual label rows).

### Frontend: `AuditPanel` component (in `components.jsx`)

Renders the risk audit findings inline within the Review phase. Each finding shows:
- Severity badge (high/medium/low, colour-coded matching existing `.orphan-badge` pattern)
- Section label
- Citation source pill (matching `.src` pill pattern in `.sec__h`)
- Finding text
- Action buttons: Accept / Manual Edit / Skip (call `PATCH /api/wd/{id}/audit/{finding_id}`)

**Placement:** rendered inside the Review phase's left-pane panel (not in the document preview pane), consistent with how `ReviewState` already presents the completion checklist. The review phase left pane is the right surface because audit is an advisor action, not a document section.

---

## Extended Components

### `app/data/constants.py` — Extended for 12 new OG groups

**What changes:**

1. `OG_LEVELS` already has `FB`, `FS` entries. Extend with the remaining 10 groups from `data/Job_evaluation/`: `ED`, `LC`, `LP`, `MT`, `NT`, `NU`, `PO`, `PS`, `SW`, `WP`. Level ranges are read from the JES standard files already present in that directory.

2. `OG_DEFINITIONS` — Add definition dict entries for each of the 12 new groups, sourced from TBS OCHRO (same sourcing pattern as existing AS/FI entries).

3. `NON_EC_TOTALS` — Add approximate total JES point ranges for each new group at each level. For groups whose published JES standard provides explicit point totals (ED, FB, FS, LC, LP, MT, NT, NU, PO, PS, SW, WP text files are present), use those directly. For groups without numeric point scales in the available data files, use `None` as the level value and the scoring path returns a `best_effort: True` flag — this is preferable to a wrong number.

4. `NON_EC_STANDARD_NAMES` (both the copy in `constants.py` and the module-level copy in `export_service.py`) — Add an entry per new group. These two copies are an acknowledged drift risk (Phase 20 code review advisory open item); a content-parity test should be added.

5. `QUAL_STANDARDS` — Add a qualification standard dict entry per new group (or point to the relevant collective agreement standard).

**QUESTION_BANK extension strategy — keeping it maintainable:**

Do NOT add 12 new answer options to existing questions. The `accumulateSignals()` function already tallies `og_candidates` lists — adding more signal options is additive. Instead:

- Add a fifth question: `"work_type_sector"` — "What sector or specialty domain does this work primarily fall under?" with answer options that each map to a cluster of new OG groups (e.g. "Law and justice" → `["LC", "LP"]`; "Health and social services" → `["NT", "NU", "SW", "WP"]`; "Science and environment" → `["MT", "PS", "PO"]`; "Education and training" → `["ED"]`; "Border and operations" → `["FB"]`; "Foreign affairs" → `["FS"]`; "None of the above" → no signals, falls through to existing EC/AS/IT/FI path).
- Add a sixth question, `"work_type_disambiguate"`, conditional on the sector answer, that disambiguates within the cluster (e.g. after "Law and justice": "Is this a management/advisory/litigation support role (LC) or a legal practitioner/litigator role (LP)?").
- New questions use `phase_slot: "work_type"` so they slot into the existing Phase 1 (Work Type) without a STEPS restructure.
- Practical size: 8 total QUESTION_BANK entries at ~80 lines each = ~640 lines. Remains in one file. If it exceeds ~1000 lines, split into `QUESTION_BANK_CORE` (existing 4) and `QUESTION_BANK_EXTENDED` (new) and merge at import with list concatenation.

### `app/services/export_service.py` — New template function

1. Add `generate_accessible_wd_docx(wd_id, db_path)` — same pattern as `generate_wd_docx` but using `accessible_wd_template.docx`. The `_build_wd_context()` helper is reused without change; only the template path differs.
2. Extend `NON_EC_STANDARD_NAMES` (module-level dict) to cover all 12 new groups.

### `app/api/export.py` — New route

Add `POST /api/wd/{id}/export/accessible-docx` alongside the existing three export routes. No structural change — same response pattern.

### `app/api/__init__.py` — Three new router imports

```python
from . import audit, sjd, writing_guide
api_router.include_router(audit.router)
api_router.include_router(sjd.router)
api_router.include_router(writing_guide.router)
```

### `v2/frontend/src/data.jsx` — Extended STEPS and new constants

1. Extend `QUAL_DEFAULTS` to cover the 12 new OG groups, mirroring backend `QUAL_STANDARDS`.
2. Add new STEPS entries for the sector-disambiguation questions.
3. SJD browser is NOT a STEPS entry — it is a collapsible panel in `.convo__head`, so it does not block the main flow.

### `v2/frontend/src/app.jsx` — New state slices

- `auditFindings: []` — populated from `POST /api/wd/{id}/audit` response.
- `dutyViolations: []` — populated from `POST /api/wd/{id}/validate-duties` response after duties commit.
- `sjdList: []` — populated once from `GET /api/sjd` on mount (or lazily on panel open).

### `v2/frontend/src/document.jsx` — Audit summary row + writing hints

1. `DocumentPane` receives optional `auditFindings` prop. When present and `reviewing === true`, renders an audit summary above the provenance footer: "N risk findings — N open".
2. Individual duty items (`doc-duty` li) receive an optional inline `.duty-hint` span rendered when `dutyViolations` has an entry for that duty index and `showWritingHints` is true. Display-only; does not block progression or export.

### `v2/frontend/src/styles.css` — Preview fix + new UI classes

**Preview white-page extension fix:**

The `.doc-scroll` flex container currently has no `align-items` declaration, which defaults to `stretch`. This causes `.doc` to stretch to fill the full scroll container height when content is shorter than the viewport, and it causes the paper to not grow beyond its content because the flex item height is set by the container. The fix:

```css
/* Add to existing .doc-scroll rule: */
.doc-scroll {
  align-items: flex-start;  /* prevents .doc from stretching to container height */
}
```

This is a one-line addition to the existing `.doc-scroll` rule block. The paper will now grow with its content and not overflow into the grey background at any document length.

Add at end of file in a `/* v3.0 */` block:
- `.audit-finding`, `.audit-finding--high`, `.audit-finding--medium`, `.audit-finding--low` — severity badge styles (use existing orphan-badge and gold/green/accent palette variables).
- `.duty-hint` — small italic hint below duty text, accent-line left border.
- `.sjd-picker`, `.sjd-card` — SJD browser panel and card styles.

---

## Data Flow Changes

### New API Routes

| Route | Method | Service | Description |
|-------|--------|---------|-------------|
| `GET /api/sjd` | GET | `sjd_library.SJD_LIBRARY` | List SJD index |
| `GET /api/sjd/{id}` | GET | `sjd_library.SJD_LIBRARY` | Single SJD record |
| `POST /api/wd/{id}/sjd-start` | POST | `sjd.py` (thin) | Seed WD record fields from SJD |
| `GET /api/wd/{id}/audit` | GET | `audit_service` | Retrieve findings with status |
| `POST /api/wd/{id}/audit` | POST | `audit_service` | Trigger fresh audit run |
| `PATCH /api/wd/{id}/audit/{finding_id}` | PATCH | `audit_service` | Update finding status |
| `POST /api/wd/{id}/validate-duties` | POST | `writing_guide_service` | Check duties against guide |
| `POST /api/wd/{id}/export/accessible-docx` | POST | `export_service` | Accessible JD DOCX |

### New Data Models

**`AuditFinding`** (Pydantic model in `app/models/audit_finding.py`):
```python
class AuditFinding(BaseModel):
    finding_id: str
    section: str
    severity: Literal["high", "medium", "low"]
    rule_id: str
    citation: str
    citation_source: str
    text: str
    status: Literal["open", "accepted", "manual_edit", "skipped"] = "open"
```

Stored in `audit_log` as JSON `detail` with `event='risk_audit_finding'`; status updates stored with `event='risk_audit_status'`. No schema migration required.

**`DutyViolation`** (plain dataclass in `writing_guide_service.py`; not persisted):
```python
@dataclass
class DutyViolation:
    duty_index: int
    rule_id: str
    text: str
    severity: Literal["error", "warning"]
```

**`SJDRecord`** (TypedDict in `sjd_library.py`; not persisted):
```python
class SJDRecord(TypedDict):
    id: str                   # sjd_number
    job_title: str
    group_level: str          # e.g. "AS-01"
    og_code: str              # parsed from group_level prefix
    noc_code: str
    supervisory: bool
    organizational_context: str
```

### State Flow: SJD Pre-fill

```
User opens SJD panel (frontend, convo__head)
  → GET /api/sjd  (index, 9 records)
  → User selects SJD card
  → POST /api/wd/{id}/sjd-start {sjd_id}
  → Backend seeds WD record: {title, group_level, noc_code, organizational_context}
  → Response: patched WorkDescription
  → Frontend updates record state, triggers flash on affected fields
```

### State Flow: Risk Audit

```
User clicks "Run Risk Audit" in ReviewState (left pane)
  → POST /api/wd/{id}/audit
  → audit_service.run_risk_audit(wd, og_code) — deterministic rules, ~milliseconds
  → Each finding written to audit_log (event='risk_audit_finding')
  → Response: {findings: [...]}
  → Frontend stores in auditFindings state slice
  → AuditPanel renders below ReviewState checklist
  → User clicks Accept/Skip → PATCH /api/wd/{id}/audit/{finding_id}
  → New audit_log row (event='risk_audit_status', detail={finding_id, status})
```

### State Flow: Writing Guide Validation

```
User completes duties commit
  → commit() fires normally (WD persisted)
  → POST /api/wd/{id}/validate-duties fires in parallel
  → writing_guide_service.check_duties(duties) — regex rules, ~microseconds
  → Response: {violations: [...]}
  → Frontend stores in dutyViolations state slice
  → document.jsx renders .duty-hint below flagged duties (display-only)
  → No blocking of progression; violations are advisory
```

### OG Classification Data Flow Change

Adding 12 new OG groups extends but does not change the data flow. `accumulateSignals()` already handles arbitrary `og_candidates` lists; `/api/og/classify` already ranks by signal tally with no group hardcoding; `OgConfirmList` renders the top-3 candidates regardless of which groups they are.

---

## Suggested Build Order

### Phase 21: OG Expansion (data foundation)

Build first because all other features that touch classification need the new OG data constants populated. Additive change, low risk, existing test patterns apply directly.

**Deliverables:** 12 new OG groups in `OG_LEVELS`, `OG_DEFINITIONS`, `NON_EC_TOTALS`, `NON_EC_STANDARD_NAMES`, `QUAL_STANDARDS` (backend). New sector-disambiguation questions in `QUESTION_BANK` (entries 5-8). Matching entries in frontend `QUAL_DEFAULTS`. A `test_qual_parity.py` to enforce content alignment between backend `QUAL_STANDARDS` and frontend `QUAL_DEFAULTS`.

### Phase 22: SJD Library

Self-contained: new constant module + 3 new routes + frontend panel. Does not depend on Phase 21 data (existing SJD examples are AS/EC/IT groups). Unblocks the Writing Guide phase by giving the advisor a realistic starting duty set to validate.

**Deliverables:** `sjd_library.py` (parses `SJD Examples.txt` at import), `api/sjd.py`, SJD picker collapsible panel in `conversation.jsx` header, `sjd-start` WD seeding endpoint.

### Phase 23: Writing Guide Integration

Depends on a populated WD (duties present). Writing guide validation is purely service+API+frontend rendering with no template or data changes. Produces duty hints that are distinct from CBA compliance audit findings (different authority, different signal).

**Deliverables:** `writing_guide_service.py`, `api/writing_guide.py`, QUESTION_BANK question-text updates (reshape questions to align with guide verb-first principle), `.duty-hint` CSS + `document.jsx` inline hint rendering, `dutyViolations` state slice in `app.jsx`.

### Phase 24: Risk Audit

Most research-intensive feature — requires reading and encoding rules from ERR Principles PDF and CA clauses. Placed fourth to give maximum time for rule corpus authoring. Depends on a complete WD with confirmed classification, duties, and quals.

**Deliverables:** `audit_service.py`, `app/models/audit_finding.py`, `api/audit.py`, `AuditPanel` component in `components.jsx`, audit CSS classes in `styles.css`, `PATCH` status update flow, `auditFindings` state slice in `app.jsx`.

### Phase 25: Accessible Template + Preview Fix

Template work and CSS are independent of all other features. The CSS fix is one line — deliver it in the first commit of this phase regardless of template progress.

**Deliverables:** `app/templates/accessible_wd_template.docx`, `scripts/build_accessible_template.py`, `POST /api/wd/{id}/export/accessible-docx` route and `generate_accessible_wd_docx` function, `align-items: flex-start` fix on `.doc-scroll`.

### Dependency graph

```
Phase 21 (OG data)
  └─► Phase 22 (SJD — independent, but benefits from expanded group coverage)
        └─► Phase 23 (Writing Guide — needs duties to validate)
              └─► Phase 24 (Risk Audit — needs complete WD)

Phase 25 (Template + CSS — independent of 22-24, can run in parallel)
```

---

## Integration Points: New vs Modified

| Feature | New files | Modified files |
|---------|-----------|----------------|
| SJD Library | `app/data/sjd_library.py`, `app/api/sjd.py` | `app/api/__init__.py`, `app.jsx` (state), `conversation.jsx` (panel) |
| Accessible Template | `scripts/build_accessible_template.py`, `app/templates/accessible_wd_template.docx` | `export_service.py` (new fn), `app/api/export.py` (new route), `app.jsx` (exportAs case), `app/api/__init__.py` |
| Writing Guide | `app/services/writing_guide_service.py`, `app/api/writing_guide.py` | `app/api/__init__.py`, `app.jsx` (state), `document.jsx` (hints), `data.jsx` (question text), `styles.css` |
| Risk Audit | `app/services/audit_service.py`, `app/models/audit_finding.py`, `app/api/audit.py` | `app/api/__init__.py`, `app.jsx` (state), `document.jsx` (summary row), `components.jsx` (AuditPanel), `styles.css` |
| OG Expansion | — | `app/data/constants.py`, `app/services/export_service.py` (NON_EC_STANDARD_NAMES), `v2/frontend/src/data.jsx` |
| Preview fix | — | `styles.css` (one line) |

---

## Architectural Invariants to Preserve

1. **No schema migration required.** All new storage uses the existing `audit_log` table with new event names. `work_descriptions.data` JSON absorbs new WD fields via Pydantic optional fields.

2. **Classification gate is not widened.** `require_og_confirmed` in `classification_gate.py` stays as-is. Audit, writing guide, and SJD seeding are advisory layers — they do not gate export.

3. **QUESTION_BANK OG code constraint (QUES-02).** New questions must not surface OG codes in `question`, `helper`, or `options[].label`. All 12 new groups are signalled only via `signals.og_candidates`.

4. **All service functions remain synchronous or use `asyncio.to_thread`.** `audit_service.run_risk_audit` and `writing_guide_service.check_duties` are synchronous rule engines — sub-millisecond, fine to call inline from an async route handler without `to_thread`.

5. **docxtpl template binaries are reproducible.** Every new `.docx` template must have a corresponding `build_*.py` script that recreates it and self-verifies via `get_undeclared_template_variables()`.

6. **Frontend state remains in `app.jsx` local state (no Redux/Zustand).** New state slices (`auditFindings`, `dutyViolations`, `sjdList`) follow the existing `useState` pattern. If any slice exceeds ~3 levels of prop-passing, consider a `useContext` wrapper — but do not introduce a store library.
