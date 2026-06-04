# Phase 13: Frontend SPA Shell — Research

**Researched:** 2026-06-04
**Domain:** React 18 / Vite SPA — prototype port, brand typography, client-side state, localStorage
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FE-01 | React 18 SPA in Vite; multi-file structure mirrors prototype: `app.jsx`, `data.jsx`, `conversation.jsx`, `document.jsx`, `components.jsx`, `styles.css` | File-by-file mapping documented; IIFE→ESM module conversion pattern established |
| FE-03 | Brand styling: Hanken Grotesk, Spectral, Spline Sans Mono; layered CSS scoped to `.app`, `.convo`, `.preview`, `.doc`; visual fidelity to prototype | Full CSS already authored; Google Fonts import pattern documented; no new CSS work needed |
| FE-04 | Client-side state: `useState` + `useMemo` only; seven state slices; no Redux/Zustand | State shape extracted verbatim from prototype `app.jsx`; useMemo patterns confirmed |
| FE-05 | Persist draft WD to localStorage on every step commit; restore on reload; crash-recovery | localStorage JSON pattern documented; useEffect trigger point identified (inside `commit()`) |
</phase_requirements>

---

## Summary

The prototype in `Job Description Builder/jd-builder/` is a fully working React 18 SPA written as a browser-global IIFE bundle (five `.jsx` files + one `styles.css`). The files use `React.createElement` throughout, communicate via `window.JD_DATA`, `window.JD_COMP`, `window.JD_CONVO`, and `window.JD_DOC` globals, and are loaded in a specific dependency order by the HTML file. The Vite project in `v2/frontend/` already has React 18 + Vite 5 installed with the proxy wired (FE-02, validated Phase 10).

Phase 13 is a **module conversion port**, not a rewrite. Every component, every CSS rule, and every data constant from the prototype is preserved verbatim; only the module system changes (IIFE globals → ES module imports/exports) and JSX syntax replaces `React.createElement`. The five files become five ES modules; `styles.css` replaces `src/index.css`. State lives in `App` in `app.jsx` exactly as in the prototype.

Two things are added that the prototype does not have: (1) a Google Fonts `<link>` in `index.html` to load the three brand typefaces, and (2) a `useEffect` in `App` that calls `localStorage.setItem` after every `commit()` and a lazy initializer that restores from `localStorage` on first render.

**Primary recommendation:** Convert the prototype IIFE files to ES module syntax one file at a time, in dependency order (data → components → conversation → document → app). Replace global window assignments with named exports/imports. Swap `React.createElement` calls for JSX. Add brand font `<link>` to `index.html`. Add localStorage persistence in `App`. No third-party libraries needed.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| App shell layout (.app grid) | Browser / Client | — | 100vh CSS grid, no server rendering |
| Client-side conversation state | Browser / Client | — | useState/useMemo in App; no API calls in this phase |
| Live document preview | Browser / Client | — | DocumentPane is pure render from in-memory state |
| Brand typography | Browser / Client | — | Google Fonts loaded in HTML head; CSS custom properties |
| localStorage crash-recovery | Browser / Client | — | localStorage API; no backend involvement |
| API proxy | Frontend Server (Vite) | — | Already configured in vite.config.js; not touched this phase |

---

## Standard Stack

### Core (already installed — `v2/frontend/package.json`)

| Library | Installed Version | Purpose | Status |
|---------|-------------------|---------|--------|
| react | ^18.3.1 | Component model, hooks | [VERIFIED: package.json] |
| react-dom | ^18.3.1 | DOM rendering via createRoot | [VERIFIED: package.json] |
| vite | ^5.4.10 | Dev server, HMR, build | [VERIFIED: package.json] |
| @vitejs/plugin-react | ^4.3.4 | JSX transform + Fast Refresh | [VERIFIED: package.json] |

### No new dependencies required

The prototype uses only React hooks (`useState`, `useRef`, `useEffect`, `useMemo`) and the native browser `localStorage` API. No additional npm packages are needed for this phase.

