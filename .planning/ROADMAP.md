# Roadmap: JD Builder

## Milestones

- ✅ **v1.0 MVP** — Phases 1–9 incl. 8.1 (shipped 2026-06-03)
- ✅ **v2.0 Real Guided Conversation** — Phases 10–20 (shipped 2026-06-10)
- ✅ **v3.0 Classification Depth & Document Quality** — Phases 21–25 (shipped 2026-06-16)
- 🚀 **v4.0 Seven-Elements Conversational Architecture** — Phases 26–29 (in progress, 2026-06-19)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1–9 incl. 8.1) — SHIPPED 2026-06-03</summary>

- [x] Phase 1: Project Foundation (3/3 plans) — completed 2026-05-28
- [x] Phase 2: NOC Data Pipeline (4/4 plans) — completed 2026-05-28
- [x] Phase 3: CA + JES Data Pipeline (4/4 plans) — completed 2026-06-01
- [x] Phase 4: NL→NOC Mapping (4/4 plans) — completed 2026-06-02
- [x] Phase 5: OG Classification (4/4 plans) — completed 2026-06-02
- [x] Phase 6: JD Generation (4/4 plans) — completed 2026-06-02
- [x] Phase 7: JES Scoring (4/4 plans) — completed 2026-06-02
- [x] Phase 8: Export (4/4 plans) — completed 2026-06-02
- [x] Phase 8.1: JES Advisor Override & Per-Factor Retry (3/3 plans) — completed 2026-06-03
- [x] Phase 9: DND DRF Integration (4/4 plans) — completed 2026-06-03

Full phase details: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

</details>

<details>
<summary>✅ v2.0 Real Guided Conversation (Phases 10–20) — SHIPPED 2026-06-10</summary>

- [x] Phase 10: Project Scaffold (4/4 plans) — completed 2026-06-03
- [x] Phase 11: Data Foundation (2/2 plans) — completed 2026-06-04
- [x] Phase 12: Socratic Question Bank (2/2 plans) — completed 2026-06-04
- [x] Phase 13: Frontend SPA Shell (3/3 plans) — completed 2026-06-04
- [x] Phase 14: NOC Pipeline (4/4 plans) — completed 2026-06-04
- [x] Phase 15: Conversational UX (4/4 plans) — completed 2026-06-05
- [x] Phase 16: OG Classification (4/4 plans) — completed 2026-06-05
- [x] Phase 17: JES Scoring (4/4 plans) — completed 2026-06-08
- [x] Phase 18: JD Composition & Live Preview (4/4 plans) — completed (v2.0 scope)
- [x] Phase 19: Qualifications & Amendments (4/4 plans) — completed 2026-06-09
- [x] Phase 20: Export (3/3 plans) — completed 2026-06-10

Full phase details archived in ROADMAP.md history above.

</details>

<details>
<summary>✅ v3.0 Classification Depth & Document Quality (Phases 21–25) — SHIPPED 2026-06-16</summary>

- [x] **Phase 21: OG Expansion + Preview Fix** — Extend all six constants atomically for 16 OG groups (12 new); consolidate NON_EC_STANDARD_NAMES; full JES scoring for point-rating groups; level-lookup for level-description groups; sub-group disambiguation for NU/SW/ED; fix .doc-scroll CSS. (OGX-01, OGX-02, OGX-03, OGX-04, OGX-05, OGX-06, OGX-07, UI-01)
- [x] **Phase 22: SJD Library** — Parse SJD_LIBRARY constant from data/SJD Examples.txt; expose GET /api/sjd endpoints; non-blocking "Browse SJDs" flow at end of Role phase; SJD pre-fill with provenance and OG-change warning. (SJD-01, SJD-02, SJD-03)
- [x] **Phase 23: Writing Guide Integration** — Structural duty validation (active-voice, word-count, no-passive, no-duplicate); non-blocking inline .duty-hint warnings via POST /api/wd/{id}/validate-duties; Client Service Results question inserted in QUESTION_BANK; per-step OG-specific duty tips from OG_DEFINITIONS. (WG-01, WG-02, WG-03, WG-04)
- [x] **Phase 24: Risk Audit** — "Run compliance audit" button in Review phase; deterministic CBA clause matching (exclusion/scope/application articles) + Federal Court ERR principle rules; per-finding Accept/Manual Edit/Skip decisions written to audit_log; Manual Edit links to existing amendment panel. (AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-05) (completed 2026-06-16)
- [x] **Phase 25: Accessible Template** — Build and self-verify wd_accessible_template.docx (Part 1: position ID + signatures; Part 2: 7 subsections); populate Effort/Working Conditions from JES factor scores; retire TBS WD template; content-presence test against fully-completed WD. (ACC-01, ACC-02, ACC-03, ACC-04) — **Completed 2026-06-16 (pending 9-step human UAT)**

