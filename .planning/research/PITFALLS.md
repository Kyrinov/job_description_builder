# Pitfalls Research — v3.0

**System:** React 18 SPA + FastAPI, ARM64 (Jetson AGX Orin), SQLite, docxtpl, WeasyPrint
**Researched:** 2026-06-10
**Scope:** Pitfalls specific to adding v3.0 features to the existing v2.0 production system.

This document is additive to `.planning/research/PITFALLS.md` (domain-level pitfalls from v1.0 research). It covers only the integration and implementation risks introduced by v3.0's five feature areas.

---

## Accessible JD Template — Template Variable Contract Drift

**Risk:** The new Accessible JD DOCX template (`data/AI Docs/Accessible Job Description Template (1).docx`) will have a different Jinja2 variable surface than the existing `wd_template.docx`. `_build_wd_context()` in `export_service.py` returns a precisely defined 15-key dict. Any variable referenced in the new template that is absent from that dict silently renders as an empty string in docxtpl — no exception is raised, no test fails, the exported document just has blank sections. This failure mode is invisible until a human opens the file.

The existing system already has two separate `NON_EC_STANDARD_NAMES` dicts — one in `export_service.py` (lines 50-55) and one in `constants.py` (lines 600-605) — carrying different content. This is the clearest existing proof that contract drift happens in this codebase when two artifacts claim to own the same data.

The build scripts (`build_wd_template.py`, `build_poster_template.py`) use `get_undeclared_template_variables()` to self-verify, but only if they are re-run after template changes. If a developer edits the `.docx` binary directly in Word without re-running the build script, the verification is bypassed entirely.

Additionally, the Accessible JD template likely restructures Section 5 (qualifications) and may add accessibility-required fields (plain-language summary, screen-reader-friendly table structure) that have no matching key in `_build_wd_context()`. Adding new keys to the context dict without removing old ones is safe; renaming or removing keys while the old template is still referenced elsewhere will silently break the old template.

**Prevention:**
- Before touching any template file, run `get_undeclared_template_variables()` on both the old and new template and diff the outputs. The diff is the work that must happen in `_build_wd_context()`.
- After building the new template, add a test that renders it with a known context dict and asserts that every declared variable is non-empty (not just that the render succeeded with non-zero bytes).
- Consolidate the two `NON_EC_STANDARD_NAMES` dicts as part of this phase. The `export_service.py` copy should import from `constants.py`; it should not define its own version.
- Gate the template swap with a flag (`USE_ACCESSIBLE_TEMPLATE=true` in env) so the old template can be tested side-by-side during the transition phase.

**Phase to address:** Accessible JD Template phase (whichever phase implements the template swap). The context dict audit must happen before the `.docx` binary is committed.

---

## Accessible JD Template — Section Reordering Breaks manifest / amendments Loop Logic

**Risk:** The TBS WD template sections are rendered in a fixed order: identification → context → duties → classification → qualifications → manifest → amendments. The Accessible JD template may reorder these sections (e.g., moving qualifications before classification, or merging the manifest into a footer). The `{%p for entry in manifest %}` and `{%p if amendments|length > 0 %}` loops in docxtpl are paragraph-level: they depend on the template's paragraph ordering, not the context dict. A section reorder that puts `{%p if amendments|length > 0 %}` before `amendments` is populated in the context will silently drop the appendix.

This is not theoretical: the Phase 20 code review already logged CR-02 (HTML injection in WeasyPrint) as a consequence of the render order assumption in the PDF path.

**Prevention:**
- After building the new template, add a test that seeds a WD with two amendment notes and one manifest entry, renders the template, and opens the resulting DOCX with `python-docx` to assert that the amendment section is present and the manifest table has at least one row.
- Do not rely on the "non-zero bytes and file > 5 kB" proxy test that current tests use. Those tests cannot detect a correctly-sized file with silently-empty sections.

**Phase to address:** Accessible JD Template phase, test-writing step.

---

## QUESTION_BANK Scaling — Signal Contamination Across 12 New Groups

