---
phase: 24-risk-audit
reviewed: 2026-06-16T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - v2/backend/app/services/risk_auditor.py
  - v2/backend/tests/test_risk_audit.py
  - v2/backend/app/api/wd.py
  - v2/frontend/src/app.jsx
  - v2/frontend/src/conversation.jsx
findings:
  critical: 0
  warning: 7
  info: 8
  total: 15
status: issues_found
---

# Phase 24: Risk Audit — Code Review Report

**Reviewed:** 2026-06-16
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 24 implements a deterministic CBA + Federal Court (ERR) compliance audit, triggered manually from the Review phase. The core design aligns with project patterns: no LLM in the audit path, deterministic rule matching, parameterized SQL (no string interpolation), and a hard DELETE-before-INSERT pattern for re-running the audit. The frontend cleanly wires a "Run compliance audit" button + findings panel via props passed to `ReviewState` without a `useEffect` auto-trigger — a deliberate design choice flagged in T-24-09.

The 7 warnings below are real but mostly non-blocking. The most actionable items are: (1) `load_cba_data` docstring contract violation — "Never raises" is false; (2) the optimistic UI update in `handleAuditDecide` can silently drop decisions on server failure; (3) frontend test coverage for audit functionality is absent. The 8 info items are style/consistency improvements and minor test gaps.

No SQL injection, no XSS, no hardcoded secrets, no path-traversal (uses `Path(__file__).parents[4] / "data/agreements"` which is verified correct). All CBAs are loaded as JSON dicts, never `eval`'d. The `confirm_og` extraction pattern matches the existing `orphan_check` precedent.

## Warnings

### WR-01: `load_cba_data` docstring lies — "Never raises" is not enforced

**File:** `v2/backend/app/services/risk_auditor.py:70-83`
**Issue:** The docstring states *"Returns None if no agreement directory mapping exists for this OG code (e.g. NT, ED) or if the JSON file is absent. Never raises."* but the implementation calls `json.load(f)` directly. If a CBA JSON file is corrupted, truncated, or contains invalid JSON (e.g. partial write), `json.load` raises `json.JSONDecodeError`, which propagates up to the `POST /api/wd/{id}/audit` endpoint and causes a 500 error. The documented contract is that callers can rely on "None on miss, never an exception" — and the existing 24-02-SUMMARY.md documents this as a verified property (line 71: "never raises").
**Fix:** Wrap the `json.load` in a try/except and return `None` on parse failure, with a logged warning. The downstream `_run_cba_checks` already handles `cba_data=None` by skipping CBA checks.

```python
def load_cba_data(og_code: str) -> dict | None:
    import logging
    log = logging.getLogger(__name__)
    dir_name = OG_AGREEMENT_DIR.get(og_code)
    if not dir_name:
        return None
    json_path = DATA_DIR / dir_name / f"{dir_name}_full.json"
    if not json_path.exists():
        return None
    try:
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("CBA JSON unreadable for %s (%s): %s", og_code, json_path, exc)
        return None
```

### WR-02: Optimistic UI removal in `handleAuditDecide` silently drops decisions on server failure

**File:** `v2/frontend/src/app.jsx:650-665`
**Issue:** The function fires `POST /api/wd/{id}/audit/decide` as fire-and-forget (`.catch(() => {})`), then immediately removes the finding from local state via `setAuditFindings(prev => prev.filter(...))`. If the server returns 422 (invalid section/decision from a buggy client build), 500 (DB write failure), or the network drops, the UI has already hidden the finding card. The user sees their click "succeed" but the `audit_log` row was never written. This violates the audit trail guarantee that decisions are recorded.
**Fix:** Two options:
1. Await the fetch and only remove the finding on `.then()` (no silent error path).
2. On failure, fire a toast and re-insert the finding into local state.

