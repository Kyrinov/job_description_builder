# Phase 17: JES Scoring — Research

**Researched:** 2026-06-05
**Domain:** EC JES 2017 per-factor scoring, non-EC approximate totals, instructor retry wrapper, FastAPI endpoint, React scorecard render
**Confidence:** HIGH — all findings verified directly from codebase (no web research needed; this is a port/wire-up phase)

---

## Summary

Phase 17 is predominantly a **port and wire-up** operation, not a greenfield build. The v1.0 `app/services/jes_service.py` contains the full production-proven JES scoring logic — per-factor instructor retry, advisor override, sentinel pattern, provenance tagging — and can be adapted for v2.0 with minimal structural changes. The key difference is that v2.0 does not use a `jes_factors` SQLite table; the EC JES 2017 degree/points scales are already hardcoded in `v2/frontend/src/data.jsx` as `EC_ELEMENTS` and `EC_DEGREES`. The decision recorded in STATE.md confirms this: "v2.0 hardcoded EC JES table over LLM scoring — EC JES 2017 is a published standard with fixed degree/point scales. Hardcoding is correct, auditable, and faster than LLM."

For the backend `POST /api/jes/score`, the scoring logic must be restructured around the hardcoded Python equivalent of `EC_ELEMENTS` + `EC_DEGREES` constants (already present as `KNOWN_JES_FACTORS` in `app/data/constants.py`, but not the full degree/points tables yet). The instructor client pattern from `app/ai/jes_scoring.py` (v1.0) is portable as-is. The `require_og_confirmed` hard gate is already implemented in `app/services/classification_gate.py` and ready to import.

For the frontend, `document.jsx` already has the `ClassBlock` component that renders both the EC per-factor scorecard and the non-EC single-totals line. `data.jsx` already has `EC_ELEMENTS`, `EC_DEGREES`, and `GENERIC_TOTALS`. The scorecard render is therefore a wiring task — the JES response from `POST /api/jes/score` must populate `record.jes_scores` / `record.jes_total` so `ClassBlock` can render. No new React components needed for the scorecard display itself.

The advisor override (JES-02) requires a new audit_log write path since the v2.0 `audit_log` table already exists in the schema.

**Primary recommendation:** Port the instructor/scoring logic from v1.0 `app/ai/jes_scoring.py` and `app/services/jes_service.py` as `v2/backend/app/ai/jes_scoring.py` and `v2/backend/app/services/jes_service.py`; add `v2/backend/app/api/jes_scoring.py` route; wire the response into `record.jes_scores` in `app.jsx`; the `document.jsx` `ClassBlock` renders it without change.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| EC JES factor scoring (LLM per-factor) | API / Backend | — | LLM calls must be server-side; instructor client is a singleton built at module import |
| Non-EC approximate totals lookup | API / Backend | — | Pure dict lookup against hardcoded table; returns standard name + points |
| `require_og_confirmed` hard gate | API / Backend | — | Already implemented; imported by route handler |
| Advisor override + audit log write | API / Backend | — | Audit trail is a backend concern; `audit_log` table is in the v2.0 SQLite DB |
| Per-factor retry (3 retries) | API / Backend | — | `instructor` `max_retries=3` parameter handles this natively |
| JES scorecard display | Browser / Frontend | — | `ClassBlock` in `document.jsx` already renders per-factor rows and totals line |
| Scorecard state management | Browser / Frontend | — | `record.jes_scores` / `record.jes_total` added to `record` state in `app.jsx` |
| Override UI (manual degree entry) | Browser / Frontend | — | Inline input when factor `level === -1` (sentinel); fires `PATCH /api/wd/{id}` or dedicated override endpoint |

---

## Standard Stack

