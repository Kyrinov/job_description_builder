# Phase 20: Export - Research

**Researched:** 2026-06-09
**Domain:** DOCX export (docxtpl), PDF (WeasyPrint ARM64), FastAPI streaming response
**Confidence:** HIGH

---

## Summary

Phase 20 ports the v1.0 export pattern into v2.0 with three additions: a job poster DOCX template,
a PDF endpoint with an ARM64 feasibility gate, and a manager amendment appendix (AMEND-02 deferred
from Phase 19). The v1.0 `export_service.py` and `build_docx_template.py` transfer directly as
structural references, but the v2.0 `WorkDescription` model differs from v1.0's (no `stage` field,
no `ProvenanceTag` objects — provenance lives as flat fields on `DraftDuty`, not as nested objects).

The export service must reconstruct a context dict from the flat v2.0 model fields. The existing
docxtpl/python-docx stack is already installed in the v2 backend (`docxtpl==0.18.0`,
`python-docx==1.1.2`). WeasyPrint is NOT installed; Pango/Cairo ARM64 system libs ARE present
(`libpango-1.0-0:arm64 1.50.6`, `libcairo2:arm64 1.16.0`) — so WeasyPrint can be pip-installed
on Jane and PDF export is likely feasible, but the 501 fallback gate must test at runtime.

The frontend `ReviewState` component already renders three export buttons (DOCX, PDF, Copy) in
`conversation.jsx`; the `exportAs(kind)` stub in `app.jsx` currently shows a toast but does not
hit any API endpoint — wiring these to real fetch calls is the only frontend work required.
Amendment notes for the DOCX appendix are stored in `audit_log` with `event='manager_amendment'`
and a JSON `detail` field containing `section` and `comment`; the GET `/api/wd/{id}/amendments`
endpoint already retrieves them.

**Primary recommendation:** Build `v2/backend/app/services/export_service.py` modelled on v1.0
but adapted for v2.0's flat model, then register two routers (`/api/wd/{id}/export/docx` and
`/api/wd/{id}/export/poster`) following the `jes_scoring.py` pattern; add WeasyPrint runtime
probe for the `/api/wd/{id}/export/pdf` 501 gate; wire the three frontend buttons to real fetch
calls with `window.open` / `URL.createObjectURL` download triggers.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| DOCX template rendering | API / Backend | — | docxtpl render is CPU-bound, belongs in a worker thread on the backend |
| PDF rendering | API / Backend | — | WeasyPrint is a server-side rendering library |
| Export file delivery | API / Backend | Browser/Client | Backend streams bytes; browser triggers download via Blob URL |
| Template build script | API / Backend | — | `scripts/build_docx_template.py` pattern — committed binary artifact |
| Export button UI | Browser/Client | — | Existing `ReviewState` buttons need real fetch wiring |
| Amendment appendix data source | API / Backend | — | `audit_log` table via existing GET `/api/wd/{id}/amendments` |

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXP-01 | Export completed WD to `.docx` via docxtpl (TBS WD template); provenance citations; version manifest; committed binary artifact with reproducible build script | docxtpl 0.18.0 installed; v1.0 build script pattern directly reusable; v2 model fields mapped below |
| EXP-02 | Job poster DOCX via second docxtpl template; bilingual headers, OG/level, key qualifications, 3–5 duties; POST `/api/wd/{id}/export/poster` | Same docxtpl pattern; poster template needs a new `build_poster_template.py` script |
| EXP-03 | PDF via WeasyPrint with ARM64 gate; 501 if system libs absent | Pango/Cairo ARM64 libs confirmed present; WeasyPrint 69.0 pip-installable; runtime import probe pattern documented |
| API-08 | POST `/api/wd/{id}/export/docx` returns `.docx` file | Follows amendments.py / jes_scoring.py router pattern; asyncio.to_thread for render |
| API-09 | POST `/api/wd/{id}/export/poster` returns `.docx` file | Same pattern as API-08 but different template |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| docxtpl | 0.18.0 | DOCX template rendering with Jinja2 | [VERIFIED: pip list in v2/backend] — already installed; used in v1.0 |
| python-docx | 1.1.2 | DOCX document construction (build script) | [VERIFIED: pip list in v2/backend] — already installed; used in v1.0 build script |
| weasyprint | 69.0 (latest) | HTML→PDF rendering | [VERIFIED: pip index versions weasyprint] — NOT yet installed; system libs present |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio.to_thread | stdlib | Offload CPU-bound render from event loop | All docxtpl and WeasyPrint render calls |
| io.BytesIO | stdlib | In-memory file buffer | Avoids temp files on disk during render |
| hashlib.sha256 | stdlib | Export hash for version manifest | SHA-256 of rendered bytes |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| docxtpl | python-docx only (no templates) | docxtpl's Jinja2 loops handle duties/JES tables cleanly; hand-rolling loops with python-docx is verbose |
| WeasyPrint | LibreOffice headless | LibreOffice is 300 MB+ and not installed; WeasyPrint is pip-installable and sufficient for one-page HTML→PDF |