**Risk:** The current `QUESTION_BANK` has 4 questions covering 4 groups (EC, AS, IT, FI). The 12 new v3.0 groups (ED, FB, FS, LC, LP, MT, NT, NU, PO, PS, SW, WP) are structurally heterogeneous: FB (Border Services) overlaps significantly with EC and PS in policy/enforcement vocabulary; LP and LC are law groups whose JES factors align more with EC than with IT/AS; NU and NT are clinical roles that share no signal vocabulary with any current group. Adding options for all 12 new groups to the existing 4 questions will produce options whose `og_candidates` signals overlap with existing groups, degrading `accumulateSignals()`'s ability to rank candidates.

The current signal accumulation is a simple tally: `og_candidates` arrays are concatenated and the most-mentioned code wins. Adding 12 new groups with multi-group `og_candidates` entries (e.g., `["LP", "EC"]` for policy-heavy law work) means that a set of answers intended to surface LP will also increment EC, pushing a plausible-but-wrong group into the top-3.

There is a second structural problem: the QUES-02 constraint forbids showing OG codes in user-visible text, which means question labels for 12 new groups must be worded without naming the group. With 12 groups, distinguishing "Social Work (SW)" from "Psychology (PS)" from "Nursing (NU)" using only abstract work-description language is genuinely hard. If the labels are too similar, users will select based on title similarity to their role, bypassing the Socratic intent.

**Prevention:**
- Do not add all 12 groups to the existing 4 questions. Instead, introduce a branching question tree: a root question ("Is this a specialized scientific/clinical/legal role?") gates whether the advisor enters the existing EC/AS/IT/FI path or a new specialized-group path.
- For the specialized path, keep question sets small and purpose-built per cluster: clinical (NU, NT, PS, SW), legal (LP, LC), enforcement/operations (FB, PO), and scientific/technical (MT, ED, FS, WP).
- After extending `QUESTION_BANK`, run the existing signal-accumulation test suite against all 4-answer combinations and verify that no new group bleeds into the top-3 for answers clearly intended to surface a different group.
- Add a `KNOWN_GROUPS` integration test: for each new group, specify the "ideal" answer set and assert that `accumulateSignals()` returns that group as the top candidate.

**Phase to address:** Broader OG Classification phase, before `QUESTION_BANK` entries are written for new groups.

---

## QUESTION_BANK Scaling — OG_LEVELS, OG_DEFINITIONS, QUAL_STANDARDS, NON_EC_TOTALS Must All Be Extended Together

**Risk:** Adding a new group requires coordinated changes across at least 6 constants and data structures:

| Artifact | Must add |
|----------|----------|
| `OG_LEVELS` | Level list (verified from rates CSV) |
| `OG_DEFINITIONS` | Group definition text (from TBS OCHRO or JES standard) |
| `QUAL_STANDARDS` | Default qualification text |
| `NON_EC_TOTALS` | Approximate total points per level (from JES standard) |
| `NON_EC_STANDARD_NAMES` (both copies, or consolidated) | Standard name string |
| Frontend `QUAL_DEFAULTS` in `data.jsx` | Matching qualification text |

Of the 12 new v3.0 groups, 10 (ED, LC, LP, MT, NT, NU, PO, PS, SW, WP) have no rates CSV in `data/rates_of_pay/`, meaning `OG_LEVELS` level counts must be derived from the JES standard files directly. Several of those files are scraped HTML with inconsistent formatting (see the `FS Foreigns Service - Job Evauation Standard.txt` typo in the filename — likely a scrape artifact). The FB group already has two JES-related files (`FB Border Services - Job Evaluation Standard 2005.txt` and `FB Border Services - Application Guidelines 2005.txt`), and it is not immediately obvious which file contains the point scales.

If any of these 6 artifacts is extended without the others, the export manifests a silent failure: `NON_EC_STANDARD_NAMES.get(og_code, "JES")` in `_build_v2_manifest()` falls back to the literal string `"JES"` for an unknown group, which is not a valid citation in an HR document. The frontend `getQualDefault()` returns the generic default text for an unrecognized OG code, which may not satisfy the applicable TBS Qualification Standard for that group.

**Prevention:**
- Create a checklist requirement: adding a new OG group is not complete until all 6 artifacts are updated. Gate this with a test: for every key in `OG_LEVELS`, assert that a corresponding entry exists in `OG_DEFINITIONS`, `QUAL_STANDARDS`, and `NON_EC_TOTALS` (or that the group is EC, the only group with per-factor scoring).
- Consolidate the duplicate `NON_EC_STANDARD_NAMES` before adding 12 new entries to it. Having two sources of truth for standard names with 4 entries will become unmanageable with 16.
- Add a cross-parity test between backend `QUAL_STANDARDS` and frontend `QUAL_DEFAULTS` (the Phase 19 code review flagged this AS/EC content drift as advisory; it must be a failing test for v3.0 since 12 new groups will all need matching pairs).
- Before writing new constants, verify `OG_LEVELS` for each new group by parsing the relevant JES standard file — do not guess levels from job titles.

