---
phase: 06-jd-generation
verified: 2026-06-02
status: passed
score: 31/31 must-haves verified
overrides_applied: 0
overrides: []
re_verification:
  previous_status: null
  previous_score: null
  gaps_closed: []
  gaps_remaining: []
  regressions: []
requirements:
  JD-01: passed
  JD-02: passed
  JD-03: passed
  JD-04: passed
human_verification:
  - "All 12 wizard visual/functional checkpoints approved by advisor on 2026-06-02 (per 06-04 SUMMARY)"
---

# Phase 6: JD Generation — Verification Report

**Phase Goal:** With a confirmed NOC match and OG classification, the system drafts key duties by selecting verbatim text from NOC profile records in the database; every duty carries a structured ProvenanceTag; advisor-added content that has no source record is tagged distinctly; after drafting, an orphan statement check flags any duty that contradicts the established functional authority for the confirmed OG; the WD is persisted to SQLite after each state transition.

**Verified:** 2026-06-02
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Phase 6 success criteria)

| #   | Truth                                                                                                                                                              | Status     | Evidence                                                                                                                                                                                                                       |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | `POST /generate-duties` returns verbatim NOC duty text — no free-form LLM duty text appears as a duty                                                              | ✓ VERIFIED | `app/services/jd_service.py:75-220` — LLM returns only `DutySelection.row_id` integers (`app/ai/jd_ranking.py:26`); `generate_duties()` reconstructs duty text from `noc_elements.element_text` via `candidate_map` guardrail (lines 122, 174-183) |
| 2   | Every duty carries a structured ProvenanceTag with source type, NOC code, section (element_type), statement text, and source version                              | ✓ VERIFIED | `app/services/jd_service.py:41-55` — `_build_duty_from_row()` builds `ProvenanceTag(source_type="NOC", source_id=noc_code, source_version=noc_version, retrieved_date=…)`; `element_type="Main duties"` is the section in `WHERE` (line 110) |
| 3   | Advisor-added content tagged `source_type='ADVISOR'` in data model; visually distinguished in UI                                                                   | ✓ VERIFIED | Data: `app/services/jd_service.py:58-72` — `_build_advisor_duty()` builds tag with `source_type="ADVISOR"`, `source_id="advisor-input"`, `source_version="advisor-added"`. UI: `templates/partials/jd_duties.html:8-14` — `.duty-advisor-tag` badge "Advisor-added — not from authoritative source". CSS: `app/static/css/main.css` — `.duty-card--advisor` amber border, `.duty-advisor-tag` amber chip (15 CSS class matches total) |
| 4   | After duty confirmation, the WorkDescription record is persisted to SQLite with all ProvenanceTags intact                                                          | ✓ VERIFIED | `app/services/jd_service.py:202, 368, 401` — `save_work_description(conn, updated_wd)` called in `generate_duties()`, `add_advisor_duty()`, and `confirm_duties()` (after each state transition). `confirm_duties()` at line 400-401 sets `stage="jd_drafted"` and persists the full WD including all `draft_duties[*].provenance` and `advisor_additions[*].provenance` |
| 5   | `POST /check-orphan-statements` returns flagged duties with rule text; clean result returns empty flags (HTTP 200, not error)                                     | ✓ VERIFIED | `app/services/jd_service.py:223-337` — `check_orphan_statements()` loads duties, calls LLM, verifies each `flag.rule_violated` is a substring of `og_full_text` (lines 322-329 fabrication guardrail). Empty flags returns `OrphanCheckResult(flags=[], summary="…")` (lines 254-258, 272-276). API: `app/api/jd_generation.py:68-96` — returns 200 with `{"flags": [], "summary": "…"}` (no HTTP error). UI: `templates/partials/jd_orphan_results.html:23-30` — clean message "All duties are consistent with the confirmed occupational group." |

**Score:** 5/5 roadmap success criteria verified

### Must-Haves Verified (across all 4 PLANs)

**Plan 06-01 (Wave 0 foundation)** — 6/6 truths verified

