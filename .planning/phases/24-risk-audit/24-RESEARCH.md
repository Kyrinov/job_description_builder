# Phase 24: Risk Audit — Research

**Researched:** 2026-06-15
**Domain:** Deterministic compliance audit — CBA clause matching + Federal Court ERR principles + amendment panel integration
**Confidence:** HIGH

---

## Summary

Phase 24 adds a manually-triggered compliance audit to the Review phase. The advisor clicks "Run compliance audit", which fires `POST /api/wd/{id}/audit`. The backend executes deterministic rule matching against the confirmed OG's CBA JSON (exclusion, scope, application articles only) and a curated set of Federal Court ERR principles encoded as Python rules. Each finding is stored in `audit_log` with `event='risk_audit_finding'`. The advisor then acts on every finding — Accept / Manual Edit / Skip — each decision written to `audit_log` with `event='risk_audit_decision'`. Manual Edit opens the existing Phase 19 amendment panel (`handleAmendToggle`/`handleAmendSave`) for the flagged section.

The two primary constraints that shape implementation complexity are: (1) false negatives are preferred over false positives in this legal domain, so the **two-signal rule** (verbatim term match AND section relevance) must gate every CBA finding; and (2) audit findings and amendment notes must share the same section key (`id`, `ov`, `du`, `cls`, `q`, `drf`) so they co-appear in the DOCX amendment appendix.

**Primary recommendation:** Model Phase 24 precisely on the Phase 23 pattern — a new `risk_auditor.py` service module, a `POST /api/wd/{id}/audit` endpoint in `wd.py`, a new `audit_log` event type, and new React state in `app.jsx` — with the `ReviewState` component in `conversation.jsx` extended to render the audit button and findings panel.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUDIT-01 | "Run compliance audit" button in Review phase; `POST /api/wd/{id}/audit`; findings stored with `event='risk_audit_finding'`; re-run replaces previous findings in UI (deduplication by max-id per section) | Endpoint pattern from `validate-duties`; audit_log from `amendments.py`; Review phase from `ReviewState` in `conversation.jsx` |
| AUDIT-02 | CBA matching against confirmed OG's JSON file (exclusion/scope/application articles); two-signal requirement (verbatim term match + section relevance); false negatives preferred | CBA JSON structure verified: sections array with `title` and `text` fields; OG-to-directory mapping established |
| AUDIT-03 | Federal Court ERR principles — completeness of duty coverage, generic vs. specific duty adequacy — encoded as deterministic rules from `data/AI Docs/ERR_Principles_drawn_from_Federal_Court.pdf` and `Wilkonson v. Canada.pdf` | Both PDFs verified present; specific checkable principles identified (duty count threshold, specificity check) |
| AUDIT-04 | Each finding: section, severity (advisory/warning), verbatim CBA clause or court citation, plain-language recommendation; Accept/Manual Edit/Skip decisions written to `audit_log` with `event='risk_audit_decision'` | audit_log schema confirmed; `detail` column stores JSON with arbitrary structure |
| AUDIT-05 | Manual Edit opens Phase 19 amendment panel for flagged section; amendment note and audit finding share same section key | `handleAmendToggle`/`handleAmendSave` already in `app.jsx`; section keys `{id, ov, du, cls, q, drf}` confirmed in `amendments.py` |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Run audit button + trigger | Browser/Frontend | — | User-initiated only; never automatic |
| Audit rule execution | API/Backend (`risk_auditor.py`) | — | Deterministic Python; no LLM; reads CBA JSON from disk |
| CBA JSON loading | API/Backend | — | Static files on disk; loaded once at audit time |
| ERR principles rules | API/Backend | — | Encoded as Python constants + predicate functions |
| Findings storage | Database (`audit_log`) | — | Same table as amendments and other events |
| Findings display + decision UI | Browser/Frontend | — | React state in `app.jsx`; rendered in `ReviewState` |
| Amendment panel linkage | Browser/Frontend | — | `handleAmendToggle` already exists; called from finding row |
| Deduplication (re-run) | API/Backend | Frontend | Backend: dedup by max-id per rule; Frontend: replace state on re-run |

---

## Standard Stack

### Core (all existing — no new dependencies needed)
| Component | Location | Purpose |
|-----------|----------|---------|
| FastAPI `APIRouter` | `app/api/wd.py` | Add `POST /api/wd/{id}/audit` endpoint (same file as `validate-duties`) |
| SQLite `audit_log` table | `app/db.py` | Store `risk_audit_finding` and `risk_audit_decision` events |
| Python `json` stdlib | `app/services/risk_auditor.py` | Load CBA JSON from `data/agreements/{DIR}/` |
| React state + `fetch` | `app.jsx` | `auditFindings` state, button handler, decision handlers |
| `ReviewState` component | `conversation.jsx` | Render audit button and findings panel |

