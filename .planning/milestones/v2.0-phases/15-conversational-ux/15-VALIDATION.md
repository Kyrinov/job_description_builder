---
phase: 15
slug: conversational-ux
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-04
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (frontend)** | vitest 4.1.8 + @testing-library/react 16.3.2 |
| **Framework (backend)** | pytest (existing) |
| **Config file (frontend)** | `v2/frontend/vitest.config.js` |
| **Quick run command (frontend)** | `cd v2/frontend && npm test` |
| **Quick run command (backend)** | `cd v2/backend && python -m pytest tests/test_wd.py -x` |
| **Full suite command** | `cd v2/backend && python -m pytest` |
| **Estimated runtime** | ~15 seconds (frontend < 5s + backend ~10s) |

---

## Sampling Rate

- **After every task commit:** Run `cd v2/frontend && npm test` (frontend tasks) or `cd v2/backend && python -m pytest tests/test_wd.py` (backend tasks)
- **After every plan wave:** Run `cd v2/backend && python -m pytest` (full suite, 39+ tests)
- **Before `/gsd-verify-work`:** Both suites must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | API-02 | T-15-01 / — | Parameterized queries prevent SQL injection | unit (RED stubs) | `cd v2/backend && python -m pytest tests/test_wd.py -x` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | CONVO-01..05 | — | N/A | unit (RED stubs) | `cd v2/frontend && npm test` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 2 | API-02 | T-15-01 | WorkDescription.model_validate_json raises 422 on malformed data | integration | `cd v2/backend && python -m pytest tests/test_wd.py -x` | ❌ W0 | ⬜ pending |
| 15-02-02 | 02 | 2 | API-02 | — | N/A | integration | `cd v2/backend && python -m pytest` | ❌ W0 | ⬜ pending |
| 15-03-01 | 03 | 2 | CONVO-01, CONVO-03 | — | N/A | unit | `cd v2/frontend && npm test` | ❌ W0 | ⬜ pending |
| 15-04-01 | 04 | 3 | CONVO-02, CONVO-04, CONVO-05 | — | N/A | unit | `cd v2/frontend && npm test` | ❌ W0 | ⬜ pending |
| 15-04-02 | 04 | 3 | CONVO-01..05, API-02 | — | N/A | integration | `cd v2/frontend && npm test && cd v2/backend && python -m pytest` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `v2/backend/tests/test_wd.py` — RED stubs for API-02 (POST/GET/PATCH /api/wd)
- [ ] `v2/frontend/src/conversation.test.jsx` — RED stubs for CONVO-01 through CONVO-05

*Existing infrastructure covers test runners and conftest — only test files need to be created.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Phase chips display correct active/done/pending states visually | CONVO-03 | CSS class rendering cannot be fully verified without a browser | Load the SPA, advance through steps, confirm chip states update visually |
| NOC candidate cards render and selection works end-to-end | CONVO-04 | Requires live Ollama + NOC pipeline | Submit a work description, confirm NocConfirmList renders candidates, select one |
| Auto-scroll brings active question into view | CONVO-05 | Scroll behavior requires real browser viewport | Advance through several steps, confirm active question is visible without manual scroll |
| In-progress WD is restored after browser refresh | API-02 | Requires real browser localStorage | Answer 2 steps, refresh browser, confirm answers and step index are restored |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
