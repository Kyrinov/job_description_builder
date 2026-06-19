# Feature Landscape — v4.0 Seven-Elements Conversational Architecture

**Domain:** GC/DND HR job description builder — subsequent milestone on existing React 18 SPA + FastAPI system
**Researched:** 2026-06-19
**Scope:** 6 feature areas; v3.0 features (SJD Library, Writing Guide, Risk Audit, OG Expansion, Accessible Template) already shipped — do not re-research

---

## Research Basis

Primary authoritative sources consulted directly:

- `data/AI Docs/Accessible Job Description Template (1).docx` — TBS template dated May 2, 2024; exact section structure confirmed
- `data/AI Docs/Job Description Writing Guide.docx` — TBS June 2023; all 7 Part 2 section definitions extracted
- `data/OASIS-2025-Skills.json`, `data/OASIS-2025-WorkContext.json` — OaSIS 2025 structured field schemas; available for Skills/Effort/Working Conditions enrichment
- TBS Directive on Classification (web) — confirmed org context required elements
- UI Patterns — completeness meter design pattern documentation

Confidence: HIGH for GoC content (direct document reads). MEDIUM for UX patterns (web synthesis). LOW where only single web source available.

---

## Feature 1: Organizational Context Conversational Step

### What it is in the GoC domain

Organizational Context is **Part 2, Section 1** of the Accessible JD Template (confirmed from document read). The TBS template provides four mandatory bullet-point prompts:

1. Work stream applicability — "Applies to the [add a specific work stream, if using a departmental SJD]"
2. Organizational placement — "Typically resides within [directorate name / region name / nationally / under a specific functional authority / other organizational level]"
3. Reporting relationship — "Typically reports to a position [at the xx-xx group and level / to an EX-xx position / to a supervision position at a minimum xx-xx group and level / other positional structure]"
4. Additional contextual information — "[Add any other contextual information that should be taken into consideration when determining the application of this job description]"

The TBS Writing Guide (June 2023, Implementation section, p. confirmed) states: "When implementing any existing job description, including an ISJD or SJD, pay particular attention to the organizational context." This is the primary gating factor for SJD application — the same job duties can be classified differently based on organizational placement and reporting structure.

The GoC Directive on Classification also confirms: "job descriptions must include the organizational context, mandate and supervisor-subordinate relationships."

**What an org context paragraph actually contains (from SJD data + template):**
- The organizational unit the position belongs to (directorate, branch, sector)
- The mandate of that unit (why it exists, what it delivers)
- Who the position reports to (title, OG/level of supervisor)
- Whether the position is regional, national, or functional authority-based
- SJD stream applicability (if an SJD is being applied — which stream within the SJD)
- Any unique scoping that determines why this particular SJD variant applies vs. another

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Capture org unit / directorate name | Required by TBS template | Low | Free-text field |
| Capture reporting relationship (supervisor OG/level) | Required by TBS template | Low | Can pre-fill from `og_confirmed`/`og_level` already on WD |
| Capture work stream (if SJD in use) | Required for SJD implementation | Low | Pre-fillable from `sjd_source` field already on WD |
| Render above Client Service Results in document preview | Required by template structure | Low | Sequencing in `document.jsx` |
| Persist as new `org_context` field on WorkDescription | Required for export | Low | Schema extension on existing WD model |
| SJD pre-fill of work stream field | Template explicitly prompts for this | Low | Read from `sjd_source` on WD |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Socratic prompts that mirror the 4 TBS bullet-point sub-elements | Produces structurally valid org context without training the advisor on the template format | Medium | QUESTION_BANK extension; answers assemble into a structured paragraph |
| Supervisor OG/level inferred from `og_confirmed`/`og_level` | Reduces re-entry; supervisor is often one level above the position being described | Low | Logic: supervisor is typically the next OG level up; advisor confirms or overrides |
| DND org chart integration hint — directorate names from `DND_Org_26-Feb-2026-L3-FINAL_v2.xlsx` | Pre-populated dropdown for DND-specific directorates reduces typos and improves analytics downstream | High | Requires parsing the Excel org chart; out of scope for v4.0 unless data is clean |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Free-text paragraph box as the only input | Advisors write inconsistently; unstructured org context is useless for workforce analytics | Use the 4 TBS sub-elements as discrete Socratic questions that assemble into the paragraph |
| Making org context a hard gate before other phases | The advisor may not know the org structure details at the start | Collect at the Role phase entry; allow "return and fill" via the existing jump navigation |
| Storing org context as a single prose blob | Blocks structured analytics export | Store as structured sub-fields (`org_unit`, `reports_to_og_level`, `work_stream`, `additional_context`); render as prose at export time |

