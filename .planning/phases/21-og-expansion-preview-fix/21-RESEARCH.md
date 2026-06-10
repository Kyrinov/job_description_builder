# Phase 21: OG Expansion + Preview Fix — Research

**Researched:** 2026-06-10
**Domain:** GC occupational group constants, JES scoring extension, Socratic signal routing, CSS flexbox
**Confidence:** HIGH

---

## Summary

Phase 21 extends the classification engine from 4 focus groups (EC, IT, AS, FI) to all 16 GC occupational groups. The work is primarily a data authoring and constant-extension task: six constants in `constants.py` must be updated atomically, a dual-copy drift in `export_service.py` must be consolidated, a frontend-backend qualification parity test must be written before new group text is authored, the `QUESTION_BANK` must grow to route four new sector clusters (PA/SH/Legal/Technical/Scientific), per-factor JES scoring must be extended to five point-rating groups (FB, FS, LP, MT, LC) plus SW-SCW, and level-lookup totals must be authored for seven level-description groups (NU, PS, NT, PO, WP, SW-CHA, ED sub-groups). Sub-group disambiguation alerts are needed for NU (HOS/CHN/EMA), SW (SCW/CHA), and ED sub-groups. One CSS one-liner fixes the document preview overflow.

All JES standards exist as local text files under `data/Job_evaluation/`. All rates of pay CSVs are present under `data/rates_of_pay/`. No external API calls or environment changes are required. The entire phase is deterministic: no LLM in the classification main flow.

**Primary recommendation:** Begin with the UI-01 CSS fix (1 line), then tackle OGX-01/02/03 as a single atomic constants wave, then OGX-04 (question bank), then OGX-05/06 (JES scoring paths), then OGX-07 (disambiguation UI). Completeness tests drive each wave.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| OG_LEVELS / constants update | Backend (constants.py) | Frontend (data.jsx) | Backend is authoritative; frontend OG_LEVELS is a JS copy for offline level-picker rendering |
| JES point-rating scoring | Backend (jes_service.py) | — | All arithmetic is deterministic; no client-side JES calculation |
| Level-lookup totals (non-EC) | Backend (constants.py + jes_service.py) | — | NON_EC_TOTALS keyed lookup, same path as current FI/AS/IT |
| QUESTION_BANK sector routing | Backend (constants.py) | Frontend (data.jsx STEPS) | Backend QUESTION_BANK drives signal accumulation; frontend STEPS mirrors it for display |
| Sub-group disambiguation | Backend (og_classification.py) + Frontend (components.jsx OgConfirmList) | — | Backend fires alert in classify response; frontend renders it analogously to existing ASEC alert |
| QUAL_DEFAULTS/QUAL_STANDARDS | Backend (constants.py) + Frontend (data.jsx) | — | Both must be kept in parity; parity test is the enforcement mechanism |
| CSS preview fix | Frontend (styles.css) | — | Single CSS property change; no backend involvement |
| Completeness tests | Backend (tests/test_constants.py) | Frontend (vitest tests) | Backend completeness test covers 6-constant parity; frontend test covers QUAL_DEFAULTS parity |

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OGX-01 | All six constants updated atomically for 16 groups; completeness test asserts cross-constant key coverage | Level counts verified from rate CSVs; JES type verified from JES text files |
| OGX-02 | NON_EC_STANDARD_NAMES consolidated into constants.py; export_service.py imports from there | Dual-copy confirmed at export_service.py lines 50-55 vs constants.py lines 600-605 |
| OGX-03 | QUAL_DEFAULTS (frontend) / QUAL_STANDARDS (backend) parity test written as failing test before new group text | Both structures confirmed in data.jsx lines 293-314 and constants.py lines 507-535 |
| OGX-04 | QUESTION_BANK extended with sector-gate question and cluster-specific questions; accumulateSignals() tests | Existing 4-question bank covers EC/IT/AS/FI only; extension pattern confirmed |
| OGX-05 | Point-rating groups (FB, FS, LP, MT, LC, SW-SCW) get per-factor JES scoring via JES_FACTORS_BY_GROUP | Point-rating confirmed from JES text files; EC_JES_ELEMENTS extension pattern applies |
| OGX-06 | Level-description groups return jes_total_points from NON_EC_TOTALS lookup; jes_scores: [] | Existing FI/AS/IT path in jes_service.py lines 182-207 is the direct pattern |
| OGX-07 | NU/SW/ED sub-group disambiguation alert surfaced; confirmed sub-group stored on WorkDescription | ASEC_DISAMBIGUATION pattern in constants.py + OgConfirmList in components.jsx lines 321-338 |
| UI-01 | .doc-scroll gets align-items: flex-start; white .doc page grows to any length | Confirmed: styles.css line 549 has flex layout missing align-items |
</phase_requirements>

