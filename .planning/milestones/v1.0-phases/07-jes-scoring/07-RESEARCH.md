# Phase 7: JES Scoring — Research

**Researched:** 2026-06-02
**Domain:** instructor-driven per-factor LLM scoring against JES database records
**Confidence:** HIGH

---

## Summary

Phase 7 implements a per-factor JES scoring pipeline that is a near-exact structural analog of the Phase 6 duty-generation pipeline. The key distinction is that instead of one LLM call over all duty candidates, Phase 7 makes **one LLM call per JES factor** — each call receives the full `factor_definition` and all `degree_descriptors` freshly queried from `jes_factors` for that `(og_code, factor_name)`. The LLM returns a structured `JESFactorScore` Pydantic object (already defined in `app/models/work_description.py` lines 72–82) validated by `instructor` with up to 3 retries.

The codebase provides all required plumbing: `JESFactorScore` model is finalized, `jes_factors` table is populated (EC has 10 factors, FB has 11, IT has 10, etc.), `source_documents` records JES version info per OG, `ProvenanceTag` supports `source_type="JES"`, and `WorkDescription.jes_scores` / `jes_total_points` fields exist. The phase adds only: an instructor client + Pydantic output model (`JESFactorRating`), a service function (`score_jes()`), a FastAPI router (`/api/jes/score`), and a wizard step template.

The per-factor loop introduces the main implementation complexity: the service must iterate the factor list, make async LLM calls, collect results, and handle per-factor failures gracefully (returning a descriptive error string for that factor rather than a silent null or raising).

**Primary recommendation:** Mirror `app/ai/jd_ranking.py` → `app/services/jd_service.py` → `app/api/jd_generation.py` in all structural decisions. New files: `app/ai/jes_scoring.py`, `app/services/jes_service.py`, `app/api/jes_scoring.py`. Stage gate: `stage == 'jd_drafted'`; stage transition: `'jes_scored'` after all factors processed.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| JES factor iteration + LLM calls | API / Backend | — | Per-factor async loop belongs in the service layer; no browser involvement |
| Pydantic output model + instructor retry | API / Backend | — | instructor wraps the OpenAI-compat client; lives at service layer |
| Factor data loading (jes_factors DB) | API / Backend | — | SQLite query by (og_code, factor_name) — synchronous call in asyncio.to_thread |
| ProvenanceTag construction per factor | API / Backend | — | Set at write time from jes_factors DB row fields (source_hash, og_code) |
| Stage gate enforcement (jd_drafted) | API / Backend | — | Checked in router and service, same pattern as Phase 6 |
| JES score persistence (WorkDescription) | Database / Storage | API / Backend | jes_scores list saved via wd_store.save_work_description |
| JES scoring UI (wizard step) | Browser / Client | Frontend (Jinja2) | HTMX form triggers POST, Jinja2 partial renders factor score cards |
| Factor score card display | Browser / Client | — | Rendered as HTMX partial swap; Alpine.js for any expand/collapse |

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| JES-01 | System generates a JES scoring sheet for the confirmed OG by making one configured local generation model call per JES factor — with the full factor descriptor and degree definitions injected fresh per call — returning a structured scoring object validated by Pydantic via `instructor` (max 3-attempt retry) | Full codebase patterns verified; jes_factors table populated; JESFactorScore model pre-defined; instructor retry pattern established in jd_ranking.py |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| instructor | 1.15.1 | Pydantic-validated structured output + retry | [VERIFIED: pip in venv] Already used for OG ranking and JD generation; project non-negotiable |
| openai (AsyncOpenAI) | (project-pinned) | OpenAI-compat client pointing to Ollama or DashScope | [VERIFIED: jd_ranking.py line 151–162] Established singleton pattern |
| pydantic | (project-pinned) | Output model validation | [VERIFIED: work_description.py] All models use Pydantic v2 |
| fastapi | (project-pinned) | Router + form handling | [VERIFIED: jd_generation.py] HTMX + JSON dual path |
| sqlite3 (stdlib) | — | JES factor data access | [VERIFIED: db.py] All DB access via get_connection() |
| asyncio.to_thread | stdlib | Sync DB calls wrapped for async service | [VERIFIED: jd_service.py lines 89, 107] Established pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Jinja2Templates | (fastapi dep) | HTMX partial rendering | Phase 7 wizard step + jes_scores partial |
| Alpine.js 3.x | CDN via base.html | Client-side expand/collapse for factor detail | If factor rationale display needs show/hide |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sequential per-factor async calls | asyncio.gather() fan-out | Fan-out risks Ollama OOM on ARM64 with large context windows; sequential is the established pattern here |
| One big call for all factors | Per-factor calls | Architecture non-negotiable: "one call per JES factor (no array-collapse)" per STATE.md |