Full phase details in Phase Details section below.

</details>

### 🚀 v4.0 Seven-Elements Conversational Architecture (Phases 26–29)

v4.0 surfaces all 7 Part 2 sections of the TBS Accessible JD Template as a natural conversational experience. Two new WD fields (org_context, responsibilities_narrative) are added, connected to a completeness audit, exposed as structured JSON/CSV export for workforce analytics, and branched into a Manager-Track UX that hides classification internals from hiring managers.

- [x] **Phase 26: Org Context Conversational Step** — Foundation phase: new org_context typed field on WorkDescription + WDPatchRequest (same-commit rule), 4-part Socratic step added to STEPS (with stepIndex regression fix before insertion), document preview rendering above Client Service Results, Accessible DOCX Part 2 export. (ORG-01, ORG-02, ORG-03) — **Complete: Plan 01 (Wave 0 RED baseline) + Plan 02 (Wave 1 GREEN) both done; 8/8 RED stubs GREEN; 153/153 backend + 65/65 frontend GREEN; ORG-01/02/03 closed**
- [ ] **Phase 27: Responsibilities Narrative + Completeness Audit** — Last new WD field (responsibilities_narrative + WDPatchRequest co-update), document preview section, Accessible DOCX export, POST /api/wd/{id}/validate-elements with 5-state matrix, Review phase completeness badge as soft gate with jump-to-fill navigation. (RESP-01, RESP-02, RESP-03, ELEM-01, ELEM-02, ELEM-03)
- [ ] **Phase 28: Manager-Track UX** — Role selector at app entry (jd-builder-v2-role localStorage key, never in WD model or answers dict), userRole state slice, conditional rendering suppressing OG/JES/CBA strings in manager mode, manager-track STEPS variant, require_og_confirmed bypass via wd_type field, DRAFT watermark on manager DOCX exports. (MGR-01, MGR-02, MGR-03)
- [ ] **Phase 29: Structured Export + Enhanced Poster** — Shared build_seven_elements(wd) helper in export_service.py, POST /api/wd/{id}/export/json (7-element analytics JSON with provenance), POST /api/wd/{id}/export/csv (utf-8-sig DictWriter, one row per duty), SPA JSON + CSV download buttons, enhanced poster with "About the Organization" section, build_poster_template.py self-verify update. (SEXP-01, SEXP-02, SEXP-03, POST-01)

**Coverage:** 16/16 v4.0 requirements mapped · 4 phases (26–29) · 0 unmapped · 0 orphans

---

### ICM Workspace (Phases 30–33)

Adds `jd-builder` as a workspace in the ICM repo (`~/ICM/workspaces/jd-builder/`), modeling the full JD creation workflow as a staged AI pipeline. Parallel to v4.0 -- no app code changes.

- [ ] **Phase 30: Workspace Scaffold + Policy Vault** — CLAUDE.md, CONTEXT.md, setup questionnaire, policy-vault with TBS classification policy, JD writing guide, and JES standards. (ICM-01, ICM-02, ICM-03)
- [ ] **Phase 31: Shared Reference Extraction** — `shared/og-definitions.md` and `shared/qualification-standards.md` extracted from app constants; `shared/department-profile.md` template. (ICM-04)
- [ ] **Phase 32: Stage CONTEXT Files** — All 5 stage CONTEXT.md files (01-intake through 05-export) with Inputs/Process/Outputs tables; all stage reference files. (ICM-05 through ICM-09)
- [ ] **Phase 33: Skills + Integration + Validation** — `skills/jd-builder-api/SKILL.md`; ICM root CLAUDE.md and README.md updated; placeholder audit; status check. (ICM-10 through ICM-13)

