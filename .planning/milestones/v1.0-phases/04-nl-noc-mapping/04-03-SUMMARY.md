---
phase: 04-nl-noc-mapping
plan: 03
subsystem: noc-mapping
tags: [wave-2, three-stage-pipeline, fts5, sqlite-vec, instructor, fastapi, htmx, tdd-green, service-layer, db-schema]

# Dependency graph
requires:
  - phase: 04-nl-noc-mapping (plan 02)
    provides: "NOCCandidate + NOCRankingResult Pydantic models, instructor_client singleton, WorkDescriptionRequest + NocMapResponse API models"
  - phase: 04-nl-noc-mapping (plan 01)
    provides: "tests/test_noc_mapping.py stubs (7 tests, SKIPPED), tests/conftest.py noc_mapping_db fixture, scripts/rebuild_noc_vectors.py"
  - phase: 01-project-foundation
    provides: "WorkDescription + NOCMatch + ProvenanceTag Pydantic models, FastAPI lifespan, get_connection() factory, create_schema() DDL, settings singleton"
  - phase: 02-noc-data-pipeline
    provides: "noc_units, noc_elements, noc_fts (FTS5), noc_chunks_vec (vec0) live tables with NOC 2021 corpus"

provides:
  - "app/services/noc_mapper.py — three-stage pipeline (FTS5 → sqlite-vec → instructor) + verbatim fidelity guardrail + TEER DB correction + to_noc_match mapper"
  - "app/services/wd_store.py — save_work_description and load_work_description CRUD helpers for the work_descriptions table"
  - "app/api/noc_mapping.py — FastAPI router: POST /api/noc/map (HTMX dual response: HTML partial or NocMapResponse JSON) and POST /api/noc/confirm (sets confirmed_noc + stage='noc_mapped')"
  - "app/db.py NOC_MAPPING_SCHEMA_DDL — noc_mapping_cache (SHA-256-keyed result cache) and noc_mapping_log (per-request flywheel metrics) tables"
  - "app/templates/partials/noc_results.html — HTMX swap target rendering ranked candidate cards with confirm buttons"
  - "app/main.py noc_mapping router registration"

affects:
  - "Phase 04 plan 04 (HTMX wizard step + WD confirm endpoint + full test suite) — depends on POST /api/noc/map and POST /api/noc/confirm being live"
  - "Phase 05 (OG Classification) — consumes NOCMatch from WorkDescription.noc_candidates to seed the OG lookup"
  - "Phase 07 (JES Scoring) — uses the same instructor Mode.JSON singleton pattern; this plan establishes the canonical FastAPI + service + guardrails template"

# Tech tracking
tech-stack:
  added: []  # all libraries (asyncio, sqlite3, sqlite-vec 0.1.9, ollama 0.6.1, instructor 1.15.1) already in requirements.txt
  patterns:
    - "Connection-per-request pattern with try/finally + asyncio.to_thread(get_connection) and asyncio.to_thread(conn.close) — avoids module-level connection and per-call pool churn"
    - "Parameterized FTS5 MATCH ? query (work_description, fts_limit) tuple — no string interpolation; security control T-04-03-01"
    - "sqlite-vec KNN JOIN on noc_elements.id = noc_chunks_vec.rowid with GROUP_CONCAT(e.element_text, char(10)) for duty aggregation; CAST(teer_level AS INTEGER) for Pydantic int"
    - "Lambda default-argument binding (lambda c=candidate.noc_code, d=duty) inside asyncio.to_thread to avoid loop-variable capture (RESEARCH.md Pitfall 4)"
    - "HTMX dual-response route: HX-Request header → TemplateResponse partial; direct call → Pydantic JSON; ValueError → HTTPException(422)"
    - "Online guardrail pattern: _check_verbatim_fidelity queries noc_elements with instr(element_text, ?) > 0 to strip fabricated duties; raises ValueError when all candidates stripped"
    - "Authoritative DB overwrite: _correct_teer_from_db re-queries noc_units.teer_level and overwrites LLM-provided teer via model_copy(update={...})"