---

## Standard Stack

### Core (unchanged from v2.0 — all already installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python / FastAPI | 3.11 / 0.111+ | Backend API | Project stack |
| Pydantic v2 | 2.x | Model validation | Project stack |
| React 18 | 18.x | Frontend SPA | Project stack |
| Vitest | 2.x | Frontend unit tests | Project stack |
| pytest + pytest-asyncio | 8.x | Backend tests | Project stack |

No new packages required for Phase 21. All work is data authoring and extension of existing code patterns.

---

## Architecture Patterns

### System Architecture Diagram

```
[QUESTION_BANK answers]
        |
        v
[accumulateSignals()] ──> signal_tally (og_code -> count)
        |
        v
POST /api/og/classify
  ├── _rank_og_candidates()
  ├── OG_DEFINITIONS lookup
  ├── OG_LEVELS lookup
  ├── disambiguation check (ASEC / new NU-SW-ED)
  └── OGClassifyResponse { candidates, asec_alert | subgroup_alert }
        |
        v
[Frontend OgConfirmList] ──> confirmed_og + sub_group stored on WD
        |
        v
POST /api/jes/score
  ├── is_point_rating(og_code)?
  │     YES ──> loop JES_FACTORS_BY_GROUP[og_code] (same pattern as EC_JES_ELEMENTS)
  │     NO  ──> NON_EC_TOTALS[og_code][og_level] (level-keyed lookup)
  └── scorecard { is_ec, factors, total_points, standard_name }
        |
        v
[Frontend ClassBlock] renders per-factor rows OR single totals line
```

### Recommended Project Structure (additions for Phase 21)

```
v2/backend/app/data/
├── constants.py         # ← extend all 6 constants + new JES_FACTORS_BY_GROUP
v2/backend/app/api/
├── og_classification.py # ← add subgroup disambiguation logic (new alert types)
v2/backend/app/services/
├── jes_service.py       # ← extend non-EC path to route by is_point_rating()
├── export_service.py    # ← remove local NON_EC_STANDARD_NAMES, import from constants
v2/backend/tests/
├── test_constants.py    # ← add completeness test + QUAL parity test
├── test_og_classification.py  # ← add per-group integration tests
├── test_jes_scoring.py  # ← add per-group JES path tests
v2/frontend/src/
├── data.jsx             # ← extend OG_LEVELS, QUESTION_BANK STEPS, QUAL_DEFAULTS
├── styles.css           # ← add align-items: flex-start to .doc-scroll
v2/frontend/src/
├── components.jsx       # ← extend OgConfirmList for subgroup disambiguation alert
```

### Pattern 1: Atomic Constant Extension (OGX-01)

**What:** All six constants must be updated together so the completeness test never passes in a partial state.

**When to use:** Any time a new OG group is added.

**The six constants and their current state:**

