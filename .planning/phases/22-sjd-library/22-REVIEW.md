---
phase: 22-sjd-library
reviewed: 2026-06-11T16:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - v2/backend/tests/test_sjd.py
  - v2/backend/app/data/sjd_library.py
  - v2/backend/app/api/sjd.py
  - v2/backend/app/api/__init__.py
  - v2/backend/app/models/draft_duty.py
  - v2/backend/app/models/work_description.py
  - v2/backend/app/api/wd.py
  - v2/backend/app/services/export_service.py
  - v2/frontend/src/data.jsx
  - v2/frontend/src/app.jsx
  - v2/frontend/src/document.jsx
  - v2/frontend/src/styles.css
findings:
  critical: 1
  warning: 8
  info: 7
  total: 16
status: issues_found
---

# Phase 22: Code Review Report

**Reviewed:** 2026-06-11
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

The SJD Library phase delivers a clean read-only API surface (`/api/sjd` + `/api/sjd/{number}`), a static 10-entry library parsed at import time, a `sjd-start` endpoint that prefills `confirmed_og`, `og_level`, seed duties, and a new `sjd_source` field, plus a non-blocking "Browse SJDs" modal in the SPA. All 10 tests pass.

Three concerns warrant attention before shipping:

1. **A parser crash on any malformed `Group Level` value** silently breaks the documented "defensive" contract — the function claims to fall back to `(string, 1)` for unparseable inputs but actually raises `ValueError`. A single bad row in `data/SJD Examples.txt` will prevent the entire backend from starting.

2. **The Organizational Context field is always empty** in the parsed library, because the parser silently drops the multi-line continuation that follows the `Organizational Context\t` key. The SJD browser panel's context preview is therefore always blank, despite the source file containing real content.

3. **`confirmed_og.og_name` is overwritten with the SJD's specific title** (e.g., "Junior Analyst") on sjd-start, instead of preserving or fetching the OG group name (e.g., "Economics and Social Science Services"). This affects what the user sees in the classification block of the live document.

The remaining findings are smaller (test hygiene, dead code, hard-coded paths, defensive patterns) — none block the phase but several should be cleaned up.

## Critical Issues

### CR-01: `_og_code_from_group_level` crashes on non-numeric suffix despite docstring's defensive claim

**File:** `v2/backend/app/data/sjd_library.py:61-79`
**Issue:** The docstring states the function *"Falls back to (string, 1) for unparseable inputs (defensive)"*, but the implementation raises `ValueError` for many malformed inputs. The default branch is reached only when `len(parts) < 2`; any input with `>= 2` parts whose last segment is non-numeric crashes:

- `XX-YY` (2 parts, alphabetic last) → `ValueError: invalid literal for int() with base 10: 'YY'`
- `CT-FIN-1A` (special prefix) → `ValueError: invalid literal for int() with base 10: '1A'`
- `EN-ENG-X` (special prefix) → `ValueError: invalid literal for int() with base 10: 'X'`
- `CT-FIN-` (empty last) → `ValueError: invalid literal for int() with base 10: ''`

This is called at module-import time (`SJD_LIBRARY: list[SJDEntry] = _parse_sjd_file(_SJD_FILE_PATH)`) for every entry in `data/SJD Examples.txt`. A single typo in a Group Level cell — e.g., `AS-pending`, `EC-TBD`, or an extra dash — will prevent the backend from starting at all. Verified by repro:

```python
>>> from app.data.sjd_library import _og_code_from_group_level
>>> _og_code_from_group_level('XX-YY')
ValueError: invalid literal for int() with base 10: 'YY'
```

**Fix:** Wrap the int conversion in `try/except` and fall back to `(parts[0], 1)` on failure, and apply the same to the `CT-FIN-` / `EN-ENG-` branches. Also wrap the per-entry build in `_parse_sjd_file` with a try/except so a single bad row doesn't poison the whole import:

```python
def _og_code_from_group_level(group_level: str) -> tuple[str, int]:
    gl = (group_level or "").strip()
    if not gl:
        return ("", 1)
    if gl.startswith("CT-FIN-"):
        try:
            return ("FI", int(gl.split("-")[-1]))
        except ValueError:
            return ("FI", 1)
    if gl.startswith("EN-ENG-"):
        try:
            return ("EN", int(gl.split("-")[-1]))
        except ValueError:
            return ("EN", 1)
    parts = gl.split("-")
    if len(parts) >= 2:
        try:
            return (parts[0], int(parts[-1]))
        except ValueError:
            return (parts[0], 1)
    return (gl, 1)
```

And in `_parse_sjd_file`:
```python
if current.get("SJD Number"):
    try:
        entries.append(_make_entry(current))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Skipping malformed SJD %s: %s", current.get("SJD Number"), exc)
        # Or: raise — depends on policy. Defensive = skip.
```