**Phase to address:** Broader OG Classification phase, data-entry step. This is a pre-condition for any classification work on new groups.

---

## CBA Clause Matching — False Positive Audit Findings in an HR Legal Context

**Risk:** A false positive in the Risk Audit — flagging a valid duty statement as a CA violation — is not a minor inconvenience in an HR legal context. It is actively dangerous for two reasons.

First, advisor fatigue: if the audit flags obviously-valid duty text, advisors learn to dismiss all audit findings, including true positives. This is the canonical false-positive failure mode in compliance tooling: the signal-to-noise ratio degrades to the point where the tool's findings are treated as noise by default. A tool that advisors learn to ignore provides negative value compared to no tool at all.

Second, documentation risk: if an advisor accepts (clicks "Accept") on an audit finding that incorrectly says "this duty may conflict with Article 7.3 of the EC CA," the audit trail records that the advisor reviewed and accepted a CA concern. If the WD is later challenged and the audit log is produced in discovery, a row saying "Accepted: potential CA conflict" exists even when there was no actual conflict. The audit log becomes a liability rather than protection.

The CBA files in `data/agreements/` are large (`EC_full.txt` is 336 KB, `PA_full.txt` is 534 KB). String-matching duty text against entire CA articles without semantic grounding will produce false positives on shared vocabulary: "provides advice" appears in articles about overtime, leave, and grievance procedures as well as scope clauses.

**Prevention:**
- Scope the CBA clause matching to a curated subset of articles, not the full agreement. The relevant articles for a WD audit are: scope/application clauses (which positions are covered), classification-relevant exclusions (what work is excluded from the bargaining unit), and any articles that constrain the content of work descriptions. Do not attempt to match against all 80+ articles in a typical CA.
- Use a pre-extracted clause index (built once at startup from the JSON versions of the CBA files that already exist in `data/agreements/*/`), not real-time full-text search. The JSON files (`EC_full.json`, etc.) are already present and structured; use them.
- Require at least two signal types to fire an audit flag: (1) vocabulary match AND (2) the matched article is in the set of classification-relevant articles. Single-signal flags should be silently suppressed.
- Display the matched CA text verbatim alongside every audit finding so the advisor can immediately see whether the match is plausible. Do not just display the article number.
- Make the "Skip" option prominent and labeled "Not applicable — no conflict found." Do not label it "Dismiss" or "Ignore" (which imply the advisor is overriding a real concern).

**Phase to address:** Risk Audit phase, requirements and UX design step, before any matching logic is written.

---

## CBA Clause Matching — Parsing Large .txt CBA Files at Runtime

**Risk:** The 28 CBA directories each contain both a `.txt` file (336 KB to 534 KB) and a `.json` file. If the Risk Audit parses the `.txt` files at runtime per export/audit request, it will add 1-2 seconds of I/O + text processing to an already compute-bound export pipeline running on a Jetson. More critically, the `.txt` files are scraped HTML with inconsistencies: the FS file has a typo in its filename, the FB directory has two files with different scope, and the scraped text includes navigation headers and "Skip to main content" artifacts that will produce garbage matches.

**Prevention:**
- Use the `.json` files, not the `.txt` files, for the Risk Audit. They are already pre-structured.
- Pre-process the relevant CA clauses into a purpose-built in-memory index at application startup (or first audit request), not on every audit call. Cache keyed by `(og_code, ca_version_hash)`.
- The audit should only load clauses for the confirmed OG group's CA, not all 28. EC advisor audits only need the EC CA; PA advisor audits only need the PA CA (which covers AS, CR, and PM).

**Phase to address:** Risk Audit phase, data access layer design.

---

## Writing Guide Validation — The False-Positive Annoyance Threshold

**Risk:** The Job Description Writing Guide describes principles like "use active voice," "start duties with a verb," and "avoid vague language." A validation pass that mechanically checks these principles against every duty entry will flag legitimate professional language as a violation. Specific examples from real GC WDs that a naive validator would flag:

- "Responsible for the coordination of..." — technically passive construction but standard GC administrative language
- "Ensures compliance with..." — "Ensures" is a valid active verb but may be flagged as vague by a keyword-based check
- "Acts as departmental representative..." — "Acts as" is idiomatic and appropriate but may trigger a "weak verb" check
- Duty statements for senior positions legitimately start with "Leads," "Directs," "Oversees" — a validator trained on EC-04 norms will flag these as vague for an EC-07 role

The failure mode is the same as CBA false positives: advisors learn to dismiss all validation flags, including real ones. The writing guide validation must have a precision rate high enough to be trustworthy in daily use. For an internal HR tool used by classification specialists, "trustworthy" means fewer than 1 false flag per 5 duties on a well-written WD — which is a high precision bar.

There is also a role-level dependence problem: what constitutes a "vague" duty at EC-03 level is appropriate at EC-07. A validator that does not account for the confirmed OG and level will consistently over-flag senior positions.

**Prevention:**
- Do not implement a keyword blacklist for "vague verbs." Instead, validate structural properties only: does the duty start with a verb (any verb, not just "strong" ones), is it a single sentence (no semicolons concatenating multiple duties), is it within the word count range (8-25 words is a reasonable range for GC WD duties).
- Make every writing guide flag suppressible per-duty without affecting other duties. The advisor should be able to mark "This flag is not applicable to this duty" and have the system remember that for the session.
- Surface writing guide tips as suggestions with an inline example of the improvement, not as errors. Reserve the error/blocking style for genuinely invalid content (empty duty field, duplicate duty text).
- Test the validator against the existing SJD examples in `data/SJD Examples.txt` before shipping. If it flags more than 15% of SJD duty statements as violations, the validator is too aggressive.

**Phase to address:** Writing Guide integration phase. Establish the structural-only validation rule before any keyword-matching logic is written.

---

## SJD Library — Template Variable Mismatch When Pre-Populating

**Risk:** An SJD from `data/SJD Examples.txt` carries these fields: Job Title, JobCode, SJD Number, Group Level, NOC/CNP, Salary, Organizational Context. The v2.0 conversation record carries: title, branch, reports, summary, position_number, duties, quals, og_code, og_level. The mapping is not 1:1:

| SJD field | Maps to record field | Risk |
|-----------|---------------------|------|
| Job Title | record.title | Safe |
| Group Level (e.g. "AS-01") | og_code + og_level | Must be parsed and split |
| NOC / CNP | noc confirmation answer | Requires the NOC pipeline to re-run or be bypassed |
| Organizational Context | record.summary (approximately) | Text is usually a paragraph, not a one-liner |
| Salary | No field in v2.0 record | Must be dropped or stored as a display-only note |
| Supervisory (Yes/No) | No direct field | Relevant for QUESTION_BANK answers, not record directly |
| Competencies | No field in v2.0 | Must be dropped |
| Streams | No field in v2.0 | Must be dropped |

The highest-risk mapping is Group Level → og_code + og_level. The SJD format uses "AS-01" (OG code + hyphen + level with leading zero). The v2.0 system stores og_code and og_level separately (`wd.confirmed_og` as a dict with `og_code` key, `wd.og_level` as an integer). An SJD pre-population that writes "AS-01" directly to a field expecting a dict or integer will cause a Pydantic validation error at the next PATCH call — and since the error surfaces at PATCH time (not at pre-population time), the advisor may have already added several answers before the error is discovered.

**Prevention:**
- Write and test a dedicated `parse_sjd_record(sjd_text: str) -> dict` function before any SJD pre-population logic touches the WD data model. The function should return a dict with the same keys as `WDPatchRequest`, not a raw SJD field dict.
- Specifically: parse "AS-01" → `{"confirmed_og": {"og_code": "AS", "og_name": "Administrative Services"}, "og_level": 1}` using `_og_code_from()` style parsing, and validate the parsed og_code against `OG_LEVELS` before writing.
- Define explicitly which SJD fields are dropped (Salary, Supervisory, Streams, Competencies) and assert that the pre-population function never writes those fields to the WD record.
- For Organizational Context: the SJD text is a full paragraph. Pre-populate it into `record.summary`, not `record.branch` or `record.title`. Surface it in the SPA as a pre-filled text that the advisor can edit, not as a locked value.

