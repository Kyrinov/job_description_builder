---
phase: 6
slug: jd-generation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-02
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_jd_ranking.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds (unit); ~60 seconds (full suite, no LLM) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_jd_ranking.py -x`
- **After every plan wave:** Run `pytest tests/test_jd_generation.py tests/test_jd_ranking.py -x`
- **Before `/gsd-verify-work`:** Full suite must be green (`pytest tests/ -x`)
- **Max feedback latency:** 15 seconds (unit), 60 seconds (full suite)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 0 | JD-01 | Row ID injection | Guardrail drops IDs not in candidate set | unit | `pytest tests/test_jd_ranking.py::test_guardrail_drops_invalid_row_id -x` | ❌ W0 | ⬜ pending |
| 6-01-02 | 01 | 0 | JD-01 | Stage skip | POST /api/jd/generate-duties returns 422 if stage != og_classified | integration | `pytest tests/test_jd_generation.py::test_generate_duties_stage_gate -x` | ❌ W0 | ⬜ pending |
| 6-01-03 | 01 | 0 | CLASS-02 gate | Stage skip | JD endpoint returns 422 without og_classified stage | integration | `pytest tests/test_og_classification.py::TestOGGate::test_og_gate_enforced -x` | ✅ (skipped) | ⬜ pending |
| 6-01-04 | 01 | 0 | JD-02 | — | ProvenanceTag fields: source_type=NOC, source_id=noc_code, source_version=NOC 2021 v1.0 | unit | `pytest tests/test_jd_ranking.py::test_provenance_tag_fields -x` | ❌ W0 | ⬜ pending |
| 6-01-05 | 01 | 0 | JD-03 | — | Advisor-added duty tagged ADVISOR in advisor_additions, not draft_duties | integration | `pytest tests/test_jd_generation.py::test_advisor_duty_tagged_correctly -x` | ❌ W0 | ⬜ pending |
| 6-01-06 | 01 | 0 | JD-03 | advisor_additions overwrite | Advisor duties preserved across re-generate call | integration | `pytest tests/test_jd_generation.py::test_advisor_duty_preserved_on_regenerate -x` | ❌ W0 | ⬜ pending |
| 6-01-07 | 01 | 0 | JD-04 | LLM fabrication in flags | Orphan check with clean duties returns HTTP 200 with empty flags | integration | `pytest tests/test_jd_generation.py::test_orphan_check_clean_returns_empty_list -x` | ❌ W0 | ⬜ pending |
| 6-01-08 | 01 | 0 | JD-04 | — | OrphanFlag cites rule_violated, source_document, source_section | unit | `pytest tests/test_jd_ranking.py::test_orphan_flag_cites_source -x` | ❌ W0 | ⬜ pending |
| 6-01-09 | 01 | 0 | JD-01+02 | — | ProvenanceTags intact after WD round-trip through SQLite | integration | `pytest tests/test_jd_generation.py::test_wd_round_trip_provenance -x` | ❌ W0 | ⬜ pending |
| 6-01-10 | 01 | 0 | JD-01+JD-02+JD-03 | — | stage="jd_drafted" set after confirm-duties | integration | `pytest tests/test_jd_generation.py::test_confirm_duties_sets_stage -x` | ❌ W0 | ⬜ pending |
| 6-02-01 | 02 | 1 | JD-01 | LLM text echo | DutyRankingResult.selections all have integer row_ids; Pydantic validates | unit | `pytest tests/test_jd_ranking.py -x` | ❌ W0 | ⬜ pending |
| 6-03-01 | 03 | 2 | JD-01 | — | generate_duties() returns duties all matching noc_elements.element_text | integration | `pytest tests/test_jd_generation.py::test_generate_duties_all_verbatim -x` | ❌ W0 | ⬜ pending |
| 6-04-01 | 04 | 3 | JD-01+02+03+04 | — | Full suite green: 130+ passing, 0 skipped | integration | `pytest tests/ -x` | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_jd_ranking.py` — unit stubs for DutyRankingResult, DutySelection, OrphanFlag, OrphanCheckResult Pydantic models; guardrail logic; PE inclusions fallback
- [ ] `tests/test_jd_generation.py` — integration stubs for generate_duties() pipeline + FastAPI routes + advisor addition + orphan check + confirm-duties endpoints
- [ ] `tests/conftest.py` update — add `jd_db` fixture (pre-populated noc_elements for NOC 21232 with 5 synthetic "Main duties" rows; og_definitions row for EC/IT/PE; no Ollama required)
- [ ] `templates/partials/og_confirmed.html` update — activate disabled "Continue to JD Generation" button
- [ ] `tests/test_og_classification.py::TestOGGate::test_og_gate_enforced` — remove `pytest.skip()`, implement real gate test against `POST /api/jd/generate-duties`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| HTMX duty card rendering with ProvenanceTag tooltip | JD-02 | Visual rendering requires browser | Start uvicorn; complete NOC + OG steps; confirm duty cards show source citation tooltip; verify advisor-added duty has distinct visual indicator |
| Orphan flag display in UI | JD-04 | Visual rendering requires browser | From duty draft step, click "Check for orphan statements"; verify flags render with rule_violated text; verify empty result renders "No issues found" |
| End-to-end wizard flow from OG confirm → duty draft → orphan check → confirm | JD-01 to JD-04 | Full wizard state machine requires browser | Complete wizard from work description input through to duty confirmation |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
