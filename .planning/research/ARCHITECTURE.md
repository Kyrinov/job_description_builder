# Architecture Patterns

**Project:** JD Builder (GoC Job Description Builder)
**Researched:** 2026-05-28
**Research mode:** Ecosystem + Feasibility

---

## Recommended Architecture

### Overview

A five-layer pipeline where each layer feeds the next, with provenance injected as a first-class field at every boundary:

```
[Data Layer]          Local parquet/JSON/SQLite — Bronze/Silver/Gold medallion
       ↓
[Index Layer]         SQLite-vec (vector) + SQLite FTS5 (keyword) — hybrid search
       ↓
[Pipeline Layer]      Stateless service modules — NL→NOC, OG classification, JD gen,
                      CA validation, JES scoring — all called via FastAPI routes
       ↓
[Session/State Layer] SQLite WD session store — the WorkDescription entity as source of truth
       ↓
[Export Layer]        DOCX/PDF renderer consuming the WD with embedded provenance
```

The prototype (JD-Builder-Lite) proved the medallion data pattern and Pydantic contracts work well. The main gap was provenance as an afterthought and live scraping brittleness. Both are fixed in this design by making provenance a field on every domain object from the start and eliminating live HTTP calls entirely.

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `data/ingest/` | One-time scripts to convert raw files → Silver parquet + SQLite FTS5 index | Offline only — no runtime dependency |
| `data/embed/` | Batch embed Silver records → SQLite-vec | Offline only — no runtime dependency |
| `services/noc_mapper.py` | Hybrid search: FTS5 shortlist → nomic-embed-text cosine rerank → Qwen3 justify top-5 | Index layer, Ollama |
| `services/og_classifier.py` | OG suggestion from confirmed NOC: embed duty text → OG definitions → Qwen3 rank + cite | Index layer, Ollama |
| `services/jd_generator.py` | Compose draft duties + overview from NOC Silver records with source citations baked in | SQLite (WD store), NOC Silver |
| `services/ca_validator.py` | Check draft duties against pre-extracted CA restriction clauses | SQLite CA restriction index |
| `services/jes_scorer.py` | Score position duties against JES factor definitions, one factor per call | JES Silver files, Ollama |
| `services/export_service.py` | Build export payload from WD entity — all provenance already present | WD store |
| `api/routes.py` | FastAPI routes — validate, dispatch, return | All services |
| `frontend/` | Vanilla JS SPA — progressive workflow: describe → map → classify → build → score → export | API routes |

---

## 1. NL-to-NOC Mapping Architecture

**Recommendation: Hybrid two-stage pipeline — FTS5 keyword shortlist → semantic rerank → LLM justify**

**Rationale:**

Pure semantic search alone misses NOC-specific vocabulary (e.g., a user who writes "manage money flows" should match "financial management" profiles, but embedding distance alone may rank it below noise). Pure LLM classification with all 900 NOC profiles in context is infeasible at 7-32B model size.

The correct approach given the corpus size (~900 unit groups, each with a lead statement + 5-10 duty statements averaging 40-60 tokens each):

1. **FTS5 keyword shortlist** — full-text search against a SQLite FTS5 index of NOC titles + lead statements + duty keywords. Returns top 30 candidates in <100ms. No model involved. Catches exact and near-exact term matches reliably.

2. **nomic-embed-text cosine rerank** — embed the user's query + each of the 30 candidates. Rerank by cosine similarity to top 10. nomic-embed-text:latest is already running on Jane (274MB, ARM64 compatible via Ollama). Inference time: ~50ms per embed on Orin.

3. **Qwen3 justify** — send the top 10 NOC profiles (title + lead statement + 3-5 key duties each, ~2K tokens total) to Qwen3.6 with the user's description and ask it to rank and justify top 3-5 matches. Use `/nothink` mode for this call — the task is classification, not deep reasoning, and thinking mode adds latency with no accuracy gain for a well-constrained prompt.

