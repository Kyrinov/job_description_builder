# Requirements — v3.0 Classification Depth & Document Quality

**Milestone:** v3.0
**Status:** Active
**Total:** 24 requirements across 6 categories
**Core Value:** An HR advisor can describe work in plain language and receive a legally defensible, fully traceable job description — grounded in NOC, collective agreement, and TBS classification policy — in minutes instead of hours.

---

## OG Expansion (OGX) — 7 requirements

- [ ] **OGX-01** — `OG_LEVELS`, `OG_DEFINITIONS`, `QUAL_STANDARDS`, `NON_EC_TOTALS`, `NON_EC_STANDARD_NAMES`, and `JES_FACTORS_BY_GROUP` updated atomically for all 16 groups (12 new: ED, FB, FS, LC, LP, MT, NT, NU, PO, PS, SW, WP); a completeness test asserts every key in `OG_LEVELS` is present in all other 5 constants
- [ ] **OGX-02** — `NON_EC_STANDARD_NAMES` consolidated into `constants.py`; `export_service.py` imports from there (eliminates the v2.0 dual-copy drift)
- [ ] **OGX-03** — `QUAL_DEFAULTS` (frontend `data.jsx`) content-parity test against `QUAL_STANDARDS` (backend `constants.py`) written as a failing test before any new group qualification text is authored; parity enforced for all 16 groups at phase close
- [ ] **OGX-04** — `QUESTION_BANK` extended with a sector-gate question routing PA/SH/Legal/Technical/Scientific clusters and cluster-specific disambiguation questions; `accumulateSignals()` produces correct top-ranked OG for each new group given its ideal answer set; per-group integration tests assert this
- [ ] **OGX-05** — Point-rating groups (FB, FS, LP, MT, LC, SW-SCW) get full per-factor JES scoring via `POST /api/jes/score` extending the existing `EC_JES_ELEMENTS` pattern; `JES_FACTORS_BY_GROUP` carries factor definitions for these groups
- [ ] **OGX-06** — Level-description groups (NU, PS, NT, PO, WP, SW-CHA, ED sub-groups) return `jes_total_points` from a level-keyed `NON_EC_TOTALS` lookup (no LLM); `jes_scores: []` for these groups, matching the v2.0 FI/AS pattern; `ClassBlock` renders correctly for both scoring paths
- [ ] **OGX-07** — Sub-group disambiguation for NU (HOS/CHN/EMA), SW (SCW/CHA), and ED sub-groups surfaced to the advisor as an alert analogous to the v2.0 AS/EC disambiguation alert; confirmed sub-group stored on `WorkDescription`

---

## Preview Fix (UI) — 1 requirement

- [ ] **UI-01** — `.doc-scroll` CSS rule in `styles.css` has `align-items: flex-start`; the simulated white `.doc` page grows to contain all preview content at any document length; no content overflows into the grey background; no layout regression in the split conversation/preview pane

---

## SJD Library (SJD) — 3 requirements

- [ ] **SJD-01** — `SJD_LIBRARY` constant (9 entries parsed from `data/SJD Examples.txt`) in `app/data/sjd_library.py`; `GET /api/sjd` with optional `?og_code=` filter; `GET /api/sjd/{number}` for detail; `POST /api/wd/{id}/sjd-start` pre-fills `confirmed_og`, `og_level`, and seed duties from a selected SJD
- [ ] **SJD-02** — Non-blocking "Browse SJDs" action surfaced at end of Role phase; selecting an SJD writes a `sjd_source` provenance field on the WD and tags seeded duties with `source="sjd"` + `sjd_number` in their `ProvenanceTag`; SJD source appears in the DOCX export manifest
- [ ] **SJD-03** — Changing `confirmed_og` after an SJD pre-fill surfaces a warning: "Departing from the SJD classification turns this into a new evaluation — the SJD decision no longer applies"

---

## Writing Guide (WG) — 4 requirements

- [ ] **WG-01** — Structural duty validation covering: active-voice opener (verb-first), word count 8–25, no passive-voice opener, no duplicate duty text; calibrated against `data/SJD Examples.txt` — fewer than 15% of SJD duties may be flagged (a higher rate indicates miscalibration)
- [ ] **WG-02** — Non-blocking inline `.duty-hint` warnings rendered during duty entry; advisor can submit with hints visible; no hard gate; `POST /api/wd/{id}/validate-duties` returns per-duty validation findings; frontend calls after duty-phase commit
- [ ] **WG-03** — `QUESTION_BANK` updated with a "Client Service Results" question inserted before the Key Activities duties step, per the Writing Guide's document structure
- [ ] **WG-04** — Inline per-step OG/group-specific duty tips shown during duty entry sourced from `OG_DEFINITIONS` excerpts (not hardcoded strings)

---

## Risk Audit (AUDIT) — 5 requirements

