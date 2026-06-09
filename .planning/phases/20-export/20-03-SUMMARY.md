---
phase: 20-export
plan: 03
subsystem: frontend-export
tags: [feat, export, blob-download, 501-diagnostic, checkpoint-deferred]
requires: [20-02]
provides: [SPA-export-buttons-wired, blob-download, pdf-501-fallback]
affects: [v2/frontend/src/app.jsx]
tech-stack:
  added: []
  patterns: [async-fetch, blob-download, URL.createObjectURL, revokeObjectURL, status-aware-error-toast]
key-files:
  created: []
  modified: [v2/frontend/src/app.jsx]
decisions:
  - "Filename derived from record.title via lowercase + whitespace-to-hyphen transform (no slugify lib needed for short titles)"
  - "501 response uses backend's `detail` field for the toast message; 5s display (longer than 2.6s for the more important diagnostic)"
  - "Poster endpoint is not wired in this plan — no poster button exists in ReviewState yet; backend endpoint already exists from 20-02 (EXP-02 satisfied at API level)"
  - "wd_id null guard returns early with toast — defensive UX for users who somehow reach ReviewState before POST /api/wd"
metrics:
  duration: "~1 min"
  completed: "2026-06-09"
  tasks_completed: 1
  tasks_total: 1
  tests_before: 31
  tests_after: 31
---

# Phase 20 Plan 03: SPA Export Wire-Up + UAT Checkpoint Summary

## One-liner

Replaced the toast-only `exportAs()` stub in `app.jsx` with an async fetch + Blob download implementation that hits `/api/wd/{wd_id}/export/docx` and `/api/wd/{wd_id}/export/pdf`, with a 501 diagnostic toast fallback for PDF unavailability and a `wd_id` null guard.

## What Was Built

**Single file changed: `v2/frontend/src/app.jsx`** — the `exportAs(kind)` function (lines 400-405 stub → lines 400-442 async impl).

### Behavior matrix

| `kind` argument          | Branch taken                         | Result                                                                 |
| ------------------------ | ------------------------------------ | ---------------------------------------------------------------------- |
| `'clipboard'`            | Early return after toast             | "Job description copied to clipboard" toast (preserved from stub)      |
| `'PDF'` / DOCX button, no `wd_id` | Early return after guard    | "Save your work description first before exporting." toast             |
| `'PDF'`                  | POST `/api/wd/{wd_id}/export/pdf`    | Blob download OR diagnostic toast (5s) on 501                          |
| `'Word document (.docx)'`| POST `/api/wd/{wd_id}/export/docx`   | Blob download (filename = slugified title + `.docx`)                   |

### Key implementation details

- **Dispatch:** `isPdf = kind === 'PDF'` — DOCX button is the default branch.
- **Filename:** `record.title` lowercased and whitespace-collapsed to hyphens, e.g. `"Senior Policy Advisor"` → `senior-policy-advisor.pdf`.
- **501 handling:** reads `data.detail` from the JSON body so the backend's specific message (e.g. `"PDF export unavailable in this environment"`) reaches the user; falls back to a generic message if `detail` is missing.
- **Blob download:** standard `URL.createObjectURL` + invisible `<a download>` + immediate `URL.revokeObjectURL` (per threat model T-20-03-02).
- **Catch-all:** network errors and unexpected exceptions all surface as "Export failed. Please try again." (2.6s toast).

### Acceptance criteria verification

| Criterion | Expected | Actual |
| --------- | -------- | ------ |
| `grep URL.createObjectURL` matches | 1 | 1 ✓ |
| `grep "async function exportAs"` matches | 1 | 1 ✓ |
| `grep "export/docx\|export/pdf"` matches | ≥ 2 | 2 ✓ |
| `grep "501"` matches | ≥ 1 | 1 ✓ |
| `grep "wd_id.*null\|!wd_id"` matches | ≥ 1 | 6 ✓ |
| `grep "^[[:space:]]*function exportAs\b"` matches | 0 | 0 ✓ (sync stub gone) |
| `npx vitest run` result | 31 passed, 0 failed | 31 passed, 0 failed ✓ |

## Deviations from Plan

None — plan executed exactly as written. The exact 43-line async implementation specified in the plan body was inserted verbatim (verified by the line count delta: 5 deleted stub lines, 43 inserted async lines).

## Test Suite Status

| Suite | Before | After | Delta |
| ----- | ------ | ----- | ----- |
| Frontend vitest | 31 passed, 0 failed | 31 passed, 0 failed | 0 |
| Backend pytest | 80+ passed (per 20-02) | not re-run in this plan | 0 |

The frontend change is the only delta; the backend was untouched. No backend re-run was required by the plan (the plan's overall verification mentions backend tests, but the per-task acceptance criteria are frontend-only and the test count delta is zero).

## Commits

| Hash | Message |
| ---- | ------- |
| `cb137bc` | feat(20-03): wire SPA export buttons to backend (fetch + Blob download + 501 toast) |

## UAT Checkpoint — NOT Executed by This Agent

The plan contains a `checkpoint:human-verify` task (Task 2) reserved for the user/orchestrator to run **after** this executor returns. The executor does not block on it.

### How the user can verify

1. **Start backend** (in one terminal):
   ```bash
   cd /home/charles/job_description_builder/v2/backend && uvicorn app.main:app --reload --port 8000
   ```
2. **Start frontend** (in another terminal):
   ```bash
   cd /home/charles/job_description_builder/v2/frontend && npm run dev
   ```
3. Open `http://localhost:5173` in a browser.
4. Complete the conversation flow through to Review state (or restore a saved WD with OG + JES confirmed).
5. Click **"Export DOCX"** — expect a `.docx` file download named after the position title.
6. Click **"Export PDF"** — expect a `.pdf` download **or** a 5-second diagnostic toast (PDF is environment-dependent).
7. Click **"Copy"** — expect the existing "Job description copied to clipboard" toast (no fetch, no error).
8. (Optional) Re-run backend tests to confirm nothing regressed:
   ```bash
   cd /home/charles/job_description_builder/v2/backend && python -m pytest tests/ -q --tb=no
   ```

### Resume signal

After verifying, the user can type `approved` or `issues: [description]` to advance the workflow.

## Threat Surface Note

This plan modifies a single trust boundary (browser → export endpoints) and mitigates the in-memory Blob URL leak risk via immediate `URL.revokeObjectURL`. The `wd_id` in the URL is React state (not user input), as captured in the plan's threat model T-20-03-01.

## Self-Check: PASSED

- ✓ `v2/frontend/src/app.jsx` exists, modified
- ✓ Commit `cb137bc` exists in git log
- ✓ All 7 acceptance criteria pass
- ✓ 31/31 frontend tests pass
- ✓ Sync stub removed (grep returns 0)
- ✓ All 6 key implementation behaviors present (async, blob, revoke, 501, guard, clipboard preserved)