**Brand fonts** are loaded via Google Fonts CDN — a `<link>` tag in `index.html`, not an npm package.

**Installation:**
```bash
# Nothing to install — all dependencies are already present in v2/frontend/
```

---

## Architecture Patterns

### System Architecture Diagram

```
index.html
  └─ <link> Google Fonts (Hanken Grotesk, Spectral, Spline Sans Mono)
  └─ <script type="module"> src/main.jsx

src/main.jsx
  └─ import App from './app.jsx'
  └─ import './styles.css'
  └─ createRoot(document.getElementById('root')).render(<App />)

src/app.jsx   [state owner]
  ├─ import { STEPS, PHASES, computeClassification, … } from './data.jsx'
  ├─ import { initialAnswer, answerValid } from './components.jsx'
  ├─ import { Header, Exchange, ActiveQuestion, ReviewState } from './conversation.jsx'
  ├─ import { DocumentPane } from './document.jsx'
  │
  ├─ useState: record, answers, stepIndex, draft, reviewing, editingReturn, flashes, toast
  ├─ useMemo: liveRecord (record + draft patch), cls (computeClassification)
  ├─ useEffect: auto-scroll threadRef on stepIndex/reviewing change
  ├─ useEffect: localStorage.setItem on record change (crash-recovery)
  └─ lazy useState initializer: restore record from localStorage on mount

src/data.jsx  [data + logic, no React]
  └─ export: I (icons), STEPS, PHASES, DRF, WORK_TYPES,
             DUTY_SUGGESTIONS, QUAL_DEFAULT, EC_ELEMENTS,
             computeClassification, refineDuty, ecFactors

src/components.jsx  [shared input controls]
  └─ import from './data.jsx'
  └─ export: Icon, Check, StepInput, initialAnswer, answerValid
  └─ sub-components (internal): TextInput, ChoiceList, ScaleInput,
                                 DutyBuilder, DrfPicker, QualEditor

src/conversation.jsx  [left pane]
  └─ import from './data.jsx' + './components.jsx'
  └─ export: Header, Exchange, ActiveQuestion, ReviewState

src/document.jsx  [right pane]
  └─ import from './data.jsx' + './components.jsx'
  └─ export: DocumentPane
  └─ internal: buildOverview, Ghost, Sec, ClassBlock, metaItem

src/styles.css  [replaces src/index.css]
  └─ :root CSS custom properties (colors, fonts, shadows, radius)
  └─ .app, .convo, .preview, .doc, .thread, .ask, .choices, …
```

### Recommended File Structure

```
v2/frontend/
├── index.html          # Add Google Fonts <link> here
└── src/
    ├── app.jsx         # App component + state + localStorage (replaces placeholder)
    ├── data.jsx        # Data constants + classification engine (new)
    ├── conversation.jsx # Convo pane components (new)
    ├── document.jsx    # Document pane components (new)
    ├── components.jsx  # Shared input controls (new)
    ├── styles.css      # Brand CSS (replaces index.css)
    └── main.jsx        # Entry point — update import from './App.jsx' → './app.jsx'
                        # and add import './styles.css'
```

### Pattern 1: IIFE Global → ES Module Conversion

**What:** The prototype wraps each file in `(function() { ... window.JD_X = {...}; })()`. In the Vite port, the IIFE wrapper is removed, `window.JD_X = {...}` becomes `export { ... }`, and consumers `import { ... } from './x.jsx'` instead of reading `window.JD_X`.

**Before (prototype):**
```js
// data.jsx — prototype
(function () {
  const I = { spark: '...', check: '...' };
  // ...
  window.JD_DATA = { I, STEPS, PHASES, DRF, WORK_TYPES, computeClassification, refineDuty, ecFactors };
})();
```

