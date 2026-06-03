---
phase: 04-nl-noc-mapping
status: advisory
depth: standard
agent: gsd-code-reviewer
files_reviewed: 13
findings_total: 8
blockers: 0
critical: 0
major: 1
minor: 1
info: 6
generated: 2026-06-01
---

# Code Review — Phase 04: NL→NOC Mapping

## Status: advisory

Phase 04 is shippable as-is. The one critical bug identified during review
(`map_noc` not persisting candidates) was fixed in commit `ea27077`. One major
and one minor issue remain for followup; the rest are info-level.

## Resolved since first pass

### CRITICAL — End-to-end flow broken: map_noc didn't persist candidates
**File:** `app/api/noc_mapping.py:33-60` (original) → fixed in `ea27077`
**Original symptom:** `POST /api/noc/map` returned candidates but never saved
them to `WorkDescription.noc_candidates`. The follow-up `POST /api/noc/confirm`
loaded the WD (404 if missing), then searched `wd.noc_candidates` for the
submitted `noc_code`. In production, `noc_candidates` was always empty, so the
confirm endpoint always returned 422. The unit test `test_confirm_noc_updates_wd`
passed only because it manually pre-populated `wd.noc_candidates` — masking
the real-world failure mode.

**Fix:**
- `map_noc` now creates a new `WorkDescription` (or loads existing if `body.wd_id` provided), converts candidates via `to_noc_match`, and persists via `save_work_description`.
- `NocMapResponse` now includes `wd_id` so callers (and the HTMX partial) can follow up with the confirm call.
- `templates/partials/noc_results.html` receives the real `wd_id` (was previously `""`).
- Added `test_end_to_end_map_then_confirm` regression test that exercises the full map → confirm flow without pre-populating `noc_candidates`.

## Outstanding findings

### MAJOR — `noc_fts` DDL mismatch in `app/db.py` (conftest works around it)
**File:** `app/db.py:50-58` (in `NOC_SCHEMA_DDL`)
**Issue:** The DDL declares `noc_fts` with `noc_code UNINDEXED` and `content=''`
(contentless). For a contentless FTS5 table, the column values are not stored —
they can only be retrieved by JOINing to a separate content table. The
`noc_code` column, being `UNINDEXED`, cannot be retrieved via SELECT at all.
This means the Stage 1 pipeline query `SELECT ... FROM noc_fts f JOIN noc_units u
ON u.noc_code = f.noc_code` returns 0 rows from a fresh schema, because
`f.noc_code` is `NULL` and the JOIN condition `NULL = '21232'` is `NULL`
(not `TRUE`).

The live DB was created by `scripts/ingest_noc.py` with a different (correct)
schema: `noc_code` indexed, no `content=''`. So the live app works, but any
fresh deployment using only `create_schema()` (without running the ingest
script) would have broken FTS5.

The conftest fixture in `tests/conftest.py:130-140` (post-04-04) drops and
recreates `noc_fts` to match the live schema. This makes the test work but
papers over the production DDL bug.

