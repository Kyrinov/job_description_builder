---
status: all_fixed
phase: 20-export
findings_in_scope: 13
fixed: 13
skipped: 0
iteration: 1
---

# Code Review Fix Report — Phase 20 (Export)

**Fixed at:** 2026-06-10T13:30:00Z
**Source review:** .planning/phases/20-export/20-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 13 (CR-01, CR-02, WR-01 through WR-11)
- Fixed: 13
- Skipped: 0

---

## Fixed

### CR-01 — `confirmed_og` string shape crashes `.get("og_code")`

**Files changed:** (already fixed in prior commit 2497d81)
**Commit:** 2497d81 (pre-existing)
**What was done:** The `_og_code_from(wd)` helper already existed in `export_service.py` (lines 145–155) and was already applied at all four cited call sites. The DOCX endpoint in `export.py` also already used the `isinstance(wd.confirmed_og, dict)` guard. No code change needed — finding was resolved by the previous phase commit. This fix pass also consolidated the `isinstance` check in the PDF endpoint to use `_og_code_from` (as part of WR-07), eliminating the remaining inline copy.

---

### CR-02 — HTML injection in WeasyPrint PDF export

**Files changed:** (already fixed in prior commit 2497d81)
**Commit:** 2497d81 (pre-existing)
**What was done:** `html.escape()` was already applied to `d.text`, `title`, and `og_str` in the PDF endpoint. No code change needed.

---

### WR-01 — PDF endpoint missing self-healing JES scoring

**Files changed:** `v2/backend/app/api/export.py`
**Commit:** 4dd0ee1
**What was done:** Added the same `jes_total_points is None or _all_floor` self-healing block to the PDF handler that existed in the DOCX handler. WDs without JES scores now trigger `score_jes_v2` before the PDF is rendered.

---

### WR-02 — Self-healing duties ignore `record.duties` fallback

**Files changed:** `v2/backend/app/api/export.py`
**Commit:** 4dd0ee1 (same commit as WR-01)
**What was done:** The self-healing duties extraction in the PDF handler now falls back to `(wd.record or {}).get("duties")` when `wd.duties` is empty, matching the fallback logic in `_build_wd_context`.

---

### WR-03 — Filename slugify inconsistency in PDF endpoint

**Files changed:** `v2/backend/app/api/export.py`
**Commit:** 7a39967
**What was done:** Imported `_slugify_title` from `export_service` and replaced the inline `.lower().replace(" ", "-")` with `_slugify_title(title, "work-description")`. PDF filenames now go through the same regex-based slugifier as DOCX exports.

---

### WR-04 — `URL.revokeObjectURL` called synchronously after `a.click()`

**Files changed:** `v2/frontend/src/app.jsx`
**Commit:** fe68a77
**What was done:** Wrapped `URL.revokeObjectURL(href)` in `setTimeout(..., 0)` so the browser has a chance to initiate the download before the object URL is revoked.

---

### WR-05 — Duck-type hack `type("_D", (), {...})()` in `_build_wd_context`

**Files changed:** `v2/backend/app/services/export_service.py`
**Commit:** ef5094f
**What was done:** Replaced the inline anonymous class construction with `DraftDuty(**d)` (using `model_config = ConfigDict(extra="ignore")` so any extra fields are silently dropped). Added `from app.models.draft_duty import DraftDuty` import.

---

### WR-06 — `requirements.txt` missing `docxtpl` and `python-docx`

**Files changed:** `v2/backend/requirements.txt`
**Commit:** 7a87577
**What was done:** Added `docxtpl==0.19.0` and `python-docx==1.1.2` entries. These are direct dependencies of `export_service.py` and were previously absent, causing fresh `pip install -r requirements.txt` to fail at import time.

---

### WR-07 — `og_level_str` zero-padding logic duplicated in three places

**Files changed:** `v2/backend/app/services/export_service.py`, `v2/backend/app/api/export.py`
**Commit:** ce8e041
**What was done:** Added `_og_level_str(og_code, og_level)` helper to `export_service.py`. Replaced inline `f"{og_code}-{int(og_level):02d}" if og_code else ""` in `_build_wd_context`, `_build_poster_context`, and the PDF endpoint with calls to the helper.

---

### WR-08 — Test gap: PDF 501 via runtime probe failure

**Files changed:** `v2/backend/tests/test_export.py`
**Commit:** e1efc54
**What was done:** Added `test_export_pdf_501_when_weasyprint_probe_fails` which monkeypatches `_weasyprint_available = False` on the export_service module to trigger the runtime probe 501 branch (distinct from the import-failure 501 path already tested).

---

### WR-09 — Test gap: 409 from `require_og_confirmed` gate

**Files changed:** `v2/backend/tests/test_export.py`
**Commit:** e1efc54 (same commit as WR-08, WR-10, WR-11)
**What was done:** Added `test_export_docx_409_without_og` and `test_export_poster_409_without_og` — both create a bare WD (no OG set) and assert the 409 response with `"error": "classification_pending"`.

---

### WR-10 — Test gap: self-healing JES flow

**Files changed:** `v2/backend/tests/test_export.py`
**Commit:** e1efc54
**What was done:** Added `test_export_docx_self_heals_jes_scores` which monkeypatches `score_jes_v2` to a no-op, creates a WD with `og_code + og_level + duties` but no `jes_total_points`, then asserts the DOCX export succeeds (self-healing path exercised without needing a live LLM).

---

### WR-11 — Test gap: duties `record.duties` fallback in `_build_wd_context`

**Files changed:** `v2/backend/tests/test_export.py`
**Commit:** e1efc54
**What was done:** Added `test_export_docx_uses_record_duties_fallback` which PATCHes a WD with duties inside `record` only (no root-level `duties` field) and asserts DOCX export returns 200 and non-empty bytes — exercising the record-fallback path in `_build_wd_context`.

---

## Skipped

None.

---

_Fixed: 2026-06-10T13:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