**Why this is reliable with Qwen-class models:**
- The model only sees pre-screened candidates — it cannot hallucinate a NOC code that isn't in the shortlist (enforce this in the prompt with explicit constraint: "select only from the following codes")
- Structured output via Ollama JSON schema enforces `{noc_code, title, confidence, rationale}[]` format
- Hybrid BM25+dense pipelines consistently outperform either alone in retrieval benchmarks (MRR@5 ~76% vs ~62% for sparse-only)

**What Qwen struggles with here:**
- Distinguishing closely related NOC codes (e.g., 10010 vs 10011 when both mention "program management") — mitigated by surfacing top 3-5 with confidence scores and asking the advisor to confirm, not auto-selecting
- Long NOC profiles with dense jargon — keep the per-profile context tight (title + lead + 3 duties, not full profile)

**Confidence level: HIGH** — based on verified hybrid retrieval architecture patterns and Qwen3 structured output capability

---

## 2. RAG Pipeline Design

### Corpus sizes (measured from actual data):

| Dataset | Volume | Nature |
|---------|--------|--------|
| NOC 2021 unit groups (~900) | ~450K tokens estimated | Structured: title, lead, duties (short), skills, inclusions/exclusions |
| Collective agreements (28 OGs) | ~8.9M chars / ~2.2M tokens | Semi-structured: articles + tables |
| JES documents (15 OGs) | ~442K chars / ~110K tokens | Structured: factors, levels, descriptors |
| Rates of pay (CSVs) | Tabular | Structured numeric |

### Chunking strategy by corpus:

**NOC profiles — section-as-chunk:**
Each NOC section (lead statement, duties list, skills, inclusions, exclusions) becomes its own chunk with the NOC code and section type embedded in chunk metadata. Duties are short (1-3 sentences), so no sub-chunking needed — chunk at the duty-item level with parent metadata preserved. This matches the domain: a duty statement is the atomic unit of retrieval.

```python
# Chunk shape for NOC duties:
{
    "noc_code": "21232",
    "noc_title": "Software developers and programmers",
    "section": "main_duties",
    "item_index": 2,
    "text": "Write, modify, integrate and test software code for e-commerce, internet or intranet applications.",
    "version": "NOC 2021",
    "source_url": "https://noc.esdc.gc.ca/...",
    "retrieved_date": "2026-05-28"
}
```

**Collective agreements — article-as-chunk:**
The CA JSON already has sections with `id`, `title`, `text` fields. Chunk at the article level (each `### Article X:` heading creates a chunk boundary). Target chunk size: 512-800 tokens. For articles with subsections, split at the subsection boundary and keep parent article as metadata. Tables become their own chunks (rate tables, leave entitlement tables).

The pre-extracted `collective_agreements_jd.json` in webscrapes already contains JD-relevant sections — this should be the primary index for CA validation, not the full CA text.

**JES documents — factor-level chunks:**
Each JES factor (Skill/Knowledge, Effort, Responsibility, Working Conditions) plus its level descriptors forms one chunk. This keeps the level descriptions together with the factor definition — exactly what JES scoring needs.

### Vector store strategy: Single SQLite database, multiple tables

**Recommendation: sqlite-vec + SQLite FTS5 in a single `.sqlite` file**

Not ChromaDB. Rationale:
- The WD session store is already SQLite — keeping everything in one SQLite database dramatically simplifies deployment and backup
- sqlite-vec is ARM64 native, has a 30MB memory footprint, and supports HNSW via extensions
- SQLite FTS5 is built-in — no extra process
- ChromaDB adds a dependency that requires a separate process or embedded mode; sqlite-vec embedded in the same DB file is strictly simpler

