---
phase: 24-risk-audit
plan: 02
subsystem: audit
tags: [pytest, tdd, audit, cba, err, federal-court, fpslreb]

# Dependency graph
requires:
  - phase: 24-risk-audit
    plan: 01
    provides: risk_auditor.py stub module + 10 RED test stubs
provides:
  - load_cba_data(og_code) → dict | None with real JSON file loading from data/agreements/{DIR}/{DIR}_full.json
  - _run_err_checks(wd) → list[dict] (Cushnie + Dervin/Trépanier principles)
  - _run_cba_checks(wd, cba_data) → list[dict] (two-signal rule: verbatim term match + section relevance)
  - run_audit(wd, cba_data) → list[dict] (orchestrates CBA + ERR checks)
  - _check_duty_coverage, _check_duty_specificity, _classify_article_type, _extract_duty_text helpers
  - _ARTICLE_RELEVANCE and _ARTICLE_TERMS constants (5 article types × curated term lists)
affects: [24-03, 24-04, phase-25]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deterministic rule matching in app/services/* (no LLM in audit path)"
    - "Two-signal rule: both verbatim term match AND section relevance must be True for a CBA finding to fire"
    - "Conservative false-negative-over-false-positive design (per legal-domain threat model)"
    - "Deduplication by article type — one CBA finding per CBA article type at most"
    - "Article classification via title substring matching (CBA section 'id' field is always empty string)"
    - "Path resolution via Path(__file__).parents[N] — verified empirically that data/agreements/ lives at repo root (parents[4])"
    - "AuditFinding dataclass with Literal['id','ov','du','cls','q','drf'] section key (matches amendment panel keys)"

key-files:
  modified:
    - v2/backend/app/services/risk_auditor.py (full implementation; was stub)

key-decisions:
  - "Two-signal rule requires BOTH signal_1 (verbatim term match) AND signal_2 (section relevance) to fire a CBA finding — chosen over single-signal because legal domain requires conservatism"
  - "Fixed DATA_DIR path from .parents[3] to .parents[4] — .parents[3] resolves to v2/ (one level too shallow); .parents[4] lands at the repo root where data/agreements/ actually exists"
  - "Curated term lists per article type (3-4 terms each) over generic NLP tokenization — predictable and testable; signals in AUDIT-02 are domain-specific terms unlikely to appear in typical duty text by coincidence"
  - "CBA finding deduplicated by article type (not by section) — one CBA_STATEMENT_OF_DUTIES finding at most, even if multiple statement-of-duties articles exist in the agreement"
  - "Severity 'warning' for ERR_DUTY_COVERAGE, 'advisory' for ERR_DUTY_SPECIFICITY — coverage gap is a stronger ERR signal than specificity underspecification"
  - "Citation text formatted as '{Article title}: {first 300 chars of article text}...' — preserves the verbatim CBA anchor for advisor review"

patterns-established:
  - "Pattern: rule_predicate(wd) → AuditFinding | None for each ERR/CBA rule — single source of truth per rule"
  - "Pattern: section_key selection prefers 'du' if in relevant_sections, else next(iter(...)) — keeps findings anchored to the most advisor-actionable section"
  - "Pattern: load_X_data() returns None for unmapped keys — graceful degradation; downstream code checks truthiness before invoking dependent logic"

requirements-completed: []  # AUDIT-02 + AUDIT-03 logic implemented and unit-tested GREEN, but full requirement validation gated on Plan 03 endpoint (AUDIT-01) — RED integration tests remain for that integration.

# Metrics
duration: 5min
completed: 2026-06-15
---

# Phase 24 Plan 02: Risk Auditor Service Implementation Summary

**Full implementation of `risk_auditor.py` service: real CBA JSON loading, two ERR predicate rules (Cushnie + Dervin/Trépanier), and CBA two-signal matching (verbatim term + section relevance) — all deterministic, offline, no LLM.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-15T18:36:02Z
- **Completed:** 2026-06-15T18:40:30Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Implemented `load_cba_data(og_code)` with real JSON file loading from `data/agreements/{DIR}/{DIR}_full.json`; verified 20/20 mapped directories exist; returns `None` for unmapped OG codes (NT, ED, UNKNOWN) and missing JSONs; never raises
- Fixed `DATA_DIR` path constant: `Path(__file__).parents[3]` → `parents[4]` (verified empirically — `.parents[3]` resolves to `v2/`, `.parents[4]` to repo root where `data/agreements/` actually lives)
- Implemented `_check_duty_coverage` (Cushnie) — fires when WD has fewer than 3 duties; severity `warning`; full FPSLREB Cushnie citation embedded
- Implemented `_check_duty_specificity` (Dervin/Trépanier) — fires when 50%+ of duties are under 8 words; severity `advisory`; full FPSLREB Dervin citation embedded
- Implemented `_classify_article_type` — substring-matches CBA section titles to 5 audit-relevant article types (scope, exclusion, application, recognition, statement of duties); ignores non-audit articles like check-off and grievance
- Implemented `_run_cba_checks` with two-signal rule — both verbatim term match AND section relevance must be True for a finding to fire; deduplicates by article type
- Wired `run_audit` to call CBA checks (skipped when `cba_data is None`) then ERR checks

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement load_cba_data() — real JSON file loading** - `41bb1dc` (feat)
2. **Task 2: Implement _run_err_checks() and _run_cba_checks() in risk_auditor.py** - `024c64e` (feat)

**Plan metadata:** Pending orchestrator post-wave commit (worktree mode)

_TDD sequence: test(24-01) `1bd68cc` RED → feat(24-02) `41bb1dc` GREEN loader → feat(24-02) `024c64e` GREEN rules_

## Files Created/Modified

- `v2/backend/app/services/risk_auditor.py` — Complete service module: constants (DATA_DIR, OG_AGREEMENT_DIR, ERR thresholds, _ARTICLE_RELEVANCE, _ARTICLE_TERMS), dataclass (AuditFinding with to_dict), public functions (load_cba_data, run_audit), and private helpers (_check_duty_coverage, _check_duty_specificity, _run_err_checks, _classify_article_type, _extract_duty_text, _run_cba_checks). 282 lines total (was 90-line stub).

## Test Status

| Test | Type | Status | Notes |
|------|------|--------|-------|
| `test_err_duty_coverage` | Unit (AUDIT-03) | **GREEN** | Was RED in Plan 01 baseline |
| `test_err_duty_specificity` | Unit (AUDIT-03) | **GREEN** | Was RED in Plan 01 baseline |
| `test_zero_findings_clean_wd` | Unit (AUDIT-01) | **GREEN** | Clean WD with 4 long duties → `[]` |
| `test_load_cba_unmapped_og` | Unit (AUDIT-02) | **GREEN** | NT, ED, UNKNOWN all return `None` |
| `test_two_signal_false_positive` | Unit (AUDIT-02) | **GREEN** | Was SKIP'd; now un-skipped and passes — CBA data loads, no verbatim term match → no CBA findings |
| `test_finding_section_key_valid` | Unit (AUDIT-05) | **GREEN** | Dataclass accepts `'du'` key; `to_dict()` round-trips |
| `test_audit_endpoint` | Integration (AUDIT-01) | **RED** | Awaits Plan 03 `POST /api/wd/{id}/audit` |
| `test_audit_rerun_replaces` | Integration (AUDIT-01) | **RED** | Awaits Plan 03 |
| `test_audit_decide` | Integration (AUDIT-04) | **RED** | Awaits Plan 04 `POST /api/wd/{id}/audit/decide` |

**Full backend suite:** 141 passed (134 pre-existing + 7 new GREEN in `test_risk_audit.py`), 3 failed (expected; awaiting Plan 03 + 04 endpoint implementation).

## Decisions Made

- **DATA_DIR path correction:** The stub used `.parents[3]`, which resolves to `v2/` (one level too shallow — `v2/data/agreements` does not exist). Verified empirically that `data/agreements/` is at the repo root, so `.parents[4]` is the correct level. Documented in code comment so future maintainers don't re-trip over the path depth.
- **Two-signal rule design:** The plan specifies "verbatim term match + section relevance" as a deliberate false-negative-over-false-positive design choice for the legal domain. Implemented with curated term lists (3-4 terms per article type) over generic NLP tokenization — predictable, testable, and avoids common-word false positives.
- **CBA finding dedup by article type:** If a CBA has multiple "scope" articles (rare but possible in multi-OG agreements like PA), the dedup set (`fired_rule_ids`) ensures at most one `CBA_SCOPE` finding fires. This matches the "one finding per rule" mental model and keeps the UI clean.
- **Section key selection:** When an article type maps to multiple JD sections (e.g. `scope` → `{du, ov, cls}`), the implementation prefers `'du'` (duties) as the primary anchor — duties are the most advisor-actionable section and the one most likely to need amendment via the existing Phase 19 panel.
- **Severity hierarchy:** `ERR_DUTY_COVERAGE` = `warning` (gating concern: missing duties), `ERR_DUTY_SPECIFICITY` = `advisory` (quality concern: short duty text). Matches the legal weight of the principles — Cushnie (completeness) is a stronger finding than Dervin (specificity).
- **Citation formatting:** `{Article title}: {first 300 chars of article text}...` — preserves the verbatim CBA anchor while keeping the citation field compact enough for UI rendering.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed DATA_DIR path depth (parents[3] → parents[4])**
- **Found during:** Task 1 verification (manual `ls data/agreements/` from repo root)
- **Issue:** The plan's specified path `Path(__file__).parents[3] / "data" / "agreements"` resolves to `v2/data/agreements`, which does not exist. The plan itself flags this as a "verify with `ls data/agreements/` from repo root before finalizing" step.
- **Fix:** Changed to `Path(__file__).parents[4] / "data" / "agreements"` — verified `data/agreements/` lives at the repo root, 4 levels up from `v2/backend/app/services/risk_auditor.py`.
- **Files modified:** `v2/backend/app/services/risk_auditor.py`
- **Verification:** Manual `python3 -c "from app.services.risk_auditor import load_cba_data; print(load_cba_data('EC')['sections'][0])"` returns the EC "Addendum" section; all 20 mapped OG directories verified to exist; NT, ED, UNKNOWN return None.
- **Committed in:** `41bb1dc` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Path correction was necessary for the loader to function. The plan's verification step explicitly anticipated this ("Verify with `ls data/agreements/` from repo root before finalizing"). No scope creep.

## Issues Encountered

None — `load_cba_data` works on the first try after the path correction. The two-signal CBA test passes on the first try (curated term lists correctly exclude the generic test duty text). The ERR rule tests pass on the first try (thresholds and predicate logic are simple).

One pre-existing `pytestmark = pytest.mark.asyncio` warning applies to the 5 unit tests in `test_risk_audit.py` (they're sync functions but inherit the module-level `pytestmark`). Not a regression introduced by this plan; carried forward from Plan 01. Can be cleaned up in a future plan if desired.

## User Setup Required

None — no external service configuration required. All logic is local Python + existing on-disk CBA JSON files.

## Next Phase Readiness

- **Plan 24-03** is unblocked: `run_audit(wd, cba_data)` and `load_cba_data(og_code)` are now fully implemented and unit-tested; ready to wire into `POST /api/wd/{id}/audit` endpoint. The endpoint must:
  1. Load WD from DB
  2. Resolve `confirmed_og` (handle string-or-dict shape from Phase 16/17 fix)
  3. Call `load_cba_data(og_code)` (returns None for NT/ED)
  4. Call `run_audit(wd, cba_data)`
  5. DELETE previous `risk_audit_finding` rows for the WD, then INSERT new ones
  6. Return `{"wd_id": id, "findings": [...]}` — ready for `test_audit_endpoint` and `test_audit_rerun_replaces`
- **Plan 24-04** is unblocked: `AuditFinding` dataclass and section-key validation are ready for the decide endpoint (needs `Literal['accept', 'manual_edit', 'skip']` decision field and `risk_audit_decision` audit_log event).
- **No blockers.** Backend test suite is healthy (141 GREEN + 3 expected RED for endpoint work + 1 SKIP — wait, actually 0 SKIP now, all unit tests GREEN). Plan 03 + 04 will deliver the HTTP layer.

## Self-Check

- [x] `v2/backend/app/services/risk_auditor.py` modified (90 → 282 lines)
- [x] Both task commits (`41bb1dc`, `024c64e`) exist in git log
- [x] `load_cba_data("EC")` returns dict with 73 sections
- [x] `load_cba_data("NT")` returns None; `load_cba_data("ED")` returns None; `load_cba_data("UNKNOWN")` returns None
- [x] `run_audit(wd, None)` returns `ERR_DUTY_COVERAGE` finding for WD with 1 duty
- [x] `run_audit(wd, None)` returns `ERR_DUTY_SPECIFICITY` finding for WD with 3 short duties
- [x] `run_audit(wd, None)` returns `[]` for clean WD with 4+ long duties
- [x] `run_audit(wd, cba_data)` returns 0 CBA findings for duty text with no verbatim CBA terms
- [x] Full backend suite (134 pre-existing + 7 new GREEN) passes; 3 expected RED for endpoint work
- [x] Plan metadata commit deferred to orchestrator (worktree mode)

---
*Phase: 24-risk-audit*
*Completed: 2026-06-15*
