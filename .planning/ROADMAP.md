# Roadmap: JD Builder

**9 phases** | **21 v1 requirements** | Fine granularity

---

## Phase Summary

| # | Phase | Goal | Requirements |
|---|-------|------|--------------|
| 1 | Project Foundation | FastAPI app boots with validated config, Ollama pre-warm, and finalized WorkDescription + ProvenanceTag data model | DATA-01, DATA-02, DATA-03 |
| 2 | NOC Data Pipeline | NOC 2021 unit group profiles are fully indexed in FTS5 + sqlite-vec with version hashes and embedding model assertion | PIPE-01, PIPE-04, PIPE-05 |
| 3 | CA + JES Data Pipeline | Collective agreement restriction clauses and JES factor objects are indexed in SQLite, keyed by OG code | PIPE-02, PIPE-03, CA-01 |
| 4 | NL→NOC Mapping | Advisor inputs plain-language work description and receives ranked NOC candidates with cited duty matches | MAP-01, MAP-02 |
| 5 | OG Classification | System presents top 3 OG candidates with inclusions/exclusions; advisor confirms OG and level before generation; AS vs EC disambiguation surfaced for policy-adjacent positions | CLASS-01, CLASS-02, CLASS-03 |
| 6 | JD Generation | System drafts verbatim NOC-sourced duties with full ProvenanceTag; advisor additions are flagged; orphan statement check runs post-draft; WD persisted | JD-01, JD-02, JD-03, JD-04 |
| 7 | JES Scoring | System produces a per-factor JES scoring sheet via the configured local generation model (`gemma4:31b` by default) with Pydantic-validated structured output | JES-01 |
| 8 | Export | Advisor exports completed WD to DOCX and PDF with rendered source citations and a version manifest | EXP-01 |
| 9 | 4/4 | Complete    | 2026-06-03 |

---

## Phase Details

### Phase 1: Project Foundation
**Goal:** Developer can start the FastAPI application, confirm all required environment variables are loaded, verify Ollama is reachable and configured models are present, and inspect the fully defined WorkDescription + ProvenanceTag Pydantic models and SQLite schema — all before any feature code is written.
**Depends on:** Nothing
**Requirements:** DATA-01, DATA-02, DATA-03
**UI hint:** no
**Success criteria:**
1. `uvicorn app.main:app` starts without error; `GET /health` returns 200 with Ollama model availability status.
2. Starting the app with a missing required environment variable produces an immediate startup failure with a descriptive error message naming the missing variable.
3. Starting the app when the configured Ollama model is absent produces a loud startup failure — the app does not silently degrade.
4. The WorkDescription Pydantic model includes all TBS-required WD fields and every content element carries a ProvenanceTag; the SQLite schema including `wd_audit_log` is created on first startup.
**Plans:** 3 plans
Plans:
- [x] 01-01-PLAN.md — Project scaffold, sqlite-vec install, all Wave 0 test stubs
- [x] 01-02-PLAN.md — app/config.py, app/models/work_description.py, app/db.py (DATA-01, DATA-02)
- [x] 01-03-PLAN.md — app/main.py, app/api/health.py, app/templates/base.html + human verify (DATA-03)

### Phase 2: NOC Data Pipeline
**Goal:** Developer can run the NOC ingest script and confirm that NOC 2021 unit group profiles are queryable via FTS5 full-text search, vector search via sqlite-vec using nomic-embed-text, and that each source document has a content hash and version label recorded; the app refuses to start if the embedding model in the index metadata does not match the configured model.
**Depends on:** Phase 1
**Requirements:** PIPE-01, PIPE-04, PIPE-05
**UI hint:** no
**Success criteria:**
1. Running the NOC ingest script produces a populated FTS5 index and a sqlite-vec embedding index; an FTS5 query returns matching unit group records.
2. Each ingested NOC source document has a `content_hash` and `version_label` recorded; each derived record stores the source version hash it was derived from.
3. Changing the configured embedding model name and restarting the app produces a startup error citing a model name mismatch — the app does not serve queries.
4. Re-running the ingest script with unchanged source files is idempotent (no duplicate records, hashes match).
**Plans:** 4 plans
Plans:
- [x] 02-01-PLAN.md — Wave 0 test stubs (test_noc_ingest.py, test_noc_startup.py, conftest noc_db fixture)
- [x] 02-02-PLAN.md — app/db.py NOC schema DDL + assert_noc_index_model() (PIPE-04, PIPE-05)
- [x] 02-03-PLAN.md — scripts/ingest_noc.py all 5 stages (PIPE-01, PIPE-04)
- [x] 02-04-PLAN.md — app/main.py lifespan integration + full suite green (PIPE-05)

