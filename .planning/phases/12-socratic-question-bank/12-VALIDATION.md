---
phase: 12
slug: socratic-question-bank
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-04
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.4 |
| **Config file** | `v2/backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `cd v2/backend && python -m pytest tests/test_question_bank.py -v` |
| **Full suite command** | `cd v2/backend && python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd v2/backend && python -m pytest tests/test_question_bank.py -v`
- **After every plan wave:** Run `cd v2/backend && python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green (18 existing + new QUES tests)
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 0 | QUES-01, QUES-02, QUES-03 | — | N/A (static data) | unit | `pytest tests/test_question_bank.py -v` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | QUES-01 | — | N/A | unit | `pytest tests/test_question_bank.py::test_question_bank_entry_schema -v` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | QUES-01 | — | N/A | unit | `pytest tests/test_question_bank.py::test_covers_minimum_four_groups -v` | ❌ W0 | ⬜ pending |
| 12-01-04 | 01 | 1 | QUES-02 | — | N/A | unit | `pytest tests/test_question_bank.py::test_no_og_codes_in_user_visible_text -v` | ❌ W0 | ⬜ pending |
| 12-01-05 | 01 | 1 | QUES-03 | — | N/A | unit | `pytest tests/test_question_bank.py::test_phase_slot_and_input_type -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `v2/backend/tests/test_question_bank.py` — stubs for QUES-01, QUES-02, QUES-03 (all tests RED until `QUESTION_BANK` is written)

*Existing infrastructure covers pytest and pyproject.toml — no new install required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | All Phase 12 behaviors are verifiable by automated tests | — |

---

## Security Domain

This phase creates a hardcoded data constant with no user input, no authentication, no network calls, and no persistence. ASVS categories V2–V6 do not apply to a static Python constant. No security concerns for this phase.
