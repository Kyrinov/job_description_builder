# Phase 21 Amendment Research: Question Bank Restructure + JES Level Determination

**Researched:** 2026-06-11
**Domain:** Socratic question routing architecture + JES level-description parsing
**Confidence:** HIGH (codebase fully read; JES files fully read)

---

## Summary

Two UAT failures require architectural fixes in Phase 21.

**Fix A — Question Bank Restructure:** The 4 original `work_type` questions (work_output_type, work_audience, knowledge_specialization, policy_interpretation) only emit signals for EC, AS, IT, and FI. They fire unconditionally for every user. A nurse entering "Health and Social Services" in the sector-gate is forced through all 4 questions, none of which match their work. The fix is to gate those 4 questions behind `sector_gate = other_sector` and add a `programme_admin_cluster` question for the currently unhandled 5th sector. The architecture is fully viable inside the existing `isStepVisible` predicate system with a one-line addition per question.

**Fix B — JES Level Determination:** `OgLevelPicker` renders bare numbered buttons. For level-description OG groups (NU, PS, NT, PO, WP, SW-CHA, ED-LAT, ED-EST), a 2-3 question mini-interview can be derived directly from the JES factor texts and benchmark position descriptions. For point-rated groups already handled by Plan 04 scoring (SW-SCW, WP via point-rating, LC, LP, FB, FS, MT) and for EC (LLM-scored), the level is already computed and should be surfaced as a result with an advisory label, not asked again. The recommended frontend approach is Option A: a new `og_level_questions` step inserted before `og_level` for level-description groups only, with backend endpoint `POST /api/jes/level-suggest` returning a recommended level that pre-selects the existing picker.

---

## Question Bank Architecture Fix

### Root Cause

The `isStepVisible` gate in `data.jsx` (lines 424-439) correctly hides cluster questions that don't match the selected sector. But the 4 original `work_type` questions have no gate at all — they always return `true` in the `default` branch. A user selecting `pa_sh_sector` sees all 4 questions with only EC/AS/IT/FI options before reaching the sector-gate.

The sector-gate (`qb_sector_gate`) is currently at phase 2 in STEPS (line 518), after all 4 work_type questions at phase 1. That ordering is the architectural defect.

### Recommended Approach

**Move `qb_sector_gate` to fire first in the classification phase — or more precisely, gate the 4 legacy questions behind `other_sector`.**

Two implementation strategies:

**Strategy 1 — STEPS reorder (invasive):** Move the `qb_sector_gate` entry before the 4 work_type entries in the STEPS array. Requires auditing `FLASH`, `answeredSteps`, and any step-index-based logic in app.jsx. Risk: step index shifts break existing saved answers.

**Strategy 2 — Gate legacy questions in isStepVisible (non-invasive, recommended):** Leave STEPS order unchanged. Add 4 new cases to `isStepVisible` so the legacy work_type questions only show when `sector === 'other_sector'`. Add a missing 5th cluster question for `programme_admin_sector`. This is the minimal-risk change because:
- No STEPS array index changes
- No app.jsx `cfgOverride` changes
- `accumulateSignals` already includes all `qb_*` step IDs
- The predicate is pure and tested; adding cases is straightforward

**The one missing piece:** There is currently NO cluster question for `programme_admin_sector` (PO/WP). That sector option appears in the sector-gate but has no downstream disambiguation. This must be created as part of this fix.

### Changes to STEPS Structure

**No reordering needed.** Changes are confined to:

1. `data.jsx` — `isStepVisible` function: add 4 new cases:
   ```javascript
   case 'qb_work_output_type':
   case 'qb_work_audience':
   case 'qb_knowledge_specialization':
   case 'qb_policy_interpretation':
     return sector === 'other_sector';
   ```
   This gates the legacy EC/AS/IT/FI questions to only show for the "other" path.

2. `data.jsx` — `accumulateSignals` `qbStepIds` array: add `'qb_programme_admin_cluster'` to the list.

3. `data.jsx` — STEPS array: add new `qb_programme_admin_cluster` step entry immediately after `qb_education_cluster` (before `noc_confirm`), with `isStepVisible` gate on `programme_admin_sector`.

4. `data.jsx` — `isStepVisible`: add case for `'qb_programme_admin_cluster'` returning `sector === 'programme_admin_sector'`.

