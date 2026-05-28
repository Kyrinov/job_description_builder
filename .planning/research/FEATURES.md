# Feature Landscape: GoC Work Description Builder

**Domain:** Government of Canada HR classification tooling — work description authoring for HR advisors
**Researched:** 2026-05-28
**Policy anchor:** TBS Directive on Classification (effective 2021-04-01), Directive on Classification Grievances, PSEA s.30-31, collective agreements (PA, EC, IT_CS and 25+ others)

---

## Policy Grounding: What a Legally Defensible WD Must Contain

The TBS Directive on Classification (28700) establishes the minimum standard. A work description that omits any of the following is either non-compliant or grievance-vulnerable.

### Mandatory Header Fields (TBS Directive on Classification)

| Field | Policy Basis | Notes |
|-------|-------------|-------|
| Position title | Directive — must "reflect the functions and nature of the work" | Cannot be generic; must describe actual work |
| Position number | Directive — mandatory identifying information | Used for tracking, CA compliance, HRMS linkage |
| Occupational group and level | Directive — mandatory identifying information | The classification decision itself |
| Supervisor's position number, group, and level | Directive — mandatory identifying information | Establishes reporting relationship for org context |
| Organizational context / mandate / supervisor-subordinate relationships | Directive — explicit requirement | Establishes work context required for JES scoring |
| Organization chart showing position's place in structure | Directive + CA articles (PA Art.57, IT_CS Art.20.02) | Must accompany or be appendable to the WD |
| Manager's signature and date signed | Directive — explicit requirement | Without this the WD is not legally complete |
| Date of last review | Directive recommends review every 5 years; 43% of occupied positions had WDs >5 years old as of 2016 TBS evaluation | System should track and surface staleness |

### Mandatory Content Elements (TBS Directive + CA Articles)

| Element | Policy Basis | Notes |
|---------|-------------|-------|
| Duties and responsibilities — complete and current | PA Art.57.01, IT_CS Art.20.02, EC Art.34; all require employee right to a "complete and current statement" | "Complete" is enforceable; missing duties = grievance trigger |
| Classification level (point value for JES-based OGs) | PA Art.57.01: "the classification level and, where applicable, the point rating allotted by factor" | Point-rated OGs must expose factor-by-factor scores |
| Written in bias-free plain language | TBS Directive — explicit requirement | Implicit PSEA s.31(3) requirement to avoid equity barriers |

### JES Scoring Requirements (Directive + JES Standards)

Every work description for a point-rated occupational group must be accompanied by a completed Job Evaluation Standard scoring sheet. All current JES standards (EC, IT, CT, and others effective 2023) are point-rating plans covering the four pay equity factors — Skill, Effort, Responsibility, Working Conditions — distributed across 7-9 elements per OG.

**EC JES (2023):** 9 elements — Decision Making, Leadership/Ops Management, Communication, Knowledge of Specialized Fields, Contextual Knowledge, Research and Analysis, Physical Effort, Sensory Effort, Working Conditions. Total 1,000 pts; 8 levels.

**IT JES (2021/2023):** 7 elements — Critical Thinking and Analysis, Leadership and Planning, Technical Knowledge, Management Knowledge, Communication and Interaction, Effort (Sensory + Physical), Work Environment (Psychological + Physical). Total 1,000 pts; 5 levels.

**Scoring evidence requirement:** Each element rating must be traceable to specific duties in the work description. A classification grievance succeeds when the rating cannot be substantiated by the documented work. This is the single largest source of legal vulnerability in current practice.

### Qualification Standard Requirements (PSEA s.31, TBS Qual Standards)

| Requirement | Policy Basis | Notes |
|-------------|-------------|-------|
| Minimum education as per TBS Qualification Standard for the OG | PSEA s.31(1); standards published per OG on Canada.ca | These are the employer-set floor — non-negotiable |
| Managers may require higher education if substantiated by duties | PSEA s.31(2); confirmed in TBS FAQ | Must be documented; cannot be arbitrary |
| Alternative education/experience accepted or excluded | Manager discretion under PSEA; must be stated explicitly | If alternative accepted, must appear on merit criteria |
| Position-specific experience (operational) | Manager discretion under PSEA s.30(2)(a) | Must be written to reflect actual duties, not wish list |

The WD establishes what the work IS; the Statement of Merit Criteria (SOMC) establishes what you need to DO that work. These are distinct documents, but the SOMC is derived from the WD. The tool builds WDs, not SOWCs, but must surface the Qual Standard so the SOMC can be constructed correctly.

### Official Languages Requirements (OLA / Directive on Official Languages for People Management)

