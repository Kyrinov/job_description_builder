---
phase: 07-jes-scoring
plan: 02
subsystem: ai
tags: [instructor, pydantic, ollama, dashscope, async-openai, singleton]

# Dependency graph
requires:
  - phase: 07-jes-scoring-01
    provides: "test stubs that lock the JESFactorRating + jes_instructor_client contract"
  - phase: 05-og-classification
    provides: "app/ai/jd_ranking.py structural analog (proven instructor singleton pattern)"
provides:
  - "app/ai/jes_scoring.py with JESFactorRating Pydantic model, JES_SCORING_SYSTEM_PROMPT, get_jes_version_info, jes_instructor_client singleton"
affects: [07-03, 07-04]

# Tech tracking
tech-stack:
  added: []
  patterns: [module-level instructor singleton, Pydantic-only LLM output (no points — degree→points via service mapping), LIKE-prefix source_documents lookup]

key-files:
  created: [app/ai/jes_scoring.py]
  modified: []

key-decisions:
  - "JESFactorRating has degree + rationale ONLY — points mapped by service via json.loads(row['point_values']) to prevent LLM point-value hallucination"
  - "Singleton constructed at module level AFTER settings import (Pitfall 6: prevents circular import)"
  - "get_jes_version_info LIKE pattern f'{og_code}%' — 2-3 char OG prefix uniquely matches one JES source file (verified in RESEARCH.md Pattern 6)"
  - "Fallback version ('JES v1.0', '') when no source_documents row found — matches Phase 3 ingest label"

patterns-established:
  - "Mirror of jd_ranking.py: same AsyncOpenAI + instructor.from_openai + Mode.JSON construction"
  - "settings module-level conditional selects cloud (DashScope) or local (Ollama) base_url"

requirements-completed: [JES-01]

# Metrics
duration: 5min
completed: 2026-06-02
---

# Phase 7 Plan 2: JES Scoring AI Module Summary

**`app/ai/jes_scoring.py` — instructor client singleton + JESFactorRating Pydantic output model + system prompt constant + version-info helper, mirroring `app/ai/jd_ranking.py` exactly.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-02T17:34:00Z
- **Completed:** 2026-06-02T17:39:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- JESFactorRating (degree + rationale) Pydantic model with Field descriptions for LLM guidance
- `jes_instructor_client` module-level singleton — works for both Ollama (local) and DashScope (cloud) based on `settings.cloud_api_key`
- `JES_SCORING_SYSTEM_PROMPT` with format placeholders `{og_name}` and `{og_code}` and explicit CRITICAL RULES
- `get_jes_version_info(conn, og_code)` helper using `LIKE f"{og_code}%"` pattern
- Module importable from `app.ai.jes_scoring` — all 4 exports available
- TestJESFactorRatingSchema and TestJESInstructorClient now PASS (unblocked from 2 skips)

## Task Commits

1. **Task 1: Create app/ai/jes_scoring.py** - `1e9760e` (feat)

**Plan metadata:** This summary (docs: complete plan)

## Files Created/Modified

- `app/ai/jes_scoring.py` — 104 lines: Pydantic model, prompt constant, DB helper, instructor singleton

## Decisions Made

None - plan executed exactly as written.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - reuses existing settings (cloud_api_key from env, or ollama_base_url fallback).

## Next Phase Readiness

- Plan 07-03 can now import `JESFactorRating`, `JES_SCORING_SYSTEM_PROMPT`, `jes_instructor_client`, and `get_jes_version_info` to build `app/services/jes_service.py`
- Stage transition test (`TestStageTransition`) still skipped — needs an LLM mock
- Stage gate tests (TestJESScoringStageGate) still skipped — need router at `/api/jes/score`

---
*Phase: 07-jes-scoring*
*Completed: 2026-06-02*
