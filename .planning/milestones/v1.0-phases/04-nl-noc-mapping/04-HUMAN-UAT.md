---
status: complete
phase: 04-nl-noc-mapping
source: [04-VERIFICATION.md]
started: 2026-06-01T22:00:00Z
updated: 2026-06-02T00:00:00Z
---

## Tests

### 1. Run scripts/rebuild_noc_vectors.py against the live app.db
expected: "[4/4] Updating index_metadata..." then "Done. noc_chunks_vec rebuilt as FLOAT[768]". Required because Phase 2 ingest created FLOAT[1024] vectors (DashScope) but Phase 4 requires FLOAT[768] (nomic-embed-text).
result: PASS — vectors rebuilt successfully; server starts with no model-mismatch assertion error.

### 2. Start the server: uvicorn app.main:app --reload
expected: Server starts without RuntimeError about embedding model mismatch (assert_noc_index_model passes).
result: PASS — server starts clean.

### 3. Open http://localhost:8000/wizard/noc in a browser
expected: Page renders with 'NL→NOC Mapping' heading, 'Work Description' label, textarea, and 'Find NOC Candidates' button (per UI-SPEC).
result: PASS — page renders correctly.

### 4. Submit a real work description
expected: NOC candidate cards appear. Each card shows NOC code, unit group title, TEER level badge, bulleted matched duty list, expandable LLM justification, and a 'Confirm this NOC' button.
result: PASS — pipeline completed via DashScope qwen3.7-max; candidate cards rendered correctly.

### 5. Click 'Confirm this NOC' on a candidate
expected: Confirmation banner appears; confirmed_noc persisted on WorkDescription (stage='noc_mapped').
result: PASS — confirmation panel rendered after fix to confirm route (was returning raw JSON; fixed to return HTML partial for HTMX requests).

## Issues Found and Resolved

| Issue | Fix | Commit |
|-------|-----|--------|
| DashScope 401: wrong endpoint (domestic vs international) | `cloud_base_url` → `dashscope-intl.aliyuncs.com` | 7bb151d |
| DashScope 404: wrong model name (`qwen-3.7-max` → `qwen3.7-max`) | `cloud_model` default corrected | 7bb151d |
| Confirm route returned raw JSON to HTMX | Added `HX-Request` branch; new `noc_confirmed.html` partial | 9631a38 |

## Summary

total: 5
passed: 5
issues: 3 (all resolved)
pending: 0
skipped: 0
blocked: 0
