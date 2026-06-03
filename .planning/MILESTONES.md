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