---

## Architecture Patterns

### System Architecture Diagram

```
POST /api/jes/score (wd_id)
        |
        v
[jes_scoring.py router]
  stage gate: wd.stage == 'jd_drafted' → 422 if not
        |
        v
[jes_service.score_jes(wd_id, db_path)]
  1. load WorkDescription via wd_store.load_work_description()
  2. query jes_factors WHERE og_code = confirmed_og  → list[factor_rows]
  3. query source_documents WHERE source_name LIKE '%og_code%JES%'  → version_info
        |
        |  for each factor_row:
        v
[jes_scoring.py instructor call]
  system_prompt: JES scoring specialist + factor context
  user_prompt: factor_definition + degree_descriptors + all confirmed duties
  response_model: JESFactorRating  (degree: str, points: int, rationale: str)
  max_retries=3
        |
        |  on success: build JESFactorScore with ProvenanceTag(source_type="JES")
        |  on failure after 3 retries: JESFactorScore with error_message field
        v
[jes_service.score_jes() continued]
  4. collect all JESFactorScore objects → wd.jes_scores
  5. compute jes_total_points = sum(score.points for score in jes_scores if score.points)
  6. wd.stage = 'jes_scored'
  7. save_work_description(conn, updated_wd)
        |
        v
[jes_scoring.py router — response path]
  HX-Request header? → TemplateResponse("partials/jes_scores.html")
  else → JSON dict of factor scores
```

### Recommended Project Structure

```
app/
├── ai/
│   └── jes_scoring.py          # instructor singleton + Pydantic output models
├── api/
│   └── jes_scoring.py          # FastAPI router  POST /api/jes/score
├── services/
│   └── jes_service.py          # score_jes() pipeline function
templates/
├── partials/
│   └── jes_scores.html         # HTMX partial: factor score cards
└── wizard/
    └── step_jes.html           # extends base.html; CTA to trigger scoring
tests/
└── test_jes_scoring.py         # Wave 0 stubs → filled in phase
```

### Pattern 1: instructor client singleton (direct analog from jd_ranking.py)

**What:** Module-level AsyncOpenAI + instructor.from_openai singleton, constructed once at import time.
**When to use:** Every LLM call in the phase goes through this singleton.

```python
# Source: app/ai/jd_ranking.py lines 151–162 [VERIFIED]
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

jes_instructor_client = instructor.from_openai(_openai_client, mode=instructor.Mode.JSON)
```

### Pattern 2: per-factor async LLM call with instructor retry

**What:** One call per factor; max_retries=3; temperature=0.0; extra_body for local Ollama context window.
**When to use:** Inside a for-loop over factor rows in score_jes().

```python
# Source: app/services/jd_service.py lines 150–170 [VERIFIED] — adapted for per-factor
extra_kwargs: dict = {}
if not settings.cloud_api_key:
    extra_kwargs["extra_body"] = {"options": {"num_ctx": 8192}}

factor_rating: JESFactorRating = await jes_instructor_client.chat.completions.create(
    model=settings.generation_model,
    messages=[
        {"role": "system", "content": JES_SCORING_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt_for_factor},
    ],
    response_model=JESFactorRating,
    max_retries=3,
    max_tokens=1024,
    temperature=0.0,
    **extra_kwargs,
)
```

### Pattern 3: ProvenanceTag for JES source

**What:** Each `JESFactorScore` gets a `ProvenanceTag` with `source_type="JES"`, `source_id=f"{og_code}/{factor_name}"`, `source_version` from `source_documents` row.
**When to use:** After each successful factor call.

