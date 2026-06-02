---
status: flagged
phase: 07-jes-scoring
files_reviewed: 9
findings: 5
date: 2026-06-02
---

# Phase 7 Code Review

## Summary

Phase 7 (JES Scoring) is structurally sound. The service follows the established
pattern from `app/services/jd_service.py` (sequential LLM calls, asyncio.to_thread
for SQLite, stage-gate validation, model_copy on save, instructor singleton
imported from `app/ai/...`). The instructor singleton in `app/ai/jes_scoring.py`
mirrors `app/ai/jd_ranking.py` exactly, and the router in `app/api/jes_scoring.py`
mirrors `app/api/jd_generation.py` (templates_dir resolution, error mapping,
HTMX/JSON dual path). The `level=-1` sentinel is correctly threaded through
JESFactorScore (non-optional int, per Phase 1 model contract), and the
sequential per-factor loop (no asyncio.gather) is the correct choice for
Ollama-on-ARM64.

Five minor issues were found. One is a real bug (silent total miscalculation
when the LLM returns a degree missing from the point_values dict). Two are
pattern deviations in the CSS layer (new custom-property names that don't exist
in Layer 2, breaking the token system). One is an accessibility/UX
inconsistency in `jes_scores.html` (`aria-disabled` on a live anchor). One is
defensive code that adds noise without value. All are low-impact; none are
security issues.

## Findings

### MEDIUM — Silent total-points miscalculation when LLM returns an unknown degree

**File:** app/services/jes_service.py:76-77, 222
**Category:** bug
**Issue:** `_build_jes_factor_score` calls `point_values.get(rating.degree)`. If
the LLM returns a degree identifier that is present in the `degree_descriptors`
list (so it parses to a numeric `level`) but missing from the `point_values`
dict (or the two are inconsistent), `points` becomes `None` while `level` is a
valid integer. The factor is then silently excluded from `jes_total` by
`sum(s.points for s in jes_scores if s.points is not None)` on line 222. The
advisor sees a lower total with no indication that a factor was dropped. This
contradicts the system prompt's promise of "return only the degree identifier
and a rationale — do not compute points" because the service can still drop
points silently when the degree→points map is incomplete.

**Fix:** Log a `logger.warning(...)` when `points is None` after a successful
LLM call, and consider whether such factors should be treated as scoring
failures (sentinel `level=-1`) rather than partial successes. At minimum, the
total should reflect the drop, not hide it.

**Impact:** Incorrect JES total points on the scored WorkDescription — the
number that drives Phase 8 export — without any operator-visible warning.

### LOW — Layer 10 CSS uses undefined design tokens

**File:** app/static/css/main.css:834-896
**Category:** pattern
**Issue:** Layer 10 (`Phase 7 — JES Scoring`) introduces new custom properties
(`--color-primary`, `--color-surface`, `--color-error-bg`, `--color-error-border`,
`--color-error-text`, `--color-text-secondary`, `--color-text-primary`,
`--color-text-muted`) that are not declared in the `:root` token block in
Layer 2. Each rule provides an inline fallback (e.g.
`var(--color-primary, #1d4ed8)`), so the page renders correctly, but the new
names diverge from the established token system
(`--color-accent`, `--color-dominant`, `--color-destructive`,
`--color-text-muted`, `--color-text`). Future maintenance will need to know
two parallel token systems exist.

**Fix:** Replace the new property names with the existing tokens from Layer 2
(`--color-accent`, `--color-dominant`, `--color-destructive`,
`--color-text-muted`, `--color-text`) and drop the inline fallbacks. If the
author specifically wanted a different shade for JES, add the new tokens to
the `:root` block in Layer 2 so they are defined in one place.

**Impact:** Stylistic drift from the documented token system; harmless
visually, but a maintainability concern.

### LOW — `aria-disabled="true"` on a live anchor that 404s

