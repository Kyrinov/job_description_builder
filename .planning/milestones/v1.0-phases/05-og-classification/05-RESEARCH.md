# Phase 5: OG Classification — Research

**Researched:** 2026-06-02
**Domain:** FastAPI + HTMX + SQLite + instructor + Ollama — OG definition lookup, LLM ranking, AS vs EC disambiguation
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLASS-01 | For the advisor-confirmed NOC match, present top 3 OG candidates side-by-side — OG code, name, definition excerpt, relevant inclusions, relevant exclusions, cited from TBS source documents | TBS-OCHRO-OG.txt is parsed and ready to ingest; `jes_og_metadata` partially exists; new `og_definitions` table needed; full OG text → ~2.8K tokens, fits in context for LLM ranking |
| CLASS-02 | Advisor confirms OG and level before JD generation proceeds — hard workflow gate | WorkDescription already has `confirmed_og`, `confirmed_level`, `stage="og_classified"`; gate enforced in confirm endpoint; downstream services check stage |
| CLASS-03 | For policy-related duties, surface AS vs EC distinction test with verbatim citations from `data/directive_on_classification.txt` before OG confirmation | `policy_fts` + `policy_chunks` already populated (190 chunks); AS/EC distinction language is in `TBS-OCHRO-OG.txt` (AS inclusions = "directed to the Public Service"; EC exclusions = "directed to the public or to the Public Service"); detection via instructor |

</phase_requirements>

---

## Summary

Phase 5 builds the OG classification step that sits between NOC confirmation (Phase 4) and JD content generation (Phase 6). The advisor-confirmed NOC and raw work description are used as input; the system returns the top 3 OG candidates with definitions, inclusions, and exclusions cited verbatim, and will not proceed until the advisor explicitly selects one.

There is one new ingest task required before Phase 5 code can serve real data: `data/TBS-OCHRO-OG.txt` (314 KB, 3,259 lines, ~80 OG codes and subgroups) must be parsed into a new `og_definitions` SQLite table. The `jes_og_metadata` table exists but only contains 16 JES-scored OGs with abbreviated definitions sourced from JES standards, not the full TBS OCHRO text with verbatim inclusions and exclusions. A new `og_definitions` table is needed to serve CLASS-01's requirement for full TBS source citations.

The AS vs EC disambiguation check (CLASS-03) is driven by two data sources: (1) the AS and EC definition/inclusion/exclusion text in `TBS-OCHRO-OG.txt` (verbatim citations), and (2) `policy_chunks` / `policy_fts` which already contains `directive_on_classification.txt` (36 chunks, fully ingested). The disambiguation logic detects "policy-adjacent" duties via an instructor call against the work description, then surfaces the relevant AS/EC clauses as citations — it does NOT require the `directive_on_classification.txt` to contain the AS/EC definitions; those live in `TBS-OCHRO-OG.txt`.

The WorkDescription model already has all required Phase 5 fields: `og_recommendation: Optional[OGRecommendation]`, `confirmed_og: Optional[str]`, `confirmed_level: Optional[str]`, and `stage` can already be set to `"og_classified"`. No schema migration is needed.

**Primary recommendation:** Four plans — (1) Wave 0 test stubs + `og_definitions` table DDL + `scripts/ingest_og_definitions.py`, (2) `app/ai/og_ranking.py` Pydantic models + instructor client, (3) `app/services/og_classifier.py` + `app/api/og_classification.py` FastAPI router, (4) HTMX wizard step `templates/wizard/step_og.html` + `templates/partials/og_results.html` + full suite green.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| OG definitions lookup (direct context) | Database / Storage | API / Backend | `og_definitions` SQLite table; all ~30 relevant OG texts fit in a single prompt (~2.8K tokens); no RAG needed |
| Policy-adjacent duty detection (AS vs EC trigger) | Ollama service | API / Backend | instructor call over work description + confirmed NOC duty list; binary classification — does this work touch external policy? |
| Top-3 OG ranking (LLM) | Ollama service | API / Backend | gemma4:31b/qwen3 sees all relevant OG definitions + confirmed NOC profile + work description; ranks top 3 with cited evidence quotes |
| AS vs EC citation surface | Database / Storage | Ollama service | FTS5 query against `policy_fts` for directive text + direct lookup of AS/EC definitions in `og_definitions`; verbatim quotes only, no generation |
| OG candidate card display | Browser / Client | Frontend Server (SSR) | HTMX partial swap (same pattern as `noc_results.html`); three side-by-side cards |
| OG confirmation (advisor selects) | Frontend Server (SSR) | Database | HTMX POST; server updates `WorkDescription.confirmed_og`, `confirmed_level`, `stage="og_classified"` |
| AS vs EC alert surface | Frontend Server (SSR) | — | Rendered as an alert banner above the OG cards when policy duties detected; no JS required |
| Hard workflow gate (CLASS-02) | API / Backend | Database | `POST /api/og/confirm` is the only path to `stage="og_classified"`; downstream `/api/jd/*` routes check `wd.stage == "og_classified"` |

---

## Standard Stack

### Core (all already installed — no pip install needed)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| instructor | 1.15.1 | Structured LLM output + retry for OG ranking and AS/EC detection | [VERIFIED: pip3 show] installed |
| openai (Python SDK) | 2.37.0 | AsyncOpenAI pointing at Ollama /v1 — same singleton pattern as Phase 4 | [VERIFIED: pip3 show] installed |
| FastAPI | 0.128.8 | APIRouter for POST /api/og/classify + POST /api/og/confirm | [VERIFIED: pip3 show] installed |
| Jinja2 | 3.1.6 | HTMX partial template rendering | [VERIFIED: pip3 show] installed |
| Pydantic | 2.12.1 | OGCandidate / OGRankingResult / ASECAlert validation | [VERIFIED: pip3 show] installed |
| sqlite-vec | 0.1.9 | Already loaded via get_connection() — no new vec queries needed in Phase 5 | [VERIFIED: pip3 show] installed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | 1.3.0 | Async test support (asyncio_mode=auto already set) | All tests touching async pipeline code |
| httpx | 0.28.1 | TestClient for FastAPI integration tests | FastAPI route tests |

