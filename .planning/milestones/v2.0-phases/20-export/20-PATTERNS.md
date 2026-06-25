# Phase 20: Export - Pattern Map

**Mapped:** 2026-06-09
**Files analyzed:** 8
**Analogs found:** 7 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `v2/backend/app/api/export.py` | router | request-response (file I/O) | `v2/backend/app/api/jes_scoring.py` | role-match |
| `v2/backend/app/services/export_service.py` | service | file I/O + CRUD | `app/services/export_service.py` (v1.0) | exact (adapted) |
| `v2/backend/scripts/build_wd_template.py` | utility/script | file I/O | `scripts/build_docx_template.py` (v1.0) | exact (adapted) |
| `v2/backend/scripts/build_poster_template.py` | utility/script | file I/O | `scripts/build_docx_template.py` (v1.0) | role-match |
| `v2/backend/app/templates/wd_template.docx` | binary artifact | file I/O | `templates/docx/work_description_template.docx` (v1.0) | exact (adapted) |
| `v2/backend/app/templates/poster_template.docx` | binary artifact | file I/O | `templates/docx/work_description_template.docx` (v1.0) | role-match |
| `v2/backend/app/api/__init__.py` | config | — | `v2/backend/app/api/__init__.py` (current) | exact (additive edit) |
| `v2/backend/tests/test_export.py` | test | request-response | `v2/backend/tests/test_amendments.py` | exact |
| `v2/frontend/src/app.jsx` (modify) | component/hook | request-response | self (current exportAs stub) | exact (replace stub) |

---

## Pattern Assignments

### `v2/backend/app/api/export.py` (router, request-response + file I/O)

**Analog:** `v2/backend/app/api/jes_scoring.py`

**Imports pattern** (jes_scoring.py lines 14–30):
```python
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.config import get_settings
from app.db import get_connection
from app.models.work_description import WorkDescription
from app.services.classification_gate import require_og_confirmed
from app.services.export_service import generate_wd_docx, generate_poster_docx
```

**Router declaration** (jes_scoring.py line 31):
```python
router = APIRouter()
```

**DOCX endpoint pattern** — adapted from jes_scoring.py lines 94–146 + research Pattern 1:
```python
@router.post("/wd/{wd_id}/export/docx")
async def export_wd_docx(wd_id: str) -> Response:
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Work description not found")
        wd = WorkDescription.model_validate_json(row["data"])
    finally:
        con.close()

    require_og_confirmed(wd)
    if wd.jes_total_points is None:
        raise HTTPException(status_code=422, detail="JES scoring incomplete — export blocked")

    result = await generate_wd_docx(wd_id=wd_id, db_path=settings.db_path)
    return Response(
        content=result["file_bytes"],
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'},
    )
```

**WeasyPrint 501 gate pattern** — research Pattern 3 (no direct codebase analog; use as-is):
```python
@router.post("/wd/{wd_id}/export/pdf")
async def export_pdf(wd_id: str):
    try:
        import weasyprint  # noqa: F401 — import probe only
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="PDF export unavailable — WeasyPrint not installed. "
                   "Install with: pip install weasyprint==69.0",
        )
    try:
        import weasyprint as _wp
        _wp.HTML(string="<p>x</p>").write_pdf()
    except Exception as exc:
        raise HTTPException(
            status_code=501,
            detail=f"PDF export unavailable — system lib error: {exc}",
        )
    # ... render actual PDF
```

**Note:** amendments.py lines 35–61 show the 404-guard pattern (`SELECT id FROM work_descriptions WHERE id = ?`) — use the same guard before calling the export service.

---

### `v2/backend/app/services/export_service.py` (service, file I/O + CRUD)

**Analog:** `app/services/export_service.py` (v1.0)

**Imports pattern** (v1.0 export_service.py lines 1–36):
```python
from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import os
from datetime import date, datetime

from docxtpl import DocxTemplate

from app.config import get_settings
from app.db import get_connection
from app.models.work_description import WorkDescription

logger = logging.getLogger(__name__)
```

**asyncio.to_thread render pattern** (v1.0 export_service.py lines 304–311):
```python
def _render() -> bytes:
    doc = DocxTemplate(template_path)
    doc.render(context)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

file_bytes = await asyncio.to_thread(_render)
```

**Template path resolution** (v1.0 export_service.py lines 244–256) — adapt for v2 layout:
```python
def _resolve_template_path(template_name: str) -> str:
    """Locate committed docxtpl template at app/templates/{template_name}."""
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)),  # app/
        "templates",
        template_name,
    )
```

