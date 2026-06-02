# Phase 6: JD Generation — Research

**Researched:** 2026-06-02
**Domain:** FastAPI + HTMX + SQLite + instructor + DashScope qwen3.7-max — verbatim NOC duty selection, ProvenanceTag, orphan statement check
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| JD-01 | Draft key duties by selecting verbatim NOC profile statements from the DB — LLM ranks and selects, never generates free-form text | `noc_elements` has 6,119 "Main duties" rows across 516 unit groups; each row has `element_text` (verbatim) + `source_hash`; LLM receives the full candidate list and returns row IDs — text is then read back from DB verbatim |
| JD-02 | Every duty carries a ProvenanceTag: source_type, NOC code, section name, statement text, source document version hash | `ProvenanceTag` model already defined in `app/models/work_description.py`; `DraftDuty` already carries `provenance: ProvenanceTag`; `source_documents` table has `version_label` and `content_hash` for NOC source; `noc_elements.source_hash` links to row's origin |
| JD-03 | Advisor-added content tagged "advisor-added / not from authoritative source" in data model and visually distinguished in UI | `DraftDuty.provenance.source_type = "ADVISOR"` already defined; `advisor_additions: list[DraftDuty]` field already on `WorkDescription`; CSS class `.duty-advisor-tag` needs to be added in Phase 6 |
| JD-04 | After duty confirmation, run orphan statement check — each duty scanned against functional authority rules; each flag cites document and article; clean result returns empty list, not error | No orphan check infrastructure exists yet; `og_definitions` inclusions/exclusions text is the primary source for functional authority rules; need new `functional_authority_rules` table OR runtime derivation from `og_definitions` |

</phase_requirements>

---

## Summary

Phase 6 sits between `stage="og_classified"` (Phase 5) and `stage="jd_drafted"`. The core design constraint for JD-01 is non-negotiable: the LLM must select from pre-indexed NOC records by row identity, never generate duty text. This means the pipeline must (a) retrieve candidate `noc_elements` rows for the confirmed NOC code, (b) pass the verbatim `element_text` values to the LLM with their row IDs, and (c) reconstruct the final duty list from the database using those IDs — never from the LLM's echo of the text. The LLM is a ranking/selection oracle, not a text generator.

The `DraftDuty` and `ProvenanceTag` models already exist and are correctly shaped for JD-02. The `WorkDescription` model already has `draft_duties: list[DraftDuty]`, `advisor_additions: list[DraftDuty]`, and `stage: "jd_drafted"` as valid values. No model migration is needed. The `noc_elements` table has 6,119 "Main duties" rows; the `source_documents` table has version hashes for the NOC CSVs. ProvenanceTags can be constructed at the point of selection.

The orphan statement check (JD-04) is the most novel piece. There is no existing `functional_authority_rules` table or orphan check infrastructure. The practical approach is to derive functional authority rules at runtime from `og_definitions` inclusions/exclusions text — the PE definition already contains language about what is "reserved" to the HM/PE group. The LLM is given the confirmed OG's exclusions text and checks each drafted duty against it. This is a classification problem (does this duty violate the exclusion for this OG?) — well-suited to instructor with a structured `OrphanFlag` output type. An empty `flags` list is the success path (not an error), matching JD-04's requirement.

**Primary recommendation:** Four plans — (1) Wave 0 test stubs + schema additions + skipped-gate activation, (2) `app/ai/jd_ranking.py` Pydantic models + instructor singleton, (3) `app/services/jd_service.py` pipeline + `app/api/jd_generation.py` router, (4) HTMX wizard step `templates/wizard/step_jd.html` + partials + CSS layer 9 + full suite green.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| NOC duty retrieval (for confirmed NOC) | Database / Storage | API / Backend | `noc_elements WHERE noc_code=? AND element_type='Main duties'` returns all verbatim duty statements; no LLM needed for retrieval |
| Duty ranking/selection (which duties fit this OG + work description) | Ollama/Cloud service | API / Backend | LLM receives full candidate duty list + confirmed OG context; returns selected row IDs ranked by relevance; instructor validates structure |
| ProvenanceTag construction | API / Backend | Database | After LLM selects row IDs, server reads `noc_elements.element_text` and `noc_elements.source_hash` from DB to build ProvenanceTag; LLM's echo of text is ignored |
| Verbatim fidelity guardrail | API / Backend | — | After LLM returns selected IDs, server re-reads each row from DB; the final duty text comes from the DB row, not from the LLM's response |
| Advisor duty addition | Browser / Client | Frontend Server (SSR) | HTMX form; advisor types new duty; POST sets `source_type="ADVISOR"` on ProvenanceTag; no LLM involved |
| Orphan statement check | Ollama/Cloud service | API / Backend | LLM sees each drafted duty + OG exclusion/inclusion rules from `og_definitions`; returns list of `OrphanFlag` objects citing violated rule; empty list = clean |
| WD persistence after duty confirmation | API / Backend | Database | Same `wd_store.save_work_description()` pattern as Phases 4/5; called at two points: after generate-duties and after confirm-duties |
| Stage gate (requires `og_classified`) | API / Backend | Database | `POST /api/jd/generate-duties` and `POST /api/jd/check-orphan-statements` both check `wd.stage == "og_classified"` before proceeding |
| Duty list display + advisor add | Frontend Server (SSR) | Browser / Client | HTMX partial swap; duty cards with provenance tooltip; Alpine.js for inline add-duty form toggle |

---

## Standard Stack