### Phase 3: CA + JES Data Pipeline
**Goal:** Developer can run the CA ingest script and confirm that restriction, scope, and exclusion clauses are extracted per OG code and stored as structured records; developer can run the JES ingest script and confirm that per-factor degree descriptors and point ranges are stored as structured factor objects queryable by `(og_code, factor_name)`; TBS policy documents (`data/directive_on_classification.txt`, `data/policy_on_people_management.txt`) are ingested and indexed for use in OG classification logic.
**Depends on:** Phase 1
**Requirements:** PIPE-02, PIPE-03, CA-01
**UI hint:** no
**Success criteria:**
1. Running the CA ingest script produces structured restriction/scope/exclusion clause records in SQLite; querying by OG code returns the correct clauses for that group.
2. Running the JES ingest script produces structured factor objects with `og_code`, `factor_name`, `degree_descriptors`, and `point_range`; querying by `(og_code, factor_name)` returns the correct factor descriptor.
3. Both ingest scripts record content hashes per source document and link derived records to their source hash (PIPE-04 coverage for these corpora).
4. Both ingest scripts are idempotent on unchanged source files.
**Plans:** 4 plans
Plans:
- [x] 03-01-PLAN.md — Wave 0 test stubs (test_ca_ingest.py, test_jes_ingest.py, test_policy_ingest.py, ca_jes_db fixture)
- [x] 03-02-PLAN.md — app/db.py CA_JES_SCHEMA_DDL extension (ca_clauses, jes_factors, policy_chunks, policy_fts)
- [x] 03-03-PLAN.md — scripts/ingest_ca.py + ingest_jes.py + ingest_policy.py (PIPE-02, PIPE-03, CA-01)
- [x] 03-04-PLAN.md — Real-data ingest run + human spot-check on LLM extraction quality

### Phase 4: NL→NOC Mapping
**Goal:** Advisor can submit a plain-language description of work to the `/api/noc/map` endpoint and receive a ranked list of NOC unit group candidates — each showing the NOC code, unit group title, TEER level, and the specific NOC duty statements that best matched — produced by the three-stage FTS5 → embedding rerank → configured local generation model justification pipeline.
**Depends on:** Phase 2
**Requirements:** MAP-01, MAP-02
**UI hint:** yes
**Success criteria:**
1. `POST /api/noc/map` with a plain-language work description returns a ranked list of NOC unit group candidates without error.
2. Each candidate includes NOC code, unit group title, TEER level, and the verbatim NOC duty statements from the database that supported the match.
3. The pipeline runs all three stages in sequence (FTS5 shortlist → embedding rerank → configured local generation model justification); the LLM only sees pre-screened candidates, not all 900 profiles.
4. Advisor can confirm a NOC match; the confirmed match is stored on the WorkDescription record.
**Plans:** 4 plans
Plans:
- [ ] 04-01-PLAN.md — Wave 0: test stubs, noc_mapping_db fixture, rebuild_noc_vectors.py
- [ ] 04-02-PLAN.md — Pydantic models (NOCCandidate, NOCRankingResult) + instructor client singleton
- [ ] 04-03-PLAN.md — 3-stage pipeline service, wd_store, FastAPI router, DB schema additions
- [ ] 04-04-PLAN.md — HTMX wizard templates, CSS, full suite green + human verify

### Phase 5: OG Classification
**Goal:** For a confirmed NOC match, the system presents the top 3 occupational group candidates side-by-side — each citing the relevant TBS OG definition excerpt, inclusions, and exclusions — and will not begin JD content generation until the advisor explicitly confirms an OG and level. For positions with policy-related duties, the system surfaces the AS vs. EC distinction test with verbatim citations from `data/directive_on_classification.txt` before the advisor confirms.
**Depends on:** Phase 3, Phase 4
**Requirements:** CLASS-01, CLASS-02, CLASS-03
**UI hint:** yes
**Success criteria:**
1. `POST /classify-og` with a confirmed NOC match returns 3 OG candidates, each with OG code, name, definition excerpt, and relevant inclusions and exclusions cited from TBS source documents.
2. Attempting to call the JD generation endpoint without a confirmed OG returns a 422 error — the gate is enforced at the API layer.
3. Advisor can confirm an OG and level; the confirmed classification is stored on the WorkDescription record.
4. When the work description contains policy-related duties, the response includes an AS vs. EC disambiguation block showing the TBS internal-vs-public-facing test with verbatim citations from `data/directive_on_classification.txt`.
**Plans:** 4 plans
Plans:
- [x] 05-01-PLAN.md — Wave 0: og_definitions DDL, ingest script, test stubs, og_db fixture, noc_confirmed.html form
- [x] 05-02-PLAN.md — app/ai/og_ranking.py: Pydantic models, OG_LEVELS, instructor singleton, prompt constants
- [x] 05-03-PLAN.md — og_classifier.py pipeline, og_classification.py router, app/main.py registration
- [x] 05-04-PLAN.md — HTMX templates, Phase 5 CSS, full suite green + human verify

