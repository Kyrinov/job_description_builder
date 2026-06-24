# Phase 29: Structured Export + Enhanced Poster — Research

**Researched:** 2026-06-24
**Domain:** FastAPI export routes, Python CSV/JSON serialization, docxtpl template extension, React fetch+Blob pattern
**Confidence:** HIGH — all findings verified against live codebase

---

## Summary

Phase 29 adds two new machine-readable export routes (`/export/json`, `/export/csv`) and one poster enhancement ("About the Organization" section). The backbone for all three is `build_seven_elements(wd)` — already live in `export_service.py` since Phase 27. This helper is the single source of truth for the 7 Part 2 elements and is already battle-tested by 5 unit tests in `test_export.py`.

The new export routes follow the established pattern in `export.py` exactly: load WD via `_load_wd()`, skip `require_og_confirmed` (both JSON/CSV must succeed for manager-track WDs), build response, return `Response(content=..., media_type=..., headers=...)`. The poster enhancement is a two-file change: `build_poster_template.py` gains an "About the Organization" paragraph using `{{ org_context }}` and `_build_poster_context()` gains that key.

The frontend change is minimal: `exportAs()` in `app.jsx` handles all four formats via a `kind` dispatch. JSON and CSV require a 3-line extension to the existing `if`/`else` chain. `ReviewState` in `conversation.jsx` gets two new `<button className="btn--export">` nodes appended inside `.export-row`.

**Primary recommendation:** Backend-first sequence — Wave 1 adds the two new routes + poster template + `_build_poster_context` key; Wave 2 adds the frontend buttons. All new tests use the existing `_create_wd_ec` / `_create_wd_for_seven_elements` fixture helpers already defined in `test_export.py`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| JSON export (7-element analytics) | API / Backend | — | Pure data serialization; no browser involvement until file is served |
| CSV export (Excel-compatible) | API / Backend | — | UTF-8-BOM encoding + RFC 4180 quoting must happen server-side |
| Download buttons (JSON + CSV) | Browser / Client | Frontend Server (SSR) | Blob + URL.createObjectURL is a client-side browser API |
| Manager-track null-field handling | API / Backend | — | `[ADVISOR TO COMPLETE]` placeholder injected at export time, not in UI |
| Poster "About the Organization" section | API / Backend | — | docxtpl template extension; `org_context` field already on WorkDescription |

---

## Standard Stack

### Core (all already installed) [VERIFIED: live codebase]

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI + Response | installed | JSON/CSV route handlers | Matches all existing export routes in `export.py` |
| `csv` (stdlib) | stdlib | DictWriter + UTF-8-BOM CSV | No dep; RFC 4180 quoting; BOM via `io.TextIOWrapper` |
| `json` (stdlib) | stdlib | JSON serialization | No dep; already used throughout |
| `io.StringIO` | stdlib | In-memory CSV buffer | Matches REQUIREMENTS.md spec for SEXP-02 |
| `docxtpl` + `DocxTemplate` | installed | Poster template render | Same as `_render_docx()` in `export_service.py` |
| `python-docx` (`docx`) | installed | `build_poster_template.py` script | Same as `build_accessible_template.py` |

### No New Dependencies Required

Phase 29 uses only the stdlib `csv` module and already-installed libraries. No `pip install` step needed.

---

## Architecture Patterns

### System Architecture Diagram

```
Frontend (app.jsx)                     Backend (export.py)
  exportAs('json') ──── POST ─────────► /api/wd/{id}/export/json
  exportAs('csv')  ──── POST ─────────► /api/wd/{id}/export/csv
         │                                    │
         │                               _load_wd(id)
         │                                    │
         │                             WorkDescription
         │                                    │
         │                        build_seven_elements(wd)
         │                                    │
         │                   ┌────────────────┴───────────────────┐
         │                   ▼                                     ▼
         │          JSON: json.dumps(payload)          CSV: csv.DictWriter
         │          + classification metadata          utf-8-sig encoding
         │                   │                                     │
         ◄── Response(bytes) ┘──────────── content ───────────────┘
         │
  resp.blob()
  URL.createObjectURL(blob)
  <a>.click() → file download
```

### Recommended File Changes