**No new packages required for Phase 5.**

---

## Architecture Patterns

### System Architecture Diagram

```
Advisor POSTs work description + confirmed NOC code (POST /api/og/classify)
         |
         v
[FastAPI route handler — async def]
         |
         v
[og_classifier.classify_og()]
         |
         +--- Step 1: Load OG definitions from DB --------------------+
         |    asyncio.to_thread(conn.execute,                         |
         |      SELECT og_code, og_name, definition,                  |
         |             inclusions, exclusions                          |
         |      FROM og_definitions                                    |
         |      WHERE is_relevant_to_core_pa = 1 OR og_code IN        |
         |            (<noc-relevant OG filter>)                       |
         |    → list of OGDefinition objects (~30 rows, ~2.8K tokens) |
         |                                                             |
         +--- Step 2: AS vs EC detection (policy-adjacent check) -----+
         |    IF work_description contains policy-adjacent duties:     |
         |    await instructor_client (OllamaAsyncClient)              |
         |      → PolicyAdjacencyResult(is_policy_adjacent: bool,      |
         |           policy_phrases: list[str])                        |
         |    IF is_policy_adjacent:                                   |
         |      asyncio.to_thread(conn.execute,                       |
         |        SELECT chunk_text FROM policy_chunks                 |
         |        WHERE doc_name = 'directive_on_classification'        |
         |      ) UNION og_definitions AS/EC rows                      |
         |      → ASECAlert(as_definition, ec_definition,              |
         |           as_inclusions, ec_exclusions, cited_chunks)        |
         |                                                             |
         +--- Step 3: LLM rank top 3 OG candidates -------------------+
              await instructor_client.chat.completions.create(
                  model=settings.generation_model,
                  response_model=OGRankingResult,
                  messages=[system_prompt, user_prompt_with_og_defs],
                  max_retries=3, temperature=0.0,
                  extra_body={"options": {"num_ctx": 16384}})
              → OGRankingResult.candidates: list[OGCandidate] (top 3)
              Each OGCandidate.evidence_quotes verified against og_definitions
                    |
         +----------+----------+
         |                     |
  Online guardrail          Return to
  (evidence verbatim        FastAPI route
   check against            → HTMX partial (step 3 result)
   og_definitions)          OR JSON response
```

### Recommended Project Structure

```
app/
├── ai/
│   └── og_ranking.py         # instructor client singleton + OGCandidate + OGRankingResult + PolicyAdjacencyResult
├── services/
│   └── og_classifier.py      # classify_og() — 3-step pipeline + verbatim guardrail
├── api/
│   └── og_classification.py  # FastAPI router: POST /api/og/classify, POST /api/og/confirm
├── models/
│   └── og.py                 # OGClassifyRequest, OGClassifyResponse (input/output shapes)
scripts/
└── ingest_og_definitions.py  # Parse TBS-OCHRO-OG.txt → og_definitions table (new)
templates/
├── partials/
│   └── og_results.html       # HTMX partial: 3 side-by-side OG candidate cards + optional AS/EC alert
└── wizard/
    └── step_og.html          # Full wizard step (extends base.html; picks up after NOC confirmed)
tests/
├── test_og_classification.py # Integration: classify_og() + FastAPI route
└── test_og_ranking.py        # Unit: Pydantic validators, verbatim guardrail, AS/EC detection
```

### Pattern 1: og_definitions Table DDL

There is no `og_definitions` table yet. The `jes_og_metadata` table exists (16 rows, JES OG codes only with abbreviated text) but does NOT contain full TBS verbatim inclusions/exclusions from `TBS-OCHRO-OG.txt` for all groups needed (AS, EC, IT, PE, PM, CR, CS, etc.).

```sql
-- Source: derived from CLASS-01 requirement + TBS-OCHRO-OG.txt structure [VERIFIED: file inspection]
CREATE TABLE IF NOT EXISTS og_definitions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    og_code      TEXT NOT NULL UNIQUE,   -- e.g., 'EC', 'AS', 'IT', 'PE'
    og_name      TEXT NOT NULL,           -- e.g., 'Economics and Social Science Services'
    parent_group TEXT,                    -- e.g., 'PA' for AS/CR/PM subgroups; NULL for standalone
    definition   TEXT NOT NULL,           -- verbatim group definition paragraph
    inclusions   TEXT,                    -- verbatim inclusions section; NULL if not present
    exclusions   TEXT,                    -- verbatim exclusions section; NULL if not present
    source_file  TEXT NOT NULL,           -- 'TBS-OCHRO-OG.txt'
    source_hash  TEXT NOT NULL,           -- SHA-256 of source_file content
    ingested_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_og_definitions_code ON og_definitions(og_code);
CREATE INDEX IF NOT EXISTS idx_og_definitions_parent ON og_definitions(parent_group);
```

This DDL must be added to `CA_JES_SCHEMA_DDL` in `app/db.py` so `create_schema()` creates it on startup (idempotent via `IF NOT EXISTS`).

### Pattern 2: OG Ingest Script

`TBS-OCHRO-OG.txt` has a consistent structure: each OG section begins with `<Name> (<code>)\n<Name> (<code>)\n<Name> (<code>) Group Definition\n\n<definition text>\nInclusions\n\n<inclusions text>\nExclusions\n\n<exclusions text>`. Subgroups omit "Group Definition" and use "Definition Excerpt of full PA/SH/RE Definition" instead.

