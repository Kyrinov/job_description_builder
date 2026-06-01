---
status: partial
phase: 04-nl-noc-mapping
source: [04-VERIFICATION.md]
started: 2026-06-01T22:00:00Z
updated: 2026-06-01T22:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Run scripts/rebuild_noc_vectors.py against the live app.db
expected: "[4/4] Updating index_metadata..." then "Done. noc_chunks_vec rebuilt as FLOAT[768]". Required because Phase 2 ingest created FLOAT[1024] vectors (DashScope) but Phase 4 requires FLOAT[768] (nomic-embed-text).
result: [pending]

### 2. Start the server: uvicorn app.main:app --reload
expected: Server starts without RuntimeError about embedding model mismatch (assert_noc_index_model passes).
result: [pending]

### 3. Open http://localhost:8000/wizard/noc in a browser
expected: Page renders with 'NL→NOC Mapping' heading, 'Work Description' label, textarea, and 'Find NOC Candidates' button (per UI-SPEC).
result: [pending]

### 4. Submit a real work description (e.g., 'Reviews and analyzes federal government procurement policies...')
expected: NOC candidate cards appear below the form within 5 minutes. Each card shows NOC code, unit group title, TEER level badge, bulleted matched duty list, expandable LLM justification, and a 'Confirm this NOC' button.
result: [pending]

### 5. Click 'Confirm this NOC' on a candidate
expected: Confirmation banner or next wizard step appears; confirmed_noc is persisted on the WorkDescription record (set stage='noc_mapped').
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps

[none — all pending items are human-action verification of live Ollama integration per 04-04-PLAN.md:438-480 checkpoint:human-verify]
