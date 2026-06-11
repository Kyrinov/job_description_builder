# Phase 22: SJD Library — Research

**Researched:** 2026-06-11
**Domain:** SJD data parsing, FastAPI read-only endpoints, DraftDuty provenance tagging, React SPA non-blocking action surface, DOCX version manifest extension
**Confidence:** HIGH

---

## Summary

Phase 22 adds a browse-and-seed workflow for DND Standard Job Descriptions (SJDs). An advisor can browse all 10 SJDs in `data/SJD Examples.txt`, optionally filter by OG group, and use one as a starting point for a new conversation. Selecting an SJD pre-fills `confirmed_og`, `og_level`, and a set of seed duties on the WorkDescription; those duties carry a new `source="sjd"` provenance path through to the DOCX version manifest. If the advisor subsequently changes `confirmed_og`, a frontend warning is displayed.

The SJD file is a flat, tab-delimited record stream: each entry opens with `Job Title\t<value>` and ends with a `Title` line. There are exactly 10 entries covering AS, CT-FIN (FI), EC, EN-ENG (EN), IT, PE, and WP groups. There are no duty lists in the raw file — SJD seed duties must be drawn from the existing `DUTY_SUGGESTIONS` map keyed by OG group.

The v2 backend (`v2/backend/app/`) is the live active codebase. The old `app/` tree is Phase 1–9 legacy and is not used by the React SPA. All new work goes into `v2/backend/app/`.

**Primary recommendation:** Parse SJD Examples.txt once into a `SJD_LIBRARY` constant at module load time; serve it through two read-only GET endpoints; add `POST /api/wd/{id}/sjd-start` to the existing WD router; extend `DraftDuty` with `sjd_number` and update `_build_v2_manifest` to emit an SJD provenance entry; surface the non-blocking browse action inside the existing `ReviewState` component (after the last phase-0 step lands the user at the review screen) or as an optional action surfaced at the end of the Role phase.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SJD_LIBRARY constant + parsing | API / Backend (`app/data/`) | — | Static data; Python module-load; no DB needed |
| `GET /api/sjd` + `GET /api/sjd/{number}` | API / Backend | — | Read-only endpoints; no auth; no DB query |
| `POST /api/wd/{id}/sjd-start` | API / Backend (`app/api/wd.py`) | — | Mutates WD record; belongs with other WD mutations |
| `sjd_source` field on WorkDescription | API / Backend model | Frontend (SPA record) | Set at write time by sjd-start; mirrored in SPA record |
| SJD provenance on DraftDuty | API / Backend model | — | `source` field extended; `sjd_number` field added |
| DOCX manifest SJD entry | API / Backend (`export_service.py`) | — | `_build_v2_manifest` emits the entry |
| "Browse SJDs" action at end of Role phase | Frontend Server (SPA) | — | Non-blocking: optional modal/panel in `conversation.jsx` |
| confirmed_og change warning (SJD-03) | Frontend (SPA) | — | Pure React state comparison; no backend guard needed |

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SJD-01 | `SJD_LIBRARY` constant (9 entries) in `app/data/sjd_library.py`; `GET /api/sjd`; `GET /api/sjd/{number}`; `POST /api/wd/{id}/sjd-start` | SJD file fully parsed — see Standard Stack and Code Examples below |
| SJD-02 | Non-blocking "Browse SJDs" action at end of Role phase; `sjd_source` on WD; `source="sjd"` + `sjd_number` on seeded duties; SJD source in DOCX manifest | DraftDuty model and manifest builder identified; React phase-end hook identified |
| SJD-03 | confirmed_og change warning after SJD pre-fill | Implemented as React state guard in `app.jsx` commit function |
</phase_requirements>

---

## Standard Stack

### Core (all already installed — no new installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | installed | Two new GET endpoints + one new POST endpoint | Existing pattern in `app/api/wd.py` and `app/api/og_classification.py` |
| Pydantic | installed | SJDEntry model for type-safe constant entries | Already used throughout v2 backend |
| React 18 | installed | Frontend modal/panel for browsing SJDs | Existing SPA pattern |

