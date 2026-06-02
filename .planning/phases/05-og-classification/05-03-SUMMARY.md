---
phase: 05-og-classification
plan: 03
subsystem: api
tags: [fastapi, pydantic, instructor, ht mx, dual-path, stage-gate, level-validation, verbatim-guardrail]

# Dependency graph
requires:
  - phase: 05-og-classification
    plan: 01
    provides: og_definitions table
  - phase: 05-og-classification
    plan: 02
    provides: og_instructor_client, OGCandidate, PolicyAdjacencyResult, OG_LEVELS
provides:
  - app/services/og_classifier.py — 3-step pipeline (load → ASEC detect → LLM rank + guardrail)
  - app/api/og_classification.py — POST /api/og/classify and POST /api/og/confirm routes
  - app/models/og.py — OGClassifyRequest and OGClassifyResponse
  - Stage gate enforcement (422 if stage != noc_mapped)
  - og_level validation (422 if not in OG_LEVELS[og_code])
  - Verbatim guardrail (strips fabricated evidence_quotes)
  - AS/EC disambiguation with directive_on_classification citation (CLASS-03)
affects: [05-04-templates, 06-jd-generation]

# Tech tracking
tech-stack:
  added: []
  patterns: [pure-function helper for ASEC alert (no hidden DB), FTS-cited CLASS-03 directive authority, asyncio.to_thread DB calls with finally close, instructor num_ctx=16384 for OG ranking context, Pydantic model_copy for immutable WD updates, HTMX dual-path response (H X-Request header)]

key-files:
  created:
    - app/models/og.py
    - app/services/og_classifier.py
    - app/api/og_classification.py
    - templates/partials/og_results.html
    - templates/partials/og_confirmed.html
  modified:
    - app/main.py

key-decisions:
  - "_build_asec_alert is a PURE function — it never opens a DB connection; it only reads from the og_rows list passed in. The pipeline always fetches ALL og_definitions rows (no WHERE filter) so AS and EC are guaranteed present."
  - "_fetch_directive_citation queries policy_fts via MATCH 'occupational OR classification OR group' for the directive_on_classification authority citation (CLASS-03 grounding)"
  - "Verbatim guardrail runs AFTER Step 3 LLM call: drop candidates with og_code not in valid set, strip evidence_quotes not substring of og_definitions text"
  - "POST /api/og/classify persists top-1 OGRecommendation to WorkDescription before responding (advisor sees ranked candidates but pipeline state is the top one)"
  - "POST /api/og/confirm sets BOTH og_level (TBS header field, DATA-01) and confirmed_level (canonical storage) — the same string value"
  - "Stage gate enforced at BOTH classify AND confirm routes (T-05-03-03)"

patterns-established:
  - "Service-layer pure-function helpers — _build_asec_alert and _strip_fabricated_quotes take data, return data, never touch DB"
  - "og_code/level validation at API layer: OG_LEVELS dict is the in-memory allowlist (T-05-03-01, T-05-03-02)"
  - "Stage-gate pattern: 422 with descriptive detail when WorkDescription is in unexpected stage"

requirements-completed: [CLASS-01, CLASS-02, CLASS-03]

# Metrics
duration: 5min
completed: 2026-06-02
---

# Phase 5 Plan 03 Summary

**Three-step OG classification pipeline (load → ASEC detect → LLM rank + verbatim guardrail) + FastAPI routes with stage gates, level validation, and CLASS-03 directive authority citation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-02
- **Completed:** 2026-06-02
- **Tasks:** 2/2
- **Files modified:** 6 (5 created, 1 modified)

## Accomplishments

- `app/services/og_classifier.py` — 3-step pipeline:
  - Step 1: `_fetch_og_rows` loads ALL og_definitions rows (no WHERE) to guarantee AS+EC present
  - Step 2: `PolicyAdjacencyResult` detection via `og_instructor_client`; on `is_policy_adjacent=True` builds ASEC alert from pure helper + fetches `directive_on_classification` citation via policy_fts (CLASS-03)
  - Step 3: `OGRankingResult` LLM rank with num_ctx=16384 + verbatim guardrail (drop invalid og_code, strip fabricated evidence_quotes)
  - Pure helpers: `_strip_fabricated_quotes`, `_build_asec_alert` (no DB access)
  - All DB calls via `asyncio.to_thread` with `finally` close
