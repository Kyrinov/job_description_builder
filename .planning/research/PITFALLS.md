# Domain Pitfalls: GoC JD Builder

**Domain:** Government of Canada HR classification tooling + local LLM + RAG
**Researched:** 2026-05-28
**Sources:** Prototype CONCERNS.md, NEW-VERSION-FINDINGS.md, TBS directives, Ollama/Jetson issue tracker, LLM reliability research 2025

---

## Critical Pitfalls

Mistakes that cause rewrites, grievances, or legal invalidation of output.

---

### CRITICAL-01: JES Structural Entropy — Array Collapse in Ratings

**What goes wrong:** When asking a local model (Qwen/llama) to produce a full JES scoring sheet in a single prompt (8-12 factors, each with a rating and narrative rationale), the model generates accurate early factors and degrades by factor 5-6. Field names shift, numeric ratings appear as strings, factor definitions bleed across entries, and rationales start referencing the wrong factor. The JSON parses but the data is semantically corrupt.

**Why it happens:** This is "array collapse" — a documented failure mode where complex nested structures degrade as generation progresses. Local models have weaker instruction-following under compounding context load than frontier models. A JES sheet is exactly the structure that triggers this: repetitive schema, similar content per entry, growing context.

**Consequences:** An exported JES scoring sheet that looks complete but has ratings and rationales mismatched to factors. An HR advisor or reviewer who doesn't audit each factor line-by-line will not catch it. In a grievance, a mismatched rationale is as bad as a missing one.

**Prevention:**
- Never generate the full JES sheet in a single LLM call
- Generate each factor independently: one call per factor, with the full factor definition injected as context each time
- Use Pydantic schema validation per factor with a 3-attempt retry loop before surfacing to the advisor
- Temperature = 0 for all JES generation calls

**Detection:** After generation, run a cross-check: does the rating for Factor X fall within the valid point range for that factor per the applicable JES? This is deterministic logic, not LLM-dependent — implement as a validator.

**Phase:** JES generation phase (JES-01, JES-02). Address in data model design before any generation logic is written.

**Prototype precedent:** JD-Builder-Lite planned JES scoring but never fully built it. This is the most likely reason — the complexity was deferred, not solved.

---

### CRITICAL-02: Hallucinated NOC Statements That Sound Authoritative

**What goes wrong:** The model generates duty statements that are plausible, professionally worded, and stylistically consistent with real NOC language — but are not present in the source NOC unit group profile. Because they sound right, the advisor accepts them. The export cites a NOC code, but the specific statement doesn't exist in that profile.

**Why it happens:** The model has seen NOC-style language in training data. When generating duties, it interpolates rather than retrieves. This is especially likely when: (a) the NOC profile has few duty statements for the work described, (b) the model is generating duties 6-10 in a sequence where it started with real statements, or (c) the context includes both the advisor's free-text description and the NOC profile, and the model blends them.

**Consequences:** Export contains citations like "NOC 21232 — Main Duties" that are fabricated. In a classification grievance, the cited source is checked. A statement that doesn't exist in the cited NOC profile undermines the entire traceability claim.

**Prevention:**
- Hard constraint: every duty statement in the export must be a verbatim quote from a source document, stored in the database at ingest time, with a row ID
- The LLM's role is selection and ranking, not generation of duty text
- If the LLM generates a duty statement that has no matching row in the NOC data table, it must be flagged as "advisor-added / not from authoritative source" and cannot carry a NOC citation
- Implement semantic similarity check: generated statement vs. closest NOC statement in vector space — if similarity < threshold, flag as likely hallucination

**Detection:** At export time, validate every cited statement: does the exact text (or a high-fidelity match) exist in the source document at the cited reference? Log any that fail this check as "provenance validation failures" and surface to advisor.

**Phase:** NOC data ingestion and JD generation phases (JD-01, JD-02). The constraint architecture must be in place before generation logic is built.

---

### CRITICAL-03: Soft Citations That Don't Survive Grievance Scrutiny