```
v2/backend/
├── app/
│   ├── api/
│   │   └── export.py          # +2 new route handlers (json + csv)
│   └── services/
│       └── export_service.py  # +_build_poster_context org_context key
│           └── (build_seven_elements already present — no change)
├── scripts/
│   └── build_poster_template.py  # +About the Organization section
└── tests/
    └── test_export.py            # +6 new tests (3 SEXP-01, 1 SEXP-02, 1 SEXP-04, 1 POST-01)

v2/frontend/src/
├── app.jsx                    # extend exportAs() with json/csv kinds
└── conversation.jsx           # +2 btn--export buttons in ReviewState
```

### Pattern 1: New Export Route (matches existing export.py pattern)

```python
# Source: v2/backend/app/api/export.py — existing poster/docx routes
@router.post("/wd/{wd_id}/export/json")
async def export_wd_json(wd_id: str) -> Response:
    """SEXP-01 — Export 7-element analytics JSON."""
    settings = get_settings()
    wd = _load_wd(wd_id, settings.db_path)
    # NO require_og_confirmed — manager-track WDs must succeed (SEXP-04 criterion)
    payload = _build_json_export(wd)
    safe_title = _slugify_title((wd.record or {}).get("title", ""), "work-description")
    filename = f"{safe_title}.json"
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

Key difference from DOCX/PDF routes: **no `require_og_confirmed` call**. Manager-track WDs without `confirmed_og` must return 200 (SEXP-04 success criterion).

### Pattern 2: UTF-8-BOM CSV with DictWriter

```python
# Source: Python stdlib csv docs + REQUIREMENTS.md SEXP-02 spec [VERIFIED: stdlib]
import csv
import io