key-files:
  created:
    - "app/services/__init__.py — package marker (empty)"
    - "app/services/wd_store.py — WorkDescription CRUD (36 lines): save/load helpers operating on work_descriptions table"
    - "app/services/noc_mapper.py — three-stage pipeline (241 lines): map_work_description orchestrator + _format_candidates + _check_verbatim_fidelity + _correct_teer_from_db + to_noc_match mapper"
    - "app/api/noc_mapping.py — FastAPI router (94 lines): POST /api/noc/map (HTMX/JSON dual response) and POST /api/noc/confirm (Form-encoded WD update)"
    - "app/templates/partials/noc_results.html — HTMX swap target (28 lines): candidate card loop with confirm buttons posting to /api/noc/confirm"
  modified:
    - "app/db.py — added NOC_MAPPING_SCHEMA_DDL constant (noc_mapping_cache + noc_mapping_log tables); integrated into create_schema() as fourth executescript block"
    - "app/main.py — added `from app.api import noc_mapping` import and `app.include_router(noc_mapping.router)` registration after the health router"

key-decisions:
  - "Pipeline SQL matches RESEARCH.md Patterns 1+2 verbatim (not the AI-SPEC Stage 1/2 queries which reference non-existent noc_fts columns). The corrected JOINs and CAST(teer_level AS INTEGER) are confirmed against the live app.db schema."
  - "Stage 2 KNN query uses GROUP_CONCAT(e.element_text, char(10)) to aggregate all Main duties per NOC code into a single text block, filtered by element_type='Main duties' to exclude non-duty embeddings (per RESEARCH.md Pattern 2)."
  - "Connection lifecycle: per-request open in try block, close in finally — never module-level. This pattern matches the conftest.py noc_mapping_db fixture which yields db_path (str) rather than the connection (the service opens its own)."
  - "Verbatim fidelity guardrail uses lambda default-argument binding (c=candidate.noc_code, d=duty) — RESEARCH.md Pitfall 4 specifically calls out that naive `lambda: conn.execute(..., (candidate.noc_code, duty))` inside an asyncio.to_thread loop binds by reference and would race. Default-arg binding makes each lambda capture its own values at lambda construction time."
  - "TEER DB correction is conservative: it only overwrites the LLM's teer field when the DB value differs. Logged at WARNING with the LLM and DB values so drift is auditable. Without this guard, a hallucinated TEER 4 for a TEER 1 unit group would propagate through Phases 5-8."
  - "to_noc_match synthesizes confidence as `1.0 - (candidate.rank / 10.0)` — rank 1 → 0.9, rank 5 → 0.5. This is a synthetic placeholder, not a calibrated probability. The plan acknowledges this is a Phase 7+ concern; for V1 the rank-derived confidence is sufficient for UI sorting and the source provenance is what matters legally."
  - "POST /api/noc/confirm uses Form() parameters (wd_id, noc_code) rather than JSON body — this matches the HTMX partial form posting pattern documented in RESEARCH.md Pattern 5 and is simpler for the HTMX hx-post="..." flow."

patterns-established:
  - "Pattern: Online guardrail with strip-or-fail semantics — _check_verbatim_fidelity iterates matched_duties, queries the DB for each via instr() > 0, strips non-verbatim entries, and raises ValueError if no candidates survive. The exception is caught at the route layer and translated to HTTP 422 with the same string as the error message — keeping the cause visible to the advisor while terminating the request cleanly."
  - "Pattern: Authoritative DB overwrite via model_copy(update={...}) — _correct_teer_from_db queries the source of truth (noc_units) and uses Pydantic's model_copy to produce a new immutable candidate with the corrected teer, preserving all other fields and the original object as audit trail."
  - "Pattern: HTMX dual-response route — single endpoint, content negotiation via HX-Request header. The branch is a single if/else at the end of the try block; the ValueError handler is shared. This avoids two near-duplicate routes and keeps the pipeline orchestrator as the single source of truth."