### New Files Required
| File | Purpose |
|------|---------|
| `v2/backend/app/services/risk_auditor.py` | All audit logic — CBA matching + ERR rules; mirrors `duty_validator.py` pattern |
| `v2/backend/tests/test_risk_audit.py` | Wave 0 stubs then GREEN implementations; mirrors `test_writing_guide.py` |

**No new pip packages required.** [VERIFIED: codebase inspection — all dependencies already present]

---

## Architecture Patterns

### System Architecture Diagram

```
[Review Phase — conversation.jsx ReviewState]
         |
    [Run Audit button click]
         |
         v
[app.jsx handleRunAudit()]
    POST /api/wd/{id}/audit
         |
         v
[app/api/wd.py — audit endpoint]
    1. Load WD from DB
    2. Resolve OG code -> CBA directory
    3. Load CBA JSON from data/agreements/{DIR}/
    4. Call risk_auditor.run_audit(wd, cba_data)
         |
         v
[app/services/risk_auditor.py]
    run_audit(wd, cba_data) ->
      for each CBA rule:
        signal_1 = verbatim_term_match(wd_text, cba_clause)
        signal_2 = section_relevant(wd_section, cba_article_type)
        if signal_1 AND signal_2: findings.append(...)
      for each ERR rule:
        if rule_predicate(wd): findings.append(...)
      return findings list
         |
         v
[audit_log INSERT — one row per finding]
    event='risk_audit_finding'
    detail={rule_id, section, severity, citation, recommendation}
         |
         v
[Response: {wd_id, findings: [...]}]
         |
         v
[app.jsx setAuditFindings(data.findings)]
         |
         v
[ReviewState renders findings panel]
    For each finding:
      [Accept] -> POST /api/wd/{id}/audit/decide
      [Manual Edit] -> handleAmendToggle(finding.section)
      [Skip] -> POST /api/wd/{id}/audit/decide
```

### Recommended Project Structure (additions only)
```
v2/backend/
├── app/
│   ├── api/
│   │   └── wd.py            # Add POST /api/wd/{id}/audit here (AUDIT-01)
│   └── services/
│       ├── duty_validator.py # Existing — Phase 23 pattern to copy
│       └── risk_auditor.py  # NEW — Phase 24: CBA + ERR rules (AUDIT-02/03)
└── tests/
    └── test_risk_audit.py   # NEW — Wave 0 stubs (mirrors test_writing_guide.py)
```

---

## CBA JSON Data Structure

[VERIFIED: direct file inspection of `data/agreements/EC/EC_full.json` and `data/agreements/PA/PA_full.json`]

```python
# Top-level keys in every {OG}_full.json:
{
  "title": str,           # Agreement title
  "url": str,             # TBS source URL
  "preamble": str,
  "sections": [           # List of article objects
    {
      "id": str,          # Often empty string — do NOT use as primary key
      "title": str,       # e.g. "Article 3: application"
      "text": str,        # Full text of the article (verbatim, markdown-light)
      "tables": list      # Usually empty
    }
  ],
  "tables": list,
  "index_record": {       # Agreement metadata
    "abbreviation": str,  # e.g. "(EC)"
    "group": str,
    "group_subgroup": str,
    "code": str,          # e.g. "231"
    "union": str,
    "signing_date": str,
    "expiry_date": str,
    "url": str
  }
}
```

**Important:** The `id` field on sections is an empty string in the EC and PA agreements inspected. Use `title` as the identifier. Match by `title.lower()` substring against article type keywords.

**Audit-relevant article types to target (AUDIT-02):**
- Purpose and scope: "article 1" / "purpose and scope"
- Application: "article 3" / "application"
- Recognition / bargaining unit coverage: "article 7" / "recognition"
- Statement of duties: "article 34" / "statement of duties" (EC-specific — confirms CBA right to current and complete JD)

**EC Article 34 verbatim text** (the key CBA obligation for audit purposes):
> "34.01 Upon written request, an employee shall be provided with a complete and current statement of the duties and responsibilities of his or her position, including the classification level and, where applicable, the point rating allotted by factor to his or her position, and an organization chart depicting the position's place in the organization."

**PA Article (statement of duties equivalent)** — PA combines multiple OG groups (AS, CR, PM, WP); its application article defines which groups are covered. Relevant for any WD where `confirmed_og` is AS, CR, PM, or WP.

---

## OG Code to Agreement Directory Mapping

[VERIFIED: `data/agreements/` directory listing + `index_record` fields inspected]

