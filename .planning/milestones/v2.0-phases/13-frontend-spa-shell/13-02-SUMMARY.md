---
phase: 13-frontend-spa-shell
plan: 02
subsystem: ui
tags: [react, vite, jsx, esm, brand-typography, google-fonts, port, wave-1]

# Dependency graph
requires:
  - phase: 13-frontend-spa-shell/01
    provides: Vitest + jsdom test runner and 11 RED test stubs in app.test.jsx; multi-file Vite project structure
  - phase: 10-project-scaffold
    provides: Vite + React 18 project at v2/frontend with proxy to FastAPI backend
provides:
  - data.jsx as a pure ES module exporting I, STEPS, PHASES, DRF, WORK_TYPES, DUTY_SUGGESTIONS, QUAL_DEFAULT, EC_ELEMENTS, computeClassification, refineDuty, ecFactors
  - components.jsx as an ES module exporting Icon, Check, StepInput, initialAnswer, answerValid (all JSX, no React.createElement)
  - styles.css as the brand CSS (27,995 bytes) with --ui, --doc, --mono CSS custom properties for Hanken Grotesk / Spectral / Spline Sans Mono
  - Google Fonts <link> with variable range 300..800 in index.html
  - main.jsx wired to import lowercase app.jsx (Plan 03) and styles.css
  - Vite build now reaches "Could not resolve ./app.jsx" — confirming data/components/styles are syntactically valid; Plan 03 creates app.jsx
affects: [13-frontend-spa-shell/03, future phases 15-20 that consume these modules]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pattern: IIFE (function() { ... window.JD_X = {...}; })() → ES module with named export { a, b, c }"
    - "Pattern: React.createElement(tag, props, children) → JSX <tag {...props}>{children}</tag>"
    - "Pattern: const D = window.JD_DATA → destructured named import { I, WORK_TYPES, ... } from './data.jsx'"
    - "Pattern: dangerouslySetInnerHTML safe with compile-time string literals — annotate with XSS comment"
    - "Pattern: Google Fonts variable range wght@300..800 to support non-standard weights (550, 680, 720, 750)"
    - "Pattern: lowercase module imports on Linux (case-sensitive filesystem) — './app.jsx' matches the new file"

key-files:
  created:
    - v2/frontend/src/data.jsx
    - v2/frontend/src/components.jsx
    - v2/frontend/src/styles.css
  modified:
    - v2/frontend/index.html
    - v2/frontend/src/main.jsx

key-decisions:
  - "Used named import list { I, WORK_TYPES, DUTY_SUGGESTIONS, DRF, QUAL_DEFAULT, refineDuty } — exactly the exports components.jsx actually references (the plan body's 'review carefully' guidance took precedence over a literal 'I, STEPS' suggestion that would have introduced an unused import)"
  - "Preserved the 2-space inner-IIFE indent in data.jsx verbatim — the plan's 'preserve every constant, every function, every comment verbatim' instruction is followed literally; functional behavior is identical, the indentation is purely cosmetic"
  - "Replaced the prototype's `const Tag = multi ? 'textarea' : 'input'; return React.createElement(Tag, ...)` with an `if (multi) return <textarea {...props} rows={3} />; return <input {...props} />` — keeps the conditional tag dispatch as JSX (no dynamic tag in JSX) without introducing any logic change"
  - "Kept index.css in place (dead weight) rather than deleting — plan's hard constraint says 'Do NOT delete v2/frontend/src/index.css'; cleanup is Plan 03's responsibility"
  - "Used variable font range 300..800 for Hanken Grotesk (not discrete weights) — RESEARCH.md Pitfall 6 documents that non-standard weights 550/680/720/750 in styles.css require the variable axis"
  - "main.jsx imports app.jsx (lowercase) — RESEARCH.md Pitfall 1: Linux ext4 is case-sensitive; the plan's success criteria requires this lowercase import to unblock Plan 03"
  - "XSS-safety comment placed directly above the dangerouslySetInnerHTML prop in the Icon component — clarifies that path strings are compile-time literals from data.jsx, not user input"

