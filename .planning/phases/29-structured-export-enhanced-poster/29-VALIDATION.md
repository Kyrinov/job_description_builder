---
phase: 29
slug: structured-export-enhanced-poster
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-24
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `v2/backend/` (pytest discovers from there) |
| **Quick run command** | `cd /home/charles/job_description_builder && python -m pytest v2/backend/tests/test_export.py -x -q` |
| **Full suite command** | `cd /home/charles/job_description_builder && python -m pytest v2/backend/tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest v2/backend/tests/test_export.py -x -q`
- **After every plan wave:** Run `python -m pytest v2/backend/tests/ -x -q` (179 existing must stay GREEN)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 29-01-01 | 01 | 0 | SEXP-01 | — | N/A | unit | `pytest tests/test_export.py::test_export_json_returns_all_seven_keys -x` | ❌ Wave 0 | ⬜ pending |
| 29-01-02 | 01 | 0 | SEXP-01 | — | N/A | unit | `pytest tests/test_export.py::test_export_json_metadata_and_provenance -x` | ❌ Wave 0 | ⬜ pending |
| 29-01-03 | 01 | 0 | SEXP-02 | — | N/A | unit | `pytest tests/test_export.py::test_export_csv_utf8_bom_one_row_per_duty -x` | ❌ Wave 0 | ⬜ pending |
| 29-01-04 | 01 | 0 | SEXP-03 | — | N/A | frontend | `npm test -- --testPathPattern conversation` | ❌ Wave 0 | ⬜ pending |
| 29-01-05 | 01 | 0 | SEXP-01/02 | — | Manager-track returns 200 not 409 | integration | `pytest tests/test_export.py::test_export_json_manager_no_409 -x` | ❌ Wave 0 | ⬜ pending |
| 29-01-06 | 01 | 0 | POST-01 | — | N/A | integration | `pytest tests/test_export.py::test_poster_org_context_section -x` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `v2/backend/tests/test_export.py` — 5 RED stubs: `test_export_json_returns_all_seven_keys`, `test_export_json_metadata_and_provenance`, `test_export_csv_utf8_bom_one_row_per_duty`, `test_export_json_manager_no_409`, `test_poster_org_context_section`
- [ ] Frontend conversation test — 2 RED stubs: Export JSON button renders, Export CSV button renders

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CSV opens in Excel without encoding error | SEXP-02 | Binary BOM verification is hard to automate reliably across platforms | Download CSV, open in Excel on Windows/Mac, confirm no "?" or garbled characters |
| JSON/CSV download triggers file-save in browser | SEXP-03 | Browser file-download dialog cannot be tested in jest/vitest | Click Export JSON and Export CSV in the running SPA; confirm browser downloads the file |
| Poster DOCX shows "About the Organization" section | POST-01 | DOCX visual rendering requires manual inspection | Export poster for a WD with org_context; open DOCX; verify section heading and text appear |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