5. `constants.py` — QUESTION_BANK: add corresponding `qb_programme_admin_cluster` entry.

6. `app.jsx` — `FLASH` map: the 4 legacy step IDs already appear as `qb_work_output_type` etc. The new cluster step ID needs to be added.

### Visibility Logic After Fix

```
qb_sector_gate          → always visible (no gate)
qb_work_output_type     → visible only if sector === 'other_sector'
qb_work_audience        → visible only if sector === 'other_sector'
qb_knowledge_spec.      → visible only if sector === 'other_sector'
qb_policy_interp.       → visible only if sector === 'other_sector'
qb_health_social_cluster → visible only if sector === 'pa_sh_sector'
qb_legal_cluster         → visible only if sector === 'legal_sector'
qb_technical_cluster     → visible only if sector === 'technical_scientific_sector'
qb_education_cluster     → visible only if sector === 'education_sector'
qb_programme_admin_cluster → visible only if sector === 'programme_admin_sector'  ← NEW
```

Result: every user answers exactly 2 questions in phase 1 (sector_gate + one cluster), not 4+ irrelevant ones. EC/AS/IT/FI users answer the sector_gate ("other_sector") + 4 legacy questions = 5 total, which is the existing behaviour for them.

### New Sector-Specific Questions: Draft Options

#### `qb_programme_admin_cluster` (NEW — Programme and Administrative Operations)

**Question:** "What is the primary focus of the programme or administrative operations work?"

**Helper:** "Consider whether the role is primarily operational communications and police support, or broader programme delivery and social services administration."

**Options:**

| id | label | og_candidates |
|----|-------|---------------|
| `police_telecom` | "Operating telecommunications systems or monitoring intercepts to support police operations" | `["PO"]` |
| `welfare_program_delivery` | "Delivering income support, benefits eligibility decisions, or welfare case management" | `["WP"]` |

**Note on WP overlap:** WP also appears in `pa_sh_sector` / `welfare_programs` in `qb_health_social_cluster`. This is intentional — welfare case workers with a social work identity enter via health/social; welfare programme administrators enter via programme/admin. The signal tally will still surface WP as dominant from either path. The duplicate routing is acceptable because `accumulateSignals` just tallies — it does not deduplicate by path.

---

## JES Level Criteria by Group

### Scope Boundary First (Critical)

Before documenting level criteria, establish which groups need questions and which are already resolved:

**Already resolved — do NOT ask level questions:**

| Group | Why resolved |
|-------|-------------|
| EC | LLM-scored JES → level returned by `/api/jes/score` |
| FI, IT, AS | `NON_EC_TOTALS` point-to-level mapping via Plan 04 |
| SW-SCW | Point-rated (Knowledge 300 pts + Professional Responsibility 400 pts + Administrative Responsibility 300 pts = 1000 pts); level boundaries 200-300/301-450/451-600/601-750/751-900 |
| WP | Point-rated (Knowledge 350 pts + Problem Solving 350 pts + Contacts 150 pts + Supervision 150 pts = 1000 pts); level boundaries 170-290/291-400/401-510/511-620/621-730/731-840/841-950 |
| LC, LP | Point-rated (LC JES); level computed from factor totals |
| FB, FS, MT | Point-rated; level computed from factor totals |

**Need Socratic level questions (level-description groups):**

| Group | Sub-group | Levels | Method |
|-------|-----------|--------|--------|
| NU | HOS (Hospital Nursing) | 1-8 | 3-factor level descriptions |
| NU | CHN (Community Health Nursing) | 1-8 | 3-factor level descriptions |
| NU | EMA (Medical Adjudicator) | 1-2 | Level descriptions only |
| PS | (Psychology) | 1-5 | 3-factor (Technical Complexity, Professional Responsibility, Management Responsibility) |
| NT | ADV (Nutritional Advisory) | 1-3 | Level descriptions |
| NT | DIT (Dietitian) | 1-4 | Level descriptions |
| PO | TCO (Telecommunications Operations) | 1-4 | Level progression chart (4 factors) |
| SW | CHA (Chaplain) | 1-3 | Level descriptions |
| ED | LAT (Language Teaching) | 1-3 | Level descriptions |
| ED | EST (Elementary/Secondary Teaching) | 1-4 | Level descriptions |

