---
phase: 17
slug: jes-scoring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-05
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend), vitest 3.x (frontend) |
| **Config file** | `v2/backend/pyproject.toml`, `v2/frontend/vite.config.js` |
| **Quick run command** | `cd v2/backend && python -m pytest tests/test_jes_scoring.py -q` |
| **Full suite command** | `cd v2/backend && python -m pytest -q && cd ../frontend && npm test -- --run` |
| **Estimated runtime** | ~30 seconds (backend quick), ~60 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run `cd v2/backend && python -m pytest tests/test_jes_scoring.py -q`
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | JES-01 | — | EC_JES_ELEMENTS constant defined | unit | `pytest tests/test_jes_scoring.py::test_ec_jes_elements_defined -q` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | JES-01 | — | EC_DEGREES covers EC-04/05/06 | unit | `pytest tests/test_jes_scoring.py::test_ec_degrees_spot_check -q` | ❌ W0 | ⬜ pending |
| 17-01-03 | 01 | 1 | JES-03 | — | NON_EC_TOTALS covers FI/IT/AS/EN | unit | `pytest tests/test_jes_scoring.py::test_non_ec_totals_coverage -q` | ❌ W0 | ⬜ pending |
| 17-01-04 | 01 | 1 | API-07 | — | WorkDescription accepts jes_scores list | unit | `pytest tests/test_jes_scoring.py::test_wd_model_jes_fields -q` | ❌ W0 | ⬜ pending |
| 17-02-01 | 02 | 2 | JES-01 | — | EC scoring returns 9 factor rows | unit | `pytest tests/test_jes_scoring.py::test_score_ec_returns_9_factors -q` | ❌ W0 | ⬜ pending |
| 17-02-02 | 02 | 2 | JES-02 | — | Override stores audit_log entry | unit | `pytest tests/test_jes_scoring.py::test_override_writes_audit_log -q` | ❌ W0 | ⬜ pending |
| 17-02-03 | 02 | 2 | JES-03 | — | Non-EC returns single totals line | unit | `pytest tests/test_jes_scoring.py::test_score_non_ec_returns_totals -q` | ❌ W0 | ⬜ pending |
| 17-02-04 | 02 | 2 | API-07 | — | POST /api/jes/score 409 without OG | integration | `pytest tests/test_jes_scoring.py::test_score_requires_og_confirmed -q` | ❌ W0 | ⬜ pending |
| 17-03-01 | 03 | 3 | JES-04 | — | ClassBlock renders EC scorecard rows | unit | `cd v2/frontend && npm test -- --run document.test` | ❌ W0 | ⬜ pending |
| 17-04-01 | 04 | 4 | JES-04 | — | UAT: EC scorecard renders in preview | manual | See Manual-Only table | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `v2/backend/tests/test_jes_scoring.py` — 6 RED stubs covering JES-01, JES-02, JES-03, API-07
- [ ] `v2/frontend/src/document.test.jsx` — ClassBlock JES scorecard render stub (extend existing file)
- [ ] Existing `v2/backend/tests/conftest.py` fixtures cover new routes (extend if needed)

*Existing pytest + vitest infrastructure covers the phase; no new framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| JES scorecard renders in Classification & Evaluation section after confirming OG | JES-04 | Visual render in SPA, not testable via unit/integration tests | Complete conversation to OG confirmation → verify scorecard populates in preview |
| Advisor override input appears after 3 retries for a failed factor | JES-02 | Requires LLM retry simulation in browser | Mock factor failure or use test WD → confirm override UI renders + degree can be entered |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