**What goes wrong:** The export says "Based on NOC 21232" or "Aligned with IT collective agreement" without specifying which section, which statement, which version, or which date. This is the "soft citation" — it creates an appearance of traceability without actual traceability. An HR tribunal or grievance adjudicator who requests the source document and asks the advisor to point to the specific clause will find the citation is an assertion, not a reference.

**Why it happens:** It is much easier to generate soft citations than hard ones. Soft citations emerge naturally from prompts like "cite the source." Hard citations require the system to know the exact section, paragraph, and version of the source at write time.

**Consequences:** Classification grievance challenge. TBS Directive on Classification requires that the work description be the basis for classification; if the WD's cited evidence cannot be located in the cited source, the classification is vulnerable. In audit or informal review, a soft-cited JD looks defensible but isn't.

**Prevention:**
- Every citation in the system must be a structured object at write time: `{source: "NOC 2021", code: "21232", section: "Main Duties", statement_index: 3, text_hash: "...", retrieved_date: "2026-05-28"}`
- No citation is written as prose ("based on") — all citations are machine-readable references that render to formatted prose at export time
- The export layer renders citations from structured objects; if the object is missing, the field renders as "source: unverified / advisor-added" rather than silently omitting it

**Detection:** Any citation that cannot be resolved to a specific source record (by ID or hash) before export should block export or generate a pre-export validation report.

**Phase:** Data architecture phase. This constraint must shape the database schema — not be retrofitted. Address in Sprint 1.

---

### CRITICAL-04: Work Description Missing Legally Required Elements

**What goes wrong:** The system generates a WD that looks complete — it has duties, qualifications, and a title — but is missing elements required by the TBS Directive on Classification (section 4.1.2). The missing elements are not obvious because the document looks well-formatted and professionally written.

**Why it happens:** The Directive on Classification requires specific elements in every WD (position information, work to be performed, supervisory responsibilities, contacts, working conditions, position context). A generation system that is not explicitly aware of this checklist will produce output that covers the elements the advisor described, not the required legal elements.

**Common missing elements (from TBS Directive):**
- Financial authorities / delegated authorities for the position
- Supervisory / managerial responsibilities explicitly stated (even if zero)
- Physical and environmental conditions (even if standard office conditions)
- Position context / reporting structure
- Freedom to act / decision-making latitude
- Contacts (internal and external, nature and purpose)

**Consequences:** A WD that passes casual advisor review but fails a classification quality audit or serves as a weak foundation for a grievance response. Retroactive correction requires re-classification.

**Prevention:**
- Build a WD completeness checklist as a pre-export validation step: for each required element, assert that the generated content addresses it
- Each element must be explicitly represented in the data model — not inferred from duty text
- Surface missing elements to the advisor as required fields, not optional suggestions
- Export is blocked (or warnings surfaced) until all mandatory elements have content

**Detection:** A static checklist validator that checks for presence/non-emptiness of each required WD section. This is deterministic logic.

**Phase:** JD data model design phase. The WD schema must match the Directive's required elements before any generation is built.

---

### CRITICAL-05: Version Drift — Citations Point to Superseded Sources

**What goes wrong:** The system is built against NOC 2021 v1.0, EC collective agreement 2022-2025, and JES version X. A data update occurs (CA renegotiation, NOC revision, JES amendment). The source files are updated on disk. But previously generated JDs retain the old citations — and the export metadata says "NOC 2021 v1.0" when the data file has been silently updated to v1.1.

**Why it happens:** Source version is not tracked at the record level; it is assumed from the file path or a global config value. When the file changes, all records in the derived table implicitly change version without any record of what changed.

**Consequences:** A JD generated 18 months ago that cited "EC CA Article 7.3" may now reference a clause that was renumbered or amended. The citation points to the right article by number but the text has changed. In a grievance, the original text matters.

**Prevention:**
- Every source document ingested gets a content hash and a version label stored at ingest time
- Every derived record (NOC statement, CA article, JES factor) stores the source document version hash it was derived from
- When a source file is updated, re-ingest is explicit (not automatic) and creates a new version, not an overwrite
- Exports store the full version manifest: which version of each data source was active when the JD was generated
- Old JDs are never retroactively re-cited against new source versions without advisor action

