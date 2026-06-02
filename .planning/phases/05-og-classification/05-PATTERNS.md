# Phase 5: OG Classification — Pattern Map

**Mapped:** 2026-06-02
**Files analyzed:** 10 new/modified files
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/db.py` | config / schema | CRUD | `app/db.py` (self — append DDL block) | exact |
| `scripts/ingest_og_definitions.py` | utility / ingest | file-I/O + CRUD | `scripts/ingest_policy.py` | exact |
| `app/ai/og_ranking.py` | service / AI client | request-response | `app/ai/noc_ranking.py` | exact |
| `app/services/og_classifier.py` | service | request-response | `app/services/noc_mapper.py` | exact |
| `app/api/og_classification.py` | controller | request-response | `app/api/noc_mapping.py` | exact |
| `app/models/og.py` | model | request-response | `app/models/noc.py` | exact |
| `templates/wizard/step_og.html` | component / template | request-response | `templates/wizard/step_noc.html` | exact |
| `templates/partials/og_results.html` | component / template | request-response | `templates/partials/noc_results.html` | exact |
| `tests/test_og_classification.py` | test | request-response | `tests/test_noc_mapping.py` | exact |
| `tests/test_og_ranking.py` | test | CRUD | `tests/test_noc_ranking.py` | exact |
| `app/static/css/main.css` | config / style | — | `app/static/css/main.css` (self — append section) | exact |

---

## Pattern Assignments

### `app/db.py` — append `og_definitions` DDL to `CA_JES_SCHEMA_DDL`

**Analog:** `app/db.py` lines 67–127 (existing `CA_JES_SCHEMA_DDL` string)

**Where to insert:** Append a new DDL block to the `CA_JES_SCHEMA_DDL` string, immediately after the `policy_fts` virtual table definition (line 127). Follow the same pattern as every prior table in that string: table DDL then supporting index DDL.

**DDL to add** (from research Pattern 1):
```sql
    -- Full TBS OCHRO OG definitions (Phase 5, CLASS-01 verbatim citation)
    CREATE TABLE IF NOT EXISTS og_definitions (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        og_code      TEXT NOT NULL UNIQUE,
        og_name      TEXT NOT NULL,
        parent_group TEXT,
        definition   TEXT NOT NULL,
        inclusions   TEXT,
        exclusions   TEXT,
        source_file  TEXT NOT NULL,
        source_hash  TEXT NOT NULL,
        ingested_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
    );

    CREATE INDEX IF NOT EXISTS idx_og_definitions_code ON og_definitions(og_code);
    CREATE INDEX IF NOT EXISTS idx_og_definitions_parent ON og_definitions(parent_group);
