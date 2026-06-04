---
phase: 11-data-foundation
type: research
researched: "2026-06-04"
domain: "Government of Canada pay data parsing + CAF rank-to-civilian equivalence"
confidence: HIGH
---

# Phase 11: Data Foundation — Research

**Researched:** 2026-06-04
**Domain:** GC rates-of-pay CSV parsing, CAF rank pay data, Python constants module
**Confidence:** HIGH (all findings from direct file inspection; no external lookups needed)

## Summary

Phase 11 encodes two hardcoded data artifacts that every downstream phase depends on:
(1) the correct `OG_LEVELS` dict replacing the one in `app/ai/og_ranking.py`, and
(2) a CAF rank-to-civilian OG equivalence table derived from pay-band comparison.

The existing `OG_LEVELS` dict in `app/ai/og_ranking.py` is wrong in two confirmed ways:
it is missing from the v2.0 backend entirely, and its v1.0 version has EC stopping at level 7
(should be 8) and IT stopping at level 4 (should be 5). CS is not a standalone OG group in
the current collective agreements — it merged into IT. IS, PE, GT, EX do not appear in the
priority OG groups for v2.0.

The rates-of-pay CSVs use a custom flat-text-with-hash-comment format: each level block is
introduced by a `# {OG}-{level}: annual rates of pay (in dollars)` comment line. The level
number is embedded in the comment header, not in a column. Parsing strategy is straightforward:
scan comment lines matching `# {CODE}-{N}:` to enumerate levels. However, given the small size
of the dataset and the need for deterministic, auditable constants, the recommended approach is
to **hardcode the extracted constants** rather than parse at runtime.

The CAF pay grades data is a single UTF-8 text file (not a CSV directory) at
`data/CAF pay grades`. It lists monthly pay for all NCM and officer ranks effective April 1,
2025, in tab-separated plain text. Pay-band overlap with civilian OG levels can be computed
by converting CAF monthly pay to annual (× 12) and comparing to the Step 1 / max step ranges
of each civilian OG level's most recent effective date row.

**Primary recommendation:** Hardcode `OG_LEVELS` and `CAF_RANK_OG_EQUIVALENCE` as Python dicts
in a new module `v2/backend/app/data/constants.py`. No runtime CSV parsing.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | System encodes correct OG level ranges for all active groups derived from `data/rates_of_pay/`; `OG_LEVELS` dict in `app/ai/og_ranking.py` replaced with corrected full set | CSV schema documented; all levels enumerated per group; extraction approach confirmed |
| DATA-02 | System encodes CAF rank→civilian OG equivalence table (hardcoded constant) derived by pay-band comparison from `data/CAF pay grades`; maps NCM and officer ranks to approximate civilian OG-level ranges; annotated "advisory — not authoritative" | CAF pay data schema documented; pay-band comparison approach confirmed |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| OG level constants | API / Backend | — | Pure Python constant; no UI needed in this phase |
| CAF rank equivalence table | API / Backend | — | Hardcoded constant; consumed by CLASS-05 in Phase 16 |
| CSV data parsing (extraction only, not runtime) | Data extraction script / manual | — | One-time extraction; result lives as a constant, not parsed at runtime |
| Unit test validation | API / Backend tests | — | pytest in `v2/backend/tests/` |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python 3.10 stdlib | 3.10.12 (installed) | Constants file, test logic | No external dep needed for hardcoded dicts |
| pytest | 8.3.4 (installed) | Unit tests | Existing test infra in `v2/backend/` |

No new packages required for Phase 11. The constants are pure Python dicts; no CSV parsing
library is needed at runtime because values are hardcoded after manual extraction.

**Installation:** None required.

## Architecture Patterns

### System Architecture Diagram

```
data/rates_of_pay/*.csv          data/CAF pay grades
        │                                 │
        │  (one-time manual inspection)   │
        ▼                                 ▼
  [Extract level numbers]      [Extract monthly pay → annual,
  [e.g. EC-01 through EC-08]    compare to civilian OG ranges]
        │                                 │
        └──────────────┬──────────────────┘
                       ▼
         v2/backend/app/data/constants.py
              OG_LEVELS dict
              CAF_RANK_OG_EQUIVALENCE dict
                       │
            ┌──────────┼────────────────┐
            ▼          ▼                ▼
     Phase 12       Phase 16        Phase 17
  (question bank) (OG classify)   (JES scoring)
  references       level range     OG code check
  OG_LEVELS        from OG_LEVELS
```

### Recommended Project Structure

