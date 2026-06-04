---
phase: 13
status: flagged
depth: standard
reviewer: gsd-code-reviewer
files_reviewed: 12
findings:
  critical: 0
  major: 1
  minor: 1
  nit: 3
generated: 2026-06-04
---

# Phase 13 Code Review — Frontend SPA Shell

## Summary

12 files reviewed (3 created, 1 modified, 1 deleted in Plan 13-03; 5 created, 2 modified in Plans 13-01/13-02). 1 major finding (toast icon bug) was found and FIXED before this report. Remaining findings are minor/nit and do not block phase completion.

## Findings

| # | Severity | File:Line | Category | Description | Status |
|---|----------|-----------|----------|-------------|--------|
| F1 | major | v2/frontend/src/app.jsx:233 | bug | Toast icon used `path={'check'}` (string literal) instead of `path={I.check}` (SVG path data). The Icon component sets `__html` to the path string, so the literal text "check" would render inside the SVG, not a checkmark icon. | **FIXED** — replaced with `path={I.check}`; added `I` to the data.jsx imports. |
| F2 | minor | v2/frontend/src/app.test.jsx:54, 59, 69, 90 | test-quality | Several tests have names that suggest they verify specific state slice values ("record initialises to empty object", "answers, stepIndex, reviewing, editingReturn, toast initialise to defaults", "flashes initialises to an instance of Set"), but the assertions are weak smokes (`container.firstChild` is not null, or `.app` exists). The state slices are internal to App and hard to test directly without a refactor. | advisory |
| F3 | minor | v2/frontend/src/document.jsx:181-188 | style | Education/Experience labels have identical 5-property inline styles (fontFamily, fontSize, textTransform, letterSpacing, color). Could be a CSS class (`quals__k`) to reduce duplication. | advisory |
| F4 | nit | v2/frontend/vitest.setup.js:3, 30-31 | test-quality | `console.log` statements in the setup file pollute test output. These were added during debugging; safe to remove. | advisory |
| F5 | nit | v2/frontend/src/app.test.jsx:20-30 vs vitest.setup.js | test-quality | The in-test polyfill block (lines 20-30 in app.test.jsx) is a defensive no-op when the setupFile installs localStorage. The polyfill class `InMemoryStorage` in the test file is dead code. Either remove the in-test polyfill OR remove the setupFile. | advisory |
| F6 | nit | v2/frontend/src/components.jsx:18 | docs | The XSS-safety comment on the Icon component says "string literals from data.jsx — not user input; XSS-safe". Several call sites in conversation.jsx pass inline SVG path strings (e.g., the Continue arrow on line 92). The comment is technically accurate (all paths are compile-time constants) but slightly misleading because paths aren't all from data.jsx. | advisory |

## Per-File Analysis

### app.jsx
- ✅ React imports correct (named imports from `react`, no default React import needed in React 17+ JSX transform)
- ✅ 8 state slices initialise correctly; record uses lazy localStorage init with try/catch
- ✅ useEffect dependency arrays correct: `[record]` for persistence, `[stepIndex, reviewing]` for scroll, `[liveRecord, record, reviewing]` for cls
- ✅ useMemo dependency arrays correct
- ✅ ClassifyBadge correctly handles 'analyzing' status with progress ring
- ⚠️ Bug F1: toast icon used `'check'` instead of `I.check` — **FIXED**
- ⚠️ Minor: setTimeout in `flash()` could fire on unmounted component (low risk — App is root)

### conversation.jsx
- ✅ JSX conversions correct; no `React.createElement` leakage
- ✅ Named imports from data.jsx and components.jsx
- ✅ Inline Icon path strings (lines 92, 135, 139, 143) are compile-time constants — XSS-safe
- ✅ Brand block structure preserved
- ✅ Phase progress header with active/done states
- ⚠️ Nit: hardcoded single-quoted JSX attribute values for Icon paths (idiomatic; avoids escaping double quotes inside SVG)

### document.jsx
- ✅ JSX conversions correct
- ✅ Internal helpers (buildOverview, Ghost, Sec, ClassBlock, metaItem) correctly internal (not exported)
- ✅ DocumentPane renders 5 sections conditionally based on record shape
- ✅ Provenance footer tags built correctly
- ⚠️ Minor F3: Education/Experience label inline styles duplicated