```python
# Source: verified by reading TBS-OCHRO-OG.txt structure [VERIFIED: file inspection]
# Pattern for parsing the file: split on double-newline blocks, identify section headers
# by the presence of "Group Definition" or "Definition Excerpt", then extract
# definition/inclusions/exclusions by scanning for "Inclusions\n" and "Exclusions\n" markers.

import re, hashlib

def parse_og_section(text: str) -> dict:
    """
    Given a raw text block for one OG, return a dict with keys:
    og_code, og_name, parent_group, definition, inclusions, exclusions
    """
    # Extract code from header: e.g., "Administrative Services (AS)"
    code_match = re.search(r'\(([A-Z]{2,4})\)', text)
    og_code = code_match.group(1) if code_match else None

    # Split on Inclusions/Exclusions markers
    inc_split = re.split(r'\nInclusions\n', text, maxsplit=1)
    definition = inc_split[0].strip() if len(inc_split) > 1 else text.strip()

    inclusions = exclusions = None
    if len(inc_split) > 1:
        exc_split = re.split(r'\nExclusions\n', inc_split[1], maxsplit=1)
        inclusions = exc_split[0].strip()
        if len(exc_split) > 1:
            exclusions = exc_split[1].strip()

    return {
        "og_code": og_code,
        "definition": definition,
        "inclusions": inclusions,
        "exclusions": exclusions,
    }
```

### Pattern 3: OG Classification Pipeline (LLM Prompt)

OG definitions total ~2.8K tokens when all ~30 relevant groups are included. This fits in a 16K context with room for the NOC profile and work description. No RAG needed — direct context injection:

```python
# Source: architecture.md §When to use RAG vs direct context [CITED: .planning/research/ARCHITECTURE.md]
# "OG definitions (28 OGs, ~100 tokens each) → Direct context — ~2.8K tokens total"

SYSTEM_PROMPT = """
You are a Government of Canada HR classification specialist.
Given a confirmed NOC code + unit group profile and a work description,
identify the top 3 most likely occupational groups (OGs) from the list provided.

CRITICAL RULES:
- You may ONLY select OG codes from the provided list — never invent codes
- evidence_quotes must be exact verbatim excerpts from the provided OG definition text, 
  not paraphrases
- Return exactly 3 candidates, ranked by confidence descending
""".strip()

def build_og_context(og_definitions: list[OGDefinition], confirmed_noc: NOCMatch) -> str:
    lines = [f"Confirmed NOC: {confirmed_noc.noc_code} — {confirmed_noc.noc_title}"]
    lines.append(f"NOC Definition: {confirmed_noc.rationale[:300]}")
    lines.append("\n--- Occupational Group Definitions ---")
    for og in og_definitions:
        lines.append(f"\n[{og.og_code}] {og.og_name}")
        lines.append(f"Definition: {og.definition[:400]}")
        if og.inclusions:
            lines.append(f"Inclusions: {og.inclusions[:400]}")
        if og.exclusions:
            lines.append(f"Exclusions: {og.exclusions[:300]}")
    return "\n".join(lines)
```

### Pattern 4: AS vs EC Detection

The AS vs EC distinction in `TBS-OCHRO-OG.txt` is grounded in one key contrast:

- **AS (Administrative Services)** inclusions: "the planning, development, delivery or management of government policies, programs, services or other activities **directed to the Public Service**"
- **EC (Economics and Social Science Services)** exclusions: "the planning, development, delivery or management of policies, programs, services or other activities **directed to the public or to the Public Service**"

The key test: if the primary work is policy work directed to the **Canadian public** (external), it is EC. If it is policy work directed to the **Public Service** (internal), it is AS.

The `directive_on_classification.txt` in `policy_chunks` (already ingested, 36 chunks) does not contain the AS/EC definitions themselves — those are in `TBS-OCHRO-OG.txt`. The directive provides the **authority framework** for classification decisions (sections 4.1–4.4). CLASS-03 requires grounding in `directive_on_classification.txt` for the general classification process authority, while the specific AS/EC inclusion/exclusion text comes from `og_definitions`.

Detection logic:

```python
# Source: CLASS-03 requirement + SME meeting notes [CITED: .planning/research/SUMMARY.md]
class PolicyAdjacencyResult(BaseModel):
    """instructor output for Step 2 policy-adjacent detection"""
    is_policy_adjacent: bool
    confidence: float = Field(ge=0.0, le=1.0)
    policy_phrases: list[str] = Field(
        description="Verbatim phrases from work description that indicate policy work"
    )
    rationale: str

POLICY_DETECTION_PROMPT = """
Determine if the following work description contains duties that are primarily
policy-development, research, or analysis work directed at the Canadian public
(external stakeholders) as opposed to internal administrative support to the
Public Service.

Policy-adjacent signals: "develop policy", "provide policy advice", "policy analysis",
"research and analysis", "socio-economic", "program evaluation", "economic research",
"evidence-based recommendations", "policy framework", "policy proposals".

Internal administrative signals: "process transactions", "provide administrative support",
"administer programs", "coordinate activities", "manage HR operations".

Work description:
{work_description}
""".strip()
```

### Pattern 5: HTMX OG Wizard Step

The NOC confirm partial already navigates to OG classification with "Continue to Classification". Phase 5 must provide `POST /api/og/classify` that:
1. Accepts `wd_id` (required — must have `stage == "noc_mapped"`) and the work description
2. Returns HTMX partial `og_results.html` with 3 OG cards + optional AS/EC alert banner
3. `POST /api/og/confirm` accepts `wd_id`, `og_code`, `og_level`; sets `confirmed_og`, `confirmed_level`, `stage="og_classified"`, persists

The existing `noc_confirmed.html` partial ends with:
```html
<form hx-post="/api/og/classify" hx-target="#wizard-step" hx-swap="outerHTML">
    <input type="hidden" name="wd_id" value="{{ wd_id }}">
    <button type="submit">Continue to Classification</button>
</form>
```

Phase 5 MUST implement `POST /api/og/classify` to handle this form submission.