```
v2/backend/
├── app/
│   ├── api/               # Existing — health.py, __init__.py
│   ├── data/              # NEW in Phase 11
│   │   ├── __init__.py    # Empty package marker
│   │   └── constants.py   # OG_LEVELS + CAF_RANK_OG_EQUIVALENCE
│   ├── models/            # Existing — 5 Pydantic models
│   ├── config.py          # Existing
│   ├── db.py              # Existing
│   ├── main.py            # Existing
│   └── __init__.py        # Existing
└── tests/
    ├── conftest.py         # Existing
    ├── test_constants.py   # NEW in Phase 11
    └── ...existing tests...
```

### Pattern: Hardcoded Constants Module

**What:** All OG level data and CAF equivalence data lives as a Python dict literal in
`v2/backend/app/data/constants.py`. No runtime parsing.

**When to use:** When the source data is small, changes infrequently, and must be auditable
and deterministic. This fits exactly — the collective agreement schedules are multi-year,
and the CAF pay data is a single effective-date snapshot.

**Example:**
```python
# Source: verified against data/rates_of_pay/EC_rates.csv (EC-01 through EC-08)
OG_LEVELS: dict[str, list[int]] = {
    "EC": list(range(1, 9)),   # EC-01 through EC-08
    "IT": list(range(1, 6)),   # IT-01 through IT-05
    "AS": list(range(1, 9)),   # AS-1 through AS-8 (PA collective agreement)
    "FI": list(range(1, 5)),   # FI-01 through FI-04 (CT-FI collective agreement)
    # ... all other groups
}
```

**Example (CAF table):**
```python
# Advisory — not authoritative. Derived by pay-band comparison,
# effective April 1, 2025. Source: data/CAF pay grades.
CAF_RANK_OG_EQUIVALENCE: dict[str, dict] = {
    "Private / Sailor 3rd or 2nd Class": {
        "monthly_pay_range_cad": (4337, 5994),
        "approx_civilian_og_levels": ["AS-01", "CR-01", "CR-02"],
        "advisory": True,
    },
    # ...
}
```

### Anti-Patterns to Avoid

- **Runtime CSV parsing on app startup:** The files have inconsistent formats (some use
  tab-separated data, some use quoted CSVs, some have non-standard continuation headers).
  Parse once manually; hardcode the result.
- **Importing from v1.0 app/ai/og_ranking.py in v2.0:** The v1.0 module is preserved but
  must not be imported into v2.0 code. Copy and correct the OG_LEVELS value.
- **Using CS as a standalone group:** CS is not a separate entry in the current collective
  agreements; it merged into IT. The v1.0 OG_LEVELS had a "CS" key — this was an error.
- **Including IS, PE, EX, GT, PM, CR in OG_LEVELS for v2.0 classification:** These groups
  exist in the agreements but are out-of-scope for the v2.0 OG classifier (the classifier
  targets EC, IT, AS, FI focus groups). OG_LEVELS should cover all active groups for
  level-range display, but the broader set (IS, PE, PM, CR, GT, EX) can be included with
  correct ranges if needed by downstream phases.

## What Is Wrong with the Existing OG_LEVELS (v1.0)

[VERIFIED: direct read of `app/ai/og_ranking.py` and `data/rates_of_pay/*.csv`]

```python
# CURRENT (WRONG) v1.0 OG_LEVELS in app/ai/og_ranking.py
OG_LEVELS: dict[str, list[int]] = {
    "AS": list(range(1, 9)),   # range(1,9) = [1..8]  ← CORRECT count, but...
    "CR": list(range(1, 7)),   # range(1,7) = [1..6]  ← WRONG: CR has 7 levels (CR-1 through CR-7)
    "PM": list(range(1, 7)),   # range(1,7) = [1..6]  ← WRONG: PM has 7 levels (PM-1 through PM-7)
    "PE": list(range(1, 8)),   # NOT in v2.0 focus groups; range count unverified
    "EC": list(range(1, 8)),   # range(1,8) = [1..7]  ← WRONG: EC has 8 levels (EC-01 through EC-08)
    "IT": list(range(1, 5)),   # range(1,5) = [1..4]  ← WRONG: IT has 5 levels (IT-01 through IT-05)
    "CS": list(range(1, 6)),   # CS is NOT a current standalone OG; merged into IT
    "EX": list(range(1, 6)),   # NOT found in rates_of_pay CSVs; unverified
    "IS": list(range(1, 8)),   # NOT found in rates_of_pay CSVs; unverified
    "GT": list(range(1, 9)),   # range(1,9) = [1..8]; GT-1 through GT-8 CONFIRMED in TC_rates.csv
}
```