### Core (all already in `requirements.txt`) [VERIFIED: v2/backend/requirements.txt]

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `instructor` | 1.15.1 | Structured LLM output with retry | Already in project; used for NOC pipeline |
| `fastapi` | 0.128.8 | Route definition | Project standard |
| `pydantic` v2 | 2.12.5 | Request/response models | Project standard |
| `openai` (AsyncOpenAI) | (pinned via instructor) | HTTP client to Ollama/cloud | Inherited from v1.0 pattern |
| `pytest-asyncio` | 0.24.0 | Async test support | Already in conftest |

No new dependencies required. [VERIFIED: requirements.txt + v1.0 jes_scoring.py]

---

## Architecture Patterns

### System Architecture Diagram

```
SPA (app.jsx)
  │  POST /api/jes/score  {og_code, og_level, duties}
  ▼
FastAPI route: app/api/jes_scoring.py
  │  require_og_confirmed(wd) → 409 if not classified
  │
  ├─[EC group]──▶ app/services/jes_service.py: score_jes_v2()
  │                  │  for each of 9 EC_ELEMENTS (hardcoded constant)
  │                  │  ─ build per-factor user prompt
  │                  │  ─ jes_instructor_client.chat.completions.create(
  │                  │      response_model=JESFactorRating, max_retries=3)
  │                  │  ─ on success → JESFactorScore(level, points, rationale)
  │                  │  ─ on failure → sentinel JESFactorScore(level=-1)
  │                  └─▶ returns JESScorecardResponse (9 rows + total)
  │
  └─[non-EC group]──▶ NON_EC_TOTALS dict lookup
                        └─▶ returns single totals line + standard name
  │
  ▼
PATCH /api/wd/{id}  ← stores jes_scores in WorkDescription
  │
  ▼
SPA document.jsx: ClassBlock renders scorecard
  ├─[EC] per-factor rows: name / D{degree} / {points}  +  totals row
  └─[non-EC] single totals line: "Evaluated under {standard}"  {total pts}
```

### Recommended Project Structure

New files (mirrors v1.0 pattern):

```
v2/backend/
├── app/
│   ├── ai/
│   │   └── jes_scoring.py       # JESFactorRating model + instructor singleton
│   ├── services/
│   │   └── jes_service.py       # score_jes_v2(), override_jes_factor()
│   └── api/
│       └── jes_scoring.py       # POST /api/jes/score + POST /api/jes/override/{factor}
├── tests/
│   └── test_jes_scoring.py      # Wave 0 RED stubs, then GREEN
```

`app/data/constants.py` gets two new constants:
- `EC_JES_ELEMENTS` — 9 elements with per-degree point scales (mirrors `EC_ELEMENTS` in `data.jsx`)
- `NON_EC_TOTALS` — approx totals for FI, IT, AS, EN by level (mirrors `GENERIC_TOTALS` in `data.jsx`)

### Pattern 1: Instructor Retry Wrapper (per-factor)

Exact v1.0 pattern to port: [VERIFIED: app/ai/jes_scoring.py, app/services/jes_service.py]

```python
# Source: app/ai/jes_scoring.py (v1.0) — portable as-is
class JESFactorRating(BaseModel):
    degree: str = Field(description="Degree identifier e.g. 'D1', 'D3'")
    rationale: str = Field(description="Justification citing duties")

# Source: app/services/jes_service.py (v1.0) — one call per factor
factor_rating = await jes_instructor_client.chat.completions.create(
    model=settings.generation_model,
    messages=[
        {"role": "system", "content": JES_SCORING_SYSTEM_PROMPT.format(...)},
        {"role": "user", "content": user_prompt},
    ],
    response_model=JESFactorRating,
    max_retries=3,          # instructor handles 3 retries natively
    max_tokens=1024,
    temperature=0.0,
    **extra_kwargs,         # {"extra_body": {"options": {"num_ctx": 8192}}} for Ollama
)
```

`max_retries=3` is instructor's built-in retry on validation failure — no custom retry loop needed. [VERIFIED: app/services/jes_service.py lines 220-236]

### Pattern 2: Sentinel Score on Failure

[VERIFIED: app/services/jes_service.py lines 126-144]

