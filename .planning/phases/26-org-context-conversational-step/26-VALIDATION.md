---
phase: 26
slug: org-context-conversational-step
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-19
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + jest/vitest (frontend) |
| **Config file** | `v2/backend/pytest.ini` / `v2/frontend/package.json` |
| **Quick run command** | `cd v2/backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd v2/backend && python -m pytest tests/ && cd ../frontend && npm test -- --watchAll=false` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd v2/backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run full suite (backend + frontend)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 26-01-01 | 01 | 0 | ORG-01 | — | Silent field drop prevented | unit | `pytest tests/test_wd.py -k org_context -x -q` | ❌ W0 | ⬜ pending |
| 26-01-02 | 01 | 0 | ORG-03 | — | Placeholder string in export when None | unit | `pytest tests/test_export.py -k org_context -x -q` | ❌ W0 | ⬜ pending |
| 26-01-03 | 01 | 0 | ORG-01 | — | stepIndex resume correct after STEPS insert | unit | `npm test -- --testPathPattern=app.test -t stepIndex --watchAll=false` | ❌ W0 | ⬜ pending |
| 26-01-04 | 01 | 0 | ORG-01 | — | OrgContextInput assembles 4 sub-answers | unit | `npm test -- --testPathPattern=conversation.test -t OrgContext --watchAll=false` | ❌ W0 | ⬜ pending |
| 26-01-05 | 01 | 0 | ORG-02 | — | DocumentPane renders org_context Sec | unit | `npm test -- --testPathPattern=document.test -t org_context --watchAll=false` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_wd.py` — stubs for ORG-01 (PATCH round-trip, WDPatchRequest co-update)
- [ ] `tests/test_export.py` — stubs for ORG-03 (org_context in DOCX + None fallback)
- [ ] `src/__tests__/app.test.jsx` — stubs for stepIndex resume regression fix
- [ ] `src/__tests__/conversation.test.jsx` — stubs for OrgContextInput 4-part assembly
- [ ] `src/__tests__/document.test.jsx` — stubs for Sec rendering above Client Service Results

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Accessible DOCX Part 2 Organizational Context section contains org_context text when filled | ORG-03 | DOCX binary output requires human inspection | Download DOCX with org_context filled; open in Word/LibreOffice; verify Part 2 "Organizational Context" section shows advisor text, not placeholder |
| Four-part Socratic step renders correctly in conversation UX | ORG-01 | Visual/interactive flow not fully captured in unit tests | Run app, step through to org context step, fill all 4 sub-questions, advance to next step and confirm text assembled in preview |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
