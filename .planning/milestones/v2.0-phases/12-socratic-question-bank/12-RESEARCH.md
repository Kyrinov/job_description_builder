# Phase 12: Socratic Question Bank — Research

**Researched:** 2026-06-04
**Domain:** Classification question bank design — Python data constant, Socratic signal accumulation, OG candidate derivation
**Confidence:** HIGH (all findings verified against the codebase; domain knowledge on EC/AS/IT/FI work types is [ASSUMED] where TBS definitions are not in-repo)

---

## Summary

Phase 12 is a **pure design-and-data artifact phase** — no new API endpoint, no new UI. The deliverable is a hardcoded Python constant (`QUESTION_BANK`) co-located with `OG_LEVELS` and `CAF_RANK_OG_EQUIVALENCE` in `v2/backend/app/data/constants.py`, plus a test module `tests/test_question_bank.py` that validates structure and cross-references.

The phase replaces the prototype's direct work-type picker (`WORK_TYPES` array in `data.jsx`, which lets a manager explicitly choose "EC", "FI", "IT", "AS") with a structured interview: the manager answers work-description questions (natural language), and the system accumulates "OG candidate signal" entries. Phase 15 will wire these entries into the conversation flow; Phase 16 will run the ranking engine against accumulated signals. Phase 12 only creates and validates the artifact that drives those later phases.

The scope of content required is modest: cover the four primary groups (EC, IT, AS, FI) as stated in QUES-01. Each question must be answerable without domain knowledge (the manager describes what the person *does*, not which group they belong to). Signals must map to OG candidate codes that exist in `OG_LEVELS` and to JES factor names that are known in `EC_ELEMENTS` (already defined in the prototype).

**Primary recommendation:** Implement `QUESTION_BANK` as a Python list-of-dicts constant appended to `constants.py`. Two plans suffice: Wave 0 stubs + structure definition, then content population and tests green.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Question bank data artifact | Backend data layer | — | Pure Python constant, imported by both Phase 15 conversation flow and Phase 16 classifier |
| OG candidate signal accumulation | Backend service (Phase 16) | — | Phase 12 only defines the signal schema; the accumulation logic lives in Phase 16's OG classifier |
| Rendering question entries as choice cards | Frontend SPA (Phase 15) | — | Phase 12 provides the data; Phase 15 reads and renders it |
| Structure validation | Backend test layer | — | `test_question_bank.py` validates keys, OG code cross-references, JES factor cross-references |

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QUES-01 | Hardcoded question bank artifact (JSON or Python constant) with entries for AS, EC, IT, FI; each entry has question text, answer options, classification signal mapping (OG candidate codes + JES factor hints) | Structure design in Architecture Patterns; JES factor names verified from prototype `EC_ELEMENTS`; OG codes verified from `OG_LEVELS` in `constants.py` |
| QUES-02 | Enforces Socratic constraint: manager never selects OG directly; OG candidates derived from accumulated answer signals | Question content design in Code Examples; all question text avoids naming OG groups; signals are OG codes, not user-visible labels |
| QUES-03 | Question bank entries drive the Work Type phase in the conversation flow; Phase 15 renders and routes answers to NOC pipeline and OG classifier | Interface contract defined in Architecture Patterns; no Phase 15 code needed in Phase 12 — artifact is the deliverable |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python (stdlib only) | ≥3.10 | Question bank is a plain dict/list constant | Zero dependencies — matches existing `constants.py` pattern [VERIFIED: v2/backend/requirements.txt] |
| pytest | 8.3.4 | Structure validation tests | Already installed; test pattern mirrors `test_constants.py` [VERIFIED: requirements.txt] |
| pydantic v2 | 2.12.5 | Optional runtime schema validation of entries at import | Already installed; use only if runtime guard is needed — may be overkill for a static constant |

### No New Dependencies Required
This phase adds no new packages. `QUESTION_BANK` is a Python list-of-dicts constant; `test_question_bank.py` uses only `pytest`. [VERIFIED: codebase inspection]

---

## Architecture Patterns

### Data Flow

```
constants.py (QUESTION_BANK)
        |
        ├─── tests/test_question_bank.py     (Phase 12: structure + cross-reference validation)
        |
        ├─── Phase 15: conversation.jsx      (renders question entries as choice-card steps)
        |
        └─── Phase 16: og_classifier.py      (reads accumulated signals → OG candidates)
```