### Phase 6: JD Generation
**Goal:** With a confirmed NOC match and OG classification, the system drafts key duties by selecting verbatim text from NOC profile records in the database; every duty carries a structured ProvenanceTag; advisor-added content that has no source record is tagged distinctly; after drafting, an orphan statement check flags any duty that contradicts the established functional authority for the confirmed OG; the WD is persisted to SQLite after each state transition.
**Depends on:** Phase 5
**Requirements:** JD-01, JD-02, JD-03, JD-04
**UI hint:** yes
**Success criteria:**
1. `POST /generate-duties` returns a list of duties where every item is verbatim text from a NOC profile record in the database — no free-form generated text appears as a duty.
2. Every duty carries a structured ProvenanceTag with source type, NOC code, section name, statement text, and source document version hash.
3. Any content the advisor adds that has no source record is tagged `advisor-added / not from authoritative source` in the data model and visually distinguished in the UI.
4. After duty confirmation, the WorkDescription record is persisted to SQLite with all ProvenanceTags intact.
5. `POST /check-orphan-statements` runs against the confirmed duty list and returns a list of flagged duties, each citing the functional authority rule violated (document name and article/section) — a clean result returns an empty flag list, not an error.
**Plans:** 4 plans
Plans:
- [x] 06-01-PLAN.md — Wave 0: test stubs, jd_db fixture, og_confirmed.html CTA activation, CLASS-02 gate test
- [x] 06-02-PLAN.md — app/ai/jd_ranking.py: Pydantic models, instructor singleton, prompt constants
- [x] 06-03-PLAN.md — jd_service.py pipeline + jd_generation.py router + app/main.py registration
- [x] 06-04-PLAN.md — HTMX wizard templates, Phase 6 CSS layer 9, full suite green + human verify

### Phase 7: JES Scoring
**Goal:** With a confirmed WD and duty list, the system generates a JES scoring sheet for the confirmed OG by making one configured local generation model call per JES factor — injecting the full factor descriptor and degree definitions fresh per call — returning a structured scoring object validated by Pydantic via `instructor` with up to 3 retries.
**Depends on:** Phase 3, Phase 6
**Requirements:** JES-01
**UI hint:** yes
**Success criteria:**
1. `POST /score-jes` returns a complete JES scoring sheet with one structured result object per factor, each containing a degree rating and rationale.
2. Each factor call injects the full factor descriptor and all degree definitions from the database record for that `(og_code, factor_name)` — never from a summary or cached prompt.
3. If a model call returns malformed output, `instructor` retries up to 3 times; a failure after 3 attempts returns a descriptive error for that factor, not a silent null.
4. The scoring sheet is stored on the WorkDescription record with ProvenanceTags linking each factor rating to its JES source record.
**Plans:** 4 plans
Plans:
- [x] 07-01-PLAN.md — Wave 0: test stubs + jes_db fixture (JES-01)
- [x] 07-02-PLAN.md — app/ai/jes_scoring.py: JESFactorRating model, jes_instructor_client singleton, prompt constants
- [x] 07-03-PLAN.md — jes_service.py pipeline + jes_scoring.py router + app/main.py registration
- [x] 07-04-PLAN.md — HTMX wizard templates, CSS layer 10, jd_confirmed.html CTA activation + human verify

### Phase 8: Export
**Goal:** Advisor can export the completed WorkDescription to DOCX and PDF; every content element's citation is rendered directly from its ProvenanceTag object (not from prose written into a template); the export includes a version manifest listing all source documents and their content hashes.
**Depends on:** Phase 6, Phase 7
**Requirements:** EXP-01
**UI hint:** yes
**Success criteria:**
1. `GET /export/{wd_id}/docx` and `GET /export/{wd_id}/pdf` both return valid, downloadable files.
2. Every duty, JES rating, and content element in the exported document displays its source citation rendered from the ProvenanceTag object on that element — no citation prose is hardcoded in the template.
3. The exported document includes a version manifest section listing every source document used (NOC, CA, JES) with its content hash and version label.
4. Any advisor-added content renders with a visible "advisor-added / not from authoritative source" marker in both DOCX and PDF outputs.
**Plans:** 4 plans
Plans:
- [x] 08-01-PLAN.md — Wave 0: export_db fixture, contract tests, docxtpl TBS WD template artifact (committed 2026-06-02)
- [x] 08-02-PLAN.md — export_service.py: pre-export gate, version manifest, docxtpl render, stage advance (EXP-01)
- [x] 08-03-PLAN.md — export.py router (docx + pdf 501) + main.py mount + /wizard/export route (EXP-01)
- [x] 08-04-PLAN.md — step_export.html, export_result partial, activate JES CTA, CSS layer 11 (Tasks 1+2 complete; Task 3 human-verify pending)