**Phase to address:** SJD Library phase, data mapping design step.

---

## SJD Library — Stale SJD Data and Provenance Integrity

**Risk:** The SJDs in `data/SJD Examples.txt` are a point-in-time snapshot. If an advisor uses an SJD as their starting point, the export must clearly attribute that the WD was seeded from a specific SJD (by SJD Number and date). If the SJD's source level or duties are outdated (e.g., the salary range in the SJD predates the current collective agreement), the export's version manifest must show the SJD as a source with a version date — not silently absorb the SJD content as if it were original advisor input.

The current `_build_v2_manifest()` function walks `wd.duties[*].provenance_noc_code` and root-level fields. It has no path for SJD provenance. If SJD pre-population writes duties to `wd.duties` with `advisor=True` (because they did not come from the live NOC pipeline), the manifest will tag them as advisor-added — which is technically correct but obscures the fact that they came from an authoritative DND SJD.

**Prevention:**
- Add an `sjd_source` field to `WorkDescription` (or to `record`) that stores `{sjd_number, sjd_date, sjd_title}` when a WD is seeded from an SJD. The field is `None` for WDs started from scratch.
- Extend `_build_v2_manifest()` to emit an SJD source entry when `wd.sjd_source is not None`.
- For duties imported from an SJD, use a new provenance tag value (e.g., `source="sjd"`) rather than `advisor=True`. This allows the export to distinguish "advisor wrote this" from "this came from a DND SJD."

**Phase to address:** SJD Library phase, data model step. The `WorkDescription` schema change must happen before any SJD pre-population logic is written.

---

## Broader OG Classification — Disambiguation Alert Scaling

**Risk:** The current AS/EC disambiguation alert fires when both AS and EC appear in the top-3 OG candidates. It is a single hard-coded alert stored in `ASEC_DISAMBIGUATION` in `constants.py`. With 12 new groups, several new ambiguous pairs will exist:

- LP (Law Practitioner) vs. LC (Law Management) — both law groups, very similar work descriptions
- PS (Psychology) vs. SW (Social Work) vs. NT (Nutrition and Dietetics) — all human services clinical roles
- EC vs. ED (Education) — both policy/analysis oriented; research and teaching roles overlap
- FB (Border Services) vs. PO (Police Operations Support) — both enforcement/operations

If the disambiguation pattern is extended by adding a separate constant for each pair (as was done for ASEC), the constants file will have O(n²) disambiguation entries for n groups. With 12 new groups, that is potentially 66 pairs, most of which will never fire.

**Prevention:**
- Refactor the disambiguation pattern before adding new groups. Instead of a dict per pair, use a rule-based structure: `DISAMBIGUATION_RULES = [{groups: {"LP", "LC"}, text: "...", citation: "..."}, ...]`. The classifier checks whether any rule's group set is a subset of the top-3 candidates and fires the appropriate alert.
- Add disambiguation entries only for pairs that are empirically confused: run `accumulateSignals()` against a set of real position descriptions that are known edge cases and identify which pairs appear together in the top-3 most frequently.
- Keep the existing `ASEC_DISAMBIGUATION` constant for backward compatibility, but migrate it to the rule-based structure in the same phase.

**Phase to address:** Broader OG Classification phase, constants design step, before adding new group entries.

---

## ARM64 Pitfalls for New Dependencies

**Risk:** The Jetson AGX Orin (aarch64) already runs the full v2.0 stack cleanly. New v3.0 features may introduce dependencies that are unavailable or broken on ARM64.

**Specific risks by feature:**

**Risk Audit (CBA parsing):** The existing `.json` CBA files can be parsed with `json` (stdlib) and matched with `rapidfuzz` (which is already installed and has ARM64 wheels at version 3.14.5). No new dependency risk here if the implementation stays within these tools. Risk arises if an NLP-based approach is chosen: `spacy` is not currently installed and its ARM64 wheels are available but large (200+ MB). `sentence-transformers` is installed (version 5.2.2) and will work but adds latency on every audit call if used for semantic clause matching — this is acceptable only if the clause index is pre-computed at startup, not computed per-audit.

**Writing Guide validation:** A structural validator (verb-first check, word count check) requires only `re` (stdlib) and has no ARM64 risk. Risk arises only if a grammar/NLP library is chosen. `language-tool-python` requires a Java runtime which is not confirmed present on the Jetson. Do not use it.

