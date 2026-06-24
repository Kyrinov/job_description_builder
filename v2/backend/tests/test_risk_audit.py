"""
test_risk_audit.py — Phase 24: AUDIT-01 through AUDIT-05 requirement tests.

CBA + ERR compliance audit: run_audit service unit tests + endpoint integration tests.
"""
import json
import pytest

pytestmark = pytest.mark.asyncio


async def _create_wd(client) -> str:
    """Helper: create a minimal WorkDescription and return its id."""
    resp = await client.post(
        "/api/wd",
        json={"record": {"title": "Test Role"}, "answers": {}, "step_index": 1},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ── AUDIT-03: ERR rule unit tests (no HTTP, no fixtures) ────────────────────

def test_err_duty_coverage():
    """AUDIT-03 — ERR_DUTY_COVERAGE fires when WD has fewer than ERR_MIN_DUTY_COUNT duties."""
    from app.services.risk_auditor import run_audit

    class D:
        def __init__(self, text): self.text = text

    class WD:
        duties = [D("Plans things.")]  # 1 duty — below threshold of 3
        confirmed_og = "EC"

    findings = run_audit(WD(), cba_data=None)
    assert any(f["rule_id"] == "ERR_DUTY_COVERAGE" for f in findings), (
        "Expected ERR_DUTY_COVERAGE finding for WD with 1 duty"
    )


def test_err_duty_specificity():
    """AUDIT-03 — ERR_DUTY_SPECIFICITY fires when 50%+ of duties are under 8 words."""
    from app.services.risk_auditor import run_audit

    class D:
        def __init__(self, text): self.text = text

    class WD:
        duties = [
            D("Plans things."),      # 2 words — short
            D("Reviews stuff."),     # 2 words — short
            D("Does work."),         # 2 words — short
        ]
        confirmed_og = "EC"

    findings = run_audit(WD(), cba_data=None)
    assert any(f["rule_id"] == "ERR_DUTY_SPECIFICITY" for f in findings), (
        "Expected ERR_DUTY_SPECIFICITY finding when all duties are under 8 words"
    )


def test_zero_findings_clean_wd():
    """AUDIT-01 — A well-formed WD with 4+ long duties and no CBA conflicts produces zero findings."""
    from app.services.risk_auditor import run_audit

    class D:
        def __init__(self, text): self.text = text

    class WD:
        duties = [
            D("Develops and implements strategic policy frameworks for the department."),
            D("Leads cross-functional working groups to coordinate program delivery activities."),
            D("Analyzes program data and prepares briefing notes for senior management."),
            D("Provides expert advice to stakeholders on regulatory compliance requirements."),
        ]
        confirmed_og = "EC"

    # cba_data=None disables CBA checks; ERR checks should pass for this WD
    findings = run_audit(WD(), cba_data=None)
    assert findings == [], f"Expected zero findings for clean WD, got: {findings}"


def test_load_cba_unmapped_og():
    """AUDIT-02 — load_cba_data returns None for OG codes with no agreement directory (NT, ED)."""
    from app.services.risk_auditor import load_cba_data

    assert load_cba_data("NT") is None, "NT has no agreement dir — must return None"
    assert load_cba_data("ED") is None, "ED has no agreement dir — must return None"
    assert load_cba_data("UNKNOWN") is None, "Unknown OG code must return None"


def test_load_cba_never_raises_on_malformed_json(monkeypatch):
    """F-03: load_cba_data honors its 'Never raises' contract when the JSON is malformed.

    A corrupted CBA file must not propagate a JSONDecodeError — the loader
    returns None so the audit endpoint degrades gracefully instead of 500ing.
    """
    from app.services import risk_auditor

    monkeypatch.setattr(risk_auditor.json, "load", lambda f: (_ for _ in ()).throw(
        json.JSONDecodeError("malformed", "doc", 0)
    ))
    assert risk_auditor.load_cba_data("EC") is None


def test_two_signal_false_positive():
    """AUDIT-02 — A WD with only one matching signal (no verbatim term) produces no CBA finding."""
    from app.services.risk_auditor import run_audit, load_cba_data

    # Load a real CBA so CBA checks run (EC has a confirmed JSON)
    cba_data = load_cba_data("EC")
    if cba_data is None:
        pytest.skip("EC CBA data not loaded yet — implement load_cba_data first")

    class D:
        def __init__(self, text): self.text = text

    class WD:
        # Duties with no verbatim CBA terminology — signal 1 should fail
        duties = [
            D("Develops leadership competency frameworks for executive coaching programs."),
            D("Coordinates inter-departmental liaison activities for strategic initiatives."),
            D("Evaluates operational risk mitigation measures for financial stewardship."),
            D("Prepares comprehensive analytical reports for senior management review."),
        ]
        confirmed_og = "EC"

    findings = run_audit(WD(), cba_data=cba_data)
    cba_findings = [f for f in findings if f["rule_id"].startswith("CBA_")]
    assert cba_findings == [], (
        f"Two-signal rule should suppress CBA findings when no verbatim term matches: {cba_findings}"
    )


def test_finding_section_key_valid():
    """AUDIT-05 — AuditFinding only accepts valid section keys (matches amendment panel keys)."""
    from app.services.risk_auditor import AuditFinding
    import dataclasses

    valid_keys = {'id', 'ov', 'du', 'cls', 'q', 'drf'}
    # Construct a finding with a valid key — should succeed
    f = AuditFinding(
        rule_id="TEST_RULE",
        section="du",
        severity="advisory",
        citation="Test citation",
        recommendation="Test recommendation",
    )
    assert f.section in valid_keys
    d = f.to_dict()
    assert d["section"] == "du"
    assert d["rule_id"] == "TEST_RULE"


# ── AUDIT-01/04/05: Integration tests (require HTTP client) ─────────────────

async def test_audit_endpoint(client, env_with_db):
    """AUDIT-01 — POST /api/wd/{id}/audit returns 200 with findings list and wd_id."""
    wd_id = await _create_wd(client)
    resp = await client.post(f"/api/wd/{wd_id}/audit")
    assert resp.status_code == 200
    body = resp.json()
    assert "findings" in body, "Response must include 'findings' key"
    assert isinstance(body["findings"], list), "'findings' must be a list"
    assert body["wd_id"] == wd_id


async def test_audit_rerun_replaces(client, env_with_db):
    """AUDIT-01 — Re-running the audit replaces previous findings; count does not double."""
    wd_id = await _create_wd(client)
    resp1 = await client.post(f"/api/wd/{wd_id}/audit")
    assert resp1.status_code == 200
    count1 = len(resp1.json()["findings"])

    resp2 = await client.post(f"/api/wd/{wd_id}/audit")
    assert resp2.status_code == 200
    count2 = len(resp2.json()["findings"])

    assert count2 == count1, (
        f"Re-run produced {count2} findings, expected same count as first run ({count1}). "
        "Deduplication (DELETE before INSERT) may be missing."
    )


async def test_audit_404(client, env_with_db):
    """AUDIT-01 — POST /api/wd/nonexistent/audit returns 404."""
    resp = await client.post("/api/wd/nonexistent-wd-id/audit")
    assert resp.status_code == 404


async def test_audit_decide(client, env_with_db):
    """AUDIT-04 — POST /api/wd/{id}/audit/decide returns 201 and writes audit_log row."""
    import sqlite3

    wd_id = await _create_wd(client)

    # Run audit first so a finding exists to decide on
    await client.post(f"/api/wd/{wd_id}/audit")

    decide_resp = await client.post(
        f"/api/wd/{wd_id}/audit/decide",
        json={"rule_id": "ERR_DUTY_COVERAGE", "section": "du", "decision": "skip"},
    )
    assert decide_resp.status_code == 201, f"Expected 201, got {decide_resp.status_code}: {decide_resp.text}"

    # Verify audit_log row written
    db_path = env_with_db
    con = sqlite3.connect(db_path)
    row = con.execute(
        "SELECT detail FROM audit_log WHERE wd_id = ? AND event = 'risk_audit_decision' ORDER BY id DESC LIMIT 1",
        (wd_id,),
    ).fetchone()
    con.close()
    assert row is not None, "No risk_audit_decision row found in audit_log"
    detail = json.loads(row[0])
    assert detail["rule_id"] == "ERR_DUTY_COVERAGE"
    assert detail["decision"] == "skip"
    assert detail["section"] == "du"