| Truth                                                                                                                                 | Evidence                                                                                                  |
| ------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `tests/test_jd_ranking.py` exists with unit stubs for DutyRankingResult, DutySelection, OrphanFlag, OrphanCheckResult + guardrail    | `tests/test_jd_ranking.py:1-229` (229 lines, 16 test functions; 16 PASSED)                                |
| `tests/test_jd_generation.py` exists with integration stubs for 4 JD routes and advisor preservation                                 | `tests/test_jd_generation.py:1-309` (309 lines, 8 test functions; 8 PASSED)                               |
| `jd_db` fixture in `conftest.py` pre-populates 5 `noc_elements` rows for NOC 21232 and an EC `og_definitions` row                     | `tests/conftest.py` — `def jd_db` fixture present                                                          |
| `og_confirmed.html` "Continue to JD Generation" button is active with HTMX `hx-get="/wizard/jd"`                                      | `templates/partials/og_confirmed.html:858-864` (PLAN 06-01 spec) — present in live file                   |
| `test_og_classification.py::TestOGGate::test_og_gate_enforced` no longer contains `pytest.skip()`; calls POST /api/jd/generate-duties and asserts HTTP 422 | `pytest tests/test_og_classification.py::TestOGGate -v` → 1 PASSED                                       |
| `pytest tests/ -x` exits 0 (full suite green; new stubs skip on ImportError)                                                          | Full suite: 141 passed, 0 skipped, 2 warnings                                                             |

**Plan 06-02 (Pydantic models + instructor singleton)** — 8/8 truths verified

| Truth                                                                                                          | Evidence                                                                       |
| -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `DutySelection` enforces integer `row_id` and `rank >= 1` via Pydantic                                         | `app/ai/jd_ranking.py:23-35` — `row_id: int`, `rank: int = Field(ge=1)`        |
| `DutyRankingResult` holds 1-15 selections and required `selection_rationale` string                           | `app/ai/jd_ranking.py:38-52` — `min_length=1, max_length=15`                   |
| `OrphanFlag` carries `duty_text`, `rule_violated`, `source_document`, `source_section`, `severity`             | `app/ai/jd_ranking.py:55-79` — all 5 fields present with Literal["hard","soft"] |
| `OrphanCheckResult` with empty flags is valid                                                                 | `app/ai/jd_ranking.py:82-94` — `default_factory=list`                          |
| `jd_instructor_client` module-level singleton follows `og_ranking.py` pattern                                  | `app/ai/jd_ranking.py:151-162` — exact pattern match                           |
| `DUTY_SELECTION_SYSTEM_PROMPT` and `ORPHAN_CHECK_SYSTEM_PROMPT` constants exist                                | `app/ai/jd_ranking.py:97-129` — both present with format placeholders          |
| `get_noc_version_info()` helper returns `(version_label, content_hash)` tuple                                  | `app/ai/jd_ranking.py:132-148` — function defined with correct signature       |
| `pytest tests/test_jd_ranking.py -x` exits 0 with all stubs passing (not skipping)                             | 16 PASSED, 0 skipped                                                           |

**Plan 06-03 (Service + router + main.py)** — 10/10 truths verified

| Truth                                                                                                  | Evidence                                                                                          |
| ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| POST `/api/jd/generate-duties` returns 422 if stage != `'og_classified'`                               | `app/services/jd_service.py:94-97` raises ValueError; `app/api/jd_generation.py:50-53` returns 422 |
| POST `/api/jd/generate-duties` returns duties where every text is verbatim from `noc_elements.element_text` | `app/services/jd_service.py:46-55, 174-183` — text built from `row["element_text"]` only         |
| POST `/api/jd/generate-duties` preserves existing `advisor_additions` on re-generate                   | `app/services/jd_service.py:192, 198` — `existing_advisor_additions` saved                       |
| POST `/api/jd/add-advisor-duty` adds duty to `advisor_additions` with `source_type='ADVISOR'`          | `app/services/jd_service.py:58-72, 365-368`                                                      |
| POST `/api/jd/check-orphan-statements` accepts stage `'og_classified'` or `'jd_drafted'`               | `app/services/jd_service.py:242-246`                                                             |
| POST `/api/jd/check-orphan-statements` returns HTTP 200 with `flags=[]` for clean duties              | `app/services/jd_service.py:254-258, 272-276`; `app/api/jd_generation.py:68-96` (200 path)       |
| POST `/api/jd/confirm-duties` sets `stage='jd_drafted'` and saves WD to SQLite                          | `app/services/jd_service.py:399-401` — sets stage and calls `save_work_description`               |
| GET `/wizard/jd` renders `step_jd.html` (Jinja2 TemplateNotFound does not raise)                       | `app/main.py:135-149`; `templates/wizard/step_jd.html` exists                                    |
| `jd_generation` router registered in `app/main.py`                                                     | `app/main.py:25` (import), `app/main.py:107` (`include_router`)                                  |
| CLASS-02 gate test passes (not skips): `pytest tests/test_og_classification.py::TestOGGate::test_og_gate_enforced -x` exits 0 | PASSED                                                                                            |

