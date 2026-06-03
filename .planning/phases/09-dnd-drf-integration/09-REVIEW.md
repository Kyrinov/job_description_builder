---
status: issues_found
phase: 09
phase_name: dnd-drf-integration
files_reviewed: 17
critical: 1
warning: 3
info: 4
total: 8
---

# Code Review: Phase 9 — DND DRF Integration

Reviewed at **standard** depth. Backend code (drf_service, router, db, model, ingest script, export extension) is clean. Frontend has one **critical** bug that breaks the primary confirm workflow, plus a few smaller issues.

---

## CR-01 — CRITICAL: CSS selector broken in drf_candidates.html confirm form

**File:** `templates/partials/drf_candidates.html:38`

**Issue:** The inline JavaScript uses a malformed CSS selector that returns zero matches, regardless of which checkboxes the user selects.

```javascript
// Line 38 — broken selector
const checked = document.querySelectorAll('input[name=' + 'candidate_ids' + '[]' + ']:checked');
```

Concatenated, this becomes the string:

```
input[name=candidate_ids[]]:checked
```

The `[` and `]` in the attribute value are not quoted, so the CSS parser interprets them as the boundary of an attribute selector — `input[name=candidate_ids][checked]:checked`. The selector requires `name="candidate_ids"` (no brackets), but the actual HTML has `name="candidate_ids[]"` (with brackets, line 20). Result: `querySelectorAll` returns an empty `NodeList`. `Array.from(checked).map(el => el.value).join(',')` produces `""`. The hidden `row_ids` input is set to an empty string, and the form posts `row_ids=""`.

**Server impact:** `confirm_drf_linkages` is called with an empty list, which **replaces** the WD's `drf_linkages` with `[]`. User selects checkboxes, clicks "Confirm Selected Linkages", sees the form's HTMX response render with **0 confirmed** — all their selections are silently lost. The primary workflow is non-functional.

**Fix:**

```javascript
// Option A — quote the attribute value
const checked = document.querySelectorAll('input[name="candidate_ids[]"]:checked');

// Option B — use a class on the checkboxes (more robust)
// In the HTML:  <input type="checkbox" class="drf-candidate-checkbox" value="{{ c.id }}">
// In the JS:    const checked = document.querySelectorAll('.drf-candidate-checkbox:checked');
```

Option B is preferred — easier to read, no quoting concerns, decouples JS from the PHP-style name.

Also consider: when `row_ids` ends up empty due to a JS failure, the server should NOT silently wipe existing linkages. Either reject the empty submission with a 400, or treat empty `row_ids` as a no-op (skip the replace).

---

## WR-01 — WARNING: `class="muted"` has no global CSS rule

**Files:** `templates/wizard/step_export.html:26,43,97`, `templates/partials/drf_candidates.html:46`, `templates/partials/drf_confirmed.html:35`

**Issue:** The `.muted` class is used in 5 places across 3 files, but `app/static/css/main.css` does not define a global `.muted` rule. The class is only used as a descendant of `.og-confirmed-banner` and `.jd-confirmed-banner` (scoped rules in earlier phases). Standalone `<p class="muted">` outside those banners renders as default text — no gray color, no smaller font, no visual de-emphasis.

**Fix:** Add a global rule to `main.css` (e.g., in Layer 14 alongside the new DRF panel styles):

```css
.muted {
    color: #6c757d;
    font-size: 0.875rem;
}
```

---

## WR-02 — WARNING: DOCX `{%p if %}` gate may not include tables between markers

**File:** `scripts/build_docx_template.py:176-196`

**Issue:** The Section 6 DRF gate uses paragraph-level tags with a table between them:

```python
doc.add_paragraph("{%p if drf_linkages|length > 0 %}")
doc.add_heading("6. Departmental Results Framework Linkages", level=1)
doc.add_paragraph("The following DRF programs and expected results are linked...")
drf_table = doc.add_table(rows=4, cols=3)
# ... table setup ...
doc.add_paragraph("{%p endif %}")
```

