---
phase: 21-og-expansion-preview-fix
verified: 2026-06-11T18:10:00Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
overrides: []
re_verification:
  previous_status: gaps_found
  previous_score: 7/9
  gaps_closed:
    - "Confirmed sub_group from OgConfirmList propagated to answers.og_confirm.sub_group via onChange (Gap 1)"
    - "Socratic mini-interview (og_level_questions) unblocked for all 6 level-description OG groups via two surgical fixes + regression test (Gap 2 + Gap 3)"
  gaps_remaining: []
  regressions: []
gaps: []
deferred: []
human_verification:
  - test: "End-to-end UX for NU + HOS sub-group → og_level_questions"
    expected: "2 questions render (nu_scope + nu_autonomy); after answering, suggested level appears as preselected pill on the og_level step"
    why_human: "Cannot verify end-to-end frontend data flow without running the dev server"
  - test: "End-to-end UX for SW + CHA sub-group → og_level_questions"
    expected: "1 question renders (sw_cha_scope); suggestion propagates to og_level preselect"
    why_human: "Same as above"
  - test: "End-to-end UX for ED + LAT or EST sub-group → og_level_questions"
    expected: "1 question renders (ed_lat_role or ed_est_role); suggestion propagates to og_level preselect"
    why_human: "Same as above"
  - test: "Document preview scroll on a long conversation"
    expected: "White page grows with content; grey background unchanged; scroll is smooth"
    why_human: "Visual/layout check — automated tests do not cover CSS rendering"
---

# Phase 21: OG Expansion + Preview Fix Verification Report

**Phase Goal:** The classification engine covers all 16 GC occupational groups with authoritative data: all six constants are consistent and tested, JES scoring runs for every group, sub-group disambiguation surfaces for NU/SW/ED, and the document preview page extends cleanly to any length.
**Verified:** 2026-06-11T18:10:00Z
**Status:** passed (all automated gaps closed; human verification items are UX/visual only)
**Re-verification:** Yes — after gap closure (Plan 21-09)

---

## Gap-Closure Summary

The two blocking gaps from the initial verification (2026-06-11T12:30:00Z) were both addressed by Plan 21-09 with three surgical changes to `v2/frontend/src/components.jsx` and `v2/frontend/src/conversation.test.jsx`:

| Gap | Fix | Commit |
|-----|-----|--------|
| Gap 1: `handleSubGroupSelect` did not call `onChange` — `sub_group` lost after picker click | Added `onChange({ ...value, sub_group: sg })` as first statement in `handleSubGroupSelect` (components.jsx:394) | efdb4f3 |
| Gap 2: `OgLevelQuestions.useEffect` catch block did not unblock user on 404 | Replaced bare `.catch(() => { setLoading(false); })` with handler that also emits `onChange({ _criteria_unavailable: true })` (components.jsx:505) | 6ae3d28 |
| Gap 3: No test covering sub_group propagation via onChange | New `describe` block in conversation.test.jsx (line 725): renders OgConfirmList with NU, clicks HOS button, asserts `onChange` called with `{ og_code: 'NU', sub_group: 'HOS' }` | a3537b9 |

