# Features Research — v3.0

**Domain:** GC HR job description builder (DND-first, classification-grounded)
**Researched:** 2026-06-10
**Scope:** 6 new features layered onto the existing v2.0 conversational React SPA + FastAPI system

---

## Feature Categories

---

### Feature 1: SJD Library

**What it is in the domain.**
SJDs (Standardized Job Descriptions) are pre-classified templates, mandatory at DND under DAOD 5025-0 and TBS Policy on Classification. The DCCO SJD Guide confirms SJDs are "off the shelf" — an advisor picks one, confirms it fits the organizational context ("jobbing"), and the classification decision follows without a fresh evaluation. The data in `data/SJD Examples.txt` shows the DND format: JobCode, SJD Number, Group/Level, NOC, Org Context paragraph, OccupationalGroup. Nine distinct entries covering AS-01/03/07, CT-FIN-04, EC-02/05, EN-ENG-04, IT-03, PE-04, WP-03.

**Table stakes.**
- Browse or search library by OG group, level, title keyword, and NOC code
- Each SJD card shows: Job title, SJD number, Group/Level, NOC, brief org context excerpt
- "Use this SJD" action: pre-populates the conversation with all fields the SJD specifies (group, level, OG code, org context, duties/streams if present), skipping the Socratic classification questions for fields already determined
- Clear indication that the SJD is pre-classified — the group/level come from the SJD decision, not from the Socratic engine
- Ability to browse without committing (reference mode vs. start-from mode)

**Differentiators.**
- Similarity ranking: when the advisor has already answered Role/WorkType questions, rank SJDs by how well their org context and OG match the accumulated signals — show "best match" at top rather than a flat alphabetical list
- "Start from SJD, then refine" flow: load SJD content into the conversation as editable pre-fills, show which fields came from the SJD (provenance-tagged), and let the advisor amend the org context paragraph before export
- Stream disambiguation: the AS-07 example shows multiple supervision-factor variants of the same SJD with different point totals — the library must surface the correct variant based on span-of-control answers

**Anti-features.**
- Do not make SJD browsing a separate app page — it must integrate into the conversational flow at the Role phase (before or after the work-type Socratic questions)
- Do not block advisors who want to ignore SJDs and build from scratch — the library is a starting point, not a gate
- Do not attempt to create new SJDs through the tool — SJD creation is a DCCO function requiring job evaluation committee approval; the tool only consumes and surfaces existing ones

**Complexity:** Medium. The data set is small (dozens to low hundreds of entries from the txt file plus any additional data seeded). The hard part is the UX decision point: where in the 6-phase flow does SJD browsing appear, and how does selecting an SJD reshape the remaining STEPS. Two sub-problems:

1. Data model: `sjd_library` SQLite table seeded from `SJD Examples.txt` and any additional parsed data; minimal schema (sjd_number, title, og_code, og_level, noc_code, org_context, streams, supervisory, salary_range).
2. Flow branching: when an SJD is selected, `accumulateSignals` must be short-circuited — og_confirmed and og_level are set from the SJD, the Socratic classification questions can be skipped or shown as pre-answered. This requires a new `sjd_selected` state slice and a branch in STEPS that collapses phases 1-2.

**Dependencies on existing system.**
- Reads `og_confirmed` and `og_level` state slices (Phases 15-16) — SJD selection writes these directly
- Interacts with `QUESTION_BANK` — the SJD path bypasses or pre-answers qb_work_output_type and the OG confirmation step
- The `WorkDescription` model needs a new `sjd_number` field for provenance tracking in export
- Export (Phase 20): the version manifest should note "Classification sourced from SJD [number]" when an SJD is used

**UX pattern for "start from template" in a conversational flow.**
The right pattern is a discoverable interrupt, not a modal gate. Concretely:

- At the end of the Role phase (after position title and org context are captured), show a non-blocking prompt: "Does this role match a known DND position? Browse SJDs" — a secondary action below the primary "Continue" button
- The SJD browser opens as a slide-in panel or a focused step within the conversation thread, not a new page. The advisor can dismiss it and proceed from scratch
- If an SJD is selected, the conversation thread shows a "pre-fill card" summarizing what was imported, with each field editable. The thread then jumps to Duties phase, skipping classification questions that are now resolved
- If the advisor returns to Classification (via jump navigation), the SJD-sourced fields are shown as locked-but-overridable with a "diverge from SJD" affordance that triggers a warning ("Changing group/level means this is no longer a jobbing action — a new classification evaluation may be required")

---

### Feature 2: Accessible JD Template

**What it is in the domain.**
The existing export uses a TBS Work Description DOCX template built in Phase 20. The new template follows the Accessible Job Description Template dated May 2, 2024 (in `data/AI Docs/`). Structural difference is significant: the accessible template is section-headings-based (Part 1: Position information and signatures; Part 2: Job description with subsections Organizational context / Client service results / Key activities / Skills / Effort / Responsibilities / Working conditions). The current v2.0 export template mirrors the TBS Work Description format which has different section labelling (Section 1: Classification, Section 2: Organization, Section 3: Key Activities, Section 4: JES, Section 5: Qualifications, Section 6: DRF). These are structurally incompatible — new template replaces, not adds to, the old one.

**Table stakes.**
- Export produces DOCX following the accessible template structure exactly: Part 1 (position info + three signature blocks: employee, supervisor, manager) and Part 2 (six subsections)
- All content from the conversation maps to the correct subsection: org context paragraph to Organizational context; duties list to Key activities; qualifications education/experience to Skills (knowledge component); JES output to Skills/Responsibility subsections as appropriate
- Signature blocks are rendered as formatted areas (name/signature/date lines), not actual form fields — consistent with the existing docx approach
- The template binary artifact is reproduced by a `build_accessible_template.py` script (consistent with the Phase 20 pattern)

**Differentiators.**
- Provenance footer carries forward: each exported section still gets the `prov__tag` citation from the version manifest — the accessible format does not preclude traceability
- "Add subheadings" instruction from the accessible template: the tool should allow the advisor to add sub-headings within Key Activities for complex roles, rather than a flat bulleted list
- Bilingual section titles as optional toggle (English-only default, toggle adds French subtitle under each heading)

**Anti-features.**
- Do not maintain two parallel export templates — the accessible template replaces the old TBS Work Description DOCX; the poster DOCX is unaffected
- Do not add Effort or Working Conditions as Socratic questions in v3.0 — the accessible template has these sections but they are out of scope for the conversation; export them as "[To be completed by advisor]" placeholders

**Complexity:** Low-Medium. The structural work is a docxtpl template rebuild (`build_accessible_template.py` + new `accessible_wd.docx` binary) and an updated `_build_wd_context()` helper in `export_service.py` that maps the existing WorkDescription fields to the new section keys. The mapping logic is straightforward because the data already exists — the effort is the template design and section-key renaming. The placeholder sections (Effort, Working Conditions) are new template variables with a fixed "placeholder" string.

**Dependencies on existing system.**
- Replaces `generate_wd_docx` / `_build_wd_context` in `export_service.py` and the committed `wd.docx` binary
- The version manifest format does not change; only the template variables that receive it change
- JES output currently renders in Section 4 of the old template — in the accessible template it goes into the Skills subsection; the `ClassBlock` rendering logic in `document.jsx` may need a subsection label change in the preview too (for consistency between preview and export)

---

### Feature 3: Writing Guide Integration

**What it is in the domain.**
The TBS Job Description Writing Guide (June 2023) is authoritative. Its Appendix C writing tips are the canonical duty-writing rules for the CPA. The key principles extracted from the guide:

**Canonical duty-writing rules (from Appendix C and body of guide):**