**Detection:** A "stale citation" report: for each JD in the system, compare the stored source version hash against the current active source version. Flag any JDs where citations reference an older version than is currently loaded.

**Phase:** Data ingestion and medallion architecture phase. Version tracking must be built into the Bronze→Gold pipeline before the first source document is ingested.

---

## High-Priority Pitfalls

Mistakes that cause significant rework, compliance gaps, or degraded output quality.

---

### HIGH-01: Context Window Exhaustion With JES Documents

**What goes wrong:** JES documents for some occupational groups are 40-80 pages. Injecting a full JES into a prompt with the WD duties, the advisor's input, and the system instruction exceeds the context window of a 7B-14B parameter model (typically 8k-32k tokens in practice, even if the model claims higher). The model silently truncates the earlier parts of the context — usually the system instructions or the beginning of the JES — and generates ratings as if it received complete context.

**Why it happens:** Models do not error when context is exceeded with recent Ollama versions — they truncate silently. The output looks complete. Research shows hallucination frequency increases monotonically as context fills, particularly dropping information from the middle of long contexts ("lost in the middle" effect).

**Consequences:** JES ratings generated with incomplete factor definitions, system instructions ignored, or duties truncated. Ratings may be internally consistent but wrong because the model was working from partial information.

**Prevention:**
- Estimate token count before each LLM call; if > 60% of model context window, switch to chunked strategy
- For JES generation: inject only the specific factor definition for the factor being rated, not the full JES document
- Use a lightweight context budget tracker: system prompt + factor definition + relevant duties = budget check before call
- Never rely on the model to handle its own context limits

**Detection:** Log token estimates (not just response length) for every LLM call. Alert if any single call exceeds 70% of the context limit.

**Phase:** LLM integration layer. Build the context budget tracker as a utility before writing any JES or generation prompts.

---

### HIGH-02: Embedding Model Mismatch Between Index and Query

**What goes wrong:** The NOC and JES data is indexed at build time using embedding model A (e.g., `nomic-embed-text`). Later, the application is updated or redeployed and embedding model B is used for query-time embeddings. Semantic search silently degrades: the vector space of queries and documents no longer aligns, but the system still returns results (just wrong ones).

**Why it happens:** Embedding models are rarely versioned or locked in early development. The developer updates Ollama, a new model default is pulled, and the index is never regenerated. This is the most common RAG operational failure in production.

**Consequences:** NOC matching returns similar-but-wrong unit groups. The advisor selects duties from the wrong occupational profile. The resulting JD has duty statements that are plausible but sourced from the wrong classification context.

**Prevention:**
- Store the embedding model name and version in the index metadata
- At app startup, assert that the configured embedding model matches the model used to build the index
- If mismatch detected, refuse to run queries and require re-indexing
- Pin the embedding model in config (`EMBED_MODEL=nomic-embed-text:v1.5`) and treat changes as a breaking change requiring index rebuild

**Detection:** Startup assertion: `assert index.embed_model == config.EMBED_MODEL`. Log warning and block search if mismatch.

**Phase:** RAG/data pipeline phase. The assertion and version tracking must be built before any semantic search is used in the application.

---

### HIGH-03: Chunking Breaking JES Factor Definitions

**What goes wrong:** JES factors have a logical structure: factor name → definition → sub-factors → point scale → benchmark positions. If the JES document is chunked by fixed token count, a chunk boundary falls mid-definition, separating the point scale from the factor description it belongs to. Retrieval returns a chunk containing the point values without the qualitative definitions, or vice versa.

**Why it happens:** Fixed-size chunking is the default in most RAG frameworks and is applied without domain awareness. JES documents are not narrative prose — they are structured reference tables. Fixed chunking destroys the structural relationships.

**Consequences:** The model receives a chunk with the right factor name but incomplete definition, generating ratings that are structurally correct but semantically unanchored.

