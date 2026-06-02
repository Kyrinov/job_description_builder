# Phase 7: JES Scoring — Pattern Map

**Mapped:** 2026-06-02
**Files analyzed:** 7 (5 new, 2 modified)
**Analogs found:** 7 / 7

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/ai/jes_scoring.py` | service/ai | request-response | `app/ai/jd_ranking.py` | exact |
| `app/services/jes_service.py` | service | CRUD + request-response | `app/services/jd_service.py` | exact |
| `app/api/jes_scoring.py` | controller | request-response | `app/api/jd_generation.py` | exact |
| `templates/wizard/step_jes.html` | component | request-response | `templates/wizard/step_jd.html` | exact |
| `templates/partials/jes_scores.html` | component | request-response | `templates/partials/jd_confirmed.html` | role-match |
| `tests/test_jes_scoring.py` | test | request-response | `tests/test_jd_generation.py` | exact |
| `app/main.py` (modified) | config | request-response | `app/main.py` lines 25-26, 107 | exact |

---

## Pattern Assignments

### `app/ai/jes_scoring.py` (ai module, request-response)

**Analog:** `app/ai/jd_ranking.py`

**Imports pattern** (`app/ai/jd_ranking.py` lines 1-21):
```python
from __future__ import annotations

import sqlite3
from typing import Literal

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config import settings
```

**Module docstring pattern** (`app/ai/jd_ranking.py` lines 1-10):
```python
"""
app/ai/jes_scoring.py — Instructor client singleton and Pydantic output models for JES scoring.

JESFactorRating is the structured output type for the per-factor scoring pipeline.
jes_instructor_client is the module-level singleton; construct once at import time,
never per-request.

Architecture non-negotiable: Do not construct jes_instructor_client inside route handlers
or service functions — it creates an httpx connection pool on every call.
"""
```

**Pydantic output model pattern** (`app/ai/jd_ranking.py` lines 23-36 — adapted for JES):
```python
class JESFactorRating(BaseModel):
    """Structured LLM output for a single JES factor rating."""

    degree: str = Field(
        description="Degree identifier — must be from the provided degree list, e.g. 'D1', 'D3'"
    )
    rationale: str = Field(
        description="Justification for the selected degree, citing the position's duties"
    )
```
Note: LLM returns only `degree` and `rationale`. The service maps `degree` → `points` via
`json.loads(row["point_values"])`. This prevents hallucinated point values.

**JES scoring system prompt constant** (pattern from `app/ai/jd_ranking.py` lines 97-129):
```python
JES_SCORING_SYSTEM_PROMPT = """
You are a Government of Canada HR classification specialist.
You are scoring a position against the Job Evaluation Standard (JES) for the {og_name} ({og_code}) group.

CRITICAL RULES:
- Select the degree identifier EXACTLY as shown in the degree list provided — e.g. "D1", "D3"
- Your degree selection must be justified by specific duties listed in the position description
- Do NOT invent degree identifiers; only use identifiers from the provided degree list
- Return only the degree identifier string and a rationale — do not compute points
""".strip()
```

**Version lookup helper** (`app/ai/jd_ranking.py` lines 132-148 — adapted for JES):
```python
def get_jes_version_info(conn: sqlite3.Connection, og_code: str) -> tuple[str, str]:
    """
    Return (version_label, content_hash) for the JES source document for the given OG.

    Pattern: source_name LIKE f"{og_code}%" — sufficient for all known OG prefixes.
    Fallback: ("JES v1.0", "") if no matching source_documents row found.
    """
    try:
        row = conn.execute(
            "SELECT version_label, content_hash FROM source_documents "
            "WHERE source_name LIKE ? LIMIT 1",
            (f"{og_code}%",),
        ).fetchone()
        if row:
            return row["version_label"], row["content_hash"]
    except Exception:
        pass
    return "JES v1.0", ""
