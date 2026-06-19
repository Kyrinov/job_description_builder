# Pitfalls Research — v4.0 Seven-Elements Conversational Architecture

**System:** React 18 SPA + FastAPI, ARM64 (Jetson AGX Orin), SQLite, docxtpl, WeasyPrint
**Researched:** 2026-06-19
**Scope:** Integration pitfalls for adding the 6 v4.0 features to the existing v2.0/v3.0 production codebase.
**Prior art:** The v3.0 PITFALLS.md (template contract drift, CBA parsing, writing guide false-positives, SJD field mapping, ARM64 dependencies) is assumed read. This document covers only the NEW risks introduced by v4.0's four pitfall categories.

---

## 1. Role-Based UX Branching — Gating STEPS on user_role

### 1a. The isStepVisible() predicate pattern is not designed for multi-role exclusion

**What goes wrong:** The existing `isStepVisible(step, answers)` function in `data.jsx` (lines 459–488) operates as a purely additive gate — it hides steps whose prerequisite answer is absent. It was designed to answer "has the sector-gate question been answered yet?" (show cluster step) not "does the current user type want to see this?" (hide classification mechanics).

If Manager-Track hides `og_confirm`, `og_level`, `qb_*` classification steps, and `jes_scoring` by checking a `user_role` stored in `answers`, the predicate will evaluate correctly at first render. The dangerous moment is step-index persistence: `stepIndex` is stored in `answers` and carries across `localStorage` restores. An advisor who switches to manager mode mid-session will have `stepIndex` pointing at an `og_confirm` step that `isStepVisible` now returns false for. The `activeStepIndex` memoization in `app.jsx` (lines 120–125) snaps forward to the first visible step — but if `og_confirm` was already answered in a prior session, the `answers` dict retains the `og_confirm` value. The WD record then carries a confirmed OG that the manager-track flow never surfaced, but that the export and completeness audit will try to use.

This is not theoretical: Phase 21 had the exact same pattern where a sub-group picker read a committed record instead of draft value and rendered incorrectly until a component-level `useEffect` fetch was added.

**Prevention:**
- Store `user_role` as a top-level React state slice (not inside `answers`), so it never persists in the WD record or contaminate the answers-driven step visibility logic.
- Add a role-change handler that calls `handleStartOver()` (or a scoped equivalent that clears classification answers) when `user_role` changes. Never allow a mid-session role switch to silently carry forward answers from a different role's flow.
- In `isStepVisible`, add manager-track exclusions as an explicit case that checks `user_role` state — but pass `user_role` as a third argument rather than embedding it in `answers`. Mixing role signal into the answers dict creates a coupling where the step predicate depends on values the WD PATCH endpoint also reads, causing the backend and frontend to disagree about what the session contains.
- Write a test: switch role from advisor to manager after completing `og_confirm`, assert that `isStepVisible('og_confirm', answers)` returns false AND that `answers.og_confirm` is cleared.

**Phase to address:** Phase 29 (Manager-Track UX), step-predicate design, before any new STEPS entries are written.

---

### 1b. Classification gate (require_og_confirmed) fires for manager-track WDs on export

**What goes wrong:** `require_og_confirmed` in `classification_gate.py` raises HTTP 409 if `wd.confirmed_og` is None. The existing export endpoints (`/export/docx`, `/export/poster`, `/export/pdf`) call this gate unconditionally. A manager-track WD is deliberately incomplete — `confirmed_og` is None because the manager never sees the OG confirmation step. The export endpoint will therefore return 409 for every manager-track WD, which is the opposite of the intended UX.

The DOCX export route also self-heals JES scores when `jes_total_points is None`, which will fire for manager-track WDs and fail silently because `og_code` will be empty. The `score_jes_v2` call will receive an empty `og_code` and return without writing anything, leaving `jes_total_points` still None. The route proceeds to call `generate_wd_docx`, which calls `_build_wd_context`, which calls `_og_code_from(wd)` — this returns an empty string, and `_og_level_str("", 0)` returns an empty string. The resulting template context has `"og_level": "[ADVISOR TO COMPLETE]"` throughout. This is actually acceptable behaviour for a manager-draft document, but only if the 409 gate is bypassed first.

