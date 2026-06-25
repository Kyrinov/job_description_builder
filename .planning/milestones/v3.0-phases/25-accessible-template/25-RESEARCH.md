# Phase 25: Accessible Template - Research

**Researched:** 2026-06-16
**Domain:** docxtpl-based DOCX templating; GoC Accessible Job Description format; JES factor-score-to-template mapping
**Confidence:** HIGH (codebase patterns and reference docx are directly inspected); MEDIUM (Part 2 subsection-to-data mapping decisions, since no CONTEXT.md exists to lock these)

## Summary

Phase 25 replaces the existing TBS-format `wd_template.docx` with a new `wd_accessible_template.docx` that mirrors the structure of the reference document at `data/AI Docs/Accessible Job Description Template (1).docx`. The existing codebase already has a complete, working, two-script pattern for this exact kind of work (`build_wd_template.py` / `build_poster_template.py` using `python-docx` to construct the skeleton + `docxtpl` Jinja2-style tags, with a self-verifying `get_undeclared_template_variables()` check) — Phase 25 should copy this pattern exactly, not invent a new one.

The reference docx has **no native fillable fields or content controls** (`grep` of `document.xml` for `w:tag`/`w:alias` returned nothing) — it is a plain static Word document with heading styles (`Heading 1`, `Heading 2`) and one 17-row label/value table for position identification. There is no canonical machine-readable variable-name contract; the team must design the Jinja2 variable names itself, following the existing project convention (snake_case, mirrors `wd_template.docx`'s contract style).

**Discrepancy to flag (per phase instructions):** The ROADMAP/phase title says "6 subsections" but the reference document's Part 2 actually contains **7** `Heading 2` subsections: Organizational context, Client service results, Key activities, Skills, Effort, Responsibilities, Working conditions. REQUIREMENTS.md's ACC-01 text also says "6 subsections" but then **lists all 7 names**. This is almost certainly a miscount in the phase/requirement text, not a real ambiguity — the reference docx is unambiguous. The planner should treat 7 as the correct count and may want to flag the off-by-one wording in ROADMAP.md/REQUIREMENTS.md as a documentation nit (not a blocking issue).

A second critical and non-obvious finding: the JES factor-score dicts persisted on `WorkDescription.jes_scores` carry a `"category"` key (e.g. `"Effort"`, `"Conditions"`, `"Skill"`, `"Responsibility"`) **only for the point-rating non-EC path** (`JES_FACTORS_BY_GROUP`). The **EC path's** `_build_factor_score()` in `jes_service.py` does **not** copy `category` into the persisted score dict — so `wd.jes_scores[i].get("category")` will be `""`/absent for EC WDs even though `EC_JES_ELEMENTS` itself has `category` defined. `export_service.py` must therefore map `factor_name` -> `category` via a lookup table built from `EC_JES_ELEMENTS` + `JES_FACTORS_BY_GROUP`, not by trusting `category` on the runtime score dict.

**Primary recommendation:** Author `v2/backend/scripts/build_accessible_template.py` using the exact `python-docx` + `docxtpl` skeleton-building pattern from `build_wd_template.py` (Heading 1 for "Part 1"/"Part 2", Heading 2 for each subsection, a `doc.add_table()` for the 17-field position table, `{%p for %}` paragraph loops for duties/skills lists, `{%tr for %}` table-row loops for JES factor tables and the version manifest). Add a `_build_factor_category_map()` helper in `export_service.py` that merges `EC_JES_ELEMENTS` and all of `JES_FACTORS_BY_GROUP` into one `{factor_name: category}` dict, then use it to bucket `wd.jes_scores` into Effort vs. Working Conditions lists, falling back to the literal string `"[To be completed by advisor]"` when the confirmed OG's routing code has no factors carrying that category (MT, SW-SCW, and every level-description group: IT, AS, FI, EN, CR, PM, GT, EL, AI, AU, ED, NU, PS, NT, PO, WP, SW, SW-CHA, ED-LAT, ED-EST — none of these have per-factor `category` data at all since they only produce `jes_total_points` with `jes_scores: []`).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| DOCX template skeleton (headings, table, Jinja2 tags) | Backend (build script, `scripts/build_accessible_template.py`) | — | Template is a committed binary artifact built by a one-off script, same as existing `wd_template.docx`/`poster_template.docx` |
| Context dict construction (`_build_wd_context`) | Backend (`app/services/export_service.py`) | — | Already owns this responsibility for the TBS template; Accessible template reuses the same function name/contract |
| Effort/Working Conditions derivation from JES factor scores | Backend (`export_service.py`, new helper) | Backend (`app/data/constants.py` — source of factor `category` data) | JES factor category data lives only in `constants.py`; export_service must read it, not duplicate it |
| Export endpoint routing | Backend (`app/api/export.py`) | — | No route signature change — same `POST /api/wd/{id}/export/docx` path, only the underlying template/context swap |
| Content-presence verification | Backend (test suite, `tests/test_export.py` or new `tests/test_accessible_template.py`) | — | python-docx read-back test, run in CI, not a runtime concern |
| Frontend / SPA | — | — | No frontend changes — export is triggered by an existing button calling the existing endpoint; only the server-side artifact changes |

## User Constraints

No `.planning/phases/25-accessible-template/*-CONTEXT.md` exists for this phase (confirmed: directory was empty before this research ran). There are no locked decisions, discretion areas, or deferred ideas to copy verbatim. The planner has full discretion over Part 2 field-to-data mapping decisions, subject to the architecture non-negotiables in STATE.md (ProvenanceTag/citation tracing, deterministic JES, no LLM in main export flow) and the project's `docxtpl`-for-DOCX-export decision already locked in STATE.md's "Decisions Carried from v2.0" table.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ACC-01 | `build_accessible_template.py` builds + self-verifies `wd_accessible_template.docx`; Part 1 (position ID + 3 signature blocks) + Part 2 (7 subsections, see discrepancy note); `get_undeclared_template_variables()` confirms declared vars | Reference docx structure fully extracted below (headings, table fields, signature blocks). Existing `build_wd_template.py`/`build_poster_template.py` provide the exact code pattern to copy, including the self-verify + `required` set assertion idiom |
| ACC-02 | `_build_wd_context()` populates all Part 2 fields; Effort/Working Conditions map from JES factor scores where the OG's JES defines those factors; `[To be completed by advisor]` otherwise | `JES_FACTORS_BY_GROUP` and `EC_JES_ELEMENTS` factor `category` values identified per group below; confirmed that level-description groups and MT/SW-SCW have no Effort/Conditions factor data; confirmed the EC-path category-stripping bug that must be worked around |
| ACC-03 | `POST /api/wd/{id}/export/docx` produces Accessible format; TBS template retired; poster template unchanged; existing export tests updated | `export.py`/`export_service.py` read in full — only `_resolve_template_path("wd_template.docx")` call site and `_build_wd_context()` need to change; `generate_poster_docx`/`_build_poster_context`/`poster_template.docx` are fully independent code paths, confirmed untouched |
| ACC-04 | Content-presence test via python-docx asserts every non-placeholder variable resolves to non-empty string for a fully-completed WD | `get_undeclared_template_variables()` pattern + python-docx paragraph/table read-back demonstrated working against the reference docx in this research session (see Code Examples) |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| docxtpl | 0.19.0 (pinned in `v2/backend/requirements.txt`); 0.18.0 actually installed locally [VERIFIED: pip show] | Jinja2-style templating over a .docx skeleton | Already the project's locked decision ("docxtpl for DOCX export" in STATE.md); used by both existing templates |
| python-docx | 1.1.2 [VERIFIED: pip show, requirements.txt] | Build the template skeleton (headings, tables, paragraphs) and read back rendered output for content-presence tests | Already used identically by `build_wd_template.py` / `build_poster_template.py`; pure-Python, ARM64-compatible (relevant since this runs on Jetson/ARM hardware per project context) |

No new packages need to be installed. **Note:** locally installed docxtpl is 0.18.0 but `requirements.txt` pins 0.19.0 — pre-existing drift, not introduced by this phase; not worth fixing unless `pip install -r requirements.txt` is re-run.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| docxtpl (current) | python-docx content controls (SDT) + manual XML patching | Reference docx itself uses no content controls; building one from scratch would deviate from the established, working pattern for no benefit |

**Installation:** None required — already in `v2/backend/requirements.txt`.

## Architecture Patterns

### System Architecture Diagram

```
Advisor clicks "Export DOCX"
        │
        ▼
POST /api/wd/{id}/export/docx  (app/api/export.py, UNCHANGED route)
        │
        ▼
_load_wd(wd_id)  →  WorkDescription (SQLite work_descriptions.data JSON)
        │
        ▼
require_og_confirmed(wd)  →  409 if OG/level not confirmed
        │
        ▼
JES self-heal block (UNCHANGED): if jes_total_points is None, call score_jes_v2()
        │
        ▼
generate_wd_docx(wd_id, db_path)   [app/services/export_service.py]
        │
        ├─→ _get_amendments(con, wd_id)        — unchanged, AMEND-02 appendix data
        │
        ├─→ _build_wd_context(wd, amendments)   — REWRITTEN for Accessible format
        │        │
        │        ├─→ position identification fields (17 fields, Part 1 table)
        │        ├─→ 3 signature blocks (employee/supervisor/manager — static labels,
        │        │      no live data needed; names/dates left blank for manual signing
        │        │      OR populated from record if available — see Open Questions)
        │        ├─→ organizational_context_text  (existing _build_organizational_context_text(), reused)
        │        ├─→ client_service_results_text  (NEW — from wd.record["client_service_results"])
        │        ├─→ duties (Key Activities)       (existing pattern, reused)
        │        ├─→ skills (education_text/experience_text)  (existing wd.qualification, reused)
        │        ├─→ effort_factors / effort_placeholder       (NEW — JES category lookup)
        │        ├─→ responsibilities_text                     (NEW — maps to duties or a
        │        │      Responsibility-category JES factor narrative; see Open Questions)
        │        └─→ working_conditions_factors / wc_placeholder (NEW — JES category lookup)
        │
        ├─→ _resolve_template_path("wd_accessible_template.docx")   — CHANGED path
        │
        └─→ _render_docx(template_path, context)  — UNCHANGED (asyncio.to_thread wrapper)
                  │
                  ▼
         DOCX bytes → SHA-256 export hash → Response(media_type=DOCX_MEDIA_TYPE)
```

Poster export (`generate_poster_docx` / `_build_poster_context` / `poster_template.docx`) is a fully separate code path and diagram branch — confirmed untouched by this phase.

### Recommended Project Structure
```
v2/backend/
├── scripts/
│   ├── build_wd_template.py        # RETIRED — delete or leave as historical reference + remove from any Makefile/CI step
│   ├── build_accessible_template.py # NEW — copy build_wd_template.py's pattern
│   └── build_poster_template.py    # UNCHANGED
├── app/
│   ├── templates/
│   │   ├── wd_template.docx        # RETIRED — delete (binary artifact)
│   │   ├── wd_accessible_template.docx  # NEW — committed binary artifact
│   │   └── poster_template.docx    # UNCHANGED
│   └── services/
│       └── export_service.py       # _build_wd_context() rewritten; _resolve_template_path call site changed
└── tests/
    └── test_export.py              # existing TBS-shape assertions updated to Accessible-shape assertions
    └── test_accessible_template.py # NEW (optional) — content-presence test (ACC-04), or co-located in test_export.py
```

### Pattern 1: Skeleton-build + self-verify script
**What:** A standalone script builds a `.docx` via `python-docx` API calls (headings, tables, paragraphs with literal `{{ var }}` / `{%p %}` / `{%tr %}` strings), saves it, then immediately re-opens it with `DocxTemplate(...).get_undeclared_template_variables()` and asserts a `required` set of variable names is a subset of what was found.
**When to use:** Any time the template is regenerated — this phase's `build_accessible_template.py` should follow this exactly.
**Example:**
```python
# Source: v2/backend/scripts/build_wd_template.py (existing project code, verified by direct read)
tpl = DocxTemplate(OUTPUT_PATH)
undeclared = sorted(tpl.get_undeclared_template_variables())
required = {"position_title", "duties", ...}
missing = required - set(undeclared)
if missing:
    raise AssertionError(f"required variables {missing!r} not declared")
```

### Pattern 2: `{%tr for %}` / `{%tr endfor %}` table-row loop placement
**What:** docxtpl's table-row loop tags MUST each occupy their own dedicated row with the tag as the ONLY content in the first cell of that row — never share a row with a data cell, and never put `{%tr for %}` and `{%tr endfor %}` in the same row.
**When to use:** Building the Effort factor table and Working Conditions factor table (if rendered as tables rather than paragraph lists) and the version-manifest table.
**Example:**
```python
# Source: v2/backend/scripts/build_wd_template.py lines 133-145 (existing project code)
# Row 1: {%tr for %} marker (own row)
_set_cell_text(jes_table.rows[1].cells[0], "{%tr for f in jes_scores %}")
# Row 2: data row (duplicated per factor)
_set_cell_text(jes_table.rows[2].cells[0], "{{ f.factor_name }}")
# Row 3: {%tr endfor %} marker (own row)
_set_cell_text(jes_table.rows[3].cells[0], "{%tr endfor %}")
```
**Pitfall avoided:** "docxtpl's patch_xml regex is greedy and matches the LAST `{%tr %}` tag in a row" — comment preserved verbatim from the existing codebase; co-locating for/endfor in one row eats the for tag.

### Pattern 3: `{%p for %}` / `{%p if %}` paragraph-level loop/conditional placement
**What:** Each `{%p ... %}` tag must be in its own paragraph; the body content between `{%p if %}` and `{%p endif %}` is a separate paragraph that is included/excluded as a whole unit.
**When to use:** Duties list (Key Activities), amendments appendix gate, and any Part 2 list-style content (e.g., Org Context's 4 bullet list items in the reference docx, which use `List Paragraph` style).
**Example:**
```python
# Source: v2/backend/scripts/build_wd_template.py lines 110-121 (existing project code)
doc.add_paragraph("{%p for duty in duties %}")
doc.add_paragraph("{{ duty.text }}")
doc.add_paragraph("{%p if duty.is_advisor %}")
doc.add_paragraph("[advisor-added / not from authoritative source]")
doc.add_paragraph("{%p endif %}")
doc.add_paragraph("{%p endfor %}")
```

### Anti-Patterns to Avoid
- **Hardcoding factor `category` lookups inline in `export_service.py` from a fresh dict literal:** Don't redefine factor-name→category mappings by hand; derive them from `EC_JES_ELEMENTS` + `JES_FACTORS_BY_GROUP` (already in `constants.py`) so there is a single source of truth and the mapping stays correct if those tables change.
- **Trusting `wd.jes_scores[i]["category"]` unconditionally:** As documented above, this key is absent for EC-scored WDs. Always derive category via factor_name lookup, never via direct dict access on the runtime score.
- **Forgetting the SW/ED sub-group routing split when deciding "does this OG have Effort/Conditions factors":** `og_code="SW"` routes to either `SW-SCW` (point-rating, no Effort/Conditions category — only Skill/Responsibility) or `SW-CHA` (level-description, no factors at all). Same for `ED` → `ED-EDS`/`ED-LAT`/`ED-EST`. The placeholder-fallback logic must check the **routing code** (`wd.confirmed_sub_group`-aware), not the raw `og_code`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DOCX templating / merge fields | Custom XML string-replace on `document.xml` | `docxtpl` (already a locked dependency) | Already proven to work for two templates in this codebase; avoids reinventing escaping/Jinja2 logic |
| Verifying all template variables are declared | Manual visual inspection of the rendered docx | `DocxTemplate.get_undeclared_template_variables()` | Already the established self-verify idiom in both existing build scripts; catches malformed tags at build time |
| Per-OG Effort/Conditions factor category mapping | A new hardcoded dict literal in export_service.py | Derive from `EC_JES_ELEMENTS` + `JES_FACTORS_BY_GROUP` (`constants.py`) | Single source of truth — avoids drift if factor tables are edited in a later phase |

**Key insight:** The codebase already solved this exact problem twice (TBS WD template, Poster template). Phase 25 is mechanically the same task — new heading/field layout matching a different reference document — not a new architecture.

## Common Pitfalls

### Pitfall 1: Off-by-one in "6 subsections" wording propagating into the plan
**What goes wrong:** A plan author miscounts Part 2 sections as 6 when building the template, omitting one (most likely candidate to be dropped: "Client service results", since it's the newest addition from Phase 23/WG-03 and easy to conflate with "Org Context").
**Why it happens:** ROADMAP.md and REQUIREMENTS.md both say "6 subsections" in prose, even though REQUIREMENTS.md's own ACC-01 bullet then lists all 7 names.
**How to avoid:** Always build from the reference docx's actual 7 `Heading 2` entries (Organizational context, Client service results, Key activities, Skills, Effort, Responsibilities, Working conditions), confirmed directly from `python-docx` paragraph dump in this research session.
**Warning signs:** A `required` variable set in the self-verify script with fewer than 7 section-text variables.

### Pitfall 2: EC `jes_scores` missing `category` key breaks Effort/Conditions bucketing
**What goes wrong:** Code that does `if score["category"] == "Effort"` raises `KeyError` for EC WDs (the most common/default OG in this project), or silently drops all EC effort/condition rows if written as `score.get("category") == "Effort"` (which always evaluates False since the key is never set).
**Why it happens:** `_build_factor_score()` in `jes_service.py` (the EC LLM-scoring path) does not copy `category` from `EC_JES_ELEMENTS[i]["category"]` into its returned dict — only the point-rating non-EC path (`score_jes_v2`'s `factor_def.get("category", "")` block) does this.
**How to avoid:** Build a `factor_name -> category` lookup dict in `export_service.py` from `EC_JES_ELEMENTS` + all `JES_FACTORS_BY_GROUP` groups, and use `lookup.get(score["factor_name"])` instead of `score.get("category")`.
**Warning signs:** EC-classified test WDs show "[To be completed by advisor]" for Effort/Working Conditions even though `EC_JES_ELEMENTS` clearly defines `Physical effort`, `Sensory effort` (category "Effort"), and `Working conditions` (category "Conditions").

### Pitfall 3: Placeholder fallback applied per-og_code instead of per-routing-code
**What goes wrong:** `wd.confirmed_og.og_code == "SW"` is ambiguous — SCW sub-group is point-rated with Skill/Responsibility factors only (no Effort/Conditions), CHA sub-group is level-description with zero factors. Naive code keyed only on `og_code` will incorrectly try to look up `"SW"` in `JES_FACTORS_BY_GROUP` (KeyError — the dict key is `"SW-SCW"`, not `"SW"`) or will incorrectly claim Effort data exists when it doesn't.
**Why it happens:** The existing `score_jes_v2()` resolves a `routing_code` (`SW-SCW`/`SW-CHA`/`ED-EDS`/`ED-LAT`/`ED-EST`) from `og_code` + `wd.confirmed_sub_group` before consulting `JES_FACTORS_BY_GROUP`/`NON_EC_TOTALS` — export_service must replicate that same routing logic, not re-derive its own simplified version.
**How to avoid:** Extract (or import/reuse) the routing-code resolution logic from `jes_service.py` rather than reimplementing it in `export_service.py`.
**Warning signs:** Tests for SW/ED WDs show wrong Effort/Conditions behavior despite EC and FB/FS/LC/LP working correctly.

### Pitfall 4: Forgetting to delete/retire the old template + build script per ACC-03
**What goes wrong:** Both `wd_template.docx` and `build_wd_template.py` remain in the repo as dead code; a future contributor re-runs the wrong build script or the old binary lingers and confuses anyone grepping for "the" WD template.
**Why it happens:** "Retire" is easy to interpret as "stop calling it" rather than "remove it."
**How to avoid:** Explicitly delete `v2/backend/app/templates/wd_template.docx` and `v2/backend/scripts/build_wd_template.py` (or, if the team prefers an audit trail, move them under a clearly-named `_retired/` subfolder) as part of the phase's task list — ACC-03 says "previous TBS WD template is retired," which the planner should interpret as removal, not just disuse.
**Warning signs:** `grep -rn "wd_template.docx"` after the phase still returns hits outside of historical git log / commit messages.

### Pitfall 5: Signature block fields have no obvious data source
**What goes wrong:** Part 1's 3 signature blocks (Employee, Supervisor, Manager) each need name/signature/date fields per the reference docx, but `WorkDescription` has no employee/supervisor/manager name fields beyond `record.reports` (a free-text "reports to" string) — there is no structured "supervisor name" or "manager name" field anywhere in the model.
**Why it happens:** v1.0/v2.0 never needed named signatories — only `supervisor_title`/`supervisor_position_number` (both currently blank-string-defaulted in `_build_wd_context`) existed.
**How to avoid:** This is genuinely an open question for the planner — likely resolution is to render the 3 signature blocks as static label/blank-line text (no data binding needed, matching how a paper form is normally signed after printing) rather than as Jinja2 variables. ACC-04's content-presence test says "every **non-placeholder** template variable resolves to a non-empty string" — this implies signature name/date fields are *expected* to be blank/placeholder and excluded from that assertion, not bound to WD data at all.
**Warning signs:** A plan that tries to add `employee_name`/`supervisor_name`/`manager_name` fields to `WorkDescription` — likely scope creep beyond ACC-01..04 since no requirement calls for capturing signatory names during the conversation flow.

## Code Examples

### Reading reference docx structure (used in this research to extract Part 1/Part 2 layout)
```python
# Verified directly in this research session against
# data/AI Docs/Accessible Job Description Template (1).docx
import docx
d = docx.Document('data/AI Docs/Accessible Job Description Template (1).docx')
for p in d.paragraphs:
    if p.text.strip():
        print(p.style.name, p.text.strip())
# Output confirmed:
#   Heading 1: "Part 1: Position information and signatures"
#   Heading 2: "Employee statement" / "Supervisor statement" / "Manager authorization"
#   Heading 1: "Part 2: Job description"
#   Heading 2 x7: "Organizational context", "Client service results", "Key activities",
#                 "Skills", "Effort", "Responsibilities", "Working conditions"
```

### Position identification table (17 rows, label/value, Part 1)
```python
# Verified via d.tables[0] — single table, 17 rows x 2 cols, label in col 0
# Fields, in order:
[
    "Position number", "Position title", "Position classification",
    "Position Effective date", "Job Code", "National occupational classification",
    "Department/Agency Name", "Geographic location",
    "Organizational component (Branch/Division)", "Office code",
    "Language requirements", "Linguistic profile", "Communications requirements",
    "Security requirements", "Supervisor position number",
    "Supervisor position title", "Supervisor classification",
]
```
Most of these have no current `WorkDescription` field (e.g. "Job Code", "Office code", "Language requirements", "Linguistic profile", "Communications requirements", "Security requirements") — see Open Questions for which should render `[To be completed by advisor]` vs. be dropped/simplified vs. require new WD fields.

### Factor category lookup (new helper export_service.py needs)
```python
# Pattern to add — not yet in codebase, derived from constants.py inspection
from app.data.constants import EC_JES_ELEMENTS, JES_FACTORS_BY_GROUP

def _factor_category_map() -> dict[str, str]:
    """Merge EC_JES_ELEMENTS + every JES_FACTORS_BY_GROUP entry into factor_name -> category."""
    mapping: dict[str, str] = {}
    for el in EC_JES_ELEMENTS:
        mapping[el["name"]] = el["category"]
    for group_factors in JES_FACTORS_BY_GROUP.values():
        for f in group_factors:
            mapping[f["name"]] = f.get("category", "")
    return mapping
```

### Content-presence test pattern (ACC-04)
```python
# Pattern verified working against docxtpl-rendered output in this research session
import docx

def test_accessible_docx_all_variables_present(rendered_bytes):
    d = docx.Document(io.BytesIO(rendered_bytes))
    full_text = "\n".join(p.text for p in d.paragraphs)
    for t in d.tables:
        for row in t.rows:
            full_text += "\n" + "\n".join(c.text for c in row.cells)
    assert "{{" not in full_text, "Unrendered Jinja2 tag leaked into output"
    assert "None" not in full_text  # catches str(None) leaking through
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| TBS Work Description format (6 numbered sections + appendix) | GoC Accessible Job Description format (Part 1 signatures + Part 2 7 subsections) | This phase (2026-06) | Single export path; STATE.md already records "Accessible Template replaces TBS WD template entirely (not an optional format)" as a v3.0 key decision — this phase executes that decision |

**Deprecated/outdated:**
- `wd_template.docx` / `build_wd_template.py`: superseded by `wd_accessible_template.docx` / `build_accessible_template.py`; retire per ACC-03.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | "Skills" Part 2 subsection should map to `wd.qualification` (education_text + experience_text) | Architecture Patterns, Code Examples | If the intended meaning of "Skills" is actually OASIS competency data or a different field, the rendered section content would be wrong; low risk since qualification (education/experience) is the closest existing analog and was already used for the equivalent "Essential Qualifications" section in the TBS template |
| A2 | "Responsibilities" Part 2 subsection maps to the Responsibility-category JES factors (narrative) or to duties — exact mapping undetermined | Architecture Patterns | Could misplace content between "Key Activities" (duties) and "Responsibilities" sections if the planner doesn't make an explicit choice; see Open Questions |
| A3 | Signature blocks (Employee/Supervisor/Manager name+signature+date) should render as blank static labels, not bound to WD data | Common Pitfalls (Pitfall 5) | If a reviewer expects these to be data-bound, the content-presence test (ACC-04) would need explicit exclusion logic for these fields, which the planner must specify rather than assume |
| A4 | Position-identification table fields with no current WD analog (Job Code, Office code, Language/Linguistic/Communications/Security requirements) should render `[To be completed by advisor]` rather than be omitted from the template entirely | Code Examples | If the team decides those fields are out of scope for v3.0 and should be dropped from the table layout instead, the template's row count and self-verify `required` set would differ |

**If this table is empty:** N/A — see entries above; all four need explicit confirmation in planning/discuss-phase before being treated as locked.

## Open Questions

1. **What exactly maps to the "Responsibilities" Part 2 subsection, distinct from "Key activities"?**
   - What we know: Duties (Key Activities) already populate from `wd.duties`/`record.duties`. JES factors include a "Responsibility" category (Decision making, Leadership & operational mgmt for EC; Interaction, People & operational mgmt, Decision making for FB; etc.).
   - What's unclear: Whether "Responsibilities" should be a narrative summary derived from Responsibility-category JES factor rationale text, a restatement of duties, or a new free-text field not yet captured in the conversation flow.
   - Recommendation: Default to rendering Responsibility-category JES factors (factor name + rationale) when available, falling back to `[To be completed by advisor]` for groups with no Responsibility-category factors defined at all (none currently lack it — every group in `JES_FACTORS_BY_GROUP` and `EC_JES_ELEMENTS` has at least one Responsibility-category factor) — confirm this choice during planning/discuss-phase since it's not explicitly specified anywhere in REQUIREMENTS.md.

2. **Should the 6 position-identification fields with no current WD data source (Job Code, Office code, Language requirements, Linguistic profile, Communications requirements, Security requirements) be included in the template at all?**
   - What we know: The reference docx has all 17 fields; the existing `WorkDescription` model has no corresponding fields for 6 of them.
   - What's unclear: Whether v3.0 scope expects these to always render `[To be completed by advisor]` (simplest, matches ACC-02's stated fallback pattern) or whether the table should be trimmed to only the fields the WD model can populate.
   - Recommendation: Include all 17 fields with `[To be completed by advisor]` fallback for the 6 unmapped ones — keeps the template visually identical to the GoC reference format (accessibility/compliance value) and is consistent with ACC-02's explicit fallback-placeholder pattern for Effort/Working Conditions; cheap to implement, low risk.

3. **Do the 3 signature blocks need any data binding at all, or are they purely static print-and-sign text?**
   - What we know: No structured employee/supervisor/manager name fields exist on `WorkDescription`. ACC-04's content-presence test specifically scopes to "every non-placeholder template variable" — implying some variables are expected/allowed to stay placeholder.
   - What's unclear: Whether "signatures" in the success criteria just means the section headings + static labels exist (no Jinja2 vars), or whether the team wants at least `supervisor_title`/`supervisor_position_number` (already collected) bound into the Supervisor statement block.
   - Recommendation: Render signature blocks as fully static text (headings + "Name:", "Signature:", "Date:" labels with blank lines) — zero new Jinja2 variables — since this is the simplest option and matches how the reference docx itself presents these fields (no data, just labeled blank space for hand/print signing).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| docxtpl | Template rendering | ✓ | 0.18.0 installed (0.19.0 pinned in requirements.txt) | None needed — already functional, pre-existing minor version drift |
| python-docx | Template build + content-presence test | ✓ | 1.1.2 | — |
| Reference document (`data/AI Docs/Accessible Job Description Template (1).docx`) | Template structure source | ✓ | — | Duplicate copy also at `data/Class context/AI documents/...` |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

Note: a LibreOffice lock file (`.~lock.Accessible Job Description Template (1).docx#`) exists next to the reference document in `data/AI Docs/`, suggesting it may currently be open in a LibreOffice session on this machine. This did not block read access via `python-docx` in this research session, but if the planner or a later task tries to `cp`/move/delete that file, check the lock isn't held by an active process first.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 + pytest-asyncio 0.24.0 [VERIFIED: requirements.txt] |
| Config file | `v2/backend/pytest.ini` or `pyproject.toml` (not inspected in detail; existing `tests/test_export.py` runs under this framework today) |
| Quick run command | `cd v2/backend && python -m pytest tests/test_export.py -x` |
| Full suite command | `cd v2/backend && python -m pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ACC-01 | `build_accessible_template.py` self-verify passes; required Jinja2 vars declared | unit (script-level assertion, run via `python scripts/build_accessible_template.py`) | `cd v2/backend && python scripts/build_accessible_template.py` | ❌ Wave 0 — script doesn't exist yet |
| ACC-02 | Effort/Working Conditions populated from JES factors; placeholder fallback for groups without those factors | unit/integration (`export_service._build_wd_context` direct call, or via export endpoint with seeded WD fixtures for EC, FB, MT, NU) | `pytest tests/test_export.py -k accessible_effort -x` | ❌ Wave 0 — new test cases |
| ACC-03 | Export endpoint returns Accessible-format DOCX; existing tests pass updated assertions | integration (existing `test_export_wd_docx_returns_bytes` etc., updated) | `pytest tests/test_export.py -x` | ✅ exists, needs assertion updates |
| ACC-04 | Content-presence: every non-placeholder var resolves non-empty for a fully-completed WD | integration (python-docx read-back of rendered bytes) | `pytest tests/test_export.py -k content_presence -x` | ❌ Wave 0 — new test |

### Sampling Rate
- **Per task commit:** `cd v2/backend && python -m pytest tests/test_export.py -x`
- **Per wave merge:** `cd v2/backend && python -m pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `v2/backend/scripts/build_accessible_template.py` — does not exist; ACC-01's self-verify script
- [ ] `v2/backend/app/templates/wd_accessible_template.docx` — generated artifact, does not exist until the script above runs
- [ ] New test cases in `tests/test_export.py` (or a new `tests/test_accessible_template.py`) covering: Accessible-format structural assertions, per-OG Effort/Working Conditions fallback behavior (at minimum: EC with full factors, FB or another point-rating group with Effort+Conditions, MT or SW-SCW with no Effort/Conditions factors at all, and a level-description group like IT/AS/NU with zero `jes_scores`), and the content-presence read-back test
- [ ] Fixture WDs for each of the 4 JES-shape categories above (EC LLM-style, point-rating-with-effort, point-rating-without-effort, level-description) — needed to exercise ACC-02's placeholder-fallback branches

## Security Domain

Not applicable — this phase has no security-sensitive surface beyond what already exists (no new auth, no new user input parsing beyond what `_build_wd_context` already handles, no new external network calls). The existing `html.escape()` pattern used in the PDF export path (`app/api/export.py`) is a reasonable model if any new free-text WD field — e.g. `client_service_results` — needs interpolation into a context that isn't already Jinja2-escaped by docxtpl (docxtpl/Jinja2 autoescaping behavior for `.docx` XML should be confirmed during implementation, but `{{ var }}` substitution into Word XML text runs via docxtpl already handles this safely in the existing TBS/poster templates with free-text duty content).

## Sources

### Primary (HIGH confidence)
- `data/AI Docs/Accessible Job Description Template (1).docx` — read directly via python-docx in this session; structure (Part 1/Part 2 headings, 17-field table, 7 Part 2 subsections) extracted and verified
- `v2/backend/scripts/build_wd_template.py` — read in full; exact pattern to replicate
- `v2/backend/scripts/build_poster_template.py` — read in full; confirms poster path is independent
- `v2/backend/app/services/export_service.py` — read in full; exact functions to change vs. leave alone
- `v2/backend/app/api/export.py` — read in full; confirms route signatures unchanged
- `v2/backend/app/services/jes_service.py` — read in full; confirms `category` key inconsistency between EC and point-rating paths (lines 105-146, 228-260)
- `v2/backend/app/data/constants.py` (lines 1360-1523) — `EC_JES_ELEMENTS`, `JES_FACTORS_BY_GROUP`, `NON_EC_TOTALS` read directly; confirmed which groups have Effort/Conditions categories
- `v2/backend/app/models/work_description.py` — read; confirms no employee/supervisor/manager name fields exist
- `v2/backend/tests/test_export.py` — read in full; existing assertions to update for ACC-03
- `v2/backend/requirements.txt` — `pip show docxtpl python-docx` cross-checked against pinned versions
- Context7 `/websites/docxtpl_readthedocs_io_en` — `get_undeclared_template_variables()` API confirmed current as of docxtpl docs

### Secondary (MEDIUM confidence)
- `v2/frontend/src/data.jsx` line 657-662 — `client_service_results` step confirmed present in QUESTION_BANK (Phase 23/WG-03), confirming a data source exists in `wd.record["client_service_results"]`

### Tertiary (LOW confidence)
- None — all findings in this research were directly verified against the codebase or reference document.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — exact versions confirmed via `pip show` and `requirements.txt`; no new dependencies needed
- Architecture: HIGH — existing two-template pattern is unambiguous and directly inspected; the only genuinely open design decisions (Open Questions 1-3) are about Part 2 field-to-data mapping for "Responsibilities" and signature blocks, which REQUIREMENTS.md does not pin down
- Pitfalls: HIGH — the EC `category`-key gap (Pitfall 2) and SW/ED sub-group routing (Pitfall 3) were found by direct code inspection, not inference

**Research date:** 2026-06-16
**Valid until:** 30 days (stable internal codebase; no external API/library currency risk since no version upgrades are needed)