```

**Instructor singleton pattern** (`app/ai/jd_ranking.py` lines 151-162):
```python
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
Critical: `settings` must be imported before this block executes (Pitfall 6 in RESEARCH.md).
Name the client `jes_instructor_client` — not `jd_instructor_client` — to avoid collision.

---

### `app/services/jes_service.py` (service, CRUD + request-response)

**Analog:** `app/services/jd_service.py`

**Imports pattern** (`app/services/jd_service.py` lines 1-35):
```python
from __future__ import annotations

import asyncio
import json
import logging
from datetime import date

from app.ai.jes_scoring import (
    JES_SCORING_SYSTEM_PROMPT,
    JESFactorRating,
    get_jes_version_info,
    jes_instructor_client,
)
from app.config import settings
from app.db import get_connection
from app.models.work_description import JESFactorScore, ProvenanceTag, WorkDescription
from app.services.wd_store import load_work_description, save_work_description

logger = logging.getLogger(__name__)
```

**Stage gate + WD load pattern** (`app/services/jd_service.py` lines 89-103):
```python
conn = await asyncio.to_thread(lambda: get_connection(db_path))
try:
    wd = await asyncio.to_thread(lambda: load_work_description(conn, wd_id))
    if wd is None:
        raise ValueError(f"WorkDescription {wd_id!r} not found")
    if wd.stage != "jd_drafted":
        raise ValueError(
            f"WorkDescription is in stage {wd.stage!r}, expected 'jd_drafted'"
        )
    if wd.confirmed_og is None:
        raise ValueError("WorkDescription has no confirmed OG — complete OG classification first")
```
Note: Phase 7 gate is `stage == 'jd_drafted'` (not `'og_classified'`). Do not copy the
Phase 6 stage literal verbatim — see Pitfall 5 in RESEARCH.md.

**asyncio.to_thread DB query pattern** (`app/services/jd_service.py` lines 107-114):
```python
factor_rows = await asyncio.to_thread(
    lambda: conn.execute(
        "SELECT id, factor_name, factor_definition, degree_descriptors, "
        "point_values, max_points, source_hash "
        "FROM jes_factors WHERE og_code = ? ORDER BY id",
        (confirmed_og,),
    ).fetchall()
)
if not factor_rows:
    raise ValueError(
        f"No JES factors found for OG {confirmed_og!r} — check jes_factors table"
    )
```

**Per-factor user prompt builder** (derived from `app/services/jd_service.py` `_build_duty_from_row` pattern + RESEARCH.md Code Examples):
```python
def _build_factor_user_prompt(factor_row, duties: list, work_description_raw: str) -> str:
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
        f"Work description: {work_description_raw[:300]}\n\n"
        "Select the degree that best fits this position and provide a rationale."
    )
```
Critical: always `json.loads(factor_row["degree_descriptors"])` — it is stored as JSON text,
not a Python list (Pitfall 1 in RESEARCH.md).

**Per-factor LLM call with instructor retry** (`app/services/jd_service.py` lines 150-170):
```python
extra_kwargs: dict = {}
if not settings.cloud_api_key:
    extra_kwargs["extra_body"] = {"options": {"num_ctx": 8192}}

factor_rating: JESFactorRating = await jes_instructor_client.chat.completions.create(
    model=settings.generation_model,
    messages=[
        {"role": "system", "content": JES_SCORING_SYSTEM_PROMPT.format(
            og_name=og_name, og_code=confirmed_og
        )},
        {"role": "user", "content": user_prompt_for_factor},
    ],
    response_model=JESFactorRating,
    max_retries=3,
    max_tokens=1024,
    temperature=0.0,
    **extra_kwargs,
)
```