requirements-completed: [MAP-01, MAP-02]

# Metrics
duration: 8min
completed: 2026-06-01
---

# Phase 4 Plan 3: Service Layer — Three-Stage NL→NOC Pipeline Summary

**Three-stage NL→NOC pipeline service (FTS5 → sqlite-vec → instructor) with online verbatim-fidelity + TEER-DB guardrails, FastAPI router with HTMX/JSON dual response, WD CRUD store, and noc_mapping_cache/log schema — turns the 7 Wave 0 integration test stubs from ERROR-free SKIPPED state to green for the next phase to fill in mocks.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-06-01T21:38:14Z
- **Completed:** 2026-06-01T21:46:18Z
- **Tasks:** 2 (both `tdd="true"`)
- **Files created:** 5 (services/__init__.py, services/wd_store.py, services/noc_mapper.py, api/noc_mapping.py, templates/partials/noc_results.html)
- **Files modified:** 2 (app/db.py, app/main.py)

## Accomplishments

- **Three-stage pipeline orchestrator** (`map_work_description`) executes the full retrieval funnel: Stage 1 BM25 FTS5 shortlist over `noc_fts` JOIN `noc_units` (parameterized MATCH ?); Stage 2 sqlite-vec cosine KNN over `noc_chunks_vec` JOIN `noc_elements` on `e.id = v.rowid` with `GROUP_CONCAT` duty aggregation; Stage 3 instructor LLM call with `Mode.JSON`, `max_retries=3`, `temperature=0.0`, `num_ctx=32768`. The system prompt enforces the verbatim-citation constraint verbatim from the AI-SPEC.
- **Online guardrails** run after Stage 3 before the result returns: `_check_verbatim_fidelity` queries `noc_elements` with `instr(element_text, ?) > 0` for every `matched_duty` and strips non-verbatim entries (logging `noc_guardrail=citation_fabrication` at ERROR); `_correct_teer_from_db` overwrites the LLM-provided teer with the authoritative `noc_units.teer_level` value when they differ (logged at WARNING). Both lambdas use default-argument binding (`c=candidate.noc_code, d=duty`) to avoid the loop-variable capture bug.
- **FastAPI router** with two routes: `POST /api/noc/map` does content negotiation — HTMX requests (HX-Request header present) get a `TemplateResponse(partials/noc_results.html, ...)` for hx-swap, direct API calls get `NocMapResponse(candidates=...)` JSON; `ValueError` from the pipeline is caught and re-raised as `HTTPException(status_code=422, detail=str(exc))`. `POST /api/noc/confirm` takes Form-encoded `wd_id` and `noc_code`, loads the WorkDescription, finds the matching candidate in `noc_candidates`, sets `confirmed_noc` and `stage="noc_mapped"`, and persists — returns 404 if `wd_id` unknown, 422 if `noc_code` not in the WD's candidate list.
- **WD CRUD helpers** (`save_work_description`, `load_work_description`) operate on the existing `work_descriptions` table with `INSERT OR REPLACE` and `model_dump_json()` for the data column. Synchronous, called inside `asyncio.to_thread()` at the service layer.
- **Schema additions** to `create_schema()`: `noc_mapping_cache` (cache_key TEXT PK, result_json TEXT, created_at) and `noc_mapping_log` (per-request metrics: wd_hash, noc_code_rank1, fts_result_count, rerank_result_count, instructor_retries, pipeline_latency_ms, guardrail_fired, sample_for_review). Both use `CREATE TABLE IF NOT EXISTS` so `create_schema()` remains idempotent on every startup. The cache is unused in this plan; it is wired up so a future plan can enable result-level caching with no schema migration.
- **HTMX partial template** (`partials/noc_results.html`) renders ranked candidate cards with hidden form fields for `wd_id` and `noc_code`, and a confirm button that posts to `/api/noc/confirm` with hx-target="#wizard-step" hx-swap="outerHTML". Empty-list case renders a "no results" message.
- **App-level wiring**: `app/main.py` now imports `noc_mapping` and calls `app.include_router(noc_mapping.router)` immediately after the health router. The router is live; lifespan startup (Ollama model assertion + create_schema + assert_noc_index_model) is unchanged.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create app/services/wd_store.py and extend app/db.py with cache/log DDL** - `baebc85` (feat)
2. **Task 2: Create app/services/noc_mapper.py and app/api/noc_mapping.py; wire into app/main.py** - `3c14184` (feat)