**Recommendation:** Update `NOC_SCHEMA_DDL` to match the live DB schema:
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS noc_fts USING fts5(
    noc_code, title, definition, element_type, element_text,
    tokenize='porter ascii'
);
```
Remove `UNINDEXED` from `noc_code` and `element_type`, and remove
`content=''`. The conftest fixture's drop+recreate can then be removed.

**Severity rationale:** Major, not critical, because the live DB already has
the correct schema (so production works today). The conftest fix ensures
tests work. The risk is for fresh deployments that don't run the ingest
script — but those deployments would also fail at vec dimension mismatch
(FLOAT[1024] vs FLOAT[768]) and surface other issues first. This is
maintenance debt worth cleaning up.

### MINOR — Starlette `TemplateResponse` deprecation warning
**Files:**
- `app/api/noc_mapping.py:114-118` (post-fix)
- `app/main.py` (`/wizard/noc` route)

**Issue:** Both routes use the old `TemplateResponse(name, context_dict_with_request_key)`
signature. Starlette 0.40+ deprecated this in favor of
`TemplateResponse(request, name, context)`. The 90-test suite produces 1
DeprecationWarning per HTMX-rendering test (3 currently) — visible in CI.

**Recommendation:** Update both call sites to the new signature. ~5 lines of
diff. Safe to bundle with a future Phase 5+ commit.

### INFO — Magic number 1500 in `_format_candidates`
**File:** `app/services/noc_mapper.py:156`
**Issue:** The duty-text truncation limit (`if len(main_duties) > 1500:`) is a
magic number. The function also logs a `noc_truncated` warning at the same
threshold. The value is correct but unexplained at the call site.
**Recommendation:** Define `MAX_DUTIES_CHARS = 1500` at module level with a
docstring explaining the rationale (fits in the LLM's context window, leaves
room for the system prompt + multiple candidates + work description).

### INFO — Hardcoded colors in CSS (hover state, destructive tint)
**File:** `app/static/css/main.css` (hover state ~line 246, destructive tint ~line 371)
**Issue:** Button hover uses hardcoded `#13396B` (darkened accent). Destructive
tint uses hardcoded `#FDEDEC` (light red). The UI-SPEC defines design tokens
for `--color-accent: #1A4A8A` but not for hover or destructive-bg variants.
**Recommendation:** Either add `--color-accent-hover` and `--color-destructive-bg`
to the `:root` block (preferred), or document the hex values inline as
intentional non-tokens.

### INFO — `to_noc_match` import was previously unused
**File:** `app/api/noc_mapping.py:32`
**Issue:** Before `ea27077`, `to_noc_match` was imported in the route but never
called. Post-fix, it's used. No action needed — flagging only because the
unused import was a code-smell indicator that the original author intended to
persist candidates but forgot the call.

### INFO — FTS5 query syntax (not SQL injection)
**File:** `app/services/noc_mapper.py:62, 66`
**Issue:** User-supplied `work_description` is passed directly to `noc_fts MATCH ?`.
FTS5 has its own query syntax (AND, OR, NOT, *, ^, NEAR, column filters). A
user could craft input with FTS5 operators and get unexpected results (e.g.,
`*` returns all rows). This is NOT a security issue (FTS5 can't escape into
SQL), but the behavior may surprise users.
**Recommendation:** Either document this in the wizard step ("plain-language
description, no special search operators") or sanitize the input by stripping
or escaping FTS5 operators. Lower priority — the typical advisor input is
natural-language sentences without operators.

### INFO — Test bootstrap global state
**File:** `tests/test_noc_mapping.py:80-93`
**Issue:** The `_app_bootstrapped` module-level global is set after the first
import, and never cleared. After bootstrap, env vars set in `_set_env` for
subsequent tests have no effect on `settings.db_path` (the Settings singleton
is already constructed with the first test's values). This is intentional (to
avoid httpx connection-pool leaks from recreating the instructor singleton),
but it's a non-obvious constraint.
**Recommendation:** Add a comment block above `_app_bootstrapped` explaining
the constraint. The current comment is brief.

### INFO — Confidence calculation is rank-based placeholder
**File:** `app/services/noc_mapper.py:232` (`to_noc_match`)
**Issue:** `confidence = 1.0 - (candidate.rank / 10.0)` is a synthetic
placeholder, not a calibrated probability. Already documented in
`04-03-SUMMARY.md` as a Phase 7+ concern.
**Recommendation:** No action this phase.

## Verification

- 90 tests pass, 0 fail (`pytest tests/`)
- 11 tests in `test_noc_mapping.py` (was 7 plan-mandated, added 4 bonus:
  guardrail-raise, HTMX HTML partial, end-to-end map-then-confirm, wd_id in
  NocMapResponse)
- No blocker or critical findings outstanding
- Phase 04 is shippable

## Sign-off

Phase 04 code review complete. Critical flow bug fixed. One major finding
(DDL mismatch) and one minor finding (Starlette deprecation) deferred to
followup commits.