Option 1 (recommended — matches the existing `handleSjdSelect` pattern):
```javascript
function handleAuditDecide(ruleId, section, decision) {
  if (!wd_id) return;
  fetch(`/api/wd/${wd_id}/audit/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rule_id: ruleId, section, decision }),
  })
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(() => {
      if (decision === 'manual_edit') {
        handleAmendToggle(section);
      } else if (decision === 'accept' || decision === 'skip') {
        setAuditFindings((prev) =>
          prev.filter((f) => !(f.rule_id === ruleId && f.section === section))
        );
      }
    })
    .catch(() => {
      setToast('Could not record decision — try again.');
      setTimeout(() => setToast(null), 3500);
    });
}
```

### WR-03: `handleRunAudit` swallows fetch errors silently

**File:** `v2/frontend/src/app.jsx:633-643`
**Issue:** On server error, `.catch(() => { setAuditRunning(false); })` resets the spinner but provides zero user feedback. The user has no idea if the audit ran or failed. This is inconsistent with the sibling `handleSjdSelect` (line 723-727) which fires a toast on failure. Worse, `auditFindings` retains stale data from the previous run, so the user may believe the new run succeeded.
**Fix:** Fire a toast on failure. Reset `auditFindings` to `[]` on failure to avoid the stale-data confusion.

```javascript
.catch(() => {
  setAuditRunning(false);
  setAuditFindings([]);  // prevent stale findings from looking fresh
  setToast('Audit could not run — try again.');
  setTimeout(() => setToast(null), 3500);
});
```

### WR-04: Zero frontend test coverage for the audit feature

**File:** `v2/frontend/src/conversation.test.jsx` and `v2/frontend/src/app.test.jsx`
**Issue:** Phase 24 introduced three new touchable UI surfaces (`handleRunAudit`, `handleAuditDecide`, `FindingCard`) and a new prop chain (`auditFindings`, `auditRunning`, `onRunAudit`, `onAuditDecide` into `ReviewState`). None are covered by the existing 60 frontend vitest tests. The pattern from Phase 22 (SJD) added 2 new tests; Phase 23 (Writing Guide) added `dutyHints` coverage. Phase 24 adds zero. This regression-prone gap means the next refactor of `ReviewState` or `App` could silently break the audit flow.
**Fix:** Add at minimum:
- `FindingCard` renders all 5 fields and 3 decision buttons (smoke render)
- `FindingCard` shows "Show more" toggle for citations > 240 chars
- `ReviewState` shows the "Run compliance audit" button
- `ReviewState` shows findings panel only when `auditFindings.length > 0`
- `handleRunAudit` POSTs to the right endpoint (mock fetch)
- `handleAuditDecide` POSTs to `/audit/decide` and removes the finding on success

### WR-05: `_classify_article_type` substring matching can mis-classify composite article titles

**File:** `v2/backend/app/services/risk_auditor.py:190-200, 171-188`
**Issue:** The function does `if article_type in title_lower`, which is a substring match. For the current EC/PA data this happens to work because titles like "Article 1: purpose and scope of agreement" cleanly contain one of `scope/exclusion/application/recognition/statement of duties` and nothing else. But this is a fragile pattern: if a future CBA adds an article like "Article X: recognition of prior application" (legal precedent is full of multi-keyword titles), the substring match returns the FIRST match in `_ARTICLE_RELEVANCE` insertion order, which may not be the semantically correct one. The function also returns `None` for titles containing none of the keywords, which is correct, but the moment a title contains TWO keywords, the order-dependence becomes a bug source.
**Fix:** Use regex anchored at word boundaries, OR use a per-article-type priority scoring system (e.g., the article type with the longest keyword match wins). At minimum, document the insertion-order dependency in a comment.

```python
import re
# Word-boundary-anchored match prevents "scope" matching inside "microscope" or
# picking the wrong article_type from a composite title.
def _classify_article_type(title: str) -> str | None:
    title_lower = title.lower()
    for article_type in _ARTICLE_RELEVANCE:
        if re.search(rf'\b{re.escape(article_type)}\b', title_lower):
            return article_type
    return None