## Warnings

### WR-01: `Organizational Context` is always empty in parsed library

**File:** `v2/backend/app/data/sjd_library.py:117-120` (and `v2/frontend/src/app.jsx:858-860`)
**Issue:** The SJD file uses a multi-line value for the "Organizational Context" field — the key is `Organizational Context\t` (empty value) on one line, then the actual content spans the next line(s) until the next key. The parser handles this with:

```python
if "\t" not in line:
    # Continuation of a multi-line field (e.g. Organizational Context) — silently drop.
    continue
```

The docstring of `_parse_sjd_file` acknowledges this. As a result, **all 10 entries have `organizational_context == ""`** (verified at runtime), even though the source file contains real content for every entry. The SJD browser panel in the SPA renders this field at `app.jsx:858-860`:

```jsx
<div className="sjd-entry__context">
  {entry.organizational_context.slice(0, 200)}{entry.organizational_context.length > 200 ? '…' : ''}
</div>
```

The "context" section of every SJD card is therefore always empty in the UI, defeating its purpose.

**Fix:** Either (a) capture continuation lines by appending them to the most recent `Organizational Context` value with a space, or (b) declare the field as "intentionally empty" in the parser docstring and remove the UI rendering. The simplest change for the immediate UX is (a):

```python
last_ctx_key = "Organizational Context"  # extendable
if "\t" not in line and last_ctx_key in current:
    current[last_ctx_key] = (current[last_ctx_key] + " " + line.strip()).strip()
    continue
```

A more correct approach is to track which multi-line-capable keys are active and accumulate their continuations.

### WR-02: `confirmed_og.og_name` overwritten with SJD title, breaking OG group name display

**File:** `v2/backend/app/api/wd.py:331`
**Issue:** On `sjd-start`, the endpoint sets:

```python
wd.confirmed_og = {"og_code": entry.og_code, "og_name": entry.title}
```

`entry.title` is the SJD's specific position title (e.g., "Junior Analyst", "Manager, Financial Management (Nature of Impact C4)"), not the official OG group name. The historical meaning of `og_name` in `confirmed_og` is the OG group name (e.g., "Economics and Social Science Services" — defined in `OG_DEFINITIONS` in `app/data/constants.py`).

The frontend renders this in two places:
- `document.jsx:368` — `<div className="cls-block__name">{r.confirmed_og.og_name}</div>` — the live document's classification block.
- `document.jsx:174` — `<div className="cls-block__name">{cls.group} — {cls.groupName}</div>` (legacy `cls.groupName`, unaffected).

So after applying an SJD, users see "Junior Analyst" under their classification badge instead of "Economics and Social Science Services". This conflates "the position this SJD describes" with "the occupational group this position belongs to".

**Fix:** Look up the canonical OG name from `OG_DEFINITIONS` rather than using `entry.title`. The sjd-start endpoint should query `OG_DEFINITIONS.get(entry.og_code, {}).get("og_name", entry.title)` and set that as `og_name`. Alternatively, add an `og_name` field to `SJDEntry` that's hard-coded in the dataclass for the 7 known groups (with a fallback to `title`).

### WR-03: `SJD_LIBRARY` parsing has no error handling for missing/malformed data file

**File:** `v2/backend/app/data/sjd_library.py:54, 107, 170`
**Issue:** The library is parsed at module import time with no try/except:

```python
_SJD_FILE_PATH = pathlib.Path(__file__).parent.parent.parent.parent.parent / "data" / "SJD Examples.txt"
# ...
SJD_LIBRARY: list[SJDEntry] = _parse_sjd_file(_SJD_FILE_PATH)
```

A missing or unreadable `data/SJD Examples.txt` will raise `FileNotFoundError` and the entire backend will fail to start. There is no logger import, no fallback constant, no degraded mode. Combined with CR-01, any single bad row also breaks startup.

**Fix:** Wrap the parse call in a `try/except`, log a warning, and fall back to an empty list. The `/api/sjd` endpoints can return 503 (or an empty list) when the library is empty. This requires adding a logger to the module. Alternatively, make the path configurable via `app.config.get_settings()` and validate at startup with a clear error message.

### WR-04: `_SJD_DUTY_SUGGESTIONS["default"]` aliases EC list by reference

**File:** `v2/backend/app/api/wd.py:86`
**Issue:** The default fallback is set via direct reference:

```python
_SJD_DUTY_SUGGESTIONS["default"] = _SJD_DUTY_SUGGESTIONS["EC"]  # fallback
```

This means `_SJD_DUTY_SUGGESTIONS["default"]` and `_SJD_DUTY_SUGGESTIONS["EC"]` point to the **same list object**. If anything ever mutates one (e.g., appending a per-call entry, removing a duty), the other changes too. Currently no mutation occurs, so the bug is latent, but the pattern is fragile and a future refactor could easily introduce a regression.