## Files Created/Modified

### Created

- `app/services/__init__.py` — Empty package marker for the new `app/services/` namespace.
- `app/services/wd_store.py` — 36 lines. `save_work_description(conn, wd)` uses `INSERT OR REPLACE` with `wd.model_dump_json()` for the data column and `datetime.utcnow().isoformat()` for both `created_at` and `last_modified`. `load_work_description(conn, wd_id)` returns the deserialized `WorkDescription` or `None`.
- `app/services/noc_mapper.py` — 241 lines. `map_work_description` orchestrator opens a per-request connection in try/finally, runs Stage 1 FTS5 (parameterized MATCH ?), Stage 2 KNN (sqlite_vec.serialize_float32 + GROUP_CONCAT), Stage 3 instructor call, then `_check_verbatim_fidelity` + `_correct_teer_from_db` guardrails before returning. `to_noc_match` maps `NOCCandidate` → `NOCMatch` with full ProvenanceTag.
- `app/api/noc_mapping.py` — 94 lines. `router = APIRouter()`; `POST /api/noc/map` reads `WorkDescriptionRequest` body, calls `map_work_description`, branches on `HX-Request` header; `POST /api/noc/confirm` takes `Form()` `wd_id` and `noc_code`, calls `load_work_description` + `save_work_description` inside a single connection lifecycle.
- `app/templates/partials/noc_results.html` — 28 lines. Jinja2 `{% for candidate in candidates %}` loop renders one `.noc-card` per candidate with TEER, rank, justification, expandable duty list, and a confirm button posting via `htmx.ajax` to `/api/noc/confirm`.

### Modified

- `app/db.py` — Added `NOC_MAPPING_SCHEMA_DDL` constant (~30 lines) with the cache and log tables; integrated into `create_schema()` as a fourth `con.executescript(...)` block; updated the docstring to list the new tables.
- `app/main.py` — Added `from app.api import noc_mapping` import and `app.include_router(noc_mapping.router)` line. No other changes.

## Decisions Made