### Core (all already installed — no pip install needed)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| instructor | 1.15.1 | Structured LLM output + retry for duty ranking and orphan check | [VERIFIED: pip3 show] |
| openai (Python SDK) | 2.37.0 | AsyncOpenAI pointing at DashScope qwen3.7-max via cloud_api_key | [VERIFIED: pip3 show] |
| FastAPI | 0.128.8 | APIRouter for JD generation endpoints | [VERIFIED: pip3 show] |
| Jinja2 | 3.1.6 | HTMX partial template rendering | [VERIFIED: pip3 show] |
| Pydantic | 2.12.5 | DutyRankingResult / OrphanCheckResult validation | [VERIFIED: pip3 show] |
| sqlite-vec | 0.1.9 | Required by get_connection() — no new vec queries in Phase 6 | [VERIFIED: pip3 show] |
| pytest-asyncio | 1.3.0 | asyncio_mode=auto already set | [VERIFIED: pyproject.toml] |
| httpx | 0.28.1 | TestClient for FastAPI integration tests | [VERIFIED: pip3 show] |

**No new packages required for Phase 6.**

---

## Architecture Patterns

### System Architecture Diagram

```
Advisor POSTs wd_id (POST /api/jd/generate-duties)
         |
         v
[FastAPI route — checks stage == "og_classified"]
         |
         v
[jd_service.generate_duties(wd_id, db_path)]
         |
         +--- Step 1: Load NOC duty candidates from DB ----------------+
         |    asyncio.to_thread(conn.execute,                          |
         |      SELECT id, element_text, source_hash                   |
         |      FROM noc_elements                                       |
         |      WHERE noc_code = ? AND element_type = 'Main duties'    |
         |    → list of (row_id, text, source_hash) tuples             |
         |    (typically 8-20 duty statements per NOC code)            |
         |                                                             |
         +--- Step 2: LLM selects relevant duty row IDs ---------------+
         |    await instructor_client (DashScope qwen3.7-max)          |
         |    Input: confirmed_noc, confirmed_og, work description,    |
         |           numbered list of verbatim duty statements         |
         |    Output: DutyRankingResult(selected_ids: list[int],       |
         |                             rationale: str)                 |
         |    max_retries=3, temperature=0.0                           |
         |                                                             |
         +--- Step 3: Reconstruct duty list from DB (NOT from LLM) ---+
              For each selected_id returned by LLM:
                - Look up row in noc_elements by id
                - If not found or wrong noc_code → drop (guardrail)
                - Build DraftDuty(text=row.element_text,
                                  provenance=ProvenanceTag(
                                    source_type="NOC",
                                    source_id=confirmed_noc,
                                    source_version="NOC 2021 v1.0",  ← from source_documents
                                    retrieved_date=date.today()
                                  ))
              Update WorkDescription.draft_duties
              Set WorkDescription.stage = "jd_drafted"
              Save WD via wd_store.save_work_description()
                    |
                    v
              Return HTMX partial (duty list cards)

---

Advisor POSTs wd_id (POST /api/jd/check-orphan-statements)
         |
         v
[FastAPI route — checks stage in ("jd_drafted", "og_classified")]
         |
         v
[jd_service.check_orphan_statements(wd_id, db_path)]
         |
         +--- Load WD draft_duties + advisor_additions from DB --------+
         |    Load og_definitions row for confirmed_og                 |
         |    → og exclusions text (the functional authority rules)    |
         |                                                             |
         +--- LLM orphan check (per duty) ----------------------------+
              await instructor_client for OrphanCheckResult
              Input: each duty text + OG exclusion/inclusion rules
              Output: OrphanCheckResult(
                flags: list[OrphanFlag],   ← empty = clean
              )
              Each OrphanFlag has:
                duty_text: str
                rule_violated: str         ← verbatim from og_definitions
                source_document: str       ← "TBS OCHRO OG Definitions"
                source_section: str        ← "EC — Exclusions"
              Return flags (empty list is a valid clean result)
```

### Recommended Project Structure

```
app/
├── ai/
│   └── jd_ranking.py         # instructor singleton + DutyRankingResult + OrphanCheckResult + OrphanFlag
├── services/
│   └── jd_service.py         # generate_duties() + check_orphan_statements() pipelines
├── api/
│   └── jd_generation.py      # FastAPI router: POST /api/jd/generate-duties, POST /api/jd/check-orphan-statements, POST /api/jd/add-advisor-duty, POST /api/jd/confirm-duties
templates/
├── partials/
│   ├── jd_duties.html        # HTMX partial: duty card list + add-duty form
│   ├── jd_orphan_results.html # HTMX partial: orphan flag list (empty = "All duties are consistent")
│   └── jd_confirmed.html     # HTMX partial: duty confirmation success state → "Continue to JES Scoring"
└── wizard/
    └── step_jd.html          # Full wizard step (extends base.html; loads after og_confirmed.html CTA)
tests/
├── test_jd_generation.py     # Integration: generate_duties() + FastAPI routes
└── test_jd_ranking.py        # Unit: Pydantic validators, verbatim guardrail, orphan flag logic
```

### Pattern 1: LLM as Selection Oracle (JD-01 Core Pattern)

The non-negotiable design: LLM returns row IDs, never raw text. Text comes from DB.