```python
# Required constant for risk_auditor.py
OG_AGREEMENT_DIR: dict[str, str] = {
    "EC":  "EC",
    "IT":  "IT_CS",
    "AS":  "PA",
    "FI":  "CT_FI",
    "CR":  "PA",
    "PM":  "PA",
    "WP":  "PA",
    "GT":  "TC",
    "EL":  "EL",
    "FB":  "FB",
    "FS":  "FS",
    "AI":  "AI",
    "AU":  "CT_FI",
    "LC":  "LP_LA",
    "LP":  "LP_LA",
    "MT":  "SP_AP",
    "NU":  "SH",
    "PS":  "SH",
    "SW":  "SH",
    "PO":  "PO",
    # NT and ED have no confirmed agreement directory match — return no CBA findings
    # These OG groups still receive ERR principle checks
}
```

**NT and ED mapping gap:** NR covers Architecture/Engineering (EN), not NT. AO covers Aircraft Operations. No agreement directory in `data/agreements/` cleanly covers NT (Nutrition/Dietetics) or ED (Education). [ASSUMED: NT maps to SH or RM; ED may have no current TBS collective agreement JSON. The audit should return zero CBA findings for these groups rather than raising an error. Planner should add a `NT` and `ED` gap note.]

---

## audit_log Structure

[VERIFIED: `app/db.py` schema DDL + `app/api/amendments.py` + `app/api/wd.py`]

```sql
-- Existing schema (no schema change needed for Phase 24)
CREATE TABLE audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    wd_id       TEXT NOT NULL,
    event       TEXT NOT NULL,
    actor       TEXT NOT NULL,
    detail      TEXT,           -- JSON string
    created_at  TEXT NOT NULL
);
```

**Existing event types in use:**
- `manager_amendment` — Phase 19 amendment notes
- (other events from earlier phases — step commits, export events)

**New event types for Phase 24:**
- `risk_audit_finding` — one row per finding produced by `POST /api/wd/{id}/audit`
- `risk_audit_decision` — one row per advisor decision (Accept/Manual Edit/Skip)

**Proposed `detail` JSON shapes:**

```python
# risk_audit_finding detail
{
    "rule_id": "CBA_STATEMENT_OF_DUTIES",   # stable string identifier
    "section": "du",                          # JD section key (matches amendment keys)
    "severity": "advisory",                   # "advisory" | "warning"
    "citation": "EC Article 34.01: ...",      # verbatim CBA clause or court citation
    "recommendation": "Verify that ...",      # plain-language guidance
    "og_code": "EC"                           # for traceability
}

# risk_audit_decision detail
{
    "rule_id": "CBA_STATEMENT_OF_DUTIES",   # links back to the finding
    "section": "du",
    "decision": "accept",                     # "accept" | "manual_edit" | "skip"
    "finding_audit_log_id": 42               # id of the risk_audit_finding row
}
```

**Deduplication on re-run (AUDIT-01):** Re-running the audit inserts new `risk_audit_finding` rows. The frontend replaces `auditFindings` state entirely from the response. To avoid accumulation, the endpoint should first DELETE existing `risk_audit_finding` rows for the WD before inserting new ones — or the endpoint returns only the current run's findings (max-id dedup). The simpler approach is to DELETE then INSERT within the endpoint, matching the "re-run replaces" requirement exactly.

---

## ERR Principles — Deterministic Rules

[VERIFIED: `data/AI Docs/ERR_Principles_drawn_from_Federal_Court.pdf` read directly]

The PDF contains principles from Federal Court, FCA, and FPSLREB decisions. The AUDIT-03 requirement specifies a **curated subset** covering two dimensions:

### ERR Rule 1: Duty Coverage Completeness (Cushnie principle)
**Source:** ERR PDF, "Job content / Statement of duties" section:
> "If a duty is not contained in a generic or a specific job description, it must be added in order to meet the requirements of the collective agreement for a complete and current Statement of Work. (FPSLREB: Cushnie)"

**Deterministic check:** Does the WD have at least 3 duties? (A minimal threshold — zero or 1 duty almost certainly means incomplete coverage.) This is a configurable constant, not LLM inference.

```python
# ERR_RULE_DUTY_COUNT
def check_duty_coverage(wd) -> AuditFinding | None:
    duties = wd.duties or []
    if len(duties) < ERR_MIN_DUTY_COUNT:  # constant = 3
        return AuditFinding(
            rule_id="ERR_DUTY_COVERAGE",
            section="du",
            severity="warning",
            citation="FPSLREB: Cushnie — 'If a duty is not contained in a job description, it must be added...'",
            recommendation=f"This WD has {len(duties)} duties. Most positions require at least 3 to adequately describe the work.",
        )
    return None
```