**Prevention:**
- Parse JES documents structurally (not as flat text): extract each factor as a discrete object with all its sub-components intact
- Store factors as structured records in the database, not as vector-indexed text chunks
- For JES tasks, retrieve by structured lookup (factor name → DB record), not semantic search
- Only use semantic search for fuzzy tasks (NOC matching, CA validation); use structured lookup for authoritative reference data

**Detection:** After JES document ingestion, validate that each factor record contains all required sub-components (definition, point scale, sub-factors). Fail ingestion if any factor is incomplete.

**Phase:** JES data ingestion phase.

---

### HIGH-04: NOC 2021 vs NOC 2016 Confusion in Source Data

**What goes wrong:** The data layer contains a mix of NOC 2021 (5-digit TEER codes) and NOC 2016 (4-digit skill-level codes) profiles. Classification logic that was written against NOC 2016 structure is invoked with NOC 2021 data, or vice versa. Occupational group mappings from TBS (written against NOC 2016) are applied to NOC 2021 codes that do not have direct equivalents.

**Why it happens:** Canada's NOC transition (November 2022) restructured ~500 occupations. GoC departments were mid-transition as of 2024. The existing data directory contains legacy files from the JD-Builder-Lite prototype era. Some OG-to-NOC mappings may reference NOC 2016 codes that no longer exist in the 2021 taxonomy.

**Consequences:** An IT position described in NOC 2021 TEER terms might match to a NOC 2016 unit group that maps to the wrong OG, or to a 2021 group that has no TBS OG mapping yet. The system suggests the wrong occupational group with misleading confidence.

**Prevention:**
- At data ingest time, tag every NOC profile with its NOC version (`NOC_VERSION=2021` or `NOC_VERSION=2016`)
- All application logic operates on NOC 2021 only; any NOC 2016 data is excluded or must be migrated
- OG-to-NOC mappings must be validated against the NOC 2021 taxonomy before being used
- Add a data quality gate at startup: assert that all loaded NOC profiles have `NOC_VERSION=2021`

**Detection:** Query the loaded data for any profiles without a version tag or with `NOC_VERSION=2016`. Log as data quality errors and exclude from matching.

**Phase:** Data ingestion and Bronze→Gold pipeline phase. Version tagging must be enforced at ingest, not added retroactively.

---

### HIGH-05: Collective Agreement Version Staleness

**What goes wrong:** The CA data files in the `data/` directory were collected at a specific point in time. CAs are renegotiated on 3-5 year cycles. The 25+ OG CA files represent a snapshot. When a CA expires and is renegotiated, the article numbers, exclusions, and duty scope definitions may change. The system's CA validation logic continues checking against the old CA version without warning.

**Why it happens:** There is no CA versioning mechanism. The files are static. Without an explicit refresh process and version tracking, the system silently operates on stale policy data.

**Consequences:** CA validation produces false-passes (a duty that now violates the updated CA passes validation) or false-flags (a duty that was clarified as permissible in the new CA is flagged as a violation). Either outcome degrades advisor trust and creates compliance risk.

**Prevention:**
- Every CA file must have a version date and expiry date in its metadata
- The application surfaces a warning if any CA in use is past its expiry date
- CA validation reports must include the CA version and dates used, so the advisor knows the validation was run against a specific version
- Build a manual refresh workflow (pull updated CA → re-ingest → update version metadata) even if automated sync is out of scope

**Detection:** At app startup, check CA file metadata dates. Warn if any CA has an expiry date in the past.

**Phase:** Data pipeline and CA validation phase (CA-01, CA-02).

---

### HIGH-06: Memory Pressure and OOM on Jetson AGX Orin

**What goes wrong:** A JES generation run that makes 10+ sequential LLM calls (one per factor) keeps the model loaded in VRAM. While the model is loaded, the RAG index is also in memory, along with Python process memory for parquet data. Under sustained use, memory pressure causes the Ollama process to OOM-kill, silently dropping in-flight requests and requiring model reload.