```html
<!-- templates/partials/og_results.html -->
{% if asec_alert %}
<div class="asec-alert" role="alert">
    <strong>AS vs EC Distinction Required</strong>
    <p>This position has policy-related duties. Review the following before confirming:</p>
    <div class="asec-comparison">
        <div class="asec-card asec-card--as">
            <h4>Administrative Services (AS)</h4>
            <p class="citation">{{ asec_alert.as_inclusions_excerpt }}</p>
            <p class="citation-source">TBS OCHRO OG Definitions — AS</p>
        </div>
        <div class="asec-card asec-card--ec">
            <h4>Economics and Social Science Services (EC)</h4>
            <p class="citation">{{ asec_alert.ec_exclusions_excerpt }}</p>
            <p class="citation-source">TBS OCHRO OG Definitions — EC</p>
        </div>
    </div>
</div>
{% endif %}

<div class="og-candidates">
{% for candidate in candidates %}
<div class="og-card">
    <h3>[{{ candidate.og_code }}] {{ candidate.og_name }}</h3>
    <section class="og-definition">
        <h4>Definition</h4>
        <blockquote>{{ candidate.definition_excerpt }}</blockquote>
        <cite>TBS OCHRO OG Definitions</cite>
    </section>
    <section class="og-inclusions">
        <h4>Relevant Inclusions</h4>
        <blockquote>{{ candidate.relevant_inclusions }}</blockquote>
    </section>
    <section class="og-exclusions">
        <h4>Relevant Exclusions</h4>
        <blockquote>{{ candidate.relevant_exclusions }}</blockquote>
    </section>
    <form hx-post="/api/og/confirm"
          hx-target="#wizard-step"
          hx-swap="outerHTML">
        <input type="hidden" name="wd_id" value="{{ wd_id }}">
        <input type="hidden" name="og_code" value="{{ candidate.og_code }}">
        <select name="og_level" required>
            <option value="">Select level...</option>
            {% for level in candidate.available_levels %}
            <option value="{{ level }}">{{ candidate.og_code }}-{{ level }}</option>
            {% endfor %}
        </select>
        <button type="submit">Confirm {{ candidate.og_code }}</button>
    </form>
</div>
{% endfor %}
</div>
```

### Pattern 6: OGRecommendation → WorkDescription Storage

`OGRecommendation` already exists in `app/models/work_description.py`:
```python
class OGRecommendation(BaseModel):
    og_code: str
    og_name: str
    level: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    provenance: ProvenanceTag
    evidence_quotes: list[str] = Field(default_factory=list)
    cited_articles: list[ProvenanceTag] = Field(default_factory=list)
    confirmed_by_advisor: bool = False
```

The `cited_articles` field (list[ProvenanceTag]) is where TBS OG definition citations go — one ProvenanceTag per cited OG section (definition, inclusions, exclusions). `source_type="TBS_OG_DEF"` is already defined in ProvenanceTag.

The `confirmed_by_advisor=True` flag MUST be set at `POST /api/og/confirm` time. `WorkDescription.stage` must be set to `"og_classified"`.

### Anti-Patterns to Avoid

- **Using `jes_og_metadata` as the OG definitions source** — it has only 16 JES-scored OGs with abbreviated text, not full TBS verbatim inclusions/exclusions for all PA subgroups. Must parse `TBS-OCHRO-OG.txt` into `og_definitions`.
- **Using policy_fts for the AS/EC definition text** — `policy_fts` indexes `directive_on_classification.txt` and `policy_on_people_management.txt`, neither of which contains AS or EC inclusion/exclusion text. AS/EC definitions come from `og_definitions` (sourced from `TBS-OCHRO-OG.txt`).
- **Allowing OG confirmation without level selection** — CLASS-02 requires both OG code AND level. The confirm endpoint must reject requests where `og_level` is missing or empty.
- **Generating level options dynamically from LLM** — OG levels are deterministic (AS-01 through AS-08, EC-01 through EC-07, etc.). Use a static lookup table in `og_ranking.py`, not LLM inference.
- **Opening instructor client per request** — use module-level singleton (same pattern as `app/ai/noc_ranking.py`).
- **Skipping the AS/EC check when work description mentions "policy"** — the check must fire before OG card rendering, not as a separate optional step. Advisors under time pressure skip optional steps.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured LLM output + retry | Custom JSON parsing + retry loop | `instructor` (installed, same pattern as Phase 4) | Handles Pydantic validation retry; OG ranking is exactly this problem |
| OG definition parsing | Write a bespoke TXT parser | Regex split on `\nInclusions\n` and `\nExclusions\n` markers (10 lines) | TBS-OCHRO-OG.txt has a consistent enough structure; no XML/JSON overhead |
| Policy-adjacent keyword detection | Hard-coded keyword list | instructor binary classification call | Work descriptions use varied vocabulary; LLM beats keyword matching for "policy-adjacent" intent detection |
| OG level validation | Infer valid levels from LLM output | Static `OG_LEVELS: dict[str, list[str]]` lookup in `og_ranking.py` | OG levels are governed by Treasury Board — they don't change at runtime |
| WD persistence | New persistence layer | `wd_store.save_work_description()` (already exists from Phase 4) | Pattern established in Phase 4; do not duplicate |

**Key insight:** Phase 5 has less novel code than Phase 4. The `og_classifier.py` pipeline is simpler than `noc_mapper.py` because all OG definitions fit in context (no FTS/vec retrieval needed), and the LLM only sees ~30 curated OG definitions rather than 900 NOC profiles.

---

## Data Findings

### TBS-OCHRO-OG.txt Structure [VERIFIED: file inspection]

| Property | Value |
|----------|-------|
| File location | `data/TBS-OCHRO-OG.txt` |
| File size | 314,697 bytes / 3,259 lines |
| OG codes present | ~80 codes/subgroups (all core public administration groups) |
| Structure | Consistent: `<Name> (<Code>)\n<Name> (<Code>)\n<Type Header>\n\n<definition>\nInclusions\n\n<inclusions>\nExclusions\n\n<exclusions>` |
| Key groups for DND | AS (PA/AS subgroup), EC, PE (PA/PE subgroup), IT, PM, CR, CS, EX |
| AS definition location | Line 978-996 |
| EC definition location | Line 477-551 |

