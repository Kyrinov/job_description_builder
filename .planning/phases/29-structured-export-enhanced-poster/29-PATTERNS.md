# Phase 29: Structured Export + Enhanced Poster — Pattern Map

**Mapped:** 2026-06-24
**Files analyzed:** 6
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `v2/backend/app/api/export.py` | route handler | request-response | `v2/backend/app/api/export.py` (existing routes) | exact — add 2 handlers to the same file |
| `v2/backend/app/services/export_service.py` | service | transform | `v2/backend/app/services/export_service.py` (`_build_poster_context`) | exact — extend the existing function |
| `v2/frontend/src/app.jsx` | client logic | request-response | `v2/frontend/src/app.jsx` (`exportAs()` lines 614-677) | exact — extend existing function |
| `v2/frontend/src/conversation.jsx` | component | event-driven | `v2/frontend/src/conversation.jsx` (`ReviewState` lines 243-255) | exact — append buttons to existing `.export-row` |
| `v2/backend/scripts/build_poster_template.py` | script | transform | `v2/backend/scripts/build_poster_template.py` (existing `build()`) | exact — insert section + update `required` set |
| `v2/backend/tests/test_export.py` | test | CRUD | `v2/backend/tests/test_export.py` (existing integration tests) | exact — same fixture helpers and assert shapes |

---

## Pattern Assignments

### `v2/backend/app/api/export.py` — Add JSON and CSV route handlers

**Analog:** `v2/backend/app/api/export.py` — existing `export_poster()` and `export_wd_docx()` handlers

**Imports already at top of file** (lines 9-28) — no new imports needed for the two new routes. Add `json`, `csv`, `io` from stdlib:

```python
# Add to existing import block:
import csv
import io
import json
# build_seven_elements must be added to the existing import from export_service:
from app.services.export_service import (
    _og_code_from,
    _og_level_str,
    _probe_weasyprint,
    _slugify_title,
    build_seven_elements,          # Phase 29 addition
    generate_poster_docx,
    generate_wd_docx,
)
```

**Core route pattern — existing poster route** (lines 95-106):

```python
@router.post("/wd/{wd_id}/export/poster")
async def export_poster(wd_id: str) -> Response:
    """EXP-02 / API-09 — Export job poster DOCX with bilingual headers."""
    settings = get_settings()
    wd = _load_wd(wd_id, settings.db_path)
    require_og_confirmed(wd)                          # <-- JSON/CSV routes OMIT this line
    result = await generate_poster_docx(wd_id=wd_id, db_path=settings.db_path)
    return Response(
        content=result["file_bytes"],
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'},
    )
```

**New JSON route — copy poster pattern, omit `require_og_confirmed`:**

```python
@router.post("/wd/{wd_id}/export/json")
async def export_wd_json(wd_id: str) -> Response:
    """SEXP-01 — Export 7-element analytics JSON."""
    settings = get_settings()
    wd = _load_wd(wd_id, settings.db_path)
    # NO require_og_confirmed — manager-track WDs must succeed (SEXP-04)
    payload = _build_json_export(wd)
    safe_title = _slugify_title((wd.record or {}).get("title", ""), "work-description")
    filename = f"{safe_title}.json"
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

**New CSV route — same skeleton, different serializer:**

```python
@router.post("/wd/{wd_id}/export/csv")
async def export_wd_csv(wd_id: str) -> Response:
    """SEXP-02 — Export 7-element analytics CSV (UTF-8-BOM for Excel)."""
    settings = get_settings()
    wd = _load_wd(wd_id, settings.db_path)
    # NO require_og_confirmed — manager-track WDs must succeed (SEXP-04)
    csv_bytes = _build_csv_export(wd)
    safe_title = _slugify_title((wd.record or {}).get("title", ""), "work-description")
    filename = f"{safe_title}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

**`_load_wd` helper** (lines 37-52) — already present, reused unchanged by both new routes:

```python
def _load_wd(wd_id: str, db_path: str) -> WorkDescription:
    con = get_connection(db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Work description not found")
        return WorkDescription.model_validate_json(row["data"])
    finally:
        con.close()
```

**`_build_json_export` private helper — add before the new route:**

