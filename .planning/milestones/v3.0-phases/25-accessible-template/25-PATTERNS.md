# Phase 25: Accessible Template - Pattern Map

**Mapped:** 2026-06-16
**Files analyzed:** 6 (1 new build script, 1 new binary artifact, 1 modified service, 1 modified API call-site, 1 modified test file, 2 retired files)
**Analogs found:** 6 / 6 (all files have a strong existing analog — this phase is mechanically identical to prior work)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `v2/backend/scripts/build_accessible_template.py` | build script / config (one-off codegen) | file-I/O (build .docx skeleton, self-verify) | `v2/backend/scripts/build_wd_template.py` | exact |
| `v2/backend/app/templates/wd_accessible_template.docx` | config (committed binary artifact) | file-I/O | `v2/backend/app/templates/wd_template.docx` | exact |
| `v2/backend/app/services/export_service.py` (`_build_wd_context`, new `_factor_category_map`/routing helper, `_resolve_template_path` call site in `generate_wd_docx`) | service | CRUD (read WD row, transform to context dict, render) | itself (existing `_build_wd_context`/`_build_v2_manifest`/`_og_code_from`) | exact (modify-in-place) |
| `v2/backend/app/api/export.py` | route / controller | request-response | itself (`export_wd_docx` handler) — **no changes expected** per RESEARCH.md (only the underlying template/context swap in export_service.py) | exact (verify-only) |
| `v2/backend/tests/test_export.py` (existing TBS-shape assertions) + new ACC-02/ACC-04 cases | test | request-response / integration | itself (existing `test_export_wd_docx_*` tests) | exact |
| `v2/backend/scripts/build_wd_template.py` + `v2/backend/app/templates/wd_template.docx` | build script + config | file-I/O | — (retired, not replaced 1:1; superseded by the two rows above) | n/a — deletion target |

## Pattern Assignments

### `v2/backend/scripts/build_accessible_template.py` (build script, file-I/O)

**Analog:** `v2/backend/scripts/build_wd_template.py` (full file read; 250 lines) and `v2/backend/scripts/build_poster_template.py` (full file read; 150 lines) — copy `build_wd_template.py`'s structure exactly, it is the closer match (multi-section document vs. poster's single-page flyer).

**Module docstring + imports pattern** (`build_wd_template.py` lines 1-46):
```python
"""
v2/backend/scripts/build_wd_template.py — Generate the docxtpl TBS Work Description template.

Run from the repo root to (re)generate v2/backend/app/templates/wd_template.docx:

    cd /home/charles/job_description_builder
    python v2/backend/scripts/build_wd_template.py

The .docx is a committed binary artifact — the contract that the export service
(Plan 20-02) fills via a context dict. The Jinja2 variable names listed below
are stable; renaming them is a contract break.
...
"""
from __future__ import annotations

import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docxtpl import DocxTemplate

OUTPUT_PATH = "v2/backend/app/templates/wd_template.docx"
```
For the new file: `OUTPUT_PATH = "v2/backend/app/templates/wd_accessible_template.docx"`. Document the full Jinja2 variable contract in the docstring (mirroring the bullet list at lines 27-36), including the 7 Part 2 subsection variables and the position-identification 17-field table.

**Cell-text helper** (`build_wd_template.py` lines 51-62) — copy verbatim, used for every table cell:
```python
def _set_cell_text(cell, text: str, *, bold: bool = False, italic: bool = False) -> None:
    """Replace the cell's content with a single paragraph containing the given text."""
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

**Position Identification table pattern** (`build_wd_template.py` lines 76-92) — same label/value table idiom, extend to 17 rows per the reference docx field list in RESEARCH.md:
```python
position_rows = [
    ("Position Title:", "{{ position_title }}"),
    ("Position Number:", "{{ position_number }}"),
    ("Group and Level:", "{{ og_level }}"),
    ("Supervisor Title:", "{{ supervisor_title }}"),
    ("Supervisor Position Number:", "{{ supervisor_position_number }}"),
    ("Review Date:", "{{ review_date }}"),
]
pos_table = doc.add_table(rows=len(position_rows), cols=2)
pos_table.style = "Light Grid Accent 1"
for i, (label, value) in enumerate(position_rows):
    _set_cell_text(pos_table.rows[i].cells[0], label, bold=True)
    _set_cell_text(pos_table.rows[i].cells[1], value)