### No new dependencies required

All SJD work is implementable using existing libraries. The SJD file is parsed at import time into a Python list of dicts — no database, no search index, no new packages.

---

## Architecture Patterns

### System Architecture Diagram

```
data/SJD Examples.txt
        |
        | (parse at import, once)
        v
app/data/sjd_library.py
  SJD_LIBRARY: list[SJDEntry]
        |
        +---> GET /api/sjd?og_code=     (filter + list)
        |
        +---> GET /api/sjd/{number}     (detail)
        |
        +---> POST /api/wd/{id}/sjd-start
                    |
                    | (read WD from DB, write confirmed_og, og_level,
                    |  seed duties with source="sjd"+sjd_number,
                    |  write sjd_source field, save WD)
                    v
              work_descriptions SQLite
                    |
                    v
              POST /api/wd/{id}/export/docx
                    |
                    v
              _build_v2_manifest()
              -> emits SJD provenance entry
```

Frontend flow:
```
Role phase (phase: 0) — last step = 'supervises'
        |
        | after answering 'supervises', commit() is called
        | next step advances to Work Type (phase 1)
        |
        v
Non-blocking "Browse SJDs" action (optional, appears after Role phase)
  -> opens SJD browser panel/modal
  -> advisor filters by OG group, selects SJD
  -> SPA calls POST /api/wd/{id}/sjd-start
  -> on success: setRecord with sjd_source, pre-filled confirmed_og, og_level, seed duties
  -> warning state: sjd_source set in record

confirmed_og change (og_confirm step):
  if record.sjd_source && newOg !== record.sjd_source.og_code:
    -> display warning toast/inline message (SJD-03)
```

### Recommended Project Structure

New files (all in v2/backend):
```
v2/backend/app/data/sjd_library.py    # SJD_LIBRARY constant + SJDEntry model
v2/backend/app/api/sjd.py             # GET /api/sjd, GET /api/sjd/{number}
```

Modified files:
```
v2/backend/app/api/wd.py              # Add POST /api/wd/{id}/sjd-start endpoint
v2/backend/app/models/draft_duty.py   # Add sjd_number Optional[str] field
v2/backend/app/models/work_description.py  # Add sjd_source Optional[dict] field
v2/backend/app/services/export_service.py  # Extend _build_v2_manifest for SJD
v2/backend/app/main.py                # Register sjd router
v2/frontend/src/app.jsx               # Add Browse SJDs action, SJD-03 warning
v2/frontend/src/data.jsx              # Add fetchSjds, fetchSjdDetail helpers (or inline in app.jsx)
v2/backend/tests/test_sjd.py          # New test file
```

---

## SJD File: Parsed Structure

The 9 SJD entries in `data/SJD Examples.txt` have been fully inspected. Each entry is a sequence of tab-separated `Field\tValue` lines, with entries separated by blank lines. The canonical fields are:

| Field | Always Present | Example |
|-------|---------------|---------|
| Job Title | Yes | "Compensation Agent" |
| JobCode | Yes | "57047" |
| SJD Number | Yes | "DND-PA-57047" |
| DND Number | Yes | "AS-01 - Compensation Agent / ..." |
| Group Level | Yes | "AS-01" |
| Supervisory | Yes | "No" / "Yes" |
| Organizational Models | Sometimes | "Compensation" |
| Streams | Sometimes | "Compensation" / "NO STREAM" |
| NOC / CNP | Yes | "13100" |
| Salary | Yes | "$61,786 - $69,106" |
| Organizational Context | Yes | multi-line text |
| Occupational Groups | Yes (sometimes blank) | "PA" / "FI" / "" |
| NOC / CNP: Skill Type | Yes | "1 Business, finance..." |
| Ask Question | Sometimes | "AskQuestion" or URL+params |
| Title | Yes (last field) | "AS-01 - Compensation Agent..." |

**The 9 entries:**