```python
_MANAGER_PLACEHOLDER = "[ADVISOR TO COMPLETE]"

def _build_json_export(wd: WorkDescription) -> dict:
    """Build 7-element analytics JSON for SEXP-01."""
    seven = build_seven_elements(wd)
    elements = {e["key"]: e for e in seven["elements"]}
    og_code = _og_code_from(wd)
    og_level_str = _og_level_str(og_code, wd.og_level or 0) if og_code else None

    return {
        "organizational_context": elements["organizational_context"]["value"] or None,
        "client_service_results": elements["client_service_results"]["value"] or None,
        "key_activities": [
            {"text": d.text, "noc_code": d.provenance_noc_code or None}
            for d in (elements["key_activities"]["value"] or [])
        ],
        "skills": None,
        "effort": None,
        "responsibility": elements["responsibility"]["value"] or None,
        "working_conditions": None,
        "element_status": {e["key"]: e["status"] for e in seven["elements"]},
        "complete_count": seven["complete_count"],
        "total": seven["total"],
        "classification": {
            "og_level": og_level_str or _MANAGER_PLACEHOLDER,
            "jes_total_points": wd.jes_total_points if wd.jes_total_points is not None else _MANAGER_PLACEHOLDER,
            "og_name": (wd.confirmed_og.get("og_name", "") if isinstance(wd.confirmed_og, dict) else "") or _MANAGER_PLACEHOLDER,
        },
        "provenance": _build_v2_manifest(wd),
        "wd_type": getattr(wd, "wd_type", "advisor"),
        "export_date": str(date.today()),
    }
```

Add `from datetime import date` to the import block (check if already present — `export_service.py` imports it, but `export.py` may not).

**`_build_csv_export` private helper — add before the CSV route:**

```python
def _build_csv_export(wd: WorkDescription) -> bytes:
    """Build UTF-8-with-BOM CSV; one row per key activity (duty). SEXP-02."""
    seven = build_seven_elements(wd)
    elements = {e["key"]: e for e in seven["elements"]}

    buf = io.StringIO()
    fieldnames = [
        "duty_text", "duty_noc_code",
        "organizational_context", "client_service_results",
        "skills_status", "effort_status", "responsibility",
        "working_conditions_status",
        "og_level", "jes_total_points", "complete_count", "total",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()

    og_code = _og_code_from(wd)
    og_level_str = _og_level_str(og_code, wd.og_level or 0) if og_code else None
    scalar = {
        "organizational_context": elements["organizational_context"]["value"] or _MANAGER_PLACEHOLDER,
        "client_service_results": elements["client_service_results"]["value"] or _MANAGER_PLACEHOLDER,
        "skills_status": elements["skills"]["status"],
        "effort_status": elements["effort"]["status"],
        "responsibility": elements["responsibility"]["value"] or _MANAGER_PLACEHOLDER,
        "working_conditions_status": elements["working_conditions"]["status"],
        "og_level": og_level_str or _MANAGER_PLACEHOLDER,
        "jes_total_points": str(wd.jes_total_points) if wd.jes_total_points is not None else _MANAGER_PLACEHOLDER,
        "complete_count": seven["complete_count"],
        "total": seven["total"],
    }
    duties = elements["key_activities"]["value"] or []
    if duties:
        for d in duties:
            writer.writerow({**scalar, "duty_text": d.text, "duty_noc_code": d.provenance_noc_code or ""})
    else:
        writer.writerow({**scalar, "duty_text": _MANAGER_PLACEHOLDER, "duty_noc_code": ""})

    # encode("utf-8-sig") prepends the BOM — Excel auto-detects UTF-8
    return buf.getvalue().encode("utf-8-sig")
```

**Critical:** `d.text` and `d.provenance_noc_code` are attribute access, NOT dict subscript. `elements["key_activities"]["value"]` returns `list[DraftDuty]` objects.

---

### `v2/backend/app/services/export_service.py` — Extend `_build_poster_context` and verify `build_seven_elements` import

**Analog:** `v2/backend/app/services/export_service.py` — `_build_poster_context()` lines 538-565

**Current `_build_poster_context` return dict** (lines 556-565):

