---
phase: 14
slug: noc-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-04
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.4 + pytest-asyncio 0.24.0 |
| **Config file** | `v2/backend/pyproject.toml` (asyncio_mode = "auto") |
| **Quick run command** | `cd v2/backend && python -m pytest tests/test_noc_pipeline.py -q` |
| **Full suite command** | `cd v2/backend && python -m pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd v2/backend && python -m pytest tests/test_noc_pipeline.py -q`
- **After every plan wave:** Run `cd v2/backend && python -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | NOC-01 | — | N/A | unit | `pytest tests/test_noc_pipeline.py -q` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 1 | API-04 | — | FTS5 uses parameterized MATCH ? | unit | `pytest tests/test_noc_pipeline.py::test_fts5_query_rewriting_strips_stop_words -x` | ❌ W0 | ⬜ pending |
| 14-01-03 | 01 | 1 | NOC-02 | — | N/A | unit | `pytest tests/test_noc_pipeline.py::TestNOCCandidateSchema -x` | ❌ W0 | ⬜ pending |
| 14-02-01 | 02 | 2 | NOC-01 | — | Verbatim guardrail strips fabricated duties | unit | `pytest tests/test_noc_pipeline.py::test_verbatim_guardrail_strips_fabricated -x` | ❌ W0 | ⬜ pending |
| 14-02-02 | 02 | 2 | NOC-01 | — | N/A | integration | `pytest tests/test_noc_pipeline.py::test_pipeline_returns_candidates -x` | ❌ W0 | ⬜ pending |
| 14-03-01 | 03 | 2 | API-04 | T-14-01 | Pydantic min_length=10 rejects short input | integration | `pytest tests/test_noc_pipeline.py::test_api_route_200 -x` | ❌ W0 | ⬜ pending |
| 14-03-02 | 03 | 2 | API-04 | — | N/A | integration | `pytest tests/test_noc_pipeline.py::test_empty_fts_result_raises_422 -x` | ❌ W0 | ⬜ pending |
| 14-04-01 | 04 | 3 | NOC-02 | — | N/A | manual | Browser: NOC confirmation cards render | ❌ manual | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `v2/backend/tests/test_noc_pipeline.py` — stubs for NOC-01, API-04, NOC-02 schema tests
- [ ] `v2/backend/tests/conftest.py` — add `noc_mapping_db` fixture (768-dim synthetic vec data)
- [ ] `v2/backend/requirements.txt` — add sqlite-vec, instructor, ollama (if not present)

*Wave 0 must create all ❌ W0 test stubs before any implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| NOC candidate confirmation cards render in the SPA | NOC-02 | React component requires browser rendering | Run `npm run dev` in `v2/frontend`; trigger NOC map call; verify 3 cards appear with code, title, TEER, and duty matches |
| Selecting a candidate stores NOC code and unblocks next step | NOC-02 | Requires full API↔SPA integration | Confirm a candidate card; verify the conversation advances past the NOC step |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
