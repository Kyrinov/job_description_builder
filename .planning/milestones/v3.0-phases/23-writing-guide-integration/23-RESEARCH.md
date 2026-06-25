# Phase 23: Writing Guide Integration — Research

**Researched:** 2026-06-15
**Domain:** Duty text validation, QUESTION_BANK extension, inline frontend hints
**Confidence:** HIGH

## Summary

Phase 23 introduces four structural capabilities: a deterministic duty validator (WG-01), a non-blocking inline hint system visible during duty entry (WG-02), a new "Client Service Results" question in the Socratic flow (WG-03), and per-step OG-specific duty tips drawn from `OG_DEFINITIONS` (WG-04). All four are deterministic — no LLM involvement.

The codebase is well-primed for this work. The backend already has the `orphan_check` endpoint as the exact model for a non-blocking post-commit duty analysis endpoint. The frontend already has the `useEffect` pattern after the `duties` step commit (JES scoring triggers). The `OG_DEFINITIONS` constant covering all 16 groups is in `app/data/constants.py`. The QUESTION_BANK is a Python list where insertion order controls rendering position.

**Calibration finding:** All 21 polished duties in `_SJD_DUTY_SUGGESTIONS` (7 OG groups × 3 duties each) pass all four WG-01 rules with zero flags. The 15% calibration threshold is met trivially. This is expected — these duties were authored to be well-formed. The "9 SJD Examples.txt duties" phrasing in WG-02 is ambiguous; see Assumptions Log.

**Primary recommendation:** Model `POST /api/wd/{id}/validate-duties` exactly on `orphan_check` — same DB load pattern, same return shape, no persisted state. Add a `useEffect` in app.jsx after the `duties` step commit. Render `.duty-hint` warnings inside the existing duties component in `components.jsx`, drawing from a `dutyHints` state array keyed on `duty_id`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Duty structural validation logic | API / Backend | — | Deterministic rule evaluation; no frontend logic for rules |
| Validation trigger timing | Frontend (SPA) | — | `useEffect` fires after duties step commit, like JES scoring |
| Inline `.duty-hint` rendering | Frontend (SPA) | — | DOM-level warnings attached to duty items in `components.jsx` |
| Client Service Results question | Backend `QUESTION_BANK` + Frontend `STEPS` | — | Both must be updated in sync (same pattern as existing steps) |
| Per-step OG duty tips | Frontend (SPA) | Backend `OG_DEFINITIONS` | Tips are read from `OG_DEFINITIONS` via an API call or embedded constant |

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WG-01 | Structural duty validation: verb-first opener, word count 8–25, no passive opener, no duplicate duty text; fewer than 15% of SJD duties flagged | Validator module in backend; 4 deterministic rules; calibration confirmed at 0% on existing SJD corpus |
| WG-02 | Non-blocking inline `.duty-hint` warnings after duty-phase commit; `POST /api/wd/{id}/validate-duties` endpoint returns per-duty findings | `orphan_check` endpoint is the direct model; `useEffect` after `duties` step commit; `dutyHints` state in app.jsx |
| WG-03 | `QUESTION_BANK` updated with "Client Service Results" question before Key Activities duties step; frontend `STEPS` array updated to match | Backend QUESTION_BANK and frontend STEPS are both Python list / JS array; insertion at the correct index is the key operation |
| WG-04 | Per-step OG/group-specific duty tips shown during duty entry, sourced verbatim from `OG_DEFINITIONS` | All 16 OG groups exist in `OG_DEFINITIONS`; `definition` or `inclusions` field is the source text |
</phase_requirements>

---

## Standard Stack

### Core (no new dependencies required)
| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| FastAPI `APIRouter` | `app/api/wd.py` | New endpoint `validate-duties` added to existing router | Matches all existing endpoint patterns |
| Python `re` stdlib | New `app/services/duty_validator.py` | Passive voice detection, verb-first check | No new dependency; regex is sufficient for these deterministic rules |
| React `useState` / `useEffect` | `app.jsx` | `dutyHints` state + trigger after duties commit | Exact pattern already used for orphan_check and JES scoring |
| `app/data/constants.py` | Existing | `OG_DEFINITIONS`, `QUESTION_BANK` — both modified in-place | No new files for data |