```python
# Source: JD-01 requirement + architecture non-negotiables [CITED: .planning/STATE.md]
class DutySelection(BaseModel):
    row_id: int = Field(description="ID from noc_elements table — must be from the provided list")
    rank: int = Field(ge=1, description="Rank 1 = most relevant to the confirmed OG and work description")
    rationale: str = Field(description="Brief reason this duty is relevant")

class DutyRankingResult(BaseModel):
    selections: list[DutySelection] = Field(
        min_length=1,
        max_length=15,
        description="Selected duty rows in relevance order — IDs must be from the provided candidate list"
    )
    selection_rationale: str = Field(description="Overall rationale for the selection set")

DUTY_SELECTION_SYSTEM_PROMPT = """
You are a Government of Canada HR classification specialist.
You are selecting which NOC duty statements best describe the work of a position in the {og_name} ({og_code}) group.

CRITICAL RULES:
- You may ONLY return row_id values from the numbered list provided — never invent IDs
- Select 5-12 duties that collectively describe the full scope of the position
- Rank by relevance to the confirmed OG and the work description (rank 1 = most relevant)
- Do NOT paraphrase or modify duty text — select by ID only
""".strip()
```

### Pattern 2: ProvenanceTag Construction from DB Row (JD-02 Pattern)

After LLM returns selected row IDs, fetch rows from DB to build ProvenanceTags:

```python
# Source: noc_elements schema [VERIFIED: app/db.py] + source_documents [VERIFIED: sqlite3]
# NOC source_hash: "50c3e31a90b0150cc5b8efd29ec020c2fd9ea5fc5b0a171ed65d3cd9a0abf32f" (elements CSV)
# NOC version_label: "NOC 2021 v1.0"

from datetime import date
from app.models.work_description import DraftDuty, ProvenanceTag

def build_duty_from_row(row, confirmed_noc: str, noc_version: str) -> DraftDuty:
    """
    Construct a DraftDuty from a noc_elements row.
    The text and source_hash come from the DB row — never from the LLM's response.
    """
    return DraftDuty(
        text=row["element_text"],          # verbatim from noc_elements.element_text
        provenance=ProvenanceTag(
            source_type="NOC",
            source_id=confirmed_noc,       # e.g. "21232"
            source_version=noc_version,    # e.g. "NOC 2021 v1.0" from source_documents
            retrieved_date=date.today(),
        ),
        advisor_modified=False,
    )
```

### Pattern 3: Advisor Duty Addition (JD-03 Pattern)

Advisor-added duties use `source_type="ADVISOR"` and go into `advisor_additions`, not `draft_duties`:

```python
# Source: WorkDescription model [VERIFIED: app/models/work_description.py]
# advisor_additions: list[DraftDuty] = Field(default_factory=list)
# source_type="ADVISOR" already defined in ProvenanceTag

from app.models.work_description import DraftDuty, ProvenanceTag

def build_advisor_duty(text: str) -> DraftDuty:
    return DraftDuty(
        text=text,
        provenance=ProvenanceTag(
            source_type="ADVISOR",
            source_id="advisor-input",
            source_version="advisor-added",
            retrieved_date=date.today(),
        ),
        advisor_modified=False,
    )
```

### Pattern 4: Orphan Statement Check (JD-04 Pattern)

The orphan check is a per-duty LLM classification call against OG exclusion rules. A single call with all duties and the OG exclusion text is more efficient than one call per duty:

```python
# Source: JD-04 requirement + og_definitions schema [VERIFIED: app/db.py + sqlite3]
class OrphanFlag(BaseModel):
    duty_text: str = Field(description="The duty statement that was flagged")
    rule_violated: str = Field(
        description="Verbatim text from og_definitions exclusions or inclusions that this duty violates"
    )
    source_document: str = Field(
        default="TBS OCHRO OG Definitions",
        description="Document containing the functional authority rule"
    )
    source_section: str = Field(
        description="Which section of the document: e.g., 'EC — Exclusions' or 'PE — Inclusions'"
    )
    severity: str = Field(
        description="'hard' if this duty is explicitly in another OG's inclusions; 'soft' if it merely conflicts with this OG's exclusions"
    )

class OrphanCheckResult(BaseModel):
    flags: list[OrphanFlag] = Field(
        default_factory=list,
        description="List of flagged duties. Empty list means all duties are consistent with the confirmed OG."
    )
    summary: str = Field(description="Brief summary of orphan check result")

ORPHAN_CHECK_SYSTEM_PROMPT = """
You are a Government of Canada HR classification specialist reviewing draft job duties for classification correctness.

You are checking whether any duties listed below fall outside the functional authority of the {og_name} ({og_code}) occupational group.

A duty is an "orphan statement" if:
1. It is explicitly listed in the Exclusions for {og_code}, OR
2. It belongs primarily to another OG's Inclusions

Functional authority rules for {og_code}:
--- EXCLUSIONS ---
{og_exclusions}

--- INCLUSIONS (for reference) ---
{og_inclusions}

For each flagged duty, cite the EXACT verbatim text from the rules above that it violates.
If NO duties violate these rules, return an empty flags list — this is a valid and expected result.
Do NOT flag duties just because they are uncommon; only flag genuine classification conflicts.
""".strip()
```

### Pattern 5: Stage Gate Enforcement

Both JD endpoints must check stage before proceeding. The skipped Phase 5 test must be activated:

```python
# Source: og_classification.py stage check pattern [VERIFIED: app/api/og_classification.py]
# Pattern to replicate in jd_generation.py:

@router.post("/api/jd/generate-duties")
async def generate_duties_route(
    request: Request,
    wd_id: str = Form(...),
) -> ...:
    wd = await asyncio.to_thread(lambda: load_work_description(conn, wd_id))
    if wd is None:
        raise HTTPException(status_code=404, ...)
    if wd.stage != "og_classified":
        raise HTTPException(
            status_code=422,
            detail=f"WorkDescription is in stage {wd.stage!r}, expected 'og_classified'",
        )
    # ... proceed with generation
```