| Requirement | Applies When | Notes |
|-------------|-------------|-------|
| Position language designation (unilingual EN/FR or bilingual CBC/BBB etc.) | All positions | Determined by manager based on duties and work location |
| Linguistic profile (R/W/O levels in second language) | Bilingual positions only | A, B, or C for Reading, Writing, Oral Interaction |
| WD itself must be available in both official languages | Bilingual designated regions / upon request | Not a pre-condition for classification, but required before staffing in bilingual regions |

**Note on bilingualism:** The WD itself does not need to be submitted in French before classification can occur, but it must be available in both languages before being used in a staffing process in a bilingual region. For DND, most positions in NHQ (Ottawa) are in a bilingual designated region. This is a post-authoring concern, not a classification-blocking one, but the tool should flag when language requirements fields are incomplete.

---

## Table Stakes Features

**Tool is unusable without these — they constitute the minimum viable compliant output.**

| Feature | Why Table Stakes | Policy Basis | Complexity |
|---------|-----------------|-------------|------------|
| Header block with all mandatory identifying fields | A WD missing position number, OG/level, supervisor info, date, or manager signature is non-compliant and non-submittable | TBS Directive s.4 | Low — structured form |
| Complete duties section (key activities + percentage of time or relative weight) | Employees have a CA right to a "complete and current statement"; missing duties trigger grievances | PA Art.57, IT_CS Art.20.02, EC Art.34 | Medium — drafting quality matters |
| Organizational context paragraph | Required by Directive; also drives JES scoring of scope elements | TBS Directive | Low — templatable |
| JES scoring sheet for confirmed OG | Classification is legally incomplete without point-rated justification; advisors cannot sign off without it | TBS classification standards, all JES documents | High — factor definitions vary by OG |
| Factor-to-duty traceability for JES scores | A score unsupported by duties is the primary grievance vector; advisor liability | TBS evaluation program findings | High — requires AI linking |
| Qualification Standard surface (per OG) | Every WD used in staffing requires a Qual Standard; omitting it means the advisor has to look it up externally | PSEA s.31, TBS Qual Standards | Medium — data lookup |
| OG definition with inclusions/exclusions | Classification to wrong OG is a critical error; advisor must confirm against definition | TBS OG Allocation Guide | Low — reference data |
| Export with provenance metadata | Classification decisions must be defensible; undocumented AI outputs cannot be signed off | PROJECT.md PROV-01 | Medium — metadata tracking |
| Manager signature date and review date fields | WD without signature date is not complete per Directive | TBS Directive | Low — form field |

---

## Differentiators

**Competitive advantages — meaningful improvement over the manual process.**

| Feature | Value Proposition | Current Pain (Manual) | Complexity |
|---------|------------------|----------------------|------------|
| Natural language → NOC mapping | Advisor describes work in plain English; system maps to NOC unit group and duty statements | Advisors manually search OASIS or use memory; inconsistent mapping, version drift | High — semantic similarity + OG boundary logic |
| OG suggestion with cited inclusions/exclusions | System recommends OG and cites the definition clause that supports it | Advisors rely on experience; wrong initial OG causes rework; classification grievances from OG mismatches | Medium — rule-based + LLM rationale |
| AI-drafted duties grounded in NOC | Duties grounded in authoritative NOC statements, not recycled boilerplate | Advisors copy-paste from old WDs; outdated language, generic statements, JES scoring mismatch | High — NOC data retrieval + drafting |
| JES scoring with AI-drafted rationale per factor | Each element pre-rated with a degree descriptor and brief rationale citing specific duties | Advisors score manually for each OG-specific element from memory; time-consuming, inconsistent | High — per-OG factor logic |
| CA validation post-draft | Flags duties that may conflict with CA scope restrictions or fall outside OG definition; cites the CA article | Advisors do this mentally from memory; misses conflicts, especially across 25+ CA groups | Medium — rule matching against CA text |
| DND DRF linkage | Connects position duties to the departmental Results Framework program and expected results | DND-specific; not done systematically; required for DND accountability reporting | Medium — DRF data lookup |
| Staleness detection | Flags if a WD being revised hasn't been reviewed in 5 years; prompts fresh JES scoring | 43% of occupied positions had WDs >5 years old (2016 TBS evaluation); problem worse by now | Low — date arithmetic |
| KLC suggestions by level | Surfaces the applicable Key Leadership Competencies for the confirmed level; advisor selects | Advisors must know which KLCs apply; inconsistent application | Low — lookup table |
| Bias-free language check | Flags gendered or exclusionary language in duties and requirements | Manual WD writing introduces unconscious bias; PSEA s.31(3) requires equity barrier evaluation | Medium — pattern matching + LLM review |

---

## Anti-Features