**After (Vite module):**
```js
// data.jsx — Vite
const I = { spark: '...', check: '...' };
// ...
export { I, STEPS, PHASES, DRF, WORK_TYPES, DUTY_SUGGESTIONS, QUAL_DEFAULT,
         EC_ELEMENTS, computeClassification, refineDuty, ecFactors };
```
[VERIFIED: codebase — window.JD_DATA pattern confirmed in all 4 non-app prototype files]

### Pattern 2: React.createElement → JSX

**What:** The prototype avoids JSX (it ran in a plain `<script>` tag). Vite with `@vitejs/plugin-react` supports JSX in `.jsx` files; the conversion is mechanical.

**Before:**
```js
React.createElement('div', { className: 'ask' },
  React.createElement('div', { className: 'ask__row' }, ...))
```

**After:**
```jsx
<div className="ask">
  <div className="ask__row">...</div>
</div>
```

### Pattern 3: localStorage Crash-Recovery

**What:** Persist `record` to localStorage on every commit. Restore on mount.

**How:** Two hooks in `App`:

```jsx
// Lazy initializer — restore on first mount
const [record, setRecord] = useState(() => {
  try {
    const saved = localStorage.getItem('jd-builder-v2-record');
    return saved ? JSON.parse(saved) : {};
  } catch {
    return {};
  }
});

// Persist on every record change
useEffect(() => {
  try {
    localStorage.setItem('jd-builder-v2-record', JSON.stringify(record));
  } catch {
    // quota exceeded — silent fail, not crash-worthy
  }
}, [record]);
```

**Key:** The `record` state contains only serializable values (strings, numbers, plain objects, arrays). The prototype confirms this — `record` is built by `step.apply()` functions that return plain patches. No DOM refs, functions, or React elements are ever stored in `record`.
[VERIFIED: codebase — all STEPS[*].apply() return plain JS objects]

### Pattern 4: Google Fonts via `<link>` in index.html

**What:** The brand typefaces are loaded from Google Fonts. No npm package is needed.

```html
<!-- index.html — add inside <head> -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;550;600;650;680;700;720;750&family=Spectral:ital,wght@0,400;0,600;0,700;1,400&family=Spline+Sans+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

The CSS already references these via `var(--ui)`, `var(--doc)`, `var(--mono)` custom properties:
```css
--ui:   "Hanken Grotesk", system-ui, sans-serif;
--doc:  "Spectral", Georgia, serif;
--mono: "Spline Sans Mono", ui-monospace, monospace;
```
[VERIFIED: codebase — styles.css :root block confirms all three font names]

### Pattern 5: main.jsx update

The existing `main.jsx` imports `'./App.jsx'` (capital A) and `'./index.css'`. Both must be updated:

```jsx
// src/main.jsx — updated
import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './app.jsx'    // lowercase — matches new file
import './styles.css'           // replaces index.css

const root = createRoot(document.getElementById('root'))
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

**Note:** `index.css` should be deleted (or left as empty); `styles.css` is the replacement.
[VERIFIED: codebase — main.jsx confirmed at v2/frontend/src/main.jsx]

### Anti-Patterns to Avoid

- **Rewriting the classification engine:** `computeClassification` and `ecFactors` in `data.jsx` are the prototype's hardcoded logic. Phase 13 ports them verbatim. The v1.0 engine replaces this logic in Phase 16 — not here.
- **Splitting components into many files:** The prototype deliberately co-locates all input controls in `components.jsx` and all doc sections in `document.jsx`. Keep this structure for fidelity.
- **Using React.lazy or Suspense:** The app is small; no code-splitting is needed and would add complexity without benefit.
- **Storing non-serializable values in `record`:** The `flashes` state is a `Set` — do NOT persist it to localStorage. Only `record` (and optionally `answers`, `stepIndex`) is safe to persist.
- **Renaming `window.JD_DATA` references before removing them:** Remove the global assignment entirely; don't leave dangling `window.JD_DATA` reads in converted files.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSX compilation | Custom transform | @vitejs/plugin-react (already installed) | Handles JSX + Fast Refresh |
| Font loading | Self-hosted font files | Google Fonts `<link>` | Fonts already designed into CSS vars; CDN is simpler |
| State management | Custom pub/sub or store | React useState + useMemo | Prototype proves this is sufficient; Redux adds no value for single-user app |
| localStorage serialization | Custom binary format | JSON.stringify/parse with try/catch | Record contains only plain JS; JSON is sufficient |