### ERR Rule 2: Generic vs. Specific Duty Adequacy (Dervin/Trépanier principle)
**Source:** ERR PDF:
> "Although the use of generic job descriptions can be an acceptable way for the employer to satisfy its obligation under the collective agreement, the job description needs to reflect the duties of the employees. It can fail to do so if the terms used do not accurately reflect the depth or scope of the grievor's work. (FPSLREB: Dervin)"

**Deterministic check:** Are any duties excessively short (fewer than 8 words after trimming)? This overlaps with WG-01 WORD_COUNT but serves a different legal purpose here. The finding fires only if 50% or more of duties are short — a threshold that indicates systematic underspecification.

```python
# ERR_RULE_DUTY_SPECIFICITY
def check_duty_specificity(wd) -> AuditFinding | None:
    duties = wd.duties or []
    if not duties:
        return None  # already caught by coverage rule
    short_count = sum(1 for d in duties if len(d.text.split()) < 8)
    if short_count / len(duties) >= ERR_SPECIFICITY_THRESHOLD:  # constant = 0.5
        return AuditFinding(
            rule_id="ERR_DUTY_SPECIFICITY",
            section="du",
            severity="advisory",
            citation="FPSLREB: Dervin — 'The job description needs to reflect the duties of the employees.'",
            recommendation="More than half the duties are very short. Review whether they adequately describe the depth and scope of the work.",
        )
    return None
```

**Wilkinson v. Canada (2020 FCA 223)** — The Wilkinson case (Federal Court of Appeal, Docket A-79-19) concerns the reasonableness of a Deputy Head's decision to reject a Classification Grievance Committee recommendation. Key principle for Phase 24: the Deputy Head's decision must be "intelligible, transparent and justified" (Wilkinson I). This applies to the **audit trail** rather than to a specific JD check — it reinforces the requirement that every advisor decision be logged. This does not encode as a separate check rule; it is the rationale for AUDIT-04's mandatory decision logging.

### Zero-finding guarantee (AUDIT-01 success criterion 5)
A minimal well-formed WD that:
- Has 3+ duties each 8+ words long
- Has a confirmed OG with no matching exclusion/scope terms in JD text
- Has no statement-of-duties article conflict

...must return zero findings. The two-signal rule achieves this: if there are no verbatim CBA term matches in the JD text, no CBA finding fires, regardless of which articles are targeted.

---

## Two-Signal Rule Implementation (AUDIT-02)

[ASSUMED: specific signal design based on requirement language + CBA JSON structure. Risk if wrong: false positives in production.]

The requirement states: "two-signal requirement before any finding fires (verbatim term match + section relevance)."

**Interpretation:**
- Signal 1 (verbatim term match): A term from the CBA article's text appears verbatim in the WD's relevant section text.
- Signal 2 (section relevance): The CBA article type (scope/exclusion/application) is relevant to the JD section being checked.

```python
def cba_two_signal_check(
    jd_section_text: str,
    cba_article_text: str,
    article_type: str,  # "scope" | "exclusion" | "application"
    jd_section_key: str,  # "du" | "ov" | "cls" | etc.
) -> bool:
    """Returns True only if BOTH signals are present."""
    # Signal 1: extract significant terms from CBA article (words > 4 chars, not stopwords)
    terms = extract_significant_terms(cba_article_text)
    signal_1 = any(term.lower() in jd_section_text.lower() for term in terms)

    # Signal 2: article type is relevant to this JD section
    SECTION_RELEVANCE = {
        "scope": {"du", "ov", "cls"},
        "exclusion": {"du"},
        "application": {"du", "cls"},
    }
    signal_2 = jd_section_key in SECTION_RELEVANCE.get(article_type, set())

    return signal_1 and signal_2
```

**Conservative design:** Extract only proper nouns and domain-specific terms from CBA articles, not common words. This is the primary false-positive suppression mechanism.

---

## Amendment Panel Integration (AUDIT-05)

[VERIFIED: `app.jsx` lines 572-626; `app/api/amendments.py`]

The Phase 19 amendment panel already exists and is fully operational. Key implementation facts:

**Section keys (Literal type in `amendments.py`):**
```python
Literal['id', 'ov', 'du', 'cls', 'q', 'drf']
```
These are the only valid section keys. Audit findings MUST map to one of these keys. Mapping:
- `du` — Key Responsibilities (duties) — most CBA findings
- `ov` — Position Overview — generic/scope findings
- `cls` — Classification & Evaluation — classification-related CBA concerns
- `id` — Position Identification
- `q` — Essential Qualifications
- `drf` — Defence Results Linkage