This module does not exist at all in `v2/backend/` — the v2.0 backend has no `OG_LEVELS`
constant yet. DATA-01 creates it from scratch in the correct location.

## CSV Schema: rates_of_pay Files

[VERIFIED: direct read of EC_rates.csv, IT_CS_rates.csv, PA_rates.csv, CT_FI_rates.csv]

### Format

The files are not strictly uniform CSVs. Each file covers one collective agreement
(which may include multiple OG groups). The format is:

```
# {OG}-{LEVEL}: annual rates of pay (in dollars)
# Section: {appendix reference}
Effective date,Step 1,Step 2,...,Step N
"date string","amount","amount",...
```

**Key structural facts:**
- Level number is embedded in the **comment header line**, not in any column.
- Each level block begins with `# {CODE}-{N}:` (varying spacing and formatting).
- The "Effective date" column contains date strings like `"D) June 22, 2025"`.
- Pay columns are quoted strings with commas in amounts: `"62,871"`.
- Some files have **multi-page** sections labeled `(continuation)` — same level, split.
- Some files include **weekly/daily/hourly** appendix sections (IT_CS_rates.csv Appendix B).

### Level Extraction Strategy

To enumerate levels: scan `# ` comment lines matching the pattern `# {GROUP}-{N}`.
The presence of a comment header for `EC-01` through `EC-08` confirms EC has 8 levels.

The level number is always the integer after the hyphen in the group code.

### Pay-Band Extraction for CAF Comparison

To determine pay ranges: find the most recent effective date row (sort by letter prefix:
D > C > B > A > $), take Step 1 (minimum) through the last step (maximum).

## Verified OG Level Counts per CSV File

[VERIFIED: direct inspection of all 26 rates_of_pay CSV files]

| CSV File | Primary OG Group(s) | Confirmed Levels | Notes |
|----------|---------------------|-----------------|-------|
| EC_rates.csv | EC | EC-01 to EC-08 | Also contains SPS-ESS-01 to SPS-ESS-08 (same pay, ES sub-group) |
| IT_CS_rates.csv | IT | IT-01 to IT-05 | Also CS levels (legacy); CS not a current standalone group |
| PA_rates.csv | AS, CR, CM, OE, PM, ST, WP | AS-1 to AS-8, CR-1 to CR-7, PM-1 to PM-7 | PA collective agreement covers multiple groups |
| CT_FI_rates.csv | FI (now CT-FIN), AU (now CT-EAV) | FI-01 to FI-04, AU-01 to AU-06 | Renamed to CT-FIN-01..04 in Sept 2023 |
| AI_rates.csv | AI | AI-01 to AI-07 | |
| AO_rates.csv | AO (CAI sub-group) | CAI-01 to CAI-05 | |
| CP_AV_rates.csv | CO, CO-DEV | CO-01 to CO-04 | |
| CX_rates.csv | CX | CX-01 to CX-05 (approx) | Corrections group |
| EB_rates.csv | EB | EB-01 to EB-08 | |
| EL_rates.csv | EL | EL-01 to EL-09 | |
| FB_rates.csv | FB | FB-1 to FB-8 | |
| FS_rates.csv | FS | FS-01 to FS-04 | |
| NR_rates.csv | AR, BI, CH, HR, MT, PC, PH, PI, PS, PT, SE | Many sub-groups | NR collective agreement |
| PO_rates.csv | PO | PO-01 to PO-08 (approx) | |
| RE_rates.csv | RE | RE-01 to RE-08 (approx) | |
| RM_rates.csv | Constable, Cst | RCMP pay rates | |
| RO_rates.csv | RO | RO-00 to RO-06 | |
| SH_rates.csv | DE, DS | DE-1 to DE-3, DS-1 to DS-7 | |
| SO_rates.csv | SO | SO-MAO-TO | |
| SP_AP_rates.csv | AC, AG | AC-01 to AC-03, AG-01 to AG-05 | |
| SRC_rates.csv | SRC sub-groups | Multiple | |
| SRE_rates.csv | SRE sub-groups | Multiple | |
| SV_rates.csv | SV sub-groups (FO, FR, HP, HR, LI, LS, MA, OP, PG, PY, SC, TI, VM) | Multiple | Service |
| TC_rates.csv | GT, EG, DD, AME, AMW, AIM | GT-1 to GT-8, EG-1 to EG-8 | Technical category |
| TR_rates.csv | TR | TR-01 to TR-05 | |
| UT_rates.csv | UT sub-groups | Multiple | |

