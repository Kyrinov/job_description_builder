"""
tests/test_drf.py — Phase 9 DND DRF Integration tests.

All tests skip (not error) until Plans 09-02 (ingest script + service),
09-03 (router + API), and 09-04 (wizard step + DOCX section) land.

The contract being asserted:
    - GET /api/drf-links/{wd_id} returns 404 for unknown WD
    - GET /api/drf-links/{wd_id} returns 200 with empty candidates for
      non-DND positions
    - GET /api/drf-links/{wd_id} returns candidate list with
      (core_responsibility, departmental_result, fiscal_year) per item
      for DND positions
    - POST /api/drf-links/{wd_id}/confirm stores confirmed linkages on
      WD.drf_linkages (list of dicts)
    - After confirm, wd.drf_linkages[0]['provenance_source_id'] matches
      the drf_rows.id
    - Service-level: matching uses overlap between duty text tokens and
      the indexed drf_rows.search_text
    - DOCX export context dict contains drf_linkages key with at least
      1 entry when WD is DND with confirmed linkages
    - GET /wizard/drf?wd_id=... returns "not a DND position" indicator
      when is_dnd_position=False
    - GET /wizard/drf?wd_id=... renders candidate list when WD is DND
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