**Installation (WeasyPrint only — others already installed):**
```bash
pip install weasyprint==69.0
```

---

## Architecture Patterns

### System Architecture Diagram

```
SPA ReviewState                       FastAPI
[Export DOCX btn] ──POST /export/docx──> export_service.generate_wd_docx()
[Export Poster btn] ──POST /export/poster──> export_service.generate_poster_docx()
[Export PDF btn] ──POST /export/pdf──> probe WeasyPrint ──absent──> 501
                                                │
                                                └──present──> render HTML → WeasyPrint → bytes

export_service.generate_wd_docx():
  load WD from SQLite
  query audit_log for manager_amendment rows
  _build_wd_context(wd, amendments) → context dict
  DocxTemplate(template_path).render(context)
  BytesIO → bytes → Response(media_type=.docx)

_build_wd_context():
  position_title, position_number ← record['title'], record.get('position_number')
  og_level ← f"{confirmed_og['og_code']}-{og_level:02d}"
  duties ← [{'text': d.text, 'noc_code': d.provenance_noc_code, 'is_advisor': d.advisor}]
  jes_scores ← wd.jes_scores (already list[dict])
  jes_total_points ← wd.jes_total_points
  manifest ← _build_version_manifest(wd)  # deduped source list
  amendments ← [{'section': ..., 'comment': ...}]  # from audit_log
```

### Recommended Project Structure
```
v2/backend/
├── app/
│   ├── api/
│   │   └── export.py            # new — POST /docx, /poster, /pdf routes
│   ├── services/
│   │   └── export_service.py    # new — generate_wd_docx(), generate_poster_docx(), probe_weasyprint()
│   └── templates/               # new directory
│       ├── wd_template.docx     # committed binary (built by build_wd_template.py)
│       └── poster_template.docx # committed binary (built by build_poster_template.py)
scripts/
├── build_wd_template.py         # new — v2 adaptation of v1.0 build_docx_template.py
└── build_poster_template.py     # new
```

### Pattern 1: DOCX Router (follows jes_scoring.py)
**What:** POST route loads WD, calls service, returns streaming file response
**When to use:** Both WD DOCX and poster DOCX endpoints

```python
# Source: v2/backend/app/api/jes_scoring.py pattern
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from app.config import get_settings
from app.db import get_connection
from app.models.work_description import WorkDescription
from app.services.export_service import generate_wd_docx

router = APIRouter()

@router.post("/wd/{wd_id}/export/docx")
async def export_wd_docx(wd_id: str) -> Response:
    settings = get_settings()
    result = await generate_wd_docx(wd_id=wd_id, db_path=settings.db_path)
    return Response(
        content=result["file_bytes"],
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'},
    )
```

### Pattern 2: asyncio.to_thread for docxtpl render
**What:** Run the synchronous DocxTemplate.render() in a thread pool
**When to use:** All export renders — blocks event loop without this

```python
# Source: v1.0 app/services/export_service.py pattern
import asyncio, io
from docxtpl import DocxTemplate

async def _render_docx(template_path: str, context: dict) -> bytes:
    def _render() -> bytes:
        doc = DocxTemplate(template_path)
        doc.render(context)
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()
    return await asyncio.to_thread(_render)
```

### Pattern 3: WeasyPrint ARM64 runtime probe
**What:** Try-import WeasyPrint at request time; return 501 if unavailable
**When to use:** PDF endpoint — avoids hard dependency at startup

```python
# Source: v1.0 app/api/export.py 501 pattern + EXP-03 requirement
@router.post("/wd/{wd_id}/export/pdf")
async def export_pdf(wd_id: str):
    try:
        import weasyprint
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="PDF export unavailable — WeasyPrint not installed. "
                   "Install with: pip install weasyprint==69.0"
        )
    # Also check system libs at runtime
    try:
        weasyprint.HTML(string="<p>test</p>").write_pdf()
    except Exception as exc:
        raise HTTPException(
            status_code=501,
            detail=f"PDF export unavailable — system lib error: {exc}"
        )
    # ... render actual PDF
```