```python
# Source: v2/backend/app/data/constants.py (verified by direct file inspection 2026-06-10)

# 1. OG_LEVELS — currently has 12 groups (EC, IT, AS, FI, CR, PM, GT, EL, FB, FS, AI, AU)
# Phase 21 adds: ED, LC, LP, MT, NT, NU, PO, PS, SW, WP
# Note: GT, EL, AI, AU are in OG_LEVELS but NOT in OG_DEFINITIONS — they're constants
# only; the 16-group target for Phase 21 covers the 12 new groups listed in the requirement

OG_LEVELS: dict[str, list[int]] = {
    # EXISTING (EC, IT, AS, FI, CR, PM, GT, EL, FB, FS, AI, AU)
    # TO ADD (verified from rates CSVs):
    "ED": list(range(1, 5)),   # ED-01 to ED-04 (EB_rates.csv: Levels 1-4)
    "LC": list(range(1, 5)),   # LC-01 to LC-04 (JES point boundaries: 4 levels)
    "LP": list(range(1, 6)),   # LP-01 to LP-05 (JES point boundaries: 5 levels)
    "MT": list(range(1, 8)),   # MT-01 to MT-07 (SP_AP_rates.csv: MT-01 to MT-07)
    "NT": list(range(1, 5)),   # NT-01 to NT-04 (NT JES: 4 level descriptions)
    "NU": list(range(1, 9)),   # NU-01 to NU-08 (SH_rates.csv: HOS/CHN 1-8)
    "PO": list(range(1, 5)),   # PO-01 to PO-04 (PO_rates.csv: TCO-01..04 + IMA series)
    "PS": list(range(1, 6)),   # PS-01 to PS-05 (SH_rates.csv: PS-1 to PS-5)
    "SW": list(range(1, 6)),   # SW-01 to SW-05 (SH_rates.csv: SCW 1-5, CHA 1-3)
    "WP": list(range(1, 7)),   # WP-01 to WP-06 (PA_rates.csv: WP-1 to WP-6)
    # NOTE: NU level count needs validation — NU uses sub-group codes (HOS/CHN levels 1-8,
    # EMA levels 1-2, PRA levels 1-5). OG_LEVELS[NU] should reflect the full level range
    # across sub-groups; use 1-8 as the HOS/CHN range is the broadest.
}

# 2. OG_DEFINITIONS — currently has EC, AS, IT, FI, CR, PM
# All 12 new groups need verbatim definition text from JES files in data/Job_evaluation/

# 3. QUAL_STANDARDS — currently has EC, AS, IT, FI, default
# All 12 new groups need education + experience + source text

# 4. NON_EC_TOTALS — currently has FI, IT, AS, EN
# NEW: all level-description groups (NU, PS, NT, PO, WP, SW-CHA, ED sub-groups)
# EXISTING point-rating groups (FB, FS, LP, MT, LC, SW-SCW) do NOT get NON_EC_TOTALS
# entries — they get per-factor scoring via JES_FACTORS_BY_GROUP instead

# 5. NON_EC_STANDARD_NAMES — currently has FI, IT, AS, EN
# NEW: all groups need their JES standard name string
# NOTE: consolidate from export_service.py (OGX-02) — see below

# 6. JES_FACTORS_BY_GROUP — DOES NOT EXIST YET; must be created
# Pattern mirrors EC_JES_ELEMENTS; keyed by OG code for point-rating groups
```

### Pattern 2: JES Service Routing (OGX-05/06)

**What:** The `score_jes_v2` non-EC path currently checks `og_code not in NON_EC_TOTALS`. Phase 21 adds a second non-EC path for point-rating groups that use `JES_FACTORS_BY_GROUP`.

**When to use:** Any group that is not EC.

```python
# Source: derived from v2/backend/app/services/jes_service.py existing pattern

POINT_RATING_GROUPS = frozenset({"FB", "FS", "LP", "MT", "LC", "SW-SCW"})
# "SW-SCW" uses the confirmed sub_group field — SW base code routes to SCW or CHA

async def score_jes_v2(wd_id, og_code, og_level, duties, db_path):
    # ...
    if og_code == "EC":
        # existing EC path — 9-factor LLM loop
        pass
    elif og_code in POINT_RATING_GROUPS or sub_group in POINT_RATING_GROUPS:
        # NEW: point-rating non-EC path — same structure as EC but no LLM
        # JES_FACTORS_BY_GROUP[og_code] provides factor definitions
        # degrees derived from benchmark level tables (no LLM — hardcoded degree->points)
        pass
    else:
        # existing level-lookup path (NON_EC_TOTALS)
        pass
```

**Important:** Point-rating groups (FB, FS, LP, MT, LC, SW-SCW) do NOT call the LLM — per the non-negotiable "Hardcoded JES tables over LLM scoring". Degrees for each factor must be authored from benchmark position descriptions in the JES text files.

### Pattern 3: Sub-Group Disambiguation Alert (OGX-07)

**What:** When a position is classified as NU, SW, or ED, the sub-group must be disambiguated before JES scoring can proceed. This is analogous to the existing ASEC alert.

**Existing pattern (ASEC):**

```python
# Source: v2/backend/app/api/og_classification.py lines 148-151 (verified 2026-06-10)
asec_alert = None
og_codes_in_top3 = {c.og_code for c in candidates}
if "AS" in og_codes_in_top3 and "EC" in og_codes_in_top3:
    asec_alert = ASECAlert(**ASEC_DISAMBIGUATION)
```

**New pattern (sub-group disambiguation):**

```python
# When confirmed OG is NU, SW, or ED, fire a sub-group alert unconditionally
# (not conditional on top-3 overlap — these groups always have sub-groups)
# The alert text lists sub-group options with their definitions.
# The confirmed sub_group is stored on WorkDescription (new field).
```

**Frontend pattern (existing ASEC alert in components.jsx):**

```jsx
// Source: v2/frontend/src/components.jsx lines 329-337 (verified 2026-06-10)
{alert && (
  <div className="asec-alert">
    <p className="asec-alert__title">...</p>
    <p className="asec-alert__body">{alert.disambiguation_text}</p>
    <span className="asec-alert__cite">{alert.citation}</span>
  </div>
)}
```