**Per-factor failure pattern** (no direct analog — see RESEARCH.md Pattern 4):
```python
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
`JESFactorScore.level` is typed `int` (non-optional). Use sentinel `-1` for failures —
setting `level=None` raises a Pydantic ValidationError (Pitfall 2 in RESEARCH.md).

**ProvenanceTag for JES factor** (derived from `app/services/jd_service.py` `_build_duty_from_row` lines 41-55):
```python
def _build_jes_factor_score(
    factor_row, rating: JESFactorRating, og_code: str, jes_version: str
) -> JESFactorScore:
    point_values = json.loads(factor_row["point_values"])
    points = point_values.get(rating.degree)
    return JESFactorScore(
        factor_name=factor_row["factor_name"],
        level=int(rating.degree.lstrip("D")) if rating.degree.startswith("D") else -1,
        points=points,
        rationale=rating.rationale,
        provenance=ProvenanceTag(
            source_type="JES",
            source_id=f"{og_code}/{factor_row['factor_name']}",
            source_version=jes_version,
            retrieved_date=date.today(),
        ),
    )
```

**Stage transition + save pattern** (`app/services/jd_service.py` lines 195-205):
```python
    # Stage advances to 'jes_scored' ONLY after ALL factors processed
    jes_total = sum(s.points for s in jes_scores if s.points is not None)
    updated_wd = wd.model_copy(update={
        "jes_scores": jes_scores,
        "jes_total_points": jes_total,
        "stage": "jes_scored",
    })
    await asyncio.to_thread(lambda: save_work_description(conn, updated_wd))

finally:
    await asyncio.to_thread(conn.close)
```

---

### `app/api/jes_scoring.py` (controller, request-response)

**Analog:** `app/api/jd_generation.py`

**Imports + router + templates pattern** (`app/api/jd_generation.py` lines 1-35):
```python
from __future__ import annotations

import os

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.jes_service import score_jes

router = APIRouter()

_templates_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"
)
templates = Jinja2Templates(directory=_templates_dir)
```

**Route handler with dual HTMX/JSON response** (`app/api/jd_generation.py` lines 38-65):
```python
@router.post("/api/jes/score")
async def score_jes_route(
    request: Request,
    wd_id: str = Form(...),
):
    """
    Run the per-factor JES scoring pipeline for a confirmed WD.
    Requires stage='jd_drafted'. Returns factor score cards (HTMX) or JSON.
    """
    try:
        result = await score_jes(wd_id=wd_id, db_path=settings.db_path)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=422, detail=msg)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/jes_scores.html",
            {
                "request": request,
                "jes_scores": result["jes_scores"],
                "jes_total_points": result["jes_total_points"],
                "wd_id": wd_id,
            },
        )
    return result
```

**ValueError → HTTP error mapping pattern** (`app/api/jd_generation.py` lines 47-53):
```python
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=422, detail=msg)
```
This exact two-branch pattern is used on every route in `jd_generation.py`. Copy it verbatim
for the `/api/jes/score` route.

---

### `templates/wizard/step_jes.html` (component, request-response)

**Analog:** `templates/wizard/step_jd.html`

**Full template structure** (`templates/wizard/step_jd.html` lines 1-22):
```html
{% extends "base.html" %}

{% block title %}JES Scoring — JD Builder{% endblock %}

{% block content %}
<section id="wizard-step">
    <h1>JES Factor Scoring</h1>
    <p>Score each JES factor for the confirmed occupational group. One LLM call per factor.</p>

    <form hx-post="/api/jes/score"
          hx-target="#jes-scores"
          hx-swap="innerHTML"
          hx-indicator="#jes-spinner"
          hx-disabled-elt="#score-btn">
        <input type="hidden" name="wd_id" value="{{ wd_id }}">
        <button id="score-btn" type="submit" class="button button--primary">Generate JES Scores</button>
        <span id="jes-spinner" class="htmx-indicator" aria-label="Scoring factors...">Scoring factors...</span>
    </form>

    <div id="jes-scores" aria-live="polite"></div>