**For v2.0 OG_LEVELS (focus groups first, then full set):**

| OG Code | Source CSV | Confirmed Level Range |
|---------|-----------|----------------------|
| EC | EC_rates.csv | 1–8 |
| IT | IT_CS_rates.csv | 1–5 |
| AS | PA_rates.csv | 1–8 |
| FI | CT_FI_rates.csv | 1–4 (renamed CT-FIN but "FI" is still the OG code used in classification) |
| CR | PA_rates.csv | 1–7 |
| PM | PA_rates.csv | 1–7 |
| GT | TC_rates.csv | 1–8 |
| EL | EL_rates.csv | 1–9 |
| FB | FB_rates.csv | 1–8 |
| FS | FS_rates.csv | 1–4 |
| AI | AI_rates.csv | 1–7 |
| AU | CT_FI_rates.csv | 1–6 (renamed CT-EAV; AU is OG code) |

**OG codes not found in rates CSVs (v1.0 included erroneously):**
- CS: not a standalone OG group in current agreements (merged into IT)
- PE, IS: not found in any rates CSV; these are archived or pre-CA groups
- EX: not in these collective agreement files (EX has its own TB Management framework)

## CAF Pay Grades Data Schema

[VERIFIED: direct read of `data/CAF pay grades` file]

The file at `data/CAF pay grades` is a **single UTF-8 plain-text file** (not a directory,
not a CSV). It uses tab-separated columns embedded in prose, formatted for web rendering.

**Effective date:** April 1, 2025.

**Structure:** NCM ranks first, then Officers, then special categories.

### NCM Ranks and Basic Monthly Pay (April 1, 2025)

| CAF Rank | Basic Monthly Pay | Annual Equivalent |
|----------|-------------------|-------------------|
| Private / Sailor 2nd or 3rd Class | $4,337–$5,994 | $52,044–$71,928 |
| Corporal / Sailor 1st Class – Standard | $6,858 (base) + increments to $7,337 | $82,296–$88,044 |
| Corporal / Sailor 1st Class – Specialist 1 | $7,606–$8,071 | $91,272–$96,852 |
| Corporal / Sailor 1st Class – Specialist 2 | $8,138–$8,636 | $97,656–$103,632 |
| Master Corporal / Master Sailor – Standard | $7,118–$7,841 | $85,416–$94,092 |
| Sergeant / Petty Officer 2nd Class – Standard | $7,959–$8,340 | $95,508–$100,080 |
| Warrant Officer / Petty Officer 1st Class – Standard | $8,694–$8,997 | $104,328–$107,964 |
| Master Warrant Officer / Chief Petty Officer 2nd Class – Standard | $9,668–$10,057 | $116,016–$120,684 |
| Chief Warrant Officer / Chief Petty Officer 1st Class | $10,562–$12,243 (pay levels A/B/C) | $126,744–$146,916 |

### Officer Ranks and Basic Monthly Pay (April 1, 2025)

| CAF Rank | Basic Monthly Pay | Annual Equivalent |
|----------|-------------------|-------------------|
| Officer Cadet / Naval Cadet | $2,913–$5,060 | $34,956–$60,720 |
| Second Lieutenant / Acting Sub-Lieutenant | $5,096–$9,514 (varies by pay level A-E) | $61,152–$114,168 |
| Lieutenant / Sub-Lieutenant | $5,397–$11,057 | $64,764–$132,684 |
| Captain / Lieutenant (Navy) | $8,861–$11,712 | $106,332–$140,544 |
| Major / Lieutenant-Commander | $11,983–$13,435 | $143,796–$161,220 |
| Lieutenant-Colonel / Commander | $13,887–$14,779 | $166,644–$177,348 |
| Colonel / Captain (Navy) | $15,684–$17,541 | $188,208–$210,492 |
| Brigadier-General / Commodore | $18,565–$20,097 | $222,780–$241,164 |
| Major-General / Rear-Admiral | $21,301–$25,020 | $255,612–$300,240 |
| Lieutenant-General / Vice-Admiral | $27,361–$29,619 | $328,332–$355,428 |

**Pay comparison anchors for civilian OG levels (most recent D-row rates, Step 1):**