1. **Active voice.** "Use the active voice. Write 'conduct studies' instead of 'studies are conducted.'" This is the single most commonly violated rule in bureaucratic JD writing.
2. **Conciseness and single idea per sentence.** "Use short, concise sentences so the reader can understand. If possible, limit each sentence to a single main idea. Avoid repetition."
3. **No unnecessary words.** "Avoid unnecessary words. For example, use 'modify procedures' instead of 'modify existing procedures'." The modifier "existing" adds nothing.
4. **No vague or ambiguous terms.** "Avoid ambiguous terms, limit terminology and jargon as it may cause confusion or misinterpretation and could result in the misapplication of the job evaluation standard."
5. **No inflated language.** "Avoid inflating language that makes work appear to be more demanding or more complex." Common violations: "strategic", "leading-edge", "critical", "highly complex" as unsupported adjectives.
6. **No duty-writing to the classification.** "Do not write to the occupational group and level that may be expected." A duty that describes a higher level job to push the rating up is a classification integrity violation.
7. **Linked ideas.** "Link ideas to each other." A duty statement should express the action + purpose: "determines and identifies search strategies and evaluates sources of information to locate records requested by clients."
8. **Gender-inclusive language.** Required under Pay Equity Act.
9. **Describe work assigned, not employee performance.** "Describe the requirements of the work that has been assigned by the manager and not the employee's performance nor the employee's qualifications."
10. **Result-oriented framing.** Client Service Results: "describe the products and/or services that a job provides or delivers." Key activities must answer "What responsibilities belong to this job?" not just enumerate tasks.

**Classification implications flagged in the guide.**
The guide explicitly connects duty-writing quality to classification outcomes: "delays in documenting significant changes in the job description may lead to an incorrect classification." From the ERR Principles document: "Classification is not as simple as doing a 'word match'. It is necessary to read the words in context and look at the whole of the work involved." (FC: Bourdeau) — this means inflated or vague duties that mislead a factor rating are a legal risk, not just a style issue.

**Table stakes.**
- Inline tips during duty entry: when the advisor is in the Key Activities / Duties step, brief contextual hints appear (e.g., "Start with an active verb", "One idea per sentence")
- Passive voice detection: flag duty statements where the main verb is passive ("is conducted", "are reviewed", "will be responsible for")
- Vague verb detection: flag statements starting with weak openers: "responsible for", "assists with", "helps with", "liaises with" (without a following active construction), "participates in" as the only verb
- Run-on detection: flag duties exceeding ~40 words or containing more than two main clauses
- Inline UI: flags appear as non-blocking warnings directly under the flagged duty row, not as a modal or a separate audit step — the advisor can dismiss or act on each one immediately

**Differentiators.**
- Socratic question reshaping: the Duties phase questions in `QUESTION_BANK` are currently generic. Reshape them to follow the guide's structure: first ask for Client Service Results (the purpose/output of the role), then Key Activities (what is done to achieve those results). This two-step framing produces better structured input and reduces the "what does this person do?" open-field problem.
- Verb suggestion: when a passive duty is flagged, offer a suggested active rewrite (heuristic, not LLM — a verb-mapping lookup for common patterns: "is conducted by" → "Conducts", "will be responsible for reviewing" → "Reviews")
- Classification-risk flag: if a duty uses terms that commonly indicate OG-group misalignment (e.g., "economic research" in an AS role, "legal interpretation" in an EC role), surface a soft warning citing the AS/EC disambiguation logic already in the system

**Anti-features.**
- Do not block submission on writing quality violations — these are non-blocking warnings only; the advisor must be able to proceed with an imperfect duty if they choose
- Do not run LLM-based rewriting of duties at this stage — the guide is explicit that the job description describes work assigned, not a stylistic interpretation; LLM rewrites risk altering meaning

**Complexity:** Medium. Three distinct sub-problems:

1. **Validation engine** (`duty_validator.py`): pure Python, no LLM. Regex + heuristic rules for passive voice, vague verb list, word count threshold. Returns a list of `DutyFlag(duty_index, rule_id, message, severity)`. Fast, deterministic, testable. Approximately 150 lines.
2. **Verb suggestion lookup**: a dictionary of 30-50 passive/weak patterns mapped to suggested active alternatives. Embedded as a constant in `duty_validator.py`.
3. **Frontend integration**: the `DutyEditor` component in `document.jsx` / `conversation.jsx` receives flags from the API (or runs client-side for instant feedback) and renders inline `.duty-warn` callouts. Decision: run validation client-side in JS for instant feedback — a small `dutyValidator.js` utility that mirrors the server-side rules. Call `POST /api/duties/validate` on commit for the authoritative record.
4. **Socratic question reshaping**: modify `QUESTION_BANK` entries for the Duties phase to add a "Client Service Results" prompt before "Key Activities". Low risk, additive change.

**Dependencies on existing system.**
- `getDutySuggestions(answers)` in `data.jsx` — duty suggestions already OG-keyed; validation is a separate layer on top
- Phase 15 STEPS array — a new step for "Client Service Results" can be inserted between WorkType and Duties phases without breaking existing flow logic
- The `prov__tag` pattern: validated/corrected duties carry the same "advisor-added" tag they always did; validation does not change provenance

---

### Feature 4: Risk Audit

**What it is in the domain.**
A "classification compliance audit" triggered explicitly by the advisor in the Review phase. It checks the draft JD against two source bodies:
- **CBA clauses**: restriction/scope/exclusion clauses per OG from the existing `data/agreements/` structure (already ingested in v1.0 for CA-01; the JSON files exist in `data/agreements/EC/`, `FB/`, etc.)
- **Federal Court ERR Principles**: the `ERR_Principles_drawn_from_Federal_Court.pdf` document, which is a structured list of binding principles organized by topic: Job content/Statement of duties, Right to grieve, Time limits, Conduct of grievance hearing, Deliberations and evaluation, Grievance report, Contesting a grievance decision

**Key ERR principles most relevant to JD writing (sourced directly from the document):**
- "A job description does not need to contain a detailed listing of all activities performed under a specific duty, nor should it necessarily list at length the manner in which those activities are accomplished." (FPSLREB: Hughes, Jarvis; FC: Currie)
- "Duties assigned to a position may be appropriately described in a generic work description. It is acceptable to use broad terms to subsume a number of functions and activities." (FPSLREB: Jaremy)
- "If a duty is not contained in a generic or a specific job description, it must be added in order to meet the requirements of the collective agreement for a complete and current Statement of Work." (FPSLREB: Cushnie)
- "Although the use of generic job descriptions can be an acceptable way for the employer to satisfy its obligation under the collective agreement, the job description needs to reflect the duties of the employees. It can fail to do so if the terms used do not accurately reflect the depth or scope of the grievor's work." (FPSLREB: Dervin)
- "Classification is not as simple as doing a 'word match'. It is necessary to read the words in context and look at the whole of the work involved." (FC: Bourdeau)
- "In a classification grievance, the Committee and Deputy Head's task is to accept the work description and determine its appropriate classification as it is drafted." (FC: Wilkinson III) — meaning a poorly drafted WD can be grieved on its face, not just on the underlying work
- "The grievance decision should logically flow from the analysis of factors and benchmarks as set out in the report." (FC: Lapointe II, Gilbert)

**Table stakes (how similar compliance tools present inline findings).**
Document compliance tools (legal review, regulatory audit) converge on a consistent pattern:
- **Inline highlighting per section**, not a flat list of all findings at the end — findings appear next to the content they concern
- **Severity-tiered callouts**: distinct visual treatment for high-risk vs. advisory findings. In this domain: "Grievance risk" (red/amber) vs. "Advisory" (blue)
- **Action buttons directly on each finding**: Accept (acknowledge, mark as reviewed), Manual Edit (jump to the relevant section in the conversation thread), Skip (dismiss with a reason). These three options map to what an advisor actually does: some findings require action, some are contextually acceptable, some are not applicable to this specific position
- **Audit summary** at the top: "N findings — X high risk, Y advisory" with a progress indicator showing how many have been addressed
- **Source citation on every finding**: "Citing: Cushnie (FPSLREB 166-34-37315) — collective agreement completeness requirement" — not just a rule name but the specific case or clause

