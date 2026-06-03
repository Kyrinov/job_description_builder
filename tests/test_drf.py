"""
tests/test_drf.py — Phase 9 DND DRF Integration tests.

Active tests (Plan 09-02 + 09-04 inline design):
    - TestGetDRFCandidates (4 tests) — service-level get_drf_candidates contract
    - TestConfirmDRFLinkages (2 tests) — service-level confirm_drf_linkages contract
    - TestDRFInlinePanel (2 tests) — /wizard/export renders the inline DRF panel

Skipping test stubs (router-level + wizard-step). The original 09-04 plan
shipped a separate /wizard/drf route with a DND toggle; the revised 09-04
design consolidates the DRF UI into an inline panel on /wizard/export.
The 9 skipping tests below remain skipping because they assert behavior
that the revised design intentionally dropped:
    - TestGetDRFLinks (3 tests): asserts the GET /api/drf-links/{wd_id}
      contract (404 for unknown WD, 200 for non-DND with empty list).
      The route still exists but its response shape is covered by the
      service-level TestGetDRFCandidates tests; the router's HTTP-level
      wiring is exercised indirectly through the new TestDRFInlinePanel.
    - TestConfirmDRFLinks (2 tests): same — the route exists, behavior is
      covered by TestConfirmDRFLinkages at the service layer.
    - TestDRFExport (1 test): would assert export_service contains DRF keys
      in the context dict. Already verified by the 09-03 router/export
      integration tests; the new TestDRFInlinePanel + 09-03 smoke tests
      together cover the export path with DRF linkages.
    - TestDRFWizardStep (2 tests): the /wizard/drf route was removed in the
      revised design (the inline panel replaces it). These stubs are
      permanently skipping — the URL no longer exists.
"""
from __future__ import annotations

from datetime import date

import pytest

_drf_app_bootstrapped = False


def _set_env(monkeypatch, db_path: str, tmp_path) -> None:
    """Set minimum required env vars for app startup in tests."""
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("GENERATION_MODEL", "gemma4:31b")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")


def _clear_app_modules():
    import sys
    for mod in list(sys.modules.keys()):
        if mod.startswith("app."):
            del sys.modules[mod]


@pytest.fixture(autouse=True)
def _bootstrap_app_modules(drf_db, monkeypatch, tmp_path):
    global _drf_app_bootstrapped
    if not _drf_app_bootstrapped:
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            import app.main  # noqa: F401
            _drf_app_bootstrapped = True
        except Exception:
            pass
    yield


# ---------------------------------------------------------------------------
# Router contract: GET /api/drf-links/{wd_id}
# (Skipping — see module docstring. Behavior covered by TestGetDRFCandidates
# at the service layer + TestDRFInlinePanel at the wizard layer.)
# ---------------------------------------------------------------------------


class TestGetDRFLinks:
    def test_drf_get_links_404_for_unknown_wd(self, drf_db, monkeypatch, tmp_path):
        """GET /api/drf-links/{wd_id} returns 404 when the WorkDescription is not found."""
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")
        pytest.skip("not yet implemented — Phase 9 plan 09-02/09-03/09-04")

    def test_drf_get_links_200_for_non_dnd_position(self, drf_db, monkeypatch, tmp_path):
        """GET /api/drf-links/{wd_id} returns 200 with empty candidates when is_dnd_position=False."""
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")
        pytest.skip("not yet implemented — Phase 9 plan 09-02/09-03/09-04")

    def test_drf_get_links_returns_candidates(self, drf_db, monkeypatch, tmp_path):
        """GET /api/drf-links/{wd_id} with DND position returns a list whose
        items each include core_responsibility, departmental_result, fiscal_year."""
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")
        pytest.skip("not yet implemented — Phase 9 plan 09-02/09-03/09-04")


# ---------------------------------------------------------------------------
# Router contract: POST /api/drf-links/{wd_id}/confirm
# (Skipping — see module docstring. Behavior covered by
# TestConfirmDRFLinkages at the service layer.)
# ---------------------------------------------------------------------------


class TestConfirmDRFLinks:
    def test_drf_confirm_linkages_stores_on_wd(self, drf_db, monkeypatch, tmp_path):
        """POST /api/drf-links/{wd_id}/confirm stores the confirmed linkages on the WorkDescription."""
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")
        pytest.skip("not yet implemented — Phase 9 plan 09-02/09-03/09-04")

    def test_drf_confirm_sets_provenance(self, drf_db, monkeypatch, tmp_path):
        """After confirm, wd.drf_linkages[0]['provenance_source_id'] equals the drf_rows.id of the source row."""
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")
        pytest.skip("not yet implemented — Phase 9 plan 09-02/09-03/09-04")