```python
return {
    "position_title": record.get("title", ""),
    "og_level": og_level_str,
    "og_name": (wd.confirmed_og.get("og_name", "") if isinstance(wd.confirmed_og, dict) else ""),
    "branch": record.get("branch", ""),
    "education": education_text,
    "experience": experience_text,
    "duties": [{"text": d.text} for d in (wd.duties or [])[:5]],
    "bilingual_title_fr": "",
}
```

**Add `org_context` key** — append to the dict before the closing brace:

```python
    "org_context": (wd.org_context or "").strip() or "[To be provided / À fournir]",
```

**`build_seven_elements` is already defined in this file** (line 425) — no import change needed. The function is already exported for Phase 29 use; `export.py` must add it to its import list (see export.py section above).

---

### `v2/frontend/src/app.jsx` — Extend `exportAs()` with JSON and CSV kinds

**Analog:** `v2/frontend/src/app.jsx` — `exportAs()` function lines 614-677

**Existing OG guard** (line 625 — must be extended):

```javascript
// CURRENT (line 625):
if (userRole !== 'manager' && (!record.confirmed_og || !record.og_level)) {

// PHASE 29 — extend to skip guard for json and csv kinds:
if (userRole !== 'manager' && kind !== 'json' && kind !== 'csv'
    && (!record.confirmed_og || !record.og_level)) {
```

**Existing endpoint dispatch** (lines 630-635 — must be extended):

```javascript
// CURRENT:
const isPdf = kind === 'PDF';
const endpoint = isPdf
  ? `/api/wd/${wd_id}/export/pdf`
  : `/api/wd/${wd_id}/export/docx`;
const ext = isPdf ? 'pdf' : 'docx';

// PHASE 29 — replace the two-branch dispatch with a four-branch dispatch:
let endpoint, ext;
if (kind === 'PDF') {
  endpoint = `/api/wd/${wd_id}/export/pdf`; ext = 'pdf';
} else if (kind === 'json') {
  endpoint = `/api/wd/${wd_id}/export/json`; ext = 'json';
} else if (kind === 'csv') {
  endpoint = `/api/wd/${wd_id}/export/csv`; ext = 'csv';
} else {
  endpoint = `/api/wd/${wd_id}/export/docx`; ext = 'docx';
}
```

**Filename construction** (line 635) — unchanged; already handles all extensions:

```javascript
const filename = `${(record.title || 'work-description').toLowerCase().replace(/\s+/g, '-')}.${ext}`;
```

**Fetch + Blob pattern** (lines 637-676) — unchanged; MIME-agnostic, works for JSON and CSV:

```javascript
const resp = await fetch(endpoint, { method: 'POST' });
// ... error handling unchanged ...
const blob = await resp.blob();
const href = URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = href;
a.download = filename;
document.body.appendChild(a);
a.click();
document.body.removeChild(a);
setTimeout(() => URL.revokeObjectURL(href), 0);
```

**Toast copy — update success toast** for the two new kinds. The existing toast fires after `a.click()`. Add kind-specific copy before the existing success path:

```javascript
// After a.click():
const successMsg = kind === 'json'
  ? 'Structured data downloaded (JSON)'
  : kind === 'csv'
    ? 'Structured data downloaded (CSV)'
    : `${ext.toUpperCase()} exported`;
setToast(successMsg);
setTimeout(() => setToast(null), 2600);
```

**Error toast copy** — existing pattern at line 660 is `Export failed — ${detail}`. Per UI-SPEC, JSON/CSV use `JSON export failed — {detail}. Try again or contact support.` and `CSV export failed — {detail}. Try again or contact support.`. Adjust the error message assembly:

```javascript
const kindLabel = kind === 'json' ? 'JSON' : kind === 'csv' ? 'CSV' : 'Export';
setToast(`${kindLabel} export failed — ${detail}. Try again or contact support.`);
```

---

### `v2/frontend/src/conversation.jsx` — Add Export JSON + CSV buttons to `ReviewState`

**Analog:** `v2/frontend/src/conversation.jsx` — `ReviewState` `.export-row` block lines 243-255