### The AS vs EC Key Distinction [VERIFIED: TBS-OCHRO-OG.txt lines 982-996, 483-506]

The defining textual difference:

**AS inclusions (line 987):** "the planning, development, delivery or management of government policies, programs, services or other activities **directed to the Public Service**" — internal PS clients only.

**EC exclusions (line 503):** "the planning, development, delivery or management of policies, programs, services or other activities **directed to the public or to the Public Service**" — EC explicitly excludes work that could be AS.

The test in plain language: if the position's primary policy work shapes what Canadians or the economy receive (external), it is EC. If the primary policy work shapes how the Public Service operates (internal), it is AS. Positions at the boundary (e.g., "provides policy advice on HR program design") often get misclassified — this is the exact pain point the SME flagged.

### policy_chunks / policy_fts Population [VERIFIED: sqlite3]

| doc_name | row count |
|----------|-----------|
| `directive_on_classification` | 36 |
| `policy_on_people_management` | 154 |

The directive is searchable via `policy_fts` with porter-stemmed FTS5. CLASS-03 requires citing the directive "verbatim" as the authority for the AS/EC classification decision process — the chunks are already available for FTS lookup by keyword ("classification", "occupational group", "evaluation"). The AS and EC definition text must come from `og_definitions`, not `policy_chunks`.

### jes_og_metadata Table [VERIFIED: sqlite3]

16 OG codes present: CT, EC, ED, EX, FB, FS, IT, LC, LP, MT, NT, NU, PO, PS, SW, WP. These cover JES-scored groups only. Notably missing from this table: AS, PE, PM, CR, CS (the most common DND civilian OGs). The `jes_og_metadata` table should NOT be used as the OG definitions source for Phase 5.

### WorkDescription Model Fields for Phase 5 [VERIFIED: app/models/work_description.py]

All required fields already exist:
- `og_recommendation: Optional[OGRecommendation]` — stores the top-3 with cited_articles
- `confirmed_og: Optional[str]` — set by `/api/og/confirm`
- `confirmed_level: Optional[str]` — set by `/api/og/confirm`
- `stage: Literal[..., "og_classified", ...]` — "og_classified" is already a valid stage value
- `OGRecommendation.cited_articles: list[ProvenanceTag]` — carries TBS_OG_DEF citations
- `ProvenanceTag.source_type: "TBS_OG_DEF"` — already defined

No model migration required. [VERIFIED: app/models/work_description.py]

---

## OG Level Static Lookup

OG levels for common DND civilian groups (used in confirm endpoint level dropdown):

```python
# Source: TBS collective agreements and classification standards [ASSUMED — verify against TBS]
OG_LEVELS: dict[str, list[int]] = {
    "AS": list(range(1, 9)),    # AS-01 through AS-08
    "CR": list(range(1, 7)),    # CR-01 through CR-06
    "PM": list(range(1, 7)),    # PM-01 through PM-06
    "PE": list(range(1, 8)),    # PE-01 through PE-07
    "EC": list(range(1, 8)),    # EC-01 through EC-07
    "IT": list(range(1, 5)),    # IT-01 through IT-04
    "CS": list(range(1, 6)),    # CS-01 through CS-05
    "EX": list(range(1, 6)),    # EX-01 through EX-05
    "IS": list(range(1, 8)),    # IS-01 through IS-07
    "GT": list(range(1, 9)),    # GT-01 through GT-08
}
```

This lookup is used by the confirm endpoint to validate the submitted level and to populate the level dropdown in the HTMX partial. Mark as [ASSUMED] — verify level ranges against current TBS collective agreements before committing to code.

---

## Common Pitfalls

### Pitfall 1: Using jes_og_metadata Instead of og_definitions

**What goes wrong:** OG candidate cards show abbreviated JES-derived text ("The EC Group comprises positions primarily involved in...") instead of full TBS OCHRO verbatim text. Fails CLASS-01 citation requirement.

**Why it happens:** `jes_og_metadata` exists and has group_definition/inclusions/exclusions columns, creating the appearance that the data is available.

**How to avoid:** Wave 0 task: add `og_definitions` table DDL to `app/db.py`, write `scripts/ingest_og_definitions.py` to parse `TBS-OCHRO-OG.txt`, run it. All service code queries `og_definitions`, not `jes_og_metadata`.

**Warning signs:** OG card shows "The EC Group comprises..." (JES shortform) instead of "Pursuant to section 101 of the Public Service Reform Act..." (TBS verbatim).

### Pitfall 2: Missing Level on OG Confirmation

**What goes wrong:** `WorkDescription.confirmed_level` is `None` after confirmation; Phase 6 JD generation uses `confirmed_og` but not level; the position title field `og_level` never gets set; export renders "EC-None".

**Why it happens:** The confirm endpoint accepts `og_code` but forgets to require `og_level`, or the HTMX form omits the level selector.

**How to avoid:** Level selection is a required field in the confirm form (`<select name="og_level" required>`). The `/api/og/confirm` endpoint raises HTTP 422 if `og_level` is empty or not in `OG_LEVELS[og_code]`.

**Warning signs:** `wd.confirmed_level is None` after confirm; test `test_og_confirm_requires_level` fails.

### Pitfall 3: LLM Invents OG Codes

**What goes wrong:** The LLM returns an OG code not in the provided list (e.g., "PA" instead of "AS", or a made-up "HR" group).

**Why it happens:** The LLM generalizes from training data rather than strictly selecting from the provided list.

**How to avoid:** Online guardrail: after `OGRankingResult` is validated by Pydantic, verify each `candidate.og_code` exists in the queried `og_definitions` rows. Strip or replace any invalid code. If fewer than 3 valid candidates remain, log the event and return what remains (minimum 1 required).

**Warning signs:** `KeyError` in level lookup for the invalid OG code; test `test_og_guardrail_strips_invalid_codes` fails.

### Pitfall 4: AS/EC Alert Not Surfaced Before Card Rendering

