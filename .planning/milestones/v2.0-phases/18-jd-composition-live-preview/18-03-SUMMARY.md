---
phase: 18-jd-composition-live-preview
plan: 03
type: execute
wave: 2
autonomous: true
files_modified:
  - v2/frontend/src/data.jsx
  - v2/frontend/src/components.jsx
  - v2/frontend/src/document.jsx
  - v2/frontend/src/styles.css
  - v2/frontend/src/document.test.jsx
---

# Plan 18-03 — Frontend implementation (Wave 2)

## What was built

- **`I.warn` SVG icon** (`v2/frontend/src/data.jsx`): warning triangle path added to icon registry for the orphan badge.
- **DutyBuilder rewire** (`v2/frontend/src/components.jsx`): now fetches verbatim duties from `GET /api/noc/{noc_code}/duties` when `cfg.noc_code` is present; shimmer/empty/fetched states; duty shape carries `provenance_noc_code`, `provenance_section: "Main duties"`, `provenance_hash`, `source: "noc"|"advisor"`; legacy `cfg.suggestions` fallback kept for pre-NOC flow; placeholder changed to "Describe a duty not listed above…"; `aria-live="polite"` count badge added.
- **`OrphanBadge` component** (`v2/frontend/src/document.jsx`): renders amber-orange badge with `I.warn` icon, "Orphan Warning" label, and citation text from `d.orphan_rationale`; exported.
- **Section 3 verbatim render** (`v2/frontend/src/document.jsx`): `d.text` (verbatim NOC text) replaces `d.polished`; src pill `'NOC 2021 · refined'` → `'NOC 2021'`; ghost note copy updated to "Select duties from the NOC list — they will appear here, verbatim and traceable."; orphan badge rendered when `d.orphan && reviewing`.
- **Section 5 unconditional** (`v2/frontend/src/document.jsx`): Essential Qualifications section now always renders with ghost state when `!r.qualsVisited`; `n++` moved outside the conditional.
- **`.orphan-badge` CSS** (`v2/frontend/src/styles.css`): amber-orange `oklch(0.58 0.14 35)` text, soft background, mono font, label + cite spans.
- **`cls` null guard** (`v2/frontend/src/document.jsx`): `safeCls = cls || {}` defensive default for safe access to `code`, `status`, `factors`, `standard`, `group`.
- **Test file**: 6 Phase 18 RED stubs replaced with real assertions.

## Verification

- `cd v2/frontend && npm run test` → **30 passed** (24 prior + 6 Phase 18)
- `cd v2/frontend && npm run build` → **clean**, bundle 201.44 kB (gzip 62.83 kB)

## Acceptance criteria

- All 6 document.test.jsx Phase 18 tests GREEN
- DOC-04 test uses `vi.fn()` spy + `fireEvent.click` on "Key Responsibilities" header + `toHaveBeenCalledWith('duties')` assertion
- DOC-05: `grep "NOC 2021 · refined" v2/frontend/src/document.jsx` → 0 matches
- `grep "verbatim and traceable"` → 1 match (ghost note updated)
- `grep OrphanBadge` → 3+ matches (def + usage + export)
- `grep orphan-badge` in styles.css → 5+ matches
- Section 5 n++ outside qualsVisited if block (verified by reading section)
- Build clean, no TypeScript/lint errors

## Deviations

- One minor test fix: DOC-05 test originally used `getByText` for "NOC 2021" but the text appears in both the src pill and the prov tag — changed to `getAllByText` + `find` to assert the src pill is among the matches. Test intent preserved.