Full milestone doc: [milestones/icm-workspace.md](milestones/icm-workspace.md)

---

## Phase Details

### Phase 21: OG Expansion + Preview Fix

**Goal:** The classification engine covers all 16 GC occupational groups with authoritative data: all six constants are consistent and tested, JES scoring runs for every group, sub-group disambiguation surfaces for NU/SW/ED, and the document preview page extends cleanly to any length.

**Depends on:** Phase 20 (v2.0 complete; constants and JES service are in place to extend)

**Requirements:** OGX-01, OGX-02, OGX-03, OGX-04, OGX-05, OGX-06, OGX-07, UI-01

**Success Criteria** (what must be TRUE):
1. Advisor can reach the Classification step with any of the 16 OG groups and receive a JES scorecard — point-rated groups (FB, FS, LP, MT, LC, SW-SCW) show per-factor rows; level-described groups (NU, PS, NT, PO, WP, SW-CHA, ED sub-groups) show a single totals line matching the v2.0 FI/AS pattern
2. Advisor classifying a NU, SW, or ED position sees a disambiguation alert identical in style to the existing AS/EC alert, and the confirmed sub-group is stored on the WorkDescription
3. When the advisor answers Socratic questions characteristic of any new OG group (ED, FB, FS, LC, LP, MT, NT, NU, PO, PS, SW, WP), that group appears in the top-3 OG candidates — confirmed by per-group integration tests
4. The document preview white page grows seamlessly with document content at any length; no content overflows into the grey background; existing split-pane layout is unaffected
5. A completeness test asserts every key in OG_LEVELS is present in OG_DEFINITIONS, QUAL_STANDARDS, NON_EC_TOTALS, NON_EC_STANDARD_NAMES, and JES_FACTORS_BY_GROUP; frontend QUAL_DEFAULTS and backend QUAL_STANDARDS match for all 16 groups

**Plans:** 9/9 plans complete

Plans:
- [x] 21-01-PLAN.md — Wave 0 test scaffolding (all Phase 21 test stubs, RED baseline)
- [x] 21-02-PLAN.md — CSS preview fix (UI-01) + NON_EC_STANDARD_NAMES consolidation (OGX-02)
- [x] 21-03-PLAN.md — Atomic constant extension for all 16 OG groups (OGX-01, OGX-03)
- [x] 21-04-PLAN.md — JES service routing: point-rating and level-description paths (OGX-05, OGX-06)
- [x] 21-05-PLAN.md — QUESTION_BANK sector-gate + cluster questions (OGX-04)
- [x] 21-06-PLAN.md — Sub-group disambiguation: API, model, frontend picker, .asec-alert CSS (OGX-07)
- [x] 21-07-PLAN.md — Question bank restructure: gate legacy work-type questions + add qb_programme_admin_cluster (OGX-04)
- [x] 21-08-PLAN.md — JES level determination: Socratic mini-interview + suggested level (JES-LEV-01)

---

### Phase 22: SJD Library

**Goal:** An advisor can browse DND Standard Job Descriptions as reference or use one as the starting point for a new conversation, with every seeded duty carrying SJD provenance through to the DOCX export manifest.

**Depends on:** Phase 21 (expanded OG data makes SJD test fixtures richer; OG constants needed for SJD pre-fill validation)

**Requirements:** SJD-01, SJD-02, SJD-03

**Success Criteria** (what must be TRUE):
1. At the end of the Role phase, a non-blocking "Browse SJDs" action is available; the advisor can filter by OG group and see SJD entries with title, OG, level, and a preview of seed duties
2. Selecting an SJD pre-fills confirmed_og, og_level, and seed duties on the WorkDescription; seed duties display a distinct "SJD" provenance marker in the document preview distinct from NOC-sourced duties
3. When the DOCX is exported after an SJD start, the version manifest includes the SJD number and source as a provenance entry
4. If the advisor changes confirmed_og after an SJD pre-fill, a warning appears: "Departing from the SJD classification turns this into a new evaluation — the SJD decision no longer applies"

**Plans:** 4/4 plans complete