**SJD Library (PDF parsing of `SJD-guide.pdf`):** `pdfplumber` and `pymupdf` (fitz) both have ARM64 wheels. `PyMuPDF` is the faster choice for text extraction from structured PDFs. Neither is currently in `requirements.txt`. However, `data/SJD Examples.txt` is already a plain-text file — use it directly rather than parsing the PDF for the initial implementation. Defer PDF parsing to a later iteration.

**docxtpl template swap:** No new dependency risk. `docxtpl 0.19.0` and `python-docx 1.1.2` are already installed and ARM64-compatible.

**Broader OG (12 new groups):** The JES scoring for new groups uses the existing `NON_EC_TOTALS` pattern (hardcoded approximate totals, no LLM). No new dependency risk.

**Prevention:**
- Before adding any new `pip` dependency for v3.0, verify ARM64 wheel availability: `pip download --platform manylinux2014_aarch64 --python-version 311 --only-binary :all: <package>` from the Jetson directly.
- For the Risk Audit, implement the first version using `rapidfuzz` (already installed) against the pre-structured JSON clause index. This avoids any new dependency entirely.
- Do not introduce `language-tool-python` or any Java-dependent grammar checker.
- For SJD PDF parsing (if needed): choose `pymupdf` over `pdfplumber`. Add it to `requirements.txt` only when actually needed, not speculatively.

**Phase to address:** Each feature phase, in the requirements/dependencies verification step before implementation begins.

---

## Phase-Specific Warnings Summary

| Feature | Pitfall | Mitigation | Phase |
|---------|---------|------------|-------|
| Accessible JD Template | Context dict missing new template variables — silent empty sections | Diff `get_undeclared_template_variables()` before and after; add content-presence test | Template phase |
| Accessible JD Template | Duplicate `NON_EC_STANDARD_NAMES` dicts diverge further | Consolidate to single source in `constants.py` before template work | Template phase (pre-condition) |
| Accessible JD Template | Section reorder silently drops amendments appendix | Assert amendment section present in rendered DOCX via `python-docx` inspection | Template phase, tests |
| Risk Audit | False positives train advisors to dismiss all audit findings | Curated clause subset only; two-signal requirement; verbatim CA text shown inline | Audit phase, requirements |
| Risk Audit | `.txt` CBA files contain scrape artifacts | Use `.json` CBA files; pre-build index at startup | Audit phase, data layer |
| Risk Audit | Audit trail becomes liability (accepted false positive recorded) | Label Skip as "Not applicable — no conflict" not "Dismiss" | Audit phase, UX |
| Writing Guide | Aggressive validation frustrates advisors | Structural checks only (verb-first, word count, no duplicates); no keyword blacklist | Writing Guide phase |
| Writing Guide | Validation insensitive to OG level | Suppress or downgrade flags for senior-level positions (EC-06, EC-07) | Writing Guide phase |
| QUESTION_BANK (12 groups) | Signal contamination across new groups | Branching tree, not flat option expansion; per-cluster question sets | OG Classification phase |
| QUESTION_BANK (12 groups) | Missing entries in 5 dependent constants | Checklist test: every OG_LEVELS key must have OG_DEFINITIONS + QUAL_STANDARDS + NON_EC_TOTALS entries | OG Classification phase |
| QUESTION_BANK (12 groups) | OG_LEVELS missing for 10 of 12 new groups | Derive from JES standard files; do not guess | OG Classification phase, data entry |
| QUESTION_BANK (12 groups) | Disambiguation O(n²) pair explosion | Refactor to rule-based structure before adding new pairs | OG Classification phase |
| SJD Library | "AS-01" pre-population crashes Pydantic validation | Dedicated `parse_sjd_record()` with OG split + validation before any WD writes | SJD phase, data model |
| SJD Library | SJD provenance absorbed as "advisor-added" | New `source="sjd"` tag; `sjd_source` field on WorkDescription; manifest extension | SJD phase, schema design |
| ARM64 | Grammar/NLP library without ARM64 wheels | Structural validator uses `re` only; clause matching uses `rapidfuzz`; no Java deps | All phases |
| ARM64 | `sentence-transformers` per-audit latency | Pre-build clause index at startup if embedding-based; not per-request | Audit phase if embeddings used |
