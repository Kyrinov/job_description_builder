---
status: partial
phase: 22-sjd-library
source: 22-VERIFICATION.md
started: 2026-06-11T18:55:00Z
updated: 2026-06-11T18:55:00Z
---

# Phase 22 — Human Verification Required

Phase 22 (SJD Library) backend and frontend wiring are fully implemented and automated tests pass. 4 items need browser-based human verification.

## Current Test

Awaiting human verification of UI behavior in browser session.

## Tests

### 1. SJD-03 warning toast (og_code change after SJD apply)
expected: Apply an SJD (e.g., DND-EC-58355) via Browse SJDs panel, advance to og_confirm, change OG code from EC to AS, commit. A toast appears for 7 seconds with the exact text: "Departing from the SJD classification turns this into a new evaluation — the SJD decision no longer applies"
result: [pending]

### 2. SJD provenance badge in document preview
expected: After applying an SJD, open the document preview. Each seeded duty (source='sjd') is prefixed with a visible "SJD" tag inline with the duty text. NOC-sourced duties are not tagged. Document footer shows "DND SJD Library" in the provenance tag list.
result: [pending]

### 3. Browse SJDs button visibility and modal panel
expected: After answering all 5 Role phase questions (title, branch, reports, reports_to_military, supervises), a subtle secondary button "Browse SJDs" is visible in the conversation thread BEFORE the Work Type question. Clicking it opens a modal panel listing 10 SJD entries with an OG filter dropdown.
result: [pending]

### 4. SJD-03 negative path (og_level-only change)
expected: After applying an SJD, on the og_confirm step, change only og_level (keep og_code the same). NO toast should appear — SJD-03 only fires on og_code change, NOT on og_level-only change.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