### Complexity

Medium. The Socratic capture is 3-4 new STEPS (additive to existing STEPS array). The data model extension is 4 new sub-fields on `WorkDescription`. The document preview sequencing moves Client Service Results below Org Context — a section-order change in `document.jsx`. SJD pre-fill is a simple read of `sjd_source` already on the WD.

The hardest sub-problem is deciding where in the STEPS array the org context questions live: they belong in the Role phase (Phase 0/1) because they inform classification — an EC-05 in a policy directorate reporting to an EX-01 is a very different JD than the same group/level in a regional operations centre. Current Phase 0 captures position title and CAF context only; org context questions extend Phase 0.

### Dependencies on Existing System

- `sjd_source` field on WorkDescription (Phase 22) — pre-fills work stream
- `og_confirmed` and `og_level` on WorkDescription (Phase 16) — used to infer supervisor's OG/level
- Phase 15 STEPS array — new steps added to Phase 0 (Role phase)
- `document.jsx` section rendering — `org_context` block inserted above `client_service_results` block
- `export_service.py` `_build_wd_context()` — new template variables `org_context_*` passed to accessible template (already has `{{ org_context }}` slot from Phase 25 build)

---

## Feature 2: Responsibilities Narrative

### What it is in the GoC domain

"Responsibilities" is **Part 2, Section 5** of the Accessible JD Template (confirmed from document). The TBS Writing Guide defines it as:

> "This section describes the job's responsibility for human, financial and technical resources. This section should describe: the specific role, authorities and latitude for decision making related to these resources; any direct supervision of employees; the requirement to lead working groups and project teams; and the level of risk involved in management of the resources."

This element directly feeds the **Responsibility factor** in the JES point-rating standard for EC (and analogous factors in FB, FS, LP, MT). For EC, the Responsibility factor includes sub-elements for supervisory authority, financial signing authority, and span of control — all of which must appear in the JD to be evaluable.

The gating logic (supervisory/senior positions): the Responsibilities section is only materially different from a generic statement when the position has direct reports, delegated financial authority, or project-team leadership. For non-supervisory EC-01 through EC-03 positions, this section is often a single sentence. For EC-04+ or any supervisory position, it is substantive.

The existing system already has `supervisory` as a signal captured in the Work Type Socratic questions and `og_level` which determines supervisory threshold. Gate logic: `supervisory == true OR og_level >= 4` for EC, or any OG with formal supervision built into their level definitions (AS, FI, etc.).

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Capture direct supervision Y/N and number of direct reports | Required by JES Responsibility factor for any supervisory position | Low | Already partially captured as a Socratic signal; needs storage |
| Capture delegated financial signing authority (Y/N, amount) | Required by JES financial signing sub-factor; common in EC-04+ and AS-05+ | Low | New Socratic question |
| Capture project/working group leadership | Required by JES Responsibility language | Low | New Socratic question |
| Gate display of these questions on supervisory/senior signal | Non-supervisory EC-01 does not need this section | Low | Boolean gate in STEPS based on `supervisory` signal |
| Render in "Responsibilities" section of document preview and export | Part 2, Section 5 of accessible template | Low | Section already exists in template (Phase 25); needs content |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Tie responsibility narrative to JES Responsibility factor degree | Show the advisor which factor degree their supervision scope implies (e.g., "3 direct reports at the same OG group implies JES Responsibility Degree B") — invisible to manager mode | Medium | Requires JES factor degree logic lookup per OG |
| Decision-making authority capture (latitude for action) | Covers the "freedom and authority to make decisions" sub-element that the Writing Guide flags as critical for Skills evaluation | Low | One additional Socratic question |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Making this section mandatory for all positions | A non-supervisory EC-01 does not have meaningful responsibility content | Gate on supervisory/senior signals; render placeholder for non-supervisory |
| LLM-drafted narrative | Writing Guide is explicit that JD content must describe assigned work, not be LLM-interpreted | Assemble structured answers into a template-filled paragraph (same pattern as org context) |

