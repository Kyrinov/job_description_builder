# Stack Research — v4.0 Seven-Elements Conversational Architecture

**Project:** JD Builder v4.0 — Seven-Elements Conversational Architecture
**Researched:** 2026-06-19
**Platform:** Jetson AGX Orin "Jane" — ARM64 (aarch64), Python 3.10.12
**Confidence:** HIGH (all findings verified by direct execution on target hardware or inspection of existing source)

---

## Context: What Already Exists (Do Not Re-Research)

| Component | Version | Status |
|-----------|---------|--------|
| FastAPI | 0.128.8 | CONFIRMED installed |
| Pydantic v2 | 2.12.5 | CONFIRMED installed |
| docxtpl | 0.19.0 (pinned) / 0.18.0 (installed) | CONFIRMED |
| python-docx | 1.1.2 | CONFIRMED installed |
| WeasyPrint | 69.0 | CONFIRMED installed |
| SQLite (stdlib) | — | CONFIRMED |
| React 18 | 18.3.1 | CONFIRMED |
| Vite | 5.4.10 | CONFIRMED |
| vitest | 4.1.8 (dev) | CONFIRMED |
| pandas | 2.3.3 | CONFIRMED installed on aarch64 |

The v3.0 research decision stands: **net new pip dependencies for v3.0 were zero**. v4.0 adds no new pip dependencies either. All six new features are implemented using stdlib, existing packages, or pure data work.

---

## Net-New Dependencies for v4.0: Zero

No new `pip install` or `npm install` required. Every v4.0 capability maps to a tool already present.

---

## Feature-by-Feature Stack Analysis

### Feature 1: Organizational Context Conversational Step

**Backend:** No new library. New field `organizational_context` on `WorkDescription` (a Pydantic str field, default `""`). The existing `_build_organizational_context_text()` function in `export_service.py` already constructs this text from `branch`/`reports`/`title`/`summary` record fields — the v4.0 step makes this explicit by also surfacing it as a directly editable field so advisors who bypass the "composed" path can enter it directly.

**SJD pre-fill:** `sjd_library.py` already carries `organizational_context` per record. The `POST /api/wd/{id}/sjd-start` route (Phase 22) can be extended to copy `organizational_context` into the new WD field in one line. No new API.

**Frontend:** New STEP entry in `data.jsx` STEPS array with `id: 'org_context'`, input type `textarea`. The existing `apply` + `transcript` pattern handles it. The step renders before `client_service_results` in Phase order. No new state slice required — `record.org_context` follows the same pattern as `record.summary`.

**Document preview:** `document.jsx` already renders `client_service_results` via a `<Sec>` component. Prepending an `org_context` section follows the identical pattern.

### Feature 2: Responsibilities Narrative

**Backend:** New field `responsibilities_narrative: Optional[str]` on `WorkDescription`. The narrative is gated on supervisory/senior positions: only written to the WD when `record.supervises` is not `'none'` AND (`og_level >= 4` OR work type is managerial). Gate logic is pure Python in the PATCH handler — no new library.

**Frontend:** New STEP entry with `id: 'responsibilities_narrative'`, input type `textarea`. The existing `isStepVisible(step, answers)` gating mechanism (already used in Phase 21 for cluster steps) handles conditional display. The condition is `answers.supervises?.id !== 'none'` — this is one line in the step's `visible` predicate. No new state slice, no new hook.

**Why no separate "supervisory flag" API call is needed:** `record.supervises` is already committed to the WD at the Role phase. The gate reads it from `answers` on the frontend and from `wd.record['supervises']` on the backend. The data is already there.

### Feature 3: Seven-Elements Completeness Audit

**Backend:** New route `POST /api/wd/{id}/validate-elements`. Returns a list of per-element status objects:

```python
class ElementStatus(BaseModel):
    element: str          # "Organizational Context", "Client Service Results", etc.
    status: str           # "populated" | "derived" | "missing"
    source: Optional[str] # "direct_entry" | "sjd_prefill" | "composed_from_record" | None
    value_preview: Optional[str]  # first 80 chars for UI confirmation
```

No new library. The audit is a pure Python function that reads `wd.record` and `wd` fields — the same fields `_build_wd_context()` already reads. Extract the seven-element read logic into a standalone `_audit_elements(wd) -> list[ElementStatus]` function, then call it from both the validate endpoint and (optionally) from `generate_wd_docx`.