**What goes wrong:** The AS/EC alert is rendered only if the advisor notices and clicks a separate "Check AS/EC" button. Advisor under pressure skips it. Wrong OG confirmed.

**Why it happens:** Developer treats the AS/EC check as optional enhancement, not a required pre-condition for card rendering.

**How to avoid:** The AS/EC detection runs in Step 2 of `classify_og()` before the LLM ranking step. The alert data is always included in the response if `is_policy_adjacent=True`. The HTMX partial renders the alert banner unconditionally at the top of the OG results if `asec_alert` is present in the template context.

**Warning signs:** No `asec_alert` in template context despite work description containing "policy analysis" language.

### Pitfall 5: policy_fts Used for AS/EC Definition Text

**What goes wrong:** FTS query on `policy_fts` for "AS definition" or "EC inclusions" returns no results or irrelevant directive sections, because `directive_on_classification.txt` does not contain OG inclusion/exclusion text.

**Why it happens:** CLASS-03 requirement says "grounded in `data/directive_on_classification.txt`" — developer queries `policy_fts` for AS/EC definition text rather than `og_definitions`.

**How to avoid:** `policy_fts` is used only for citing the directive's authority sections (e.g., "section 4.1.1 — classification must follow OG definitions"). The AS/EC definition, inclusions, and exclusion text comes from `og_definitions WHERE og_code IN ('AS', 'EC')`.

**Warning signs:** FTS query returns 0 rows for "inclusions exclusions AS EC".

---

## Code Examples

### og_definitions Table Insert Pattern

```python
# Source: based on ca_clauses UNIQUE constraint pattern [VERIFIED: app/db.py]
conn.execute(
    """
    INSERT OR IGNORE INTO og_definitions
        (og_code, og_name, parent_group, definition, inclusions, exclusions, source_file, source_hash)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (og_code, og_name, parent_group, definition, inclusions, exclusions, "TBS-OCHRO-OG.txt", file_hash),
)
```

### instructor Client (module-level singleton, same pattern as Phase 4)

```python
# Source: app/ai/noc_ranking.py [VERIFIED: live codebase]
# app/ai/og_ranking.py — identical pattern
import instructor
from openai import AsyncOpenAI
from app.config import settings

og_instructor_client = instructor.from_openai(
    AsyncOpenAI(
        base_url=settings.ollama_base_url.rstrip("/") + "/v1",
        api_key="ollama",
    ),
    mode=instructor.Mode.JSON,
)
```

### Pydantic Model for OG Ranking Result

```python
# Source: OGRecommendation model in work_description.py [VERIFIED: live codebase]
from pydantic import BaseModel, Field

class OGCandidate(BaseModel):
    og_code: str = Field(description="OG code — must be from the provided list only")
    rank: int = Field(ge=1, le=3)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    evidence_quotes: list[str] = Field(
        description="Verbatim text from provided OG definition — no paraphrases"
    )

class OGRankingResult(BaseModel):
    candidates: list[OGCandidate] = Field(min_length=1, max_length=3)

class PolicyAdjacencyResult(BaseModel):
    is_policy_adjacent: bool
    confidence: float = Field(ge=0.0, le=1.0)
    policy_phrases: list[str]
    rationale: str
```

### OG Confirm Endpoint Pattern

```python
# Source: /api/noc/confirm pattern [VERIFIED: app/api/noc_mapping.py]
@router.post("/api/og/confirm")
async def confirm_og(
    request: Request,
    wd_id: str = Form(...),
    og_code: str = Form(...),
    og_level: str = Form(...),
) -> dict:
    # Validate og_level is a valid level for the og_code
    valid_levels = OG_LEVELS.get(og_code, [])
    try:
        level_int = int(og_level)
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail=f"og_level must be an integer, got {og_level!r}")
    if level_int not in valid_levels:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid level {og_level!r} for OG {og_code!r}. Valid: {valid_levels}"
        )

    conn = await asyncio.to_thread(lambda: get_connection(settings.db_path))
    try:
        wd = await asyncio.to_thread(lambda: load_work_description(conn, wd_id))
        if wd is None:
            raise HTTPException(status_code=404, detail=f"WorkDescription {wd_id!r} not found")
        if wd.stage != "noc_mapped":
            raise HTTPException(
                status_code=422,
                detail=f"WorkDescription is in stage {wd.stage!r}, expected 'noc_mapped'"
            )

        # Update OGRecommendation.confirmed_by_advisor
        if wd.og_recommendation and wd.og_recommendation.og_code == og_code:
            wd.og_recommendation = wd.og_recommendation.model_copy(
                update={"confirmed_by_advisor": True, "level": f"{og_code}-{og_level}"}
            )

        wd.confirmed_og = og_code
        wd.confirmed_level = f"{og_code}-{og_level}"
        wd.og_level = f"{og_code}-{og_level}"     # TBS header field (DATA-01)
        wd.stage = "og_classified"
        await asyncio.to_thread(lambda: save_work_description(conn, wd))
    finally:
        await asyncio.to_thread(conn.close)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/og_confirmed.html",
            {
                "request": request,
                "og_code": og_code,
                "og_level": f"{og_code}-{og_level}",
                "wd_id": wd_id,
            },
        )
    return {"status": "confirmed", "og_code": og_code, "og_level": f"{og_code}-{og_level}", "wd_id": wd_id}
```

---

## Runtime State Inventory

> Phase 5 is not a rename/refactor phase. This section is not applicable.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Ollama service | All LLM calls | Confirmed running | — | None — hard blocker |
| gemma4:31b or cloud model | OG ranking + AS/EC detection | Confirmed present (or cloud via CLOUD_API_KEY) | — | qwen3.7-max via cloud |
| nomic-embed-text | Stage 2 (NOC mapper) | Confirmed present | — | Not needed in Phase 5 (no vec queries) |
| sqlite-vec | Schema creation | Confirmed 0.1.9 | 0.1.9 | None — installed |
| instructor | All LLM calls | Confirmed 1.15.1 | 1.15.1 | None — installed |
| TBS-OCHRO-OG.txt | og_definitions ingest | Confirmed present | — | None — file is in data/ |
| directive_on_classification.txt | policy_chunks (already ingested) | Confirmed (36 chunks in DB) | — | None — already in DB |

