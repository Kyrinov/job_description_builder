# Phase 8: Export - Pattern Map

**Mapped:** 2026-06-02
**Files analyzed:** 5
**Analogs found:** 5 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/services/export_service.py` | service | request-response + file-I/O | `app/services/jes_service.py` | exact |
| `app/api/export.py` | router | request-response + file-I/O | `app/api/jes_scoring.py` | exact |
| `templates/wizard/step_export.html` | template (wizard step) | request-response | `templates/wizard/step_jes.html` | exact |
| `templates/partials/export_result.html` | template (HTMX partial) | request-response | `templates/partials/jes_scores.html` | exact |
| `app/main.py` (modification) | config/router mount | — | `app/main.py` lines 109, 161–181 | exact |

---

## Pattern Assignments

### `app/services/export_service.py` (service, request-response + file-I/O)

**Analog:** `app/services/jes_service.py`

**Imports pattern** (jes_service.py lines 15–32):
```python
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from app.config import settings
from app.db import get_connection
from app.models.work_description import WorkDescription
from app.services.wd_store import load_work_description, save_work_description

logger = logging.getLogger(__name__)
```

**Stage gate validation pattern** (jes_service.py lines 141–156):
```python
wd: WorkDescription | None = await asyncio.to_thread(
    lambda: load_work_description(conn, wd_id)
)
if wd is None:
    raise ValueError(f"WorkDescription {wd_id!r} not found")
if wd.stage != "jes_scored":
    raise ValueError(
        f"WorkDescription is in stage {wd.stage!r}, expected 'jes_scored'"
    )
```

**Pre-export validation pattern** — new to Phase 8, modeled on jes_service sentinel logic (jes_service.py lines 76–86):
```python
# Blocking condition: any factor with level == -1 or points is None
failed_factors = [
    s.factor_name for s in wd.jes_scores
    if s.level == -1 or s.points is None
]
if failed_factors:
    raise ValueError(
        f"Export blocked — incomplete JES factors: {', '.join(failed_factors)}. "
        "Return to JES scoring step to resolve."
    )
```

**asyncio.to_thread for SQLite** (jes_service.py lines 141–143):
```python
conn = await asyncio.to_thread(lambda: get_connection(db_path))
# ... all SQLite ops wrapped:
wd = await asyncio.to_thread(lambda: load_work_description(conn, wd_id))
await asyncio.to_thread(lambda: save_work_description(conn, updated_wd))
```

**Stage advancement after confirmed success** (jes_service.py lines 231–238):
```python
updated_wd = wd.model_copy(
    update={
        "stage": "exported",
        "export_hash": sha256_hex,       # SHA-256 of file bytes
        "exported_at": datetime.utcnow(),
    }
)
await asyncio.to_thread(lambda: save_work_description(conn, updated_wd))
```

**Connection cleanup** (jes_service.py lines 247–248):
```python
finally:
    await asyncio.to_thread(conn.close)
```

**Return dict shape** (jes_service.py lines 240–245):
```python
return {
    "wd_id": str(wd.id),
    "file_bytes": bytes_value,       # for streaming in router
    "filename": "work_description.docx",
    "export_hash": sha256_hex,
}
```

**ProvenanceTag fields used for version manifest** (work_description.py lines 16–40 + 130):
```python
# Collect all unique source documents from every element bearing a ProvenanceTag
# Sources to walk: confirmed_noc.provenance, og_recommendation.provenance,
#   confirmed_og.cited_articles (list[ProvenanceTag]), each DraftDuty.provenance,
#   each JESFactorScore.provenance, organizational_context.provenance
# Deduplicate on (source_type, source_id, source_version)
# Each ProvenanceTag has: source_type, source_id, source_version, retrieved_date
```

---

### `app/api/export.py` (router, request-response + file-I/O)

**Analog:** `app/api/jes_scoring.py`

**Module docstring + imports pattern** (jes_scoring.py lines 1–18):
```python
"""
app/api/export.py — FastAPI router for DOCX export (Phase 8).

GET /export/{wd_id}/docx — generate and stream DOCX for a completed WorkDescription.
  Requires stage='jes_scored'. Returns file download or HTMX partial.
GET /export/{wd_id}/pdf  — returns 501 Not Implemented (WeasyPrint ARM64 deferred).

Direct analog: app/api/jes_scoring.py
"""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.export_service import generate_export