```python
# Derived from jd_service.py _build_duty_from_row pattern [VERIFIED]
ProvenanceTag(
    source_type="JES",
    source_id=f"{og_code}/{factor_name}",          # e.g. "EC/Decision making"
    source_version=jes_version_label,               # e.g. "JES v1.0"
    retrieved_date=date.today(),
)
```

### Pattern 4: per-factor failure — descriptive error, not silent null

**What:** If instructor raises after 3 retries, catch the exception and store an error representation rather than raising from the service.
**When to use:** Wrap the per-factor LLM call in try/except inside the loop.

```python
# [ASSUMED pattern — no direct analog; derived from JES-01 success criterion 3]
try:
    factor_rating = await jes_instructor_client.chat.completions.create(...)
    score = _build_jes_factor_score(factor_row, factor_rating, og_code, jes_version)
except Exception as exc:
    score = JESFactorScore(
        factor_name=factor_row["factor_name"],
        level=-1,           # sentinel: -1 means scoring failed
        points=None,
        rationale=f"Scoring failed after 3 retries: {exc}",
        provenance=ProvenanceTag(
            source_type="JES",
            source_id=f"{og_code}/{factor_row['factor_name']}",
            source_version=jes_version_label,
            retrieved_date=date.today(),
        ),
    )
```

**Note:** `JESFactorScore.level` is typed `int` (not `Optional[int]`), so a sentinel value like `-1` or a separate `error_message: Optional[str]` field needs a design decision. See Open Questions.

### Pattern 5: DB query for jes_factors by og_code

**What:** Load all factor rows for a confirmed OG code from `jes_factors` table.

```python
# Source: app/db.py schema + jd_service.py DB query pattern [VERIFIED]
factor_rows = await asyncio.to_thread(
    lambda: conn.execute(
        "SELECT id, factor_name, factor_definition, degree_descriptors, "
        "point_values, max_points, source_hash "
        "FROM jes_factors WHERE og_code = ? ORDER BY id",
        (confirmed_og,),
    ).fetchall()
)
```

**Important:** `degree_descriptors` is stored as JSON text — must `json.loads()` before injecting into prompt. Same for `point_values`.

### Pattern 6: JES version lookup

**What:** Query `source_documents` for the JES source_name matching the confirmed OG to get `version_label` and `content_hash` for `ProvenanceTag.source_version`.

```python
# Source: jd_ranking.py get_noc_version_info() pattern [VERIFIED] — adapted for JES
# source_name pattern: "EC Economics and Social Science Services - Job Evaluation Standard 2017.txt"
row = conn.execute(
    "SELECT version_label, content_hash FROM source_documents "
    "WHERE source_name LIKE ? LIMIT 1",
    (f"{og_code}%",),
).fetchone()
```

**Caveat:** The `source_name` column uses a human-readable filename like `"EC Economics and Social Science Services - Job Evaluation Standard 2017.txt"`. The LIKE pattern `f"{og_code}%"` is sufficient for the known OG codes (all are 2–3 character prefixes that uniquely match exactly one JES source). [VERIFIED: source_documents inspection on app.db]

### Anti-Patterns to Avoid

- **Injecting all factors in one LLM call:** Explicitly forbidden by architecture non-negotiable in STATE.md — "one configured local generation model call per JES factor (no array-collapse)."
- **Constructing jes_instructor_client inside the service function:** Creates a new httpx connection pool per request. Module-level singleton is mandatory (same rule as jd_ranking.py/og_ranking.py).
- **Parsing degree_descriptors from the LLM response:** The degree text must come from the DB row (`degree_descriptors` JSON array), not from LLM echoing. The LLM returns only the selected `degree` identifier (e.g. `"D3"`) and a `rationale`.
- **Setting stage='jes_scored' before all factors complete:** Stage should only advance after all factor calls (successful or errored) have been collected and saved.
- **Silent null on failure:** JES-01 criterion 3 explicitly requires a descriptive error for the factor, not a silent null.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured output retry | Custom JSON parsing loop | instructor `max_retries=3` | Local models return malformed JSON frequently; instructor handles repair automatically |
| Pydantic model validation | Manual type checks | Pydantic v2 model with Field constraints | Already the project standard; works with instructor directly |
| Async SQLite calls | Direct sqlite3 in coroutine | `asyncio.to_thread(lambda: conn.execute(...))` | sqlite3 is sync; blocking the event loop causes HTMX timeouts |
| Per-factor error handling | Raise from service | Catch per-factor, store error sentinel in score | Phase success criterion 3 requires per-factor error reporting |

