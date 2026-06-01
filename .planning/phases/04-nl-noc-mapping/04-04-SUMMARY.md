---
phase: 04-nl-noc-mapping
plan: 04
subsystem: ui
tags: [htmx, wizard, css, fastapi, static-files, tests]
provides:
  - HTMX wizard step at GET /wizard/noc (templates/wizard/step_noc.html)
  - HTMX partial for NOC candidate cards (templates/partials/noc_results.html)
  - Design-token CSS with .noc-card, .teer-badge, .error-state, .empty-state, .htmx-indicator
  - Static files route at /static mounting app/static/
  - 10 integration/unit tests for the NL→NOC pipeline + API routes + guardrails
key-files:
  created:
    - app/static/css/main.css
    - templates/wizard/step_noc.html
    - templates/partials/noc_results.html
  modified:
    - app/templates/base.html
    - app/main.py
    - tests/conftest.py
    - tests/test_noc_mapping.py
metrics:
  duration_seconds: 720
  tasks_completed: 4
  commits: 4
  tests_added: 10
  tests_passing: 90
---

# Plan 04-04 — HTMX wizard + CSS + turn test stubs green

## What was built

The advisor-facing UI surface for Phase 4's NL→NOC mapping pipeline. After this plan:

- `GET /wizard/noc` renders the wizard step (textarea + "Find NOC Candidates" button).
- `POST /api/noc/map` returns either JSON (direct API) or an HTML partial (HTMX `HX-Request: true`).
- NOC candidate cards show NOC code, unit group title, TEER badge, verbatim matched duty list, collapsible LLM justification, and a "Confirm this NOC" button that posts to `/api/noc/confirm`.
- Static files are served from `/static` (CSS only at this phase).
- 10 integration/unit tests cover the three-stage pipeline, the verbatim fidelity guardrail (including the all-stripped ValueError path), the FastAPI route (JSON + HTMX HTML partial), the confirm endpoint (CRUD roundtrip + 404), and the 422 on empty FTS5 shortlist.

## Tasks

### Task 1a — Create CSS and Jinja2 templates
**Commit:** `14214e5`
**Files:** `app/static/css/main.css`, `templates/wizard/step_noc.html`, `templates/partials/noc_results.html`

CSS follows the seven-layer architecture from `04-UI-SPEC.md`:
1. CSS reset
2. Design tokens on `:root` (all exact values from UI-SPEC: `--color-accent: #1A4A8A`, etc.)
3. Base typography
4. Layout
5. Form elements (textarea, button — min-height 44px for accessibility)
6. Component classes: `.noc-card`, `.noc-card.confirmed`, `.teer-badge`, `.error-state`, `.empty-state`, `.confirmation-banner`
7. HTMX indicator (`.htmx-indicator` with `.htmx-request` toggle)

`step_noc.html` extends `base.html`, includes the work description textarea with the exact placeholder from UI-SPEC, the HTMX form posting to `/api/noc/map` with `hx-target="#noc-results"`, `hx-swap="innerHTML"`, `hx-indicator="#spinner"`, and a spinner with `aria-label="Loading"`. The `#noc-results` div has `aria-live="polite"` for screen-reader announcements.

`noc_results.html` is a BARE FRAGMENT (no `{% extends %}`). Iterates over `candidates` (list[NOCCandidate] — `noc_code`, `title`, `teer`, `matched_duties`, `justification`) and renders one `.noc-card` per candidate with: header (code + title + TEER badge), matched duty list, collapsible `<details>` for the LLM justification, and a confirm form posting to `/api/noc/confirm` with `wd_id` + `noc_code` hidden inputs. Empty state shows a `.empty-state` with role="alert" and a plain-language rewording hint.

### Task 1b — Wire base.html CSS link, StaticFiles mount, /wizard/noc route
**Commit:** `140861e`
**Files:** `app/templates/base.html`, `app/main.py`

Added `<link rel="stylesheet" href="/static/css/main.css">` in `base.html` head (before the Alpine.js script). Added `StaticFiles` mount at `/static` pointing to `app/static/`, and `Jinja2Templates` for `templates/` (sibling of `app/`) so the wizard template can use `{% extends "base.html" %}`. Added `GET /wizard/noc` route returning `templates.TemplateResponse("wizard/step_noc.html", ...)`.

