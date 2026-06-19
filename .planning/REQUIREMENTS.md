# Requirements — v4.0 Seven-Elements Conversational Architecture

**Milestone:** v4.0
**Status:** Active
**Total:** 16 requirements across 6 categories
**Core Value:** An HR advisor can describe work in plain language and receive a legally defensible, fully traceable job description — grounded in NOC, collective agreement, and TBS classification policy — in minutes instead of hours.

---

## Organizational Context (ORG) — 3 requirements

- [ ] **ORG-01** — User can provide organizational context through a 4-part Socratic step (work stream, organizational placement, reporting relationship, additional context); responses are assembled into `org_context: Optional[str]` on WorkDescription; `WDPatchRequest` updated in the same commit
- [ ] **ORG-02** — Organizational context renders in the document live preview above the Client Service Results section
- [ ] **ORG-03** — Organizational context populates the Part 2 Organizational Context section of the Accessible JD DOCX export

---

## Responsibilities Narrative (RESP) — 3 requirements

- [ ] **RESP-01** — User can enter a free-text responsibilities narrative (available on all positions, not gated on supervisory flag); stored as `responsibilities_narrative: Optional[str]` on WorkDescription; `WDPatchRequest` updated in the same commit
- [ ] **RESP-02** — Responsibilities narrative renders as its own section in the document live preview
- [ ] **RESP-03** — Responsibilities narrative populates the Part 2 Responsibilities section of the Accessible JD DOCX export

---

## Seven-Elements Completeness Audit (ELEM) — 3 requirements

- [ ] **ELEM-01** — `POST /api/wd/{id}/validate-elements` returns per-element status (populated / derived / missing) for all 7 Part 2 elements; JES-derived Effort and Working Conditions show as "derived" not "missing"; Responsibilities shows as "not_applicable" only when no text is provided (field is open to all positions)
- [ ] **ELEM-02** — Review phase displays a completeness badge showing how many of the 7 elements are populated or derived (soft gate — advisor must acknowledge, not blocked from export)
- [ ] **ELEM-03** — Structured data export (JSON and CSV) includes per-element completeness status alongside element values

---

## Manager-Track UX (MGR) — 3 requirements

- [ ] **MGR-01** — A role selector screen precedes the conversation: "I am a classification advisor" / "I am a hiring manager"; selection is persisted to localStorage and does not modify the WD data model
- [ ] **MGR-02** — Manager mode renders no OG codes, JES factor names, or CBA clause references in any user-visible text or UI label
- [ ] **MGR-03** — Manager-track STEPS variant skips classification-internal steps (og_confirm, og_level, JES override); the manager's output is a draft JD for the classification team

---

## Structured Data Export (SEXP) — 3 requirements

- [ ] **SEXP-01** — `POST /api/wd/{id}/export/json` returns all 7 Part 2 elements (Organizational Context, Client Service Results, Key Activities, Skills, Effort, Responsibility, Working Conditions) plus classification metadata and provenance as JSON; uses a shared `build_seven_elements(wd)` helper in `export_service.py`
- [ ] **SEXP-02** — `POST /api/wd/{id}/export/csv` returns the same 7-element schema as UTF-8-with-BOM CSV (Excel-compatible); uses `csv.DictWriter` with `io.StringIO`; per-element completeness status included
- [ ] **SEXP-03** — SPA Review phase displays JSON and CSV download buttons alongside existing DOCX/PDF buttons; uses the same `exportAs()` async fetch + Blob + `URL.createObjectURL` pattern

---

## Enhanced Job Poster (POST) — 1 requirement

- [ ] **POST-01** — Job poster DOCX gains an "About the organization" section populated from `org_context`; Key Activities and Skills sections sourced from the 7-element structured data; `build_poster_template.py` script updated and self-verifying

---

## Future Requirements (Deferred)

| Requirement | Reason for deferral |
|-------------|---------------------|
| SJD pre-fill for org_context | SJD_LIBRARY `organizational_context` field could auto-fill ORG-01; deferred until SJD dataset is richer |
| DND org unit dropdown for org placement | `DND_Org_26-Feb-2026-L3-FINAL_v2.xlsx` not yet parsed; v5 |
| NOC→OaSIS crosswalk in JSON export | `data/OASIS-2025-Taxonomy.json` may contain crosswalk; verify before committing to scope |
| Effort / Working Conditions as dedicated Socratic steps | JES-derived values sufficient for v4.0; dedicated advisor questions are v5 |

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-user / auth | Single-user local app |
| Manager WD separate DOCX template or watermarked format | Manager-track uses same Accessible JD template; separate template is v5 |
| Real-time analytics pipeline integration | JSON/CSV export is the handoff point; downstream ingestion is Julian's team's concern |
| Bilingual export of 7-element data | French content generation is out of scope |

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| ORG-01 | Phase 26 | Pending |
| ORG-02 | Phase 26 | Pending |
| ORG-03 | Phase 26 | Pending |
| RESP-01 | Phase 27 | Pending |
| RESP-02 | Phase 27 | Pending |
| RESP-03 | Phase 27 | Pending |
| ELEM-01 | Phase 27 | Pending |
| ELEM-02 | Phase 27 | Pending |
| ELEM-03 | Phase 27 | Pending |
| MGR-01 | Phase 28 | Pending |
| MGR-02 | Phase 28 | Pending |
| MGR-03 | Phase 28 | Pending |
| SEXP-01 | Phase 29 | Pending |
| SEXP-02 | Phase 29 | Pending |
| SEXP-03 | Phase 29 | Pending |
| POST-01 | Phase 29 | Pending |