- [ ] **AUDIT-01** — "Run compliance audit" button in the Review phase (never runs automatically); `POST /api/wd/{id}/audit` executes deterministic rule matching; findings stored in `audit_log` with `event='risk_audit_finding'`; audit is re-runnable and replaces previous findings in the UI (deduplication by max-id per section)
- [ ] **AUDIT-02** — Audit matches against the confirmed OG's CBA JSON file (`data/agreements/{OG}/`) — exclusion, scope, and application articles only; two-signal requirement before any finding fires (verbatim term match + section relevance); false negatives preferred over false positives in this legal domain
- [ ] **AUDIT-03** — Audit evaluates a curated subset of Federal Court ERR principles (completeness of duty coverage, generic vs. specific duty adequacy) sourced from `data/AI Docs/ERR_Principles_drawn_from_Federal_Court.pdf` and `data/AI Docs/Wilkonson v. Canada.pdf`; principles encoded as deterministic rules, not LLM inference
- [ ] **AUDIT-04** — Each finding displays: section, severity (advisory/warning), verbatim CBA clause or court citation, plain-language recommendation; advisor chooses Accept / Manual Edit / Skip; Skip label is "Not applicable — no conflict found"; every decision written to `audit_log` with `event='risk_audit_decision'`
- [ ] **AUDIT-05** — Manual Edit action opens the existing Phase 19 amendment panel for the flagged section; amendment note and audit finding share the same section key so they co-appear in the DOCX amendment appendix

---

## Accessible Template (ACC) — 4 requirements

- [ ] **ACC-01** — `build_accessible_template.py` script builds and self-verifies `app/templates/wd_accessible_template.docx`; Part 1: position identification + 3 signature blocks; Part 2: 6 subsections (Org Context, Client Service Results, Key Activities, Skills, Effort, Responsibilities, Working Conditions); `get_undeclared_template_variables()` confirms all template variables are declared
- [ ] **ACC-02** — `_build_wd_context()` in `export_service.py` populates all Part 2 fields; Effort and Working Conditions sections map from JES factor scores where the confirmed OG's JES standard defines those factors; `[To be completed by advisor]` placeholder where the JES does not define them
- [ ] **ACC-03** — `POST /api/wd/{id}/export/docx` produces the Accessible format; previous TBS WD template retired; poster DOCX template unchanged; all existing export tests updated to assert Accessible format structure
- [ ] **ACC-04** — Content-presence test opens the rendered DOCX via `python-docx` and asserts every non-placeholder template variable resolves to a non-empty string for a fully-completed WD

---

## Future Requirements (Deferred)

| Requirement | Reason for deferral |
|-------------|---------------------|
| Bilingual section toggle in Accessible Template | French content generation is out of scope |
| Effort/Working Conditions as dedicated Socratic steps | Derivable from JES in v3.0; dedicated questions are v4 |
| Audit findings appendix in DOCX export | Phase 24 ships the audit UI; DOCX integration is v3.1 |
| Larger DND SJD dataset | 9 entries sufficient for v3.0 workflow architecture |
| SJD similarity ranking | Keyword/OG browse sufficient at launch |
| Verb suggestion lookup in Writing Guide | Structural rules sufficient; vocabulary enhancement is v4 |
| Hard gate on audit completion before export | Advisory-only in v3.0; gate is v3.1 if adoption proves it useful |

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-user / auth | Single-user local app |
| LLM in audit or duty validation | All v3.0 features are deterministic |
| Real-time CBA update sync | Static curated dataset |
| Full-article CBA scope matching | Scope/exclusion/application articles only; full-article too broad for conservative audit |

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| OGX-01 | Phase 21 | Pending |
| OGX-02 | Phase 21 | Pending |
| OGX-03 | Phase 21 | Pending |
| OGX-04 | Phase 21 | Pending |
| OGX-05 | Phase 21 | Pending |
| OGX-06 | Phase 21 | Pending |
| OGX-07 | Phase 21 | Pending |
| UI-01  | Phase 21 | Pending |
| SJD-01 | Phase 22 | Pending |
| SJD-02 | Phase 22 | Pending |
| SJD-03 | Phase 22 | Pending |
| WG-01  | Phase 23 | Pending |
| WG-02  | Phase 23 | Pending |
| WG-03  | Phase 23 | Pending |
| WG-04  | Phase 23 | Pending |
| AUDIT-01 | Phase 24 | Pending |
| AUDIT-02 | Phase 24 | Pending |
| AUDIT-03 | Phase 24 | Pending |
| AUDIT-04 | Phase 24 | Pending |
| AUDIT-05 | Phase 24 | Pending |
| ACC-01 | Phase 25 | Pending |
| ACC-02 | Phase 25 | Pending |
| ACC-03 | Phase 25 | Pending |
| ACC-04 | Phase 25 | Pending |
