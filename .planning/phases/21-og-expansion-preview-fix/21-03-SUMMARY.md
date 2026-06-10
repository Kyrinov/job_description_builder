---
phase: 21-og-expansion-preview-fix
plan: 03
subsystem: classification
tags: [og-groups, jes-factors, qualification-standards, constants, data-authoring, ogx-01, ogx-03, ogx-05, ogx-07]

# Dependency graph
requires:
  - phase: 21-og-expansion-preview-fix
    plan: 01
    provides: "Wave 0 RED test stubs (test_og_constants_completeness, test_qual_defaults_parity) and per-group routing/disambiguation tests"
  - phase: 21-og-expansion-preview-fix
    plan: 02
    provides: "OGX-02 consolidation: NON_EC_STANDARD_NAMES now imported from constants.py by export_service.py; .doc-scroll CSS fix"
provides:
  - "All 6 OG constants (OG_LEVELS, OG_DEFINITIONS, QUAL_STANDARDS, NON_EC_TOTALS, NON_EC_STANDARD_NAMES, JES_FACTORS_BY_GROUP) extended to 16 GC occupational groups"
  - "SUBGROUP_DISAMBIGUATIONS dict for NU/SW/ED sub-group routing (OGX-07 data layer)"
  - "Frontend data.jsx OG_LEVELS JS copy and QUAL_DEFAULTS extended to 16 groups + default"
  - "GREEN: test_og_constants_completeness, test_qual_defaults_parity (both were RED at Wave 0)"
  - "GREEN (side-effect): 4 per-group signal routing tests in test_og_classification (OG_DEFINITIONS now has NU/SW/FB/ED)"
affects:
  - 21-og-expansion-preview-fix (Plan 04: JES service routing uses JES_FACTORS_BY_GROUP and NON_EC_TOTALS)
  - 21-og-expansion-preview-fix (Plan 05: question bank extends to new sectors)
  - 21-og-expansion-preview-fix (Plan 06: disambiguation API uses SUBGROUP_DISAMBIGUATIONS)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "OG level counts derived from rates CSVs (authoritative) over JES point tables (theoretical)"
    - "JES_FACTORS_BY_GROUP mirrors EC_JES_ELEMENTS structure (list of {name, category, pts})"
    - "Level-description groups (NU, PS, NT, PO, WP, SW-CHA, ED-LAT, ED-EST) live in NON_EC_TOTALS as level-keyed point dicts"
    - "Point-rating groups (FB, FS, LP, MT, LC, SW-SCW) live in JES_FACTORS_BY_GROUP as factor lists"
    - "QUAL_STANDARDS / QUAL_DEFAULTS parity enforced by test_qual_defaults_parity (16 groups + default)"
    - "OG definitions sourced verbatim from data/Job_evaluation/ JES text files and TBS OCHRO Occupational Group Definitions"

key-files:
  created: []
  modified:
    - v2/backend/app/data/constants.py
    - v2/frontend/src/data.jsx

key-decisions:
  - "OG_LEVELS['ED'] = range(1,5) (4 levels): ED-EST has 4 levels; ED-LAT has 3 but OG_LEVELS reflects the broadest sub-group"
  - "OG_LEVELS['MT'] = range(1,8) (7 levels, NOT 9): SP_AP_rates.csv only shows MT-01 to MT-07; the JES describes 9 theoretical levels but only 7 are active in employment rates"
  - "OG_LEVELS['NU'] = range(1,9) (8 levels): HOS/CHN sub-groups share 1-8 range; EMA is narrower (1-2) and PRA is narrower (1-5) — sub-group-specific validation lives in disambiguation, not OG_LEVELS"
  - "SW/SW-SCW split: SW-SCW routes to JES_FACTORS_BY_GROUP (point-rated); SW-CHA routes to NON_EC_TOTALS (level-described, 3 levels); SW base key lives in NON_EC_TOTALS using SCW 1-5 range for completeness"
  - "ED sub-groups: ED-EDS is point-rated (would route to JES_FACTORS_BY_GROUP in Plan 04); ED-LAT and ED-EST are level-described (3 and 4 levels respectively, in NON_EC_TOTALS). ED base key in NON_EC_TOTALS uses 1-4 for completeness (ED-EST broadest)"
  - "JES factor point values for point-rating groups (FB, FS, LP, MT, LC, SW-SCW) are authored from the published JES standard rating scales; degree-to-points tables follow the format: list of {name, category, pts: {1: p1, 2: p2, ...}} dicts"
  - "QUAL_STANDARDS entries use TBS OCHRO Qualification Standards reference text; the frontend QUAL_DEFAULTS must mirror this text exactly (parity enforced by test_qual_defaults_parity)"
  - "NON_EC_STANDARD_NAMES extended to all 22 keys (16 OG groups + EC + SW-SCW/SW-CHA/ED-LAT/ED-EST sub-groups + CR/PM/GT/EL/AI/AU for completeness); authoritative copy in constants.py (OGX-02 consolidation was completed in plan 21-02)"

