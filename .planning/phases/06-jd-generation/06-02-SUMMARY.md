---
phase: 06-jd-generation
plan: 02
subsystem: jd-generation
tags: [wave-1, pydantic, instructor, duty-selection, orphan-check, selection-oracle]

# Dependency graph
requires:
  - phase: 06-01
    provides: "Wave 0 jd_db fixture + test stubs (tests/test_jd_ranking.py) + WorkDescription model fields"
provides:
  - DutySelection Pydantic model (row_id int, rank ge=1, rationale)
  - DutyRankingResult Pydantic model (1-15 selections, required selection_rationale)
  - OrphanFlag Pydantic model (severity Literal[hard, soft], default source_document)
  - OrphanCheckResult Pydantic model (default empty flags list)
  - DUTY_SELECTION_SYSTEM_PROMPT constant (og_name, og_code placeholders)
  - ORPHAN_CHECK_SYSTEM_PROMPT constant (og_code, og_name, og_exclusions, og_inclusions)
  - get_noc_version_info(conn) -> (version_label, content_hash) helper
  - jd_instructor_client module-level singleton (cloud_api_key or ollama fallback)
affects:
  - 06-03 (jd_service + jd_generation router imports from this module)
  - 06-04 (JD wizard UI renders duty cards + orphan check results)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "LLM-as-selection-oracle: Pydantic models enforce integer row_id output; server reconstructs duty text from DB rows after LLM returns IDs"
    - "instructor singleton: construct at module import; settings.cloud_api_key switches between DashScope cloud and local Ollama"
    - "Empty flags = success: OrphanCheckResult.flags defaults to empty list (JD-04 explicit requirement)"

key-files:
  created:
    - app/ai/jd_ranking.py
  modified: []

key-decisions:
  - "Used Literal['hard', 'soft'] for OrphanFlag.severity (Pydantic-enforced, vs free str) — prevents LLM from inventing arbitrary severity labels"
  - "OrphanFlag.source_document defaults to 'TBS OCHRO OG Definitions' — only field with default; reduces prompt pressure on LLM"
  - "DutyRankingResult.selections min_length=1, max_length=15 — guards against LLM returning empty or runaway lists"
  - "get_noc_version_info() returns tuple not dict — caller writes fields directly into ProvenanceTag.source_version"
  - "Singleton pattern identical to og_ranking.py (only rename og_instructor_client → jd_instructor_client) — zero learning curve for Plan 06-03 service code"

patterns-established:
  - "Pattern: Module-level instructor singleton using settings.cloud_api_key ternary — replicate for any new LLM-touching module"
  - "Pattern: Pydantic structured output where LLM returns row IDs and server re-reads DB — non-negotiable for JD-01 verbatim fidelity"
  - "Pattern: Format-placeholder prompts (DUTY_SELECTION_SYSTEM_PROMPT.format(og_name=..., og_code=...)) — caller substitutes confirmed OG context"

requirements-completed: [JD-01, JD-02, JD-04]

# Metrics
duration: 2min
completed: 2026-06-02
---

# Phase 6 Plan 02: Wave 1 — jd_ranking.py Summary

**Pydantic output models (DutySelection, DutyRankingResult, OrphanFlag, OrphanCheckResult), instructor singleton, and prompt constants for the JD generation pipeline — unblocks 14 of 23 previously skipped tests**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-02T16:19:50Z
- **Completed:** 2026-06-02T16:21:47Z
- **Tasks:** 1
- **Files modified:** 1 (created)

## Accomplishments

- Created `app/ai/jd_ranking.py` with all four Pydantic models, both prompt constants, the
  `get_noc_version_info()` helper, and the module-level `jd_instructor_client` singleton
  (exact same pattern as `app/ai/og_ranking.py`; only the variable name changed)
- All 16 tests in `tests/test_jd_ranking.py` now PASS (previously all 14 non-ProvenanceTag
  tests were skipping on `ImportError`; the 2 `TestProvenanceTagConstruction` tests
  already passed because they only depend on `app.models.work_description`)
- Full suite green: 131 passed, 10 skipped (was 117 passed, 24 skipped before this plan;
  net +14 unblocked, -14 skipped)
- The 10 remaining skips are: 9 in `test_jd_generation.py` (waiting on Plan 06-03's
  `app/api/jd_generation.py` and `app/services/jd_service.py`) + 1 in
  `test_og_classification.py::TestOGGate::test_og_gate_enforced` (waiting on
  Plan 06-03 to wire the same router to the gate test)

## Task Commits

Each task was committed atomically:

1. **Task 1: app/ai/jd_ranking.py — Pydantic models + instructor singleton + prompt constants + version helper** - `ce3ac47` (feat)

**Plan metadata:** (will be `docs(06-02): SUMMARY.md for plan 02` after this commit)

