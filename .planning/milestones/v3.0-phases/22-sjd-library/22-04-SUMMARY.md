---
phase: 22-sjd-library
plan: 04
subsystem: frontend-spa
tags: [SJD-02, SJD-03, fetch-helpers, browse-panel, og-warning, provenance-badge, threat-T-22-02, threat-T-22-05, threat-T-22-06]
dependency_graph:
  requires:
    - 22-02 (GET /api/sjd + GET /api/sjd/{number} endpoints)
    - 22-03 (POST /api/wd/{id}/sjd-start endpoint + DraftDuty.source="sjd" + WorkDescription.sjd_source)
  provides:
    - fetchSjds / fetchSjdDetail async helpers in data.jsx
    - Browse SJDs non-blocking action after Role phase
    - SJD browser panel with OG-group filter
    - SJD-03 og_confirm OG-change advisory toast
    - SJD provenance badge in document.jsx duty list
  affects:
    - v2/frontend/src/data.jsx
    - v2/frontend/src/app.jsx
    - v2/frontend/src/document.jsx
    - v2/frontend/src/styles.css
tech-stack:
  added: []
  patterns:
    - async fetch helper co-located with data layer (data.jsx)
    - useState-driven modal panel for non-blocking browser
    - toast advisory with 7s timeout (SJD-03) / 4s (apply success) / 3.5s (error)
    - inline provenance badge (`<span class="tag tag--sjd">SJD</span>`) for duty source="sjd"
key-files:
  created: []
  modified:
    - v2/frontend/src/data.jsx (added fetchSjds + fetchSjdDetail, 26 insertions)
    - v2/frontend/src/app.jsx (Browse SJDs button, SJD panel, sjd-start, SJD-03 toast)
    - v2/frontend/src/document.jsx (SJD provenance badge in duty list, SJD prov tag in footer)
    - v2/frontend/src/styles.css (.sjd-panel-overlay, .sjd-panel, .sjd-entry, .tag--sjd, .btn-secondary, .sjd-browse-action)
decisions:
  - "fetchSjds / fetchSjdDetail co-located with data layer (data.jsx) to keep fetch logic next to other data utilities (matches v2 pattern)"
  - "SJD browser panel rendered as modal overlay (not inline) so the conversation flow isn't blocked when the panel is open"
  - "SJD-03 toast comparison: `newOgCode !== sjdOgCode` on `og_code` only — level changes (og_level) deliberately do NOT fire the warning, matching the requirement"
  - "SJD-03 toast text exactly: 'Departing from the SJD classification turns this into a new evaluation — the SJD decision no longer applies'"
  - "Browse SJDs button visibility: `step.phase >= 1 && wd_id && !reviewing` — only after Role phase and once a WD row exists for sjd-start"
  - "OG group filter dropdown hardcoded to the 7 groups in SJD_LIBRARY (AS/EC/FI/IT/EN/PE/WP) — matches backend OG normalization from plan 22-02"
  - "organizational_context truncated at 200 chars in panel UI per T-22-05 (full text is government-published; truncation is UX choice only)"
  - "SJD provenance badge inline before duty text (parallel to NOC duties marked by section's `src` header)"
  - "DND SJD Library prov tag added to document footer (parallel to NOC/JES/OG/DRF tags)"
metrics:
  duration: "6m13s (18:36:59Z → 18:43:12Z)"
  completed_date: "2026-06-11T18:43:12Z"
  tasks: 2
  files: 4
  commits:
    - "4441b63: feat(22-04): add fetchSjds and fetchSjdDetail helpers to data.jsx"
    - "eea394c: feat(22-04): add Browse SJDs panel, sjd-start integration, and SJD-03 warning"
---

# Phase 22 Plan 04: SJD Browse UI + sjd-start Frontend Call + SJD-03 Warning

## One-liner

Wired the SJD library into the frontend SPA: async fetch helpers, non-blocking "Browse SJDs" action after Role phase, SJD browser panel with OG filter, sjd-start call with record mirror, SJD-03 og_confirm OG-change advisory toast, and SJD provenance badge in the document preview.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add fetchSjds / fetchSjdDetail to data.jsx | `4441b63` | `v2/frontend/src/data.jsx` |
| 2 | Browse SJDs action, SJD browser panel, SJD-03 warning, SJD provenance badge | `eea394c` | `v2/frontend/src/app.jsx`, `v2/frontend/src/document.jsx`, `v2/frontend/src/styles.css` |

## What Was Built

### Task 1 — Fetch helpers (`v2/frontend/src/data.jsx`)

Added two async fetch helpers immediately before the final `export` block, extending the existing export list:

```javascript
async function fetchSjds(ogCode = null) {
  const url = ogCode
    ? `/api/sjd?og_code=${encodeURIComponent(ogCode)}`
    : '/api/sjd';
  const r = await fetch(url);
  if (!r.ok) throw new Error(`fetchSjds: HTTP ${r.status}`);
  return r.json();
}

async function fetchSjdDetail(sjdNumber) {
  const r = await fetch(`/api/sjd/${encodeURIComponent(sjdNumber)}`);
  if (!r.ok) throw new Error(`fetchSjdDetail: HTTP ${r.status}`);
  return r.json();
}
```