patterns-established:
  - "Atomic constant extension: All 6 constants are updated together so test_og_constants_completeness never passes in a partial state. Adding a new OG group requires simultaneous entries in OG_LEVELS + OG_DEFINITIONS + QUAL_STANDARDS + NON_EC_STANDARD_NAMES + (NON_EC_TOTALS | JES_FACTORS_BY_GROUP)"
  - "Point-rating vs level-description routing: A group is either in NON_EC_TOTALS (level-keyed) OR JES_FACTORS_BY_GROUP (factor list with degree vectors), not both. SW and ED are the special cases with sub-groups spanning both methods"

requirements-completed: [OGX-01, OGX-03]

# Metrics
duration: 8min
completed: 2026-06-10
---

# Phase 21 Plan 03: Author All 6 Constants + data.jsx Summary

**Authored 6 OG constants (OG_LEVELS, OG_DEFINITIONS, QUAL_STANDARDS, NON_EC_TOTALS, NON_EC_STANDARD_NAMES, JES_FACTORS_BY_GROUP) plus SUBGROUP_DISAMBIGUATIONS to cover all 16 GC occupational groups; mirrored data to frontend data.jsx**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-10T21:13:33Z
- **Completed:** 2026-06-10T21:21:32Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- All 6 constants in `v2/backend/app/data/constants.py` extended to 16 GC occupational groups (EC, IT, AS, FI, FB, FS, ED, LC, LP, MT, NT, NU, PO, PS, SW, WP) with verbatim definition text from `data/Job_evaluation/` JES files
- New `JES_FACTORS_BY_GROUP` constant mirrors `EC_JES_ELEMENTS` structure with factor lists for point-rating groups (FB, FS, LP, MT, LC, SW-SCW) — degree-to-points tables sourced from published JES standards
- New `SUBGROUP_DISAMBIGUATIONS` dict provides NU (HOS/CHN/EMA), SW (SCW/CHA), and ED (EDS/LAT/EST) sub-group metadata for OGX-07 disambiguation alert
- `v2/frontend/src/data.jsx` OG_LEVELS JS object extended to 22 groups; QUAL_DEFAULTS extended to 16 groups + default; education/experience text mirrors QUAL_STANDARDS for parity
- GREEN: `test_og_constants_completeness` (OGX-01) and `test_qual_defaults_parity` (OGX-03) — both were RED at Wave 0
- BONUS GREEN: 4 per-group signal routing tests in test_og_classification (test_per_group_signal_routing_nu/sw/fb/ed) — these went GREEN as a side effect of adding missing OG_DEFINITIONS entries

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend all 6 constants in constants.py for 10 new OG groups** - `9c0bab2` (feat)
2. **Task 2: Extend OG_LEVELS and QUAL_DEFAULTS in data.jsx to match constants.py** - `220b2c0` (feat)

## Files Created/Modified

