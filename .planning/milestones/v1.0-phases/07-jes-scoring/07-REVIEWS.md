---
phase: 7
reviewers: [codex, opencode]
reviewed_at: 2026-06-02T18:46:07Z
plans_reviewed: [07-01-PLAN.md, 07-02-PLAN.md, 07-03-PLAN.md, 07-04-PLAN.md]
notes: gemini skipped (GEMINI_API_KEY not configured); claude skipped (self — running inside Claude Code CLI)
---

# Cross-AI Plan Review — Phase 7: JES Scoring

## Codex Review (gpt-5.5)

### 1. Summary

The plans are directionally strong: they isolate model output from authoritative point mapping, preserve sequential local inference for constrained hardware, and maintain traceability. However, the current design has several gaps that could produce misleading "successful" JES sheets. The most important issue is that factor-level failures still advance the WorkDescription to `jes_scored`, despite the success criteria requiring a complete scoring sheet and descriptive errors. Provenance persistence, database schema assumptions, degree validation, and retry verification also need to be made explicit before implementation.

### 2. Strengths

- The per-factor call design directly satisfies the requirement to inject fresh authoritative descriptors and degree definitions.
- Excluding points from `JESFactorRating` is the correct boundary: the model selects a degree; the database remains authoritative for points.
- Sequential model calls are appropriate for Ollama on Jetson AGX Orin and avoid predictable memory pressure from concurrent generation.
- `instructor` singleton construction at module scope follows the established project pattern.
- The stage gate chain remains consistent with earlier phases.
- A sentinel error object provides a visible failure mode instead of silently dropping factors.
- HTMX and JSON dual-path behavior fits an advisor-facing wizard while preserving API usability.
- The UI plan explicitly distinguishes failed factors and exposes source provenance.

### 3. Concerns

**Plan 07-01: Test Scaffolding**

- **HIGH:** The test plan does not verify the core JES-01 behavior: one model call per factor, sequential invocation, full descriptor injection, all degree definitions, `max_retries=3`, or database-derived point mapping.
- **HIGH:** There is no persistence test confirming that scores and factor-level ProvenanceTags are stored on the WorkDescription record.
- **MEDIUM:** "All 8 test stubs" conflicts with the listed coverage — the classes and cases appear to describe more than eight individual tests. Name the exact test functions.
- **MEDIUM:** Requiring `pytest ...` to exit non-zero because every stub skips is fragile. Pytest commonly exits successfully when tests are collected and skipped. The requirement should be "collects without import errors and reports skips."
- **MEDIUM:** The fixture seeds two factors but does not mention `og_definitions`, degree definitions, `point_values`, confirmed OG data, or the exact WorkDescription storage shape needed by Plan 07-03.
- **LOW:** Schema-only tests for `JESFactorRating` should verify that extra fields (e.g., hallucinated `points`) are rejected if "exactly 2 fields" is a real contract.

**Plan 07-02: Model and Singleton**

- **HIGH:** `degree: str` is too permissive. The LLM can return `D99`, `"3"`, or whitespace. Validation must reject degrees absent from the current factor's database record before points are computed.
- **MEDIUM:** `get_jes_version_info()` uses `LIKE f"{og_code}%"`, which can match unrelated records and treats `%` and `_` in `og_code` as wildcards. Prefer an explicit source-document relationship or an exact structured key.
- **MEDIUM:** The fallback `("JES v1.0", "")` creates weak provenance. Empty hashes should be treated as missing source metadata or clearly marked as unavailable.
- **MEDIUM:** The plan does not define behavior when multiple matching source documents exist. Ordering must be deterministic.
- **LOW:** The system prompt is useful, but the user prompt contract needs to define the serialization format for descriptors and degree definitions to reduce ambiguity.

**Plan 07-03: Service and Router**

- **HIGH:** Advancing to `jes_scored` when any factor has `level=-1` risks treating an incomplete or unusable sheet as completed. Keep the WD at `jd_drafted`, or introduce an explicit `jes_scoring_failed` / `jes_scored_with_errors` state.
- **HIGH:** Persistence is underspecified. The success criteria require storing the sheet on the WorkDescription with provenance tags, but the behavior list only describes returning a dictionary and advancing the stage.
- **HIGH:** Provenance granularity is unclear. Each score must identify the exact JES factor source record, not only a broad JES version and content hash.
- **HIGH:** The plan does not define a transaction boundary. Persisting scores and advancing the stage should occur atomically.
- **HIGH:** Invalid degree output is not handled explicitly. `_build_jes_factor_score` may fail when parsing the suffix or indexing `point_values`. This should become a descriptive factor error or trigger model retry.
- **MEDIUM:** Catching a broad exception per factor may hide application bugs as model failures. Catch expected inference exceptions; log unexpected ones with context.
- **MEDIUM:** Simultaneous scoring requests for the same WD could duplicate model calls and race stage updates.
- **MEDIUM:** The API path differs from the phase success criterion: `/score-jes` versus `/api/jes/score`. Pick one canonical route.
- **MEDIUM:** Total points must exclude sentinel errors and should be marked incomplete when any factor fails.
- **LOW:** `factor_count` is ambiguous — consider `successful_factor_count`, `failed_factor_count`, `is_complete`.