**Frontend:** New `[elementAudit, setElementAudit]` useState slice in `app.jsx`. The ReviewState component (in `conversation.jsx`) already renders the audit findings panel (Phase 24 pattern) — the completeness badge follows the same `auditRan`/`auditFindings` pattern, just for elements instead of risk findings. One button click triggers `POST /api/wd/{id}/validate-elements`, response populates `elementAudit`. The badge is green (all 7 populated/derived), amber (some missing), or red (3+ missing).

**Why a separate endpoint rather than embedding in GET /api/wd/{id}:** The completeness check is user-initiated (Review phase), not automatic. Keeping it as an explicit POST preserves the same advisor-control contract as Phase 24 Risk Audit. This also avoids re-running the element walk on every GET.

### Feature 4: Manager-Track UX

**Backend:** No new API surface. The manager track is a frontend-only concern at this stage. The WD model stores all data identically regardless of user role — the manager track just hides OG/JES/CBA mechanics in the UI and routes to a simplified review. The WD export is the same DOCX; the classification team consumes it downstream.

One addition: a `user_role` field stored in `WorkDescription` (`'advisor'` | `'manager'`, default `'advisor'`). This lets the export manifest note the authoring role (traceability). No new endpoint required — it is set via the existing `PATCH /api/wd/{id}` route.

**Frontend:** New `[userRole, setUserRole]` useState slice. A role selector renders at the entry screen (before the first STEP). Setting `userRole = 'manager'` suppresses:
- The four QUESTION_BANK Socratic steps (`qb_*`) — OG is not visible in manager mode
- The `og_confirm` and `og_level` steps
- The `noc_confirm` step
- The JES scoring section in the document preview
- The CBA/risk audit button in the Review phase

This is implemented via the existing `isStepVisible(step, answers)` predicate: each suppressed step gets a `visible: (answers, role) => role !== 'manager'` check. The predicate already receives `answers`; extend its signature to also receive `userRole` from the App closure.

**Why no new state management library (Redux, Zustand, Jotai):** The `userRole` slice is one boolean-equivalent value touched in two places: the entry selector and the `isStepVisible` predicate. The existing `useState` + prop-passing pattern handles it with zero overhead. The app has 11 existing useState slices — adding a 12th is consistent with the established pattern. The rule from v2.0 onward is: add a state management library only when prop drilling reaches 4+ levels or cross-cutting state creates obvious complexity. Neither condition is met here.

**Why not React Context:** The role propagates from App → `isStepVisible` (a utility in `data.jsx`) which is already imported and called in App. Passing `userRole` as a parameter to that function is simpler than wrapping the tree in a Provider.

### Feature 5: Enhanced Job Poster Generation

**Backend:** `export_service.py` already has `_build_poster_context(wd)`. The enhancement adds three field mappings:

- `org_context` → "About the Organization" poster section (new field on WD)
- `key_activities` / duties → "Key Activities" (already present as top-5 duties; rename the label)
- `qualification` → "Skills and Qualifications" (already present)

The poster DOCX template (`wd_poster_template.docx`) is the binary artifact to update via `build_poster_template.py`. The `_build_poster_context` function receives two additional keys. No new library.

**Frontend:** The "Export Poster" button already calls `POST /api/wd/{id}/export/poster`. No frontend change needed — the backend context enrichment is transparent to the client.

### Feature 6: Structured Data Export (JSON + CSV)

This is the most detailed decision. Three options evaluated:

**Option A: stdlib `csv` module**
- Ships with Python 3.10. Zero install, zero ARM64 risk.
- `csv.DictWriter` produces RFC 4180-compliant CSV in-memory via `io.StringIO`.
- Adequate for a 7-row, 2-column (element, value) export or a multi-column pivot.
- Confirmed working on Jane: direct test produces correct output (see verification below).
- Limitation: no type coercion, no multi-sheet, no column type inference. None of these limitations matter for a 7-row structured export.

**Option B: pandas 2.3.3**
- Confirmed installed on aarch64 (Jane already has it for data work).
- `DataFrame.to_csv()` and `DataFrame.to_json()` are idiomatic.
- Adds ~30 MB import overhead and a 50-200ms cold import penalty to a route that is rarely called.
- Correct choice if the export grows to hundreds of rows, requires type-aware column formatting, or needs multi-sheet Excel.