---

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
|-----|-------|--------|----------|
| 1   | All 22 OG_LEVELS keys are present in all 6 constants (OGX-01 completeness test) | ✓ VERIFIED | `python3 -c "from app.data.constants import ..."` → `Missing: NONE`, `OG_LEVELS keys: 22` |
| 2   | QUAL_STANDARDS has explicit entries for all 16 GC groups + default (OGX-03) | ✓ VERIFIED | 17 keys present: {AS, EC, ED, FB, FI, FS, IT, LC, LP, MT, NT, NU, PO, PS, SW, WP, default} |
| 3   | NON_EC_STANDARD_NAMES consolidated into constants.py; export_service.py imports it (OGX-02) | ✓ VERIFIED | `test_standard_names_import_from_constants` PASSED (115/115) |
| 4   | POST /api/jes/score returns per-factor rows for FB/FS/LP/MT/LC/SW-SCW (OGX-05) | ✓ VERIFIED | 6 tests in test_jes_scoring.py PASSED |
| 5   | POST /api/jes/score returns jes_scores=[] + total_points for NU/PS/NT/PO/SW-CHA (OGX-06) | ✓ VERIFIED | `test_score_nu/ps/sw_cha_returns_totals` PASSED; three-way routing in jes_service.py |
| 6   | POST /api/og/classify returns subgroup_alert for confirmed_og in {NU, SW, ED} (OGX-07) | ✓ VERIFIED | `test_nu/sw/ed_disambiguation_alert_fires` PASSED (backend API) |
| 7   | POST /api/wd/{id}/confirm-subgroup validates sub_group against ALLOWED_SUBGROUPS (T-21-01) | ✓ VERIFIED | `test_confirmed_sub_group_invalid_value_returns_422` PASSED |
| 8   | Per-group signal routing: signal_tally dominated by a single new group returns that group as top candidate (OGX-04) | ✓ VERIFIED | `test_per_group_signal_routing_{nu,sw,fb,ed}` PASSED (4/4) |
| 9   | Sub-group picker renders in OgConfirmList for NU/SW/ED; picker posts to /confirm-subgroup | ✓ VERIFIED | 2 frontend tests PASSED (renders for NU, hidden for EC) |
| 10  | Confirmed sub_group from picker propagated to answers.og_confirm.sub_group (next-step use) | ✓ VERIFIED (FIXED) | `onChange({ ...value, sub_group: sg })` at components.jsx:394; regression test "calls onChange with sub_group when a sub-group picker button is clicked" PASSED (conversation.test.jsx:725); full data-flow chain confirmed: onChange → answers.og_confirm.sub_group → cfgOverride (app.jsx:646) → cfg.sub_group (components.jsx:485) → API URL (components.jsx:496) |
| 11  | og_level_questions Socratic mini-interview loads correct criteria for all 6 level-description OG groups (JES-LEV-01) | ✓ VERIFIED (FIXED) | Gap 1 fix populates cfg.sub_group so the API call includes the sub_group parameter; Gap 2 fix (`onChange({ _criteria_unavailable: true })` at components.jsx:505) unblocks user if fetch still fails — answerValid returns truthy, Continue re-enabled; 12/12 backend level-suggest tests PASSED |
| 12  | OgLevelPicker renders (suggested) pill for preselected level (JES-LEV-01) | ✓ VERIFIED | 3 frontend tests PASSED (renders pill, hides when user clicks, hides when preselect=null) |
| 13  | isStepVisible gate hides og_level_questions for point-rated groups (EC/IT/AS/FI) | ✓ VERIFIED | 4 frontend tests PASSED |
| 14  | .doc-scroll CSS has `align-items: flex-start` (UI-01) | ✓ VERIFIED | styles.css line 551: `display: flex; justify-content: center; align-items: flex-start;` |
| 15  | .asec-alert CSS block defined (closes Phase 16 gap) | ✓ VERIFIED | styles.css lines 690-716 present |
| 16  | Sector-gate + cluster questions gated by qb_sector_gate answer (OGX-04) | ✓ VERIFIED | isStepVisible switch in data.jsx; 8 new + 4 updated tests PASSED |

**Score:** 16/16 observable truths verified

### Deferred Items

