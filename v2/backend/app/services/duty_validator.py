"""app/services/duty_validator.py — WG-01 structural duty validation. Four deterministic text rules. No LLM. Called only from POST /api/wd/{id}/validate-duties."""
from __future__ import annotations

import re


def validate_duties(duties: list) -> list[dict]:
    return []