---

## Common Pitfalls

### Pitfall 1: Case-sensitivity on Linux for file imports

**What goes wrong:** Vite on Linux is case-sensitive. The existing `main.jsx` imports `'./App.jsx'` (capital A). The new file will be `app.jsx` (lowercase). If `main.jsx` is not updated, Vite will throw a 404 on the module import.

**Why it happens:** macOS HFS+ is case-insensitive; the prototype was probably developed there. Linux ext4 is case-sensitive.

**How to avoid:** Update `main.jsx` import to `'./app.jsx'` in the same commit that creates `app.jsx`.

### Pitfall 2: Forgetting to remove index.css

**What goes wrong:** Both `index.css` and `styles.css` get imported. The placeholder `index.css` resets fonts to system-ui, which overrides the brand CSS.

**Why it happens:** `main.jsx` currently imports `'./index.css'`. If styles.css is added without removing the old import, the placeholder styles conflict.

**How to avoid:** In `main.jsx`, replace `import './index.css'` with `import './styles.css'`. Either delete `index.css` or leave it empty.

### Pitfall 3: IIFE-scoped `const` declarations used before conversion

**What goes wrong:** In the prototype, each IIFE has `const D = window.JD_DATA` at the top. If a file is converted to a module but still references `window.JD_DATA` instead of importing, it will fail at runtime (undefined).

**Why it happens:** Partial conversion — one file converted, its dependency not yet converted.

**How to avoid:** Convert in dependency order: `data.jsx` first (no imports), then `components.jsx` (imports data), then `conversation.jsx` (imports data + components), then `document.jsx` (imports data + components), then `app.jsx` last. Never import from a file that hasn't been converted yet.

### Pitfall 4: `Set` in state is not JSON-serializable

**What goes wrong:** `flashes` state is `new Set()`. If code accidentally includes `flashes` in the localStorage payload, `JSON.stringify(new Set(['title']))` returns `"{}"` — all flash data is silently dropped on restore.

**Why it happens:** Passing the full App state object to `localStorage.setItem`.

**How to avoid:** Only persist `record` (and optionally `answers` and `stepIndex`) — these are the only values needed for crash-recovery. Never include `flashes`, `reviewing`, `editingReturn`, `toast`, or refs.

### Pitfall 5: `dangerouslySetInnerHTML` with SVG path strings

**What goes wrong:** The `Icon` component uses `dangerouslySetInnerHTML: { __html: path }` to inject SVG path strings. This pattern is safe here because all paths are hardcoded string literals in `data.jsx` — but if a linter or reviewer flags it, understand why it's intentional.

**Why it happens:** The prototype stores SVG path `d` attribute strings (not full SVG markup) in the `I` constants, then injects them into a `<svg>` container. This is the prototype's design; port it as-is.

**How to avoid flagging yourself:** Add a comment in `components.jsx`: `// Icon paths are string literals from data.jsx — not user input; XSS-safe`.

### Pitfall 6: Font weight values outside Google Fonts variable range

**What goes wrong:** The CSS uses weights like `font-weight: 550`, `680`, `720`, `750` — non-standard numeric values. These work only if the Hanken Grotesk variable font is loaded with the correct weight axis range.

**Why it happens:** Variable fonts support fractional weights; the `<link>` must specify a weight range (e.g., `wght@300..800`) not discrete values.

**How to avoid:** Use the variable font URL format: `family=Hanken+Grotesk:wght@300..800` rather than discrete weights. This ensures intermediate values like `550` render correctly.

---

## Code Examples

