---
status: advisory
phase: 20-export
files_reviewed: 14
critical: 2
warning: 11
info: 10
total: 23
reviewed_at: 2026-06-10T12:00:00Z
reviewer: gsd-code-reviewer (auto)
---

# Code Review — Phase 20 (Export)

**Status:** advisory (2 critical findings, all have known fixes)

**Files reviewed (14):**
- v2/backend/app/api/__init__.py
- v2/backend/app/api/export.py
- v2/backend/app/api/wd.py
- v2/backend/app/data/constants.py
- v2/backend/app/main.py
- v2/backend/app/models/work_description.py
- v2/backend/app/services/classification_gate.py
- v2/backend/app/services/export_service.py
- v2/backend/app/services/jes_service.py
- v2/backend/requirements.txt
- v2/backend/scripts/build_poster_template.py
- v2/backend/scripts/build_wd_template.py
- v2/backend/tests/test_export.py
- v2/frontend/src/app.jsx

---

## Critical (2)

### CR-01 — `(wd.confirmed_og or {}).get("og_code", "")` crashes when confirmed_og is a non-empty string

**Location:**
- `v2/backend/app/api/export.py:138` (PDF endpoint)
- `v2/backend/app/services/export_service.py:181` (`_build_v2_manifest`)
- `v2/backend/app/services/export_service.py:239` (`_build_wd_context`)
- `v2/backend/app/services/export_service.py:302` (`_build_poster_context`)

**Issue:** The `WorkDescription` model allows `confirmed_og: Optional[Union[str, dict]]` (the cumulative Phase 16 Pydantic fix from this phase). The DOCX self-healing path correctly uses `isinstance(wd.confirmed_og, dict)`, but the four sites above do not. When `confirmed_og` is a non-empty string like `"EC"`, `(wd.confirmed_og or {})` returns `"EC"` (truthy), then `"EC".get("og_code", "")` raises `AttributeError`. The DOCX export will 500 for any WD where confirmed_og was persisted as a bare string.

**Fix:** Add a small helper in `app/services/export_service.py` and use it everywhere `og_code` is extracted from `confirmed_og`:

```python
def _og_code_from(wd) -> str:
    if isinstance(wd.confirmed_og, dict):
        return wd.confirmed_og.get("og_code", "")
    return wd.confirmed_og or ""
```

Apply at all four sites. Equivalent fix in `export.py:138`.

---

### CR-02 — HTML injection in WeasyPrint PDF export

**Location:** `v2/backend/app/api/export.py:148-149` (PDF endpoint)

**Issue:** Duty text is interpolated directly into HTML without escaping:

```python
duties_html = "".join(
    f"<li>{d.text}</li>" for d in (wd.duties or [])
)
```

If a duty text contains HTML special characters (e.g. `<`, `>`, `&`), WeasyPrint will interpret them as markup. A duty like "Configure <Network> services" breaks the rendered HTML. While this is server-side rendering (not classic XSS), it produces broken output and is a real content-injection vector.

**Fix:** Use `html.escape()` on the duty text (and on `title` for the `<title>` tag and `<h1>`):

```python
import html
duties_html = "".join(
    f"<li>{html.escape(d.text)}</li>" for d in (wd.duties or [])
)
```

Also `html.escape(title)` for the `<title>` and `<h1>` tags.

---

## Warning (11)

### WR-01 — PDF endpoint doesn't run the DOCX self-healing logic

**Location:** `v2/backend/app/api/export.py` (PDF handler)

The DOCX endpoint runs self-healing JES scoring when `jes_total_points is None or _all_floor`. The PDF endpoint does not. A WD with no JES scores will render PDF with an empty JES section.

**Fix:** Extract the self-healing block into a helper and call from both DOCX and PDF endpoints.

### WR-02 — Self-healing duties only look at `wd.duties`, not `wd.record.duties`

**Location:** `v2/backend/app/api/export.py` (self-healing duties extraction)

`_build_wd_context` falls back to `record.duties` when `wd.duties` is empty (the record-fallback path). Self-healing does not mirror this fallback, so WDs in record-only state will be re-scored with an empty duties list, producing poor scores.

**Fix:** Apply the same record-fallback in the self-healing duties extraction.

### WR-03 — Filename slugify inconsistency

**Location:** `v2/backend/app/api/export.py:175` (PDF endpoint)