**Prevention:**
- Add a `wdType` field to `WorkDescription` (e.g., `wd_type: Literal["advisor", "manager"] = "advisor"`). Use this in `require_og_confirmed` to skip the gate for manager-type WDs.
- Alternatively, keep the gate but add a `force_draft=true` query param to the export endpoints for manager-track exports, which bypasses the OG check and generates a watermarked "DRAFT — PENDING CLASSIFICATION" document.
- The manager-draft export should use a different document template or header banner so the output is visually distinct from a finalised advisor WD.
- Do not add manager-track logic to `_build_wd_context` by inserting if/else branches on `wd_type` — that function is already 130+ lines. Create a `_build_manager_context(wd)` function that reuses the safe portions of the context.

**Phase to address:** Phase 29 (Manager-Track UX), export integration step. Gate bypass must be implemented before manager-track export is tested.

---

### 1c. Amendment panels, audit findings, and duty hints are keyed to wd_id, not user_role — state leaks between role contexts

**What goes wrong:** `amendmentNotes`, `amendmentPanels`, `auditFindings`, and `dutyHints` are loaded per `wd_id`. If an advisor converts a manager-track WD to a full advisor WD (or vice versa), these state slices will be stale because they were populated under the prior role's flow. The amendment hydration `useEffect` (app.jsx line 171) fires on `[wd_id, reviewing]` — it correctly re-fetches on review, but does not re-fetch when `user_role` changes. A manager who enters review will get amendment panels intended for advisor sections (e.g., "Classification" section) that have no visual counterpart in manager mode, and those panel states will be in `amendmentPanels` but never rendered — they are orphaned UI state that wastes memory and could confuse future state reads.

**Prevention:**
- Add `user_role` to the dependency array of the amendment hydration `useEffect` so it refetches when role changes.
- When `user_role` changes, explicitly clear `auditFindings`, `dutyHints`, and `amendmentPanels` state.
- The Section keys used in `amendmentPanels` (e.g., `'cls'`, `'drf'`) must be validated against the sections actually rendered in the current role's document view. Add a filter: `Object.fromEntries(Object.entries(amendmentPanels).filter(([k]) => VISIBLE_SECTIONS_FOR_ROLE[user_role].includes(k)))` before passing to the document component.

**Phase to address:** Phase 29 (Manager-Track UX), state isolation design step.

---

## 2. Additive Schema Migration — Optional Fields on a Pydantic JSON Blob

### 2a. Legacy WD rows silently deserialise missing fields as None — correct by accident, until it isn't

**What goes wrong:** `WorkDescription` uses `model_config = ConfigDict(extra="ignore")`. When a new Optional field (e.g., `org_context: Optional[str] = None`) is added to the model and a legacy row is loaded via `WorkDescription.model_validate_json(row["data"])`, the missing key is silently populated as `None`. This is the intended Pydantic v2 behaviour for Optional fields with defaults.

The trap is in the completeness audit (Phase 28). `POST /api/wd/{id}/validate-elements` will check whether each of the 7 elements is populated. For a legacy WD row that was created before Phase 26, `org_context` will be `None` — correctly flagged as missing. But `client_service_results` lives in `record` (a freeform dict), not as a typed field, and `responsibilities` will also come back as `None`. The completeness audit must therefore distinguish between:

- Field genuinely not collected (legacy WD): show "Not collected yet"
- Field collected but blank (advisor deliberately left empty): show "Advisor left blank"
- Field JES-derived but JES not yet run: show "Run JES scoring first"
- Field populated: show "Complete"

If the audit treats all four states as "missing", it will flag every legacy WD as fully incomplete, which is false and undermines trust in the tool.