---

### NU — Nursing (HOS and CHN Sub-groups)

**Evaluation method:** 3 factors: Professional Complexity and Responsibility (PC), Responsibility for Management and Management Advisory Services (RM), Impact (I). Level = degree held by at least 2 of 3 factors.

**Key discriminating dimension per level (from benchmark summary):**

| Level | PC | RM | I | Typical role |
|-------|----|----|---|-------------|
| 1 | N/A | N/A | N/A | Developmental — under guidance of senior nurse |
| 2 | D2 | D2 | D2 | Staff Nurse: assigned patient load, follows procedures |
| 3 | D3 | D2-3 | D3 | Assistant Head Nurse / Community Health Nurse: unit or community scope, adapts interventions |
| 4 | D4 | D4 | D4 | Head Nurse / Nurse-in-Charge: 24-hr unit management, supervises staff, controls budget |
| 5 | D5 | D4-5 | D5 | In-Service Educator / Coordinator / Manager Health Care: group-of-units scope, designs education programs |
| 6 | D6 | D6 | D6 | Assistant Director / Zone Nursing Officer: multi-unit or zone, establishes standards, full HR/budget authority |
| 7 | D7 | D7 | D7 | Regional Nursing Officer: regional program coordination, policy recommendations |
| 8 | D8 | D8 | D8 | National Nursing Consultant: national policy, international impact |

**Discriminating questions (2-3 for Socratic level suggestion):**

**Q1 — Scope of nursing responsibility:**
- "Provides direct nursing care to an assigned number of patients" → Level 2
- "Plans and delivers care for a unit or community, adapts interventions to client needs" → Level 3
- "Manages delivery of nursing services in a unit or community health facility on a 24-hour basis" → Level 4-5
- "Coordinates or evaluates nursing programs across multiple units, a hospital, or a zone" → Level 6-7
- "Develops national nursing policies, standards, or advises on programs available to Canadians" → Level 8

**Q2 — Guidance received / autonomy:**
- "Receives detailed guidance from a senior nurse; decisions reviewed while in progress" → Level 1-2
- "Receives guidance on program policy and clinical issues; resolves most issues independently" → Level 3-4
- "Receives direction on institutional or administrative policy objectives only; independently manages operations" → Level 5-6
- "Receives direction on government policy and program objectives only" → Level 7-8

**Q3 — People management scope:**
- "No supervisory responsibility; guides auxiliary staff only" → Level 2-3
- "Supervises and appraises nursing staff in a unit; controls unit budget" → Level 4
- "Manages staff across multiple units; allocates resources; takes disciplinary action" → Level 5-6
- "Provides functional direction to regional or zone nursing officers; advises on HR requirements for the region or nation" → Level 7-8

**NU-EMA special case:** Only 2 levels.
- EMA-1: Assesses medical information for eligibility decisions (routine cases)
- EMA-2: Provides expert/supervisory guidance on complex cases at regional/national level

Single question suffices: "Does this role primarily assess individual applicant files for eligibility, or does it provide expert advice and direction on complex adjudication cases?"

---

### PS — Psychology

**Evaluation method:** 3 factors: Technical Complexity (TC), Professional Responsibility (PR), Management Responsibility (MR). Level = degree held by at least 2 of 3. Note: degree definitions provided only for degrees 2 and 4; degrees 1, 3, 5 are interpolated from benchmarks.

| Level | TC | PR | MR | Typical role |
|-------|----|----|-----|-------------|
| 1 | D1 | D1 | D1 | Junior Psychologist: established techniques, supervised, no staff management |
| 2 | D2 | D2 | D1 | Staff Psychologist: modifies/adapts techniques, independently interprets findings, advises on treatment |
| 3 | D2-3 | D2-3 | D2 | Section Head: manages small team, directs applied research, provides test development services |
| 4 | D4 | D4 | D4 | Head Psychologist: originates new methods, final decision authority, independent of professional guidance, manages program |
| 5 | D4-5 | D4-5 | D4-5 | Assistant Director: directs multi-functional psychology program, senior management consultation |

**Discriminating questions:**