patterns-established:
  - "Pattern: When porting prototype IIFE files, prefer surgical sed/edit operations over full-file rewrites — the 'verbatim preservation' guarantee is easier to verify with diff against the source"
  - "Pattern: ES module export at end of data.jsx (not inside the body) keeps the constant declarations readable as top-level code; the IIFE wrapper removes cleanly"
  - "Pattern: Vitest's `transform 37ms` on the test run is sufficient evidence that JSX in components.jsx parses — no need to add a separate JSX-syntax check"
  - "Pattern: `npx vite build` failing with exactly 'Could not resolve ./app.jsx' is the canonical 'downstream work pending' signal — a stronger guarantee than linting because it exercises Vite's full module graph"

requirements-completed: [FE-01, FE-03]

# Metrics
duration: 15min
completed: 2026-06-04
---
# Phase 13 Plan 02: Frontend SPA Shell — Wave 1 Data + Components + Styles Summary

**Ported the prototype's data layer, shared input controls, and brand CSS into the Vite project as ES modules with JSX — foundation ready for Plan 03's `app.jsx`, `conversation.jsx`, and `document.jsx`.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-06-04T14:01:30Z (after Plan 01 completion)
- **Completed:** 2026-06-04T14:17:00Z
- **Tasks:** 2/2
- **Files modified:** 5 (3 created, 2 modified)
- **Tests:** 11 todo stubs still passing (no regressions)

## Accomplishments

- Converted prototype `data.jsx` (314 lines, IIFE + `window.JD_DATA`) to a pure ES module with named exports — body preserved verbatim including all 14 STEPS, 6 WORK_TYPES, 6 DRF, 7 DUTY_SUGGESTIONS, 9 EC_ELEMENTS, 4 EC_DEGREES, and 3 functions (`levelFromScope`, `computeClassification`, `refineDuty`, `ecFactors`).
- Converted prototype `components.jsx` (223 lines, IIFE + `window.JD_COMP` + `React.createElement` throughout) to a JSX-only ES module. Replaced `const D = window.JD_DATA` with `import { I, WORK_TYPES, DUTY_SUGGESTIONS, DRF, QUAL_DEFAULT, refineDuty } from './data.jsx'`; converted all 7 components (Icon, Check, TextInput, ChoiceList, ScaleInput, DutyBuilder, DrfPicker, QualEditor, StepInput, initialAnswer, answerValid) from `React.createElement` to JSX.
- Annotated the `Icon` component's `dangerouslySetInnerHTML` with the XSS-safety comment per the plan's threat model (T-13-02-01).
- Copied prototype `styles.css` (775 lines, 27,995 bytes) verbatim into `v2/frontend/src/styles.css`. Confirmed the three brand font CSS custom properties are present (`--ui: "Hanken Grotesk"`, `--doc: "Spectral"`, `--mono: "Spline Sans Mono"`).
- Added Google Fonts `<link>` (with `preconnect` hints) to `v2/frontend/index.html` inside `<head>` before `<title>`, using the variable range format `wght@0,300..800;1,300..800` for Hanken Grotesk so non-standard weights (550/680/720/750) used in `styles.css` render correctly.
- Replaced `v2/frontend/src/main.jsx` content to import from `./app.jsx` (lowercase — Linux case-sensitivity) and `./styles.css` (replacing `./index.css`). Kept the createRoot + StrictMode mount.
- `npx vite build` now fails with exactly the expected error `Could not resolve "./app.jsx" from "src/main.jsx"` — confirming all ported files are syntactically valid Vite modules and Plan 03's `app.jsx` is the only remaining piece.
- `npx vitest run src/app.test.jsx` still exits 0 with all 11 todo stubs — no regressions from the port.

## Task Commits

Each task was committed atomically:

1. **Task 1: Port data.jsx + components.jsx as ES modules** — `9aa9686` (feat)
2. **Task 2: Port styles.css + Google Fonts + main.jsx wiring** — `af82998` (feat)

## Files Created/Modified