### components.jsx
- ✅ Existing component, not modified in Plan 13-03 — verified XSS-safety comment in place
- ✅ Icon component uses `dangerouslySetInnerHTML` with compile-time constants only
- ✅ StepInput, Check, initialAnswer, answerValid all correct

### data.jsx
- ✅ Existing file, not modified in Plan 13-03 — exports match the imports in conversation.jsx, document.jsx, app.jsx
- ✅ `I.check`, `I.spark`, `QUAL_DEFAULT` all available

### app.test.jsx
- ✅ InMemoryStorage polyfill class correct
- ✅ beforeAll polyfills `HTMLElement.prototype.scrollTo` (jsdom omits it)
- ⚠️ Minor F2: Several test names overstate what the assertions verify
- ⚠️ Nit F5: In-test polyfill is redundant with vitest.setup.js

### vitest.config.js / vitest.setup.js
- ✅ Dedicated config file (workaround for vitest 4.x config discovery in subdirs)
- ✅ InMemoryStorage satisfies the Storage interface
- ⚠️ Nit F4: console.log statements in setup file

### vite.config.js
- ✅ Test block simplified to `setupFiles: []` (polyfill moved to vitest.config.js)
- ✅ No jsdom environment change (still in dedicated config)

### package.json
- ✅ `test` script invokes `vitest run --config ./vitest.config.js` for reproducibility

## Security Check

| Check | Result | Notes |
|-------|--------|-------|
| `dangerouslySetInnerHTML` only on compile-time constants | PASS | Icon component: paths are string literals (from data.jsx OR inline in JSX); active question helper: `step.helper` could be a function but prototype data is hardcoded |
| localStorage key origin-scoped | PASS | `jd-builder-v2-record` is browser-local; no cross-origin data |
| localStorage quota handling | PASS | try/catch wraps setItem; quota errors are silently swallowed |
| Corrupt localStorage JSON | PASS | lazy initializer catches JSON.parse errors; falls back to `{}` |
| React keys in lists | PASS | phase `key={p}`, factor `key={f.name}`, duty `key={d.id}`, indicator `key={i}` |
| XSS in user input | PASS | no user input is rendered as HTML; only as text via JSX interpolation (auto-escaped) |

## React Hook Correctness

| Hook | Usage | Verdict |
|------|-------|---------|
| `useState` | 8 slices with correct initial values | PASS |
| `useRef` | `threadRef`, `docRef` for DOM access | PASS |
| `useEffect` | localStorage persistence (dep: `[record]`), scroll-to-bottom (dep: `[stepIndex, reviewing]`) | PASS |
| `useMemo` | liveRecord (dep: `[record, draft, step]`), cls (dep: `[liveRecord, record, reviewing]`) | PASS |

No dependency-array warnings, no infinite-loop risk.

## JSX Correctness

- ✅ Zero `React.createElement` calls in conversation.jsx, document.jsx, app.jsx
- ✅ Zero `window.*` global references in conversation.jsx, document.jsx, app.jsx
- ✅ No `\uXXXX` escape sequences in JSX text (would render as literal characters) — all unicode characters are either in JS string literals (where escapes are valid) or actual unicode characters in JSX text
- ✅ Template literals for className concatenation work correctly

## Test Reliability

- ✅ InMemoryStorage correctly implements Storage interface
- ✅ Tests have `beforeEach`/`afterEach` to reset storage between tests
- ✅ No race conditions (no async, no setTimeout in tests)
- ⚠️ F2: Some tests have weak assertions relative to their names
- ⚠️ F5: Polyfill redundancy is a maintenance concern (not a correctness issue)

## Recommendations

1. **F1** (FIXED) — toast icon now uses `I.check` SVG path data
2. **F2** (advisory) — consider strengthening test assertions, e.g., check that `data-` attributes or specific text appears in the rendered output
3. **F3** (advisory) — extract Education/Experience label styles to a CSS class in styles.css (would require re-porting plan amendment)
4. **F4** (nit) — remove `console.log` statements from vitest.setup.js
5. **F5** (nit) — choose one polyfill location: either vitest.setup.js OR the in-test polyfill, not both
6. **F6** (nit) — clarify the XSS comment in components.jsx to acknowledge inline Icon path strings (or move all paths to data.jsx `I.*` exports)

## Self-Check: PASSED (with 1 fix)