```
Reference docx has 17 rows (RESEARCH.md "Code Examples" section lists the exact label order — Position number, Position title, Position classification, Position Effective date, Job Code, National occupational classification, Department/Agency Name, Geographic location, Organizational component, Office code, Language requirements, Linguistic profile, Communications requirements, Security requirements, Supervisor position number, Supervisor position title, Supervisor classification). Per RESEARCH Open Question 2, fields with no WD data source should still get a Jinja2 var with a `[To be completed by advisor]` fallback computed in `_build_wd_context`, not omitted from the table.

**Paragraph-level `{%p for %}` / `{%p if %}` loop pattern** (`build_wd_template.py` lines 108-121) — use for Key Activities (duties), and any Part 2 list-style content:
```python
doc.add_paragraph("{%p for duty in duties %}")
doc.add_paragraph("{{ duty.text }}")
src_para = doc.add_paragraph()
src_run = src_para.add_run("Source: NOC {{ duty.noc_code }}")
src_run.italic = True
doc.add_paragraph("{%p if duty.is_advisor %}")
doc.add_paragraph("[advisor-added / not from authoritative source]")
doc.add_paragraph("{%p endif %}")
doc.add_paragraph("{%p endfor %}")
```

**Table-row `{%tr for %}` / `{%tr endfor %}` loop pattern** (`build_wd_template.py` lines 126-145) — use for the Effort factor table and Working Conditions factor table:
```python
jes_table = doc.add_table(rows=4, cols=3)
jes_table.style = "Light Grid Accent 1"
_set_cell_text(jes_table.rows[0].cells[0], "Factor", bold=True)
_set_cell_text(jes_table.rows[0].cells[1], "Degree", bold=True)
_set_cell_text(jes_table.rows[0].cells[2], "Points", bold=True)
# Row 1: {%tr for %} marker — MUST be alone in its row, first cell only
_set_cell_text(jes_table.rows[1].cells[0], "{%tr for f in jes_scores %}")
# Row 2: data row (duplicated per factor by the for loop)
_set_cell_text(jes_table.rows[2].cells[0], "{{ f.factor_name }}")
_set_cell_text(jes_table.rows[2].cells[1], "{{ f.degree }}")
_set_cell_text(jes_table.rows[2].cells[2], "{{ f.points }}")
# Row 3: {%tr endfor %} marker — MUST be alone in its row
_set_cell_text(jes_table.rows[3].cells[0], "{%tr endfor %}")
```
**Critical pitfall (preserve comment verbatim):** "docxtpl's patch_xml regex is greedy and matches the LAST `{%tr %}` tag in a row" — never co-locate `{%tr for %}` and `{%tr endfor %}` in the same row, never share a row with a data cell.

**Conditional appendix gate pattern** (`build_wd_template.py` lines 196-216) — reusable for any Part 2 subsection that needs a placeholder-vs-content gate (e.g. Effort/Working Conditions tables that may be empty for some OGs):
```python
doc.add_paragraph("{%p if amendments|length > 0 %}")
doc.add_heading("Appendix: Manager Amendments for Review", level=1)
...
doc.add_paragraph("{%p endif %}")
```
For Effort/Working Conditions, the simpler approach (per RESEARCH.md ACC-02) is to always render the section heading and either the factor table (`{%tr for %}` loop) or fall back to literal placeholder text `[To be completed by advisor]` passed as a context string variable — no `{%p if%}` gate needed if the placeholder string itself is always non-empty.

**Self-verify pattern** (`build_wd_template.py` lines 222-249) — copy structure, update `required` set to the new Accessible-template contract:
```python
if __name__ == "__main__":
    build()
    tpl = DocxTemplate(OUTPUT_PATH)
    undeclared = sorted(tpl.get_undeclared_template_variables())
    print(f"WD template variables ({len(undeclared)}): {undeclared}")
    required = {
        "position_title", "position_number", "og_level", ...,
        # 7 Part 2 subsection text/list variables (org context, client_service_results,
        # duties, education_text/experience_text, effort_*, responsibilities_*,
        # working_conditions_*), plus manifest
    }
    missing = required - set(undeclared)
    if missing:
        raise AssertionError(
            f"build_accessible_template: required variables {missing!r} not declared "
            f"in template. Found: {undeclared}"
        )
    print("Accessible template OK")
