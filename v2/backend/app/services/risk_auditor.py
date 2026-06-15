"""
app/services/risk_auditor.py — CBA + ERR compliance audit rules.

Deterministic rule matching. No LLM. Called only from POST /api/wd/{id}/audit.

Rules (implemented in Phase 24 Plan 02):
  CBA_STATEMENT_OF_DUTIES  — verbatim term match + section relevance (two-signal)
  ERR_DUTY_COVERAGE        — at least ERR_MIN_DUTY_COUNT duties present (Cushnie)
  ERR_DUTY_SPECIFICITY     — not 50%+ of duties under 8 words (Dervin/Trépanier)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal

# ── Constants ────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parents[3] / "data" / "agreements"

OG_AGREEMENT_DIR: dict[str, str] = {
    "EC": "EC",
    "IT": "IT_CS",
    "AS": "PA",
    "FI": "CT_FI",
    "CR": "PA",
    "PM": "PA",
    "WP": "PA",
    "GT": "TC",
    "EL": "EL",
    "FB": "FB",
    "FS": "FS",
    "AI": "AI",
    "AU": "CT_FI",
    "LC": "LP_LA",
    "LP": "LP_LA",
    "MT": "SP_AP",
    "NU": "SH",
    "PS": "SH",
    "SW": "SH",
    "PO": "PO",
    # NT, ED: no confirmed agreement directory — CBA checks skipped for these groups
}

ERR_MIN_DUTY_COUNT = 3          # Cushnie principle minimum
ERR_SPECIFICITY_THRESHOLD = 0.5 # Dervin/Trépanier: 50%+ short duties = systematic underspecification


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class AuditFinding:
    rule_id: str
    section: Literal['id', 'ov', 'du', 'cls', 'q', 'drf']
    severity: Literal['advisory', 'warning']
    citation: str        # verbatim CBA clause or court citation
    recommendation: str  # plain-language guidance for the advisor

    def to_dict(self) -> dict:
        return asdict(self)


# ── CBA loader ───────────────────────────────────────────────────────────────

def load_cba_data(og_code: str) -> dict | None:
    """Load CBA JSON for the given OG code.

    Returns None if no agreement directory mapping exists for this OG code
    (e.g. NT, ED) or if the JSON file is absent. Never raises.
    """
    # STUB: always returns None until Plan 02 implementation
    return None


# ── Public entry point ───────────────────────────────────────────────────────

def run_audit(wd, cba_data: dict | None) -> list[dict]:
    """Run all CBA and ERR checks. Returns list of finding dicts.

    Args:
        wd: WorkDescription instance
        cba_data: Loaded CBA JSON dict, or None if no agreement mapping exists.

    Returns:
        List of AuditFinding.to_dict() results — empty list if no findings.
    """
    # STUB: returns empty list until Plan 02 implementation
    return []