Schema sketch:
```sql
CREATE VIRTUAL TABLE noc_chunks_fts USING fts5(noc_code, title, text);
CREATE TABLE noc_chunks_vec (
    id TEXT PRIMARY KEY,
    noc_code TEXT,
    section TEXT,
    text TEXT,
    embedding BLOB  -- nomic-embed-text 768-dim float32
);
CREATE TABLE ca_restriction_clauses (
    id TEXT PRIMARY KEY,
    og_code TEXT,
    article_id TEXT,
    article_title TEXT,
    text TEXT,
    embedding BLOB,
    restriction_type TEXT  -- 'scope', 'exclusion', 'work_assignment'
);
CREATE TABLE jes_factor_chunks (
    id TEXT PRIMARY KEY,
    og_code TEXT,
    factor TEXT,
    level INTEGER,
    text TEXT,
    embedding BLOB
);
```

### When to use RAG vs direct context:

| Scenario | Approach | Reason |
|----------|----------|--------|
| NOC shortlisting (900 profiles) | RAG (hybrid) | Too large for context; retrieval selects relevant subset |
| NOC profile for confirmed match | Direct context | Single profile ~500-800 tokens; fits in prompt easily |
| OG definitions (28 OGs, ~100 tokens each) | Direct context | ~2.8K tokens total — put all 28 in prompt for classification |
| CA validation for specific OG | RAG → pre-extracted clauses | Single CA is ~50K-150K chars; pre-extracted restriction clauses fit in context |
| JES factor scoring | Direct context per factor | Each factor's descriptor set is ~500-1000 tokens |
| Rates of pay | Direct context lookup | Tabular; query by OG + level, return row |

---

## 3. Provenance Tracking Architecture

**Core principle: Provenance is a field on the domain object, not a post-processing step.**

Every content element in the system carries a `ProvenanceTag` from the moment it is retrieved. The WD entity aggregates these tags. The export renderer reads them directly — no re-derivation.

```python
class ProvenanceTag(BaseModel):
    source_type: Literal["NOC", "CA", "JES", "TBS_DIRECTIVE", "ADVISOR", "AI_GENERATED"]
    source_id: str          # NOC code, CA article ID, JES factor+level, or free text
    source_version: str     # "NOC 2021", "AI CA 2026", "CT JES 2023"
    source_url: Optional[str]
    retrieved_date: date
    model_name: Optional[str]       # if AI_GENERATED
    prompt_version: Optional[str]   # if AI_GENERATED
    modified_by_advisor: bool = False
```

Every service function returns a typed object carrying a `provenance` field:

```python
class DraftDuty(BaseModel):
    text: str
    provenance: ProvenanceTag
    noc_code: str
    noc_section: str

class OGRecommendation(BaseModel):
    og_code: str
    og_name: str
    confidence: float
    rationale: str
    evidence_spans: list[str]
    provenance: list[ProvenanceTag]  # one per cited article/definition
```

The WD entity is the accumulator — every field has a provenance tag:

```python
class WorkDescription(BaseModel):
    id: UUID
    advisor_input: str                          # raw NL input, no provenance needed
    noc_matches: list[NOCMatch]                 # with provenance
    confirmed_noc: Optional[NOCMatch]
    og_recommendation: Optional[OGRecommendation]
    confirmed_og: Optional[str]
    draft_duties: list[DraftDuty]               # each duty has provenance
    position_overview: Optional[DraftText]      # with provenance
    jes_scores: list[JESFactorScore]            # each with provenance
    ca_validation_report: Optional[CAReport]    # with per-clause provenance
    qualification_standard: Optional[QualStandard]
    advisor_additions: list[AdvisorAddition]    # source_type=ADVISOR
    created_at: datetime
    exported_at: Optional[datetime]
    export_version: Optional[str]
```

**Architecture decision: Persist the WD entity to SQLite as JSON at every state transition.** This makes every intermediate state recoverable and auditable. The export is a render of the final WD state — not a reconstruction.

---

## 4. Collective Agreement Validation Pipeline

**Recommendation: Pre-extract restriction clauses at ingest + embed → validate by similarity + rule match**