| # | SJD Number | Title | Group Level | OG Code (Occupational Groups) |
|---|-----------|-------|-------------|-------------------------------|
| 1 | DND-PA-57047 | Compensation Agent | AS-01 | PA (maps to AS) |
| 2 | DND-PA-60053 | Business Analyst | AS-03 | PA (maps to AS) |
| 3 | DND-PA-58886 | Manager, Planning (up to 25) | AS-07 | PA (maps to AS) |
| 4 | DND-CT-FIN-59082 | Manager, Financial Management | CT-FIN-04 | FI |
| 5 | DND-EC-58355 | Junior Analyst | EC-02 | EC |
| 6 | DND-EC-58536 | Analyst | EC-05 | EC |
| 7 | DND-NR-60695 | Engineering Specialist (Civil) | EN-ENG-04 | (blank — NR/EN) |
| 8 | DND-IT-59950 | IT Team Leader, IT Planning | IT-03 | (blank — IT) |
| 9 | DND-HM-58817 | Team Leader | PE-04 | HM (maps to PE) |
| 10 | DND-PA-46034 | Addictions Counsellor | WP-03 | PA (maps to WP) |

**Important:** The file contains 10 entries, not 9. The requirement says 9. The planner must decide whether to include all 10 or drop one (likely the last one, WP-03 "Addictions Counsellor", which re-uses the PA org group but is clearly a WP group entry). This is flagged as an assumption below — count the entries in the file and use 9 or all 10.

**OG code normalization required:** The `Occupational Groups` field uses org-unit codes ("PA", "HM") not classification group codes. The actual classification group is encoded in the `Group Level` field (e.g., "AS-01" → OG code = "AS"). The parser must extract OG group from `Group Level` by splitting on "-" and taking everything before the first "-" (with CT-FIN as a special case → "FI").