**Prevention:**
- Do not add `org_context` and `responsibilities_narrative` as bare Optional fields. Add them alongside a corresponding `{field}_collected_at: Optional[datetime]` sentinel or a `metadata: dict` blob on WorkDescription that tracks which fields were explicitly set during the v4.0 flow. A `None` value without the sentinel means "not collected yet"; a `None` with the sentinel means "advisor explicitly skipped or left blank."
- Alternatively, encode completeness state in `schema_version`. Currently `schema_version = 1` for all rows. Bump to `schema_version = 2` when a WD has gone through the v4.0 flow. The completeness audit returns "not applicable — legacy WD" for `schema_version < 2` rows.
- The simpler approach: add a `seven_elements_flow: bool = False` field. The Phase 26 conversational step sets it to True when `org_context` is committed. The completeness audit gates all 7-element checks on `seven_elements_flow`.
- Do not put the completeness logic in `_build_wd_context` — it already has 29 variables. Create a dedicated `build_elements_status(wd) -> dict` function.

**Phase to address:** Phase 26 (Org Context Step) — schema design. Must be decided before any new fields are committed to the model. Phase 28 (Completeness Audit) will depend on this decision.

---

### 2b. WDPatchRequest does not include new v4.0 fields — PATCH silently drops them

**What goes wrong:** `WDPatchRequest` in `wd.py` currently lists every patchable field explicitly. When `org_context` and `responsibilities_narrative` are added to `WorkDescription`, they must also be added to `WDPatchRequest`. If a developer adds the field to `WorkDescription` but forgets to add it to `WDPatchRequest`, the SPA's commit() call will include `org_context` in the request body, `WDPatchRequest(model_config=ConfigDict(extra="ignore"))` will silently drop it, the PATCH will succeed with HTTP 200, and the field will never be written to the database. The SPA will believe it succeeded, but the export and completeness audit will see `None`.

This has happened before: Phase 20 required 6 UAT fix commits after initial ship, several of which were caused by fields present in the frontend request body but not plumbed through the backend response or PATCH model.

**Prevention:**
- When adding a new WorkDescription field intended to be patchable, add it to `WDPatchRequest` in the same commit, not a later one.
- Add a test that creates a WD, PATCHes with a non-None value for each new field, GETs the WD, and asserts the field is non-None. This closes the silent-drop gap.
- Consider a property test: serialize `WDPatchRequest.model_fields.keys()` and `WorkDescription.model_fields.keys()` and assert that every `WDPatchRequest` field is also on `WorkDescription` — and that every new `WorkDescription` field that is NOT intentionally server-managed (like `id`, `created_at`, `schema_version`) has a corresponding `WDPatchRequest` entry.

**Phase to address:** Phase 26 (Org Context Step) and Phase 27 (Responsibilities Narrative), backend model step. One failing test per new field.

---

### 2c. record dict vs. typed field ambiguity for new 7-element fields

**What goes wrong:** The existing system has a schizophrenic data storage pattern. Some fields are typed on `WorkDescription` (`confirmed_og`, `og_level`, `jes_scores`). Others live in the freeform `record: dict` (`client_service_results`, `title`, `branch`, `reports`, `quals`, `duties`). The `_build_wd_context` function reads from both (`record.get("client_service_results")`, `wd.qualification`, `wd.duties`). The completeness audit will need to check both locations for each of the 7 elements, and if the source of truth is wrong for even one element, the audit will give a false result.

For v4.0, `org_context` and `responsibilities_narrative` could be stored either way. Storing in `record` is consistent with `client_service_results` but makes the field invisible to the Pydantic schema and untyped. Storing as typed fields is more correct but requires schema migration and careful WDPatchRequest plumbing.

The completeness audit is especially vulnerable: if `org_context` is stored in `record` but the audit checks `wd.org_context`, it returns None always. If `org_context` is stored as a typed field but `_build_wd_context` reads `record.get("org_context")`, the template renders the placeholder always.

**Prevention:**
- Adopt a consistent rule before Phase 26: fields that appear in the Accessible JD Template's 7 Part 2 sections are typed fields on `WorkDescription`. Fields that are Part 1 identification data (position number, branch, title) remain in `record`. Document this rule in a comment at the top of `work_description.py`.
- After making this decision, audit `_build_wd_context` for all existing 7-element reads and ensure they use the correct source. Specifically: `client_service_results` currently reads `record.get("client_service_results")` — if the rule above is adopted, this should be a typed field. Decide before Phase 26 whether to migrate it or leave it as an exception.

**Phase to address:** Phase 26 (Org Context Step), schema design. This is a pre-condition for all 7-element completeness logic.

---

