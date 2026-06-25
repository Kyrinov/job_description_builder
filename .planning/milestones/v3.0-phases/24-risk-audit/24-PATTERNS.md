# Phase 24: Risk Audit — Pattern Map

**Mapped:** 2026-06-15
**Files analyzed:** 6 (2 new, 4 modified)
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `v2/backend/app/services/risk_auditor.py` | service | request-response (deterministic transform) | `v2/backend/app/services/duty_validator.py` | exact |
| `v2/backend/tests/test_risk_audit.py` | test | — | `v2/backend/tests/test_writing_guide.py` | exact |
| `v2/backend/app/api/wd.py` (add 2 endpoints) | controller | request-response + CRUD | `v2/backend/app/api/wd.py` lines 304–328 (`validate-duties`) | exact |
| `v2/frontend/src/conversation.jsx` (extend ReviewState) | component | event-driven | `v2/frontend/src/conversation.jsx` lines 111–164 (ReviewState) | exact |
| `v2/frontend/src/app.jsx` (add state + handlers) | controller | event-driven | `v2/frontend/src/app.jsx` lines 94–96, 365–375, 578–626 | exact |
| `v2/backend/app/api/wd.py` (AuditDecideRequest model) | model | CRUD | `v2/backend/app/api/amendments.py` lines 28–32 (AmendmentRequest) | role-match |

---

## Pattern Assignments

### `v2/backend/app/services/risk_auditor.py` (service, deterministic transform)

**Analog:** `v2/backend/app/services/duty_validator.py`

**Module docstring pattern** (lines 1–17):
```python
"""
app/services/risk_auditor.py — CBA + ERR compliance audit rules.

Deterministic rule matching. No LLM. Called only from POST /api/wd/{id}/audit.

Rules:
  CBA_STATEMENT_OF_DUTIES  — verbatim term match + section relevance (two-signal)
  ERR_DUTY_COVERAGE        — at least ERR_MIN_DUTY_COUNT duties present (Cushnie)
  ERR_DUTY_SPECIFICITY     — not 50%+ of duties under 8 words (Dervin/Trépanier)
"""
from __future__ import annotations
```

**Imports pattern** — duty_validator.py line 19 (minimal stdlib only; no ORM imports):
```python
import re
```

For risk_auditor.py, use:
```python
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal
```

**Core function signature pattern** — duty_validator.py lines 31–42:
```python
def validate_duties(duties: list) -> list[dict]:
    """Return per-duty findings for WG-01 rules.

    Args:
        duties: list of objects with .id (str) and .text (str) attributes.

    Returns:
        list of dicts: [{"duty_id": str, "rules_failed": [...]}]
        Only duties with at least one failing rule are included.
    """
    findings: list[dict] = []
    ...
    return findings
```

Copy this pattern for `run_audit`:
```python
def run_audit(wd, cba_data: dict | None) -> list[dict]:
    """Run all CBA and ERR checks. Returns list of finding dicts.

    Args:
        wd: WorkDescription instance
        cba_data: Loaded CBA JSON, or None if no agreement mapping exists.

    Returns:
        List of AuditFinding.to_dict() — empty list if no findings.
    """
    findings = []
    if cba_data:
        findings.extend(_run_cba_checks(wd, cba_data))
    findings.extend(_run_err_checks(wd))
    return findings
```

**Per-rule predicate pattern** — duty_validator.py lines 48–80 (if-check, append dict, return None or finding):
```python
# Rule: WORD_COUNT
if wc < 8 or wc > 25:
    rules_failed.append({
        "rule": "WORD_COUNT",
        "detail": f"{wc} word{'s' if wc != 1 else ''} (expected 8–25)",
    })
```

For risk_auditor, each ERR rule is a standalone function returning `AuditFinding | None`:
```python
def check_duty_coverage(wd) -> AuditFinding | None:
    duties = wd.duties or []
    if len(duties) < ERR_MIN_DUTY_COUNT:
        return AuditFinding(
            rule_id="ERR_DUTY_COVERAGE",
            section="du",
            severity="warning",
            citation="FPSLREB: Cushnie — ...",
            recommendation=f"This WD has {len(duties)} duties. ...",
        )
    return None
```

