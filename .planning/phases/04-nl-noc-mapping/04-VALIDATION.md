---
phase: 4
slug: nl-noc-mapping
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-01
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — `asyncio_mode = "auto"` already set |
| **Quick run command** | `pytest tests/test_noc_ranking.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~30 seconds (unit tests, no Ollama); integration tests require Ollama (~3–5 min) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_noc_ranking.py -x`
- **After every plan wave:** Run `pytest tests/test_noc_mapping.py tests/test_noc_ranking.py -x`
- **Before `/gsd-verify-work`:** `pytest tests/ -x` full suite must be green
- **Max feedback latency:** 30 seconds (unit tests); 300 seconds (integration with Ollama)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 0 | MAP-01 | — | N/A | unit (stubs) | `pytest tests/test_noc_ranking.py --co -q` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 0 | MAP-01 | — | N/A | unit (stubs) | `pytest tests/test_noc_mapping.py --co -q` | ❌ W0 | ⬜ pending |
| 4-01-03 | 01 | 0 | MAP-01 | — | N/A | infra | `python -c "import sqlite_vec; import instructor; import openai"` | ✅ | ⬜ pending |
| 4-01-04 | 01 | 0 | MAP-01 | — | N/A | data | `python scripts/rebuild_noc_vectors.py --verify` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 1 | MAP-02 | — | N/A | unit | `pytest tests/test_noc_ranking.py::test_noc_candidate_schema -x` | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 1 | MAP-02 | — | N/A | unit | `pytest tests/test_noc_ranking.py::test_teer_is_integer -x` | ❌ W0 | ⬜ pending |
| 4-02-03 | 02 | 1 | MAP-01 | — | N/A | unit | `pytest tests/test_noc_ranking.py::test_instructor_client_mode_json -x` | ❌ W0 | ⬜ pending |
| 4-03-01 | 03 | 2 | MAP-01 | T-SQL-inj | FTS5 MATCH uses parameterized query | unit | `pytest tests/test_noc_mapping.py::test_fts5_stage_returns_noc_codes -x` | ❌ W0 | ⬜ pending |
| 4-03-02 | 03 | 2 | MAP-01 | — | N/A | unit | `pytest tests/test_noc_mapping.py::test_stage2_calls_embed_model -x` | ❌ W0 | ⬜ pending |
| 4-03-03 | 03 | 2 | MAP-01 | — | N/A | unit | `pytest tests/test_noc_mapping.py::test_empty_fts_result_raises_422 -x` | ❌ W0 | ⬜ pending |
| 4-03-04 | 03 | 2 | MAP-02 | T-LLM-fab | Fabricated duties stripped before response | unit | `pytest tests/test_noc_mapping.py::test_verbatim_guardrail_strips_fabricated -x` | ❌ W0 | ⬜ pending |
| 4-03-05 | 03 | 2 | MAP-01 | — | N/A | integration | `pytest tests/test_noc_mapping.py::test_pipeline_returns_candidates -x` | ❌ W0 | ⬜ pending |
| 4-03-06 | 03 | 2 | MAP-01 | — | N/A | integration | `pytest tests/test_noc_mapping.py::test_api_route_200 -x` | ❌ W0 | ⬜ pending |
| 4-04-01 | 04 | 3 | MAP-01+02 | — | N/A | integration | `pytest tests/test_noc_mapping.py::test_confirm_noc_updates_wd -x` | ❌ W0 | ⬜ pending |
| 4-04-02 | 04 | 3 | MAP-01 | — | N/A | integration | `pytest tests/ -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_noc_ranking.py` — unit test stubs for Pydantic validators, instructor client mode, TEER int cast, retry logic, guardrail logic
- [ ] `tests/test_noc_mapping.py` — integration test stubs for 3-stage pipeline, FastAPI route, FTS5 empty guardrail, verbatim guardrail, confirm endpoint
- [ ] `tests/conftest.py` update — add `noc_mapping_db` fixture (pre-populated with synthetic NOC data + 768-dim fake vectors; does NOT require Ollama)
- [ ] `scripts/rebuild_noc_vectors.py` — standalone script to rebuild `noc_chunks_vec` as FLOAT[768] using `nomic-embed-text` via Ollama; run before any Phase 4 tests against real DB

*Existing `noc_db` fixture creates the schema but does not populate FTS5 or vec — the `noc_mapping_db` fixture must extend it with synthetic data.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LLM cites verbatim duty statements for a real work description | MAP-02 | End-to-end requires live gemma4:31b; non-deterministic prose | POST `/api/noc/map` with a real DND policy analyst work description; confirm every `matched_duties` item appears verbatim in the DB via `SELECT element_text FROM noc_elements WHERE noc_code=? AND instr(element_text, ?)>0` |
| HTMX swap renders results correctly in browser | MAP-01 | UI rendering not testable in pytest | Navigate to wizard NOC step; submit a work description; confirm results cards render with NOC code, title, TEER, and duty list |
| Confirm button updates WorkDescription.confirmed_noc | MAP-01 | Requires browser interaction | Click Confirm on a candidate; reload page; confirm `confirmed_noc` is persisted |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (unit) / 300s (integration)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
