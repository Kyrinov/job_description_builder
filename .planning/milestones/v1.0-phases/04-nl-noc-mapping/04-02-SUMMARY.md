---
phase: 04-nl-noc-mapping
plan: 02
subsystem: noc-mapping
tags: [wave-1, pydantic-models, instructor-client, structured-output, tdd-green]

# Dependency graph
requires:
  - phase: 04-nl-noc-mapping (plan 01)
    provides: "test_noc_ranking.py stubs (5 tests, 0 implemented), test_noc_mapping.py stubs, noc_mapping_db fixture, rebuild_noc_vectors.py"
provides:
  - "app/ai/noc_ranking.py — NOCCandidate + NOCRankingResult Pydantic models with input validators"
  - "app/ai/noc_ranking.py — module-level instructor_client singleton (instructor.from_openai + Mode.JSON) at settings.ollama_base_url/v1"
  - "app/models/noc.py — WorkDescriptionRequest (POST body) and NocMapResponse (response) API models"
  - "test_noc_ranking.py::TestNOCCandidateSchema 5/5 GREEN (were SKIPPED in Wave 0)"
affects:
  - "app/services/noc_mapper.py (Plan 04-03) — imports instructor_client, NOCRankingResult, NOCCandidate"
  - "app/api/noc_mapping.py (Plan 04-04) — imports WorkDescriptionRequest, NocMapResponse"
  - "app/models/noc.py consumers (Plan 04-04 router + Plan 04-04 wizard)"

# Tech tracking
tech-stack:
  added: []  # all libraries (instructor 1.15.1, openai 2.37.0, pydantic 2.12.5) already in requirements.txt
  patterns:
    - "Module-level instructor client singleton (built once at import time, reused for app lifetime)"
    - "instructor.Mode.JSON for Ollama (Mode.TOOLS silently fails on most Ollama models)"
    - "Pydantic field_validator for defence-in-depth beyond Field constraints (e.g., noc_code_all_digits in addition to pattern=r'^\\d{5}$')"
    - "Pydantic model_validator across-list (ranks_are_sequential) enforcing 1..N with no gaps or duplicates"

key-files:
  created:
    - "app/ai/__init__.py — package marker (empty)"
    - "app/ai/noc_ranking.py — Pydantic output models + instructor_client singleton (90 lines)"
    - "app/models/noc.py — request/response Pydantic models (36 lines)"
  modified: []

key-decisions:
  - "Drop title min_length=3 from AI-SPEC verbatim spec — the test contract (test_noc_ranking.py) and plan's behavior block both construct NOCCandidate with title='T' (1 char). The 3-char constraint would make the tests fail RED. Documented as Rule 1 auto-fix in deviations."
  - "Keep all other AI-SPEC constraints verbatim: noc_code pattern+all_digits, teer 0-5, rank 1-10, matched_duties min_length=1 + non-blank, justification min_length=30, ranks_are_sequential 1..N"
  - "Use AsyncOpenAI + instructor.from_openai with mode=Mode.JSON (per AI-SPEC pitfall #1: Mode.TOOLS silently fails on most Ollama models)"
  - "Module-level instructor_client singleton — build once at import time. Constructing per-request creates/tears down httpx connection pool on every call (50-200ms overhead, connection-exhaustion risk under load)"

patterns-established:
  - "Pattern: Module-level AI client singleton — `instructor_client = instructor.from_openai(AsyncOpenAI(base_url=settings.ollama_base_url.rstrip('/') + '/v1', api_key='ollama'), mode=instructor.Mode.JSON)` constructed at module import; never inside route handlers or service functions"
  - "Pattern: API input/output models in `app/models/noc.py` import AI output types from `app/ai/noc_ranking.py` — establishes the dependency direction (router -> api models -> ai models) that service layer (Plan 04-03) and router (Plan 04-04) plug into"

requirements-completed: [MAP-02]

# Metrics
duration: 5min
completed: 2026-06-01
---

# Phase 4 Plan 2: Pydantic Models and Instructor Client Singleton Summary