**Q1 — Independence of professional judgment:**
- "Work is reviewed by a supervisor who has final responsibility for validity of conclusions" → Level 1-2
- "Completed work is reviewed for soundness of professional judgment but this position determines its own approach" → Level 2-3
- "Professionally independent; guidance restricted to policy matters; assumes final responsibility for all decisions and recommendations" → Level 4-5

**Q2 — Method development vs. application:**
- "Applies established psychodiagnostic methods and techniques with some adaptation" → Level 1
- "Modifies and adapts established methods; develops new techniques for specific clinical problems" → Level 2-3
- "Originates new approaches and complex methodologies; develops procedures and studies for changing program requirements" → Level 4-5

**Q3 — Staff and program management:**
- "No continuous staff supervision; may occasionally guide a research assistant or intern" → Level 1-2
- "Supervises technical and junior professional staff; recommends project initiation" → Level 3
- "Plans, organizes, and directs a multi-functional psychology program; manages budget and professional staff" → Level 4-5

---

### NT — Nutrition and Dietetics

NT has three sub-groups: Advisory (ADV, 3 levels), Dietitian (DIT, 4 levels), Home Economist (HME, 4 levels). The og_confirm sub-group selection step already determines which sub-group applies.

**ADV (Nutritional Advisory):**
| Level | Key feature |
|-------|-------------|
| 1 | Zone-level advisory (limited geographic scope); or advises professionals in nutrition field |
| 2 | Regional-level advisory; or plans and conducts nutritional improvement programs nationally |
| 3 | National/headquarters advisory; consults with provincial governments and international organizations |

**Single discriminating question for ADV:**
"What is the geographic or program scope of the nutrition advisory work?"
- "Provides nutrition advice within a defined zone or locality" → Level 1
- "Coordinates nutrition programs or provides advisory services across a region" → Level 2
- "Advises headquarters, regional and zone staff nationally; consults with provincial governments or international organizations" → Level 3

**DIT (Dietitian):**
| Level | Key feature |
|-------|-------------|
| 1 | Plans therapeutic diets or supervises food service for a ward/small facility; under supervision |
| 2 | Manages dietary service of one facility or supervises a designated function in a larger hospital |
| 3 | Manages dietary service for a federal hospital (meals for patients and staff) |
| 4 | Manages dietary service for a large federal hospital (large patient and staff population) |

**Single discriminating question for DIT:**
"What is the scope of the dietary service management responsibility?"
- "Plans therapeutic diets or supervises food service for a veterans health centre or a group of wards" → Level 1-2
- "Manages the complete dietary service for a federal hospital including meals for patients and staff" → Level 3-4 (follow-up: "large population" → Level 4)

**HME (Home Economist):**
| Level | Key feature |
|-------|-------------|
| 1 | Selects, tests and modifies recipes; writes food materials; under supervision |
| 2 | Conducts projects independently; experimental design and sensory evaluation |
| 3 | Supervises experimental/informational projects; supervises professional staff |
| 4 | Plans, directs and coordinates a program for agricultural/seafood market development |

---

### PO — Police Operations Support (TCO Sub-group)

**Evaluation method:** Level progression chart (cumulative). Four levels.

| Level | Key discriminator |
|-------|------------------|
| 1 | Trainee or close supervision; basic knowledge of telecom equipment and protocols |
| 2 | Autonomous under general supervision; full operation of telecom and police information systems; may include training delivery |
| 3 | Independent with little/no technical guidance; develops/maintains training programs or national policy/standards; may supervise day-to-day operations |
| 4 | Independent within established national management framework; manages through subordinate supervisors; budget and contingency planning responsibility |

**Note:** PO also has an IMA (Intercept Monitoring and Analysis) sub-group. Research focused on TCO as it is the broadest and most common.

**Discriminating questions for PO:**

**Q1 — Supervision and autonomy:**
- "Works as a trainee or under close technical supervision" → Level 1
- "Operates systems autonomously under general supervision; minimal coaching role" → Level 2
- "Works independently with little technical guidance; may supervise day-to-day operations" → Level 3
- "Manages operations through subordinate supervisors; holds budget and strategic planning authority" → Level 4