router = APIRouter()
```

**Templates resolution pattern** (jes_scoring.py lines 21–24):
```python
_templates_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"
)
templates = Jinja2Templates(directory=_templates_dir)
```

**GET route with HTMX dual-path** (jes_scoring.py lines 27–57):
```python
@router.get("/export/{wd_id}/docx")
async def export_docx(request: Request, wd_id: str):
    try:
        result = await generate_export(wd_id=wd_id, db_path=settings.db_path)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=422, detail=msg)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/export_result.html",
            {
                "request": request,
                "wd_id": wd_id,
                "export_hash": result["export_hash"],
                "filename": result["filename"],
            },
        )
    # Non-HTMX: stream file download
    return Response(
        content=result["file_bytes"],
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'},
    )
```

**501 stub route** (D-08):
```python
@router.get("/export/{wd_id}/pdf")
async def export_pdf(request: Request, wd_id: str):
    raise HTTPException(
        status_code=501,
        detail="PDF export is not yet available — download DOCX and convert locally.",
    )
```

**Router mount in main.py** (main.py lines 105–109):
```python
# Add alongside existing routers:
from app.api import export
app.include_router(export.router)
```

**Wizard route in main.py** (main.py lines 161–181 — wizard_jes as template):
```python
@app.get("/wizard/export", response_class=HTMLResponse)
async def wizard_export(request: Request, wd_id: str = "") -> HTMLResponse:
    import jinja2
    try:
        return wizard_templates.TemplateResponse(
            "wizard/step_export.html", {"request": request, "wd_id": wd_id}
        )
    except jinja2.TemplateNotFound:
        return HTMLResponse(
            "<!DOCTYPE html><html><body>"
            f"<h1>Export Wizard</h1>"
            f"<p>WorkDescription ID: {wd_id or '(none)'}</p>"
            "<p>The full template will be added in Plan 08-XX.</p>"
            "</body></html>"
        )
```

---

### `templates/wizard/step_export.html` (template, wizard step)

**Analog:** `templates/wizard/step_jes.html`

**Full file pattern** (step_jes.html lines 1–22):
```html
{% extends "base.html" %}

{% block title %}Export Work Description — JD Builder{% endblock %}