### Task 2 — Turn test stubs green
**Commit:** `893db7a`
**Files:** `tests/test_noc_mapping.py`

Replaced all 7 `pytest.skip` stubs with real implementations:

| Test | What it verifies |
|------|------------------|
| `test_fts5_stage_returns_noc_codes` | Stage 1 FTS5 query returns NOC codes using `noc_mapping_db` fixture (with mocked embed + LLM) |
| `test_stage2_calls_embed_model` | Stage 2 calls `OllamaAsyncClient.embed` with model = `OLLAMA_EMBED_MODEL` |
| `test_pipeline_returns_candidates` | Full mocked 3-stage pipeline returns `NOCRankingResult` with ≥ 1 candidate |
| `test_verbatim_guardrail_strips_fabricated` | `_check_verbatim_fidelity` strips duties not in DB; real duties survive |
| `test_verbatim_guardrail_raises_when_all_stripped` | `_check_verbatim_fidelity` raises `ValueError` if all duties stripped |
| `test_empty_fts_result_raises_422` | `POST /api/noc/map` with empty FTS5 shortlist returns HTTP 422 |
| `test_api_route_200` | `POST /api/noc/map` (no `HX-Request`) returns JSON with candidates |
| `test_api_route_htmx_returns_html` | `POST /api/noc/map` with `HX-Request: true` returns HTML partial |
| `test_confirm_noc_updates_wd` | `POST /api/noc/confirm` stores `confirmed_noc` on WorkDescription + sets stage to `noc_mapped` |
| `test_confirm_noc_404_when_wd_missing` | `POST /api/noc/confirm` with unknown `wd_id` returns HTTP 404 |

**Test infrastructure note:** The pipeline tests (3) and guardrail tests (2) call `map_work_description`/`_check_verbatim_fidelity` directly with explicit `db_path`, so they don't need module re-imports. The FastAPI tests (5) use a `test_db_routing` fixture that patches `app.db.get_connection` at every import site, so the cached `settings.db_path` is overridden to the per-test `noc_mapping_db`. This avoids the httpx connection-pool leak that would result from clearing/reimporting `app.*` modules between tests (the `instructor_client` singleton holds an `AsyncOpenAI` whose `httpx.AsyncClient` connection pool is never explicitly closed when the module is dropped).

### Task 3 — Conftest FTS5 schema fix
**Commit:** `69062e2`
**Files:** `tests/conftest.py`

The `create_schema()` DDL in `app/db.py` defines `noc_fts` as:
```sql
CREATE VIRTUAL TABLE noc_fts USING fts5(
    noc_code    UNINDEXED,    -- ← problem
    title, definition, element_type UNINDEXED, element_text,
    content='',              -- ← contentless — problem
    tokenize='porter ascii'
);
```

For a contentless FTS5 table, the column values are not stored in the inverted index — they are only retrievable by JOINing to a separate content table. The `noc_code` column, being `UNINDEXED`, cannot be retrieved via SELECT at all. This means the Stage 1 query `SELECT ... FROM noc_fts f JOIN noc_units u ON u.noc_code = f.noc_code` returns 0 rows for any query (because `f.noc_code` is `NULL`, and the JOIN condition becomes `NULL = '21232'`, which is `NULL` — not `TRUE`).

The live DB was created by `scripts/ingest_noc.py` with a different (correct) schema: `noc_code` indexed, no `content=''`. The conftest fixture already drops+recreates `noc_chunks_vec` to match the live DB; this commit does the same for `noc_fts`.

## Deviations from plan

### Auto-fix (Rule 1): conftest FTS5 schema mismatch
The `noc_mapping_db` fixture populated FTS5 with data, but the schema's `UNINDEXED` + `content=''` columns meant the Stage 1 JOIN returned 0 rows. This was not caught by the 04-01 plan's verification (which only checked row counts, not query results). Fixed by dropping+recreating `noc_fts` in the conftest fixture to match the live DB schema.