**What makes Accept/Edit/Skip UX work well.**
Based on patterns from document review tools (contract analysis, regulatory compliance):
1. **Non-modal, inline** — each finding is a dismissible card anchored to the JD section it concerns, not a popup that breaks focus
2. **Accept is not "ignore"** — it marks the finding as "reviewed and accepted as-is" with a timestamp, creating an audit trail. This matters for classification integrity
3. **Edit navigates directly** — clicking Edit does not open a new view; it activates the amendment panel for that section (which already exists via the Phase 19 amendment UX) or jumps the conversation thread to the relevant step
4. **Skip requires a reason** — a short dropdown: "Not applicable to this position", "Addressed in organizational context", "Will be resolved before filing" — this gives the advisor defensibility if the JD is later grieved
5. **Completion gate** — the Review phase checklist already has checkboxes; adding "Risk audit complete" as a required checklist item (or "Risk audit dismissed N/N findings") makes the audit non-bypassable without at least acknowledging findings

**Anti-features.**
- Do not make the audit automatic on every save — it should be an explicit "Run audit" button. Automatic audits on every edit create noise and slow the workflow
- Do not require the audit to be completed before export — it is an advisory tool, not a hard gate. The export may include an audit log appendix if the audit was run
- Do not connect to live CA APIs or FPSLREB databases — all source material is already in `data/`; the audit is a static rules engine over ingested content

**Complexity:** High. Three sub-problems:

1. **Rules engine** (`audit_service.py`): for each JD section (org context, key activities, qualifications, classification), apply a set of rules drawn from CBA clause data and hardcoded ERR principle mappings. Returns `AuditFinding(section, severity, citation, message, suggestion)`. The CBA clause check requires loading the relevant OG's agreement JSON and checking whether key activities fall within scope. This is the hardest part — it requires semantic matching between duties and CA article scope, which is fuzzy. Recommendation: start with pattern-matching rules for the most common violations (orphan statements, scope violations, missing key duties) and avoid LLM for v3.0.
2. **Frontend audit panel**: new `AuditPanel` component in `document.jsx`. Renders findings grouped by section with Accept/Edit/Skip controls. Connects to new `POST /api/wd/{id}/audit` endpoint. The amendment panel (Phase 19) provides a reusable visual model — audit findings can reuse `.amend-panel` CSS patterns.
3. **Audit persistence**: findings and their Accept/Skip dispositions need to be stored in `audit_log` with `event='audit_finding'` and `event='audit_disposition'` rows. The existing `audit_log` table handles this without schema change; only the event type is new.

**Dependencies on existing system.**
- Requires `confirmed_og` and `og_level` to be set (classification gate must already be satisfied)
- Uses `data/agreements/` JSON content (CA-01 from v1.0 — the ingest pipelines are archived but the JSON files exist in `data/agreements/`)
- Amendment panel UX (Phase 19): the Edit action reuses the amendment panel's open/close mechanism
- Export (Phase 20): if audit was run, add an "Audit log" appendix to the DOCX export listing findings and dispositions

---

### Feature 5: Broader OG Classification

**What it is in the domain.**
v2.0 covers EC (9-element point-rating JES), IT, FI, AS, EX with hardcoded totals. v3.0 adds 12 new groups. All 12 have JES standard files in `data/Job_evaluation/`. The structural landscape is more varied than EC:

**EC (existing, 9 elements, point-rating):**
9 factors: Decision making, Leadership/operational management, Communication, Knowledge of specialized fields, Contextual knowledge, Research and analysis, Physical effort, Sensory effort, Working conditions. Point boundaries EC-01 (40-99) through EC-08 (750-1000).

**New groups — structural classification:**

