---
phase: 19-qualifications-amendments
plan: 03
subsystem: api+frontend
tags: [amend-01, audit-log, fastapi-router, review-state, inline-panel, vitest, pytest, pydantic-literal, hot-toast]

# Dependency graph
requires:
  - phase: 19-qualifications-amendments
    plan: 02
    provides: "QUAL-01/02/03 RED→GREEN baseline (QUAL_DEFAULTS map, .qual-sub-k CSS, touched-gated validation); .sec__h CSS layout and Sec component pattern available for amendment panel"
  - phase: 19-qualifications-amendments
    plan: 01
    provides: "6 skip-decorated test stubs in v2/backend/tests/test_amendments.py for POST/GET/404/audit_log/422_invalid_section/422_oversized_comment; audit_log schema already includes wd_id/event/actor/detail/created_at"
provides:
  - "AMEND-01 backend: POST /api/wd/{wd_id}/amendments (201) writes audit_log row with event='manager_amendment', section+comment in detail JSON; 404 guard on missing WD; Literal section key validation; 2000-char cap on comment"
  - "AMEND-01 backend: GET /api/wd/{wd_id}/amendments (200) returns latest note per section, deduplicating via ORDER BY id DESC + first-occurrence-wins"
  - "AMEND-01 frontend: amendmentNotes + amendmentPanels useState slices in App() with hydration useEffect on [wd_id, reviewing]"
  - "AMEND-01 frontend: inline .amend-panel with textarea + Save/Discard buttons + character count; .amend-btn icon button + .amend-indicator gold dot in every .sec__h when reviewing===true"
  - "AMEND-01 frontend: 'N amendment note(s) attached' checklist row in ReviewState when at least 1 note saved"
affects:
  - "19-04 (full suite green gate — backend 73+ and frontend 31+ must remain GREEN; both verified at execution)"
  - "Phase 20 DOCX export will read amendment rows from audit_log (AMEND-02 docxtpl appendix) — data path now in place"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "audit_log INSERT pattern for advisory/state-change events: event string + JSON-encoded detail (used by jes_override already; extended to manager_amendment)"
    - "Page-refresh hydration via useEffect on [wd_id, reviewing] + GET to a /audit-log-derived endpoint (mirrors orphan_check useEffect pattern)"
    - "Section-keyed UI state objects in app.jsx: amendmentPanels[sectionKey] = { open, text, saved }; DocumentPane receives amendmentPanels prop and dispatches Sec with sectionKey-keyed slices"
    - "Pydantic Literal['id', 'ov', 'du', 'cls', 'q', 'drf'] for enum-validated free-text body fields; 422 on invalid key without reaching the handler"
    - "GET endpoint audit-log deduplication via ORDER BY id DESC + Python dict first-occurrence-wins (no SQL GROUP BY needed; keeps the index simple)"

key-files:
  created:
    - v2/backend/app/api/amendments.py
  modified:
    - v2/backend/app/api/__init__.py
    - v2/backend/tests/test_amendments.py
    - v2/frontend/src/app.jsx
    - v2/frontend/src/document.jsx
    - v2/frontend/src/conversation.jsx
    - v2/frontend/src/styles.css