**How Manual Edit works in existing code:**
```javascript
// app.jsx — existing handler
function handleAmendToggle(sectionKey, textOrNull) { ... }
function handleAmendSave(sectionKey, text) { ... }
```
The audit finding's "Manual Edit" action simply calls `handleAmendToggle(finding.section)`. No new backend endpoint needed — `POST /api/wd/{id}/amendments` already handles the save.

**Co-appearance requirement:** Audit findings and amendment notes share the same `section` key. The DOCX amendment appendix (Phase 25 scope, deferred) will query both `risk_audit_finding` and `manager_amendment` rows grouped by section. No implementation needed in Phase 24 — just ensure the section key on findings matches.

---

## Review Phase Frontend Pattern

[VERIFIED: `conversation.jsx`, `app.jsx`]

`ReviewState` in `conversation.jsx` is the component rendered when `reviewing === true` in `app.jsx`. It currently renders:
- Checklist of completion items
- Export buttons (DOCX, PDF, Copy)
- Restart button

**Phase 24 adds to `ReviewState`:**
1. A "Run compliance audit" button that calls a prop `onRunAudit` (similar to `onExport`)
2. A findings panel (hidden until audit runs) that renders each finding with 3 decision buttons

**`ReviewState` props to add:**
```javascript
// conversation.jsx
function ReviewState({ record, cls, onExport, onRestart, amendmentNotes,
                       auditFindings, onRunAudit, onAuditDecide }) {
```

**New state in `app.jsx`:**
```javascript
const [auditFindings, setAuditFindings] = useState([]);  // [] until audit runs
const [auditRunning, setAuditRunning] = useState(false);

function handleRunAudit() {
    if (!wd_id) return;
    setAuditRunning(true);
    fetch(`/api/wd/${wd_id}/audit`, { method: 'POST' })
        .then(r => r.ok ? r.json() : Promise.reject(r.status))
        .then(data => {
            setAuditFindings(data.findings || []);
            setAuditRunning(false);
        })
        .catch(() => { setAuditRunning(false); });
}

function handleAuditDecide(ruleId, section, decision) {
    if (!wd_id) return;
    fetch(`/api/wd/${wd_id}/audit/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rule_id: ruleId, section, decision }),
    }).catch(() => {});
    // If manual_edit: also open amendment panel
    if (decision === 'manual_edit') {
        handleAmendToggle(section);
    }
}
```

---

## Backend Endpoint Pattern

[VERIFIED: `validate-duties` endpoint in `app/api/wd.py` as template]

```python
# app/api/wd.py — new endpoint

@router.post("/wd/{wd_id}/audit")
async def run_compliance_audit(wd_id: str) -> dict:
    """AUDIT-01: Deterministic CBA + ERR compliance audit. Manual trigger only.

    Deletes previous risk_audit_finding rows for this WD, then runs the audit
    and inserts new rows. Returns findings to frontend for UI rendering.
    """
    from app.services.risk_auditor import run_audit, load_cba_data
    import json

    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Work description not found")
        wd = WorkDescription.model_validate_json(row["data"])

        og_code = (
            wd.confirmed_og.get("og_code")
            if isinstance(wd.confirmed_og, dict)
            else wd.confirmed_og or ""
        )

        cba_data = load_cba_data(og_code)  # returns None if no agreement dir
        findings = run_audit(wd, cba_data)

        now = datetime.now(timezone.utc)
        # Delete previous findings for this WD
        con.execute(
            "DELETE FROM audit_log WHERE wd_id = ? AND event = 'risk_audit_finding'",
            (wd_id,),
        )
        # Insert new findings
        for finding in findings:
            con.execute(
                "INSERT INTO audit_log (wd_id, event, actor, detail, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (wd_id, "risk_audit_finding", "system",
                 json.dumps(finding), now.isoformat()),
            )
        con.commit()
    finally:
        con.close()
    return {"wd_id": wd_id, "findings": findings}


@router.post("/wd/{wd_id}/audit/decide", status_code=201)
async def audit_decide(wd_id: str, body: AuditDecideRequest) -> dict:
    """AUDIT-04: Log advisor Accept/Manual Edit/Skip decision."""