Groups using **point-rating** (similar to EC, full scoring possible):
- **FS (Foreign Service)**: point-rating plan, 10 elements. Levels FS-01 through FS-04.
- **LP (Law Practitioner)**: point-rating plan with elements including Physical/Sensory Efforts and Psychological/Physical Work Environment. Five levels LP-01 through LP-05. Benchmark-driven.
- **MT (Meteorology)**: point-rating, uses "illustrative position descriptions" instead of benchmarks. Four factors with two elements each.
- **FB (Border Services)**: point-rating, 10 elements. A 2005 standard with a separate Application Guidelines file. Levels FB-01 through FB-07.
- **LC (Law Management)**: point-rating. Levels LC-01 through LC-02. Narrow group.
- **SW Social Work (SCW sub-group)**: point-rating, three factors. The SW group also contains a Chaplain (CHA) sub-group using level descriptions.

Groups using **level descriptions** (non-scoring; narrative factor-degree matching, no point total):
- **NU (Nursing)**: three factors (Professional Complexity and Responsibility, Responsibility for Management and Management Advisory Services, Impact) applied via level descriptions. Eight levels for HOS and CHN sub-groups. Medical Adjudicator (EMA) sub-group uses example work activities, two levels.
- **PS (Psychology)**: level descriptions, three factors (Technical Complexity, Professional Responsibility, Management Responsibility). Five levels PS-01 through PS-05.
- **NT (Nutrition and Dietetics)**: level descriptions, same three-factor structure as NU HOS/CHN. Eight levels NT-01 through NT-08. Near-identical structure to NU.
- **PO (Police Operations Support)**: level descriptions. Levels PO-01 through PO-03.
- **WP (Welfare Programs)**: level descriptions. WP-01 through WP-07.
- **ED (Education)**: mixed. Language Teaching (LAT) and Elementary/Secondary Teaching (EST) sub-groups use level descriptions; other sub-groups may use point-rating. The standard file requires a full read to determine the complete sub-group map.

**Key structural differences versus EC:**

1. **Point-rating vs. level descriptions**: EC, FS, LP, MT, FB, LC, SW-SCW all use point-rating — the JES scoring service can be extended with a new degree/points table per group (same pattern as `EC_JES_ELEMENTS`). NU, PS, NT, PO, WP, SW-CHA, ED sub-groups use level descriptions — the output is a level assignment, not a point total. The Socratic questions for these groups must target factor-degree matching, not point scoring. This is a fundamentally different rendering path in the UI.
2. **Sub-groups requiring disambiguation before scoring**: NU (HOS, CHN, EMA), SW (SCW, CHA), ED (LAT, EST, others). An advisor describing a Health Services position must be routed to the correct sub-group before factor application — analogous to the existing AS/EC disambiguation. The SH macro-group (NU, NT, PS, SW are all sub-standards of SH) adds a disambiguation layer.
3. **Factor count varies**: EC has 9 elements. LP has 7 elements including physical/sensory/work environment. MT has 4 factors times 2 elements each = 8 inputs. FB has 10 elements. The existing `KNOWN_JES_FACTORS` frozenset must become a per-group dict: `JES_FACTORS_BY_GROUP: dict[str, frozenset]`.
4. **Output for level-description groups**: `{"level_description_match": "NU-04", "factors": [{"name": "Professional Complexity", "degree": 3}], "jes_total_points": null, "method": "level_description"}`. The frontend `ClassBlock` already handles `jes_total_points == null` from the Phase 17 render-gate fix — this null path is already partially wired.

**Table stakes.**
- All 12 new groups wired into the Socratic question bank with group-specific work-type and scope questions
- For point-rating groups: full per-element scoring with degree vectors and point totals with level boundaries
- For level-description groups: factor-degree matching returning a level assignment (NU-03, PS-02, etc.) with factors listed and degrees noted
- Sub-group disambiguation where required (NU, SW, ED)
- `NON_EC_TOTALS` expanded to cover all 12 new groups' approximate totals where point-rating is used, and replaced with level-description metadata for others