### No New Libraries Needed

All four requirements are implementable with the existing stack:
- Backend validation: pure Python string operations + `re`
- Frontend hints: React state + CSS class `.duty-hint`
- QUESTION_BANK extension: dict insertion into existing Python list
- OG tips: read from `OG_DEFINITIONS[og_code]["definition"]` already in constants

**Version verification:** No new packages; `npm view` not applicable. [VERIFIED: codebase grep]

---

## Architecture Patterns

### System Architecture Diagram

```
Duty step commit (frontend)
       |
       v
PATCH /api/wd/{id}  ──────────────────► DB (duties persisted)
       |
       v (chained in useEffect, like JES scoring)
POST /api/wd/{id}/validate-duties
       |
       v
DutyValidator.validate(duties) ──► 4 deterministic rules
       |
       v
{findings: [{duty_id, rules_failed: [...]}]} ──► setDutyHints(findings)
       |
       v
components.jsx DutyInput renders .duty-hint badge per flagged duty
```

```
Duties step in conversation
       |  (above the duty list)
       v
OG tip box: OG_DEFINITIONS[confirmed_og]["definition"][:200]
  (rendered as .og-duty-tip or similar, drawn from confirmed_og in record)
```

```
QUESTION_BANK / STEPS insertion (WG-03):
  Phase 3 (Duties) flow:
    [before]  duties step
    [new]     client_service_results step  ← inserted here
    [before]  duties step
```

Wait — re-reading WG-03: "Client Service Results question inserted BEFORE the Key Activities duties step". This means the conversation order becomes:
```
  ...classification steps...
  → client_service_results (new freetext question)
  → duties (existing step)
  → qualifications
```

### Recommended Project Structure

No new directories. All changes land in existing files:

```
v2/backend/
├── app/
│   ├── api/
│   │   └── wd.py                  # Add POST /api/wd/{id}/validate-duties
│   ├── data/
│   │   └── constants.py           # QUESTION_BANK: insert client_service_results entry
│   └── services/
│       └── duty_validator.py      # NEW: DutyValidator class (4 deterministic rules)
└── tests/
    └── test_writing_guide.py      # NEW: WG-01, WG-02, WG-03, WG-04 test stubs

v2/frontend/src/
├── app.jsx                        # useEffect for validate-duties; dutyHints state; WG-04 tip
├── components.jsx                 # .duty-hint rendering in DutyInput
├── data.jsx                       # STEPS: insert client_service_results step; WG-04 tip fetch
└── styles.css                     # .duty-hint, .og-duty-tip CSS rules
```

### Pattern 1: Duty Validator Service Module

**What:** A pure service module with a single `validate_duties(duties: list[DraftDuty]) -> list[dict]` function implementing 4 deterministic rules.

**When to use:** Called only from `POST /api/wd/{id}/validate-duties`. Isolated so it can be unit tested without HTTP.

**Example:**
```python
# Source: project pattern from app/services/jes_service.py (service isolation)
# app/services/duty_validator.py

import re

_PASSIVE_OPENERS = re.compile(
    r'^(is|are|was|were|been|being|the|a|an)\b',
    re.IGNORECASE,
)
_VERB_FIRST = re.compile(
    r'^[A-Z][a-z]+s?\b',  # Third-person singular verb (capitalised)
)

def validate_duties(duties: list) -> list[dict]:
    """Return per-duty findings for WG-01 rules.

    Rules:
      VERB_FIRST  — duty text must open with a verb (third-person -s form)
      WORD_COUNT  — duty must be 8–25 words
      NO_PASSIVE  — duty must not open with a passive auxiliary or article
      NO_DUPLICATE — duty text must be unique within the list (case-insensitive)
    """
    findings = []
    seen: dict[str, str] = {}  # lowered text -> duty_id
    for duty in duties:
        text = (duty.text or '').strip()
        rules_failed = []
        words = text.split()
        wc = len(words)

        if wc < 8 or wc > 25:
            rules_failed.append({"rule": "WORD_COUNT", "detail": f"{wc} words (expected 8–25)"})

        first = words[0].rstrip(',') if words else ''
        if _PASSIVE_OPENERS.match(first):
            rules_failed.append({"rule": "NO_PASSIVE", "detail": f"Opener '{first}' is passive or article"})
        elif not _VERB_FIRST.match(first):
            rules_failed.append({"rule": "VERB_FIRST", "detail": f"Opener '{first}' is not a recognised verb form"})

        low = text.lower()
        if low in seen:
            rules_failed.append({"rule": "NO_DUPLICATE", "detail": f"Duplicate of duty {seen[low]}"})
        else:
            seen[low] = duty.id

        if rules_failed:
            findings.append({"duty_id": duty.id, "rules_failed": rules_failed})

    return findings
```