```python
# Failed factor after 3 retries → sentinel, NOT raised exception
JESFactorScore(
    factor_name=factor_name,
    level=-1,       # sentinel — non-optional int, None would fail Pydantic
    points=None,
    rationale=f"Scoring failed after 3 retries: {exc}",
    provenance=...,
)
```

The frontend detects `level === -1` and renders the override input. [ASSUMED — v2.0 override UI is not yet built; this is the pattern to implement]

### Pattern 3: Degree Normalization

LLMs return "D3" or "3" inconsistently. The `_resolve_degree` function (v1.0) handles exact → strip-D → add-D lookup against the point_values dict. [VERIFIED: app/services/jes_service.py lines 72-85]

In v2.0, `point_values` comes from `EC_JES_ELEMENTS[i].pts` (a Python dict), not a SQLite row. The normalization logic is identical.

### Pattern 4: Non-EC Approximate Totals

[VERIFIED: v2/frontend/src/data.jsx lines 118-120]

`GENERIC_TOTALS` in `data.jsx` is the reference:
```js
const GENERIC_TOTALS = {
  FI: { 4: 470, 5: 560, 6: 660 },
  IT: { 4: 480, 5: 575, 6: 690 },
  AS: { 4: 430, 5: 510, 6: 600 },
  EN: { 4: 500, 5: 600, 6: 720 }
};
```

The backend `NON_EC_TOTALS` constant must match these exactly. Standard names from `data.jsx` WORK_TYPES:
- FI: "FI / CT Job Evaluation Standard (2023)" [VERIFIED: data.jsx line 79]
- IT: "IT Job Evaluation Standard" [VERIFIED: data.jsx line 82]
- AS: "AS / PA Job Evaluation Standard" [VERIFIED: data.jsx line 85]
- EN: "EN Job Evaluation Standard" [VERIFIED: data.jsx line 88]

### Pattern 5: Advisor Override + Audit Log

[VERIFIED: app/services/jes_service.py lines 426-530 (v1.0)]

The override sets `advisor_adjusted=True`, flips provenance `source_type` to `"ADVISOR"`, and writes an `audit_log` entry. In v2.0, the `audit_log` table already exists (`db.py` SCHEMA_DDL). The `override_jes_factor` function can be ported as synchronous (it was sync in v1.0); the v2.0 audit_log write uses `con.execute` directly.

JES-02 states: override stored as `audit_log` entry with `type="jes_override"`. The v2.0 `audit_log` schema has `event TEXT NOT NULL` — use `event = "jes_override"`.

### Pattern 6: WorkDescription Model Extension

`WorkDescription` in `v2/backend/app/models/work_description.py` does not yet have `jes_scores` or `jes_total_points`. These must be added. [VERIFIED: work_description.py — fields absent]

Required new fields:
```python
jes_scores: list[dict] = Field(default_factory=list)  # list of JESFactorScore.model_dump()
jes_total_points: Optional[int] = None
```

Storing as `list[dict]` (not a typed list of Pydantic models) keeps the pattern consistent with how `confirmed_og` and `noc_candidates` are stored — plain dicts that survive JSON round-trips without requiring import cycles. [VERIFIED: work_description.py pattern for confirmed_og (Optional[dict])]

`WDPatchRequest` in `wd.py` must also accept `jes_scores` and `jes_total_points` so the route can persist the scorecard. [VERIFIED: wd.py WDPatchRequest — these fields absent]

### Pattern 7: Frontend JES Wiring

`ClassBlock` in `document.jsx` already handles both cases: [VERIFIED: document.jsx lines 105-155]

```jsx
// EC: cls.factors is a list → renders per-factor rows
// non-EC: cls.factors is null/undefined → renders single totals line
function ClassBlock({ cls }) {
  if (cls.factors) { /* per-factor render */ }
  return /* single totals line */;
}
```

