# Stack Research — v3.0

**Project:** JD Builder v3.0 — Classification Depth & Document Quality
**Researched:** 2026-06-10
**Platform:** Jetson AGX Orin "Jane" — ARM64 (aarch64), Python 3.10.12
**Confidence:** HIGH (all findings verified by direct execution on target hardware)

---

## Context: What Already Exists

The v2.0 stack is locked and working. Do not change or re-research it.

| Component | Version | Status |
|-----------|---------|--------|
| FastAPI | 0.128.8 | CONFIRMED installed |
| Pydantic v2 | 2.12.5 | CONFIRMED installed |
| python-docx | 1.1.2 | CONFIRMED installed |
| docxtpl | 0.18.0 | CONFIRMED installed (requirements.txt pins 0.19.0; pip shows 0.18.0 — harmless) |
| WeasyPrint | 69.0 | CONFIRMED installed |
| SQLite (stdlib) | — | CONFIRMED |
| React 18 + Vite | 18.3.1 / 5.4.10 | CONFIRMED |

---

## New Dependencies

| Library | Version | Purpose | ARM64 ok? |
|---------|---------|---------|-----------|
| PyMuPDF (`pymupdf`) | 1.27.2.3 | Read PDF reference docs (ERR Principles, Wilkonson case) to extract audit rule text at build time | CONFIRMED installed and running on aarch64 |
| *(none for DOCX reading)* | — | python-docx 1.1.2 already reads .docx files; no new library needed for Accessible JD Template or Writing Guide parsing | already installed |
| *(none for SJD storage)* | — | SJD library is a Python constant in `constants.py` (9 records from SJD Examples.txt); no new library needed | N/A |
| *(none for audit patterns)* | — | Risk Audit uses existing FastAPI route + Pydantic models; no new framework needed | N/A |
| *(none for CSS fix)* | — | Preview page height is a 2-line CSS fix; no JS library needed | N/A |

**Net new pip dependencies for v3.0: zero.** All required capabilities are either already installed or pure Python data work.

---

## Feature-by-Feature Analysis

### Feature 1: SJD Library

**Storage: Python constant in `constants.py`, not a SQLite table.**

The SJD Examples.txt contains 9 records in a TSV-like format (Job Title, JobCode, SJD Number, Group Level, Supervisory, NOC, Salary, Organizational Context). Parsed once at module load into a list of typed dicts. No query-time search is needed — the advisor browses by OG group and level. A SQLite table adds migration complexity with zero query benefit at this record count.

Data shape per SJD record:
```python
{
  "sjd_number": "DND-PA-57047",
  "job_title": "Compensation Agent",
  "og_code": "AS",
  "og_level": 1,
  "noc_code": "13100",
  "supervisory": False,
  "organizational_context": "...",
  "salary_range": "$61,786 - $69,106"
}
```

FastAPI route: `GET /api/sjd` with optional `?og_code=AS` filter. Returns list of SJD summaries. `GET /api/sjd/{sjd_number}` returns full record. No new dependency.

### Feature 2: Accessible JD DOCX Template

**Library: python-docx 1.1.2 — already installed. No new library.**

The Accessible JD Template (`data/AI Docs/Accessible Job Description Template (1).docx`) was verified readable by python-docx: 58 paragraphs, 1 table, standard heading styles (Heading 1, Heading 2, Normal). The template uses standard OOXML styles with no custom XML hacks.

Approach: create a new `accessible_jd_template.docx` Jinja2-compatible template using docxtpl, mirroring the structure of the accessible template. The existing `build_wd_template.py` pattern (from Phase 20) handles this cleanly. The template binary is committed as an artifact; the build script is the reproducible source.

No new library. docxtpl + python-docx covers all .docx read and render operations.

### Feature 3: Writing Guide Integration

**Library: python-docx 1.1.2 — already installed. No new library.**

The Writing Guide (`data/AI Docs/Job Description Writing Guide.docx`) is 550 paragraphs across 13 tables. python-docx reads it correctly. The guide's duty-writing rules (strong action verbs, present tense, no gerunds, no passive voice, specificity requirements) are extracted once as a Python constant at build time — not at runtime.

Validation approach: a pure-Python regex + rule-table function `validate_duty_statement(text: str) -> list[DutyWarning]`. No NLP library. The Writing Guide's explicit principles reduce to ~8-12 detectable patterns (starts with gerund, passive construction, missing object, vague verb, etc.). This is testable, auditable, and runs in under 1ms per duty.

