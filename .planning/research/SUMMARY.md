# Project Research Summary

**Project:** JD Builder v4.0 — Seven-Elements Conversational Architecture
**Domain:** GC/DND HR job description builder — React 18 SPA + FastAPI on Jetson AGX Orin (ARM64)
**Researched:** 2026-06-19
**Confidence:** HIGH

## Executive Summary

JD Builder v4.0 extends a mature v3.0 production codebase (Phases 1–25 complete, 188+ tests) to surface the full TBS Accessible JD Template Part 2 structure as a conversational experience. The seven Part 2 elements — Organizational Context, Client Service Results, Key Activities, Skills, Effort, Responsibilities, Working Conditions — are already partially captured by the system; v4.0 adds the two missing conversational steps (Org Context and Responsibilities Narrative), connects all seven to a completeness audit, and exposes them via structured JSON/CSV export for workforce analytics. A Manager-Track UX branches the experience for hiring managers who should never see OG codes or JES terminology. The entire feature set is implementable with zero new pip or npm dependencies — all capabilities map to stdlib, Pydantic v2, FastAPI, and React patterns already in production.

The recommended build sequence is strictly dependency-ordered: Org Context step first (Phase 26) because it creates the new WD fields that every downstream feature reads; Responsibilities Narrative and Completeness Audit together next (Phase 27) because the audit is trivial once the fields exist and validates field plumbing immediately; Manager-Track UX third (Phase 28) as a UI-only branch with no model changes; Enhanced Poster and Structured Export last (Phase 29) as output-layer features that consume all prior work via the shared `build_seven_elements()` helper. The phasing aligns with the feature dependency graph confirmed across all four research files.

The dominant risks are not architectural — the patterns are proven. They are integration discipline risks: silent PATCH drops when new fields are added to WorkDescription but not WDPatchRequest; stepIndex regression when STEPS array gains entries and localStorage carries a stale integer; the completeness audit producing false results by reading the wrong source for org_context (derived text vs. typed field); and the Manager-Track requiring `require_og_confirmed` to be bypassed for manager-mode export without breaking the existing advisor gate. Each risk has a clear mitigation strategy identified in PITFALLS.md and must be addressed in the phase where the risk first arises.

---

## Key Findings

### Recommended Stack

Zero new dependencies for v4.0. The entire feature set is built on the existing stack: FastAPI 0.128.8 + Pydantic v2.12.5 (new model fields, new routes), stdlib `csv` + `json` (structured export), React 18 + existing `useState` pattern (Manager-Track UX), and the already-installed docxtpl 0.18.0 (poster template update). pandas 2.3.3 is confirmed installed on aarch64 but is not used for the 7-row CSV export — the stdlib `csv.DictWriter` + `io.StringIO` pattern produces RFC 4180-compliant output with zero import overhead. If the export scope grows to multi-sheet XLSX or analytics pivot tables, pandas is already available with no pip change required.

**Core technologies and their v4.0 roles:**
- **FastAPI + Pydantic v2:** New Optional fields on WorkDescription (`org_context`, `responsibilities_narrative`); new elements router (`app/api/elements.py`) with three endpoints; `extra="ignore"` on WorkDescription handles legacy row backward compatibility with no migration.
- **stdlib csv + json:** Structured export routes — `csv.DictWriter` with `utf-8-sig` encoding for Excel compatibility; `json.dumps` with `ensure_ascii=False` for French characters. No polars, no pandas for this path.
- **React useState (12th slice):** `userRole` state persisted to localStorage key `jd-builder-v2-role` using the existing lazy-init pattern. `elementStatuses` state populated by `POST /api/wd/{id}/validate-elements` on review entry.
- **docxtpl + build_poster_template.py:** Poster template binary updated via existing build script; `_build_poster_context()` gains org_context and key_activities keys.
- **No state management library:** The 11 existing useState slices do not meet the threshold (4+ levels of prop drilling, cross-cutting complexity) that would justify Zustand, Redux, or React Context.

### Expected Features

**Must have (table stakes) — v4.0 scope:**
- Org Context conversational step capturing the 4 TBS Accessible Template sub-elements (org unit, reports-to OG/level, work stream, additional context)
- `organizational_context` rendered above Client Service Results in document preview and export, per TBS template structure
- Responsibilities Narrative step gated on supervisory signal (`supervises != 'none'` OR `og_level >= 4`), capturing direct reports, financial signing authority, project leadership, decision latitude
- Per-element completeness badge in Review phase showing populated / derived / missing / not-applicable for all 7 elements
- Manager-Track UX: role selector at entry, suppression of OG/JES/CBA terminology in all user-visible strings, "draft for advisor" export watermark
- `POST /api/wd/{id}/export/json` and `POST /api/wd/{id}/export/csv` — structured 7-element data for workforce analytics
- Enhanced job poster with "About the Organization" section sourced from org_context

