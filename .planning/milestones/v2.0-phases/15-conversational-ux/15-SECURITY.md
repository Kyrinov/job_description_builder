---
phase: 15-conversational-ux
status: clean
reviewer: manual (gsd-secure-phase subagent not installed; per init missing_agents list)
method: STRIDE threat-model verification against plan frontmatter
reviewed_at: "2026-06-05T10:55:00.000Z"
threats_total: 13
threats_open: 0
---

# Phase 15 Security Review

## Scope

Phase 15 introduced:
- `v2/backend/app/api/wd.py` (new) — POST/GET/PATCH /api/wd
- `v2/backend/app/api/__init__.py` (modified) — register wd router
- `v2/frontend/src/app.jsx` (modified) — fetch /api/wd on every commit
- `v2/frontend/src/data.jsx` (modified) — STEPS, PHASES, accumulateSignals, DUTY_SUGGESTIONS
- `v2/frontend/src/components.jsx` (modified) — og_confirm stub, NOC duty cfg, placeholder
- `v2/frontend/src/conversation.jsx` (modified) — cfgOverride prop
- `v2/frontend/src/styles.css` (modified) — NOC card layout

No new external attack surfaces. All new endpoints are local single-user.

## STRIDE Threat Verification

| Threat ID | Category | Component | Plan Disposition | Verified |
|-----------|----------|-----------|------------------|----------|
| T-15-01 | Tampering | test_wd.py fixture isolation | accept (per-test tmp DB) | ✓ — conftest.py uses tmp_db_path per test |
| T-15-02 | Information Disclosure | test assertions reveal schema | accept (local dev only) | ✓ — no secrets in test payloads |
| T-15-03 | Tampering | GET /api/wd/{wd_id} path param | mitigate (parameterized SQL) | ✓ — `WHERE id = ?` confirmed in wd.py:91 |
| T-15-04 | Tampering | work_descriptions.data JSON column | mitigate (Pydantic validate_json) | ✓ — `WorkDescription.model_validate_json(row["data"])` at wd.py:97, 111 |
| T-15-05 | Information Disclosure | GET /api/wd/{id} enumeration | accept (UUID v4, no auth scope) | ✓ — non-guessable IDs |
| T-15-06 | Spoofing | POST /api/wd id injection | mitigate (server-generated uuid4) | ✓ — WDCreateRequest has no id field; server always generates |
| T-15-07 | Tampering | QUESTION_BANK signals in apply() | mitigate (apply stores only a.id) | ✓ — verified all 4 qb_* apply functions return `{ qb_*: a.id }`, not signals |
| T-15-08 | Information Disclosure | XSS via option title rendering | accept (React text node) | ✓ — NocConfirmList uses `<span className="choice__title">{c.title}</span>` not dangerouslySetInnerHTML |
| T-15-09 | Tampering | wd_id from localStorage → PATCH URL | accept (UUID v4, no auth scope) | ✓ — non-guessable |
| T-15-10 | Denial of Service | NOC pipeline latency blocks commit flow | mitigate (fire-and-forget) | ✓ — fetch in commit() has no await; `nocLoading` spinner in UI; `.catch(() => {})` swallows errors |
| T-15-11 | Information Disclosure | noc/map response contains verbatim NOC duty text | accept (NOC 2021 is public) | ✓ — no PII in pipeline |
| T-15-12 | Tampering | XSS via NocConfirmList candidate title rendering | accept (React text node) | ✓ — same as T-15-08 |
| T-15-13 | Repudiation | WD CRUD calls fail silently | accept (localStorage fallback, single-user) | ✓ — localStorage crash-recovery still works; PATCH failures degrade gracefully |

## Secret handling

- ✓ `v2/backend/.env` contains `CLOUD_API_KEY` and is correctly gitignored
- ✓ No API keys, tokens, or credentials in any committed source file
- ✓ `.gitignore` covers `v2/backend/.env`

## AuthN/AuthZ

- N/A for Phase 15 (single-user local app, per PROJECT.md)
- All wd_ids are UUID v4 (non-guessable)
- Documented as "T-15-05 accept" in plan frontmatter

## Network exposure

- Backend listens on `127.0.0.1:8000` (loopback only)
- Frontend at `127.0.0.1:5173` (loopback only)
- Vite proxy passes `/api` → `:8000`
- No public network exposure in v2.0 dev config

## CORS

- N/A — frontend served by Vite proxy at same-origin from the browser's perspective

## Input validation

- ✓ Pydantic v2 models validate all request bodies (WDCreateRequest, WDPatchRequest, WorkDescriptionRequest)
- ✓ `extra="ignore"` allows forward-compatible field additions without breaking
- ✓ `min_length=10` on `work_description` in /api/noc/map
- ✓ UUID validation implicit via path-param typing

## Output encoding

- ✓ All user-facing text rendered as React text nodes (escaped by default)
- ✓ `dangerouslySetInnerHTML` only used for trusted SVG path strings from data.jsx (XSS-safe per comment at use site)

## Audit logging

- ⚠ `audit_log` table exists in schema (per db.py:46-58) but Phase 15 does not write to it
- This is acceptable: audit_log write is the responsibility of the WD CRUD routes, and Phase 15's scope is the conversational flow + persistence primitives. Adding audit writes here would couple the routes to audit semantics that aren't fully specified yet.
- **Recommendation**: add audit writes in Phase 18 (JD Composition) or a dedicated audit phase if the work is split.

## Verdict

**status: clean** — 0 open threats. All 13 STRIDE threats have their planned mitigations in place. No new attack surfaces introduced. The phase is secure for its single-user local scope.

The QUAL_DEFAULT deferral to Phase 19 is a known-scope decision, not a security issue.