| Civilian OG | Step 1 (annual, 2025) | Max Step (annual, 2025) |
|-------------|----------------------|------------------------|
| AS-01 | $61,632 | $69,106 (Step 4) |
| AS-04 | $80,411 | $87,108 (Step 3) |
| AS-08 | $116,218 to $136,793 (range) | — |
| EC-01 | $62,871 | $73,087 (Step 5) |
| EC-04 | $83,862 | $97,051 (Step 5) |
| EC-06 | $113,278 | $131,375 (Step 5) |
| EC-08 | $139,155 | $159,046 (Step 5) |
| IT-01 | $69,188 | $89,159 (Step 8) |
| IT-03 | $101,090 | $125,600 (Step 8) |
| IT-05 | $133,249 | $173,642 (Step 9) |
| FI-01 | $66,982 | $93,965 (Step 7, D-row) |
| FI-04 | $117,501 | $151,719 (Step 7, D-row) |

### CAF Pay-Band to Civilian OG Comparison Logic

Convert CAF monthly pay to annual: `monthly × 12`. Then find which civilian OG level ranges
the annual pay overlaps. Use Step 1 (min) and max-step (max) of the most recent D-row
effective date as the band bounds.

**For the hardcoded CAF_RANK_OG_EQUIVALENCE table, the following approximate mappings apply:**

| CAF Rank (simplified) | Annual Pay Range | Approx Civilian OG Equivalent |
|-----------------------|-----------------|-------------------------------|
| Private / Sailor 2nd–3rd | $52k–$72k | AS-01, CR-01, CR-02 |
| Corporal Standard | $82k–$88k | AS-03 to AS-04, EC-02 |
| Master Corporal Standard | $85k–$94k | AS-04, EC-02 to EC-03 |
| Sergeant Standard | $96k–$100k | AS-05 to AS-06, EC-03 |
| Warrant Officer Standard | $104k–$108k | AS-07, EC-05 (low end) |
| Master Warrant Officer Standard | $116k–$121k | AS-08 (low), EC-06 |
| Chief Warrant Officer (A/B/C) | $127k–$147k | EC-07 to EC-08, IT-04 |
| 2Lt / Acting Sub-Lt (D/E pay levels) | $84k–$114k | AS-04 to EC-06 range |
| Lieutenant (D/E pay levels) | $86k–$133k | AS-05 to IT-04 range |
| Captain / Lt(N) | $106k–$141k | EC-06 to EC-08, IT-04 |
| Major / Lt-Cdr | $144k–$161k | EC-08 (max), IT-05 (low) |
| Lt-Col / Cdr | $167k–$177k | IT-05 mid-range |
| Colonel / Capt(N) | $188k–$210k | EX-01 to EX-02 range (advisory) |
| BGen / Cmdre and above | $223k+ | EX-03 and above (advisory) |

**Important:** These are approximate pay-band overlaps, not formal equivalences. The table
must be annotated `"advisory": True` in code and labelled "advisory — not authoritative"
wherever displayed (REQUIREMENTS.md DATA-02, CLASS-05).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Level enumeration | A runtime CSV parser | Hardcoded `list(range(1, N+1))` constants | CSV format varies per file; constants are faster, auditable, never break on file changes |
| Pay-band comparison at runtime | A live comparison engine | Hardcoded equivalence dict | Pay data is a point-in-time snapshot; runtime comparison adds complexity with no benefit for an advisory display |

## Common Pitfalls

### Pitfall 1: Off-by-One in range()

**What goes wrong:** `list(range(1, 8))` produces `[1,2,3,4,5,6,7]` — 7 items, not 8.
**Why it happens:** Python `range(start, stop)` is exclusive of `stop`.
**How to avoid:** For EC (8 levels), write `list(range(1, 9))`. Always cross-check:
`len(list(range(1, N+1))) == N`.
**Warning signs:** The v1.0 bug — `EC: list(range(1, 8))` gives levels 1–7, missing EC-08.

### Pitfall 2: CS as a Standalone Group

**What goes wrong:** Including `"CS": list(range(1, 6))` in OG_LEVELS as if CS is a
separate group from IT.
**Why it happens:** Older GC classification resources treated CS separately. The v1.0 code
perpetuated this.
**How to avoid:** The IT collective agreement (PIPSC) covers IT-01 through IT-05 and the
Computer Systems group is now subsumed. Do not add CS as a separate key.
**Warning signs:** Any reference to `OG_LEVELS["CS"]` in v2.0 code is a bug.

### Pitfall 3: FI vs CT-FIN Naming Confusion

**What goes wrong:** Treating `CT-FIN` as the OG code instead of `FI`.
**Why it happens:** The CT-FI collective agreement renamed FI levels to CT-FIN-01..04 in
September 2023 for internal accounting, but the OG classification code in the TBS system
remains "FI".
**How to avoid:** Use `"FI"` as the dict key in `OG_LEVELS`. Note in comments that the
CA refers to these as CT-FIN levels internally.