Plans:
- [x] 22-01-PLAN.md — Wave 0 test scaffolding (all Phase 22 test stubs, RED baseline) — 10 test functions in v2/backend/tests/test_sjd.py; 9/10 RED
- [x] 22-02-PLAN.md — SJD_LIBRARY constant + GET /api/sjd endpoints + router registration — 7/9 test_sjd.py stubs GREEN; full backend suite 122 passed, 3 failed (the 3 RED tests are 22-03 scope)
- [x] 22-03-PLAN.md — DraftDuty/WorkDescription model extensions + POST /api/wd/{id}/sjd-start + manifest provenance — 10/10 test_sjd.py GREEN; 125/125 backend suite GREEN
- [x] 22-04-PLAN.md — Frontend: fetchSjds helpers + Browse SJDs action + SJD browser panel + SJD-03 warning — 224.07 kB JS / 68.62 kB gzip; 60/60 frontend tests GREEN; 125/125 backend tests GREEN; awaiting human UAT of 9-step browser verification

---

### Phase 23: Writing Guide Integration

**Goal:** Every duty the advisor authors or selects is evaluated against Writing Guide structural rules, with non-blocking inline hints visible during entry, a Client Service Results question anchoring the duty section, and OG-specific tips drawn from authoritative source text.

**Depends on:** Phase 21 (OG_DEFINITIONS source for per-group tips covers all 16 groups), Phase 22 (SJD duties are a calibration corpus for the validator false-positive rate)

**Requirements:** WG-01, WG-02, WG-03, WG-04

**Success Criteria** (what must be TRUE):
1. After the duty-phase commit, the advisor sees inline .duty-hint warnings on any duty that fails structural rules (non-verb opener, word count outside 8–25, passive-voice opener, duplicate text); warnings are non-blocking — the advisor can proceed without fixing them
2. POST /api/wd/{id}/validate-duties returns per-duty validation findings; fewer than 15% of the 9 SJD Examples.txt duties are flagged (confirming calibration)
3. The QUESTION_BANK includes a "Client Service Results" question inserted before the Key Activities duties step, matching the Writing Guide's document structure; the conversation pane renders it in the correct position
4. During duty entry, the advisor sees a per-step tip drawn verbatim from OG_DEFINITIONS for the confirmed OG group — not a hardcoded string

**Plans:** 4/4 plans complete

Plans:
- [x] 23-01-PLAN.md — Wave 0: RED baseline test stubs + duty_validator.py stub
- [x] 23-02-PLAN.md — duty_validator.py: four WG-01 deterministic rules
- [x] 23-03-PLAN.md — POST /api/wd/{id}/validate-duties endpoint
- [x] 23-04-PLAN.md — Frontend: client_service_results step, OG_DUTY_TIPS, dutyHints rendering

**UI hint**: yes

---

### Phase 24: Risk Audit

**Goal:** An advisor in Review phase can run a deterministic compliance audit that matches confirmed OG CBA clauses and Federal Court ERR principles against the current JD, and make an explicit Accept / Manual Edit / Skip decision on every finding — all decisions logged to the audit trail.

**Depends on:** Phase 23 (duty-validation infrastructure and Writing Guide steps are complete; validated duties feed audit checks)

**Requirements:** AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-05

**Success Criteria** (what must be TRUE):
1. The "Run compliance audit" button appears in the Review phase; the audit never runs automatically; re-running replaces previous findings in the UI
2. Each finding displays: the JD section it applies to, severity (advisory/warning), the verbatim CBA clause or court citation, and a plain-language recommendation
3. For every finding, the advisor can choose Accept, Manual Edit, or Skip ("Not applicable — no conflict found"); each choice is written to audit_log with event='risk_audit_decision'
4. Manual Edit opens the existing amendment panel for the flagged section; the amendment note and the audit finding share the same section key and co-appear when the section is inspected
5. The audit produces zero findings for a minimal well-formed WD that has no CA conflicts and no ERR principle violations — confirming the two-signal rule suppresses false positives

**Plans:** 4/4 plans complete

