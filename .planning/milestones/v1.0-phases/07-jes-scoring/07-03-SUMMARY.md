---
phase: 07-jes-scoring
plan: 03
subsystem: api+service
tags: [fastapi, instructor, asyncio, scoring, jinja2, htmx]

# Dependency graph
requires:
  - phase: 07-jes-scoring-02
    provides: "JESFactorRating, jes_instructor_client, JES_SCORING_SYSTEM_PROMPT, get_jes_version_info"
  - phase: 06-jd-generation
    provides: "JD service + router as structural analog, stage gate patterns"
provides:
  - "app/services/jes_service.py with score_jes() async pipeline (per-factor LLM loop)"
  - "app/api/jes_scoring.py with POST /api/jes/score (HTMX/JSON dual path)"
  - "app/main.py updates: router registration + GET /wizard/jes route"
affects: [07-04]

# Tech tracking
tech-stack:
  added: []
  patterns: [sequential per-factor LLM calls, level=-1 sentinel for failures, HTMX/JSON dual-path, ValueError→HTTPException mapping, model_copy stage transition, asyncio.to_thread for sync SQLite]

key-files:
  created: [app/services/jes_service.py, app/api/jes_scoring.py]
  modified: [app/main.py]

key-decisions:
  - "Sequential per-factor LLM calls (not asyncio.gather) — prevents Ollama OOM on ARM64 (matches STATE.md non-negotiable)"
  - "Per-factor try/except with sentinel JESFactorScore(level=-1, points=None) — instructor retries 3x, then sentinel captured instead of raised"
  - "Stage advances to 'jes_scored' ONLY after ALL factors collected (including failures) — never advance mid-loop"
  - "jes_total = sum(s.points for s in jes_scores if s.points is not None) — failed factors contribute 0 to total but remain visible"
  - "Failure rationale text includes exception string for audit trail (e.g., 'Scoring failed after 3 retries: <error>')"

patterns-established:
  - "Mirror of jd_service.py: stage gate + asyncio.to_thread + model_copy + finally conn.close"
  - "Mirror of jd_generation.py: dual HTMX/JSON path with HX-Request header check"
  - "Degree → int level: int(degree.lstrip('D')) if degree.startswith('D') else -1; try/except for parse safety"

requirements-completed: [JES-01]

# Metrics
duration: 12min
completed: 2026-06-02
---

# Phase 7 Plan 3: JES Service + Router Summary

**Per-factor JES scoring pipeline (`app/services/jes_service.py`), `POST /api/jes/score` HTMX/JSON dual-path router, and `app/main.py` registration with `GET /wizard/jes` route — unlocks stage-gate, no-factors, and schema tests.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-06-02T17:40:00Z
- **Completed:** 2026-06-02T17:52:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `score_jes(wd_id, db_path)` async pipeline: stage gate → factor lookup → sequential per-factor LLM calls → provenance-tagged scores → stage advance to 'jes_scored'
- Failure-handling pattern: per-factor try/except with sentinel `JESFactorScore(level=-1, points=None, rationale="Scoring failed after 3 retries: <err>")` — never raises mid-loop
- `app/api/jes_scoring.py` POST `/api/jes/score` router with HTMX partial + JSON response, `ValueError("not found") → 404`, other `ValueError → 422`
- `app/main.py` updated: import `jes_scoring`, `include_router(jes_scoring.router)`, new `GET /wizard/jes` route with TemplateNotFound fallback
- TestJESScoringStageGate (2 tests), TestNoFactors now PASS; full suite **149 passed, 1 skipped** (was 146 passed, 4 skipped = +3 new passes, -3 fewer skips)

## Task Commits

1. **Task 1: Create app/services/jes_service.py** - `24210cb` (feat)
2. **Task 2: Create app/api/jes_scoring.py and register in app/main.py** - `7d43bc3` (feat)

**Plan metadata:** This summary (docs: complete plan)

## Files Created/Modified

- `app/services/jes_service.py` — 242 lines: helpers (`_build_factor_user_prompt`, `_build_jes_factor_score`, `_make_error_score`) + `score_jes()` async pipeline
- `app/api/jes_scoring.py` — 49 lines: `POST /api/jes/score` route with ValueError→HTTPException mapping
- `app/main.py` — +33 lines: import + router registration + GET `/wizard/jes` route with TemplateNotFound fallback

## Decisions Made

- Used `tuple[str, str]` return type annotation on `_build_jes_factor_score` to match `get_jes_version_info` pattern
- Wrapped `int(rating.degree.lstrip("D"))` in try/except (`ValueError, AttributeError`) per T-07-05 — invalid degree strings fall back to sentinel level=-1
- Loaded `og_name` via dedicated `SELECT og_name FROM og_definitions` query (not joined with factors) for cleaner separation of concerns

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - reuses existing settings, no new env vars.

## Next Phase Readiness

- Plan 07-04 can now build `templates/wizard/step_jes.html` and `templates/partials/jes_scores.html` to replace the TemplateNotFound fallback
- All API endpoints in place; end-to-end LLM scoring will work as soon as Ollama/DashScope is reachable
- TestStageTransition still skipped — needs LLM mock to validate the stage advance without hitting real inference

---
*Phase: 07-jes-scoring*
*Completed: 2026-06-02*
