---
status: partial
phase: 14-noc-pipeline
source: [14-VERIFICATION.md]
started: 2026-06-04T18:50:00Z
updated: 2026-06-04T18:50:00Z
---

## Current Test

Awaiting human testing — Phase 14 implementation is complete and all automated checks pass (39/39 backend, 9/9 frontend, 0 regressions). 2 items need human eyes before the phase can be marked fully verified.

## Tests

### 1. Visual browser rendering of NOC candidate cards
expected: Open browser, navigate to a STEPS entry with `type: 'noc_confirm'` and a `candidates` array. Each candidate card renders with noc_code, title, TEER badge, and up to 2 matched duties. Clicking a card applies the `is-sel` CSS class. `onChange(noc_code)` fires on click.
result: [pending]

### 2. Live NOC pipeline execution with real Ollama
expected: With Ollama running on `localhost:11434` (gemma4:31b + nomic-embed-text:latest pulled) and v2 backend booted with `NOC_DB_PATH=/home/charles/job_description_builder/app.db`, `POST /api/noc/map` returns 1-5 candidates with code, title, TEER, and verbatim duty matches. Stages 1-3 execute in sequence; online guardrails strip fabricated duties.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps

No gaps blocking Phase 14 completion. Both items are non-blocking and consistent with the phase boundary:
- Item 1 is Phase 15 work (Plan 04 explicitly defers STEPS wiring to Phase 15).
- Item 2 was approved in the plan's UAT checkpoint (live browser rendering deferred to Phase 15 STEPS wiring; live Ollama execution is a quality check, not a blocker).

To run Item 1 manually:
```bash
# Temporary STEPS entry (add to v2/frontend/src/data.jsx, remove after):
# { id: 'noc-test', title: 'NOC Test', input: { type: 'noc_confirm', candidates: [
#   { noc_code: '21232', title: 'Software engineers and designers', teer: 1, matched_duties: ['Develop software.'] },
#   { noc_code: '21211', title: 'Data scientists', teer: 1, matched_duties: ['Analyze data.'] }
# ] } }
cd /home/charles/job_description_builder/v2/frontend && npm run dev
# Navigate to the test step; verify cards render; click a card; verify is-sel
```

To run Item 2 manually:
```bash
# Start Ollama
ollama serve &
ollama pull gemma4:31b
ollama pull nomic-embed-text:latest

# Boot v2 backend
cd /home/charles/job_description_builder/v2/backend
echo "NOC_DB_PATH=/home/charles/job_description_builder/app.db" >> .env
uvicorn app.main:app --port 8000 &

# Send a real work description
curl -X POST http://localhost:8000/api/noc/map \
  -H 'Content-Type: application/json' \
  -d '{"work_description": "develop and maintain application software in an agile team"}'
```