```

**Decision endpoint also in `wd.py`** — keeps all WD-scoped endpoints together, matching the `validate-duties`, `orphan_check`, `sjd-start` precedent.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CBA text parsing | Custom PDF parser | Use existing `{OG}_full.json` | JSON files already exist, fully structured |
| Agreement metadata lookup | Scraping TBS website | `OG_AGREEMENT_DIR` constant | Static data, verified in this research |
| ERR principle source | LLM inference | Hardcoded rule predicates | Requirement explicitly states deterministic rules, not LLM |
| Audit event storage | New table | Existing `audit_log` table | Schema already has `event` + JSON `detail` column |
| Amendment panel | New component | `handleAmendToggle`/`handleAmendSave` | Already built and tested in Phase 19 |
| Section key validation | New Literal | Import from `amendments.py` pattern | Consistent with existing `Literal['id', 'ov', 'du', 'cls', 'q', 'drf']` |

---

## Common Pitfalls

### Pitfall 1: CBA Section `id` Field is Empty
**What goes wrong:** Code tries to use `section["id"]` to index CBA articles — gets empty string for all 73 EC sections.
**Why it happens:** The `id` field in the JSON is `""` for all sections in both EC and PA agreements (verified).
**How to avoid:** Use `section["title"].lower()` for matching. Match by substring: `"article 1" in title.lower()` or `"application" in title.lower()`.
**Warning signs:** All rule checks return no matches; audit always produces 0 findings even for clearly deficient WDs.

### Pitfall 2: NT and ED OGs Have No Agreement Directory Match
**What goes wrong:** `load_cba_data("NT")` crashes with FileNotFoundError.
**Why it happens:** NT (Nutrition and Dietetics) and ED (Education) do not have an obvious matching JSON file in `data/agreements/`. NR covers Architecture/Engineering (EN group), not NT.
**How to avoid:** `load_cba_data()` must return `None` gracefully for unmapped OG codes. The audit still runs ERR principle checks for these groups; CBA checks are simply skipped.
**Warning signs:** 500 error on audit for NT or ED positions.

### Pitfall 3: Audit Auto-Firing on Review Entry
**What goes wrong:** Audit runs automatically when `reviewing` becomes `true`, similar to the orphan check `useEffect`.
**Why it happens:** AUDIT-01 explicitly states "never runs automatically." Copy-pasting the orphan check `useEffect` pattern would cause this.
**How to avoid:** The audit is triggered ONLY by a button click handler (`handleRunAudit`), never in a `useEffect`.
**Warning signs:** `POST /api/wd/{id}/audit` fires on every review entry.

### Pitfall 4: Deduplication Race on Re-Run
**What goes wrong:** Re-running the audit doubles findings in the UI.
**Why it happens:** Frontend appends new findings to existing state instead of replacing; or backend inserts without deleting old rows.
**How to avoid:** Backend DELETEs all previous `risk_audit_finding` rows before inserting. Frontend sets `auditFindings` to `data.findings` (full replace, not append).
**Warning signs:** Finding count doubles on each re-run.

### Pitfall 5: Section Key Mismatch Between Audit and Amendment
**What goes wrong:** Manual Edit opens a generic panel, not the section-specific one; findings don't co-appear with amendment notes in later DOCX output.
**Why it happens:** Audit finding uses section key `"duties"` instead of `"du"`.
**How to avoid:** Findings MUST use the exact same Literal values as `amendments.py`: `'id' | 'ov' | 'du' | 'cls' | 'q' | 'drf'`. Map CBA and ERR rule results to these keys in `risk_auditor.py`.
**Warning signs:** `handleAmendToggle("duties")` called — no panel opens.

### Pitfall 6: Multi-OG Agreement Files (PA covers AS, CR, PM, WP)
**What goes wrong:** Audit for an AS position loads `PA_full.json` but PA has 31 sections covering all PA sub-groups; scope matching may be too broad.
**Why it happens:** PA is a multi-group agreement. AUDIT-02 scopes matching to "exclusion, scope, and application articles only" — this keeps the match surface small enough for the two-signal rule to suppress false positives.
**How to avoid:** Filter articles by keyword matching "scope", "application", "recognition" in the title; ignore all other articles. The two-signal rule provides the remaining false-positive suppression.

---

## Code Examples

### CBA Data Loader
```python
# app/services/risk_auditor.py
import json
from pathlib import Path

DATA_DIR = Path(__file__).parents[3] / "data" / "agreements"

OG_AGREEMENT_DIR: dict[str, str] = {
    "EC": "EC", "IT": "IT_CS", "AS": "PA", "FI": "CT_FI",
    "CR": "PA", "PM": "PA", "WP": "PA", "GT": "TC",
    "EL": "EL", "FB": "FB", "FS": "FS", "AI": "AI", "AU": "CT_FI",
    "LC": "LP_LA", "LP": "LP_LA", "MT": "SP_AP",
    "NU": "SH", "PS": "SH", "SW": "SH", "PO": "PO",
    # NT, ED: no agreement dir — CBA checks skipped
}

def load_cba_data(og_code: str) -> dict | None:
    """Load CBA JSON for the given OG code. Returns None if no mapping exists."""
    dir_name = OG_AGREEMENT_DIR.get(og_code)
    if not dir_name:
        return None
    json_path = DATA_DIR / dir_name / f"{dir_name}_full.json"
    if not json_path.exists():
        return None
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)
```

### Audit Finding Dataclass
```python
# app/services/risk_auditor.py
from dataclasses import dataclass, asdict
from typing import Literal