None.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `v2/backend/app/data/constants.py` | All 6 constants for 16 OG groups + JES_LEVEL_CRITERIA + SUBGROUP_DISAMBIGUATIONS | ✓ VERIFIED | 22 OG_LEVELS keys; all constants complete (cross-constant completeness test PASSED) |
| `v2/frontend/src/data.jsx` | OG_LEVELS JS copy + QUAL_DEFAULTS + 5 cluster STEPS + og_level_questions STEPS | ✓ VERIFIED | All present; isStepVisible gate implemented |
| `v2/backend/app/services/jes_service.py` | Three-way JES routing (EC / point-rating / level-description) | ✓ VERIFIED | POINT_RATING_GROUPS frozenset; SW/ED sub-group routing; routing branch at lines 220-282 |
| `v2/backend/app/api/og_classification.py` | SubGroupAlert model, subgroup_alert response, confirm-subgroup endpoint, ALLOWED_SUBGROUPS | ✓ VERIFIED | All present; 422 on invalid sub_group confirmed |
| `v2/frontend/src/components.jsx` | OgConfirmList with sub-group picker; OgLevelQuestions; OgLevelPicker; Gap 1 + Gap 2 fixes | ✓ VERIFIED | handleSubGroupSelect calls onChange at line 394; OgLevelQuestions catch emits sentinel at line 505 |
| `v2/frontend/src/app.jsx` | cfgOverride for og_level_questions + preselect on og_level | ✓ VERIFIED | cfgOverride lines 642-655; `sub_group: answers.og_confirm?.sub_group || record.confirmed_og?.sub_group || null` (line 646) now receives the sub_group from the fixed onChange |
| `v2/frontend/src/styles.css` | .doc-scroll align-items + .asec-alert block | ✓ VERIFIED | Line 551 + lines 690-716 |
| `v2/frontend/src/conversation.test.jsx` | Regression test for sub_group propagation via onChange | ✓ VERIFIED | New describe block at line 725; test passes |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `OgConfirmList.handleSubGroupSelect` | `answers.og_confirm.sub_group` (parent step draft) | `onChange({ ...value, sub_group: sg })` | ✓ WIRED (FIXED) | components.jsx:394 — onChange fires synchronously as FIRST statement, before setSelectedSubGroup and API call |
| `answers.og_confirm.sub_group` | `cfg.sub_group` in OgLevelQuestions | cfgOverride (app.jsx:646) | ✓ WIRED | `sub_group: answers.og_confirm?.sub_group || record.confirmed_og?.sub_group || null` — now populated by the fixed onChange |
| `cfg.sub_group` | `/api/jes/level-criteria?og_code=NU&sub_group=HOS` | OgLevelQuestions useEffect (components.jsx:485,496) | ✓ WIRED | `const subGroup = cfg?.sub_group || null;` then URL conditional adds `&sub_group=${subGroup}` when non-null |
| `OgLevelQuestions.useEffect catch` | Parent step `answerValid = true` | `onChange({ _criteria_unavailable: true })` | ✓ WIRED (FIXED) | components.jsx:505 — sentinel unblocks Continue button even when level-criteria fetch fails |
| `OgConfirmList picker onClick` | `POST /api/wd/{id}/confirm-subgroup` | fetch with body {sub_group: sg} | ✓ WIRED | Still fires; now AFTER onChange call — API call validates and persists to DB |
| `JES_FACTORS_BY_GROUP` | `jes_service.py point-rating branch` | `routing_code in POINT_RATING_GROUPS` | ✓ WIRED | Line 220: `if routing_code in POINT_RATING_GROUPS:` |
| `NON_EC_TOTALS` | `jes_service.py level-description branch` | routing_code lookup | ✓ WIRED | Line 265: raises ValueError if not in NON_EC_TOTALS |
| `GET /api/jes/level-criteria?og_code=NU&sub_group=HOS` | `JES_LEVEL_CRITERIA["NU-HOS"]` | Backend key lookup | ✓ WIRED | test_level_criteria_nu_hos_returns_entry PASSED |
| `POST /api/jes/level-suggest` | `_resolve_level_suggestion` | Pure helper | ✓ WIRED | 12/12 level-suggest tests PASSED |
| `constants.py OG_LEVELS` | `data.jsx OG_LEVELS` | Identical integer arrays | ✓ WIRED | Parity confirmed for ED, MT, NU, etc. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `OgConfirmList` sub-group picker | `subGroupAlert` | `fetch('/api/og/classify')` → API `SUBGROUP_DISAMBIGUATIONS[confirmed_og]` | ✓ Yes | Returns real sub-groups for NU/SW/ED |
| `OgConfirmList.handleSubGroupSelect` | `sub_group` in parent draft | `onChange({ ...value, sub_group: sg })` — synchronous | ✓ Yes | FIXED: sub_group now flows to `answers.og_confirm.sub_group` |
| `OgLevelQuestions` criteria | `criteria` | `fetch('/api/jes/level-criteria?og_code=NU&sub_group=HOS')` → `JES_LEVEL_CRITERIA["NU-HOS"]` | ✓ Yes | With sub_group populated, API call succeeds and returns real criteria |
| `OgLevelQuestions` catch path | `_criteria_unavailable` sentinel | `onChange({ _criteria_unavailable: true })` on fetch failure | ✓ Yes (fallback) | FIXED: user is unblocked even on fetch failure; can proceed to OgLevelPicker |
| `OgLevelPicker` preselect | `preselect` | `answers.og_level_questions?.suggested_level` | ✓ Flowing | When questions answered, suggestion propagates to preselect pill |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend tests (115 total) | `cd v2/backend && python -m pytest tests/ -q` | `115 passed in 10.04s` | ✓ PASS |
| Frontend tests (60 total) | `cd v2/frontend && npx vitest run` | `Tests 60 passed (60)` | ✓ PASS |
| Gap 1 fix present in components.jsx | `grep -n "onChange({ ...value, sub_group: sg })"` | Line 394 | ✓ PASS |
| Gap 2 fix present in components.jsx | `grep -n "_criteria_unavailable"` | Line 505 | ✓ PASS |
| Regression test present in conversation.test.jsx | `grep -n "calls onChange with sub_group"` | Line 725 | ✓ PASS |
| Cross-constant completeness | `python3 -c "from app.data.constants import ..."` | `Missing: NONE` for all 22 OG_LEVELS keys | ✓ PASS |
| sub_group data-flow chain | Code trace: onChange:394 → cfgOverride:646 → subGroup:485 → URL:496 | Complete chain confirmed | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| OGX-01 | 21-03 | 6 atomic constants for all 16 OG groups | ✓ MET | Cross-constant completeness test PASSED; 22 OG_LEVELS keys, all covered |
| OGX-02 | 21-02 | NON_EC_STANDARD_NAMES consolidation | ✓ MET | `test_standard_names_import_from_constants` PASSED; export_service.py imports from constants |
| OGX-03 | 21-03 | QUAL_DEFAULTS/QUAL_STANDARDS parity | ✓ MET | `test_qual_defaults_parity` PASSED; 16 groups + default in both files |
| OGX-04 | 21-05, 21-07 | Sector-gate + cluster question restructure | ✓ MET | Sector-gate + 5 clusters; per-group routing tests PASSED; isStepVisible implemented |
| OGX-05 | 21-04 | JES point-rating routing (FB, FS, LP, MT, LC, SW-SCW) | ✓ MET | 6 tests in test_jes_scoring.py PASSED; three-way routing in jes_service.py |
| OGX-06 | 21-04 | JES level-description routing (NU, PS, NT, PO, WP, SW-CHA, ED sub-groups) | ✓ MET | `test_score_nu/ps/sw_cha_returns_totals` PASSED; NON_EC_TOTALS lookup works |
| OGX-07 | 21-06, 21-09 | Sub-group disambiguation for NU/SW/ED + sub_group propagation | ✓ MET | API works; picker renders; sub_group now propagated to parent draft via onChange (Gap 1 fix); confirm-subgroup persists to DB |
| UI-01 | 21-02 | .doc-scroll CSS fix | ✓ MET | styles.css line 551: `align-items: flex-start` |
| JES-LEV-01 | 21-08, 21-09 | Socratic mini-interview + suggested level | ✓ MET | Backend: 12/12 level-suggest tests PASSED; Frontend: cfg.sub_group now populated (Gap 1 fix); catch block unblocks user on 404 (Gap 2 fix); regression test added (Gap 3 fix); 60/60 frontend tests PASSED |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `v2/backend/app/data/constants.py` | 632-686 | NU-HOS and NU-CHN have identical `questions` arrays | ⚠️ Warning | DRY violation; non-blocking. Carry-forward from initial verification Minor #1 |
| `v2/backend/app/data/constants.py` | NT-DIT ward_small_facility | length-2 hint list with `level_resolution: "direct"` | ⚠️ Warning | Data invariant inconsistency; backend still works. Carry-forward from initial verification Minor #3 |
| `v2/backend/app/api/jes_scoring.py` | 50-67 | KNOWN_OG_CODES comment misleading | ℹ️ Info | Documentation mismatch; non-functional. Carry-forward from Minor #2 |
| `v2/backend/app/api/jes_scoring.py` | 367-370 | `level_criteria_groups` uses `key.split("-")[0]` | ℹ️ Info | Works for current data; defensive comment would help. Carry-forward from Minor #4 |

