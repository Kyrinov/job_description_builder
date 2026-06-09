---
issue_id: ISSUE-18-01
phase: 18-jd-composition-live-preview
date: 2026-06-09
severity: minor
status: open
source: UAT human verification
---

# Orphan badge styling appears blue instead of amber

## Reported

UAT human verification: created an IT-02 business analyst position with duties
involving "business analysis" / "administrative programs". The orphan badge
expected to appear in amber-orange (per UI-SPEC) is rendering in **blue**.

## Likely cause

The `.orphan-badge` CSS class uses `oklch(0.58 0.14 35)` for the text and
`oklch(0.97 0.035 50)` for the background — these are warm amber-orange tones.
Possible explanations:

1. CSS specificity: a more specific selector elsewhere in `styles.css` is
   overriding the colors (e.g. `.sec .orphan-badge` rule with different
   color).
2. HMR cache: stale CSS bundle served to the browser; hard refresh would
   clear it.
3. Browser color management: oklch() not honored uniformly in all browsers
   (Chromium since v111 supports it).
4. The user may be seeing the prov-tag dot (which is `var(--accent)` — blue)
   next to the duty text rather than the orphan badge itself.

## Reproduction steps

1. Start dev servers
2. Go through full flow to duties step
3. Select an IT position (e.g. IT-02) with duties containing "business
   analysis" or "administrative programs"
4. Enter review state
5. Inspect the `.orphan-badge` element — expected amber-orange, observed blue

## Disposition

Accepted by user as minor feature. Not blocking phase completion. Logged in
`.planning/notes/ISSUE-18-01-orphan-badge-styling.md` for future polish.