### Recommended Project Structure

Phase 12 touches exactly two files:

```
v2/backend/
├── app/data/
│   └── constants.py          ← append QUESTION_BANK below existing constants
└── tests/
    └── test_question_bank.py  ← new test module (QUES-01 validation)
```

No new directories. No new modules. [VERIFIED: v2/backend/app/data/ and tests/ already exist]

### Pattern 1: Question Bank Entry Schema

Each entry in `QUESTION_BANK` is a dict with the following required keys:

```python
# Source: designed for this phase; mirrors test_constants.py validation pattern
{
    "id": str,           # stable slug, used by Phase 15 for stepId routing
    "phase_slot": str,   # "work_type" — the conversation phase this belongs to
    "question": str,     # plain-language question shown to the manager
    "helper": str,       # sub-label (matches prototype step helper pattern)
    "input_type": str,   # "choices" | "scale" — matches Phase 15 input controls
    "options": [         # list of answer option dicts
        {
            "id": str,       # stable slug
            "label": str,    # display text
            "signals": {     # classification signals emitted when this option is selected
                "og_candidates": list[str],  # OG codes, e.g. ["EC", "AS"]
                "jes_factor_hints": list[str],  # factor names from EC_ELEMENTS
                "teer_affinity": list[int],  # NOC TEER levels this answer aligns with
            }
        }
    ]
}
```

**Key constraint (QUES-02):** No `question` text or `label` text may contain the strings "EC", "AS", "IT", "FI", "occupational group", or "classification group". The OG codes live only inside `signals.og_candidates`, never in user-visible text.

### Pattern 2: Signal Accumulation Contract (for Phase 16)

Phase 12 does not implement accumulation — it only defines the signal schema. The planner must document the interface contract so Phase 16 can consume it correctly:

```python
# Canonical shape of accumulated signals after a conversation session
# (Phase 16 will read this structure — Phase 12 just establishes the schema)
accumulated_signals = {
    "og_candidates": Counter,    # {og_code: vote_count}
    "jes_factor_hints": Counter, # {factor_name: vote_count}
    "teer_affinity": Counter,    # {teer_level: vote_count}
}
```

This is a reference schema for Phase 16. Phase 12 only needs to ensure every `signals` dict in `QUESTION_BANK` is compatible with this shape.

### Pattern 3: Existing Classification Model Compatibility

`v2/backend/app/models/classification.py` has `work_type: Literal["EC", "FI", "IT", "AS", "EN"]`. The question bank signals must produce output compatible with this field. The resolution rule (most-voted OG code wins) is Phase 16's job — Phase 12 just emits valid OG codes.

**Current `Classification` model gap:** `level: Optional[int] = Field(default=None, ge=4, le=6)` — the level validator hardcodes 4-6. This contradicts `OG_LEVELS` where EC goes 1-8. This is a Phase 16 bug to fix, not Phase 12's concern. Phase 12's tests should NOT validate against the `Classification` model; they validate against `OG_LEVELS` directly.

### Pattern 4: Question Content Design

Based on the prototype's `WORK_TYPES` and the EC JES 2017 factors, a minimal complete set covers **3 discriminating questions** that together distinguish EC / AS / IT / FI without naming the group:

| Question theme | Discriminates |
|----------------|--------------|
| Nature of the primary work output | EC (analysis/advice) vs AS (admin/coordination) vs IT (systems/data) vs FI (financial) |
| Who the work informs (internal admin vs external policy) | EC vs AS |
| Technical domain of knowledge | IT vs FI vs EC vs AS |