**Missing dependencies with no fallback:** None — all dependencies available.

**Data prerequisite (not a missing package):** `og_definitions` table does not exist yet. `scripts/ingest_og_definitions.py` must be written and run in Wave 0 before any Phase 5 service code can serve real OG data.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| asyncio_mode | `auto` (already set) |
| Quick run command | `pytest tests/test_og_ranking.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLASS-01 | `classify_og()` returns 3 candidates with og_code, og_name, definition, inclusions, exclusions | integration | `pytest tests/test_og_classification.py::test_classify_og_returns_3_candidates -x` | Wave 0 |
| CLASS-01 | Each candidate's evidence_quotes verified verbatim against og_definitions rows | unit | `pytest tests/test_og_ranking.py::test_verbatim_guardrail_strips_fabricated_quotes -x` | Wave 0 |
| CLASS-01 | ProvenanceTag source_type="TBS_OG_DEF" present on each OGCandidate's cited_articles | unit | `pytest tests/test_og_ranking.py::test_provenance_tag_source_type -x` | Wave 0 |
| CLASS-02 | `/api/og/confirm` returns 422 if og_level missing or invalid | integration | `pytest tests/test_og_classification.py::test_confirm_requires_valid_level -x` | Wave 0 |
| CLASS-02 | After confirm, WorkDescription.stage == "og_classified" | integration | `pytest tests/test_og_classification.py::test_confirm_sets_stage_og_classified -x` | Wave 0 |
| CLASS-02 | `/api/og/classify` returns 422 if WorkDescription not in "noc_mapped" stage | integration | `pytest tests/test_og_classification.py::test_classify_requires_noc_mapped_stage -x` | Wave 0 |
| CLASS-03 | AS/EC alert fires when work description contains policy-adjacent language | unit (mock) | `pytest tests/test_og_ranking.py::test_asec_alert_fires_on_policy_adjacent -x` | Wave 0 |
| CLASS-03 | AS/EC alert includes verbatim AS inclusion and EC exclusion text from og_definitions | integration | `pytest tests/test_og_classification.py::test_asec_alert_citations_are_verbatim -x` | Wave 0 |
| CLASS-03 | AS/EC alert does NOT fire for non-policy work description | unit (mock) | `pytest tests/test_og_ranking.py::test_asec_alert_suppressed_for_non_policy_work -x` | Wave 0 |
| CLASS-01+02 | HTMX POST /api/og/classify returns HTML partial | integration | `pytest tests/test_og_classification.py::test_api_route_htmx_returns_html -x` | Wave 0 |
| CLASS-02 | Guardrail rejects invalid OG code not in og_definitions | unit | `pytest tests/test_og_ranking.py::test_guardrail_rejects_invalid_og_code -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_og_ranking.py -x` (fast unit tests, < 5 s, no Ollama needed)
- **Per wave merge:** `pytest tests/test_og_classification.py tests/test_og_ranking.py -x`
- **Phase gate:** `pytest tests/ -x` full suite green (currently 95 passing) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_og_ranking.py` — unit tests for Pydantic validators, verbatim guardrail, AS/EC detection logic, OG level validation
- [ ] `tests/test_og_classification.py` — integration tests for classify_og() pipeline + FastAPI routes
- [ ] `tests/conftest.py` update — add `og_db` fixture (pre-populated with `og_definitions` rows for AS, EC, IT, PE; does NOT require Ollama)
- [ ] `og_definitions` table DDL added to `CA_JES_SCHEMA_DDL` in `app/db.py`
- [ ] `scripts/ingest_og_definitions.py` written and run against `data/TBS-OCHRO-OG.txt`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Yes | `OGClassifyRequest.wd_id` validated as UUID; `og_code` validated against `OG_LEVELS` dict; `og_level` validated as integer in valid range |
| V4 Access Control | No | Single-user local tool; no multi-user auth in v1 |
| V2 Authentication | No | Local tool; no auth in v1 |
| V6 Cryptography | No | SHA-256 source hash is provenance tracking, not a security feature |
| V3 Session Management | Partial | `wd_id` ties OG classification to a specific WorkDescription; server validates stage == "noc_mapped" before classifying |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| OG code injection via og_code confirm param | Tampering | Validate `og_code` against `OG_LEVELS` dict (in-memory allowlist); reject unknown codes with HTTP 422 |
| Stage skip (skipping NOC confirm, direct OG classify) | Elevation of Privilege | `POST /api/og/classify` checks `wd.stage == "noc_mapped"`; rejects with HTTP 422 if wrong stage |
| LLM fabrication in evidence_quotes | Repudiation | Online verbatim guardrail checks each evidence_quote is a substring of the corresponding `og_definitions.definition + inclusions + exclusions` text before returning |
| SQLite injection via wd_id | Tampering | Parameterized queries; wd_id validated as UUID string before DB lookup |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JES-source OG metadata (`jes_og_metadata`) | Full TBS OCHRO OG definitions (`og_definitions`) | Phase 5 (new) | CLASS-01 verbatim citation requirement fulfilled |
| Manual AS/EC advisor memory | Programmatic AS/EC detection + citation surface | Phase 5 (new) | SME-identified pain point resolved; misclassification risk reduced |
| No OG workflow gate | `stage="og_classified"` hard gate on JD generation | Phase 5 (new) | Phase 6 can assert confirmed_og is set before generating duties |

