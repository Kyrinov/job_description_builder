# Phase 27: Responsibilities Narrative + Completeness Audit — Context

**Gathered:** 2026-06-24
**Status:** Ready for planning
**Source:** Synthesized from STATE.md (v4.0 locked decisions) + ROADMAP.md (authoritative phase goal) + REQUIREMENTS.md. No `/gsd-discuss-phase` was run.

> ⚠ **Items marked `[PLANNER DISCRETION — confirm before execution]` are inferences**, not user-locked
> decisions. They resolve genuine conflicts between REQUIREMENTS.md and ROADMAP.md by favoring the
> ROADMAP phase goal (more specific, more recent). Review these before `/gsd-execute-phase 27`. If you
> disagree with any, adjust the relevant PLAN.md task or run `/gsd-discuss-phase 27` to lock overrides.

<domain>
## Phase Boundary

Advisors can record a free-text responsibilities narrative that exports to the Accessible DOCX, and the
Review phase displays a per-element completeness badge over all 7 Part 2 elements via a single
`POST /api/wd/{id}/validate-elements` endpoint.

**In scope:** RESP-01/02/03, ELEM-01/02/03.
**Depends on:** Phase 26 (org_context typed field exists; both new WD fields present before the audit can
evaluate all 7 elements).
**Out of scope:** JSON/CSV value-export HTTP routes (SEXP-01/02 → Phase 29); manager-track UX (Phase 28);
enhanced poster (Phase 29).

The 7 Part 2 elements (from ROADMAP / REQUIREMENTS SEXP-01):
1. Organizational Context → `organizational_context_text`
2. Client Service Results → `client_service_results_text`
3. Key Activities → `duties`
4. Skills → `education_text` / `experience_text`
5. Effort → JES Effort factors (derived)
6. Responsibility → `responsibilities_narrative` (NEW this phase)
7. Working Conditions → JES Conditions factors (derived)

</domain>

<decisions>
## Implementation Decisions

### Locked (carried from STATE.md v4.0 — NON-NEGOTIABLE)

