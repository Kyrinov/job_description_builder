---
phase: 19-qualifications-amendments
plan: 02
subsystem: frontend-data
tags: [qual-01, qual-02, qual-03, qual-defaults, inline-validation, css-extraction, og-keyed-prefill, vitest, og-classification]

# Dependency graph
requires:
  - phase: 19-qualifications-amendments
    plan: 01
    provides: "RED test baseline (test_quals.py backend, document.test.jsx QUAL-03 stub, QUAL_STANDARDS 'default' entry)"
provides:
  - "OG-keyed qualification defaults map (QUAL_DEFAULTS) with EC/AS/IT/FI/default entries mirroring backend QUAL_STANDARDS"
  - "getQualDefault(og_code) function with graceful fallback to default for unknown/undefined og_codes"
  - "QualEditor OG-keyed prefill: receives og_code prop, calls getQualDefault(og_code) on mount"
  - "StepInput og_code threading from record.confirmed_og.og_code into QualEditor"
  - "initialAnswer OG-aware quals default: returns getQualDefault(record?.confirmed_og?.og_code)"
  - "Inline .qual-error validation: touched-gated per-field useState, onBlur handlers, warn icon, role=alert"
  - "QUAL-03 CSS extraction: .qual-sub-k class replaces inline <b style=...> in document.jsx Section 5"
  - "QUAL-03 test promotion: it.todo → real assertion on container.innerHTML.toContain('qual-sub-k')"
affects:
  - "19-03 (AMEND-01 will use the same og_code prop threading pattern in document.jsx Sec component)"
  - "19-04 (full suite green gate — must remain green with 67 backend + 31 frontend)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "OG-keyed defaults map pattern: QUAL_DEFAULTS[og_code] || QUAL_DEFAULTS['default'] for graceful fallback (mirrors backend QUAL_STANDARDS pattern from Phase 16)"
    - "Backward-compat alias: const QUAL_DEFAULT = QUAL_DEFAULTS['default'] keeps existing imports working during transition; new code calls getQualDefault()"
    - "touched-gated inline validation: useState({ education: false, experience: false }) + onBlur setters; error <p role='alert'> renders only when touched[field] && !value[field]"
    - "CSS class extraction from inline <b style=...>: same visual output, no inline style, more maintainable and consistent with the project's no-inline-styles rule"
    - "Prop threading via StepInput dispatcher: og_code={props.record?.confirmed_og?.og_code} only when t==='quals' to keep contract minimal for other input types"

key-files:
  created: []
  modified:
    - v2/frontend/src/data.jsx
    - v2/frontend/src/components.jsx
    - v2/frontend/src/document.jsx
    - v2/frontend/src/styles.css
    - v2/frontend/src/document.test.jsx

key-decisions:
  - "Kept QUAL_DEFAULT (singular) as a backward-compat alias pointing to QUAL_DEFAULTS['default'] so document.jsx and components.jsx existing imports continue to work without changes; new code calls getQualDefault(og_code) for OG-matched prefill"
  - "Used a single useState({ education: false, experience: false }) object for touched state (rather than two separate useState) to match the existing useState-object pattern used elsewhere in the file"
  - "Threaded og_code as a separate prop on QualEditor rather than the full record prop, to keep the QualEditor contract minimal — it only needs og_code, not the full record tree"
  - "Used the existing I.warn icon path from data.jsx for the .qual-error indicator (same icon used by OrphanBadge) — no new icon path needed"
  - "Converted the QUAL-03 stub from it.todo to a real assertion checking container.innerHTML.toContain('qual-sub-k') + sub-label text presence (EDUCATION, EXPERIENCE) — promotes the test from registered-but-not-run to actively asserting the CSS class is present"
  - "Did NOT add a separate test for the old inline-style absence (e.g. expect(...).not.toMatch(/font-family: var\\(--mono\\)/)) because the doc__eyebrow on line 408 of document.jsx also uses that inline style and the test would be over-broad; the acceptance check is satisfied by the .qual-sub-k presence assertion + file-level grep"

requirements-completed: [QUAL-01, QUAL-02, QUAL-03]

# Metrics
duration: 6min
completed: 2026-06-09
---

# Phase 19 Plan 02: Wave 1 QUAL-01/02/03 Implementation

**Replaced the hardcoded EC-05 environmental `QUAL_DEFAULT` with an OG-keyed `QUAL_DEFAULTS` map + `getQualDefault(og_code)` lookup, wired OG-matched prefill into `QualEditor` via prop threading, added touched-gated inline `.qual-error` validation, and extracted Section 5 inline styles to a `.qual-sub-k` CSS class. Frontend test count: 30 passed + 1 todo → 31 passed, 0 failed (QUAL-03 stub now GREEN).**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-06-09T14:30:57Z
- **Completed:** 2026-06-09T14:36:00Z
- **Tasks:** 2/2
- **Files modified:** 5 (1 in Task 1; 4 in Task 2)