**Plan 06-04 (Templates + CSS + human verify)** — 7/7 truths verified

| Truth                                                                                                                       | Evidence                                                                                                |
| --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `step_jd.html` extends `base.html` and contains the "Generate Duties" HTMX form targeting `#jd-duties`                       | `templates/wizard/step_jd.html:1-22` — extends base.html, `hx-post="/api/jd/generate-duties"` form      |
| `jd_duties.html` renders each duty as a `.duty-card` with source citation; advisor duties have `.duty-advisor-tag` visual | `templates/partials/jd_duties.html:6-23`                                                                |
| `jd_orphan_results.html` renders flag list when flags present; renders "All duties are consistent" when flags empty        | `templates/partials/jd_orphan_results.html:5-30`                                                        |
| `jd_confirmed.html` renders confirmation success state with disabled "Continue to JES Scoring" CTA                          | `templates/partials/jd_confirmed.html:1-8`                                                              |
| CSS layer 9 appended to `main.css` with `.duty-card`, `.duty-advisor-tag`, `.orphan-flag` classes                            | 15 matches for these class names in `app/static/css/main.css`                                           |
| All Jinja2 templates render without TemplateNotFound errors                                                                 | Smoke test: 6/6 scenarios PASS (1473, 2340, 2353, 271, 765, 372 chars)                                  |
| `pytest tests/ -x` exits 0 (141+ passing, 0 skipped)                                                                        | 141 passed, 0 skipped, 2 warnings                                                                      |

**Total score: 31/31 must-haves verified across 4 PLANs**

### Required Artifacts (Three-Level Verification)

| Artifact                                    | Exists | Substantive | Wired   | Final Status |
| ------------------------------------------- | ------ | ----------- | ------- | ------------ |
| `app/ai/jd_ranking.py`                      | ✓      | ✓ (162 lines, 4 Pydantic models + 2 prompts + helper + singleton) | ✓ Imported by `app/services/jd_service.py:22-29` | ✓ VERIFIED    |
| `app/services/jd_service.py`                | ✓      | ✓ (410 lines, 4 async pipeline functions) | ✓ Imported by `app/api/jd_generation.py:23-28` | ✓ VERIFIED    |
| `app/api/jd_generation.py`                  | ✓      | ✓ (182 lines, 4 POST routes with stage gates) | ✓ Registered in `app/main.py:25, 107` | ✓ VERIFIED    |
| `templates/wizard/step_jd.html`             | ✓      | ✓ (22 lines, HTMX form) | ✓ Rendered by `app/main.py:135-149` GET /wizard/jd | ✓ VERIFIED    |
| `templates/partials/jd_duties.html`         | ✓      | ✓ (84 lines, duty cards + advisor tag + 3 forms) | ✓ Rendered by `app/api/jd_generation.py:55-65, 143-151` | ✓ VERIFIED    |
| `templates/partials/jd_orphan_results.html` | ✓      | ✓ (32 lines, flag list + clean message) | ✓ Rendered by `app/api/jd_generation.py:86-95` | ✓ VERIFIED    |
| `templates/partials/jd_confirmed.html`      | ✓      | ✓ (8 lines, success state) | ✓ Rendered by `app/api/jd_generation.py:172-181` | ✓ VERIFIED    |
| `app/static/css/main.css` (Phase 6 layer 9) | ✓      | ✓ (200 lines appended) | ✓ Loaded via `/static/main.css` mount in `app/main.py:112` | ✓ VERIFIED    |

### Key Link Verification