**Key insight:** The instructor retry + Pydantic validation loop that took the prototype months to stabilize is already production-tested in this codebase. Copy it exactly — do not invent a new retry mechanism.

---

## Common Pitfalls

### Pitfall 1: `degree_descriptors` is JSON text, not a Python object
**What goes wrong:** Code treats `row["degree_descriptors"]` as a list and gets a string; `for d in row["degree_descriptors"]` iterates characters.
**Why it happens:** SQLite TEXT column stores JSON; `sqlite3.Row` does not auto-parse JSON.
**How to avoid:** Always `json.loads(row["degree_descriptors"])` before iterating.
**Warning signs:** `TypeError: string indices must be integers` in the service log.

### Pitfall 2: `JESFactorScore.level` is `int`, not `Optional[int]`
**What goes wrong:** On failure, setting `level=None` raises a Pydantic validation error.
**Why it happens:** The finalized Phase 1 model has `level: int` (non-optional). See work_description.py line 74.
**How to avoid:** Use a sentinel integer (e.g., `-1`) for failed factors, OR add an `Optional[str] error_message` field to `JESFactorScore`. If a field is added, a migration script is required (model is finalized, schema_version must bump). The simpler path is sentinel `-1` with a descriptive `rationale` string.
**Warning signs:** `ValidationError: level field required` or `int is not None`.

### Pitfall 3: No JES factors in DB for the confirmed OG
**What goes wrong:** `factor_rows` is empty; the loop produces zero scores; WD advances to `jes_scored` with empty `jes_scores`.
**Why it happens:** JES data was not ingested for all OGs; some OG codes (e.g., AS, CR, PM) do not have JES data in `data/`.
**How to avoid:** Check `len(factor_rows) == 0` after DB query and raise `ValueError` with a descriptive message before any LLM calls.
**Warning signs:** `jes_scores: []` and `jes_total_points: None` after scoring endpoint returns 200.

### Pitfall 4: prompt token overflow with all duties + full degree descriptors
**What goes wrong:** Long duty lists combined with verbose factor definitions exceed `num_ctx=8192` for local Ollama.
**Why it happens:** EC has up to 8 degrees per factor, each with verbose descriptive text; duty list can be 12+ entries.
**How to avoid:** Truncate duty list in the per-factor prompt to the top-N (e.g., 10) most relevant duties. Use the established pattern `work_description[:500]` for raw input, or combine duties with a character budget.
**Warning signs:** Ollama returns empty response or timeout; instructor retries exhaust.

### Pitfall 5: Stage gate too strict — confusing `jd_drafted` vs `og_classified`
**What goes wrong:** Service checks `stage == 'og_classified'` instead of `stage == 'jd_drafted'`, blocking the endpoint after Phase 6 confirm step.
**Why it happens:** Copy-paste from Phase 6 generate_duties() without updating stage name.
**How to avoid:** Phase 7 gate is `stage == 'jd_drafted'` (duties have been confirmed). See WorkDescription.stage Literal chain: `"jd_drafted"` → `"jes_scored"`.
**Warning signs:** `422: WorkDescription is in stage 'jd_drafted', expected 'og_classified'`.

### Pitfall 6: instructor client name collision
**What goes wrong:** `jes_instructor_client` imported before `settings` loaded causes AttributeError or circular import.
**Why it happens:** All three existing ai modules (og_ranking, jd_ranking) construct the client at module-level; if any module imports another, import order matters.
**How to avoid:** `jes_scoring.py` must import `settings` before constructing the client, identical to the existing modules. Do not import from other ai modules.
**Warning signs:** `AttributeError: 'Settings' object has no attribute 'cloud_api_key'` at import time.

---

## Code Examples

Verified patterns from official sources (project codebase):

### Load JES factors for an OG and build the per-factor prompt

