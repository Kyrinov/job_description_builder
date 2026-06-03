# Retrospective: JD Builder

---

## Milestone: v1.0 — MVP

**Shipped:** 2026-06-03
**Phases:** 10 (incl. 8.1) | **Plans:** 38 | **Timeline:** 7 days

### What Was Built

- NOC 2021 FTS5 + sqlite-vec ingest pipeline with provenance tracking
- CA restriction clause + JES factor + TBS policy data pipelines
- Three-stage NL→NOC mapping (FTS5 → embedding rerank → LLM justification) with HTMX wizard
- OG classification with verbatim TBS citations, AS/EC disambiguation, and hard stage gate
- Provenance-first JD generation: every duty is verbatim NOC text with structured ProvenanceTag
- Per-factor JES scoring with instructor retry; per-factor advisor override/retry (Phase 8.1)
- DOCX export with ProvenanceTags as rendered citations and version manifest
- DRF integration: inline candidate panel on /wizard/export; DOCX Section 6 for confirmed linkages

### What Worked

- **TDD wave pattern**: Wave 0 (stubs) → Wave 1 (models) → Wave 2 (service) → Wave 3 (router) → Wave 4 (UI) produced no regressions across 38 plans. Each plan started with failing tests.
- **ProvenanceTag first**: defining the provenance model in Phase 1 before any service code meant every downstream phase could build to the same contract without ambiguity.
- **HTMX dual-path pattern**: every route returning HTML for HX-Request and JSON for non-HX-Request made testing trivial and the API useful independently.
- **instructor + retry**: routing all LLM structured output through instructor prevented silent null results and surfaced exactly which factors failed, enabling Phase 8.1's targeted fix.
- **Committed binary artifact** for DOCX template: deterministic, self-verifying build script meant the template was never "stale" between phases.
- **Phase insertion (8.1)**: recognizing that the export was blocked with no recovery path and inserting a small, focused phase (3 plans, 1 day) was the right call — avoided a messy partial fix in Phase 8.

### What Was Inefficient

- **REQUIREMENTS.md not updated during phases**: the traceability table accumulated "Pending" entries for all shipped requirements, requiring a bulk fix at milestone close. Should have updated on each phase completion.
- **02-02-SUMMARY.md never written**: plan 02-02 was completed but no summary was created. A gap in the archive.
- **Phase 4 deferred bugs**: both the noc_fts DDL bug and Starlette TemplateResponse deprecation were flagged and deferred, adding to v2 debt rather than being fixed inline.
- **Phase 9 design flip mid-execution**: the /wizard/drf separate step was built (2 commits), then reverted (2 commits), then rebuilt as the inline panel. The forward commits were clean but the exploration cost ~30 min.

### Patterns Established

- **CSS Layer system**: layers 1–14 appended in phase order to main.css. Layer-scoped selectors prevent bleedthrough. Works well for a single-CSS-file HTMX app.
- **Per-router rebootstrap in tests**: each phase's test module owns its own `_bootstrapped` global and re-imports from `app.main` — prevents module-level state collisions when pytest runs all tests in one process.
- **docxtpl separate-row for/endfor**: patch_xml regex is greedy (matches LAST `{%tr %}` tag in a row) — for and endfor markers must be in their own rows above and below the data row.
- **DashScope as Stage 3 drop-in**: qwen3-max via dashscope-intl.aliyuncs.com accepts OpenAI-compatible API; `AsyncOpenAI(base_url=..., api_key=...)` works with instructor unchanged. Local model for factual retrieval; cloud model for structured reasoning.

### Key Lessons

1. **Insert phases fearlessly**: Phase 8.1 was the right abstraction. Small, scoped, time-boxed. Don't hack a fix into an existing phase to avoid inserting a new one.
2. **Commit planning artifacts alongside code commits**: ROADMAP.md and STATE.md fell out of sync from REQUIREMENTS.md because they were updated separately. A single "docs(phase-N): complete plan" commit should always update all three.
3. **The export gate is a forcing function**: designing export to fail on incomplete data (invalid JES factors, missing confirmed OG) drove Phase 8.1 and prevented silent bad data from reaching the output.
4. **ProvenanceTag > prose citations**: defining ProvenanceTag at the model level meant export_service.py could render citations from data without any hardcoded strings. Template never needs to change when citation format changes.
5. **ARM64 dependency risk**: pin everything. DuckDB 1.5.3 was pinned explicitly because 1.4.x had broken aarch64 wheels. Check ARM64 wheel availability before adding any new package.

### Cost Observations

- DashScope qwen3-max used for Stage 3 NL→NOC justification and OG classification LLM calls
- Local gemma4:31b used for CA ingest extraction (batch, not latency-sensitive)
- instructor retry cost: negligible at 3-attempt max; no runaway retries observed
- 7 days end-to-end from scaffold to shipped — all 21 requirements delivered

---

## Cross-Milestone Trends

| Metric | v1.0 |
|--------|------|
| Timeline | 7 days |
| Phases | 10 (incl. 1 inserted) |
| Plans | 38 |
| Tests at ship | 188 |
| Requirements delivered | 21/21 |
| Regressions | 0 |
| Phase insertions | 1 (8.1) |
| Phase reverts needed | 0 (2 mid-phase reverts in 09-04, not full phase reverts) |
