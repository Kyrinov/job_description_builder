# Roadmap: JD Builder

## Milestones

- ✅ **v1.0 MVP** — Phases 1–9 incl. 8.1 (shipped 2026-06-03)
- ✅ **v2.0 Real Guided Conversation** — Phases 10–20 (shipped 2026-06-10)
- 🚀 **v3.0 Classification Depth & Document Quality** — Phases 21–25 (in progress, 2026-06-10)

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

### 🚀 v3.0 Classification Depth & Document Quality (Phases 21–25)

v3.0 expands the classification engine to all GC occupational groups with JES standards, replaces the export template with the Accessible JD format, wires the Job Description Writing Guide into duty authoring, adds a CBA + jurisprudence compliance audit, and seeds a DND SJD library as a conversation starting point.

- [x] **Phase 21: OG Expansion + Preview Fix** — Extend all six constants atomically for 16 OG groups (12 new); consolidate NON_EC_STANDARD_NAMES; full JES scoring for point-rating groups; level-lookup for level-description groups; sub-group disambiguation for NU/SW/ED; fix .doc-scroll CSS. (OGX-01, OGX-02, OGX-03, OGX-04, OGX-05, OGX-06, OGX-07, UI-01)
- [ ] **Phase 22: SJD Library** — Parse SJD_LIBRARY constant from data/SJD Examples.txt; expose GET /api/sjd endpoints; non-blocking "Browse SJDs" flow at end of Role phase; SJD pre-fill with provenance and OG-change warning. (SJD-01, SJD-02, SJD-03)
- [ ] **Phase 23: Writing Guide Integration** — Structural duty validation (active-voice, word-count, no-passive, no-duplicate); non-blocking inline .duty-hint warnings via POST /api/wd/{id}/validate-duties; Client Service Results question inserted in QUESTION_BANK; per-step OG-specific duty tips from OG_DEFINITIONS. (WG-01, WG-02, WG-03, WG-04)
- [ ] **Phase 24: Risk Audit** — "Run compliance audit" button in Review phase; deterministic CBA clause matching (exclusion/scope/application articles) + Federal Court ERR principle rules; per-finding Accept/Manual Edit/Skip decisions written to audit_log; Manual Edit links to existing amendment panel. (AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-05)
- [ ] **Phase 25: Accessible Template** — Build and self-verify wd_accessible_template.docx (Part 1: position ID + signatures; Part 2: 6 subsections); populate Effort/Working Conditions from JES factor scores; retire TBS WD template; content-presence test against fully-completed WD. (ACC-01, ACC-02, ACC-03, ACC-04)

**Coverage:** 24/24 v3.0 requirements mapped · 5 phases (21–25) · 0 unmapped · 0 orphans

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

**Plans:** 4 plans

Plans:
- [ ] 22-01-PLAN.md — Wave 0 test scaffolding (all Phase 22 test stubs, RED baseline)
- [ ] 22-02-PLAN.md — SJD_LIBRARY constant + GET /api/sjd endpoints + router registration
- [ ] 22-03-PLAN.md — DraftDuty/WorkDescription model extensions + POST /api/wd/{id}/sjd-start + manifest provenance
- [ ] 22-04-PLAN.md — Frontend: fetchSjds helpers + Browse SJDs action + SJD browser panel + SJD-03 warning

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

**Plans:** TBD

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

**Plans:** TBD

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

**Plans:** TBD

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
| **21. OG Expansion + Preview Fix** | **v3.0** | **8/8** | **Gaps Found** | — |
| **22. SJD Library** | **v3.0** | **0/?** | **Not started** | — |
| **23. Writing Guide Integration** | **v3.0** | **0/?** | **Not started** | — |
| **24. Risk Audit** | **v3.0** | **0/?** | **Not started** | — |
| **25. Accessible Template** | **v3.0** | **0/?** | **Not started** | — |