@dataclass
class AuditFinding:
    rule_id: str
    section: Literal['id', 'ov', 'du', 'cls', 'q', 'drf']
    severity: Literal['advisory', 'warning']
    citation: str       # verbatim CBA clause or court citation
    recommendation: str # plain-language guidance

    def to_dict(self) -> dict:
        return asdict(self)
```

### run_audit Signature
```python
# app/services/risk_auditor.py
def run_audit(wd, cba_data: dict | None) -> list[dict]:
    """Run all CBA and ERR checks. Returns list of finding dicts.

    Args:
        wd: WorkDescription instance
        cba_data: Loaded CBA JSON, or None if no agreement mapping exists

    Returns:
        List of AuditFinding.to_dict() — empty list if no findings.
    """
    findings = []
    if cba_data:
        findings.extend(_run_cba_checks(wd, cba_data))
    findings.extend(_run_err_checks(wd))
    return findings
```

### Decision Request Model
```python
# app/api/wd.py
class AuditDecideRequest(BaseModel):
    rule_id: str = Field(min_length=1, max_length=100)
    section: Literal['id', 'ov', 'du', 'cls', 'q', 'drf']
    decision: Literal['accept', 'manual_edit', 'skip']
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Full CBA article scanning | Scope/exclusion/application articles only + two-signal gate | Drastically reduces false positives |
| LLM-based compliance checking | Deterministic rule predicates | Reproducible, offline, auditable (v3.0 policy) |
| Separate audit UI flow | Integrated into existing Review phase and amendment panel | No new navigation; advisor stays in context |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | NT and ED have no matching agreement directory; audit returns zero CBA findings for these groups | OG-to-Agreement Mapping | If wrong: a mapping exists and CBA checks are missing for those groups |
| A2 | Two-signal rule implementation: Signal 1 = verbatim term match; Signal 2 = section relevance by article type | Two-Signal Rule | If wrong: different signal definition needed; could affect false-positive rate |
| A3 | DELETE-then-INSERT strategy for deduplication on re-run | Backend Endpoint Pattern | If wrong: max-id-per-rule dedup in response is needed instead |
| A4 | `risk_audit_decision` endpoint lives in `wd.py` at `POST /api/wd/{id}/audit/decide` | Backend Pattern | Minor — could be in separate file; doesn't affect functionality |

---

## Open Questions

1. **NT and ED agreement mapping**
   - What we know: `data/agreements/` has no directory that cleanly covers NT (Nutrition/Dietetics) or ED (Education)
   - What's unclear: Does a relevant agreement JSON exist under a non-obvious name (e.g., RM, UT, or one of the specialty directories)?
   - Recommendation: Implement with graceful fallback (None return); log a warning. Planner should add a task to verify with user if needed.

2. **CBA term extraction for Signal 1**
   - What we know: Must be significant terms (not stopwords, not < 4 chars)
   - What's unclear: Should extraction use a curated keyword list per article, or a generic NLP-free tokenizer?
   - Recommendation: Curated keyword list per article type (3-5 keywords per article) — more predictable and testable than generic tokenization.

3. **Minimum duty count threshold for ERR_DUTY_COVERAGE**
   - What we know: Cushnie principle says missing duties must be added; no explicit minimum in the PDF
   - What's unclear: What threshold avoids false positives for truly simple positions?
   - Recommendation: 3 duties as minimum; flag as advisory (not warning) to keep it non-blocking.

