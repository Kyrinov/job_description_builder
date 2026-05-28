# Roadmap: JD Builder

**9 phases** | **19 v1 requirements** | Fine granularity

---

## Phase Summary

| # | Phase | Goal | Requirements |
|---|-------|------|--------------|
| 1 | Project Foundation | FastAPI app boots with validated config, Ollama pre-warm, and finalized WorkDescription + ProvenanceTag data model | DATA-01, DATA-02, DATA-03 |
| 2 | NOC Data Pipeline | NOC 2021 unit group profiles are fully indexed in FTS5 + sqlite-vec with version hashes and embedding model assertion | PIPE-01, PIPE-04, PIPE-05 |
| 3 | CA + JES Data Pipeline | Collective agreement restriction clauses and JES factor objects are indexed in SQLite, keyed by OG code | PIPE-02, PIPE-03, CA-01 |
| 4 | NL→NOC Mapping | Advisor inputs plain-language work description and receives ranked NOC candidates with cited duty matches | MAP-01, MAP-02 |
| 5 | OG Classification | System presents top 3 OG candidates with inclusions/exclusions; advisor confirms OG and level before generation | CLASS-01, CLASS-02 |
| 6 | JD Generation | System drafts verbatim NOC-sourced duties with full ProvenanceTag; advisor additions are flagged; WD persisted | JD-01, JD-02, JD-03 |
| 7 | JES Scoring | System produces a per-factor JES scoring sheet via Qwen3 in `/think` mode with Pydantic-validated structured output | JES-01 |
| 8 | Export | Advisor exports completed WD to DOCX and PDF with rendered source citations and a version manifest | EXP-01 |
| 9 | DND DRF Integration | For DND positions, system surfaces DRF program linkages connecting position duties to departmental expected results | DRF-01 |

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
**Plans:** TBD

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
**Plans:** TBD

### Phase 3: CA + JES Data Pipeline
**Goal:** Developer can run the CA ingest script and confirm that restriction, scope, and exclusion clauses are extracted per OG code and stored as structured records; developer can run the JES ingest script and confirm that per-factor degree descriptors and point ranges are stored as structured factor objects queryable by `(og_code, factor_name)`.
**Depends on:** Phase 1
**Requirements:** PIPE-02, PIPE-03, CA-01
**UI hint:** no
**Success criteria:**
1. Running the CA ingest script produces structured restriction/scope/exclusion clause records in SQLite; querying by OG code returns the correct clauses for that group.
2. Running the JES ingest script produces structured factor objects with `og_code`, `factor_name`, `degree_descriptors`, and `point_range`; querying by `(og_code, factor_name)` returns the correct factor descriptor.
3. Both ingest scripts record content hashes per source document and link derived records to their source hash (PIPE-04 coverage for these corpora).
4. Both ingest scripts are idempotent on unchanged source files.
**Plans:** TBD

### Phase 4: NL→NOC Mapping
**Goal:** Advisor can submit a plain-language description of work to the `/map-to-noc` endpoint and receive a ranked list of NOC unit group candidates — each showing the NOC code, unit group title, TEER level, and the specific NOC duty statements that best matched — produced by the three-stage FTS5 → embedding rerank → Qwen3 justification pipeline.
**Depends on:** Phase 2
**Requirements:** MAP-01, MAP-02
**UI hint:** yes
**Success criteria:**
1. `POST /map-to-noc` with a plain-language work description returns a ranked list of NOC unit group candidates without error.
2. Each candidate includes NOC code, unit group title, TEER level, and the verbatim NOC duty statements from the database that supported the match.
3. The pipeline runs all three stages in sequence (FTS5 shortlist → embedding rerank → Qwen3 justification); the LLM only sees pre-screened candidates, not all 900 profiles.
4. Advisor can confirm a NOC match; the confirmed match is stored on the WorkDescription record.
**Plans:** TBD