| From                                      | To                                          | Via                                                                                  | Status   | Details                                                                                          |
| ----------------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------ |
| POST `/api/jd/generate-duties`            | `jd_service.generate_duties()`              | `await generate_duties(wd_id=wd_id, db_path=settings.db_path)`                       | ✓ WIRED  | `app/api/jd_generation.py:48` → `app/services/jd_service.py:75`                                |
| `generate_duties()`                       | `noc_elements` (Main duties)                | `asyncio.to_thread` + `conn.execute("SELECT id, element_text, source_hash FROM noc_elements WHERE noc_code = ? AND element_type = 'Main duties'")` | ✓ WIRED  | `app/services/jd_service.py:107-114`                                                              |
| `generate_duties()`                       | `candidate_map` guardrail                   | `candidate_map = {row["id"]: row for row in candidate_rows}` + filter at line 176   | ✓ WIRED  | `app/services/jd_service.py:122, 174-183`                                                          |
| `check_orphan_statements()`               | `og_definitions` (inclusions fallback)      | `og_inclusions = og_row["inclusions"] or og_row["definition"] or ""`                 | ✓ WIRED  | `app/services/jd_service.py:280`                                                                  |
| `check_orphan_statements()`               | `og_full_text` fabrication guardrail        | `if flag.rule_violated and flag.rule_violated in og_full_text`                       | ✓ WIRED  | `app/services/jd_service.py:322-329`                                                              |
| `add_advisor_duty()`                      | `advisor_additions` persistence             | `save_work_description(conn, updated_wd)`                                            | ✓ WIRED  | `app/services/jd_service.py:368`                                                                  |
| `confirm_duties()`                        | `stage="jd_drafted"` + SQLite persistence   | `model_copy(update={"stage": "jd_drafted"})` + `save_work_description`               | ✓ WIRED  | `app/services/jd_service.py:400-401`                                                              |
| `step_jd.html` HTMX form                  | POST `/api/jd/generate-duties`              | `hx-post="/api/jd/generate-duties"`                                                  | ✓ WIRED  | `templates/wizard/step_jd.html:10-14`                                                             |
| `jd_duties.html` advisor duty             | `.duty-advisor-tag` CSS class               | Jinja2 conditional on `source_type == 'ADVISOR'`                                       | ✓ WIRED  | `templates/partials/jd_duties.html:8-14`                                                          |
| `jd_duties.html` confirm form             | POST `/api/jd/confirm-duties`               | `hx-post="/api/jd/confirm-duties"`                                                   | ✓ WIRED  | `templates/partials/jd_duties.html:70-75`                                                         |
| `jd_orphan_results.html` empty flags      | "All duties are consistent" message         | Jinja2 `{% if flags %}{% else %}` branch                                            | ✓ WIRED  | `templates/partials/jd_orphan_results.html:23-30`                                                  |
| `app/main.py`                             | `jd_generation.router`                      | `app.include_router(jd_generation.router)`                                            | ✓ WIRED  | `app/main.py:107`                                                                                 |

### Data-Flow Trace (Level 4)

| Artifact                  | Data Variable      | Source                                       | Produces Real Data | Status  |
| ------------------------- | ------------------ | -------------------------------------------- | ------------------ | ------- |
| `generate_duties()` output | duty text         | `noc_elements.element_text` (NOC profile)    | ✓ Yes              | ✓ FLOWING — text is reconstructed from DB rows, never LLM text |
| `DraftDuty.provenance.source_version` | version label | `source_documents.version_label` via `get_noc_version_info()` | ✓ Yes | ✓ FLOWING — `app/ai/jd_ranking.py:132-148` queries source_documents |
| `add_advisor_duty()` output | duty text        | advisor form input                           | ✓ Yes              | ✓ FLOWING — `duty_text.strip()` truncated to 500 chars, stored in DB |
| `OrphanFlag.rule_violated` | rule text         | `og_definitions` (definition + inclusions + exclusions) | ✓ Yes (verified) | ✓ FLOWING — `app/services/jd_service.py:322-329` substring guardrail drops fabricated rules |

### Behavioral Spot-Checks

| Behavior                                                                 | Command                                                                                                | Result                              | Status   |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ | ----------------------------------- | -------- |
| All Phase 6 modules import                                               | `python -c "from app.services.jd_service import ...; from app.api.jd_generation import router; print('All imports OK')"` | "All imports OK" + "jd_instructor_client: True" | ✓ PASS    |
| `jd_instructor_client` is non-None                                        | Same command above                                                                                     | True                                | ✓ PASS    |
| All 4 Jinja2 templates render in all 6 scenarios (smoke test)            | `python3 -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader(['templates', 'app/templates'])); [env.get_template(t).render(**c) for t, c in tests]"` | 6/6 templates render                | ✓ PASS    |
| Full test suite green                                                    | `python -m pytest tests/ -x -q`                                                                        | 141 passed, 0 skipped, 2 warnings    | ✓ PASS    |
| Phase 6 specific tests                                                   | `python -m pytest tests/test_jd_ranking.py tests/test_jd_generation.py tests/test_og_classification.py::TestOGGate -v` | 26/26 PASSED                         | ✓ PASS    |
| CSS layer 9 class definitions present                                    | `grep -c "duty-card\|duty-advisor-tag\|orphan-flag\|jd-confirmed-banner" app/static/css/main.css`      | 15 matches                           | ✓ PASS    |
| `wd_store.save_work_description` called in jd_service                    | `grep "save_work_description" app/services/jd_service.py`                                              | 4 matches (1 import + 3 calls)       | ✓ PASS    |
| Router registered in main.py                                             | `grep "jd_generation\|wizard/jd" app/main.py`                                                          | 3 matches (import, include_router, GET) | ✓ PASS    |