The skipped test in `tests/test_og_classification.py`:
```python
class TestOGGate:
    def test_og_gate_enforced(self, og_db):
        """JD generation endpoint returns 422 without confirmed OG (CLASS-02 gate)."""
        pytest.skip("Phase 6 gate test — deferred to Phase 6 plans")
```
This must be activated in Wave 0 — the gate is now implemented in `app/api/jd_generation.py`. Remove the `pytest.skip()` and wire it to call `POST /api/jd/generate-duties` with a WD in `stage="noc_mapped"` and verify HTTP 422.

### Pattern 6: NOC Version Hash Lookup

ProvenanceTags need the NOC source document version hash, which lives in `source_documents`:

```python
# Source: [VERIFIED: sqlite3 query on app.db]
# SELECT source_name, version_label, content_hash FROM source_documents WHERE source_name LIKE '%noc%';
# Returns:
#   noc_2021_version_1.0_-_elements.csv | NOC 2021 v1.0 | 50c3e31a...

def get_noc_version_info(conn: sqlite3.Connection) -> tuple[str, str]:
    """Return (version_label, content_hash) for the NOC elements source document."""
    row = conn.execute(
        "SELECT version_label, content_hash FROM source_documents "
        "WHERE source_name LIKE '%elements%' LIMIT 1"
    ).fetchone()
    if row:
        return row["version_label"], row["content_hash"]
    return "NOC 2021 v1.0", ""  # fallback
```

### Pattern 7: og_confirmed.html CTA to JD Step

The current `og_confirmed.html` has a disabled placeholder button:
```html
<button type="button" class="button button--primary" disabled>Continue to JD Generation</button>
```
Phase 6 Plan 1 (Wave 0) must activate this button as an HTMX trigger pointing to the JD wizard step or POST endpoint. This follows the same pattern as Phase 5 activating the NOC confirm CTA to OG classification.

### Anti-Patterns to Avoid

- **LLM echoes duty text, server trusts the echo** — The LLM must return row IDs. The server re-reads element_text from the DB. If the LLM returns text instead of an ID, the guardrail must reject it, not use it as a duty.
- **One instructor call per duty for orphan check** — All drafted duties should be checked in a single LLM call. The full duty list fits in context easily (~2-5 KB for 15 duties). Per-duty calls multiply latency by 10-15x.
- **Using `element_type` other than 'Main duties'** — The `noc_elements` table has six element types (Additional information, All examples, Employment requirements, Exclusion(s), Illustrative example(s), Inclusion(s), Main duties). Only "Main duties" produces valid duty statements. Other types are context/metadata and must not appear as job duties.
- **Setting stage to "jd_drafted" before orphan check** — The stage should be set to `"jd_drafted"` after duty confirmation, not after duty generation. The advisor must review the generated list (and optionally run the orphan check) before confirming.
- **Orphan check returning 500 on clean result** — An empty `flags: []` is the correct clean response. The endpoint must return HTTP 200 with `{"flags": [], "summary": "No orphan statements detected"}` — not a 404 or error.
- **ProvenanceTag built from LLM response text** — The `source_hash` must come from `noc_elements.source_hash` (the hash of the source CSV row), not computed on the fly from the LLM's text output.
- **Opening instructor client per request** — Use module-level singleton, same pattern as `og_ranking.py`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured LLM output + retry | Custom JSON parsing | `instructor` (installed, same pattern as Phases 4/5) | Handles Pydantic validation retry; duty ranking + orphan check are exactly this problem |
| Row ID → DB text reconstruction | Trust LLM's echo of duty text | `noc_elements` DB lookup by row ID | JD-01 non-negotiable; DB is authoritative; LLM can hallucinate text even when selecting |
| Orphan check rule indexing | Build a custom DAOD/rule database | Runtime derivation from `og_definitions.exclusions` + `og_definitions.inclusions` already in DB | All functionally relevant exclusion rules are already in `og_definitions` from Phase 5 ingest; no new data source needed for v1 |
| Advisor content tracking | New "modifications" table | `WorkDescription.advisor_additions: list[DraftDuty]` already exists | Phase 1 model already has this field; `source_type="ADVISOR"` already defined in ProvenanceTag |
| WD persistence | New persistence layer | `wd_store.save_work_description()` (already exists) | Pattern established in Phase 4; don't duplicate |

**Key insight:** Phase 6 has more moving parts than Phase 5 (four endpoints vs two) but less novel infrastructure. The LLM selection oracle pattern is the core innovation; everything else reuses established Phase 4/5 patterns.

---

## Data Findings

### noc_elements Table — Main Duties Inventory [VERIFIED: sqlite3]

| Property | Value |
|----------|-------|
| Total "Main duties" rows | 6,119 |
| Unique NOC codes with duties | 516 |
| Average duties per NOC code | ~12 |
| Element text format | Imperative verb phrase ("Design...", "Analyze...", "Develop...") |
| source_hash per row | SHA-256 of source CSV; same hash for all rows from same ingest: `50c3e31a...` |

The typical NOC unit group has 8-20 main duty statements. The full candidate list for a single NOC code fits comfortably in a prompt (~500-2,000 tokens). No RAG needed — direct context injection.

### NOC Source Document Versioning [VERIFIED: sqlite3]

```
source_name:    noc_2021_version_1.0_-_elements.csv
version_label:  NOC 2021 v1.0
content_hash:   50c3e31a90b0150cc5b8efd29ec020c2fd9ea5fc5b0a171ed65d3cd9a0abf32f
```

ProvenanceTags built in Phase 6 must use `source_version="NOC 2021 v1.0"` and the `source_hash` from `noc_elements.source_hash` (which matches this document hash).

### og_definitions — Orphan Check Source [VERIFIED: sqlite3]