**Existing `.export-row` block** (lines 243-255):

```jsx
<div className="export-row">
  <button className="btn--export" onClick={() => onExport('Word document (.docx)')}>
    <Icon path='<rect x="3" y="2.5" width="14" height="15" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M6 7h8M6 10h8M6 13h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>' />
    Export DOCX
  </button>
  <button className="btn--export" onClick={() => onExport('PDF')}>
    <Icon path='<rect x="3" y="2.5" width="14" height="15" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M6.5 13v-3.5h1.2a1.1 1.1 0 010 2.2H6.5M11 9.5V13M11 9.5h1.8M11 11.4h1.4" stroke="currentColor" stroke-width="1.3" fill="none" stroke-linecap="round"/>' />
    Export PDF
  </button>
  <button className="btn--export" onClick={() => onExport('clipboard')}>
    <Icon path='<rect x="6" y="3" width="11" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M3.5 6v9.5A1.5 1.5 0 005 17h8" fill="none" stroke="currentColor" stroke-width="1.6"/>' />
    Copy
  </button>
  {/* Phase 29 additions — append after Copy, before closing </div> */}
  <button className="btn--export" onClick={() => onExport('json')}>
    <Icon path='<text x="2" y="14" font-size="12" font-family="monospace" fill="currentColor">{}</text>' />
    Export JSON
  </button>
  <button className="btn--export" onClick={() => onExport('csv')}>
    <Icon path='<rect x="3" y="5" width="14" height="10" rx="1" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M3 9h14M9 5v10" stroke="currentColor" stroke-width="1.4"/>' />
    Export CSV
  </button>
</div>
```

**`Icon` component** — existing helper in `components.jsx`. All existing buttons use it with an inline SVG path string. Match the same `path=` prop signature exactly.

**No `userRole` gate** on JSON/CSV buttons — both are visible to managers and advisors per UI-SPEC.

**`ReviewState` function signature** (line 187) — unchanged; `onExport` prop already wired:

```jsx
function ReviewState({ record, cls, onExport, onRestart, amendmentNotes = {},
                       auditFindings = [], auditRunning = false, auditRan = false,
                       onRunAudit, onAuditDecide, completeness = null,
                       userRole = 'advisor' }) {
```

---

### `v2/backend/scripts/build_poster_template.py` — Add "About the Organization" section

**Analog:** `v2/backend/scripts/build_poster_template.py` — existing section blocks lines 67-87

**Existing section pattern** (lines 83-87 — Branch section):

```python
# ------------------------------------------------------------------
# Branch / Direction
# ------------------------------------------------------------------
branch_head = doc.add_paragraph()
branch_run = branch_head.add_run("Branch / Direction:")
branch_run.bold = True
doc.add_paragraph("{{ branch }}")
```

**New "About the Organization" section — insert AFTER the Branch block (line 87) and BEFORE the `# Key Duties` heading:**

```python
# ------------------------------------------------------------------
# About the Organization / À propos de l'organisation
# ------------------------------------------------------------------
org_head = doc.add_paragraph()
org_run = org_head.add_run("About the Organization / À propos de l'organisation:")
org_run.bold = True
doc.add_paragraph("{{ org_context }}")
```

**Update `required` set** (lines 137-141) — add `"org_context"`:

```python
# CURRENT:
required = {
    "position_title", "bilingual_title_fr",
    "og_level", "og_name", "branch",
    "duties", "education_text", "experience_text",
}

# PHASE 29 — add org_context:
required = {
    "position_title", "bilingual_title_fr",
    "og_level", "og_name", "branch",
    "duties", "education_text", "experience_text",
    "org_context",
}
```

**Also update the module docstring** (line 22 — `Jinja2 variables` block) to include `org_context`.

**Run from repo root after editing:**

```
python v2/backend/scripts/build_poster_template.py
```

This regenerates `v2/backend/app/templates/poster_template.docx`. Commit the regenerated binary alongside the script change.

---

### `v2/backend/tests/test_export.py` — Add Wave 0 RED stubs + implementation tests

**Analog:** `v2/backend/tests/test_export.py` — existing integration tests (Phase 28, lines 309-366) and unit tests (Phase 27, lines 770-955)

