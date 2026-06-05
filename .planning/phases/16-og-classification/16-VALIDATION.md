---
phase: 16
slug: og-classification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-05
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + vitest (frontend) |
| **Config file** | `v2/backend/pytest.ini` / `v2/frontend/vite.config.js` |
| **Quick run command** | `cd v2/backend && python -m pytest tests/test_og_classification.py -q` |
| **Full suite command** | `cd v2/backend && python -m pytest -q && cd ../../frontend && npm run test` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd v2/backend && python -m pytest tests/test_og_classification.py -q`
- **After every plan wave:** Run full suite (backend + frontend)
- **Before `/gsd-verify-work`:** Full suite must be green (43 backend + 18+ frontend)
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 0 | CLASS-01, API-06 | T-16-03 | validate og_code ∈ OG_DEFINITIONS; reject unknown | unit | `cd v2/backend && python -m pytest tests/test_og_classification.py -q` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 0 | CLASS-02 | T-16-01 | AS/EC disambiguation only surfaced when both in top-3 | unit | `cd v2/backend && python -m pytest tests/test_og_classification.py -q` | ❌ W0 | ⬜ pending |
| 16-01-03 | 01 | 0 | CLASS-04 | — | N/A (gate logic) | unit | `cd v2/backend && python -m pytest tests/test_og_classification.py -q` | ❌ W0 | ⬜ pending |
| 16-01-04 | 01 | 0 | API-03 | T-16-02 | validate og_code ∈ OG_DEFINITIONS before returning defs | unit | `cd v2/backend && python -m pytest tests/test_og_classification.py -q` | ❌ W0 | ⬜ pending |
| 16-02-01 | 02 | 1 | CLASS-01, API-06 | T-16-03 | POST /api/og/classify returns top-3 with confidence scores | integration | `cd v2/backend && python -m pytest tests/test_og_classification.py::test_og_classify_returns_top3 -q` | ❌ W0 | ⬜ pending |
| 16-02-02 | 02 | 1 | CLASS-02 | — | disambiguation block appears when AS+EC in top-3 | integration | `cd v2/backend && python -m pytest tests/test_og_classification.py::test_asec_disambiguation -q` | ❌ W0 | ⬜ pending |
| 16-02-03 | 02 | 1 | API-03 | — | GET /api/og/definitions returns definition+inclusions+exclusions | integration | `cd v2/backend && python -m pytest tests/test_og_classification.py::test_og_definitions_endpoint -q` | ❌ W0 | ⬜ pending |
| 16-02-04 | 02 | 1 | API-03 | — | GET /api/quals/default returns qual standard text | integration | `cd v2/backend && python -m pytest tests/test_og_classification.py::test_quals_default_endpoint -q` | ❌ W0 | ⬜ pending |
| 16-02-05 | 02 | 1 | CLASS-04 | — | /api/jes/score returns 400 if og_code or og_level null | integration | `cd v2/backend && python -m pytest tests/test_og_classification.py::test_hard_gate -q` | ❌ W0 | ⬜ pending |
| 16-03-01 | 03 | 2 | CLASS-03 | — | level-selection step renders correct range | unit | `cd v2/frontend && npm run test -- --reporter=verbose conversation.test` | ✅ | ⬜ pending |
| 16-03-02 | 03 | 2 | CLASS-04 | — | doc preview shows Classification pending until both confirmed | unit | `cd v2/frontend && npm run test -- --reporter=verbose conversation.test` | ✅ | ⬜ pending |
| 16-03-03 | 03 | 2 | CLASS-05 | — | CAF advisory renders when reports_to_military=true | unit | `cd v2/frontend && npm run test -- --reporter=verbose conversation.test` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `v2/backend/tests/test_og_classification.py` — 7 stubs (RED) for CLASS-01, CLASS-02, CLASS-04, API-06, API-03
- [ ] `v2/frontend/src/conversation.test.jsx` additions — 2–3 new stubs for CLASS-03, CLASS-04 (pending state), CLASS-05

*All other infrastructure exists — no new frameworks or config files needed (43 backend + 18 frontend tests passing baseline confirmed).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OG candidate confirmation cards render correctly in SPA | CLASS-01 | Browser rendering; jsdom doesn't render CSS | Start `npm run dev` + `uvicorn`; submit a work description; confirm NOC; verify 3 OG cards appear with rationale text |
| AS/EC disambiguation alert visually distinct | CLASS-02 | CSS visual distinction requires browser | When EC+AS top-3, verify disambiguation block appears above cards |
| Level selection choice cards render correct range | CLASS-03 | Browser rendering | After OG confirmed as EC, verify choice cards show EC-01 through EC-08 |
| CAF advisory label visible beside reporting line | CLASS-05 | Browser rendering | Answer "reports to military supervisor" → verify advisory label "advisory — not authoritative" appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