**Should have (differentiators):**
- SJD pre-fill of org_context from existing `sjd_source.organizational_context` on `POST /api/wd/{id}/sjd-start`
- "Jump to fill" links from completeness badge to the relevant STEPS entry via existing `jumpToExchange(idx)`
- `responsibilities_applicable` flag in completeness audit and CSV export to distinguish IC positions (null by design) from supervisory positions that forgot to fill
- `data_completeness` column in CSV encoding full / approximate / missing for non-EC groups that lack per-factor JES scores
- Soft gate on export when elements are missing (acknowledge dialog, not hard block)
- Provenance metadata in JSON export (`sjd_sourced`, `audit_run`, `noc_confirmed`, `schema_version`)
- Plain-language section labels in manager mode ("Physical demands" instead of "Effort", "Work environment" instead of "Working Conditions")

**Defer to v5+:**
- DND org chart directorate dropdown (requires parsing `DND_Org_26-Feb-2026-L3-FINAL_v2.xlsx` — data quality check needed first)
- OaSIS skills crosswalk in JSON export (NOC to OaSIS code mapping not yet built; data is present in `data/OASIS-2025-Taxonomy.json`)
- Bulk export `GET /api/export/bulk/json?og_code=EC` (multi-session state; out of scope for single-user Jetson app)
- Multi-session advisor review queue for manager-created WDs
- Advisor "preview as manager" toggle
- Dedicated Socratic questions for Effort and Working Conditions (currently derived from JES factors; Julian's directive for v4 is to keep that path)

### Architecture Approach

v4.0 makes additive changes to the existing file structure — no new top-level directories, no new services, no routing changes to main.py beyond a single router mount. The one new file is `app/api/elements.py`, which co-locates three endpoints with high domain cohesion (validate-elements, export/json, export/csv). The central architectural decision is the shared `build_seven_elements(wd) -> dict` function in `export_service.py`, which becomes the single source of truth for reading all 7 Part 2 elements from a WorkDescription — consumed by JSON export, CSV export, and (optionally) the completeness audit. This prevents the logic from being duplicated across three endpoints.

**Major components and their v4.0 responsibilities:**

1. **WorkDescription model** — gains `org_context: Optional[str]`, `responsibilities_narrative: Optional[str]`, and `user_role: str = "advisor"` as root-level fields (not in record dict), because these fields are read by the export pipeline and must be typed and directly accessible without parsing the freeform record blob.
2. **`app/api/elements.py` (new)** — three endpoints: `POST /validate-elements` (completeness audit, no OG gate), `POST /export/json` (structured analytics export), `POST /export/csv` (flat tabular export). Mounted in main.py alongside existing routers.
3. **`build_seven_elements(wd)` in export_service.py** — shared helper mapping all 7 Part 2 elements to their WD source fields; uses `_factor_category_map()` for JES bucketing; calls `_build_organizational_context_text()` as fallback for org_context. Called by both JSON and CSV routes.
4. **`build_elements_status(wd)` in export_service.py** — dedicated completeness logic function implementing the 5-state matrix for JES-derived elements (EC with scores / EC without scores / non-EC with level / non-EC without level / not-applicable). Single source of truth for completeness; consumed by the audit endpoint and the CSV `data_completeness` column.
5. **`data.jsx STEPS` additions** — `org_context` step inserted in Phase 0 block (after branch, before reports_to_military); `responsibilities_narrative` step inserted in Phase 3 block with `visible` predicate checking `answers.supervises?.id`.
6. **Manager-Track UX in app.jsx** — `userRole` state slice (localStorage-persisted); pre-STEPS role selector rendered when `userRole === null`; `userRole` passed as prop to ReviewState, DocumentPane, ClassBlock; manager mode suppresses OG/JES/CBA panels via conditional rendering.

### Critical Pitfalls

1. **stepIndex regression on STEPS array extension** — when Phase 26 inserts the org_context step, any session with a persisted `stepIndex` integer in localStorage will resume at the wrong step. Fix: switch session resume from integer position to `STEPS.findLastIndex(s => answers[s.id] !== undefined)` before adding any new STEPS entries. Must be addressed in Phase 26 before the first new step is written.

2. **WDPatchRequest co-update rule** — adding a field to WorkDescription without simultaneously adding it to WDPatchRequest causes the frontend commit() to silently drop the field (Pydantic extra="ignore" swallows the unknown key with HTTP 200, giving no indication of failure). Mitigation: same-commit rule — every new WorkDescription field that is advisor-patchable must have a corresponding WDPatchRequest field added in the same git commit, with a roundtrip test (PATCH to GET, assert field non-None) gating merge.

3. **user_role must not enter the answers dict** — if `user_role` is stored inside the `answers` dict (alongside Socratic answers), the PATCH endpoint will write it into the WD record, making role a property of the document rather than a session preference. A mid-session role switch then carries forward answers from the prior role's flow. Fix: `userRole` lives exclusively as a React state slice and localStorage key; it is never sent in the WD PATCH body.

4. **Completeness audit reading the wrong org_context source** — `_build_organizational_context_text()` always returns a non-empty synthesized string from record fields (branch, reports, title, summary), which would make every WD appear as "org_context populated" in the audit even if the advisor never went through the Phase 26 step. Fix: the audit must check `wd.org_context` (the typed root field), not the derived text. Export uses the derived text as fallback; audit uses only the typed field as signal.

5. **require_og_confirmed fires 409 for manager-track WDs at export** — manager-mode WDs deliberately never have `confirmed_og` set. The existing export routes call `require_og_confirmed` unconditionally, producing 409 for every manager-track export. Fix: add `wd_type: Literal["advisor", "manager"] = "advisor"` to WorkDescription; the gate skips for manager-type WDs. Manager-draft exports render `[ADVISOR TO COMPLETE]` placeholder OG strings — already the default behavior of `_og_level_str("", 0)`.

---

## Implications for Roadmap

Based on the cross-feature dependency graph confirmed across all four research files, the build order is deterministic. Features 1 and 2 create new WD fields; all other features read those fields. Feature 3 (audit) validates the field contract immediately. Feature 4 (Manager-Track) is UI-only and independent but must come before Features 5 and 6 ship to users so export labels are correct. Features 5 and 6 are pure output-layer additions once the `build_seven_elements()` helper exists.

### Phase 26: Org Context Conversational Step (Feature 1)
**Rationale:** Foundation phase. Creates `org_context` typed field on WorkDescription and WDPatchRequest; adds STEPS entry; wires SJD pre-fill. Every downstream feature (completeness audit, enhanced poster, JSON/CSV export) reads `wd.org_context`. Must come first.
**Delivers:** Advisor can capture TBS-compliant organizational context via conversation; org_context renders in document preview above Client Service Results; SJD pre-fill sets the field automatically from sjd_source.
**Addresses:** Feature 1 (Org Context); also establishes the `_build_wd_context` preference for typed field over synthesized fallback.
**Avoids:** stepIndex regression (fix resume-by-last-answered before inserting new step); org_context None-on-legacy sentinel (`seven_elements_flow` boolean or `schema_version` bump); WDPatchRequest co-update rule.
**Research flag:** Standard patterns — no phase research needed. All implementation details are fully specified in ARCHITECTURE.md and PITFALLS.md.

### Phase 27: Responsibilities Narrative + Completeness Audit (Features 2 + 3)
**Rationale:** Build together. The responsibilities_narrative field is the last new WD field; the completeness audit is a read-only function over both new fields and existing JES/qualification fields. Shipping the audit immediately after both fields exist validates the field contract before the export layer is built on top of it.
**Delivers:** Gated Responsibilities Narrative step for supervisory/senior positions; `POST /api/wd/{id}/validate-elements` endpoint; completeness badge in ReviewState showing N/7 elements with populated/derived/missing/not-applicable status.
**Addresses:** Features 2 + 3; establishes `build_elements_status()` as the shared completeness logic function.
**Avoids:** responsibilities_narrative vs. JES Responsibility name collision (use distinct keys in audit response); `responsibilities_applicable` flag for IC positions (null-by-design, not null-by-error); JES-derived Effort/WC false negatives when jes_total_points is None (audit triggers score_jes_v2 as side effect); 5-state JES matrix (EC scored / EC unscored / non-EC with level / non-EC without level / not-applicable) must be fully implemented and tested.
**Research flag:** Standard patterns — well-specified in ARCHITECTURE.md Q2 and PITFALLS.md sections 2 and 4.

### Phase 28: Manager-Track UX (Feature 4)
**Rationale:** UI-only change with no model dependencies. Independent of Features 1-3 in terms of data model, but must be built after Features 1 and 2 are stable so the manager path covers the complete conversation flow including org_context and responsibilities_narrative steps. Built before Features 5 and 6 so export labels are correct when those features ship.
**Delivers:** Role selector at app entry; userRole state slice persisted to localStorage; manager mode suppresses OG/JES/CBA panels in document preview, classification block, and ReviewState; manager-track WD exports as "DRAFT — PENDING CLASSIFICATION" without 409 gate error.
**Addresses:** Feature 4 (Manager-Track UX).
**Avoids:** user_role in answers dict (keep as separate React state, never sent in PATCH body); require_og_confirmed 409 for manager WDs (add wd_type field or force_draft bypass); amendment panel state leaks across role contexts (add userRole to useEffect deps; clear role-specific state on role change); conditional rendering audit across all components that surface advisor-specific terminology.
**Research flag:** Moderate complexity — the conditional rendering audit (scanning every user-visible string in STEPS, document.jsx, conversation.jsx, and export labels) requires a systematic internal pass. No external research needed.

### Phase 29: Enhanced Job Poster + Structured Data Export (Features 5 + 6)
**Rationale:** Output-layer phase. Both features share the `build_seven_elements(wd)` helper; building them together avoids writing the function twice. The poster is additive to `_build_poster_context()`; the JSON/CSV routes are new endpoints in elements.py. All source data (org_context, responsibilities_narrative, jes_scores, duties, qualification) is available after Phases 26-27.
**Delivers:** Enhanced job poster with "About the Organization" section; `POST /export/json` returning analytics-ready 7-element JSON with provenance metadata; `POST /export/csv` returning flat tabular format with one row per duty, utf-8-sig encoding, and data_completeness column; frontend download buttons in ReviewState.
**Addresses:** Features 5 + 6.
**Avoids:** Naive string interpolation for CSV (use csv.DictWriter with QUOTE_ALL; test roundtrip with commas/quotes/newlines in duty text); non-EC empty Effort/WC columns (emit synthetic approximate row using NON_EC_TOTALS; add data_completeness column); combining JSON/CSV into a single content-negotiation route (keep separate routes per established /export/docx, /export/poster, /export/pdf pattern); _factor_category_map() is the single source for JES bucketing — never read score.get('category') directly.
**Research flag:** Standard patterns — fully specified. CSV encoding and non-EC column handling are the only implementation sub-problems requiring care; both are addressed in PITFALLS.md section 3.

### Phase Ordering Rationale

- Features 1 and 2 must precede everything because they create the WD fields all other features read. There is no shortcut.
- Feature 3 (completeness audit) is bundled with Feature 2 because its implementation is trivial once both fields exist and it provides immediate validation of the field plumbing.
- Feature 4 (Manager-Track) is independent of the data model but must precede Features 5 and 6 so export labels and the "draft for advisor" watermark are in place when those outputs ship.
- Feature 6 (Structured Export) is bundled with Feature 5 (Enhanced Poster) because they share `build_seven_elements()`. Writing this function once and testing it thoroughly before wiring two endpoints to it is lower risk than writing it twice.
- The PITFALLS.md phase warnings are explicit: stepIndex fix belongs in Phase 26 before any STEPS entry is added; WDPatchRequest co-update discipline belongs in Phases 26 and 27; require_og_confirmed bypass belongs in Phase 28; csv.DictWriter pattern belongs in Phase 29 before any export code is written.

### Research Flags

Phases with standard patterns (skip research-phase for all four phases):
- **Phase 26:** Fully specified. WorkDescription field extension, STEPS entry, SJD pre-fill hook, commit() mirror — all are existing patterns with exact implementation in ARCHITECTURE.md.
- **Phase 27:** Fully specified. Gated STEPS entry (reuses isStepVisible pattern), validate-elements endpoint (pure computation over existing fields), completeness badge (sibling to existing audit panel in ReviewState).
- **Phase 28:** No external research needed. Conditional rendering audit is internal work; localStorage persistence follows existing pattern; wd_type bypass for require_og_confirmed is clearly defined.
- **Phase 29:** Fully specified. `build_seven_elements()` implementation is fully written in ARCHITECTURE.md Q3. CSV encoding pattern and non-EC handling are specified in PITFALLS.md section 3.

No phase requires deeper research during planning. All implementation details are resolved. The only open questions (DND org chart dropdown, NOC to OaSIS crosswalk) are explicitly deferred to v5+.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All findings from direct execution on Jane (ARM64); confirmed versions; stdlib csv test executed; no new dependencies — zero uncertainty |
| Features | HIGH | Primary sources: TBS Accessible JD Template (May 2024) and Writing Guide (June 2023) read directly; 7 Part 2 element definitions authoritative; UX patterns for manager-track at MEDIUM (web synthesis) |
| Architecture | HIGH | Based on direct codebase read of all modified files: models/work_description.py, api/wd.py, export_service.py, data.jsx, app.jsx; isStepVisible pattern, WDPatchRequest setattr loop, _factor_category_map() all confirmed |
| Pitfalls | HIGH | All pitfalls are grounded in specific prior-phase failures documented in the project history (Phase 20 UAT regressions, Phase 21 sub-group picker bug, Phases 15-17 STEPS ordering bugs); not speculative |

**Overall confidence:** HIGH

### Gaps to Address

- **NOC to OaSIS code mapping** — `data/OASIS-2025-Taxonomy.json` should contain the crosswalk between NOC 2021 codes (stored on WD as `confirmed_noc`) and OaSIS codes. This mapping is needed only for the optional OaSIS skills crosswalk in the JSON export, which is deferred to v5+. Verify the mapping exists before scoping it into the v5 roadmap.

- **DND org chart directorate dropdown** — `DND_Org_26-Feb-2026-L3-FINAL_v2.xlsx` exists in the project. A quick data quality check (parse L3 column, count distinct directorate names, assess string cleanliness) would determine whether this is a one-day enhancement or a multi-day data cleaning project. Deferred to v5+ pending that check.

- **Effort and Working Conditions as explicit Socratic questions** — FEATURES.md notes this was in the Phase 23 deferred table as "dedicated questions are v4." ARCHITECTURE.md's `build_seven_elements()` derives both from JES factor scores, not new Socratic steps. Julian's directive should be confirmed: does v4.0 add Socratic questions for Effort and WC, or continue the JES-derivation path? Research treats it as the latter; if the directive changes this, Phase 27 scope expands.

- **Manager-track plain-language Socratic question set** — must be confirmed before Phase 28 begins: verify that the QUESTION_BANK questions in data/constants.py use OG-neutral language already (per QUES-02 constraint from prior phases) so the manager path is a display-label change, not a new signal accumulation architecture.

- **CSV column set for Julian's analytics pipeline** — the CSV schema (one row per duty with scalar fields repeated) is designed for Julian's anticipated workflow. The exact column set may need one iteration after Julian reviews a sample output from Phase 29.

---

## Sources

### Primary (HIGH confidence)
- `v2/backend/app/models/work_description.py` — WorkDescription field inventory, extra="ignore" config, existing typed fields vs. record dict pattern
- `v2/backend/app/api/wd.py` — WDPatchRequest field list, setattr patch loop
- `v2/backend/app/services/export_service.py` — `_build_wd_context()`, `_build_organizational_context_text()`, `_factor_category_map()`, `_build_poster_context()` — all inspected directly
- `v2/backend/app/api/export.py` — existing separate-route pattern for /export/docx, /export/poster, /export/pdf
- `v2/frontend/src/app.jsx` — 11 existing useState slices, localStorage pattern, commit() mirror list, useEffect triggers
- `v2/frontend/src/data.jsx` — STEPS array (28 entries), isStepVisible() predicate, accumulateSignals(), PHASES
- `v2/frontend/src/conversation.jsx` — ReviewState component structure, audit panel pattern (Phase 24)
- `v2/backend/requirements.txt` — pinned versions confirmed on aarch64
- `data/AI Docs/Accessible Job Description Template (1).docx` — TBS May 2024; 7 Part 2 element section structure authoritative
- `data/AI Docs/Job Description Writing Guide.docx` — TBS June 2023; Responsibilities section definition authoritative
- Direct execution on Jane: pandas 2.3.3 on aarch64 confirmed; stdlib csv 7-row roundtrip test confirmed

### Secondary (MEDIUM confidence)
- `data/OASIS-2025-Skills.json`, `data/OASIS-2025-WorkContext.json` — OaSIS 2025 field schemas; analytics export schema designed to align with these dimensions
- TBS Directive on Classification (web) — organizational context mandatory elements confirmed
- UI Patterns (ui-patterns.com) — completeness meter design: non-sequential optional task progress indicator
- Multi-role UX research (web synthesis) — navigation adaptation principle; role selector card pattern

### Tertiary (LOW confidence)
- Julian's analytics team column preferences for CSV — anticipated from OaSIS data structure and stated use cases; actual column set to be validated after Phase 29 sample output

---
*Research completed: 2026-06-19*
*Ready for roadmap: yes*