```python
# Source: app/services/jd_service.py + app/db.py schema [VERIFIED]
import json
from datetime import date

async def _load_factors(conn, og_code: str) -> list:
    return await asyncio.to_thread(
        lambda: conn.execute(
            "SELECT id, factor_name, factor_definition, degree_descriptors, "
            "point_values, max_points, source_hash "
            "FROM jes_factors WHERE og_code = ? ORDER BY id",
            (og_code,),
        ).fetchall()
    )

def _build_factor_user_prompt(factor_row, duties: list[str], work_description: str) -> str:
    degrees = json.loads(factor_row["degree_descriptors"])
    degree_text = "\n".join(
        f"  {d['degree']} ({d.get('points', '?')} pts): {d['text']}"
        for d in degrees
    )
    duties_text = "\n".join(f"{i+1}. {d}" for i, d in enumerate(duties[:10]))
    return (
        f"Factor: {factor_row['factor_name']}\n"
        f"Definition: {factor_row['factor_definition'] or '(none)'}\n\n"
        f"Degree Definitions:\n{degree_text}\n\n"
        f"Position duties:\n{duties_text}\n\n"
        f"Work description: {work_description[:300]}\n\n"
        "Select the degree that best fits this position and provide a rationale."
    )
```

### JESFactorRating Pydantic output model (new, for app/ai/jes_scoring.py)

```python
# [ASSUMED pattern — no direct precedent; derived from JESFactorScore in work_description.py]
from pydantic import BaseModel, Field

class JESFactorRating(BaseModel):
    """Structured LLM output for a single JES factor rating."""
    degree: str = Field(
        description="Degree identifier — must be from the provided degree list, e.g. 'D1', 'D3'"
    )
    rationale: str = Field(
        description="Justification for the selected degree, citing the position's duties"
    )
```

**Note:** The LLM returns only `degree` (e.g., `"D3"`) and `rationale`. The service maps `degree` → `points` via `json.loads(row["point_values"])` — it does not ask the LLM to compute points. This prevents hallucinated point values.

### Fixture for test_jes_scoring.py (new jes_db fixture)

