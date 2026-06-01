---
phase: 03-ca-jes-data-pipeline
plan: 04
type: summary
status: complete
completed: 2026-06-01
---

# Plan 03-04 Summary — Real-Data Run

## What was built

All three Phase 3 ingest pipelines ran successfully against real source data and were
verified by automated SQL assertions and a human spot-check.

### Data ingested

| Table | Rows | Source |
|-------|------|--------|
| `ca_clauses` | 578 | 28 CA JSONs across 33 OG codes |
| `jes_factors` | 105 | 16 JES OG evaluation standard TXTs |
| `jes_og_metadata` | 16 | same JES files |
| `policy_chunks` | 190 | 2 TBS policy TXTs (directive + policy_on_people_management) |
| `source_documents` | 46 | 28 CA + 16 JES + 2 policy |

### Quality spot-check results (Task 3)

All 5 checks passed:

1. **EC restriction clauses** — Article 13.01 (outside employment restriction): semantically correct
2. **EC scope clauses** — Articles 1.01 & 3.01 describing coverage: correct
3. **IT/CS multi-OG split** — both OGs have 6 clauses each (equal, > 0): correct
4. **EC JES Decision Making** — D1–D8 extracted with exact points 5/15/35/60/90/125/165/210: perfect match
5. **Policy FTS retrieval** — `MATCH 'AS OR EC OR classification'` returns Directive on Classification chunks: correct

### Known gaps (accepted)

- **CT-FIN / CT-EAV**: source files contain only placeholder text; only CT-IAU sub-group has extractable factor data
- **EX Problem Solving / Accountability degrees**: Hay chart tables absent from source TXT; factor names extracted but no degree descriptors
- **NOC tables empty**: `app.db` was rebuilt during Phase 3 development; Phase 2 NOC ingest (`ingest_noc.py`) must be re-run before Phase 4 work begins

### Technical fixes required during this plan

- `think: False` moved to top-level Ollama payload (was ignored inside `options`)
- Pydantic schema inlined in `format` field (Ollama grammar parser rejects `$defs`/`$ref`)
- System message added to force JSON-only output
- Bare array response handler added (`if isinstance(parsed, list)`)
- PS OG methodology corrected from `point-rating` to `level-descriptions` (direct DB fix)

## Verification

```
sqlite3 app.db "SELECT COUNT(*) FROM ca_clauses"           -- 578
sqlite3 app.db "SELECT COUNT(DISTINCT og_code) FROM ca_clauses"  -- 33
sqlite3 app.db "SELECT COUNT(*) FROM jes_factors"          -- 105
sqlite3 app.db "SELECT COUNT(DISTINCT og_code) FROM jes_factors"  -- 16
sqlite3 app.db "SELECT COUNT(*) FROM policy_chunks"        -- 190
python -m pytest tests/ -x -q                              -- 75 passed
```

## Deviation from plan

Plan expected 49 `source_documents` rows (2 NOC + 28 CA + 17 JES + 2 policy). Actual is 46:
- 0 NOC rows (DB rebuilt; Phase 2 re-run needed)
- 16 JES files (plan overcounted; 16 OG standards exist, consistent with 16 OGs in `jes_og_metadata`)

All Phase 3 acceptance criteria pass. Source count deviation is a Phase 2 re-run task, not a Phase 3 failure.