---

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — pure Python + existing SQLite + existing CBA JSON files already on disk)

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest + pytest-asyncio |
| Config file | `v2/backend/pytest.ini` (or `pyproject.toml`) |
| Quick run command | `cd v2/backend && pytest tests/test_risk_audit.py -x` |
| Full suite command | `cd v2/backend && pytest tests/ -x` |
| Frontend framework | Vitest + jsdom |
| Frontend run command | `cd v2/frontend && npm test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUDIT-01 | `POST /api/wd/{id}/audit` returns 200 with findings list | integration | `pytest tests/test_risk_audit.py::test_audit_endpoint -x` | Wave 0 |
| AUDIT-01 | Re-run replaces previous findings (no duplication) | integration | `pytest tests/test_risk_audit.py::test_audit_rerun_replaces -x` | Wave 0 |
| AUDIT-01 | 404 for unknown WD | integration | `pytest tests/test_risk_audit.py::test_audit_404 -x` | Wave 0 |
| AUDIT-02 | CBA loader returns None for unmapped OG (NT, ED) | unit | `pytest tests/test_risk_audit.py::test_load_cba_unmapped_og -x` | Wave 0 |
| AUDIT-02 | Two-signal rule suppresses single-signal matches | unit | `pytest tests/test_risk_audit.py::test_two_signal_false_positive -x` | Wave 0 |
| AUDIT-03 | ERR duty coverage rule fires when < 3 duties | unit | `pytest tests/test_risk_audit.py::test_err_duty_coverage -x` | Wave 0 |
| AUDIT-03 | ERR specificity rule fires when 50%+ duties < 8 words | unit | `pytest tests/test_risk_audit.py::test_err_duty_specificity -x` | Wave 0 |
| AUDIT-03 | Well-formed WD produces zero findings | unit | `pytest tests/test_risk_audit.py::test_zero_findings_clean_wd -x` | Wave 0 |
| AUDIT-04 | Decision endpoint writes audit_log row with correct detail | integration | `pytest tests/test_risk_audit.py::test_audit_decide -x` | Wave 0 |
| AUDIT-05 | Audit finding section key is valid amendment section key | unit | `pytest tests/test_risk_audit.py::test_finding_section_key_valid -x` | Wave 0 |

### Wave 0 Gaps
- [ ] `tests/test_risk_audit.py` — all 10 test stubs, RED baseline (mirrors `test_writing_guide.py` Wave 0 structure)
- [ ] `app/services/risk_auditor.py` — stub module (empty `run_audit` returning `[]`; empty `load_cba_data` returning `None`)

---

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | `Literal` type for section + decision fields; `min_length`/`max_length` on `rule_id` |
| V4 Access Control | no | Single-user local app — no auth |
| V2 Authentication | no | Single-user local app |
| V6 Cryptography | no | No encryption needed |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Arbitrary `rule_id` injection into audit_log detail | Tampering | `max_length=100` on `rule_id`; `detail` is JSON, not SQL |
| Path traversal in CBA file loading | Tampering | `og_code` validated against static `OG_AGREEMENT_DIR` dict; no user-controlled path construction |
| Arbitrary `section` key in decide endpoint | Tampering | `Literal['id','ov','du','cls','q','drf']` — same pattern as `amendments.py` |

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: codebase] `v2/backend/app/api/amendments.py` — audit_log schema, section key Literal, INSERT/GET pattern
- [VERIFIED: codebase] `v2/backend/app/api/wd.py` — `validate-duties` endpoint pattern; `orphan_check` CBA-adjacent pattern
- [VERIFIED: codebase] `v2/backend/app/db.py` — audit_log DDL confirmed
- [VERIFIED: codebase] `v2/frontend/src/app.jsx` — `handleAmendToggle`, `handleAmendSave`, `reviewing` state, `ReviewState` usage
- [VERIFIED: codebase] `v2/frontend/src/conversation.jsx` — `ReviewState` component current structure
- [VERIFIED: file inspection] `data/agreements/EC/EC_full.json` — CBA JSON structure, section schema, Article 34 text
- [VERIFIED: file inspection] `data/agreements/PA/PA_full.json` — multi-OG agreement structure
- [VERIFIED: file inspection] `data/agreements/` directory listing — 27 OG agreement directories enumerated
- [VERIFIED: PDF read] `data/AI Docs/ERR_Principles_drawn_from_Federal_Court.pdf` — Cushnie, Dervin, Trépanier principles
- [VERIFIED: PDF read] `data/AI Docs/Wilkonson v. Canada.pdf` — 2020 FCA 223; reasonableness standard for Deputy Head decisions

### Secondary (MEDIUM confidence)
- [VERIFIED: codebase] `v2/backend/tests/test_writing_guide.py` — test structure pattern for Wave 0 + unit/integration split
- [VERIFIED: codebase] `v2/backend/tests/conftest.py` — test fixture patterns (client, env_with_db, tmp_db_path)
- [VERIFIED: codebase] `v2/backend/app/data/constants.py` lines 36-62 — OG_LEVELS keys for completeness check

### Tertiary (LOW confidence — assumptions flagged in Assumptions Log)
- [ASSUMED] NT and ED OG codes have no matching CBA agreement directory
- [ASSUMED] Two-signal implementation: verbatim term match + section relevance by article type

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components are existing; no new libraries
- CBA JSON structure: HIGH — directly inspected
- ERR principles: HIGH — PDFs read directly
- Amendment panel integration: HIGH — code verified
- audit_log schema: HIGH — DDL verified
- NT/ED agreement mapping: LOW — no directory match found; gap acknowledged
- Two-signal rule specifics: MEDIUM — design inferred from requirement + CBA structure

**Research date:** 2026-06-15
**Valid until:** 2026-07-15 (stable codebase; CBA JSONs are static)