---

### `v2/backend/tests/test_risk_audit.py` (test)

**Analog:** `v2/backend/tests/test_writing_guide.py`

**Module docstring + pytestmark pattern** (lines 1–10):
```python
"""
test_risk_audit.py — Phase 24: AUDIT-01 through AUDIT-05 requirement tests.

CBA + ERR compliance audit: run_audit service unit tests + endpoint integration tests.
"""
import json
import pytest

pytestmark = pytest.mark.asyncio
```

**Helper WD creator pattern** (lines 13–19) — use the same `_create_wd` helper:
```python
async def _create_wd(client) -> str:
    resp = await client.post(
        "/api/wd",
        json={"record": {"title": "Test Role"}, "answers": {}, "step_index": 1},
    )
    assert resp.status_code == 201
    return resp.json()["id"]
```

**Unit test stub pattern** (lines 26–43) — inline `class D` for lightweight objects:
```python
def test_err_duty_coverage():
    """AUDIT-03 — ERR_DUTY_COVERAGE fires when WD has fewer than 3 duties."""
    from app.services.risk_auditor import run_audit

    class D:
        def __init__(self, text): self.text = text

    class WD:
        def __init__(self, duties): self.duties = duties; self.confirmed_og = "EC"

    wd = WD([D("Plans things for the department.")])  # 1 duty — below threshold
    findings = run_audit(wd, cba_data=None)
    assert any(f["rule_id"] == "ERR_DUTY_COVERAGE" for f in findings)
```

**Integration test pattern** (lines 135–149) — `client` + `env_with_db` fixtures, POST and assert status + body shape:
```python
async def test_audit_endpoint(client, env_with_db):
    """AUDIT-01 — POST /api/wd/{id}/audit returns 200 with findings list."""
    wd_id = await _create_wd(client)
    resp = await client.post(f"/api/wd/{wd_id}/audit")
    assert resp.status_code == 200
    body = resp.json()
    assert "findings" in body
    assert isinstance(body["findings"], list)
    assert body["wd_id"] == wd_id
```

**Fixtures to request** — always use `client` + `env_with_db` for integration tests (same as test_writing_guide.py). No new fixtures needed; conftest.py already provides both.

---

### `v2/backend/app/api/wd.py` — add `POST /api/wd/{id}/audit` (controller, request-response)

**Analog:** `v2/backend/app/api/wd.py` lines 304–328 (`validate-duties` endpoint)

**Existing imports to reuse** (lines 1–20 of wd.py — already present, no new imports at module level):
```python
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Union
from uuid import uuid4
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from app.config import get_settings
from app.db import get_connection
from app.models.work_description import WorkDescription
```
Add `from typing import Literal` to the existing `typing` import line.

**validate-duties endpoint pattern** (lines 304–328) — exact template for `run_compliance_audit`:
```python
@router.post("/wd/{wd_id}/validate-duties")
async def validate_duties_endpoint(wd_id: str) -> dict:
    """WG-01/WG-02: Structural duty validation. Non-blocking advisory check.
    ...
    """
    from app.services.duty_validator import validate_duties as _validate_duties
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
    findings = _validate_duties(wd.duties)
    return {"wd_id": wd_id, "findings": findings}
```

Differences for audit endpoint:
1. Import `from app.services.risk_auditor import run_audit, load_cba_data` (deferred, inside function body — same style as `from app.services.duty_validator import validate_duties`)
2. Open connection in `try/finally` (same pattern), but keep connection open through INSERT (not just SELECT) — must call `con.commit()` before `con.close()`
3. Add DELETE-then-INSERT block before returning, guarded in the same `try` block
4. OG code extraction: copy the `og_code = wd.confirmed_og.get("og_code") if isinstance(...)` pattern from `orphan_check` (lines 283–287)

**orphan_check OG extraction** (lines 281–287) — copy for audit endpoint:
```python
og_code = (
    wd.confirmed_og.get("og_code")
    if isinstance(wd.confirmed_og, dict)
    else wd.confirmed_og or ""
)
```