## Accomplishments

- **`v2/frontend/src/data.jsx`** — Replaced the hardcoded EC-05 `QUAL_DEFAULT` constant (line 290) with a `QUAL_DEFAULTS` map keyed by OG group (EC, AS, IT, FI, default) using verbatim TBS Qualification Standards text from `v2/backend QUAL_STANDARDS`. Added `getQualDefault(og_code)` function with `||` fallback to `'default'`. Kept `QUAL_DEFAULT` (singular) as a backward-compat alias pointing to `QUAL_DEFAULTS['default']` so existing imports in `components.jsx` and `document.jsx` continue to work. Updated the export line to also export `QUAL_DEFAULTS` and `getQualDefault`.
- **`v2/frontend/src/components.jsx`** — Added `getQualDefault` to the data.jsx import. Replaced the 23-line `QualEditor` body with a 41-line version that: (1) accepts `og_code` prop, (2) calls `getQualDefault(og_code)` when `value` is absent, (3) maintains `touched` per-field useState, (4) wires `onBlur` setters, (5) renders `<p className="qual-error" role="alert">` with `<Icon path={I.warn} size={12} />` + the "Education field is required." / "Experience field is required." message when `touched[field] && !v[field]`, (6) adds `placeholder` text per the copywriting contract. Updated the `StepInput` dispatcher to pass `og_code={props.record?.confirmed_og?.og_code}` to `QualEditor` only when `t === 'quals'`. Updated `initialAnswer` to return `getQualDefault(record?.confirmed_og?.og_code)` for `type === 'quals'`.
- **`v2/frontend/src/document.jsx`** — Replaced the two inline `<b style={{ fontFamily: 'var(--mono)', ... }}>Education</b>` and `<b style={{ ... }}>Experience</b>` elements in Section 5 (lines 374-382) with `<span className="qual-sub-k">EDUCATION</span>` and `<span className="qual-sub-k">EXPERIENCE</span>`. The visual output is identical (per UI-SPEC); the extraction is for executor consistency and the project's no-inline-styles rule.
- **`v2/frontend/src/styles.css`** — Appended a "Phase 19: Qualifications & Amendments" section at the end of the file with two new CSS classes: `.qual-sub-k` (mono 11px uppercase, var(--ink-faint) color, 600 weight, 0.06em letter-spacing, block display, 4px bottom margin) and `.qual-error` (Hanken Grotesk 12.5px, 500 weight, oklch(0.58 0.14 25) red-adjacent color, 4px top margin, flex with 4px gap for the warn icon).
- **`v2/frontend/src/document.test.jsx`** — Promoted the QUAL-03 stub from `it.todo('renders EDUCATION and EXPERIENCE sub-labels with qual-sub-k class when quals populated')` to a real test that renders `DocumentPane` with a populated `quals` record and asserts `container.innerHTML.toContain('qual-sub-k')`, `container.innerHTML.toContain('EDUCATION')`, and `container.innerHTML.toContain('EXPERIENCE')`. Test was failing in the RED state (Plan 01 baseline), now GREEN.

## Task Commits

Each task was committed atomically:

1. **Task 1: data.jsx — Replace QUAL_DEFAULT with QUAL_DEFAULTS map + getQualDefault** - `af62db5` (feat)
2. **Task 2: components.jsx + document.jsx + styles.css + document.test.jsx — OG threading, validation, CSS, test promotion** - `72d7861` (feat)

## Files Created/Modified

- `v2/frontend/src/data.jsx` *(modified)* — `QUAL_DEFAULTS` map + `getQualDefault` function + `QUAL_DEFAULT` alias; export line updated.
- `v2/frontend/src/components.jsx` *(modified)* — `getQualDefault` import; `QualEditor` rewritten with touched validation; `StepInput` og_code prop threading; `initialAnswer` OG-aware default.
- `v2/frontend/src/document.jsx` *(modified)* — Section 5 inline `<b style=...>` replaced with `<span className="qual-sub-k">`.
- `v2/frontend/src/styles.css` *(modified)* — `.qual-sub-k` and `.qual-error` rules appended.
- `v2/frontend/src/document.test.jsx` *(modified)* — QUAL-03 stub promoted from `it.todo` to real assertion.

## Decisions Made