Plans:
- [x] 24-01-PLAN.md — Wave 0: RED baseline test stubs + risk_auditor.py stub
- [x] 24-02-PLAN.md — risk_auditor.py: CBA loader + ERR rules + two-signal CBA matching
- [x] 24-03-PLAN.md — POST /api/wd/{id}/audit + POST /api/wd/{id}/audit/decide endpoints
- [x] 24-04-PLAN.md — Frontend: auditFindings state + handleRunAudit + ReviewState audit panel

**UI hint**: yes

---

### Phase 25: Accessible Template

**Goal:** The exported DOCX uses the Accessible JD format with both parts fully populated — including Effort and Working Conditions derived from JES factor scores — and every template variable resolves to a non-empty string for a completed WD.

**Depends on:** Phase 21 (JES scoring extended to all groups; Effort/Working Conditions sections map from JES factor scores), Phase 24 (export infrastructure stable after all audit and amendment changes)

**Requirements:** ACC-01, ACC-02, ACC-03, ACC-04

**Success Criteria** (what must be TRUE):
1. POST /api/wd/{id}/export/docx produces a DOCX structured per the Accessible JD format: Part 1 (position identification + 3 signature blocks) and Part 2 (Org Context, Client Service Results, Key Activities, Skills, Effort, Responsibilities, Working Conditions)
2. Effort and Working Conditions sections are populated from JES factor scores for OG groups whose JES standard defines those factors; sections show "[To be completed by advisor]" only where the OG's JES does not define them
3. A content-presence test opens the rendered DOCX via python-docx and confirms every non-placeholder template variable resolves to a non-empty string for a fully-completed WD
4. The previous TBS WD template is retired; all existing export tests pass with assertions updated to the Accessible format structure; the poster DOCX template is unchanged

**Plans:** 3/3 plans complete

Plans:
- [x] 25-01-PLAN.md — Wave 0: RED baseline — 4 JES-shape fixture helpers + ACC-02/ACC-04 tests in test_export.py
- [x] 25-02-PLAN.md — build_accessible_template.py + self-verifying wd_accessible_template.docx (Part 1 17-field table + 3 static signature blocks; Part 2 7 subsections) (ACC-01)
- [x] 25-03-PLAN.md — _factor_category_map + rewritten _build_wd_context + Accessible template path swap + retire TBS template (ACC-02, ACC-03, ACC-04) — 6 RED tests GREEN, 19/19 test_export.py, 150/150 full backend suite

---

### Phase 26: Org Context Conversational Step

**Goal:** Advisors can capture and persist organizational context through a 4-part conversational step; the text renders in the document preview above Client Service Results and exports to the Accessible JD DOCX Part 2 Organizational Context section.

**Depends on:** Phase 25 (Accessible Template complete; Part 2 structure is the export target)

**Requirements:** ORG-01, ORG-02, ORG-03

**Success Criteria** (what must be TRUE):
1. Advisor completes the org context step (work stream, organizational placement, reporting relationship, additional context) and the assembled text appears in the live document preview above the Client Service Results section without disrupting any existing step.
2. A PATCH /api/wd round-trip (PATCH with org_context → GET → assert org_context non-None) confirms WDPatchRequest was co-updated in the same commit as WorkDescription; no silent field drop.
3. An existing session with a persisted stepIndex integer in localStorage resumes at the correct step after the org_context step is inserted into STEPS — confirming the resume-by-last-answered fix is in place before any STEPS entry is added.
4. Downloading the Accessible JD DOCX for a WD with org_context filled shows that text in the Part 2 Organizational Context section; a WD without org_context shows the advisor placeholder string.

**Plans:** 2/2 plans complete

Plans:
- [x] 26-01-PLAN.md — Wave 0 RED test stubs (3 backend + 5 frontend = 8 total; 150 pre-existing backend + 60 pre-existing frontend GREEN; new stubs fail with AssertionErrors)
- [x] 26-02-PLAN.md — Full implementation (stepIndex resume fix, WD + WDPatchRequest co-update, OrgContextInput 4-part component, STEPS org_context insertion, DocumentPane org_ctx + csr Secs, export_service priority over synthesized fallback); all 8 Wave 0 RED stubs GREEN; 153 backend + 65 frontend GREEN

**UI hint**: yes

---

### Phase 27: Responsibilities Narrative + Completeness Audit