### Complete localStorage persistence pattern for App

```jsx
// Source: prototype app.jsx state shape + localStorage API
function App() {
  // Lazy initializer restores record on mount
  const [record, setRecord] = useState(() => {
    try {
      const raw = localStorage.getItem('jd-builder-v2-record');
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  });

  const [answers, setAnswers] = useState({});
  const [stepIndex, setStepIndex] = useState(0);
  const [draft, setDraft] = useState(() => initialAnswer(STEPS[0], {}));
  const [reviewing, setReviewing] = useState(false);
  const [editingReturn, setEditingReturn] = useState(false);
  const [flashes, setFlashes] = useState(new Set());
  const [toast, setToast] = useState(null);

  // Persist record on every commit (crash-recovery)
  useEffect(() => {
    try {
      localStorage.setItem('jd-builder-v2-record', JSON.stringify(record));
    } catch {
      // storage quota exceeded — degrade gracefully, do not throw
    }
  }, [record]);

  // ... rest of App
}
```

### Conversion skeleton for a single file (conversation.jsx)

```jsx
// Source: prototype conversation.jsx → ES module conversion
import { PHASES, I } from './data.jsx';
import { Icon, Check, StepInput, answerValid } from './components.jsx';

// Header, Exchange, ActiveQuestion, ReviewState defined here
// (same logic, JSX replaces React.createElement)

export { Header, Exchange, ActiveQuestion, ReviewState };
// No more: window.JD_CONVO = { ... }
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `ReactDOM.render()` | `createRoot().render()` | React 18 (2022) | main.jsx already uses createRoot — correct |
| Class components | Function components + hooks | React 16.8 (2019) | Prototype already uses function components |
| `React.createElement` manually | JSX (compiled by Vite) | N/A — always available with bundler | Conversion is the point of this phase |
| IIFE global modules | ES module imports/exports | N/A — Vite requires ESM | Conversion is the point of this phase |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Google Fonts CDN is accessible from the dev machine | Standard Stack / Pattern 4 | Fonts fall back to system-ui/Georgia/monospace — functional but wrong brand appearance; fix by self-hosting |
| A2 | Hanken Grotesk supports variable font weight axis on Google Fonts | Pitfall 6 | Non-standard weights (550, 680, etc.) may render as nearest standard weight; visual fidelity degraded |

---

## Open Questions

1. **Should `answers` and `stepIndex` also be persisted to localStorage?**
   - What we know: The requirement says "restore most recent in-progress WD on reload" — `record` alone is enough to restore the document, but `answers` + `stepIndex` would restore conversation position too.
   - What's unclear: The requirement says "crash-recovery for the single-user local app" — ambiguous whether position recovery is needed.
   - Recommendation: Persist `record`, `answers`, and `stepIndex` together under one key. This is minimal extra code and gives a full restore. Mark as a planner decision.

2. **Should `styles.css` be a new file or replace `index.css` in-place?**
   - What we know: `main.jsx` currently imports `'./index.css'`; the prototype's CSS file is named `styles.css`.
   - Recommendation: Create `src/styles.css` as a new file matching the prototype name (FE-01 requires the prototype structure); update `main.jsx` to import `'./styles.css'`; delete `src/index.css`. This preserves FE-01 fidelity.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Vite dev server | ✓ | v25.9.0 | — |
| npm | Package management | ✓ | 11.12.1 | — |
| Vite | Dev server / build | ✓ | ^5.4.10 (installed) | — |
| React 18 | SPA framework | ✓ | ^18.3.1 (installed) | — |
| @vitejs/plugin-react | JSX transform | ✓ | ^4.3.4 (installed) | — |
| Google Fonts CDN | Brand typography | [ASSUMED] | — | System fonts (ui-sans/Georgia/monospace) |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** Google Fonts CDN (A1 above).

---

## Validation Architecture

### Test Framework

No frontend test framework is currently installed in `v2/frontend/`. Vitest is the standard choice for Vite projects (same config, same toolchain).

| Property | Value |
|----------|-------|
| Framework | Vitest (not yet installed — Wave 0 gap) |
| Config file | `vite.config.js` — Vitest config added inline |
| Quick run command | `cd v2/frontend && npx vitest run --reporter=verbose` |
| Full suite command | `cd v2/frontend && npx vitest run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FE-01 | All 5 source files + styles.css exist in `src/` | smoke | `ls v2/frontend/src/{app,data,conversation,document,components}.jsx v2/frontend/src/styles.css` | ❌ Wave 0 |
| FE-03 | CSS custom properties for brand fonts present in styles.css | smoke | `grep -q "Hanken Grotesk" v2/frontend/src/styles.css && grep -q "Spectral" v2/frontend/src/styles.css` | ❌ Wave 0 |
| FE-04 | App exports 7 state slices (record, answers, stepIndex, draft, reviewing, editingReturn, flashes) | unit | `npx vitest run src/app.test.jsx` | ❌ Wave 0 |
| FE-05 | localStorage.setItem called on record change; record restored from localStorage on mount | unit | `npx vitest run src/app.test.jsx` | ❌ Wave 0 |