The PDF endpoint uses `(title or "work-description").lower().replace(" ", "-")` while `export_service.py` has a more robust `_slugify_title`. Inconsistent slugification can produce ugly filenames (e.g. "Manager, Lead.pdf" → "manager,-lead.pdf").

**Fix:** Move `_slugify_title` to a shared module and use in both.

### WR-04 — `URL.revokeObjectURL` called immediately after `a.click()`

**Location:** `v2/frontend/src/app.jsx:455`

In some browsers, revoking the object URL immediately after `a.click()` can cancel the download because the browser hasn't yet read the blob. Should be wrapped in `setTimeout(..., 0)` or `requestAnimationFrame`.

**Fix:**
```javascript
a.click();
setTimeout(() => URL.revokeObjectURL(href), 0);
```

### WR-05 — `_build_wd_context` uses `type("_D", (), {...})()` duck-type hack

**Location:** `v2/backend/app/services/export_service.py:227-234`

The record-fallback path constructs duck-typed duty objects inline. If a future field is added to `DraftDuty`, this fallback won't include it. Fragile.

**Fix:** Use `DraftDuty(**d)` directly:
```python
from app.models.draft_duty import DraftDuty
root_duties = [DraftDuty(**d) for d in (record.get("duties") or [])]
```

### WR-06 — `requirements.txt` missing `docxtpl` and `python-docx`

**Location:** `v2/backend/requirements.txt`

The export code imports `docxtpl` and `python-docx` but neither is declared in requirements.txt. Fresh installs with `pip install -r requirements.txt` will fail at import time.

**Fix:** Add the missing entries.

### WR-07 — `og_level_str` zero-padding logic duplicated

**Location:** 3 places: `_build_wd_context`, `_build_poster_context`, PDF endpoint

The `f"{og_code}-{int(og_level):02d}"` pattern is repeated. Should be a helper.

**Fix:** Add `_og_level_str(og_code, og_level)` helper.

### WR-08 — Test coverage gap: 501 when WeasyPrint present but Pango/Cairo missing

The existing `test_export_pdf_501_when_weasyprint_absent` tests the import failure path. The runtime probe (`_probe_weasyprint()`) returning False is a separate path not covered.

### WR-09 — Test coverage gap: 409 from `require_og_confirmed` gate

No test exercises the 409 path through the export endpoints.

### WR-10 — Test coverage gap: self-healing JES flow

The self-healing block in `export_wd_docx` is untested.

### WR-11 — Test coverage gap: duties record-fallback in `_build_wd_context`

The `record.duties` fallback path is untested.

---

## Info (10)

- **IN-01:** `Union[str, dict]` is a fragile shape. Recommend normalizing to dict at PATCH time in `wd.py:patch_wd` (convert string to `{"og_code": ..., "og_name": ""}`). Single type downstream = no isinstance checks needed.
- **IN-02:** `record.title` not escaped in PDF `<title>` and `<h1>` tags (related to CR-02).
- **IN-03:** PDF endpoint imports `weasyprint` twice (once as bare import, once as `_wp`). Could be combined.
- **IN-04:** Frontend `exportAs` only checks `kind === 'PDF'` and `'clipboard'` — anything else defaults to DOCX. Should validate the kind argument explicitly.
- **IN-05:** Manifest dedup uses `(source_type, source_id, source_version)` tuple — correct.
- **IN-06:** Export endpoint re-loads WD after self-healing. Two DB reads — could be one if self-healing returned the updated WD. Minor.
- **IN-07:** `_resolve_template_path` comment is correct (file is in `app/services/`, two dirs up lands in `app/`).
- **IN-08:** Test `_create_wd_with_jes_scores` seeds with `confirmed_og` as a dict. Doesn't test the string variant (related to CR-01).
- **IN-09:** `int(og_level_int)` cast in PDF endpoint is redundant (model already enforces int).
- **IN-10:** `_all_floor` variable name doesn't quite describe "all scores at degree 0/1 AND has duties". Could be clearer.

---

## Verdict

**Phase 20 can ship after fixing CR-01 and CR-02** (both have known fixes, both are small). The 11 Warning findings are real but mostly deferred cleanup. The 10 Info findings are advisory.

**Recommended next action:** Run `/gsd-code-review-fix 20` to auto-apply the critical fixes, or hand-fix CR-01 (5-line helper + 4 call-site edits) and CR-02 (1-line `html.escape`).
