# Phase 8: Export - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-02
**Phase:** 08-export
**Areas discussed:** Export gate & data quality, Document structure & TBS format, PDF dependency strategy, UI placement & wizard step

---

## Export Gate & Data Quality

### JES data completeness before export

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-export validation | Check for points=None or level=-1 before generating; block with named error | ✓ |
| Warn but allow | Show banner, let advisor download with incomplete factors | |
| Trust the data | Export whatever is on the WorkDescription | |

**User's choice:** Pre-export validation — block export if any factor is incomplete.
**Notes:** Directly addresses Phase 7 code review MEDIUM bug (silent points=None
exclusion from jes_total) and Codex review HIGH concern (level=-1 factors advancing
to jes_scored). Phase 8 adds the hard gate Phase 7 did not enforce.

### Failed factors — block or warn in document

| Option | Description | Selected |
|--------|-------------|----------|
| Block export | All JES factors must have level > 0 and points not None | ✓ |
| Allow with document warning | Export proceeds; failed factors get SCORING INCOMPLETE marker | |

**User's choice:** Block export.
**Notes:** Aligns with "legally defensible" principle from PROJECT.md. A JES sheet
with failed factors is not a complete Work Description.

---

## Document Structure & TBS Format

### Template format selection

| Option | Description | Selected |
|--------|-------------|----------|
| Use this guide's Annex 2.1 | Generic NOC handbook structure (Main functions, Duties, Working conditions, Employment Requirements) | |
| Use TBS WD format | Formal GoC Work Description structure (position header, org context, key activities, JES sheet, qualifications, provenance manifest) | ✓ |
| Hybrid — TBS WD structure, this guide for language | TBS format for structure, NOC handbook for duty framing guidance | |

**User's choice:** TBS WD format.
**Notes:** The `data/job description guide` file is the HRSDC Employers' Handbook (2007) — 
a general guide, not the formal TBS WD template. User confirmed TBS WD format is correct.
`data/directive_on_classification.txt` is the authoritative source for section structure.

---

## PDF Dependency Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| DOCX first, PDF deferred | Implement DOCX; PDF stub returns 501; defer until WeasyPrint ARM64 verified | ✓ |
| Both with runtime check | Implement both; startup check for Pango/Cairo; PDF returns 503 if missing | |
| Both — assume deps present | Implement both; treat WeasyPrint todo as pre-flight only | |

**User's choice:** DOCX first, PDF deferred.
**Notes:** STATE.md has open todo to verify WeasyPrint Pango/Cairo on Jane (Jetson AGX
Orin). Implementing a 501 stub satisfies the route surface without risk.

---

## UI Placement & Wizard Step

### Wizard placement

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated export step | New step_export.html with summary + validation errors + Download DOCX CTA | ✓ |
| Button on JES completion page | No new step; export button added to jes_scored view | |

**User's choice:** Dedicated export step.
**Notes:** Keeps wizard flow linear. Export page shows position summary, JES total,
version manifest preview, and any blocking validation errors inline.

### Re-export behaviour

| Option | Description | Selected |
|--------|-------------|----------|
| Allow re-export | Regenerate on every click; update export_hash and exported_at each time | ✓ |
| One-time with confirmation | First export is "official"; re-export requires explicit confirmation | |

**User's choice:** Allow re-export without confirmation.

---

## Claude's Discretion

- Internal file naming / temp file handling for docxtpl rendering
- Exact DOCX section/heading styles and table layouts
- Streaming response vs file attachment headers
- export_hash computation method (file bytes SHA-256 vs WD JSON hash)

## Deferred Ideas

- PDF export (WeasyPrint ARM64 dependency risk)
- Pre-export completeness validator for TBS mandatory WD elements (EXP-02, v2)
- Advisor review checklist with per-element sign-off (EXP-03, v2)
- Bilingual export / French translation flag (LANG-01, v2)