**Why not full CA long-context:**
A single CA is 50-150K chars (~15-40K tokens). At 32B model size on Orin with a 32K context window, loading the full CA text for each duty validation round-trip is too slow and consumes the entire context. With 8-10 duties to validate, this approach is unworkable at local inference speed.

**Why not pure embedding similarity:**
Embedding similarity alone will surface semantically similar clauses but may miss relevant restrictions phrased differently. "Positions in this group include only work of type X" may not score high against a duty description that doesn't mention type X.

**Recommended approach:**

**At ingest (offline, one-time):**
1. Parse each CA JSON into articles
2. Run Qwen3 over each article in batch with the instruction: "Extract any clauses that restrict, define the scope of, or exclude work assignments for positions in this occupational group. Return structured JSON: `{article_id, article_title, restriction_text, restriction_type}`." Use `/nothink` mode.
3. Store extracted restriction clauses in `ca_restriction_clauses` SQLite table with embeddings
4. This is a one-time ingest — re-run when CAs are updated

**At validation time (per JD):**
1. For each draft duty, embed the duty text
2. Search `ca_restriction_clauses` filtered by `og_code` using vector similarity (top 5)
3. Also run FTS5 keyword search for explicit exclusion language
4. Bundle retrieved restriction clauses with draft duties into a single validation prompt: "For each duty, determine if it conflicts with or is excluded by the listed restrictions. Return structured JSON."
5. One Qwen3 call handles all duties together — the restriction clause set for a single OG is typically 10-20 clauses, which fits in context comfortably

**What Qwen struggles with in CA validation:**
- Inferring that a duty violates a restriction when the connection is indirect (e.g., the duty mentions "procurement" and the CA defines scope as "administrative services only" without mentioning procurement explicitly). Mitigate by including the OG definition alongside the restriction clauses.
- Long lists of duties — keep to 10 or fewer per call, batch if needed

**Confidence: MEDIUM** — the ingest-time extraction approach is sound architecturally, but the extraction quality of restriction clauses depends on prompt quality and Qwen3's ability to parse CA legal language. Expect to iterate on the extraction prompt.

---

## 5. JES Scoring Architecture

**Recommendation: One call per factor, full factor descriptor set in context**

**Why one call per factor:**
JES factors are semantically independent. A single call asking the model to score all factors simultaneously causes interference — the model anchors on early factors and produces inconsistent evidence for later ones. The rubric-based LLM evaluation literature (2025-2026) confirms that analytic rubrics scored criterion-by-criterion outperform holistic scoring for nuanced dimensions.

Each factor call structure:
```
[System]: You are a GoC classification specialist scoring a position against the [OG] JES.
[Factor descriptor block]: Full text for this factor (levels 1-N with descriptors). ~500-800 tokens.
[Position duties]: The draft duties from the WD entity. ~300-600 tokens.
[Instruction]: Score this position on [FACTOR]. Return JSON: {level, score, rationale, evidence_quotes[]}
```

**Context inclusion strategy:**
- Include the full factor descriptor set (all levels) — never just the "likely" levels. Qwen needs the comparison ladder to calibrate.
- Include the full set of draft duties — not a summary. The model needs the actual text to quote from for evidence.
- Do not include the entire JES document. The irrelevant factors add noise and consume context with no benefit.
- Include the OG definition and inclusions/exclusions — this prevents the model from scoring as if the position were in a different OG.

**Evidence requirement:**
The `evidence_quotes` field must be text extracted verbatim from the draft duties. Enforce this with a prompt constraint: "evidence_quotes must be direct quotes from the Position Duties section above, not paraphrases." Validate in code that each quote string appears in the duty text.