**Context build — v2.0 field mapping** (v1.0 export_service.py lines 159–241 as structural reference; v2 fields differ — use mapping table from RESEARCH.md):
```python
def _build_wd_context(wd: WorkDescription, amendments: list[dict]) -> dict:
    og_code = (wd.confirmed_og or {}).get("og_code", "")
    og_level_int = wd.og_level or 0
    return {
        "position_title": wd.record.get("title", ""),
        "position_number": wd.record.get("position_number", ""),
        "og_level": f"{og_code}-{int(og_level_int):02d}" if og_code else "",
        "supervisor_title": wd.record.get("reports", ""),
        "supervisor_position_number": "",   # not captured in v2 conversation
        "review_date": str(date.today()),
        "organizational_context_text": _build_org_context(wd),
        "organizational_context_source": "Drafted from answers",
        "duties": [
            {
                "text": d.text,
                "noc_code": d.provenance_noc_code or "",
                "is_advisor": bool(d.advisor),
            }
            for d in (wd.duties or [])
        ],
        "jes_scores": wd.jes_scores or [],   # already list[dict]
        "jes_total_points": wd.jes_total_points or 0,
        "manifest": _build_v2_manifest(wd),
        "amendments": amendments,
    }
```

**CRITICAL: v2.0 model field differences from v1.0** (RESEARCH.md pitfalls section):
- No `wd.stage` field — use `require_og_confirmed(wd)` gate
- No `wd.draft_duties`, `wd.advisor_additions` — use `wd.duties` (list of `DraftDuty`)
- No `d.provenance` sub-object — use `d.provenance_noc_code`, `d.provenance_hash`, `d.advisor` flat fields
- No `wd.og_recommendation.provenance` — use `wd.confirmed_og` dict with `og_code`/`og_name`
- `wd.jes_scores` is already `list[dict]` (not model objects)
- `og_level` must be zero-padded: `f"{og_code}-{int(og_level):02d}"`

**Amendment query pattern** (amendments.py lines 64–87):
```python
def _get_amendments(con, wd_id: str) -> list[dict]:
    rows = con.execute(
        "SELECT detail, created_at FROM audit_log "
        "WHERE wd_id = ? AND event = 'manager_amendment' "
        "ORDER BY id DESC",
        (wd_id,),
    ).fetchall()
    seen: set[str] = set()
    notes = []
    for row in rows:
        detail = json.loads(row["detail"])
        section = detail.get("section")
        if section and section not in seen:
            seen.add(section)
            notes.append({
                "section": section,
                "comment": detail.get("comment", ""),
                "created_at": row["created_at"],
            })
    return notes
```

**Export hash + return dict pattern** (v1.0 export_service.py lines 319–337):
```python
if not file_bytes:
    raise ValueError("Export produced empty document.")

export_hash = hashlib.sha256(file_bytes).hexdigest()

return {
    "wd_id": wd_id,
    "file_bytes": file_bytes,
    "filename": f"{safe_title}.docx",
    "export_hash": export_hash,
}
```

---

### `v2/backend/scripts/build_wd_template.py` (script, file I/O)

**Analog:** `scripts/build_docx_template.py` (v1.0) — copy structure, adapt variables

**Imports and output path pattern** (v1.0 build_docx_template.py lines 33–43):
```python
from __future__ import annotations

import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from docxtpl import DocxTemplate

OUTPUT_PATH = "v2/backend/app/templates/wd_template.docx"
```

**Cell helper pattern** (v1.0 build_docx_template.py lines 45–56) — copy verbatim:
```python
def _set_cell_text(cell, text: str, *, bold: bool = False, italic: bool = False) -> None:
    for para in list(cell.paragraphs):
        p_el = para._p
        p_el.getparent().remove(p_el)
    para = cell.add_paragraph()
    run = para.add_run(text)
    if bold:
        run.bold = True
    if italic:
        run.italic = True
```

**paragraph-level loop pattern** (v1.0 build_docx_template.py lines 103–114) — MUST be in own paragraphs:
```python
doc.add_paragraph("{%p for duty in duties %}")
doc.add_paragraph("{{ duty.text }}")
doc.add_paragraph("{%p if duty.is_advisor %}")
doc.add_paragraph("[advisor-added / not from authoritative source]")
doc.add_paragraph("{%p endif %}")
doc.add_paragraph("{%p endfor %}")
```

