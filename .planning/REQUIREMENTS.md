# Requirements — v4.0 Seven-Elements Conversational Architecture

**Milestone:** v4.0
**Status:** Active
**Total:** 16 requirements across 6 categories
**Core Value:** An HR advisor can describe work in plain language and receive a legally defensible, fully traceable job description — grounded in NOC, collective agreement, and TBS classification policy — in minutes instead of hours.

---

## Organizational Context (ORG) — 3 requirements

- [x] **ORG-01
** — User can provide organizational context through a 4-part Socratic step (work stream, organizational placement, reporting relationship, additional context); responses are assembled into `org_context: Optional[str]` on WorkDescription; `WDPatchRequest` updated in the same commit
- [x] **ORG-02
** — Organizational context renders in the document live preview above the Client Service Results section
- [x] **ORG-03
** — Organizational context populates the Part 2 Organizational Context section of the Accessible JD DOCX export

---

## Responsibilities Narrative (RESP) — 3 requirements

- [x] **RESP-01** — User can enter a free-text responsibilities narrative (available on all positions, not gated on supervisory flag); stored as `responsibilities_narrative: Optional[str]` on WorkDescription; `WDPatchRequest` updated in the same commit
- [x] **RESP-02** — Responsibilities narrative renders as its own section in the document live preview
- [x] **RESP-03** — Responsibilities narrative populates the Part 2 Responsibilities section of the Accessible JD DOCX export

---

## Seven-Elements Completeness Audit (ELEM) — 3 requirements

- [x] **ELEM-01** — `POST /api/wd/{id}/validate-elements` returns per-element status (populated / derived / missing) for all 7 Part 2 elements; JES-derived Effort and Working Conditions show as "derived" not "missing"; Responsibilities shows as "not_applicable" only when no text is provided (field is open to all positions)
- [x] **ELEM-02** — Review phase displays a completeness badge showing how many of the 7 elements are populated or derived (soft gate — advisor must acknowledge, not blocked from export)
- [x] **ELEM-03** — Structured data export (JSON and CSV) includes per-element completeness status alongside element values

---

## Manager-Track UX (MGR) — 3 requirements

- [x] **MGR-01** — A role selector screen precedes the conversation: "I am a classification advisor" / "I am a hiring manager"; selection is persisted to localStorage and does not modify the WD data model
- [x] **MGR-02** — Manager mode renders no OG codes, JES factor names, or CBA clause references in any user-visible text or UI label
- [x] **MGR-03** — Manager-track STEPS variant skips classification-internal steps (og_confirm, og_level, JES override); the manager's output is a draft JD for the classification team

---

## Structured Data Export (SEXP) — 3 requirements

- [x] **SEXP-01** — `POST /api/wd/{id}/export/json` returns all 7 Part 2 elements (Organizational Context, Client Service Results, Key Activities, Skills, Effort, Responsibility, Working Conditions) plus classification metadata and provenance as JSON; uses a shared `build_seven_elements(wd)` helper in `export_service.py`
- [x] **SEXP-02** — `POST /api/wd/{id}/export/csv` returns the same 7-element schema as UTF-8-with-BOM CSV (Excel-compatible); uses `csv.DictWriter` with `io.StringIO`; per-element completeness status included
- [x] **SEXP-03** — SPA Review phase displays JSON and CSV download buttons alongside existing DOCX/PDF buttons; uses the same `exportAs()` async fetch + Blob + `URL.createObjectURL` pattern

---

## Enhanced Job Poster (POST) — 1 requirement

- [x] **POST-01** — Job poster DOCX gains an "About the organization" section populated from `org_context`; Key Activities and Skills sections sourced from the 7-element structured data; `build_poster_template.py` script updated and self-verifying

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
| ORG-01 | Phase 26 | Complete (Plan 26-02 — co-update + 4-part step + stepIndex resume) |
| ORG-02 | Phase 26 | Complete (Plan 26-02 — DocumentPane org_ctx + csr Secs) |
| ORG-03 | Phase 26 | Complete (Plan 26-02 — export_service priority over synthesized fallback) |
| RESP-01 | Phase 27 | Complete |
| RESP-02 | Phase 27 | Complete |
| RESP-03 | Phase 27 | Complete |
| ELEM-01 | Phase 27 | Complete |
| ELEM-02 | Phase 27 | Complete |
| ELEM-03 | Phase 27 | Complete |
| MGR-01 | Phase 28 | Complete (Plan 28-01 — RoleSelector + userRole localStorage hydration + D-28-03 user_role drop guard test) |
| MGR-02 | Phase 28 | Complete (Plan 28-02 — ClassifyBadge / Classification Sec / ReviewState audit panel suppression + 3 MGR-02 inspection tests) |
| MGR-03 | Phase 28 | Complete (Plan 28-01 — wd_type co-update + require_og_confirmed bypass + DRAFT watermark + MANAGER_SKIP_STEPS filter) |
| SEXP-01 | Phase 29 | Complete (Plan 29-02 — POST /api/wd/{id}/export/json + _build_json_export + build_seven_elements shared helper + [ADVISOR TO COMPLETE] manager-track placeholder) |
| SEXP-02 | Phase 29 | Complete (Plan 29-02 — POST /api/wd/{id}/export/csv + _build_csv_export + utf-8-sig BOM + one row per duty + per-element status columns) |
| SEXP-03 | Phase 29 | Complete (Plan 29-03 — Export JSON + Export CSV buttons in ReviewState .export-row + 4-branch exportAs() dispatch in app.jsx + OG guard bypass for json/csv + kind-specific success/error toasts) |
| POST-01 | Phase 29 | Complete (Plan 29-02 — _build_poster_context org_context key + About the Organization section in poster_template.docx + build_poster_template.py self-verify update) |
