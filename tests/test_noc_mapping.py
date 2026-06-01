from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


async def test_fts5_stage_returns_noc_codes(noc_mapping_db, monkeypatch, tmp_path):
    """Stage 1 FTS5 query returns at least one NOC code using the noc_mapping_db fixture."""
    pytest.skip("not yet implemented — Wave 1/2 will implement app.services.noc_mapper")


async def test_stage2_calls_embed_model(noc_mapping_db, monkeypatch, tmp_path):
    """Stage 2 calls OllamaAsyncClient.embed with model matching OLLAMA_EMBED_MODEL."""
    pytest.skip("not yet implemented — Wave 1/2 will implement app.services.noc_mapper")


async def test_empty_fts_result_raises_422(monkeypatch, tmp_path):
    """POST /api/noc/map when FTS5 returns empty shortlist returns HTTP 422."""
    pytest.skip("not yet implemented — Wave 2/3 will wire FastAPI router")


async def test_verbatim_guardrail_strips_fabricated(noc_mapping_db, monkeypatch, tmp_path):
    """_check_verbatim_fidelity strips duties not verbatim in DB; raises if all stripped."""
    pytest.skip("not yet implemented — Wave 1/2 will implement app.services.noc_mapper")


async def test_pipeline_returns_candidates(noc_mapping_db, monkeypatch, tmp_path):
    """Full mocked 3-stage pipeline returns NOCRankingResult with >= 1 candidate."""
    pytest.skip("not yet implemented — Wave 1/2 will implement app.services.noc_mapper")


async def test_api_route_200(noc_mapping_db, monkeypatch, tmp_path):
    """POST /api/noc/map with mocked pipeline returns HTTP 200 with candidates."""
    pytest.skip("not yet implemented — Wave 2/3 will wire FastAPI router")


async def test_confirm_noc_updates_wd(noc_mapping_db, monkeypatch, tmp_path):
    """POST /api/noc/confirm with valid wd_id + noc_code stores confirmed_noc on WorkDescription."""
    pytest.skip("not yet implemented — Wave 2/3 will wire FastAPI router and wd_store")