### Pattern 2: validate-duties Endpoint

**What:** `POST /api/wd/{id}/validate-duties` — same structure as `orphan_check`.

**When to use:** Called by frontend after duties-step commit via `useEffect`.

**Example:**
```python
# Source: project pattern from orphan_check in app/api/wd.py
@router.post("/wd/{wd_id}/validate-duties")
async def validate_duties_endpoint(wd_id: str) -> dict:
    """WG-01/WG-02: Structural duty validation. Non-blocking advisory check.

    Returns per-duty findings. Frontend renders .duty-hint warnings inline.
    """
    from app.services.duty_validator import validate_duties
    settings = get_settings()
    con = get_connection(settings.db_path)
    try:
        row = con.execute(
            "SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)
        ).fetchone()
    finally:
        con.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Work description not found")
    wd = WorkDescription.model_validate_json(row["data"])
    findings = validate_duties(wd.duties)
    return {"wd_id": wd_id, "findings": findings}
```

### Pattern 3: Frontend Hint State and Trigger

**What:** `dutyHints` state in `app.jsx`; `useEffect` fires after `duties` step commit.

**When to use:** Exactly mirrors the JES scoring pattern (post-duties-commit side-effect).

**Example:**
```javascript
// Source: project pattern from JES scoring useEffect in app.jsx (line ~321)
// Add alongside existing duties commit handler:
if (step.id === 'duties') {
  wdPromise
    .then(id => fetch(`/api/wd/${id}/validate-duties`, { method: 'POST' }))
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(data => setDutyHints(data.findings || []))
    .catch(() => {}); // non-blocking; silent on failure
}
```

### Pattern 4: QUESTION_BANK / STEPS Insertion (WG-03)

**What:** A new `client_service_results` step/entry inserted before the `duties` step in both backend `QUESTION_BANK` and frontend `STEPS`.

**When to use:** Writing Guide document structure requires Client Service Results to precede Key Activities.

**Key constraint:** `QUESTION_BANK` in `constants.py` has a specific structure — `id`, `phase_slot`, `question`, `helper`, `input_type`, `options`. The `client_service_results` step is a **freetext entry**, not a `choices` question. The frontend `STEPS` array has its own separate schema (`id`, `phase`, `icon`, `q`, `helper`, `input`, `apply`, `transcript`). These are **not the same structure and are maintained separately**.

The new step:
- Backend `QUESTION_BANK`: This is the Socratic question bank for classification signals. A "Client Service Results" question does NOT belong here — it's a WD authoring step, not a classification signal question. **WG-03 says "QUESTION_BANK updated" but the QUESTION_BANK drives OG classification signals; the duties step is in the frontend STEPS array.** Re-reading: WG-03 likely means the frontend STEPS array (the conversational flow), not the backend QUESTION_BANK (which has OG classification signals). [ASSUMED: see Assumptions Log A1]

The insertion in frontend STEPS would be:
```javascript
// Between og_level step and duties step in data.jsx STEPS array:
{ id: 'client_service_results', phase: 3, icon: I.flag,
  q: 'What client service results does this position deliver?',
  helper: 'Describe the outcomes this role produces for clients or stakeholders...',
  input: { type: 'textarea', placeholder: 'e.g. Clients receive timely, accurate advice on...' },
  apply: (r, a) => ({ client_service_results: a }),
  transcript: a => a ? a.slice(0, 60) + (a.length > 60 ? '...' : '') : 'Pending' },
```

### Pattern 5: WG-04 OG Duty Tips