### Pattern 4: docxtpl template build script with self-verify
**What:** Build .docx template via python-docx; load with DocxTemplate and assert variable contract
**When to use:** Any new template — catches missing/misspelled Jinja2 variables at build time

```python
# Source: v1.0 scripts/build_docx_template.py — get_undeclared_template_variables() pattern
from docxtpl import DocxTemplate
tpl = DocxTemplate(OUTPUT_PATH)
undeclared = sorted(tpl.get_undeclared_template_variables())
required = {"position_title", "duties", "jes_scores", "manifest"}
missing = required - set(undeclared)
if missing:
    raise AssertionError(f"Required vars missing from template: {missing}")
```

### Pattern 5: Amendment appendix fetch for DOCX
**What:** Query audit_log for manager_amendment rows before building DOCX context
**When to use:** WD DOCX export — AMEND-02 requirement

```python
# Source: v2/backend/app/api/amendments.py GET route pattern
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
                "section": SECTION_NAMES.get(section, section),
                "comment": detail.get("comment", ""),
                "created_at": row["created_at"],
            })
    return notes
```

### Pattern 6: Frontend file download via Blob URL
**What:** Fetch endpoint, convert response to Blob, trigger `<a>` click
**When to use:** DOCX and PDF download buttons in `ReviewState`

```javascript
// Source: [ASSUMED] — standard browser file download from fetch
async function downloadExport(kind) {
  const url = kind === 'docx'
    ? `/api/wd/${wd_id}/export/docx`
    : `/api/wd/${wd_id}/export/poster`;
  const resp = await fetch(url, { method: 'POST' });
  if (!resp.ok) { setToast('Export failed.'); return; }
  const blob = await resp.blob();
  const href = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = href;
  a.download = kind === 'docx'
    ? `${record.title || 'work-description'}.docx`
    : `${record.title || 'job-poster'}.docx`;
  a.click();
  URL.revokeObjectURL(href);
}
```

### Anti-Patterns to Avoid

- **Writing temp files to disk during render:** Use `io.BytesIO()` — temp files can collide or leak on ARM64 with constrained /tmp
- **Calling DocxTemplate.render() on the event loop thread:** Always wrap in `asyncio.to_thread` — docxtpl is synchronous and CPU-bound
- **Importing WeasyPrint at module level:** Import inside the PDF route handler — prevents startup failure if system libs are absent
- **Calling `get_undeclared_template_variables()` only at export time:** Call it in the build script too — catches contract violations at build time, not first export
- **Using v1.0 ProvenanceTag object access on v2.0 model:** v2.0 DraftDuty has `provenance_noc_code`, `provenance_hash`, `advisor` as flat fields — there is no `.provenance` sub-object

---

## V2.0 Model → DOCX Context Mapping

This is the critical translation table. The v1.0 export service uses `wd.og_recommendation.provenance`,
`wd.draft_duties`, `wd.advisor_additions`, etc. — none of these exist on v2.0's WorkDescription.

### WorkDescription v2.0 fields and their DOCX equivalents

| DOCX Template Variable | v2.0 Source Field | Notes |
|------------------------|-------------------|-------|
| `position_title` | `wd.record.get('title', '') or wd.title` | record dict is the canonical answer store |
| `position_number` | `wd.record.get('position_number', '')` | may be absent — default to "" |
| `og_level` | `f"{wd.confirmed_og['og_code']}-{wd.og_level:02d}"` | confirmed_og is a dict with og_code/og_name |
| `supervisor_title` | `wd.record.get('reports', '')` | "reports" step answer |
| `supervisor_position_number` | `''` | not captured in v2.0 conversation — leave blank |
| `review_date` | `str(date.today())` | generated at export time |
| `organizational_context_text` | composed from `wd.record` via `buildOverview()` logic | same logic as document.jsx:buildOverview |
| `organizational_context_source` | `"Drafted from answers"` | no ProvenanceTag in v2.0 |
| `duties` | `[{'text': d.text, 'noc_code': d.provenance_noc_code, 'is_advisor': d.advisor}]` | `wd.duties` is `list[DraftDuty]` |
| `jes_scores` | `wd.jes_scores` | already `list[dict]` with `factor_name`, `degree`, `points` |
| `jes_total_points` | `wd.jes_total_points or 0` | |
| `manifest` | deduplicated list from duty provenance + JES standard | see pattern below |
| `amendments` | queried from `audit_log` WHERE `event='manager_amendment'` | AMEND-02 |

