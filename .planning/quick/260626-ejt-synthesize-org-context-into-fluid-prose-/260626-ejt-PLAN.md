---
quick_id: 260626-ejt
title: Synthesize org context into fluid prose via LLM; prune redundant fields
date: 2026-06-26
status: in-progress
---

# Quick Task 260626-ejt — Org Context fluid-prose synthesis

## Problem
The "Organizational context" questionnaire step (`org_context`) asks four questions.
Two of them — **Organizational placement** and **Reporting relationship** — duplicate
data already captured in Phase 0 (`record.branch`, `record.reports`). The remaining two
(**Work stream / program**, **Additional context**) are fine. The assembled value is
also just the raw fields concatenated, not natural prose.

## Decisions (user-confirmed)
- **Trigger:** synthesize on Continue (commit of the `org_context` step).
- **Inputs:** branch + reports + work_stream + additional (the four data points, nothing inferred).
- **Fallback:** if the LLM call fails/unavailable, keep the joined plain text already
  written to `record.org_context` (current behavior). No error surfaced to the advisor.

## Tasks

### T1 — Prune OrgContextInput to two fields (frontend)
`frontend/src/components.jsx`
- `OrgContextInput`: drop `org_placement` + `reporting` textareas. Keep `work_stream` +
  `additional`. Initialize state from `value` (object) so re-edit repopulates. Emit an
  object `{ work_stream, additional }` via `onChange`.
- `initialAnswer` (`org_context_input`) → `{ work_stream: '', additional: '' }`.
- `answerValid` (`org_context_input`) → object with non-empty `work_stream`.

### T2 — Step apply + transcript emit object/fallback (frontend)
`frontend/src/data.jsx` (`org_context` step)
- `apply`: `{ org_context_parts: a, org_context: join(work_stream, additional) }`
  (joined plain text = the fallback).
- `transcript`: derive preview from the parts (answer is now an object, not a string).

### T3 — Backend synthesis endpoint
`backend/app/api/org_context.py` (new) + register in `backend/app/api/__init__.py`
- `POST /api/org-context/synthesize` → `{ prose }`.
- Module-level `AsyncOpenAI` singleton (cloud MiniMax or Ollama), mirrors
  `app/ai/jes_scoring.py`. Plain chat completion (free-form prose, no instructor).
- 422 if all inputs empty; 502 on LLM error/empty (frontend swallows → fallback stays).

### T4 — Wire synthesis on Continue (frontend)
`frontend/src/app.jsx` (`commit`)
- After the JES trigger, add an `org_context` trigger: chain off `wdPromise`, POST the
  four data points, on success `setRecord({ org_context: prose })` + PATCH the WD.
  Toast affordance while in flight; cleared on settle. Non-blocking on failure.

### T5 — Backend test
`backend/tests/test_org_context.py` (new)
- Patch `org_context_client.chat.completions.create` with `AsyncMock`; assert prose
  returned. Assert 422 on all-empty payload.

## Verify
- `cd backend && python -m pytest tests/test_org_context.py -q`
- `cd frontend && npm run test`
- `cd backend && ruff check app/api/org_context.py`
