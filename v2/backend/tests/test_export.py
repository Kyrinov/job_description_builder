"""
test_export.py — Phase 20: Export endpoint tests.

Integration tests for:
  POST /api/wd/{id}/export/docx  (API-08, EXP-01)
  POST /api/wd/{id}/export/poster (API-09, EXP-02)
  POST /api/wd/{id}/export/pdf    (EXP-03)

All tests are skipped until Plan 02 implements export.py and wires it
into api/__init__.py. Remove @pytest.mark.skip when the router is live.
"""
from __future__ import annotations

import io

import docx
import pytest

pytestmark = pytest.mark.asyncio


async def _create_wd(client) -> str:
    resp = await client.post(
        "/api/wd",
        json={"record": {"title": "Test Role"}, "answers": {}, "step_index": 1},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_wd_with_jes_scores(client) -> str:
    """Create a WD seeded with confirmed_og + jes_total_points required for export."""
    wd_id = await _create_wd(client)
    resp = await client.patch(
        f"/api/wd/{wd_id}",
        json={
            "confirmed_og": {"og_code": "EC", "og_name": "Economics and Social Science Services"},
            "og_level": 4,
            "jes_total_points": 621,
            "jes_scores": [
                {"factor_name": "Decision Making", "degree": 3, "points": 150},
                {"factor_name": "Communication", "degree": 2, "points": 84},
            ],
            "duties": [
                {
                    "id": "d1",
                    "text": "Provides advice on economic policy.",
                    "source": "noc",
                    "provenance_noc_code": "4163",
                    "provenance_hash": "abc123",
                    "advisor": False,
                }
            ],
        },
    )
    assert resp.status_code == 200
    return wd_id


# ---------------------------------------------------------------------------
# Phase 25 — Accessible Template fixture helpers (ACC-02 RED baseline)
# 4 JES-shape variants needed to exercise the new Effort/Working-Conditions
# bucketing logic: EC (LLM-style, no category key on persisted dict),
# point-rating-with-Effort (FB), point-rating-without-Effort (MT),
# level-description (AS, jes_scores: []).
# ---------------------------------------------------------------------------

_DUTY_SEED = {
    "id": "d1",
    "text": "Provides advice on policy matters.",
    "source": "noc",
    "provenance_noc_code": "4163",
    "provenance_hash": "abc123",
    "advisor": False,
}

_RECORD_SEED = {
    "title": "Test Role",
    "client_service_results": "Citizens receive timely, accurate policy guidance.",
    "quals": {
        "education": "Degree in economics.",
        "experience": "5 years policy analysis.",
    },
}

_QUAL_SEED = {
    "education": "Degree in economics.",
    "experience": "5 years policy analysis.",
    "source": "EC-05 default",
    "last_modified": "2026-06-16T00:00:00Z",
}


async def _create_wd_ec(client) -> str:
    """EC: jes_scores carry Effort + Conditions factors but NO `category` key.

    The EC LLM-scoring path (_build_factor_score in jes_service.py) omits the
    category field from the persisted dict, so export_service must look up
    category via a factor_name -> category map (ACC-02 pitfall 2).
    """
    wd_id = await _create_wd(client)
    resp = await client.patch(
        f"/api/wd/{wd_id}",
        json={
            "confirmed_og": {"og_code": "EC", "og_name": "Economics and Social Science Services"},
            "og_level": 4,
            "jes_total_points": 43,
            "jes_scores": [
                {"factor_name": "Physical effort", "degree": 2, "points": 4},
                {"factor_name": "Sensory effort", "degree": 1, "points": 2},
                {"factor_name": "Working conditions", "degree": 3, "points": 12},
                {"factor_name": "Communication", "degree": 2, "points": 25},
            ],
            "duties": [_DUTY_SEED],
            "record": _RECORD_SEED,
            "qualification": _QUAL_SEED,
        },
    )
    assert resp.status_code == 200
    return wd_id


async def _create_wd_point_rating_with_effort(client) -> str:
    """FB (point-rating): jes_scores carry Effort + Conditions factors WITH category key.

    Exercises the point-rating path where category IS on the persisted dict
    (per JES_FACTORS_BY_GROUP['FB'] in constants.py).
    """
    wd_id = await _create_wd(client)
    resp = await client.patch(
        f"/api/wd/{wd_id}",
        json={
            "confirmed_og": {"og_code": "FB", "og_name": "Border Services"},
            "og_level": 4,
            "jes_total_points": 71,
            "jes_scores": [
                {"factor_name": "Physical effort", "degree": 2, "points": 5},
                {"factor_name": "Sensory effort", "degree": 2, "points": 4},
                {"factor_name": "Risk to health", "degree": 2, "points": 10},
                {"factor_name": "Work environment", "degree": 1, "points": 2},
                {"factor_name": "Knowledge", "degree": 3, "points": 50},
            ],
            "duties": [_DUTY_SEED],
            "record": _RECORD_SEED,
            "qualification": _QUAL_SEED,
        },
    )
    assert resp.status_code == 200
    return wd_id


async def _create_wd_point_rating_no_effort(client) -> str:
    """MT (point-rating): jes_scores carry ONLY Skill/Responsibility factors.

    No Effort or Working Conditions category at all — must fall back to
    '[To be completed by advisor]' placeholder (ACC-02).
    """
    wd_id = await _create_wd(client)
    resp = await client.patch(
        f"/api/wd/{wd_id}",
        json={
            "confirmed_og": {"og_code": "MT", "og_name": "Meteorology"},
            "og_level": 4,
            "jes_total_points": 110,
            "jes_scores": [
                {"factor_name": "Knowledge", "degree": 3, "points": 50},
                {"factor_name": "Decision making", "degree": 3, "points": 60},
            ],
            "duties": [_DUTY_SEED],
            "record": _RECORD_SEED,
            "qualification": _QUAL_SEED,
        },
    )
    assert resp.status_code == 200
    return wd_id


async def _create_wd_level_description(client) -> str:
    """AS (level-description): jes_total_points set, jes_scores is [].

    No factor data at all for level-description groups — must fall back to
    '[To be completed by advisor]' placeholder (ACC-02).
    """
    wd_id = await _create_wd(client)
    resp = await client.patch(
        f"/api/wd/{wd_id}",
        json={
            "confirmed_og": {"og_code": "AS", "og_name": "Administrative Services"},
            "og_level": 4,
            "jes_total_points": 500,
            "jes_scores": [],
            "duties": [_DUTY_SEED],
            "record": _RECORD_SEED,
            "qualification": _QUAL_SEED,
        },
    )
    assert resp.status_code == 200
    return wd_id


async def test_export_wd_docx_returns_bytes(client, env_with_db):
    """EXP-01 / API-08 — POST /api/wd/{id}/export/docx returns .docx bytes with correct MIME type."""
    wd_id = await _create_wd_with_jes_scores(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(resp.content) > 0


async def test_export_wd_docx_manifest(client, env_with_db):
    """EXP-01 — Exported DOCX bytes are non-zero (version manifest rendered in template)."""
    wd_id = await _create_wd_with_jes_scores(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    # Proxy for "manifest section rendered": file is > 5 kB (empty docx is ~4 kB)
    assert len(resp.content) > 5000, "DOCX file suspiciously small — manifest may not have rendered"


async def test_export_wd_docx_amendments_appendix(client, env_with_db):
    """EXP-01 / AMEND-02 — DOCX bytes delivered even when amendment notes exist."""
    wd_id = await _create_wd_with_jes_scores(client)
    # Add an amendment note
    await client.post(
        f"/api/wd/{wd_id}/amendments",
        json={"section": "du", "comment": "Review this duty for scope."},
    )
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    assert len(resp.content) > 0


async def test_export_poster_returns_bytes(client, env_with_db):
    """EXP-02 / API-09 — POST /api/wd/{id}/export/poster returns .docx bytes."""
    wd_id = await _create_wd_with_jes_scores(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/poster")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(resp.content) > 0


async def test_export_pdf_501_when_weasyprint_absent(client, env_with_db, monkeypatch):
    """EXP-03 — POST /api/wd/{id}/export/pdf returns 501 when WeasyPrint import fails."""
    import sys
    monkeypatch.setitem(sys.modules, "weasyprint", None)
    wd_id = await _create_wd(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/pdf")
    assert resp.status_code == 501
    assert "WeasyPrint" in resp.json()["detail"]


async def test_export_docx_404(client, env_with_db):
    """API-08 — POST /api/wd/does-not-exist/export/docx returns 404."""
    resp = await client.post("/api/wd/does-not-exist/export/docx")
    assert resp.status_code == 404


async def test_export_poster_404(client, env_with_db):
    """API-09 — POST /api/wd/does-not-exist/export/poster returns 404."""
    resp = await client.post("/api/wd/does-not-exist/export/poster")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# WR-08: PDF 501 via runtime probe failure (Pango/Cairo missing at render time)
# ---------------------------------------------------------------------------

async def test_export_pdf_501_when_weasyprint_probe_fails(client, env_with_db, monkeypatch):
    """WR-08 — POST /api/wd/{id}/export/pdf returns 501 when _probe_weasyprint() is False.

    Distinct from the import-failure path: WeasyPrint imports cleanly but the
    runtime probe (_probe_weasyprint) returns False, indicating Pango/Cairo are
    missing. This covers the second 501 branch in the PDF handler.
    """
    import app.services.export_service as es
    monkeypatch.setattr(es, "_weasyprint_available", False)

    wd_id = await _create_wd(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/pdf")
    # 501 from the _probe_weasyprint() guard; or 501 if weasyprint not installed
    assert resp.status_code == 501


# ---------------------------------------------------------------------------
# WR-09: 409 from require_og_confirmed gate on all export endpoints
# ---------------------------------------------------------------------------

async def test_export_docx_409_without_og(client, env_with_db):
    """WR-09 — POST /api/wd/{id}/export/docx returns 409 when OG not confirmed."""
    wd_id = await _create_wd(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "classification_pending"


async def test_export_poster_409_without_og(client, env_with_db):
    """WR-09 — POST /api/wd/{id}/export/poster returns 409 when OG not confirmed."""
    wd_id = await _create_wd(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/poster")
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "classification_pending"


# ---------------------------------------------------------------------------
# WR-10: self-healing JES flow in export_wd_docx
# ---------------------------------------------------------------------------

async def test_export_docx_self_heals_jes_scores(client, env_with_db, monkeypatch):
    """WR-10 — DOCX export triggers JES self-healing when jes_total_points is None.

    Confirms that the self-healing block is exercised: score_jes_v2 is called
    and the WD is re-loaded. We monkeypatch score_jes_v2 to a no-op (CI has no
    LLM) and assert that the export still succeeds (200 + non-empty bytes).
    """
    import app.api.export as export_mod

    async def _fake_score(**kwargs):  # noqa: ARG001
        return None

    monkeypatch.setattr(export_mod, "score_jes_v2", _fake_score)

    wd_id = await _create_wd(client)
    # PATCH confirmed_og + og_level so the 409 gate passes, but leave
    # jes_total_points as None so self-healing is triggered.
    resp = await client.patch(
        f"/api/wd/{wd_id}",
        json={
            "confirmed_og": {"og_code": "EC", "og_name": "Economics and Social Science Services"},
            "og_level": 4,
            "duties": [
                {
                    "id": "d1",
                    "text": "Analyses economic data for policy recommendations.",
                    "source": "noc",
                    "provenance_noc_code": "4163",
                    "advisor": False,
                }
            ],
        },
    )
    assert resp.status_code == 200

    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    assert len(resp.content) > 0


# ---------------------------------------------------------------------------
# WR-11: duties record-fallback in _build_wd_context
# ---------------------------------------------------------------------------

async def test_export_docx_uses_record_duties_fallback(client, env_with_db):
    """WR-11 — DOCX export succeeds when duties live in record only (no root duties).

    Exercises the _build_wd_context record-fallback path: root wd.duties is
    empty but record.duties has duty data. The export must still return 200
    and non-empty bytes.
    """
    wd_id = await _create_wd(client)
    # PATCH via the record dict only — no root-level duties field
    resp = await client.patch(
        f"/api/wd/{wd_id}",
        json={
            "confirmed_og": {"og_code": "EC", "og_name": "Economics and Social Science Services"},
            "og_level": 3,
            "jes_total_points": 520,
            "jes_scores": [
                {"factor_name": "Decision Making", "degree": 2, "points": 120},
            ],
            "record": {
                "title": "Policy Analyst",
                "duties": [
                    {
                        "id": "d1",
                        "text": "Develops policy briefs for senior management.",
                        "source": "noc",
                        "provenance_noc_code": "4163",
                        "provenance_section": "Main duties",
                        "provenance_hash": "abc123",
                        "advisor": False,
                        "orphan": False,
                    }
                ],
            },
        },
    )
    assert resp.status_code == 200

    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    assert len(resp.content) > 0


# ---------------------------------------------------------------------------
# Phase 21 — OGX-02: NON_EC_STANDARD_NAMES consolidated into constants.py
# ---------------------------------------------------------------------------

def test_standard_names_import_from_constants():
    """OGX-02 — export_service.py must import NON_EC_STANDARD_NAMES from constants.py,
    not define it locally.

    FAILS at Wave 0: export_service.py lines 50-55 still have local dict.
    Goes GREEN after Plan 02 (Wave 1) removes the local dict and adds the import.
    """
    import inspect
    import importlib
    export_service = importlib.import_module("app.services.export_service")
    source = inspect.getsource(export_service)
    # Must import from app.data.constants — not define locally
    assert "from app.data.constants import" in source and "NON_EC_STANDARD_NAMES" in source, \
        "export_service.py must import NON_EC_STANDARD_NAMES from app.data.constants"
    # Must NOT define a local copy
    assert "NON_EC_STANDARD_NAMES: dict" not in source, \
        "export_service.py must not define a local NON_EC_STANDARD_NAMES dict"


# ---------------------------------------------------------------------------
# Phase 25 — Accessible Template: ACC-02 / ACC-04 RED baseline (Plan 25-01)
# These 6 tests pin the contract for the new GoC Accessible JD format.
# They are EXPECTED TO FAIL at Wave 0 (current implementation is the
# legacy TBS Work Description format) — Plans 02 and 03 turn them GREEN
# by rewriting _build_wd_context and rendering through the new
# wd_accessible_template.docx (ACC-01..04).
# ---------------------------------------------------------------------------

# 7 Part 2 subsection headings from the reference document
# (data/AI Docs/Accessible Job Description Template (1).docx).
ACCESSIBLE_PART2_HEADINGS = [
    "Organizational context",
    "Client service results",
    "Key activities",
    "Skills",
    "Effort",
    "Responsibilities",
    "Working conditions",
]

ADVISOR_PLACEHOLDER = "[To be completed by advisor]"


def _docx_text(content: bytes) -> str:
    """Read back a rendered DOCX and concatenate paragraph + table-cell text.

    Used by the content-presence and structure tests to inspect what the
    export endpoint actually produced, since raw .docx bytes are zipped
    XML and can't be grepped directly.
    """
    d = docx.Document(io.BytesIO(content))
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            parts.extend(c.text for c in row.cells)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# ACC-02: Effort / Working Conditions section content (4 fallback branches)
# ---------------------------------------------------------------------------

async def test_accessible_effort_ec_populated(client, env_with_db):
    """ACC-02 — EC export must show Effort and Working-Conditions factors populated
    despite the EC scoring path persisting jes_scores WITHOUT a `category` key.

    The new Accessible format must look up category via factor_name -> category
    map (EC_JES_ELEMENTS / JES_FACTORS_BY_GROUP), NOT trust wd.jes_scores[*].category.

    Asserts both the factor name strings (which appear in the current TBS
    template's JES Factor column) AND the 'Effort' section heading (capital E),
    which only appears in the new Accessible format — the factor names
    'Physical effort' / 'Sensory effort' use lowercase 'e' so they don't match.
    This combination distinguishes a dedicated 'Effort' section from a stray
    factor_name cell in a JES table.
    """
    wd_id = await _create_wd_ec(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    text = _docx_text(resp.content)
    assert "Physical effort" in text, "EC Effort factor 'Physical effort' not present in rendered DOCX"
    assert "Sensory effort" in text, "EC Effort factor 'Sensory effort' not present in rendered DOCX"
    assert "Working conditions" in text, "EC Working Conditions factor not present in rendered DOCX"
    # Heading-style 'Effort' (capital E) — distinguishes Accessible section
    # from the lowercase 'effort' in factor_name values.
    assert "Effort" in text, (
        "Expected 'Effort' section heading (capital E) in rendered DOCX — "
        "EC effort factors must appear under a dedicated Effort section."
    )


async def test_accessible_effort_fb_populated(client, env_with_db):
    """ACC-02 — FB (point-rating with Effort + Conditions) export must show
    both Conditions factors ('Risk to health', 'Work environment') and Effort
    factors ('Physical effort', 'Sensory effort') in the rendered DOCX.

    Asserts factor names AND the 'Effort' heading (capital E) so the test
    fails in the current TBS template (which has no 'Effort' section) and
    passes once the Accessible template lands in Plan 25-02/03.
    """
    wd_id = await _create_wd_point_rating_with_effort(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    text = _docx_text(resp.content)
    assert "Risk to health" in text, "FB Conditions factor 'Risk to health' not present"
    assert "Work environment" in text, "FB Conditions factor 'Work environment' not present"
    assert "Physical effort" in text, "FB Effort factor 'Physical effort' not present"
    assert "Sensory effort" in text, "FB Effort factor 'Sensory effort' not present"
    assert "Effort" in text, (
        "Expected 'Effort' section heading in FB export — Effort factors "
        "must appear under a dedicated Effort section, not just in the JES table."
    )


async def test_accessible_effort_no_factor_group_placeholder(client, env_with_db):
    """ACC-02 — Point-rating group with NO Effort/Conditions categories (MT)
    must render the '[To be completed by advisor]' placeholder string in the
    Effort and Working-Conditions sections.
    """
    wd_id = await _create_wd_point_rating_no_effort(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    text = _docx_text(resp.content)
    assert ADVISOR_PLACEHOLDER in text, (
        "Expected '[To be completed by advisor]' placeholder for MT group with no Effort/WC factors"
    )


async def test_accessible_effort_level_description_placeholder(client, env_with_db):
    """ACC-02 — Level-description group (AS, jes_scores: []) must render
    the '[To be completed by advisor]' placeholder in Effort and
    Working-Conditions sections.
    """
    wd_id = await _create_wd_level_description(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    text = _docx_text(resp.content)
    assert ADVISOR_PLACEHOLDER in text, (
        "Expected '[To be completed by advisor]' placeholder for level-description group (AS)"
    )


# ---------------------------------------------------------------------------
# ACC-04: Content-presence (no literal Jinja2 / None leaks in rendered DOCX)
# ---------------------------------------------------------------------------

async def test_accessible_content_presence(client, env_with_db):
    """ACC-04 — Rendered DOCX for a fully-completed EC WD must have NO:
      * unrendered Jinja2 tag (literal '{{')
      * bare 'None' token (str(None) leak)
      * unrendered Jinja2 block tag (literal '%}')

    Together these three guards catch every common template-rendering bug
    the Accessible-template rewrite is at risk of introducing.

    Also asserts that `record.client_service_results` text (seeded via
    _RECORD_SEED) is actually rendered in the new 'Client service results'
    Part 2 subsection — fails against the current TBS template which has
    no such field/section.
    """
    wd_id = await _create_wd_ec(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    text = _docx_text(resp.content)
    assert "{{" not in text, "Unrendered Jinja2 expression tag leaked into output"
    # Wrap with newlines so the assertion matches a bare 'None' line, not a
    # substring like 'Nonetax' or 'NoneType'.
    assert "\nNone\n" not in ("\n" + text + "\n"), "str(None) leaked into rendered output"
    assert "%}" not in text, "Unrendered Jinja2 block tag leaked into output"
    # The new 'Client service results' Part 2 subsection must surface
    # record.client_service_results (seeded by _create_wd_ec). Fails in the
    # current TBS template (no such field/render) — locks the new data path.
    assert "Citizens receive timely" in text, (
        "client_service_results from record was not rendered — Part 2 "
        "'Client service results' section must surface record.client_service_results"
    )


# ---------------------------------------------------------------------------
# ACC-01: Structure — all 7 Part 2 subsection headings + Part 1/2 markers
# ---------------------------------------------------------------------------

async def test_accessible_structure_headings(client, env_with_db):
    """ACC-01 — Rendered Accessible DOCX must contain all 7 Part 2 subsection
    headings (Organizational context, Client service results, Key activities,
    Skills, Effort, Responsibilities, Working conditions) and the Part 1 /
    Part 2 markers from the reference document.
    """
    wd_id = await _create_wd_ec(client)
    resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert resp.status_code == 200
    text = _docx_text(resp.content)
    for heading in ACCESSIBLE_PART2_HEADINGS:
        assert heading in text, f"Missing Part 2 subsection heading: {heading!r}"
    assert "Part 1" in text, "Missing 'Part 1' marker (Position information and signatures)"
    assert "Part 2" in text, "Missing 'Part 2' marker (Job description)"


# ---------------------------------------------------------------------------
# Phase 26 — ORG-03: RED baseline for org_context export priority
# ---------------------------------------------------------------------------

async def test_org_context_in_export(client, env_with_db):
    """ORG-03: When org_context is set, the typed value appears in the DOCX output."""
    wd_id = await _create_wd_ec(client)
    patch_resp = await client.patch(
        f"/api/wd/{wd_id}", json={"org_context": "Test org context text for export"}
    )
    assert patch_resp.status_code == 200

    export_resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert export_resp.status_code == 200
    doc = docx.Document(io.BytesIO(export_resp.content))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Test org context text for export" in full_text


async def test_org_context_fallback_in_export(client, env_with_db):
    """ORG-03: When org_context is None, synthesized fallback (branch/reports/summary) is used.
    No template variable leak ({{}}) must appear in the output."""
    wd_id = await _create_wd_ec(client)
    # _create_wd_ec does NOT set org_context — org_context stays None
    export_resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert export_resp.status_code == 200
    doc = docx.Document(io.BytesIO(export_resp.content))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "{{" not in full_text
    assert "organizational_context_text" not in full_text


async def test_org_context_empty_string_falls_back(client, env_with_db):
    """F-01: A whitespace-only org_context must fall back to synthesized text,
    not render a blank Organizational Context section (defense-in-depth)."""
    wd_id = await _create_wd_ec(client)
    patch_resp = await client.patch(f"/api/wd/{wd_id}", json={"org_context": "   "})
    assert patch_resp.status_code == 200

    export_resp = await client.post(f"/api/wd/{wd_id}/export/docx")
    assert export_resp.status_code == 200
    doc = docx.Document(io.BytesIO(export_resp.content))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "{{" not in full_text
    assert "organizational_context_text" not in full_text