### Version Manifest for v2.0

The v1.0 manifest walked ProvenanceTag objects. v2.0 must construct it from flat fields:

```python
def _build_v2_manifest(wd: WorkDescription) -> list[dict]:
    """Build deduplicated version manifest from v2.0 flat fields."""
    seen: set[tuple] = set()
    manifest = []
    def _add(source_type, source_id, source_version):
        key = (source_type, source_id, source_version)
        if key not in seen:
            seen.add(key)
            manifest.append({
                "source_type": source_type,
                "source_id": source_id,
                "source_version": source_version,
                "retrieved_date": str(date.today()),
            })

    # NOC duties
    for d in wd.duties:
        if d.provenance_noc_code:
            _add("NOC", d.provenance_noc_code, "NOC 2021")

    # JES standard
    if wd.jes_total_points is not None:
        og_code = (wd.confirmed_og or {}).get("og_code", "")
        if og_code == "EC":
            _add("JES", "EC JES 2017", "EC JES 2017")
        elif og_code:
            _add("JES", og_code, NON_EC_STANDARD_NAMES.get(og_code, "JES"))

    # OG definitions
    if wd.confirmed_og:
        _add("OG", "TBS OG Definitions", "TBS OG Definitions 2024")

    # Qualifications
    if wd.qualification:
        _add("QUAL", "TBS Qualification Standard", "TBS Qualification Standard 2024")

    return manifest
```

### Job Poster Context

The poster template is simpler — it does not need JES scores or the full manifest:

| Poster Variable | v2.0 Source |
|-----------------|-------------|
| `position_title` | `wd.record.get('title', '')` |
| `og_level` | `f"{og_code}-{og_level:02d}"` |
| `og_name` | `wd.confirmed_og['og_name']` |
| `branch` | `wd.record.get('branch', '')` |
| `education` | `wd.qualification.education` |
| `experience` | `wd.qualification.experience` |
| `duties` | top 3–5 from `wd.duties` — `[{'text': d.text}]` |
| `bilingual_title_fr` | `""` (bilingual placeholder — not translated) |

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DOCX template loops (duties, JES rows, manifest rows) | Manual paragraph/table insertion per row | `docxtpl` `{%tr for %}/{%p for %}` loops | Handles table row duplication and paragraph-level loops with Jinja2; manual insertion is 5x more code and breaks on edge cases (empty lists, nested tables) |
| HTML→PDF rendering | Custom PDF library | `weasyprint` | WeasyPrint handles CSS layout, pagination, Unicode; custom PDF is weeks of work |
| File download from SPA | Form POST to new tab | `fetch` + `Blob` + `URL.createObjectURL` | Avoids browser popup blockers; works with CORS/proxy setup already in place |
| Amendment section in DOCX | Custom pagination logic | docxtpl `{%p if amendments|length > 0 %}` gate | Same pattern used for DRF section in v1.0 build script |

---

## Common Pitfalls

### Pitfall 1: v1.0 ProvenanceTag Field Access on v2.0 Model
**What goes wrong:** Copying `wd.confirmed_noc.provenance.source_id` from v1.0 export_service; AttributeError because v2.0 `NOCMatch` has no `.provenance` sub-object.
**Why it happens:** v2.0 DraftDuty uses flat fields (`provenance_noc_code`, `provenance_hash`, `advisor`) not a nested `ProvenanceTag`.
**How to avoid:** Use the v2.0 Model → DOCX Context Mapping table above; never import or reference v1.0 model fields.
**Warning signs:** `AttributeError: 'NOCMatch' object has no attribute 'provenance'` at export time.

### Pitfall 2: v1.0 Stage Gate Does Not Exist in v2.0
**What goes wrong:** Copying the `wd.stage == 'jes_scored'` check from v1.0 generate_export(); AttributeError because v2.0 WorkDescription has no `stage` field.
**Why it happens:** v2.0 uses `require_og_confirmed()` gate (see jes_scoring.py) instead of a stage machine.
**How to avoid:** Use `require_og_confirmed(wd)` from `app.services.classification_gate` as the readiness gate, plus check `wd.jes_total_points is not None` before export.
**Warning signs:** `ValidationError: extra fields not permitted` or `AttributeError: 'WorkDescription' object has no attribute 'stage'`.

