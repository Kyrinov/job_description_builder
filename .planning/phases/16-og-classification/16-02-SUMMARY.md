---
phase: 16-og-classification
plan: 02
subsystem: classification-api
tags: [backend, api, deterministic-classification, hard-gate, threat-model-mitigations]
requires: [16-01]
provides: [POST-/api/og/classify, GET-/api/og/definitions, GET-/api/quals/default, require_og_confirmed-gate, CLASS-01-backend, CLASS-02-backend, CLASS-04-gate, API-06, API-03]
affects: [16-03, 16-04, 17-jes-scoring, 18-jd-composition, 19-qualifications, 20-export]
tech-stack:
  added: []
  patterns: [deterministic-signal-ranking, pydantic-input-validation, hardcoded-constants-only, fastapi-router-registration]
key-files:
  created:
    - v2/backend/app/api/og_classification.py
    - v2/backend/app/services/classification_gate.py
  modified:
    - v2/backend/app/api/__init__.py
key-decisions:
  - "No LLM calls in OG classification (deterministic). Confidence capped at 0.9 (signal-based only); LLM only used in Phase 14 NOC pipeline."
  - "Default fallback when signal_tally is empty: fixed ranking [EC(0.55), AS(0.35), IT(0.10)] — endpoint never returns empty list"
  - "AS/EC disambiguation alert built once in ASEC_DISAMBIGUATION constant (Plan 01); route just includes the constant if both AS and EC appear in top-3"
  - "Evidence quotes field is empty list (no fabrication); rationale is template-based with vote count and definition excerpt"
  - "Classification gate uses 409 Conflict (not 422) to distinguish from request validation errors — semantically 'classification pending'"
requirements-completed:
  - CLASS-01
  - CLASS-02
  - CLASS-04
  - API-06
  - API-03
duration: ~5 min
completed: 2026-06-05T09:15:00Z
---

# Phase 16 Plan 02: OG Classification API + Hard Gate Summary

Wave 1 of 4 for Phase 16. Turns all 7 RED stubs from Plan 01 GREEN; delivers the OG classification backend and the hard gate utility for downstream phases.

## One-liner

Three deterministic OG endpoints (classify, definitions, qual defaults) and a `require_og_confirmed` 409 gate — all 50 backend tests GREEN.

## Tasks completed

- **Task 1**: Created `v2/backend/app/api/og_classification.py` with `POST /api/og/classify`, `GET /api/og/definitions`, `GET /api/quals/default`. Deterministic ranker filters unknown OG codes (T-16-01), validates og_code query param (T-16-02), caps work_description at 2000 chars (T-16-03). AS/EC alert triggered when both appear in top-3.
- **Task 2**: Registered `og_classification` router in `app/api/__init__.py`. Created `app/services/classification_gate.py` with `require_og_confirmed(wd)` raising 409 if `confirmed_og` or `og_level` is missing. All 50 backend tests PASS (43 prior + 7 new OG classification tests).

## Test results

- `python -m pytest -q` — **50 passed** in 5.22s (43 prior + 7 new)
- `python -m pytest tests/test_og_classification.py -v` — all 7 tests PASSED
- Import checks: `og_classification` and `classification_gate` import without error

## Deviations from Plan

None. Plan executed as written.

## Next

Plan 16-03: wire frontend OG classification conversation steps (`og_confirm`, `og_level`, `reports_to_military`), implement `OgConfirmList` + `OgLevelPicker` components, extend `app.jsx` with OG pipeline fetch + invalidation.