## 3. CSV Export Edge Cases

### 3a. Duty text with embedded commas, newlines, and double-quotes causes silent row corruption in naive CSV

**What goes wrong:** GC work description duty text routinely contains commas ("Plans, coordinates and manages") and can contain double-quotes if an advisor pastes text from Word. Python's `csv` stdlib correctly wraps fields in double-quotes and escapes internal double-quotes as `""`. The silent corruption risk is not in the library — it's in not using the library.

Any implementation that uses string interpolation (`f"{duty.text},{og_code}\n"`) or `str.join()` to build CSV will corrupt rows whose fields contain commas, newlines (multi-line duty text is legal), or double-quotes. The resulting file will parse incorrectly in Excel with no error — it will silently misalign columns.

The second corruption vector: the 7-element CSV will export `effort_factors` and `working_conditions_factors` as JES factor rows. Each JES factor has a `rationale` field (a free-text LLM-generated string). Rationale text can contain all three dangerous characters.

**Prevention:**
- Use `csv.DictWriter` with `quoting=csv.QUOTE_ALL`. Never build CSV strings manually.
- Use `io.StringIO` as the in-memory buffer, not `io.BytesIO`. Write to StringIO, encode as UTF-8-with-BOM (`utf-8-sig`) before returning the Response. The BOM is required for Excel on Windows to auto-detect encoding; without it, French characters (accents, cedillas) in duty text will display as mojibake when the file is opened by Julian's team.
- For array-valued columns (multiple effort factors, multiple duties), join with a pipe delimiter (`|`) not a comma, and document this in the export specification. Do not use nested CSV or JSON within CSV cells.
- Add a roundtrip test: generate a CSV from a WD whose duty text contains `"has commas, quotes\", and a newline\nembedded"`, parse it back with `csv.DictReader`, assert field values match exactly.

**Phase to address:** Phase 30 (Structured Data Export), implementation step. Establish the `csv.DictWriter + utf-8-sig` pattern before writing a single line of export code.

---

### 3b. JES-derived Effort and Working Conditions are absent for non-EC groups — CSV has structurally empty columns

**What goes wrong:** The 7-element CSV maps: Effort → JES effort factors, Working Conditions → JES working conditions factors. For non-EC groups (AS, IT, FI, MT, FS, etc.), `wd.jes_scores` is either empty or contains only a totals dict (the `NON_EC_TOTALS` path), not per-factor scored rows. The completeness audit (Phase 28) will show these as "JES-derived — not available for this group."

If the CSV export proceeds with an empty `effort_factors` list and emits empty cells for those columns, Julian's analytics pipeline will interpret them as missing data for non-EC positions. This is technically correct (the data does not exist) but may cause Julian's aggregation queries to undercount non-EC positions or treat them as data-quality errors.

**Prevention:**
- For non-EC groups, substitute the `NON_EC_TOTALS` approximate point total into a synthetic effort row: `{"factor_name": "Total (approximate)", "points": NON_EC_TOTALS[og_code][og_level], "rationale": "Non-EC group — level-description JES; individual factor scores not available"}`. This gives Julian's pipeline a non-null value with a machine-readable caveat.
- Add a `data_completeness` column to the CSV that encodes `"full"` (EC with all 9 factors scored), `"approximate"` (non-EC with level totals), or `"missing"` (JES not run). Julian's pipeline can filter on this column instead of treating null effort columns as data quality failures.
- Document the `data_completeness` values in the export endpoint's docstring and in the completeness audit response.

**Phase to address:** Phase 28 (Completeness Audit), element status design — the audit must define what "derived but approximate" means before Phase 30 implements it in the CSV.

---

### 3c. Supervisory/senior gate for Responsibilities Narrative means some WDs legitimately have null Responsibilities — CSV must distinguish null-by-design from null-by-error

**What goes wrong:** Phase 27 gates the Responsibilities Narrative step on `supervises != 'none'` (or equivalent). An individual-contributor WD will never have `responsibilities_narrative` populated — it is null-by-design, not null-by-error. The CSV export will emit an empty Responsibilities cell for all IC positions.