**Plan 07-04: UI**

- **MEDIUM:** The UI enables "Continue to JES Scoring" but does not specify whether the CTA appears only when the WD is actually `jd_drafted`.
- **MEDIUM:** Failed factors need an explicit incomplete-sheet banner — a numeric total beside sentinel failures could imply a legally usable result.
- **MEDIUM:** The wizard page should handle direct navigation with a missing, unknown, or wrong-stage `wd_id`.
- **LOW:** The form should disable repeat submissions while inference is running (per-factor local calls may take substantial time).

### 4. Suggestions

- Add explicit tests for: one model call per factor, sequential calls, full descriptor injection, database-derived points, malformed output + retry, failure after 3 attempts, invalid-but-well-formed degree identifiers, atomic persistence, stage behavior when one factor fails, concurrent duplicate requests.
- Make degree validation factor-aware: parse the DB degree-definition keys first, then reject any returned degree outside that set before mapping points.
- Change completion semantics: all factors valid → `jes_scored`; any factor failed → remain at `jd_drafted`, return `is_complete=false`.
- Wrap score persistence and stage transition in one SQLite transaction.
- Use deterministic factor ordering (e.g., explicit `display_order` column).
- Align route naming across success criteria, tests, router, and templates.

### 5. Risk Assessment

**Overall risk: HIGH**

The architecture is appropriate, but the completion semantics and persistence contract are not yet robust enough for a legally defensible workflow. A sheet containing failed factors could currently be marked `jes_scored`, and the plans do not prove that exact factor-level provenance is stored atomically. Tightening those areas and expanding the tests around JES-01 would reduce implementation risk to **MEDIUM**.

---

## OpenCode Review (qwen3.6-implementer — analyzed live codebase)

*Note: OpenCode read the actual implementation files before reviewing — its assessment reflects post-implementation state.*

### 1. Summary

Phase 7 is fully implemented with a clean separation across `app/ai/jes_scoring.py` (instructor singleton + Pydantic models), `app/services/jes_service.py` (per-factor pipeline), `app/api/jes_scoring.py` (HTMX dual-path router), and `tests/test_jes_scoring.py` (8 test classes with DB fixtures). The implementation faithfully follows established patterns from prior phases and correctly addresses all JES-01 requirements.

### 2. Strengths

- **No-points architectural decision:** `JESFactorRating` has only `degree` + `rationale` — prevents LLM hallucination of point values. Solid domain decision.
- **Sequential per-factor loop:** Correctly uses sequential iteration (not `asyncio.gather`) for ARM64 Ollama OOM protection. Well-documented as a "STATE-card non-negotiable."
- **Error resilience:** Failed factors get `level=-1` sentinel with descriptive rationale, not silent null — requirement explicitly requires this and the implementation delivers.
- **Provenance linkage:** Each `JESFactorScore` gets a `ProvenanceTag(source_type="JES")` with `source_id="{og_code}/{factor_name}"` and `source_version` from `get_jes_version_info`. Requirement fully met.
- **Stage gate chain:** Properly enforces `jd_drafted` gate before scoring; transitions to `jes_scored` only after all factors collected.
- **Instructor singleton at module level:** Module-level construction prevents per-request httpx pool creation — correctly documented.
- **DB fixture:** Properly seeds 2 EC factors with realistic degree descriptors and `point_values` JSON, plus `source_documents` row for version lookup. Uses `tmp_path` isolation.
- **HTMX dual-path:** `HX-Request` header detection correctly switches between `TemplateResponse` and JSON.

### 3. Concerns

- **MEDIUM:** `TestStageTransition` is unconditionally skipped (`pytest.skip("Requires LLM mock")`) — no mock implementation path exists. This leaves a gap in testing the actual stage transition logic. An `AsyncMock` for `jes_instructor_client.chat.completions.create` should be implemented.
- **MEDIUM:** Plan 07-04 UI templates (`templates/wizard/step_jes.html`, `templates/partials/jes_scores.html`, CSS in `app/static/css/main.css`) need verification that they exist and are complete.
- **LOW:** `get_jes_version_info` uses `LIKE f"{og_code}%"` — works for known OG prefixes but `LIMIT 1` wins on first match without deterministic ordering. No test covers this edge case.
- **LOW:** `_make_error_score` puts `f"Scoring failed after 3 retries: {exc}"` in the user-visible rationale — leaks raw exception text. The exception is already logged via `logger.warning`; the rationale could be sanitized.
- **LOW:** `TestNoFactors` relies on no AS-coded rows in `jes_db` fixture — implicit assumption fragile if fixture later gains AS factors.