</section>
{% endblock %}
```
Pattern: `{% extends "base.html" %}` + `{% block content %}` wrapping an `hx-post` form
targeting a `div` with `aria-live="polite"` for the async partial swap. Mirrors `step_jd.html`
exactly. The `hx-target` points to `#jes-scores`; the partial response fills that div.

---

### `templates/partials/jes_scores.html` (component, request-response)

**Analog:** `templates/partials/jd_confirmed.html` (structural pattern), `templates/partials/jd_duties.html` (card list pattern)

**Partial wrapper pattern** (`templates/partials/jd_confirmed.html` lines 1-8):
```html
{# HTMX partial: JES factor score cards #}
{# Replaces #jes-scores after POST /api/jes/score succeeds #}
<div id="jes-scores" role="status">
    <h2>JES Scoring Results</h2>
    <p>Total Points: <strong>{{ jes_total_points }}</strong></p>

    {% for score in jes_scores %}
    <div class="jes-factor-card {% if score.level == -1 %}jes-factor-card--error{% endif %}">
        <h3>{{ score.factor_name }}</h3>
        {% if score.level == -1 %}
        <p class="error">Scoring failed: {{ score.rationale }}</p>
        {% else %}
        <p>Degree: <strong>D{{ score.level }}</strong> — {{ score.points }} pts</p>
        <p>{{ score.rationale }}</p>
        <p class="muted">Source: {{ score.provenance.source_id }} ({{ score.provenance.source_version }})</p>
        {% endif %}
    </div>
    {% endfor %}
</div>
```
Note: render a warning card when `score.level == -1` (failure sentinel). The `jd_confirmed.html`
partial shows the `id` attribute matches the HTMX target from `step_jes.html` (`#jes-scores`).

---

### `tests/test_jes_scoring.py` (test, request-response)

**Analog:** `tests/test_jd_generation.py`

**Module-level env setup helpers** (`tests/test_jd_generation.py` lines 22-36):
```python
from __future__ import annotations

import pytest

_app_bootstrapped = False


def _set_env(monkeypatch, db_path: str, tmp_path) -> None:
    """Set minimum required env vars for app startup in tests."""
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("GENERATION_MODEL", "gemma4:31b")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")


def _clear_app_modules():
    import sys
    for mod in list(sys.modules.keys()):
        if mod.startswith("app."):
            del sys.modules[mod]
```

**autouse bootstrap fixture** (`tests/test_jd_generation.py` lines 38-49):
```python
@pytest.fixture(autouse=True)
def _bootstrap_app_modules(jes_db, monkeypatch, tmp_path):
    global _app_bootstrapped
    if not _app_bootstrapped:
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            import app.main  # noqa: F401
            _app_bootstrapped = True
        except Exception:
            pass
    yield
```
Rename the fixture argument from `jd_db` → `jes_db` (the new fixture added to conftest.py).

**WD factory helper for jd_drafted stage** (`tests/test_jd_generation.py` lines 52-105 — adapted):
```python
def _make_jd_drafted_wd(db_path: str) -> str:
    """
    Insert a WorkDescription in stage='jd_drafted' with confirmed NOC 21232, OG EC,
    and 2 draft duties. Returns wd_id as string.
    """
    try:
        from app.db import get_connection
        from app.models.work_description import (
            WorkDescription, NOCMatch, OGRecommendation, DraftDuty, ProvenanceTag
        )
        from app.services.wd_store import save_work_description
        from datetime import date
    except ImportError:
        pytest.skip("app modules not yet implemented")

    conn = get_connection(db_path)
    # ... build NOCMatch, OGRecommendation, DraftDuty list, then:
    wd = WorkDescription(
        session_id="test-session-jes",
        raw_input="Provides economic policy analysis and program evaluation.",
        confirmed_noc=noc_match,
        confirmed_og="EC",
        confirmed_level="EC-04",
        og_recommendation=og_rec,
        draft_duties=duties,
        stage="jd_drafted",     # <-- Phase 7 requires this stage, not 'og_classified'
    )
    save_work_description(conn, wd)
    conn.close()
    return str(wd.id)
```

