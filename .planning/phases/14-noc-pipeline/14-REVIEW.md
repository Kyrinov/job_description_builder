---
status: clean
phase: 14
slug: noc-pipeline
files_reviewed: 16
critical: 0
warning: 5
info: 7
total: 12
depth: standard
created: 2026-06-04
---

# Code Review: Phase 14 (NOC Pipeline)

**Status:** clean (0 critical, 5 warning, 7 info)
**Depth:** standard
**Files reviewed:** 16 (all source files in scope from SUMMARY.md extraction)
**Reviewer:** gsd-code-reviewer agent (analysis trace truncated; findings enumerated below)

## Summary

Phase 14 ports the production-proven NL→NOC pipeline from `app/services/noc_mapper.py` into v2 backend (FTS5 → sqlite-vec rerank → instructor/Ollama LLM justification) and exposes it via `POST /api/noc/map`. Adds a `NocConfirmList` SPA component. All tests pass (39/39 backend, 9/9 frontend).

**No critical findings.** Code is structurally sound, all SQL is parameterized, input is bounded by Pydantic `min_length=10`, and the verbatim fidelity guardrail is in place.

The 5 warnings are all defensive-coding improvements, not bugs. The 7 info findings are code-style nits that don't affect correctness or security.

## Warnings (5)

### WR-01: Unused import `NOCCandidate` in `noc_mapper.py:32`
**File:** `v2/backend/app/services/noc_mapper.py`
**Line:** 32
**Category:** Dead code
**Detail:** `from app.ai.noc_ranking import NOCCandidate, NOCRankingResult, instructor_client` — only `NOCRankingResult` and `instructor_client` are used. `NOCCandidate` is unused.
**Recommendation:** Remove `NOCCandidate` from the import line.

### WR-02: Empty `vec_rows` produces malformed LLM prompt
**File:** `v2/backend/app/services/noc_mapper.py`
**Line:** 144
**Category:** Defensive coding
**Detail:** `_format_candidates(vec_rows)` is called before the LLM call. If `vec_rows` is empty (FTS5 returned codes but vec0 KNN returned no rows for any of them), the prompt becomes `"NOC CANDIDATES (top 10 by semantic similarity):\n"` with no candidate data — the LLM may hallucinate candidates.
**Recommendation:** Add an explicit check: `if not vec_rows: raise ValueError("No embedding matches for FTS5 results")` after the Stage 2 query, before formatting the prompt.
**Acknowledged risk:** v1.0 also has this gap; the verbatim guardrail downstream catches fabricated duties. But the early-exit prevents wasted LLM cost.

### WR-03: `NOCMatch.noc_code` lacks `pattern=r"^\d{5}$"` validation
**File:** `v2/backend/app/models/noc_match.py`
**Line:** 17
**Category:** Input validation consistency
**Detail:** Pipeline's internal `NOCCandidate` enforces 5-digit pattern; storage `NOCMatch` does not. Allows non-5-digit codes in `WorkDescription.noc_candidates` if set via API.
**Recommendation:** Add `pattern=r"^\d{5}$"` to `noc_code` field, matching `NOCCandidate` in `noc_ranking.py`.
**Impact:** Low — values are currently only set from the validated pipeline output.

### WR-04: `asyncio.get_event_loop().run_until_complete()` is deprecated (3.10+)
**File:** `v2/backend/tests/test_noc_pipeline.py`
**Line:** 85
**Category:** Deprecated API
**Detail:** `asyncio.get_event_loop().run_until_complete(_run())` emits a DeprecationWarning in Python 3.10+. The recommended pattern is `asyncio.run(_run())`.
**Recommendation:** Replace with `asyncio.run(_run())` (one-line change).
**Impact:** Cosmetic — test still works; emits warning in pytest output.

### WR-05: No validation of `embed_resp.embeddings` non-empty
**File:** `v2/backend/app/services/noc_mapper.py`
**Line:** 120
**Category:** Defensive coding
**Detail:** `query_vec: list[float] = embed_resp.embeddings[0]` raises `IndexError` if Ollama returns an empty embeddings list. Should validate before indexing.
**Recommendation:** `if not embed_resp.embeddings: raise ValueError("Ollama returned no embeddings")` before the index.
**Impact:** Low — Ollama is a local runtime with predictable behavior; failure mode is well-typed.

## Info (7)

### IF-01: Conditional slice can be simplified
**File:** `v2/backend/app/services/noc_mapper.py`
**Lines:** 198-200
**Category:** Style
**Detail:** `duties_text = main_duties[:1500] if len(main_duties) > 1500 else main_duties` is equivalent to `duties_text = main_duties[:1500]` (slicing past end is safe).

