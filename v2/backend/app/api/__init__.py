"""
app/api — v2.0 API routers.

Each router mounts under a specific path. main.py aggregates them via
`app.include_router(api_router, prefix="/api")` so the Vite proxy
(`/api` → :8000) is a simple pass-through.

To add a new endpoint module:
1. Create app/api/<name>.py with `router = APIRouter()` and route handlers
2. Import and include it below
"""
from __future__ import annotations

from fastapi import APIRouter

from . import health

api_router = APIRouter()
api_router.include_router(health.router)

__all__ = ["api_router"]