**JES scoring reliability with Qwen-class models:**
- Factor-level scoring at 7B-32B is moderately reliable when the rubric is explicit and the context is tight. Levels within 1 point of the correct answer are expected.
- The evidence requirement is the fragile part — smaller models tend to paraphrase rather than quote. Use Qwen3.6 (32B effective dense equivalent) for JES scoring, not the smaller models.
- Thinking mode (`/think`) is worth enabling for JES — this is a task where deliberate reasoning over the level descriptors improves calibration at the cost of ~2x latency. Acceptable given JES is a one-time step per JD.

**Call budget per JD:**
A typical JES has 4-6 factors per subgroup. At one call per factor = 4-6 Ollama calls. At ~15-30 seconds per call on Orin with Qwen3.6 in thinking mode = 60-180 seconds total. Acceptable — this is a background async operation, not interactive.

---

## 6. Component Build Order

Dependencies flow strictly left-to-right. Nothing in a later stage should be started before its dependency is shippable.

```
Stage 1: Data Foundation (no LLM involved)
  ├── Ingest NOC 2021 data → Silver parquet + FTS5 + sqlite-vec embeddings
  ├── Ingest CA JSONs → article chunks + pre-extracted restriction clauses → FTS5 + sqlite-vec
  └── Ingest JES TXTs → factor chunks → sqlite-vec

Stage 2: Core Models + Search
  ├── WD data model (Pydantic) with ProvenanceTag — ALL other services depend on this
  ├── NL→NOC hybrid search (FTS5 + nomic-embed + Qwen3 justify)
  └── FastAPI skeleton + /map-to-noc endpoint

Stage 3: OG Classification
  ├── OG definitions data (gap: TBS OCHRO OG definitions needed)
  ├── og_classifier.py — embed + prompt with OG definitions
  └── /classify-og endpoint with evidence

Stage 4: JD Generation
  ├── jd_generator.py — NOC Silver → draft duties with provenance
  ├── WD session store (SQLite persistence)
  └── /generate-jd endpoint

Stage 5: CA Validation
  ├── Depends on: Stage 1 (CA restriction clauses indexed), Stage 4 (draft duties)
  ├── ca_validator.py
  └── /validate-ca endpoint

Stage 6: JES Scoring
  ├── Depends on: Stage 4 (draft duties confirmed), JES Silver data
  ├── jes_scorer.py — one call per factor
  └── /score-jes endpoint

Stage 7: Export
  ├── Depends on: All above — WD entity fully populated
  ├── export_service.py + DOCX/PDF renderer
  └── /export endpoint

Stage 8: Frontend SPA
  ├── Can start in parallel with Stage 3 onward — static shell first
  └── Progressive workflow: describe → map → classify → build → score → export
```

**Key dependency constraints:**
- The WD Pydantic model must be finalized before Stage 2 begins — every service writes to it
- NOC data ingestion (Stage 1) is gating — nothing else works without it
- OG classification (Stage 3) requires external data not yet present: TBS OCHRO OG definitions. This is the highest-priority data gap before Stage 3 can start.
- CA validation (Stage 5) is independent of OG classification — it only needs the draft duties and the OG code (confirmed in Stage 3)

---

## 7. Core Data Model

### Central Entity: WorkDescription

The WD is the single source of truth for a session. It is created at first user input, persisted after every state transition, and read by the export renderer unchanged.