### Complexity

Low-Medium. The Socratic questions are 3-4 new STEPS, all gated. The storage is 4-5 new sub-fields on WorkDescription (`direct_reports_count`, `financial_signing_authority`, `project_leadership`, `decision_latitude`). The gate logic reuses the existing `supervisory` signal from Phase 12. No new API routes needed — this extends the existing WD PATCH flow.

### Dependencies on Existing System

- `supervisory` signal from Phase 12 QUESTION_BANK — gate trigger
- `og_level` (Phase 16) — secondary gate (level 4+ implies supervisory capacity)
- Phase 15 STEPS array — new gated steps in Duties phase or new Phase between Duties and Qualifications
- Accessible template (Phase 25) — `{{ responsibilities }}` variable already declared; needs populated content instead of placeholder

---

## Feature 3: Seven-Elements Completeness Audit

### What it is in document-building tools

The completeness audit answers: "Which of the 7 Part 2 elements have substantive content vs. are still placeholder/empty?" It is not a quality audit (that is Phase 24's Risk Audit) — it is a coverage audit.

**Authoritative pattern — Completeness Meter (ui-patterns.com, confirmed):**
> "A completeness meter displays progress as a percentage-based indicator. It divides an end-goal into smaller sub-tasks. As users complete each task, the percentage increases toward 100%. The interface provides links or hints to how the progress can be improved. Should NOT be used when the end-goal is dependent on a series of strictly sequential tasks — it is better for non-linear, optional task completion."

This is precisely the right pattern for 7-element coverage: the elements are not strictly sequential (an advisor can capture Working Conditions before Responsibilities) but all 7 should be non-empty before export.

**The 7 elements (from Accessible JD Template, confirmed):**
1. Organizational Context
2. Client Service Results
3. Key Activities
4. Skills
5. Effort
6. Responsibilities
7. Working Conditions

**Three status values per element:**
- `populated` — user-provided content exists (advisor entered via Socratic conversation)
- `derived` — content is derivable from existing WD data without new input (e.g., Skills can be partially derived from OASIS data keyed to the confirmed NOC code; Effort/Working Conditions can be derived from JES factor scores where the OG's JES standard defines those factors — ACC-02 already implements `_factor_category_map()` for this)
- `missing` — no content and no derivable source; export will produce a `[To be completed by advisor]` placeholder

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Per-element status badge (populated / derived / missing) in Review phase | Users expect to know what is complete before exporting | Low | Read from WD fields; logic is a mapping function |
| Overall completeness indicator (e.g., "5 of 7 elements complete") | Summary view expected in any document builder | Low | Aggregate of per-element status |
| "Jump to fill" links per missing element | Navigate to the relevant conversation step from the Review phase | Low | Reuse `jumpToExchange(idx)` already in `app.jsx` |
| `POST /api/wd/{id}/validate-elements` endpoint | Returns per-element status JSON | Low | Pure computation; no DB writes |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Distinguish "derived" from "missing" visually | Tells advisor they don't need to manually fill Effort if it's derivable from JES — reduces friction | Low | Third badge state; CSS only |
| OASIS Skills enrichment signal | For the confirmed NOC code, the OASIS 2025 Skills data already in `data/OASIS-2025-Skills.json` provides skill ratings — surface as a "derivable from NOC" indicator for the Skills element | Medium | Requires NOC→OaSIS code mapping; data is present but mapping needs building |
| Block export with a "soft gate" until advisor acknowledges missing elements | Not a hard block — advisor sees "2 elements are placeholder — export anyway?" dialog | Low | One-click acknowledge pattern |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Hard gate on export until all 7 are populated | Advisors legitimately export with Effort/Working Conditions as placeholders for advisor-to-complete workflows | Soft gate with acknowledgment only |
| Running the completeness check on every save | Creates performance noise; only meaningful when advisor is in Review phase | Trigger on Review phase entry or explicit "Check completeness" button |
| Combining with Risk Audit (Phase 24) | Two different concerns: coverage vs. compliance | Keep as separate badge/section in Review state; Risk Audit panel is already its own component |

### Complexity

Low. This is a read-only computation over fields already stored on WorkDescription. The endpoint computes a mapping:

```
org_context → populated if org_context_unit or org_context_reports_to is non-empty
client_service_results → populated if answers['client_service_results'] is non-empty
key_activities → populated if draft duties list length > 0
skills → populated if quals have education/experience; derived if confirmed_noc is set (OASIS lookup)
effort → derived if jes_scores include sensory/physical effort factors; missing otherwise
responsibilities → populated if responsibilities_narrative fields are non-empty; derived if supervisory==false (standard placeholder is valid)
working_conditions → derived if jes_scores include working conditions factor; missing if no JES factor
```

The frontend renders this as a checklist in `ReviewState` (already exists — Phase 24 added the audit panel to ReviewState). Adding a completeness section above the audit panel is additive.

### Dependencies on Existing System

- `jes_scores` on WorkDescription (Phase 17) — source for derived Effort/Working Conditions
- `_factor_category_map()` in `export_service.py` (Phase 25 ACC-02) — already maps JES factors to Part 2 sections; reuse this logic
- `confirmed_noc` on WorkDescription (Phase 14) — enables OASIS Skills derivation signal
- Phase 24 `ReviewState` audit panel — completeness badge added as a sibling component
- Phase 25 accessible template placeholders — the `[To be completed by advisor]` strings are already the canonical placeholder value to detect "missing"

---

## Feature 4: Manager-Track UX

### What it is in conversational HR tools

**The core design principle (from multi-role UX research):**
> "Navigation adaptation: the main navigation should adapt based on user role. An administrator might see 'System Settings' and 'User Management,' while a standard user would not. Users receive only the minimum information and functionality required to perform their job."

**Julian's directive makes the boundary explicit:** Managers never see "OG", "JES", or the 7-element framework names. They just build a JD. The classification mechanics are the advisor's domain.

**Role selector at entry — the "I am a" pattern:**
Research confirms this is standard onboarding practice. The pattern: at the application entry point (before any conversation step), a role choice card is presented. Two cards: "Classification Advisor / HR Professional" and "Hiring Manager". This is a one-click selection, not a form. Selection persists in localStorage (same key as existing `jd-builder-v2-record`).

**What manager mode hides vs. shows:**

| UI Element | Advisor Mode | Manager Mode |
|------------|-------------|--------------|
| OG group/level badge | Shown (Phase 16) | Hidden — show only "Job level: Senior Analyst" etc. |
| JES scoring block | Shown (Phase 17) | Hidden completely |
| Classification Socratic questions (qb_work_output_type etc.) | Shown | Hidden — replaced by plain-language "What type of work does this role do?" |
| AS/EC disambiguation alert | Shown | Hidden |
| CBA/collective agreement references | Shown | Hidden |
| Risk Audit panel | Shown | Hidden — replaced by "Send to your HR advisor for review" prompt |
| 7-element framework labels (Effort, Responsibilities, Working Conditions section names) | Shown as document section headers | Hidden — show as "Physical demands", "Decision-making", "Work environment" in plain English |
| Completeness badge | Shown with 7-element names | Shown with plain-language equivalents |
| Export buttons | DOCX + PDF + Accessible | "Download draft JD" (same DOCX, different label) |

**What manager mode outputs:** The same Accessible JD DOCX — but with a cover note "This draft job description has been prepared by [manager] for review by your HR Classification team. Please contact [X] to complete the classification evaluation." The structured data is captured invisibly and available for export.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Role selector at app entry ("I am a..." cards) | Required to branch experience | Low | One new component; localStorage persistence |
| Manager mode hides all OG/JES/CBA terminology in conversation pane | Core directive from Julian | Medium | Conditional rendering on `userRole` state slice |
| Manager mode replaces classification steps with plain-language equivalents | Manager should describe work without classification vocabulary | Medium | New STEPS entries for manager path; existing advisor STEPS unchanged |
| Manager output is a "draft for advisor" — labeled as such | Prevents manager from treating output as final classification decision | Low | Export label and cover-page text change |
| Role persists across sessions (localStorage) | Prevents re-selecting every session | Low | Add `userRole` to existing localStorage recovery pattern |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Advisor mode can "preview as manager" | Advisor can see what the manager will see before sending | Medium | Toggle in advisor mode only |
| Manager output auto-flags for advisor review — `GET /api/wd/{id}/review-needed` | Manager-created WDs enter a "pending advisor review" status visible to the advisor | High | Requires multi-session state; out of scope for v4.0 single-user app |
| Plain-language OG mapping in manager mode | When manager selects "Policy and research" work type, the advisor mode sees EC-04 signals — invisible translation layer | Medium | Signal accumulation unchanged; display labels change |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Two separate apps or routes | Doubles maintenance burden; classification data must stay on same WD model | Conditional rendering on `userRole` state slice within the same SPA |
| Asking for role selection on every session start | Friction for established users | Persist to localStorage; allow role change from settings |
| Exposing "OG code", "JES", "EC-04" anywhere in manager-facing text — even in error messages | Julian's directive is explicit | Audit every user-visible string in the STEPS array and document preview for advisor-only terminology |
| Making manager mode produce a different data model | The workforce analytics export must work from the same WD regardless of which role created it | Single WD schema; role only affects display layer |

### Complexity

Medium-High. The data model is unchanged — `userRole` is a UI concern only. The implementation has two distinct sub-problems:

1. **STEPS branching**: The current STEPS array drives both phases and conversation steps. Manager mode needs a parallel STEPS variant that omits classification questions and replaces with plain-language equivalents. This is the same pattern as the existing supervisory gate but applied to the entire classification phase (Phase 1 in STEPS). Two options: (a) a `getSteps(userRole)` function that returns different STEPS arrays; (b) a `managerVisible` flag on each step. Option (a) is cleaner — no interleaving of concerns.

2. **Conditional rendering audit**: Every component that renders advisor-specific terminology needs a `userRole` prop or context. This touches `conversation.jsx` step rendering, `document.jsx` section labels, `ClassBlock`, the Review phase checklist, and export button labels. A systematic audit pass is required.

The `userRole` state slice is a new addition to the 8 existing state slices in `app.jsx`. The localStorage key needs a new `user_role` field.

### Dependencies on Existing System

- Phase 15 STEPS array — parallel manager variant created
- Phase 12 QUESTION_BANK — manager path uses subset of questions with relabeled text
- Phase 13 SPA state slices — new `userRole` slice added
- Phase 20 export buttons and labels — conditional on `userRole`
- Phase 24 Risk Audit panel — hidden in manager mode
- Phase 25 DOCX export — cover note text conditional on `userRole`

---

## Feature 5: Enhanced Job Poster Generation

### What it is in the domain

The existing job poster DOCX (Phase 20) already produces a bilingual-header poster with top-5 duties and qualifications. The v4.0 enhancement uses all 7 Part 2 elements as source material:

- **Org Context → "About the team/organization"** section in the poster (currently blank or absent)
- **Client Service Results → Job summary** (currently inferred from duties)
- **Key Activities → Duties** (already in place — top-5)
- **Skills → Qualifications** (already in place)
- **Effort → Physical demands** (currently absent; only relevant for some OG groups)
- **Responsibilities → Level/scope** statement (adds seniority context for job seekers)
- **Working Conditions → Work environment** (currently absent)

The job poster serves a dual purpose in the GoC: (1) a staffing advertisement for open competitions, and (2) a reference document for managers explaining the role. The v3.0 poster only addressed (1). The enhanced poster addresses both.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Org Context paragraph in "About the organization" poster section | Posters without org context feel generic | Low | Map `org_context_*` fields to poster template variable |
| Client Service Results as the job summary blurb | More accurate than inferring from duties | Low | Map `client_service_results` answer to poster summary |
| Responsibilities narrative in "Level and scope" section | Helps job seekers assess if the role fits their experience | Low | Map `responsibilities_narrative` to poster section |
| Effort / Working Conditions sections (gated on content availability) | Only render if content is non-empty; do not show "[To be completed]" in a public poster | Low | Content gate in `_build_poster_context()` |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Bilingual poster sections populated from 7-element data | French placeholder already in template (Phase 20); enhanced data enables more complete bilingual stubs | Low | Machine translation is out of scope; placeholder quality improves |
| Poster format toggle: "competition poster" vs. "role brief" | Competition poster is public-facing; role brief is manager-facing with classification details | Medium | Two template variants or conditional sections |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Duplicating poster template logic in two places | Phase 20's `build_poster_template.py` is the single source of truth | Extend `_build_poster_context()` in `export_service.py` only |
| Showing JES scores or OG codes in the public poster | Staffing posters are external-facing | Gate classification fields behind `include_classification` flag (default False for poster) |

### Complexity

Low. This is purely additive to the existing poster generation. `_build_poster_context()` in `export_service.py` gains new optional keys. The poster DOCX template (`build_poster_template.py`) gains new optional sections (rendered only when content is non-empty via Jinja2 `{% if %}` blocks). No new routes or schema changes needed.

### Dependencies on Existing System

- Phase 20 `_build_poster_context()` and `build_poster_template.py` — extended, not replaced
- Feature 1 (Org Context) — must be built first; poster can only show org context once it's captured
- Feature 2 (Responsibilities Narrative) — must be built first for the "Level and scope" poster section

---

## Feature 6: Structured Data Export (JSON + CSV)

### What it is in workforce analytics

**Julian's directive:** "A JD is a way to get data for a bunch of different things." The structured export captures all 7 Part 2 elements as machine-readable data for workforce analytics.

**What HR analytics teams actually consume (MEDIUM confidence — web synthesis + OaSIS data structure evidence):**

From the OaSIS 2025 data already in the project (`data/OASIS-2025-Skills.json`, `data/OASIS-2025-WorkContext.json`), the field schema that GoC analytics infrastructure is already designed around includes:

- **Occupation identifier** — NOC code (primary key linking to external taxonomy)
- **Skills profile** — per-skill ratings (0-5 scale, 34 skill dimensions in OaSIS)
- **Work context** — structured ratings for automation, competition, consequence of error, freedom to make decisions, time pressure, work schedules, hazardous conditions (25+ work context dimensions)
- **Classification fields** — OG code, level, JES score/method

For workforce analytics export from this system, the schema maps to:

```json
{
  "export_version": "4.0",
  "export_date": "ISO-8601",
  "wd_id": "string",
  "position": {
    "title": "string",
    "og_code": "string",
    "og_level": "integer",
    "noc_code": "string",
    "sjd_number": "string | null",
    "effective_date": "string | null"
  },
  "classification": {
    "jes_total_points": "integer | null",
    "jes_method": "point_rating | level_description",
    "jes_scores": [{"factor": "string", "degree": "string", "points": "integer | null"}]
  },
  "part2_elements": {
    "organizational_context": {
      "org_unit": "string",
      "reports_to_og_level": "string",
      "work_stream": "string | null",
      "additional_context": "string | null"
    },
    "client_service_results": "string",
    "key_activities": ["string"],
    "skills": {
      "education": "string",
      "experience": "string",
      "knowledge_areas": ["string"]
    },
    "effort": "string | null",
    "responsibilities": {
      "direct_reports_count": "integer | null",
      "financial_signing_authority": "boolean | null",
      "project_leadership": "boolean | null",
      "decision_latitude": "string | null"
    },
    "working_conditions": "string | null"
  },
  "provenance": {
    "noc_confirmed": "boolean",
    "sjd_sourced": "boolean",
    "classification_date": "string | null",
    "audit_run": "boolean"
  }
}
```

**CSV format for analytics pipelines:** One row per position. Flat schema — nested objects are serialized as dot-notation columns (`part2_elements.organizational_context.org_unit`, `classification.jes_total_points`, etc.). This is the format analytics tools (Excel, Power BI, Python pandas, R) can consume directly without JSON parsing.

**What analytics teams use these fields for:**
- Role profiling and job architecture (NOC + OG + level + skills → job family taxonomy)
- Span-of-control analysis (direct_reports_count + og_level → supervision ratio)
- Workforce planning scenario modeling (key_activities → competency demand mapping)
- Classification consistency auditing (same OG/level → same JES score range)
- OaSIS skills gap analysis (position skills vs. NOC-linked OaSIS profile)

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `POST /api/wd/{id}/export/json` — returns structured JSON | Machine-readable format is the primary analytics ask | Low | Serialization of existing WD fields + new Part 2 fields |
| `POST /api/wd/{id}/export/csv` — returns flat CSV | Interoperability with Excel/Power BI without JSON parsing | Low | Flatten the JSON schema to dot-notation columns |
| All 7 Part 2 elements in export (populated or null) | Analytics teams need consistent schema across all exports; nulls are acceptable | Low | Include all 7 regardless of population status |
| Provenance metadata in export (sjd_sourced, audit_run, noc_confirmed) | Analytics teams need to know data quality / derivation method | Low | 4-5 boolean/string provenance fields |
| Frontend download button — "Export data (JSON)" and "Export data (CSV)" | Users expect self-serve download | Low | Same pattern as existing `exportAs()` in `app.jsx` |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| OaSIS skills crosswalk in JSON export | Link position's confirmed NOC to OaSIS skills profile ratings from `data/OASIS-2025-Skills.json` — gives analytics teams a normalized skills baseline without building the mapping themselves | Medium | NOC → OaSIS code mapping needed; data is present |
| Bulk export (`GET /api/export/bulk/json?og_code=EC`) | Analytics teams want all WDs for a group in one pull | High | Out of scope for v4.0 single-session app; mark as v5.0 |
| Completeness score in export (`part2_completeness_score: 5/7`) | Enables analytics teams to filter for high-quality data | Low | Integer computed from completeness audit feature |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Exporting raw `WorkDescription.data` JSON blob | Internal schema is not analytics-ready; field names are implementation names not semantic names | Map to the analytics-facing schema above |
| Requiring all 7 elements to be populated before export is allowed | Analytics teams want partial data too | Export nulls for missing elements; include completeness score |
| Combining with DOCX export route | Structured data and document export are different concerns with different consumers | Separate routes; separate download buttons |

### Complexity

Low-Medium. The JSON export is a new serialization function — `_build_analytics_context()` in `export_service.py` — that maps WD fields to the analytics schema. The CSV export is a flattening of the JSON output (`pandas.json_normalize()` or equivalent pure-Python approach). Two new FastAPI routes. Two new frontend download buttons in the Review phase export block. No schema changes to the WD model — all fields already exist or will be added by Features 1 and 2.

The only moderately complex sub-problem is the NOC→OaSIS code mapping for the optional skills crosswalk. The OaSIS data uses its own code system (`Code OaSIS` field) which cross-references to NOC via the `OASIS-2025-Taxonomy.json` file. This mapping is buildable but requires a lookup pass.

### Dependencies on Existing System

- Feature 1 (Org Context sub-fields) — `org_unit`, `reports_to_og_level`, `work_stream` must exist on WD
- Feature 2 (Responsibilities sub-fields) — `direct_reports_count`, `financial_signing_authority`, etc. must exist on WD
- Feature 3 (Completeness Audit) — `completeness_score` appears in export provenance block
- Phase 17 `jes_scores` on WorkDescription — classification section of JSON export
- Phase 20 export infrastructure (`export_service.py`, `app/api/export.py`) — new functions added alongside existing

---

## Cross-Feature Dependency Map

```
Feature 1 (Org Context)
  new WD fields: org_unit, reports_to_og_level, work_stream, additional_context
  gate: Role phase (Phase 0/1 STEPS)
  pre-fill: sjd_source (Phase 22), og_confirmed/og_level (Phase 16)
  feeds: Feature 3 completeness (org_context populated check)
  feeds: Feature 5 poster (About the org section)
  feeds: Feature 6 JSON/CSV (part2_elements.organizational_context)

Feature 2 (Responsibilities Narrative)
  new WD fields: direct_reports_count, financial_signing_authority, project_leadership, decision_latitude
  gate: supervisory signal (Phase 12) OR og_level >= 4
  feeds: Feature 3 completeness (responsibilities populated/derived check)
  feeds: Feature 5 poster (Level and scope section)
  feeds: Feature 6 JSON/CSV (part2_elements.responsibilities)

Feature 3 (Completeness Audit)
  read-only computation over WD fields
  depends on: Feature 1 and Feature 2 for complete 7-element coverage
  depends on: Phase 25 _factor_category_map() for derived Effort/Working Conditions
  depends on: Phase 14 confirmed_noc for derived Skills signal
  depends on: Phase 24 ReviewState component (sibling badge added)

Feature 4 (Manager-Track UX)
  UI layer only; no new WD schema changes
  depends on: Phase 15 STEPS array (parallel manager variant)
  depends on: Phase 12 QUESTION_BANK (subset for manager path)
  depends on: Phase 13 localStorage state (new userRole slice)
  must be built AFTER Features 1 and 2 — manager path for org context and responsibilities
  needs to be built BEFORE Features 5 and 6 ship to users (manager mode affects export labels)

Feature 5 (Enhanced Poster)
  depends on: Feature 1 (org context content)
  depends on: Feature 2 (responsibilities content)
  extends Phase 20 _build_poster_context() — additive only

Feature 6 (Structured Data Export)
  depends on: Feature 1 and Feature 2 (new WD fields in schema)
  depends on: Feature 3 (completeness_score in provenance block)
  extends Phase 20 export_service.py — new serialization function
  data/OASIS-2025-Skills.json + data/OASIS-2025-Taxonomy.json already present for optional skills crosswalk
```

---

## MVP Prioritization for v4.0

**Build first (foundations that everything else depends on):**
1. Feature 1 — Organizational Context conversational step. Creates new WD fields used by Features 3, 5, 6.
2. Feature 2 — Responsibilities Narrative. Creates remaining new WD fields used by Features 3, 5, 6.

**Build second (the audit and analytics layer):**
3. Feature 3 — Seven-Elements Completeness Audit. Pure computation over fields from Features 1 and 2. Depends on both being in place.
4. Feature 6 — Structured Data Export. Can be built in parallel with Feature 3 once Features 1 and 2 are in place; no dependency on Feature 3 except the completeness score field.

**Build third (UX and output enhancement):**
5. Feature 4 — Manager-Track UX. Depends on all content features being stable (Features 1-3) so the manager path covers complete content.
6. Feature 5 — Enhanced Poster. Depends on Features 1 and 2 for source content; built last as an output enhancement.

---

## Open Questions

- **Org Context — DND org chart data:** `DND_Org_26-Feb-2026-L3-FINAL_v2.xlsx` exists in the project. If the directorate names are in a parseable format, a dropdown of DND organizational units for the `org_unit` field would significantly improve analytics quality. Scope this as optional enhancement pending a quick data quality check.

- **NOC→OaSIS code mapping:** The OASIS 2025 files use OaSIS codes (`00010.00` format) while the WD stores NOC 2021 codes (`1111` format). The `OASIS-2025-Taxonomy.json` should contain the crosswalk. Verify this mapping exists before committing the OaSIS skills crosswalk to the JSON export scope.

- **Manager mode — Socratic question coverage:** The plain-language manager path needs to produce enough signal to drive the same classification engine as the advisor path. The current QUESTION_BANK Socratic questions use OG-neutral language already (Phase 12 constraint: "OG codes appear only in signals.og_candidates"). This means the manager path questions can reuse the existing Socratic signals with different display text. Confirm this before designing a fully parallel STEPS array.

- **Effort and Working Conditions as Socratic questions:** The Writing Guide defines both sections and the TBS template has placeholders. The Phase 23 Deferred table noted "dedicated questions are v4." Confirm with Julian whether v4.0 adds Socratic questions for these elements or continues to derive them from JES factor scores + placeholders.

- **Export route consolidation:** v3.0 already has `POST /api/wd/{id}/export/docx`, `/poster`, `/pdf`. The JSON and CSV routes at `/export/json` and `/export/csv` extend this pattern cleanly. Confirm naming convention before building.
