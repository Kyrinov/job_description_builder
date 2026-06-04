---
phase: 13
slug: frontend-spa-shell
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-04
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest + jsdom (not yet installed — Wave 0 gap) |
| **Config file** | `v2/frontend/vite.config.js` — test block added in Wave 0 |
| **Quick run command** | `cd v2/frontend && npx vitest run --reporter=verbose` |
| **Full suite command** | `cd v2/frontend && npx vitest run` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd v2/frontend && npx vitest run --reporter=verbose`
- **After every plan wave:** Run `cd v2/frontend && npx vitest run`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 0 | FE-01, FE-04, FE-05 | — | N/A | setup | `cd v2/frontend && npm install --save-dev vitest @testing-library/react @testing-library/user-event jsdom && npx vitest run` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | FE-01 | — | N/A | smoke | `ls v2/frontend/src/{app,data,conversation,document,components}.jsx v2/frontend/src/styles.css` | ❌ W0 | ⬜ pending |
| 13-02-01 | 02 | 1 | FE-03 | — | N/A | smoke | `grep -q "Hanken Grotesk" v2/frontend/src/styles.css && grep -q "Spectral" v2/frontend/src/styles.css && echo OK` | ❌ W0 | ⬜ pending |
| 13-03-01 | 03 | 2 | FE-04 | — | N/A | unit | `cd v2/frontend && npx vitest run src/app.test.jsx` | ❌ W0 | ⬜ pending |
| 13-03-02 | 03 | 2 | FE-05 | — | N/A | unit | `cd v2/frontend && npx vitest run src/app.test.jsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `npm install --save-dev vitest @testing-library/react @testing-library/user-event jsdom` in `v2/frontend/`
- [ ] `v2/frontend/vite.config.js` — add `test: { environment: 'jsdom' }` block
- [ ] `v2/frontend/src/app.test.jsx` — stubs for FE-04 (state slices) and FE-05 (localStorage round-trip)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Brand fonts render visually in SPA | FE-03 | Font rendering is visual; grep confirms declaration but not render | Start `npm run dev`, open browser, inspect font-family in DevTools on `.app` container |
| localStorage recovery restores conversation position | FE-05 | Partial — unit test covers data; UX fidelity (step position restored) requires human check | Answer 3 questions, refresh page, verify stepIndex and answers are restored |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