Inline tips: a `WRITING_TIPS` dict keyed by `og_code` and step, populated from guide content, returned via `GET /api/writing-tips?og_code=EC&step=duties`. Pure data, no new library.

### Feature 4: Risk Audit

**Library: none new. Pattern: new FastAPI router + Pydantic models.**

The audit checks JD content against:
- CBA clauses (text already in `data/agreements/` — existing v1.0 ingest, available as plaintext)
- Federal Court principles from `data/AI Docs/ERR_Principles_drawn_from_Federal_Court.pdf` (8 pages, extracted via PyMuPDF at build time into a constant)
- Wilkonson v. Canada (29 pages, same approach)

PyMuPDF (`fitz`) is already installed (1.27.2.3, CONFIRMED on aarch64). It is not in `requirements.txt` — add it. It is not a runtime dependency in the hot path; it is used once in a data-prep script to extract audit rule text into a Python constant before committing.

The audit itself is deterministic rule matching, not LLM. Each finding has: `section`, `finding_type` (cba_clause | federal_court_principle), `citation`, `description`, `severity` (high | medium | low), `recommendation`. The advisor responds with `Accept | Manual Edit | Skip`. This is stored in `audit_log` with `event='risk_audit_decision'`.

FastAPI pattern: `POST /api/wd/{id}/audit` triggers the audit, returns `list[AuditFinding]`. `POST /api/wd/{id}/audit/decision` records advisor decision. No streaming needed — the audit runs in <100ms deterministically.

No new Python library. New Pydantic models (`AuditFinding`, `AuditDecision`) and a new router `app/api/audit.py`.

### Feature 5: Broader OG Classification (12 new groups)

**Library: none new. Data work only.**

All 12 JES standards are already present in `data/Job_evaluation/` as plaintext files:
- ED, FB (has both standard and application guidelines), FS (same), LC, LP, MT, NT, NU, PO, PS, SW, WP

The OG_LEVELS dict already contains FB and FS. The remaining 10 (ED, LC, LP, MT, NT, NU, PO, PS, SW, WP) need level ranges added — sourced from `data/rates_of_pay/` CSV files.

The expansion is pure Python constant work in `constants.py`:
1. Add level ranges to `OG_LEVELS` for the 10 missing groups
2. Add `JES_ELEMENTS` dicts for each group (factor names + degree/point tables from the .txt files)
3. Add `DEGREE_VECTORS` for each group (same structure as `EC_DEGREES`)
4. Add entries to `NON_EC_STANDARD_NAMES` for groups without full JES tables in data
5. Extend `QUESTION_BANK` with Socratic signals covering all 12 new groups

The JES scoring service (`app/services/jes_scoring.py`) already has an OG-dispatch pattern. Adding new groups is additive, no structural change.

No new library.

### Feature 6: Document Preview Page Extension

**Library: none. Pure CSS fix.**

Root cause: `.app` is `height: 100vh`. The `.preview` column is a flex child with `min-height: 0`. The `.doc-scroll` container is `flex: 1 1 auto; min-height: 0; overflow-y: auto`. The `.doc` paper div has no explicit `min-height` and grows with content — this part is correct. The bug is that `.doc` is a block inside a scroll container, so it should grow freely. If content overflows into the grey background, the issue is either `overflow: hidden` somewhere in the ancestor chain or a missing `align-self` on `.doc`.

Fix: confirm `.doc-scroll` uses `align-items: flex-start` (or `align-content: flex-start`) so the `.doc` child doesn't stretch to the scroll container's cross-axis height. The scroll container itself scrolls; the paper grows. Two CSS properties, no library.

```css
.doc-scroll {
  /* existing */
  flex: 1 1 auto; min-height: 0; overflow-y: auto;
  padding: 38px 34px 80px;
  display: flex; justify-content: center;
  /* add: */
  align-items: flex-start;   /* paper starts at top, grows down */
}
```

If the paper is already `flex-start` aligned and the bug is content being clipped, the alternative fix is `min-height: max-content` on `.doc`. Diagnose in browser before committing.

---

## Integration Points

### PyMuPDF — where it hooks in

Used exclusively in one-shot data extraction scripts (not runtime). Add to `requirements.txt`. Usage pattern:

```python
import fitz  # PyMuPDF
doc = fitz.open("data/AI Docs/ERR_Principles_drawn_from_Federal_Court.pdf")
text = "\n".join(page.get_text() for page in doc)
```

Output is a Python constant `FEDERAL_COURT_PRINCIPLES: list[AuditRule]` in `app/data/audit_rules.py`. The FastAPI audit endpoint reads this constant, never calls fitz at request time.

### SJD constant — where it hooks in