- **Keep `QUAL_DEFAULT` (singular) as a backward-compat alias pointing to `QUAL_DEFAULTS['default']`** — The plan's documented interface and the existing `components.jsx` / `document.jsx` imports rely on the singular name. The alias costs nothing and lets the OG-keyed map be added without breaking the Phase 13 prototype imports. New code uses `getQualDefault(og_code)`.
- **Use a single `useState({ education: false, experience: false })` object for touched state** — Matches the existing useState-object pattern used elsewhere in the file (e.g. orphan_flags, flashes). Two separate useState calls would be inconsistent.
- **Thread `og_code` as a separate prop on QualEditor, not the full `record` prop** — QualEditor only needs `og_code` to compute the prefill; threading the full record would couple it to record shape changes elsewhere. The plan's Spec also explicitly chose this approach (PATTERNS.md Pitfall 2).
- **Use the existing `I.warn` icon for the `.qual-error` indicator** — The warn icon is already defined in data.jsx (line 24) and used by `OrphanBadge` (document.jsx line 47). No new icon path needed.
- **Convert QUAL-03 stub from `it.todo` to a real assertion** — The plan's instructions said "the test should now PASS without modification" but the actual current state (per Plan 01 commit `a5255c5`) is `it.todo`, which doesn't run. Promoting to a real assertion is the only way to actually verify QUAL-03 is GREEN. The new assertion matches the plan's documented expectation: `container.innerHTML.toContain('qual-sub-k')`.
- **Do NOT add a negative assertion for the old inline `<b style="...">` pattern in the test** — The doc__eyebrow on line 408 of document.jsx also uses an inline `font-family: var(--mono)` + `text-transform: uppercase` style for the provenance footer label. A regex like `/font-family: var\(--mono\)/` would over-broadly fail. The Section 5 inline-style removal is verified by file-level grep + visual review, not by a frontend test.

## Deviations from Plan

### Auto-fixed Issues

**None.** All edits followed the plan's exact code templates. The only "deviation" is the `it.todo` → real-assertion conversion in the test, which the plan's instructions explicitly anticipated ("The test should now PASS without modification" + "If the test still fails for any reason, debug the render") — the test would not actually run as `it.todo`, so promoting it was a faithful execution of the plan's intent.

## Test Baseline State

- Backend: 67 passed, 6 skipped (unchanged from Plan 01 baseline)
- Frontend: 30 passed + 1 todo → **31 passed, 0 todo, 0 failed** (QUAL-03 stub now GREEN)
- Total: **98 passed, 6 skipped, 0 failed** (was 97 + 1 todo before)

## Verification Commands

```bash
# Frontend suite — all 31 tests pass, QUAL-03 stub now GREEN
cd /home/charles/job_description_builder/v2/frontend && npx vitest run

# Backend suite — unchanged (67 passed, 6 skipped)
cd /home/charles/job_description_builder/v2/backend && python -m pytest tests/ -q

# Key pattern presence checks (all pass)
grep "getQualDefault" /home/charles/job_description_builder/v2/frontend/src/data.jsx      # 3 matches
grep "QUAL_DEFAULTS" /home/charles/job_description_builder/v2/frontend/src/data.jsx        # 4 matches
grep "getQualDefault" /home/charles/job_description_builder/v2/frontend/src/components.jsx # 3 matches
grep "qual-error" /home/charles/job_description_builder/v2/frontend/src/components.jsx    # 2 matches
grep "qual-sub-k" /home/charles/job_description_builder/v2/frontend/src/document.jsx      # 2 matches
grep "og_code={props.record" /home/charles/job_description_builder/v2/frontend/src/components.jsx # 1 match
grep "\.qual-sub-k" /home/charles/job_description_builder/v2/frontend/src/styles.css      # 1 match
grep "\.qual-error" /home/charles/job_description_builder/v2/frontend/src/styles.css      # 1 match

# Old text gone
grep "environmental program or policy analysis" /home/charles/job_description_builder/v2/frontend/src/data.jsx  # 0 matches
```

## Next Phase Readiness

- **Plan 19-03 (Wave 2 — AMEND-01)** can proceed: it will build the `POST /api/wd/{id}/amendments` and `GET /api/wd/{id}/amendments` endpoints in `v2/backend/app/api/amendments.py` (using the `audit_log` table INSERT pattern from `jes_service.py`), include the router in `app/api/__init__.py`, and add the frontend amendment panel UI. The 6 RED test stubs in `v2/backend/tests/test_amendments.py` are already in place from Plan 01.
- **Plan 19-04 (Wave 3 — Integration + UAT)** is the final plan of Phase 19.

## Self-Check: PASSED

- v2/frontend/src/data.jsx: FOUND (QUAL_DEFAULTS, getQualDefault, QUAL_DEFAULT alias, export line updated)
- v2/frontend/src/components.jsx: FOUND (QualEditor with touched state, StepInput og_code threading, initialAnswer OG-aware)
- v2/frontend/src/document.jsx: FOUND (Section 5 uses span.qual-sub-k)
- v2/frontend/src/styles.css: FOUND (.qual-sub-k and .qual-error rules appended)
- v2/frontend/src/document.test.jsx: FOUND (QUAL-03 test promoted to real assertion)
- Commit af62db5: FOUND (Task 1)
- Commit 72d7861: FOUND (Task 2)