### Pitfall 3: docxtpl {%tr for %} and {%p for %} Must Be in Their Own Paragraph/Row
**What goes wrong:** `{% for duty in duties %}{{ duty.text }}{% endfor %}` all in one paragraph renders as a single paragraph with literal tag text.
**Why it happens:** docxtpl's XML patch regex is greedy — the for/endfor tags must each occupy their own Word paragraph (for `{%p ...%}`) or their own table row (for `{%tr ...%}`).
**How to avoid:** Follow the exact pattern in `build_docx_template.py`: add_paragraph for `{%p for %}`, add_paragraph for body, add_paragraph for `{%p endfor %}`.
**Warning signs:** The rendered DOCX shows literal `{%p for duty in duties %}` text.

### Pitfall 4: empty confirmed_og dict vs None
**What goes wrong:** `wd.confirmed_og['og_code']` raises KeyError because confirmed_og is `{}` (stored as empty dict from a partial frontend commit).
**Why it happens:** `WorkDescription.confirmed_og` is `Optional[dict]` — a PATCH that sends `confirmed_og: {}` stores an empty dict, not None.
**How to avoid:** Always guard: `og_code = (wd.confirmed_og or {}).get('og_code', '')` and check it's non-empty before rendering.
**Warning signs:** KeyError at context build time.

### Pitfall 5: WeasyPrint silently fails without cffi/Pango at import
**What goes wrong:** `import weasyprint` succeeds (pure Python install) but `weasyprint.HTML(...).write_pdf()` raises `OSError: cannot load library 'pango-1.0'` at render time.
**Why it happens:** WeasyPrint imports cleanly but the actual render invokes Pango via cffi at call time, not import time.
**How to avoid:** The runtime probe must actually call `weasyprint.HTML(string="<p>x</p>").write_pdf()` in a try/except, not just `import weasyprint`. Cache the result in a module-level variable to avoid re-probing on every request.
**Warning signs:** `OSError: cannot load library 'libpango'` in the 501 diagnostic.

### Pitfall 6: og_level zero-padding inconsistency
**What goes wrong:** Template renders "EC-5" instead of "EC-05"; downstream TBS tools reject the classification string.
**Why it happens:** `og_level` is stored as integer 5; string formatting must zero-pad to 2 digits.
**How to avoid:** Always format as `f"{og_code}-{int(og_level):02d}"`.
**Warning signs:** Classification string in DOCX reads "EC-5" instead of "EC-05".

---

## WeasyPrint ARM64 Feasibility Assessment

**Confirmed present (system libs):** [VERIFIED: dpkg -l]
- `libpango-1.0-0:arm64 1.50.6+ds-2ubuntu1`
- `libpangocairo-1.0-0:arm64 1.50.6+ds-2ubuntu1`
- `libcairo2:arm64 1.16.0-5ubuntu2.1`

**WeasyPrint status:** [VERIFIED: pip index versions weasyprint]
- Latest: `69.0` — installable via pip
- NOT currently installed in v2 backend

**Assessment:** ARM64 system libs are present. WeasyPrint 69.0 is pip-installable and should work.
The Phase 20 plan must include a Wave 0 step to `pip install weasyprint` and run a smoke test
(`weasyprint.HTML(string="<p>x</p>").write_pdf()`). If the smoke test passes, the PDF endpoint
is fully implemented. If it fails (missing cffi or other binding), the runtime probe correctly
returns 501.

**PDF render approach for v2.0:** WeasyPrint renders from HTML, not from a .docx. The PDF endpoint
should render the WD as styled HTML (mirroring the document.jsx sections) and pass it to
`weasyprint.HTML(string=html).write_pdf()`. This is simpler than converting DOCX→PDF.

---

## Frontend Export Wiring

The `exportAs(kind)` function in `app.jsx` currently only fires a toast — it never hits the API.
Phase 20 must replace this stub with real fetch calls.

**Current state (app.jsx line 400–405):**
```javascript
function exportAs(kind) {
  const msg = kind === 'clipboard' ? 'Job description copied to clipboard'
    : `${record.title || 'Work description'} exported as ${kind}`;
  setToast(msg);
  setTimeout(() => setToast(null), 2600);
}
```