### Phase 08.1: Advisor override and per-factor retry for incomplete JES scoring (INSERTED)

**Goal:** When JES scoring leaves factors incomplete (`level=-1` or `points=None`), the advisor can either re-run a single factor through the model or override it manually with their own level/points/rationale — and the export gate accepts advisor-overridden factors. Closes the gap where the export validator blocks a WorkDescription with no recovery path other than re-running the full 10-factor pipeline.
**Requirements**: JES-01 (extension)
**UI hint:** yes
**Success criteria:**
1. For any JES factor with `level=-1` or `points=None`, the JES factor card in the UI shows a **Retry** button that re-runs the model call for that single factor and updates the score inline.
2. For the same failed factors, the card shows an **Override** button that opens a form: the advisor enters `level` (1–4 or whatever the factor supports), `points` (or auto-derived from the factor's `point_values` JSON), and a free-text `rationale`; on submit, the factor's `advisor_adjusted=True`, `advisor_adjusted_level=<level>`, and `advisor_adjustment_rationale=<text>` are populated and the `provenance.source_type` flips to `ADVISOR`.
3. `validate_export_readiness` accepts factors where `advisor_adjusted=True` AND the advisor's level/points are valid; only `level=-1` (LLM failure) or `points is None` on a non-overridden factor still blocks.
4. The blocked-export error block (added in Phase 8 fix `38eec77`) now shows a **"Why is this blocked?"** link to the JES scoring page where the failed factors are listed; the user can resolve them inline.
5. Tests cover: retry endpoint, override endpoint, validator accepts advisor-overridden factors, validator still rejects unoverridden failures, the override form is rendered on the card, the retry updates the factor in place.
**Plans:** 3/3 plans complete
Plans:
- [x] 08.1-01-PLAN.md — Service layer: per-factor retry, per-factor override, validator update
- [x] 08.1-02-PLAN.md — API: POST /api/jes/retry/{wd_id}/{factor_name}, POST /api/jes/override/{wd_id}/{factor_name}, router mount + tests
- [x] 08.1-03-PLAN.md — UI: per-card Retry/Override buttons, override form partial, jes_scores.html activation wiring, CSS layer 12

### Phase 9: DND DRF Integration
**Goal:** For a WorkDescription identified as a DND position, the system surfaces Departmental Results Framework program linkages — connecting the position's duties to DRF programs and expected results — sourced from the DRF CSV dataset already in `data/`.
**Depends on:** Phase 6
**Requirements:** DRF-01
**UI hint:** yes
**Success criteria:**
1. When the WD is flagged as a DND position, `GET /drf-links/{wd_id}` returns candidate DRF program linkages for the position's duties.
2. Each linkage cites the DRF program name, expected result, and the source row from the DRF CSV dataset.
3. Advisor-confirmed DRF linkages are stored on the WorkDescription record and rendered in the exported document.
**Plans:** 4/4 plans complete
Plans:
- [x] 09-01-PLAN.md — Wave 1: WorkDescription model fields, DRF_SCHEMA_DDL, test stubs + drf_db fixture
- [x] 09-02-PLAN.md — Wave 2: scripts/ingest_drf.py + app/services/drf_service.py (keyword matching + confirmation)
- [x] 09-03-PLAN.md — Wave 3: API router, main.py mount, export_service extension, DOCX template rebuild
- [x] 09-04-PLAN.md — Wave 4: inline DRF panel on step_export (revised design) + CSS Layer 14 + WD default is_dnd_position=True + flag-dnd route removed + DOCX Section 6 gate moved to linkage count + 2 new active tests

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Foundation | 3/3 | Complete | 2026-05-28 |
| 2. NOC Data Pipeline | 4/4 | Complete | 2026-05-28 |
| 3. CA + JES Data Pipeline | 4/4 | Complete | 2026-06-01 |
| 4. NL→NOC Mapping | 4/4 | Complete | 2026-06-02 |
| 5. OG Classification | 4/4 | Complete | 2026-06-02 |
| 6. JD Generation | 4/4 | Complete | 2026-06-02 |
| 7. JES Scoring | 4/4 | Complete | 2026-06-02 |
| 8. Export | 4/4 | Complete (08-01 + 08-02 + 08-03 + 08-04 complete: export scaffold + service + router + wizard step + CSS Layer 11) | 2026-06-02 |
| 8.1. JES Advisor Override & Per-Factor Retry | 3/3 | Complete | 2026-06-03 |
| 9. DND DRF Integration | 4/4 | Complete (09-01 + 09-02 + 09-03 + 09-04 complete: model + DDL + ingest + service + API router + export integration + DOCX template + inline panel on /wizard/export; 09-04 shipped the revised inline-panel design with /flag-dnd route removed and DOCX Section 6 gated on linkage count) | 2026-06-03 |