**Fixture helpers available** — do not redefine, reuse as-is:

| Helper | Line | What it creates |
|--------|------|-----------------|
| `_create_wd(client)` | 22 | Bare WD (title only) |
| `_create_wd_ec(client)` | 94 | EC WD with Effort + Conditions factors |
| `_create_wd_with_jes_scores(client)` | 31 | EC WD with full JES + confirmed_og |
| `_wd_for_seven_elements(**overrides)` | 770 | In-memory WD (no HTTP) |

**Test shape for SEXP-01 — matches existing integration test pattern** (lines 309-328):

```python
async def test_export_json_returns_all_seven_keys(client, env_with_db):
    """SEXP-01 — POST /api/wd/{id}/export/json returns all 7 Part 2 element keys."""
    wd_id = await _create_wd_ec(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/json")
    assert resp.status_code == 200
    data = resp.json()
    for key in ("organizational_context", "client_service_results", "key_activities",
                "skills", "effort", "responsibility", "working_conditions"):
        assert key in data, f"Missing key: {key}"
```

**Test shape for SEXP-01 metadata:**

```python
async def test_export_json_metadata_and_provenance(client, env_with_db):
    """SEXP-01 — JSON export includes classification metadata + provenance list."""
    wd_id = await _create_wd_ec(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/json")
    assert resp.status_code == 200
    data = resp.json()
    assert "classification" in data
    assert "provenance" in data
    assert isinstance(data["provenance"], list)
    assert "export_date" in data
```

**Test shape for SEXP-04 — manager bypass** (mirrors MGR-03 at lines 309-328):

```python
async def test_export_json_manager_no_409(client, env_with_db):
    """SEXP-04 — manager-track WD exports JSON without 409."""
    wd_id = await _create_wd(client)
    await client.patch(f"/api/wd/{wd_id}", json={"wd_type": "manager"})
    resp = await client.post(f"/api/wd/{wd_id}/export/json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["classification"]["og_level"] == "[ADVISOR TO COMPLETE]"
```

**Test shape for SEXP-02 — CSV:**

```python
async def test_export_csv_utf8_bom_one_row_per_duty(client, env_with_db):
    """SEXP-02 — POST /api/wd/{id}/export/csv returns UTF-8-BOM CSV, one row per duty."""
    wd_id = await _create_wd_ec(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/csv")
    assert resp.status_code == 200
    # UTF-8-BOM: first 3 bytes are \xef\xbb\xbf
    assert resp.content[:3] == b"\xef\xbb\xbf", "Missing UTF-8 BOM"
    # Decode and count rows (header + 1 per duty; _create_wd_ec seeds 1 duty)
    import csv, io
    text = resp.content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    assert len(rows) == 1
    assert "duty_text" in rows[0]
```

**Test shape for POST-01 — poster org_context:**

```python
async def test_poster_org_context_section(client, env_with_db):
    """POST-01 — Poster DOCX contains 'About the Organization' section when org_context set."""
    wd_id = await _create_wd_with_jes_scores(client)
    await client.patch(f"/api/wd/{wd_id}", json={"org_context": "We are the Department of Test."})
    resp = await client.post(f"/api/wd/{wd_id}/export/poster")
    assert resp.status_code == 200
    import docx, io
    doc = docx.Document(io.BytesIO(resp.content))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "About the Organization" in text
    assert "We are the Department of Test." in text
```