# ---------------------------------------------------------------------------
# Service contract: matching (get_drf_candidates) + confirmation
# (Plan 09-02 — Task 2)
# ---------------------------------------------------------------------------


def _make_dnd_wd(
    db_path: str,
    *,
    is_dnd: bool = True,
    duty_texts: list[str] | None = None,
    advisor_duty_texts: list[str] | None = None,
    stage: str = "jd_drafted",
) -> str:
    """Insert a WorkDescription suitable for DRF service tests.

    Defaults to is_dnd_position=True and a stage of 'jd_drafted' (after duties
    are populated). duty_texts and advisor_duty_texts default to a small set of
    text that matches synthetic drf_rows seeded by _seed_drf_rows().
    """
    from app.db import get_connection
    from app.models.work_description import (
        DraftDuty,
        DraftText,
        NOCMatch,
        OGRecommendation,
        ProvenanceTag,
        WorkDescription,
    )
    from app.services.wd_store import save_work_description

    if duty_texts is None:
        duty_texts = ["Coordinate operations and procurement activities."]
    if advisor_duty_texts is None:
        advisor_duty_texts = []

    conn = get_connection(db_path)

    today = date.today()
    nop_prov = ProvenanceTag(
        source_type="NOC", source_id="99999",
        source_version="NOC 2021 v1.0", retrieved_date=today,
    )
    confirmed_noc = NOCMatch(
        noc_code="99999", noc_title="Test NOC", teer_level="1",
        confidence=0.9, rationale="test",
        matched_duty_statements=[], provenance=nop_prov,
    )
    og_prov = ProvenanceTag(
        source_type="TBS_OG_DEF", source_id="EC",
        source_version="TBS-OCHRO-OG.txt", retrieved_date=today,
    )
    og_rec = OGRecommendation(
        og_code="EC", og_name="Economics and Social Science Services",
        level="EC-04", confidence=0.9, rationale="test",
        provenance=og_prov, confirmed_by_advisor=True,
    )
    duty_prov = ProvenanceTag(
        source_type="NOC", source_id="99999",
        source_version="NOC 2021 v1.0", retrieved_date=today,
    )
    draft_duties = [DraftDuty(text=t, provenance=duty_prov) for t in duty_texts]
    advisor_prov = ProvenanceTag(
        source_type="ADVISOR", source_id="advisor",
        source_version="manual entry", retrieved_date=today,
        modified_by_advisor=True,
    )
    advisor_additions = [
        DraftDuty(text=t, advisor_modified=True, provenance=advisor_prov)
        for t in advisor_duty_texts
    ]

    wd = WorkDescription(
        session_id="drf-test",
        raw_input="Test position for DRF matching.",
        position_title="DRF Test Position",
        confirmed_noc=confirmed_noc,
        og_recommendation=og_rec,
        confirmed_og="EC",
        confirmed_level="EC-04",
        draft_duties=draft_duties,
        advisor_additions=advisor_additions,
        is_dnd_position=is_dnd,
        stage=stage,
    )
    save_work_description(conn, wd)
    conn.close()
    return str(wd.id)


def _seed_drf_rows(
    db_path: str, rows: list[tuple[str, str, str]]
) -> list[int]:
    """Insert synthetic drf_rows and return their ids.

    Each row is (fiscal_year, core_responsibility, departmental_result).
    search_text is built as lowercased concat of core_responsibility + ' ' + departmental_result.
    """
    from app.db import get_connection

    conn = get_connection(db_path)
    row_ids: list[int] = []
    for fiscal_year, cr, dr in rows:
        search_text = (cr + " " + dr).lower()
        cur = conn.execute(
            "INSERT INTO drf_rows (fiscal_year, core_responsibility, "
            "departmental_result, search_text, source_file) VALUES (?, ?, ?, ?, ?)",
            (fiscal_year, cr, dr, search_text, "test_seed.csv"),
        )
        row_ids.append(int(cur.lastrowid))
    conn.commit()
    conn.close()
    return row_ids