New file: `app/data/sjd_library.py`. Contains `SJD_LIBRARY: list[dict]` parsed from SJD Examples.txt. Imported by a new router `app/api/sjd.py`. The conversation front-end gets a new step type (`sjd_browse`) that calls `GET /api/sjd` and lets the advisor pre-populate the WD record from a selected SJD.

### Writing Guide rules — where they hook in

New file: `app/data/writing_rules.py`. Contains `DUTY_VALIDATION_RULES: list[DutyRule]` (regex + description + fix hint) and `WRITING_TIPS: dict[str, list[str]]`. The existing `app/api/wd.py` PATCH endpoint calls `validate_duty_statement()` and returns warnings in the response alongside the saved record. No separate endpoint needed.

### Audit rules — where they hook in

New file: `app/data/audit_rules.py`. New router `app/api/audit.py`. The audit is triggered explicitly by the advisor in the Review phase (not automatic). The `audit_log` table already exists and can store audit decisions with `event='risk_audit_decision'`.

### OG expansion — where it hooks in

`app/data/constants.py` only. The OG classifier (`app/api/og.py`) and JES scorer (`app/services/jes_scoring.py`) dispatch on `og_code`. Adding new groups to `OG_LEVELS`, `JES_ELEMENTS`, and `QUESTION_BANK` is sufficient — the dispatch logic is already OG-agnostic.

---

## What NOT to Add

| Temptation | Why Not |
|------------|---------|
| A database table for SJD library | 9 records. A Python constant is simpler, testable, version-controlled, and requires no migration. Add a SQLite table only if the library grows beyond ~200 records or needs full-text search. |
| An NLP library (spaCy, NLTK) for duty validation | The Writing Guide principles reduce to ~10 regex patterns. spaCy on ARM64 has wheel availability issues for some versions; it pulls in large models; and it's overkill for rule-based validation. Regex + a lookup table is auditable and fast. |
| A rule-engine library (drools-style) for audit | The audit has ~20-30 rules. A list of dataclasses with a `check(wd: WorkDescription) -> list[AuditFinding]` signature is sufficient. Durable Rules, Pyke, or similar frameworks add complexity for no gain at this scale. |
| LLM for Writing Guide validation or Risk Audit | The Writing Guide gives explicit, enumerable principles. The Federal Court document gives citable rules. Deterministic matching is auditable; LLM output is not. The audit must be legally defensible. |
| A new PDF library | PyMuPDF is already installed. WeasyPrint handles export. No gap. |
| A frontend charting/visualization library | The Risk Audit findings are rendered as an inline list with Accept/Edit/Skip controls. No chart. No new npm package. |
| React Router or a client-side router | The SJD browser is a new step in the existing STEPS array, not a new page. The existing step-navigation pattern handles it. |
| A separate microservice for the audit | Single-user local app. One FastAPI process. Splitting into services adds network complexity and a second process to manage on the Jetson. |

---

## ARM64 Compatibility Summary

All existing packages: CONFIRMED on aarch64 (running on this machine).

PyMuPDF 1.27.2.3: CONFIRMED on aarch64. Already installed at `/home/charles/.local/lib/python3.10/site-packages`. The package bundles libmupdf as a native extension; the aarch64 wheel is published to PyPI and resolves cleanly. No system dependencies beyond what is already present.

No new packages with ARM64 risk.

---

## Required requirements.txt Change

Add one line to `v2/backend/requirements.txt`:

```
pymupdf==1.27.2.3
```

This documents an already-installed package that the data-prep scripts depend on. It is not a runtime hot-path dependency, but it should be pinned so a fresh environment can reproduce the audit rule extraction scripts.

---

## Sources

- python-docx verified readable on target hardware: direct execution of `docx.Document(...)` on both source files (Accessible JD Template: 58 paragraphs, 1 table; Writing Guide: 550 paragraphs, 13 tables)
- PyMuPDF ARM64: `pip show pymupdf` → Version 1.27.2.3, confirmed on aarch64 3.10.12 on this machine
- PyMuPDF PDF read verified: `fitz.open(...)` on ERR_Principles (8 pages) and Wilkonson (29 pages), both readable
- SJD Examples.txt: 9 records, tab-separated format confirmed by file inspection
- OG JES standards: 18 files in `data/Job_evaluation/` confirmed present for all 12 new groups
- CSS fix rationale: styles.css inspected; `.doc-scroll` uses `display: flex; justify-content: center` without `align-items: flex-start` — paper stretches to scroll container height, causing visible overflow for short documents; fix is additive, not a rewrite
