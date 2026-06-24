# Phase 28: Manager-Track UX — Context

**Gathered:** 2026-06-24
**Status:** Ready for planning
**Source:** Derived from ROADMAP.md (Phase 28 entry) + REQUIREMENTS.md (MGR-01/02/03) + STATE.md (locked v4.0 decisions). discuss-phase was not run; the design is crystallized in the existing artifacts.

<domain>
## Phase Boundary

A hiring manager can use the full JD Builder application to describe a position and receive a draft job description — without ever seeing classification internals (OG codes, JES factor names, CBA clause references). The manager's output is a clearly-labelled draft for the classification team to finalize. The classification advisor flow is unchanged.

**In scope:**
- Role selector screen at SPA entry (advisor vs. hiring manager)
- `userRole` state slice + `jd-builder-v2-role` localStorage key
- `wd_type: Literal['advisor', 'manager']` field on WorkDescription + WDPatchRequest + WDCreateRequest
- `require_og_confirmed` bypass for manager-track WDs (MGR-03)
- Manager-track STEPS variant that skips classification-internal steps
- Conditional UI suppression of OG codes, JES factor names, CBA citations in manager mode (MGR-02)
- DRAFT watermark ("DRAFT — PENDING CLASSIFICATION") on manager-track DOCX exports

**Out of scope (Phase 29 or later):**
- Structured JSON/CSV export (Phase 29 SEXP-01/02/03)
- Enhanced job poster (Phase 29 POST-01)
- Separate manager DOCX template (REQUIREMENTS.md "Out of Scope" — manager uses the same Accessible JD template + watermark)
- Bilingual export
- Multi-user auth
</domain>

<decisions>
## Implementation Decisions

### Role Storage (MGR-01) — LOCKED (STATE.md v4.0 decision)
- **D-28-01**: `user_role` lives in `localStorage` under key `jd-builder-v2-role` ONLY. It is NEVER added to the WorkDescription model, NEVER sent in the WD PATCH/POST body, NEVER stored in `work_descriptions.data`. The SPA reads it into a `userRole` state slice on mount.
- **D-28-02**: On first load (when `jd-builder-v2-role` is absent from localStorage), a role selector screen precedes the conversation. Selecting "I am a hiring manager" persists `'manager'` and launches manager-track. Selecting "I am a classification advisor" persists `'advisor'` and launches the standard flow. Refreshing the page does NOT re-show the selector (the persisted key short-circuits it).
- **D-28-03**: The backend WDPatchRequest uses `ConfigDict(extra="ignore")`, which silently drops unknown keys (HTTP 200). This is exactly why a guard test MUST assert that `user_role` sent in the PATCH body does NOT appear in `work_descriptions.data` after a round-trip — the test is the contract (mirrors the Phase 26/27 co-update gate pattern).

### Manager-Track Bypass (MGR-03) — LOCKED (STATE.md v4.0 decision)
- **D-28-04**: `wd_type: Literal['advisor', 'manager'] = 'advisor'` typed field on WorkDescription. Added to WDPatchRequest AND WDCreateRequest in the SAME git commit (co-update rule). The SPA sends `wd_type: 'manager'` in the POST body when creating a WD in a manager session.
- **D-28-05**: `require_og_confirmed(wd)` in `classification_gate.py` returns early (no-op) when `wd.wd_type == 'manager'`. The bypass is intrinsic to the wd_type field — every caller (export.py DOCX/poster/PDF routes, jes_scoring.py) inherits it for free. No call-site changes needed.
- **D-28-06**: The SPA's client-side `exportAs` guard (`if (!record.confirmed_og || !record.og_level) return`) is bypassed when `userRole === 'manager'` — managers can export without confirmed OG.

### Manager-Track STEPS Variant (MGR-03) — LOCKED (ROADMAP criterion #3)
- **D-28-07**: The manager-track STEPS variant is implemented by filtering at the consumption point, NOT by duplicating the STEPS array. The set of classification-internal step IDs skipped in manager mode: `{ noc_confirm, og_confirm, og_level_questions, og_level }`. These are classification-confirmation steps; a manager's job is to describe the work, not classify it. The Socratic question bank (`qb_*`) steps still run to gather conversational signals.
- **D-28-08**: `stepIndex` resume-by-last-answered (Phase 26 invariant) MUST keep working in manager mode — the reduce walks STEP_RECORD_KEY[s.id] and naturally skips filtered steps because they never appear in the visible STEPS list. No change to the resume logic itself.

### DRAFT Watermark (MGR-03) — LOCKED (ROADMAP criterion #3)
- **D-28-09**: Manager-track DOCX exports are watermarked with "DRAFT — PENDING CLASSIFICATION" as a prominent paragraph at the top of the document. The watermark is applied inside `generate_wd_docx` (export_service.py) by post-processing the rendered bytes with python-docx when `wd.wd_type == 'manager'`. The watermark is intrinsic to manager-track exports and cannot be bypassed by the client.