**Goal:** Advisors can record a responsibilities narrative that exports to the Accessible DOCX, and the Review phase displays a per-element completeness badge over all 7 Part 2 elements using a single validate-elements endpoint.

**Depends on:** Phase 26 (org_context field exists; both new WD fields must be present before the completeness audit can evaluate all 7 elements)

**Requirements:** RESP-01, RESP-02, RESP-03, ELEM-01, ELEM-02, ELEM-03

**Success Criteria** (what must be TRUE):
1. Advisor enters a free-text responsibilities narrative; it appears as its own named section in the document live preview and persists via PATCH /api/wd without loss on GET round-trip — confirming WDPatchRequest co-update.
2. Downloading the Accessible JD DOCX shows the responsibilities narrative in the Part 2 Responsibilities section; a WD without the narrative shows the advisor placeholder.
3. POST /api/wd/{id}/validate-elements returns per-element status for all 7 elements: Effort and Working Conditions show as "derived" (not "missing") when jes_total_points is populated; Responsibilities shows the narrative value when filled, and "missing" (not "not_applicable") when empty — because the field is open to all positions.
4. The completeness audit reads wd.org_context (the typed root field), not the derived fallback text from _build_organizational_context_text() — confirmed by a test that leaves org_context None while record has branch/reports data, asserting the element status is "missing".
5. The Review phase completeness badge shows N/7 elements as populated or derived; the advisor can proceed to export with any count after acknowledging the badge — the badge is a soft gate, not a hard block.

**Plans:** 2 plans

Plans:
- [ ] 27-01-PLAN.md — Responsibilities Narrative vertical slice (RESP-01/02/03): typed responsibilities_narrative field + WDPatchRequest co-update, free-text STEPS step, DocumentPane Responsibilities Sec, DOCX export priority (narrative or placeholder)
- [ ] 27-02-PLAN.md — Seven-Elements Completeness Audit (ELEM-01/02/03): build_seven_elements(wd) shared helper, POST /api/wd/{id}/validate-elements endpoint, Review-phase N/7 completeness badge (soft gate)

**UI hint**: yes

---

### Phase 28: Manager-Track UX

**Goal:** A hiring manager can use the full application without seeing OG codes, JES factor names, or CBA clause references; their session is clearly labelled as a draft for the classification team, and the DOCX exports without a 409 gate error.

**Depends on:** Phase 27 (full conversation flow including org_context and responsibilities_narrative steps is stable before branching it for manager-track)

**Requirements:** MGR-01, MGR-02, MGR-03

**Success Criteria** (what must be TRUE):
1. On first load (localStorage key jd-builder-v2-role absent), a role selector screen precedes the conversation; selecting "I am a hiring manager" persists the role to localStorage and launches manager-track; selecting "I am a classification advisor" launches the standard flow; refreshing the page does not re-show the selector.
2. In manager mode, no OG group codes (EC, AS, IT, FI, etc.), JES factor names (e.g. "Supervision", "Initiative and Independent Action"), or CBA clause references appear in any visible UI element — confirmed by systematic visual inspection against the manager-track checklist covering STEPS labels, document preview, classification block, ReviewState, and export labels.
3. The manager-track STEPS array skips og_confirm, og_level, and JES override steps; a manager can reach Review and trigger a DOCX download without a 409 from require_og_confirmed; the downloaded DOCX is watermarked as "DRAFT — PENDING CLASSIFICATION".
4. The userRole value is never present in the WD PATCH body sent to /api/wd — confirmed by a test asserting WDPatchRequest does not accept a user_role key and that the field does not appear in the work_descriptions.data JSON column after a full conversation.

**Plans:** TBD

**UI hint**: yes

---

### Phase 29: Structured Export + Enhanced Poster

**Goal:** Advisors and managers can download machine-readable JSON and CSV exports mapping all 7 Part 2 elements for workforce analytics; the job poster gains an "About the Organization" section sourced from org_context.

**Depends on:** Phase 28 (manager-track wd_type field in place so export routes handle both tracks; org_context and responsibilities_narrative fields available from Phases 26–27)

**Requirements:** SEXP-01, SEXP-02, SEXP-03, POST-01