```python
# Source: conftest.py jd_db fixture pattern [VERIFIED] — adapted for JES
@pytest.fixture
def jes_db(tmp_path):
    """
    Temp SQLite DB with full schema + synthetic jes_factors rows for EC (3 factors)
    and a WorkDescription in stage='jd_drafted' with 3 draft duties.
    """
    from app.db import create_schema, get_connection
    db_path = str(tmp_path / "test_jes.db")
    con = get_connection(db_path)
    create_schema(con)

    # Insert 2 synthetic EC JES factors
    import json
    factors = [
        ("EC", "Decision making",
         "Measures latitude applied and impact of decision making.",
         json.dumps([
             {"degree": "D1", "text": "Issue-specific, impact on own work unit.", "points": 5},
             {"degree": "D2", "text": "Issue-specific, impact on components of project.", "points": 15},
             {"degree": "D3", "text": "Multiple issues, impact on branch or division.", "points": 35},
         ]),
         json.dumps({"D1": 5, "D2": 15, "D3": 35}),
         35, "fakehash_jes_v1"),
        ("EC", "Communication",
         "Measures the nature of communication activities.",
         json.dumps([
             {"degree": "D1", "text": "Provides factual information.", "points": 10},
             {"degree": "D2", "text": "Explains findings and recommendations.", "points": 30},
         ]),
         json.dumps({"D1": 10, "D2": 30}),
         30, "fakehash_jes_v1"),
    ]
    for f in factors:
        con.execute(
            "INSERT OR IGNORE INTO jes_factors "
            "(og_code, factor_name, factor_definition, degree_descriptors, "
            "point_values, max_points, source_hash) VALUES (?,?,?,?,?,?,?)",
            f,
        )

    # JES source_documents row
    con.execute(
        "INSERT OR IGNORE INTO source_documents(source_name, version_label, content_hash, ingested_at) "
        "VALUES (?, ?, ?, datetime('now'))",
        ("EC Economics and Social Science Services - Job Evaluation Standard 2017.txt",
         "JES v1.0", "fakehash_jes_v1"),
    )
    con.commit()
    yield db_path
    con.close()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| One LLM call for all JES factors | One call per factor | Architecture decision (Phase 1) | Prevents context overflow; allows per-factor retry isolation |
| Free-form JES rationale generation | Structured `JESFactorRating` via instructor | Phase 7 | Pydantic validation ensures degree + rationale always present |

**Not applicable / no changes:**
- `instructor` mode: `Mode.JSON` used throughout project; no change needed for Phase 7.
- `AsyncOpenAI` client targeting Ollama `/v1`: unchanged from Phase 5/6.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Sentinel `-1` is the correct approach for failed JESFactorScore.level (vs. adding Optional[str] error_message field) | Code Examples / Pitfall 2 | If sentinel is used but planner adds error_message field, migration script needed (schema_version bump) |
| A2 | `source_name LIKE f"{og_code}%"` is sufficient to uniquely match the JES source document for all OG codes | Pattern 6 | If two JES source files start with the same OG prefix, the LIKE would return the wrong version; verification: inspect source_documents for overlapping prefixes |
| A3 | Sequential (not fan-out) per-factor LLM calls is the intended execution pattern | Architecture Patterns | If parallelism is desired, asyncio.gather() with semaphore is alternative; but sequential matches existing jd_service.py style |

**A2 verification available:** `SELECT source_name FROM source_documents WHERE source_name LIKE 'EC%'` should return exactly one row — verified during research (`"EC Economics and Social Science Services - Job Evaluation Standard 2017.txt"`). [VERIFIED]

---

## Open Questions

1. **How should a failed factor (after 3 instructor retries) be represented?**
   - What we know: `JESFactorScore.level: int` (non-optional, Phase 1 finalized model). `JESFactorScore.points: Optional[int]`.
   - What's unclear: Use sentinel `level=-1` and descriptive `rationale`? Or add `Optional[str] error_message` field (requires schema_version bump and migration)?
   - Recommendation: Use `level=-1` sentinel to avoid model migration. Document in PLAN.md that `-1` means scoring failed; UI renders a warning card instead of a degree badge.

2. **Should JES scoring be triggered automatically after duty confirmation, or explicitly by the advisor?**
   - What we know: Phase 6 `confirm-duties` sets `stage='jd_drafted'` and returns a confirmed partial. Phase 7 adds a new `POST /api/jes/score` endpoint.
   - What's unclear: Does the JES step appear in the same wizard page as JD (step_jd.html) or its own page (step_jes.html)?
   - Recommendation: Separate `wizard/step_jes.html` page, linked from `jd_confirmed.html` partial. Keeps pages focused and matches the OG → JD → JES progression.

3. **Which OG codes have no JES data in the DB?**
   - What we know: app.db has factors for CT, EC, ED, EX, FB, FS, IT, LC, LP, MT, NU, PO, PS, SW, WP (15 OGs). Missing from the DB but potentially confirmed: AS, CR, PM, PE, CS, IS, GT, RE, SH, etc.
   - What's unclear: If an advisor confirms OG "AS", there are no jes_factors rows — the service must return a clear error, not silently succeed with 0 scores.
   - Recommendation: Add explicit check after loading factor_rows — raise ValueError with `"No JES factors found for OG {confirmed_og} — check jes_factors table"`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| instructor | LLM structured output | ✓ | 1.15.1 | — |
| openai (AsyncOpenAI) | instructor client | ✓ | project-pinned | — |
| pydantic | Output model validation | ✓ | project-pinned v2 | — |
| SQLite jes_factors table populated | factor data load | ✓ | 15 OGs in app.db | — |
| Ollama / DashScope API | LLM calls | ✓ | settings.generation_model | — |
| pytest 9.0.2 | tests | ✓ | 9.0.2 | — |

**Missing dependencies with no fallback:** None identified.

**Note on OG coverage:** JES data is absent from `jes_factors` for OGs commonly used in DND (AS, PM, CR, PE). The service must handle the "no factors" case gracefully. This is a data gap, not a code dependency issue.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pytest.ini (project root) |
| Quick run command | `pytest tests/test_jes_scoring.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| JES-01 | POST /api/jes/score stage gate: 422 if stage != 'jd_drafted' | unit | `pytest tests/test_jes_scoring.py::TestJESScoringStageGate -x` | ❌ Wave 0 |
| JES-01 | POST /api/jes/score returns 404 for unknown wd_id | unit | `pytest tests/test_jes_scoring.py::TestJESScoringStageGate -x` | ❌ Wave 0 |
| JES-01 | Each JESFactorScore has factor_name, level, rationale, provenance | unit | `pytest tests/test_jes_scoring.py::TestJESFactorScoreSchema -x` | ❌ Wave 0 |
| JES-01 | JESFactorRating Pydantic model validates degree + rationale fields | unit | `pytest tests/test_jes_scoring.py::TestJESFactorRatingSchema -x` | ❌ Wave 0 |
| JES-01 | ProvenanceTag built from jes_factors row has source_type='JES' | unit | `pytest tests/test_jes_scoring.py::TestProvenanceTagJES -x` | ❌ Wave 0 |
| JES-01 | Scoring with 0 factors in DB raises ValueError (no factors for OG) | unit | `pytest tests/test_jes_scoring.py::TestNoFactors -x` | ❌ Wave 0 |
| JES-01 | WD stage transitions to 'jes_scored' after successful scoring | integration | `pytest tests/test_jes_scoring.py::TestStageTransition -x` | ❌ Wave 0 |
| JES-01 | jes_instructor_client singleton exists in app.ai.jes_scoring | unit | `pytest tests/test_jes_scoring.py::TestJESInstructorClient -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_jes_scoring.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green (141 existing + new Phase 7 tests) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_jes_scoring.py` — all 8 test stubs above
- [ ] `tests/conftest.py` — add `jes_db` fixture (synthetic EC factors + jd_drafted WD)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user local app — no auth |
| V3 Session Management | no | Session via wd_id only; no user sessions |
| V4 Access Control | no | No multi-tenant, no role checks |
| V5 Input Validation | yes | Pydantic v2 on all LLM output; wd_id validated by UUID parse |
| V6 Cryptography | no | No crypto operations in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM output hallucination (fabricated degree) | Tampering | instructor Pydantic validation; degree must match regex/enum if constrained |
| Invalid wd_id path traversal | Tampering | db_path validated by Settings.db_path_must_be_under_project_root |
| Prompt injection via raw_input or duty text | Tampering | Inputs are truncated (raw_input[:500], duties[:10]) before LLM injection; no user-controlled system prompt content |

