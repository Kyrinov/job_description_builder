"""
app/api/health.py — GET /health endpoint.

Returns Ollama model availability status for observability.
The lifespan already hard-fails if Ollama is unreachable at startup;
this endpoint reports live status for monitoring.
"""
from fastapi import APIRouter
import ollama

from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Returns 200 with Ollama model availability status.

    Successful response: {"status": "ok", "required_models": [...], "missing_models": []}
    Degraded response:   {"status": "degraded", ...}
    Error response:      {"status": "error", "detail": "..."}
    """
    try:
        client = ollama.AsyncClient(host=settings.ollama_base_url)
        response = await client.list()
        available_models = [m.model for m in response.models]
        required = [settings.ollama_generation_model, settings.ollama_embed_model]
        missing = [m for m in required if m not in available_models]
        return {
            "status": "ok" if not missing else "degraded",
            "ollama_url": settings.ollama_base_url,
            "required_models": required,
            "missing_models": missing,
            "all_available_models": available_models,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}