The sub-group disambiguation UI should reuse this component pattern, extending OgConfirmList or a new SubGroupPicker step to capture the sub-group selection.

### Pattern 4: QUAL_DEFAULTS / QUAL_STANDARDS Parity Test (OGX-03)

**What:** Write a failing pytest test that compares keys in frontend `QUAL_DEFAULTS` against `QUAL_STANDARDS` in backend constants. This test is written BEFORE any new group qualification text is authored.

**Existing state:**

```
Backend QUAL_STANDARDS: EC, AS, IT, FI, default
Frontend QUAL_DEFAULTS: EC, AS, IT, FI, default
```

**Test structure:**

```python
# tests/test_constants.py addition
def test_qual_defaults_parity():
    """OGX-03 — QUAL_STANDARDS (backend) must have an entry for every key
    in the frontend QUAL_DEFAULTS constant (16 groups + default at phase close)."""
    # The test imports QUAL_STANDARDS from constants.py;
    # the frontend QUAL_DEFAULTS keys are embedded in the test as a known set.
    # Initially FAILS (no new group entries yet) — this is the desired state at Wave 0.
    from app.data.constants import QUAL_STANDARDS
    EXPECTED_GROUPS = {"EC", "AS", "IT", "FI", "ED", "FB", "FS", "LC", "LP",
                        "MT", "NT", "NU", "PO", "PS", "SW", "WP", "default"}
    missing = EXPECTED_GROUPS - set(QUAL_STANDARDS.keys())
    assert not missing, f"QUAL_STANDARDS missing keys: {missing}"
```

### Pattern 5: CSS Preview Fix (UI-01)

**What:** `.doc-scroll` currently uses `display: flex; justify-content: center` without `align-items`. The default `align-items: stretch` causes the `.doc` element to stretch to fill the container height, then overflow at long document lengths.

**Root cause (verified in styles.css lines 548-552):**

```css
/* CURRENT — missing align-items */
.doc-scroll {
  flex: 1 1 auto; min-height: 0; overflow-y: auto;
  padding: 38px 34px 80px;
  display: flex; justify-content: center;
}

/* FIX — add align-items: flex-start */
.doc-scroll {
  flex: 1 1 auto; min-height: 0; overflow-y: auto;
  padding: 38px 34px 80px;
  display: flex; justify-content: center; align-items: flex-start;
}
```

`align-items: flex-start` makes the `.doc` element take its natural height (sized by content) rather than stretching to fill `.doc-scroll`. The scroll container then handles overflow naturally.

### Anti-Patterns to Avoid

- **Partial constant updates:** Never add a new OG code to OG_LEVELS without simultaneously adding it to OG_DEFINITIONS, QUAL_STANDARDS, NON_EC_TOTALS (if level-description) or JES_FACTORS_BY_GROUP (if point-rating), and NON_EC_STANDARD_NAMES. The completeness test will catch this but it creates a broken intermediate state.
- **LLM for new group JES scoring:** The non-negotiable says hardcoded JES tables. Point-rating groups must have authored degree-vector tables or benchmark-derived factor definitions, not LLM-generated values.
- **Copying NON_EC_STANDARD_NAMES from export_service.py:** The local copy in export_service.py must be deleted entirely after the import from constants.py is added (OGX-02). Leaving both would re-create the drift.
- **Sub-group in confirmed_og vs separate field:** The sub-group (NU-HOS, SW-SCW, ED-EDS) should be stored as a separate field (`confirmed_sub_group` or similar) on WorkDescription, not embedded in the og_code string. This maintains clean separation and avoids breaking OG_LEVELS lookups.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JES factor point lookup | Custom point interpolation | Hardcoded `pts` dict per factor in JES_FACTORS_BY_GROUP | Published TBS standards have exact integer values; interpolation would be wrong |
| QUAL text authoring | LLM generation | TBS Qualification Standards reference text from data/Job_evaluation/ files | Must be authoritative, traceable to TBS OCHRO source |
| OG definition text | LLM paraphrase | Verbatim text from data/Job_evaluation/ JES files | Definitions are legally precise; paraphrase introduces error |
| Disambiguation UI | New custom component | Extend existing OgConfirmList + asec-alert CSS pattern | Pattern already exists and is tested |
| Level range lookup | Derive from JES point tables | Authoritative level counts from data/rates_of_pay/ CSVs | Rates CSVs are the employment contract; JES point ranges may describe more levels than actually exist in employment |

---

## Runtime State Inventory