_Note: No TDD red/green/refactor split — the test file (06-01) is in Wave 0 and
pre-existed in the skipping state. The "TDD true" flag in the plan means tests must
transition from skipping → passing, which they do in a single feat commit._

## Files Created/Modified

- `app/ai/jd_ranking.py` (new, 197 lines)
  - 4 Pydantic models: `DutySelection`, `DutyRankingResult`, `OrphanFlag`, `OrphanCheckResult`
  - 2 prompt constants: `DUTY_SELECTION_SYSTEM_PROMPT`, `ORPHAN_CHECK_SYSTEM_PROMPT`
  - 1 helper: `get_noc_version_info(conn) -> tuple[str, str]`
  - 1 singleton: `jd_instructor_client = instructor.from_openai(_openai_client, mode=instructor.Mode.JSON)`
  - Singleton decision (cloud vs ollama) based on `settings.cloud_api_key` — identical
    to `og_ranking.py` pattern; ensures one httpx connection pool per process

## Decisions Made

- **Copy og_ranking.py singleton verbatim (only rename `og_instructor_client` →
  `jd_instructor_client`):** Plan 06-03 service code that imports both modules will see
  consistent initialization semantics; the cloud_api_key ternary logic is already
  battle-tested from Phases 4 and 5; no need to invent a new pattern.
- **Empty `flags` list is the success path on orphan check (JD-04 explicit
  requirement):** `OrphanCheckResult.flags: list[OrphanFlag] = Field(default_factory=list)`
  is critical — the route handler in Plan 06-03 must NOT treat an empty result as an error
  and must return HTTP 200 with `{"flags": [], "summary": "..."}`.
- **`Literal["hard", "soft"]` for severity, not free `str`:** Prevents the LLM from
  inventing arbitrary severity labels (e.g., "medium", "critical"); the route handler can
  rely on these exact two values for downstream UI rendering and filtering.
- **`get_noc_version_info()` returns tuple, not dict or Pydantic model:** Plan 06-03
  caller writes fields directly into `ProvenanceTag.source_version` and uses the hash
  for traceability logging; tuple is the minimum-viable shape with the lowest import cost.
- **`source_document` default on `OrphanFlag`:** Only the field with a default in the
  four models — reduces LLM prompt pressure and the LLM rarely needs to override
  "TBS OCHRO OG Definitions" anyway.

## Deviations from Plan

None — plan executed exactly as written. The provided code block in the plan's
`<action>` was copied verbatim into `app/ai/jd_ranking.py` with no additions, removals,
or reformatting.

## Issues Encountered

None.

## Threat Surface

Plan frontmatter threat model (T-06-02-01, T-06-02-02, T-06-02-03) was reviewed and
confirmed all mitigations are present in the implementation:

- **T-06-02-01 (Tampering — row_id type)**: `DutySelection.row_id: int = Field(...)`
  enforces integer output via Pydantic; instructor will retry on ValidationError. ✓
- **T-06-02-02 (Repudiation — rule_violated fabrication)**: `OrphanFlag.rule_violated`
  description requires "verbatim text from og_definitions exclusions or inclusions that
  this duty violates — must be a substring of the provided rules text"; Plan 06-03
  service layer will add the post-check substring guardrail. ✓ (carryover to 06-03)
- **T-06-02-03 (Info Disclosure — cloud_api_key)**: API key loaded from env at module
  import, not logged, not stored. ✓ (accepted risk in plan)

No new threat surface introduced beyond what plan frontmatter identified.

## Next Phase Readiness

- Plan 06-03 (jd_service + jd_generation router) is unblocked. It can now:
  - Import `DutySelection`, `DutyRankingResult`, `OrphanFlag`, `OrphanCheckResult`
  - Use `DUTY_SELECTION_SYSTEM_PROMPT.format(og_name=..., og_code=...)` in duty selection call
  - Use `ORPHAN_CHECK_SYSTEM_PROMPT.format(og_code=..., og_name=..., og_exclusions=..., og_inclusions=...)` in orphan check call
  - Call `get_noc_version_info(conn)` to populate `ProvenanceTag.source_version`
  - Call `await jd_instructor_client.chat.completions.create(...)` for both LLM calls
  - Implement the verbatim fidelity guardrail using the `DutySelection.row_id` to look
    up `noc_elements` rows by primary key
- No blockers. Wave 2 service code can proceed.

---
*Phase: 06-jd-generation*
*Completed: 2026-06-02*

## Self-Check: PASSED

- `app/ai/jd_ranking.py` — 162 lines, exists on disk
- `.planning/phases/06-jd-generation/06-02-SUMMARY.md` — 165 lines, exists on disk
- Commit `ce3ac47` — present in `git log`
- `python -c "from app.ai.jd_ranking import ...; print('OK')"` — exits 0, prints "OK"
- `pytest tests/test_jd_ranking.py -x -q` — 16 passed (no skips)
- `pytest tests/ -x -q` — 131 passed, 10 skipped, 2 warnings