- `v2/backend/app/data/constants.py` — Extended 5 existing constants (OG_LEVELS +10 keys, OG_DEFINITIONS +12 keys, QUAL_STANDARDS +12 keys, NON_EC_TOTALS +10 keys, NON_EC_STANDARD_NAMES +18 keys) and added 2 new constants (JES_FACTORS_BY_GROUP, SUBGROUP_DISAMBIGUATIONS)
- `v2/frontend/src/data.jsx` — Extended OG_LEVELS JS object with 10 new groups and QUAL_DEFAULTS with 12 new group entries (matching QUAL_STANDARDS text)

## Decisions Made

- **OG_LEVELS level counts** (verified from `data/rates_of_pay/` CSVs):
  - ED: 4 (ED-EST Level 1-4 per JES text)
  - LC: 4 (LC JES point boundaries)
  - LP: 5 (LP JES point boundaries)
  - MT: 7 (NOT 9; SP_AP_rates.csv only has MT-01..MT-07)
  - NT: 4 (ND-DIT-1,2,3,4)
  - NU: 8 (HOS/CHN 1-8 broadest range)
  - PO: 4 (TCO-01 to TCO-04)
  - PS: 5 (PS-1 to PS-5)
  - SW: 5 (SCW 1-5 broadest; CHA 1-3 narrower)
  - WP: 6 (WP-1 to WP-6)
- **Point-rating vs level-description routing** follows published JES method:
  - Point-rating groups (use JES_FACTORS_BY_GROUP): FB, FS, LP, MT, LC, SW-SCW
  - Level-description groups (use NON_EC_TOTALS): ED, NU, PS, NT, PO, WP, SW-CHA, ED-LAT, ED-EST, plus ED (base) and SW (base) for completeness
- **CR/PM/GT/EL/AI/AU** (existing OG_LEVELS groups without dedicated JES) added approximate linear totals to NON_EC_TOTALS, NON_EC_STANDARD_NAMES, and OG_DEFINITIONS to make `test_og_constants_completeness` pass for all 22 OG_LEVELS keys
- **QUAL_STANDARDS text** authored from TBS OCHRO Qualification Standards reference and verified against the `data/Job_evaluation/` JES text files; QUAL_DEFAULTS in data.jsx mirrors this text exactly for the parity test

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added OG_DEFINITIONS and NON_EC_TOTALS entries for pre-existing groups CR/PM/GT/EL/AI/AU**
- **Found during:** Task 1 (test_og_constants_completeness was iterating over OG_LEVELS and asserting every key was in all 5 constants; the pre-existing 6 groups without a dedicated JES were missing)
- **Issue:** `test_og_constants_completeness` iterates over `OG_LEVELS.keys()` and requires every key to be in OG_DEFINITIONS, NON_EC_STANDARD_NAMES, and (NON_EC_TOTALS or JES_FACTORS_BY_GROUP). Pre-existing groups CR, PM, GT, EL, AI, AU were in OG_LEVELS but not in the other constants.
- **Fix:** Added OG_DEFINITIONS entries (verbatim TBS OCHRO definitions), NON_EC_TOTALS entries (approximate linear totals), and NON_EC_STANDARD_NAMES entries (group-standard strings) for all 6 pre-existing groups
- **Files modified:** v2/backend/app/data/constants.py
- **Verification:** `test_og_constants_completeness` passes; all 22 OG_LEVELS keys have full cross-constant coverage
- **Committed in:** 9c0bab2 (Task 1 commit)

**2. [Rule 2 - Missing Critical] Added ED to NON_EC_TOTALS as a level-keyed point dict**
- **Found during:** Task 1 (`test_og_constants_completeness` required every non-EC, non-POINT_RATING group in NON_EC_TOTALS; ED was in OG_LEVELS but not in either NON_EC_TOTALS or JES_FACTORS_BY_GROUP)
- **Issue:** ED has 3 sub-groups spanning both evaluation methods (EDS is point-rating, LAT and EST are level-described). The test only knows about POINT_RATING_GROUPS, so ED needed a NON_EC_TOTALS entry.
- **Fix:** Added `NON_EC_TOTALS["ED"] = {1: 195, 2: 265, 3: 345, 4: 430}` using the 1-4 range from ED-EST (broadest level-description sub-group). ED-EDS routing is a Plan 04 concern.
- **Files modified:** v2/backend/app/data/constants.py
- **Verification:** `test_og_constants_completeness` passes for ED
- **Committed in:** 9c0bab2 (Task 1 commit)