**Things to deliberately NOT build in V1.**

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Auto-submit classification decision to HRMS/PeopleSoft | Classification approval authority rests with designated managers and HROs (DAOD 5025-0); tool cannot hold this authority | Export to DOCX/PDF for human sign-off; the tool produces evidence, not decisions |
| Real-time OASIS or CA scraping | Prototype proved this breaks on HTML structure changes; blocked during Canada.ca maintenance windows | Local authoritative files, manually refreshed; tool warns when source files are older than X months |
| Statement of Merit Criteria (SOMC) generation | SOMC is a staffing document governed by PSEA appointment processes; separate from classification; V1 is classification only | Surface Qual Standard data as reference; SOMC authoring is V3+ |
| Pay rate recommendation | Pay band calculation is complex, depends on appointment type, collective agreement, increments, and Phoenix legacy issues; liability risk | Display the applicable rate table as reference only |
| Classification grievance tracking | Grievance management is an HRO workflow system problem; out of scope and legally sensitive | Include CA citation metadata in export so grievance handling has traceable source |
| Manager-facing UX | Managers need substantially more guardrails, plain-language prompting, and error-proofing; V1 advisor workflow cannot safely be exposed to managers without redesign | PROJECT.md Out of Scope; V2 goal |
| Automated French translation of WD | Machine translation of legal HR documents is high-risk; bilingual requirement is not a classification pre-condition | Flag language designation fields; advisor arranges official translation through departmental language bureau |
| Multi-position bulk processing | V1 is single-position; bulk tooling requires audit logging, version control, and conflict resolution not yet designed | Document the pattern; V2 feature with proper queue management |
| Live integration with Phoenix/HRMS | Phoenix integration is a government-wide risk area; out of scope and dangerous without proper testing | Export formats designed for manual HRMS entry; document field mapping |

---

## Feature Dependencies

```
NOC data loaded (Bronze → Gold)
  → OG suggestion (CLASS-01, CLASS-02)
    → JES scoring sheet (JES-01, JES-02)
      → Export with provenance (EXPORT-01, PROV-01)

OG suggestion confirmed
  → Qualification Standard surface (QUAL-01)
  → CA validation (CA-01, CA-02)
  → KLC suggestions (COMP-01)

Duties drafted (JD-01, JD-02)
  → JES scoring (JES-01) — scoring requires complete duties
  → CA validation (CA-01) — validation requires drafted duties
  → Bias-free language check
```

---

## MVP Recommendation

### Must ship (MVP = legally usable output)

1. **Header block** — all mandatory fields from Directive, form-driven, required before export
2. **Natural language input → NOC mapping** — core value proposition; drives everything downstream
3. **OG suggestion with cited OG definition** — advisor confirms before proceeding
4. **AI-drafted duties from NOC** — complete enough that the advisor edits, not writes from scratch
5. **JES scoring sheet for confirmed OG** — point ratings with AI-drafted rationale per element
6. **Qual Standard surface** — lookup for confirmed OG, pre-populates fields
7. **Export (DOCX + PDF) with provenance metadata** — traceable citations on every content element

### High-value for V1 but deferrable if timeline is tight

8. **CA validation** — post-draft flag; advisors can work around manually, but this is a key differentiator
9. **DRF linkage** — DND-specific; significant value for DND but not blocking for other departments

### Defer to V2

10. **Manager-facing UX** (PROJECT.md Out of Scope — confirmed)
11. **SOMC generation** — distinct legal document; scope creep in V1
12. **Bulk processing / multi-position** — requires audit infrastructure not yet designed
13. **French translation workflow** — operational concern, not classification concern

---

## DND-Specific Requirements

**Based on DAOD 5025-0 and DND classification context:**

| Requirement | Source | Impact on Features |
|-------------|--------|-------------------|
| Classification authority delegated from DM to managers/HROs | DAOD 5025-0 | Tool must produce advisor-ready evidence, not make the decision; export for sign-off |
| DND civilian positions follow TBS classification standards (no DND-specific JES) | DAOD 5025-0 | No DND-specific JES data needed; same OGs and standards as rest of CPA |
| DRF linkage is DND-specific accountability requirement | PROJECT.md, DRF dataset in data/ | DRF-01 requirement; connects position to Departmental Results Framework program |
| DND Ombudsman report identified "positions over people" problem — WDs not reflecting actual work | Ombudsman report on civilian classification | Differentiator: duties grounded in NOC rather than copied from previous incumbent's WD |
| DAOD 5025-0 requires cyclical review | DAOD 5025-0 | Staleness detection feature; flag WDs not reviewed in 5 years |
| DWAN constraints: tool runs on-premise (Jetson AGX Orin) | PROJECT.md | Confirms Ollama-first, no external API dependency requirement; local data architecture |