> Phase 21 is a data/code extension phase. No runtime state renaming or migration is involved.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no OG code renaming, no key changes to existing groups | None |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | v2/frontend/dist/ will be stale after data.jsx changes | `npm run build` in Wave 0 or final wave |

---

## Common Pitfalls

### Pitfall 1: MT Level Count Discrepancy
**What goes wrong:** The MT JES text file describes 9 point ranges (MT-1 through MT-9), but `SP_AP_rates.csv` only shows MT-01 through MT-07. Using 9 levels would include levels that have no employment rates.
**Why it happens:** JES standards sometimes define more theoretical levels than exist in the active pay schedule.
**How to avoid:** Always derive `OG_LEVELS` from the rates CSV, not the JES point table. `OG_LEVELS["MT"] = list(range(1, 8))` (7 levels). [VERIFIED: SP_AP_rates.csv direct inspection 2026-06-10]
**Warning signs:** If a level is referenced in OG_LEVELS but has no row in the rates CSV for that group, it's a phantom level.

### Pitfall 2: NU Sub-Group Level Count Confusion
**What goes wrong:** NU has multiple sub-groups (HOS, CHN, EMA, PRA) with different level ranges. HOS/CHN share levels 1-8; EMA has levels 1-2; PRA has levels 1-5. Storing a single flat `OG_LEVELS["NU"]` loses this nuance.
**Why it happens:** The rates CSV shows sub-group level codes, not a single NU-N series.
**How to avoid:** `OG_LEVELS["NU"]` should reflect the union of all sub-group levels using the HOS/CHN 1-8 range as the standard (broadest range). Sub-group-specific level validation belongs in the disambiguation step, not in OG_LEVELS. [VERIFIED: SH_rates.csv direct inspection 2026-06-10]

### Pitfall 3: SW Point-Rating vs Level-Description Split
**What goes wrong:** SW has two sub-groups with different JES methods: SCW (Social Welfare) uses point-rating; CHA (Chaplain) uses level descriptions. Treating all SW as either point-rating or level-description is wrong.
**Why it happens:** OGX-07 sub-group disambiguation is needed before JES routing is possible.
**How to avoid:** The jes_service routing must branch on `confirmed_sub_group` ("SCW" vs "CHA"), not on `og_code` alone. Only SW-SCW goes to JES_FACTORS_BY_GROUP; SW-CHA goes to NON_EC_TOTALS. [VERIFIED: SW JES text file direct inspection 2026-06-10]

### Pitfall 4: ED Sub-Group JES Method Split
**What goes wrong:** ED has three sub-groups: LAT (Language teaching, level descriptions), EST (Elementary/Secondary teaching, level descriptions), EDS (Education Services, point-rating). The `ED Education - Job Evaluation Standard 2017.txt` describes all three differently.
**Why it happens:** A single OG code covers multiple evaluation methods.
**How to avoid:** Same disambiguation pattern as SW — confirm sub-group before routing JES. EDS uses point-rating; LAT and EST use level descriptions. [VERIFIED: ED JES text file direct inspection 2026-06-10]

### Pitfall 5: QUAL_STANDARDS default Fallback Breaks Parity Test
**What goes wrong:** The parity test counts "default" as a required key in QUAL_STANDARDS. If the frontend `QUAL_DEFAULTS` uses "default" but the test enumerates group keys differently, the test will be mis-specified.
**Why it happens:** The parity test needs to compare group keys (EC, AS, etc.) + "default" key.
**How to avoid:** Define `EXPECTED_GROUPS` in the test explicitly as the set of all 16 groups plus "default", not derived programmatically from either constant.

### Pitfall 6: PO Sub-Group vs Level Ambiguity
**What goes wrong:** `PO_rates.csv` shows sub-group codes (PO-TCO-01 through PO-TCO-04, PO-IMA series). Mapping these to a flat PO-01 through PO-04 in OG_LEVELS is an approximation.
**Why it happens:** PO uses benchmark-based level descriptions with multiple sub-groups (TCO = Technical/Clerical Operations, IMA = Immigration).
**How to avoid:** Model PO similarly to NU — use 4 levels in OG_LEVELS (longest TCO range is 4), note the sub-group complexity in a comment. For Phase 21, OGX-07 does not require PO disambiguation — only NU, SW, and ED are called out. [VERIFIED: PO_rates.csv and PO JES text inspection 2026-06-10]