81 OG rows present, including all common DND groups (AS, EC, IT, PE, PM, CR). Each row has `inclusions` and `exclusions` columns. PE's exclusions text (about what is NOT in the PE group) is available and rich enough for the orphan check. CS is not in the DB (confirmed by sqlite3 query — only AS, CR, EC, IT, PE, PM were returned for the DND OGs). [VERIFIED: sqlite3]

Note: PE inclusions column returns NULL in the DB (`SELECT og_code, inclusions FROM og_definitions WHERE og_code='PE'` → empty). The inclusions text for PE is in the `definition` column (as "Definition Excerpt of full HM Definition"). The orphan check prompt must use the `definition` column text when `inclusions` is NULL for a given OG.

### noc_fts DDL Bug (Deferred from Phase 4) [VERIFIED: app/db.py]

The `noc_fts` table in `NOC_SCHEMA_DDL` is declared without `content=''`:
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS noc_fts USING fts5(
    noc_code, title, definition, element_type, element_text,
    tokenize='porter ascii'
);
```
This is correct for Phase 6 — the ingest script (`scripts/ingest_noc.py`) already worksaround the earlier `content=''` confusion by recreating the table without it. The FTS table is populated directly with data. This bug does NOT affect Phase 6 because Phase 6 does not use `noc_fts` — it queries `noc_elements` directly by `noc_code`. **The noc_fts DDL fix remains deferred.**

### WorkDescription Model — Phase 6 Fields [VERIFIED: app/models/work_description.py]

All required fields already exist:
- `draft_duties: list[DraftDuty]` — receives selected verbatim NOC statements
- `advisor_additions: list[DraftDuty]` — receives advisor-entered duties with `source_type="ADVISOR"`
- `stage: Literal[..., "jd_drafted", ...]` — "jd_drafted" is a valid stage value
- `DraftDuty.provenance: ProvenanceTag` — carries all source citation fields
- `ProvenanceTag.source_type: "NOC"` and `"ADVISOR"` — both already defined

No schema migration needed.

---

## Common Pitfalls

### Pitfall 1: LLM Returns Text Instead of Row IDs

**What goes wrong:** The LLM interprets "select duties" as "write duty text" and returns paraphrased or invented text instead of integer row IDs. Fails JD-01 immediately.

**Why it happens:** The prompt structure is ambiguous — the LLM sees both the duty text and the row IDs but may not understand it must return IDs.

**How to avoid:** The Pydantic model `DutyRankingResult.selections: list[DutySelection]` where `DutySelection.row_id: int` enforces integer output via instructor. The prompt must explicitly number each duty as `[42] Analyze...` so the LLM associates IDs with text. Post-selection guardrail: verify each returned `row_id` exists in the pre-loaded candidate map; drop any ID not in the candidate set.

**Warning signs:** `DutySelection.row_id` fails Pydantic int validation; instructor retries 3 times; ValueError on candidate lookup.

### Pitfall 2: Orphan Check Returns 500 on Empty Flag List

**What goes wrong:** Route handler treats `flags: []` as an error path and either raises HTTP 500 or returns a confusing response. JD-04 explicitly requires that a clean result returns an empty flag list, not an error.

**Why it happens:** Developer confuses "no flags" with "check failed" and adds error handling that treats empty as a failure.

**How to avoid:** The `OrphanCheckResult` model has `flags: list[OrphanFlag] = Field(default_factory=list)`. The route handler must return HTTP 200 with the `OrphanCheckResult` regardless of whether `flags` is empty. Template must render "No issues found — all duties are consistent with {og_code}" when `flags` is empty.

**Warning signs:** `test_orphan_check_clean_returns_empty_list` fails with HTTP 500 or error response.

### Pitfall 3: PE Inclusions NULL in DB

**What goes wrong:** The orphan check prompt injects `og_inclusions = ""` for PE (and other OGs where `inclusions` is NULL). The LLM has no inclusion rules to check against and cannot distinguish PE duties from PE exclusions.

**Why it happens:** The Phase 5 ingest parser correctly handled OGs where the inclusions section doesn't exist in `TBS-OCHRO-OG.txt`. For PE, the inclusions are embedded in the `definition` column (as a "Definition Excerpt of full HM Definition").

**How to avoid:** In `jd_service.check_orphan_statements()`, when loading OG definition for orphan check, use `definition` as fallback when `inclusions IS NULL`:
```python
og_inclusions = row["inclusions"] or row["definition"] or ""
```

**Warning signs:** Orphan check for PE-classified positions never flags any PE-exclusive duties as orphans.

### Pitfall 4: Stage Set Too Early (Before Advisor Confirms)

**What goes wrong:** `stage="jd_drafted"` is set immediately after duty generation before the advisor confirms the list. A browser refresh or navigation away loses the generated duties.

**Why it happens:** Developer mirrors the NOC mapping pattern where stage is set at generation time. But JD generation has a confirmation step.

**How to avoid:** Introduce a transient stage `"jd_pending_confirmation"` OR set stage only at `POST /api/jd/confirm-duties`. Given the existing stage Literal, the simpler approach is to persist duties to `draft_duties` immediately (without stage change) and only set `stage="jd_drafted"` when the advisor explicitly confirms the list.

The current stage Literal does not include `"jd_pending_confirmation"`. Two options:
1. Add a new stage value (requires model change) — [ASSUMED: avoid model changes]
2. Save duties to `draft_duties` with `stage` still at `"og_classified"` after generation; set `stage="jd_drafted"` only at `/api/jd/confirm-duties`

**Recommendation:** Option 2 — no model change needed. The route for `POST /api/jd/check-orphan-statements` must accept both `"og_classified"` and `"jd_drafted"` stages (orphan check can run at any time after duties are drafted).

### Pitfall 5: advisor_additions Overwritten at Re-generate

**What goes wrong:** Advisor adds custom duties, then clicks "Regenerate". The new `generate_duties()` call replaces `draft_duties` but also clears `advisor_additions`. Advisor loses their custom entries.

**Why it happens:** `generate_duties()` replaces the full `WorkDescription` without preserving `advisor_additions`.

**How to avoid:** In `jd_service.generate_duties()`, load the current WD, update only `draft_duties`, and explicitly carry forward the existing `advisor_additions` unchanged.

### Pitfall 6: og_confirmed.html CTA Still Disabled

**What goes wrong:** The `og_confirmed.html` partial has `<button ... disabled>Continue to JD Generation</button>`. Phase 6 Wave 0 must activate this button with a proper HTMX trigger, or the advisor has no way to reach the JD step from the UI.

**Why it happens:** Phase 5 intentionally left this as a disabled placeholder pending Phase 6 implementation.

**How to avoid:** Wave 0 Task 1 — update `templates/partials/og_confirmed.html` to replace the disabled button with an active HTMX trigger pointing to `GET /wizard/jd?wd_id={{ wd_id }}` or an HTMX navigation pattern.

---

## Code Examples

### Duty Candidate Query

```python
# Source: noc_elements schema [VERIFIED: app/db.py] + sqlite3 inspection
rows = await asyncio.to_thread(
    lambda: conn.execute(
        "SELECT id, element_text, source_hash FROM noc_elements "
        "WHERE noc_code = ? AND element_type = 'Main duties' "
        "ORDER BY id",
        (confirmed_noc,)
    ).fetchall()
)
# Build numbered candidate list for LLM prompt:
numbered = "\n".join(f"[{row['id']}] {row['element_text']}" for row in rows)
```

### instructor Client Singleton (jd_ranking.py)

```python
# Source: app/ai/og_ranking.py singleton pattern [VERIFIED: live codebase]
import instructor
from openai import AsyncOpenAI
from app.config import settings