**Differentiators.**
- SH macro-group disambiguation: NU, NT, PS, and SW are all sub-standards of SH. An advisor describing a Health Services position should be asked which SH sub-standard applies before classification proceeds.
- For level-description groups, surface the level-description text for the matched level alongside the factor-degree assignments, giving the advisor a narrative basis for the classification recommendation.

**Complexity:** High-but-mechanical. The work is high-volume but structurally repetitive:
- 5-6 new point-rating groups each need a `GROUP_JES_ELEMENTS` constant (degree/points dict) and point-boundary table — same pattern as `EC_JES_ELEMENTS`
- 6-7 level-description groups need factor/degree tables without point totals
- Sub-group logic for NU, SW, ED adds conditional branching in `jes_service.py`
- The `QUESTION_BANK` needs 12 new group-keyed entries or a new work-type signal to group mapping for health-services and legal-services clusters
- Biggest risk: the existing `jes_service.py` uses `instructor` + Ollama for EC JES scoring via LLM. For level-description groups, the LLM would be asked to match a narrative description to factor-degree descriptors — a different prompt pattern that needs validation before committing

**Dependencies on existing system.**
- `KNOWN_JES_FACTORS` frozenset (Phase 12) becomes `JES_FACTORS_BY_GROUP: dict[str, frozenset]`
- `EC_JES_ELEMENTS` and `EC_DEGREES` constants replicated per new point-rating group
- `NON_EC_TOTALS` dict (Phase 17) expanded for all 12 new groups
- `jes_service.py` `score_jes_v2()` must dispatch to the correct group's scoring method based on `confirmed_og`
- Frontend `ClassBlock` in `document.jsx` already handles null total; needs a new rendering branch for "level description method" that shows "Level: NU-04 (matched by factor degrees)" instead of a points bar

---

### Feature 6: Document Preview Page Extension

**What it is in the domain.**
The simulated white page in the right-hand preview pane clips content when the JD is long. CSS diagnosis from `v2/frontend/src/styles.css`:
- `.doc-scroll`: `flex: 1 1 auto; min-height: 0; overflow-y: auto` — correct for a scrollable flex child
- `.doc`: `width: 100%; max-width: 680px; padding: 52px 56px 60px` — no fixed height, content-driven — this is correct
- The bug is almost certainly that a parent container in the flex chain has `overflow: hidden` (confirmed: multiple ancestors have `overflow: hidden` in the stylesheet at lines 58 and 162) that clips the scroll container before it can scroll

**Table stakes.**
- The white paper card grows in height to contain all content at any document length — no content flows into the grey background
- Vertical scrolling within `.doc-scroll` works correctly at all document lengths
- The visual appearance (shadow, border, left accent bar from `.doc::before`) remains intact at any height
- The fix does not break the split-pane layout (conversation thread on left, document on right)

**Differentiators.**
- Sticky document header (`.doc__eyebrow` with the classification badge and export buttons) that stays visible while scrolling through long documents — useful for 12+ section JDs from the new OG groups
- The simulated page at 680px width matches the actual DOCX/PDF output width, giving the advisor a true WYSIWYG preview at any length

**Anti-features.**
- Do not introduce a fixed pixel height on `.doc` — this is the root cause of the current bug; height must be determined by content
- Do not paginate the preview into separate A4 pages — this is a digital editing tool, not a print preview; pagination adds complexity without UX value

**Complexity:** Low. This is a CSS and layout fix, not a feature build. The fix is one of:
1. Ensure the parent container chain does not have `overflow: hidden` on any element that wraps `.doc-scroll`
2. Verify `.doc-scroll` has explicit `flex: 1 1 auto; min-height: 0` with no competing `height` constraint from an ancestor
3. The `.doc` element may need `align-self: flex-start` to prevent flex-stretch from constraining its height

Estimate: under 20 lines of CSS change. Risk: regression in the split-pane layout — one test pass with a long JD is sufficient validation.

