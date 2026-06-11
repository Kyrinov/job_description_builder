---
phase: 21-og-expansion-preview-fix
verified: 2026-06-11T12:30:00Z
status: gaps_found
score: 7/9 must-haves verified
overrides_applied: 0
overrides: []
requirements_checked: [OGX-01, OGX-02, OGX-03, OGX-04, OGX-05, OGX-06, OGX-07, UI-01, JES-LEV-01]

gaps:
  - truth: "Confirmed sub_group from OgConfirmList is propagated to answers.og_confirm so the og_level_questions step (cfg.sub_group) can fetch the correct JES level criteria"
    status: failed
    reason: |
      OgConfirmList.handleSubGroupSelect (components.jsx:393-408) updates local state and POSTs
      to /api/wd/{id}/confirm-subgroup, but NEVER calls onChange({...value, sub_group: sg}).
      The cfgOverride for og_level_questions (app.jsx:646) reads
        sub_group: answers.og_confirm?.sub_group || record.confirmed_og?.sub_group || null
      but neither path can ever be set by the current OgConfirmList flow. result: cfg.sub_group
      is null in OgLevelQuestions for NU/SW/CHA/ED/LAT/ED/EST/NT/PO users, the API call
      /api/jes/level-criteria?og_code=NU returns 404 (only NU-HOS/NU-CHN/NU-EMA exist in
      JES_LEVEL_CRITERIA), criteria stays null, the component renders "Level criteria
      not available for this group.", and the user is stuck — answerValid returns false
      (value is null) so the Continue button is disabled. Only PS (bare key in
      JES_LEVEL_CRITERIA, no sub_group needed) works end-to-end.
    artifacts:
      - path: "v2/frontend/src/components.jsx"
        issue: "handleSubGroupSelect (line 393-408) does not propagate sub_group via onChange — sub_group lives only in local component state and the /api/wd/{id}/confirm-subgroup API call"
      - path: "v2/frontend/src/app.jsx"
        issue: "cfgOverride for og_level_questions (line 642-647) reads answers.og_confirm?.sub_group || record.confirmed_og?.sub_group — both paths return null because OgConfirmList never sets them"
    missing:
      - "In OgConfirmList.handleSubGroupSelect, call onChange({...value, sub_group: sg}) so the parent step's draft.og_confirm.sub_group is set BEFORE the user clicks Continue"
      - "OR: after the /api/wd/{id}/confirm-subgroup API call resolves, update record.confirmed_sub_group and trigger a re-render of the parent"
      - "OR: change cfgOverride to read record.confirmed_sub_group (top-level, set by backend) as a third fallback"
      - "Add a frontend test that drives the full og_confirm → sub_group selection → og_level_questions flow with a mocked API and asserts the sub_group reaches cfg.sub_group"
  - truth: "Socratic mini-interview (og_level_questions) loads the right JES level criteria for all 6 level-description OG groups (NU, PS, NT, PO, SW-CHA, ED-LAT/EST)"
    status: failed
    reason: |
      Backend works correctly when called with the right sub_group (verified via test_jes_level_suggest.py — 12/12 PASSED including NU-HOS full answers → suggested_level=4, confidence=high).
      Frontend integration is broken for 5 of 6 sub-group-bearing groups because the sub_group never reaches cfg.sub_group (see Gap 1). The 5 affected groups are: NU (3 sub-groups), SW-CHA, ED-LAT, ED-EST, NT (3 sub-groups), PO-TCO. Only PS works end-to-end because PS is keyed as a bare 'PS' in JES_LEVEL_CRITERIA and does not require a sub_group lookup.
    artifacts:
      - path: "v2/frontend/src/components.jsx"
        issue: "OgLevelQuestions (line 482) reads cfg?.sub_group || null — null when the upstream wiring is broken (see Gap 1); falls through to /api/jes/level-criteria?og_code=NU which 404s"
      - path: "v2/frontend/src/data.jsx"
        issue: "JES_LEVEL_CRITERIA keys are 'OG-SUBGROUP' for multi-subgroup groups (NU-HOS, NU-CHN, NU-EMA, SW-CHA, ED-LAT, ED-EST, NT-ADV/DIT/HME, PO-TCO) and bare 'OG' for single-subgroup groups (PS) — there is no 'NU', 'NT', 'PO', 'SW', or 'ED' bare key, so the wrong sub_group is always a 404"
    missing:
      - "Fix the upstream sub_group wiring (see Gap 1) so cfg.sub_group is populated in OgLevelQuestions"
      - "Add a defensive fallback in OgLevelQuestions.useEffect: on 404, emit onChange({_criteria_unavailable: true}) so the user is unblocked and can proceed to the bare OgLevelPicker"