**Defines the NL→NOC structured-output contract: NOCCandidate + NOCRankingResult with input validators, module-level instructor_client (Mode.JSON) at Ollama /v1, and WorkDescriptionRequest/NocMapResponse API models — turns 5 Wave 0 test stubs from SKIPPED to GREEN.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-01T21:28:45Z
- **Completed:** 2026-06-01T21:33:25Z
- **Tasks:** 2 (both `tdd=true`)
- **Files modified:** 3 created, 0 modified

## Accomplishments

- **NOCCandidate Pydantic model** with five layers of input validation: 5-digit `noc_code` regex + `noc_code_all_digits` field_validator (defence-in-depth), `teer` 0–5, `rank` 1–10, `matched_duties` min-length 1 + `duties_not_blank` validator, `justification` min 30 chars. Rejects non-digit codes (`"ABCDE"`), out-of-range TEER (`6`), blank duties, and short justifications.
- **NOCRankingResult Pydantic model** with cross-list `ranks_are_sequential` validator: 1..N with no gaps or duplicates. Accepts `[1,2]`; rejects `[1,3]`.
- **instructor_client module-level singleton** built once at import via `instructor.from_openai(AsyncOpenAI(base_url=settings.ollama_base_url.rstrip("/") + "/v1", api_key="ollama"), mode=instructor.Mode.JSON)`. Type confirmed `AsyncInstructor` at runtime. Wired to settings (not hardcoded) so test envs can override `OLLAMA_BASE_URL`.
- **WorkDescriptionRequest** with `work_description: str = Field(..., min_length=10)` and optional `wd_id: str | None` — exact body shape the Plan 04-04 POST /api/noc/map route expects.
- **NocMapResponse** wraps `list[NOCCandidate]` with `min_length=1, max_length=5` — same shape as `NOCRankingResult.candidates` so the route handler can pass-through without field mapping.
- **5/5 tests in tests/test_noc_ranking.py::TestNOCCandidateSchema now PASS** (were SKIPPED in Wave 0). The test stubs imported `app.ai.noc_ranking` inside `try/except ImportError: pytest.skip(...)` — that safety net is now unreachable but harmless.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create app/ai/noc_ranking.py — Pydantic models and instructor client** - `f9c309a` (feat)
2. **Task 2: Create app/models/noc.py — request/response models** - `56b3095` (feat)

## Files Created/Modified

- `app/ai/__init__.py` — Empty package marker for the new `app/ai/` namespace.
- `app/ai/noc_ranking.py` — 90 lines. `NOCCandidate` and `NOCRankingResult` Pydantic models with field_validators, plus module-level `instructor_client` singleton. Imports `settings.ollama_base_url` from `app.config`.
- `app/models/noc.py` — 36 lines. `WorkDescriptionRequest` (work_description + optional wd_id) and `NocMapResponse` (candidates list[NOCCandidate]). Imports `NOCCandidate` from `app.ai.noc_ranking`.

## Decisions Made

