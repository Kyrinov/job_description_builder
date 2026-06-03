# Phase 8: Export - Context

**Gathered:** 2026-06-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 8 delivers downloadable DOCX export of the completed WorkDescription. Every
content element's source citation is rendered directly from its ProvenanceTag object
(no prose citations hardcoded in templates). The exported document includes a version
manifest listing all source documents used with content hashes and version labels.
Advisor-added content is marked visibly. PDF export is explicitly deferred.

</domain>

<decisions>
## Implementation Decisions

### Export Gate & Data Quality

- **D-01:** Phase 8 includes a pre-export validation service that inspects the
  WorkDescription before generating any document. Export is **blocked** (returns a
  named error, not a 500) if any JES factor has `level == -1` or `points is None`.
  The error message must name the specific factors that failed and direct the advisor
  back to the JES scoring step.

- **D-02:** The export gate addresses the Phase 7 code review finding (MEDIUM bug):
  `jes_total_points` can be silently wrong when a LLM-returned degree maps to
  `points=None` in the `point_values` dict. The pre-export validator treats
  `points is None` as a blocking condition — a factor with a valid `level` but no
  `points` is not considered complete for export purposes.

- **D-03:** Stage advancement to `"exported"` only occurs after the document is
  successfully generated and the file bytes are confirmed non-empty. `export_hash`
  and `exported_at` are updated on every successful export (re-export is allowed).

### Document Format

- **D-04:** The exported DOCX follows the formal GoC **TBS Work Description format**
  (not the generic HRSDC employer handbook layout). Section structure is derived from:
  (1) TBS-required WD fields defined in DATA-01 (`position_title`, `position_number`,
  `og_level`, `supervisor_title`, `supervisor_position_number`, `review_date`,
  `organizational_context`); (2) `data/directive_on_classification.txt` (the
  authoritative format reference); (3) the WorkDescription model field order.

- **D-05:** Citations in the document are rendered from ProvenanceTag fields
  (`source_type`, `source_id`, `source_version`, `retrieved_date`) — no citation
  prose is written directly into the docxtpl template. The template uses Jinja2
  variable substitution only.

- **D-06:** Advisor-added content (`source_type == "ADVISOR"` or
  `advisor_modified == True` on a DraftDuty) renders with a visible
  "advisor-added / not from authoritative source" marker in the DOCX. This is
  a distinct visual treatment (e.g. italics + inline label), not just a footnote.

- **D-07:** The exported document includes a **version manifest section** listing
  every source document used in the WorkDescription (NOC, CA, JES, TBS OG
  definitions, directive). Each entry includes: source type label, source_id,
  source_version, and retrieved_date — all read from the ProvenanceTags on the
  WorkDescription content elements.

### PDF Strategy

- **D-08:** Phase 8 implements **DOCX export only**. PDF export is explicitly
  deferred until WeasyPrint + Pango/Cairo ARM64 compatibility is confirmed on
  Jane (Jetson AGX Orin). The `GET /export/{wd_id}/pdf` endpoint is created but
  returns HTTP 501 Not Implemented with a clear message:
  `"PDF export is not yet available — download DOCX and convert locally."`
  This satisfies the success criterion route surface without shipping broken PDF.

### UI / Wizard

- **D-09:** Export gets a **dedicated wizard step** — `templates/wizard/step_export.html`.
  The wizard advances to this step after `stage == "jes_scored"`. The page shows:
  - Position summary (title, OG/level, NOC match)
  - JES scoring summary (factor count, total points — only if all factors valid)
  - Version manifest preview (source documents that will appear in the export)
  - Download DOCX button (primary CTA)
  - Any pre-export validation errors shown inline (named factors blocking export)

- **D-10:** Re-export is allowed without confirmation. Clicking Download DOCX
  regenerates the document from the current WorkDescription state, updates
  `export_hash` and `exported_at`, and streams the file. No "replace previous
  export" confirmation gate.

### Phase 7 Review Issues Incorporated

- **D-11:** The pre-export validator (D-01, D-02) directly resolves the Codex review
  concern about incomplete JES sheets reaching `jes_scored` and being treated as
  complete. Phase 8 adds the hard gate that Phase 7's stage transition did not.

- **D-12:** The silent `points=None` total miscalculation flagged in the Phase 7
  code review (REVIEW.md MEDIUM finding, `jes_service.py:76-77`) is handled by
  D-02 — Phase 8 treats `points is None` as a blocking condition and will not
  export a document with an incomplete JES total. Whether jes_service.py is patched
  in Phase 7 cleanup or Phase 8 is left to the planner; the export gate enforces
  correctness regardless.