A 4–6 question bank is sufficient. More questions add refinement but Phase 15 needs a manageable flow. [ASSUMED — TBS doesn't publish a canonical discriminating question set]

**Concrete question design (verified against prototype WORK_TYPES, EC_ELEMENTS, and OG_LEVELS):**

```
Q1: "What best describes the main type of output this person produces?"
    Options:
    - "Analysis, recommendations, or policy advice" → og_candidates: ["EC"], jes_hints: ["Research & analysis", "Decision making"]
    - "Financial plans, budgets, or costing reports" → og_candidates: ["FI"], jes_hints: ["Knowledge of specialized fields"]
    - "Systems, applications, or digital services" → og_candidates: ["IT"], jes_hints: ["Knowledge of specialized fields"]
    - "Administrative coordination and support" → og_candidates: ["AS"], jes_hints: ["Leadership & operational mgmt"]

Q2: "Who primarily uses what this person produces?"
    Options:
    - "Senior management for decisions or briefings" → og_candidates: ["EC", "FI"], jes_hints: ["Communication", "Decision making"]
    - "Operational teams and staff internally" → og_candidates: ["AS", "IT"], jes_hints: ["Leadership & operational mgmt"]
    - "External stakeholders or the public" → og_candidates: ["EC"], jes_hints: ["Communication", "Research & analysis"]

Q3: "How specialized is the knowledge this role requires?"
    Options:
    - "Deep expertise in a technical field (economics, science, social science)" → og_candidates: ["EC"], teer_affinity: [1, 2]
    - "Deep expertise in accounting, finance, or financial systems" → og_candidates: ["FI"], teer_affinity: [1, 2]
    - "Deep expertise in software, infrastructure, or data systems" → og_candidates: ["IT"], teer_affinity: [1, 2]
    - "General administrative and organizational skills" → og_candidates: ["AS"], teer_affinity: [2, 3]

Q4: "Does this person develop or interpret rules, policies, or legislation?"
    Options:
    - "Yes — policy development or regulatory analysis is central" → og_candidates: ["EC"], jes_hints: ["Research & analysis", "Contextual knowledge"]
    - "Yes — financial policy or accounting standards" → og_candidates: ["FI"], jes_hints: ["Knowledge of specialized fields"]
    - "No — they implement or administer established policy" → og_candidates: ["AS", "IT"]
```

These are starter questions. The planner should treat them as the minimum viable bank. Questions for EN (Engineering) are deferred — `OG_LEVELS` has no "EN" key [VERIFIED: constants.py] and the `Classification` model's `work_type` Literal does include "EN" [VERIFIED: classification.py] but EN is not a v2.0 focus group.

**Note on TEER signals:** NOC TEER levels (1=highest qualification, 5=lowest) provide a cross-signal. EC and FI work maps to TEER 1-2; AS clerical work maps to TEER 3-4; IT maps to TEER 1-2. These are affinity hints, not hard gates. [ASSUMED — based on training knowledge of NOC TEER framework; not verified against NOC dataset in this session]

### Anti-Patterns to Avoid

- **Naming OG groups in question text or option labels:** Violates QUES-02. The string "EC" must never appear in `question`, `helper`, or `options[].label`.
- **JSON file instead of Python constant:** REQUIREMENTS.md says "JSON or Python constant" but the codebase pattern (established in Phase 11) uses Python constants in `constants.py`. Stay consistent — a JSON file would require a loader and introduce a new read-at-import pattern not used elsewhere.
- **Embedding level derivation in the question bank:** Level (EC-04, EC-05, etc.) is derived from scope questions (scopeDirection, scopeAdvises, scopeImpact) in Phase 16, not from the work-type question bank. The question bank signals only identify the group (EC/AS/IT/FI), not the level.
- **Creating a separate module** (e.g., `question_bank.py`): Adds a new file when `constants.py` is the established pattern and the data is small. Append to existing file.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Accumulating signals across multiple answers | Custom weighted voting system | Simple `Counter` in Phase 16 | Signal accumulation is trivially a vote count; no ML needed; deterministic |
| Validating question bank schema at runtime | Custom validator class | Pytest tests at test time | Static constant — validate once at test time, not on every import |
| Internationalizing question text | i18n framework | English-only constant | Single-language app per scope; bilingual is explicitly out of scope |

---

## Common Pitfalls

### Pitfall 1: OG Code in User-Visible Text
**What goes wrong:** A question option label says "Policy/EC work" — this violates the Socratic constraint. A manager who sees "EC" is selecting OG directly.
**Why it happens:** Easy shorthand when writing question content.
**How to avoid:** Review every `label` string before committing. Run a grep check in the test: `assert "EC" not in option["label"]` etc.
**Warning signs:** Any option label containing a 2-letter OG code.

### Pitfall 2: OG Candidate Code Not in OG_LEVELS
**What goes wrong:** A signal emits `"og_candidates": ["CS"]` — CS was removed (merged into IT). The downstream classifier fails silently or raises a KeyError.
**Why it happens:** Copy-paste from v1.0 code which had CS in OG_LEVELS.
**How to avoid:** Test explicitly: `assert all(code in OG_LEVELS for code in option["signals"]["og_candidates"])`.
**Warning signs:** CS, EX, or any code not in the verified OG_LEVELS constant.

### Pitfall 3: JES Factor Name Typos
**What goes wrong:** `"jes_factor_hints": ["Research and analysis"]` — the canonical name is "Research & analysis" (ampersand, not "and"). The Phase 17 JES scorer won't match.
**Why it happens:** Natural language variation.
**How to avoid:** Define `KNOWN_JES_FACTORS` as a set derived from `EC_ELEMENTS` in `constants.py`, then validate each hint in `test_question_bank.py`.
**Warning signs:** Any "and" in a factor name hint (all canonical names use "&").

### Pitfall 4: Classification Model Level Field Bug
**What goes wrong:** A developer tries to validate question bank signals against the `Classification` pydantic model and hits `ge=4, le=6` — this rejects EC-01, EC-02, EC-03.
**Why it happens:** `classification.py` level validator was written for the prototype's simplified 3-level model (levels 4/5/6) and hasn't been corrected for the full OG_LEVELS data.
**How to avoid:** Phase 12 tests cross-reference against `OG_LEVELS`, not `Classification`. Flag the model bug as a Phase 16 fix-item in the plan.
**Warning signs:** Any test that imports `Classification` and tries to set `level=1`.

---

## Code Examples

### Minimal QUESTION_BANK structure (verified pattern)

```python
# Source: mirrors test_constants.py import/validation pattern [VERIFIED: codebase]
# Append to v2/backend/app/data/constants.py after CAF_RANK_OG_EQUIVALENCE

KNOWN_JES_FACTORS: frozenset[str] = frozenset({
    "Decision making",
    "Leadership & operational mgmt",
    "Communication",
    "Knowledge of specialized fields",
    "Contextual knowledge",
    "Research & analysis",
    "Physical effort",
    "Sensory effort",
    "Working conditions",
})

QUESTION_BANK: list[dict] = [
    {
        "id": "work_output_type",
        "phase_slot": "work_type",
        "question": "What best describes the main type of output this person produces?",
        "helper": "Think about what they actually deliver — not their title.",
        "input_type": "choices",
        "options": [
            {
                "id": "analysis_advice",
                "label": "Analysis, options, or recommendations for decision-makers",
                "signals": {
                    "og_candidates": ["EC"],
                    "jes_factor_hints": ["Research & analysis", "Decision making"],
                    "teer_affinity": [1, 2],
                },
            },
            {
                "id": "financial_reports",
                "label": "Financial plans, budgets, or costing reports",
                "signals": {
                    "og_candidates": ["FI"],
                    "jes_factor_hints": ["Knowledge of specialized fields"],
                    "teer_affinity": [1, 2],
                },
            },
            {
                "id": "systems_data",
                "label": "Systems, applications, or digital services",
                "signals": {
                    "og_candidates": ["IT"],
                    "jes_factor_hints": ["Knowledge of specialized fields"],
                    "teer_affinity": [1, 2],
                },
            },
            {
                "id": "admin_coordination",
                "label": "Administrative coordination, logistics, or operational support",
                "signals": {
                    "og_candidates": ["AS"],
                    "jes_factor_hints": ["Leadership & operational mgmt"],
                    "teer_affinity": [2, 3, 4],
                },
            },
        ],
    },
    # ... additional questions follow same schema
]
```

### test_question_bank.py structure (verified test pattern)

```python
# Source: mirrors test_constants.py pattern [VERIFIED: tests/test_constants.py]
from app.data.constants import QUESTION_BANK, OG_LEVELS, KNOWN_JES_FACTORS

REQUIRED_KEYS = {"id", "phase_slot", "question", "helper", "input_type", "options"}
REQUIRED_SIGNAL_KEYS = {"og_candidates", "jes_factor_hints", "teer_affinity"}

def test_question_bank_has_minimum_questions():
    assert len(QUESTION_BANK) >= 4

def test_every_entry_has_required_keys():
    for entry in QUESTION_BANK:
        assert REQUIRED_KEYS.issubset(entry.keys()), f"Entry '{entry.get('id')}' missing keys"

def test_every_option_has_required_signal_keys():
    for entry in QUESTION_BANK:
        for opt in entry["options"]:
            assert REQUIRED_SIGNAL_KEYS.issubset(opt["signals"].keys())

def test_og_candidates_all_exist_in_og_levels():
    for entry in QUESTION_BANK:
        for opt in entry["options"]:
            for code in opt["signals"]["og_candidates"]:
                assert code in OG_LEVELS, f"OG code '{code}' not in OG_LEVELS"

def test_jes_factor_hints_all_known():
    for entry in QUESTION_BANK:
        for opt in entry["options"]:
            for hint in opt["signals"]["jes_factor_hints"]:
                assert hint in KNOWN_JES_FACTORS, f"Unknown JES factor hint: '{hint}'"

def test_no_og_codes_in_user_visible_text():
    og_codes = set(OG_LEVELS.keys())
    for entry in QUESTION_BANK:
        for field in ("question", "helper"):
            for code in og_codes:
                assert code not in entry[field], \
                    f"OG code '{code}' found in user-visible field '{field}' of '{entry['id']}'"
        for opt in entry["options"]:
            for code in og_codes:
                assert code not in opt["label"], \
                    f"OG code '{code}' found in option label of '{entry['id']}'"

def test_covers_minimum_four_groups():
    all_candidates = set()
    for entry in QUESTION_BANK:
        for opt in entry["options"]:
            all_candidates.update(opt["signals"]["og_candidates"])
    for required_group in ("EC", "AS", "IT", "FI"):
        assert required_group in all_candidates, \
            f"Group '{required_group}' has no signal in QUESTION_BANK"
```

---

## State of the Art

| Old Approach (prototype) | Current Approach (v2.0) | When Changed | Impact |
|--------------------------|------------------------|--------------|--------|
| `WORK_TYPES` direct picker — manager selects "Policy/EC" or "IT" card | `QUESTION_BANK` Socratic questions — manager describes work, system derives group | Phase 12 (now) | Eliminates direct OG selection; maintains legal defensibility of classification |
| Hardcoded `levelFromScope` (sum ≤4→4, ≤7→5, >7→6) mapping to levels 4-6 | Signals feed into v1.0 OG ranker (Phase 16) for evidence-based group + OG_LEVELS for level range | Phase 16 | Full EC-01 to EC-08 range now accessible |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 4–6 questions is sufficient to distinguish EC/AS/IT/FI without naming OG groups | Architecture Patterns, Code Examples | If wrong: more questions needed; Phase 15 UX flow longer than planned |
| A2 | TEER 1-2 affinity for EC/FI/IT; TEER 2-4 for AS clerical | Architecture Patterns | If wrong: TEER signals give wrong cross-weight to NOC pipeline in Phase 16 |
| A3 | Python list-of-dicts in constants.py is preferable to a JSON file | Architecture Patterns | If wrong: need a loader; minor refactor |
| A4 | EN (Engineering) group excluded from Phase 12 question bank | Code Examples | If wrong: Phase 12 must add EN questions; REQUIREMENTS.md says "AS, EC, IT, FI at minimum" so EN extension is permitted |
| A5 | `KNOWN_JES_FACTORS` frozenset co-located in constants.py rather than imported from a Phase 17 constant | Architecture Patterns | If wrong: circular import issue at Phase 17 — can easily be moved then |

---

## Open Questions

1. **Should `KNOWN_JES_FACTORS` be defined in `constants.py` or deferred to Phase 17's JES module?**
   - What we know: The prototype `EC_ELEMENTS` defines the 9 factor names. Phase 17 will need them for JES scoring.
   - What's unclear: Whether defining them now in `constants.py` creates a coupling Phase 17 must respect vs. causing duplication.
   - Recommendation: Define in `constants.py` now (Phase 12 test needs them). Phase 17 imports from there. Clean dependency direction: data layer supplies names, service layer uses them.

2. **Does the `Classification` model's `level: ge=4, le=6` bug need to be fixed in Phase 12 or Phase 16?**
   - What we know: Phase 12 tests cross-reference against `OG_LEVELS` only, so Phase 12 tests will pass regardless.
   - What's unclear: Whether the planner should add a model fix task to Phase 12 (since the model is in the data layer) or defer to Phase 16.
   - Recommendation: Flag in Phase 12 plan as a Phase 16 prerequisite; don't include it in Phase 12 plans since no Phase 12 test exercises the model.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 12 is a pure data-constant + test phase. No external dependencies. Python ≥3.10 and pytest 8.3.4 are already installed and verified in Phase 11.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 |
| Config file | `v2/backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd v2/backend && python -m pytest tests/test_question_bank.py -v` |
| Full suite command | `cd v2/backend && python -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUES-01 | Every entry has required keys; OG codes valid; JES hints valid | unit | `pytest tests/test_question_bank.py -v` | ❌ Wave 0 |
| QUES-01 | Covers EC, AS, IT, FI at minimum | unit | `pytest tests/test_question_bank.py::test_covers_minimum_four_groups` | ❌ Wave 0 |
| QUES-02 | No OG code appears in user-visible question or label text | unit | `pytest tests/test_question_bank.py::test_no_og_codes_in_user_visible_text` | ❌ Wave 0 |
| QUES-03 | All entries have `phase_slot = "work_type"`; input_type is a known value | unit | `pytest tests/test_question_bank.py::test_phase_slot_and_input_type` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd v2/backend && python -m pytest tests/test_question_bank.py -v`
- **Per wave merge:** `cd v2/backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green (18 existing + new QUES tests) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_question_bank.py` — covers QUES-01, QUES-02, QUES-03 (all tests RED until `QUESTION_BANK` is written)

---

## Security Domain

This phase creates a hardcoded data constant with no user input, no authentication, no network calls, and no persistence. ASVS categories V2–V6 do not apply to a static Python constant. No security concerns for this phase.

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: `/home/charles/job_description_builder/v2/backend/app/data/constants.py`] — `OG_LEVELS` and `CAF_RANK_OG_EQUIVALENCE` shape; canonical OG codes (EC, IT, AS, FI, CR, PM, GT, EL, FB, FS, AI, AU); no CS key
- [VERIFIED: `/home/charles/job_description_builder/v2/backend/tests/test_constants.py`] — test structure pattern, cross-reference validation pattern
- [VERIFIED: `/home/charles/job_description_builder/v2/backend/app/models/classification.py`] — `Classification` model fields; `work_type` Literal; level field bug (`ge=4, le=6`)
- [VERIFIED: `/home/charles/job_description_builder/Job Description Builder/jd-builder/data.jsx`] — `WORK_TYPES` direct picker (being replaced); `EC_ELEMENTS` 9 factor names and canonical spellings; `STEPS` interview script structure; `levelFromScope` logic
- [VERIFIED: `/home/charles/job_description_builder/.planning/REQUIREMENTS.md`] — QUES-01, QUES-02, QUES-03 requirements text; phase dependency chain
- [VERIFIED: `/home/charles/job_description_builder/v2/backend/requirements.txt`] — pytest 8.3.4, pydantic 2.12.5; no new dependencies needed
- [VERIFIED: `/home/charles/job_description_builder/v2/backend/pyproject.toml`] — pytest config, asyncio_mode, testpaths

### Secondary (MEDIUM confidence)
- [VERIFIED: `/home/charles/job_description_builder/app/ai/og_ranking.py`] — v1.0 OG classification context; confirms EC/AS/IT/FI are the four primary groups; policy detection signals

### Tertiary (LOW confidence — training knowledge, not verified against TBS docs this session)
- NOC TEER level definitions (1=highest qualification requirement, 5=lowest) — [ASSUMED]
- TBS occupational group definitions and inclusions/exclusions for EC, AS, IT, FI — [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; verified from requirements.txt
- Architecture (file placement, entry schema): HIGH — verified from existing constants.py and test patterns
- Question content (which questions distinguish which groups): MEDIUM — grounded in prototype WORK_TYPES and EC_ELEMENTS (verified), but TBS OG definitions not read this session
- JES factor names: HIGH — verified from prototype EC_ELEMENTS (9 canonical names with exact spellings)
- OG codes: HIGH — verified from OG_LEVELS in constants.py

**Research date:** 2026-06-04
**Valid until:** 2026-09-04 (stable domain — TBS OG definitions change rarely)