---

## Sources

### Primary (HIGH confidence)

- `app/ai/jd_ranking.py` — instructor client singleton + Pydantic output pattern [VERIFIED in session]
- `app/ai/og_ranking.py` — second instructor singleton example [VERIFIED in session]
- `app/services/jd_service.py` — per-call async LLM + asyncio.to_thread DB pattern [VERIFIED in session]
- `app/api/jd_generation.py` — HTMX + JSON dual response router pattern [VERIFIED in session]
- `app/services/wd_store.py` — save/load WorkDescription pattern [VERIFIED in session]
- `app/models/work_description.py` — JESFactorScore (lines 72–82), WorkDescription.jes_scores (lines 129–131) [VERIFIED in session]
- `app/db.py` — jes_factors schema: og_code, factor_name, factor_definition, degree_descriptors (JSON), point_values (JSON), max_points, source_hash [VERIFIED in session]
- `tests/conftest.py` — fixture patterns (jd_db) for creating test WD records [VERIFIED in session]
- `tests/test_jd_generation.py` — test structure for Phase 6 analog [VERIFIED in session]
- `app/static/css/main.css` — CSS layer structure (layers 1–8 established) [VERIFIED in session]
- Live `app.db` inspection — jes_factors populated for 15 OGs; EC has 10 factors including Decision making (D1–D8), Communication, etc. [VERIFIED in session]
- Live `app.db` source_documents — JES version labels confirmed as "JES v1.0" per OG file [VERIFIED in session]

### Secondary (MEDIUM confidence)

- instructor 1.15.1 changelog — Mode.JSON confirmed as the correct mode for Ollama OpenAI-compat endpoint [VERIFIED: import in venv]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are installed and used identically in Phase 5/6
- Architecture: HIGH — direct structural analog to Phase 6; jes_factors table inspected and populated; JESFactorScore model pre-defined
- Pitfalls: HIGH — JSON text columns and non-optional int fields verified against live schema; stage gate pitfall verified against jd_service.py
- Test structure: HIGH — conftest.py fixture pattern is well-established; test file does not yet exist (Wave 0)

**Research date:** 2026-06-02
**Valid until:** 2026-07-02 (stable stack; only meaningful change would be a jes_factors data update or instructor major version)