**Q2 — Policy and program scope:**
- "Operates communications equipment and responds to public requests; routine transactions" → Level 1-2
- "Develops or maintains training programs; analyzes and provides expert advice on national policies" → Level 3
- "Initiates joint activities with partner organizations; accountable for organizational-level operations" → Level 4

---

### SW-CHA — Chaplain Sub-group

**Evaluation method:** Level descriptions (3 levels).

| Level | Key feature |
|-------|-------------|
| 1 | Provides pastoral counselling to hospital patients; advises patients' families |
| 2 | Provides or coordinates pastoral counselling to inmates and their families; implements religious rehabilitation programs; communicates with community |
| 3 | Regional coordination of spiritual programs; consultation, administration, and planning services; training needs assessment and facilitation for region |

**Single discriminating question for SW-CHA:**
"What is the primary scope of the chaplaincy work?"
- "Provides pastoral counselling and support to patients or inmates in a single institution" → Level 1-2 (follow-up: "inmate rehabilitation and community communication" → Level 2)
- "Coordinates spiritual programs and chaplaincy services across a region; provides consultation and training" → Level 3

---

### ED-LAT — Language Teaching

**Evaluation method:** Level descriptions (3 levels).

| Level | Key feature |
|-------|-------------|
| 1 | Teacher: teaches a second language; develops lesson plans; tests students for proficiency |
| 2 | Senior Teacher: fosters development of other teachers; reviews classroom work; assigns teachers to classes |
| 3 | Principal: directs, evaluates and guides the work of senior teachers and teachers; allocates space and equipment; manages school |

**Discriminating question for ED-LAT:**
"What is the primary role in the language teaching program?"
- "Teaches a language directly to students; develops lesson plans and tests proficiency" → Level 1
- "Reviews and mentors other language teachers; advises on course content and methodology" → Level 2
- "Directs the school; evaluates and guides senior teachers; allocates facilities and resources" → Level 3

---

### ED-EST — Elementary and Secondary Teaching

**Evaluation method:** Level descriptions (4 levels).

| Level | Key feature |
|-------|-------------|
| 1 | Teacher or Equivalent: teaches subjects or counsels students; under general supervision |
| 2 | Department Head: plans, implements and supervises teaching of a subject; advises teachers on methodology |
| 3 | Assistant Principal: assists principal; allocates resources; disciplines students |
| 4 | Principal: administers academic program; supervises classroom instruction; evaluates program |

**Discriminating question for ED-EST:**
"What is the primary role in the school or educational program?"
- "Teaches academic, technical, vocational, or adult education subjects; or counsels students" → Level 1
- "Plans and supervises teaching of a particular subject or area; advises teachers on methodology and materials" → Level 2
- "Assists in school administration; allocates resources; supports the principal" → Level 3
- "Administers the full school program; supervises instruction; evaluates curriculum and student achievement" → Level 4

---

## Data Structures

### JES_LEVEL_CRITERIA Structure

The backend needs a new constant `JES_LEVEL_CRITERIA` in `constants.py`, keyed by `og_code` or sub-group identifier, containing the questions and their answer-to-level mappings.

