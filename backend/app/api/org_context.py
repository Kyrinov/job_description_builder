"""
app/api/org_context.py — Organizational context prose synthesis.

POST /api/org-context/synthesize — takes branch, reports-to, work stream, and
additional context and returns 1-3 fluid sentences describing where the position
sits in the organization. Used by the org_context questionnaire step (Phase 26)
to replace mechanical field concatenation with natural prose.

LLM client: module-level AsyncOpenAI singleton (cloud MiniMax if cloud_api_key
is set, else Ollama), mirroring the factory pattern in app/ai/jes_scoring.py.
Plain chat completion — no instructor/structured output, since the result is
free-form prose.

On any LLM error (or empty output) this returns 502. The frontend swallows the
failure and keeps the joined-plain-text fallback already written to
record.org_context, so the advisor never sees an error.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config import get_settings

router = APIRouter()


# ---------------------------------------------------------------------------
# LLM client singleton — built once at import time. Tests patch
# app.api.org_context.org_context_client.chat.completions.create directly.
# ---------------------------------------------------------------------------
def make_org_context_client() -> AsyncOpenAI:
    """Build the AsyncOpenAI client from current settings (cloud or Ollama)."""
    settings = get_settings()
    if settings.cloud_api_key:
        return AsyncOpenAI(
            base_url=settings.cloud_base_url,
            api_key=settings.cloud_api_key,
        )
    return AsyncOpenAI(
        base_url=settings.ollama_base_url.rstrip("/") + "/v1",
        api_key="ollama",  # placeholder; Ollama does not validate this
    )


org_context_client = make_org_context_client()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class OrgContextRequest(BaseModel):
    branch: str = Field(default="", max_length=500)
    reports: str = Field(default="", max_length=500)
    work_stream: str = Field(default="", max_length=2000)
    additional: str = Field(default="", max_length=2000)


class OrgContextResponse(BaseModel):
    prose: str


SYSTEM_PROMPT = (
    "You are a Government of Canada classification advisor writing the "
    "'Organizational Context' section of a work description. Given a few data "
    "points about where a position sits in the organization, write one to three "
    "fluid, professional sentences that read as natural prose. Write in the "
    "third person, present tense. Do not use bullet points, headings, or field "
    "labels. Do not invent facts beyond the data points provided; if a data "
    "point is missing, simply omit it."
)


def build_user_prompt(req: OrgContextRequest) -> str:
    """Assemble a labelled, LLM-friendly prompt from the non-empty data points."""
    lines: list[str] = []
    if req.branch.strip():
        lines.append(f"Branch or directorate: {req.branch.strip()}")
    if req.reports.strip():
        lines.append(f"Reports to: {req.reports.strip()}")
    if req.work_stream.strip():
        lines.append(f"Work stream or program: {req.work_stream.strip()}")
    if req.additional.strip():
        lines.append(f"Additional context: {req.additional.strip()}")
    data = "\n".join(lines)
    return (
        "Write the Organizational Context paragraph from these data points:\n\n"
        f"{data}"
    )


@router.post("/org-context/synthesize", response_model=OrgContextResponse)
async def synthesize_org_context(req: OrgContextRequest) -> OrgContextResponse:
    """Synthesize fluid org-context prose from the supplied data points."""
    # Need at least one data point — otherwise there is nothing to synthesize.
    if not any(s.strip() for s in (req.branch, req.reports, req.work_stream, req.additional)):
        raise HTTPException(status_code=422, detail="No organizational context provided")

    settings = get_settings()
    try:
        completion = await org_context_client.chat.completions.create(
            model=settings.generation_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(req)},
            ],
            max_tokens=400,
            temperature=0.3,
        )
        prose = (completion.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001 — surface as 502; frontend keeps fallback
        raise HTTPException(status_code=502, detail="Org context synthesis failed") from exc

    if not prose:
        raise HTTPException(status_code=502, detail="Org context synthesis returned empty")

    return OrgContextResponse(prose=prose)