```python
class ProvenanceTag(BaseModel):
    source_type: Literal["NOC", "CA", "JES", "TBS_OG_DEF", "TBS_DIRECTIVE", "QUAL_STD", "ADVISOR", "AI_GENERATED"]
    source_id: str                  # NOC code, "AI CA 2026 Article 5.02", "CT JES 2023 Skill L3"
    source_version: str
    source_url: Optional[str]
    retrieved_date: date
    model_name: Optional[str]
    prompt_version: Optional[str]
    modified_by_advisor: bool = False

class NOCMatch(BaseModel):
    noc_code: str                   # "21232"
    noc_title: str
    confidence: float               # 0.0-1.0
    rationale: str
    provenance: ProvenanceTag

class DraftDuty(BaseModel):
    id: UUID
    text: str
    provenance: ProvenanceTag       # source NOC code + section + item index
    advisor_modified: bool = False
    advisor_modified_text: Optional[str]

class OGRecommendation(BaseModel):
    og_code: str                    # "EC"
    og_name: str
    level: Optional[str]            # "EC-04" if determinable
    confidence: float
    rationale: str
    evidence_quotes: list[str]      # quotes from input that justify
    cited_articles: list[ProvenanceTag]  # TBS OG def, inclusions, exclusions
    confirmed_by_advisor: bool = False

class JESFactorScore(BaseModel):
    factor_name: str                # "Knowledge", "Decision Making", etc.
    level: int
    rationale: str
    evidence_quotes: list[str]      # verbatim from draft duties
    provenance: ProvenanceTag       # JES document + factor + level
    advisor_adjusted: bool = False
    advisor_adjusted_level: Optional[int]
    advisor_adjustment_rationale: Optional[str]

class CAViolation(BaseModel):
    duty_id: UUID
    duty_text: str
    restriction_clause: str
    restriction_source: ProvenanceTag
    severity: Literal["conflict", "unclear", "note"]
    explanation: str

class CAValidationReport(BaseModel):
    og_code: str
    ca_version: str
    articles_checked: list[ProvenanceTag]
    violations: list[CAViolation]
    passed: list[UUID]              # duty IDs that passed
    validated_at: datetime

class WorkDescription(BaseModel):
    id: UUID
    session_id: str
    advisor_email: Optional[str]

    # Stage 1: Input
    raw_input: str
    input_timestamp: datetime

    # Stage 2: NOC mapping
    noc_candidates: list[NOCMatch]
    confirmed_noc: Optional[NOCMatch]

    # Stage 3: OG classification
    og_recommendation: Optional[OGRecommendation]
    confirmed_og: Optional[str]     # "EC"
    confirmed_level: Optional[str]  # "EC-04"

    # Stage 4: JD content
    position_title: Optional[str]
    position_overview: Optional[DraftText]
    draft_duties: list[DraftDuty]
    qualification_standard: Optional[QualStandard]
    competencies: list[Competency]

    # Stage 5: CA validation
    ca_validation: Optional[CAValidationReport]

    # Stage 6: JES scoring
    jes_scores: list[JESFactorScore]
    jes_total_points: Optional[int]

    # Metadata
    created_at: datetime
    last_modified: datetime
    export_hash: Optional[str]      # hash of exported content for change detection
    exported_at: Optional[datetime]
```

### SQLite schema for session persistence:

