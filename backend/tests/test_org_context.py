"""
tests/test_org_context.py — org-context prose synthesis endpoint.

Covers POST /api/org-context/synthesize:
- happy path: data points → LLM → prose
- prompt assembly only includes non-empty data points
- 422 when no data points are supplied
- 502 when the LLM call raises (frontend falls back to joined plain text)
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.api.org_context import OrgContextRequest, build_user_prompt, strip_think


def _mock_completion(content: str) -> SimpleNamespace:
    """Build a minimal stand-in for an AsyncOpenAI chat completion."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def test_build_user_prompt_omits_empty_fields():
    """Only non-empty data points appear in the assembled prompt."""
    prompt = build_user_prompt(
        OrgContextRequest(branch="Strategic Policy Branch", reports="", work_stream="Policy", additional="")
    )
    assert "Strategic Policy Branch" in prompt
    assert "Policy" in prompt
    assert "Reports to:" not in prompt
    assert "Additional context:" not in prompt


def test_strip_think_removes_reasoning_block():
    """A complete <think>…</think> block is removed, leaving only the answer."""
    raw = "<think>Let me draft this.\nMaybe two sentences.</think>\n\nThe position sits within the Branch."
    assert strip_think(raw) == "The position sits within the Branch."


def test_strip_think_drops_truncated_open_block():
    """A truncated block (no closing tag) yields empty rather than raw reasoning."""
    raw = "<think>The user wants me to write a paragraph. Let me deliberate at length"
    assert strip_think(raw) == ""


@pytest.mark.asyncio
async def test_synthesize_strips_think_block(client, env_with_db):
    """Reasoning <think> output is stripped before the prose is returned."""
    raw = "<think>deliberating…</think>\n\nThe position reports to the Director."
    with patch("app.api.org_context.org_context_client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_completion(raw))
        resp = await client.post(
            "/api/org-context/synthesize",
            json={"branch": "Strategic Policy Branch", "reports": "", "work_stream": "", "additional": ""},
        )
    assert resp.status_code == 200
    assert resp.json()["prose"] == "The position reports to the Director."


@pytest.mark.asyncio
async def test_synthesize_returns_prose(client, env_with_db):
    """Happy path — data points are synthesized into prose via the LLM client."""
    prose = "The position sits within the Strategic Policy Branch and reports to the Director."
    with patch("app.api.org_context.org_context_client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_completion(prose))
        resp = await client.post(
            "/api/org-context/synthesize",
            json={
                "branch": "Strategic Policy Branch",
                "reports": "Director, Policy Development",
                "work_stream": "Policy analysis",
                "additional": "",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["prose"] == prose


@pytest.mark.asyncio
async def test_synthesize_rejects_all_empty(client, env_with_db):
    """422 when no data points are supplied — nothing to synthesize."""
    resp = await client.post(
        "/api/org-context/synthesize",
        json={"branch": "", "reports": "", "work_stream": "", "additional": ""},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_synthesize_llm_failure_returns_502(client, env_with_db):
    """502 when the LLM call raises — frontend keeps its joined-text fallback."""
    with patch("app.api.org_context.org_context_client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("upstream down"))
        resp = await client.post(
            "/api/org-context/synthesize",
            json={"branch": "Strategic Policy Branch", "reports": "", "work_stream": "", "additional": ""},
        )
    assert resp.status_code == 502