key-decisions:
  - "Used Pydantic Literal['id', 'ov', 'du', 'cls', 'q', 'drf'] for AmendmentRequest.section instead of free-form str with manual validation — 422 rejection happens in Pydantic, before the route handler runs, and the test stub test_save_amendment_invalid_section confirms this"
  - "Comment max_length=2000 mirrors the work_description T-16-03 cap; the test stub test_save_amendment_oversized_comment verifies 422 on 2001 chars (T-19-02 threat model)"
  - "GET deduplication via ORDER BY id DESC + Python dict 'first occurrence per section wins' loop, rather than GROUP BY json_extract(detail, '$.section') — keeps the SQL portable, avoids SQLite-specific JSON path functions, and is O(n) on rows per WD (small)"
  - "amendmentNotes (saved text) and amendmentPanels (UI: open/text/saved) are SEPARATE useState objects in App() — amendmentNotes survives page refresh via the hydration useEffect; amendmentPanels is local UI state and resets on close/refresh"
  - "Sec component reads `amendmentPanel.saved ?? amendmentNote ?? null` for the gold dot visibility — falls through the live panel state to the API-hydrated note; both pathways show the indicator"
  - "App.jsx now imports nothing new — handleAmendToggle and handleAmendSave are local closures, consistent with handleJesOverride; SECTION_NAMES lookup table is module-local to App() to avoid polluting the data.jsx export"
  - "DocumentPane accepts amendmentNotes/amendmentPanels/onAmendToggle/onAmendSave as OPTIONAL props (no default arg) — existing tests in document.test.jsx that call DocumentPane without these props (Phase 17/18) still pass because JSX attribute absence is equivalent to undefined; the Sec component's destructuring with default `??` operators handles undefined gracefully"
  - "All 6 Sec call sites (id, ov, du, cls, q, drf) pass the amendment props even though the drf section is conditional — drf is included so the amend panel works in the rare DND-DRF case; cls receives props in BOTH the ghost and resolved branches of Section 4"

requirements-completed: [AMEND-01]

# Metrics
duration: 8min
completed: 2026-06-09
---

# Phase 19 Plan 03: AMEND-01 Manager Amendment Notes

**Implemented manager amendment notes (AMEND-01) end-to-end: new `v2/backend/app/api/amendments.py` with POST/GET routes, frontend `App()` state + handlers + hydration useEffect, `Sec` component extension with inline `.amend-panel` + `.amend-btn` + `.amend-indicator`, `ReviewState` checklist row, and 6 new CSS classes. Backend 6 amendment stubs now GREEN; backend 67→73 passed (0 failed, 0 skipped); frontend 31/31 tests pass; Vite build clean (201.76 kB / 62.91 kB gzip).**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-06-09T14:41:46Z
- **Completed:** 2026-06-09T14:49:22Z
- **Tasks:** 2/2
- **Files modified:** 7 (1 new, 6 modified)

## Accomplishments

- **`v2/backend/app/api/amendments.py`** (new, 87 lines) — Two routes on a fresh `APIRouter()`:
  - `POST /api/wd/{wd_id}/amendments` (status_code=201) — accepts `AmendmentRequest` (Pydantic model with `section: Literal['id','ov','du','cls','q','drf']` and `comment: str` with `min_length=1, max_length=2000`); checks WD existence (404 guard same as `jes_override`); writes one `audit_log` row with `event='manager_amendment'`, `actor='advisor'`, `detail=json({section, comment})`; returns `{wd_id, section, saved: True}`.
  - `GET /api/wd/{wd_id}/amendments` (status_code=200) — selects `detail, created_at` from `audit_log WHERE wd_id=? AND event='manager_amendment' ORDER BY id DESC`; Python-side loop picks first occurrence per section (latest wins); returns `{wd_id, notes: {sectionKey: comment}}`.