**Why it happens:** Jetson AGX Orin has unified memory (CPU and GPU share a pool). Ollama's memory management for Jetson has known issues — specifically, memory may not release cleanly after model unloading (confirmed in Ollama issue tracker, issues #12283 and #12528 as of 2025). Reducing context window from 8192 to 2048 can save 1-2GB per call, but this directly conflicts with long JES documents.

**Consequences:** Mid-generation failure for a JES scoring sheet. The advisor gets a partial result with no clear error message. Restarting requires reloading the model (cold start: 15-30 seconds for a 7B model on Jetson).

**Prevention:**
- Set an explicit `OLLAMA_NUM_CTX` cap in environment config appropriate to Jetson's available memory
- Generate JES factors in sequential, independent calls — do not batch multiple factors per call
- Implement a circuit breaker: if an LLM call fails with OOM or timeout, surface a clear error and offer retry rather than silently returning partial output
- Lazy-load non-critical in-memory data (parquet tables not needed for current workflow step)
- Test under sustained multi-step workflows (full JD generation end to end) before declaring the pipeline production-ready

**Detection:** Monitor Ollama process memory between calls during test runs. Log pre-call and post-call memory estimates. Set warning threshold at 80% of Jetson's available unified memory pool.

**Phase:** Infrastructure and LLM integration phase, and integration testing phase.

---

## Moderate Pitfalls

Mistakes that degrade quality or increase rework without causing legal/compliance failures.

---

### MOD-01: Semantic Retrieval Returning Similar-but-Wrong NOC Profiles

**What goes wrong:** An advisor describes "financial analyst performing budget forecasting and variance analysis for a federal department." The semantic search returns FI (Financial Management) profiles alongside EC (Economics and Social Science) and AS (Administrative Services) profiles with high similarity scores. The top result is FI-02, but the correct classification is EC-04. The advisor, trusting the ranked list, selects FI.

**Why it happens:** Embedding similarity reflects surface vocabulary overlap, not occupational classification logic. Financial analysis language appears in multiple NOC unit groups. Semantic search cannot apply the TBS OG inclusion/exclusion rules (which require domain knowledge, not semantic similarity).

**Prevention:**
- Treat semantic search as a shortlist tool, not a classifier
- Layer structured OG exclusion logic on top of semantic results: after retrieval, apply OG definition checks to eliminate candidates that clearly fail inclusion/exclusion criteria
- Surface the OG inclusion/exclusion rationale alongside each candidate so the advisor can apply policy judgment
- Show similarity scores — do not hide the fact that multiple candidates are close

**Detection:** Implement a smoke test suite with 10-15 known position descriptions and their correct OG mappings. Run this suite after any change to the embedding model, chunking strategy, or retrieval configuration.

**Phase:** NOC matching and classification phase (INPUT-01, CLASS-01, CLASS-02).

---

### MOD-02: Prompt Drift in Duty Statement Generation

**What goes wrong:** The system generates 10 duty statements in sequence for a JD. Statements 1-4 follow the required format: active verb, object, context. By statement 7, the model has shifted to a different style — passive voice, different specificity level, or introducing qualifications that belong in the skills section. The JD is internally inconsistent without the advisor noticing.

**Why it happens:** This is alignment drift in multi-turn or long-sequence generation. System prompts are too brittle for sustained long contexts. The model's attention on early instructions degrades as the generation sequence grows.

**Prevention:**
- Generate each duty statement independently with the full formatting instruction in each call — do not rely on the model "remembering" format requirements from statement 1 to statement 10
- Post-process: run a consistency check comparing structural patterns (first word is a verb, no qualification language) across all generated statements
- Provide 2-3 worked examples in every duty generation prompt (few-shot, not zero-shot)

**Detection:** A lightweight structural validator: check that each duty statement starts with an imperative verb, stays within word count bounds, and contains no language from the "belongs in skills/qualifications" category (maintain a keyword list).

**Phase:** JD generation phase (JD-01).

---

### MOD-03: OG Scope Creep Into Another Group's Territory

