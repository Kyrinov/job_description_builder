---
phase: 18-jd-composition-live-preview
plan: 04
type: execute
wave: 3
autonomous: false
files_modified:
  - v2/frontend/src/app.jsx
---

# Plan 18-04 — app.jsx wiring + full suite green gate (Wave 3)

## What was built

- **Duties step cfgOverride** (`v2/frontend/src/app.jsx`): replaced `getDutySuggestions(answers)` injection with `noc_code: record.confirmed_noc ? (typeof record.confirmed_noc === 'string' ? record.confirmed_noc : record.confirmed_noc?.noc_code || null) : null` so DutyBuilder fetches verbatim duties from the backend (JD-01).
- **Duties in PATCH payload** (`v2/frontend/src/app.jsx`): added `if (step.id === 'duties' && newRecord.duties) { wdPayload.duties = newRecord.duties; }` after the hoisted fields block so duties persist with ProvenanceTag fields to the backend (JD-02).
- **Orphan check useEffect** (`v2/frontend/src/app.jsx`): fires automatically on entering review state when `wd_id && record.duties?.length && record.confirmed_og`; fetches `POST /api/wd/${wd_id}/orphan_check`; merges `orphan` + `orphan_rationale` fields into matching duty objects; silent on failure (advisory check); `setOrphanFlags` state added.
- **Cleanup**: removed unused `getDutySuggestions` import from app.jsx.

## Threat model coverage

- T-18-08 (wd_id tampering): wd_id is server-generated UUID; not user-controllable
- T-18-09 (DoS): useEffect depends on `[reviewing, wd_id]`; reviewing is boolean
- T-18-10 (information disclosure): orphan_rationale is public TBS OG exclusion text; no PII

## Verification

- `cd v2/backend && python -m pytest -x` → **64 passed** (58 prior + 6 Phase 18). 0 regressions.
- `cd v2/frontend && npm run test` → **30 passed** (24 prior + 6 Phase 18). 0 regressions.
- `cd v2/frontend && npm run build` → **clean**, bundle 196.43 kB (gzip 61.50 kB).

## Acceptance criteria

- `grep "noc_code.*record.confirmed_noc"` in app.jsx → match (cfgOverride updated)
- `grep "getDutySuggestions"` in app.jsx → 0 matches for the duties cfgOverride context
- `grep "wdPayload.duties"` → match
- `grep "orphan_check"` → match (useEffect fetch URL)
- `grep "orphanFlags"` → 2+ matches (useState + setOrphanFlags)
- `npm run build` clean

## UAT human verification — APPROVED with one minor open issue

All 18 UAT checks passed by the user on 2026-06-09. Duties selection, document preview (DOC-01..05), click-to-edit (DOC-04) all confirmed working in browser.

**Known issue (advisory only, not blocking):**
- `.orphan-badge` rendering appears blue instead of amber-orange in some browser conditions. Logged in `.planning/notes/ISSUE-18-01-orphan-badge-styling.md`. User accepted as minor feature; deferred to future polish.

See "How to verify" instructions in the plan file for the 18-step UAT procedure covering duty selection, document preview, orphan check, and click-to-edit.
