"""
app/main.py — FastAPI application entry point.

Startup sequence (DATA-03):
1. pydantic-settings Settings validates env vars (raises on import if missing)
2. lifespan checks Ollama reachability and model presence (raises RuntimeError if fails)
3. lifespan creates SQLite schema (idempotent)
4. App begins serving requests

Run with: uvicorn app.main:app --reload
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import ollama
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import health
from app.api import jd_generation
from app.api import noc_mapping
from app.api import og_classification
from app.config import settings
from app.db import assert_noc_index_model, create_schema, get_connection


def ollama_client_factory():
    """
    Factory for the Ollama AsyncClient.

    Extracted as a module-level callable so tests can monkeypatch it:
        monkeypatch.setattr("app.main.ollama_client_factory", lambda: mock_client)
    """
    return ollama.AsyncClient(host=settings.ollama_base_url)


def _normalize_model_name(name: str) -> str:
    """Append :latest tag if the model name has no tag (Pitfall 2 mitigation)."""
    return name if ":" in name else f"{name}:latest"


async def assert_ollama_ready() -> None:
    """
    Pre-startup assertion: Ollama must be reachable and required models present.

    Raises RuntimeError if either condition is not met.
    RuntimeError causes Uvicorn to abort startup with a non-zero exit code (DATA-03).
    """
    client = ollama_client_factory()

    try:
        response = await client.list()
        available = {m.model for m in response.models}
    except Exception as e:
        raise RuntimeError(
            f"Ollama is not reachable at {settings.ollama_base_url}. "
            f"Ensure the Ollama service is running. Error: {e}"
        ) from e

    required = {
        _normalize_model_name(settings.ollama_generation_model),
        _normalize_model_name(settings.ollama_embed_model),
    }
    missing = required - available
    if missing:
        raise RuntimeError(
            f"Required Ollama models are not present: {missing}. "
            f"Run `ollama pull <model>` for each missing model."
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager for startup/shutdown hooks (DATA-03).

    Uses lifespan — NOT @app.on_event which is deprecated since FastAPI 0.93.
    """
    # --- startup ---
    await assert_ollama_ready()
    con = get_connection(settings.db_path)
    create_schema(con)
    assert_noc_index_model(con, settings.ollama_embed_model)  # PIPE-05
    con.close()

    yield

    # --- shutdown ---
    # Connection pool cleanup happens here in later phases


app = FastAPI(
    title="JD Builder",
    description="Government of Canada Job Description Builder",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(noc_mapping.router)
app.include_router(og_classification.router)
app.include_router(jd_generation.router)

# Phase 4 — static CSS file serving (UI-SPEC §CSS Architecture)
_static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(_static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

# Phase 4 — Jinja2 templates for the wizard. Search BOTH the project-root
# `templates/` dir (where step_noc.html and partials/noc_results.html live,
# matching the _templates_dir resolution in app/api/noc_mapping.py) AND
# `app/templates/` (where base.html lives). Jinja2Templates accepts a list
# of directories; the loader searches them in order so the wizard
# template's `{% extends "base.html" %}` resolves correctly.
_templates_dirs = [
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
    os.path.join(os.path.dirname(__file__), "templates"),
]
wizard_templates = Jinja2Templates(directory=_templates_dirs)


@app.get("/wizard/noc", response_class=HTMLResponse)
async def wizard_noc(request: Request) -> HTMLResponse:
    """Render the NL→NOC mapping wizard step (Phase 4)."""
    return wizard_templates.TemplateResponse(
        "wizard/step_noc.html", {"request": request}
    )


@app.get("/wizard/jd", response_class=HTMLResponse)
async def wizard_jd(request: Request, wd_id: str = "") -> HTMLResponse:
    """Render the JD generation wizard step (Phase 6).

    Falls back to a minimal placeholder if templates/wizard/step_jd.html is not yet
    present (Plan 06-04 owns the real template). Once Plan 06-04 lands, the Jinja
    template takes over and this fallback becomes dead code.
    """
    import jinja2

    try:
        return wizard_templates.TemplateResponse(
            "wizard/step_jd.html", {"request": request, "wd_id": wd_id}
        )
    except jinja2.TemplateNotFound:
        return HTMLResponse(
            "<!DOCTYPE html><html><body>"
            f"<h1>JD Generation Wizard</h1>"
            f"<p>WorkDescription ID: {wd_id or '(none)'}</p>"
            "<p>The full template will be added in Plan 06-04.</p>"
            "</body></html>"
        )