- **`v2/backend/app/api/__init__.py`** — Added `amendments` to the import list and `api_router.include_router(amendments.router)` below `jes_scoring`.
- **`v2/backend/tests/test_amendments.py`** — Removed all 6 `@pytest.mark.skip(reason="amendments.py not yet implemented — unblock in Wave 2")` decorators; the stubs are now the test contracts themselves.
- **`v2/frontend/src/app.jsx`** — Added `amendmentNotes` (saved text keyed by sectionKey) and `amendmentPanels` (UI state `{open, text, saved}` keyed by sectionKey) `useState` slices. Added hydration `useEffect` on `[wd_id, reviewing]` that fetches `/api/wd/{wd_id}/amendments` and populates `amendmentNotes` (mirrors the `orphan_check` useEffect pattern). Added `handleAmendToggle(sectionKey, textOrNull)` with 3 modes (toggle / discard / text-update) and `handleAmendSave(sectionKey, text)` that POSTs to the endpoint and fires toast on success/failure. Updated `<DocumentPane>` call to pass 4 new props (`amendmentNotes`, `amendmentPanels`, `onAmendToggle`, `onAmendSave`) and `<ReviewState>` call to pass `amendmentNotes`. Module-local `SECTION_NAMES` lookup table for the toast copy.
- **`v2/frontend/src/document.jsx`** — `Sec` component extended with 6 new props (`sectionKey`, `amendmentNote`, `amendmentPanel`, `onAmendToggle`, `onAmendSave`, `reviewing`). When `reviewing && sectionKey`, renders a 22×22 icon `<button className="amend-btn">` with the pencil SVG path and an `aria-label="Add amendment note for {title}"`. When `savedNote` is non-null, renders `<span className="amend-indicator">` (gold dot). When `panelOpen`, renders `<div className="amend-panel">` with label, textarea, "Save note" (primary), "Discard note" (ghost), and live character count. Section click handler now also gates on `!panelOpen` so the amendment textarea doesn't trigger `onEdit`. `DocumentPane` signature extended with 4 new props. All 6 `<Sec>` call sites updated to pass the amendment props with the correct `sectionKey` (`id`, `ov`, `du`, `cls`, `q`, `drf`).
- **`v2/frontend/src/conversation.jsx`** — `ReviewState` accepts `amendmentNotes = {}` prop. After the 5 existing checklist items, computes `amendmentCount = Object.values(amendmentNotes).filter(n => n).length` and pushes a `"{N} amendment note(s) attached"` row to `checks` only when count > 0 (singular/plural per copywriting contract).
- **`v2/frontend/src/styles.css`** — Appended 6 new CSS classes to the existing "Phase 19: Qualifications & Amendments" block: `.amend-btn` (22×22 icon button with hover state), `.amend-btn.is-active`, `.amend-indicator` (8px gold dot), `.amend-panel` (12px 16px padding, panel surface), `.amend-panel__label` (mono 10px uppercase eyebrow), `.amend-panel textarea.tf` (72px min-height override), `.amend-panel__actions` (flex row), `.amend-count` (mono 9.5px right-aligned char count). All values verbatim from `19-UI-SPEC.md` Section D.

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend — amendments.py + api/__init__.py router + unblock 6 amendment tests** - `513be6d` (feat)
2. **Task 2: Frontend — app.jsx state+handlers, document.jsx Sec extension, conversation.jsx checklist, styles.css classes** - `f1380ab` (feat)

## Files Created/Modified

- `v2/backend/app/api/amendments.py` *(new, 87 lines)* — POST/GET routes with Pydantic Literal section validation, audit_log write, 404 guard, 2000-char cap.
- `v2/backend/app/api/__init__.py` *(modified)* — `from . import ... amendments` + `api_router.include_router(amendments.router)`.
- `v2/backend/tests/test_amendments.py` *(modified)* — 6 `@pytest.mark.skip` decorators removed; stubs now run against the live endpoint.
- `v2/frontend/src/app.jsx` *(modified)* — `amendmentNotes`/`amendmentPanels` useState, hydration useEffect, `handleAmendToggle`/`handleAmendSave`, prop pass-through to `DocumentPane` and `ReviewState`.
- `v2/frontend/src/document.jsx` *(modified)* — `Sec` component with 6 new props, amendment panel JSX, `DocumentPane` signature extended, all 6 `Sec` call sites updated.
- `v2/frontend/src/conversation.jsx` *(modified)* — `ReviewState` accepts `amendmentNotes`; amendment count row pushed to `checks`.
- `v2/frontend/src/styles.css` *(modified)* — 6 new CSS classes appended to the Phase 19 block.

## Decisions Made

