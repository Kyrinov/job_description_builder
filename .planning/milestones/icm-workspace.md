# Milestone vICM.0: ICM Workspace

**Goal:** Add `jd-builder` as a workspace in the ICM repo (`/home/charles/ICM/workspaces/jd-builder/`) that models the full JD creation workflow as a staged AI pipeline -- from plain-language role description to a legally defensible, fully traced export.

**Why:** The JD builder has a natural multi-stage content pipeline identical in shape to `script-to-animation` and `course-deck-production`: unstructured input → classification → composition → review → export. Capturing it in ICM format gives Claude a structured context layer for assisting with any JD build session, independent of the web app's wizard UX.

**Phases:** 30–33  
**Output location:** `/home/charles/ICM/workspaces/jd-builder/`

---

## Requirements

| ID | Requirement |
|----|-------------|
| ICM-01 | `workspaces/jd-builder/CLAUDE.md` exists with folder map, triggers (`setup`, `status`), and routing table |
| ICM-02 | `workspaces/jd-builder/CONTEXT.md` maps all 5 stage types to their CONTEXT.md files |
| ICM-03 | `policy-vault/` contains TBS classification policy, JD writing guide rules, and JES standards in Layer 3 format (under 200 lines each) |
| ICM-04 | `shared/og-definitions.md` and `shared/qualification-standards.md` authored from `OG_DEFINITIONS` and `QUAL_STANDARDS` app constants |
| ICM-05 | `stages/01-intake/CONTEXT.md` has Inputs/Process/Outputs tables; Socratic questions reference file exists |
| ICM-06 | `stages/02-classification/CONTEXT.md` has Inputs/Process/Outputs tables; OG classifier rules and JES scoring guide exist |
| ICM-07 | `stages/03-composition/CONTEXT.md` has Inputs/Process/Outputs tables; duty writing rules reference file matches the 4 rules in `duty_validator.py` |
| ICM-08 | `stages/04-review/CONTEXT.md` has Inputs/Process/Outputs tables; seven-elements and compliance-rules reference files exist |
| ICM-09 | `stages/05-export/CONTEXT.md` has Inputs/Process/Outputs tables; export-formats reference file documents DOCX/PDF/JSON/CSV |
| ICM-10 | `skills/jd-builder-api/SKILL.md` documents all key API endpoints with request/response shapes |
| ICM-11 | ICM root `CLAUDE.md` routing table updated; ICM `README.md` workspaces list updated |
| ICM-12 | `grep -r "{{" workspaces/jd-builder/` returns zero hits outside `setup/questionnaire.md` and `shared/department-profile.md` |
| ICM-13 | All stage CONTEXT.md files are under 80 lines; all reference files are under 200 lines |

---

## Phase 30: Workspace Scaffold + Policy Vault

**Goal:** The workspace folder exists with a working CLAUDE.md, CONTEXT.md, setup questionnaire, and policy-vault directory containing the three core TBS reference files (classification policy, JD writing guide, JES standards). Running `setup` in Claude Code navigates correctly.

**Depends on:** Nothing -- creates the ICM workspace from scratch in `/home/charles/ICM/`

**Requirements:** ICM-01, ICM-02, ICM-03

**Success Criteria:**
1. `workspaces/jd-builder/CLAUDE.md` loads cleanly: folder map is accurate, `setup` trigger defined, routing table has all 5 stages
2. `workspaces/jd-builder/CONTEXT.md` is under 30 lines; maps each task type to the correct stage CONTEXT.md path
3. `setup/questionnaire.md` asks department name, primary OG groups used, DRF integration flag (yes/no), advisor name -- all as flat numbered questions with sensible defaults
4. `policy-vault/tbs-classification-policy.md` contains the definition of "work description", the AS/EC disambiguation rule, and the requirement for every duty to trace to an authoritative source -- all under 200 lines
5. `policy-vault/jd-writing-guide.md` contains the 4 structural duty rules (active-voice opener, 8-25 words, no passive, no duplicate) plus the 7 Part 2 element names -- under 200 lines
6. `policy-vault/jes-standards.md` contains the 9 EC JES factor names with degree descriptions, plus a table mapping each non-EC OG to its scoring method (point-rating / level-description / approximate-total) -- under 200 lines

**Plans:** TBD

---

## Phase 31: Shared Reference Extraction

**Goal:** `shared/` contains three files extracted from the app's authoritative constants: OG definitions for all 16 groups, OG-keyed qualification standards, and a blank department profile template. These are Layer 3 reference files -- stable across every JD build run.

**Depends on:** Phase 30 (workspace structure exists)

**Requirements:** ICM-04

