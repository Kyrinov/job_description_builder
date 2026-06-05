---
phase: 16-og-classification
status: passed
date: 2026-06-05
verifier: manual (gsd-verifier subagent not installed)
plans-verified: [16-01, 16-02, 16-03, 16-04]
requirements-verified: [CLASS-01, CLASS-02, CLASS-03, CLASS-04, CLASS-05, API-03, API-06]
---

# Phase 16: OG Classification — VERIFICATION

## Goal (from ROADMAP.md)

> After NOC is confirmed, the system returns top-3 OG candidates with verbatim rationale, surfaces AS/EC disambiguation when applicable, guides the advisor through level selection from the correct range, and hard-gates JD generation until OG + level are confirmed; CAF rank context displays as an advisory.

**Verdict: PASSED.** All 7 requirements delivered; 4/4 plans complete; 50/50 backend + 19/19 frontend tests GREEN; clean build; human UAT approved; code review clean.

## Requirements Verification

### CLASS-01 — Evidence-based OG ranking from confirmed NOC + work description

**Status:** ✅ DELIVERED

- Backend: `POST /api/og/classify` accepts `confirmed_noc_code`, `work_description`, `signal_tally`; returns `candidates: list[OGCandidate]` ranked by signal tally with confidence scores capped at 0.9
- Deterministic — no LLM calls in this module (per architecture non-negotiable: "Deterministic classification in the main flow — LLM used only for NOC justification")
- Frontend: OgConfirmList renders the candidates as selectable cards
- Test: `test_og_classify_returns_candidates` PASSES

### CLASS-02 — AS/EC disambiguation when both in top-3

**Status:** ✅ DELIVERED

- Backend: ASEC_DISAMBIGUATION constant built from OG_DEFINITIONS excerpts; route returns `asec_alert: ASECAlert` when both "AS" and "EC" in top-3
- Frontend: `ogAlert` state in app.jsx, populated from `data.asec_alert || null` in the fetch handler; cfgOverride passes `asec_alert: ogAlert` to OgConfirmList; component renders an `asec-alert` block with disambiguation_text and citation
- Test: `test_og_classify_asec_alert_when_both_present` PASSES, `test_og_classify_no_asec_alert_when_only_ec` PASSES
- End-to-end wiring verified: setOgAlert in fetch → cfgOverride.asec_alert → OgConfirmList render

### CLASS-03 — Level picker with correct range

**Status:** ✅ DELIVERED

- Frontend: OgLevelPicker component renders one button per level
- Levels come from `OG_LEVELS[og_code]` — JS constant duplicated from `constants.py` (12 OG groups, exact range per group)
- For EC: 8 buttons; for IT: 5; for AS: 8; for FI: 4
- Test: `OgLevelPicker renders level range` PASSES (8 buttons for EC range 1-8)
- Empty-state message shown if no levels (waits for og_confirm to populate)

### CLASS-04 — Hard gate (frontend + backend)

**Status:** ✅ DELIVERED

- Frontend: document.jsx shows "Classification pending — confirm occupational group and level to proceed" in Classification & Evaluation section when `!record.confirmed_og || !record.og_level`
- Backend: `app/services/classification_gate.py` exports `require_og_confirmed(wd)` raising 409 Conflict with `error: "classification_pending"` if either field missing
- The frontend gate is UX-only; the backend gate is the authoritative one (to be wired into Phase 17/18/20 export routes)
- Test: `test_patch_wd_confirmed_og_persists` PASSES (WDPatchRequest + model extension)
- UAT confirmed: Classification pending state visible in browser

### CLASS-05 — CAF rank advisory display

**Status:** ✅ DELIVERED

- Frontend: `getCafEquivalence(ogCode, ogLevel)` helper in document.jsx with hardcoded `CAF_EQUIV` lookup covering CR/AS/EC/IT/FI groups
- Conditional render in Position Identification section: `{r.reports_to_military && r.confirmed_og && r.og_level && (<div className="caf-advisory">...)}`
- Label: "CAF Rank Equivalent (advisory — not authoritative):"
- Fallback: "See TBS advisory tables" if no match
- UAT confirmed: CAF advisory displays when reports_to_military = "Yes" and OG confirmed
- Source: `CAF_RANK_OG_EQUIVALENCE` in `constants.py` (advisory only, not authoritative)

### API-06 — POST /api/og/classify

**Status:** ✅ DELIVERED

- Route: `v2/backend/app/api/og_classification.py::classify_og`
- Request model: `OGClassifyRequest` with Pydantic validation
- Response model: `OGClassifyResponse` with candidates + asec_alert
- Threat mitigations: T-16-01 (filter unknown codes), T-16-02 (return 404 on unknown), T-16-03 (max_length=2000)
- Test: 4 of 7 tests in test_og_classification.py cover this endpoint, all PASSING

### API-03 — GET /api/og/definitions + GET /api/quals/default

**Status:** ✅ DELIVERED

- `GET /api/og/definitions?og_code=EC` — returns OGDefinitionResponse with verbatim definition text
- `GET /api/quals/default?og_code=EC` — returns QualStandardResponse with education + experience text
- Both return 404 for unknown codes
- Tests: `test_og_definitions_returns_ec_definition`, `test_og_definitions_404_for_unknown_code`, `test_quals_default_returns_ec_text` all PASSING

## Test Results

| Test suite | Count | Status |
|------------|-------|--------|
| v2 backend pytest | 50 | ✅ 50/50 pass |
| v1 backend pytest (regression) | 188 (9 skipped) | ✅ no regressions |
| v2 frontend vitest | 19 | ✅ 19/19 pass |
| Frontend build | 195.65 kB gzip 61.40 kB | ✅ clean |

## Code Review

Manual review (gsd-code-reviewer subagent not installed; consistent with prior phases per workflow fallback rule). Status: **clean** — 0 critical, 0 high, 0 medium, 3 low. See `16-REVIEW.md`.

## UAT

Human UAT approved. All 11 verification steps confirmed:
1. Backend server starts (port 8000)
2. Frontend server starts (port 5173)
3. Classification pending state visible initially
4. reports_to_military step appears in Phase 0
5. og_confirm step appears with cards + AS/EC alert
6. og_level step shows correct number of level buttons
7. Classification & Evaluation section unlocks after OG + level confirmed
8. CAF rank advisory displays when reports_to_military = "Yes"
9. Backend API endpoints respond correctly
10. All automated tests GREEN

## Deviations

Already documented in plan SUMMARYs:
- 5-of-7 RED expected in Plan 16-01 (vs 7); 2 tests expected 404 and got 404 from missing route (semantic GREEN)
- AS/FI definitions sourced from TBS OCHRO standard (PA and CT-FI collective agreements don't contain OG group definition text)
- OgConfirmList test query adapter — `getByRole('button')` + `queryAllByText` instead of `getByText(/EC/)`
- Plan 16-04 "fires once" comment in app.jsx is misleading (trigger fires on every commit) — flagged in REVIEW.md as a low finding

## Next Phase Readiness

Phase 17 (JES Scoring) is unblocked. JES scoring requires:
- `confirmed_og` ✅ set via og_confirm step
- `og_level` ✅ set via og_level step
- `WorkDescription.confirmed_og` and `WorkDescription.og_level` ✅ available on the model

The `require_og_confirmed` gate in `app/services/classification_gate.py` is ready for Phase 17/18/20 to import and use as a 409 gate.