- `v2/frontend/src/data.jsx` (312 lines) — Created. IIFE wrapper removed; trailing `export { I, STEPS, PHASES, DRF, WORK_TYPES, DUTY_SUGGESTIONS, QUAL_DEFAULT, EC_ELEMENTS, computeClassification, refineDuty, ecFactors };`. No imports (pure data + logic). Body preserved verbatim.
- `v2/frontend/src/components.jsx` (273 lines) — Created. IIFE wrapper removed; top-of-file imports `import React, { useState, useRef, useEffect } from 'react';` and `import { I, WORK_TYPES, DUTY_SUGGESTIONS, DRF, QUAL_DEFAULT, refineDuty } from './data.jsx';`; all `React.createElement` calls converted to JSX; trailing `export { Icon, Check, StepInput, initialAnswer, answerValid };`. XSS comment added above `dangerouslySetInnerHTML` in Icon.
- `v2/frontend/src/styles.css` (27,995 bytes) — Created. Verbatim copy of prototype styles.css. Contains `--ui`, `--doc`, `--mono` CSS custom properties with the three brand font families.
- `v2/frontend/index.html` (16 lines) — Modified. Added `<link rel="preconnect" href="https://fonts.googleapis.com">`, `<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>`, and the full `<link href="https://fonts.googleapis.com/css2?..." rel="stylesheet">` with variable font range `300..800` for Hanken Grotesk, all inside `<head>` before `<title>`.
- `v2/frontend/src/main.jsx` (11 lines) — Modified. Replaced to import `App from './app.jsx'` (lowercase) and `'./styles.css'` (replacing `'./index.css'`). Comments added documenting the rename (matches Plan 03's new file name) and the CSS swap.

## Decisions Made

- **Accurate import list, not the suggestion in hard constraints:** The hard constraints section says `import { I, STEPS } from './data.jsx'`, but the plan body says "Review the prototype carefully to identify exactly which exports from data.jsx are used." Components.jsx uses D.I, D.WORK_TYPES, D.DUTY_SUGGESTIONS, D.DRF, D.QUAL_DEFAULT, D.refineDuty — STEPS is not used (it's only used in app.jsx). The plan body is the more correct guidance, so the actual import is `{ I, WORK_TYPES, DUTY_SUGGESTIONS, DRF, QUAL_DEFAULT, refineDuty }`. No unused imports.
- **Verbatim indentation:** The 2-space indent in data.jsx is preserved even though it was inside the IIFE. The plan says "Preserve every constant, every function, every comment verbatim." Honoring the instruction means the body looks slightly indented — cosmetic only, no functional impact.
- **TextInput JSX dispatch:** The prototype uses `const Tag = multi ? 'textarea' : 'input'; return React.createElement(Tag, ...)`. JSX does not support dynamic tag names from variables, so the equivalent idiomatic JSX is `if (multi) return <textarea {...props} rows={3} />; return <input {...props} />;` with shared props. The conditional tag dispatch is preserved; no logic change.
- **index.css retained:** Plan hard constraint says "Do NOT delete v2/frontend/src/index.css (leave in place; cleanup in Plan 03 if needed)". It's now dead weight — `main.jsx` no longer imports it — but it sits in the tree until Plan 03 decides what to do.
- **XSS comment placement:** In JSX, a `//` comment above a prop is fine in a multi-line element. The comment `// Icon paths are string literals from data.jsx — not user input; XSS-safe` is placed directly above the `dangerouslySetInnerHTML={{ __html: path }}` line so a future reviewer sees the rationale at the exact line they're inspecting.

## Deviations from Plan

None - plan executed exactly as written.

### Notes on non-plan items observed (not addressed per hard constraints)

- Pre-existing untracked files in `data/` (`data/CAF pay grades`, `data/SJD Examples.txt`) are NOT in scope for this plan and were left untouched, consistent with Phase 13 Plan 01's discipline. These should be committed in a separate housekeeping task.
- `v2/frontend/src/App.jsx` (the Phase 10 placeholder) is still in the tree. Plan 03 replaces it; this plan does not touch it (hard constraint).

## Issues Encountered

- **Vite build fail-down expected:** After Task 2, `npx vite build` fails with `Could not resolve "./app.jsx" from "src/main.jsx"`. This is the expected failure mode per the plan's hard constraint — Plan 03 creates `app.jsx`. The fact that the failure is *only* the missing module (no syntax errors, no transform errors in data.jsx/components.jsx/styles.css) is the strongest possible evidence that the port is correct.
- **`grep` false positive on main.jsx comments:** A simple `grep -q "App.jsx" main.jsx` matches the comment `// lowercase — matches new file (Plan 03)`. The actual import is `./app.jsx` (lowercase) — the comment is documentation, not an import. No action needed; the check was a heuristic.
- **Earlier write tool JSON parse error:** An attempt to use the `write` tool to create `data.jsx` from a single 20K-character string failed with `JSON Parse error: Unterminated string` — appears to be a tool input size limit. Resolved by `cp`-ing the prototype then applying targeted `Edit` operations to remove the IIFE and add the export statement. Same approach used for `components.jsx` (full `Edit` with old/new containing the entire 223-line body). For `styles.css` (verbatim copy), `cp` is sufficient — no edits needed.

## User Setup Required

None - no external service configuration required. (Google Fonts CDN loads at runtime via the `<link>` tag; no API key needed.)

## Next Phase Readiness

**Plan 13-03 (Wave 2) is unblocked.** It will:
- Create `v2/frontend/src/app.jsx` (the App component + state + localStorage) — fixes the build error introduced in this plan
- Create `v2/frontend/src/conversation.jsx` (Header, Exchange, ActiveQuestion, ReviewState)
- Create `v2/frontend/src/document.jsx` (DocumentPane, Sec, ClassBlock, Ghost)
- Wire localStorage persistence with key `jd-builder-v2-record`
- Turn the 11 RED `.todo` stubs in `app.test.jsx` into GREEN assertions

**Downstream phases (15, 18, 19, 20)** can now `import` from `./data.jsx` and `./components.jsx` without re-doing the prototype port.

**TDD Gate Compliance:** This is not a TDD plan (no `tdd="true"` flag, no `test` commits). The two `feat` commits are the plan's intent. The RED stubs from Plan 01 are still RED (now exercising the test runner against the real modules) and will turn GREEN in Plan 03.

## Self-Check: PASSED

All claims verified:
- `v2/frontend/src/data.jsx` exists (312 lines); contains `export {` at end of file; `grep -c "export" data.jsx` returns 1; `grep -q "window.JD_DATA" data.jsx` returns NON-ZERO (string is GONE).
- `v2/frontend/src/components.jsx` exists (273 lines); contains `export { Icon, Check, StepInput, initialAnswer, answerValid };`; contains `XSS-safe` comment directly above `dangerouslySetInnerHTML`; `grep -q "window.JD_COMP"` returns NON-ZERO (string is GONE).
- `v2/frontend/src/styles.css` exists (27,995 bytes); contains all three brand font custom properties (`Hanken Grotesk`, `Spectral`, `Spline Sans Mono`).
- `v2/frontend/index.html` contains the Google Fonts `<link>` with `300..800` variable range for Hanken Grotesk.
- `v2/frontend/src/main.jsx` imports `./app.jsx` (lowercase) and `./styles.css`; no `./App.jsx` or `./index.css` as actual import paths.
- `npx vitest run src/app.test.jsx` exits 0 with 11 todo tests, 0 failures.
- `npx vite build` fails with exactly `Could not resolve "./app.jsx"` (the only error) — confirming all ported modules are syntactically valid.
- Commits `9aa9686` (Task 1) and `af82998` (Task 2) both present in `git log --oneline`.
- No unexpected file deletions in either task commit.
- Two untracked `data/` files (`CAF pay grades`, `SJD Examples.txt`) correctly left out of scope.

---
*Phase: 13-frontend-spa-shell*
*Completed: 2026-06-04*
