"""
conftest.py — shared test fixtures for the v2.0 backend.

Provides:
- tmp_db_path: per-test fresh SQLite file under pytest tmp_path
- env_with_db: env vars wired so Settings picks up tmp_db_path
- test_app: FastAPI app instance bound to tmp_db_path
- client: httpx.AsyncClient bound to test_app via ASGITransport
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def tmp_db_path(tmp_path) -> str:
    """Per-test fresh SQLite file path."""
    return str(tmp_path / "test.db")


@pytest.fixture
def env_with_db(tmp_db_path, monkeypatch):
    """Set env vars so Settings picks up tmp_db_path."""
    import os
    parent = os.path.dirname(tmp_db_path) or "."
    monkeypatch.setenv("DB_PATH", tmp_db_path)
    monkeypatch.setenv("PROJECT_ROOT", parent)
    return tmp_db_path


@pytest_asyncio.fixture
async def test_app(env_with_db):
    """FastAPI app with lifespan-driven schema creation against tmp DB.

    Wave 0 stub: pytest.importorskip causes collection-level skip until
    app.main is implemented in Plan 02. After Plan 02, this fixture
    imports the real app and the rest of the suite can run.
    """
    pytest.importorskip("app.main")
    from app.main import app  # noqa: F401  (post-Plan-02 import)
    return app


@pytest_asyncio.fixture
async def client(test_app):
    """AsyncClient bound to test_app for in-process HTTP calls."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