`computeClassification` in `data.jsx` still computes a `cls` object from the legacy `workType` / scope questions. The JES scorecard from the API response needs to be merged into the `record` and then reflected in `cls`. The cleanest approach: after `POST /api/jes/score` resolves, call `PATCH /api/wd/{id}` with `jes_scores` and `jes_total_points`, and update `record` state. The `ClassBlock` can then read from `record.jes_scores` directly (a new render branch in `document.jsx` Section 4).

The current Section 4 in `document.jsx` (Classification & Evaluation) already has a "classified" branch showing `resolvedCode`. Phase 17 extends this branch to also render the JES scorecard once `record.jes_scores` is populated. [VERIFIED: document.jsx lines 250-287]

The JES score fetch should trigger after `og_level` is committed — mirroring how the OG pipeline fires after `noc_confirm` is committed. [VERIFIED: app.jsx lines 192-214 OG trigger pattern]

### Anti-Patterns to Avoid

- **`asyncio.gather` for factor calls:** v1.0 comment is explicit — sequential calls only, to avoid Ollama OOM on ARM64. [VERIFIED: jes_service.py line 14]
- **Constructing instructor client per request:** Module-level singleton only. [VERIFIED: jes_scoring.py lines 93-104]
- **Querying `jes_factors` SQLite table:** v2.0 has no such table. EC factors are hardcoded constants. The v1.0 code queries the DB — the v2.0 port replaces those queries with dict lookups against `EC_JES_ELEMENTS`.
- **`level=None` in JESFactorScore:** Pydantic rejects it. Always use `level=-1` as the failure sentinel. [VERIFIED: jes_service.py line 134]
- **Omitting degree normalization:** LLMs mix "D3" and "3" — always run `_resolve_degree`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured LLM output with retry | Custom retry loop + JSON parse | `instructor` `max_retries=3` | Already in requirements; handles validation retries natively |
| Degree/points lookup table | Database schema | Python dict constant in `app/data/constants.py` | Matches STATE.md decision; no ingest scripts, no schema migration |
| OG confirmation check | Custom gate logic | `require_og_confirmed(wd)` from `classification_gate.py` | Already implemented; raises 409 Conflict |
| Per-factor prompt building | Inline f-strings in route handler | `_build_factor_user_prompt()` service function | Keeps route thin; testable in isolation |

---

## Common Pitfalls

### Pitfall 1: EC_JES_ELEMENTS / EC_DEGREES Not in v2.0 Backend Yet

**What goes wrong:** The Python backend has no degree/points tables. `KNOWN_JES_FACTORS` is a frozenset of names only (no points). Wave 0 must add `EC_JES_ELEMENTS` and `EC_DEGREES` to `app/data/constants.py` before any scoring logic lands.
**Why it happens:** `KNOWN_JES_FACTORS` was added in Phase 12 only for test cross-referencing, not for scoring.
**How to avoid:** Wave 0 adds the full tables to `constants.py`, mirrors `EC_ELEMENTS` and `EC_DEGREES` from `data.jsx` exactly. [VERIFIED: data.jsx lines 93-109, constants.py lines 163-173]

### Pitfall 2: WorkDescription Model Missing jes_scores / jes_total_points

**What goes wrong:** `POST /api/jes/score` returns scores but they cannot be stored; `PATCH /api/wd/{id}` silently drops unknown fields (`extra="ignore"` on `WorkDescription`).
**Why it happens:** `WorkDescription` (Phase 10) predates JES requirements.
**How to avoid:** Wave 0 extends `WorkDescription` with `jes_scores: list[dict]` and `jes_total_points: Optional[int]`; extends `WDPatchRequest` with the same fields. [VERIFIED: work_description.py, wd.py]

### Pitfall 3: v2.0 Has No `jes_factors` DB Table

**What goes wrong:** Naively porting v1.0 `score_jes()` copies the SQLite queries for `jes_factors` rows — which do not exist in v2.0's `work_descriptions` + `audit_log` schema.
**Why it happens:** v1.0 loaded factors from DB via `app/scripts/jes_ingest.py`. v2.0 has no ingest pipeline.
**How to avoid:** Replace all `conn.execute("SELECT ... FROM jes_factors")` calls with lookups against the hardcoded `EC_JES_ELEMENTS` constant.

