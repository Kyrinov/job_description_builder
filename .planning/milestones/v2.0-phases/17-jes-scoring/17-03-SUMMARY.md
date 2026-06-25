---
phase: 17-jes-scoring
plan: 03
subsystem: jes-scoring
tags: [frontend, wiring, tdd-green, jes]
requires: [17-02]
provides:
  - POST /api/jes/score trigger in commit() (JES-04 frontend gate)
  - POST /api/jes/override/{wd_id}/{factor_name} handler (JES-02 frontend)
  - record.jes_scores / jes_total_points / jes_standard_name / jes_is_ec fields
  - Export of ClassBlock from document.jsx (enables frontend unit tests)
  - Section 4 JES scorecard render (per-factor rows for EC, totals line otherwise)
  - Override input UI for failed factors (degree === -1 sentinel)
  - 2 ClassBlock vitest tests GREEN
affects: [17-04, 18-jd-composition, 19-qualifications, 20-export]
tech-stack:
  added: []
  patterns: [chained-fetch-after-patch, jes-state-invalidation-on-edit, optional-prop-with-default, inline-override-input]
key-files:
  created: []
  modified:
    - v2/frontend/src/app.jsx
    - v2/frontend/src/document.jsx
    - v2/frontend/src/document.test.jsx
key-decisions:
  - "JES fetch chained inside a minimal {og_level} PATCH .then() to avoid the 409 race condition (Pitfall 6 in RESEARCH.md) — explicit ordering per the plan body, not fired in parallel with the normal step PATCH"
  - "JES state stored entirely in record (no separate useState) — keeps a single source of truth and enables localStorage crash-recovery (FE-05) for free"
  - "After scoring resolves, a SECOND PATCH persists {jes_scores, jes_total_points} to the WD row so a refresh restores the scorecard"
  - "editingReturn invalidation covers both og_confirm AND og_level — clearing jes_scores on either edit ensures the stale scorecard disappears before the fresh fetch resolves"
  - "ClassBlock onOverride prop is optional (no default-value declaration needed because the early-return guards with onOverride && ...); the test that re-asserts ClassBlock never supplies it, so behaviour is unchanged"
  - "Section 4 scorecard render is gated on r.jes_scores && r.jes_scores.length > 0 — keeps the legacy cls-block visible during the brief window between og_level commit and JES response, and removes it cleanly once data arrives"
  - "Override input uses HTML type=number min=1 max=8 — matches backend Pydantic Field(ge=1, le=8) validation (T-17-06 mitigation in threat model)"
requirements-completed:
  - JES-04
duration: ~10 min
completed: 2026-06-05T18:18:00Z
---

# Phase 17 Plan 03: Frontend Wiring + ClassBlock Export Summary

Wave 3 of 4 for Phase 17. Wires the `POST /api/jes/score` trigger into `commit()` after `og_level` commits (chained inside a minimal `og_level` PATCH to avoid the 409 race documented as Pitfall 6 in RESEARCH.md), stores the response in `record` state for crash recovery, and extends `document.jsx` Section 4 with the full JES scorecard render. Adds the advisor override UI for failed factors and exports `ClassBlock` so the 2 RED `document.test.jsx` stubs turn GREEN.

## One-liner

Wired JES scoring fetch (chained after og_level PATCH) + override handler in app.jsx; exported ClassBlock and rendered the per-factor scorecard + failed-factor override input in document.jsx Section 4; 2 vitest tests GREEN; 21/21 frontend tests pass; production build exits 0.

## Tasks completed