### Auto-add (Rule 3): 3 bonus tests beyond the 7 plan-mandated stubs
- `test_verbatim_guardrail_raises_when_all_stripped` — the plan described the raise behavior but didn't list a dedicated test. The existing `test_verbatim_guardrail_strips_fabricated` only covered the partial-strip case.
- `test_api_route_htmx_returns_html` — the plan's `test_api_route_200` only verified the JSON path. The HTMX HTML partial is a critical contract (the wizard depends on it) and warranted a dedicated assertion.
- `test_confirm_noc_404_when_wd_missing` — the plan described the 200 success path. The 404 path is the more important negative test (catches ID lookup bugs).

### Architectural decision: `test_db_routing` fixture instead of module re-import
Initial implementation used an autouse fixture that cleared `app.*` modules between tests. This leaked httpx connection pools from the `instructor_client` singleton (which creates an `AsyncOpenAI` → `httpx.AsyncClient` at module import; the connection pool is never `aclose()`d when the module is dropped, preventing the test event loop from completing). Replaced with a targeted `monkeypatch.setattr` on `app.db.get_connection` at all import sites — the cached `settings.db_path` is bypassed, no module re-imports, no connection pool leak.

## Verification

### Automated
```
$ pytest tests/ -v
... 90 passed, 1 warning in 11.84s
```

The 1 warning is a pre-existing Starlette deprecation about `TemplateResponse(name, {request})` in `app/api/noc_mapping.py:49` (not from this plan — that signature was established in 04-03). The new template-first parameter ordering is `TemplateResponse(request, name, {context})`. Surfacing for 04-05/06 followup.

### Per-must_haves check

| must_have.truths | Status |
|------------------|--------|
| `GET /wizard/noc` renders `step_noc.html` with textarea + Find button | ✓ Verified by `app/main.py:@app.get("/wizard/noc")` + `templates/wizard/step_noc.html` |
| HTMX POST `/api/noc/map` swaps `noc_results.html` into `#noc-results` | ✓ Verified by `test_api_route_htmx_returns_html` (asserts "Software engineers and designers" + "Confirm this NOC" in response body) |
| NOC candidate cards show code + title + TEER + duties + Confirm button | ✓ Verified by `templates/partials/noc_results.html` (header h2 with `[code] title`, `.teer-badge`, `<ul>` of `matched_duties`, confirm form) |
| Full pytest suite passes | ✓ `pytest tests/` → 90 passed, 0 failed |
| `app/static/css/main.css` contains design tokens + `.noc-card` class | ✓ All 7 token values from UI-SPEC present, `.noc-card` defined with border + radius + padding |

| must_haves.artifacts | Status |
|----------------------|--------|
| `templates/wizard/step_noc.html` | ✓ Exists, contains `hx-post="/api/noc/map"`, `Find NOC Candidates`, `Searching NOC database` |
| `templates/partials/noc_results.html` | ✓ Exists, contains `hx-post="/api/noc/confirm"`, `Confirm this NOC`, `TEER {{ candidate.teer }}` |
| `app/static/css/main.css` | ✓ Exists, contains `--color-accent: #1A4A8A`, all design tokens, `.noc-card`, `.htmx-indicator` |
| `app/templates/base.html` (link tag) | ✓ Exists, `<link rel="stylesheet" href="/static/css/main.css">` added |

| must_haves.key_links | Status |
|----------------------|--------|
| `step_noc.html` → `/api/noc/map` via `hx-post` | ✓ |
| `noc_results.html` → `/api/noc/confirm` via `hx-post` | ✓ |
| `main.css` → `base.html` via `<link>` tag | ✓ |

## Commits

- `14214e5`: `feat(04-04): add wizard step, HTMX partial, and main CSS`
- `140861e`: `feat(04-04): wire main.css link, static files, and wizard route`
- `69062e2`: `test(04-04): fix noc_mapping_db fixture FTS5 schema to match live DB`
- `893db7a`: `test(04-04): turn 7 test_noc_mapping.py stubs into real tests`
- This SUMMARY.md (final docs commit)

## Self-Check

- [x] All 4 must_haves.truths satisfied
- [x] All 4 must_haves.artifacts exist with `contains` markers
- [x] All 3 must_haves.key_links wired
- [x] All 10 tests in test_noc_mapping.py pass (0 skipped)
- [x] Full pytest suite: 90 passed, 0 failed
- [x] No modifications to STATE.md or ROADMAP.md
- [x] SUMMARY.md committed before return
- [ ] Human-verify checkpoint (Task 3) — deferred to orchestrator; not blocking for code-completion

PASSED
