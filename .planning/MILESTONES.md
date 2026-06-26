# Milestones: JD Builder

---

## ✅ v1.0 MVP — Shipped 2026-06-03

**Phases:** 1–9 (incl. 8.1) | **Plans:** 38 | **Timeline:** 2026-05-27 → 2026-06-03 (7 days)
**Tests at ship:** 188 passing, 9 skipped | **LOC:** ~15,539 Python + 773 HTML + 1,138 CSS

### Delivered

A DND-first end-to-end job description builder: advisor describes work in plain language → NOC mapping → OG classification → JD generation with provenance → JES scoring → DOCX export with version manifest and DRF linkages.

### Key Accomplishments

1. **NOC 2021 FTS5 + sqlite-vec pipeline** — 900+ unit group profiles indexed with content hashes; three-stage NL→NOC mapping (FTS5 shortlist → embedding rerank → LLM justification)
2. **CA + JES + policy data pipelines** — restriction/scope/exclusion clauses per OG; JES factor descriptors per og_code + factor_name; TBS Directive on Classification in FTS for live citation
3. **OG classification with hard gate** — top-3 candidates with verbatim TBS inclusions/exclusions; AS/EC disambiguation surfaced from directive; JD generation blocked until OG confirmed
4. **Provenance-first JD generation** — every duty is verbatim NOC text with structured ProvenanceTag; orphan statement check flags authority violations; advisor-added content distinctly tagged
5. **JES scoring with recovery path** — per-factor instructor calls with 3 retries; Phase 8.1 added per-factor retry + advisor override so a failed factor never permanently blocks export
6. **DOCX export with version manifest** — docxtpl TBS WD template; ProvenanceTags rendered as citations; source document hashes in manifest; DRF Section 6 for DND positions
7. **DRF integration** — 42 DRF rows ingested; keyword-scored candidates; inline panel on /wizard/export; confirmed linkages in DOCX Section 6

### Known Deferred Items at Close

- PDF export (EXP-01 partial) — `/export/{wd_id}/pdf` returns 501; DOCX is primary
- noc_fts DDL bug (UNINDEXED + content='' — deferred from Phase 4)
- Starlette TemplateResponse deprecation warning
- 02-02-SUMMARY.md not written

### Archive

- [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) — full phase details
- [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md) — all 21 v1 requirements with outcomes

---

## ✅ v2.0 Real Guided Conversation — Shipped 2026-06-10

**Phases:** 10–20 (11 phases) | **Plans:** 38 (3 + 3 + 3 + 4 + 4 + 4 + 4 + 4 + 4 + 4 + 1) | **Timeline:** 2026-06-03 → 2026-06-10 (7 days)
**Tests at ship:** 80 v2 backend + 31 v2 frontend + 188 v1 backend (preserved) = **299 total GREEN, 0 failed** | **Requirements:** 52/52 (49 active + 3 validated in Phase 10)

### Delivered

A conversational job description builder that replaces the v1.0 HTMX wizard with a React 18 SPA. The advisor progresses through 6 conversational phases (Role → Work Type → Classification → Duties → Qualifications → Review), accumulates signals deterministically, and receives a fully traceable job description export.

### Key Accomplishments