**Note:** FE-01 and FE-03 are verifiable via shell commands without a test runner. FE-04 and FE-05 require a test runner with jsdom.

### Wave 0 Gaps

- [ ] Install vitest + jsdom: `cd v2/frontend && npm install --save-dev vitest @testing-library/react @testing-library/user-event jsdom`
- [ ] `v2/frontend/vite.config.js` — add `test: { environment: 'jsdom' }` block
- [ ] `v2/frontend/src/app.test.jsx` — covers FE-04 (state slices) + FE-05 (localStorage round-trip)

---

## Security Domain

This phase has no network calls, no authentication, no input that leaves the browser, and no server-side code. The only security-relevant surface is:

| ASVS Category | Applies | Notes |
|---------------|---------|-------|
| V5 Input Validation | Minimal | `dangerouslySetInnerHTML` in Icon component uses hardcoded string literals from `data.jsx` — not user input. Annotate in code. |
| All others | No | No auth, no sessions, no crypto, no external data in this phase |

---

## Sources

### Primary (HIGH confidence)
- `Job Description Builder/jd-builder/app.jsx` — state shape, commit logic, useMemo patterns, localStorage entry point
- `Job Description Builder/jd-builder/data.jsx` — STEPS, PHASES, computeClassification, all exports
- `Job Description Builder/jd-builder/conversation.jsx` — Header, Exchange, ActiveQuestion, ReviewState
- `Job Description Builder/jd-builder/document.jsx` — DocumentPane, Sec, ClassBlock, Ghost
- `Job Description Builder/jd-builder/components.jsx` — Icon, StepInput, all input controls
- `Job Description Builder/jd-builder/styles.css` — full CSS including brand vars and all component classes
- `v2/frontend/package.json` — installed dependencies confirmed
- `v2/frontend/vite.config.js` — proxy and build config confirmed
- `v2/frontend/src/main.jsx` — current entry point
- `v2/frontend/src/App.jsx` — current placeholder
- `.planning/REQUIREMENTS.md` — FE-01, FE-03, FE-04, FE-05 verbatim

### Secondary (MEDIUM confidence)
- npm registry: `vite@8.0.16`, `@vitejs/plugin-react@6.0.2`, `react@19.2.7` — latest published versions noted; project uses ^18.3.1/^5.4.10 range which is appropriate [VERIFIED: npm view output]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all deps installed and confirmed in package.json
- Architecture: HIGH — source files read in full; conversion pattern is mechanical
- Pitfalls: HIGH — derived from direct reading of prototype code and known Vite/React constraints
- localStorage pattern: HIGH — React docs + prototype state shape both confirmed

**Research date:** 2026-06-04
**Valid until:** 2026-07-04 (stable stack; Vite/React minor versions won't affect patterns)
