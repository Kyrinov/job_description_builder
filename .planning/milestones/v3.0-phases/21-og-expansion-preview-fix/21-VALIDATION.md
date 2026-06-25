---
phase: 21
slug: og-expansion-preview-fix
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-10
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest 8.x + pytest-asyncio |
| **Framework (frontend)** | Vitest 2.x |
| **Config file (backend)** | `v2/backend/pytest.ini` or `v2/backend/pyproject.toml` |
| **Config file (frontend)** | `v2/frontend/vitest.config.js` |
| **Quick run command** | `cd v2/backend && python -m pytest tests/test_constants.py tests/test_question_bank.py -x -q` |
| **Full suite command** | `cd v2/backend && python -m pytest -x -q && cd ../frontend && npm test` |
| **Estimated runtime** | ~30 seconds (backend quick), ~60 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `cd v2/backend && python -m pytest tests/test_constants.py tests/test_question_bank.py -x -q`
- **After every plan wave:** Run `cd v2/backend && python -m pytest -x -q && cd ../frontend && npm test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 21-W0-01 | W0 | 0 | OGX-01 | — | N/A | unit | `pytest tests/test_constants.py::test_og_constants_completeness -x` | ❌ W0 | ⬜ pending |
| 21-W0-02 | W0 | 0 | OGX-03 | — | N/A | unit | `pytest tests/test_constants.py::test_qual_defaults_parity -x` | ❌ W0 (FAILING) | ⬜ pending |
| 21-W0-03 | W0 | 0 | OGX-02 | — | N/A | unit | `pytest tests/test_export.py -k "standard_names" -x` | ❌ W0 | ⬜ pending |
| 21-W0-04 | W0 | 0 | OGX-04 | — | N/A | integration | `pytest tests/test_og_classification.py -k "per_group" -x` | ❌ W0 | ⬜ pending |
| 21-W0-05 | W0 | 0 | OGX-05 | — | N/A | integration | `pytest tests/test_jes_scoring.py -k "score_fb" -x` | ❌ W0 | ⬜ pending |
| 21-W0-06 | W0 | 0 | OGX-06 | — | N/A | integration | `pytest tests/test_jes_scoring.py -k "score_nu" -x` | ❌ W0 | ⬜ pending |
| 21-W0-07 | W0 | 0 | OGX-07 | — | confirmed_sub_group validated against known sub-group lists for NU/SW/ED | integration | `pytest tests/test_og_classification.py -k "nu_disambiguation" -x` | ❌ W0 | ⬜ pending |
| 21-W0-08 | W0 | 0 | UI-01 | — | N/A | unit | `cd v2/frontend && npm test -- -t "doc-scroll"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_constants.py::test_og_constants_completeness` — asserts every key in OG_LEVELS is present in OG_DEFINITIONS, QUAL_STANDARDS, NON_EC_TOTALS, NON_EC_STANDARD_NAMES, JES_FACTORS_BY_GROUP (OGX-01)
- [ ] `tests/test_constants.py::test_qual_defaults_parity` — parity test between frontend QUAL_DEFAULTS and backend QUAL_STANDARDS; must be RED before new group text is authored (OGX-03)
- [ ] `tests/test_export.py` test for NON_EC_STANDARD_NAMES import from constants (OGX-02)
- [ ] `tests/test_og_classification.py::test_per_group_signal_routing` — per-group integration tests for all 12 new OG groups (OGX-04)
- [ ] `tests/test_jes_scoring.py` stubs for point-rating groups: FB, FS, LP, MT, LC, SW-SCW (OGX-05)
- [ ] `tests/test_jes_scoring.py` stubs for level-lookup groups: NU, PS, NT, PO, WP, SW-CHA, ED sub-groups (OGX-06)
- [ ] `tests/test_og_classification.py::test_nu_sw_ed_disambiguation` — sub-group alert for NU, SW, ED (OGX-07)
- [ ] Frontend CSS test for `.doc-scroll align-items: flex-start` (UI-01)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ED level count confirmation (EB vs ED mapping) | OGX-01 | Low-confidence assumption: EB_rates.csv proxied for ED; actual level count needs authoring-time confirmation | During JES authoring, verify ED sub-group level count against `data/Job_evaluation/ED Education` file directly |
| JES_FACTORS_BY_GROUP degree vectors for point-rating groups | OGX-05 | Factor names and degree→points tables must be extracted from JES text files during authoring | Read each of FB, FS, LP, MT, LC, SW-SCW JES standard files; confirm factor structure matches EC_JES_ELEMENTS pattern before coding |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