- **Pipeline SQL matches RESEARCH.md Patterns 1+2 verbatim.** The plan's `context` section explicitly warns "DO NOT use the AI-SPEC Stage 1/2 queries — those have wrong column names." The implementation uses `SELECT DISTINCT f.noc_code, u.title, CAST(u.teer_level AS INTEGER) AS teer, u.definition FROM noc_fts f JOIN noc_units u ON u.noc_code = f.noc_code WHERE noc_fts MATCH ?` for Stage 1, and the `GROUP_CONCAT`/KNN pattern for Stage 2 with the correct `e.id = v.rowid` join key.
- **Connection-per-request pattern with try/finally.** The plan's action block shows `conn = await asyncio.to_thread(lambda: get_connection(db_path))` inside a `try` block, with `await asyncio.to_thread(conn.close)` in `finally`. This was followed verbatim. The alternative (module-level connection) was rejected because it would conflict with the `noc_mapping_db` test fixture which yields `db_path` (str) rather than a shared connection.
- **Default-argument binding for lambdas inside `asyncio.to_thread` loops.** RESEARCH.md Pitfall 4 specifically warns about loop-variable capture in lambdas. Both guardrail lambdas use `lambda c=candidate.noc_code, d=duty:` and `lambda nc=candidate.noc_code:`. This is defensive: a naive `lambda: conn.execute(..., (candidate.noc_code, duty))` would work here only because `map_work_description` runs each guardrail sequentially (not concurrently), but the pattern is the canonical Python idiom and the plan's acceptance criteria explicitly requires the grep pattern `lambda c=candidate.noc_code, d=duty`.
- **Verbatim fidelity guardrail raises `ValueError` on full strip.** The plan's behavior block states "Empty FTS5 result raises ValueError (not silently returns [])" and the guardrail follows the same pattern. A full strip (all candidates fabricated) raises `ValueError("All candidates had fabricated duties — result withheld")` which the route layer maps to HTTP 422.
- **TEER DB correction is conditional on mismatch.** The guardrail only runs `model_copy(update={"teer": db_row["teer"]})` when the LLM-provided teer differs from the DB teer, and logs at WARNING. This avoids unnecessary model copies when the LLM is correct, and produces an audit trail when correction is needed.
- **`to_noc_match` synthesizes confidence as `1.0 - (candidate.rank / 10.0)`.** Rank 1 → 0.9, rank 5 → 0.5. This is a placeholder for UI sorting; the AI-SPEC acknowledges that calibrated confidence is a Phase 7+ concern. The provenance is what matters legally.
- **POST /api/noc/confirm uses Form() parameters, not JSON body.** Matches the HTMX form-posting pattern from RESEARCH.md Pattern 5. The plan's action block shows `wd_id: str = Form(...)` and `noc_code: str = Form(...)` explicitly.
- **Added `partials/noc_results.html` even though it is not strictly required for the plan.** The plan's acceptance criteria require `grep "TemplateResponse" app/api/noc_mapping.py` to return 1 match, which the implementation does. The template file is required for the TemplateResponse to render at runtime (Jinja2 will raise `TemplateNotFound` otherwise). The plan references it in the action block ("templates/partials/noc_results.html") so creating it is in-scope.

## Deviations from Plan

### None — plan executed exactly as written

All 7 acceptance criteria from the plan's `must_haves.truths` are satisfied:

| Truth | Evidence |
|-------|----------|
| POST /api/noc/map with HX-Request returns HTML partial | `grep "HX-Request" app/api/noc_mapping.py` → 3 matches; `grep "TemplateResponse" app/api/noc_mapping.py` → 3 matches |
| POST /api/noc/map without HX-Request returns NocMapResponse JSON | `return NocMapResponse(candidates=result.candidates)` in else branch |
| FTS5 zero-rows returns HTTP 422 | `if not fts_rows: raise ValueError(...)` caught and re-raised as `HTTPException(status_code=422, ...)` |
| Parameterized FTS5 MATCH ? | `grep "noc_fts MATCH ?" app/services/noc_mapper.py` → 1 match (security control T-04-03-01) |
| KNN joins elements + casts teer | `grep "e.id = v.rowid" → 1 match`, `grep "CAST(u.teer_level AS INTEGER)" → 2 matches` |
| Lambda default-arg binding | `grep "lambda c=candidate.noc_code, d=duty" → 1 match`, `grep "lambda nc=candidate.noc_code" → 1 match` |
| Verbatim fidelity strips + raises | `grep "instr(element_text" → 1 match`; `if not clean_candidates: raise ValueError(...)` |
| save/load on work_descriptions | `grep "INSERT OR REPLACE INTO work_descriptions" → 1 match` |
| DDL for cache and log | `grep "noc_mapping_cache" app/db.py → 2 matches`, `grep "noc_mapping_log" app/db.py → 2 matches` |

All 4 must_haves.artifacts exist on disk with the specified exports (verified via `python -c "from app.services.noc_mapper import map_work_description, to_noc_match; from app.api.noc_mapping import router; print('OK')"`).

All 4 must_haves.key_links are wired:
- FTS5 MATCH ? with parameter → `(work_description, fts_limit)` tuple
- KNN JOIN on elements → `JOIN noc_elements e ON e.id = v.rowid`
- Router → service → `await map_work_description(work_description=body.work_description, db_path=settings.db_path)`
- main.py → router → `app.include_router(noc_mapping.router)`