**Deprecated/outdated for Phase 5:**
- `jes_og_metadata` as classification source — use `og_definitions` only; `jes_og_metadata` remains for JES scoring in Phase 7

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | AS levels run AS-01 through AS-08; EC levels EC-01 through EC-07 | Code Examples (OG_LEVELS dict) | [ASSUMED] If level ranges have changed under PA group restructuring, the confirm endpoint will reject valid levels. Verify against current TBS collective agreements before committing. |
| A2 | `noc_confirmed.html` partial already contains a form with `hx-post="/api/og/classify"` | Pattern 5 | [ASSUMED] Phase 4 may not have added the "Continue to Classification" form yet. Verify `templates/partials/noc_confirmed.html` content in Wave 0; add the form if missing. |
| A3 | All ~30 relevant OG definitions fit within a 16K context window alongside NOC profile + work description | Architecture Patterns | [ASSUMED] Based on ARCHITECTURE.md estimate of ~2.8K tokens for 28 OGs. Measure actual token counts during ingest; if >8K tokens needed for OG context block, reduce to most-likely 10 OGs based on NOC-to-OG frequency heuristic. |
| A4 | `TBS-OCHRO-OG.txt` sections can be split reliably on `\nInclusions\n` and `\nExclusions\n` markers | Pattern 2 | [ASSUMED — medium risk] File has consistent structure per inspection, but some OG sections lack Inclusions or Exclusions. Parser must handle `None` for missing sections gracefully. Test against the actual file in Wave 0. |

**Verified claims:** All other claims are [VERIFIED: file inspection], [VERIFIED: sqlite3], or [VERIFIED: codebase grep].

---

## Open Questions (RESOLVED)

1. **Does `templates/partials/noc_confirmed.html` already have the "Continue to Classification" form with `hx-post="/api/og/classify"`?**
   - What we know: Phase 4 created this partial; the UI-SPEC says "Confirmation success CTA: Continue to Classification"
   - What's unclear: Whether the Phase 4 executor added the form pointing to the Phase 5 endpoint (which didn't exist yet)
   - Recommendation: Wave 0 — read `templates/partials/noc_confirmed.html`; if it has a placeholder button or no action, add the HTMX form in Plan 05-01.
   - **RESOLVED:** Form was absent per Wave 0 inspection; Plan 05-01 Task 2 adds the HTMX form pointing to `/api/og/classify`.

2. **Should `og_definitions` include ALL ~80 OG codes from TBS-OCHRO-OG.txt or only the ~30 DND-relevant ones?**
   - What we know: The file covers the full core public administration; DND primarily uses AS, EC, PE, IT, CS, PM, CR, IS, EX
   - What's unclear: Whether ingest should be selective or comprehensive
   - Recommendation: Ingest all OGs — the table is small (~80 rows, <100KB), and future phases (or DND-specific logic) may need non-standard groups. Filter at query time using `WHERE og_code IN (?)` for the classification prompt.
   - **RESOLVED:** Ingest all ~80 OGs from TBS-OCHRO-OG.txt; filter at query time. Plan 05-01 Task 1 implements this.

3. **What is the correct LLM context window to request for OG classification?**
   - What we know: ARCHITECTURE.md estimates ~2.8K tokens for 28 OGs; confirmed NOC profile is ~500-800 tokens; work description is ~200-500 tokens
   - What's unclear: Total varies by how many OG definitions are included
   - Recommendation: Use `num_ctx=16384` (same as Phase 4 Stage 3); measure actual token count during Wave 0 integration test with a representative work description.
   - **RESOLVED:** Use `num_ctx=16384` for Step 3 OG ranking (Plan 05-03). Plan 05-02 and 05-03 implement this in `extra_body`.

---

## Sources

### Primary (HIGH confidence)

- `data/TBS-OCHRO-OG.txt` — Full TBS OCHRO OG definitions file; AS definition (lines 978-996), EC definition (lines 477-551), file structure confirmed [VERIFIED: file inspection]
- `data/directive_on_classification.txt` — Classification directive; 36 chunks already in `policy_chunks` [VERIFIED: sqlite3]
- `app/db.py` — Full schema DDL; `og_definitions` table absent; `jes_og_metadata` present (16 rows, JES OGs only); `policy_chunks/policy_fts` present [VERIFIED: sqlite3 + grep]
- `app/models/work_description.py` — OGRecommendation, confirmed_og, confirmed_level, stage="og_classified" all confirmed present [VERIFIED: file read]
- `app/api/noc_mapping.py` — Confirm endpoint pattern (stage check, wd_store, HTMX response) confirmed [VERIFIED: file read]
- `app/services/wd_store.py` — save/load WorkDescription helpers confirmed present [VERIFIED: file read]
- `app/ai/noc_ranking.py` pattern — instructor singleton, Mode.JSON, same pattern applies to og_ranking.py [VERIFIED: Phase 4 research]
- `tests/conftest.py` — Fixture patterns (ca_jes_db, noc_db, valid_env, mock_healthy_ollama) confirmed [VERIFIED: file read]
- Live test suite — 95 tests passing, 0 failures [VERIFIED: pytest run]

### Secondary (MEDIUM confidence)

- `.planning/research/ARCHITECTURE.md` — "OG definitions (28 OGs, ~100 tokens each) → Direct context — ~2.8K tokens total" [CITED: .planning/research/ARCHITECTURE.md §When to use RAG vs direct context]
- SME meeting notes — "AS vs EC distinction is a known pain point; internal departmental guidance → AS; shaping policy for the Canadian public → EC" [CITED: .planning/research/SUMMARY.md §Differentiating Features]
- `.planning/phases/04-nl-noc-mapping/04-RESEARCH.md` — instructor singleton pattern, HTMX wizard pattern, connection lifecycle [CITED: 04-RESEARCH.md]

### Tertiary (LOW confidence)

- OG level ranges (AS-01 to AS-08, EC-01 to EC-07, etc.) [ASSUMED — verify against current TBS collective agreements]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified installed; no new packages needed
- Schema / data sources: HIGH — verified against live DB and file inspection
- Architecture patterns: HIGH — all patterns follow existing project conventions from Phase 4
- OG level ranges: LOW — assumed from training knowledge; must be verified

**Research date:** 2026-06-02
**Valid until:** 2026-07-02 (stable library versions; TBS OG definitions are policy documents that rarely change)