### Pitfall 7: QUESTION_BANK QUES-02 Constraint on New Options
**What goes wrong:** Adding new QUESTION_BANK options that reference OG codes in user-visible text (label or helper) fails the existing `test_no_og_codes_in_user_visible_text` test.
**Why it happens:** QUES-02 is enforced by test. The `option["label"]` key is checked, but in `data.jsx` the equivalent key is `"title"`.
**How to avoid:** In `constants.py` QUESTION_BANK, option labels use the `"label"` key. In `data.jsx`, options use `"title"`. Both must avoid OG codes. Signal routing (`og_candidates`) is hidden inside `signals`. The existing test only checks `opt["label"]` — the frontend uses `opt.title`. Both must comply. [VERIFIED: test_question_bank.py lines 57-67, data.jsx lines 369-403]

### Pitfall 8: export_service NON_EC_STANDARD_NAMES Drift (OGX-02)
**What goes wrong:** `export_service.py` has its own local copy of `NON_EC_STANDARD_NAMES` (lines 50-55) with different values than `constants.py` (e.g., "CT JES 2023" vs "FI / CT Job Evaluation Standard (2023)"). Adding 12 new groups to constants.py without also deleting the export_service copy recreates the drift immediately.
**Why it happens:** The local copy was created in Phase 20 before the constants.py consolidation requirement was formalized.
**How to avoid:** OGX-02 must: (1) add all 16 groups to `NON_EC_STANDARD_NAMES` in constants.py, (2) delete the local dict from export_service.py, (3) add the import. Do both changes in the same commit. [VERIFIED: export_service.py lines 46-55 direct inspection 2026-06-10]

---

## Code Examples

### Completeness test structure (OGX-01)

```python
# Source: derived from existing test_constants.py pattern (verified 2026-06-10)
def test_og_constants_completeness():
    """OGX-01 — every key in OG_LEVELS is present in all other 5 constants."""
    from app.data.constants import (
        OG_LEVELS, OG_DEFINITIONS, QUAL_STANDARDS,
        NON_EC_TOTALS, NON_EC_STANDARD_NAMES, JES_FACTORS_BY_GROUP
    )
    # POINT_RATING_GROUPS use JES_FACTORS_BY_GROUP, not NON_EC_TOTALS
    POINT_RATING_GROUPS = {"FB", "FS", "LP", "MT", "LC"}  # SW handled via sub-group
    
    for og_code in OG_LEVELS:
        assert og_code in OG_DEFINITIONS, f"{og_code} missing from OG_DEFINITIONS"
        assert og_code in QUAL_STANDARDS or "default" in QUAL_STANDARDS, \
            f"{og_code} missing from QUAL_STANDARDS"
        assert og_code in NON_EC_STANDARD_NAMES, \
            f"{og_code} missing from NON_EC_STANDARD_NAMES"
        if og_code in POINT_RATING_GROUPS:
            assert og_code in JES_FACTORS_BY_GROUP, \
                f"{og_code} missing from JES_FACTORS_BY_GROUP"
        elif og_code not in ("EC",):  # EC uses EC_JES_ELEMENTS
            assert og_code in NON_EC_TOTALS, \
                f"{og_code} missing from NON_EC_TOTALS"
```

### JES_FACTORS_BY_GROUP structure for a point-rating group

```python
# Source: ASSUMED based on EC_JES_ELEMENTS pattern in constants.py (verified 2026-06-10)
# Actual factor names and degree->points must be authored from JES text files
JES_FACTORS_BY_GROUP: dict[str, list[dict]] = {
    "FB": [
        # From data/Job_evaluation/FB Border Services - Job Evaluation Standard 2005.txt
        # TYPE: point-rating plan; factors to be extracted from rating scale section
        {"name": "...", "category": "...", "pts": {1: ..., 2: ..., ...}},
    ],
    "FS": [...],  # data/Job_evaluation/FS Foreigns Service - Job Evauation Standard.txt
    "LP": [...],  # data/Job_evaluation/LP Law Practitioner - Job Evaluation Standard
    "MT": [...],  # data/Job_evaluation/MT Meteorology - Job Evaluation Standard
    "LC": [...],  # data/Job_evaluation/LC Law Management - Job Evaluation Standard.txt
    # SW-SCW: keyed as "SW-SCW" or handled by routing on confirmed_sub_group
}
```

### Sub-group disambiguation constants structure

