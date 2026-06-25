---
status: issues
phase: 19-qualifications-amendments
reviewed: 2026-06-09
reviewer: orchestrator (delegated to gsd-code-reviewer subagent; output truncated, REVIEW.md synthesized from partial agent analysis)
---

# Phase 19 Code Review

**Status:** issues (advisory — non-blocking)
**Reviewed:** 2026-06-09

## Findings

### High (1)

- [H1] **QUAL_STANDARDS vs QUAL_DEFAULTS content drift** — `v2/backend/app/data/constants.py` (backend) and `v2/frontend/src/data.jsx` (frontend) have meaningfully different text for EC, AS, and FI groups. The plan/PATTERNS docs say they should mirror each other ("verbatim TBS Qualification Standards reference"), but the texts diverge. AS education is materially different: backend says "two years of a post-secondary program" (post-secondary), frontend says "secondary school diploma" (much lower threshold). EC and FI have smaller word-choice differences. **Impact:** user may see different text in the document preview vs what is stored as the canonical backend value. **Suggested fix:** regenerate `QUAL_DEFAULTS` in `data.jsx` from `QUAL_STANDARDS` at build time, or add a cross-language consistency test.

### Medium (2)

- [M1] **`test_quals.py` does not catch the content drift** — both `test_qual_default_ec` and `test_qual_default_all_groups` only assert that fields are non-empty and contain loose keywords ("degree", "policy"). The test comment in `test_quals.py` says the frontend map "must mirror" the backend constant, but the test never enforces that. **Suggested fix:** add a `test_qual_default_matches_frontend` that imports the frontend module via a JS-side test, or at minimum hardcode both expected strings and assert they are equal in spirit (longest common substring, key phrases).
- [M2] **GET `/api/wd/{id}/amendments` does not 404 on missing WD** — POST returns 404 if the WD doesn't exist, but GET silently returns `{"wd_id": "...", "notes": {}}` with 200. Asymmetric and may mask broken client state. **Suggested fix:** add a `SELECT id FROM work_descriptions WHERE id = ?` guard to the GET handler and raise 404 when the WD is missing.

### Low (5)

- [L1] **`v2/backend/app/api/amendments.py` — `created_at` is SELECTed in GET but never included in the response payload.** Dead column. Either return it (e.g., per-note `updated_at`) or drop it from the SELECT.
- [L2] **`Sec` `amendmentPanel.saved` is never hydrated from server.** Only `amendmentNotes` is hydrated by the `useEffect` in `app.jsx`. If the user had local `amendmentPanels[key].saved` (e.g., from a prior in-memory state in a long-lived session), it would diverge from the server-truth `amendmentNotes[key]`. In practice, page refresh wipes `amendmentPanels` (it is not in localStorage), so the divergence is unreachable. **Suggested fix:** hydrate `amendmentPanels.saved` from `amendmentNotes` on the same effect, or document the divergence.
- [L3] **`document.jsx` uses `r.quals || QUAL_DEFAULT` (generic) as the fallback** instead of `getQualDefault(r.confirmed_og?.og_code)`. In practice this fallback is unreachable because `qualsVisited: true` implies `r.quals` is set (commit() pairs them), but it's a code smell. **Suggested fix:** swap to `getQualDefault(r.confirmed_og?.og_code)` for consistency with the editor.
- [L4] **`QualEditor` `touched` state is not reset when `og_code` prop changes.** If the user re-classifies to a different OG after partially filling the quals step, the error display from the previous og_code's first-blur would still be present until the user blurs the new field. Minor UX.
- [L5] **`handleAmendToggle` text-while-closed is silently dropped.** The `cur.open` guard means a call like `onAmendToggle(key, "text")` while the panel is closed would fall through to the toggle branch (opening with `saved` text) and discard the `text` argument. Currently unreachable in the UI (textarea is only rendered when open), but defensive programming would either log a warning or handle the case explicitly.

### Info (2)

- [I1] **`v2/frontend/src/document.test.jsx` QUAL-03 test is a real assertion**, not a stub. It renders `<DocumentPane>` with a populated `record.quals` and asserts that `container.innerHTML.toContain('qual-sub-k')`. This exercises the production code path and will catch a regression where the class name is removed from `document.jsx`.
- [I2] **`handleAmendSave` checks `text.trim()` for the empty-string guard but sends the untrimmed `text` in the fetch body.** Minor inconsistency; backend `Field(min_length=1)` accepts whitespace, so this is not a security issue, but the user might save a note with leading/trailing spaces they did not intend.

## Reviewer Notes

- The review is **advisory only** per workflow `code_review_gate` — never blocks phase execution.
- The agent subagent output was truncated twice during delegation; this REVIEW.md is a synthesis of the partial analysis and a direct read of the changed source files. Findings H1, M1, M2, L1, L3, L4, L5, I1, I2 are evidence-based; L2 is a theoretical concern.
- The most actionable follow-up is **H1 + M1**: a content-drift test that pins the backend and frontend texts to a single source of truth. Recommend scheduling this as a Phase 19.1 or Phase 20 prep task.