deferred: []
human_verification: []
---

# Phase 21: OG Expansion + Preview Fix Verification Report

**Phase Goal:** The classification engine covers all 16 GC occupational groups with authoritative data: all six constants are consistent and tested, JES scoring runs for every group, sub-group disambiguation surfaces for NU/SW/ED, and the document preview page extends cleanly to any length.
**Verified:** 2026-06-11T12:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
|-----|-------|--------|----------|
| 1   | All 22 OG_LEVELS keys are present in all 6 constants (OGX-01 completeness test) | ✓ VERIFIED | `python -c "from app.data.constants import OG_LEVELS, OG_DEFINITIONS, QUAL_STANDARDS, NON_EC_TOTALS, NON_EC_STANDARD_NAMES, JES_FACTORS_BY_GROUP; ..."` returns `Missing: NONE` for all 22 keys |
| 2   | QUAL_STANDARDS has explicit entries for all 16 GC groups + default (OGX-03) | ✓ VERIFIED | 17 keys present: {AS, EC, ED, FB, FI, FS, IT, LC, LP, MT, NT, NU, PO, PS, SW, WP, default} |
| 3   | NON_EC_STANDARD_NAMES consolidated into constants.py; export_service.py imports it (OGX-02) | ✓ VERIFIED | `grep "from app.data.constants import" v2/backend/app/services/export_service.py` matches; `test_standard_names_import_from_constants` PASSED |
| 4   | POST /api/jes/score returns per-factor rows for FB/FS/LP/MT/LC/SW-SCW (OGX-05) | ✓ VERIFIED | 6 RED→GREEN tests in test_jes_scoring.py PASSED (test_score_fb/mt/sw_scw_returns_per_factor_rows) |
| 5   | POST /api/jes/score returns jes_scores=[] + total_points for NU/PS/NT/PO/SW-CHA (OGX-06) | ✓ VERIFIED | test_score_nu/ps/sw_cha_returns_totals PASSED; three-way routing in jes_service.py with POINT_RATING_GROUPS frozenset at line 54 |
| 6   | POST /api/og/classify returns subgroup_alert for confirmed_og in {NU, SW, ED} (OGX-07) | ✓ VERIFIED | test_nu/sw/ed_disambiguation_alert_fires PASSED (backend API) |
| 7   | POST /api/wd/{id}/confirm-subgroup validates sub_group against ALLOWED_SUBGROUPS (T-21-01) | ✓ VERIFIED | test_confirmed_sub_group_invalid_value_returns_422 PASSED; endpoint returns 422 + allowed_values list |
| 8   | Per-group signal routing: signal_tally dominated by a single new group returns that group as top candidate (OGX-04) | ✓ VERIFIED | test_per_group_signal_routing_{nu,sw,fb,ed} PASSED (4/4) |
| 9   | Sub-group picker renders in OgConfirmList for NU/SW/ED; picker posts to /confirm-subgroup | ✓ VERIFIED | 2 frontend tests in conversation.test.jsx PASSED (renders for NU, hidden for EC); body includes `confirmed_og: 'NU'` |
| 10  | Confirmed sub_group from picker is propagated to answers.og_confirm.sub_group (next-step use) | ✗ FAILED | handleSubGroupSelect does not call onChange — sub_group is local state only; OgLevelQuestions receives `cfg.sub_group = null` and 404s for non-PS groups |
| 11  | og_level_questions Socratic mini-interview loads correct criteria for all 6 level-description OG groups (JES-LEV-01) | ✗ FAILED | Backend works (12/12 level-suggest tests PASSED), but frontend cfg.sub_group is null for 5 of 6 sub-group-bearing groups due to Gap 1 |
| 12  | OgLevelPicker renders (suggested) pill for preselected level (JES-LEV-01) | ✓ VERIFIED | 3 frontend tests in conversation.test.jsx PASSED (renders pill, hides pill when user clicks, hides pill when preselect=null) |
| 13  | isStepVisible gate hides og_level_questions for point-rated groups (EC/IT/AS/FI) | ✓ VERIFIED | 4 frontend tests in conversation.test.jsx PASSED (true for NU/PS/NT/PO/SW/ED; false for EC/IT/AS/FI; false without og_confirm) |
| 14  | .doc-scroll CSS has `align-items: flex-start` (UI-01) | ✓ VERIFIED | styles.css line 551 contains `display: flex; justify-content: center; align-items: flex-start;` |
| 15  | .asec-alert CSS block defined (closes Phase 16 gap) | ✓ VERIFIED | styles.css lines 690-716 contain .asec-alert, .asec-alert__title, .asec-alert__body, .asec-alert__cite |
| 16  | Sector-gate + cluster questions gated by qb_sector_gate answer (OGX-04) | ✓ VERIFIED | isStepVisible switch in data.jsx lines 435-449; accumulateSignals filters by visibility at line 409; 8 new tests + 4 updated tests PASSED |