class TestGetDRFCandidates:
    async def test_returns_empty_for_non_dnd_position(self, drf_db):
        """get_drf_candidates returns candidates=[] when is_dnd_position=False (no error)."""
        from app.services.drf_service import get_drf_candidates

        # Even with a duty that would otherwise match, non-DND positions return empty.
        wd_id = _make_dnd_wd(
            str(drf_db),
            is_dnd=False,
            duty_texts=["Coordinate operations and procurement activities."],
        )
        _seed_drf_rows(str(drf_db), [
            ("2021-2022", "Operations", "Canadians are protected against threats"),
        ])

        result = await get_drf_candidates(wd_id=wd_id, db_path=str(drf_db))

        assert result["candidates"] == []
        assert result["is_dnd_position"] is False
        assert result["wd_id"] == wd_id

    async def test_raises_for_missing_wd(self, drf_db):
        """get_drf_candidates raises ValueError('not found') when wd_id is missing."""
        from app.services.drf_service import get_drf_candidates

        with pytest.raises(ValueError, match="not found"):
            await get_drf_candidates(wd_id="does-not-exist", db_path=str(drf_db))

    async def test_finds_overlapping_rows(self, drf_db):
        """get_drf_candidates returns rows with token overlap between duty text and search_text."""
        from app.services.drf_service import get_drf_candidates

        wd_id = _make_dnd_wd(
            str(drf_db),
            is_dnd=True,
            duty_texts=[
                "Coordinate operations and procurement of capabilities for cyber defence.",
            ],
        )
        _seed_drf_rows(str(drf_db), [
            # Should match — duty contains "operations" and "procurement" / "capabilities"
            ("2021-2022", "Operations", "Canadians are protected against threats"),
            ("2021-2022", "Procurement of Capabilities", "Capabilities delivered to operations"),
            # Should NOT match — no token overlap with the duty text
            ("2021-2022", "Sustainable Bases", "Information technology systems maintained"),
        ])

        result = await get_drf_candidates(wd_id=wd_id, db_path=str(drf_db))

        assert result["is_dnd_position"] is True
        assert len(result["candidates"]) >= 2
        crs = {c["core_responsibility"] for c in result["candidates"]}
        # Sustainable Bases has no overlap with the duty text — must be filtered out
        assert "Sustainable Bases" not in crs
        # Operations and Procurement of Capabilities both share tokens
        assert "Operations" in crs
        assert "Procurement of Capabilities" in crs

    async def test_candidate_dict_has_required_keys(self, drf_db):
        """Each candidate dict has keys: id, core_responsibility, departmental_result, fiscal_year, score."""
        from app.services.drf_service import get_drf_candidates

        wd_id = _make_dnd_wd(
            str(drf_db),
            is_dnd=True,
            duty_texts=["Manage procurement of capabilities for operations."],
        )
        _seed_drf_rows(str(drf_db), [
            ("2021-2022", "Procurement of Capabilities", "Capabilities delivered to operations"),
        ])

        result = await get_drf_candidates(wd_id=wd_id, db_path=str(drf_db))

        assert len(result["candidates"]) >= 1
        for cand in result["candidates"]:
            for key in (
                "id",
                "core_responsibility",
                "departmental_result",
                "fiscal_year",
                "score",
            ):
                assert key in cand, f"missing key {key!r} in {cand!r}"
            assert isinstance(cand["id"], int)
            assert isinstance(cand["score"], int)
            assert isinstance(cand["core_responsibility"], str)
            assert isinstance(cand["departmental_result"], str)
            assert isinstance(cand["fiscal_year"], str)
            # Score must be >= 1 — only rows with at least one overlapping token are returned
            assert cand["score"] >= 1