**table-row loop pattern** (v1.0 build_docx_template.py lines 126–140) — for/data/endfor in separate rows:
```python
# Row 0: header
# Row 1: {%tr for f in jes_scores %}
_set_cell_text(table.rows[1].cells[0], "{%tr for f in jes_scores %}")
# Row 2: data row (duplicated per iteration)
_set_cell_text(table.rows[2].cells[0], "{{ f.factor_name }}")
# Row 3: {%tr endfor %}
_set_cell_text(table.rows[3].cells[0], "{%tr endfor %}")
```

**Amendment appendix gate pattern** (v1.0 build_docx_template.py lines 176–196 as model):
```python
doc.add_paragraph("{%p if amendments|length > 0 %}")
doc.add_heading("Manager Amendments for Review", level=1)
doc.add_paragraph("Manager-proposed — pending advisor ratification")
# table loop for amendments
doc.add_paragraph("{%p endif %}")
```

**Self-verify pattern** (v1.0 build_docx_template.py lines 203–219):
```python
doc.save(OUTPUT_PATH)
tpl = DocxTemplate(OUTPUT_PATH)
undeclared = sorted(tpl.get_undeclared_template_variables())
print(f"Template variables ({len(undeclared)}): {undeclared}")
required = {"position_title", "duties", "jes_scores", "manifest", "amendments"}
missing = required - set(undeclared)
if missing:
    raise AssertionError(f"Required vars missing from template: {missing}")
```

**v2 template variable contract** (derived from RESEARCH.md mapping table):
- `position_title`, `position_number`, `og_level`, `supervisor_title`, `supervisor_position_number`, `review_date`
- `organizational_context_text`, `organizational_context_source`
- `duties` (list of `{text, noc_code, is_advisor}`)
- `jes_scores` (list of `{factor_name, degree, points, rationale}`)
- `jes_total_points`
- `manifest` (list of `{source_type, source_id, source_version, retrieved_date}`)
- `amendments` (list of `{section, comment, created_at}`)

---

### `v2/backend/scripts/build_poster_template.py` (script, file I/O)

**Analog:** `scripts/build_docx_template.py` (v1.0) — same structure, simpler content

Same `_set_cell_text` helper, same self-verify pattern, same `{%p for %}`/`{%tr for %}` loop pattern as `build_wd_template.py`. Poster variable contract (from RESEARCH.md):
- `position_title`, `og_level`, `og_name`, `branch`
- `education`, `experience`
- `duties` (top 3–5, list of `{text}` only — no noc_code/is_advisor)
- `bilingual_title_fr` (empty placeholder string)

---

### `v2/backend/app/api/__init__.py` (additive edit)

**Analog:** `v2/backend/app/api/__init__.py` (current, lines 1–26)

**Current import line** (line 16):
```python
from . import health, noc_mapping, wd, og_classification, jes_scoring, amendments
```

**After edit** — add `export` to import and `include_router`:
```python
from . import health, noc_mapping, wd, og_classification, jes_scoring, amendments, export

api_router.include_router(export.router)
```

The `__init__.py` docstring (lines 8–10) describes the exact two-step pattern: create the module, import it here, call `include_router`.

---

### `v2/backend/tests/test_export.py` (test, request-response)

**Analog:** `v2/backend/tests/test_amendments.py`

**Module-level marks** (test_amendments.py lines 14):
```python
import pytest

pytestmark = pytest.mark.asyncio
```

**WD creation helper** (test_amendments.py lines 17–23) — copy verbatim:
```python
async def _create_wd(client) -> str:
    resp = await client.post(
        "/api/wd",
        json={"record": {"title": "Test Role"}, "answers": {}, "step_index": 1},
    )
    assert resp.status_code == 201
    return resp.json()["id"]
```

**404 test pattern** (test_amendments.py lines 79–85):
```python
async def test_export_docx_404(client, env_with_db):
    resp = await client.post("/api/wd/does-not-exist/export/docx")
    assert resp.status_code == 404
```

**WD state setup for export tests** — tests need a WD with `confirmed_og` and `jes_total_points` set. Adapt `_create_wd` to also PATCH the WD with required fields before calling export, or use direct DB writes (see test_jes_scoring.py pattern for seeding WD state).

**DOCX bytes assertion pattern**:
```python
async def test_export_wd_docx_returns_bytes(client, env_with_db):
    wd_id = await _create_wd_with_jes_scores(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(resp.content) > 0
```

**501 gate test pattern**:
```python
async def test_export_pdf_501_when_weasyprint_absent(client, env_with_db, monkeypatch):
    """EXP-03 — PDF endpoint returns 501 when WeasyPrint import fails."""
    import sys
    monkeypatch.setitem(sys.modules, "weasyprint", None)
    wd_id = await _create_wd(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/pdf")
    assert resp.status_code == 501
    assert "WeasyPrint" in resp.json()["detail"]
```