- **responsibilities_narrative as typed root field on WorkDescription** (mirrors org_context), NOT in the
  freeform record dict. Export + audit read the typed field directly. *(STATE: "org_context and
  responsibilities_narrative as typed root fields")*
- **WDPatchRequest co-update rule enforced** — `WorkDescription.responsibilities_narrative` and
  `WDPatchRequest.responsibilities_narrative` ship in the SAME git commit, gated by a round-trip test.
  *(STATE v4.0 decision; `extra="ignore"` would silently drop an unknown PATCH key with HTTP 200.)*
- **max_length=4000 on WDPatchRequest.responsibilities_narrative** (ASVS V5 DoS mitigation; consistent with
  T-26-01 for org_context).
- **stepIndex resume-by-last-answered is inherited for free** — do NOT re-touch the resume initialiser.
  The new STEPS entry is added to `STEP_RECORD_KEY` only; `STEPS.reduce` handles the rest. *(STATE decision.)*
- **Completeness audit reads `wd.org_context` (typed root field), NOT derived fallback text.** A WD with
  `org_context=None` but record branch/reports data MUST report Organizational Context as "missing".
  *(ROADMAP success criterion #4 / STATE decision — `_build_organizational_context_text()` returns a
  non-empty synthesized string even when the advisor skipped the step, which would be a false positive.)*
- **`build_seven_elements(wd) -> dict` shared helper in export_service.py** — single source of truth for
  7-element data; consumed by the validate-elements endpoint (this phase) and the JSON/CSV routes
  (Phase 29). *(STATE decision.)*
- **DocumentPane conditional Sec with dynamic `n++`** — the new Responsibilities Sec follows the
  org_ctx/csr template exactly so downstream sections renumber transparently. *(STATE pattern.)*
- **Export priority idiom preserves a fallback path** to avoid `{{template leak}}` — but see R-RESP-03 below
  for the responsibilities-specific variant (placeholder, not synthesis).

### the agent's Discretion (PLANNER-RESOLVED — confirm before execution)

- **R-RESP-01 — Narrative input is a single free-text `textarea`, NOT a 4-part assembly.** `[PLANNER DISCRETION]`
  RESP-01 says "free-text responsibilities narrative". The existing `textarea` input type is already fully
  supported by `TextInput` / `answerValid` / `initialAnswer` — **no new component is needed** (unlike
  org_context's OrgContextInput). `apply()` writes a single typed string to `record.responsibilities_narrative`.
  *(Rationale: REQ wording is explicit; simpler than org_context; STATE only said the 4-part pattern is
  "possibly" reusable.)*

- **R-RESP-03 — DOCX Part 2 "Responsibility" content = `responsibilities_narrative` when filled, else
  `_ADVISOR_PLACEHOLDER`.** `[PLANNER DISCRETION]`
  This REPLACES the current JES-derived `responsibilities_text` (built from the JES "Responsibility" factor
  category) as the source for the Part 2 Responsibility section. ROADMAP criterion #2 is literal: *"a WD
  without the narrative shows the advisor placeholder."* Verified: **no existing test asserts
  responsibilities_text from JES factors** (only a docstring mentions it), so this change is safe and breaks
  nothing. The JES Responsibility category factors are no longer rendered in this section.

- **R-ELEM-01a — Empty Responsibilities status = `"missing"`, NEVER `"not_applicable"`.** `[PLANNER DISCRETION — CONFLICT]`
  REQUIREMENTS.md ELEM-01 says "not_applicable only when no text is provided"; ROADMAP criterion #3 explicitly
  corrects this to *"missing (not not_applicable) when empty — because the field is open to all positions."*
  **ROADMAP wins** (more specific, more recent, and explicitly frames itself as a correction). So: empty →
  `missing`; never `not_applicable`.

- **R-ELEM-01b — Effort & Working Conditions status = `"derived"` when `wd.jes_total_points is not None`,
  else `"missing"`.** `[PLANNER DISCRETION]`
  Per ROADMAP #3. The presence of JES point totals is the "derived" signal (the JES ran). Category-empty
  groups (e.g. MT) still count as derived when jes_total_points is set.

- **R-ELEM-01c — Other element statuses:** `[PLANNER DISCRETION]`
  - Organizational Context: `populated` iff `(wd.org_context or "").strip()` else `missing`.
  - Client Service Results: `populated` iff `record.client_service_results` non-empty else `missing`.
  - Key Activities: `populated` iff `wd.duties` non-empty else `missing`.
  - Skills: `populated` iff qualification education/experience present else `missing`.

- **R-ELEM-EP — `validate-elements` response shape:** `[PLANNER DISCRETION]`
  `POST /api/wd/{id}/validate-elements` → `200 { "wd_id", "elements": [ { "key", "label", "status" } ],
  "complete_count": <N>, "total": 7 }` where `status ∈ {"populated","derived","missing"}` and
  `complete_count` = count of populated|derived. 404 when WD missing (mirrors audit/orphan_check guard).

- **R-ELEM-02 — Completeness badge is a SOFT gate.** `[PLANNER DISCRETION]`
  ReviewState shows a "Completeness: N/7 elements" line in the existing checklist (no new hard block). Export
  buttons stay enabled at any count. The badge is informational; the existing checklist pattern is extended.
  *(ROADMAP #5: "soft gate, not a hard block".)*

- **R-ELEM-03 — ELEM-03 partially delivered this phase.** `[PLANNER DISCRETION — SCOPE]`
  `build_seven_elements(wd)` returns each element's value AND its completeness status (JSON-serializable), and
  `validate-elements` returns that status as JSON. The literal 7-element JSON/CSV **value-export HTTP routes**
  are Phase 29 (SEXP-01/02) per ROADMAP sequencing. **ELEM-03's "JSON and CSV include completeness status" is
  satisfied at the data-structure level here; full route surfacing is Phase 29.** *(Confirm this scoping is
  acceptable — otherwise add a 3rd plan to build the JSON/CSV routes now.)*

### Deferred Ideas
- Responsibilities narrative as a multi-part (decision-impact / delegation-scope) assembly — STATE flagged
  this as "possible"; R-RESP-01 resolves it as single free-text for v4.0. Multi-part is v5 if needed.
- SJD pre-fill for responsibilities narrative — deferred (SJD_LIBRARY dataset not enriched for this).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Established patterns (this phase reuses them verbatim)
- `.planning/phases/26-org-context-conversational-step/26-02-PLAN.md` — gold-standard plan for the
  typed-field + co-update + STEPS step + DocumentPane Sec + export-priority pattern (RESP mirrors this).
- `.planning/phases/26-org-context-conversational-step/26-02-SUMMARY.md` — what landed, exact file edits,
  the 4 auto-fix deviations (placeholder-test rewrites, STEPS-count bump).
- `.planning/phases/26-org-context-conversational-step/26-PATTERNS.md` — "Critical Implementation Order".

### Source-of-truth files (the contracts plans are written against)
- `v2/backend/app/models/work_description.py` — `org_context: Optional[str] = None` (line 56); add
  `responsibilities_narrative` next to it.
- `v2/backend/app/api/wd.py` — `WDPatchRequest.org_context` (line 151); add `responsibilities_narrative`
  next to it; new `validate-elements` route follows the `validate-duties` endpoint pattern (line 306).
- `v2/backend/app/services/export_service.py` — `_build_wd_context` `responsibilities_text` (line 354-360)
  and `organizational_context_text` priority (line 397); new `build_seven_elements(wd)` here.
- `v2/frontend/src/data.jsx` — STEPS `org_context` (664), `client_service_results` (671), `duties` (679);
  new step inserts after `duties`.
- `v2/frontend/src/components.jsx` — `StepInput` (768), `answerValid` (793), `initialAnswer` (785) —
  `textarea` already handled; no new component.
- `v2/frontend/src/document.jsx` — DocumentPane `org_ctx` Sec (304-324), `csr` Sec (325-340) — new
  Responsibilities Sec follows this template.
- `v2/frontend/src/app.jsx` — FLASH dict, SECTION_NAMES, `exportAs` (532), Review wiring (879-883).
- `v2/frontend/src/conversation.jsx` — `ReviewState` (187) + checklist (190-205) + export-row (224).

</canonical_refs>

<specifics>
## Specific Ideas

- Responsibilities step belongs in phase 3 (Duties), inserted AFTER `duties` and BEFORE `quals` so the
  conversation reads: Org Context → Client Service Results → Key Activities → Responsibilities narrative →
  Qualifications. (Element order in the DOCX is fixed by the template; step order is conversational.)
- Badge fetch: reuse the `onRunAudit` / `useEffect([...reviewing, wd_id])` hydration pattern already used for
  orphan-check + amendment-notes to fetch validate-elements once the user enters Review.
- `textarea` max length on the frontend is optional; the authoritative cap is the backend `max_length=4000`.

</specifics>

<deferred>
## Deferred Ideas
- Multi-part responsibilities narrative (decision-impact / delegation-scope) — v5.
- SJD pre-fill of responsibilities_narrative — v5 (dataset not enriched).
- Effort / Working Conditions as dedicated Socratic steps — v5 (JES-derived is sufficient for v4.0).
</deferred>

---

*Phase: 27-responsibilities-narrative-completeness-audit*
*Context gathered: 2026-06-24 (planner-synthesized from STATE + ROADMAP + REQUIREMENTS; no discuss-phase)*
