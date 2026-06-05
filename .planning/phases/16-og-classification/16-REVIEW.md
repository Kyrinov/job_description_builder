---
phase: 16-og-classification
status: clean
reviewer: manual (gsd-code-reviewer subagent not installed)
date: 2026-06-05
plans-reviewed: [16-01, 16-02, 16-03, 16-04]
---

# Phase 16 Code Review

## Summary

**Status: clean (no critical/high issues)**

Phase 16 implements OG classification with deterministic signal-based ranking (no LLM calls in this module), AS/EC disambiguation via `ogAlert` state, a hard-gate utility for downstream phases, and a CAF rank advisory display. All 7 backend tests + 50 prior tests GREEN; 19/19 frontend tests GREEN; clean build; human UAT approved.

## Methodology

Manual review using standard patterns: STRIDE threat model, Pydantic input validation, React XSS posture, OWASP top 10. `gsd-code-reviewer` subagent not installed (consistent with prior phases per the workflow's fallback rule).

## Threat Model Coverage

| Threat ID | Status | Notes |
|-----------|--------|-------|
| T-16-01 (signal_tally unknown codes) | mitigated | `_rank_og_candidates` filters `{k: v for k, v in signal_tally.items() if k in OG_DEFINITIONS}` |
| T-16-02 (og_code query tampering) | mitigated | `if og_code not in OG_DEFINITIONS: raise HTTPException(404)` |
| T-16-03 (oversized work_description DoS) | mitigated | Pydantic `Field(min_length=10, max_length=2000)` |
| T-16-04 (og_level range bypass) | mitigated | `WorkDescription.og_level: Field(default=None, ge=1)`; classification_gate.py checks `og_level is not None` |
| T-16-05 (XSS in OgConfirmList) | accepted | React text nodes; no `dangerouslySetInnerHTML` |
| T-16-06 (og_confirm tampering) | accepted | Frontend answerValid + backend validates via PATCH |
| T-16-07 (phase 0 step insertion safety) | mitigated | FLASH map uses `step.id` keys (not indices) |
| T-16-08 (document.jsx XSS) | accepted | React text nodes only |
| T-16-09 (CAF lookup null returns) | accepted | Falls back to "See TBS advisory tables" |
| T-16-10 (frontend gate bypass) | accepted | Frontend gate is UX only; backend `require_og_confirmed` blocks export at API layer (Phase 17/18/20 will import) |

## Findings

### Critical (0)

None.

### High (0)

None.

### Medium (0)

None.

### Low (3)

1. **Misleading "fires once" comment in app.jsx**: The OG trigger comment says "fires once when noc_confirm step is committed" but the trigger actually fires on every commit of that step (e.g., on re-answer via `editStep()`). The "once" wording suggests the trigger should be skipped on subsequent visits. **Recommendation**: Either remove the "once" wording from the comment or guard the trigger with a `!answers.noc_confirm` check. Current behavior is functionally correct (re-fetches the OG ranking on re-answer) but the comment is misleading.

2. **CAF_EQUIV lookup is a hardcoded static dict in document.jsx**: ~30 entries covering CR/AS/EC/IT/FI groups at all levels. This will drift from `CAF_RANK_OG_EQUIVALENCE` in `constants.py` if the Python constant is updated. **Recommendation**: When the Python constant stabilizes, consider exposing it via `/api/og/caf-equivalence?og_code=EC&og_level=5` and caching the response. Not blocking for Phase 16 — advisory only, the lookup is best-effort with a "See TBS advisory tables" fallback.

3. **Test query adapter for OgConfirmList (already documented in 16-03-SUMMARY)**: The plan's test used `getByText(/EC/)` which fails RED because the new component renders "EC" in two places. Changed to `getByRole('button')` + `queryAllByText`. Test still validates the same contract; the change is a minimal test fix.

## Compliance Checks

- **No secrets in code**: PASS (no env vars, tokens, or credentials)
- **No SQL injection**: PASS (no SQL; data is hardcoded in constants)
- **No PII logging**: PASS (no logger statements with user data)
- **Pydantic validation on all inputs**: PASS (OGClassifyRequest, OGDefinitionResponse)
- **Proper HTTP status codes**: PASS (200/404/409 used correctly)
- **No use of `dangerouslySetInnerHTML` for user input**: PASS (React text nodes throughout)
- **Deterministic responses (no LLM in classification)**: PASS (no instructor, no Ollama in this module)
- **Verbatim source text for OG definitions (CLASS provenance)**: PASS (EC from EC JES 2017 file; IT from IT JES file; AS/FI from TBS OCHRO standard with clear source note)
- **Advisory labelling on CAF equivalence**: PASS (label "advisory — not authoritative" in display)

## Deviations from Plan (already documented in plan SUMMARYs)

- 5 of 7 RED stubs in Plan 16-01 (vs 7 expected) — 2 tests expected 404 and got 404 from missing route, so they pass (semantic GREEN)
- AS/FI definitions sourced from TBS OCHRO standard (not from PA/CT-FI collective agreements, which don't contain group definition text)
- OgConfirmList test query adapter — `getByRole('button')` + `queryAllByText` instead of `getByText`

## Sign-off

**Status: clean** — no blocking issues. The 3 low findings are minor (misleading comment, hardcoded CAF lookup drift risk, test query adapter) and don't require Phase 17 rework. Recommend addressing the misleading comment in the next phase that touches app.jsx.

**Files reviewed:**
- `v2/backend/app/data/constants.py` (+177 lines: OG_DEFINITIONS, ASEC_DISAMBIGUATION, QUAL_STANDARDS)
- `v2/backend/app/models/work_description.py` (+3 lines: confirmed_og, og_level, reports_to_military)
- `v2/backend/app/api/wd.py` (+3 lines: WDPatchRequest fields)
- `v2/backend/app/api/og_classification.py` (new, 188 lines: 3 endpoints + ranker + threat mitigations)
- `v2/backend/app/api/__init__.py` (+2 lines: router registration)
- `v2/backend/app/services/classification_gate.py` (new, 37 lines: require_og_confirmed)
- `v2/backend/tests/test_og_classification.py` (new, 104 lines: 7 test stubs)
- `v2/frontend/src/data.jsx` (+42 lines: OG_LEVELS, 3 new STEPS)
- `v2/frontend/src/components.jsx` (+86 lines: OgConfirmList, OgLevelPicker, dispatcher, answerValid)
- `v2/frontend/src/app.jsx` (+73 lines: ogCandidates/ogLoading/ogAlert state, OG trigger, invalidation, cfgOverride, restart, FLASH map)
- `v2/frontend/src/conversation.test.jsx` (+34 lines: 2 new test stubs)
- `v2/frontend/src/document.jsx` (+96 lines: getCafEquivalence, Classification pending state, CAF advisory)
