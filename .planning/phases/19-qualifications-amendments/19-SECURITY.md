---
phase: 19
slug: qualifications-amendments
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-09
---

# Phase 19 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
>
> Phase 19 delivers **QUAL-01/02/03** (OG-keyed qualification defaults, inline
> `.qual-error` validation, `.qual-sub-k` CSS) and **AMEND-01/02** (manager
> amendment notes via `POST/GET /api/wd/{wd_id}/amendments` writing to
> `audit_log`). Threat model spans 4 plans; verification is consolidation of
> the per-plan threat_models and 6 threat IDs.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Test code → application code (19-01) | Tests import from app modules directly; no external input | Test fixtures and seeded DB rows |
| Browser → React state (19-02) | `QualEditor` textarea input; no server crossing in this plan | Form text (education, experience) |
| Browser → `POST /api/wd/{wd_id}/amendments` (19-03) | Free-text `comment` + enum `section` key cross the API boundary | Manager-authored note text; section key |
| `audit_log.wd_id` SQL parameter (19-03) | `wd_id` from URL path parameter is interpolated into a parameterised SQL query | Work-description identifier (UUID string) |
| UAT interaction (19-04) | Human-only verification; no code changes in this plan | N/A |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-19-W0-01 | Tampering | test stubs (Wave 0) | accept | Test files only (`v2/backend/tests/test_quals.py`, `v2/backend/tests/test_amendments.py`, `v2/frontend/src/document.test.jsx`); no production surface introduced in Wave 0 — stubs are now promoted to real tests | closed |
| T-19-02-01 | Tampering | QualEditor empty submit (19-02) | mitigate | `answerValid()` at `v2/frontend/src/components.jsx:495` gates quals on `value && value.education && value.experience`; `touched` `useState` at `components.jsx:426` plus `onBlur` setters at `components.jsx:438, 455` add visible feedback via `.qual-error` (`components.jsx:441, 458`) but do NOT weaken the submit gate enforced by `app.jsx:177` | closed |
| T-19-01 | Tampering | `AmendmentRequest.section` (19-03) | mitigate | Pydantic `Literal['id', 'ov', 'du', 'cls', 'q', 'drf']` validator at `v2/backend/app/api/amendments.py:29` rejects unknown section keys with HTTP 422 before the handler runs | closed |
| T-19-02 | Tampering | `AmendmentRequest.comment` (19-03) | mitigate | Pydantic `Field(min_length=1, max_length=2000)` at `v2/backend/app/api/amendments.py:32` — same 2000-char cap as `work_description`; oversized payloads return HTTP 422 | closed |
| T-19-03 | Tampering | `wd_id` path parameter — `audit_log` INSERT (19-03) | mitigate | `SELECT id FROM work_descriptions WHERE id = ?` 404 guard at `v2/backend/app/api/amendments.py:43` (parameterised query) raises `HTTPException(404)` before the `INSERT INTO audit_log` at `amendments.py:47-57` runs — same pattern as `jes_override` | closed |
| T-19-04-01 | Information Disclosure | `audit_log` amendment data (19-04) | accept | Single-user local app; no multi-user access control needed (no auth, no network exposure beyond localhost) — see Accepted Risks Log | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|------------|------|
| R-19-W0-01 | T-19-W0-01 | Wave 0 introduced only test files (`v2/backend/tests/test_quals.py` — 3 tests verifying `QUAL_STANDARDS` constant; `v2/backend/tests/test_amendments.py` — 6 integration tests now GREEN against the live endpoint; `v2/frontend/src/document.test.jsx` QUAL-03 describe block). No production code, no new routes, no new data flow. All test code is excluded from production builds. | Phase 19 planner (PLAN 19-01 threat model) | 2026-06-09 |
| R-19-04-01 | T-19-04-01 | Phase 19 is a single-user local app: no authentication, no session management, no multi-user data segregation, and the FastAPI service is bound to localhost (`uvicorn` dev server, no public exposure). Amendment notes written to `audit_log` are scoped to the local user's SQLite database. As ASVS Level 1 applies (single-tenant, trusted-local-environment) and the app's threat model is built around input validation and tamper-resistance rather than confidentiality, the absence of access control is an accepted design choice rather than a defect. | Phase 19 planner (PLAN 19-04 threat model) | 2026-06-09 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-09 | 6 | 6 | 0 | gsd-security-auditor (per `/gsd-secure-phase` Phase 19) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log (2 entries: R-19-W0-01, R-19-04-01)
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-09

---

## Verification Evidence

### Mitigations verified in source

| Threat | Evidence (file:line) |
|--------|----------------------|
| T-19-02-01 | `v2/frontend/src/components.jsx:495` — `if (t === 'quals') return !!(value && value.education && value.experience);` (submit gate unchanged); `components.jsx:426` `useState({ education: false, experience: false })`; `components.jsx:438, 455` `onBlur` setters; `components.jsx:441, 458` `<p className="qual-error" role="alert">` rendered only when `touched[field] && !v[field]`. Caller `v2/frontend/src/app.jsx:177` enforces `if (!answerValid(step, draft)) return;` before persisting. |
| T-19-01 | `v2/backend/app/api/amendments.py:29` — `section: Literal['id', 'ov', 'du', 'cls', 'q', 'drf'] = Field(...)`. Pydantic returns 422 on any other value. |
| T-19-02 | `v2/backend/app/api/amendments.py:32` — `comment: str = Field(min_length=1, max_length=2000)`. Pydantic returns 422 on `len > 2000`. |
| T-19-03 | `v2/backend/app/api/amendments.py:42-46` — `row = con.execute("SELECT id FROM work_descriptions WHERE id = ?", (wd_id,)).fetchone(); if row is None: raise HTTPException(status_code=404, detail="Work description not found")`. The subsequent `con.execute("INSERT INTO audit_log (wd_id, event, actor, detail, created_at) VALUES (?, ?, ?, ?, ?)", (wd_id, "manager_amendment", "advisor", json.dumps({"section": body.section, "comment": body.comment}), now.isoformat(),))` at lines 47-57 uses a parameterised query — no string interpolation of `wd_id`, no SQL injection vector. |

### Test baseline at audit time (per 19-04 SUMMARY)

- Backend: **73 passed, 0 failed, 0 skipped** (67 pre-Phase-19 baseline + 3 QUAL tests + 6 AMEND tests, all GREEN)
- Frontend: **31 passed, 0 failed** (QUAL-03 stub promoted from `it.todo` to real assertion at `v2/frontend/src/document.test.jsx:144-161`)
- Vite production build: exits 0, 201.76 kB / 62.91 kB gzip

### Unregistered threat flags

*None.* No `## Threat Flags` section was present in any of `19-01-SUMMARY.md`, `19-02-SUMMARY.md`, `19-03-SUMMARY.md`, or `19-04-SUMMARY.md`. The executors did not surface any new attack surface outside the declared threat register.