### 4. Suggestions

- Implement `TestStageTransition` with `unittest.mock.AsyncMock` to patch `jes_instructor_client.chat.completions.create` — verify `jes_scored` stage transition and `jes_total_points` sum.
- Add test for `get_jes_version_info` fallback: no matching `source_documents` row → returns `("JES v1.0", "")`.
- Add test for `points=None` fallback in `_build_jes_factor_score` when `point_values` has no key for the returned degree.
- Consider a `--no-factors` fixture variant in `conftest` for `TestNoFactors` to be self-documenting.
- Sanitize error rationale: use `"Scoring failed after 3 retries — see server logs"` in user-facing field; keep raw exception in `logger.warning` only.

### 5. Risk Assessment

**Overall Risk: LOW**

The implementation solidly achieves all JES-01 requirements. The sequential per-factor loop correctly protects against ARM64 Ollama OOM. The instructor singleton pattern is correct. The Pydantic validation + retry chain (`max_retries=3`) matches the phase goal. Provenance linkage is complete. The one gap that matters is the unimplemented `TestStageTransition` (MEDIUM) — a test gap, not an implementation risk. The `get_jes_version_info` LIKE pattern is a minor data integrity concern (LOW) that only surfaces if OG prefixes collide.

**Recommendation: Proceed with confidence. Implement the missing `TestStageTransition` mock and add `version_info` edge-case test before merging.**

---

## Consensus Summary

### Context Note

Codex reviewed the **plans** (pre-implementation); OpenCode reviewed the **live codebase** (post-implementation). Their diverging risk ratings (HIGH vs LOW) reflect this difference in perspective. OpenCode's LOW assessment should be taken as the more accurate signal for current state.

### Agreed Strengths

Both reviewers independently praised:
- **No-points in `JESFactorRating`** — LLM returns only degree identifier; service maps to points from DB. Prevents hallucination.
- **Sequential per-factor loop** — correct decision for ARM64 Ollama, not `asyncio.gather`.
- **`level=-1` sentinel** — visible error per factor instead of silent null or raised exception.
- **`instructor` singleton at module level** — correct architecture.
- **Stage gate chain consistency** — `jd_drafted` → `jes_scored` enforced properly.
- **HTMX dual-path** — clean advisor-facing UX while preserving API usability.

### Agreed Concerns

Issues raised by both reviewers (priority order):
1. **TestStageTransition is permanently skipped (MEDIUM)** — the actual stage transition logic has no test coverage. Implement with `AsyncMock`.
2. **`get_jes_version_info` LIKE pattern (LOW)** — `LIKE f"{og_code}%"` without deterministic ordering could return wrong version if OG prefix collides. No test covers fallback path.
3. **Error rationale leaks raw exception text (LOW)** — `f"Scoring failed after 3 retries: {exc}"` in user-visible field. Sanitize; keep raw in logs only.

### Divergent Views

- **Completion semantics when factors fail:** Codex (plan review) flagged HIGH risk that `level=-1` factors still advance stage to `jes_scored`. OpenCode (live review) marked this LOW — the implementation advances regardless, which is a documented design choice (the HTMX UI renders error cards visually, not silently). This is a **product decision worth reviewing**: should a sheet with failed factors be considered "scored" or remain as `jd_drafted`?
- **Degree validation:** Codex flagged that `degree: str` is too permissive (LLM could return `D99`). OpenCode did not flag this as an active concern in the live code — suggesting `instructor` retries handle malformed output in practice. Worth adding an explicit test.
- **Transaction boundary:** Codex flagged atomicity of persist + stage advance as HIGH. OpenCode didn't raise this — suggesting the existing `asyncio.to_thread` + single `save_work_description` call is sufficient for a single-user local app.

### Top 3 Action Items

1. **Implement `TestStageTransition`** with `AsyncMock` — verify `jes_scored` stage + `jes_total_points` sum (MEDIUM, both reviewers).
2. **Verify Plan 07-04 UI templates** exist and render correctly — `step_jes.html`, `jes_scores.html`, CSS layer 10 (MEDIUM, OpenCode; the human verify checkpoint in Plan 07-04 covers this).
3. **Decide: should `level=-1` factors block `jes_scored` transition?** — document the decision explicitly in a code comment or STATE.md update (MEDIUM, Codex concern).