**Decision endpoint Pydantic model** — copy AmendmentRequest from `v2/backend/app/api/amendments.py` lines 28–32:
```python
class AmendmentRequest(BaseModel):
    section: Literal['id', 'ov', 'du', 'cls', 'q', 'drf'] = Field(
        ..., description="Semantic section key"
    )
    comment: str = Field(min_length=1, max_length=2000)
```

For Phase 24:
```python
class AuditDecideRequest(BaseModel):
    rule_id: str = Field(min_length=1, max_length=100)
    section: Literal['id', 'ov', 'du', 'cls', 'q', 'drf']
    decision: Literal['accept', 'manual_edit', 'skip']
```

**audit_log INSERT pattern** — copy from amendments.py lines 47–57:
```python
con.execute(
    "INSERT INTO audit_log (wd_id, event, actor, detail, created_at) "
    "VALUES (?, ?, ?, ?, ?)",
    (
        wd_id,
        "manager_amendment",
        "advisor",
        json.dumps({"section": body.section, "comment": body.comment}),
        now.isoformat(),
    ),
)
con.commit()
```

---

### `v2/frontend/src/conversation.jsx` — extend ReviewState (component, event-driven)

**Analog:** `v2/frontend/src/conversation.jsx` lines 111–164 (ReviewState)

**Current function signature** (line 111):
```javascript
function ReviewState({ record, cls, onExport, onRestart, amendmentNotes = {} }) {
```

Extend to:
```javascript
function ReviewState({ record, cls, onExport, onRestart, amendmentNotes = {},
                       auditFindings = [], auditRunning = false,
                       onRunAudit, onAuditDecide }) {
```

**checklist extension pattern** (lines 120–127) — append audit summary row after amendmentCount check:
```javascript
// AMEND-01: amendment count checklist row (only when at least 1 note saved)
const amendmentCount = Object.values(amendmentNotes).filter(n => n).length;
if (amendmentCount > 0) {
  checks.push([
    `${amendmentCount} amendment note${amendmentCount === 1 ? '' : 's'} attached`,
    true,
  ]);
}
```

**Export button pattern** (lines 146–159) — copy button rendering structure for the "Run compliance audit" button:
```jsx
<button className="btn--export" onClick={() => onExport('Word document (.docx)')}>
  <Icon path='...' />
  Export DOCX
</button>
```

For audit button, follow the same className + onClick + Icon pattern:
```jsx
<button className="btn--export" onClick={onRunAudit} disabled={auditRunning}>
  {auditRunning ? 'Auditing…' : 'Run compliance audit'}
</button>
```

**Findings panel** — render below export-row, inside the `done-card` div. Each finding row renders 3 decision buttons. Pattern is a `.map()` over the findings array — same approach as `checks.map(...)` at lines 139–145.

---

### `v2/frontend/src/app.jsx` — add audit state + handlers (controller, event-driven)

**Analog:** `v2/frontend/src/app.jsx`

**State declaration pattern** (lines 94–96) — insert alongside dutyHints and amendmentNotes state:
```javascript
// Phase 23 (WG-02): structural duty validation findings, populated after duties commit
const [dutyHints, setDutyHints] = useState([]);
const [amendmentNotes, setAmendmentNotes] = useState({});
const [amendmentPanels, setAmendmentPanels] = useState({});
```

Add after line 96:
```javascript
// Phase 24 (AUDIT-01): compliance audit findings, populated only by button click
const [auditFindings, setAuditFindings] = useState([]);
const [auditRunning, setAuditRunning] = useState(false);
```

**fetch-then-setState handler pattern** (lines 365–375) — `validate-duties` chained fetch:
```javascript
wdPromise
  .then(id => fetch(`/api/wd/${id}/validate-duties`, { method: 'POST' }))
  .then(r => r.ok ? r.json() : Promise.reject(r.status))
  .then(data => setDutyHints(data.findings || []))
  .catch(() => {}); // non-blocking; silent on failure
```

Copy structure for `handleRunAudit` (standalone function, NOT inside wdPromise chain — audit is button-click only, not chained off a commit):
```javascript
function handleRunAudit() {
  if (!wd_id) return;
  setAuditRunning(true);
  fetch(`/api/wd/${wd_id}/audit`, { method: 'POST' })
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(data => {
      setAuditFindings(data.findings || []);
      setAuditRunning(false);
    })
    .catch(() => { setAuditRunning(false); });
}
```