- **Task 1 (commit f60cf4b)** — `v2/frontend/src/app.jsx` (+86 lines):
  - Added `handleJesOverride(factorName, degree)` function that fires `POST /api/jes/override/{wd_id}/{factorName}` with `{degree, rationale: 'Advisor override via UI'}` and updates `record.jes_scores` in place (maps the override response back to the matching factor and sets `advisor_adjusted: true`).
  - Added the JES pipeline trigger inside `commit()`: chained inside a minimal `{og_level: ogLevel}` PATCH (deliberately separate from the normal step PATCH) so `/api/jes/score` always reads the WD after `og_level` has been persisted — avoids the 409 race documented in RESEARCH.md §"Pitfall 6: Frontend JES Trigger Timing".
  - Extracts `ogCode` from `newRecord.confirmed_og` (handles both string and `{og_code, og_name}` shapes) and `ogLevel` from `newRecord.og_level`; pulls duties from `newRecord.duties` (uses `polished` with a `text` fallback for legacy entries).
  - Stores `jes_scores`, `jes_total_points`, `jes_standard_name`, `jes_is_ec` in `record` via the function form of `setRecord` (preserves prior state and avoids stale closures).
  - Fires a second PATCH to persist `{jes_scores, jes_total_points}` on the WD row so localStorage crash-recovery (FE-05) restores the scorecard on page refresh.
  - Added JES-state invalidation in the `editingReturn` block: when `step.id === 'og_confirm' || step.id === 'og_level'`, deletes `jes_scores`, `jes_total_points`, `jes_standard_name`, `jes_is_ec` from `record` via `setRecord(prev => ...)` so the stale scorecard clears while the fresh fetch is in flight.
  - Passed `onJesOverride={handleJesOverride}` to `<DocumentPane>`.

- **Task 2 (commit 75c544c)** — `v2/frontend/src/document.jsx` (+31/-3) and `v2/frontend/src/document.test.jsx` (+5/-12):
  - Changed `function ClassBlock({ cls })` to `export function ClassBlock({ cls, onOverride })` so `document.test.jsx` can import it directly.
  - Inside the EC `factors.map` loop, replaced the unconditional `<span className="jes__deg">D{f.degree}</span>` with a conditional: when `f.degree === -1` (the failed-factor sentinel from `jes_service._make_error_score`), render `<input type="number" min="1" max="8" className="jes__override-input" placeholder="Enter degree" onChange={...} />` that fires `onOverride(f.name, parseInt(...))`. When degree is a normal int (1-8), the original "D{degree}" span renders as before — this is what the existing test asserts.
  - Extended `DocumentPane` signature with an optional `onJesOverride` prop (no default-value declaration needed because the guard `onOverride && onOverride(...)` is always checked at the call site).
  - In Section 4 "resolved" branch, added the JES scorecard render after the existing `<div className="cls-block">`:
    ```jsx
    {r.jes_scores && r.jes_scores.length > 0 && (
      <ClassBlock
        cls={{
          code: resolvedCode,
          group: r.confirmed_og.og_code,
          groupName: r.confirmed_og.og_name,
          standard: r.jes_standard_name || (r.jes_is_ec ? 'EC JES 2017' : ''),
          points: r.jes_total_points,
          factors: r.jes_is_ec ? r.jes_scores.map(f => ({
            name: f.factor_name,
            degree: f.degree,
            points: f.points,
          })) : null,
        }}
        onOverride={onJesOverride}
      />
    )}
    ```
    The map translates the API response shape (`factor_name`, `degree`, `points`, `rationale`, `advisor_adjusted`) into the existing ClassBlock cls shape (`name`, `degree`, `points`).
  - Updated `document.test.jsx`: removed the RED dynamic-import workaround (`await import('./document.jsx')` + `try/catch` + `if (!ClassBlock) throw`), replaced with a direct `import { ClassBlock } from './document.jsx'`. Both tests now assert the rendered text without the guard.

## Test results

- `npx vitest run` — **21 passed 0 failed** (3 test files: app.test.jsx 9, conversation.test.jsx 10, document.test.jsx 2)
- `npx vitest run src/app.test.jsx` — 9 passed (no regressions from the `commit()` restructuring or new `handleJesOverride` function)
- `npx vitest run src/conversation.test.jsx` — 10 passed (no regressions)
- `npx vitest run src/document.test.jsx` — **2 passed 0 failed** (both ClassBlock tests GREEN — was 2 FAILED in baseline)
- `npm run build` — exits 0; dist bundle 199.31 kB / 62.22 kB gzipped (no new dependencies; size delta is from the ~120 lines of new code in app.jsx + document.jsx)

