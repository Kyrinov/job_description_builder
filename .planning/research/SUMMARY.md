# Research Summary — JD Builder

**Synthesized from:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md
**Date:** 2026-05-28

---

## Recommended Stack

Use FastAPI (already installed, 0.128.8) over the prototype's Flask. The core workflow involves LLM streaming during generation, and Flask's WSGI model blocks every other request while Ollama is running. FastAPI's `StreamingResponse` + `async for chunk in client.chat(..., stream=True)` is the correct pattern. Pair with HTMX 2.x + Alpine.js 3.x (no build step, ~29 KB combined) for a server-rendered wizard UI. DuckDB 1.5.3 (**pin this version** — aarch64 wheels are broken in 1.4.x) for parquet queries; SQLite + sqlite-vec for app state and vector search in the same file; Polars for Bronze→Gold pipeline transforms. All embeddings go through `nomic-embed-text` via Ollama — already resident with no cold start, eliminating the 500 MB sentence-transformers problem from the prototype. Use `instructor` as a retry wrapper over Ollama's native `format` parameter for JES and NOC classification calls.

**ARM64 caveats:** Pin DuckDB to 1.5.3. WeasyPrint requires Pango/Cairo system libs (should be present on JetPack Ubuntu). Qwen3 structured output has edge cases in some Ollama versions — `instructor` retry is mandatory for JES and NOC calls. **Do not use:** sentence-transformers, LangChain, LlamaIndex, React/Vue/Svelte, wkhtmltopdf.

---

## Table Stakes Features

Legally required for the output to be usable and defensible:

- **Complete header block** — position title, number, OG/level, supervisor info, manager signature, review date. TBS Directive s.4. Non-compliant without it.
- **Complete and current duties section with relative weights** — CA-enforceable right (PA Art.57.01, IT_CS Art.20.02, EC Art.34). Missing duties are a grievance trigger.
- **Organizational context paragraph** — TBS Directive; also required for JES scope element scoring.
- **OG definition with inclusions/exclusions cited** — wrong OG is the second-most common grievance trigger.
- **JES scoring sheet for the confirmed OG** — point ratings, degree descriptor citations, rationale per factor. Classification is legally incomplete without it. PA Art.57.01 explicitly requires point ratings be provided to the employee.
- **Factor-to-duty traceability in JES scores** — each rating must cite specific duties by verbatim quote. Unsupported scores are the primary grievance vector.
- **Qualification Standard surface for the confirmed OG** — PSEA s.31 minimum floor. Required before WD is used in staffing.
- **Export with machine-readable provenance metadata** — every element carries a structured citation object. Prose citations ("based on NOC 21232") do not survive grievance scrutiny.
- **Pre-export completeness validator** — static checklist blocking export if mandatory WD elements (financial authorities, supervisory responsibilities, physical conditions, freedom to act, contacts) are absent.

---

## Differentiating Features

1. Natural language → NOC mapping with ranked candidates and cited duty matches — eliminates manual OASIS search inconsistency
2. OG suggestion citing specific definition clauses with inclusions/exclusions — makes policy anchor visible; currently relies on advisor memory
3. AI-drafted duties selected verbatim from NOC records — eliminates copy-paste boilerplate that causes JES mismatches
4. JES scoring with per-factor AI rationale citing duties — 33% of advisors lacked adequate JES expertise per TBS evaluation; this is the core time savings
5. CA validation with article-level citations — currently done from memory across 25+ CA groups
6. DND DRF linkage — connects position duties to Departmental Results Framework; not done systematically today
7. Staleness detection — 43% of occupied positions had WDs >5 years old as of 2016 TBS evaluation; surfaces this proactively

---

## Architecture Decisions (Non-Negotiable)

These must be locked in from Phase 1 — retrofitting any of them is expensive:

**1. Provenance as a first-class field on every domain object.**
Every service function returns a typed object with a `ProvenanceTag` at the point of retrieval. The WD entity accumulates these. Export reads them — never re-derives citations. Content arriving at export without a structured provenance object renders as "advisor-added / not from authoritative source."

**2. WorkDescription Pydantic model finalized before any service is written.**
It is persisted to SQLite as JSON after every state transition. Every service writes to it; the export reads it. Schema changes after services are built are expensive.

**3. One LLM call per JES factor, never a full JES sheet in one call.**
"Array collapse" is a confirmed failure mode — structurally valid JSON with semantically mismatched ratings by factor 5–6. One call per factor, full factor descriptor injected fresh, `temperature=0`, Pydantic validation with 3-attempt retry via `instructor`.

**4. LLM selects duty text; it does not generate it.**
Every duty in the export must be verbatim text from a source record in the database, with a row ID. If no matching source record exists, the duty is flagged "advisor-added / not from authoritative source." Eliminates hallucinated NOC duty citations.

**5. CA restriction clauses pre-extracted at ingest, not retrieved from full CA at validation time.**
Full CAs are 50–150K chars. Loading at validation time saturates context on Orin for 8–10 duty rounds. Batch-extract restriction/scope/exclusion clauses with Qwen3 at ingest; validate against the extracted subset.

**6. Separate sqlite-vec tables per corpus type.**
NOC duties, CA restriction clauses, and JES factors have different semantic distributions. Mixed index degrades retrieval. JES factor retrieval uses structured lookup by `(og_code, factor_name)`, not semantic search.

**7. NL→NOC is a three-stage pipeline: FTS5 shortlist → embedding rerank → Qwen3 justify.**
Pure semantic search misses NOC-specific vocabulary. Full LLM over 900 profiles is infeasible locally. Qwen3 only sees pre-screened candidates — cannot hallucinate a code not in the shortlist.