- **Pydantic `Literal['id','ov','du','cls','q','drf']` for `section` validation** — Mirrors the Pydantic 422-before-handler pattern used by `JESOverrideRequest.factor_name` validation against `KNOWN_JES_FACTORS`. The test stub `test_save_amendment_invalid_section` confirms the 422 path.
- **GET dedup via `ORDER BY id DESC` + Python first-occurrence-wins** — Avoids SQLite-specific JSON path functions (`json_extract`) for portability. O(n) per WD where n is small (amendment notes are sparse); the alternative `GROUP BY json_extract(detail, '$.section')` would be faster but couples to SQLite 3.38+ json1 extension semantics.
- **Separate `amendmentNotes` and `amendmentPanels` `useState` objects in App()** — `amendmentNotes` (saved text) is API-derived and survives refresh via the hydration useEffect; `amendmentPanels` (UI: open/text/saved) is local-only and resets on close/refresh. Splitting them keeps the hydration useEffect simple (it only writes to `amendmentNotes`) and avoids stale-data bugs.
- **`Sec` reads `amendmentPanel.saved ?? amendmentNote ?? null` for the gold dot** — Falls through the live panel state to the API-hydrated note. Both pathways show the indicator; the panel state takes priority for instant UI feedback while the open panel has unsaved changes, but the indicator is also correct for sections where the panel was never opened.
- **`SECTION_NAMES` lookup table is module-local to `App()` in app.jsx** — Kept out of `data.jsx` to avoid growing the public export surface; the table is only used in the toast copy and is not a shared design token.
- **DocumentPane amendment props are optional (no default value, no propTypes check)** — Existing tests in `document.test.jsx` (Phase 17/18) call `DocumentPane` without these props and must continue to pass; JSX attribute absence is equivalent to `undefined`, and the Sec component's destructuring with `??` operators (`amendmentPanel?.open`, `amendmentPanel?.text ?? ''`, etc.) handles `undefined` gracefully.
- **All 6 Sec call sites (including conditional drf) pass amendment props** — drf is included so the amend panel works in the DND-DRF case; cls receives props in BOTH the ghost (line ~282) and resolved (line ~297) branches of Section 4 because the ghost branch is reachable during review state when OG confirmation was never completed.
- **Did NOT add a separate `test_amendment_flow.jsx` frontend test** — The plan's Task 2 acceptance criteria did not list a frontend test for the new amendment panel UI; the existing 31 tests in `document.test.jsx` / `app.test.jsx` / `conversation.test.jsx` continue to pass with the new props because they are optional. The amendment panel is verifiable end-to-end via the manual UAT gate in Plan 19-04.

## Deviations from Plan

### Auto-fixed Issues

**None.** All edits followed the plan's exact code templates, and all acceptance criteria thresholds that were measurable via grep were met (with the line-counting quirks noted below as informational).

### Informational Mismatches (no fix needed)

- **Plan acceptance criteria:** "`grep "handleAmendSave\|handleAmendToggle" v2/frontend/src/app.jsx` returns at least 4 matches" → actual `grep -c` output: 3 (3 unique lines).
  - **Why:** `grep -c` counts UNIQUE MATCHING LINES, not total occurrences. The function names appear 4 times total (`function handleAmendToggle` def, `function handleAmendSave` def, `onAmendToggle={handleAmendToggle}`, `onAmendSave={handleAmendSave}`), but the two prop references are on the same JSX line, so only 3 lines match. Verified via `grep -o "handleAmendSave\|handleAmendToggle" v2/frontend/src/app.jsx | wc -l` → 4 occurrences.
  - **Resolution:** The functional wiring is correct; the grep line-count is a measurement artifact of the JSX prop pass-through being on one line.

- **Plan acceptance criteria:** "`grep "amend-btn" v2/frontend/src/document.jsx` returns at least 2 matches" → actual `grep -c` output: 1.
  - **Why:** The plan's Sec component template (in both the PATTERNS.md and the action step) only references `amend-btn` once — in the button's `className` (`className={`amend-btn${panelOpen ? ' is-active' : ''}`}`). There is no second in-JSX reference; the `:hover` and `.is-active` style targets are in `styles.css` (not `document.jsx`). The 19-UI-SPEC.md CSS section mentions `.amend-btn:hover, .amend-btn.is-active` as 2 CSS rules, but no second JSX usage.
  - **Resolution:** The functional wiring is correct (the button class is applied); the acceptance criteria text was over-stated relative to the plan's own code template. No code change needed.

## Test Baseline State