```sql
CREATE TABLE work_descriptions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    stage TEXT NOT NULL,  -- 'input', 'noc_mapped', 'og_classified', 'jd_drafted', 'ca_validated', 'jes_scored', 'exported'
    data JSON NOT NULL,   -- full WD Pydantic model serialized
    created_at TEXT NOT NULL,
    last_modified TEXT NOT NULL
);

CREATE TABLE wd_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wd_id TEXT NOT NULL,
    event TEXT NOT NULL,   -- 'noc_confirmed', 'duty_modified', 'og_confirmed', etc.
    actor TEXT NOT NULL,   -- 'advisor' or 'system'
    detail JSON,
    timestamp TEXT NOT NULL
);
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Live scraping in production data path
**What:** Fetching NOC profiles from OASIS at request time
**Why bad:** Prototype broke repeatedly; no offline capability; ARM64 SSL quirks caused intermittent failures
**Instead:** All NOC data ingested locally at Silver tier; Ollama-only at runtime

### Anti-Pattern 2: Provenance as post-processing
**What:** Generating content first, attaching citations afterward
**Why bad:** The model cannot reliably re-derive which NOC clause justified which duty statement after the fact; citations become fabricated
**Instead:** Each retrieval call returns (content, ProvenanceTag) as a unit; provenance flows with data, never added later

### Anti-Pattern 3: Full CA document in LLM context
**What:** Loading the entire CA (50-150K chars) into the context window for duty validation
**Why bad:** Saturates context; most content is irrelevant (leave articles, pay tables); degrades model focus; too slow on Orin
**Instead:** Pre-extract restriction clauses at ingest; validate against the extracted subset only

### Anti-Pattern 4: All JES factors in one call
**What:** Single prompt asking the model to score all 4-6 factors simultaneously
**Why bad:** Factors influence each other; model anchors on first factors; evidence gets reused across factors without differentiation
**Instead:** One call per factor with factor-specific context only

### Anti-Pattern 5: Thinking mode for all LLM calls
**What:** Enabling Qwen3's `/think` mode for every inference call
**Why bad:** Adds 2-5x latency; most tasks (NOC shortlist justify, CA validation) do not benefit from chain-of-thought
**Instead:** `/nothink` for classification and retrieval tasks; `/think` only for JES scoring where deliberate rubric reasoning matters

### Anti-Pattern 6: Single vector index for all corpus types
**What:** One ChromaDB/sqlite-vec collection for NOC + CA + JES data
**Why bad:** Retrieval quality degrades when semantically different document types compete in the same index; NOC duties and CA legal clauses have different semantic distributions
**Instead:** Separate tables/collections per corpus type with typed metadata filters

---

## Scalability Considerations

| Concern | V1 (single user, local) | V2 target (multi-user) |
|---------|------------------------|----------------------|
| LLM throughput | Serial Ollama calls, 1 JD at a time | Queue-based async with priority |
| Vector index | sqlite-vec in single file | Migrate to dedicated vector DB if >100K chunks |
| Session state | SQLite WD store, single file | PostgreSQL + row-level WD isolation |
| Embedding freshness | Re-embed on data update script | Background job triggered by data change |
| Export generation | Synchronous, <5s | Background job with polling |

---

## Sources

- Hybrid retrieval benchmarks (BM25+dense+rerank MRR@5 76.46%): [Building RAG Update: Hybrid Search, Reranking & Production Hardening](https://aboullaite.me/rag-revisited-2026/)
- Constrained LLM reranker (hard candidate constraint pattern): [Rationale-Augmented Retrieval with Constrained LLM Re-Ranking](https://arxiv.org/pdf/2510.05131)
- SQLite-vec for local RAG: [Embedded Intelligence: How SQLite-vec Delivers Fast, Local Vector Search for AI](https://dev.to/aairom/embedded-intelligence-how-sqlite-vec-delivers-fast-local-vector-search-for-ai-3dpb)
- Qwen3 structured output + Ollama: [Constraining LLMs with Structured Output: Ollama, Qwen3 & Python](https://medium.com/@rosgluk/constraining-llms-with-structured-output-ollama-qwen3-python-or-go-2f56ff41d720)
- Qwen3 thinking mode ARM64: [Run Qwen 3 Locally with Ollama](https://localaimaster.com/blog/qwen-3-local-setup-guide)
- Rubric-based analytic scoring criterion-by-criterion: [Rubric-Based Evaluations & LLM-as-a-Judge](https://medium.com/@adnanmasood/rubric-based-evals-llm-as-a-judge-methodologies-and-empirical-validation-in-domain-context-71936b989e80)
- Legal clause provenance in RAG: [Towards Reliable Retrieval in RAG Systems for Large Legal Datasets](https://arxiv.org/html/2510.06999v1)
- Qwen2.5/3 technical capability: [Qwen3 Technical Report](https://arxiv.org/pdf/2505.09388)
- Document chunking for short clauses: [Best Chunking Strategies for RAG (2026)](https://www.firecrawl.dev/blog/best-chunking-strategies-rag)
- Prior architecture (JD-Builder-Lite): `/home/charles/JD-Builder-Lite/.planning/codebase/ARCHITECTURE.md`
- Project requirements: `/home/charles/job_description_builder/.planning/PROJECT.md`