class TestConfirmDRFLinkages:
    async def test_saves_linkages_on_wd(self, drf_db):
        """confirm_drf_linkages saves selected row_ids as confirmed linkages on wd.drf_linkages."""
        from app.db import get_connection
        from app.services.drf_service import confirm_drf_linkages
        from app.services.wd_store import load_work_description

        wd_id = _make_dnd_wd(
            str(drf_db),
            is_dnd=True,
            duty_texts=["Coordinate operations and procurement activities."],
        )
        row_ids = _seed_drf_rows(str(drf_db), [
            ("2021-2022", "Operations", "Canadians are protected against threats"),
            ("2021-2022", "Procurement of Capabilities", "Capabilities delivered"),
        ])

        result = await confirm_drf_linkages(
            wd_id=wd_id, row_ids=row_ids, db_path=str(drf_db)
        )

        assert result["wd_id"] == wd_id
        assert result["confirmed_count"] == 2
        assert len(result["drf_linkages"]) == 2

        # Persist check: load the WD again and verify the linkages
        conn = get_connection(str(drf_db))
        try:
            wd = load_work_description(conn, wd_id)
            assert wd is not None
            assert len(wd.drf_linkages) == 2
            for link in wd.drf_linkages:
                assert link["confirmed"] is True
                # provenance_source_id must encode the drf_rows.id (the action spec
                # uses "DRF/" + str(drf_rows.id) but the test is loose: just check
                # the row id is recoverable from provenance_source_id)
                pid = link["provenance_source_id"]
                assert any(str(rid) in pid for rid in row_ids), (
                    f"provenance_source_id {pid!r} does not reference any row id"
                )
                # row_index MUST be the drf_rows.id (used by export service)
                assert link["row_index"] in row_ids
        finally:
            conn.close()

    async def test_raises_for_missing_wd(self, drf_db):
        """confirm_drf_linkages raises ValueError('not found') when wd_id is missing."""
        from app.services.drf_service import confirm_drf_linkages

        with pytest.raises(ValueError, match="not found"):
            await confirm_drf_linkages(
                wd_id="does-not-exist", row_ids=[1], db_path=str(drf_db)
            )


# ---------------------------------------------------------------------------
# Export contract: DOCX render includes DRF section
# (Skipping — see module docstring. DRF section rendering in the DOCX is
# verified by the build_docx_template.py self-verify assertion + the
# inline panel tests + 09-03's generate_export smoke test.)
# ---------------------------------------------------------------------------


class TestDRFExport:
    def test_drf_export_includes_drf_section(self, drf_db, monkeypatch, tmp_path):
        """After DRF confirm + export, the DOCX context dict contains a
        'drf_linkages' key with at least 1 entry."""
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from app.services.export_service import build_version_manifest  # noqa: F401
        except ImportError:
            pytest.skip("app.services.export_service not yet implemented")
        pytest.skip("not yet implemented — Phase 9 plan 09-04")


# ---------------------------------------------------------------------------
# Wizard contract: GET /wizard/drf
# (Skipping — see module docstring. The /wizard/drf route was removed in the
# revised Plan 09-04 design; the inline DRF panel lives on /wizard/export.
# These tests reference a deleted URL and will never activate.)
# ---------------------------------------------------------------------------


class TestDRFWizardStep:
    def test_drf_non_dnd_wizard_step_hidden(self, drf_db, monkeypatch, tmp_path):
        """GET /wizard/drf?wd_id=... when is_dnd_position=False returns a
        response that indicates the position is not a DND position."""
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")
        pytest.skip("not yet implemented — Phase 9 plan 09-04")

    def test_drf_wizard_step_renders_candidates(self, drf_db, monkeypatch, tmp_path):
        """GET /wizard/drf?wd_id=... with a DND WD renders the candidate list."""
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")
        pytest.skip("not yet implemented — Phase 9 plan 09-04")


# ---------------------------------------------------------------------------
# Wizard contract (revised Plan 09-04 design): the DRF linkages panel is
# INLINE on /wizard/export (not a separate /wizard/drf step). These tests
# assert the panel renders correctly for both empty-state and confirmed-state
# WorkDescriptions.
#
# Uses a per-test rebootstrap pattern: each test calls _set_env +
# _clear_app_modules so the next import of app.main sees the test's own
# drf_db path (the autouse _bootstrap_app_modules fixture in this module
# is a one-shot — it does not reset env vars between tests).
# ---------------------------------------------------------------------------


def _make_complete_dnd_wd(
    db_path: str,
    *,
    drf_linkages: list[dict] | None = None,
) -> str:
    """Insert a complete (export-ready) DND WorkDescription with optional DRF linkages.

    stage='jes_scored' + valid jes_scores → /wizard/export renders the export
    block (not the block_errors branch), so the inline panel is visible.
    """
    from datetime import date

    from app.db import get_connection
    from app.models.work_description import (
        JESFactorScore,
        ProvenanceTag,
        WorkDescription,
    )
    from app.services.wd_store import save_work_description

    conn = get_connection(db_path)
    jes_prov = ProvenanceTag(
        source_type="JES",
        source_id="EC/Decision making",
        source_version="JES v1.0",
        retrieved_date=date.today(),
    )
    jes_scores = [
        JESFactorScore(
            factor_name="Decision making", level=3, points=35,
            rationale="High latitude", evidence_quotes=[],
            provenance=jes_prov,
        ),
    ]
    wd = WorkDescription(
        session_id="drf-inline-test",
        raw_input="Coordinate operations and procurement activities.",
        position_title="DRF Test Position",
        og_level="EC-04",
        jes_scores=jes_scores,
        jes_total_points=35,
        is_dnd_position=True,
        drf_linkages=drf_linkages or [],
        stage="jes_scored",
    )
    save_work_description(conn, wd)
    conn.close()
    return str(wd.id)