Both URL-encode their inputs (T-22-02 mitigation). Both throw on non-2xx so callers handle errors explicitly.

### Task 2 — Browse SJDs surface + SJD browser panel + SJD-03 warning

**app.jsx changes:**

1. **Import:** `fetchSjds` added to the existing data.jsx import.

2. **State (4 new useState hooks):**
   ```javascript
   const [sjdPanelOpen, setSjdPanelOpen] = useState(false);
   const [sjdEntries, setSjdEntries] = useState([]);
   const [sjdOgFilter, setSjdOgFilter] = useState('');
   const [sjdLoading, setSjdLoading] = useState(false);
   ```

3. **SJD-03 warning inside `commit()` (after `setAnswers(newAnswers)`, before the WD persistence block):**
   ```javascript
   if (step.id === 'og_confirm' && record.sjd_source) {
     const newOgCode = typeof patch.confirmed_og === 'object'
       ? patch.confirmed_og?.og_code
       : patch.confirmed_og;
     const sjdOgCode = record.sjd_source?.og_code;
     if (newOgCode && sjdOgCode && newOgCode !== sjdOgCode) {
       setToast('Departing from the SJD classification turns this into a new evaluation — the SJD decision no longer applies');
       setTimeout(() => setToast(null), 7000);
     }
   }
   ```
   Comparison is on `og_code` only — `og_level`-only changes deliberately do NOT fire the warning (requirement).

4. **Three handler functions:**
   - `handleBrowseSjds()` — opens panel, fires initial fetch with current `sjdOgFilter` (or all groups)
   - `handleSjdFilterChange(ogCode)` — updates filter state, refetches
   - `handleSjdSelect(entry)` — POST `/api/wd/{wd_id}/sjd-start` with `{ sjd_number }`, mirrors `sjd_source` / `confirmed_og` / `og_level` / `duties` into record, fires 4s success toast or 3.5s error toast

5. **JSX — Browse SJDs button (after ActiveQuestion in the thread, before the right pane):**
   ```jsx
   {!reviewing && step.phase >= 1 && wd_id && (
     <div className="sjd-browse-action">
       <button className="btn-secondary" onClick={handleBrowseSjds}
               title="Browse DND Standard Job Descriptions">
         Browse SJDs
       </button>
     </div>
   )}
   ```

6. **JSX — SJD browser panel (modal overlay, alongside toast):**
   - Header with title + close (✕) button
   - OG-group filter dropdown (All groups / AS / EC / FI / IT / EN / PE / WP — matches the 7 normalized groups in SJD_LIBRARY)
   - Scrollable list of entries showing `title` + `group_level_str · noc_code · salary_range` + `organizational_context` truncated at 200 chars (T-22-05)
   - "Use this SJD" button per entry

**document.jsx changes:**

1. **SJD provenance badge in duty list:**
   ```jsx
   {d.source === 'sjd' && <span className="tag tag--sjd">SJD</span>}
   ```
   Inline before duty text, parallel to how NOC duties are marked by the section's `src` header.

2. **SJD prov tag in document footer:**
   ```javascript
   if (r.sjd_source) provTags.push('DND SJD Library');
   ```
   Sits alongside the NOC / JES / OG / DRF / Qualification / Advisor-added tags.

**styles.css additions:**

- `.sjd-browse-action` + `.btn-secondary` — subtle non-CTA action button
- `.sjd-panel-overlay` (fixed full-screen backdrop) + `.sjd-panel` (modal card) + `.sjd-entry` (per-entry card)
- `.tag--sjd` — uppercase mono badge, accent-soft background, distinct from other provenance markers
- `.prov__tag--sjd` — footer variant (parallel styling for visual consistency, currently unused but available)

## Verification

### Automated

| Check | Result |
|-------|--------|
| `npm run build` (v2/frontend) | exit 0 — 224.07 kB JS / 68.62 kB gzip, 28.03 kB CSS / 6.00 kB gzip |
| `npm test` (v2/frontend) | 60/60 pass (3 test files) |
| `pytest` (v2/backend) | 125/125 pass (no regressions) |
| `grep "async function fetchSjds" data.jsx` | matches (line 653) |
| `grep "async function fetchSjdDetail" data.jsx` | matches (line 667) |
| `grep "fetchSjds, fetchSjdDetail" data.jsx` | matches (line 679) |
| `grep "encodeURIComponent(ogCode)" data.jsx` | matches (line 655) |
| `grep "fetchSjds" app.jsx` | matches import + 2 usages (lines 5, 624, 638) |
| `grep "sjdPanelOpen" app.jsx` | matches useState + panel render (lines 97, 824) |
| `grep "sjd-start" app.jsx` | matches fetch call (line 650) |
| `grep "Departing from the SJD classification" app.jsx` | matches exact warning text (line 218) |
| `grep "step.id === 'og_confirm'" app.jsx` | matches SJD-03 guard inside commit() (line 212) |
| `grep "sjd_source" app.jsx` | matches 4 lines (warning guard + record update + comments) |
| `grep "Browse SJDs" app.jsx` | matches button text (line 791) |
| `grep "step.phase >= 1" app.jsx` | matches visibility condition (line 784) |
| `grep "tag--sjd\|source === 'sjd'" document.jsx` | matches SJD provenance badge (line 317) |