**Wave 0 stub shape** (use `pytest.mark.xfail` or a simple `assert False` with a comment, matching the project's existing RED-baseline approach — the project uses plain async tests with no skip marker; use `pytest.mark.xfail(strict=True, reason="Wave 0 RED stub")`):

```python
@pytest.mark.xfail(strict=True, reason="Wave 0 RED stub — export/json route not yet implemented")
async def test_export_json_returns_all_seven_keys(client, env_with_db):
    ...
```

---

### `v2/frontend/src/styles.css` — No changes required

**Analog:** `v2/frontend/src/styles.css` lines 832-840

**Existing `.btn--export` class is complete** (lines 833-839):

```css
.export-row { display: flex; gap: 10px; margin-top: 26px; flex-wrap: wrap; }
.btn--export {
  border: 1.5px solid var(--line); background: var(--panel); color: var(--ink); font-weight: 620;
  padding: 12px 18px; border-radius: 11px; display: inline-flex; align-items: center; gap: 9px;
  transition: all 0.15s;
}
.btn--export:hover { border-color: var(--accent-line); background: var(--accent-soft); color: var(--accent-deep); transform: translateY(-1px); }
.btn--export svg { width: 17px; height: 17px; }
```

The JSON and CSV buttons use `className="btn--export"` — the class already handles all styling, hover state, icon sizing (17px), and flex layout. No CSS changes needed.

---

## Shared Patterns

### 404 Guard (`_load_wd`)

**Source:** `v2/backend/app/api/export.py` lines 37-52
**Apply to:** Both new route handlers (JSON + CSV)

```python
def _load_wd(wd_id: str, db_path: str) -> WorkDescription:
    con = get_connection(db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Work description not found")
        return WorkDescription.model_validate_json(row["data"])
    finally:
        con.close()
```

Already in `export.py`. Both new routes call it identically — `_load_wd(wd_id, settings.db_path)`.

### OG Guard Bypass (Critical)

**Source:** `v2/backend/app/services/classification_gate.py` + `v2/backend/tests/test_export.py` lines 309-328
**Apply to:** JSON route, CSV route (both skip `require_og_confirmed`)

```python
# DOCX/PDF/Poster routes: call require_og_confirmed(wd)
# JSON/CSV routes: DO NOT call require_og_confirmed(wd)
# This is intentional — SEXP-04 requires 200 for manager-track WDs without confirmed_og
```

### FastAPI `Response` with `Content-Disposition`

**Source:** `v2/backend/app/api/export.py` lines 88-92 (DOCX handler)
**Apply to:** Both new route handlers

```python
return Response(
    content=<bytes>,
    media_type="application/json",          # or "text/csv; charset=utf-8"
    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
)
```

### `_slugify_title` for filenames

**Source:** `v2/backend/app/services/export_service.py` line 600
**Apply to:** Both new route handlers — same filename slug as DOCX/PDF routes

```python
safe_title = _slugify_title((wd.record or {}).get("title", ""), "work-description")
filename = f"{safe_title}.json"   # or .csv
```

### Blob Download (Frontend)

**Source:** `v2/frontend/src/app.jsx` lines 664-672
**Apply to:** `exportAs()` extension — already present, no changes to the download block

```javascript
const blob = await resp.blob();
const href = URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = href;
a.download = filename;
document.body.appendChild(a);
a.click();
document.body.removeChild(a);
setTimeout(() => URL.revokeObjectURL(href), 0);
```

### `_og_code_from` + `_og_level_str` for classification metadata

**Source:** `v2/backend/app/services/export_service.py` lines 148-158, 595-597
**Apply to:** `_build_json_export` and `_build_csv_export` private helpers in `export.py`

```python
og_code = _og_code_from(wd)    # tolerates str or dict shape of confirmed_og
og_level_str = _og_level_str(og_code, wd.og_level or 0) if og_code else None
# og_level_str is "" when og_code is ""; use `or _MANAGER_PLACEHOLDER` to fill
```

### Poster Section Pattern

**Source:** `v2/backend/scripts/build_poster_template.py` lines 83-87
**Apply to:** New "About the Organization" section in `build_poster_template.py`

```python
section_head = doc.add_paragraph()
section_run = section_head.add_run("Heading / Titre bilingue:")
section_run.bold = True
doc.add_paragraph("{{ jinja2_var }}")
```

---

## No Analog Found

All files have exact or near-exact analogs in the codebase. No entries.

---

## Metadata

**Analog search scope:** `v2/backend/app/api/`, `v2/backend/app/services/`, `v2/backend/scripts/`, `v2/backend/tests/`, `v2/frontend/src/`
**Files scanned:** 10 (export.py, export_service.py, test_export.py, app.jsx, conversation.jsx, styles.css, build_poster_template.py, classification_gate.py, conftest.py, components.jsx)
**Pattern extraction date:** 2026-06-24