**What goes wrong:** A DND position classified as EC involves some procurement coordination duties. The generated duty statements include "Coordinates procurement activities and liaises with contracting officers." Under the EC collective agreement, procurement-focused work belongs to PG (Purchasing and Supply). Including a procurement-heavy duty may expose the WD to a CA scope challenge.

**Why it happens:** NOC profiles describe what people do, not which GoC collective agreement they fall under. The model generating duties from NOC has no awareness of CA boundary conditions between OGs. Duty scope overlap is common in real positions, but the JD must be drafted to reflect the dominant work, not inadvertently import duties that belong to another bargaining unit.

**Prevention:**
- After duty generation, run CA validation (CA-01) with explicit scope-boundary checks: for each OG, load the CA exclusions and cross-reference duties against those exclusion patterns
- Surface flagged duties as "potential scope conflict with [OG] CA" rather than silently including them
- Include OG definition exclusions in the classification prompt so the model is aware of boundary conditions when suggesting duties

**Detection:** CA validation step with duty-by-duty scope flags. Pattern matching on known scope-boundary terms (procurement → PG, information technology → CS/IT, legal → LP, etc.).

**Phase:** CA validation phase (CA-01, CA-02). Also feed back into classification phase.

---

### MOD-04: Qualification Standard Education Requirements Set Too High

**What goes wrong:** The system pre-populates education requirements from the applicable Qualification Standard (e.g., "Graduation with a degree from a recognized university" for EC). The advisor, not re-reading the standard carefully, raises the requirement to "Master's degree" based on the seniority of the position. This over-specifies the minimum standard in a way that is not supported by the Qualification Standard and may be challenged as an unnecessary barrier in staffing.

**Why it happens:** The qualification standard sets a minimum. Raising it requires documented rationale under the PSEA and Directive on Classification. Advisors frequently conflate "preferred qualifications" with "minimum standard." The tool may contribute to this by not making the distinction visible.

**Prevention:**
- Clearly distinguish minimum standard (from TBS Qualification Standard) from "asset qualifications" (position-specific enhancements) in the UI and data model
- If an advisor raises the minimum above the standard, require them to enter a documented rationale (stored as a provenance note)
- Surface the relevant Qualification Standard text inline so the advisor sees the authorized minimum before modifying

**Detection:** Validation rule: if the education field contains language more restrictive than the standard for the OG (e.g., "master's" where the standard only requires "degree"), flag it with the relevant standard reference.

**Phase:** Qualification standards phase (QUAL-01).

---

### MOD-05: Rubber-Stamping — Advisor Accepts AI Output Without Substantive Review

**What goes wrong:** The tool produces a well-formatted, professionally worded JD. The advisor, under time pressure, reviews it in 2 minutes and approves it for export. The JD contains a hallucinated duty statement (CRITICAL-02), a mismatched JES rationale (CRITICAL-01), and a missing required WD element (CRITICAL-04). All of these would have been caught by a 20-minute review but were missed because the quality of the output's appearance reduced the advisor's vigilance.

**Why it happens:** High-quality AI output reduces cognitive engagement. Research (November 2025) specifically identifies this as "maximalist AI use minimizing agency expertise and careful consideration." The more complete the tool's output looks, the less likely the advisor is to interrogate it.

**Prevention:**
- Design the review flow to require explicit advisor action on each generated element, not a single "approve all" button
- Highlight which elements are AI-generated vs. sourced verbatim vs. advisor-entered — visual distinction must be persistent, not a one-time warning
- Include a pre-export checklist that explicitly prompts the advisor to verify: (a) duty statements against source, (b) JES ratings against factor definitions, (c) education requirements against the standard
- Do not export without the advisor completing the checklist (with timestamps stored for audit)

**Detection:** Track which review steps the advisor completed and how long was spent. If total review time is < 5 minutes for a full JD, log it as a quality concern.

**Phase:** UX design and export phase (EXPORT-01). The review flow architecture must be decided before UI is built.

---

## Minor Pitfalls

Issues that cause friction or localized failures without systemic impact.

---

### MINOR-01: Ollama Cold Start Latency on First Request

