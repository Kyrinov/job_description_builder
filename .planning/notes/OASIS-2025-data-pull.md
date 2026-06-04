# OASIS 2025 Data Pull — Discussion Note

**Date:** 2026-06-04
**Context:** Had a side discussion with the user about pulling the rest of the
OASIS 2025 v1.0 English data from the CKAN DataStore. This file is a
hand-off so any future session (Claude Code or otherwise) has the
decisions in one place.

## What was done

The user already had 5 of the OASIS 2025 JSON files in `data/`
(Abilities, Attributes, Knowledges, Skills, Taxonomy). 13 more were
missing. I pulled them from the open.canada.ca CKAN DataStore using
`datastore_search` with offset pagination (default page 100, used 1000).
Package ID: `10ce43bd-fb58-4969-806b-4bffebc87bec`.

13 new files in `data/` — committed in `2602e0a`:

| File | Rows |
|---|---|
| WorkActivities | 900 |
| WorkContext | 900 |
| Interests | 900 |
| CoreCompetencies | 5,457 |
| **SkillsMatch** | **0** (schema only, 902 fields — server has no records) |
| Labels | 900 |
| LeadStatement | 900 |
| WorkplacesEmployers | 3,418 |
| ExampleTitles | 18,666 |
| MainDuties | 4,991 |
| EmploymentRequirements | 2,851 |
| AdditionalInformation | 1,158 |
| Exclusions | 3,074 |

`datastore_search_sql` is **not** enabled on this CKAN instance — only
`datastore_search`. Don't try SQL endpoint, it 400s.

The 5 pre-existing files are still untracked in the working tree
(`git status` shows them as `??`); the user has not committed them.
Only the 13 new files are in `2602e0a`. Don't assume all 18 OASIS files
are tracked.

## Key architectural context

v2.0's classification is **deterministic work-type + 3 scope questions**
(PROJECT.md, Out-of-Scope: "Live OASIS scraping as primary data source").
OaSIS is **reference / citation material**, not a classifier driver.
The authoritative classification source is still `TBS-OCHRO-OG.txt` and
`directive_on_classification.txt`. OaSIS informs the *work description
text* (duties, exclusions, qual requirements), not the *classification*.

Phase 14 (NOC Pipeline) is FTS5 over **NOC 2021** — a separate dataset.
OaSIS 2025 is complementary, not a replacement.

## Decision: incorporate now, as thin slices — NOT a new phase

Reasoning (in priority order):

1. The constants.py curation pattern is already proven (Phase 11
   `OG_LEVELS`, Phase 12 `QUESTION_BANK`). Zero new architecture.
2. 4 of 7 remaining v2.0 phases (16, 18, 19, 20) have direct, high-value
   hooks. Not a v3 problem.
3. Risk is low — OaSIS data is reference. Worst case: a wrong default
   string shows up. No classifier regression possible.
4. Phase 19's qual defaults (QUAL-01/02/03 success criteria) explicitly
   cite "TBS Qualification Standard". Sourcing the text from OaSIS
   `EmploymentRequirements` is stronger than hand-written defaults.
5. v2.0 already dropped 10 v1.0 candidates to keep scope tight; adding
   a "OaSIS Curation" phase would be the same cargo-cult it just avoided.

## What to add (now) — thin slice, ~150–200 LOC constants + ~80 LOC API + ~12 tests

| Phase | Add | Notes |
|---|---|---|
| **16** OG Classification | `EXCLUSIONS_BY_NOC` + `ADDITIONAL_INFO_BY_NOC` constants feeding `GET /api/og/definitions` and CLASS-03 disambiguation | Direct CLASS-01/03 citation source |
| **18** JD Composition | `OASIS_LABELS` (canonical OaSIS profile name) + `LEAD_STATEMENTS` for live preview hero text | Hero line of position overview |
| **19** Qualifications | `EMPLOYMENT_REQUIREMENTS_BY_NOC` for OG-matched qual defaults | Replaces hand-written qual text |
| **20** Job Poster | (deferred — see below) | |

## Deferred to v3

- `WorkContext` + `WorkActivities` — better fit with the DND SJD library
  corpus work, not standalone valuable
- `Interests` + `CoreCompetencies` — same
- `SkillsMatch` — server has no data; revisit if/when ESDC publishes
  v1.1; possibly drop entirely
- `WorkplacesEmployers` — job poster feature, paired with `ExampleTitles`
  autocomplete (better done as a single "poster enrichment" v3 phase)
- `ExampleTitles` — poster autocomplete, deferred with the rest of
  poster work

## Open question for future sessions

If a v2.1 hotfix path is preferred over in-phase integration, the
trade-off is: shipping v2.0 with less-accurate qual defaults vs. risking
phase scope drift. The user has not decided. Default recommendation if
asked: in-phase.

## File pointers for drill-down

- `data/OASIS-2025-*.json` — the 18 files (5 pre-existing untracked, 13
  in commit `2602e0a`)
- `.planning/PROJECT.md` lines 38–96 — v2.0 active requirements
- `.planning/ROADMAP.md` — Phases 14–20 success criteria
- `v2/backend/app/data/constants.py` — 351 lines, the curation target
- `v2/backend/app/data/` — module where new constants land