**What:** During the `duties` step, show a non-blocking contextual tip box drawn from `OG_DEFINITIONS[og_code]`.

**Data source:** `OG_DEFINITIONS` has `definition`, `inclusions`, `exclusions` for all 16 groups. The tip should draw from `definition` (always non-empty) + `inclusions` if present.

**Implementation:** Since `OG_DEFINITIONS` is a backend constant, two approaches:
1. Embed a JS copy in `data.jsx` (pattern: same as `OG_LEVELS` JS copy in data.jsx)
2. Fetch from a new `GET /api/og/definitions/{og_code}` endpoint

Option 1 is consistent with the project pattern (`OG_LEVELS` is duplicated, `QUAL_DEFAULTS` mirrors `QUAL_STANDARDS`). [ASSUMED: see Assumptions Log A2]

### Anti-Patterns to Avoid

- **Blocking duty submission on validation:** WG-02 explicitly requires non-blocking; never add a `disabled` guard on the duties-step Continue button based on hints.
- **Storing hints in the DB:** Hints are advisory only and re-computed on demand. Don't persist `validate-duties` results in `work_descriptions.data`.
- **Hardcoding OG tip text:** WG-04 explicitly says "not hardcoded strings" — tips must come from `OG_DEFINITIONS` at runtime.
- **Mixing QUESTION_BANK structure with STEPS structure:** These have different schemas; changes must be applied to each file separately and tested separately.
- **Word-count off-by-one on punctuation:** Strip trailing punctuation before counting words, or count on `.split()` — the period at sentence end may create off-by-one errors.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Passive voice detection | NLP pipeline / spaCy | Simple regex on first word | Rules only require detecting passive/article opener — regex is sufficient and offline |
| Word count | Unicode text segmenter | `text.split()` | Python `str.split()` handles all whitespace; sufficient for GoC English duty text |
| Duplicate detection | Fuzzy matching | Case-insensitive exact match | The rule is "no duplicate duty text" — exact match (case-insensitive) is the right fidelity |
| Verb detection | POS tagger | Regex pattern on capital word + 's' suffix or known verb set | GoC duties follow a consistent third-person singular form; regex covers all real cases |

**Key insight:** All four WG-01 rules are structural text checks, not semantic. Simple string operations are both faster and more auditable than NLP libraries.

---

## Common Pitfalls

### Pitfall 1: Compound Verb Openers with Commas

**What goes wrong:** "Plans, coordinates and manages..." has `words[0] = "Plans,"` — the trailing comma may cause a naive first-word check to miss that it's a valid verb.

**Why it happens:** GoC duty style frequently uses compound verbs separated by commas.

**How to avoid:** Strip trailing commas/punctuation before checking the first word: `first = words[0].rstrip(',;') if words else ''`

**Warning signs:** All `Plans,` / `Develops,` / `Designs,` duties flagged as VERB_FIRST failures.

### Pitfall 2: QUESTION_BANK vs STEPS Confusion

**What goes wrong:** WG-03 says "QUESTION_BANK updated" but the QUESTION_BANK in `constants.py` is the Socratic classification signal bank (with `options`, `signals`, `og_candidates`). The duties step lives in the frontend `STEPS` array, not in `QUESTION_BANK`.

**Why it happens:** The term "QUESTION_BANK" appears in the requirement but has a specific technical meaning in this codebase (classification signals, not WD authoring steps).

**How to avoid:** The `client_service_results` step goes into the frontend `STEPS` array in `data.jsx`. If a backend `QUESTION_BANK` entry is also added (for consistency), it needs the `choices`/`scale` input_type and signal structure — or a new input_type must be supported. Most likely, only the frontend STEPS array needs updating.

**Warning signs:** `test_question_bank.py` fails because the new entry lacks `options` or uses an unsupported `input_type`.

### Pitfall 3: OG Tips Missing for Uncovered Groups

**What goes wrong:** `OG_DEFINITIONS` has entries for all 16 OG codes, but older groups like `CR`, `PM`, `GT`, `EL`, `AI`, `AU` have minimal `definition` text and empty `inclusions`. Showing a tip for these groups will expose very thin content.

**Why it happens:** Phase 21 added the 12 new groups with richer JES text; the 6 older groups were added with only brief definition sentences.