**File:** templates/partials/jes_scores.html:27-28
**Category:** quality (a11y)
**Issue:** The "Continue to Export" link points to `/wizard/export?wd_id=...`
but no such route exists in `app/main.py` (no `wizard_export` handler). The
`aria-disabled="true"` attribute signals disabled state to assistive tech, but
the element is still a regular `<a href="...">` — clicking it navigates to a
404. The CSS rule `button[aria-disabled="true"]` does not match an `<a>`, so
the link is not visually disabled either (no `cursor: not-allowed`, no
muted color). The combination of `aria-disabled` and an active link is
inconsistent and misleading to screen-reader users.

**Fix:** Either (a) replace the link with `<button type="button" disabled>`
plus a visible "Available in Phase 8" caption, (b) render plain text with no
anchor, or (c) leave the link active and drop `aria-disabled`. Option (a) most
faithfully communicates the "placeholder" intent.

**Impact:** Minor — advisor gets a 404 today, screen-reader users get a
confusing "disabled but clickable" signal.

### LOW — Sentinel rationale claims "after 3 retries" for non-LLM failures

**File:** app/services/jes_service.py:212-217
**Category:** quality
**Issue:** The `except Exception` on line 212 catches any failure inside the
try block — including JSON parse errors in `_build_jes_factor_score` (e.g.,
malformed `point_values` JSON in the DB row) and any unexpected error in the
mapping logic — and reports it as "Scoring failed after 3 retries". The
"3 retries" framing is the instructor-retry message, but the catch is broader
than that, so the rationale mislabels the failure mode.

**Fix:** Narrow the try to the LLM call only, or change the rationale to
something generic like "Scoring failed: {exc}" and let the operator inspect
the exception text.

**Impact:** Low — operator logs are still accurate; only the in-UI rationale
text is slightly misleading.

### LOW — Dead defensive branches in degree→level parser

**File:** app/services/jes_service.py:78-81
**Category:** quality
**Issue:**
```python
try:
    level = int(rating.degree.lstrip("D")) if rating.degree.startswith("D") else -1
except (ValueError, AttributeError):
    level = -1
```
`JESFactorRating.degree: str` is guaranteed to be a string by the Pydantic
model, so `AttributeError` is unreachable and the `else -1` branch only fires
when the LLM returns something that does not start with "D" (a degree like
"1" or "L3"). The function still works, but the dual guards and the AttributeError
catch are dead code given the upstream type guarantee.

**Fix:** Simplify to `int(rating.degree[1:]) if rating.degree.startswith("D") else -1`
or just inline the explicit cases. Keep the ValueError catch because
`int("X")` is reachable when degree is "DX", "Dabc", etc.

**Impact:** Cosmetic.

## Pattern Compliance

- Comparison to `app/ai/jd_ranking.py` (structural analog): **pass.** Singleton
  construction, model definitions, prompt constants, DB version helper all
  follow the same shape. The `get_jes_version_info` function is parameterized
  by `og_code` (which is necessary because each OG has its own JES source file)
  and the rest of the file is a direct port. Per-file comment in
  `app/ai/jes_scoring.py:11` correctly cites the analog.
- Comparison to `app/services/jd_service.py` (service analog): **pass with
  deviations noted.** asyncio.to_thread wrapping, stage-gate validation order
  (load → stage check → confirmed_og check → factor load → LLM loop →
  save), instructor kwargs construction, error message format, and
  `model_copy(update={...})` save pattern are all identical. The deviations
  are intentional and documented in the file's docstring: sequential
  per-factor loop (vs single composite LLM call), `level=-1` sentinel (vs
  `raise ValueError`), and stage-gate value `'jd_drafted'` (vs
  `'og_classified'`). The MEDIUM finding above is a deviation that is not
  documented — silent total miscalculation.
- Comparison to `app/api/jd_generation.py` (router analog): **pass.** Templates
  directory resolution, `Form(...)` parameter binding, `ValueError`-based
  error mapping (404 for "not found" / 422 for everything else), and
  HTMX/JSON dual response path are all mirrored exactly. File-level
  docstring correctly cites the analog.

## Verdict

FLAGGED — consider running /gsd-code-review-fix 7

The MEDIUM finding (silent total miscalculation) is the only one that affects
correctness. The other four are pattern/quality/a11y deviations that are safe
to defer. If the team prefers a clean phase close-out, all five are
straightforward to fix in a single follow-up commit.
