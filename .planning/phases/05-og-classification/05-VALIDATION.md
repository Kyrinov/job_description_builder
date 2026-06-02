---
phase: 5
slug: og-classification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-02
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini / pyproject.toml |
| **Quick run command** | `python -m pytest tests/test_og_classification.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_og_classification.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 0 | CLASS-01 | — | N/A | stub | `python -m pytest tests/test_og_classification.py -x -q` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 1 | CLASS-01 | — | OG definitions carry ProvenanceTag with source_type="TBS_OG_DEF" | unit | `python -m pytest tests/test_og_classification.py::test_og_candidate_provenance -x -q` | ✅ | ⬜ pending |
| 5-03-01 | 03 | 2 | CLASS-01 | — | Top 3 OG candidates returned with cited definitions | unit | `python -m pytest tests/test_og_classification.py::test_classify_og_returns_candidates -x -q` | ✅ | ⬜ pending |
| 5-03-02 | 03 | 2 | CLASS-02 | — | JD generation endpoint returns 422 without confirmed OG | unit | `python -m pytest tests/test_og_classification.py::test_og_gate_enforced -x -q` | ✅ | ⬜ pending |
| 5-03-03 | 03 | 2 | CLASS-03 | — | AS vs EC block present when policy duties detected | unit | `python -m pytest tests/test_og_classification.py::test_as_ec_disambiguation -x -q` | ✅ | ⬜ pending |
| 5-04-01 | 04 | 3 | CLASS-01 | — | HTMX partial renders OG candidates | manual | `GET /api/og/classify` HTMX response | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_og_classification.py` — stubs for CLASS-01, CLASS-02, CLASS-03
- [ ] `tests/conftest.py` — og_db fixture with og_definitions table populated

*Existing pytest infrastructure from Phases 1–4 covers framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| HTMX OG candidate cards render side-by-side with cited inclusions/exclusions | CLASS-01 | Browser rendering; HTMX partial response | Run app, submit confirmed NOC match, verify 3 OG cards display with verbatim citations |
| AS vs EC disambiguation block displays before advisor confirms OG | CLASS-03 | Browser rendering; policy keyword detection flow | Submit work description with "policy" keyword, verify disambiguation block appears |
| Advisor can confirm OG and level; confirmed classification stored | CLASS-02 | End-to-end wizard flow | Confirm OG via UI, verify WorkDescription.confirmed_og and confirmed_level set in DB |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