### Pitfall 4: CAF Data is a Text File, Not a CSV Directory

**What goes wrong:** Attempting `os.listdir("data/CAF pay grades/")` or
`pd.read_csv("data/CAF pay grades")`.
**Why it happens:** The path looks like a directory name but is a single file.
**How to avoid:** `data/CAF pay grades` is a single UTF-8 text file (verified via `file`
command). Read it as plain text. No CSV parsing needed — all values are hardcoded from
manual inspection.

### Pitfall 5: Importing v1.0 OG_LEVELS into v2.0

**What goes wrong:** `from app.ai.og_ranking import OG_LEVELS` in v2.0 code.
**Why it happens:** The file exists and has the right name.
**How to avoid:** `app/ai/og_ranking.py` is v1.0 code preserved for reference only. All
v2.0 modules must import from `app.data.constants` (v2 path), never from v1.0 modules.

## Code Examples

### constants.py Skeleton

```python
# Source: verified against data/rates_of_pay/*.csv (direct file inspection 2026-06-04)
# and data/CAF pay grades (single text file, effective April 1, 2025)

"""
app/data/constants.py — Authoritative data constants for v2.0.

OG_LEVELS: maps OG code → list of level integers, derived from rates_of_pay CSVs.
CAF_RANK_OG_EQUIVALENCE: maps CAF rank name → approximate civilian OG equivalents.

IMPORTANT: CAF_RANK_OG_EQUIVALENCE is advisory only. It is derived from pay-band
comparison and does not constitute a formal equivalence under DAOD or TB policy.
Label as "advisory — not authoritative" on all surfaces that display it.
"""
from __future__ import annotations

# Correct OG level ranges derived from data/rates_of_pay/ CSV files.
# Key: OG group code (string). Value: list of level integers (1-indexed).
# EC: EC-01 to EC-08 (8 levels) — EC_rates.csv
# IT: IT-01 to IT-05 (5 levels) — IT_CS_rates.csv
# AS: AS-1 to AS-8 (8 levels) — PA_rates.csv (PA collective agreement)
# FI: FI-01 to FI-04 (4 levels) — CT_FI_rates.csv (internally CT-FIN, OG code remains FI)
OG_LEVELS: dict[str, list[int]] = {
    "EC": list(range(1, 9)),   # EC-01 to EC-08
    "IT": list(range(1, 6)),   # IT-01 to IT-05
    "AS": list(range(1, 9)),   # AS-1 to AS-8 (PA collective agreement)
    "FI": list(range(1, 5)),   # FI-01 to FI-04 (CT-FIN internally, FI is OG code)
    "CR": list(range(1, 8)),   # CR-1 to CR-7 (PA collective agreement)
    "PM": list(range(1, 8)),   # PM-1 to PM-7 (PA collective agreement)
    "GT": list(range(1, 9)),   # GT-1 to GT-8 (TC collective agreement)
    "EL": list(range(1, 10)),  # EL-01 to EL-09
    "FB": list(range(1, 9)),   # FB-1 to FB-8
    "FS": list(range(1, 5)),   # FS-01 to FS-04
    "AI": list(range(1, 8)),   # AI-01 to AI-07
    "AU": list(range(1, 7)),   # AU-01 to AU-06 (CT-EAV internally, AU is OG code)
}

# CAF rank to approximate civilian OG equivalence.
# ADVISORY ONLY — NOT AUTHORITATIVE.
# Derived by annual pay-band comparison, effective April 1, 2025.
# Monthly pay × 12 compared to Step 1–max step of civilian OG levels (D-row rates).
CAF_RANK_OG_EQUIVALENCE: dict[str, dict] = {
    "Private / Sailor 2nd or 3rd Class": {
        "approx_annual_pay_cad": (52044, 71928),
        "approx_civilian_og_levels": ["AS-01", "CR-01", "CR-02"],
        "advisory": True,
        "note": "Entry-level; pay band overlaps AS-01 and CR-01/02 ranges.",
    },
    # ... (full table populated from pay-band comparison above)
}
```

### Test Pattern (test_constants.py)