**Fix:** Copy the list:

```python
_SJD_DUTY_SUGGESTIONS["default"] = list(_SJD_DUTY_SUGGESTIONS["EC"])
# Or use copy.deepcopy if the contents themselves could mutate (they're dicts here).
import copy
_SJD_DUTY_SUGGESTIONS["default"] = copy.deepcopy(_SJD_DUTY_SUGGESTIONS["EC"])
```

### WR-05: `_build_sjd_seed_duties` has untyped `entry: object` parameter

**File:** `v2/backend/app/api/wd.py:89`
**Issue:** The function signature uses untyped `object` for the SJDEntry argument:

```python
def _build_sjd_seed_duties(entry: object) -> list:
```

The function then accesses `entry.og_code` and `entry.sjd_number`. A typo or refactor that renames these attributes would silently break at runtime. The `SJDEntry` type is already defined in `app.data.sjd_library`.

**Fix:**

```python
from app.data.sjd_library import SJDEntry
# ...
def _build_sjd_seed_duties(entry: SJDEntry) -> list[DraftDuty]:
```

### WR-06: SJD browser OG filter dropdown is hard-coded to 7 codes

**File:** `v2/frontend/src/app.jsx:838-846`
**Issue:** The filter `<select>` lists only 7 OG groups:

```jsx
<option value="AS">AS</option>
<option value="EC">EC</option>
<option value="FI">FI</option>
<option value="IT">IT</option>
<option value="EN">EN</option>
<option value="PE">PE</option>
<option value="WP">WP</option>
```

If new SJD entries are added to the library with a new OG code (e.g., a future Phase adds `NU` or `SW` SJDs), the filter won't expose them. There's already an `OG_LEVELS` constant in `data.jsx:30-54` that lists 22 OG groups. A new `OG_CODES_IN_SJDS` constant could be computed from the SJD library response.

**Fix:** Derive the dropdown options from the SJD list returned by the API (group by `og_code`), or maintain a small constant `const SJD_OG_GROUPS = ["AS", "EC", "FI", "IT", "EN", "PE", "WP"];` exported from `data.jsx` next to `OG_LEVELS` so it's discoverable and can be updated atomically with the library.

### WR-07: `fetchSjdDetail` is exported but never called

**File:** `v2/frontend/src/data.jsx:667-671`
**Issue:** The function is defined and exported, but no frontend file imports or calls it:

```bash
$ grep -rn "fetchSjdDetail" v2/frontend/src/
v2/frontend/src/data.jsx:667:  async function fetchSjdDetail(sjdNumber) {
v2/frontend/src/data.jsx:679:  fetchSjds, fetchSjdDetail,
```

The single-detail endpoint `/api/sjd/{sjd_number}` is also tested (`test_get_sjd_by_number`, `test_get_sjd_404`) but has no frontend consumer. Dead code.

**Fix:** Either remove `fetchSjdDetail` (and the corresponding export entry) until a consumer exists, or wire it into the SJD browser UI (e.g., fetch full context when an entry is clicked, rather than using the truncated list-card preview).

### WR-08: `pytestmark = pytest.mark.asyncio` applies to sync tests

**File:** `v2/backend/tests/test_sjd.py:10`
**Issue:** The module-level `pytestmark = pytest.mark.asyncio` is applied to every test, including the 4 sync tests (`test_sjd_library_count`, `test_sjd_entry_fields`, `test_og_code_normalization`, `test_seed_duties_provenance`). Pytest emits 4 warnings at runtime:

```
PytestWarning: The test <Function test_sjd_library_count> is marked with '@pytest.mark.asyncio' but it is not an async function.
```

The tests pass, but the warnings are noise that suggests incorrect test configuration.

**Fix:** Drop the module-level `pytestmark` and decorate only the async tests:

```python
# Remove: pytestmark = pytest.mark.asyncio

# Then mark each async test:
@pytest.mark.asyncio
async def test_list_sjds_returns_all(client): ...
```

## Info

### IN-01: Dead CSS class `.prov__tag--sjd`