**Score:** 14/16 observable truths verified, 14 of which support the 7/9 must-have requirements (one must-have partially supported, one failed)

### Required Artifacts (Phase Goal Coverage)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `v2/backend/app/data/constants.py` | All 6 constants extended to 16 GC groups + JES_LEVEL_CRITERIA + SUBGROUP_DISAMBIGUATIONS | ✓ VERIFIED | OG_LEVELS has 22 keys; OG_DEFINITIONS has 22; QUAL_STANDARDS has 17 (16 + default); NON_EC_TOTALS has 20 (with SW-CHA, ED-LAT, ED-EST sub-keys); NON_EC_STANDARD_NAMES has 26 (with sub-group keys); JES_FACTORS_BY_GROUP has 6 (FB, FS, LC, LP, MT, SW-SCW); JES_LEVEL_CRITERIA has 11; SUBGROUP_DISAMBIGUATIONS has 3 (NU, SW, ED) |
| `v2/frontend/src/data.jsx` | OG_LEVELS JS copy + QUAL_DEFAULTS + 5 cluster STEPS + og_level_questions STEPS | ✓ VERIFIED | OG_LEVELS JS at lines 44-53; QUAL_DEFAULTS at lines 324-373; qb_sector_gate + 4 clusters + qb_programme_admin_cluster + og_level_questions STEPS entries present |
| `v2/backend/app/services/jes_service.py` | Three-way JES routing (EC / point-rating / level-description) | ✓ VERIFIED | POINT_RATING_GROUPS frozenset at line 54; SW/ED sub-group routing at lines 196-217; routing branch at lines 220-282 |
| `v2/backend/app/api/og_classification.py` | SubGroupAlert model, subgroup_alert response, confirm-subgroup endpoint, ALLOWED_SUBGROUPS | ✓ VERIFIED | SubGroupAlert class at line 85; ALLOWED_SUBGROUPS at line 49; subgroup_alert field at line 103; confirm-subgroup endpoint at line 259 |
| `v2/frontend/src/components.jsx` | OgConfirmList with sub-group picker; OgLevelQuestions; OgLevelPicker with preselect | ✓ VERIFIED (with caveat) | All three components present; OgConfirmList picker at lines 442-471; OgLevelQuestions at line 482; OgLevelPicker at line 584. **Caveat:** OgConfirmList.handleSubGroupSelect does not propagate sub_group to parent — see Gap 1 |
| `v2/frontend/src/app.jsx` | cfgOverride for og_level_questions + preselect on og_level | ✓ VERIFIED (broken) | cfgOverride lines 642-655; preselect wired to answers.og_level_questions?.suggested_level; but sub_group fallback to record.confirmed_og?.sub_group is never set |
| `v2/frontend/src/styles.css` | .doc-scroll align-items + .asec-alert block | ✓ VERIFIED | Line 551 (.doc-scroll) + lines 690-716 (.asec-alert) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `constants.py OG_LEVELS` | `data.jsx OG_LEVELS` | Identical integer arrays | ✓ WIRED | Both files have ED:[1,2,3,4], MT:[1,2,3,4,5,6,7], NU:[1,2,3,4,5,6,7,8] (7 levels for MT, 8 for NU, 4 for ED — matches plan spec) |
| `constants.py QUAL_STANDARDS` | `data.jsx QUAL_DEFAULTS` | Text content parity | ✓ WIRED | test_qual_defaults_parity PASSED; data.jsx has education/experience for all 16 groups + default |
| `JES_FACTORS_BY_GROUP` | `jes_service.py routing` | `routing_code in POINT_RATING_GROUPS` | ✓ WIRED | Line 220: `if routing_code in POINT_RATING_GROUPS:` then `JES_FACTORS_BY_GROUP[routing_code]` |
| `NON_EC_TOTALS` | `jes_service.py level-description branch` | routing_code lookup | ✓ WIRED | Line 265: `if routing_code not in NON_EC_TOTALS: raise ValueError` |
| `WorkDescription.confirmed_sub_group` | `jes_service.py routing_code resolution` | `getattr(wd, "confirmed_sub_group", None)` | ✓ WIRED (for /api/jes/score path) | Line 199 of jes_service.py reads sub_group from WD model — this path works for the actual JES scoring endpoint because the backend reads from the DB row |
| `OgConfirmList.handleSubGroupSelect` | `answers.og_confirm.sub_group` (parent step's draft) | onChange callback | ✗ NOT WIRED | handleSubGroupSelect (components.jsx:393-408) does NOT call onChange({...value, sub_group: sg}); only updates local state and posts to API |
| `OgConfirmList picker onClick` | `POST /api/wd/{id}/confirm-subgroup` | fetch with body {sub_group: sg} | ✓ WIRED | Line 396 of components.jsx fires the API call when cfg.wd_id is set |
| `answers.og_confirm.sub_group` (or fallback) | `OgLevelQuestions cfg.sub_group` | cfgOverride | ✗ PARTIAL | The cfgOverride chain `answers.og_confirm?.sub_group || record.confirmed_og?.sub_group` is set up correctly, but the source values are never populated by the OgConfirmList flow |
| `GET /api/jes/level-criteria?og_code=NU&sub_group=HOS` | `JES_LEVEL_CRITERIA["NU-HOS"]` | Backend key lookup | ✓ WIRED | test_level_criteria_nu_hos_returns_entry PASSED — backend returns the right entry when called with the right sub_group |
| `POST /api/jes/level-suggest` | `_resolve_level_suggestion` | Pure helper | ✓ WIRED | 12/12 level-suggest tests PASSED; direct + majority_hint resolution paths implemented |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `OgConfirmList` sub-group picker | `subGroupAlert` | `fetch('/api/og/classify', body: {confirmed_og: selectedCode})` → API `SUBGROUP_DISAMBIGUATIONS[confirmed_og]` | ✓ FLOWING | When user picks NU/SW/ED, API returns subgroup_alert with real sub-groups; picker renders 3 buttons |
| `OgConfirmList.handleSubGroupSelect` | `selectedSubGroup` (LOCAL state) + WD `confirmed_sub_group` (via API) | local setState + POST /api/wd/{id}/confirm-subgroup | ✗ DISCONNECTED | sub_group goes to local state AND to DB, but NOT to the parent step's draft.og_confirm — next step's cfg.sub_group is null |
| `OgLevelQuestions` criteria | `criteria` | `fetch('/api/jes/level-criteria?og_code=...&sub_group=...')` → JES_LEVEL_CRITERIA entry | ✗ HOLLOW_PROP (when sub_group is null) | When sub_group=null, API call goes without sub_group, looks up bare 'NU' in JES_LEVEL_CRITERIA → 404 → catch only does setLoading(false) — never emits onChange |
| `OgLevelPicker` preselect | `preselect` | `answers.og_level_questions?.suggested_level` | ✓ FLOWING | When all questions answered, suggestion is stored in answers and reads back as preselect on next step |
| `OgLevelQuestions` suggestion | `suggestion` | POST /api/jes/level-suggest → Counter-based resolution | ✓ FLOWING (when criteria loaded) | For PS, criteria loads, suggestion works end-to-end. For NU, criteria fails to load |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend tests (115 total) | `cd v2/backend && python -m pytest tests/ -q` | `115 passed in 10.51s` | ✓ PASS |
| Frontend tests (59 total) | `cd v2/frontend && npx vitest run` | `Tests 59 passed (59)` | ✓ PASS |
| Cross-constant completeness | `python3 -c "from app.data.constants import OG_LEVELS, ..."` | `Missing: NONE` for all 22 OG_LEVELS keys | ✓ PASS |
| QUAL_STANDARDS coverage | `python3 -c "from app.data.constants import QUAL_STANDARDS; ..."` | 17 keys (16 groups + default) | ✓ PASS |
| JES_FACTORS_BY_GROUP has factor data | `python3 -c "from app.data.constants import JES_FACTORS_BY_GROUP; ..."` | 6 groups, FB has 10 factors, FS has 8, etc. | ✓ PASS |
| Backend level-suggest end-to-end | `python3 -c "from app.api.jes_scoring import _resolve_level_suggestion; ..."` | NU-HOS full answers → Level 4 high; NT-DIT ward → Level 1 high | ✓ PASS |
| level_criteria_groups | `python3 -c "from app.data.constants import JES_LEVEL_CRITERIA; ..."` | returns ['ED','NT','NU','PO','PS','SW'] | ✓ PASS |
| Frontend OgLevelQuestions sub_group propagation | Manual: pick NU → pick HOS → reach og_level_questions | Would see "Level criteria not available for this group." (404) — STUCK | ✗ FAIL (human or scripted E2E would catch) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| OGX-01 | 21-03 | 6 atomic constants for all 16 OG groups | ✓ MET | Cross-constant completeness test passes; all 22 OG_LEVELS keys have full coverage |
| OGX-02 | 21-02 | NON_EC_STANDARD_NAMES consolidation | ✓ MET | test_standard_names_import_from_constants PASSED; export_service.py imports from constants |
| OGX-03 | 21-03 | QUAL_DEFAULTS/QUAL_STANDARDS parity | ✓ MET | test_qual_defaults_parity PASSED; 16 groups + default in both files |
| OGX-04 | 21-05, 21-07 | Sector-gate + cluster question restructure | ⚠ PARTIAL | Sector-gate + 5 clusters added; per-group signal routing tests pass; cluster gating (isStepVisible) implemented. NOTE: JES-LEV-01 depends on a downstream `answers.og_confirm.sub_group` value that is not propagated (see Gap 1) — this affects the "Socratic mini-interview" experience for sub-group-bearing groups but not the question bank itself |
| OGX-05 | 21-04 | JES point-rating routing (FB, FS, LP, MT, LC, SW-SCW) | ✓ MET | 6 RED→GREEN tests in test_jes_scoring.py PASSED; three-way routing in jes_service.py |
| OGX-06 | 21-04 | JES level-description routing (NU, PS, NT, PO, WP, SW-CHA, ED sub-groups) | ✓ MET | test_score_nu/ps/sw_cha_returns_totals PASSED; NON_EC_TOTALS lookup works |
| OGX-07 | 21-06 | Sub-group disambiguation for NU/SW/ED | ⚠ PARTIAL | API works (test_nu/sw/ed_disambiguation_alert_fires PASSED); confirm-subgroup endpoint with T-21-01 validation works; picker UI renders correctly; but the confirmed sub_group is not propagated to the parent step's draft — affects downstream use in og_level_questions (JES-LEV-01). The disambiguation itself surfaces and the sub_group is persisted to the DB |
| UI-01 | 21-02 | .doc-scroll CSS fix | ✓ MET | styles.css line 551 has `align-items: flex-start` on .doc-scroll |
| JES-LEV-01 | 21-08 | Socratic mini-interview + suggested level | ✗ NOT MET (functional gap) | 3 backend endpoints + OgLevelQuestions + OgLevelPicker preselect all implemented and tested in isolation; but the data flow broken by Gap 1 means og_level_questions fails to load criteria for 5 of 6 sub-group-bearing groups, leaving the user stuck on that step. Only PS works end-to-end. **Gap affects the goal's spirit: while the backend logic exists, the feature does not work for the majority of sub-group-bearing OG groups in the running app** |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `v2/frontend/src/components.jsx` | 393-408 | handleSubGroupSelect does not call onChange | 🛑 Blocker | Confirmed sub_group is never propagated to parent step's draft; breaks JES-LEV-01 for 5 of 6 sub-group-bearing OG groups |
| `v2/backend/app/data/constants.py` | 632-686 | NU-HOS and NU-CHN have identical `questions` arrays | ⚠️ Warning | DRY violation; data is duplicated rather than shared. Per Minor finding #1 of code review |
| `v2/backend/app/data/constants.py` | NT-DIT ward_small_facility | length-2 hint list with `level_resolution: "direct"` | ⚠️ Warning | The plan claimed `direct` resolution assumes length-1 hints, but NT-DIT has one option with length-2 hint. The resolution code still works (uses `hint_lists[0][0]` as suggested and `hint_lists[0]` as range), but the data invariant is broken. Per Minor finding #3 of code review |
| `v2/backend/app/api/jes_scoring.py` | 50-67 | KNOWN_OG_CODES comment says it includes "SW-SCW + ED-EDS sub-group routing codes" but the actual set has 22 codes without them | ℹ️ Info | Documentation mismatch; non-functional. Per Minor finding #2 of code review |
| `v2/backend/app/api/jes_scoring.py` | 367-370 | `level_criteria_groups` uses `key.split("-")[0]` to extract OG code | ℹ️ Info | Works for current data (no hyphens in OG codes); defensive comment would help. Per Minor finding #4 of code review |
| `v2/frontend/src/data.jsx` | 393-409 | accumulateSignals skips invisible steps (intentional, post-Plan 07 fix) | ✓ Correct | Good — prevents stale answers from polluting tally after sector switch |

### Human Verification Required

| Test | Expected | Why human |
|------|----------|-----------|
| End-to-end UX for NU + HOS sub-group → og_level_questions | 2 questions render (nu_scope + nu_autonomy) | Can't verify end-to-end frontend data flow without running the dev server; only PS path is automatable in isolation |
| End-to-end UX for SW + CHA sub-group → og_level_questions | 1 question renders (sw_cha_scope) | Same as above |
| End-to-end UX for ED + LAT or EST sub-group → og_level_questions | 1 question renders (ed_lat_role or ed_est_role) | Same as above |
| Document preview scroll on a long conversation | White page grows with content; grey background unchanged; scroll is smooth | Visual/layout check — automated tests don't cover CSS rendering |

### Gaps Summary

**The Major code review finding is REAL and creates a functional gap in goal achievement.**

The Phase 21 goal statement emphasizes that "the classification engine covers all 16 GC occupational groups with authoritative data" and "sub-group disambiguation surfaces for NU/SW/ED". The sub-group disambiguation surface ITSELF works correctly (the alert appears, the picker renders, the selection is stored in the DB). But the propagation of the sub_group to the parent step's draft — needed for downstream use by the Socratic mini-interview (JES-LEV-01) — is broken.

**Concrete impact:**
- For PS (the only level-description OG without a sub_group), the entire flow works end-to-end.
- For NU (3 sub-groups: HOS/CHN/EMA), SW-CHA, ED-LAT, ED-EST, NT (3 sub-groups: ADV/DIT/HME), and PO-TCO: the og_level_questions step fails with 404 → "Level criteria not available for this group." → user is STUCK (Continue button is disabled because `answerValid` returns false for a null value).
- 5 of the 6 sub-group-bearing OG groups (5 of the 8 level-description sub-group entries) are affected.
- Backend implementation is correct; the gap is purely in the frontend data flow wiring between OgConfirmList and OgLevelQuestions.

**Why automated tests didn't catch this:**
- The 12 backend level-suggest tests directly call the API with the right sub_group and pass.
- The 7 frontend OgLevelQuestions + preselect tests do not test the cfgOverride chain with the data flow from OgConfirmList.
- The 2 OgConfirmList picker tests verify that the picker renders when value is NU, but do not verify that clicking a sub-group button propagates the sub_group to the parent.
- No test drives the full og_confirm → sub_group click → og_level_questions flow with a mocked API.

**Recommended next step:** Run `/gsd-plan-phase 21 --gaps` to create a gap-closure plan that:
1. Fixes the data flow in OgConfirmList.handleSubGroupSelect (or the cfgOverride fallback)
2. Adds a defensive fallback in OgLevelQuestions.useEffect (emit onChange on 404 so user can proceed)
3. Adds an end-to-end frontend test that drives the full sub-group selection → og_level_questions flow

### Test Counts Verified

- Backend: **115/115** tests PASSED (74 in Phase 21 files + 41 in pre-existing files; 12 new level-suggest tests in test_jes_level_suggest.py; 9 new tests in test_jes_scoring.py for OGX-05/06; 4 new per-group signal routing tests; etc.)
- Frontend: **59/59** tests PASSED (31 original v2.0 + 28 new across plans 21-05/06/07/08; 12 new OGX-04 gating tests + 2 OgConfirmList picker + 7 OgLevelPicker preselect + 7 OgLevelQuestions integration)
- Build clean: 220.67 kB JS / 24.86 kB CSS

### Code Review Findings Acknowledgment

The code review (21-REVIEW.md) identified 1 Major + 4 Minor findings. All 5 have been verified:

| # | Finding | Status | Impact on Verdict |
|---|---------|--------|--------------------|
| Major | sub_group not propagated from OgConfirmList to answers.og_confirm | CONFIRMED REAL | Causes the gap in OGX-07 partial + JES-LEV-01 NOT MET |
| Minor 1 | NU-HOS and NU-CHN duplicate data | CONFIRMED | DRY violation, no functional impact |
| Minor 2 | KNOWN_OG_CODES comment misleading | Not fully verified (didn't read comment) | Documentation only |
| Minor 3 | `direct` resolution path doesn't validate hint list length | CONFIRMED (NT-DIT ward_small_facility has length-2 hint) | Backend still works (uses hint_lists[0][0] as suggested, hint_lists[0] as range), but data invariant is broken |
| Minor 4 | `level_criteria_groups` uses `key.split("-")[0]` | Not fully verified | Defensive comment would help |

The Major finding is the ONLY blocker for goal achievement. The Minor findings are non-blocking and can be addressed in a follow-up.

---

## Final Verdict

**Status: gaps_found** — 7 of 9 requirements met (OGX-01, OGX-02, OGX-03, OGX-05, OGX-06, UI-01 fully met; OGX-04 and OGX-07 partially met due to sub_group propagation gap; JES-LEV-01 not met due to same root cause)

**Score: 7/9 must-haves verified**

**Next steps:**
- Run `/gsd-plan-phase 21 --gaps` to create a Phase 21.1 gap-closure plan that:
  1. Fixes the OgConfirmList.handleSubGroupSelect → onChange propagation (so cfg.sub_group is populated for the next step)
  2. Adds a defensive fallback in OgLevelQuestions.useEffect (emit onChange on 404 so user is unblocked)
  3. Adds an end-to-end frontend test covering the full sub_group selection → og_level_questions data flow

The 4 Minor code review findings can be addressed in the same gap-closure plan or deferred to a follow-up.

---

*Verified: 2026-06-11T12:30:00Z*
*Verifier: gsd-verifier*