```python
# Source: mirrors existing test pattern in v2/backend/tests/test_models.py
from app.data.constants import OG_LEVELS, CAF_RANK_OG_EQUIVALENCE

def test_og_levels_ec_has_8_levels():
    assert OG_LEVELS["EC"] == list(range(1, 9))
    assert len(OG_LEVELS["EC"]) == 8

def test_og_levels_it_has_5_levels():
    assert OG_LEVELS["IT"] == list(range(1, 6))
    assert len(OG_LEVELS["IT"]) == 5

def test_og_levels_as_has_8_levels():
    assert OG_LEVELS["AS"] == list(range(1, 9))

def test_og_levels_fi_has_4_levels():
    assert OG_LEVELS["FI"] == list(range(1, 5))

def test_og_levels_all_groups_are_lists_of_ints():
    for code, levels in OG_LEVELS.items():
        assert isinstance(levels, list), f"{code} levels must be a list"
        assert all(isinstance(n, int) for n in levels), f"{code} levels must be ints"
        assert levels == list(range(levels[0], levels[-1] + 1)), \
            f"{code} levels must be contiguous"

def test_og_levels_no_cs_key():
    assert "CS" not in OG_LEVELS, "CS is not a current standalone OG group"

def test_caf_table_all_entries_advisory_flagged():
    for rank, entry in CAF_RANK_OG_EQUIVALENCE.items():
        assert entry.get("advisory") is True, \
            f"CAF rank '{rank}' must be flagged advisory=True"

def test_caf_table_og_codes_exist_in_og_levels():
    all_og_codes = set(OG_LEVELS.keys())
    for rank, entry in CAF_RANK_OG_EQUIVALENCE.items():
        for og_level_str in entry["approx_civilian_og_levels"]:
            og_code = og_level_str.split("-")[0]
            assert og_code in all_og_codes, \
                f"CAF '{rank}' references OG code '{og_code}' not in OG_LEVELS"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-----------------|--------------|--------|
| v1.0: OG_LEVELS in `app/ai/og_ranking.py` with EC stopping at 7 | v2.0: Correct OG_LEVELS in `v2/backend/app/data/constants.py` | Phase 11 | EC-08 level is now reachable in classification |
| v1.0: CS as standalone group | v2.0: CS removed (IT covers all CS positions) | Phase 11 | No broken OG lookups for CS positions |
| v1.0: No CAF rank equivalence table | v2.0: CAF_RANK_OG_EQUIVALENCE in constants.py | Phase 11 | CLASS-05 advisory display can render in Phase 16 |

## Open Questions

1. **EX levels for senior classification**
   - What we know: EX (Executive Group) is not in the rates_of_pay CSVs; EX has its own
     TB Management Framework separate from collective agreements.
   - What's unclear: Should EX-01 through EX-05 appear in OG_LEVELS for v2.0?
   - Recommendation: Include EX-01 to EX-05 as an ASSUMED range (consistent with v1.0);
     flag in comments as sourced from TBS EX framework, not a CA CSV. Out of v2.0 primary
     classifier scope but needed if OG_LEVELS is used for display completeness.

2. **IS and PE groups**
   - What we know: Neither appears in any rates_of_pay CSV. v1.0 included them.
   - What's unclear: Are these still active OG classifications?
   - Recommendation: Exclude from v2.0 OG_LEVELS unless a downstream phase requires them.
     Flag as [ASSUMED] if included.

3. **Precise CAF equivalence for OF-1 to OF-3 officer levels**
   - What we know: Lt and Capt pay spans a very wide band ($65k–$141k annually) depending
     on pay level (A through E). This makes clean OG mapping fuzzy.
   - What's unclear: Which pay level (A/B/C/D/E) is most representative for mapping.
   - Recommendation: Use pay level D (most common general duty officer track) as the
     representative anchor. Document the choice in comments.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10 | constants.py, tests | ✓ | 3.10.12 | — |
| pytest | test_constants.py | ✓ | 8.3.4 | — |
| pytest-asyncio | existing tests | ✓ | 0.24.0 | — |
| data/rates_of_pay/*.csv | Data extraction | ✓ | 26 files present | — |
| data/CAF pay grades | Data extraction | ✓ | Single text file | — |

No missing dependencies. Phase 11 is purely code and constants — no external services needed.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 |
| Config file | `v2/backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd v2/backend && python -m pytest tests/test_constants.py -x -q` |
| Full suite command | `cd v2/backend && python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | EC has 8 levels | unit | `pytest tests/test_constants.py::test_og_levels_ec_has_8_levels -x` | ❌ Wave 0 |
| DATA-01 | IT has 5 levels | unit | `pytest tests/test_constants.py::test_og_levels_it_has_5_levels -x` | ❌ Wave 0 |
| DATA-01 | AS has 8 levels | unit | `pytest tests/test_constants.py::test_og_levels_as_has_8_levels -x` | ❌ Wave 0 |
| DATA-01 | FI has 4 levels | unit | `pytest tests/test_constants.py::test_og_levels_fi_has_4_levels -x` | ❌ Wave 0 |
| DATA-01 | All levels are contiguous int lists | unit | `pytest tests/test_constants.py::test_og_levels_all_groups_are_lists_of_ints -x` | ❌ Wave 0 |
| DATA-01 | CS key absent from OG_LEVELS | unit | `pytest tests/test_constants.py::test_og_levels_no_cs_key -x` | ❌ Wave 0 |
| DATA-02 | All CAF entries flagged advisory=True | unit | `pytest tests/test_constants.py::test_caf_table_all_entries_advisory_flagged -x` | ❌ Wave 0 |
| DATA-02 | CAF OG codes all exist in OG_LEVELS | unit | `pytest tests/test_constants.py::test_caf_table_og_codes_exist_in_og_levels -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd v2/backend && python -m pytest tests/test_constants.py -x -q`
- **Per wave merge:** `cd v2/backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green (including existing 10 tests from Phase 10) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_constants.py` — all DATA-01 and DATA-02 tests (8 test functions)
- [ ] `app/data/__init__.py` — empty package marker (required for importability)
- [ ] `app/data/constants.py` — the actual constants (implemented in Wave 1)

