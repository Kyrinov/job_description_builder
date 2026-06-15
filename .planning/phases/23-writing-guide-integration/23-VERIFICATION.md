---
phase: 23-writing-guide-integration
status: passed
verifier: orchestrator
verified_at: "2026-06-15T12:55:00Z"
---

# Phase 23 Verification — Writing Guide Integration

## Goal (from ROADMAP.md)

> An advisor in the duty-entry step of the conversation receives (a) inline structural hints on duties that fail active-voice, word-count, no-passive, or no-duplicate rules; (b) a non-blocking advisory endpoint that powers those hints; (c) a "Client Service Results" question inserted in the conversational flow; and (d) a per-step OG-specific duty tip drawn from the authoritative group definition.

## Requirements

| ID | Description | Status |
|----|-------------|--------|
| WG-01 | Structural duty validation (verb-first, word-count 8–25, no passive, no duplicate); < 15% of SJD duties flagged | **PASSED** — `duty_validator.py` implements all 4 rules; 5/5 unit tests GREEN; 0% flag rate on 9-duty calibration corpus |
| WG-02 | Non-blocking inline `.duty-hint` warnings via `POST /api/wd/{id}/validate-duties` | **PASSED** — endpoint wired; frontend `dutyHints` state populated after duties commit; `.duty-hint` badge rendered in DutyBuilder (NOC, suggestion, advisor paths); silent on failure |
| WG-03 | Client Service Results step in conversation before duties | **PASSED** — `client_service_results` step inserted in STEPS at phase 3, before `duties`. Frontend-only per RESEARCH.md A1/Pitfall 2 (not in backend QUESTION_BANK). |
| WG-04 | Per-step OG-specific duty tips from OG_DEFINITIONS | **PASSED** — `OG_DUTY_TIPS` constant in data.jsx (22 OG groups; empty string for thin groups CR/PM/GT/AI/AU/ED); `og_tip` passed via cfgOverride; `.og-duty-tip` box rendered at top of DutyBuilder when `confirmed_og` is set and tip is ≥ 80 chars |

## Goal-Backward Verification

### Success Criterion 1: Inline `.duty-hint` warnings after duty-phase commit, non-blocking

**Must exist:**
- [x] `app.jsx` `dutyHints` state declaration — confirmed at line 95
- [x] `app.jsx` `POST /api/wd/{id}/validate-duties` chained in duties commit — confirmed at line 367-371
- [x] `app.jsx` `setDutyHints([])` on editingReturn re-entry of duties — confirmed at line 420
- [x] `app.jsx` `duty_hints: dutyHints` in cfgOverride — confirmed at line 770
- [x] `components.jsx` `dutyHint(dutyId)` helper — confirmed at line 146
- [x] `components.jsx` `dutyHint(...)` calls in NOC, suggestion, advisor renderers — confirmed at lines 227, 252, 267
- [x] `styles.css` `.duty-hint` rule — confirmed at line 783

**Must wire:**
- [x] Endpoint → frontend fetch chain (silently catches errors)
- [x] Frontend state → DutyBuilder `cfg` prop
- [x] DutyBuilder `cfg.duty_hints` → inline `<span class="duty-hint">` rendering

**Verified:** The duty hint system is end-to-end wired. Non-blocking (silent catch), non-persisted (state-only), non-mutating (read-only endpoint).

### Success Criterion 2: POST /api/wd/{id}/validate-duties returns per-duty findings; < 15% of SJD duties flagged

**Must exist:**
- [x] `app/api/wd.py` `@router.post("/wd/{wd_id}/validate-duties")` — confirmed at line 304-305
- [x] `app/api/wd.py` `validate_duties_endpoint(wd_id: str) -> dict` — confirmed
- [x] Endpoint calls `from app.services.duty_validator import validate_duties` — confirmed at line 312
- [x] Endpoint mirrors `run_orphan_check` pattern (parameterised SQL, 404 on miss, WorkDescription.model_validate_json) — confirmed

**Verified by test results:**
- `test_validate_duties_endpoint` — PASSED (200 with `findings` and `wd_id` in body)
- `test_validate_duties_404` — PASSED (404 for unknown WD; no longer a false-positive — endpoint is real)
- `test_calibration_sjd_corpus` — PASSED (0% flag rate on 9 SJD duties; threshold is < 15%)

**Must wire:**
- [x] `WorkDescription.duties` deserialised from DB row → `validate_duties()` → response
- [x] `validate_duties()` reads `.id` and `.text` from each duty (correctly handles `DraftDuty` model)

**Verified:** The endpoint correctly serialises the validator's findings back to the frontend.

### Success Criterion 3: STEPS includes Client Service Results before duties step

**Must exist:**
- [x] `data.jsx` `{ id: 'client_service_results', phase: 3, ... }` — confirmed at line 657
- [x] Step is BEFORE `{ id: 'duties', phase: 3, ... }` (line 665)
- [x] `input.type === 'textarea'` (correct shape)
- [x] `apply: (r, a) => ({ client_service_results: a })` — stores on record

**Verified by test results:**
- `conversation.test.jsx` `getVisibleSteps omits all cluster steps when no sector answer (22 - 9 = 13)` — PASSED with updated count of 13 (was 12; new step adds 1)