**Stage gate test class pattern** (`tests/test_jd_generation.py` lines 143-177):
```python
class TestJESScoringStageGate:
    def test_score_jes_stage_gate(self, jes_db, monkeypatch, tmp_path):
        """POST /api/jes/score returns 422 if stage != 'jd_drafted'."""
        _set_env(monkeypatch, str(jes_db), tmp_path)
        _clear_app_modules()
        try:
            from app.api import jes_scoring  # noqa: F401
        except ImportError:
            pytest.skip("app.api.jes_scoring not yet implemented")

        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)

        wd_id = _make_og_classified_wd(str(jes_db))  # wrong stage
        resp = client.post("/api/jes/score", data={"wd_id": wd_id})
        assert resp.status_code == 422

    def test_score_jes_404_on_unknown_wd(self, jes_db, monkeypatch, tmp_path):
        """POST /api/jes/score returns 404 for unknown wd_id."""
        # same TestClient pattern, wd_id="00000000-0000-0000-0000-000000000000"
```

**jes_db fixture for conftest.py** (RESEARCH.md Code Examples — no existing analog):
```python
@pytest.fixture
def jes_db(tmp_path):
    """
    Temp SQLite DB with full schema + synthetic jes_factors rows for EC (2 factors)
    and a WorkDescription in stage='jd_drafted' with 2 draft duties.
    """
    from app.db import create_schema, get_connection
    import json
    db_path = str(tmp_path / "test_jes.db")
    con = get_connection(db_path)
    create_schema(con)

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
Add this fixture to `tests/conftest.py` (the existing file, not a new conftest).

---

### `app/main.py` (modified — router registration)

**Analog:** `app/main.py` lines 24-26 and line 107

**Import line pattern** (`app/main.py` lines 24-26):
```python
from app.api import health
from app.api import jd_generation
from app.api import noc_mapping
from app.api import og_classification
# ADD:
from app.api import jes_scoring
```

**Router registration pattern** (`app/main.py` line 107):
```python
app.include_router(health.router)
app.include_router(noc_mapping.router)
app.include_router(og_classification.router)
app.include_router(jd_generation.router)
# ADD (after jd_generation):
app.include_router(jes_scoring.router)
```

**Wizard GET route pattern** (`app/main.py` lines 135-156):
```python
@app.get("/wizard/jes", response_class=HTMLResponse)
async def wizard_jes(request: Request, wd_id: str = "") -> HTMLResponse:
    """Render the JES scoring wizard step (Phase 7)."""
    import jinja2
    try:
        return wizard_templates.TemplateResponse(
            "wizard/step_jes.html", {"request": request, "wd_id": wd_id}
        )
    except jinja2.TemplateNotFound:
        return HTMLResponse(
            "<!DOCTYPE html><html><body>"
            f"<h1>JES Scoring Wizard</h1>"
            f"<p>WorkDescription ID: {wd_id or '(none)'}</p>"
            "<p>The full template will be added in Plan 07-04.</p>"
            "</body></html>"
        )
```
Copy the same TemplateNotFound fallback pattern from the `wizard_jd` handler (lines 136-156).

---

## Shared Patterns

### Stage gate enforcement
**Source:** `app/services/jd_service.py` lines 89-103
**Apply to:** `app/services/jes_service.py` `score_jes()` function AND `app/api/jes_scoring.py` router
```python
if wd is None:
    raise ValueError(f"WorkDescription {wd_id!r} not found")
if wd.stage != "jd_drafted":
    raise ValueError(
        f"WorkDescription is in stage {wd.stage!r}, expected 'jd_drafted'"
    )