Julian's analytics pipeline cannot distinguish "IC position, field not applicable" from "supervisor position where the advisor forgot to complete the step." If Julian's team is counting completeness rates, IC positions will artificially deflate the rate.

**Prevention:**
- Add a `responsibilities_applicable: bool` field to the 7-element status (populated by the completeness audit) that encodes whether the Responsibilities Narrative step was visible to the advisor. Export this as a column in the CSV alongside the Responsibilities text column.
- In the completeness audit, set `responsibilities_applicable = (record.get("supervises") != "none")` using the same predicate as the STEPS gate. The audit result and the CSV must both encode this flag.
- Treat `responsibilities_applicable = False` as "complete" in the completeness badge, not "missing."

**Phase to address:** Phase 27 (Responsibilities Narrative), gate predicate design. The `responsibilities_applicable` flag must be defined here, before Phase 28 and Phase 30 consume it.

---

## 4. Completeness Audit False Positives and Negatives

### 4a. JES-derived Effort and Working Conditions — Phase 25 values not present until export-time self-heal fires

**What goes wrong:** Phase 25 added JES factor bucketing in `_build_wd_context` via `_factor_category_map()`. But JES scoring is triggered by the frontend chaining JES fetch off the WD PATCH at the `og_level` step (Phase 17 pattern). JES scores are written to `wd.jes_scores` when the advisor confirms the OG and level. The export self-heal in `export.py` re-runs `score_jes_v2` if `jes_total_points is None or all-factors-at-floor` — but this only fires at export time, not before.

The completeness audit at Phase 28 runs `POST /api/wd/{id}/validate-elements` before the advisor exports. If the advisor has confirmed OG and level but `jes_total_points` is None (JES scoring failed silently, or the advisor is on the Jetson with Ollama unavailable), the completeness audit will flag Effort and Working Conditions as "missing" — even though the data will be populated at export time by the self-heal path.

This produces a false negative: the completeness badge shows red for Effort and Working Conditions, the advisor panics or re-runs the flow, and the export succeeds anyway.

**Prevention:**
- The completeness audit for Effort and Working Conditions should not simply check `jes_scores is not None and len > 0`. It should check: `(og_code == "EC" and jes_total_points is not None) OR (og_code != "EC" and og_level is not None)`. Non-EC groups will always have level-approximate totals available once OG and level are confirmed — they do not require per-factor scores.
- For EC groups where `jes_total_points is None`, the audit should trigger `score_jes_v2` inline (the same self-heal the export does) and report status based on the result. The audit endpoint should not just read the persisted WD state — it should ensure JES is populated as a side effect.
- Add a test: create an EC WD with `jes_total_points = None` (simulating a failed scoring run), call `POST /api/wd/{id}/validate-elements`, assert that the endpoint triggers JES scoring and returns `"status": "populated"` for Effort and Working Conditions, not `"missing"`.

**Phase to address:** Phase 28 (Completeness Audit), element status logic for JES-derived elements.

---

### 4b. org_context is pre-filled by `_build_organizational_context_text()` — audit may show "populated" for a synthesised placeholder

**What goes wrong:** `_build_wd_context` calls `_build_organizational_context_text(wd)` to generate `organizational_context_text`. This function synthesises a context paragraph from `record.branch`, `record.reports`, `record.title`, and `record.summary` even when no dedicated `org_context` field exists. The output looks like: "Located within Strategic Policy Branch, and reporting to the Director, the Senior Policy Analyst performs coordination..."

Phase 26 adds an explicit `org_context` conversational step that lets the advisor write their own organizational context. If the completeness audit checks `wd.org_context is not None`, it will correctly identify Phase-26-captured context. But if it checks the derived value from `_build_organizational_context_text`, it will always return "populated" — even for legacy WDs that never went through the new step. The audit would then show 7/7 elements complete for all legacy WDs, which defeats the purpose.