**Success Criteria:**
1. `shared/og-definitions.md` lists all 16 OG groups with: code, full name, TBS inclusions excerpt, TBS exclusions excerpt -- content matches `OG_DEFINITIONS` constant in `v2/backend/app/services/constants.py`
2. `shared/qualification-standards.md` lists the Education and Experience default text for each OG group keyed by OG code -- content matches `QUAL_STANDARDS` constant
3. `shared/department-profile.md` contains `{{DEPARTMENT_NAME}}`, `{{DRF_INTEGRATION}}`, and `{{ADVISOR_NAME}}` placeholders with instructions for the setup trigger to fill them; file includes a note that this is the only file that should be edited during setup
4. No OG definition or qualification standard text appears in more than one file (Pattern 5: Canonical Sources)

**Plans:** TBD

---

## Phase 32: Stage CONTEXT Files

**Goal:** All 5 stage folders have CONTEXT.md files that follow the ICM Inputs/Process/Outputs contract. Each stage's reference files exist and are populated with the domain knowledge agents need to execute that stage.

**Depends on:** Phase 31 (shared reference files exist to be referenced in stage Inputs tables)

**Requirements:** ICM-05, ICM-06, ICM-07, ICM-08, ICM-09

**Success Criteria:**
1. `stages/01-intake/CONTEXT.md`: Process section has at minimum 4 steps (ask Socratic questions, collect org context, collect supervisory scope, save intake profile); references `socratic-questions.md` which lists the 4 QUESTION_BANK work-type questions with all 14 answer options and their OG signal mappings
2. `stages/02-classification/CONTEXT.md`: Inputs table includes the intake output and `shared/og-definitions.md`; Process section covers signal tally → top-3 candidates → advisor confirmation → JES scoring; Checkpoint defined after OG candidates are presented; `jes-scoring-guide.md` explains EC per-factor vs. non-EC approximate-total paths
3. `stages/03-composition/CONTEXT.md`: Process section covers duty drafting, writing-guide validation, optional SJD pre-fill, qualification editing; Audit section checks all 4 structural duty rules; `duty-writing-rules.md` matches the exact rules in `duty_validator.py` (active-voice, 8-25 word count, no passive, no duplicate)
4. `stages/04-review/CONTEXT.md`: Inputs table references all prior stage outputs; `seven-elements.md` lists the 7 Part 2 element names with definitions; `compliance-rules.md` summarizes the two-signal CBA matching rule and Federal Court ERR principles; Checkpoint before export approval
5. `stages/05-export/CONTEXT.md`: Process section lists DOCX (Accessible Template), poster DOCX, PDF (ARM64 gate), JSON (7-element analytics), CSV; `export-formats.md` documents the provenance manifest structure
6. Every CONTEXT.md is under 80 lines; every reference file is under 200 lines; output/.gitkeep exists in every stage

**Plans:** TBD

---

## Phase 33: Skills + Integration + Validation

**Goal:** The `jd-builder-api` skill documents the backend as a callable tool; the ICM root CLAUDE.md and README.md reference the new workspace; no placeholder leakage exists outside setup files; a dry-run `status` check confirms all 5 stages are PENDING (empty output folders, .gitkeep present).

**Depends on:** Phase 32 (all stage files exist)

**Requirements:** ICM-10, ICM-11, ICM-12, ICM-13

**Success Criteria:**
1. `skills/jd-builder-api/SKILL.md` documents these endpoints with request/response shapes: `POST /api/wd`, `PATCH /api/wd/{id}`, `POST /api/og/classify`, `POST /api/jes/score`, `POST /api/wd/{id}/validate-duties`, `POST /api/wd/{id}/audit`, `POST /api/wd/{id}/export/docx|poster|json|csv`
2. ICM root `CLAUDE.md` Routing table has a `jd-builder` row pointing to `workspaces/jd-builder/CLAUDE.md`
3. ICM `README.md` workspaces list includes `jd-builder` with a one-line description
4. `grep -r "{{" /home/charles/ICM/workspaces/jd-builder/` returns only hits in `setup/questionnaire.md` and `shared/department-profile.md`
5. Running `status` in the jd-builder workspace: agent scans all 5 `stages/*/output/` folders, all show PENDING (only `.gitkeep`), ASCII pipeline renders correctly
6. All CONTEXT.md files confirmed under 80 lines; all reference and shared files confirmed under 200 lines

**Plans:** TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 30. Workspace Scaffold + Policy Vault | 0/? | Not started | -- |
| 31. Shared Reference Extraction | 0/? | Not started | -- |
| 32. Stage CONTEXT Files | 0/? | Not started | -- |
| 33. Skills + Integration + Validation | 0/? | Not started | -- |