- Backend: 67 passed + 6 skipped → **73 passed, 0 skipped, 0 failed** (all 6 amendment tests now GREEN)
- Frontend: 31 passed → **31 passed, 0 failed, 0 regressions** (QUAL-03 and other prior tests unaffected by new optional props)
- Total: **104 passed, 0 failed** (was 98 passed + 6 skipped before)

## Verification Commands

```bash
# Backend — 6/6 amendment tests GREEN, full suite 73 passed
cd /home/charles/job_description_builder/v2/backend && python -m pytest tests/test_amendments.py -v
cd /home/charles/job_description_builder/v2/backend && python -m pytest tests/ -q

# Frontend — all 31 tests pass
cd /home/charles/job_description_builder/v2/frontend && npx vitest run

# Build — clean, 201.76 kB / 62.91 kB gzip (up from 199.36 kB / 62.28 kB in Phase 17)
cd /home/charles/job_description_builder/v2/frontend && npm run build

# Spot checks (all pass)
grep "manager_amendment" /home/charles/job_description_builder/v2/backend/app/api/amendments.py        # 2 matches
grep "amendments" /home/charles/job_description_builder/v2/backend/app/api/__init__.py              # 2 matches
grep -c "pytest.mark.skip" /home/charles/job_description_builder/v2/backend/tests/test_amendments.py  # 1 (docstring only; 0 actual decorators)
grep "amendmentNotes\|amendmentPanels" /home/charles/job_description_builder/v2/frontend/src/app.jsx  # 5 matches
grep "amend-panel" /home/charles/job_description_builder/v2/frontend/src/document.jsx                # 3 matches
grep "sectionKey" /home/charles/job_description_builder/v2/frontend/src/document.jsx                 # 13 matches (covers all 6 sections)
grep "amendment note" /home/charles/job_description_builder/v2/frontend/src/conversation.jsx         # 1 match
grep "\.amend-btn" /home/charles/job_description_builder/v2/frontend/src/styles.css                  # 3 matches
grep "\.amend-indicator" /home/charles/job_description_builder/v2/frontend/src/styles.css             # 1 match
grep "\.amend-panel" /home/charles/job_description_builder/v2/frontend/src/styles.css                 # 4 matches
```

## Next Phase Readiness

- **Plan 19-04 (Wave 3 — Full Suite Green Gate + UAT)** can proceed: backend 73+ and frontend 31+ are both GREEN; the full test suite is verified; the Vite build exits 0. The UAT gate can validate the amendment panel end-to-end in a browser: open review, click `.amend-btn` on a section header, type a note, click Save, observe toast and gold dot, refresh page, observe gold dot persists, and verify the checklist row appears in `ReviewState`.
- **Phase 20 (Export)** has the data path in place: amendment notes are written to `audit_log` and the DOCX export will be able to read them via a query similar to the new GET endpoint (AMEND-02 is docxtpl appendix rendering, scoped to Phase 20).

## Self-Check: PASSED

- v2/backend/app/api/amendments.py: FOUND (87 lines, AmendmentRequest + save_amendment + get_amendments + router)
- v2/backend/app/api/__init__.py: FOUND (amendments imported + router included)
- v2/backend/tests/test_amendments.py: FOUND (0 actual @pytest.mark.skip decorators; 6 tests GREEN)
- v2/frontend/src/app.jsx: FOUND (amendmentNotes + amendmentPanels state; handleAmendToggle + handleAmendSave; hydration useEffect; DocumentPane + ReviewState props)
- v2/frontend/src/document.jsx: FOUND (Sec with amendment props; DocumentPane extended; 6 Sec call sites updated)
- v2/frontend/src/conversation.jsx: FOUND (ReviewState accepts amendmentNotes; checklist row)
- v2/frontend/src/styles.css: FOUND (6 new amendment CSS classes appended to Phase 19 block)
- Commit 513be6d: FOUND (Task 1)
- Commit f1380ab: FOUND (Task 2)
- .planning/phases/19-qualifications-amendments/19-03-SUMMARY.md: FOUND

---
*Phase: 19-qualifications-amendments*
*Completed: 2026-06-09*