if settings.cloud_api_key:
    _openai_client = AsyncOpenAI(
        base_url=settings.cloud_base_url,
        api_key=settings.cloud_api_key,
    )
else:
    _openai_client = AsyncOpenAI(
        base_url=settings.ollama_base_url.rstrip("/") + "/v1",
        api_key="ollama",
    )

jd_instructor_client = instructor.from_openai(_openai_client, mode=instructor.Mode.JSON)
```

### LLM Duty Selection Call

```python
# Source: og_classifier.py LLM call pattern [VERIFIED: live codebase]
result: DutyRankingResult = await jd_instructor_client.chat.completions.create(
    model=settings.generation_model,
    messages=[
        {"role": "system", "content": DUTY_SELECTION_SYSTEM_PROMPT.format(
            og_name=og_name, og_code=og_code
        )},
        {"role": "user", "content": user_prompt},
    ],
    response_model=DutyRankingResult,
    max_retries=3,
    max_tokens=2048,
    temperature=0.0,
    **({"extra_body": {"options": {"num_ctx": 8192}}} if not settings.cloud_api_key else {}),
)
```

### Stage Gate + WD Load Pattern

```python
# Source: og_classification.py route pattern [VERIFIED: live codebase]
conn = await asyncio.to_thread(lambda: get_connection(settings.db_path))
try:
    wd = await asyncio.to_thread(lambda: load_work_description(conn, wd_id))
    if wd is None:
        raise HTTPException(status_code=404, detail=f"WorkDescription {wd_id!r} not found")
    if wd.stage != "og_classified":
        raise HTTPException(
            status_code=422,
            detail=f"WorkDescription is in stage {wd.stage!r}, expected 'og_classified'",
        )
    # ... generate duties ...
finally:
    await asyncio.to_thread(conn.close)