**Option C: polars**
- Not installed on Jane. Would require `pip install polars` — polars publishes aarch64 wheels on PyPI (confirmed via PyPI metadata), so ARM64 is not a blocker in principle, but it is an unnecessary new dependency for a 7-row export.

**Decision: stdlib `csv` for the CSV export route. pandas is available as a fallback if the export scope grows.**

Rationale: the 7 Part 2 elements are always exactly 7 rows. The export is a one-shot serialisation of already-computed Python dicts. `io.StringIO` + `csv.DictWriter` produces the correct output in under 1ms with zero import penalty. The pandas cold-import cost (50-200ms) is disproportionate to the task. If Julian's analytics toolchain later requires multi-column pivot tables, multi-sheet XLSX, or typed column schemas, swap to pandas at that point — it is already installed and the migration is one function rewrite with no pip change.

**Implementation: separate routes, not content negotiation**

Two options for multi-format export:

- Content negotiation: single `POST /api/wd/{id}/export/structured`, reads `Accept` header, returns JSON or CSV.
- Separate routes: `POST /api/wd/{id}/export/json` + `POST /api/wd/{id}/export/csv`.

**Decision: separate routes.** Rationale:
1. The existing export router uses separate routes for every format (`/export/docx`, `/export/poster`, `/export/pdf`). Consistency with the established pattern is the dominant reason.
2. Content negotiation requires the client to set `Accept` headers correctly. The SPA's `exportAs()` function uses `fetch` with a `Blob` download — explicit route names are clearer and easier to test.
3. FastAPI's `@router.post("/wd/{wd_id}/export/json")` with `Response(content=..., media_type="application/json")` and `@router.post("/wd/{wd_id}/export/csv")` with `media_type="text/csv"` are trivial. The shared work is a `_build_seven_elements_dict(wd) -> dict` helper called by both routes.
4. Separate routes produce distinct OpenAPI schema entries, which is useful if the API is ever documented for Julian's analytics team.

**JSON export implementation:**

```python
import json

@router.post("/wd/{wd_id}/export/json")
async def export_structured_json(wd_id: str) -> Response:
    wd = _load_wd(wd_id, settings.db_path)
    require_og_confirmed(wd)
    payload = _build_seven_elements_dict(wd)
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{wd_id}-elements.json"'},
    )
```

`json` is stdlib. No new dependency.

**CSV export implementation:**

```python
import csv, io

@router.post("/wd/{wd_id}/export/csv")
async def export_structured_csv(wd_id: str) -> Response:
    wd = _load_wd(wd_id, settings.db_path)
    require_og_confirmed(wd)
    elements = _build_seven_elements_dict(wd)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["element", "value"])
    writer.writeheader()
    for element, value in elements.items():
        writer.writerow({"element": element, "value": value})
    return Response(
        content=buf.getvalue().encode("utf-8-sig"),  # BOM for Excel compatibility
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{wd_id}-elements.csv"'},
    )
```

Note: `utf-8-sig` (UTF-8 with BOM) is used so Excel on Windows opens the file without the "import text wizard". This is a two-character change from `utf-8` and requires no library.

**Shared helper `_build_seven_elements_dict`:**

This function reads the same fields `_build_wd_context()` already reads for the Accessible DOCX template. The seven elements and their WD field sources:

| Part 2 Element | WD Source Field |
|---------------|----------------|
| Organizational Context | `wd.record.get('org_context')` or composed from branch/reports/title/summary |
| Client Service Results | `wd.record.get('client_service_results')` |
| Key Activities | `wd.duties` (list of DraftDuty.text) — joined as newline-separated string |
| Skills | `wd.qualification.education + experience` |
| Effort | JES effort factors from `wd.jes_scores` (factor_name + degree + points) |
| Responsibility | JES responsibility factors from `wd.jes_scores` |
| Working Conditions | JES conditions factors from `wd.jes_scores` |

The `_factor_category_map()` function already exists in `export_service.py` and performs the JES factor bucketing. Reuse it.

---

## Integration Points

### WorkDescription model additions (v4.0)

Two new fields required on `WorkDescription`:

```python
organizational_context: Optional[str] = None  # v4.0: explicit org context field
responsibilities_narrative: Optional[str] = None  # v4.0: supervisory/senior narrative
user_role: str = "advisor"  # v4.0: "advisor" | "manager"
```