{% block content %}
<section id="wizard-step">
    <h1>Export Work Description</h1>
    <p>Download the completed Work Description as a DOCX file.</p>

    {# Pre-export validation errors (rendered server-side on page load) #}
    {% if validation_errors %}
    <div id="export-errors" role="alert" class="export-errors">
        <p>Export blocked — resolve the following before downloading:</p>
        <ul>
        {% for err in validation_errors %}
            <li>{{ err }}</li>
        {% endfor %}
        </ul>
    </div>
    {% endif %}

    {# Position + JES summary (static on page load) #}
    ...

    {# Download CTA — HTMX GET triggers file download or partial swap #}
    <a href="/export/{{ wd_id }}/docx"
       class="button button--primary"
       {% if validation_errors %}aria-disabled="true"{% endif %}>
        Download DOCX
    </a>

    <div id="export-result" aria-live="polite"></div>
</section>
{% endblock %}
```

**Hidden wd_id input pattern** (step_jes.html line 15):
```html
<input type="hidden" name="wd_id" value="{{ wd_id }}">
```

**HTMX indicator pattern** (step_jes.html lines 10–17):
```html
hx-indicator="#export-spinner"
hx-disabled-elt="#download-btn"
<span id="export-spinner" class="htmx-indicator" aria-label="Generating DOCX...">Generating...</span>
```

---

### `templates/partials/export_result.html` (template, HTMX partial)

**Analog:** `templates/partials/jes_scores.html`

**Full file pattern** (jes_scores.html lines 1–29):
```html
{# HTMX partial: export confirmation after successful DOCX generation #}
{# Replaces #export-result after GET /export/{wd_id}/docx succeeds (HTMX path) #}
<div id="export-result" role="status">
    <h2>Export Complete</h2>
    <p>Document generated successfully.</p>
    <p class="export-hash muted">SHA-256: <code>{{ export_hash }}</code></p>
    <a href="/export/{{ wd_id }}/docx" class="button button--primary">
        Download DOCX
    </a>
</div>
```

**Error card pattern for per-factor failures** (jes_scores.html lines 8–12):
```html
{# For pre-export validation errors when shown inline #}
<div class="export-error-card {% if blocking %}export-error-card--blocking{% endif %}">
    <p class="export-error-factor">{{ factor_name }}: {{ error_message }}</p>
</div>
```

**Provenance/source citation pattern** (jes_scores.html lines 20–23):
```html
<p class="jes-source muted">
    Source: {{ score.provenance.source_id }} ({{ score.provenance.source_version }})
</p>
```

---

### `.docx` template file for docxtpl

**No direct codebase analog** — new artifact. See `## No Analog Found` section.

---

## Shared Patterns

### asyncio.to_thread for SQLite
**Source:** `app/services/jes_service.py` lines 141–143, 161–163, 238, 247–248
**Apply to:** `app/services/export_service.py` — every SQLite read/write must be wrapped
```python
conn = await asyncio.to_thread(lambda: get_connection(db_path))
wd = await asyncio.to_thread(lambda: load_work_description(conn, wd_id))
await asyncio.to_thread(lambda: save_work_description(conn, updated_wd))
# always in finally:
await asyncio.to_thread(conn.close)
```

### ValueError → HTTPException mapping
**Source:** `app/api/jes_scoring.py` lines 39–45
**Apply to:** `app/api/export.py` — all routes
```python
except ValueError as exc:
    msg = str(exc)
    if "not found" in msg:
        raise HTTPException(status_code=404, detail=msg)
    raise HTTPException(status_code=422, detail=msg)
```

### HTMX dual-path (TemplateResponse vs data response)
**Source:** `app/api/jes_scoring.py` lines 47–57
**Apply to:** `app/api/export.py` — DOCX route returns file bytes for non-HTMX, partial for HTMX
```python
if request.headers.get("HX-Request"):
    return templates.TemplateResponse("partials/export_result.html", {...})
return Response(content=file_bytes, media_type="application/vnd.openxmlformats-...", headers={...})
```

### Templates directory resolution
**Source:** `app/api/jes_scoring.py` lines 21–24
**Apply to:** `app/api/export.py`
```python
_templates_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"
)
templates = Jinja2Templates(directory=_templates_dir)
```

### model_copy for stage advancement
**Source:** `app/services/jes_service.py` lines 231–238
**Apply to:** `app/services/export_service.py` — advance to `"exported"` with export_hash + exported_at
```python
updated_wd = wd.model_copy(update={"stage": "exported", "export_hash": ..., "exported_at": ...})
await asyncio.to_thread(lambda: save_work_description(conn, updated_wd))
```

### ProvenanceTag fields available for version manifest
**Source:** `app/models/work_description.py` lines 16–40
**Apply to:** `app/services/export_service.py` — collect all unique `(source_type, source_id, source_version, retrieved_date)` tuples from every element in the WorkDescription
```python
# Fields on ProvenanceTag: source_type, source_id, source_version, source_url, retrieved_date
# Advisor content marker: source_type == "ADVISOR" or DraftDuty.advisor_modified == True
```

### Wizard TemplateNotFound fallback + route
**Source:** `app/main.py` lines 161–181
**Apply to:** new `/wizard/export` route in `app/main.py`
```python
@app.get("/wizard/export", response_class=HTMLResponse)
async def wizard_export(request: Request, wd_id: str = "") -> HTMLResponse:
    import jinja2
    try:
        return wizard_templates.TemplateResponse(
            "wizard/step_export.html", {"request": request, "wd_id": wd_id}
        )
    except jinja2.TemplateNotFound:
        return HTMLResponse("...")
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `templates/docx/work_description_template.docx` | docxtpl template | file-I/O | No .docx templates exist in the codebase. docxtpl (v0.18.0) and python-docx (v1.1.2) are already in requirements.txt. Planner should use TBS WD format from `data/directive_on_classification.txt` + docxtpl Jinja2 variable substitution syntax. Key variables: `{{ position_title }}`, `{{ og_level }}`, `{{ draft_duties }}` (loop), `{{ jes_scores }}` (loop), version manifest table. Advisor-added content needs distinct inline style (italics + label per D-06). |

---

## Metadata

**Analog search scope:** `app/services/`, `app/api/`, `templates/wizard/`, `templates/partials/`, `app/main.py`, `app/models/`
**Files scanned:** 9
**Pattern extraction date:** 2026-06-02