def _build_csv_export(wd: WorkDescription) -> bytes:
    """Build UTF-8-with-BOM CSV; one row per key activity (duty)."""
    seven = build_seven_elements(wd)
    elements = {e["key"]: e for e in seven["elements"]}

    # utf-8-sig writes the BOM (\xef\xbb\xbf) at the start — Excel auto-detects UTF-8
    buf = io.StringIO()
    fieldnames = [
        "duty_text", "duty_noc_code",
        "organizational_context", "client_service_results",
        "skills_status", "effort_status", "responsibility",
        "working_conditions_status",
        "og_level", "jes_total_points", "complete_count", "total"
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()

    duties = elements["key_activities"]["value"] or []
    # scalar fields repeated per row (per SEXP-02 spec)
    og_level_str = _og_level_str(_og_code_from(wd), wd.og_level or 0)
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
    if duties:
        for d in duties:
            row = {**scalar, "duty_text": d.text, "duty_noc_code": d.provenance_noc_code or ""}
            writer.writerow(row)
    else:
        writer.writerow({**scalar, "duty_text": _MANAGER_PLACEHOLDER, "duty_noc_code": ""})

    # encode with BOM — Excel opens without "Import Text" dialog
    return buf.getvalue().encode("utf-8-sig")
```

**Critical detail:** `encode("utf-8-sig")` adds the BOM byte sequence. `csv.DictWriter` handles all RFC 4180 quoting automatically (commas, quotes, newlines in cell values are correctly escaped). Do NOT manually escape — DictWriter does it.

### Pattern 3: JSON Export Payload Structure

```python
# SEXP-01 contract: all 7 Part 2 element keys + classification metadata + provenance
def _build_json_export(wd: WorkDescription) -> dict:
    """Build 7-element analytics JSON for SEXP-01."""
    seven = build_seven_elements(wd)
    elements = {e["key"]: e for e in seven["elements"]}
    og_code = _og_code_from(wd)
    og_level_str = _og_level_str(og_code, wd.og_level or 0) if og_code else None

    MANAGER_PH = "[ADVISOR TO COMPLETE]"

    return {
        # 7 Part 2 elements
        "organizational_context": elements["organizational_context"]["value"] or None,
        "client_service_results": elements["client_service_results"]["value"] or None,
        "key_activities": [
            {"text": d.text, "noc_code": d.provenance_noc_code or None}
            for d in (elements["key_activities"]["value"] or [])
        ],
        "skills": None,  # status only — actual content is in qualification fields
        "effort": None,  # derived from JES; no scalar representation at this layer
        "responsibility": elements["responsibility"]["value"] or None,
        "working_conditions": None,  # derived from JES
        # Per-element completeness
        "element_status": {e["key"]: e["status"] for e in seven["elements"]},
        "complete_count": seven["complete_count"],
        "total": seven["total"],
        # Classification metadata
        "classification": {
            "og_level": og_level_str or MANAGER_PH,
            "jes_total_points": wd.jes_total_points if wd.jes_total_points is not None else MANAGER_PH,
            "og_name": (wd.confirmed_og.get("og_name", "") if isinstance(wd.confirmed_og, dict) else "") or MANAGER_PH,
        },
        # Provenance
        "provenance": _build_v2_manifest(wd),
        "wd_type": getattr(wd, "wd_type", "advisor"),
        "export_date": str(date.today()),
    }
```

**Manager-track placeholder rule:** Any classification field not set by the manager uses the string `"[ADVISOR TO COMPLETE]"` in the output, not `null`. This matches the success criterion 4 exactly. However, the 7 Part 2 element fields themselves (`organizational_context`, `responsibility`, etc.) should return `null` when the advisor hasn't filled them — the placeholder only applies to *classification* fields (og_level, jes_total_points, og_name).

### Pattern 4: exportAs() Extension in app.jsx

```javascript
// Source: v2/frontend/src/app.jsx lines 614-676 (verified)
async function exportAs(kind) {
  if (kind === 'clipboard') { /* ... existing ... */ return; }
  if (!wd_id) { /* ... existing guard ... */ return; }
  // Existing OG guard — skip for json/csv (no OG required, same as manager bypass)
  if (userRole !== 'manager' && kind !== 'json' && kind !== 'csv'
      && (!record.confirmed_og || !record.og_level)) {
    setToast('Complete the OG group and level steps before exporting.');
    /* ... */
    return;
  }
  // Extend the endpoint/ext/filename dispatch:
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
  const filename = `${(record.title || 'work-description').toLowerCase().replace(/\s+/g, '-')}.${ext}`;
  // ... rest of fetch+blob pattern unchanged
}
```

The existing `resp.blob()` → `URL.createObjectURL` → anchor click pattern is MIME-agnostic. JSON and CSV responses will download correctly with no special handling needed on the frontend.

**Current OG guard location (line 625):**
```javascript
if (userRole !== 'manager' && (!record.confirmed_og || !record.og_level)) {
```
This must be extended to also skip the guard for `kind === 'json'` and `kind === 'csv'`, since SEXP-04 requires manager-track WDs (and advisor WDs without OG) to succeed at 200.

### Pattern 5: ReviewState Button Addition

```jsx
// Source: v2/frontend/src/conversation.jsx lines 243-255 (existing export-row)
<div className="export-row">
  <button className="btn--export" onClick={() => onExport('Word document (.docx)')}>
    <Icon path="..." />
    Export DOCX
  </button>
  <button className="btn--export" onClick={() => onExport('PDF')}>
    <Icon path="..." />
    Export PDF
  </button>
  <button className="btn--export" onClick={() => onExport('clipboard')}>
    <Icon path="..." />
    Copy
  </button>
  {/* Phase 29 additions: */}
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

No `userRole` gating on the JSON/CSV buttons — per UI-SPEC, both are visible to managers (POST-01's org_context content exports fine for managers, and the 7 Part 2 elements are content, not classification metadata).

### Pattern 6: Poster Template Extension

```python
# Source: build_poster_template.py lines 54-127 (existing build() function)
# Add AFTER the Branch section and BEFORE Key Duties:

# ------------------------------------------------------------------
# About the Organization
# ------------------------------------------------------------------
org_head = doc.add_paragraph()
org_run = org_head.add_run("About the Organization / À propos de l'organisation:")
org_run.bold = True
doc.add_paragraph("{{ org_context }}")
```

And in `_build_poster_context()` in `export_service.py`:
```python
# Add org_context to the returned dict:
return {
    "position_title": record.get("title", ""),
    "og_level": og_level_str,
    "og_name": ...,
    "branch": record.get("branch", ""),
    "education": education_text,
    "experience": experience_text,
    "duties": [{"text": d.text} for d in (wd.duties or [])[:5]],
    "bilingual_title_fr": "",
    "org_context": (wd.org_context or "").strip() or "[To be provided / À fournir]",
}
```

The `build_poster_template.py` self-verify block already asserts a `required` set. Add `"org_context"` to `required`:
```python
required = {
    "position_title", "bilingual_title_fr",
    "og_level", "og_name", "branch",
    "duties", "education_text", "experience_text",
    "org_context",  # Phase 29 addition
}
```

### Anti-Patterns to Avoid

- **Calling `require_og_confirmed` on JSON/CSV routes:** These routes must succeed for manager-track WDs with no confirmed_og. The OG gate is for classification-gated outputs (DOCX WD, PDF). JSON/CSV export content only.
- **Using `response.json()` on the frontend for CSV download:** The existing `resp.blob()` pattern handles all content types. Do not add special JSON parsing before the blob call.
- **Trusting `wd.jes_scores[*]["category"]`:** The `_factor_category_map()` helper exists precisely because the EC scoring path doesn't persist the category key. `build_seven_elements()` already handles this correctly via the `jes_total_points is not None` heuristic.
- **Setting BOM via `io.StringIO` constructor:** `StringIO` doesn't support encoding. Write `buf.getvalue().encode("utf-8-sig")` to add BOM. Do not try `io.TextIOWrapper` wrapping — it adds unnecessary complexity.
- **Adding the org_context section AFTER Key Duties in the poster:** The UI-SPEC says "About the Organization" belongs near the top of the poster, before duties. Insert after Branch in `build_poster_template.py`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RFC 4180 CSV quoting | Manual comma/quote escaping | `csv.DictWriter` | Handles all edge cases (embedded quotes, commas, newlines, CR/LF) per spec |
| UTF-8 BOM for Excel | Manual byte prefix | `.encode("utf-8-sig")` | Python stdlib encodes BOM as first 3 bytes automatically |
| 7-element data assembly | Re-deriving from WD fields | `build_seven_elements(wd)` | Already in `export_service.py`, tested by 5 unit tests, is the SSOT |
| Provenance manifest | Rebuilding from wd fields | `_build_v2_manifest(wd)` | Already in `export_service.py`, handles SJD, NOC, JES, OG sources |

**Key insight:** The hardest part of this phase (`build_seven_elements`) is already done. The new routes are thin wrappers that serialize its output.

---

## build_seven_elements() — Existing API (verified in source)

The helper is at `export_service.py` line 425. Its return shape is:
```python
{
    "elements": [
        {
            "key": "organizational_context",   # 7 keys total
            "label": "Organizational Context",
            "status": "populated" | "derived" | "missing",
            "value": str | list[DraftDuty] | None
        },
        # ... 6 more
    ],
    "complete_count": int,  # count of populated + derived
    "total": 7
}
```

Element keys in order: `organizational_context`, `client_service_results`, `key_activities`, `skills`, `effort`, `responsibility`, `working_conditions`.

**Value types by element:**
- `organizational_context`: `str` (typed `wd.org_context`) or `""` when missing
- `client_service_results`: `str` from `record["client_service_results"]` or `""` when missing
- `key_activities`: `list[DraftDuty]` (the raw duty objects — `.text` and `.provenance_noc_code` attributes)
- `skills`: `None` (status only — actual content is in `wd.qualification`)
- `effort`: `None` (status only — derived from `jes_total_points`)
- `responsibility`: `str` (typed `wd.responsibilities_narrative`) or `""` when missing
- `working_conditions`: `None` (status only)

**Implication for CSV:** The CSV route iterates over `elements["key_activities"]["value"]` (list of DraftDuty objects) to produce one row per duty. Scalar fields (org_context, csr, responsibility) are repeated in each row. Skills/effort/working_conditions appear as status strings only.

---

## Manager-Track Null-Field Handling Strategy

**Rule:** Classification fields not set by the manager show `"[ADVISOR TO COMPLETE]"` in the export output, NOT `null`. The 7 Part 2 element fields return `null` when empty (the advisor hasn't filled them yet for any WD type).

**Fields that need placeholder for manager-track:**
- `og_level` — manager never confirms OG
- `jes_total_points` — JES never ran
- `og_name` — comes from `confirmed_og` which is `None`

**Fields that return null naturally (no placeholder needed):**
- `organizational_context` — can be `null` for any WD type
- `client_service_results` — can be `null` for any WD type
- `responsibility` — can be `null` for any WD type

**Verification:** `build_seven_elements()` already handles missing values correctly — it returns `"missing"` status and empty string values. The export route adds the classification metadata layer where the placeholder applies.

---

## Provenance Fields for JSON Export

`_build_v2_manifest(wd)` (already in `export_service.py`, line 161) returns a list of:
```python
{
    "source_type": "NOC" | "JES" | "OG" | "QUAL" | "SJD",
    "source_id": str,
    "source_version": str,
    "retrieved_date": str  # ISO date
}
```

This is ready-made for the JSON export `"provenance"` field. No additional provenance tracking needed for Phase 29.

---

## Existing Test Patterns

The `test_export.py` file uses these patterns (verified):

**Fixture helpers available to reuse:**
- `_create_wd_ec(client)` — EC WD with Effort + Conditions factors
- `_create_wd_point_rating_with_effort(client)` — FB WD
- `_create_wd_point_rating_no_effort(client)` — MT WD (no effort/WC)
- `_create_wd_level_description(client)` — AS WD (empty jes_scores)
- `_create_wd_with_jes_scores(client)` — basic EC WD
- `_wd_for_seven_elements(**overrides)` — unit test WD builder (no HTTP)

**Test shape for new route tests:**
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

**Manager bypass test shape (matches existing MGR-03 pattern):**
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

---

## Common Pitfalls

### Pitfall 1: OG Gate on JSON/CSV Routes
**What goes wrong:** Adding `require_og_confirmed(wd)` at the top of the JSON/CSV route handlers, mirroring the DOCX pattern.
**Why it happens:** The DOCX/PDF/Poster routes all call `require_og_confirmed`. Copying that pattern to the new routes will cause manager-track WDs to 409.
**How to avoid:** The JSON/CSV routes deliberately omit `require_og_confirmed`. Success criterion 4 explicitly states "both JSON and CSV export routes succeed for a manager-track WD without a 409."
**Warning signs:** A test `test_export_json_manager_no_409` fails with 409.

### Pitfall 2: BOM Encoding in StringIO
**What goes wrong:** `io.StringIO(newline='')` does not produce a BOM. Writing to StringIO and calling `.getvalue()` then returning it as bytes without `encode("utf-8-sig")` will produce UTF-8 without BOM — Excel will show garbled text for any non-ASCII characters.
**Why it happens:** StringIO is a text buffer, not a bytes buffer. BOM is a bytes-level construct.
**How to avoid:** Always write to `io.StringIO()`, then `buf.getvalue().encode("utf-8-sig")`.
**Warning signs:** CSV opens in Excel but French characters (é, à, ç) appear corrupted.

### Pitfall 3: key_activities Value Is a List of DraftDuty Objects
**What goes wrong:** Treating `elements["key_activities"]["value"]` as a list of dicts and accessing `d["text"]` → KeyError.
**Why it happens:** `build_seven_elements()` returns `wd.duties` directly — these are `DraftDuty` Pydantic model instances, not plain dicts.
**How to avoid:** Access `.text` and `.provenance_noc_code` as attributes: `d.text`, `d.provenance_noc_code`.
**Warning signs:** `TypeError: 'DraftDuty' object is not subscriptable` when building CSV rows.

### Pitfall 4: build_poster_template.py Output Path
**What goes wrong:** Running the script from a different directory than the repo root — the relative `OUTPUT_PATH = "v2/backend/app/templates/poster_template.docx"` will write to the wrong location.
**Why it happens:** OUTPUT_PATH is a relative path (verified in the script at line 38).
**How to avoid:** Always run from repo root: `python v2/backend/scripts/build_poster_template.py` from `/home/charles/job_description_builder/`.
**Warning signs:** `FileNotFoundError` or a `poster_template.docx` created in the wrong directory.

### Pitfall 5: Self-Verify `required` Set Must Be Updated
**What goes wrong:** Adding `{{ org_context }}` to the poster template but NOT adding `"org_context"` to the `required` set in the self-verify block — the script exits 0 but the contract assertion is weakened.
**Why it happens:** `tpl.get_undeclared_template_variables()` lists what IS in the template; `required - set(undeclared)` catches what SHOULD be there but isn't. If `required` is not updated, the check won't catch a future accidental deletion of `{{ org_context }}`.
**How to avoid:** Add `"org_context"` to `required` in the same commit as the template change.

### Pitfall 6: Poster `require_og_confirmed` Still Active
**What goes wrong:** Manager users can't download the poster DOCX (POST-01) because `export_poster()` in `export.py` still calls `require_og_confirmed(wd)`.
**Why it happens:** The Phase 28 bypass only covers the DOCX WD export. Checking `export.py` line 100 confirms `export_poster` also calls `require_og_confirmed`.
**How to avoid:** This is a known pre-existing constraint. POST-01 scope is "About the Organization" section for WDs with org_context — the phase requirement doesn't mandate poster export for manager-track. The poster `require_og_confirmed` is out of scope for Phase 29. Verify that POST-01 success criterion only references "a WD with org_context" — which works fine for advisor-track WDs.

---

## Code Examples

### Complete UTF-8-BOM CSV Pattern (Python stdlib)

```python
# Source: Python stdlib csv documentation [VERIFIED: stdlib]
import csv
import io

buf = io.StringIO()
writer = csv.DictWriter(buf, fieldnames=["col_a", "col_b", "col_c"])
writer.writeheader()
writer.writerow({"col_a": "value with, comma", "col_b": 'value with "quotes"', "col_c": "line\nbreak"})
csv_bytes = buf.getvalue().encode("utf-8-sig")  # BOM prepended automatically
```

DictWriter automatically quotes values containing delimiters, quote characters, or newlines per RFC 4180 with default `quoting=csv.QUOTE_MINIMAL`.

### FastAPI Response with Content-Disposition

```python
# Source: v2/backend/app/api/export.py lines 88-92 (existing pattern)
return Response(
    content=csv_bytes,
    media_type="text/csv; charset=utf-8",
    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
)
```

For JSON: `media_type="application/json"`, content is `json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 7-element data assembled inline in each consumer | `build_seven_elements(wd)` shared helper | Phase 27 | JSON/CSV routes call the helper directly — no re-implementation |
| Manager-track blocked by OG gate | `wd_type == 'manager'` bypass in `require_og_confirmed` | Phase 28 | JSON/CSV routes inherit this for free by NOT calling the gate |
| TBS template (wd_template.docx) | Accessible template (wd_accessible_template.docx) | Phase 25 | DOCX export now uses the Accessible format; poster is separate and unchanged |

---

## Open Questions

1. **Should CSV export also succeed for manager-track without OG?**
   - What we know: SEXP-04 success criterion says "both JSON and CSV export routes succeed for a manager-track WD without a 409"
   - What's unclear: Whether the frontend OG guard in `exportAs()` should also be skipped for CSV (same as JSON)
   - Recommendation: Yes — skip the OG guard for both `kind === 'json'` and `kind === 'csv'` in `exportAs()`. UI-SPEC confirms both buttons are visible to managers.

2. **Does `_build_poster_context()` need to handle manager-track?**
   - What we know: `export_poster()` calls `require_og_confirmed(wd)`, which still 409s for manager-track
   - What's unclear: Whether POST-01 implies removing the OG gate from poster export for managers
   - Recommendation: POST-01 success criterion says "a WD with org_context shows About the Organization" — it doesn't specify manager-track. Poster export already works for advisor-track WDs with confirmed_og. No gate change needed for POST-01.

---

## Environment Availability

All tools required are already installed and confirmed by the running test suite (179 backend + 85 frontend GREEN at Phase 28 completion).

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| FastAPI | All routes | ✓ | installed | — |
| python-docx | build_poster_template.py | ✓ | installed | — |
| docxtpl | poster render | ✓ | installed | — |
| csv (stdlib) | SEXP-02 | ✓ | stdlib | — |
| io (stdlib) | SEXP-02 | ✓ | stdlib | — |
| json (stdlib) | SEXP-01 | ✓ | stdlib | — |
| pytest / pytest-asyncio | tests | ✓ | installed | — |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `v2/backend/` (pytest discovers from there) |
| Quick run command | `cd /home/charles/job_description_builder && python -m pytest v2/backend/tests/test_export.py -x -q` |
| Full suite command | `cd /home/charles/job_description_builder && python -m pytest v2/backend/tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEXP-01 | POST /export/json returns all 7 keys | integration | `pytest tests/test_export.py::test_export_json_returns_all_seven_keys -x` | ❌ Wave 0 |
| SEXP-01 | JSON includes classification metadata + provenance | integration | `pytest tests/test_export.py::test_export_json_metadata_and_provenance -x` | ❌ Wave 0 |
| SEXP-02 | POST /export/csv returns UTF-8-BOM CSV, one row per duty | integration | `pytest tests/test_export.py::test_export_csv_utf8_bom_one_row_per_duty -x` | ❌ Wave 0 |
| SEXP-03 | Frontend buttons trigger download | frontend | `npm test -- --testPathPattern conversation` | ❌ Wave 0 |
| SEXP-04 (SC 4) | Manager-track JSON/CSV 200 without OG | integration | `pytest tests/test_export.py::test_export_json_manager_no_409 -x` | ❌ Wave 0 |
| POST-01 | Poster DOCX contains "About the Organization" section | integration | `pytest tests/test_export.py::test_poster_org_context_section -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest v2/backend/tests/test_export.py -x -q`
- **Per wave merge:** `pytest v2/backend/tests/ -x -q` (179 existing must stay GREEN)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] 5 RED stubs in `test_export.py` (backend)
- [ ] 2 RED stubs in frontend conversation test (Export JSON + Export CSV buttons)

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | All WD data comes from the DB (already validated at PATCH time); no raw user input flows into CSV/JSON without prior validation |
| V4 Access Control | no | No auth layer in this project (local tool) |
| V6 Cryptography | no | No secrets in export paths |

**Threat: CSV injection (formula injection).** A duty text beginning with `=`, `+`, `-`, or `@` can execute as a formula in Excel. Mitigation: `csv.DictWriter` with `QUOTE_MINIMAL` does NOT protect against formula injection — it only quotes for RFC 4180 compliance. Since the WD builder is an internal HR tool (not public-facing), the risk is LOW. If desired, a prefix `'` (single quote) or a `csv.QUOTE_ALL` strategy would mitigate. **Recommendation for this phase:** Document the risk, do not mitigate, as the project has no auth layer and this is an internal tool. [ASSUMED: no additional security controls required for this internal HR tool — confirm with project owner if public release is planned]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | CSV injection mitigation is not required for this internal HR tool | Security Domain | Low — tool is not public-facing; no external users |
| A2 | `elements["key_activities"]["value"]` returns `DraftDuty` objects (not dicts) at the time JSON/CSV routes call `build_seven_elements` | Pitfall 3 | TypeError in CSV/JSON build — easy to catch in Wave 0 test |
| A3 | POST-01 does not require removing `require_og_confirmed` from `export_poster()` | Open Questions | Manager-track users can't download poster DOCX — but scope doesn't require it |

---

## Sources

### Primary (HIGH confidence) — verified in live codebase

- `/home/charles/job_description_builder/v2/backend/app/services/export_service.py` — `build_seven_elements`, `_build_poster_context`, `_build_v2_manifest`, `_ADVISOR_PLACEHOLDER`, `_og_level_str`, `_slugify_title`
- `/home/charles/job_description_builder/v2/backend/app/api/export.py` — existing route handlers, `_load_wd`, `require_og_confirmed` call sites
- `/home/charles/job_description_builder/v2/backend/scripts/build_poster_template.py` — `build()` function, self-verify block, `required` set
- `/home/charles/job_description_builder/v2/backend/tests/test_export.py` — fixture helpers, test patterns, 5 `build_seven_elements` unit tests
- `/home/charles/job_description_builder/v2/frontend/src/app.jsx` lines 614-676 — `exportAs()` implementation
- `/home/charles/job_description_builder/v2/frontend/src/conversation.jsx` lines 187-256 — `ReviewState` + `.export-row` + `.btn--export` pattern
- `/home/charles/job_description_builder/v2/backend/app/models/work_description.py` — `WorkDescription` fields including `org_context`, `wd_type`, `responsibilities_narrative`
- `/home/charles/job_description_builder/v2/backend/app/services/classification_gate.py` — manager bypass in `require_og_confirmed`

### Secondary (MEDIUM confidence)

- Python stdlib `csv` module documentation [ASSUMED consistent with Python 3.10 on this machine]
- UTF-8-BOM via `encode("utf-8-sig")` — standard Python encoding name [VERIFIED: stdlib behavior]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in live codebase; no new dependencies
- Architecture: HIGH — routing pattern, fixture helpers, and `build_seven_elements` all verified in source
- Pitfalls: HIGH — all pitfalls derived from direct code inspection, not speculation
- UTF-8-BOM CSV pattern: HIGH — stdlib behavior, same pattern used throughout Python ecosystem

**Research date:** 2026-06-24
**Valid until:** 2026-07-24 (stable stdlib + fastapi patterns; no fast-moving ecosystem)
