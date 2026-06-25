"""
test_sjd.py — SJD-01 / SJD-02 requirements tests.

Wave 0: All tests are RED stubs. Implementation is in plans 22-02 and 22-03.

Requirements covered: SJD-01, SJD-02.
"""
import pytest

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Unit tests — SJD_LIBRARY constant (no HTTP client needed)
# ---------------------------------------------------------------------------

def test_sjd_library_count():
    """SJD-01: SJD_LIBRARY has exactly 10 entries (all entries from data/SJD Examples.txt)."""
    from app.data.sjd_library import SJD_LIBRARY
    assert len(SJD_LIBRARY) == 10


def test_sjd_entry_fields():
    """SJD-01: Every SJDEntry has all required fields with non-empty string values."""
    from app.data.sjd_library import SJD_LIBRARY
    for entry in SJD_LIBRARY:
        assert entry.sjd_number, f"Missing sjd_number on entry {entry}"
        assert entry.title, f"Missing title on entry {entry.sjd_number}"
        assert entry.og_code, f"Missing og_code on entry {entry.sjd_number}"
        assert isinstance(entry.og_level, int) and entry.og_level >= 1, \
            f"og_level must be a positive int on {entry.sjd_number}"


def test_og_code_normalization():
    """SJD-01: OG codes are normalized (no org-unit codes like PA, HM, NR)."""
    from app.data.sjd_library import SJD_LIBRARY
    VALID_OG_CODES = {"AS", "FI", "EC", "IT", "EN", "PE", "WP", "PS", "NU", "SW",
                      "FB", "FS", "LC", "LP", "MT", "NT", "PO"}
    for entry in SJD_LIBRARY:
        assert entry.og_code in VALID_OG_CODES, \
            f"Unexpected og_code {entry.og_code!r} on {entry.sjd_number} — must be normalized"


# ---------------------------------------------------------------------------
# Integration tests — GET /api/sjd endpoints
# ---------------------------------------------------------------------------

async def test_list_sjds_returns_all(client):
    """SJD-01: GET /api/sjd with no filter returns all 10 entries."""
    response = await client.get("/api/sjd")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 10


async def test_list_sjds_filter_by_og(client):
    """SJD-01: GET /api/sjd?og_code=EC returns only EC-group entries."""
    response = await client.get("/api/sjd?og_code=EC")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert all(e["og_code"] == "EC" for e in data), "All returned entries must have og_code=EC"


async def test_get_sjd_by_number(client):
    """SJD-01: GET /api/sjd/{number} returns the correct entry for a known SJD number."""
    response = await client.get("/api/sjd/DND-EC-58355")
    assert response.status_code == 200
    data = response.json()
    assert data["sjd_number"] == "DND-EC-58355"
    assert data["og_code"] == "EC"
    assert data["og_level"] == 2


async def test_get_sjd_404(client):
    """SJD-01 / T-22-01: GET /api/sjd/{number} returns 404 for unknown SJD number."""
    response = await client.get("/api/sjd/DND-DOES-NOT-EXIST")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Integration tests — POST /api/wd/{id}/sjd-start
# ---------------------------------------------------------------------------

async def test_sjd_start_prefills_wd(client):
    """SJD-01 / SJD-02: POST /api/wd/{id}/sjd-start sets confirmed_og, og_level,
    duties, and sjd_source on the WorkDescription."""
    # First create a WD
    create_resp = await client.post("/api/wd", json={"record": {}, "answers": {}, "step_index": 0})
    assert create_resp.status_code == 201
    wd_id = create_resp.json()["id"]

    # Call sjd-start with a known SJD
    resp = await client.post(
        f"/api/wd/{wd_id}/sjd-start",
        json={"sjd_number": "DND-EC-58355"},
    )
    assert resp.status_code == 200
    wd = resp.json()
    assert wd["confirmed_og"] is not None, "confirmed_og must be set after sjd-start"
    assert wd["og_level"] == 2, "og_level must be 2 for EC-02"
    assert isinstance(wd["duties"], list) and len(wd["duties"]) > 0, "seed duties must be populated"
    assert wd["sjd_source"] is not None, "sjd_source must be set"
    assert wd["sjd_source"]["sjd_number"] == "DND-EC-58355"
    assert wd["sjd_source"]["og_code"] == "EC"


def test_seed_duties_provenance():
    """SJD-02: Seed duties built for sjd-start have source='sjd' and sjd_number set."""
    from app.api.wd import _build_sjd_seed_duties
    from app.data.sjd_library import SJD_LIBRARY
    entry = next(e for e in SJD_LIBRARY if e.og_code == "EC")
    duties = _build_sjd_seed_duties(entry)
    assert len(duties) > 0, "Seed duties must not be empty"
    for d in duties:
        assert d.source == "sjd", f"Expected source='sjd' but got {d.source!r}"
        assert d.sjd_number == entry.sjd_number, \
            f"Expected sjd_number={entry.sjd_number!r} but got {d.sjd_number!r}"


# ---------------------------------------------------------------------------
# Integration test — DOCX manifest SJD provenance entry
# ---------------------------------------------------------------------------

async def test_manifest_includes_sjd_source(client):
    """SJD-02: After sjd-start, POST /api/wd/{id}/export/docx manifest includes SJD provenance entry."""
    # Create WD and run sjd-start
    create_resp = await client.post("/api/wd", json={"record": {"confirmed_og": {"og_code": "EC"}},
                                                      "answers": {}, "step_index": 0})
    assert create_resp.status_code == 201
    wd_id = create_resp.json()["id"]

    sjd_resp = await client.post(f"/api/wd/{wd_id}/sjd-start", json={"sjd_number": "DND-EC-58355"})
    assert sjd_resp.status_code == 200

    # Export and check manifest — the export endpoint returns a DOCX binary,
    # so we test _build_v2_manifest directly instead
    from app.services.export_service import _build_v2_manifest
    from app.db import get_connection
    from app.config import get_settings
    from app.models.work_description import WorkDescription

    settings = get_settings()
    con = get_connection(settings.db_path)
    row = con.execute("SELECT data FROM work_descriptions WHERE id = ?", (wd_id,)).fetchone()
    con.close()
    wd = WorkDescription.model_validate_json(row["data"])
    manifest = _build_v2_manifest(wd)

    sjd_entries = [e for e in manifest if e["source_type"] == "SJD"]
    assert len(sjd_entries) == 1, f"Expected 1 SJD manifest entry, got {len(sjd_entries)}"
    assert sjd_entries[0]["source_id"] == "DND-EC-58355"
    assert sjd_entries[0]["source_version"] == "DND SJD Library"