**Prevention:**
- The completeness audit must check `wd.org_context` (the typed field added in Phase 26), NOT the output of `_build_organizational_context_text`. The synthesised context is a fallback for export — it is not evidence that the advisor has explicitly addressed the element.
- `_build_wd_context` should use `wd.org_context` if present, and fall back to `_build_organizational_context_text(wd)` only when `org_context is None`. This way the export always has something to render, but the audit correctly distinguishes the two cases.
- Name the typed field `org_context` (not `organizational_context` or `organizational_context_text`) to make it distinct from the template variable `organizational_context_text`. The naming collision is a latent bug waiting to happen: if a developer confuses the field with the template variable and writes `wd.organizational_context_text` in a PATCH, Pydantic will reject it (field does not exist) and the error will surface as a confusing 422, not a clear "wrong field name."

**Phase to address:** Phase 26 (Org Context Step), schema and template integration step.

---

### 4c. Responsibilities Narrative vs. the JES "Responsibility" factor — name collision creates audit ambiguity

**What goes wrong:** The 7 Part 2 elements include "Responsibility" — but in the JES scoring context, "Responsibility" refers to the JES Responsibility factor (a scored dimension of the EC JES, bucketed by `_factor_category_map()`). In the v4.0 context, "Responsibilities" refers to the Phase 27 narrative field about decision-making authority. These are two different things with nearly identical names.

The completeness audit must check both:
- Element 6 (Responsibilities): Is `wd.responsibilities_narrative` populated? (Phase 27 conversational field)
- JES Responsibility: Are `responsibility_factors` non-empty in `wd.jes_scores`? (Phase 17 JES scoring)

If the audit implementation conflates these (checking `responsibility_factors` instead of `responsibilities_narrative` for Element 6), it will always show EC positions as "complete" for Element 6 (because they have JES Responsibility factors) and non-EC positions as "missing" (because they have no per-factor scores) — the exact opposite of the intended logic.

**Prevention:**
- Name the Phase 27 field `responsibilities_narrative` (not `responsibilities` or `responsibility_text`) to force a naming distinction from `responsibility_factors` in the JES context.
- In the completeness audit response, use unambiguous keys: `"responsibilities_narrative_status"` for the Phase 27 field, `"jes_responsibility_status"` for the JES factor. Do not use a single `"responsibility"` key that could mean either.
- In `_build_wd_context`, the existing `responsibilities_text` variable is already populated from JES Responsibility factors (`responsibility_factors`). Phase 27's narrative is a separate document section — do not overwrite `responsibilities_text` with `wd.responsibilities_narrative`. Add a new template variable `responsibilities_narrative_text` for the Phase 27 content.
- Add a test that explicitly verifies: a WD with `jes_scores` containing a Responsibility factor but `responsibilities_narrative = None` should have `responsibilities_narrative_status = "missing"` in the completeness audit.

**Phase to address:** Phase 27 (Responsibilities Narrative), field naming. Must be resolved before Phase 28 implements the audit.

---

### 4d. Completeness audit "derived" status for JES fields must survive the seven_elements_flow=False case

**What goes wrong:** Phase 25 added JES factor bucketing. For EC groups, `jes_scores` contains all 9 factors with explicit point values. The Effort factors are: `["Physical Effort", "Sensory Demands", "Work Environment"]` (from `_factor_category_map()`). For non-EC groups, `jes_scores` is an empty list and `jes_total_points` is the approximate total.

The completeness audit must handle this matrix:

| OG type | JES run | Effort status | Working Conditions status |
|---------|---------|---------------|--------------------------|
| EC | Yes, complete | "populated" | "populated" |
| EC | No (not run) | "run JES first" | "run JES first" |
| EC | Partial (some floor) | "partially scored" | "partially scored" |
| Non-EC | Level confirmed | "derived (approximate)" | "derived (approximate)" |
| Non-EC | No level | "confirm level first" | "confirm level first" |

A simple `len(effort_factors) > 0` check collapses all five states into two (non-empty / empty), giving false positives for partial scoring and false negatives for non-EC groups with confirmed levels.

**Prevention:**
- Implement `build_elements_status(wd)` as a dedicated function (not inline in the endpoint) with explicit handling for each row of the matrix above. The function must be unit-tested against all five states.
- For partial EC scoring (some factors at degree=-1 sentinel), report "partially scored" rather than "populated" — the export self-heal will attempt to re-run, but the audit should flag it honestly.
- `build_elements_status` must be the single source of truth for completeness logic. Do not duplicate it in `_build_wd_context` or the CSV export. The CSV's `data_completeness` column should call the same function, not re-implement the logic.