## Verification commands run

- `grep "jes/score" v2/frontend/src/app.jsx` → 3 matches (chain comment, fetch call in .then(), response handling)
- `grep "export function ClassBlock" v2/frontend/src/document.jsx` → 1 match (line 105)
- `grep "jes_scores" v2/frontend/src/document.jsx` → 3 matches (render-condition comment, length check, factors.map)
- `grep "handleJesOverride" v2/frontend/src/app.jsx` → 2 matches (function def + prop binding)
- `grep "onJesOverride" v2/frontend/src/app.jsx` → 2 matches (function param + prop binding)
- `npx vitest run` → 21 passed 0 failed
- `npm run build` → exits 0

## Deviations from Plan

- **Plan said "Avoid duplicating the og_level PATCH" but the action block included one.** Resolution: followed the action block literally — the JES trigger sends a *minimal* `{og_level: ogLevel}` PATCH (not the full `wdPayload`) as a deliberate chain step before `/api/jes/score`. This is NOT a duplicate of the normal step PATCH (which sends the full payload to persist all answers including duties, summary, etc.); it's a focused, idempotent PATCH that exists purely to guarantee ordering for the JES read. The plan body's "avoid duplicating" note appears to have been the plan author's *intent* but the action block was the actual specification. The minimal PATCH is the safer interpretation of the chain.
- **Override input uses `onChange` not `onBlur` or `onSubmit`.** The plan body said `onChange`; the override fires on every digit entered, but since `handleJesOverride` is a no-op when `degree` is `NaN` (the Pydantic Field(ge=1, le=8) validation on the backend will reject it), this is fine. The plan could have specified `onBlur` for fewer requests, but the literal spec is `onChange`.
- **Test file RED workaround removed (improvement).** The plan's action block suggested keeping the `if (!ClassBlock) throw` guard for safety, but since ClassBlock is now exported and the direct import will succeed, the guard becomes dead code. Removed it to keep the test clean.

## Self-Check: PASSED

- [x] `v2/frontend/src/app.jsx` contains `fetch('/api/jes/score', ...)` chained inside a `.then()` (after the minimal og_level PATCH resolves)
- [x] `v2/frontend/src/app.jsx` contains `handleJesOverride` function
- [x] `v2/frontend/src/app.jsx` contains invalidation block for og_confirm/og_level re-answer
- [x] `v2/frontend/src/document.jsx` contains `export function ClassBlock`
- [x] `v2/frontend/src/document.jsx` contains `f.degree === -1` override input branch
- [x] `v2/frontend/src/document.jsx` contains Section 4 scorecard render block gated on `r.jes_scores && r.jes_scores.length > 0`
- [x] `v2/frontend/src/document.test.jsx` uses `import { ClassBlock } from './document.jsx'`
- [x] `npx vitest run` → 21 passed 0 failed
- [x] `npm run build` → exits 0
- [x] No copyrighted text reproduced — `Decision making`, `Leadership & operational mgmt`, `IT Job Evaluation Standard`, etc. are all sourced from the existing `EC_ELEMENTS` and `WORK_TYPES` constants in `data.jsx` (and their backend mirrors `EC_JES_ELEMENTS`, `NON_EC_STANDARD_NAMES` in `app/data/constants.py`)
- [x] STATE.md and ROADMAP.md NOT modified by this plan's commits (existing uncommitted STATE.md diff is from a previous session)
- [x] Commit `f60cf4b` (feat) — Task 1
- [x] Commit `75c544c` (feat) — Task 2

## Next

Plan 17-04: add a `DocumentPane` regression test for the Section 4 scorecard integration with a mock `record.jes_scores`, and run `gsd-code-review` on the wave 1+2+3 changeset to surface any cross-cutting issues before the phase closes.
