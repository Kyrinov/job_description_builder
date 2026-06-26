---
quick_id: 260626-ejt
title: Synthesize org context into fluid prose via LLM; prune redundant fields
date: 2026-06-26
status: complete
commit: 65b46c2
---

# Summary — 260626-ejt

## What changed
The `org_context` questionnaire step ("Tell me about the organizational context…")
asked four questions; two of them — **Organizational placement** and **Reporting
relationship** — duplicated data already captured in Phase 0 (`record.branch`,
`record.reports`). Those two fields were removed. The remaining **Work stream /
program** and **Additional context** fields now feed an LLM that produces fluid
prose for the Organizational Context section instead of mechanical concatenation.

## How it works
- **`OrgContextInput`** (`frontend/src/components.jsx`) renders two textareas, seeds
  state from `value` (re-edit repopulates), and emits `{ work_stream, additional }`.
- **`org_context` step** (`frontend/src/data.jsx`) `apply()` stashes the raw parts in
  `org_context_parts` and writes a **joined-plain-text fallback** to `org_context`.
- **`commit()`** (`frontend/src/app.jsx`) — on Continue, chains off the WD persist
  promise to POST `{ branch, reports, work_stream, additional }` to the new endpoint,
  then `setRecord({ org_context: prose })` and PATCHes the WD. A toast shows progress.
- **`POST /api/org-context/synthesize`** (`backend/app/api/org_context.py`) — module-
  level `AsyncOpenAI` singleton (cloud MiniMax or Ollama), plain chat completion,
  1–3 sentence system prompt. 422 on empty input, 502 on LLM error.

## Decisions (user-confirmed)
- Trigger: **on Continue**.
- Inputs: **branch + reports + work_stream + additional** (no inference).
- Fallback: **joined plain text** stays if synthesis fails — no error shown.

## Verification
- `backend`: `pytest -q` → **188 passed**; new `tests/test_org_context.py` → 4 passed.
- `frontend`: `npm run test` → **88 passed** (OrgContextInput test updated to the
  object-emit contract + new re-edit seeding test).
- `ruff check` on new/changed backend files → clean.

## Commits
- `2bd2659` feat(backend): add org-context prose synthesis endpoint
- `65b46c2` feat(ui): synthesize org context into fluid prose; prune redundant fields

## Notes / follow-ups
- The Organizational Context document section already shows the fallback text
  immediately and upgrades to prose in place when synthesis resolves; the result
  remains editable in Review (`onEditStep('org_context')`).
- In-flight sessions persisted before this change stored `org_context` as a string;
  re-entering the step starts fresh (object answer). Acceptable edge case.