**Amendment panel linkage pattern** (lines 578–591) — `handleAmendToggle` called with sectionKey:
```javascript
function handleAmendToggle(sectionKey, textOrNull) {
  setAmendmentPanels(prev => {
    ...
    return { ...prev, [sectionKey]: { ...cur, open: !cur.open, text: cur.saved || '' } };
  });
}
```

`handleAuditDecide` calls this directly when `decision === 'manual_edit'`:
```javascript
function handleAuditDecide(ruleId, section, decision) {
  if (!wd_id) return;
  fetch(`/api/wd/${wd_id}/audit/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rule_id: ruleId, section, decision }),
  }).catch(() => {});
  if (decision === 'manual_edit') {
    handleAmendToggle(section);  // opens existing Phase 19 amendment panel
  }
}
```

**ReviewState prop passing pattern** (line 783):
```jsx
? <ReviewState record={record} cls={cls} onExport={exportAs} onRestart={restart} amendmentNotes={amendmentNotes} />
```

Extend to pass new props:
```jsx
? <ReviewState record={record} cls={cls} onExport={exportAs} onRestart={restart}
               amendmentNotes={amendmentNotes}
               auditFindings={auditFindings} auditRunning={auditRunning}
               onRunAudit={handleRunAudit} onAuditDecide={handleAuditDecide} />
```

**CRITICAL: Do NOT use a useEffect for audit.** The orphan check (lines 139–160) fires automatically in a `useEffect`. Audit must NOT follow this pattern — it is button-click only (AUDIT-01 pitfall 3 in RESEARCH.md).

---

## Shared Patterns

### audit_log INSERT
**Source:** `v2/backend/app/api/amendments.py` lines 47–57
**Apply to:** Both `POST /api/wd/{id}/audit` (bulk INSERT of findings) and `POST /api/wd/{id}/audit/decide` (INSERT decision row)
```python
con.execute(
    "INSERT INTO audit_log (wd_id, event, actor, detail, created_at) "
    "VALUES (?, ?, ?, ?, ?)",
    (wd_id, "risk_audit_finding", "system",
     json.dumps(finding), now.isoformat()),
)
con.commit()
```
Note: use `actor="system"` for findings (machine-generated), `actor="advisor"` for decisions (human action) — matches `amendments.py` pattern of `actor="advisor"`.

### Section key Literal validation
**Source:** `v2/backend/app/api/amendments.py` lines 29–31
**Apply to:** `AuditDecideRequest` model in `wd.py` + `AuditFinding` dataclass section field in `risk_auditor.py`
```python
section: Literal['id', 'ov', 'du', 'cls', 'q', 'drf']
```

### WD fetch + 404 guard
**Source:** `v2/backend/app/api/wd.py` lines 317–326
**Apply to:** Both new audit endpoints in `wd.py`
```python
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
```
**Important:** The audit endpoint keeps `con` open through INSERT + commit before `con.close()`. The `try/finally` block must wrap all DB operations, not just the SELECT.

### Deferred service import (inside function body)
**Source:** `v2/backend/app/api/wd.py` line 315
**Apply to:** Both new audit endpoints
```python
# Deferred import — matches existing convention in validate-duties and orphan_check
from app.services.risk_auditor import run_audit, load_cba_data
```

### fetch + silent error handler (frontend)
**Source:** `v2/frontend/src/app.jsx` lines 371–375
**Apply to:** `handleRunAudit` and `handleAuditDecide` in `app.jsx`
```javascript
.catch(() => {}); // non-blocking; silent on failure
```
For `handleRunAudit`, error should also reset `auditRunning` to `false`:
```javascript
.catch(() => { setAuditRunning(false); });
```

---

## No Analog Found

None. All Phase 24 files have direct analogs in the existing codebase.

---

## Metadata

**Analog search scope:** `v2/backend/app/services/`, `v2/backend/app/api/`, `v2/backend/tests/`, `v2/frontend/src/`
**Files read:** 7 (duty_validator.py, test_writing_guide.py, wd.py, amendments.py, conftest.py, app.jsx, conversation.jsx)
**Pattern extraction date:** 2026-06-15