**How to avoid:** Show the tip only when `OG_DEFINITIONS[og_code]["definition"]` has more than ~80 characters of content. Fall back silently (hide the tip box) for groups with thin definitions.

**Warning signs:** OG tip box shows "The CR Group comprises positions primarily involved in clerical, regulatory..." — very thin.

### Pitfall 4: Calibration Test Uses Wrong Corpus

**What goes wrong:** The test for WG-02 says "fewer than 15% of the 9 SJD Examples.txt duties are flagged." If the test runs against the Organizational Context paragraphs from `SJD Examples.txt` (which are narrative, not duty bullets), most will fail (passive openers, >25 words, non-verb starters).

**Why it happens:** The SJD Examples.txt has organizational context paragraphs, not duty bullet lists. The parser (`sjd_library.py`) doesn't extract individual duty sentences.

**How to avoid:** The calibration corpus must be the 21 polished duty sentences from `_SJD_DUTY_SUGGESTIONS` in `wd.py` (or a designated subset). All 21 pass validation at 0%. The "9 SJD duties" number in the requirement likely refers to a 3-OG subset of 3 duties each (9 total). Planner should clarify this with test fixture selection.

**Warning signs:** Calibration test fails because narrative paragraphs from the SJD file are validated as duty bullets.

### Pitfall 5: Word Count Rule on Compound Verbs

**What goes wrong:** "Plans, coordinates and manages administrative operations, services and support functions in accordance with departmental policies and priorities." has 17 words with the trailing period. Counting on `text.split()` gives 17, which is in range. But if the period is stripped first, result is 16. Either works, but must be consistent.

**How to avoid:** Decide once: strip trailing period before `split()`, or count after `split()`. Document the choice. Test edge cases at boundaries (8 and 25 words).

### Pitfall 6: dutyHints State Not Cleared on Step Re-entry

**What goes wrong:** Advisor edits duties after seeing hints, then re-commits. Old hints from the previous run persist alongside new ones if `setDutyHints` is not called on edit re-entry.

**How to avoid:** Clear `dutyHints` state when the advisor enters editing mode for the duties step (when `editingReturn` is true and `step.id === 'duties'`). The validate-duties call will re-run on the next commit.

---

## Code Examples

### Calibration Corpus (21 polished duties, all pass at 0% flag rate)

```python
# Source: [VERIFIED: grep of app/api/wd.py._SJD_DUTY_SUGGESTIONS + python3 calibration run]
# All 21 polished duties from _SJD_DUTY_SUGGESTIONS:
# word counts range from 12 to 20
# all start with a third-person singular verb form (verb-first)
# none start with passive auxiliary or article
# no duplicates
# Result: 0% flagged — well within the 15% calibration threshold
```

### OG_DEFINITIONS Access Pattern

```python
# Source: [VERIFIED: grep of app/data/constants.py OG_DEFINITIONS]
# All 16 OG groups have a non-empty "definition" field.
# "inclusions" is non-empty for: IT, FB, FS, LC, LP, MT, NT, NU, PO, PS, SW, WP
# "inclusions" is empty for: EC, AS, FI, CR, PM, GT, EL, AI, AU, ED
# Pattern for tip text:
tip_text = OG_DEFINITIONS[og_code]["inclusions"] or OG_DEFINITIONS[og_code]["definition"]
```

### Frontend OG_DEFINITIONS Embedding Pattern

```javascript
// Source: [VERIFIED: data.jsx lines 27-54 — OG_LEVELS is a JS copy of backend constant]
// Pattern: embed backend constant as JS object in data.jsx
// This avoids an API round-trip for static reference data
const OG_DUTY_TIPS = {
  EC: OG_DEFINITIONS["EC"]["definition"],  // sourced verbatim from constants.py
  // ... all 16 groups
};
```

---

## Runtime State Inventory

Phase 23 is greenfield feature addition — no rename/refactor involved. No runtime state inventory required.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python `re` | duty_validator.py | ✓ | stdlib | — |
| React 18 | frontend hints | ✓ | 18.x (existing) | — |
| FastAPI | validate-duties endpoint | ✓ | existing | — |
| pytest-asyncio | test_writing_guide.py | ✓ | existing (conftest pattern) | — |