**Fixture chain** — all tests use `client` + `env_with_db` from conftest.py (lines 65–93). No conftest changes needed.

---

### `v2/frontend/src/app.jsx` — `exportAs` function (modify, request-response)

**Analog:** Current `exportAs` stub in app.jsx (lines 400–405) + fetch pattern from other handlers

**Current stub** (app.jsx lines 400–405):
```javascript
function exportAs(kind) {
  const msg = kind === 'clipboard' ? 'Job description copied to clipboard'
    : `${record.title || 'Work description'} exported as ${kind}`;
  setToast(msg);
  setTimeout(() => setToast(null), 2600);
}
```

**Replacement pattern** — modelled on `handleJesOverride` (app.jsx lines 418–437) for the fetch call structure, plus Blob download (research Pattern 6):
```javascript
async function exportAs(kind) {
  if (kind === 'clipboard') {
    // existing clipboard logic
    setToast('Job description copied to clipboard');
    setTimeout(() => setToast(null), 2600);
    return;
  }
  if (!wd_id) {
    setToast('Save your work description first before exporting.');
    setTimeout(() => setToast(null), 2600);
    return;
  }
  const endpoint = kind === 'PDF'
    ? `/api/wd/${wd_id}/export/pdf`
    : `/api/wd/${wd_id}/export/docx`;
  const ext = kind === 'PDF' ? 'pdf' : 'docx';
  try {
    const resp = await fetch(endpoint, { method: 'POST' });
    if (resp.status === 501) {
      const data = await resp.json();
      setToast(data.detail || 'PDF export unavailable.');
      setTimeout(() => setToast(null), 4000);
      return;
    }
    if (!resp.ok) {
      setToast('Export failed.');
      setTimeout(() => setToast(null), 2600);
      return;
    }
    const blob = await resp.blob();
    const href = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = href;
    a.download = `${record.title || 'work-description'}.${ext}`;
    a.click();
    URL.revokeObjectURL(href);
  } catch {
    setToast('Export failed.');
    setTimeout(() => setToast(null), 2600);
  }
}
```

**ReviewState call sites** (conversation.jsx lines 147, 151, 155) pass `'Word document (.docx)'`, `'PDF'`, `'clipboard'` — map `'Word document (.docx)'` to the DOCX endpoint in the kind comparison.

---

## Shared Patterns

### WD Load + 404 Guard
**Source:** `v2/backend/app/api/jes_scoring.py` lines 113–124 and `v2/backend/app/api/amendments.py` lines 39–46
**Apply to:** `export.py` router — all three export endpoints
```python
row = con.execute(
    "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
).fetchone()
if row is None:
    raise HTTPException(status_code=404, detail="Work description not found")
wd = WorkDescription.model_validate_json(row["data"])
```

### OG Confirmed Gate
**Source:** `v2/backend/app/api/jes_scoring.py` line 127
**Apply to:** DOCX and poster export endpoints (gate matches jes_scoring pattern)
```python
require_og_confirmed(wd)
```

### Settings Injection (lazy import pattern)
**Source:** `v2/backend/app/api/jes_scoring.py` lines 113–115
**Apply to:** All route handlers in `export.py`
```python
from app.config import get_settings
settings = get_settings()
```

### asyncio.to_thread for CPU-bound sync work
**Source:** `app/services/export_service.py` (v1.0) lines 304–311
**Apply to:** All `DocxTemplate.render()` calls and `weasyprint.HTML().write_pdf()` calls in `export_service.py`

### Connection try/finally
**Source:** `v2/backend/app/api/amendments.py` lines 39–61 and `v2/backend/app/api/jes_scoring.py` lines 114–124
**Apply to:** All DB-touching functions in `export_service.py`
```python
con = get_connection(db_path)
try:
    # ... DB work
finally:
    con.close()
```

### pytest.mark.asyncio module marker
**Source:** `v2/backend/tests/test_amendments.py` line 14
**Apply to:** `tests/test_export.py` — mark entire module
```python
pytestmark = pytest.mark.asyncio
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `v2/backend/app/templates/poster_template.docx` | binary artifact | file I/O | No poster template exists; build script produces it; pattern from `wd_template.docx` applies structurally |

---

## Metadata

**Analog search scope:** `v2/backend/app/api/`, `v2/backend/app/services/`, `v2/backend/tests/`, `app/services/` (v1.0), `scripts/` (v1.0), `v2/frontend/src/`
**Files scanned:** 10
**Pattern extraction date:** 2026-06-09