### Claude's Discretion

- Internal file naming / temp file handling for docxtpl rendering (tmp_path vs
  BytesIO)
- Exact DOCX section/heading styles (H1, H2, table styles in the .docx template)
- How to structure the docxtpl .docx template file (table-based vs paragraph-based
  for duties / JES factors)
- Streaming response vs file attachment headers for the download
- Whether `export_hash` is a SHA-256 of the file bytes or the WorkDescription JSON

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data Model (read first)
- `app/models/work_description.py` — WorkDescription, ProvenanceTag, JESFactorScore,
  DraftDuty, OGRecommendation; all fields the export renders from. FINALIZED Phase 1 —
  do not change field names without migration script.

### TBS Classification Authority
- `data/directive_on_classification.txt` — TBS Directive on Classification 2021;
  defines the legal requirements for a Work Description and authoritative section
  structure. Use for DOCX template section design.

### Phase 7 Reviews (carry forward)
- `.planning/phases/07-jes-scoring/07-REVIEWS.md` — Cross-AI review of Phase 7
  plans + live code. D-01/D-02/D-11/D-12 decisions are directly drawn from
  concerns raised here (Codex HIGH: completion semantics; code review MEDIUM:
  silent points=None exclusion).
- `.planning/phases/07-jes-scoring/07-REVIEW.md` — Code review findings for
  Phase 7 implementation. MEDIUM bug at `jes_service.py:76-77` informs D-02.

### NOC Job Description Guidance
- `data/job description guide` — HRSDC Job Descriptions Handbook (2007). Annex 2.1
  documents the general GC JD field structure. **Not the format to follow** (TBS WD
  format takes precedence per D-04), but useful for understanding how NOC duty
  statements should be framed in the exported document.

### Established Service Patterns
- `app/services/jes_service.py` — Most recent service implementation; follow its
  pattern for async service structure, `asyncio.to_thread` for SQLite, stage gate
  validation, and error handling.
- `app/api/jes_scoring.py` — Most recent router implementation; follow HTMX dual-path
  pattern (`HX-Request` header detection → TemplateResponse vs JSON).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `WorkDescription.export_hash` and `WorkDescription.exported_at` — already on the
  model, just needs to be written on successful export
- `WorkDescription.stage = "exported"` — already a valid stage literal; export service
  advances to it post-generation
- `ProvenanceTag` fields `source_type`, `source_id`, `source_version`, `retrieved_date`
  — all the data needed to render citations and build the version manifest is already
  on the model

### Established Patterns
- Services live in `app/services/{feature}_service.py`; routers in `app/api/{feature}.py`
- Router uses `templates_dir` resolution pattern (see `app/api/jes_scoring.py`)
- HTMX dual-path: `HX-Request` header → `TemplateResponse` vs JSON response
- Stage gate validation returns 422 if prerequisite stage not met (e.g., `jd_drafted`
  check before JES scoring)
- `asyncio.to_thread` wraps all SQLite reads/writes from async context
- `instructor` singleton at module scope (not needed for export, but pattern is established)

### Integration Points
- Export router mounts at `app/main.py` alongside existing routers
- Wizard navigation: `step_export.html` is the terminal wizard step; after export
  the advisor has completed the V1 workflow
- `app/templates/base.html` is the only existing template — all wizard steps follow
  same base

</code_context>

<specifics>
## Specific Ideas

- Pre-export validator should produce a structured error object (not just a string)
  so the UI can render per-factor error cards rather than a generic message
- The version manifest in the document can be a table: | Source | ID | Version | Date |
  with one row per unique ProvenanceTag source_version in the WorkDescription
- docxtpl + python-docx for DOCX generation (already referenced in REQUIREMENTS.md
  EXP-01); no new library decisions needed for DOCX
- WeasyPrint ARM64 verification todo (from STATE.md) should be closed as a
  separate task/note, not a Phase 8 blocker — D-08 handles it with 501 stub

</specifics>

<deferred>
## Deferred Ideas

- PDF export via WeasyPrint — deferred until ARM64 Pango/Cairo compatibility
  confirmed on Jane (Jetson AGX Orin). Stub route returns 501 in Phase 8.
- Pre-export completeness validator for TBS mandatory WD elements (financial
  authorities, physical conditions, freedom to act, contacts) — this is EXP-02,
  a v2 requirement. Phase 8 gates on JES completeness only (D-01/D-02).
- Advisor review checklist with per-element sign-off (EXP-03, v2).
- Bilingual export / French translation flag (LANG-01, v2).

</deferred>

---

*Phase: 08-export*
*Context gathered: 2026-06-02*