### Requirements Traceability

| Requirement | Status | Code Citation                                                                                                                                                                                                                                                                                                                          |
| ----------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **JD-01** (verbatim NOC duty text)  | passed  | `app/services/jd_service.py:75-220` — `generate_duties()` 3-step pipeline: (1) loads `noc_elements` rows for confirmed NOC, (2) LLM returns only `DutySelection.row_id` integers, (3) `candidate_map` guardrail drops LLM row_ids not in pre-loaded set; final `DraftDuty.text` is built from `row["element_text"]` only (line 47) |
| **JD-02** (ProvenanceTag on every duty) | passed  | `app/services/jd_service.py:41-55` (`_build_duty_from_row` — NOC tag) and `58-72` (`_build_advisor_duty` — ADVISOR tag) both construct `ProvenanceTag` with all required fields: `source_type`, `source_id`, `source_version`, `retrieved_date`. `DutySelection.row_id` → `noc_elements.id` → `DraftDuty.id` linkage preserved           |
| **JD-03** (ADVISOR tag distinct)     | passed  | Data: `app/services/jd_service.py:58-72` — `source_type="ADVISOR"`, `source_id="advisor-input"`, `source_version="advisor-added"`. UI: `templates/partials/jd_duties.html:8-14` — `.duty-card--advisor` modifier + `.duty-advisor-tag` badge with "Advisor-added — not from authoritative source" text. CSS: `app/static/css/main.css` — amber border, amber chip |
| **JD-04** (orphan check + empty = clean) | passed  | `app/services/jd_service.py:223-337` — `check_orphan_statements()` returns `OrphanCheckResult(flags=[], summary=...)` for clean duties (lines 254-258, 272-276). Fabrication guardrail: `if flag.rule_violated and flag.rule_violated in og_full_text` (line 323). UI: `templates/partials/jd_orphan_results.html:23-30` — clean state when flags empty. API: `app/api/jd_generation.py:68-96` — 200 status, no HTTP error |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (none) | —    | —       | —        | —      |

No anti-patterns detected. Specifically verified:
- No TODO/FIXME/placeholder comments in any Phase 6 file
- No empty implementations (`return null`, `return []`, `return {}`) in any route handler
- No hardcoded empty data at call sites (DutySelection is Pydantic-validated; OrphanFlag is Pydantic-validated with Literal severity)
- No static JSON returns with no DB query (all endpoints hit the DB or LLM)
- No console.log-only implementations

### Human Verification

| Item                                                              | Result                                                    |
| ----------------------------------------------------------------- | --------------------------------------------------------- |
| All 12 wizard visual/functional checkpoints (per 06-04 SUMMARY)    | ✓ APPROVED by advisor on 2026-06-02                       |
| Duty cards render with NOC source citation                        | ✓ (verified in browser per 06-04 SUMMARY)                  |
| Advisor-added duty shows amber "Advisor-added" badge              | ✓ (verified in browser per 06-04 SUMMARY)                  |
| Orphan check renders flag cards with rule text OR clean message   | ✓ (verified in browser per 06-04 SUMMARY)                  |
| Confirm Duties transitions to success state with disabled JES CTA | ✓ (verified in browser per 06-04 SUMMARY)                  |

No outstanding human verification items.

### Deferred Items

None. Phase 6 has no deferred items — all 5 roadmap success criteria are met and all 4 JD requirements (JD-01, JD-02, JD-03, JD-04) are satisfied by the implementation. Phase 7 (JES Scoring) builds on the `jd_drafted` stage but addresses JES-01, not Phase 6 must-haves.

### Summary

Phase 6 is **complete and verified**. All 5 ROADMAP success criteria are satisfied with code citations. All 4 requirements (JD-01 through JD-04) have evidence in the codebase. All 31 must-haves across the 4 PLANs are verified. The full test suite is green (141 passed, 0 skipped) and the human-verify checkpoint was approved by the advisor.

**No gaps. No outstanding human verification items. No regressions.**

---

_Verified: 2026-06-02_
_Verifier: gsd-verifier_
