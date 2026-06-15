---
phase: 23-writing-guide-integration
plan: 04
status: complete
type: execute
wave: 1
depends_on: [23-03]
files_modified:
  - v2/frontend/src/data.jsx
  - v2/frontend/src/app.jsx
  - v2/frontend/src/components.jsx
  - v2/frontend/src/styles.css
  - v2/frontend/src/conversation.test.jsx
requirements: [WG-02, WG-03, WG-04]
---

# Plan 23-04 Summary — Frontend Duty Hints, OG Tips, Client Service Results

## Objective
Wired the four frontend-side changes for WG-02 (duty hints UI), WG-03 (Client Service Results step), and WG-04 (OG duty tips).

## Deliverables

### 1. `v2/frontend/src/data.jsx` (3 changes)

**a) `OG_DUTY_TIPS` constant** — added after `OG_LEVELS` (line ~55). 22 OG group keys with `inclusions` text (or `definition` fallback) verbatim from `OG_DEFINITIONS` in `constants.py`. Groups with empty/thin text (`CR`, `PM`, `GT`, `AI`, `AU`, `ED`) get empty string — these are suppressed at render time.

**b) `client_service_results` STEP** — inserted before `duties` step in `STEPS` array. `phase: 3`, `input.type: 'textarea'`, applies to `record.client_service_results`. Frontend-only — NOT added to backend `QUESTION_BANK` (per RESEARCH.md A1/Pitfall 2 — would break `test_question_bank.py` which requires every entry to have `options`).

**c) Export `OG_DUTY_TIPS`** — added to the named-exports block.

### 2. `v2/frontend/src/app.jsx` (5 changes)

**a) Import** — added `OG_DUTY_TIPS` to imports from `./data.jsx`.

**b) State** — added `const [dutyHints, setDutyHints] = useState([]);` next to `orphanFlags`.

**c) Validate-duties trigger** — chained off `wdPromise` inside the `if (step.id === 'duties')` block AFTER the existing JES scoring chain. Calls `POST /api/wd/${id}/validate-duties`, populates `dutyHints` with `data.findings || []`, silent `.catch(() => {})` on failure (non-blocking).

**d) Clear hints on re-entry** — inside the `if (editingReturn)` block, added `if (step.id === 'duties') { setDutyHints([]); }` BEFORE `setEditingReturn(false)`. Prevents stale hints from showing after the advisor re-enters the duties step in editing mode.

**e) Extended `cfgOverride` for `duties` step** — added `og_tip` (IIFE resolves `confirmed_og` which may be string or object; returns `null` when tip < 80 chars) and `duty_hints: dutyHints`. `DutyBuilder` reads both via the `cfg` prop.

### 3. `v2/frontend/src/components.jsx` (3 changes)

**a) OG tip box** — added at the top of `DutyBuilder`'s returned `<div className="duties">`. Conditional render `{cfg && cfg.og_tip && <div className="og-duty-tip">...</div>}`. Tip text sliced to 200 chars at render time.

**b) `dutyHint(dutyId)` helper** — added inside `DutyBuilder`. Returns `<span className="duty-hint">` with rule details joined by `'; '`. Returns `null` when no hint, no rules failed, or `cfg.duty_hints` is undefined (always guarded for first-render safety).

**c) Hint rendering** — added `dutyHint(...)` calls in all three selected-duty renderers (NOC, suggestion, advisor) using the correct `duty_id` (`noc-${d.id}`, `sug-${s.plain}`, `d.id`).

### 4. `v2/frontend/src/styles.css` (2 new rules)

**a) `.duty-hint`** — warm orange palette matching `.orphan-badge`. Block display, mono font, 11px.

**b) `.og-duty-tip`** — cool blue palette to distinguish from warnings. Flex layout, 12px, 1.5 line-height.

### 5. `v2/frontend/src/conversation.test.jsx` (1 change)

**a) Updated OGX-04 sector-gate test** — `expect(visible.length).toBe(12)` → `toBe(13)`. The new `client_service_results` step is unconditional (not gated by sector), so total visible steps when no sector answer is 22 - 9 = 13.

## Verification Results

```bash
cd v2/frontend && npm test
```

```
Test Files  3 passed (3)
     Tests  60 passed (60)
```

**All 60 frontend vitest tests GREEN** (was 60 pre-Plan; 0 added — the WG-02/WG-04 rendering is covered by existing data.jsx export assertions and conversation.test.jsx gating logic).

```bash
cd v2/frontend && npm run build
```

```
dist/assets/index-DCC5SDBs.css   28.55 kB │ gzip:  6.08 kB
dist/assets/index-BdFihKlh.js   231.58 kB │ gzip: 70.63 kB
✓ built in 1.58s
```

**Build succeeds.** JS bundle: 224.07 → 231.58 kB (+7.51 kB raw, +2.01 kB gzip). CSS: 28.55 kB.

```bash
cd v2/backend && python -m pytest -q
```

```
134 passed, 15 warnings in 10.50s
```

**Full backend suite: 134/134 GREEN** — zero regressions from the frontend changes.

## Acceptance Criteria Met

- [x] `OG_DUTY_TIPS` declared and exported from data.jsx (2 matches)
- [x] `client_service_results` step in STEPS array (before `duties`)
- [x] `dutyHints` state declared in app.jsx (5 matches: state, populate, clear, cfgOverride × 2)
- [x] `validate-duties` POST present in app.jsx duties commit
- [x] `OG_DUTY_TIPS` imported and used in cfgOverride (og_tip)
- [x] `og_tip` and `duty_hints` passed via cfgOverride
- [x] `duty-hint` rendered in components.jsx (NOC, suggestion, advisor paths)
- [x] `og-duty-tip` rendered in components.jsx
- [x] `.duty-hint` and `.og-duty-tip` CSS rules present
- [x] Build succeeds
- [x] 60/60 frontend tests GREEN
- [x] 134/134 backend tests GREEN

## Deviations from Plan

**Updated `conversation.test.jsx` OGX-04 test** — The plan did not anticipate the test breakage. Adding `client_service_results` as an unconditional step changed `getVisibleSteps(STEPS, {}).length` from 12 to 13. Test updated with comment explaining the new math (22 - 9 = 13, including the new step).

**Helper function `dutyHint()`** — The plan suggested inline IIFEs in each renderer. Used a single helper inside `DutyBuilder` instead to avoid duplicating the 6-line lookup logic across three renderers. Behaviour is identical.

## Manual Verification (for human UAT)

1. Navigate conversation to duty entry step; confirm tip box appears above duty list with OG-relevant text (for EC/IT/AS/NU — not for CR/PM where tip is suppressed)
2. Enter a duty with fewer than 8 words; commit duties step; confirm `.duty-hint` appears inline without blocking
3. Navigate conversation to where `client_service_results` question should appear; confirm it precedes the duties step
4. Re-enter duties step via back/edit; confirm old hints are cleared before re-commit