```

### WR-06: Citation text can be empty or just the ellipsis

**File:** `v2/backend/app/services/risk_auditor.py:255`
**Issue:** `citation=f"{title}: {section.get('text', '')[:300]}..."` produces a citation like `"Article 3: application: ..."` when the article text is empty or fewer than 1 character. While the current EC/PA data has substantive article text, the schema allows empty text (no schema enforcement), and a future manually-edited CBA file could trigger this. The trailing `"..."` is misleading because it implies there is text being elided when there is none.
**Fix:** Guard the truncation:

```python
text = section.get('text', '')
suffix = f"{text[:300]}..." if len(text) > 300 else text
citation = f"{title}: {suffix}"
```

### WR-07: Pydantic `AuditDecideRequest` validation paths are completely untested

**File:** `v2/backend/tests/test_risk_audit.py:177-204`
**Issue:** The model has three validators worth testing (`rule_id: min_length=1, max_length=100`; `section: Literal[...]`; `decision: Literal[...]`). Only one happy-path test exists. The existing `test_save_amendment_invalid_section` and `test_save_amendment_oversized_comment` in `test_amendments.py` (lines 119-136) demonstrate the pattern. The 24-PATTERNS.md explicitly noted "section key Literal validation" as a shared pattern, so this gap is a deviation from the cited analog.
**Fix:** Add at least:
- `test_audit_decide_invalid_section` — `"section": "INJECTED"` returns 422
- `test_audit_decide_oversized_rule_id` — `rule_id` of 101 chars returns 422
- `test_audit_decide_empty_rule_id` — empty `rule_id` returns 422
- `test_audit_decide_invalid_decision` — `"decision": "MAYBE"` returns 422
- `test_audit_decide_404` — non-existent `wd_id` returns 404

## Info

### IN-01: Heavy inline styles in `FindingCard` break the project's CSS-class convention

**File:** `v2/frontend/src/conversation.jsx:113-184`
**Issue:** Every visual property uses inline `style={{...}}` (border, borderRadius, padding, fontWeight, fontSize, color, margin, display, gap). The rest of the project routes styling through `styles.css` and `className`. Examples: `.sjd-entry`, `.sjd-panel`, `.check-row`, `.btn--export`. The className `audit-finding` is applied but no matching CSS rule exists in the file's referenced stylesheet.
**Fix:** Move the inline styles into `v2/frontend/src/styles.css` (or wherever the audit-related classes should live) and reference them via className. The CSS-rule approach gives the audit feature proper visual states (`.audit-finding--advisory`, `.audit-finding--warning`) instead of relying on the string `severity` value in JSX.

### IN-02: "Run compliance audit" button uses `className="btn--export"`

**File:** `v2/frontend/src/conversation.jsx:240-249`
**Issue:** The audit button reuses the export button class. Semantically the audit is not an export action — it is a review/verification action. Future styling changes to exports (e.g., adding a download icon) would inadvertently affect the audit button.
**Fix:** Add a `.btn--audit` (or `.btn--review`) class to `styles.css` and use it on this button.

### IN-03: `FindingCard` `Show more` toggle slices on character count, not word boundary

**File:** `v2/frontend/src/conversation.jsx:115-117`
**Issue:** `citation.slice(0, 240)` can cut mid-word or mid-sentence. The 240-char threshold is arbitrary — for French citations (which the project must support, per the bilingual poster in Phase 20), words are longer on average and slicing at 240 chars is more aggressive.
**Fix:** Slice at the last word boundary before 240 chars, or accept the visual quirk and document the heuristic.

### IN-04: `FindingCard` exports an unused component to the public API

**File:** `v2/frontend/src/conversation.jsx:274`
**Issue:** `FindingCard` is added to the export list but is not consumed by any other file in the frontend (`grep -rn FindingCard` only finds the definition and the in-file usage). The export was likely added to facilitate unit testing, but the export line should match whether tests are actually written (see WR-04) — otherwise the export is dead surface.
**Fix:** Either keep the export and add the planned tests, or remove the export until tests exist.

### IN-05: `test_two_signal_false_positive` is conditionally skipped — weakens the suite

**File:** `v2/backend/tests/test_risk_audit.py:92-118`
**Issue:** The test calls `load_cba_data("EC")` and uses `pytest.skip(...)` if the file is missing. In the CI environment the file IS present, so the test runs — but in any environment where the repo's `data/agreements/EC/EC_full.json` is missing (e.g., a Docker COPY that excludes data files), the test silently skips and the two-signal CBA rule goes unverified. The skip is a smell — a robust test would load a synthetic CBA dict directly via a fixture, removing the dependency on the file system.
**Fix:** Replace the `load_cba_data("EC")` call with a fixture that builds a minimal CBA dict inline. The current fixture strategy in `conftest.py` is file-based; an inline fixture is more portable for this test.

### IN-06: `test_audit_rerun_replaces` doesn't directly assert the DELETE happened

**File:** `v2/backend/tests/test_risk_audit.py:154-168`
**Issue:** The test only compares finding count from the response body across two runs. A buggy implementation that APPEND-INSERTs instead of DELETE-INSERTs would still pass this test if the new run produces the same number of findings as the first (which is the case for a stable WD with no input changes). The audit_log table would have duplicated rows.
**Fix:** Open a `sqlite3` connection (as `test_audit_decide` does at line 194) and assert `COUNT(*) FROM audit_log WHERE wd_id = ? AND event = 'risk_audit_finding'` equals the finding count after the second run.

### IN-07: No test for `load_cba_data` happy path with a mapped OG

**File:** `v2/backend/tests/test_risk_audit.py:83-89`
**Issue:** The `test_load_cba_unmapped_og` test only covers the negative cases (NT, ED, UNKNOWN). There is no positive test that confirms `load_cba_data("EC")` returns a non-None dict with the expected `sections` key. If the path resolution were broken (e.g., after a directory move), the audit endpoint would silently return zero CBA findings for every WD.
**Fix:** Add `test_load_cba_returns_ec_data` that asserts the returned dict has a `sections` list with at least one entry. Tied to WR-01: also assert it doesn't raise on a well-formed file.

### IN-08: `className="btn--export"` for "Auditing…" state has no spinner indicator

**File:** `v2/frontend/src/conversation.jsx:246-248`
**Issue:** The disabled state shows only text change ("Auditing…"). For accessibility (and clarity during slow LLM-free audits, which are still sub-second on this dataset but could grow with more CBA articles), a spinner or animated indicator would help.
**Fix:** Add a small CSS spinner or an `Icon` next to the text. Pure polish, not blocking.

---

_Reviewed: 2026-06-16T00:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