**Required state:** Three distinct cases — DOCX download, PDF download (or 501 toast), clipboard copy.
The `ReviewState` component in `conversation.jsx` calls `onExport` with three strings:
`'Word document (.docx)'`, `'PDF'`, `'clipboard'`.

The SPA needs `wd_id` to be non-null for the export to work. The export buttons should be
disabled (or show a toast) if `wd_id` is null (WD not yet persisted).

---

## Runtime State Inventory

This is a greenfield feature — no rename/refactor. However, the export endpoints will log
to `audit_log`. There are no pre-existing records that need migration.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | None — export is write-once; no migration needed | None |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | None — no new env vars required | None |
| Build artifacts | `v2/backend/app/templates/` directory does not exist yet | Wave 0: create directory + committed .docx templates |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| docxtpl | EXP-01, EXP-02 | Yes | 0.18.0 | — |
| python-docx | Template build scripts | Yes | 1.1.2 | — |
| weasyprint | EXP-03 | No — needs install | 69.0 (latest) | 501 runtime gate |
| libpango-1.0-0 (ARM64) | WeasyPrint PDF | Yes | 1.50.6 | — |
| libcairo2 (ARM64) | WeasyPrint PDF | Yes | 1.16.0 | — |
| pytest | Test suite | Yes | 8.3.4 | — |

**Missing dependencies with no fallback:**
- None that block execution — WeasyPrint can be pip-installed.