```python
JES_LEVEL_CRITERIA: dict[str, dict] = {
    "NU-HOS": {
        "method": "level_description",
        "questions": [
            {
                "id": "nu_scope",
                "question": "What best describes the scope of the nursing responsibility?",
                "options": [
                    {"id": "direct_care_assigned", "label": "Provides direct nursing care to an assigned number of patients", "level_hint": [2]},
                    {"id": "unit_or_community", "label": "Plans and delivers care for a unit or community, adapting interventions to client needs", "level_hint": [3]},
                    {"id": "unit_mgmt_24hr", "label": "Manages nursing services in a unit or facility on a 24-hour basis", "level_hint": [4, 5]},
                    {"id": "multi_unit_zone", "label": "Coordinates or evaluates nursing programs across multiple units, a hospital, or a zone", "level_hint": [6, 7]},
                    {"id": "national_policy", "label": "Develops national nursing policies or advises on programs available to Canadians", "level_hint": [8]},
                ],
            },
            {
                "id": "nu_autonomy",
                "question": "What guidance does this person receive?",
                "options": [
                    {"id": "detailed_guidance", "label": "Detailed guidance from a senior nurse; decisions reviewed while in progress", "level_hint": [1, 2]},
                    {"id": "policy_clinical", "label": "Guidance on program policy and clinical issues; resolves most issues independently", "level_hint": [3, 4]},
                    {"id": "admin_objectives", "label": "Direction on institutional or administrative policy objectives only; independently manages operations", "level_hint": [5, 6]},
                    {"id": "govt_objectives", "label": "Direction on government policy and program objectives only", "level_hint": [7, 8]},
                ],
            },
        ],
        "level_resolution": "majority_hint",   # level where >=2 questions agree
        "fallback": "pick_list",               # fall back to bare picker if no agreement
    },
    "NU-CHN": { ... },  # same structure, same questions apply
    "NU-EMA": {
        "method": "level_description",
        "questions": [
            {
                "id": "ema_scope",
                "question": "What best describes the role?",
                "options": [
                    {"id": "individual_adjudication", "label": "Assesses individual applicant files to determine medical eligibility", "level_hint": [1]},
                    {"id": "expert_direction", "label": "Provides expert advice and functional direction on complex adjudication cases at regional or national level", "level_hint": [2]},
                ],
            },
        ],
        "level_resolution": "direct",
    },
    "PS": { ... },
    "NT-ADV": { ... },
    "NT-DIT": { ... },
    "NT-HME": { ... },
    "PO-TCO": { ... },
    "SW-CHA": { ... },
    "ED-LAT": { ... },
    "ED-EST": { ... },
}
```

**Key design decisions:**
- `method: "level_description"` distinguishes from point-rated groups (which use `method: "point_rating"`)
- `level_hint` is a list because single-question options often span 2 levels; the endpoint resolves by intersection across multiple questions
- `level_resolution: "majority_hint"` means: collect all `level_hint` lists from answered questions; return the level that appears in the most lists; on tie, return the lower level (conservative)
- `fallback: "pick_list"` means: if resolution is ambiguous (no level in majority), return `null` and the frontend shows the bare picker

### Backend Endpoint

**`POST /api/jes/level-suggest`**

Request body:
```json
{
  "og_code": "NU",
  "sub_group": "HOS",
  "answers": {
    "nu_scope": "unit_mgmt_24hr",
    "nu_autonomy": "policy_clinical"
  }
}
```

Response:
```json
{
  "suggested_level": 4,
  "confidence": "high",       // "high" = all questions agree; "medium" = majority; "low" = only 1 question matched
  "level_range": [4, 5],     // the hint range from the strongest-signal answer
  "rationale": "Your description of 24-hour unit management with policy-level guidance suggests Level 4 (Head Nurse or Nurse-in-Charge equivalent)."
}
```

If `suggested_level` is `null`, the frontend falls back to the bare OgLevelPicker without pre-selection.

**The endpoint does NOT need to be async or call an LLM.** It is pure lookup logic in Python against `JES_LEVEL_CRITERIA`. It can be implemented as a synchronous FastAPI route.

---

## Frontend Flow

### Recommended: Option A — `og_level_questions` step before `og_level`

**Why Option A over Option B:**
- Preserves the existing `og_level` step, which already has PATCH persistence, cfgOverride, and badge logic
- The advisor can always override the suggestion in the existing picker
- Backend is stateless (no new model, no session state)
- Testing is straightforward: unit-test the endpoint, integration-test the pre-selection

**Implementation:**

1. Add new STEPS entry `og_level_questions` of type `og_level_questions`, inserted immediately before the `og_level` entry (phase 2):
   ```javascript
   { id: 'og_level_questions', phase: 2, icon: I.ladder,
     q: 'A few quick questions to suggest the right level.',
     helper: 'Answer based on the position as described. You can override the suggestion on the next screen.',
     input: { type: 'og_level_questions', questions: [] },
     apply: (r, a) => ({ og_level_questions: a }),
     transcript: a => a ? 'Answered' : 'Pending' }
   ```

2. `isStepVisible` gate for `og_level_questions`: only show when `confirmed_og.og_code` is in the set of level-description groups AND sub_group is available:
   ```javascript
   case 'og_level_questions':
     const LEVEL_DESC_GROUPS = new Set(['NU','PS','NT','PO','SW','ED']);
     return !!(answers.og_confirm && LEVEL_DESC_GROUPS.has(answers.og_confirm.og_code));
   ```