1. **React 18 SPA + FastAPI JSON API** — 5 .jsx files (~1,200 LOC) + FastAPI service with Pydantic v2 models and parameterized SQLite; Vite proxies /api/* to :8000
2. **Deterministic classification (no LLM in main flow)** — 6-phase interview with Socratic question bank; work-type + 3 scope Qs → ranked OG candidates from signal tally; AS/EC disambiguation surfaced; CAF rank advisory (advisory-flagged, not authoritative); `require_og_confirmed` 409 hard gate
3. **NOC pipeline preserved from v1.0** — FTS5 + sqlite-vec + Ollama LLM justification; NocConfirmList component; `confirmed_noc` stored on WD
4. **JES scoring** — Per-factor EC JES 2017 with 3-retry instructor wrapper + sentinel pattern; non-EC approximate totals (FI/IT/AS/EN); advisor per-factor override; `jes_scores` + `jes_total_points` rendered in Section 4
5. **JD composition + live preview** — Verbatim NOC duties with provenance; advisor-added duties distinctly tagged; orphan check; live document preview with ghost placeholders, composed overview, section click-to-edit, provenance footer, qualification section
6. **OG-keyed qualifications** — `QUAL_DEFAULTS` map replaces the EC-only hardcode; `getQualDefault(og_code)`; inline `.qual-error` validation; uppercase monospace sub-labels
7. **Manager amendments** — Per-section amendment notes via POST /amendments; audit log rows; gold-dot indicators in document; gated appendix in DOCX
8. **Export pipeline** — DOCX (TBS Work Description) with version manifest + amendment appendix; DOCX (job poster) with bilingual headers; PDF via WeasyPrint with ARM64 501 gate; SPA async exportAs() with 501 diagnostic toast

### Architecture Non-Negotiables (Honored)

- ProvenanceTag on every exported content element — set at write time, rendered at export ✓
- Every content element in the exported DOCX/PDF traces to an authoritative source citation ✓
- Evidence-based classification (NOC + OG + JES engine) replaces the v1.0 work-type picker ✓
- Deterministic classification in the main flow — LLM used only for NOC justification ✓
- Socratic constraint: manager never selects OG directly; OG is derived from accumulated answer signals ✓

### Known Deferred / Advisory Items at Close

- 11 code-review warning + 10 info findings from Phase 20 (advisory, non-blocking; tracked in `20-REVIEW.md`)
- WeasyPrint PDF on Jane (ARM64 Pango/Cairo) — runtime probe gates to 501 if libs missing
- 1 HIGH content-drift between `QUAL_STANDARDS` (backend) and `QUAL_DEFAULTS` (frontend) for AS — advisory; recommend content-parity test
- 2 of 3 AS/FI definitions sourced from TBS OCHRO standard instead of PA/CT-FI CAs (CAs cover the groups but lack the group definition text itself)

### Archive

- [v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md) — full phase details
- [v2.0-REQUIREMENTS.md](milestones/v2.0-REQUIREMENTS.md) — all 52 v2 requirements with outcomes
- [v2.0-RETROSPECTIVE.md](RETROSPECTIVE.md) — milestone retrospective

---

## ✅ v3.0 Classification Depth & Document Quality — Shipped 2026-06-16

**Phases:** 21–25 (5 phases) | **Plans:** 24 (9 + 4 + 4 + 4 + 3) | **Timeline:** 2026-06-11 → 2026-06-16 (6 days)
**Tests at ship:** 150 backend + 60 frontend GREEN

> Note: this entry was reconstructed at v4.0 close — v3.0 was not formally closed with a MILESTONES.md entry at the time. Phase artifacts archived under `milestones/v3.0-phases/`.

### Delivered

Extended the classification engine to all 16 GC occupational groups, added the DND SJD library, Writing-Guide duty validation, a deterministic compliance Risk Audit, and the TBS Accessible JD DOCX template (Part 1 + Part 2 seven subsections).

### Key Accomplishments

1. **16 OG groups end-to-end** — atomic extension of all six constants; JES point-rating + level-description routing; NU/SW/ED sub-group disambiguation; document-preview overflow fix
2. **SJD Library** — `SJD_LIBRARY` parsed from `data/SJD Examples.txt`; `GET /api/sjd`; Browse SJDs flow with provenance through to the DOCX manifest
3. **Writing Guide integration** — deterministic duty validation (active-voice, word-count, no-passive, no-duplicate) via `POST /api/wd/{id}/validate-duties`; OG-specific tips from `OG_DEFINITIONS`
4. **Risk Audit** — two-signal CBA clause matching + Federal Court ERR principles; per-finding Accept/Manual Edit/Skip logged to audit_log
5. **Accessible JD template** — self-verifying `wd_accessible_template.docx` (Part 1 17-field table + 3 signature blocks; Part 2 seven subsections); Effort/Working Conditions from JES factor scores; TBS WD template retired

### Archive

- [v3.0 phases](milestones/v3.0-phases/) — full phase execution artifacts

---

## ✅ v4.0 Seven-Elements Conversational Architecture — Shipped 2026-06-26

**Phases:** 26–29 (4 phases) | **Plans:** 9 (2 + 2 + 2 + 3) | **Timeline:** 2026-06-19 → 2026-06-26 (7 days)
**Tests at ship:** 184 backend + 87 frontend GREEN | **Requirements:** 16/16 validated

### Delivered

The full TBS Accessible JD Template (all 7 Part 2 elements) captured through natural conversation. Two new typed WorkDescription fields (`org_context`, `responsibilities_narrative`), a seven-element completeness audit with a Review-phase badge, machine-readable JSON/CSV export for workforce analytics, and a Manager-Track UX that hides OG/JES/CBA internals from hiring managers while producing a draft JD for the classification team.

### Key Accomplishments

1. **Org Context conversational step** — 4-part Socratic step → assembled `org_context`; renders above Client Service Results; populates Accessible DOCX Part 2 (ORG-01/02/03)
2. **Responsibilities narrative** — free-text typed field on all positions; own preview section; Accessible DOCX Part 2 Responsibility (RESP-01/02/03)
3. **Seven-Elements completeness audit** — `build_seven_elements(wd)` single source of truth; `POST /api/wd/{id}/validate-elements` with populated/derived/missing status; Review-phase N/7 soft-gate badge (ELEM-01/02/03)
4. **Manager-Track UX** — localStorage role selector (never in the WD model); `wd_type` field; classification-gate bypass; manager STEPS variant; DRAFT watermark; systematic MGR-02 suppression of OG codes / JES factor names / CBA citations (MGR-01/02/03)
5. **Structured export** — `POST /api/wd/{id}/export/json` (7-element analytics + provenance) and `/export/csv` (UTF-8-BOM, one row per duty, RFC 4180); SPA download buttons; manager-track bypass with `[ADVISOR TO COMPLETE]` placeholders (SEXP-01/02/03)
6. **Enhanced poster** — "About the Organization" section from `org_context`; `build_poster_template.py` self-verifying (POST-01)

### Post-Ship Hardening (quick tasks / fixes)

- Org-context prose synthesis endpoint (LLM fluid-prose) + redundant-field prune (placement/reporting already captured in Phase 0) — quick task 260626-ejt
- Org-context synthesis bounded with 30s client timeout; toast no longer hangs; step auto-advances on synthesis completion; always-visible Home button

### Known Deferred Items at Close

- Manager-track **poster and PDF** exports lack the DRAFT watermark applied to the manager DOCX (Phase 28 MAJ-01 / Phase 29 MAJ-01)
- CSV **formula injection** not neutralized — accepted per T-29-02-03 disposition (internal HR tool, trusted input)
- v5 candidates: SJD pre-fill for org_context, DND org-unit dropdown, NOC→OaSIS crosswalk in JSON export, dedicated Effort/Working Conditions Socratic steps

### Archive

- [v4.0-ROADMAP.md](milestones/v4.0-ROADMAP.md) — full phase details
- [v4.0-REQUIREMENTS.md](milestones/v4.0-REQUIREMENTS.md) — all 16 v4 requirements with outcomes

---
