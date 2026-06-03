"""Shared pytest fixtures for Phase 1 tests."""
import sys

import pytest


def _clear_app_modules():
    """Remove all app modules from sys.modules for a clean import."""
    for key in list(sys.modules.keys()):
        if key.startswith("app."):
            del sys.modules[key]


def _set_valid_env(monkeypatch, temp_db_path, tmp_path):
    """Helper to set all required env vars for a valid Settings instantiation."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "gemma4:31b")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    monkeypatch.setenv("DB_PATH", temp_db_path)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))


@pytest.fixture(autouse=True)
def _clean_module_state():
    """Clear app modules between tests to prevent cross-test contamination."""
    yield  # no-op


@pytest.fixture
def temp_db_path(tmp_path):
    """Temporary SQLite database file path for isolation."""
    return str(tmp_path / "test_app.db")


@pytest.fixture
def valid_env(monkeypatch, temp_db_path, tmp_path):
    """Set all required env vars for a valid Settings instantiation."""
    _set_valid_env(monkeypatch, temp_db_path, tmp_path)


@pytest.fixture
def mock_healthy_ollama():
    """Mock AsyncClient that simulates healthy Ollama with both required models."""
    from unittest.mock import AsyncMock, MagicMock

    mock = MagicMock()
    entries = []
    for name in ("gemma4:31b", "nomic-embed-text:latest"):
        entry = MagicMock()
        entry.model = name
        entries.append(entry)
    mock.list = AsyncMock(return_value=MagicMock(models=entries))
    return mock


@pytest.fixture
def noc_db(tmp_path):
    """
    Temp-file SQLite connection with NOC schema and sqlite_vec loaded.
    Used by test_noc_ingest.py tests — does NOT require Ollama to be running.
    """
    from app.db import get_connection, create_schema
    db_path = str(tmp_path / "test_noc.db")
    con = get_connection(db_path)
    create_schema(con)
    yield con
    con.close()


@pytest.fixture
def ca_jes_db(tmp_path):
    """
    Temp-file SQLite connection with full schema (NOC + CA/JES) and sqlite_vec loaded.
    Used by test_ca_ingest.py, test_jes_ingest.py, test_policy_ingest.py.
    Does NOT require Ollama to be running.

    Note: uses a different db_path ('test_ca_jes.db') than the noc_db fixture
    to avoid sharing state across test modules.
    """
    from app.db import get_connection, create_schema

    db_path = str(tmp_path / "test_ca_jes.db")
    con = get_connection(db_path)
    create_schema(con)  # creates all tables — NOC + CA_JES once Plan 03-02 lands
    yield con
    con.close()


@pytest.fixture
def noc_mapping_db(tmp_path):
    """
    Temp SQLite DB with NOC schema, synthetic FTS5 data, and 768-dim fake vec rows.
    Used by test_noc_mapping.py integration tests — does NOT require Ollama to be running.

    Synthetic data: NOC 21232 "Software engineers and designers", TEER 2,
    one Main duties element. FTS5 and vec populated. index_metadata set to
    nomic-embed-text:latest so assert_noc_index_model() passes.
    """
    import sqlite_vec as sv
    from app.db import create_schema, get_connection

    db_path = str(tmp_path / "test_noc_mapping.db")
    con = get_connection(db_path)
    create_schema(con)

    # Insert synthetic noc_units row
    con.execute(
        "INSERT OR IGNORE INTO noc_units(noc_code, teer_level, title, definition, source_hash) "
        "VALUES (?, ?, ?, ?, ?)",
        ("21232", "1", "Software engineers and designers",
         "Design, develop, and test software systems.", "fakehash_v1"),
    )
    # Insert synthetic noc_elements (Main duties)
    con.execute(
        "INSERT OR IGNORE INTO noc_elements(noc_code, element_type, element_text, source_hash) "
        "VALUES (?, ?, ?, ?)",
        ("21232", "Main duties", "Develop and maintain application software.", "fakehash_v1"),
    )
    # Populate FTS5 from noc_units + noc_elements
    con.execute(
        "INSERT INTO noc_fts(noc_code, title, definition, element_type, element_text) "
        "SELECT noc_code, title, definition, '', '' FROM noc_units"
    )
    con.execute(
        "INSERT INTO noc_fts(noc_code, title, definition, element_type, element_text) "
        "SELECT e.noc_code, u.title, u.definition, e.element_type, e.element_text "
        "FROM noc_elements e JOIN noc_units u ON u.noc_code = e.noc_code"
    )
    # Drop old vec table (may be FLOAT[1024] from Phase 2 ingest), recreate as FLOAT[768]
    con.execute("DROP TABLE IF EXISTS noc_chunks_vec")
    con.executescript(
        "CREATE VIRTUAL TABLE noc_chunks_vec USING vec0("
        "rowid INTEGER PRIMARY KEY, embedding FLOAT[768] distance_metric=cosine)"
    )
    # Insert fake 768-dim vector for the element row
    elem_row = con.execute(
        "SELECT id FROM noc_elements WHERE noc_code = '21232' LIMIT 1"
    ).fetchone()
    fake_vec = sv.serialize_float32([0.1] * 768)
    con.execute(
        "INSERT INTO noc_chunks_vec(rowid, embedding) VALUES (?, ?)",
        (elem_row["id"], fake_vec),
    )
    # Update index_metadata so assert_noc_index_model() passes during tests
    con.execute(
        "INSERT OR REPLACE INTO index_metadata(key, value, updated_at) "
        "VALUES (?, ?, datetime('now'))",
        ("embedding_model", "nomic-embed-text:latest"),
    )
    con.commit()

    yield db_path
    con.close()


@pytest.fixture
def og_db(tmp_path):
    """
    Temp SQLite DB with full schema + synthetic og_definitions rows for AS, EC, IT, PE.
    Used by test_og_classification.py and test_og_ranking.py.
    Does NOT require Ollama to be running.
    """
    from app.db import create_schema, get_connection

    db_path = str(tmp_path / "test_og.db")
    con = get_connection(db_path)
    create_schema(con)  # creates og_definitions table

    for row in [
        (
            "EC", "Economics and Social Science Services", "PA",
            "Positions primarily involved in economic and social research and related activities.",
            "the planning, development, delivery or management of policies, programs, services or other activities in the social sciences directed toward Canadians",
            "the planning, development, delivery or management of policies, programs, services or other activities directed to the public or to the Public Service",
        ),
        (
            "AS", "Administrative Services", "PA",
            "Positions primarily involved in administrative services work.",
            "the planning, development, delivery or management of government policies, programs, services or other activities directed to the Public Service",
            None,
        ),
        (
            "IT", "Information Technology", None,
            "Positions primarily involved in IT systems development and operation.",
            None,
            None,
        ),
        (
            "PE", "Personnel Administration", "PA",
            "Positions primarily involved in HR policy and classification work.",
            None,
            None,
        ),
    ]:
        con.execute(
            "INSERT OR IGNORE INTO og_definitions "
            "(og_code, og_name, parent_group, definition, inclusions, exclusions, source_file, source_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (*row, "TBS-OCHRO-OG.txt", "testhash_v1"),
        )
    con.commit()

    yield db_path
    con.close()


@pytest.fixture
def jd_db(tmp_path):
    """
    Temp SQLite DB with full schema + synthetic noc_elements (5 Main duties rows for NOC
    21232) and og_definitions row for EC. Used by test_jd_generation.py integration tests.
    Does NOT require Ollama to be running.
    """
    from app.db import create_schema, get_connection

    db_path = str(tmp_path / "test_jd.db")
    con = get_connection(db_path)
    create_schema(con)

    # Synthetic NOC unit row
    con.execute(
        "INSERT OR IGNORE INTO noc_units(noc_code, teer_level, title, definition, source_hash) "
        "VALUES (?, ?, ?, ?, ?)",
        ("21232", "1", "Software engineers and designers",
         "Design, develop, and test software systems.", "fakehash_noc_v1"),
    )
    # Synthetic source_documents row (for ProvenanceTag version lookup)
    con.execute(
        "INSERT OR IGNORE INTO source_documents(source_name, version_label, content_hash) "
        "VALUES (?, ?, ?)",
        ("noc_2021_version_1.0_-_elements.csv", "NOC 2021 v1.0",
         "50c3e31a90b0150cc5b8efd29ec020c2fd9ea5fc5b0a171ed65d3cd9a0abf32f"),
    )
    # 5 synthetic Main duties rows
    duties = [
        "Design and develop software systems and applications.",
        "Analyze user requirements and translate to technical specifications.",
        "Conduct code reviews and ensure software quality standards.",
        "Collaborate with stakeholders to define system architecture.",
        "Write and maintain technical documentation for software systems.",
    ]
    for duty_text in duties:
        con.execute(
            "INSERT OR IGNORE INTO noc_elements(noc_code, element_type, element_text, source_hash) "
            "VALUES (?, ?, ?, ?)",
            ("21232", "Main duties", duty_text,
             "50c3e31a90b0150cc5b8efd29ec020c2fd9ea5fc5b0a171ed65d3cd9a0abf32f"),
        )
    # EC og_definitions row (for orphan check)
    con.execute(
        "INSERT OR IGNORE INTO og_definitions "
        "(og_code, og_name, parent_group, definition, inclusions, exclusions, source_file, source_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "EC", "Economics and Social Science Services", "PA",
            "Positions primarily involved in economic and social research.",
            "planning, development, delivery or management of policies directed toward Canadians",
            "administrative support work directed internally to the Public Service",
            "TBS-OCHRO-OG.txt", "testhash_v1",
        ),
    )
    con.commit()
    yield db_path
    con.close()


@pytest.fixture
def jes_db(tmp_path):
    """
    Temp SQLite DB with full schema + synthetic jes_factors rows for EC (2 factors)
    and a source_documents row for JES version lookup.
    Used by test_jes_scoring.py. Does NOT require Ollama to be running.

    Factors seeded:
      - EC / Decision making: D1=5pts, D2=15pts, D3=35pts; max_points=35
      - EC / Communication:   D1=10pts, D2=30pts; max_points=30
    """
    import json
    from app.db import create_schema, get_connection

    db_path = str(tmp_path / "test_jes.db")
    con = get_connection(db_path)
    create_schema(con)

    factors = [
        (
            "EC", "Decision making",
            "Measures latitude applied and impact of decision making.",
            json.dumps([
                {"degree": "D1", "text": "Issue-specific, impact on own work unit.", "points": 5},
                {"degree": "D2", "text": "Issue-specific, impact on components of project.", "points": 15},
                {"degree": "D3", "text": "Multiple issues, impact on branch or division.", "points": 35},
            ]),
            json.dumps({"D1": 5, "D2": 15, "D3": 35}),
            35, "fakehash_jes_v1",
        ),
        (
            "EC", "Communication",
            "Measures the nature of communication activities.",
            json.dumps([
                {"degree": "D1", "text": "Provides factual information.", "points": 10},
                {"degree": "D2", "text": "Explains findings and recommendations.", "points": 30},
            ]),
            json.dumps({"D1": 10, "D2": 30}),
            30, "fakehash_jes_v1",
        ),
    ]
    for f in factors:
        con.execute(
            "INSERT OR IGNORE INTO jes_factors "
            "(og_code, factor_name, factor_definition, degree_descriptors, "
            "point_values, max_points, source_hash) VALUES (?,?,?,?,?,?,?)",
            f,
        )
    con.execute(
        "INSERT OR IGNORE INTO source_documents"
        "(source_name, version_label, content_hash, ingested_at) "
        "VALUES (?, ?, ?, datetime('now'))",
        (
            "EC Economics and Social Science Services - Job Evaluation Standard 2017.txt",
            "JES v1.0",
            "fakehash_jes_v1",
        ),
    )
    con.commit()
    yield db_path
    con.close()


@pytest.fixture
def export_db(tmp_path):
    """
    Temp SQLite DB with full schema for Phase 8 export tests.
    Empty schema (no seeded data) — tests build a WorkDescription with
    make_exported_wd() to control stage and content precisely.
    Used by tests/test_export.py. Does NOT require Ollama to be running.
    """
    from app.db import create_schema, get_connection

    db_path = str(tmp_path / "test_export.db")
    con = get_connection(db_path)
    create_schema(con)
    con.commit()
    yield db_path
    con.close()


@pytest.fixture
def drf_db(tmp_path):
    """Fresh SQLite database for Phase 9 DRF integration tests."""
    try:
        from app.db import create_schema, get_connection
    except ImportError:
        pytest.skip("app modules not yet implemented")
    db_path = str(tmp_path / "drf_test.db")
    conn = get_connection(db_path)
    create_schema(conn)
    conn.close()
    return db_path


def make_exported_wd(db_path: str, *, complete: bool = True) -> str:
    """
    Insert a WorkDescription in stage='jes_scored' ready for export.

    When complete=True, JES factors are fully scored (no sentinel level=-1
    and no points=None). When complete=False, the second factor is the
    failed-factor sentinel (level=-1, points=None) per D-01/D-02.

    Returns the wd_id (UUID string).
    """
    from app.db import get_connection
    from app.models.work_description import (
        DraftDuty,
        DraftText,
        JESFactorScore,
        NOCMatch,
        OGRecommendation,
        ProvenanceTag,
        WorkDescription,
    )
    from app.services.wd_store import save_work_description
    from datetime import date

    conn = get_connection(db_path)

    noc_prov = ProvenanceTag(
        source_type="NOC", source_id="41401",
        source_version="NOC 2021 v1.0", retrieved_date=date.today(),
    )
    confirmed_noc = NOCMatch(
        noc_code="41401",
        noc_title="Economists and economic policy researchers and analysts",
        teer_level="1", confidence=0.9, rationale="Strong match",
        matched_duty_statements=["Conduct economic analysis."],
        provenance=noc_prov,
    )

    og_prov = ProvenanceTag(
        source_type="TBS_OG_DEF", source_id="EC",
        source_version="TBS-OCHRO-OG.txt", retrieved_date=date.today(),
    )
    directive_prov = ProvenanceTag(
        source_type="TBS_DIRECTIVE", source_id="Directive 4.2.1",
        source_version="TBS Directive on Classification 2021",
        retrieved_date=date.today(),
    )
    og_recommendation = OGRecommendation(
        og_code="EC", og_name="Economics and Social Science Services",
        level="EC-05", confidence=0.85,
        rationale="Policy work directed to Canadians",
        provenance=og_prov,
        cited_articles=[directive_prov],
        confirmed_by_advisor=True,
    )

    org_ctx = DraftText(
        text="Operates within the Policy Branch.",
        provenance=og_prov,
    )

    duty_prov = ProvenanceTag(
        source_type="NOC", source_id="41401",
        source_version="NOC 2021 v1.0", retrieved_date=date.today(),
    )
    draft_duties = [
        DraftDuty(
            text="Conduct economic analysis of policy options.",
            provenance=duty_prov,
        ),
    ]

    advisor_prov = ProvenanceTag(
        source_type="ADVISOR", source_id="advisor",
        source_version="manual entry", retrieved_date=date.today(),
        modified_by_advisor=True,
    )
    advisor_additions = [
        DraftDuty(
            text="Liaise with provincial counterparts.",
            advisor_modified=True,
            provenance=advisor_prov,
        ),
    ]

    jes_prov_1 = ProvenanceTag(
        source_type="JES", source_id="EC/Decision making",
        source_version="JES v1.0", retrieved_date=date.today(),
    )
    jes_prov_2 = ProvenanceTag(
        source_type="JES", source_id="EC/Communication",
        source_version="JES v1.0", retrieved_date=date.today(),
    )
    if complete:
        jes_scores = [
            JESFactorScore(
                factor_name="Decision making", level=3, points=35,
                rationale="High latitude",
                provenance=jes_prov_1,
            ),
            JESFactorScore(
                factor_name="Communication", level=2, points=30,
                rationale="Explains findings",
                provenance=jes_prov_2,
            ),
        ]
        jes_total_points = 65
    else:
        # incomplete=True: second factor is the failed-factor sentinel per D-01
        jes_scores = [
            JESFactorScore(
                factor_name="Decision making", level=3, points=35,
                rationale="High latitude",
                provenance=jes_prov_1,
            ),
            JESFactorScore(
                factor_name="Communication", level=-1, points=None,
                rationale="Scoring failed after 3 retries",
                provenance=jes_prov_2,
            ),
        ]
        jes_total_points = 35

    wd = WorkDescription(
        session_id="test-session",
        raw_input="Develops policy options for senior management.",
        position_title="Senior Policy Analyst",
        position_number="12345",
        og_level="EC-05",
        supervisor_title="Manager, Policy",
        supervisor_position_number="00001",
        review_date=date(2026, 6, 2),
        organizational_context=org_ctx,
        confirmed_noc=confirmed_noc,
        og_recommendation=og_recommendation,
        confirmed_og="EC",
        confirmed_level="EC-05",
        draft_duties=draft_duties,
        advisor_additions=advisor_additions,
        jes_scores=jes_scores,
        jes_total_points=jes_total_points,
        stage="jes_scored",
    )
    save_work_description(conn, wd)
    conn.close()
    return str(wd.id)