```
Phase 7 gate is `'jd_drafted'` — not `'og_classified'`. The service raises ValueError; the
router converts to HTTPException (404 for "not found", 422 for anything else).

### asyncio.to_thread for sync SQLite calls
**Source:** `app/services/jd_service.py` lines 89, 107, 202, 205
**Apply to:** `app/services/jes_service.py` — all DB calls must be wrapped
```python
conn = await asyncio.to_thread(lambda: get_connection(db_path))
try:
    wd = await asyncio.to_thread(lambda: load_work_description(conn, wd_id))
    rows = await asyncio.to_thread(lambda: conn.execute("SELECT ...", (...,)).fetchall())
    await asyncio.to_thread(lambda: save_work_description(conn, updated_wd))
finally:
    await asyncio.to_thread(conn.close)
```

### instructor + extra_body for local Ollama
**Source:** `app/services/jd_service.py` lines 150-170
**Apply to:** every LLM call in `app/services/jes_service.py`
```python
extra_kwargs: dict = {}
if not settings.cloud_api_key:
    extra_kwargs["extra_body"] = {"options": {"num_ctx": 8192}}

result = await jes_instructor_client.chat.completions.create(
    model=settings.generation_model,
    ...,
    max_retries=3,
    max_tokens=1024,
    temperature=0.0,
    **extra_kwargs,
)
```

### HTMX dual-path response
**Source:** `app/api/jd_generation.py` lines 55-65
**Apply to:** `app/api/jes_scoring.py` score route
```python
if request.headers.get("HX-Request"):
    return templates.TemplateResponse(
        "partials/jes_scores.html",
        {"request": request, "jes_scores": ..., "jes_total_points": ..., "wd_id": wd_id},
    )
return result  # plain JSON dict
```

### model_copy for WD updates
**Source:** `app/services/jd_service.py` lines 195-202
**Apply to:** `app/services/jes_service.py` before save
```python
updated_wd = wd.model_copy(update={
    "jes_scores": jes_scores,
    "jes_total_points": jes_total,
    "stage": "jes_scored",
})
await asyncio.to_thread(lambda: save_work_description(conn, updated_wd))
```

### JSON text column parsing
**Source:** RESEARCH.md Pitfall 1 + Code Examples
**Apply to:** every access of `factor_row["degree_descriptors"]` and `factor_row["point_values"]`
```python
degrees = json.loads(factor_row["degree_descriptors"])   # NOT factor_row["degree_descriptors"]
point_values = json.loads(factor_row["point_values"])     # NOT factor_row["point_values"]
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `templates/partials/jes_scores.html` | component | request-response | No existing factor-score-card partial; closest is `jd_duties.html` for list structure and `jd_confirmed.html` for wrapper id/role attributes — combine both patterns |
| `tests/conftest.py` `jes_db` fixture | test fixture | — | No existing fixture seeds `jes_factors` + `jd_drafted` WD; derive from `jd_db` fixture pattern in `conftest.py` lines 207-264 |

---

## Key Design Decisions to Carry Forward

1. `JESFactorScore.level` is `int` (non-optional, finalized Phase 1 model at `work_description.py` line 74). Failed factors use sentinel `level=-1` with descriptive `rationale`. No model migration needed.
2. Sequential per-factor LLM calls (not `asyncio.gather` fan-out) — matches `jd_service.py` style and avoids Ollama OOM on ARM64.
3. `degree_descriptors` and `point_values` are JSON text in SQLite — always `json.loads()` before use.
4. Stage gate is `'jd_drafted'` → `'jes_scored'`. Never advance stage before all factors (including failures) are collected.
5. `jes_instructor_client` must be constructed at module level in `app/ai/jes_scoring.py`, never inside service functions.

---

## Metadata

**Analog search scope:** `app/ai/`, `app/api/`, `app/services/`, `app/models/`, `app/main.py`, `templates/wizard/`, `templates/partials/`, `tests/`
**Files scanned:** 9 source files read directly
**Pattern extraction date:** 2026-06-02