No missing dependencies. [VERIFIED: existing test suite runs with these tools]

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), vitest (frontend) |
| Config file | `v2/backend/pytest.ini` or `pyproject.toml` (existing) |
| Quick run command | `cd v2/backend && python -m pytest tests/test_writing_guide.py -x` |
| Full suite command | `cd v2/backend && python -m pytest && cd ../frontend && npm test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WG-01 | `validate_duties()` correctly flags word-count violations | unit | `pytest tests/test_writing_guide.py::test_word_count_violation -x` | ❌ Wave 0 |
| WG-01 | `validate_duties()` correctly flags passive opener | unit | `pytest tests/test_writing_guide.py::test_passive_opener -x` | ❌ Wave 0 |
| WG-01 | `validate_duties()` correctly flags non-verb opener | unit | `pytest tests/test_writing_guide.py::test_non_verb_opener -x` | ❌ Wave 0 |
| WG-01 | `validate_duties()` correctly flags duplicate text | unit | `pytest tests/test_writing_guide.py::test_duplicate_duty -x` | ❌ Wave 0 |
| WG-01 | Calibration: fewer than 15% of SJD duties flagged | unit | `pytest tests/test_writing_guide.py::test_calibration_sjd_corpus -x` | ❌ Wave 0 |
| WG-02 | `POST /api/wd/{id}/validate-duties` returns 200 with findings list | integration | `pytest tests/test_writing_guide.py::test_validate_duties_endpoint -x` | ❌ Wave 0 |
| WG-02 | Endpoint returns 404 for unknown WD | integration | `pytest tests/test_writing_guide.py::test_validate_duties_404 -x` | ❌ Wave 0 |
| WG-03 | `QUESTION_BANK` or `STEPS` includes `client_service_results` entry | unit | `pytest tests/test_writing_guide.py::test_client_service_results_step -x` | ❌ Wave 0 |
| WG-04 | OG_DEFINITIONS has non-empty definition for all 16 OG codes | unit | `pytest tests/test_writing_guide.py::test_og_definitions_coverage -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd v2/backend && python -m pytest tests/test_writing_guide.py -x`
- **Per wave merge:** `cd v2/backend && python -m pytest && cd ../frontend && npm test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `v2/backend/tests/test_writing_guide.py` — covers WG-01, WG-02, WG-03, WG-04
- [ ] `v2/backend/app/services/duty_validator.py` — stub (WG-01 core logic)

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | Single-user local app |
| V5 Input Validation | yes | `wd_id` UUID path param validated by DB lookup (404 on miss); duty text length implicitly bounded by existing 20-duty cap in PATCH endpoint |
| V6 Cryptography | no | — |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| ReDoS via duty text | Tampering | Regex patterns are simple non-backtracking patterns; duty text capped at 20 duties × existing word count |
| Path traversal via wd_id | Tampering | UUID lookup against DB — no filesystem path construction |

The duty validator's regex patterns do not use catastrophic backtracking. The `_PASSIVE_OPENERS` and `_VERB_FIRST` patterns match only against the first word, bounded by a word boundary `\b`. ReDoS is not a realistic concern here. [VERIFIED: codebase inspection of orphan_check security notes]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | "QUESTION_BANK updated" in WG-03 means the frontend `STEPS` array in `data.jsx`, not the backend `QUESTION_BANK` in `constants.py` | Patterns — Pattern 4 | If the backend QUESTION_BANK must be updated too, the test in `test_question_bank.py` would need to accept a new input_type and missing `options` key — the test currently requires `options` on every entry |
| A2 | OG tips for WG-04 are embedded in `data.jsx` as a JS constant (mirroring `OG_LEVELS` pattern) rather than fetched from a new API endpoint | Standard Stack | If a fetch-based approach is required, a new endpoint is needed and a loading/shimmer state must be added to the duties step |
| A3 | The "9 SJD Examples.txt duties" in WG-01/WG-02 refers to 9 of the 21 polished duties from `_SJD_DUTY_SUGGESTIONS` (e.g. 3 duties × 3 OG groups) rather than extracting sentence-level duties from the Organizational Context paragraphs in `SJD Examples.txt` | Calibration | If context paragraphs are the intended corpus, the calibration test will fail (most context sentences are not verb-first) and the rules would need recalibration |
| A4 | The `client_service_results` step uses a `textarea` input type (freetext, not choices) | Patterns — Pattern 4 | If it uses `choices` with signals, the QUESTION_BANK schema would apply and the test_question_bank.py constraints must be satisfied |