```

### Activated Phase 6 Gate Test (from test_og_classification.py)

```python
# Replace the pytest.skip() stub with real implementation in Wave 0:
class TestOGGate:
    def test_og_gate_enforced(self, og_db):
        """JD generation endpoint returns 422 without confirmed OG (CLASS-02 gate)."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        # Create a WD in noc_mapped stage (not og_classified)
        # POST to /api/jd/generate-duties with that wd_id
        # Assert HTTP 422
        ...  # full implementation in Wave 0 plan
```

---

## Runtime State Inventory

> Phase 6 is not a rename/refactor phase. This section is not applicable.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| DashScope cloud API | All LLM calls (qwen3.7-max) | Confirmed (CLOUD_API_KEY set in .env) | qwen3.7-max | Local gemma4:31b via Ollama if cloud fails |
| Ollama service | Fallback LLM + health check | Confirmed running | — | Cloud primary |
| nomic-embed-text | Not needed in Phase 6 | N/A | — | — |
| sqlite-vec | Required by get_connection() | Confirmed 0.1.9 | 0.1.9 | None — installed |
| instructor | All LLM calls | Confirmed 1.15.1 | 1.15.1 | None — installed |
| noc_elements (Main duties) | Duty candidate retrieval | Confirmed — 6,119 rows | — | None — must be populated |
| og_definitions | Orphan check rules | Confirmed — 81 rows including PE, EC, AS | — | None — must be populated |

**Missing dependencies with no fallback:** None — all dependencies available.

**Note on CLOUD_API_KEY:** The `.env` file has `CLOUD_MODEL=qwen3.7-max` and `CLOUD_BASE_URL` set but `CLOUD_API_KEY` is not visible in the env dump (intentionally excluded from inspection). Confirm it is set before running Phase 6 integration tests that make real LLM calls. [ASSUMED: CLOUD_API_KEY is set based on STATE.md confirming qwen3.7-max is the Stage 3 LLM and Phase 4/5 already use it]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| asyncio_mode | `auto` (already set) |
| Quick run command | `pytest tests/test_jd_ranking.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| JD-01 | `generate_duties()` returns duties where every text matches a noc_elements.element_text row (no invented text) | integration | `pytest tests/test_jd_generation.py::test_generate_duties_all_verbatim -x` | Wave 0 |
| JD-01 | Guardrail drops a DutySelection whose row_id is not in the candidate set | unit | `pytest tests/test_jd_ranking.py::test_guardrail_drops_invalid_row_id -x` | Wave 0 |
| JD-01 | `/api/jd/generate-duties` returns 422 if stage != "og_classified" | integration | `pytest tests/test_jd_generation.py::test_generate_duties_stage_gate -x` | Wave 0 (activates skipped Phase 5 test too) |
| JD-02 | Each DraftDuty.provenance has source_type="NOC", source_id=noc_code, source_version="NOC 2021 v1.0" | unit | `pytest tests/test_jd_ranking.py::test_provenance_tag_fields -x` | Wave 0 |
| JD-03 | Advisor-added duty has source_type="ADVISOR" and appears in advisor_additions, not draft_duties | integration | `pytest tests/test_jd_generation.py::test_advisor_duty_tagged_correctly -x` | Wave 0 |
| JD-03 | Advisor-added duty is preserved across re-generate call | integration | `pytest tests/test_jd_generation.py::test_advisor_duty_preserved_on_regenerate -x` | Wave 0 |
| JD-04 | `/api/jd/check-orphan-statements` with clean duties returns HTTP 200 with empty flags list | integration | `pytest tests/test_jd_generation.py::test_orphan_check_clean_returns_empty_list -x` | Wave 0 |
| JD-04 | Each OrphanFlag cites rule_violated, source_document, and source_section | unit | `pytest tests/test_jd_ranking.py::test_orphan_flag_cites_source -x` | Wave 0 |
| JD-04 | WorkDescription stage is "jd_drafted" after confirm-duties | integration | `pytest tests/test_jd_generation.py::test_confirm_duties_sets_stage -x` | Wave 0 |
| JD-01+02 | ProvenanceTags intact after WD round-trip through SQLite | integration | `pytest tests/test_jd_generation.py::test_wd_round_trip_provenance -x` | Wave 0 |
| CLASS-02 gate | (Activated from Phase 5 skip) JD endpoint returns 422 without og_classified stage | integration | `pytest tests/test_og_classification.py::TestOGGate::test_og_gate_enforced -x` | EXISTS (skipped) |

### Sampling Rate

- **Per task commit:** `pytest tests/test_jd_ranking.py -x` (fast unit tests, < 5 s, no LLM needed)
- **Per wave merge:** `pytest tests/test_jd_generation.py tests/test_jd_ranking.py -x`
- **Phase gate:** `pytest tests/ -x` full suite green (currently 114 passing, 1 skipped → target 130+ passing, 0 skipped)

### Wave 0 Gaps

- [ ] `tests/test_jd_ranking.py` — unit tests for DutyRankingResult, DutySelection, OrphanFlag, OrphanCheckResult Pydantic models; guardrail logic; PE inclusions fallback
- [ ] `tests/test_jd_generation.py` — integration tests for generate_duties() pipeline + FastAPI routes + advisor addition + orphan check endpoints
- [ ] `tests/conftest.py` update — add `jd_db` fixture (pre-populated noc_elements for NOC 21232 with 5 synthetic "Main duties" rows; og_definitions row for EC/IT; no Ollama required)
- [ ] `templates/partials/og_confirmed.html` update — activate disabled "Continue to JD Generation" button
- [ ] `tests/test_og_classification.py::TestOGGate::test_og_gate_enforced` — remove `pytest.skip()`, implement real gate test

*(No new DDL required — all necessary tables exist from prior phases)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Yes | `wd_id` validated as string (UUID format); `duty_text` from advisor truncated server-side (max 500 chars); `row_id` validated as integer in candidate set |
| V4 Access Control | No | Single-user local tool; no multi-user auth in v1 |
| V2 Authentication | No | Local tool; no auth in v1 |
| V6 Cryptography | No | SHA-256 source hash is provenance tracking, not a security feature |
| V3 Session Management | Partial | `wd_id` ties duty generation to a specific WorkDescription; server validates stage == "og_classified" before generating |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Row ID injection (LLM returns negative ID or ID from different NOC) | Tampering | Guardrail: verify each `row_id` is in the pre-loaded candidate dict (keyed on IDs from `WHERE noc_code=?` query); drop any ID not present |
| Advisor text injection (XSS via advisor_duty text field) | Tampering | Jinja2 auto-escaping; advisor_text treated as plain text, never rendered as raw HTML |
| Stage skip (call generate-duties with pre-og_classified WD) | Elevation of Privilege | `POST /api/jd/generate-duties` checks `wd.stage == "og_classified"`; rejects with HTTP 422 |
| LLM fabrication in orphan check rule_violated | Repudiation | Post-check guardrail: verify `rule_violated` text is a substring of `og_definitions.exclusions + inclusions + definition` for the confirmed OG before returning the flag |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LLM writes duty text directly | LLM selects from indexed records by ID | Phase 6 (new — architecture non-negotiable) | Enforces verbatim traceability; no hallucinated duties |
| Orphan check = manual classification advisor review | Programmatic orphan check against og_definitions rules | Phase 6 (new) | Systematic detection of classification boundary violations |
| No duty persistence between steps | WD persisted to SQLite after each state transition | Phase 4 pattern, extended to JD duties in Phase 6 | Advisor can navigate away and return |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | CLOUD_API_KEY is set in the environment at execution time | Environment Availability | [ASSUMED] If not set, all LLM calls fall back to local gemma4:31b which is too slow (6 min/request per STATE.md); Phase 6 integration tests requiring LLM calls will time out |
| A2 | PE `inclusions` column is NULL in `og_definitions` because the ingest parser correctly captured the definition excerpt as `definition` | Data Findings + Pitfall 3 | [VERIFIED: sqlite3 query on app.db] PE inclusions IS NULL — the fallback to `definition` column is needed |
| A3 | Functional authority rules sufficient for JD-04 orphan check can be derived from `og_definitions.exclusions` + `.inclusions` already in DB — no additional DAOD/policy documents needed for v1 | Pattern 4 | [ASSUMED] JD-04 says "pre-indexed set of functional authority rules" — the requirement cites "DAOD/functional authority" as an example. If the project team requires a separate DAOD table, this is a v1 blocker. Recommend confirming with Charles before Wave 2. |
| A4 | `og_confirmed.html` disabled CTA can be activated by changing button attributes only — no new route needed if JD wizard step uses GET /wizard/jd?wd_id=... | Pitfall 6 | [ASSUMED] The `app/main.py` will need a new `GET /wizard/jd` route added. This is standard and follows the Phase 4/5 wizard route pattern. |
| A5 | CS occupational group is not in og_definitions (only AS, CR, EC, IT, PE, PM confirmed) | Data Findings | [VERIFIED: sqlite3] CS is absent from og_definitions. If a CS-classified position is created, the orphan check will have no exclusion rules to check against. Return a warning rather than silently skipping. |

---

## Open Questions

1. **Does JD-04 require a separate `functional_authority_rules` table with DAOD citations, or is runtime derivation from `og_definitions` sufficient?**
   - What we know: JD-04 says "pre-indexed set of functional authority rules" and cites "DAOD/functional authority" as an example source
   - What's unclear: Whether the project stakeholder (DND HR advisors) needs actual DAOD article citations (e.g., "DAOD 5012-0, Section 4") or whether `og_definitions` exclusion/inclusion citations suffice for v1
   - Recommendation: Implement v1 with `og_definitions` as the rule source. Flag this as [ASSUMED: A3] for Charles to confirm. If DAOD table is needed, add a Wave 0 task to create the schema and ingest script.

2. **Should the orphan check run automatically after duty generation, or only on explicit advisor request?**
   - What we know: JD-04 says "after duties are drafted, the system runs an orphan statement check" — this reads as automatic
   - What's unclear: Whether it should block confirmation (hard gate) or just surface flags (soft advisory)
   - Recommendation: Soft advisory — the orphan check results are displayed and the advisor can confirm anyway. This matches the spirit of the tool (advisor-in-the-loop). The check fires automatically after generation but does not block confirmation.

---

## Sources

### Primary (HIGH confidence)

- `app/models/work_description.py` — DraftDuty, ProvenanceTag, WorkDescription, advisor_additions — all confirmed [VERIFIED: file read]
- `app/db.py` — noc_elements schema, og_definitions schema, source_documents schema — all confirmed [VERIFIED: file read]
- `app/ai/og_ranking.py` — instructor singleton pattern, DashScope client setup — confirmed [VERIFIED: file read]
- `app/services/og_classifier.py` — 3-step pipeline pattern, verbatim guardrail, asyncio.to_thread pattern — confirmed [VERIFIED: file read]
- `app/api/og_classification.py` — stage gate, HTMX dual-response, WD load/save pattern — confirmed [VERIFIED: file read]
- `app/services/wd_store.py` — save/load helpers confirmed [VERIFIED: file read]
- `templates/partials/og_confirmed.html` — disabled CTA button confirmed [VERIFIED: file read]
- `tests/test_og_classification.py` — skipped Phase 6 gate test confirmed at line 121 [VERIFIED: grep]
- Live DB — `noc_elements` 6,119 "Main duties" rows, 516 unique NOC codes; `og_definitions` 81 rows; `source_documents` NOC version info confirmed [VERIFIED: sqlite3]

### Secondary (MEDIUM confidence)

- `.planning/STATE.md` — Architecture non-negotiables; DashScope qwen3.7-max as Stage 3; stage gates confirmed [CITED: .planning/STATE.md §Architecture non-negotiables]
- `.planning/REQUIREMENTS.md` — JD-01 through JD-04 exact requirement text [CITED: .planning/REQUIREMENTS.md §JD Content Generation]
- Phase 5 RESEARCH.md — Pipeline structure, instructor patterns, HTMX wizard patterns [CITED: .planning/phases/05-og-classification/05-RESEARCH.md]

### Tertiary (LOW confidence)

- A3 claim that og_definitions exclusion text is sufficient for JD-04 orphan check without a dedicated DAOD table [ASSUMED — needs stakeholder confirmation]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified installed; no new packages needed
- Data sources: HIGH — verified against live DB; row counts, schema columns, source_hash values all confirmed
- Architecture patterns: HIGH — all patterns follow existing Phase 4/5 conventions; no novel infrastructure
- Orphan check approach: MEDIUM — functional approach verified; scope of rules (og_definitions vs DAOD table) awaits stakeholder confirmation

**Research date:** 2026-06-02
**Valid until:** 2026-07-02 (stable library versions; NOC data is static; og_definitions populated and stable)
