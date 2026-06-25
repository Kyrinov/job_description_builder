---
phase: 25
slug: accessible-template
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-16
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.4 + pytest-asyncio 0.24.0 |
| **Config file** | v2/backend/pytest.ini or pyproject.toml |
| **Quick run command** | `cd v2/backend && python -m pytest tests/test_export.py -x` |
| **Full suite command** | `cd v2/backend && python -m pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd v2/backend && python -m pytest tests/test_export.py -x`
- **After every plan wave:** Run `cd v2/backend && python -m pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | ACC-01 | — | N/A | unit | `python scripts/build_accessible_template.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | ACC-02 | — | N/A | unit/integration | `pytest tests/test_export.py -k accessible_effort -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | ACC-03 | — | N/A | integration | `pytest tests/test_export.py -x` | ✅ existing, needs updates | ⬜ pending |
| TBD | TBD | TBD | ACC-04 | — | N/A | integration | `pytest tests/test_export.py -x` | ✅ existing, needs updates | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky — table is finalized by the planner once tasks are defined.*

---

## Wave 0 Requirements

- [ ] `v2/backend/scripts/build_accessible_template.py` — new build script (analog to `build_wd_template.py`), self-verify mode
- [ ] `v2/backend/app/templates/wd_accessible_template.docx` — generated template artifact
- [ ] New/updated test cases in `tests/test_export.py` for Accessible format assertions

---

## Manual-Only Verifications

None identified — content-presence test (ACC-03 success criterion) is fully automatable via python-docx.