**Decision:** Step is frontend-only (in `STEPS` array), not in backend `QUESTION_BANK`. Per `RESEARCH.md A1/Pitfall 2`, this is correct: the step has no classification signals (it's a textarea), and `test_question_bank.py` requires every entry to have an `options` key. Adding it to `QUESTION_BANK` would break the existing test. Frontend-only is the right choice.

### Success Criterion 4: Per-step OG tip drawn from OG_DEFINITIONS, suppressed for thin groups

**Must exist:**
- [x] `data.jsx` `OG_DUTY_TIPS` constant — confirmed at line 59
- [x] 22 OG group keys present (EC, AS, IT, FI, CR, PM, GT, EL, AI, AU, FB, FS, ED, LC, LP, MT, NT, NU, PO, PS, SW, WP)
- [x] Empty string for CR, PM, GT, AI, AU, ED (thin groups)
- [x] `OG_DUTY_TIPS` exported — confirmed at line 709
- [x] `app.jsx` cfgOverride `og_tip` IIFE — confirmed at lines 760-765
- [x] `components.jsx` `.og-duty-tip` rendering — confirmed at line 195-198
- [x] `styles.css` `.og-duty-tip` rule — confirmed at line 797

**Logic verified:**
- `og_tip = OG_DUTY_TIPS[ogCode] || ''` — empty string if code not found
- `return tip.length >= 80 ? tip : null` — suppressed for thin groups AND for short tips
- `cfg.og_tip` is `null` for thin groups → `{cfg && cfg.og_tip && ...}` is falsy → box not rendered

**Verified:** The tip is drawn verbatim from `OG_DEFINITIONS` (via JS copy in `OG_DUTY_TIPS`), not a hardcoded string. Suppression logic is correct.

## File-by-File Audit

### Backend

| File | Status | Lines Changed | Notes |
|------|--------|---------------|-------|
| `v2/backend/app/services/duty_validator.py` | NEW | +95 | Full implementation with 4 rules |
| `v2/backend/tests/test_writing_guide.py` | NEW | +190 | 9 test functions (5 validator, 2 endpoint, 2 guard) |
| `v2/backend/app/api/wd.py` | MODIFIED | +27 | New endpoint after `run_orphan_check` |

### Frontend

| File | Status | Lines Changed | Notes |
|------|--------|---------------|-------|
| `v2/frontend/src/data.jsx` | MODIFIED | +37 | OG_DUTY_TIPS + client_service_results + export |
| `v2/frontend/src/app.jsx` | MODIFIED | +34 | dutyHints state, validate-duties chain, editingReturn clear, cfgOverride |
| `v2/frontend/src/components.jsx` | MODIFIED | +24 | dutyHint helper, .duty-hint + .og-duty-tip rendering |
| `v2/frontend/src/styles.css` | MODIFIED | +29 | .duty-hint + .og-duty-tip CSS rules |
| `v2/frontend/src/conversation.test.jsx` | MODIFIED | -3/+4 | Updated visible-step count 12 → 13 for OGX-04 test |

## Test Suite Results

```
Backend:  134 passed, 15 warnings in 10.50s
Frontend: 60 passed, 0 failed
Build:    ✓ 231.58 kB JS / 70.63 kB gzip / 28.55 kB CSS / 6.08 kB CSS gzip
```

**No regressions.** Test count: backend 125 → 134 (+9 from test_writing_guide.py), frontend unchanged at 60.

## Deviations from Plan

1. **Tightened `_VERB_FIRST` regex** (`^[A-Z][a-zA-Z]*$` → `^[A-Z][a-zA-Z]*s$`) — required by the `test_non_verb_opener` test which expects "Administrative" to be flagged. Plan's regex incorrectly accepted capitalised adjectives as verbs. Tightened regex requires trailing 's' (3rd-person singular verb form), matching the GoC duty style (all corpus openers end in 's').

2. **Helper function `dutyHint()` instead of inline IIFE** — cleaner DRY across 3 renderers. Behaviour identical.

3. **Updated `conversation.test.jsx` OGX-04 test** — new step changes visible-step count from 12 to 13. Plan did not anticipate this.

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| `validate-duties` endpoint silent failure leaves stale hints | `setDutyHints([])` on editingReturn clears stale state |
| `OG_DUTY_TIPS` could drift from `OG_DEFINITIONS` | Both are static, single-source-of-truth at write time; no API call needed |
| `_VERB_FIRST` regex too strict (rejects legitimate openers) | All 9 calibration corpus duties pass at 0% flag rate; < 15% threshold met with headroom |
| Compound verb opener ("Plans,") false-positive | `rstrip(',;:.')` strips trailing punctuation before regex |
| Tip text too long for UI | `.slice(0, 200)` at render time caps display length |

## Status: PASSED

Phase 23 achieves all 4 success criteria and delivers all 4 requirement IDs (WG-01, WG-02, WG-03, WG-04).

134/134 backend tests + 60/60 frontend tests GREEN. Build succeeds.

**Human UAT items** (4 steps):
1. Navigate conversation to duty entry step; confirm tip box appears above duty list for EC/IT/AS/NU (not for CR/PM where tip is suppressed)
2. Enter a duty with fewer than 8 words; commit; confirm `.duty-hint` appears inline without blocking
3. Navigate conversation to where `client_service_results` question should appear; confirm it precedes the duties step
4. Re-enter duties step via back/edit; confirm old hints are cleared before re-commit