### Phase 5: OG Classification
**Goal:** For a confirmed NOC match, the system presents the top 3 occupational group candidates side-by-side — each citing the relevant TBS OG definition excerpt, inclusions, and exclusions — and will not begin JD content generation until the advisor explicitly confirms an OG and level.
**Depends on:** Phase 3, Phase 4
**Requirements:** CLASS-01, CLASS-02
**UI hint:** yes
**Success criteria:**
1. `POST /classify-og` with a confirmed NOC match returns 3 OG candidates, each with OG code, name, definition excerpt, and relevant inclusions and exclusions cited from TBS source documents.
2. Attempting to call the JD generation endpoint without a confirmed OG returns a 422 error — the gate is enforced at the API layer.
3. Advisor can confirm an OG and level; the confirmed classification is stored on the WorkDescription record.
**Plans:** TBD

### Phase 6: JD Generation
**Goal:** With a confirmed NOC match and OG classification, the system drafts key duties by selecting verbatim text from NOC profile records in the database; every duty carries a structured ProvenanceTag; advisor-added content that has no source record is tagged distinctly; the WD is persisted to SQLite after each state transition.
**Depends on:** Phase 5
**Requirements:** JD-01, JD-02, JD-03
**UI hint:** yes
**Success criteria:**
1. `POST /generate-duties` returns a list of duties where every item is verbatim text from a NOC profile record in the database — no free-form generated text appears as a duty.
2. Every duty carries a structured ProvenanceTag with source type, NOC code, section name, statement text, and source document version hash.
3. Any content the advisor adds that has no source record is tagged `advisor-added / not from authoritative source` in the data model and visually distinguished in the UI.
4. After duty confirmation, the WorkDescription record is persisted to SQLite with all ProvenanceTags intact.
**Plans:** TBD

### Phase 7: JES Scoring
**Goal:** With a confirmed WD and duty list, the system generates a JES scoring sheet for the confirmed OG by making one Qwen3 `/think` call per JES factor — injecting the full factor descriptor and degree definitions fresh per call — returning a structured scoring object validated by Pydantic via `instructor` with up to 3 retries.
**Depends on:** Phase 3, Phase 6
**Requirements:** JES-01
**UI hint:** yes
**Success criteria:**
1. `POST /score-jes` returns a complete JES scoring sheet with one structured result object per factor, each containing a degree rating and rationale.
2. Each factor call injects the full factor descriptor and all degree definitions from the database record for that `(og_code, factor_name)` — never from a summary or cached prompt.
3. If a Qwen3 call returns malformed output, `instructor` retries up to 3 times; a failure after 3 attempts returns a descriptive error for that factor, not a silent null.
4. The scoring sheet is stored on the WorkDescription record with ProvenanceTags linking each factor rating to its JES source record.
**Plans:** TBD

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
**Plans:** TBD

### Phase 9: DND DRF Integration
**Goal:** For a WorkDescription identified as a DND position, the system surfaces Departmental Results Framework program linkages — connecting the position's duties to DRF programs and expected results — sourced from the DRF CSV dataset already in `data/`.
**Depends on:** Phase 6
**Requirements:** DRF-01
**UI hint:** yes
**Success criteria:**
1. When the WD is flagged as a DND position, `GET /drf-links/{wd_id}` returns candidate DRF program linkages for the position's duties.
2. Each linkage cites the DRF program name, expected result, and the source row from the DRF CSV dataset.
3. Advisor-confirmed DRF linkages are stored on the WorkDescription record and rendered in the exported document.
**Plans:** TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Foundation | 0/? | Not started | - |
| 2. NOC Data Pipeline | 0/? | Not started | - |
| 3. CA + JES Data Pipeline | 0/? | Not started | - |
| 4. NL→NOC Mapping | 0/? | Not started | - |
| 5. OG Classification | 0/? | Not started | - |
| 6. JD Generation | 0/? | Not started | - |
| 7. JES Scoring | 0/? | Not started | - |
| 8. Export | 0/? | Not started | - |
| 9. DND DRF Integration | 0/? | Not started | - |