**DND does not have a separate classification standard** — civilian positions use the same GoC-wide OG structure and TBS JES standards. The DND-specific layer is: DRF linkage, DAOD compliance for authority delegation, and departmental guidance from ADM(HR-Civ) on HRMS data entry (beyond V1 scope).

---

## What HR Advisors Actually Complain About (Grounded in Evidence)

From the TBS Evaluation of the Classification Program (published findings) and CA provisions:

1. **Outdated WDs:** 43% of occupied positions had WDs >5 years old as of 2016; problem is systemic and worsening. Advisors inherit old WDs written for previous incumbents and spend hours updating them.

2. **JES scoring inconsistency:** 33% of surveyed classification advisors disagreed they had adequate classification expertise. Factor rating requires knowledge of each OG-specific element; advisors evaluate across many OGs and cannot hold all degree descriptors in memory.

3. **Generic boilerplate duties:** Copy-pasting from previous WDs produces duties that don't reflect actual work. This creates JES scoring mismatches and classification grievances.

4. **Missing traceability:** When employees challenge a classification, advisors need to show which duties support each JES factor rating. Without documented links, defense is verbal and weak.

5. **Classification reform churn:** PA group restructuring (CR, AS, PM etc. → 5 new sub-groups) means thousands of WDs are being re-evaluated under new standards with new factor definitions. Advisors need to rerate positions without clear guidance on how new factor definitions map to old duties.

6. **OG boundary disputes:** Inclusions/exclusions language in OG definitions is dense and frequently misapplied. IT vs EC, EC vs PE, AS vs IS — wrong OG allocation is the second-most common grievance trigger after JES scoring disagreements.

---

## Policy Areas That Are Ambiguous or Under Active Change

| Area | Ambiguity | Risk for Tool |
|------|-----------|--------------|
| PA group classification reform | New sub-groups (CR→AS transition, new CT, new MN) not fully implemented; WDs in transition; new JES factors effective but conversion still ongoing | Tool must use current JES standard text, not pre-2023 versions; PA OG boundaries are in flux |
| NOC 2021 adoption in GoC classification | Switch to NOC 2021 happened November 2022 but TBS Allocation Guide and many internal mapping tools still reference NOC 2016 structures | Use NOC 2021 as primary; document version in all NOC citations; flag if a matched NOC unit group doesn't have a clear OG mapping |
| Pay equity compliance in JES | New JES standards (EC 2023, IT 2021) were redesigned to comply with Pay Equity Act; older standards (EC 2009, IT pre-2021) may not. Using old standards creates pay equity liability | Always use current JES versions; version-tag JES source data |
| Bilingualism requirement timing | Policy is clear that WD must be available in both languages before use in staffing, but not before classification. Edge case: can a position be classified with only an EN WD? | Tool should flag but not block; include language designation field in header; advisor responsibility |
| Deputy Head-Directed Classification | Appendix A of the Directive allows DH-directed decisions outside standard process — not common but creates edge cases where standard JES scoring doesn't apply | Document as known edge case; tool does not support DH-directed classification in V1 |

---

## Sources

- TBS Directive on Classification (id=28700), effective 2021-04-01 — work description requirements (via WebSearch extract, confirmed against multiple secondary sources; direct fetch blocked by canada.ca WAF)
- PA Collective Agreement (PSAC/TBS, 2023) — Article 57: Statement of Duties — direct text from `/data/agreements/PA/PA_full.json`
- IT_CS Collective Agreement (PIPSC/TBS) — Article 20: Reclassification and Statement of Duties — direct text from `/data/agreements/IT_CS/IT_CS_full.txt`
- EC Collective Agreement (CAPE/TBS) — Article 34 reference — from `/data/agreements/EC/` JSON
- EC JES (2023 effective date) — 9 elements, point boundaries, degree descriptors — direct text from `/data/Job_evaluation/EC Economics and Social Science Services - Job Evaluation Standard 2017.txt`
- IT JES (2021, amended 2025) — 7 elements, weighting model — direct text from `/data/Job_evaluation/IT Information Technology - Job Evaluation Standard.txt`
- PSEA s.30-31 — merit, qualification standards — direct text from `/data/public_service_employment_act.txt`
- DAOD 5025-0 Classification of Civilian Positions — via WebSearch extract
- TBS Evaluation of the Classification Program — 43% outdated WDs finding, capacity gaps — via WebSearch extract
- TBS Key Leadership Competencies framework (OCHRO) — 6 competencies — via WebSearch
- NOC 2021 Version 1.0 — TEER structure, 5-digit hierarchy — via WebSearch (Statistics Canada / ESDC)
- PA Classification Reform / Occupational Group Structure Review — PA sub-groups, conversion timeline — via PSAC WebSearch
- Official Languages Directive (id=26168) and Commissioner guidance — bilingual position designation — via WebSearch