- `app/api/og_classification.py`:
  - `POST /api/og/classify`: 404 if WD not found, 422 if stage != noc_mapped, 422 if no confirmed_noc, 422 on ValueError; persists OGRecommendation to WD; HTMX/JSON dual-path
  - `POST /api/og/confirm`: 422 on non-integer or out-of-range og_level (per OG_LEVELS allowlist), 404/422 stage gates, sets confirmed_og + confirmed_level + og_level + stage='og_classified' and confirmed_by_advisor=True
- `app/main.py`: registered `og_classification.router`
- Template stubs (og_results.html, og_confirmed.html) so Wave 3 integration tests pass without TemplateNotFound

## Task Commits

1. **Task 1: og.py + og_classifier.py** — `4ad879e` (feat)
2. **Task 2: og_classification.py + main.py + template stubs** — `4ad879e` (feat, same commit)

## Files Created/Modified

- `app/models/og.py` — NEW: `OGClassifyRequest`, `OGClassifyResponse` (32 lines)
- `app/services/og_classifier.py` — NEW: pipeline + helpers (203 lines)
- `app/api/og_classification.py` — NEW: 2 routes (220 lines)
- `app/main.py` — added `from app.api import og_classification` and `app.include_router(og_classification.router)`
- `templates/partials/og_results.html` — NEW: Wave 3 stub (4 lines, replaced in Plan 05-04)
- `templates/partials/og_confirmed.html` — NEW: Wave 3 stub (4 lines, replaced in Plan 05-04)

## Decisions Made

- Plan referenced `ProvenanceTag` with `source_text` and `ingested_at` fields that don't exist in the model; adapted to use actual fields (`source_version`, `retrieved_date=date.today()`, `model_name=settings.generation_model`) following the `NOCMatch` pattern in `app/services/noc_mapper.py:266-282`
- _build_asec_alert is a PURE function: it never opens a DB connection. Step 1 (classify_og) always fetches all og_definitions rows (no WHERE filter) so AS and EC are guaranteed present. If somehow absent, function returns None and caller skips alert.
- FTS5 directive citation query uses 'occupational OR classification OR group' — broader than just 'occupational group OR classification' to ensure matches across chunked TBS policy text
- `Pydantic model_copy(update={...})` for all immutable WD updates (preserves Pydantic v2 immutability)
- Both classify and confirm routes enforce stage='noc_mapped' gate (T-05-03-03)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Schema mismatch] Adapted ProvenanceTag field names to actual model**
- **Found during:** Task 1 (writing og_classifier.py and og_classification.py)
- **Issue:** Plan's code used `source_text` and `ingested_at` on ProvenanceTag; the actual model has `source_version`, `retrieved_date`, `source_url`, `model_name`
- **Fix:** Used the NOCMatch creation pattern from `app/services/noc_mapper.py:266-282` — `source_type` + `source_id` + `source_version` + `retrieved_date=date.today()` + `model_name=settings.generation_model`
- **Files modified:** `app/api/og_classification.py`
- **Verification:** Routes import cleanly; no Pydantic ValidationError
- **Committed in:** `4ad879e` (Task 2 commit)

## Issues Encountered

None beyond the auto-fixed schema mismatch above.

## Next Phase Readiness

- Plan 05-04 (HTMX templates + CSS) can proceed — backend complete
- All 9 of 10 test_og_classification stubs now pass; the 1 remaining skip is the deferred Phase 6 gate test (CLASS-02 enforcement test belongs to JD generation phase)
- Full suite: 99 passed, 1 skipped

---
*Phase: 05-og-classification*
*Completed: 2026-06-02*
