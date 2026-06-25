# GSD Phase 4 Issues — Debug Brief

**Phase:** 04-nl-noc-mapping
**Status:** Code-complete, 91/91 automated tests pass, but live UI broken
**Date:** 2026-06-01
**Prepared for:** Claude Sonnet 4.6 debug session

---

## TL;DR

Phase 4 implementation is correct and fully tested in isolation, but the live `POST /api/noc/map` endpoint returns **HTTP 422 Unprocessable Entity** for every natural-language work description an advisor types into the wizard UI. The root cause is in **Stage 1 of the three-stage pipeline** (FTS5 keyword shortlist), where the query is too restrictive for natural-language input.

**Recommended fix:** Rewrite the FTS5 query to OR-join key terms (after stop-word filtering) instead of passing the raw work description. The FTS5 shortlist is supposed to be a broad-recall filter, not a strict AND-match — Stage 2 (embedding rerank) and Stage 3 (LLM justification) are the precision stages.

---

## 1. Symptom (from live user test)

The user opened `http://localhost:8000/wizard/noc`, typed a plain-language work description, clicked "Find NOC Candidates", and the candidate list never appeared. The server log showed:

```
INFO:     127.0.0.1:45968 - "POST /api/noc/map HTTP/1.1" 422 Unprocessable Entity
INFO:     127.0.0.1:36088 - "POST /api/noc/map HTTP/1.1" 422 Unprocessable Entity
INFO:     127.0.0.1:40384 - "POST /api/noc/map HTTP/1.1" 422 Unprocessable Entity
(repeated 5+ times)
```

**Reproduces 100% of the time** with multi-sentence natural-language input. Single keywords (e.g. typing just "procurement") likely work.

The 422 is raised by this code path in `app/api/noc_mapping.py`:

```python
try:
    result = await map_work_description(...)
except ValueError as exc:
    raise HTTPException(status_code=422, detail=str(exc))
```

And the `ValueError` is raised in `app/services/noc_mapper.py:69-72` when the FTS5 shortlist is empty:

```python
if not fts_rows:
    raise ValueError(
        "FTS5 shortlist empty — work description has no lexical overlap with NOC corpus"
    )
```

So the 422 is the **empty FTS5 shortlist** guardrail firing.

## 2. Why the FTS5 shortlist is empty (root cause)

The Stage 1 query at `app/services/noc_mapper.py:53-67` passes the work description **raw** to FTS5's `MATCH` operator:

```python
SELECT DISTINCT f.noc_code, u.title, ...
FROM noc_fts f
JOIN noc_units u ON u.noc_code = f.noc_code
WHERE noc_fts MATCH ?
ORDER BY rank
LIMIT ?
```

FTS5's default MATCH semantics is **implicit AND** — all terms in the query string must match in a single FTS5 row for it to be returned. With the `porter ascii` tokenizer, common English stop words (`and`, `the`, `of`, `to`, `in`, `is`, `a`, `an`) are stripped at index time but not at query time, so the query still has to match the remaining terms.

For the example work description `Reviews and analyzes federal government procurement policies`, FTS5 tokenizes this into 6 terms after stop-word removal: `reviews`, `analyzes`, `federal`, `government`, `procurement`, `policies`. FTS5 then requires ALL 6 of these to appear in a single FTS5 row.

But NOC profiles don't contain "reviews" or "analyzes" or "federal" as duty text — they have duty statements like "Procure and purchase general and specialized equipment, materials or business services". So no FTS5 row matches all 6 terms, and the shortlist is empty.

### Empirical evidence (tested against the live `app.db`)

I ran the actual FTS5 queries against the live DB to confirm this diagnosis:

| Query | Rows returned |
|-------|---------------|
| `develop and maintain application software` | 5 (including NOC 21231 "Software engineers and designers") |
| `software` | 5 (includes "Data entry clerks" — false positive from definition text) |
| `procurement` | 5 (including NOC 12102 "Procurement and purchasing agents and officers") |
| `policy` | 5 (including senior managers) |
| `reviews and analyzes federal government procurement policies` | **0** (the user's actual input) |

The pattern is clear: **single keywords work, multi-word sentences don't**, because the implicit AND requires all words to match in a single document.

This was not caught by the test suite because:
- `test_fts5_stage_returns_noc_codes` uses the short query `"develop and maintain application software"` (5 terms, all NOC-relevant) which happens to return rows
- The fixture's synthetic data is sparse (1 NOC unit, 1 element) so the AND-mode query is more likely to find a match
- No test exercises a realistic multi-sentence work description

## 3. Files involved

| File | Lines | Role |
|------|-------|------|
| `app/services/noc_mapper.py` | 53-72 | Stage 1 FTS5 query — the broken line |
| `app/api/noc_mapping.py` | 50-56 | Catches `ValueError` and returns 422 |
| `app/db.py` | 50-58 | `NOC_SCHEMA_DDL` for `noc_fts` — has the `UNINDEXED`+`content=''` bug (separate issue, see §5) |
| `tests/test_noc_mapping.py` | 17-50 | `test_fts5_stage_returns_noc_codes` uses too-short a query to catch this |
| `tests/conftest.py` | 119-140 | `noc_mapping_db` fixture works around the DDL bug by dropping+recreating `noc_fts` |
| `app/templates/partials/noc_results.html` | n/a | Shows `.empty-state` if no candidates — but this never triggers because we raise before returning |

## 4. Recommended fix

Tokenize the work description, filter stop words, and OR-join the remaining terms before passing to FTS5. The FTS5 stage is the **broad-recall filter** — it should return ANY candidate whose profile mentions at least one key term. Stages 2 (embedding rerank) and 3 (LLM justification) provide the precision.

### Implementation sketch

Add a helper to `app/services/noc_mapper.py`:

```python
# Common English stop words + work-description-specific verbs that don't help discriminate NOC codes
_FTS_STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "in", "is", "it", "its", "of", "on", "or", "that", "the", "this", "to", "was",
    "were", "will", "with", "you", "your",
    # Work-description verbs that are too generic to discriminate:
    "reviews", "analyzes", "review", "analyze", "provides", "develops", "develop",
    "performs", "perform", "responsible", "responsibilities", "duties", "tasks",
    "including", "include", "may", "also", "well", "such", "etc",
})


def _fts_query_from_text(text: str) -> str:
    """Convert a natural-language work description into an OR-joined FTS5 query string.

    Splits on whitespace + punctuation, lowercases, filters stop words and short
    tokens (< 3 chars). Joins remaining terms with ' OR ' so FTS5 returns rows
    matching ANY term (broad recall). Stages 2 & 3 narrow down to precision.

    Returns empty string if no usable terms remain (caller should raise
    ValueError → 422).
    """
    import re
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    keywords = [t for t in tokens if t not in _FTS_STOP_WORDS and len(t) >= 3]
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            deduped.append(kw)
    return " OR ".join(deduped)
```

Then in `map_work_description` at line 66, replace `(work_description, fts_limit)` with `(_fts_query_from_text(work_description), fts_limit)`. Also add a guard:

```python
fts_query = _fts_query_from_text(work_description)
if not fts_query:
    raise ValueError(
        "Work description produced no usable search terms after stop-word filtering. "
        "Please describe the work using more specific terms."
    )
fts_rows = await asyncio.to_thread(
    lambda: conn.execute("...", (fts_query, fts_limit)).fetchall()
)
```

### Expected behavior after fix

For the user's input `Reviews and analyzes federal government procurement policies`:
- Tokens after lowercasing: `reviews`, `and`, `analyzes`, `federal`, `government`, `procurement`, `policies`
- After stop-word + short-token filter: `federal`, `government`, `procurement`, `policies`
- FTS5 query: `federal OR government OR procurement OR policies`
- This will return NOC codes whose profiles contain ANY of these terms, including NOC 12102 "Procurement and purchasing agents and officers"
- Stage 2 embedding rerank narrows to top-10 by semantic similarity
- Stage 3 LLM justification ranks top-5 with verbatim duty citations

### Tests to add

1. `test_fts5_query_rewriting_strips_stop_words` — unit test for `_fts_query_from_text`:
   - `"reviews and analyzes federal government procurement policies"` → `"federal OR government OR procurement OR policies"`
   - `"the"` → `""` (caller raises 422)
   - `"a b c d e f"` (all short tokens) → `""` (caller raises 422)

2. `test_stage1_returns_candidates_for_real_work_description` — integration test:
   - Use a real-world work description (e.g. "Reviews and analyzes federal government procurement policies. Provides written advice to management on regulatory compliance.")
   - Run the full pipeline with mocked embed + LLM
   - Assert candidates is non-empty (currently would raise 422; after fix, returns candidates)

3. `test_fts5_query_empty_after_filtering_raises_value_error` — for the guard:
   - Pass work_description = "the a an" (only stop words)
   - Assert ValueError with appropriate message

## 5. Related (separate) issue — DDL bug masked by conftest

**Not the cause of the live 422**, but related. Code review found that `app/db.py:50-58` declares `noc_fts` with `noc_code UNINDEXED, content=''` (contentless), which makes `f.noc_code` unretrievable via SELECT in a contentless FTS5 table. The live DB happens to have the correct schema (noc_code indexed, no content='') because `scripts/ingest_noc.py` creates the FTS5 table with its own DDL, overriding the one in `create_schema()`.

The conftest fixture at `tests/conftest.py:121-127` (commit `69062e2`) drops and recreates `noc_fts` with the correct schema to make tests work. So the test suite is healthy. But:

- **Fresh deployments** that only run `create_schema()` (without the ingest script) would have broken FTS5 → empty shortlist → 422. The vector rebuild script (`scripts/rebuild_noc_vectors.py`) only rebuilds `noc_chunks_vec`, not `noc_fts`.
- This is **debt**, not a current production issue (live DB is fine). Flagged as MAJOR in `04-REVIEW.md`.

### Recommended fix (separate from the FTS5 query fix)

Update `NOC_SCHEMA_DDL` in `app/db.py:50-58` to match the live DB schema:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS noc_fts USING fts5(
    noc_code, title, definition, element_type, element_text,
    tokenize='porter ascii'
);
```

(Remove `UNINDEXED` from `noc_code` and `element_type`, remove `content=''`.)

Then the conftest fixture's drop+recreate block can be removed. `IF NOT EXISTS` means existing live DBs are unaffected.

## 6. UI feedback for empty shortlist (nice-to-have, not blocking)

Currently, when the FTS5 shortlist is empty, the route raises 422 and the HTMX partial never gets rendered — the user sees nothing in the `#noc-results` div. The partial's `{% else %}` branch has a `.empty-state` div with role="alert", but it's never reached because we raise before returning.

A better UX: when the shortlist is empty, return an empty `NocMapResponse` (or `NocMapResponse(candidates=[], wd_id=...)`) instead of raising, so the partial renders the `.empty-state` block:

```python
if not fts_rows:
    # Return empty result instead of raising — let the UI show the empty state
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/noc_results.html",
            {"request": request, "candidates": [], "wd_id": ""},
        )
    return NocMapResponse(candidates=[], wd_id="")
```

Combined with the FTS5 query rewriting (which should make this empty case very rare), this gives a graceful degradation. The 422 path remains for unexpected errors (e.g., LLM timeout, DB corruption).

## 7. Environment context for the debug session

- **Repo root:** `/home/charles/job_description_builder`
- **Python:** 3.10.12
- **Ollama:** running at `http://localhost:11434` with `gemma4:31b` (generation) and `nomic-embed-text:latest` (embedding) — both resident
- **Live DB:** `app.db` (44,515 FTS5 rows, 516 NOC unit groups)
- **Test DB:** tempfile per test, populated by `noc_mapping_db` fixture
- **Test command:** `python -m pytest tests/ -v` (currently 91/91 pass)
- **Key commits:**
  - `ea27077` — fix critical end-to-end flow bug (map_noc not persisting candidates)
  - `69062e2` — conftest FTS5 schema workaround
  - `893db7a` — turn 7 test stubs into real tests
  - `8900f7e` — code review (advisory, 0 blockers, 1 major, 1 minor, 6 info)

## 8. Useful commands

```bash
# Run all tests
python -m pytest tests/ -v

# Test only the FTS5 path against the live DB
python -c "
from app.db import get_connection
con = get_connection('app.db')
for q in ['procurement', 'reviews and analyzes federal government procurement policies', 'software', 'develop and maintain software']:
    rows = con.execute('SELECT DISTINCT f.noc_code, u.title FROM noc_fts f JOIN noc_units u ON u.noc_code = f.noc_code WHERE noc_fts MATCH ? LIMIT 5', (q,)).fetchall()
    print(f'{q!r}: {len(rows)} rows')
"

# Start the server and test in browser
uvicorn app.main:app --reload
# Then open http://localhost:8000/wizard/noc and try various inputs
```

## 9. Suggested approach for the debug session

1. **Confirm the diagnosis** by running the FTS5 query directly against the live DB (see §2)
2. **Implement the fix** at `app/services/noc_mapper.py:53-72` (add `_fts_query_from_text` helper, use it in the Stage 1 query)
3. **Add tests** at `tests/test_noc_mapping.py`:
   - Unit test for `_fts_query_from_text` (stop-word filtering, empty-result case)
   - Integration test with a realistic multi-sentence work description
4. **Verify the full suite** still passes (`pytest tests/ -v`)
5. **Optionally** implement the empty-state UI fix (§6) as a polish step
6. **Optionally** fix the DDL bug (§5) as a followup — separate commit, separate review

After the fix, the user's repro case (typing a multi-sentence work description) should return ranked NOC candidates within 5 minutes, with the matching NOC (e.g. NOC 12102 for procurement work) at the top of the list.