**Missing dependencies with fallback:**
- WeasyPrint: if `pip install weasyprint` or the smoke test fails, the PDF endpoint returns 501 (EXP-03 explicitly allows this). Add to `requirements.txt` and test.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 + pytest-asyncio 0.24.0 |
| Config file | `v2/backend/pyproject.toml` |
| Quick run command | `cd v2/backend && python -m pytest tests/test_export.py -x` |
| Full suite command | `cd v2/backend && python -m pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXP-01 | POST /api/wd/{id}/export/docx returns .docx bytes | integration | `pytest tests/test_export.py::test_export_wd_docx_returns_bytes -x` | Wave 0 |
| EXP-01 | DOCX contains version manifest section | integration | `pytest tests/test_export.py::test_export_wd_docx_manifest -x` | Wave 0 |
| EXP-01 | DOCX contains amendment appendix when notes exist | integration | `pytest tests/test_export.py::test_export_wd_docx_amendments_appendix -x` | Wave 0 |
| EXP-02 | POST /api/wd/{id}/export/poster returns .docx bytes | integration | `pytest tests/test_export.py::test_export_poster_returns_bytes -x` | Wave 0 |
| EXP-03 | POST /api/wd/{id}/export/pdf returns 501 when WeasyPrint absent | unit | `pytest tests/test_export.py::test_export_pdf_501_when_weasyprint_absent -x` | Wave 0 |
| API-08 | 404 on unknown wd_id | integration | `pytest tests/test_export.py::test_export_docx_404 -x` | Wave 0 |
| API-09 | 404 on unknown wd_id for poster | integration | `pytest tests/test_export.py::test_export_poster_404 -x` | Wave 0 |

### Wave 0 Gaps

- [ ] `tests/test_export.py` — covers all EXP/API-08/API-09 requirements above
- [ ] `v2/backend/app/templates/` directory — must exist before templates can be committed
- [ ] `scripts/build_wd_template.py` — v2 adaptation of v1.0 `build_docx_template.py`
- [ ] `scripts/build_poster_template.py` — new script for job poster template
- [ ] WeasyPrint install: `pip install weasyprint==69.0` + smoke test + add to `requirements.txt`

*(Existing conftest.py, `client` fixture, and `env_with_db` fixture cover all new tests — no changes to conftest needed.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Single-user local app |
| V3 Session Management | No | No sessions |
| V4 Access Control | No | Single-user local app |
| V5 Input Validation | Yes | wd_id path parameter validated as non-empty string; WD existence check → 404 |
| V6 Cryptography | No | SHA-256 used for export hash only — no key management needed |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via wd_id | Tampering | wd_id is a UUID string; only used as a DB lookup key, never in file paths |
| Oversized DOCX context | DoS | duties list capped at 10 (jes_scoring.py pattern); amendment comments capped at 2000 chars (existing validation in amendments.py) |
| WeasyPrint SSRF via HTML input | Spoofing | HTML passed to WeasyPrint must be generated server-side from WD data — never accept raw HTML from the client |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PDF endpoint renders from server-generated HTML (not DOCX→PDF conversion) | WeasyPrint section | If DOCX→PDF is required, LibreOffice headless is needed — not installed; significant impact |
| A2 | `supervisor_position_number` is left blank (not captured in v2 conversation) | Model mapping table | If TBS WD format requires it, Phase 20 must add a data capture step — out of scope |
| A3 | Bilingual poster headers use placeholder empty string for French title | Poster context table | If actual French translation is required, a translation step must be added — out of scope per REQUIREMENTS.md |

---

## Open Questions

1. **Amendment appendix section heading in DOCX**
   - What we know: AMEND-02 says "Manager Amendments for Review" with section reference + "Manager-proposed — pending advisor ratification" tag
   - What's unclear: Should the amendments render as a new Section 6 (renumbering other sections) or as an unnumbered appendix after the version manifest?
   - Recommendation: Unnumbered appendix (after Section 5 manifest) — avoids renumbering existing section numbers that may be cited by reviewers

2. **PDF quality requirements**
   - What we know: WeasyPrint renders HTML to PDF; the live document preview in document.jsx is the HTML source of truth
   - What's unclear: Should the PDF match the SPA's visual design (Hanken Grotesk, Spectral fonts) or use a simplified print stylesheet?
   - Recommendation: Generate a separate print-style HTML string from WD data (not the React DOM) — avoids depending on the SPA render tree

3. **Poster "bilingual headers" scope**
   - What we know: EXP-02 says bilingual headers; French is flagged-only in REQUIREMENTS.md Out of Scope
   - What's unclear: Does the poster need actual translated French or just header placeholders showing "Position Title / Titre du poste"?
   - Recommendation: Bilingual field labels only (English/French label pairs); leave French content blank with a placeholder

---

## Sources

### Primary (HIGH confidence)
- v2/backend/app/models/work_description.py — WorkDescription model fields [VERIFIED: file read]
- v2/backend/app/models/draft_duty.py — DraftDuty provenance fields [VERIFIED: file read]
- v2/backend/app/models/qualification_standard.py — QualificationStandard fields [VERIFIED: file read]
- v2/backend/app/api/amendments.py — amendment write/read pattern [VERIFIED: file read]
- v2/backend/app/api/jes_scoring.py — router pattern to follow [VERIFIED: file read]
- v2/backend/app/db.py — audit_log schema [VERIFIED: file read]
- v2/backend/requirements.txt — `docxtpl==0.18.0`, `python-docx==1.1.2` confirmed [VERIFIED: file read]
- app/services/export_service.py (v1.0) — export pattern reference [VERIFIED: file read]
- scripts/build_docx_template.py (v1.0) — template build pattern [VERIFIED: file read]
- v2/frontend/src/app.jsx — exportAs stub location + wd_id state [VERIFIED: file read]
- v2/frontend/src/conversation.jsx — ReviewState export buttons [VERIFIED: file read]
- `pip list` in v2/backend — docxtpl 0.18.0, python-docx 1.1.2 confirmed [VERIFIED: bash]
- `dpkg -l libpango* libcairo*` — ARM64 system libs confirmed present [VERIFIED: bash]
- `pip index versions weasyprint` — 69.0 latest, pip-installable [VERIFIED: bash]
- `python3 -c "import weasyprint"` — NOT installed in v2 backend [VERIFIED: bash]

### Secondary (MEDIUM confidence)
- v1.0 template variables list from `DocxTemplate.get_undeclared_template_variables()` [VERIFIED: bash runtime call]

### Tertiary (LOW confidence)
- WeasyPrint HTML-from-string rendering approach — [ASSUMED] based on WeasyPrint API design; not tested on Jane

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — docxtpl/python-docx verified installed; WeasyPrint verified pip-available, system libs present
- Architecture: HIGH — v1.0 export pattern fully read; v2.0 model fields fully read; router pattern verified in jes_scoring.py
- Pitfalls: HIGH — v1.0 vs v2.0 model diff directly observed by reading both models; docxtpl tag placement rule from v1.0 build script
- WeasyPrint ARM64: MEDIUM — system libs confirmed present, but actual install + smoke test not yet run

**Research date:** 2026-06-09
**Valid until:** 2026-07-09 (stable library versions; WeasyPrint ARM64 assessment valid until Jane's OS is upgraded)
