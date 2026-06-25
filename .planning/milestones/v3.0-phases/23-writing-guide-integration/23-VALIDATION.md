---
phase: 23
slug: writing-guide-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-15
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), vitest (frontend) |
| **Config file** | `v2/backend/pytest.ini` (existing) |
| **Quick run command** | `cd v2/backend && python -m pytest tests/test_writing_guide.py -x` |
| **Full suite command** | `cd v2/backend && python -m pytest && cd ../frontend && npm test` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd v2/backend && python -m pytest tests/test_writing_guide.py -x`
- **After every plan wave:** Run `cd v2/backend && python -m pytest && cd ../frontend && npm test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 0 | WG-01 | — | N/A | unit | `pytest tests/test_writing_guide.py -x` | ❌ W0 | ⬜ pending |
| 23-02-01 | 02 | 1 | WG-01 | ReDoS | duty text bounded by 20-duty cap | unit | `pytest tests/test_writing_guide.py::test_word_count_violation -x` | ❌ W0 | ⬜ pending |
| 23-02-02 | 02 | 1 | WG-01 | ReDoS | simple non-backtracking regex patterns | unit | `pytest tests/test_writing_guide.py::test_passive_opener -x` | ❌ W0 | ⬜ pending |
| 23-02-03 | 02 | 1 | WG-01 | ReDoS | simple non-backtracking regex patterns | unit | `pytest tests/test_writing_guide.py::test_non_verb_opener -x` | ❌ W0 | ⬜ pending |
| 23-02-04 | 02 | 1 | WG-01 | — | N/A | unit | `pytest tests/test_writing_guide.py::test_duplicate_duty -x` | ❌ W0 | ⬜ pending |
| 23-02-05 | 02 | 1 | WG-01 | — | <15% of SJD corpus flagged | unit | `pytest tests/test_writing_guide.py::test_calibration_sjd_corpus -x` | ❌ W0 | ⬜ pending |
| 23-03-01 | 03 | 2 | WG-02 | path traversal | wd_id UUID lookup against DB — no filesystem path | integration | `pytest tests/test_writing_guide.py::test_validate_duties_endpoint -x` | ❌ W0 | ⬜ pending |
| 23-03-02 | 03 | 2 | WG-02 | — | 404 on unknown wd_id | integration | `pytest tests/test_writing_guide.py::test_validate_duties_404 -x` | ❌ W0 | ⬜ pending |
| 23-04-01 | 04 | 3 | WG-03 | — | N/A | unit | `pytest tests/test_writing_guide.py::test_client_service_results_step -x` | ❌ W0 | ⬜ pending |
| 23-05-01 | 05 | 3 | WG-04 | — | N/A | unit | `pytest tests/test_writing_guide.py::test_og_definitions_coverage -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `v2/backend/tests/test_writing_guide.py` — stubs for WG-01, WG-02, WG-03, WG-04 (all 9 test functions RED at Wave 0)
- [ ] `v2/backend/app/services/duty_validator.py` — stub with `validate_duties()` signature only

*Wave 0 stubs must be RED (imports succeed, assertions fail) before any implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `.duty-hint` warnings render inline during duty entry | WG-02 | Frontend visual rendering not covered by vitest | Open WD in duty phase, enter a duty with <8 words, verify `.duty-hint` element appears without blocking submission |
| Per-step OG tip renders during duty entry | WG-04 | Frontend visual rendering | Confirm OG group, navigate to duty step, verify tip text matches OG_DEFINITIONS definition for that group |
| Client Service Results question renders in correct position | WG-03 | Conversation flow ordering | Run through conversation to duty phase, verify "Client Service Results" question appears before Key Activities duties |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