**File:** `v2/frontend/src/styles.css:1133-1146`
**Issue:** A `.prov__tag--sjd` class is defined (with a comment that says it's the "SJD provenance tag in the document footer"), but the SJD tag is rendered with the generic `.prov__tag` class in `document.jsx:466` and `:484-488`:

```jsx
{provTags.map(t => (
  <span key={t} className="prov__tag">
    <i />{t}
  </span>
))}
```

So `.prov__tag--sjd` is never applied.

**Fix:** Either apply `prov__tag--sjd` in addition to `prov__tag` for the SJD-tagged entry, or remove the dead CSS rule. The current behavior (SJD tag uses the generic style) is fine if intentional; the comment in the CSS is misleading.

### IN-02: SJD-03 advisory toast has no test coverage

**File:** `v2/frontend/src/app.jsx:212-221`
**Issue:** The SJD-03 logic fires a toast when the user changes `og_confirm` to a different OG code after an SJD is applied. There's no test exercising this path. Given the security-advisory note (`T-22-06`), some regression coverage would be valuable.

**Fix:** Add a test (frontend Cypress or backend unit test of the diff logic) that simulates: apply SJD with og_code=EC, then `PATCH /api/wd/{id}` with `confirmed_og={"og_code": "FI", ...}`, then verify the toast text is shown / no server-side error.

### IN-03: No visual flash on classification block after SJD apply

**File:** `v2/frontend/src/document.jsx:357`
**Issue:** The classification `Sec` flashes via `fresh={isFresh('og_level')}`, which only triggers when the `og_level` step is committed via the normal interview flow. After `handleSjdSelect` updates `confirmed_og` and `og_level` via the SJD panel, the `flashes` set is not updated, so the classification block doesn't get the visual "fresh" highlight. Duties do flash because the `commit()` flow for the `duties` step adds `'duties'` to `flashes` (FLASH map line 24).

**Fix:** In `app.jsx:handleSjdSelect` after a successful apply, fire `flash('og_level')` (and `flash('duties')` for the duties list). Or add a generic `flash('sjd_applied')` key that the classification and duties sections both observe.

### IN-04: `DraftDuty.sjd_number` set but never read by export manifest

**File:** `v2/backend/app/models/draft_duty.py:24`, `v2/backend/app/services/export_service.py:149-205`
**Issue:** The new `sjd_number: Optional[str]` field is set on each seed duty by `_build_sjd_seed_duties` (`wd.py:105`). The export manifest builder, however, reads the SJD provenance from `wd.sjd_source.sjd_number` (top-level WD field), not from the individual duty's `sjd_number`. The two could diverge if a user manually edits the duties list (e.g., deletes a duty) — the SJD provenance would still appear in the manifest even though the duties no longer reference the SJD. This is not necessarily wrong (the WD was sourced from an SJD regardless of current duties), but the redundancy is worth noting.

**Fix:** Document the intent in `DraftDuty.sjd_number`'s docstring (audit field for individual duty provenance; manifest derives from WD-level `sjd_source`). Or alternatively, derive the manifest entry from the duties themselves, ensuring deletions cleanly remove provenance.

### IN-05: Hard-coded SJD file path via 5 `parent` calls

**File:** `v2/backend/app/data/sjd_library.py:54`
**Issue:** The path is hard-coded with a fragile chain of `.parent` calls:

```python
_SJD_FILE_PATH = pathlib.Path(__file__).parent.parent.parent.parent.parent / "data" / "SJD Examples.txt"
```

If the repo is restructured (e.g., `v2/backend/app/data/` moves to `v2/backend/src/data/`), the path silently breaks. A misconfigured environment (e.g., running from a Docker container where `data/` is at a different path) will also fail.

**Fix:** Make the path configurable via `app.config.get_settings()` (e.g., `settings.sjd_library_path`) with a sensible default. The file is part of the v2/backend app's data layer; a config-driven path is consistent with how `db_path` and other resources are handled.

### IN-06: `_SJD_DUTY_SUGGESTIONS` duplicates frontend `DUTY_SUGGESTIONS`

**File:** `v2/backend/app/api/wd.py:28-86` vs `v2/frontend/src/data.jsx:178-259`
**Issue:** Both files contain per-OG-group duty suggestion lists. The backend's list is a strict subset (3 duties per group, no `EN` group, no `default` group beyond EC) of the frontend's list (7 duties per group, with EN, plus a `default`). The wd.py docstring acknowledges this. When the frontend list is updated, the backend will drift — and the SJD seed duties will look different from the interactive "pick from suggestions" list.

**Fix:** Promote the canonical list to `app/data/constants.py` (e.g., `SJD_SEED_DUTIES`), import it in `wd.py`, and (optionally) also import it in the frontend via a small build-step. The minimal version is to make `wd.py` import from a single source.

### IN-07: Organizational Context truncation is moot because the field is always empty

**File:** `v2/frontend/src/app.jsx:857-860`
**Issue:** The comment in the JSX reads `T-22-05: organizational_context truncated at 200 chars (UX choice only)`, but the underlying field is always `""` because of WR-01. The 200-char truncation never fires, and the `<p>` always renders an empty string inside `.sjd-entry__context`.

**Fix:** Resolves automatically once WR-01 is fixed. If the field is intentionally never populated, remove the comment and consider hiding the `.sjd-entry__context` div when the field is empty (or remove it entirely).

---

_Reviewed: 2026-06-11T16:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