**8. Source document version hashing from day one.**
Every source document ingested gets a content hash and version label. Every derived record stores the source version hash it was derived from. Exports include a full version manifest. Cannot be retrofitted.

---

## Critical Data Gaps

| Dataset | Needed For | Status | Priority |
|---------|-----------|--------|----------|
| **NOC 2021 unit group profiles (parquet or JSON)** | All NOC mapping; all duty drafting; FTS5 + vec indexes | Not in data/ | **HARD BLOCKER — Phases 3–5** |
| **TBS OCHRO OG Definitions with inclusions/exclusions** | OG classification (CLASS-01, CLASS-02) | Not collected | **HARD BLOCKER — Phase 4** |
| **TBS Qualification Standards (per OG)** | QUAL-01 pre-population | Not collected | **HARD BLOCKER — Phase 6** |
| TBS Directive on Classification (full text) | Completeness validator; legal anchor | Not ingested | HIGH |
| TB Secretariat Allocation Guide | OG allocation methodology | Not collected | HIGH |
| Key Leadership Competencies framework | COMP-01 | Not collected | MEDIUM |

NOC 2021 profiles are the single hardest blocker. Nothing in the NL→NOC pipeline, duty drafting, or JES scoring works without them. Any NOC 2016 data in the repo must be version-tagged and excluded — all application logic operates on NOC 2021 only.

---

## Top 5 Pitfalls to Avoid

1. **JES array collapse** — Local models produce structurally valid but semantically corrupt JES sheets when all factors are requested in one prompt. Prevent with one-call-per-factor, `instructor` retry, Pydantic validation, and a deterministic point-range validator.

2. **Hallucinated NOC duty statements** — The model interpolates plausible NOC-style text that doesn't exist in source profiles and the citation looks real. Prevent by treating the LLM as a selector over pre-indexed verbatim records only — never a generator.

3. **Soft citations** — Prose citations don't survive grievance scrutiny. Prevent by making every citation a structured `ProvenanceTag` object at write time that renders to prose at export — never the reverse.

4. **Ollama OOM mid-JES on Jetson** — Sequential JES calls in unified memory may hit OOM without a clear error. Prevent with explicit `OLLAMA_NUM_CTX` cap, circuit breaker that fails loudly with recoverable state, and mandatory end-to-end test on hardware before production.

5. **Embedding model mismatch after Ollama update** — Updating Ollama silently changes default embedding model; vector index and queries fall out of alignment; NOC search returns wrong results silently. Prevent with startup assertion comparing index metadata model name against configured model — refuse to run queries on mismatch.

---

## Build Order Recommendation

| Phase | Name | Key Output | Hard Prerequisites |
|-------|------|-----------|-------------------|
| 1 | Project Foundation | FastAPI skeleton, WorkDescription Pydantic models, SQLite schema, Ollama pre-warm | None |
| 2 | Data Pipeline (Bronze→Gold) | NOC/CA/JES indexed in SQLite + FTS5 + sqlite-vec; version hashes; OG definitions ingested | NOC 2021 data acquired |
| 3 | NL-to-NOC Pipeline | `/map-to-noc` endpoint, hybrid FTS5+embed+Qwen3, advisor confirmation | Phase 2 NOC index |
| 4 | OG Classification | `/classify-og` endpoint, OG suggestion with inclusions/exclusions cited | Phase 2 OG definitions; Phase 3 NOC match |
| 5 | JD Generation | Verbatim duty selection, position overview, WD persisted to SQLite | Phase 3 + 4 confirmed |
| 6 | Qualifications + Competencies | TBS Qual Standard surface, KLC competencies by level | Phase 2 Qual Standards; Phase 4 confirmed OG |
| 7 | CA Validation | `ca_validator.py`, per-duty check against pre-extracted restriction clauses | Phase 2 CA ingest; Phase 5 draft duties |
| 8 | JES Scoring | Per-factor Qwen3 in `/think` mode, evidence quotes, point-range validator | Phase 2 JES; Phase 5 duties |
| 9 | Export | DOCX + PDF via docxtpl + WeasyPrint, pre-export completeness validator, advisor review checklist | Phase 5–8 complete |
| 10 | DND DRF Integration | DRF program linkages surfaced alongside position duties | Phase 5; DRF CSV already in data/ |

---

## Watch Out For

**PA classification reform creates an active data hazard.** PA group restructuring (CR, AS, PM → new sub-groups) is ongoing. New JES factors are effective but conversion is incomplete. Assert post-2023 JES standard versions at ingest; reject pre-2023 JES documents.

**The advisor rubber-stamp problem is a data model constraint, not a UX nice-to-have.** High-quality AI output demonstrably reduces advisor vigilance. The review flow must require explicit per-element advisor action with timestamps stored in `wd_audit_log`. Design into Phase 1 data model — cannot be retrofitted.

**Ollama unified memory on Jetson is under-documented and issue-prone.** Issues #12283 and #12528 confirm memory may not release cleanly after model unloading. Do not declare the pipeline production-ready without a full end-to-end test (Phases 3–8 in sequence) on hardware under load.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All packages verified via pip dry-run or confirmed installed on Jetson |
| Features | HIGH | Grounded in primary GoC policy sources with direct text references |
| Architecture | HIGH | Derived from prototype failure analysis + hybrid retrieval benchmarks |
| Pitfalls | HIGH | CRITICAL pitfalls grounded in prototype failures + 2025–2026 LLM reliability research |

**Overall: HIGH**

**Remaining unknowns:** OG definition data structure (unknown until collected); CA restriction clause extraction quality (prompt-dependent, needs iteration); JES scoring accuracy vs GoC specialists (plan UAT after Phase 8); NOC 2021 acquisition format (confirm before Phase 2 planning).