```python
# Source: ASSUMED pattern based on ASEC_DISAMBIGUATION in constants.py (verified 2026-06-10)
# One dict per group requiring disambiguation
NU_SUBGROUP_DISAMBIGUATION: dict = {
    "subgroups": ["HOS", "CHN", "EMA"],
    "descriptions": {
        "HOS": "Hospital nursing — positions in hospitals and related facilities",
        "CHN": "Community health nursing — positions in public health and community settings",
        "EMA": "Emergency medical attendant nursing — positions in emergency medical services",
    },
    "disambiguation_text": "...",  # from NU JES text
    "citation": "TBS OCHRO — Nursing (NU) Job Evaluation Standard",
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 4-group OG engine (EC/IT/AS/FI) | 16-group engine | Phase 21 | Expands classification coverage to all GC occupational groups |
| Dual-copy NON_EC_STANDARD_NAMES | Single source in constants.py | Phase 21 (OGX-02) | Eliminates drift risk |
| QUAL_STANDARDS with only 4 groups | 16 groups + default | Phase 21 | Full qualification standard coverage |
| ASEC-only disambiguation alert | NU/SW/ED disambiguation added | Phase 21 | Covers all multi-sub-group groups |
| Preview white page stretches/overflows | align-items: flex-start | Phase 21 (UI-01) | Correct scroll behaviour for any document length |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ED has 4 levels (Level 1-4 from EB_rates.csv) | Standard Stack / OGX-01 | Wrong level count in OG_LEVELS["ED"]; test failure and incorrect level picker |
| A2 | PO has 4 levels (TCO-01 to TCO-04 as longest sub-group) | Pitfall 6 / OGX-01 | Could be 3 or 5 if IMA sub-group has a different range; needs final verification from PO_rates.csv full inspection |
| A3 | JES_FACTORS_BY_GROUP structure mirrors EC_JES_ELEMENTS (list of {name, category, pts}) | Code Examples / OGX-05 | If JES factor schemas differ significantly (e.g., FB has categorical not numeric degrees), the jes_service loop may need adaptation |
| A4 | SW sub-group should be stored as `confirmed_sub_group` (new WD field) | Architecture Patterns / OGX-07 | If stored differently (e.g., embedded in confirmed_og.og_code), the API and WD model need matching changes |
| A5 | NU OG_LEVELS uses HOS/CHN 1-8 as the standard level range | Pitfall 2 / OGX-01 | If sub-group disambiguation changes which levels are valid, level picker must be sub-group-aware |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python / pytest | Backend tests | ✓ | 3.11+ | — |
| Vitest | Frontend tests | ✓ | 2.x | — |
| data/Job_evaluation/*.txt | JES factor authoring | ✓ | All 12 new group files present | — |
| data/rates_of_pay/*.csv | Level range verification | ✓ | All relevant CSVs present | — |

All dependencies available. No new installs required.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest 8.x + pytest-asyncio |
| Backend config | `v2/backend/` (pytest.ini or pyproject.toml) |
| Frontend framework | Vitest 2.x |
| Frontend config | `v2/frontend/vitest.config.js` |
| Backend quick run | `cd v2/backend && python -m pytest tests/test_constants.py tests/test_question_bank.py -x -q` |
| Backend full suite | `cd v2/backend && python -m pytest -x -q` |
| Frontend quick run | `cd v2/frontend && npm test -- --reporter=verbose` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OGX-01 | All 6 constants cover all 16 OG keys | unit | `pytest tests/test_constants.py::test_og_constants_completeness -x` | ❌ Wave 0 |
| OGX-01 | OG_LEVELS contiguous int lists for all 16 groups | unit | `pytest tests/test_constants.py::test_og_levels_all_groups_are_lists_of_ints -x` | ✅ (extends existing) |
| OGX-02 | export_service imports NON_EC_STANDARD_NAMES from constants | unit | `pytest tests/test_export.py -k "standard_names" -x` | ❌ Wave 0 |
| OGX-03 | QUAL_DEFAULTS parity with QUAL_STANDARDS (16 groups) | unit | `pytest tests/test_constants.py::test_qual_defaults_parity -x` | ❌ Wave 0 (FAILING) |
| OGX-04 | accumulateSignals() returns correct top OG for each new group ideal answer set | integration | `pytest tests/test_og_classification.py -k "per_group" -x` | ❌ Wave 0 |
| OGX-04 | QUESTION_BANK still passes QUES-02 (no OG codes in labels) | unit | `pytest tests/test_question_bank.py -x` | ✅ (existing) |
| OGX-05 | POST /api/jes/score for FB returns per-factor rows | integration | `pytest tests/test_jes_scoring.py -k "score_fb" -x` | ❌ Wave 0 |
| OGX-05 | JES_FACTORS_BY_GROUP has entries for FB, FS, LP, MT, LC | unit | `pytest tests/test_constants.py -k "jes_factors_by_group" -x` | ❌ Wave 0 |
| OGX-06 | POST /api/jes/score for NU returns jes_scores=[] + total_points from NON_EC_TOTALS | integration | `pytest tests/test_jes_scoring.py -k "score_nu" -x` | ❌ Wave 0 |
| OGX-07 | NU classification response includes sub-group disambiguation alert | integration | `pytest tests/test_og_classification.py -k "nu_disambiguation" -x` | ❌ Wave 0 |
| UI-01 | .doc-scroll contains align-items: flex-start | unit | `cd v2/frontend && npm test -- -t "doc-scroll"` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd v2/backend && python -m pytest tests/test_constants.py tests/test_question_bank.py -x -q`
- **Per wave merge:** `cd v2/backend && python -m pytest -x -q && cd ../frontend && npm test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_constants.py::test_og_constants_completeness` — covers OGX-01 (NEW test)
- [ ] `tests/test_constants.py::test_qual_defaults_parity` — covers OGX-03 (NEW failing test)
- [ ] `tests/test_og_classification.py::test_per_group_signal_routing` — covers OGX-04 per-group assertions
- [ ] `tests/test_jes_scoring.py::test_score_fb_*` etc. — covers OGX-05 per-group point-rating
- [ ] `tests/test_jes_scoring.py::test_score_nu_*` etc. — covers OGX-06 level-lookup groups
- [ ] `tests/test_og_classification.py::test_nu_sw_ed_disambiguation` — covers OGX-07