**What goes wrong:** The first LLM call after app startup takes 15-30 seconds while Ollama loads the model into VRAM. The advisor has no feedback during this time and may assume the application has hung.

**Prevention:** Pre-warm the model at app startup with a trivial call (e.g., `"ping"`). Show a loading indicator during warmup. Log the warmup completion time.

**Phase:** Application startup / infrastructure phase. The prototype had this same issue (CONCERNS.md: 30-60 second cold start).

---

### MINOR-02: Hardcoded Data Paths Preventing Environment Portability

**What goes wrong:** Data file paths are hardcoded to the development machine, making the app non-runnable on a clean clone.

**Prevention:** All paths via environment variables with explicit startup validation. This is a direct lesson from JD-Builder-Lite (CONCERNS.md: `C:/Users/Administrator/Dropbox/...`).

**Phase:** Project setup / Sprint 1. Non-negotiable — must be in place before any other development.

---

### MINOR-03: Circular Provenance — AI Rewrite Severing the Source Chain

**What goes wrong:** The advisor requests that the tool "rewrite" a sourced NOC statement in plain language. The system rewrites it. The result is now stored with the original NOC citation, but the text is the model's paraphrase, not the verbatim source. If the paraphrase diverges significantly, the citation is now fraudulent — it points to a source that says something different from what the WD actually contains.

**Prevention:**
- Distinguish between "verbatim from source" and "paraphrase / advisor edit" in the data model — these are different provenance types
- A rewritten statement must be marked as "Advisor-edited (source: NOC 21232)" — the citation becomes a reference, not a verbatim attribution
- Never allow a rewritten statement to be exported with a "verbatim" citation type

**Detection:** At export time, validate citation type consistency: if `citation_type = "verbatim"`, the stored text must hash-match the source record.

**Phase:** JD generation and export phase. Provenance data model must support this distinction.

---

### MINOR-04: Session State Lost Mid-Workflow

**What goes wrong:** An advisor is partway through a JD (duties approved, JES in progress) and the browser is closed or the server restarts. The partial state is lost. The advisor must restart from scratch.

**Prevention:**
- Persist all workflow state to the database incrementally, not in session memory
- The application re-loads the in-progress JD from the database on return to the form
- Explicit autosave after each major step (duties approved, JES factor saved)

**Phase:** Application architecture phase. Session persistence must be designed into the data model — cannot be retrofitted.

---

### MINOR-05: Export That Looks Professional but Fails Classifier Review

**What goes wrong:** The DOCX export is well-formatted and visually polished. However, a classification specialist reviewing it cannot locate the JES rationale for a specific factor, cannot find the CA validation results, or finds that provenance metadata is buried in a footer no one reads.

**Prevention:**
- The export structure must be validated against TBS WD format expectations, not just "looks good as a Word document"
- JES scoring sheet must be a clearly labeled table with factor names, ratings, and rationale — not embedded in body text
- Provenance metadata (data sources, versions, generation date) must appear on page 1 or a prominent appendix — not a hidden footer

**Phase:** Export design phase (EXPORT-01, PROV-01).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Data ingestion | NOC 2021/2016 version confusion | Tag every profile at ingest; reject NOC 2016 records |
| Data ingestion | JES chunking breaks factor integrity | Parse JES as structured objects, not text chunks |
| Data ingestion | CA version not tracked | Store version date and expiry in every CA record |
| NOC matching (INPUT-01) | Embedding model mismatch after update | Assert model version at startup |
| NOC matching (INPUT-01) | Semantic search returns wrong OG | Layer OG exclusion logic on top of vector results |
| OG classification (CLASS-01/02) | Hallucinated OG rationale | Each piece of rationale must point to a specific OG definition record |
| JD generation (JD-01/02) | Prompt drift in duty statements | One call per statement; few-shot; structural validator |
| JD generation (JD-01/02) | Hallucinated duty statements | Duty text must exist verbatim in source DB; LLM selects, does not generate |
| JES scoring (JES-01/02) | JES array collapse | One call per factor; Pydantic validation; retry loop |
| JES scoring (JES-01/02) | Context window exhaustion | Token budget check before every call; inject only the current factor definition |
| CA validation (CA-01/02) | OG scope creep into another CA | Explicit scope-boundary pattern matching |
| CA validation (CA-01/02) | Stale CA version | Version expiry check at app startup; version in every CA validation report |
| Qualification standards (QUAL-01) | Education requirement set too high | Surface standard minimum inline; require rationale for any elevation |
| Export (EXPORT-01/PROV-01) | Soft citations | All citations are structured objects rendered at export time; no prose citations |
| Export (EXPORT-01/PROV-01) | Missing required WD elements | Pre-export completeness validator against TBS mandatory WD elements |
| UX / Review flow | Rubber-stamping | Explicit per-element review actions; pre-export checklist with timestamps |
| Infrastructure | Ollama OOM on Jetson | Context window cap; memory monitoring; circuit breaker on LLM calls |
| Infrastructure | Cold start latency | Pre-warm model at startup; loading indicator |