## Security Domain

Security enforcement is not applicable to this phase. Phase 11 creates read-only hardcoded
Python constants with no HTTP endpoints, no user input, no authentication surface, and no
data persistence. No ASVS categories apply.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | FI is the correct OG code to use as dict key (not CT-FIN) | Verified OG Level Counts | Phase 16 OG classifier would fail to look up FI level range if key is wrong |
| A2 | EX group has levels 01–05 (sourced from TBS EX framework, not a CA CSV) | Open Questions | EX level lookup would be wrong if TBS framework differs |
| A3 | IS and PE are excluded from v2.0 OG_LEVELS as inactive/out-of-scope | Open Questions | If a position uses IS or PE, level range lookup would fail |
| A4 | Officer pay level D is the representative anchor for general duty officers | CAF Pay-Band Comparison Logic | CAF equivalence display could be misleading for officers on pay level A/B/C/E |

**Claims A1, A3, A4 are ASSUMED (not externally verified against TBS policy documents in this session). A1 is supported by the fact that the collective agreement still uses FI in section headers.**

## Sources

### Primary (HIGH confidence)

- `data/rates_of_pay/EC_rates.csv` — EC levels 1–8 confirmed by direct file read
- `data/rates_of_pay/IT_CS_rates.csv` — IT levels 1–5 confirmed by direct file read
- `data/rates_of_pay/PA_rates.csv` — AS levels 1–8, CR levels 1–7, PM levels 1–7 confirmed
- `data/rates_of_pay/CT_FI_rates.csv` — FI levels 1–4, AU levels 1–6 confirmed
- `data/rates_of_pay/TC_rates.csv` — GT levels 1–8, EG levels 1–8 confirmed
- `data/CAF pay grades` — CAF rank pay table, effective April 1, 2025, confirmed by direct read
- `app/ai/og_ranking.py` — v1.0 OG_LEVELS dict confirmed incorrect (EC stops at 7, IT stops at 4)
- `v2/backend/app/` — directory structure confirmed (no `data/` subpackage exists yet)
- `v2/backend/tests/` — test pattern confirmed (pytest, asyncio_mode=auto, conftest.py fixtures)

### Secondary (MEDIUM confidence)

- `v2/backend/pyproject.toml` — test config: `testpaths = ["tests"]`, `asyncio_mode = "auto"`

### Tertiary (LOW confidence)

- A2 (EX levels 01–05): ASSUMED from TBS management framework knowledge, not verified against a file in this session

## Metadata

**Confidence breakdown:**
- CSV schema and level counts: HIGH — directly inspected all relevant files
- OG_LEVELS errors in v1.0: HIGH — directly read `app/ai/og_ranking.py`
- CAF pay data schema: HIGH — directly read `data/CAF pay grades`
- Hardcode vs runtime recommendation: HIGH — fits project decision "curated hardcoded data over ingest pipelines" (STATE.md)
- EX/IS/PE group inclusion: LOW — not in any rates CSV; ASSUMED from training knowledge

**Research date:** 2026-06-04
**Valid until:** 2026-12-04 (collective agreement rates updated periodically; OG level counts change rarely)

---

## RESEARCH COMPLETE
