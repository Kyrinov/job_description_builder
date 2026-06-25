---
phase: 11
slug: data-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-04
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.4 |
| **Config file** | `v2/backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `cd v2/backend && python -m pytest tests/test_constants.py -x -q` |
| **Full suite command** | `cd v2/backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd v2/backend && python -m pytest tests/test_constants.py -x -q`
- **After every plan wave:** Run `cd v2/backend && python -m pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green (including the 10 Phase 10 tests)
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 0 | DATA-01, DATA-02 | — | N/A | unit stub | `cd v2/backend && python -m pytest tests/test_constants.py -x -q` | ❌ Wave 0 | ⬜ pending |
| 11-01-02 | 01 | 1 | DATA-01 | — | N/A | unit | `pytest tests/test_constants.py::test_og_levels_ec_has_8_levels -x` | ❌ Wave 0 | ⬜ pending |
| 11-01-03 | 01 | 1 | DATA-01 | — | N/A | unit | `pytest tests/test_constants.py::test_og_levels_it_has_5_levels -x` | ❌ Wave 0 | ⬜ pending |
| 11-01-04 | 01 | 1 | DATA-01 | — | N/A | unit | `pytest tests/test_constants.py::test_og_levels_as_has_8_levels -x` | ❌ Wave 0 | ⬜ pending |
| 11-01-05 | 01 | 1 | DATA-01 | — | N/A | unit | `pytest tests/test_constants.py::test_og_levels_fi_has_4_levels -x` | ❌ Wave 0 | ⬜ pending |
| 11-01-06 | 01 | 1 | DATA-01 | — | N/A | unit | `pytest tests/test_constants.py::test_og_levels_all_groups_are_lists_of_ints -x` | ❌ Wave 0 | ⬜ pending |
| 11-01-07 | 01 | 1 | DATA-01 | — | N/A | unit | `pytest tests/test_constants.py::test_og_levels_no_cs_key -x` | ❌ Wave 0 | ⬜ pending |
| 11-02-01 | 02 | 1 | DATA-02 | — | N/A | unit | `pytest tests/test_constants.py::test_caf_table_all_entries_advisory_flagged -x` | ❌ Wave 0 | ⬜ pending |
| 11-02-02 | 02 | 1 | DATA-02 | — | N/A | unit | `pytest tests/test_constants.py::test_caf_table_og_codes_exist_in_og_levels -x` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_constants.py` — 8 test function stubs (DATA-01 × 6, DATA-02 × 2)
- [ ] `app/data/__init__.py` — empty package marker (required for importability before constants exist)

*Wave 0 must be committed before Wave 1 tasks begin. All 8 tests start RED; they go GREEN when Wave 1 delivers `app/data/constants.py`.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