3. New component `OgLevelQuestions` in `components.jsx`:
   - Receives `cfg.questions` (fetched from `GET /api/jes/level-criteria?og_code=...&sub_group=...`)
   - Renders as standard `choices` questions in sequence
   - On all questions answered: calls `POST /api/jes/level-suggest`, stores response in component state
   - Emits `{ questions_answered: true, suggested_level: N, confidence: "high" }` as the step answer

4. Modified `cfgOverride` in app.jsx for `og_level` step: if `answers.og_level_questions?.suggested_level` exists, pass `preselect: answers.og_level_questions.suggested_level` into the cfg. `OgLevelPicker` highlights the suggested level visually (different styling, not locked).

5. `OgLevelPicker` enhancement: if `cfg.preselect` is set, render that button with `is-suggested` class and a brief label "(suggested)" — selectable and overridable.

**What this does NOT require:**
- No changes to PATCH persistence (og_level PATCH fires as before when user confirms)
- No changes to the classification badge logic
- No new database columns
- No LLM call

---

## Scope Boundary

### Groups that get JES level questions

| Group / Sub-group | Level Method | Questions Needed |
|-------------------|-------------|-----------------|
| NU-HOS | Level description | 2 questions (scope + autonomy) |
| NU-CHN | Level description | 2 questions (same as HOS) |
| NU-EMA | Level description | 1 question |
| PS | 3-factor description | 3 questions |
| NT-ADV | Level description | 1 question |
| NT-DIT | Level description | 1-2 questions |
| NT-HME | Level description | 1 question |
| PO-TCO | Level progression | 2 questions |
| SW-CHA | Level description | 1 question |
| ED-LAT | Level description | 1 question |
| ED-EST | Level description | 1 question |

### Groups whose level is already computed (no new questions)

| Group | Reason | How Level Is Determined |
|-------|--------|------------------------|
| EC | LLM-scored JES | `/api/jes/score` response includes level |
| FI, IT, AS | Point totals in `NON_EC_TOTALS` | Plan 04 already computed |
| SW-SCW | Point-rated (1000 pt scale, boundaries 200-300-450-600-750-900) | Plan 04 |
| WP | Point-rated (1000 pt scale, boundaries 170-290-400-510-620-730-840-950) | Plan 04 |
| LC, LP | Point-rated | Plan 04 |
| FB, FS, MT | Point-rated | Plan 04 |
| CR, PM, GT, EL, AI, AU | `NON_EC_TOTALS` approximations | Plan 04 |

**For groups with already-computed levels:** `OgLevelPicker` should be modified to show a "Suggested: Level XX (based on JES scoring)" banner above the picker, pre-selecting the computed level but allowing override. This is a cosmetic change to the existing component, not a new flow.

---

## Pitfalls

### Pitfall 1: NU sub-group confusion at the og_confirm stage

**What goes wrong:** The user confirms `NU` as their OG group in `og_confirm`, but the sub-group (HOS / CHN / EMA) is stored in `confirmed_og.sub_group`. If `sub_group` is not populated at that point, `JES_LEVEL_CRITERIA` lookup fails silently and the `og_level_questions` step skips.

**Prevention:** Verify that `OgConfirmList` always populates `sub_group` when the user selects NU. If not, add a follow-up within the `og_level_questions` step: "Which NU sub-group best fits this position?" as the first question for NU.

**Warning sign:** `og_level_questions` step is skipped for a NU position when it should appear.

### Pitfall 2: `isStepVisible` receives stale `answers` snapshot

**What goes wrong:** `isStepVisible` reads `answers.qb_sector_gate.id` to gate legacy questions. If the user edits the sector-gate answer via the "Edit" button in the thread, the legacy question steps may not re-evaluate immediately because answered steps in the exchange thread are pre-rendered.

**Prevention:** `getVisibleSteps` is called from `stepIndex` memo in app.jsx — it will re-derive on any `answers` state change. Editing sector-gate will cause previously-answered legacy steps to become invisible in the visible-steps list. This is desirable. Verify that the "edit" path (`jumpToExchange`) invalidates answers for steps that become invisible after an edit.

**Warning sign:** User changes sector from "other" to "health/social" and the 4 EC/AS/IT/FI questions remain in the thread.