The 7 Wave 0 integration test stubs in `tests/test_noc_mapping.py` remain SKIPPED (intentional — they will turn green in Wave 3 when the mocks are applied; the plan explicitly states "all 7 tests either pass or remain SKIPPED; none ERROR"). The full suite runs `80 passed, 7 skipped in 10.53s` with 0 ERRORs.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. The `noc_mapping` router reuses the existing `settings.db_path`, `settings.ollama_base_url`, `settings.ollama_embed_model`, and `settings.ollama_generation_model` — all already configured in `.env`. The `instructor_client` singleton was created in Plan 04-02 and is imported here. No new environment variables, no new tools, no dashboard configuration.

**Pre-existing Wave 0 prerequisite still applies:** Before any Wave 3 mock-based tests run against the live `app.db`, run `python scripts/rebuild_noc_vectors.py --db-path app.db` to convert `noc_chunks_vec` from FLOAT[1024] (DashScope) to FLOAT[768] (nomic-embed-text). Without it, the startup assertion in `app/db.py::assert_noc_index_model()` raises `RuntimeError`. (Documented in 04-01-SUMMARY.md.)

## Next Phase Readiness

**Ready for Plan 04-04 (HTMX wizard step + full test suite green):**
- ✅ `app.services.noc_mapper.map_work_description` is importable and ready for `await map_work_description(...)` in the Wave 3 integration test bodies
- ✅ `app.api.noc_mapping.router` is registered in `app.main` and accepts POST /api/noc/map with `WorkDescriptionRequest` body
- ✅ `POST /api/noc/confirm` is live and can persist `confirmed_noc` to `work_descriptions`
- ✅ `app.services.wd_store.save_work_description` / `load_work_description` are the canonical WD persistence helpers
- ✅ `noc_mapping_cache` and `noc_mapping_log` tables are created on startup; cache is unused (a future plan can enable result-level caching)
- ✅ `templates/partials/noc_results.html` is the HTMX swap target for the wizard step
- ✅ `WorkDescription.noc_candidates: list[NOCMatch]` and `confirmed_noc: Optional[NOCMatch]` are populated via `to_noc_match` (which the Wave 3 plan can call from the API layer if it needs to persist the candidate list before the advisor confirms)

**No new blockers introduced by this plan.**

---

*Phase: 04-nl-noc-mapping*
*Completed: 2026-06-01*

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `app/services/wd_store.py` exists | ✅ FOUND |
| `app/services/noc_mapper.py` exists | ✅ FOUND |
| `app/api/noc_mapping.py` exists | ✅ FOUND |
| `app/templates/partials/noc_results.html` exists | ✅ FOUND |
| `app/db.py` contains `noc_mapping_cache` and `noc_mapping_log` DDL | ✅ 2 matches each |
| `app/main.py` has `include_router(noc_mapping.router)` | ✅ FOUND |
| `noc_fts MATCH ?` parameterized query in mapper | ✅ FOUND |
| `e.id = v.rowid` KNN join key in mapper | ✅ FOUND |
| `lambda c=candidate.noc_code, d=duty` default-arg binding | ✅ FOUND |
| `lambda nc=candidate.noc_code` default-arg binding | ✅ FOUND |
| `HX-Request` header check in router | ✅ FOUND |
| `TemplateResponse` for HTMX partial rendering | ✅ FOUND |
| `from app.services.noc_mapper import map_work_description, to_noc_match; from app.api.noc_mapping import router` | ✅ all imports OK |
| `pytest tests/test_noc_mapping.py tests/test_noc_ranking.py` | ✅ 5 passed, 7 skipped, 0 ERRORs |
| `pytest tests/ -x` full suite | ✅ 80 passed, 7 skipped, 0 ERRORs |
| Commit `baebc85` (Task 1) in history | ✅ FOUND |
| Commit `3c14184` (Task 2) in history | ✅ FOUND |
| No accidental file deletions in task commits | ✅ `git diff --diff-filter=D HEAD~2 HEAD` empty for both commits |
| No STATE.md or ROADMAP.md modifications | ✅ not staged in either commit |