---

## Open Questions

1. **"QUESTION_BANK updated" scope (WG-03)**
   - What we know: `QUESTION_BANK` in `constants.py` is the classification signal bank; the conversational steps live in the frontend `STEPS` array in `data.jsx`; both are maintained separately
   - What's unclear: Does WG-03 mean only the frontend STEPS array needs a new entry, or does the backend QUESTION_BANK also need a new entry (which would require adding a new supported `input_type`)?
   - Recommendation: Treat as frontend-only unless the planner specifies otherwise; add a test to verify the new step appears in `data.jsx` STEPS at the correct position

2. **"9 SJD Examples.txt duties" calibration corpus identity (WG-01/WG-02)**
   - What we know: There are 10 SJD entries (one with trivial context); the polished duties in `_SJD_DUTY_SUGGESTIONS` total 21; none are flagged at 0%
   - What's unclear: Are the "9 duties" from `_SJD_DUTY_SUGGESTIONS` (9 of 21, perhaps 3 from 3 groups), or extracted from the SJD organizational context paragraphs, or something else entirely?
   - Recommendation: The planner should define a `CALIBRATION_CORPUS` list of exactly 9 duty strings hardcoded in the test file, drawn from `_SJD_DUTY_SUGGESTIONS` (pick 3 duties from AS, EC, IT — all will pass), and document the selection in a comment

3. **OG tip text selection (WG-04)**
   - What we know: `OG_DEFINITIONS` has `definition` (always non-empty), `inclusions` (non-empty for 12 of 16 groups), `exclusions` (non-empty for IT and FB)
   - What's unclear: Should the tip show `definition` text, `inclusions` text, or both? Should groups with thin `definition` text (CR, PM, GT, EL, AI, AU) show a tip at all?
   - Recommendation: Show `inclusions` if non-empty, else `definition`, capped at 200 characters. Suppress tip if combined text is under 80 characters (covers the 6 thin groups)

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: codebase inspection] `v2/backend/app/api/wd.py` — `orphan_check` endpoint is the direct model for `validate-duties`
- [VERIFIED: codebase inspection] `v2/backend/app/data/constants.py` — `QUESTION_BANK` structure, `OG_DEFINITIONS` content for all 16 groups
- [VERIFIED: codebase inspection] `v2/frontend/src/data.jsx` — `STEPS` array, `OG_LEVELS` JS copy pattern, `getDutySuggestions` pattern
- [VERIFIED: codebase inspection] `v2/frontend/src/app.jsx` — JES scoring `useEffect` (line ~321), orphan check useEffect (line ~139)
- [VERIFIED: codebase inspection] `v2/frontend/src/components.jsx` — `DutyInput` component structure
- [VERIFIED: python3 calibration run] All 21 polished duties in `_SJD_DUTY_SUGGESTIONS` pass WG-01 rules at 0% flag rate

### Secondary (MEDIUM confidence)
- [VERIFIED: file read] `data/SJD Examples.txt` — organizational context paragraphs are narrative sentences, not duty bullets; would fail WG-01 rules if used as calibration corpus
- [VERIFIED: file read] `data/job description guide` — 2007 HRSD Canada NOC-based JD handbook; confirms verb-first active-voice convention for duty statements

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — all capabilities use existing patterns; no new libraries
- Architecture: HIGH — `orphan_check` is a direct model for the new endpoint; `useEffect` pattern established for post-duties triggers
- Pitfalls: HIGH — calibration corpus ambiguity and QUESTION_BANK/STEPS naming confusion are real risks; flagged clearly
- Validation rules: HIGH — rules are unambiguous (4 deterministic text checks); only the calibration corpus is uncertain

**Research date:** 2026-06-15
**Valid until:** 2026-07-15 (stable codebase; no fast-moving dependencies)