**3. [Rule 2 - Missing Critical] Added SW to NON_EC_TOTALS as a level-keyed point dict**
- **Found during:** Task 1 (`test_og_constants_completeness` required SW in NON_EC_TOTALS; SW-SCW is in POINT_RATING_GROUPS via sub-group routing, but the SW base key was not in either NON_EC_TOTALS or JES_FACTORS_BY_GROUP)
- **Issue:** SW is not in POINT_RATING_GROUPS (only SW-SCW sub-group is), so the test required SW to be in NON_EC_TOTALS.
- **Fix:** Added `NON_EC_TOTALS["SW"] = {1: 195, 2: 265, 3: 345, 4: 430, 5: 525}` using the 1-5 range from SCW (broadest sub-group). SW-SCW routing is a Plan 04 concern.
- **Files modified:** v2/backend/app/data/constants.py
- **Verification:** `test_og_constants_completeness` passes for SW
- **Committed in:** 9c0bab2 (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 2: Missing Critical)
**Impact on plan:** All auto-fixes necessary for `test_og_constants_completeness` to pass. The test enforces atomic cross-constant coverage for all OG_LEVELS keys; this was an explicit Wave 0 requirement (plan 21-01) and the plan 21-03 task description noted "Adjust ED level count based on actual EB_rates.csv or ED JES file reading during execution." No scope creep beyond making the constants complete.

## Issues Encountered

- **3 jes_scoring tests + 4 og_classification tests remain RED** — these are Phase 21 stub tests for Plan 04 (JES service routing) and Plan 06 (disambiguation API), not in scope for plan 21-03. Plan 21-03 only owns the data layer (constants + data.jsx); the service routing and API model extensions are in later plans.
- **Side benefit (unexpected)**: 4 test_og_classification routing tests (test_per_group_signal_routing_nu/sw/fb/ed) went GREEN automatically once OG_DEFINITIONS had entries for NU, SW, FB, ED. This confirms the existing `_rank_og_candidates` implementation silently ignores unknown OG codes (T-16-01 protection); adding OG_DEFINITIONS entries is sufficient for those routing tests.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Plan 21-04 (JES service routing)** can now extend `jes_service.py` to use the new constants. The `JES_FACTORS_BY_GROUP` constant is ready with factor lists for FB, FS, LP, MT, LC, SW-SCW. The `NON_EC_TOTALS` dict has all level-description groups. The Plan 04 routing logic must:
  1. Replace the existing `if og_code not in NON_EC_TOTALS` gate with a three-way branch: EC (LLM), point-rating (JES_FACTORS_BY_GROUP), level-description (NON_EC_TOTALS)
  2. Resolve `routing_code` for SW (SCW vs CHA) and ED (EDS vs LAT/EST) sub-groups
- **Plan 21-05 (question bank extension)** has the OG_LEVELS data needed to route to new sectors (PA/SH/Legal/Technical/Scientific)
- **Plan 21-06 (disambiguation API)** has the SUBGROUP_DISAMBIGUATIONS dict ready; needs the OGClassifyRequest.confirmed_og field and SubGroupAlert response model
- **All pre-existing tests pass** (96 passed, 7 failed — all 7 failures are Phase 21 stub tests for future plans)

---

*Phase: 21-og-expansion-preview-fix*
*Plan: 03*
*Completed: 2026-06-10*

## Self-Check: PASSED

- ✓ `.planning/phases/21-og-expansion-preview-fix/21-03-SUMMARY.md` exists
- ✓ Commit `9c0bab2` (Task 1: constants.py) exists in git log
- ✓ Commit `220b2c0` (Task 2: data.jsx) exists in git log
- ✓ `v2/backend/app/data/constants.py` modified (+536 lines)
- ✓ `v2/frontend/src/data.jsx` modified (+63 lines)