```

**`create_schema` docstring update** (lines 178–189): Update the docstring to add `og_definitions` to the "Tables created here" list, following the pattern of the existing Phase 3 / Phase 4 bullets.

**UNIQUE constraint insert pattern** — copy from `ca_clauses` insert logic; use `INSERT OR IGNORE` on the `UNIQUE(og_code)` constraint:
```python
# From app/db.py pattern (ca_clauses uses same UNIQUE + INSERT OR IGNORE approach)
conn.execute(
    """
    INSERT OR IGNORE INTO og_definitions
        (og_code, og_name, parent_group, definition, inclusions, exclusions, source_file, source_hash)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (og_code, og_name, parent_group, definition, inclusions, exclusions, "TBS-OCHRO-OG.txt", file_hash),
)
```

---

### `scripts/ingest_og_definitions.py` (utility, file-I/O + CRUD)

**Analog:** `scripts/ingest_policy.py`

**Module docstring pattern** (lines 1–13):
```python
"""
scripts/ingest_og_definitions.py — TBS OCHRO OG definitions ingest (Phase 5 CLASS-01 prereq).

Reads data/TBS-OCHRO-OG.txt, parses each OG section into (og_code, og_name,
parent_group, definition, inclusions, exclusions), upserts into og_definitions table.

Usage:
    python scripts/ingest_og_definitions.py \\
        --db-path /home/charles/job_description_builder/app.db \\
        --data-dir /home/charles/job_description_builder/data
"""
```

**Imports + sys.path pattern** (lines 14–25):
```python
from __future__ import annotations

import argparse
import hashlib
import re
import sqlite3
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
```

**Path traversal guard** (lines 42–54 of `ingest_policy.py`) — copy verbatim, rename `validate_db_path`:
```python
def validate_db_path(db_path: str) -> Path:
    resolved = Path(db_path).resolve()
    project_root = Path(__file__).resolve().parent.parent
    try:
        resolved.relative_to(project_root)
        return resolved
    except ValueError:
        print(
            f"Error: --db-path must be under the project root ({project_root}).\n"
            f"Got: {resolved!r}\nPath traversal is not permitted.",
            file=sys.stderr,
        )
        raise SystemExit(1)
```

**Connection factory pattern** (lines 61–68 of `ingest_policy.py`) — identical `load_connection()` function; copy verbatim.

**SHA-256 hash function** (lines 75–77 of `ingest_policy.py`) — copy `compute_file_hash()` verbatim.

**Core parse function** (from RESEARCH.md Pattern 2):
```python
def parse_og_section(text: str) -> dict:
    """
    Given a raw text block for one OG, return a dict with keys:
    og_code, og_name, parent_group, definition, inclusions, exclusions
    """
    code_match = re.search(r'\(([A-Z]{2,4})\)', text)
    og_code = code_match.group(1) if code_match else None

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

**CLI entrypoint pattern** (lines 252–313 of `ingest_policy.py`) — follow the same `parse_args()` → `main()` → `raise SystemExit(main())` structure. The `main()` function must: validate db path, connect, call `create_schema(con)`, parse TBS-OCHRO-OG.txt, upsert rows, print summary counts.

**Print progress pattern** (lines 274–306 of `ingest_policy.py`):
```python
print(f"[1/3] Connecting to {db_path} ...", flush=True)
# ... connect ...
print(f"[2/3] Parsing TBS-OCHRO-OG.txt ...", flush=True)
# ... parse ...
print(f"[3/3] Upserting og_definitions ...", flush=True)
# ... upsert ...
total = con.execute("SELECT COUNT(*) FROM og_definitions").fetchone()[0]
print(f"\nIngest complete:\n  og_definitions: {total:,} rows\n", flush=True)
```

---

### `app/ai/og_ranking.py` (service/AI client, request-response)

**Analog:** `app/ai/noc_ranking.py`

**Module docstring + architecture note** (lines 1–10 of `noc_ranking.py`) — copy and adapt:
```python
"""
app/ai/og_ranking.py — Instructor client singleton and Pydantic output models for OG ranking.

OGCandidate, OGRankingResult, and PolicyAdjacencyResult are the structured output
types for the OG classification pipeline. og_instructor_client is the module-level
singleton; construct once at import time, never per-request.

Architecture non-negotiable: Do not construct og_instructor_client inside route handlers
or service functions — it creates an httpx connection pool on every call.
"""
```

**Imports pattern** (lines 13–17 of `noc_ranking.py`):
```python
from __future__ import annotations

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, field_validator

from app.config import settings
```

**Pydantic output models** (from RESEARCH.md Code Examples):
```python
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

**Static OG levels lookup** (from RESEARCH.md OG Level Static Lookup section):
```python
OG_LEVELS: dict[str, list[int]] = {
    "AS": list(range(1, 9)),
    "CR": list(range(1, 7)),
    "PM": list(range(1, 7)),
    "PE": list(range(1, 8)),
    "EC": list(range(1, 8)),
    "IT": list(range(1, 5)),
    "CS": list(range(1, 6)),
    "EX": list(range(1, 6)),
    "IS": list(range(1, 8)),
    "GT": list(range(1, 9)),
}
```

**Module-level singleton** (lines 81–95 of `noc_ranking.py`) — identical structure, rename to `og_instructor_client`:
```python
# Module-level singleton — built once at import time, reused for the application lifetime.
# Mode.JSON is required for Ollama. Do NOT construct per-request.
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

og_instructor_client = instructor.from_openai(_openai_client, mode=instructor.Mode.JSON)
```

**Prompt constants** (from RESEARCH.md Pattern 3 and Pattern 4) — define `SYSTEM_PROMPT`, `POLICY_DETECTION_PROMPT`, and `build_og_context()` function in this file.

---

### `app/services/og_classifier.py` (service, request-response)

**Analog:** `app/services/noc_mapper.py`

**Module docstring** (lines 1–18 of `noc_mapper.py`) — adapt for OG pipeline:
```python
"""
app/services/og_classifier.py — Three-step OG classification pipeline.

Steps:
  1. Load OG definitions from og_definitions table (~30 rows, direct context)
  2. AS vs EC policy-adjacent detection (instructor binary classification)
  3. LLM rank top-3 OG candidates (instructor OGRankingResult)

Online guardrail: evidence_quotes verified verbatim against og_definitions rows.
"""
```

**Imports pattern** (lines 19–35 of `noc_mapper.py`):
```python
from __future__ import annotations

import asyncio
import logging

from app.ai.og_ranking import (
    OGCandidate, OGRankingResult, PolicyAdjacencyResult,
    OG_LEVELS, SYSTEM_PROMPT, POLICY_DETECTION_PROMPT,
    build_og_context, og_instructor_client,
)
from app.config import settings
from app.db import get_connection
from app.models.work_description import OGRecommendation, ProvenanceTag

logger = logging.getLogger(__name__)
```

**Connection lifecycle** (lines 82–83 + 181–183 of `noc_mapper.py`) — open per-call, close in `finally`:
```python
async def classify_og(
    work_description: str,
    confirmed_noc_code: str,
    db_path: str,
) -> dict:
    conn = await asyncio.to_thread(lambda: get_connection(db_path))
    try:
        # ... pipeline steps ...
    finally:
        await asyncio.to_thread(conn.close)
```

**`asyncio.to_thread` DB query pattern** (lines 91–105 of `noc_mapper.py`):
```python
og_rows = await asyncio.to_thread(
    lambda: conn.execute(
        """
        SELECT og_code, og_name, definition, inclusions, exclusions
        FROM og_definitions
        WHERE og_code IN ({placeholders})
        """,
        tuple(relevant_codes),
    ).fetchall()
)
```

**instructor call pattern** (lines 147–176 of `noc_mapper.py`):
```python
result: OGRankingResult = await og_instructor_client.chat.completions.create(
    model=settings.generation_model,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_og_context(og_rows, confirmed_noc_code, work_description)},
    ],
    response_model=OGRankingResult,
    max_retries=3,
    max_tokens=2048,
    temperature=0.0,
    extra_body={"options": {"num_ctx": 16384}},
)
```

**Verbatim guardrail pattern** (lines 208–237 of `noc_mapper.py`) — adapt `_check_verbatim_fidelity` to check each `evidence_quote` is a substring of the corresponding `og_definitions.definition + inclusions + exclusions` text. Same `instr(column, ?)` SQL check pattern.

**`model_copy(update=...)` pattern** (line 232 of `noc_mapper.py`) — used throughout for immutable Pydantic model updates:
```python
candidate.model_copy(update={"evidence_quotes": verified_quotes})
```

---

### `app/api/og_classification.py` (controller, request-response)

**Analog:** `app/api/noc_mapping.py`

**Router setup + templates pattern** (lines 1–34 of `noc_mapping.py`):
```python
from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.db import get_connection
from app.models.og import OGClassifyRequest, OGClassifyResponse
from app.services.og_classifier import classify_og
from app.services.wd_store import load_work_description, save_work_description

router = APIRouter()

_templates_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"
)
templates = Jinja2Templates(directory=_templates_dir)
```

**POST classify route pattern** (lines 37–97 of `noc_mapping.py`) — adapt `map_noc` → `classify_og_route`:
- Accept `wd_id` as Form field (not JSON body, unlike `/api/noc/map`)
- Load WorkDescription from DB, check `wd.stage == "noc_mapped"` (raise HTTP 422 if wrong)
- Call `classify_og(work_description=wd.raw_input, confirmed_noc_code=str(wd.confirmed_noc.noc_code), db_path=settings.db_path)`
- Persist result to `wd.og_recommendation`
- Dual-path HTMX/JSON response (same `request.headers.get("HX-Request")` check)

**ValueError → HTTP 422 pattern** (lines 51–56 of `noc_mapping.py`):
```python
try:
    result = await classify_og(...)
except ValueError as exc:
    raise HTTPException(status_code=422, detail=str(exc))
```

**POST confirm route pattern** (lines 100–142 of `noc_mapping.py`) — adapt `confirm_noc` → `confirm_og`. Key differences from NOC confirm:
- Form fields: `wd_id`, `og_code`, `og_level` (three fields, not two)
- Validate `og_level` against `OG_LEVELS[og_code]` before DB write (raise HTTP 422 if invalid)
- Set `wd.confirmed_og`, `wd.confirmed_level = f"{og_code}-{og_level}"`, `wd.stage = "og_classified"`
- Set `wd.og_recommendation.confirmed_by_advisor = True` via `model_copy(update=...)`

**Full confirm route** (from RESEARCH.md Code Examples — OG Confirm Endpoint Pattern):
```python
@router.post("/api/og/confirm")
async def confirm_og(
    request: Request,
    wd_id: str = Form(...),
    og_code: str = Form(...),
    og_level: str = Form(...),
) -> dict:
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
    # ... load wd, check stage == "noc_mapped", update fields, save ...
```

**HTMX dual-path response** (lines 132–142 of `noc_mapping.py`):
```python
if request.headers.get("HX-Request"):
    return templates.TemplateResponse(
        "partials/og_confirmed.html",
        {"request": request, "og_code": og_code, "og_level": f"{og_code}-{og_level}", "wd_id": wd_id},
    )
return {"status": "confirmed", "og_code": og_code, "og_level": f"{og_code}-{og_level}", "wd_id": wd_id}
```

**Register router in `app/main.py`** — follow the pattern already used for `noc_mapping.router`; add one `app.include_router(og_classification.router)` line.

---

### `app/models/og.py` (model, request-response)

**Analog:** `app/models/noc.py`

**File structure** (lines 1–41 of `noc.py`) — same pattern:
```python
"""
app/models/og.py — Request and response Pydantic models for the OG classification API.

OGClassifyRequest: POST /api/og/classify body (wd_id only — work description loaded from DB)
OGClassifyResponse: POST /api/og/classify response
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.ai.og_ranking import OGCandidate


class OGClassifyRequest(BaseModel):
    wd_id: str = Field(..., description="WorkDescription ID — must be in 'noc_mapped' stage")


class OGClassifyResponse(BaseModel):
    candidates: list[OGCandidate] = Field(..., min_length=1, max_length=3)
    wd_id: str
    asec_alert: dict | None = None
```

---

### `templates/wizard/step_og.html` (component/template, request-response)

**Analog:** `templates/wizard/step_noc.html`

**Full file pattern** (lines 1–34 of `step_noc.html`) — identical structure, adapt content:
```html
{% extends "base.html" %}

{% block title %}OG Classification — JD Builder{% endblock %}

{% block content %}
<section id="wizard-step">
    <h1>Occupational Group Classification</h1>
    <p>The system will identify the top 3 occupational groups based on the confirmed NOC profile.</p>

    <form hx-post="/api/og/classify"
          hx-target="#og-results"
          hx-swap="innerHTML"
          hx-indicator="#spinner"
          hx-disabled-elt="#classify-btn">
        <input type="hidden" name="wd_id" value="{{ wd_id }}">
        <button id="classify-btn" type="submit">Find OG Candidates</button>
        <span id="spinner" class="htmx-indicator" aria-label="Loading">Classifying occupational group...</span>
    </form>

    <div id="og-results" aria-live="polite"></div>
</section>
{% endblock %}
```

**Key differences from `step_noc.html`:**
- No `hx-ext="json-enc"` needed — form sends `wd_id` as a hidden field (no textarea required; work description comes from DB)
- No `{% block scripts %}` block needed unless json-enc is used
- `hx-target="#og-results"`, not `#noc-results`

---

### `templates/partials/og_results.html` (component/template, request-response)

**Analog:** `templates/partials/noc_results.html`

**Card loop structure** (lines 1–35 of `noc_results.html`) — same `{% for candidate in candidates %}` / `{% else %}` / `{% endfor %}` structure with per-card HTMX confirm form.

**AS/EC alert banner** — new element prepended before the card loop; no analog in NOC templates. Follows `role="alert"` ARIA pattern used in `noc_results.html`'s `.empty-state` block:
```html
{% if asec_alert %}
<div class="asec-alert" role="alert">
    <strong>AS vs EC Distinction Required</strong>
    ...
</div>
{% endif %}
```

**Per-card confirm form** (lines 22–28 of `noc_results.html`) — adapt, adding level select:
```html
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
```

**Full template excerpt** is provided in RESEARCH.md Pattern 5 (lines 310–364) — use that directly.

---

### `tests/test_og_classification.py` (test, request-response)

**Analog:** `tests/test_noc_mapping.py`

**Module-level env setup helper** (lines 13–24 of `test_noc_mapping.py`) — copy `_set_env()` verbatim; it sets the same five env vars.

**Mock Ollama client factory** (lines 26–34) — copy `_make_mock_ollama_client()` verbatim.

**Bootstrap fixture** (lines 81–90) — copy `_bootstrap_app_modules` autouse fixture pattern; replace `noc_mapping_db` with `og_db` fixture:
```python
@pytest.fixture(autouse=True)
def _bootstrap_app_modules(og_db, monkeypatch, tmp_path):
    global _app_bootstrapped
    if not _app_bootstrapped:
        _set_env(monkeypatch, str(og_db), tmp_path)
        _clear_app_modules()
        import app.main  # noqa: F401
        _app_bootstrapped = True
    yield
```

**`test_db_routing` fixture** (lines 93–114) — copy and adapt; patch import sites for `og_classification` instead of `noc_mapping`:
```python
monkeypatch.setattr("app.api.og_classification.get_connection", patched_get_connection)
monkeypatch.setattr("app.services.og_classifier.get_connection", patched_get_connection)
```

**FastAPI integration test pattern** (lines 275–336) — copy `AsyncClient(transport=ASGITransport(app=app))` pattern verbatim; adapt for `/api/og/classify` and `/api/og/confirm` routes.

**Stage gate test** — new; no analog in NOC tests. Follow the 422-on-bad-input pattern (lines 275–289):
```python
async def test_classify_requires_noc_mapped_stage(test_db_routing, og_db):
    """POST /api/og/classify returns 422 if WorkDescription not in noc_mapped stage."""
    # Pre-populate WD in 'input' stage (not 'noc_mapped')
    ...
    response = await client.post("/api/og/classify", data={"wd_id": wd_id})
    assert response.status_code == 422
```

**End-to-end test** (lines 339–371) — adapt `test_end_to_end_map_then_confirm` pattern for classify → confirm flow; confirm must include `og_level` form field.

**WD persistence test** (lines 374–431) — copy `test_confirm_noc_updates_wd` pattern; verify `wd.stage == "og_classified"`, `wd.confirmed_og`, `wd.confirmed_level` after confirm.

---

### `tests/test_og_ranking.py` (test, CRUD)

**Analog:** `tests/test_noc_ranking.py`

**Overall structure** — class-based (`class TestOGCandidateSchema`) with `pytest.skip` on ImportError, same as `test_noc_ranking.py` lines 7–82.

**Schema validation pattern** (lines 9–24 of `test_noc_ranking.py`):
```python
class TestOGCandidateSchema:
    def test_og_candidate_schema(self):
        try:
            from app.ai.og_ranking import OGCandidate
        except ImportError:
            pytest.skip("app.ai.og_ranking not yet implemented")
        c = OGCandidate(og_code="EC", rank=1, confidence=0.9,
                        rationale="...", evidence_quotes=["verbatim text"])
        assert c.og_code == "EC"
```

**Instructor singleton test** (lines 74–82):
```python
def test_og_instructor_client_exists(self):
    try:
        from app.ai.og_ranking import og_instructor_client
    except ImportError:
        pytest.skip("app.ai.og_ranking not yet implemented")
    assert og_instructor_client is not None
```

**Verbatim guardrail unit test** — adapt `test_verbatim_guardrail_strips_fabricated` (lines 192–235 of `test_noc_mapping.py`); mock `conn.execute` returning `None` for fabricated quotes.

**AS/EC detection test** — mock `og_instructor_client` to return `PolicyAdjacencyResult(is_policy_adjacent=True, ...)` for policy-laden input; verify `asec_alert` is populated in result.

**OG level validation test** — assert `OG_LEVELS["AS"] == list(range(1, 9))`; assert unknown code returns `[]`.

---

### `app/static/css/main.css` — append Phase 5 component classes

**Analog:** `app/static/css/main.css` lines 269–363 (`.noc-card` component block)

**Section header pattern** (line 265):
```css
/* =====================================================================
 * 8. OG CLASSIFICATION COMPONENT CLASSES
 * ===================================================================== */
```

**OG card classes** — mirror `.noc-card` structure (lines 270–349) with `.og-card`, `.og-card-header`, `.og-definition`, `.og-inclusions`, `.og-exclusions`.

**Level select styling** — add `.og-level-select` using the existing `select` base styles already present in the CSS reset section.

**AS/EC alert classes** — use the `.error-state` border-left pattern (lines 365–382) as structural template:
```css
/* .asec-alert — AS vs EC disambiguation warning */
.asec-alert {
    border-left: 4px solid var(--color-accent);
    padding: var(--space-md);
    margin-bottom: var(--space-lg);
    background-color: var(--color-secondary);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

/* .asec-comparison — side-by-side AS/EC definition cards */
.asec-comparison {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-md);
    margin-top: var(--space-md);
}

.asec-card {
    background-color: var(--color-dominant);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: var(--space-md);
}
```

**CSS variables** — all Phase 5 classes must use the existing CSS custom properties (`var(--color-*)`, `var(--space-*)`, `var(--text-*)`, `var(--radius-*)`) already defined in `main.css`; no new variables needed.

---

## Shared Patterns

### Connection Lifecycle (apply to: `og_classifier.py`, `og_classification.py`)

**Source:** `app/services/noc_mapper.py` lines 82–183, `app/api/noc_mapping.py` lines 59–81

Connection opens per-request via `asyncio.to_thread`, closes in `finally`:
```python
conn = await asyncio.to_thread(lambda: get_connection(db_path))
try:
    # all DB work here
finally:
    await asyncio.to_thread(conn.close)
```

Never hold a module-level connection. Never call `sqlite3.connect()` directly — always use `get_connection()`.

### HTMX Dual-Path Response (apply to: `og_classification.py`)

**Source:** `app/api/noc_mapping.py` lines 83–97 and 132–142

```python
if request.headers.get("HX-Request"):
    return templates.TemplateResponse("partials/og_results.html", {...})
return OGClassifyResponse(candidates=..., wd_id=wd_id_str)
```

### instructor Client Call with Ollama num_ctx (apply to: `og_classifier.py`)

**Source:** `app/services/noc_mapper.py` lines 144–176

Use `extra_body={"options": {"num_ctx": 16384}}` for OG ranking (larger context than NOC's 8192). Cloud path omits `extra_body`:
```python
extra_kwargs: dict = {}
if not settings.cloud_api_key:
    extra_kwargs["extra_body"] = {"options": {"num_ctx": 16384}}

result = await og_instructor_client.chat.completions.create(
    ...
    **extra_kwargs,
)
```

### Pydantic `model_copy(update=...)` (apply to: `og_classifier.py`, `og_classification.py`)

**Source:** `app/services/noc_mapper.py` line 232, `app/api/noc_mapping.py` line 127

Pydantic v2 immutable model updates:
```python
wd.og_recommendation = wd.og_recommendation.model_copy(
    update={"confirmed_by_advisor": True, "level": f"{og_code}-{og_level}"}
)
```

### Test Module Bootstrap Guard (apply to: `test_og_classification.py`)

**Source:** `tests/test_noc_mapping.py` lines 78–90

Module-level `_app_bootstrapped = False` flag prevents the instructor singleton from being reconstructed on every test, which would leak httpx connection pools:
```python
_app_bootstrapped = False

@pytest.fixture(autouse=True)
def _bootstrap_app_modules(og_db, monkeypatch, tmp_path):
    global _app_bootstrapped
    if not _app_bootstrapped:
        _set_env(monkeypatch, str(og_db), tmp_path)
        _clear_app_modules()
        import app.main  # noqa: F401
        _app_bootstrapped = True
    yield
```

### pytest.skip on ImportError (apply to: `test_og_ranking.py`)

**Source:** `tests/test_noc_ranking.py` lines 12–13

All Wave 0 stub tests use this pattern so the suite stays green before the module is written:
```python
try:
    from app.ai.og_ranking import OGCandidate
except ImportError:
    pytest.skip("app.ai.og_ranking not yet implemented")
```

### WorkDescription Stage Gate (apply to: `og_classification.py`)

**Source:** `app/api/noc_mapping.py` lines 113–126 (noc confirm's implicit pattern)

New for Phase 5 — classify endpoint must gate on `wd.stage == "noc_mapped"`:
```python
wd = await asyncio.to_thread(lambda: load_work_description(conn, wd_id))
if wd is None:
    raise HTTPException(status_code=404, detail=f"WorkDescription {wd_id!r} not found")
if wd.stage != "noc_mapped":
    raise HTTPException(
        status_code=422,
        detail=f"WorkDescription is in stage {wd.stage!r}, expected 'noc_mapped'",
    )
```

---

## conftest.py Addition Required

**Source:** `tests/conftest.py` lines 57–153 (existing `noc_db`, `ca_jes_db`, `noc_mapping_db` fixture pattern)

Add `og_db` fixture to `tests/conftest.py` — pre-populates `og_definitions` with AS, EC, IT, PE rows for unit/integration tests that do not require Ollama:
```python
@pytest.fixture
def og_db(tmp_path):
    """
    Temp SQLite DB with full schema + synthetic og_definitions rows for AS, EC, IT, PE.
    Used by test_og_classification.py and test_og_ranking.py.
    Does NOT require Ollama to be running.
    """
    from app.db import create_schema, get_connection

    db_path = str(tmp_path / "test_og.db")
    con = get_connection(db_path)
    create_schema(con)  # creates og_definitions table

    for row in [
        ("EC", "Economics and Social Science Services", "PA",
         "Positions primarily involved in economic and social research...",
         "the planning, development, delivery or management of policies...",
         "the planning...directed to the public or to the Public Service"),
        ("AS", "Administrative Services", "PA",
         "Positions primarily involved in administrative support...",
         "the planning...directed to the Public Service",
         None),
        ("IT", "Information Technology", None,
         "Positions primarily involved in IT systems development...", None, None),
        ("PE", "Personnel Administration", "PA",
         "Positions primarily involved in HR policy...", None, None),
    ]:
        con.execute(
            "INSERT OR IGNORE INTO og_definitions "
            "(og_code, og_name, parent_group, definition, inclusions, exclusions, source_file, source_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (*row, "TBS-OCHRO-OG.txt", "testhash_v1"),
        )
    con.commit()

    yield db_path
    con.close()
```

---

## No Analog Found

All Phase 5 files have close analogs. No files require fallback to RESEARCH.md patterns alone.

| File | Notes |
|------|-------|
| `app/models/og.py` | Thin wrapper; `app/models/noc.py` is a complete pattern match |
| `templates/partials/og_confirmed.html` | Implied by Phase 5 confirm endpoint; analog is `templates/partials/noc_confirmed.html` (7 lines) — copy directly, adapt field names |

---

## Metadata

**Analog search scope:** `app/`, `scripts/`, `templates/`, `tests/`
**Files scanned:** 12 source files read in full
**Pattern extraction date:** 2026-06-02