```

---

### `v2/backend/app/templates/wd_accessible_template.docx` (config, file-I/O)

**Analog:** `v2/backend/app/templates/wd_template.docx` — not human-edited; this is the binary output artifact of running `build_accessible_template.py`. No code excerpt applies; just confirm the build script is re-run and the resulting `.docx` is committed (`git add` the binary), matching how `wd_template.docx` is currently committed alongside its build script.

---

### `v2/backend/app/services/export_service.py` (service, CRUD)

**Analog:** itself — full file already read (455 lines). Three call sites/functions change:

**1. New factor-category lookup helper** — add near `_build_v2_manifest`, importing from `constants.py` per the Don't-Hand-Roll guidance (single source of truth, not a hardcoded dict literal):
```python
# New imports needed (existing import block at lines 33-38 only imports NON_EC_STANDARD_NAMES):
from app.data.constants import (
    EC_JES_ELEMENTS,
    JES_FACTORS_BY_GROUP,
    NON_EC_STANDARD_NAMES,
)

def _factor_category_map() -> dict[str, str]:
    """Merge EC_JES_ELEMENTS + every JES_FACTORS_BY_GROUP entry into factor_name -> category.

    Never trust wd.jes_scores[i]["category"] directly — the EC scoring path
    (_build_factor_score in jes_service.py) does not copy category onto the
    persisted score dict, only the point-rating non-EC path does.
    """
    mapping: dict[str, str] = {}
    for el in EC_JES_ELEMENTS:
        mapping[el["name"]] = el["category"]
    for group_factors in JES_FACTORS_BY_GROUP.values():
        for f in group_factors:
            mapping[f["name"]] = f.get("category", "")
    return mapping
```

**2. Existing `_og_code_from()` pattern (lines 136-146) — reuse for routing-code resolution.** The new Effort/Working-Conditions placeholder-fallback logic must replicate the SW/ED sub-group routing split that `jes_service.py`'s `score_jes_v2` already implements (lines 192-217 of `jes_service.py`, reproduced below) — do not re-derive a simplified version:
```python
# Source: v2/backend/app/services/jes_service.py lines 199-217 (existing project code)
sub_group = getattr(wd, "confirmed_sub_group", None)
routing_code = og_code
if og_code == "SW":
    routing_code = "SW-SCW" if sub_group == "SCW" else "SW-CHA"
elif og_code == "ED":
    if sub_group == "EDS":
        routing_code = "ED-EDS"
    elif sub_group == "LAT":
        routing_code = "ED-LAT"
    elif sub_group == "EST":
        routing_code = "ED-EST"
    else:
        routing_code = "ED-LAT"
```
Groups with zero Effort/Conditions factor data (confirmed in RESEARCH.md): `MT`, `SW-SCW` (point-rating groups with Skill/Responsibility only), and every level-description group (`IT`, `AS`, `FI`, `EN`, `CR`, `PM`, `GT`, `EL`, `AI`, `AU`, `ED`/`ED-LAT`/`ED-EST`/`SW-CHA`, `NU`, `PS`, `NT`, `PO`, `WP`) — these only have `jes_total_points` with `jes_scores: []`. The placeholder-fallback condition should be `if routing_code in JES_FACTORS_BY_GROUP or og_code == "EC": bucket by category` else `placeholder = "[To be completed by advisor]"`.

**3. `_build_wd_context()` rewrite** — keep the existing function name/signature (planner contract per RESEARCH.md Architectural Responsibility Map: "Accessible template reuses the same function name/contract"). Existing structure to extend (lines 242-290):
```python
def _build_wd_context(wd: WorkDescription, amendments: list[dict]) -> dict:
    record = wd.record or {}
    og_code = _og_code_from(wd)
    og_level_int = wd.og_level or 0
    og_level_str = _og_level_str(og_code, og_level_int)

    if wd.qualification is not None:
        education_text = wd.qualification.education
        experience_text = wd.qualification.experience
    else:
        record_quals = record.get("quals") or {}
        education_text = record_quals.get("education", "")
        experience_text = record_quals.get("experience", "")

    root_duties = wd.duties or []
    if not root_duties:
        root_duties = [DraftDuty(**d) for d in (record.get("duties") or [])]
    ...