### Manual verification steps (pending human UAT)

The plan's `autonomous: false` flag and `checkpoint:human-verify` are post-execution. The following steps require a browser session:

1. Open the SPA in a browser.
2. Answer all 5 Role phase questions (title, branch, reports, reports_to_military, supervises).
3. Confirm "Browse SJDs" button appears below the active question.
4. Click "Browse SJDs" — confirm panel opens and shows 10 entries.
5. Filter by "EC" — confirm only 2 EC entries appear (DND-EC-58355 and DND-EC-58536).
6. Click "Use this SJD" on DND-EC-58355 — confirm "SJD applied" toast (4s) and panel closes.
7. Advance to og_confirm step — change OG to AS — confirm SJD-03 warning toast (7s) with exact text.
8. Advance to og_confirm step — keep OG as EC but change level — confirm NO warning toast.
9. Open document preview — confirm seeded duties have "SJD" provenance badge; confirm "DND SJD Library" tag in provenance footer.

## Deviations from Plan

None — plan executed exactly as written. All 8 change items (A through E in Task 2) implemented as specified.

### Minor implementation notes (not deviations)

- Added `DND SJD Library` prov tag in document.jsx footer for parity with the requirement that "every content element is traceable" (PROJECT.md non-negotiable). The plan's context section mentions SJD provenance but didn't explicitly require the footer tag; included as the natural extension of the SJD-02 requirement set.
- Added 4 toast texts (not in plan but discoverable from existing toast patterns): success (4s) for "SJD applied", error (3.5s) for "Could not apply SJD" / "Could not load SJDs" / "Complete at least the first Role step before browsing SJDs".
- SJD entry shows `group_level_str · noc_code · salary_range` (3 metadata fields). Plan suggested this format; all 3 fields are populated by the backend SJD_LIBRARY entries.

## Security Mitigations Applied

| Threat | Mitigation Applied | Location |
|--------|-------------------|----------|
| T-22-02 (Tampering of og_code query param) | `encodeURIComponent(ogCode)` in `fetchSjds` before URL construction | `data.jsx:655` |
| T-22-05 (Information disclosure via SJD organizational_context) | Truncated at 200 chars in panel UI with ellipsis when > 200 | `app.jsx:859` |
| T-22-06 (Spoofing via SJD-03 warning skipped) | Warning is advisory only — non-blocking, no backend enforcement, user can keep working | `app.jsx:208-221` |

## Files Modified

| File | Lines Added | Net Change | Description |
|------|------------|-----------|-------------|
| `v2/frontend/src/data.jsx` | +26 | 26/0 | Added `fetchSjds` + `fetchSjdDetail` + extended export block |
| `v2/frontend/src/app.jsx` | +122 / -0 | 122/0 | 4 useState hooks, SJD-03 warning, 3 handlers, Browse SJDs button, SJD panel modal |
| `v2/frontend/src/document.jsx` | +7 / -0 | 7/0 | SJD provenance badge in duty list + SJD prov tag in footer |
| `v2/frontend/src/styles.css` | +197 / -0 | 197/0 | `.sjd-panel-overlay`, `.sjd-panel`, `.sjd-entry`, `.tag--sjd`, `.btn-secondary`, `.sjd-browse-action` |

## Known Stubs

None. All features are fully implemented; the SJD browser panel renders against the live backend (10 SJD entries), sjd-start POSTs work end-to-end, and the SJD-03 toast is wired to `commit()`.

## Threat Flags

None new. All security-relevant surface from this plan is already covered by the plan's `<threat_model>` (T-22-02, T-22-05, T-22-06). No new endpoints, auth paths, file access patterns, or schema changes were introduced.

## TDD Gate Compliance

N/A — this is a frontend integration plan, not a TDD plan. No RED/GREEN/REFACTOR cycle required.

## Self-Check: PASSED

**Created files:** N/A (no new files created; all changes were modifications to existing files).

**Commit verification:**
- `4441b63` ✓ found in git log (Task 1)
- `eea394c` ✓ found in git log (Task 2)

**Build status:** exit 0 — 224.07 kB JS / 68.62 kB CSS bundle.

**Test status:** 60/60 frontend tests pass; 125/125 backend tests pass.

## Next Steps

Phase 22 Plan 04 is the final plan in Phase 22. After human UAT approval of the 9 manual verification steps above, the phase is complete and the SJD Library feature (SJD-01, SJD-02, SJD-03) is fully delivered.

- Phase 23 (Writing Guide Integration) is unblocked.
- Phase 24 (Risk Audit) is unblocked.
- Phase 25 (Accessible Template) is unblocked.