`docxtpl`'s paragraph-level `{%p %}` markers operate at the paragraph level. Whether they encompass tables between the markers is library-version-dependent and historically inconsistent. If the gate doesn't work as expected, the table would render even when `drf_linkages` is empty (the empty shell the comment specifically wants to avoid).

**Fix:** Add an end-to-end render test that exports a WD with `drf_linkages=[]` and asserts Section 6 is absent. If the gate fails, restructure with `{%p if %}` wrapping each table cell or use a Jinja2 `if` inside a table row's cell text.

---

## WR-03 — WARNING: Empty `row_ids` wipes existing linkages (silent data loss)

**File:** `app/api/drf_integration.py:91-95` (parsing) and `app/services/drf_service.py:104-117` (replace)

**Issue:** `row_ids.split(",")` with `token.isdigit()` silently filters non-digit tokens. If the form posts `row_ids=""` (which it always does due to CR-01), the parsed list is empty. `confirm_drf_linkages` then replaces `wd.drf_linkages` with `[]`. The user clicks "Refine Linkages", doesn't select anything (or the JS is broken), clicks Confirm, and **all** previously confirmed linkages are deleted. There is no "are you sure?" prompt, no undo, no warning.

**Fix:** In `drf_service.confirm_drf_linkages`, treat `row_ids=[]` as a no-op (return existing linkages) when called with an explicit "refine" intent, OR require at least one selection when the form is submitted. Alternatively, add a `replace: bool = True` parameter to the service and have the router default `replace=True` only on an explicit "Replace Linkages" button (separate from "Add to Selection").

This is a UX data-loss risk that compounds CR-01.

---

## IF-01 — INFO: `_tokenize` regex doesn't handle accented characters

**File:** `app/services/drf_service.py:52`

**Issue:** `re.findall(r"[a-z]+", text.lower())` matches only ASCII lowercase letters. If the WD's `raw_input` or duty text contains French words (e.g., "développement", "sécurité"), those tokens are silently dropped from the matching set. For a DND-only English prototype, this is acceptable. Worth noting for future bilingual support.

**Fix (when needed):** Use `re.findall(r"[a-zà-ÿ]+", text.lower(), flags=re.UNICODE)` to include Latin-1 supplement characters.

---

## IF-02 — INFO: DRF ProvenanceTag uses `date.today()` for `retrieved_date`

**File:** `app/services/export_service.py:147`

**Issue:** The synthesized DRF ProvenanceTag uses `date.today()` as `retrieved_date`. This reflects the **export** date, not the date the source data was retrieved. For a one-time ingest of a static CSV, this is acceptable. For a system where DRF data could be re-ingested from a newer dataset vintage, the field becomes misleading.

**Fix (when needed):** Store the dataset's `ingested_at` timestamp on the WD or look it up from a `drf_ingest_runs` table at emission time.

---

## IF-03 — INFO: `Jinja2Templates` directory setup is inconsistent

**File:** `app/api/drf_integration.py:32` vs `app/main.py:126-130`

**Issue:** `main.py` creates a `Jinja2Templates` with two directories (project-root `templates/` AND `app/templates/`). `drf_integration.py` creates its own `Jinja2Templates` with only the project-root `templates/` directory. If a future partial is added to `app/templates/partials/`, the DRF router wouldn't find it.

**Fix:** Centralize the templates directory setup — either pass the same `Jinja2Templates` instance to the router, or share a module-level singleton.

---

## IF-04 — INFO: `wd_id` form field is redundant with URL path param

**File:** `templates/partials/drf_candidates.html:13`

**Issue:** The form has `<input type="hidden" name="wd_id" value="{{ wd_id }}">` even though the form's `hx-post` URL already includes `{{ wd_id }}` as a path segment. The handler reads `wd_id` from the path param, so the form field is unused.

**Fix:** Remove the redundant hidden input.

---

## Self-Check

- [x] All 17 files in scope were reviewed
- [x] 1 critical, 3 warning, 4 info findings classified
- [x] Fixes are concrete (file:line + suggested code)
- [x] No findings on backend correctness (drf_service, drf_integration router, model, db, ingest)
