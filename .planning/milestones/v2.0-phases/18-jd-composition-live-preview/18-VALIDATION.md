---
phase: 18
slug: jd-composition-live-preview
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-08
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + httpx (backend) · Vitest + jsdom + @testing-library/react (frontend) |
| **Config file** | `v2/backend/pytest.ini` / `v2/frontend/vite.config.js` |
| **Quick run command** | `cd v2/backend && python -m pytest tests/test_jd_composition.py -x` |
| **Full suite command** | `cd v2/backend && python -m pytest -x && cd ../frontend && npm run test` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd v2/backend && python -m pytest tests/test_jd_composition.py -x`
- **After every plan wave:** Run `cd v2/backend && python -m pytest -x && cd ../frontend && npm run test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 0 | JD-01..04 | T-18-01 / — | Stubs RED, no logic | unit | `cd v2/backend && python -m pytest tests/test_jd_composition.py -x` | ❌ W0 | ⬜ pending |
| 18-01-02 | 01 | 0 | DOC-01..05 | — | Frontend stubs RED | unit | `cd v2/frontend && npm run test` | ❌ W0 | ⬜ pending |
| 18-02-01 | 02 | 1 | JD-01 | T-18-01 | NOC code validated before DB query | integration | `cd v2/backend && python -m pytest tests/test_jd_composition.py::test_get_noc_duties_returns_main_duties -x` | ❌ W0 | ⬜ pending |
| 18-02-02 | 02 | 1 | JD-02 | T-18-02 | Provenance hash non-null | unit | `cd v2/backend && python -m pytest tests/test_jd_composition.py::test_draft_duty_provenance_fields -x` | ❌ W0 | ⬜ pending |
| 18-02-03 | 02 | 1 | JD-03 | — | advisor flag stored in JSON | unit | `cd v2/backend && python -m pytest tests/test_jd_composition.py::test_advisor_duty_source_type -x` | ❌ W0 | ⬜ pending |
| 18-02-04 | 02 | 1 | JD-04 | — | EC returns empty orphan flags | integration | `cd v2/backend && python -m pytest tests/test_jd_composition.py::test_orphan_check_ec_no_flags -x` | ❌ W0 | ⬜ pending |
| 18-03-01 | 03 | 2 | JD-01 | — | DutyBuilder fetches from API | unit (frontend) | `cd v2/frontend && npm run test -- document.test.jsx` | ❌ W0 | ⬜ pending |
| 18-03-02 | 03 | 2 | JD-04 | — | Orphan badge renders when d.orphan+reviewing | unit (frontend) | `cd v2/frontend && npm run test -- document.test.jsx` | ❌ W0 | ⬜ pending |
| 18-03-03 | 03 | 2 | DOC-01 | — | Section 5 ghost renders unconditionally | unit (frontend) | `cd v2/frontend && npm run test -- document.test.jsx` | ❌ W0 | ⬜ pending |
| 18-03-04 | 03 | 2 | DOC-03 | — | Ghost note copy matches UI-SPEC | unit (frontend) | `cd v2/frontend && npm run test -- document.test.jsx` | ❌ W0 | ⬜ pending |
| 18-03-05 | 03 | 2 | DOC-04 | — | Section click calls onEditStep('duties') | unit (frontend) | `cd v2/frontend && npm run test -- document.test.jsx` | ❌ W0 | ⬜ pending |
| 18-03-06 | 03 | 2 | DOC-05 | — | Section 3 src pill shows "NOC 2021" not "NOC 2021 · refined" | unit (frontend) | `cd v2/frontend && npm run test -- document.test.jsx` | ❌ W0 | ⬜ pending |
| 18-04-01 | 04 | 3 | JD-01..04, DOC-01..05 | all | Full suite green gate | integration | `cd v2/backend && python -m pytest -x && cd ../frontend && npm run test` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `v2/backend/tests/test_jd_composition.py` — stubs for JD-01..04 backend tests
- [ ] `noc_duties_db` fixture in `v2/backend/tests/conftest.py` — creates `noc_elements` with `element_type='Main duties'` rows for test NOC code
- [ ] `v2/frontend/src/document.test.jsx` stubs — covers DOC-01, DOC-03, DOC-04, DOC-05, orphan badge (JD-04 frontend)

*Existing test infrastructure (`v2/backend/tests/conftest.py`, `v2/frontend/src/*.test.jsx`) covers Phase 18 patterns — no new framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `freshWash` animation fires on Section 3 when duties first populate | DOC-03 | CSS animation not testable in jsdom | Load app, complete duty step, observe gold wash on Section 3 |
| Selection count badge updates live as duty cards toggled | JD-01 | Requires real browser interaction | Toggle duty cards, verify counter updates without submit |
| Orphan badge visible at review with IT position (has real exclusions) | JD-04 | Requires real IT OG_DEFINITIONS exclusions checked against duty text | Add duty contradicting IT exclusion, enter review state, verify badge |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