- **Dropped `title: min_length=3` from the AI-SPEC verbatim spec.** The test stub `test_teer_is_integer` constructs `NOCCandidate(..., title="T", ...)` and expects success; `test_duties_not_blank` does the same. The plan's `<behavior>` block explicitly states `title="T"` should construct without error. The AI-SPEC over-constrained the field. Removing the `min_length=3` constraint aligns the code with the test contract and the plan's own behavior specification. All other AI-SPEC constraints were kept verbatim.
- **Kept all other AI-SPEC constraints verbatim:** `noc_code` regex + `noc_code_all_digits` validator (defence-in-depth: regex catches non-digits, validator is the second opinion), TEER 0–5, rank 1–10, matched_duties ≥ 1 + non-blank, justification ≥ 30 chars, ranks_are_sequential 1..N.
- **Used `AsyncOpenAI` (not sync `OpenAI`).** The instructor client must be safe to `await` inside FastAPI route handlers. `AsyncOpenAI` is the OpenAI Python SDK's async variant.
- **Used `instructor.Mode.JSON` (not `Mode.TOOLS`).** Per AI-SPEC pitfall #1, most Ollama-served models do not implement OpenAI tool/function calling. `Mode.JSON` instructs the model to output raw JSON and parses it directly. Verified by import + runtime `instructor_client` type = `AsyncInstructor`.
- **Module-level singleton, not dependency-injected.** The plan and AI-SPEC both specify a module-level client. This was a deliberate design choice — constructing per-request creates/tears down an httpx connection pool on every call (50–200ms overhead, connection-exhaustion risk under concurrent load).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Dropped `title: min_length=3` from NOCCandidate**
- **Found during:** Task 1 (running `pytest tests/test_noc_ranking.py -x` after writing the verbatim AI-SPEC content)
- **Issue:** AI-SPEC and PATTERNS.md both specify `title: str = Field(..., min_length=3)`. The plan's verbatim `action` block copies this. But the Wave 0 test stub `test_teer_is_integer` constructs `NOCCandidate(..., title="T", ...)` and asserts `c.teer == 0` (i.e., expects success). The plan's own `<behavior>` block states `title="T"` should construct without error. With `min_length=3`, the test fails RED with `string_too_short`. The AI-SPEC over-constrained the field; the test contract is the source of truth (and is consistent with the plan's behavior block).
- **Fix:** Replaced `title: str = Field(..., min_length=3)` with `title: str = Field(..., description="NOC unit group title as it appears in noc_units.title")` — dropped the min_length constraint, kept a useful description for the generated JSON schema. All 5 tests now pass GREEN.
- **Files modified:** `app/ai/noc_ranking.py`
- **Verification:** `pytest tests/test_noc_ranking.py -x` → 5 passed, 0 skipped, 0 failed
- **Committed in:** `f9c309a` (part of Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1: bug — code didn't match the test contract)
**Impact on plan:** Negligible — removed an over-restrictive constraint that contradicts the Wave 0 test contract and the plan's own behavior block. All other AI-SPEC content kept verbatim.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. The instructor_client points at `settings.ollama_base_url` (defaults to `http://localhost:11434`) which the existing `.env` already configures. No new environment variables, no new tools, no dashboard configuration.

## Next Phase Readiness

**Ready for Plan 04-03 (Service Layer — Three-Stage Pipeline):**
- ✅ `app.ai.noc_ranking.instructor_client` is importable and ready for `await instructor_client.chat.completions.create(model=..., response_model=NOCRankingResult, ...)` in the Stage 3 LLM call
- ✅ `NOCRankingResult` is the structured output type for the pipeline
- ✅ `NOCCandidate` is the per-row type that the verbatim guardrail in Plan 04-03 will validate duties against
- ✅ `app.models.noc.WorkDescriptionRequest` is the API body type for the route
- ✅ `app.models.noc.NocMapResponse` is the route's response type

**Pre-existing Wave 0 prerequisite still applies:** Before any Plan 04-03 code touches the live `app.db`, run `python scripts/rebuild_noc_vectors.py --db-path app.db` to convert `noc_chunks_vec` from FLOAT[1024] (DashScope) to FLOAT[768] (nomic-embed-text). Without it, the startup assertion in `app/db.py::assert_noc_index_model()` raises `RuntimeError`. (Documented in 04-01-SUMMARY.md.)

**No new blockers introduced by this plan.**

---

*Phase: 04-nl-noc-mapping*
*Completed: 2026-06-01*

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `app/ai/noc_ranking.py` exists | ✅ FOUND |
| `app/ai/__init__.py` exists | ✅ FOUND |
| `app/models/noc.py` exists | ✅ FOUND |
| `.planning/phases/04-nl-noc-mapping/04-02-SUMMARY.md` exists | ✅ FOUND |
| Commit `f9c309a` (Task 1) in history | ✅ FOUND |
| Commit `56b3095` (Task 2) in history | ✅ FOUND |
| `pytest tests/test_noc_ranking.py` | ✅ 5 passed in 3.67s (0 skipped, 0 failed) |
| `from app.ai.noc_ranking import NOCCandidate, NOCRankingResult, instructor_client; from app.models.noc import WorkDescriptionRequest, NocMapResponse` | ✅ all imports OK |
| No accidental file deletions | ✅ `git diff --diff-filter=D HEAD~1 HEAD` empty for both task commits |
| No state files modified (per orchestrator constraint) | ✅ STATE.md and ROADMAP.md not in staged changes |