---

## Security Domain

> Phase 21 makes no changes to authentication, session management, or access control.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Existing: og_code validated against OG_DEFINITIONS in og_classification.py (T-16-02); must extend as new codes are added |
| V6 Cryptography | no | — |

### Known Threat Patterns for This Phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unknown og_code in signal_tally bypasses definition check | Tampering | Existing T-16-01: silently ignored (verified in og_classification.py line 92) — no change needed for new codes; new codes will be added to OG_DEFINITIONS |
| Sub-group field injection (arbitrary sub_group value) | Tampering | New: confirmed_sub_group must be validated against known sub-group lists for NU/SW/ED |

---

## Sources

### Primary (HIGH confidence)
- Direct file inspection: `v2/backend/app/data/constants.py` — all 6 current constants structure confirmed
- Direct file inspection: `v2/backend/app/services/jes_service.py` — JES routing pattern confirmed
- Direct file inspection: `v2/backend/app/api/og_classification.py` — ASEC disambiguation pattern confirmed
- Direct file inspection: `v2/frontend/src/styles.css` lines 548-552 — .doc-scroll bug confirmed
- Direct file inspection: `v2/frontend/src/components.jsx` lines 321-338 — OgConfirmList + asec-alert pattern
- Direct file inspection: `v2/frontend/src/data.jsx` lines 293-314 — QUAL_DEFAULTS structure
- Direct file inspection: `v2/backend/app/services/export_service.py` lines 50-55 — local NON_EC_STANDARD_NAMES confirmed
- Direct file inspection: `data/Job_evaluation/*.txt` — JES type (point-rating vs level-description) verified for all 12 new groups
- Direct file inspection: `data/rates_of_pay/*.csv` — level counts verified for FB (8), FS (4), MT (7 from SP_AP_rates.csv), NU (8 from SH_rates.csv), PS (5), SW-SCW (5), SW-CHA (3), WP (6 from PA_rates.csv), PO (4 from PO_rates.csv)

### Secondary (MEDIUM confidence)
- Direct file inspection: `data/Job_evaluation/NT Nutrition and Dietetics - Job Evaluation Standard` — NT has 4 levels (Level 1-4 text confirmed)
- Direct file inspection: `data/Job_evaluation/LC Law Management - Job Evaluation Standard.txt` — LC has 4 levels (point boundary table)
- Direct file inspection: `data/Job_evaluation/LP Law Practitioner - Job Evaluation Standard` — LP has 5 levels (point boundary table 1-5)

### Tertiary (LOW confidence — needs verification during authoring)
- [ASSUMED] ED has 4 levels (EB_rates.csv shows Level 1-4 for EB/Education group — needs confirmation that ED and EB share the same level count)
- [ASSUMED] JES_FACTORS_BY_GROUP will mirror EC_JES_ELEMENTS structure — actual factor names must be extracted from each JES text file during implementation

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — no new libraries; all existing
- Architecture: HIGH — all patterns verified from existing codebase
- Level counts: HIGH for FB, FS, MT, NU, PS, SW, WP; MEDIUM for NT, LC, LP; LOW for ED (EB proxy)
- Pitfalls: HIGH — verified from direct file inspection

**Research date:** 2026-06-10
**Valid until:** 2026-07-10 (stable data — GC OG structures change infrequently)