---

## Lessons From JD-Builder-Lite

The following pitfalls were directly observed in the prototype and must be explicitly addressed, not just acknowledged:

| Prototype Issue | Root Cause | Fix in New Version |
|-----------------|-----------|-------------------|
| OASIS scraping fragility broke the app repeatedly | HTML structure changed; no fallback; no local cache | Local parquet as primary source; no live scraping in production |
| Hardcoded Windows paths killed portability | Config values embedded in code | All paths via environment variables; validated at startup |
| 500MB sentence-transformer cold start (30-60s) | Lazy model loading; no pre-warm | Pre-warm at startup; lighter embedding model; loading indicator |
| No tests → bugs found only in UAT | Test coverage deferred | Test each layer (data ingestion, matching, generation, export) from day 1 |
| SSL verification disabled | Expedient dev shortcut left in | SSL enabled always; no `verify=False` anywhere |
| Structured output under token pressure returned null fields | Instructor + OpenAI schema enforcement insufficient | One-call-per-item strategy; Pydantic retry loop; token budget check |
| Session metadata not versioned → brittle after schema changes | No schema versioning in session | Persist to DB not session; version every schema; migration strategy |
| JES scoring planned but never shipped | Complexity deferred; no architecture for per-factor generation | Architecture JES as first-class from day 1; per-factor generation pattern established in Sprint 1 |

---

## Sources

- `/home/charles/JD-Builder-Lite/.planning/codebase/CONCERNS.md` — Prototype codebase audit
- `/home/charles/JD-Builder-Lite/.planning/NEW-VERSION-FINDINGS.md` — Prototype architectural lessons
- [TBS Directive on Classification](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=28700&section=HTML)
- [TBS Directive on Classification Grievances](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=28698)
- [Ollama Jetson memory issue #12283](https://github.com/ollama/ollama/issues/12283)
- [Ollama large context usability issue #9890](https://github.com/ollama/ollama/issues/9890)
- [Why RAG Systems Fail in Production — DigitalOcean](https://www.digitalocean.com/community/conceptual-articles/why-rag-systems-fail-in-production)
- [Local LLM JSON Output Failure Patterns — n1n.ai](https://explore.n1n.ai/blog/local-llm-json-output-failure-patterns-fix-2026-04-24)
- [LLM Hallucination in Long Contexts — Medium/Bootcamp](https://medium.com/design-bootcamp/when-more-becomes-less-why-llms-hallucinate-in-long-contexts-fc903be6f025)
- [AI Rubber-Stamping Legal Challenges — Governing for Impact, Nov 2025](https://governingforimpact.org/wp-content/uploads/2025/11/Potential-Legal-Challenges-to-AI-Rubber-Stamping-Issue-Brief-11-20-25-templated.pdf)
- [NOC 2021 Transition — Statistics Canada](https://www.statcan.gc.ca/en/subjects/standard/noc/2021/introductionV1)
- [RAG Chunking Strategies — Elysiate 2025](https://www.elysiate.com/blog/rag-systems-production-guide-chunking-retrieval-2025)