### Pitfall 3: `accumulateSignals` double-counting WP

**What goes wrong:** WP appears in both `pa_sh_sector` (via `qb_health_social_cluster` welfare_programs option) and `programme_admin_sector` (via the new `qb_programme_admin_cluster` welfare_program_delivery option). A user who explores both paths in an edit cycle could accumulate 2 WP signals when they should have 1.

**Prevention:** `accumulateSignals` only reads the current active (non-null) answers. Since `qb_health_social_cluster` is only visible when `sector = pa_sh_sector`, and `qb_programme_admin_cluster` only when `sector = programme_admin_sector`, only one of these can be active at a time. The stale answer from the other cluster will remain in the `answers` object but the predicate-gating ensures only one cluster step is on the visible path. However: if the stale answer is still in `answers` (not cleared on sector change), it WILL be read by `accumulateSignals` because that function iterates all `qbStepIds` regardless of visibility.

**Fix:** Either (a) clear cluster answers when sector-gate answer changes, or (b) modify `accumulateSignals` to check `isStepVisible` before reading each step's answer. Option (b) is cleaner and requires passing `answers` to the visibility check, which is already the signature.

### Pitfall 4: `og_level_questions` fires for groups that are already point-scored

**What goes wrong:** If the `LEVEL_DESC_GROUPS` set in `isStepVisible` is not maintained in sync with which groups have a `JES_LEVEL_CRITERIA` entry, the step will show but the API call will return 404 or an empty response.

**Prevention:** The set in `isStepVisible` and the keys in `JES_LEVEL_CRITERIA` (backend) must be derived from the same source of truth. Consider exporting the list from a backend endpoint `GET /api/jes/level-criteria-groups` so the frontend always uses the current backend definition.

### Pitfall 5: SW routing ambiguity (CHA vs SCW)

**What goes wrong:** SW has two sub-groups: Chaplain (CHA, level-description, 3 levels) and Social Work (SCW, point-rated, 5 levels). The current `qb_health_social_cluster` routes social_work_services to SW generally. If the confirmed og shows `SW` with sub_group `CHA`, the point-rating path will produce wrong results; if `SW` with sub_group `SCW`, level-questions path is wrong.

**Prevention:** The `og_confirm` sub-group selection (already implemented for NU/SW/ED in the OgConfirmList picker) must produce the correct sub_group for SW. Verify that `SW-CHA` vs `SW-SCW` sub-groups are surfaced in og_confirm. The `og_level_questions` step must branch on sub_group: CHA → level-description questions (3 levels); SCW → pre-computed point score from Plan 04.

---

## Sources

All findings verified by direct file read.

- `v2/frontend/src/data.jsx` (lines 1-610) — STEPS structure, isStepVisible, accumulateSignals, OG_LEVELS
- `v2/frontend/src/app.jsx` (lines 1-60, 600-680) — cfgOverride pattern for og_level step
- `v2/frontend/src/components.jsx` (lines 477-505) — OgLevelPicker
- `v2/backend/app/data/constants.py` (lines 197-550, 1195-1246) — QUESTION_BANK, NON_EC_TOTALS
- `data/Job_evaluation/NU Nursing - Job Evaluation Standard` — full read; 3 factors, 15 benchmarks
- `data/Job_evaluation/PS Psychology - Job Evaluation Standard` — full factors and benchmark index
- `data/Job_evaluation/NT Nutrition and Dietetics - Job Evaluation Standard` — full read; 3 sub-groups
- `data/Job_evaluation/PO Police Operations Support - Job Evaluation Standard` — full level progression chart
- `data/Job_evaluation/SW Social Work - Job Evaluation Standard` — CHA and SCW sub-groups; point boundaries
- `data/Job_evaluation/ED Education - Job Evaluation Standard 2017.txt` — all 3 sub-groups; level descriptions
- `data/Job_evaluation/WP Welfare - Job Evaluation Standard` — point boundaries verified (170-840+)

**Confidence:** HIGH for architecture fix (pure code reading). HIGH for NU, PS, PO, SW-CHA, ED, NT level criteria (read verbatim from JES files). MEDIUM for NT-HME (JES file read but Home Economist sub-group is narrow and may be rare in federal government context).
