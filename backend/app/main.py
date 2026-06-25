"""
app/main.py — FastAPI application entry point (v2.0).

Startup sequence (Phase 10):
1. pydantic-settings Settings validates env vars (raises on import if missing)
2. lifespan creates the SQLite schema at Settings.db_path (idempotent)
3. App begins serving requests on /api/* (Vite proxy → :5173 in dev)

Run with: uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import api_router
from app.config import get_settings
from app.db import create_schema, get_connection


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: create SQLite schema. Shutdown: nothing (sqlite3 closes on GC)."""
    # --- startup ---
    settings = get_settings()
    con = get_connection(settings.db_path)
    create_schema(con)
    con.close()

    yield

    # --- shutdown --- (no resources to release in v2.0)


def create_app() -> FastAPI:
    """App factory — testable without relying on module-level state."""
    app = FastAPI(
        title="JD Builder v2.0 API",
        version="0.1.0",
        description="Conversational WD builder — FastAPI JSON API backend",
        lifespan=lifespan,
    )

    # Diagnostic: log RequestValidationError to surface the offending field
    @app.exception_handler(RequestValidationError)
    async def _log_validation_error(request: Request, exc: RequestValidationError):
        body = None
        try:
            body = await request.json()
        except (ValueError, UnicodeDecodeError):
            body = "<unparseable>"
        logging.getLogger("app.main").warning(
            "422 %s %s — validation errors: %s — body keys: %s",
            request.method, request.url.path, exc.errors(),
            sorted(body.keys()) if isinstance(body, dict) else type(body).__name__,
        )
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    # Mount all routers under /api so the Vite proxy is a simple pass-through
    app.include_router(api_router, prefix="/api")

    return app


# Module-level instance for `uvicorn app.main:app`
app = create_app()