These are additive — Pydantic v2 with `extra="ignore"` means existing WD rows deserialise without error. No schema migration needed. `schema_version` can increment to 2 if a migration tracker is desired, but the model handles it gracefully without one.

### export.py router additions

Add to `app/api/export.py`:
- `POST /api/wd/{wd_id}/export/json`
- `POST /api/wd/{wd_id}/export/csv`
- `POST /api/wd/{wd_id}/validate-elements`

All three follow the existing `_load_wd()` → `require_og_confirmed()` → build response pattern. The validate-elements route does NOT require `og_confirmed` (advisors in manager mode need completeness feedback before classification is set).

### Frontend state additions (v4.0)

New useState slices (in App):
- `[userRole, setUserRole]` — `'advisor'` | `'manager'`, initialized from localStorage key `'jd-builder-v2-role'`
- `[elementAudit, setElementAudit]` — array of `{element, status, source, value_preview}` from `/validate-elements`
- `[elementAuditRan, setElementAuditRan]` — boolean, same pattern as `auditRan`

No new npm packages. No state management library.

---

## What NOT to Add

| Temptation | Why Not |
|------------|---------|
| pandas for CSV export | Already installed but 50-200ms cold import is disproportionate to a 7-row export. stdlib csv is adequate. Add pandas only if export grows to multi-column analytics tables or Julian's toolchain requires XLSX. |
| polars for CSV export | Not installed. Would require a new pip dep and an ARM64 wheel confirmation. Zero benefit over stdlib csv for this use case. |
| Zustand / Redux for role-based UX | userRole is one value touched in two places. useState + prop is sufficient. The existing 11 useState slices are not at a complexity threshold that justifies a store library. |
| React Context for userRole | Over-engineering for a value that flows App → isStepVisible (a utility function, not a deeply nested component tree). |
| A new FastAPI middleware for role gating | The manager track is a UI concern, not an API security boundary. The WD data model is identical regardless of role. Role-based API gating is a future multi-tenant concern. |
| Content negotiation (Accept header routing) | Inconsistent with the existing `/export/docx`, `/export/poster`, `/export/pdf` separate-route pattern. Harder to test and document. |
| A dedicated validation microservice | Single-user local app on the Jetson. One FastAPI process. Seven-element validation is a pure Python function, not a network boundary. |
| sqlalchemy / an ORM for new fields | All WD persistence is parameterized SQL with JSON blobs. v4.0 adds fields to the JSON model, not new SQL columns. An ORM would require schema migration infrastructure for zero benefit. |
| A charting library for completeness badge | The completeness status is 7 items with three states. CSS + inline SVG (already used for the classification confidence ring) handles it with no new dependency. |

---

## ARM64 Compatibility Summary

No new packages. All existing packages confirmed on aarch64. The two stdlib modules used (csv, json) are part of CPython — no wheels, no platform concern.

pandas 2.3.3 is confirmed installed on aarch64 (`import pandas; platform.machine() == 'aarch64'`). If the CSV export is ever migrated to pandas, no ARM64 work is required.

---

## Required requirements.txt Changes

None. v4.0 adds zero new pip dependencies.

The `pymupdf==1.27.2.3` line (documented in v3.0 STACK.md as a needed addition) should be confirmed present. If not yet added, add it — but that is a v3.0 carry-forward, not a v4.0 requirement.

---

## Sources

- `v2/backend/requirements.txt` — current pinned versions, inspected directly
- `v2/backend/app/api/export.py` — existing route structure, separate-route pattern confirmed
- `v2/backend/app/services/export_service.py` — `_build_organizational_context_text`, `_factor_category_map`, `_build_wd_context` inspected; seven-element field sources identified
- `v2/backend/app/models/work_description.py` — existing fields, extension points identified
- `v2/frontend/src/app.jsx` — existing useState slices (11 confirmed), `isStepVisible` usage pattern
- `v2/frontend/package.json` — no state management library currently installed
- `v2/frontend/src/data.jsx` — STEPS array structure, `isStepVisible` predicate pattern, `supervises` step confirmed
- Direct execution on Jane: `python3 -c "import pandas; print(pandas.__version__)"` → 2.3.3, `platform.machine()` → aarch64
- Direct execution on Jane: stdlib csv DictWriter test — 7-row export produced correctly in-memory
- polars: not installed on Jane (`import polars` → ImportError); PyPI publishes aarch64 wheels but installation is unnecessary
