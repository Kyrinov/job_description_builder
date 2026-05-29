---
phase: 3
slug: ca-jes-data-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-29
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (already configured from Phase 2) |
| **Quick run command** | `pytest tests/test_ca_ingest.py tests/test_jes_ingest.py tests/test_policy_ingest.py -x -q` |
| **Full suite command** | `pytest -x -q` |
| **Estimated runtime** | ~15 seconds (stubs); ~5–20 min when ingest scripts run LLM calls |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_ca_ingest.py tests/test_jes_ingest.py tests/test_policy_ingest.py -x -q`
- **After every plan wave:** Run `pytest -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds (stubs only; LLM-dependent tests tagged `@pytest.mark.slow`)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 0 | PIPE-02, PIPE-03, CA-01 | — | N/A | stub | `pytest tests/test_ca_ingest.py tests/test_jes_ingest.py tests/test_policy_ingest.py --collect-only -q` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 1 | PIPE-02, CA-01 | T-3-01 | Path traversal blocked for --db-path | unit | `pytest tests/test_ca_ingest.py -x -q` | ❌ W0 | ⬜ pending |
| 3-03-01 | 03 | 1 | PIPE-03 | T-3-01 | Path traversal blocked for --db-path | unit | `pytest tests/test_jes_ingest.py -x -q` | ❌ W0 | ⬜ pending |
| 3-04-01 | 04 | 1 | PIPE-02, PIPE-03 | — | N/A | integration | `pytest tests/test_ca_ingest.py tests/test_jes_ingest.py tests/test_policy_ingest.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ca_ingest.py` — stubs for PIPE-02 and CA-01
- [ ] `tests/test_jes_ingest.py` — stubs for PIPE-03
- [ ] `tests/test_policy_ingest.py` — stubs for policy FTS indexing (Phase 5 prereq)
- [ ] `tests/conftest.py` — add `ca_jes_db` fixture (temp-file DB with CA_JES_SCHEMA_DDL applied)

*Existing `noc_db` fixture in conftest.py is the analog to follow.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LLM extraction produces semantically correct clauses | PIPE-02 | Correctness of extracted text requires human judgement | Query `SELECT * FROM ca_clauses WHERE og_code='EC' LIMIT 5` and confirm clauses are restriction/scope/exclusion text from the CA |
| JES factor degree descriptors match source TXT | PIPE-03 | LLM paraphrase vs. verbatim — requires comparison | Query `SELECT degree_descriptors FROM jes_factors WHERE og_code='EC' AND factor_name LIKE '%Decision%'` and compare D1 text against the source TXT |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