No new anti-patterns introduced by Plan 21-09. All pre-existing minor findings are non-blocking.

### Human Verification Required

The following items require human testing with a running dev server:

#### 1. NU + HOS sub-group end-to-end flow

**Test:** In a running dev server, create a new WD, classify as NU, select HOS sub-group in OgConfirmList, proceed to og_level_questions.
**Expected:** 2 questions render (nu_scope + nu_autonomy); after answering, suggested level appears as preselected pill on the og_level step; Continue is enabled throughout.
**Why human:** Cannot verify end-to-end frontend data flow without running the dev server.

#### 2. SW + CHA sub-group end-to-end flow

**Test:** Same flow but select SW then CHA sub-group.
**Expected:** 1 question renders (sw_cha_scope); suggestion propagates to og_level preselect pill.
**Why human:** Same as above.

#### 3. ED + LAT or EST sub-group end-to-end flow

**Test:** Same flow but select ED then LAT or EST sub-group.
**Expected:** 1 question renders (ed_lat_role or ed_est_role); suggestion propagates.
**Why human:** Same as above.

#### 4. Document preview scroll on a long conversation

**Test:** Open a WD with a long conversation history; scroll the preview panel.
**Expected:** White .doc page grows with content; grey background unchanged; no overflow; smooth scroll.
**Why human:** Visual/layout check — automated tests do not cover CSS rendering.

### Gaps Summary

No automated gaps remain. All 3 gaps from the initial verification were closed by Plan 21-09:

- **Gap 1** (sub_group propagation): `onChange({ ...value, sub_group: sg })` added as first statement in `handleSubGroupSelect` — components.jsx:394.
- **Gap 2** (user stuck on og_level_questions 404): `onChange({ _criteria_unavailable: true })` added in the catch block — components.jsx:505.
- **Gap 3** (no regression test): New test at conversation.test.jsx:725 asserts sub_group: 'HOS' reaches the onChange call.

The 4 Minor code-review findings (DRY violation in NU constants, NT-DIT data invariant, two misleading comments in jes_scoring.py) remain as non-blocking warnings and can be addressed in a follow-up.

---

## Final Verdict

**Status: passed** — All 9 requirements met. 16/16 observable truths verified. 60/60 frontend tests passing. 115/115 backend tests passing. Remaining items are human UX verification (visual layout + end-to-end dev-server flows) that do not block the automated goal achievement verdict.

---

*Verified: 2026-06-11T18:10:00Z*
*Verifier: Claude (gsd-verifier)*
*Re-verification after Plan 21-09 gap closure*