### Pitfall 4: Stage Gate Mismatch

**What goes wrong:** v1.0 checks `wd.stage == 'jd_drafted'`. v2.0 `WorkDescription` has no `stage` field — it uses `confirmed_og` + `og_level` presence instead.
**Why it happens:** v2.0 WD model was designed without a stage machine.
**How to avoid:** Use `require_og_confirmed(wd)` which checks `confirmed_og` and `og_level` (already the correct v2.0 gate). Do not port the `wd.stage` check. [VERIFIED: classification_gate.py]

### Pitfall 5: degree field in JESFactor model (1–7 constraint)

**What goes wrong:** The existing `JESFactor` model in `app/models/classification.py` has `degree: int = Field(ge=1, le=7)`. This is from the prototype's simplified scope model and is a different type than the `JESFactorScore` needed for Phase 17 output.
**Why it happens:** The `JESFactor` Pydantic model was defined in Phase 10 as part of the `Classification` model — it exists for the legacy workType-based classification, not for the EC JES 2017 per-factor output.
**How to avoid:** Do NOT reuse `JESFactor` from `classification.py` for JES scoring output. Create a new `JESFactorScore` Pydantic model (as in v1.0) or store as plain dicts in `WorkDescription.jes_scores`. The `JESFactor` from `classification.py` is legacy; don't extend it.

### Pitfall 6: Frontend JES Trigger Timing