**Phase to address:** Phase 28 (Completeness Audit), core logic design. This function must be written and tested before the Review badge and CSV column consume it.

---

## Phase-Specific Warnings Summary

| Feature | Pitfall | Mitigation | Phase |
|---------|---------|------------|-------|
| Manager-Track UX | `user_role` in `answers` causes step visibility / WD record contamination | Store `user_role` as separate React state; clear classification answers on role switch | Phase 29 |
| Manager-Track UX | `require_og_confirmed` 409 fires for manager WDs at export | Add `wd_type` field or `force_draft` param; bypass gate for manager-type WDs | Phase 29 |
| Manager-Track UX | Amendment panels / audit findings keyed to wd_id, leak across role contexts | Add `user_role` to useEffect deps; clear role-specific state on role change | Phase 29 |
| Org Context Step | `org_context` None on legacy WDs silently deserialises as None | Add `seven_elements_flow` boolean sentinel; completeness audit gates 7-element checks on it | Phase 26 |
| Org Context / Responsibilities | New fields missing from `WDPatchRequest` — PATCH silently drops them | Add fields to `WDPatchRequest` in the same commit; add PATCH roundtrip test per field | Phase 26, 27 |
| record vs. typed field | `client_service_results` in record, new fields typed — inconsistent source of truth | Decide rule before Phase 26: Part 2 fields are typed, Part 1 fields stay in record | Phase 26 |
| CSV Export | Naive string interpolation corrupts rows with commas, newlines, quotes | Use `csv.DictWriter` with `QUOTE_ALL`; encode as `utf-8-sig` for Excel | Phase 30 |
| CSV Export | Non-EC groups have empty Effort/Working Conditions columns | Emit synthetic approximate row using `NON_EC_TOTALS`; add `data_completeness` column | Phase 30 |
| CSV Export | IC positions have null Responsibilities by design, not by error | Add `responsibilities_applicable` column; completeness audit must encode this | Phase 27 |
| Completeness Audit | JES scores absent pre-export; audit flags Effort/WC as missing | Audit triggers `score_jes_v2` as side effect for EC groups with null `jes_total_points` | Phase 28 |
| Completeness Audit | `_build_organizational_context_text()` always returns a string — audit reads wrong source | Audit checks `wd.org_context` (typed field), not derived context text | Phase 26, 28 |
| Completeness Audit | "Responsibilities" name collision: JES factor vs. Phase 27 narrative | Name field `responsibilities_narrative`; use `responsibilities_narrative_status` in audit keys | Phase 27 |
| Completeness Audit | Partial EC JES scoring (sentinel -1 factors) collapses to "populated" | Implement `build_elements_status()` with 5-state matrix; test all states explicitly | Phase 28 |

---

## Cross-Cutting Risk: stepIndex Persistence After STEPS Array Extension

**What goes wrong:** Every time STEPS gains new entries (Phase 26 adds org_context step, Phase 27 adds responsibilities_narrative step), the integer `stepIndex` persisted in `localStorage` under `jd-builder-v2-record` becomes stale. An advisor who started a WD before Phase 26 will have `stepIndex = 8` (pointing at what was `noc_confirm`). After Phase 26 inserts an org_context step at position 6 (after `supervises`), `stepIndex = 8` now points at `qb_sector_gate`. The advisor's session resumes at the wrong step.

This happened in Phases 15–17 (STEPS ordering bugs caused UX regressions).

**Prevention:**
- Do not rely on integer `stepIndex` for session resume. Instead, resume by finding the last answered step: `const resumeIdx = STEPS.findLastIndex(s => answers[s.id] !== undefined)`. This is position-independent.
- When adding new steps to STEPS, place them at the end of their phase block (not at a low index), or bump a `STEPS_VERSION` constant and clear `localStorage` on version mismatch at app startup.
- Add a test: insert a hypothetical step at position 3 in a test copy of STEPS, simulate a persisted `stepIndex = 5`, and assert that `activeStepIndex` resolves correctly.

**Phase to address:** Phase 26 (Org Context Step) — any STEPS array modification. This must be resolved before the first new step is added.