**Success Criteria** (what must be TRUE):
1. POST /api/wd/{id}/export/json returns a JSON object with all 7 Part 2 element keys (organizational_context, client_service_results, key_activities, skills, effort, responsibility, working_conditions) plus classification metadata and provenance fields; org_context and responsibilities_narrative populate their elements when filled; null when not set.
2. POST /api/wd/{id}/export/csv returns a UTF-8-with-BOM CSV with one row per key activity (duty), scalar fields repeated per row; the file opens in Excel without encoding errors; cells containing commas, double-quotes, or newlines are correctly quoted per RFC 4180.
3. The Review phase SPA shows JSON Download and CSV Download buttons alongside existing DOCX/PDF buttons; clicking either triggers a file download using the existing exportAs() pattern (fetch + Blob + URL.createObjectURL).
4. Both JSON and CSV export routes succeed for a manager-track WD without a 409; classification fields not set by the manager use "[ADVISOR TO COMPLETE]" placeholder strings in the output.
5. Downloading the job poster DOCX for a WD with org_context shows an "About the Organization" section; build_poster_template.py self-verifies with exit 0 after the template update.

**Plans:** TBD

**UI hint**: yes

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Project Foundation | v1.0 | 3/3 | Complete | 2026-05-28 |
| 2. NOC Data Pipeline | v1.0 | 4/4 | Complete | 2026-05-28 |
| 3. CA + JES Data Pipeline | v1.0 | 4/4 | Complete | 2026-06-01 |
| 4. NL→NOC Mapping | v1.0 | 4/4 | Complete | 2026-06-02 |
| 5. OG Classification | v1.0 | 4/4 | Complete | 2026-06-02 |
| 6. JD Generation | v1.0 | 4/4 | Complete | 2026-06-02 |
| 7. JES Scoring | v1.0 | 4/4 | Complete | 2026-06-02 |
| 8. Export | v1.0 | 4/4 | Complete | 2026-06-02 |
| 8.1. JES Advisor Override | v1.0 | 3/3 | Complete | 2026-06-03 |
| 9. DND DRF Integration | v1.0 | 4/4 | Complete | 2026-06-03 |
| 10. Project Scaffold | v2.0 | 4/4 | Complete | 2026-06-03 |
| 11. Data Foundation | v2.0 | 2/2 | Complete | 2026-06-04 |
| 12. Socratic Question Bank | v2.0 | 2/2 | Complete | 2026-06-04 |
| 13. Frontend SPA Shell | v2.0 | 3/3 | Complete | 2026-06-04 |
| 14. NOC Pipeline | v2.0 | 4/4 | Complete | 2026-06-04 |
| 15. Conversational UX | v2.0 | 4/4 | Complete | 2026-06-05 |
| 16. OG Classification | v2.0 | 4/4 | Complete | 2026-06-05 |
| 17. JES Scoring | v2.0 | 4/4 | Complete | 2026-06-08 |
| 18. JD Composition & Live Preview | v2.0 | 4/4 | Complete | — |
| 19. Qualifications & Amendments | v2.0 | 4/4 | Complete | 2026-06-09 |
| 20. Export | v2.0 | 3/3 | Complete | 2026-06-10 |
| 21. OG Expansion + Preview Fix | v3.0 | 9/9 | Complete | 2026-06-11 |
| 22. SJD Library | v3.0 | 4/4 | Complete (pending UAT) | 2026-06-11 |
| 23. Writing Guide Integration | v3.0 | 4/4 | Complete (pending UAT) | 2026-06-15 |
| 24. Risk Audit | v3.0 | 4/4 | Complete | 2026-06-16 |
| 25. Accessible Template | v3.0 | 3/3 | Complete (pending UAT) | 2026-06-16 |
| **26. Org Context Conversational Step** | **v4.0** | **2/2** | **Complete (Wave 0 RED + Wave 1 GREEN; 153 backend + 65 frontend GREEN; ORG-01/02/03 closed)** | — |
| **27. Responsibilities Narrative + Completeness Audit** | **v4.0** | **0/2** | **Ready to execute** | — |
| **28. Manager-Track UX** | **v4.0** | **0/?** | **Not started** | — |
| **29. Structured Export + Enhanced Poster** | **v4.0** | **0/?** | **Not started** | — |
