---
phase: 19
slug: qualifications-amendments
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-09
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest + pytest-asyncio |
| **Framework (frontend)** | Vitest + jsdom + @testing-library/react |
| **Backend config** | `v2/backend/tests/conftest.py` |
| **Frontend config** | `v2/frontend/vite.config.js` (test block) |
| **Quick run (backend)** | `cd v2/backend && python -m pytest tests/ -q` |
| **Quick run (frontend)** | `cd v2/frontend && npx vitest run` |
| **Full suite** | Both of the above |
| **Estimated runtime** | ~15 seconds (backend ~10s, frontend ~5s) |

---

## Sampling Rate

- **After every task commit:** Run `cd v2/backend && python -m pytest tests/ -q`
- **After every plan wave:** Run both backend and frontend suites
- **Before `/gsd-verify-work`:** Full suite must be green (64+ backend, 7+ frontend passing)
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 0 | QUAL-01 | — | N/A | unit | `pytest tests/test_quals.py -x` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 0 | QUAL-01 | — | N/A | unit | `cd v2/frontend && npx vitest run` | ❌ W0 | ⬜ pending |
| 19-01-03 | 01 | 0 | AMEND-01 | — | input validated | integration | `pytest tests/test_amendments.py -x` | ❌ W0 | ⬜ pending |
| 19-01-04 | 01 | 0 | — | — | jsdom env fixed | unit | `cd v2/frontend && npx vitest run` | ✅ exists | ⬜ pending |
| 19-02-01 | 02 | 1 | QUAL-01 | — | N/A | unit | `pytest tests/test_quals.py::test_qual_default_ec -x` | ❌ W0 | ⬜ pending |
| 19-02-02 | 02 | 1 | QUAL-01 | — | N/A | unit | `pytest tests/test_quals.py::test_qual_default_all_groups -x` | ❌ W0 | ⬜ pending |
| 19-02-03 | 02 | 1 | QUAL-02 | — | N/A | unit | `cd v2/frontend && npx vitest run components.test` | ❌ W0 | ⬜ pending |
| 19-02-04 | 02 | 1 | QUAL-03 | — | N/A | unit | `cd v2/frontend && npx vitest run document.test` | ❌ W0 | ⬜ pending |
| 19-03-01 | 03 | 2 | AMEND-01 | T-19-01 | section key validated; 404 on bad WD | integration | `pytest tests/test_amendments.py::test_save_amendment_creates_audit_row -x` | ❌ W0 | ⬜ pending |
| 19-03-02 | 03 | 2 | AMEND-01 | T-19-02 | oversized comment rejected | integration | `pytest tests/test_amendments.py::test_get_amendments_latest_per_section -x` | ❌ W0 | ⬜ pending |
| 19-03-03 | 03 | 2 | AMEND-01 | T-19-03 | 404 on non-existent WD | integration | `pytest tests/test_amendments.py::test_save_amendment_404 -x` | ❌ W0 | ⬜ pending |
| 19-04-01 | 04 | 3 | AMEND-02 | — | N/A | integration | `pytest tests/test_amendments.py::test_amendment_audit_log_fields -x` | ❌ W0 | ⬜ pending |
| 19-04-02 | 04 | 3 | all | — | N/A | full | `pytest tests/ -q && npx vitest run` | ✅ / ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `v2/backend/tests/test_quals.py` — stubs for QUAL-01 (getQualDefault backend-side)
- [ ] `v2/backend/tests/test_amendments.py` — stubs for AMEND-01, AMEND-02
- [ ] `v2/frontend/src/components.test.jsx` — stubs for QUAL-01 prefill, QUAL-02 validation
- [ ] `v2/frontend/src/document.test.jsx` — extend for QUAL-03 sub-labels class
- [ ] Fix jsdom `ReferenceError: document is not defined` — 23 frontend tests currently failing; must be green before Phase 19 tests can run

*Wave 0 is a blocker: the frontend test suite is non-green entering Phase 19.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| QualEditor shows correct OG-matched text on first mount (visual check) | QUAL-01 | Vitest can assert prefill value but not visual rendering of textareas in the SPA | Load the app, complete qualification confirmation for EC, navigate to quals step, verify textarea shows EC degree text |
| Amendment panel opens/closes on click in review state | AMEND-01 | UI interaction flow in review state requires browser session with a WD in reviewing=true | Complete a WD, enter review state, click amendment icon on any section, enter text, save, verify gold dot appears |
| Amendment note survives page refresh | AMEND-01 | Requires browser refresh cycle with real GET /api/wd/{id}/amendments call | After saving a note, refresh the browser, verify the note text is still visible in the amendment panel |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