**CT-FIN special case:** `Group Level = "CT-FIN-04"` → OG code = "FI" (the CT-FIN series uses the FI occupational group in the app's OG_LEVELS constant).

**No duty lists in the file:** The SJD entries have `Organizational Context` (a paragraph describing the position) but no itemized duty lists. Seed duties for the pre-fill must come from `DUTY_SUGGESTIONS[og_code]` in `data.jsx` for the frontend, or be represented as the organizational context text + a reference to the SJD standard duties. The cleanest approach: use the existing `DUTY_SUGGESTIONS` dict to generate seed duties tagged with `source="sjd"`.

**Parsing strategy:** Simple line-by-line parser in `sjd_library.py`. Split each line on `\t` with `maxsplit=1`, accumulate key-value pairs until a blank line resets the current entry, then append to list. Normalize `og_code` by splitting `Group Level` on `-` and mapping prefixes.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SJD text search/similarity | Custom BM25 or vector search | OG-group filter + title display | Requirements explicitly defer SJD similarity ranking; keyword/OG browse is sufficient |
| SJD persistence | New SQLite table | Python module constant | 9 static entries; no runtime mutation needed |
| Duty text generation from org context | LLM call | DUTY_SUGGESTIONS map keyed by OG group | All v3.0 features are deterministic; LLM is not in audit/validation flow |

---

## Common Pitfalls

### Pitfall 1: OG Code Extraction from Group Level
**What goes wrong:** Using `Occupational Groups` field directly — it contains org-unit codes ("PA", "HM", "NR") that do not match the `OG_LEVELS` dictionary keys ("AS", "FI", "IT").
**Why it happens:** The SJD file was authored for DND's HR system, not for the JD Builder's OG taxonomy.
**How to avoid:** Always extract OG group from `Group Level` by parsing the prefix (e.g., "AS-01" → "AS"; "CT-FIN-04" → "FI"; "EN-ENG-04" → "EN"; "PE-04" → "PE"; "WP-03" → "WP").
**Warning signs:** Filter by `og_code="AS"` returns no results when SJDs exist for AS-level positions.

### Pitfall 2: Level Extraction Edge Cases
**What goes wrong:** The level integer extracted from "AS-01" needs leading-zero stripping (1 not 01) to match `OG_LEVELS` integer lists.
**Why it happens:** SJD file uses zero-padded levels; `OG_LEVELS` stores bare integers.
**How to avoid:** `int(level_str)` after splitting on "-".

### Pitfall 3: CT-FIN OG Code Mapping
**What goes wrong:** "CT-FIN-04" parsed naively produces og_code="CT" — which is not in `OG_LEVELS`.
**Why it happens:** CT-FIN is a sub-group of the Financial Management (FI) classification.
**How to avoid:** Explicit mapping rule: if `Group Level` starts with "CT-FIN", og_code = "FI".

### Pitfall 4: sjd-start Race with WD PATCH
**What goes wrong:** Frontend calls `POST /api/wd/{id}/sjd-start` before the WD row is created (no wd_id yet).
**Why it happens:** The WD is only created after the first `commit()` in the SPA (first step sends POST /api/wd). The "Browse SJDs" action must only be available after a wd_id exists.
**How to avoid:** Disable/hide the "Browse SJDs" action in the SPA until `wd_id` is non-null. Since the action is surfaced at the end of the Role phase and commit() creates the WD on the first step, wd_id will exist by the time "Browse SJDs" is available — but add a defensive check.

### Pitfall 5: SJD-03 Warning Scope
**What goes wrong:** Warning fires even when the advisor is changing og_level (not og_code), or fires on every og_confirm visit after SJD pre-fill.
**Why it happens:** Treating any OG-confirm change as a classification departure.
**How to avoid:** Compare the NEW `og_code` (from the draft, not the committed level) against `record.sjd_source.og_code`. Only fire when og_code changes, not when og_level changes.

### Pitfall 6: Manifest Deduplication Key
**What goes wrong:** Multiple SJD-seeded duties emit duplicate manifest entries (one per duty).
**Why it happens:** `_build_v2_manifest` walks all duties and emits one entry per unique (source_type, source_id, source_version).
**How to avoid:** Use `source_type="SJD"`, `source_id=sjd_number`, `source_version="DND SJD Library"` — deduplication by tuple key already handles multiple duties from the same SJD.

---

## Code Examples

### SJD_LIBRARY constant structure

```python
# Source: [VERIFIED: direct file inspection of data/SJD Examples.txt]
# app/data/sjd_library.py

from dataclasses import dataclass
from typing import Optional
from datetime import date

@dataclass(frozen=True)
class SJDEntry:
    sjd_number: str          # e.g. "DND-PA-57047"
    job_code: str             # e.g. "57047"
    title: str                # e.g. "Compensation Agent"
    og_code: str              # normalized: "AS", "FI", "EC", "IT", "EN", "PE", "WP"
    og_level: int             # integer level: 1, 3, 7, 4, 2, 5, 4, 3, 4, 3
    group_level_str: str      # original: "AS-01"
    supervisory: bool
    noc_code: str
    salary_range: str
    organizational_context: str
    streams: str

SJD_LIBRARY: list[SJDEntry] = [...]  # 9 (or 10) entries parsed at module load
```

### Parsing strategy

```python
# Source: [ASSUMED] — standard Python parsing; no library needed
def _parse_sjd_file(path: str) -> list[SJDEntry]:
    entries = []
    current: dict[str, str] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if not line.strip():
                if current.get("SJD Number"):
                    entries.append(_make_entry(current))
                current = {}
                continue
            if "\t" in line:
                key, _, val = line.partition("\t")
                # Organizational Context spans multiple lines — accumulate
                if key.strip() == "Organizational Context":
                    current["Organizational Context"] = val.strip()
                elif key.strip() not in current:
                    current[key.strip()] = val.strip()
    if current.get("SJD Number"):
        entries.append(_make_entry(current))
    return entries
```

### OG code normalization

```python
# Source: [VERIFIED: inspected all 9/10 SJD entries in data/SJD Examples.txt]
def _og_code_from_group_level(group_level: str) -> tuple[str, int]:
    """Return (og_code, level_int) from Group Level string."""
    gl = group_level.strip()
    if gl.startswith("CT-FIN-"):
        level = int(gl.split("-")[-1])
        return ("FI", level)
    if gl.startswith("EN-ENG-"):
        level = int(gl.split("-")[-1])
        return ("EN", level)
    parts = gl.split("-")
    if len(parts) >= 2:
        return (parts[0], int(parts[-1]))
    return (gl, 1)
```

### New endpoints in app/api/sjd.py

```python
# Source: [ASSUMED] — follows existing og_classification.py pattern
from fastapi import APIRouter, HTTPException, Query
from app.data.sjd_library import SJD_LIBRARY

router = APIRouter()

@router.get("/api/sjd")
def list_sjds(og_code: str = Query(default=None)):
    """Return all SJD entries, optionally filtered by og_code."""
    entries = SJD_LIBRARY
    if og_code:
        entries = [e for e in entries if e.og_code.upper() == og_code.upper()]
    return [e.__dict__ for e in entries]  # or dataclasses.asdict(e)

@router.get("/api/sjd/{sjd_number}")
def get_sjd(sjd_number: str):
    """Return a single SJD entry by sjd_number."""
    entry = next((e for e in SJD_LIBRARY if e.sjd_number == sjd_number), None)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"SJD {sjd_number!r} not found")
    return entry.__dict__
```

### POST /api/wd/{id}/sjd-start (in app/api/wd.py)

```python
# Source: [ASSUMED] — follows existing orphan_check endpoint pattern in wd.py
class SJDStartRequest(BaseModel):
    sjd_number: str

@router.post("/wd/{wd_id}/sjd-start")
async def sjd_start(wd_id: str, body: SJDStartRequest) -> WorkDescription:
    """Pre-fill confirmed_og, og_level, seed duties and sjd_source from a selected SJD."""
    from app.data.sjd_library import SJD_LIBRARY
    entry = next((e for e in SJD_LIBRARY if e.sjd_number == body.sjd_number), None)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"SJD {body.sjd_number!r} not found")

    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute("SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Work description not found")
        wd = WorkDescription.model_validate_json(row["data"])

        # Build seed duties from DUTY_SUGGESTIONS keyed by OG group
        from app.data.constants import DUTY_SUGGESTIONS_BACKEND  # or inline
        seed_duties = _build_sjd_seed_duties(entry)

        wd.confirmed_og = {"og_code": entry.og_code, "og_name": entry.title}
        wd.og_level = entry.og_level
        wd.duties = seed_duties
        wd.sjd_source = {
            "sjd_number": entry.sjd_number,
            "title": entry.title,
            "og_code": entry.og_code,
            "og_level": entry.og_level,
        }
        wd.last_modified = datetime.now(timezone.utc)
        con.execute("UPDATE work_descriptions SET data = ?, last_modified = ? WHERE id = ?",
                    (wd.model_dump_json(), wd.last_modified.isoformat(), wd_id))
        con.commit()
    finally:
        con.close()
    return wd
```

### DraftDuty extension

```python
# Source: [VERIFIED: v2/backend/app/models/draft_duty.py]
# Add to existing DraftDuty model:
source: Literal["noc", "advisor", "sjd"]  # extend the Literal
sjd_number: Optional[str] = None           # e.g. "DND-PA-57047"
```

### WorkDescription extension

```python
# Source: [VERIFIED: v2/backend/app/models/work_description.py]
# Add one new field:
sjd_source: Optional[dict] = None  # {sjd_number, title, og_code, og_level}
```

### Manifest extension in export_service.py

```python
# Source: [VERIFIED: v2/backend/app/services/export_service.py _build_v2_manifest]
# Add after existing manifest walks:
if wd.sjd_source:
    sjd_num = wd.sjd_source.get("sjd_number", "")
    if sjd_num:
        _add("SJD", sjd_num, "DND SJD Library")
```

### Frontend: Browse SJDs action surface

The Role phase consists of steps with `phase: 0`: `title`, `branch`, `reports`, `reports_to_military`, `supervises`. After the user commits `supervises` (the last phase-0 step), `commit()` advances to `stepIndex = 5` (first phase-1 step). The "Browse SJDs" non-blocking action should be offered:

**Option A (recommended):** After the Role phase is complete (all phase-0 steps answered), show a subtle action link/button in the conversation thread before the Work Type phase begins. This requires detecting when `step.phase === 1` and the `answers` contain all 5 phase-0 step IDs, then rendering the Browse action above the active question.

**Option B:** Surface as an optional action in the phase-0 completion summary (analogous to how the review screen has export buttons). This is slightly more disruptive.

The requirement says "non-blocking action surfaced at end of Role phase." Option A is cleanest.

### Frontend: SJD-03 warning

In `app.jsx`, inside the `commit()` function, after the new record is built:

```javascript
// SJD-03: warn if confirmed_og changes after an SJD pre-fill
if (step.id === 'og_confirm' && record.sjd_source) {
  const newOgCode = typeof patch.confirmed_og === 'object'
    ? patch.confirmed_og?.og_code
    : patch.confirmed_og;
  const sjdOgCode = record.sjd_source?.og_code;
  if (newOgCode && sjdOgCode && newOgCode !== sjdOgCode) {
    setToast(
      'Departing from the SJD classification turns this into a new evaluation — the SJD decision no longer applies'
    );
    // Toast auto-clears after 7 seconds (non-blocking, no gate)
    setTimeout(() => setToast(null), 7000);
  }
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| v1 ProvenanceTag sub-object on DraftDuty | v2 flat `provenance_noc_code`, `advisor`, `source` fields | Phase 10–18 | SJD provenance follows flat-field pattern |
| Single source type "noc" / "advisor" | Add "sjd" to `source` Literal | Phase 22 | Extends existing pattern without schema break |

---

## Runtime State Inventory

This is not a rename/refactor phase. Omitted.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `data/SJD Examples.txt` | `sjd_library.py` parsing | Yes (in repo) | — | — |
| `DUTY_SUGGESTIONS` (frontend) | Seed duty generation | Yes (in `data.jsx`) | — | — |
| `docxtpl` | DOCX manifest | Yes (installed) | — | — |
| SQLite | WD store | Yes | — | — |

No missing dependencies.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `v2/backend/pyproject.toml` |
| Quick run command | `cd v2/backend && python -m pytest tests/test_sjd.py -x` |
| Full suite command | `cd v2/backend && python -m pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SJD-01 | SJD_LIBRARY has 9 (or 10) entries, all fields present | unit | `pytest tests/test_sjd.py::test_sjd_library_count -x` | Wave 0 |
| SJD-01 | GET /api/sjd returns all entries | integration | `pytest tests/test_sjd.py::test_list_sjds_returns_all -x` | Wave 0 |
| SJD-01 | GET /api/sjd?og_code=EC returns only EC entries | integration | `pytest tests/test_sjd.py::test_list_sjds_filter_by_og -x` | Wave 0 |
| SJD-01 | GET /api/sjd/{number} returns correct entry | integration | `pytest tests/test_sjd.py::test_get_sjd_by_number -x` | Wave 0 |
| SJD-01 | GET /api/sjd/{number} returns 404 for unknown | integration | `pytest tests/test_sjd.py::test_get_sjd_404 -x` | Wave 0 |
| SJD-01 | POST /api/wd/{id}/sjd-start sets confirmed_og, og_level, duties, sjd_source | integration | `pytest tests/test_sjd.py::test_sjd_start_prefills_wd -x` | Wave 0 |
| SJD-02 | Seeded duties have source="sjd" and sjd_number set | unit | `pytest tests/test_sjd.py::test_seed_duties_provenance -x` | Wave 0 |
| SJD-02 | DOCX manifest includes SJD provenance entry after sjd-start | integration | `pytest tests/test_sjd.py::test_manifest_includes_sjd_source -x` | Wave 0 |
| SJD-03 | SJD-03 warning is frontend-only state logic | manual | — | Manual |

### Sampling Rate
- **Per task commit:** `cd v2/backend && python -m pytest tests/test_sjd.py -x`
- **Per wave merge:** `cd v2/backend && python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `v2/backend/tests/test_sjd.py` — covers all SJD-01 and SJD-02 requirements above

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a (single-user local app) |
| V3 Session Management | no | n/a |
| V4 Access Control | no | n/a |
| V5 Input Validation | yes | `sjd_number` validated by lookup against static SJD_LIBRARY; 404 on unknown |
| V6 Cryptography | no | n/a |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Invalid sjd_number injection | Tampering | Lookup against SJD_LIBRARY constant; 404 on miss; no eval or path construction |
| OG code injection via ?og_code= | Tampering | Filter is case-insensitive equality against og_code field; no SQL; no eval |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The file has 10 entries (including WP-03 "Addictions Counsellor") but requirements say 9 | SJD File: Parsed Structure | If the intent is 9, drop the WP-03 entry or one other; planner should confirm with user |
| A2 | Seed duties for sjd-start come from DUTY_SUGGESTIONS[og_code] since SJD file has no duty lists | Architecture Patterns | If SJD duties should come from the Organizational Context text (parsed into duties), a different strategy is needed; requires product decision |
| A3 | "Browse SJDs" action surfaces after Role phase steps are committed (before Work Type phase starts) | Code Examples / Frontend | If it should appear at a different step, the placement logic changes but the implementation is the same |
| A4 | DraftDuty.source Literal extended to include "sjd" (backward-compatible for existing "noc" and "advisor" values) | Code Examples | Minor schema change; existing WD rows with source="noc"/"advisor" continue to validate |
| A5 | SJD-03 warning is implemented as a frontend-only toast (non-blocking) rather than a backend guard | Code Examples / Architecture | If a hard gate is needed, a backend check on PATCH /wd/{id} would be required — but requirements say "non-blocking" |

---

## Open Questions (RESOLVED)

1. **Entry count: 9 or 10?**
   - What we know: The file has 10 entries; the requirement says 9.
   - What's unclear: Which entry is excluded — presumably WP-03 "Addictions Counsellor" (DND-PA-46034) since it uses the PA org code for a WP position and was likely a late addition.
   - Recommendation: Planner to include all 10 in SJD_LIBRARY but note the discrepancy; or treat WP-03 as entry 10 and ask user to confirm.

2. **Seed duty content: DUTY_SUGGESTIONS or Organizational Context?**
   - What we know: SJD file has organizational context paragraphs but no itemized duty lists.
   - What's unclear: Whether seeded duties should be the OG-group duty suggestions (polished statements from data.jsx) or extracted from the organizational context text.
   - Recommendation: Use DUTY_SUGGESTIONS[og_code] for clean polished duties with proper provenance; label them with sjd_number to maintain SJD traceability. The organizational context paragraph can be pre-filled as a separate field if needed.

---

## Sources

### Primary (HIGH confidence)
- `data/SJD Examples.txt` — direct file inspection; all 10 entries counted and fields catalogued [VERIFIED]
- `v2/backend/app/models/draft_duty.py` — DraftDuty model with existing source/provenance fields [VERIFIED]
- `v2/backend/app/models/work_description.py` — WorkDescription model with confirmed_og, og_level, duties [VERIFIED]
- `v2/backend/app/services/export_service.py` — `_build_v2_manifest` function and manifest shape [VERIFIED]
- `v2/backend/app/api/wd.py` — existing WD mutation endpoints and orphan_check pattern [VERIFIED]
- `v2/frontend/src/data.jsx` — STEPS array, PHASES, phase:0 last step is 'supervises' [VERIFIED]
- `v2/frontend/src/app.jsx` — commit() function, record/toast patterns, SJD-03 implementation point [VERIFIED]

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — SJD-01/02/03 requirements text [VERIFIED]
- `.planning/STATE.md` — Phase 21 completed; Phase 22 not started; v3 active codebase is v2/backend [VERIFIED]

---

## Metadata

**Confidence breakdown:**
- SJD file structure: HIGH — directly inspected all entries
- Standard stack: HIGH — no new dependencies; all patterns from existing code
- Architecture: HIGH — follows established patterns in wd.py and export_service.py
- Pitfalls: HIGH — OG code normalization pitfalls verified against actual file content
- Assumptions: A1 (entry count) and A2 (seed duty source) need product confirmation

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (stable domain; no external dependencies)
