---
status: passed
phase: 07-jes-scoring
date: 2026-06-02
verifier: general-agent
---

# Phase 7 Verification Report

## Goal-Backward Summary

Phase 7 Goal: With a confirmed WD and duty list, the system generates a JES scoring sheet for the confirmed OG by making one configured local generation model call per JES factor — injecting the full factor descriptor and degree definitions fresh per call — returning a structured scoring object validated by Pydantic via `instructor` with up to 3 retries.

All four success criteria are satisfied. The implementation mirrors the structural analogs from Phase 6 (`jd_ranking.py`, `jd_service.py`, `jd_generation.py`) exactly, with the documented deviations: sequential per-factor loop (not asyncio.gather), `level=-1` failure sentinel, and the `'jd_drafted'` stage gate. The human verify checkpoint in Plan 07-04 was approved; 10 factor cards rendered end-to-end in the live UI.

## Success Criteria

### SC#1: POST /score-jes returns complete scoring sheet
**Status:** PASS
**Evidence:** `app/api/jes_scoring.py:27` registers `@router.post("/api/jes/score")`. Handler calls `score_jes()` and returns the result dict containing `jes_scores` (list of `JESFactorScore.model_dump()` dicts, each with `level` int and `rationale` str) and `jes_total_points`. The HTMX path additionally renders `templates/partials/jes_scores.html` with one factor card per score. Tests `TestJESScoringStageGate::test_score_jes_stage_gate` (422 on wrong stage) and `TestJESScoringStageGate::test_score_jes_404_on_unknown_wd` (404 on unknown wd) both PASS.

### SC#2: Full factor descriptor + degree definitions injected fresh per call
**Status:** PASS
**Evidence:** `app/services/jes_service.py:195-214` — the per-factor loop iterates `for factor_row in factor_rows` and calls `_build_factor_user_prompt(factor_row, duties, wd.raw_input)` (line 196) which `json.loads(factor_row["degree_descriptors"])` (line 49) and renders every degree line as `"  {d['degree']} ({d.get('points', '?')} pts): {d['text']}"`. Each call gets a different `factor_row` (loaded `ORDER BY id` on line 165), the system prompt is freshly formatted with `og_name=og_name, og_code=confirmed_og` (line 203), and the user prompt is built fresh per factor. No summary or cached prompt is used.

### SC#3: instructor retries 3x; descriptive error on failure (not silent null)
**Status:** PASS
**Evidence:** `app/services/jes_service.py:210` — `max_retries=3` passed to `jes_instructor_client.chat.completions.create(...)`. Per-factor `try/except Exception` (line 197 / line 218) catches any failure after the 3 retries, logs a warning (line 219), and produces a `JESFactorScore(level=-1, points=None, rationale=f"Scoring failed after 3 retries: {exc}", provenance=...)` via `_make_error_score()` (line 103). `JESFactorScore.level: int` (non-optional, see `app/models/work_description.py:74`) — `level=-1` is a valid sentinel (None would be invalid Pydantic). The `_make_error_score` builder enforces this pattern. `TestJESFactorScoreSchema::test_jes_factor_score_sentinel_level` PASSES.

### SC#4: Scoring sheet on WD with ProvenanceTags → JES source
**Status:** PASS
**Evidence:** `app/services/jes_service.py:230-238` — after the per-factor loop, `wd.model_copy(update={"jes_scores": jes_scores, "jes_total_points": jes_total, "stage": "jes_scored"})` is constructed and `save_work_description(conn, updated_wd)` persists the WD. Every `JESFactorScore` (success or failure) carries a `ProvenanceTag(source_type="JES", source_id=f"{og_code}/{factor_row['factor_name']}", source_version=jes_version, retrieved_date=date.today())` — built in both `_build_jes_factor_score` (line 94-99) and `_make_error_score` (line 115-121). The `source_id` format `{og_code}/{factor_name}` links each factor to its specific `(og_code, factor_name)` DB row. `TestProvenanceTagJES::test_provenance_tag_source_type_jes` PASSES.

## Test Suite
- 8 passed, 1 skipped, 0 failed (in `tests/test_jes_scoring.py`)
- Full project suite: 149 passed, 1 skipped, 0 failed
- Critical JES-specific tests:
  - TestJESScoringStageGate (2 tests): PASSED
  - TestJESFactorScoreSchema (2 tests — fields + sentinel): PASSED
  - TestJESFactorRatingSchema (1 test): PASSED
  - TestProvenanceTagJES (1 test): PASSED
  - TestNoFactors (1 test): PASSED
  - TestStageTransition (1 test): SKIPPED (requires LLM mock — non-blocking, same status as Phase 6's analogous test)
  - TestJESInstructorClient (1 test): PASSED

## Issues Found

None that affect the success criteria. The code review at `07-REVIEW.md` flagged five minor items — one MEDIUM and four LOW — which do not change the phase outcome:

- **MEDIUM (logged, not blocking):** `_build_jes_factor_score` in `app/services/jes_service.py:76-83` silently sets `points=None` (contributing 0 to total) if the LLM returns a degree that is parseable to a numeric `level` but missing from the `point_values` dict. The fix has been partially applied: a `logger.warning(...)` now fires on line 79, making the data-integrity issue visible in logs. Full resolution (treating such factors as failures with `level=-1`) is deferred to a follow-up.
- **LOW:** Layer 10 CSS uses custom-property names (`--color-primary`, `--color-error-bg`, etc.) that are not declared in the Layer 2 `:root` token block; each rule has an inline fallback so the page renders correctly.
- **LOW:** `templates/partials/jes_scores.html:27-28` has `aria-disabled="true"` on a live `<a href="/wizard/export?wd_id=...">` that 404s today (Phase 8 route not yet mounted).
- **LOW:** `_make_error_score` rationale says "Scoring failed after 3 retries" even when the failure is non-LLM (e.g., malformed `point_values` JSON in the DB row).
- **LOW:** Dead defensive branches in degree→level parser (`AttributeError` catch is unreachable given the Pydantic `str` guarantee).

These are quality items, not correctness issues for the success criteria. They are safe to address in a single follow-up commit.

## Verdict

passed — proceed to roadmap update

The four success criteria are met with concrete file:line evidence and passing tests. The human verify checkpoint in Plan 07-04 was approved (end-to-end flow tested: 10 factor cards rendered with degree badges and total points in the live UI).

## Recommendations

1. **Roadmap update:** mark Phase 7 as complete in `.planning/ROADMAP.md` Progress table (move from "Not started" to "Complete 2026-06-02").
2. **Follow-up commit (optional, not blocking Phase 8):** apply the MEDIUM fix from `07-REVIEW.md` — when `point_values.get(rating.degree)` is None after a successful LLM call, downgrade the factor to the `level=-1` failure sentinel so the total accurately reflects the drop, rather than warning-and-continue.
3. **Phase 8 readiness:** the "Continue to Export" disabled link in `templates/partials/jes_scores.html:27` is already wired to `/wizard/export?wd_id=...`; Phase 8 Plan 08-03 must mount the `wizard_export` route and Plan 08-04 must drop the `aria-disabled` attribute when activating it.
4. **TestStageTransition is the only remaining skipped test** — Phase 8 or a future phase should add an LLM mock to enable it (mirrors Phase 6's `TestJDStageTransition` pattern).