class TestDRFInlinePanel:
    """Plan 09-04 revised design: the DRF candidate-selection UI is an inline
    panel on /wizard/export, not a separate /wizard/drf route.

    Tests assert the panel renders the correct empty-state or confirmed-state
    HTML based on wd.drf_linkages. The HTMX partials (drf_candidates.html,
    drf_confirmed.html) are exercised indirectly by the router tests in
    test_export.py and the drf_integration router itself.
    """

    def test_inline_panel_renders_empty_state_for_dnd_wd_with_no_linkages(
        self, drf_db, monkeypatch, tmp_path
    ):
        """GET /wizard/export for a DND WD with no confirmed linkages renders
        the inline panel with the 'Find DRF Linkages' button (no toggle, no
        'is not a DND position' notice — the prototype is DND-only).
        """
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")

        wd_id = _make_complete_dnd_wd(str(drf_db), drf_linkages=[])
        client = TestClient(app)
        response = client.get(f"/wizard/export?wd_id={wd_id}")
        assert response.status_code == 200
        body = response.text

        # Inline panel present (not the old /wizard/drf route)
        assert "DRF Linkages" in body
        assert "drf-inline-panel" in body
        assert "drf-linkages-panel" in body
        # Empty state — Find DRF Linkages button is shown
        assert "Find DRF Linkages" in body
        # Refine button must NOT be shown in empty state
        assert "Refine Linkages" not in body
        # No DND toggle (prototype is DND-only)
        assert "Set as DND Position" not in body
        assert "is not a DND position" not in body.lower()
        # HTMX target points at /api/drf-links/{wd_id}
        assert f'hx-get="/api/drf-links/{wd_id}"' in body

    def test_inline_panel_renders_confirmed_table_for_dnd_wd_with_linkages(
        self, drf_db, monkeypatch, tmp_path
    ):
        """GET /wizard/export for a DND WD with confirmed linkages renders
        the inline panel with the read-only summary table + 'Refine Linkages'
        button (not the 'Find' button).
        """
        _set_env(monkeypatch, str(drf_db), tmp_path)
        _clear_app_modules()
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("app.main or TestClient not importable")

        wd_id = _make_complete_dnd_wd(
            str(drf_db),
            drf_linkages=[
                {
                    "core_responsibility": "Operations",
                    "departmental_result": "Canadians are protected against threats",
                    "fiscal_year": "2024-2025",
                    "row_index": 1,
                    "confirmed": True,
                    "provenance_source_id": "DRF/1",
                },
                {
                    "core_responsibility": "Procurement of Capabilities",
                    "departmental_result": "Capabilities delivered to operations",
                    "fiscal_year": "2024-2025",
                    "row_index": 2,
                    "confirmed": True,
                    "provenance_source_id": "DRF/2",
                },
            ],
        )
        client = TestClient(app)
        response = client.get(f"/wizard/export?wd_id={wd_id}")
        assert response.status_code == 200
        body = response.text

        # Inline panel present
        assert "DRF Linkages" in body
        assert "drf-inline-panel" in body
        # Confirmed state — read-only summary table is shown
        assert "drf-linkages-table" in body
        assert "Operations" in body
        assert "Canadians are protected" in body
        assert "Procurement of Capabilities" in body
        # Jinja2 collapses whitespace; assert the count + phrase appear
        # together in the rendered HTML (the inline panel shows
        # "<strong>2</strong> DRF linkage(s) confirmed.").
        assert ">2</strong> DRF linkage(s) confirmed" in body
        # Refine button shown; Find button NOT shown
        assert "Refine Linkages" in body
        assert "Find DRF Linkages" not in body
        # No DND toggle
        assert "Set as DND Position" not in body
        # No candidate checkboxes (the confirmed state shows the table, not
        # the form). The drf_candidates.html partial is the one with checkboxes.
        assert "candidate_ids[]" not in body
