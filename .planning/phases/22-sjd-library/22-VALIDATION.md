---
phase: 22
slug: sjd-library
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-11
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (backend); Vitest/jest (frontend) |
| **Config file** | `v2/backend/pyproject.toml` |
| **Quick run command** | `cd v2/backend && python -m pytest tests/test_sjd.py -x` |
| **Full suite command** | `cd v2/backend && python -m pytest tests/ -x && cd ../../v2/frontend && npm test -- --run` |
| **Estimated runtime** | ~15 seconds (backend), ~20 seconds (frontend) |

---

## Sampling Rate

- **After every task commit:** Run `cd v2/backend && python -m pytest tests/test_sjd.py -x`
- **After every plan wave:** Run full suite (backend + frontend)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 1 | SJD-01 | — | N/A | unit | `pytest tests/test_sjd.py::test_sjd_library_count -x` | ❌ W0 | ⬜ pending |
| 22-01-02 | 01 | 1 | SJD-01 | — | N/A | unit | `pytest tests/test_sjd.py::test_sjd_entry_fields -x` | ❌ W0 | ⬜ pending |
| 22-01-03 | 01 | 1 | SJD-01 | — | N/A | unit | `pytest tests/test_sjd.py::test_og_code_normalization -x` | ❌ W0 | ⬜ pending |
| 22-02-01 | 02 | 1 | SJD-01 | T-22-01 | 404 on unknown sjd_number | integration | `pytest tests/test_sjd.py::test_list_sjds_returns_all -x` | ❌ W0 | ⬜ pending |
| 22-02-02 | 02 | 1 | SJD-01 | — | N/A | integration | `pytest tests/test_sjd.py::test_list_sjds_filter_by_og -x` | ❌ W0 | ⬜ pending |
| 22-02-03 | 02 | 1 | SJD-01 | T-22-01 | 404 on unknown | integration | `pytest tests/test_sjd.py::test_get_sjd_by_number -x` | ❌ W0 | ⬜ pending |
| 22-02-04 | 02 | 1 | SJD-01 | T-22-01 | 404 returned | integration | `pytest tests/test_sjd.py::test_get_sjd_404 -x` | ❌ W0 | ⬜ pending |
| 22-03-01 | 03 | 1 | SJD-01, SJD-02 | — | N/A | integration | `pytest tests/test_sjd.py::test_sjd_start_prefills_wd -x` | ❌ W0 | ⬜ pending |
| 22-03-02 | 03 | 1 | SJD-02 | — | N/A | unit | `pytest tests/test_sjd.py::test_seed_duties_provenance -x` | ❌ W0 | ⬜ pending |
| 22-03-03 | 03 | 1 | SJD-02 | — | N/A | integration | `pytest tests/test_sjd.py::test_manifest_includes_sjd_source -x` | ❌ W0 | ⬜ pending |
| 22-04-01 | 04 | 2 | SJD-02, SJD-03 | — | N/A | manual | — | Manual | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `v2/backend/tests/test_sjd.py` — test stubs for all SJD-01 and SJD-02 automated tests above

*Existing infrastructure covers all other needs (pytest, conftest.py, FastAPI test client).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| "Browse SJDs" action appears at end of Role phase (after all phase-0 questions answered) | SJD-02 | React SPA UI interaction — not covered by backend test client | 1. Open app; answer all Role phase questions; 2. Confirm "Browse SJDs" action/button appears before Work Type phase begins |
| SJD browser filters by OG group | SJD-01 | Frontend filter UI state | 1. Click Browse SJDs; 2. Select OG filter "AS"; 3. Confirm only AS entries appear (3 entries) |
| Selecting SJD pre-fills og in SPA record | SJD-02 | SPA state update from API call | 1. Select DND-EC-58355; 2. Confirm `record.confirmed_og.og_code === "EC"` and `record.og_level === 2` in React DevTools |
| SJD-03 warning toast appears on og change | SJD-03 | Toast is React state — frontend only | 1. Complete sjd-start with AS SJD; 2. Advance to og_confirm step; 3. Change OG to EC; 4. Confirm warning toast appears |
| Toast does NOT fire on og_level change only | SJD-03 | Edge case — og_code unchanged | 1. Complete sjd-start with AS-01 SJD; 2. At og_confirm change only the level (AS-03); 3. Confirm no warning toast |
| SJD provenance tag displayed in document preview | SJD-02 | Visual distinction from NOC duties | 1. After sjd-start, open document preview; 2. Confirm seeded duties show "SJD" provenance badge distinct from "NOC" |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