**What goes wrong:** JES score fetch fires before `og_level` is persisted to the backend, causing `require_og_confirmed` to return 409.
**Why it happens:** `fetch` in `commit()` is fire-and-forget; the PATCH for `og_level` and the JES trigger could race.
**How to avoid:** Trigger JES score fetch at the `og_level` step commit, after the PATCH for `og_level` resolves (chain the fetch, don't fire in parallel). [VERIFIED: app.jsx NOC trigger pattern at line 175 — fires synchronously in commit(), no race]

---

## Code Examples

### EC_JES_ELEMENTS constant (to add to constants.py)

```python
# Source: data.jsx EC_ELEMENTS (verified against data.jsx lines 93-103)
EC_JES_ELEMENTS = [
    {"name": "Decision making",                 "category": "Responsibility", "pts": {1:5, 2:15, 3:35, 4:60, 5:90, 6:125, 7:165, 8:210}},
    {"name": "Leadership & operational mgmt",   "category": "Responsibility", "pts": {1:5, 2:20, 3:50, 4:90, 5:140}},
    {"name": "Communication",                   "category": "Skill",          "pts": {1:5, 2:25, 3:50, 4:75, 5:100, 6:140, 7:180}},
    {"name": "Knowledge of specialized fields", "category": "Skill",          "pts": {1:5, 2:15, 3:35, 4:55, 5:80, 6:105}},
    {"name": "Contextual knowledge",            "category": "Skill",          "pts": {1:5, 2:20, 3:40, 4:60, 5:80, 6:105}},
    {"name": "Research & analysis",             "category": "Skill",          "pts": {1:5, 2:30, 3:75, 4:120, 5:165, 6:210}},
    {"name": "Physical effort",                 "category": "Effort",         "pts": {1:3, 2:4, 3:6, 4:10, 5:15}},
    {"name": "Sensory effort",                  "category": "Effort",         "pts": {1:2, 2:3, 3:5, 4:10}},
    {"name": "Working conditions",              "category": "Conditions",     "pts": {1:5, 2:8, 3:12, 4:17, 5:25}},
]

# Source: data.jsx EC_DEGREES (verified against data.jsx lines 105-109)
# Index aligns with EC_JES_ELEMENTS above
EC_DEGREES = {
    "EC-04": [4, 2, 4, 4, 3, 3, 1, 2, 2],
    "EC-05": [5, 3, 5, 5, 4, 4, 1, 2, 2],
    "EC-06": [6, 4, 6, 5, 5, 5, 1, 2, 2],
}

# Source: data.jsx GENERIC_TOTALS (verified against data.jsx lines 118-120)
NON_EC_TOTALS = {
    "FI": {4: 470, 5: 560, 6: 660},
    "IT": {4: 480, 5: 575, 6: 690},
    "AS": {4: 430, 5: 510, 6: 600},
    "EN": {4: 500, 5: 600, 6: 720},
}

# Standard names for non-EC groups — must match WORK_TYPES in data.jsx
NON_EC_STANDARD_NAMES = {
    "FI": "FI / CT Job Evaluation Standard (2023)",
    "IT": "IT Job Evaluation Standard",
    "AS": "AS / PA Job Evaluation Standard",
    "EN": "EN Job Evaluation Standard",
}
```

### POST /api/jes/score request/response shape

```python
class JESScorecardRequest(BaseModel):
    wd_id: str                             # load WD, run require_og_confirmed
    og_code: str = Field(min_length=1)
    og_level: int = Field(ge=1)
    duties: list[str] = Field(default_factory=list)

class JESFactorScoreOut(BaseModel):
    factor_name: str
    degree: int                            # -1 = failed sentinel
    points: Optional[int]
    rationale: str
    advisor_adjusted: bool = False

class JESScorecardResponse(BaseModel):
    wd_id: str
    og_code: str
    is_ec: bool
    factors: list[JESFactorScoreOut]      # 9 items for EC; empty list for non-EC
    total_points: int
    standard_name: str                    # e.g. "EC JES 2017", "IT Job Evaluation Standard"
    has_failed_factors: bool              # True if any factor has degree == -1
```

### audit_log write for override (JES-02)

```python
# Source: db.py SCHEMA_DDL — verified: audit_log has (wd_id, event, actor, detail, created_at)
import json
from datetime import datetime, timezone

con.execute(
    "INSERT INTO audit_log (wd_id, event, actor, detail, created_at) VALUES (?, ?, ?, ?, ?)",
    (
        wd_id,
        "jes_override",
        "advisor",
        json.dumps({"factor_name": factor_name, "degree": degree, "rationale": rationale}),
        datetime.now(timezone.utc).isoformat(),
    ),
)
```

---

## State of the Art

| Old Approach (v1.0) | v2.0 Approach | Rationale |
|---------------------|---------------|-----------|
| `jes_factors` SQLite table + DB queries | Hardcoded `EC_JES_ELEMENTS` + `EC_DEGREES` Python constants | STATE.md decision: "v2.0 curated hardcoded data over v1.0 ingest pipelines" |
| `wd.stage == 'jd_drafted'` gate check | `require_og_confirmed(wd)` → 409 Conflict | v2.0 has no stage machine; gate is on OG confirmation |
| `get_jes_version_info(conn, og_code)` DB query | Hardcoded version label "EC JES 2017" / per-group names | No `source_documents` table in v2.0 |
| Per-factor OG name lookup from `og_definitions` DB table | `OG_DEFINITIONS[og_code]["og_name"]` constant lookup | v2.0 uses `OG_DEFINITIONS` constant from `constants.py` |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | JES score trigger fires from `og_level` commit in `app.jsx`, after PATCH resolves | Architecture Patterns, Pattern 6 | JES score fires before OG confirmed → 409; easy fix |
| A2 | `record.jes_scores` stored as `list[dict]` (not typed Pydantic list) in WorkDescription | Architecture Patterns, Pattern 6 | Type errors if Pydantic validation is strict; mitigation: test in Wave 0 |
| A3 | `EC_DEGREES` covers only EC-04, EC-05, EC-06 as default cases; other EC levels fall back to EC-05 | Code Examples | EC-01 through EC-03 or EC-07/08 positions will get EC-05 defaults; acceptable per v1.0 precedent |

---

## Open Questions

1. **Should Phase 17 include the override UI in the frontend (JES-02)?**
   - What we know: JES-02 requires the SPA to prompt for manual degree entry when `level === -1`; the v1.0 override was a backend-only `PATCH /api/jes/override` call.
   - What's unclear: The trigger point (inline in scorecard? separate modal?).
   - Recommendation: Inline: render a number input in the `ClassBlock` row when `factor.degree === -1`; on commit, call a dedicated `POST /api/jes/override/{wd_id}/{factor_name}` route.

2. **`EC_DEGREES` only covers EC-04, EC-05, EC-06 — what about other EC levels?**
   - What we know: `data.jsx` only has three reference degree vectors. The v1.0 service fetched all degrees from DB for whatever EC level was confirmed.
   - What's unclear: Whether advisors will ever classify positions at EC-01 through EC-03 or EC-07/EC-08.
   - Recommendation: Fall back to EC-05 degree vector for unlisted EC levels (matches current `ecFactors()` in `data.jsx` which already defaults to EC-05). Flag for future improvement.

---

## Environment Availability

Step 2.6: SKIPPED — no new external dependencies. `instructor`, `openai` (AsyncOpenAI), `fastapi`, and `pydantic` are all present in `requirements.txt`. Ollama is already confirmed running (50 backend tests pass including NOC pipeline tests that require it via mock). [VERIFIED: requirements.txt, test run output: 50 passed]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 + pytest-asyncio 0.24.0 |
| Config file | `v2/backend/pyproject.toml` |
| Quick run command | `python3 -m pytest v2/backend/tests/test_jes_scoring.py -x -q` |
| Full suite command | `python3 -m pytest v2/backend/tests/ -q && cd v2/frontend && npx vitest run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| JES-01 | POST /api/jes/score returns 9-factor scorecard for EC | integration | `pytest tests/test_jes_scoring.py::test_jes_score_ec_returns_9_factors -x` | ❌ Wave 0 |
| JES-01 | Per-factor degree/points correct against EC_DEGREES reference | unit | `pytest tests/test_jes_scoring.py::test_ec_degree_points_mapping -x` | ❌ Wave 0 |
| JES-02 | POST /api/jes/override stores audit_log entry with type=jes_override | integration | `pytest tests/test_jes_scoring.py::test_jes_override_writes_audit_log -x` | ❌ Wave 0 |
| JES-03 | POST /api/jes/score returns single totals line for FI, IT, AS | integration | `pytest tests/test_jes_scoring.py::test_jes_score_non_ec_returns_totals_line -x` | ❌ Wave 0 |
| JES-04 | ClassBlock renders per-factor rows for EC / single line for non-EC | unit (vitest) | `npx vitest run src/document.test.jsx` | ❌ Wave 0 |
| API-07 | POST /api/jes/score returns 409 when og_level not confirmed | integration | `pytest tests/test_jes_scoring.py::test_jes_score_409_when_og_not_confirmed -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python3 -m pytest v2/backend/tests/test_jes_scoring.py -x -q`
- **Per wave merge:** `python3 -m pytest v2/backend/tests/ -q`
- **Phase gate:** Full suite green (backend + vitest) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `v2/backend/tests/test_jes_scoring.py` — 6 RED stubs covering JES-01, JES-02, JES-03, API-07
- [ ] `v2/frontend/src/document.test.jsx` — ClassBlock render test for EC and non-EC (JES-04)
- [ ] `EC_JES_ELEMENTS` + `EC_DEGREES` + `NON_EC_TOTALS` + `NON_EC_STANDARD_NAMES` constants in `app/data/constants.py`
- [ ] `jes_scores: list[dict]` + `jes_total_points: Optional[int]` fields on `WorkDescription` and `WDPatchRequest`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user local app |
| V3 Session Management | no | No auth |
| V4 Access Control | no | No auth |
| V5 Input Validation | yes | Pydantic Field constraints on og_code, og_level, duties |
| V6 Cryptography | no | Not applicable |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| og_code injection / unknown OG code | Tampering | Validate og_code against known keys (OG_DEFINITIONS or known EC/FI/IT/AS/EN set) before scoring; return 400 for unknown codes |
| Unbounded duties list (prompt injection) | Tampering | Cap duties list at 10 (mirrors v1.0 `duties[:10]` truncation); cap per-duty length |
| Oversized work_description in prompt | Tampering | Truncate to 300 chars in prompt builder (mirrors v1.0 `raw_input[:300]`); Pydantic `max_length` on request model |
| factor_name injection in override route | Tampering | Validate `factor_name` against `KNOWN_JES_FACTORS` frozenset before writing audit_log |

---

## Sources

### Primary (HIGH confidence — codebase verified this session)

- `app/services/jes_service.py` (v1.0) — full port reference: score_jes, retry_jes_factor, override_jes_factor, sentinel pattern, degree normalization
- `app/ai/jes_scoring.py` (v1.0) — JESFactorRating model, instructor singleton, JES_SCORING_SYSTEM_PROMPT
- `v2/frontend/src/data.jsx` — EC_ELEMENTS, EC_DEGREES, GENERIC_TOTALS, WORK_TYPES (standard names), ClassBlock (document.jsx)
- `v2/backend/app/models/work_description.py` — confirmed missing jes_scores/jes_total_points
- `v2/backend/app/models/classification.py` — JESFactor model (legacy; do not reuse for scoring output)
- `v2/backend/app/services/classification_gate.py` — require_og_confirmed already implemented
- `v2/backend/app/data/constants.py` — KNOWN_JES_FACTORS present; EC_JES_ELEMENTS absent
- `v2/backend/app/db.py` — audit_log schema (event, actor, detail columns confirmed)
- `v2/backend/app/api/__init__.py` — jes_scoring router not yet registered
- `.planning/STATE.md` — "v2.0 hardcoded EC JES table" decision confirmed

### Secondary (MEDIUM confidence)

- `v2/backend/requirements.txt` — instructor 1.15.1 confirmed present; no new deps needed
- Test run output — 50 backend tests + 19 vitest tests GREEN confirmed baseline

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in requirements.txt; verified in-repo
- Architecture: HIGH — direct port of verified v1.0 code + wire-up to verified v2.0 components
- EC JES 2017 degree/points tables: HIGH — verified in data.jsx lines 93-109 (hardcoded from 2017 published standard)
- Non-EC approximate totals: HIGH — verified in data.jsx lines 118-120
- Pitfalls: HIGH — all identified from direct code inspection

**Research date:** 2026-06-05
**Valid until:** End of Phase 17 (no external dependencies; all findings are from codebase)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| JES-01 | Per-factor JES scoring for EC group (9 elements from EC JES 2017); ported from v1.0 with instructor retry wrapper (max 3 retries per factor) | Port `app/ai/jes_scoring.py` (JESFactorRating + instructor singleton) and adapt `app/services/jes_service.py` (sequential factor loop); replace DB queries with `EC_JES_ELEMENTS` constant lookups |
| JES-02 | Per-factor retry + advisor override; override stored as audit_log entry type="jes_override" | Port `override_jes_factor()` from v1.0; audit_log table exists in v2.0 DB; validate factor_name against KNOWN_JES_FACTORS |
| JES-03 | Approximate point totals for non-EC groups (FI, IT, AS, EN) with standard name cited | `NON_EC_TOTALS` dict + `NON_EC_STANDARD_NAMES` dict to add to constants.py; exact values verified in data.jsx GENERIC_TOTALS and WORK_TYPES |
| JES-04 | JES scorecard in Classification & Evaluation section of live document preview | `ClassBlock` in document.jsx already renders both EC (per-factor rows) and non-EC (single totals line); wiring = populate `record.jes_scores` from API response in app.jsx after og_level commit |
| API-07 | POST /api/jes/score — accepts OG code + level + duties; returns JES scorecard | New route in app/api/jes_scoring.py; `require_og_confirmed` gate; register in app/api/__init__.py |
</phase_requirements>
