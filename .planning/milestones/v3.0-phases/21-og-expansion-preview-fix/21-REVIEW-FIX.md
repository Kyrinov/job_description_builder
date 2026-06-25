---
phase: 21-og-expansion-preview-fix
fixed_at: 2026-06-11T00:00:00Z
review_path: .planning/phases/21-og-expansion-preview-fix/21-REVIEW.md
iteration: 1
fix_scope: critical_warning
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 21: Code Review Fix Report

**Fixed at:** 2026-06-11
**Source review:** .planning/phases/21-og-expansion-preview-fix/21-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: AttributeError crash in orphan_check when confirmed_og is a bare string

**Files modified:** `v2/backend/app/api/wd.py`
**Commit:** 4c459af
**Applied fix:** Changed the `else` branch of the `confirmed_og` shape-check from `wd.confirmed_og.og_code` (attribute access on a string, raises `AttributeError`) to `wd.confirmed_og or ""` (direct string use with empty-string fallback). The `if isinstance(wd.confirmed_og, dict)` branch is unchanged.

---

### WR-02: Frontend OG_LEVELS for FB offers Level 08 but JES scoring clamps to max degree 7

**Files modified:** `v2/backend/app/data/constants.py`, `v2/frontend/src/data.jsx`
**Commit:** 82f3153
**Applied fix:** Changed `"FB": list(range(1, 9))` to `list(range(1, 8))` in `constants.py` (FB-1 to FB-7, matching the highest JES factor max degree of 7). Changed `FB: [1,2,3,4,5,6,7,8]` to `FB: [1,2,3,4,5,6,7]` in `data.jsx`. Both constants now agree and the level picker will never surface an unreachable FB-08.

---

### WR-03: og_level parameter mutated in place in score_jes_v2, making log/audit trail misleading

**Files modified:** `v2/backend/app/services/jes_service.py`
**Commit:** 6b0b15a
**Applied fix:** Introduced `effective_level = og_level` before the branch. When clamping fires, `effective_level` is updated to the nearest available level while `og_level` retains the original caller-supplied value. The warning log now correctly reports both the requested level (`og_level`) and the substituted level (`effective_level`). The lookup `NON_EC_TOTALS[routing_code][effective_level]` uses the clamped value.

---

_Fixed: 2026-06-11_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