### UI Suppression (MGR-02) — LOCKED (ROADMAP criterion #2)
- **D-28-10**: In manager mode, the following UI surfaces are suppressed or replaced:
  - `ClassifyBadge` (preview header) — hidden entirely
  - Classification & Evaluation Sec (document.jsx) — shows "Classification pending — to be completed by the classification team" instead of OG code/level/JES scorecard
  - ReviewState "Classified as {code} · {points} pts" checklist line — hidden
  - Compliance audit (CBA citations) — hidden (managers don't run compliance audits)
- **D-28-11**: The systematic MGR-02 inspection is enforced by automated tests that render the manager-mode UI and assert no OG code patterns (EC, AS, IT, FI, etc.), no JES factor names ("Supervision", "Initiative"), and no CBA clause references appear in the rendered output.

### the agent's Discretion
- The exact visual design of the role selector screen (button layout, copy, iconography) — follow the existing Header/Exchange aesthetic.
- Whether to add a "Switch role" affordance in the Header after a role is chosen — recommended but not required by ROADMAP.
- The watermark styling (bold red, all-caps, centered) — prominent enough to be unmissable but not destructive to the document layout.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project foundation
- `.planning/ROADMAP.md` — Phase 28 entry: 4 success criteria + 3 requirements (MGR-01/02/03)
- `.planning/REQUIREMENTS.md` — MGR-01/02/03 verbatim requirement text
- `.planning/STATE.md` — v4.0 locked decisions (user_role in localStorage only; wd_type bypass; stepIndex resume invariant; DocumentPane conditional Sec template)

### Pattern references (prior phase plans to mirror)
- `.planning/phases/26-org-context-conversational-step/26-02-PLAN.md` — WDPatchRequest co-update rule + stepIndex resume + DocumentPane conditional Sec template
- `.planning/phases/27-responsibilities-narrative-completeness-audit/27-01-PLAN.md` — TDD within-task RED→GREEN pattern for a WD field vertical slice (the closest analog to Plan 28-01)
- `.planning/phases/27-responsibilities-narrative-completeness-audit/27-02-SUMMARY.md` — established conventions (build_seven_elements shared helper, soft-gate pattern, sibling useEffect)

### Codebase touchpoints
- `v2/backend/app/models/work_description.py` — WorkDescription model (wd_type insertion point: line 57, next to responsibilities_narrative)
- `v2/backend/app/api/wd.py` — WDPatchRequest (line 125) + WDCreateRequest (line 114) + PATCH endpoint (line 206) + POST endpoint (line 154)
- `v2/backend/app/services/classification_gate.py` — require_og_confirmed (bypass insertion point: line 36, before the raise)
- `v2/backend/app/services/export_service.py` — generate_wd_docx (line 616, watermark insertion point after line 642 render)
- `v2/backend/app/api/export.py` — export_wd_docx (line 55), require_og_confirmed call (line 60)
- `v2/frontend/src/app.jsx` — App component (line 75), record useState (line 77), stepIndex resume (line 96), exportAs guard (line 574), POST/PATCH call site (line 348-367), main render (line 909)
- `v2/frontend/src/data.jsx` — STEPS array (line 500), isStepVisible (line ~460), getVisibleSteps (line 493), exports (line 727)
- `v2/frontend/src/document.jsx` — Classification Sec (line 402-468), ClassifyBadge rendering
- `v2/frontend/src/conversation.jsx` — ReviewState (line 187), "Classified as" checklist line (line 193)

</canonical_refs>

<specifics>
## Specific Ideas

- The role selector should feel like a deliberate first step (not a modal or a toast). A centered card with two large buttons is the recommended shape — mirrors the "done-card" aesthetic in ReviewState.
- The DRAFT watermark should be visually unmissable: bold, red, all-caps, centered at the very top of the document. The text "DRAFT — PENDING CLASSIFICATION" makes the document's status obvious to the classification team who receives it.
- The manager-track STEPS variant preserves the Socratic question bank (qb_* steps) because those gather plain-language work descriptions — the manager's actual job. Only the classification-confirmation steps are skipped.
- The `userRole` state is read from localStorage on mount (like `record` and `wd_id`). It flows down to `getVisibleSteps` / `isStepVisible` as a filter parameter, to `DocumentPane` / `ReviewState` as a suppression flag, and to the POST/PATCH body builder as the `wd_type` source.

</specifics>

<deferred>
## Deferred Ideas

- Separate manager DOCX template (REQUIREMENTS.md "Out of Scope" — v5)
- "Switch role" affordance in the Header (the agent's Discretion — can be added if user requests)
- Manager-track specific Socratic questions (the qb_* bank serves both tracks in v4.0)
- Manager-mode PDF export watermark (PDF route is 501 on ARM64 anyway; the DOCX watermark is the v4.0 deliverable)

</deferred>

---

*Phase: 28-manager-track-ux*
*Context gathered: 2026-06-24 (derived from ROADMAP + REQUIREMENTS + STATE — discuss-phase not run)*