**Dependencies on existing system.**
- `v2/frontend/src/styles.css` — `.doc`, `.doc-scroll`, `.preview`, `.app` rules only
- No backend changes required
- Recommended build order: do this first — it immediately unblocks QA for all other v3.0 features that produce longer documents

---

## Cross-Feature Dependency Map

```
SJD Library
  writes og_confirmed, og_level (depends on Phase 16 OG Classification UX)
  adds sjd_number field to WorkDescription (affects export manifest)
  interacts with QUESTION_BANK STEPS (depends on Phase 15 STEPS array)

Accessible JD Template
  replaces wd.docx template binary (depends on Phase 20 export infrastructure)
  section mapping depends on Writing Guide section structure (coordinate with Feature 3)

Writing Guide Integration
  adds duty_validator.py service (no existing dependencies, purely additive)
  reshapes QUESTION_BANK Duties phase (depends on Phase 12 QUESTION_BANK)
  client-side dutyValidator.js mirrors server-side rules
  Socratic question for "Client Service Results" adds a new STEP (Phase 15 STEPS array)

Risk Audit
  requires confirmed_og (depends on Phase 16 classification gate)
  reads data/agreements/ JSON (CA-01 data from v1.0, files already present)
  reuses amendment panel UX (depends on Phase 19 amendment infrastructure)
  adds audit appendix to DOCX export (depends on Phase 20 export_service.py)

Broader OG Classification
  expands QUESTION_BANK (depends on Phase 12)
  expands JES_FACTORS_BY_GROUP (depends on Phase 17 JES scoring)
  expands NON_EC_TOTALS (depends on Phase 17)
  jes_service.py dispatch logic (depends on Phase 17 score_jes_v2)
  ClassBlock frontend rendering (depends on Phase 17 render-gate fix, already handles null total)

Preview Page Extension
  pure CSS fix, no cross-feature dependencies
  should be done first — unblocks QA for all other features that produce longer documents
```

## MVP Prioritization for v3.0

**Build first (foundations and quick wins):**
1. Preview Page Extension — CSS fix, zero risk, immediately improves QA for all other work
2. Accessible JD Template — self-contained, replaces Phase 20 template, clearly scoped

**Build second (core value adds):**
3. Writing Guide Integration — medium complexity, high user value, additive to existing duty entry UX
4. SJD Library — medium complexity, directly addresses DND mandatory SJD policy, depends on Phase 15/16 being stable (they are)

**Build last (high complexity, high value):**
5. Risk Audit — complex rules engine; benefits from Writing Guide validation engine being in place first
6. Broader OG Classification — high volume of mechanical data work; needs careful JES standard data extraction per group

## Open Questions

- **Writing Guide**: the Effort and Working Conditions sections of the accessible template require inputs not currently captured in the Socratic conversation. Are these sections to be advisor-completed placeholders in v3.0, or should new Socratic questions be added? Recommend placeholders in v3.0, new questions in v4.0.
- **Broader OG — ED group**: the Education group has multiple sub-groups (Language Teaching, Elementary/Secondary Teaching confirmed, others unclear). The standard file needs a complete read before coding the scoring dispatch.
- **Risk Audit — scope matching threshold**: the CA clause check is inherently fuzzy. How strict should scope/exclusion matching be? A false positive that flags a valid duty as "out of scope" is worse than a false negative in this domain. Recommend a conservative threshold — only flag explicit exclusion-clause violations, not soft scope ambiguity.
- **SJD Library — data volume**: `SJD Examples.txt` has 9 entries. Is there a larger DND SJD dataset available to seed from? The browse experience will be thin at launch if the library is small; the "start from SJD" flow remains valuable regardless.
- **Broader OG — LLM for level-description scoring**: the existing EC JES scoring uses instructor + Ollama. For level-description groups (NU, PS, NT, WP, PO), the LLM must match narrative input to factor-degree descriptors rather than assigning point values. This is a different prompt pattern and needs a prototype/validation before committing it to the scoring service architecture.