```
Reuse `_build_organizational_context_text(wd)` (lines 213-239) verbatim for the `organizational_context_text` Part 2 field — already exists and is explicitly called out in RESEARCH.md's architecture diagram as "reused."

New fields to compute (per RESEARCH.md architecture diagram, lines 90-97):
- `client_service_results_text` — NEW, from `wd.record["client_service_results"]` (frontend confirmed source: `v2/frontend/src/data.jsx` lines 657-662, QUESTION_BANK)
- `effort_factors` / `effort_placeholder` — bucket `wd.jes_scores` by `_factor_category_map().get(score["factor_name"]) == "Effort"`, else placeholder string
- `working_conditions_factors` / `wc_placeholder` — same pattern, category `"Conditions"`
- `responsibilities_text` — per RESEARCH.md Open Question 1 default recommendation: Responsibility-category JES factors (factor name + rationale), falling back to placeholder (no group currently lacks a Responsibility-category factor per RESEARCH.md)

**4. `generate_wd_docx()` template path call site** (line 401) — only this one line changes:
```python
# BEFORE:
template_path = _resolve_template_path("wd_template.docx")
# AFTER:
template_path = _resolve_template_path("wd_accessible_template.docx")
```
`_render_docx`, `_resolve_template_path` itself, `_get_amendments`, `_build_v2_manifest`, `_og_code_from`, `_og_level_str`, `_slugify_title`, and the entire poster path (`_build_poster_context`/`generate_poster_docx`) are confirmed unchanged — do not touch them.

---

### `v2/backend/app/api/export.py` (route/controller, request-response)

**Analog:** itself (full file already read, 203 lines) — **no code changes expected**. The route signature `POST /wd/{wd_id}/export/docx` (line 55), the `require_og_confirmed` gate (line 60), and the JES self-heal block (lines 61-86) all operate on `wd.jes_total_points`/`wd.jes_scores` independent of which template is rendered — `generate_wd_docx()` is called unchanged (line 87). Use this file only to verify no accidental coupling to the old TBS-specific field names exists; if a future grep shows `export.py` referencing `wd_template.docx` directly, that would be the one thing to change (RESEARCH.md confirms it currently does not — only `export_service.py`'s `_resolve_template_path` call site needs the path swap).

---

### `v2/backend/tests/test_export.py` (test, integration)

**Analog:** itself (full file already read, 273 lines). Existing assertions to update for ACC-03 (structural — these currently pass with the TBS template and must keep passing with Accessible-format bytes, since none of them assert template-specific text, only byte-count/MIME-type/status-code):
```python
# Source: v2/backend/tests/test_export.py lines 57-65 (existing, no change needed structurally)
async def test_export_wd_docx_returns_bytes(client, env_with_db):
    wd_id = await _create_wd_with_jes_scores(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(resp.content) > 0
```
These pass unmodified against the new template since they assert MIME type + non-zero bytes only. New tests to add (ACC-02/ACC-04), modeled on the existing `_create_wd_with_jes_scores` fixture helper (lines 28-54):
```python
# Source: v2/backend/tests/test_export.py lines 28-54 (existing fixture helper pattern to copy)
async def _create_wd_with_jes_scores(client) -> str:
    wd_id = await _create_wd(client)
    resp = await client.patch(
        f"/api/wd/{wd_id}",
        json={
            "confirmed_og": {"og_code": "EC", "og_name": "Economics and Social Science Services"},
            "og_level": 4,
            "jes_total_points": 621,
            "jes_scores": [
                {"factor_name": "Decision Making", "degree": 3, "points": 150},
                {"factor_name": "Communication", "degree": 2, "points": 84},
            ],
            "duties": [...],
        },
    )
    assert resp.status_code == 200
    return wd_id
```
For ACC-02 fallback coverage, create 4 variant fixture helpers (per RESEARCH.md Wave 0 Gaps): EC (LLM-style, has Effort/Conditions categories), a point-rating group with Effort+Conditions (e.g. FB or FS), a point-rating group without Effort/Conditions (MT or SW-SCW with `confirmed_sub_group: "SCW"`), and a level-description group with `jes_scores: []` (e.g. IT, AS, or NU). For ACC-04, use the content-presence read-back pattern from RESEARCH.md's Code Examples section directly (python-docx re-read of rendered bytes, assert no literal `{{` or `None` leaked through).

**Existing test that locks an import-shape contract** (lines 257-273) — unaffected by this phase, no change needed, but instructive as the project's "assert source code shape" idiom if the planner wants an equivalent guard for the new `_factor_category_map` import:
```python
def test_standard_names_import_from_constants():
    import inspect, importlib
    export_service = importlib.import_module("app.services.export_service")
    source = inspect.getsource(export_service)
    assert "from app.data.constants import" in source and "NON_EC_STANDARD_NAMES" in source
    assert "NON_EC_STANDARD_NAMES: dict" not in source
```

---

## Shared Patterns

### docxtpl skeleton-build + self-verify
**Source:** `v2/backend/scripts/build_wd_template.py` (whole file), `v2/backend/scripts/build_poster_template.py` (whole file)
**Apply to:** `build_accessible_template.py`
The two-phase idiom — build with `python-docx`, then immediately reload with `DocxTemplate(...).get_undeclared_template_variables()` and assert a `required` set is a subset — is mandatory for any new template script in this codebase. No exceptions found.

### Factor category derivation (never trust runtime `category` key)
**Source:** `v2/backend/app/data/constants.py` lines 1366-1468 (`EC_JES_ELEMENTS`, `JES_FACTORS_BY_GROUP`); `v2/backend/app/services/jes_service.py` lines 105-130 (`_build_factor_score`, confirms EC path omits `category`) vs. lines 237-246 (point-rating path, confirms it includes `category`)
**Apply to:** `export_service.py`'s new Effort/Working-Conditions bucketing logic
Always derive `category` via a `factor_name -> category` lookup built fresh from `constants.py`, never via `score.get("category")` on the persisted `wd.jes_scores` dict.

### SW/ED sub-group routing-code resolution
**Source:** `v2/backend/app/services/jes_service.py` lines 192-217 (`score_jes_v2`)
**Apply to:** `export_service.py`'s placeholder-fallback decision ("does this OG have Effort/Conditions factor data at all")
Must key off `routing_code` (e.g. `"SW-SCW"`, `"SW-CHA"`, `"ED-LAT"`), not the raw `og_code` (`"SW"`/`"ED"`) — `JES_FACTORS_BY_GROUP` dict keys are routing codes, and a naive `og_code` lookup will `KeyError` or silently mis-classify.

### `og_code` shape tolerance
**Source:** `v2/backend/app/services/export_service.py` lines 136-146 (`_og_code_from`)
**Apply to:** any new helper in `export_service.py` that reads `wd.confirmed_og`
`confirmed_og` may be a bare string or a dict — always go through `_og_code_from(wd)`, never `wd.confirmed_og.get("og_code")` directly (AttributeError risk on string shape).

### Cell-text replacement helper
**Source:** `v2/backend/scripts/build_wd_template.py` lines 51-62 (identical copy in `build_poster_template.py` lines 41-52)
**Apply to:** `build_accessible_template.py` — copy `_set_cell_text()` verbatim; it is duplicated (not shared via import) in both existing scripts, so duplicating it a third time is the established convention, not an anti-pattern here.

## No Analog Found

None — every file in this phase's scope has a direct, strong analog already in the codebase (this phase is explicitly "mechanically the same task" per RESEARCH.md's Don't Hand-Roll section).

## Metadata

**Analog search scope:** `v2/backend/scripts/`, `v2/backend/app/services/`, `v2/backend/app/api/`, `v2/backend/app/data/`, `v2/backend/app/templates/`, `v2/backend/tests/`
**Files scanned:** `build_wd_template.py`, `build_poster_template.py`, `export_service.py`, `export.py`, `jes_service.py`, `constants.py` (targeted ranges), `work_description.py` (grep), `test_export.py` — 8 files read/grepped, all read in full or via non-overlapping targeted ranges, no re-reads
**Pattern extraction date:** 2026-06-16