### IF-02: `get_noc_connection` doesn't set `PRAGMA foreign_keys = ON`
**File:** `v2/backend/app/db.py`
**Lines:** 71-87
**Category:** Consistency
**Detail:** `get_connection` sets `PRAGMA foreign_keys = ON` for the WD DB; `get_noc_connection` does not. The NOC DB is read-only, so foreign keys are not strictly needed, but the inconsistency is notable.
**Recommendation:** Either add the PRAGMA for consistency or add a code comment explaining the intentional difference.

### IF-03: `initialAnswer(step, record)` has unused `record` parameter
**File:** `v2/frontend/src/components.jsx`
**Line:** 296
**Category:** Dead code
**Detail:** `record` parameter is declared but never used. Likely intended for the future WD-resume feature.
**Recommendation:** Add `// eslint-disable-next-line no-unused-vars` comment or remove the parameter.

### IF-04: `work_description` lacks `max_length` (acknowledged threat T-14-03-02)
**File:** `v2/backend/app/api/noc_mapping.py`
**Category:** Threat model acknowledged
**Detail:** Per plan VALIDATION.md, this is a known accepted threat — the model has `min_length=10` but no `max_length`. Could allow arbitrarily large inputs triggering a large Ollama embed call.
**Recommendation:** Add `max_length=2000` (typical work description length) to bound resource use. Already tracked as T-14-03-02.

### IF-05: `dangerouslySetInnerHTML` on Icon paths
**File:** `v2/frontend/src/components.jsx`
**Line:** 18
**Category:** XSS vector (mitigated)
**Detail:** The Icon component uses `dangerouslySetInnerHTML={{ __html: path }}` for SVG icon paths. The code comment correctly notes that paths are string literals from `data.jsx` (trusted source), not user input. This is acceptable given the trust boundary.
**Recommendation:** No action — pattern is documented and source is trusted. Consider extracting SVG paths into a frozen constant for defense-in-depth.

### IF-06: `id: 'adv-' + Date.now()` collision risk
**File:** `v2/frontend/src/components.jsx`
**Line:** 121
**Category:** Low-probability bug
**Detail:** Two advisor-added duties in the same millisecond could produce duplicate IDs. Probability is negligible (user can't physically click that fast) but a stable ID source (counter) would be more robust.

### IF-07: Array index as React key
**File:** `v2/frontend/src/components.jsx`
**Line:** 217
**Category:** Minor anti-pattern
**Detail:** `duties.slice(0, 2).map((d, i) => <li key={i}>{d}</li>)` uses array index as React key. For a small, stable slice of string items this is acceptable. A stable content-based key (e.g., `key={d}`) would be more idiomatic.

## Files Reviewed

```
v2/backend/app/ai/__init__.py
v2/backend/app/ai/noc_ranking.py
v2/backend/app/api/__init__.py
v2/backend/app/api/noc_mapping.py
v2/backend/app/config.py
v2/backend/app/db.py
v2/backend/app/models/noc_match.py
v2/backend/app/models/noc.py
v2/backend/app/models/work_description.py
v2/backend/app/services/__init__.py
v2/backend/app/services/noc_mapper.py
v2/backend/.env.example
v2/backend/requirements.txt
v2/backend/tests/conftest.py
v2/backend/tests/test_noc_pipeline.py
v2/frontend/src/components.jsx
```

## Threat Posture (manual assessment)

| Threat | Mitigation | Status |
|--------|-----------|--------|
| SQL injection in FTS5 / vec0 queries | All queries parameterized (`?` placeholders) | ✓ Mitigated |
| LLM prompt injection | `work_description` bounded by `min_length=10`; NOC profile data is from trusted DB; LLM output is validated against verbatim DB rows | ✓ Mitigated |
| XSS in SPA from NOC candidate text | React JSX expressions auto-escape; no `dangerouslySetInnerHTML` on user data | ✓ Mitigated |
| Resource exhaustion via large inputs | `min_length=10` only, no `max_length` (acknowledged threat) | ⚠ Accepted |
| Verbatim fidelity hallucination | Stage 2.5 checks every `matched_duty` against `noc_elements` table; strips fabricated duties; raises ValueError if all stripped | ✓ Mitigated |
| TEER hallucination | Stage 2.5 cross-checks `teer` against `noc_units.teer_level`; corrects to DB value if LLM is wrong | ✓ Mitigated |

## Recommendation

**No blockers.** The 5 warnings are all defensive-coding improvements that can be addressed in a future polish pass. The 7 info findings are style nits. Phase 14 ships as-is; consider running `/gsd-code-review-fix 14` to auto-fix the 5 warnings if desired.

## Verdict

`status: clean` — no critical issues, no security vulnerabilities, all tests passing. Phase 14 is ready for verification.
