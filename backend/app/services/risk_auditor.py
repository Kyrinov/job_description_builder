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
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal

# ── Constants ────────────────────────────────────────────────────────────────

# Repo-root resolved: backend/app/services/risk_auditor.py -> parents[3] is the repo
# root (services -> app -> backend -> root), then into data/agreements/.
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
    (e.g. NT, ED), if the JSON file is absent, or if the file is unreadable
    or malformed. Never raises.
    """
    dir_name = OG_AGREEMENT_DIR.get(og_code)
    if not dir_name:
        return None
    json_path = DATA_DIR / dir_name / f"{dir_name}_full.json"
    if not json_path.exists():
        return None
    try:
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# ── ERR (Federal Court) rules ────────────────────────────────────────────────

def _check_duty_coverage(wd) -> AuditFinding | None:
    """ERR_DUTY_COVERAGE: fires when WD has fewer than ERR_MIN_DUTY_COUNT duties.

    Source: FPSLREB Cushnie — 'If a duty is not contained in a generic or a specific
    job description, it must be added in order to meet the requirements of the
    collective agreement for a complete and current Statement of Work.'
    """
    duties = wd.duties or []
    if len(duties) < ERR_MIN_DUTY_COUNT:
        return AuditFinding(
            rule_id="ERR_DUTY_COVERAGE",
            section="du",
            severity="warning",
            citation=(
                "FPSLREB: Cushnie — 'If a duty is not contained in a generic or a specific "
                "job description, it must be added in order to meet the requirements of the "
                "collective agreement for a complete and current Statement of Work.'"
            ),
            recommendation=(
                f"This position description has {len(duties)} "
                f"{'duty' if len(duties) == 1 else 'duties'}. "
                f"Most positions require at least {ERR_MIN_DUTY_COUNT} duties to adequately "
                "describe the work. Review whether all significant responsibilities are listed."
            ),
        )
    return None


def _check_duty_specificity(wd) -> AuditFinding | None:
    """ERR_DUTY_SPECIFICITY: fires when 50%+ of duties are under 8 words (Dervin/Trépanier).

    Source: FPSLREB Dervin — 'Although the use of generic job descriptions can be an
    acceptable way for the employer to satisfy its obligation under the collective
    agreement, the job description needs to reflect the duties of the employees. It
    can fail to do so if the terms used do not accurately reflect the depth or scope
    of the grievor's work.'
    """
    duties = wd.duties or []
    if not duties:
        return None  # already caught by coverage rule
    short_count = sum(1 for d in duties if len(d.text.split()) < 8)
    if short_count / len(duties) >= ERR_SPECIFICITY_THRESHOLD:
        return AuditFinding(
            rule_id="ERR_DUTY_SPECIFICITY",
            section="du",
            severity="advisory",
            citation=(
                "FPSLREB: Dervin — 'Although the use of generic job descriptions can be an "
                "acceptable way for the employer to satisfy its obligation under the collective "
                "agreement, the job description needs to reflect the duties of the employees. "
                "It can fail to do so if the terms used do not accurately reflect the depth "
                "or scope of the grievor's work.'"
            ),
            recommendation=(
                f"{short_count} of {len(duties)} duties are very short (under 8 words). "
                "Review whether they adequately describe the depth and scope of the work, "
                "as required by the collective agreement."
            ),
        )
    return None


def _run_err_checks(wd) -> list[dict]:
    """Evaluate Federal Court ERR principle rules against the WorkDescription."""
    findings = []

    # ERR Rule 1: Duty Coverage Completeness (Cushnie principle)
    duty_coverage = _check_duty_coverage(wd)
    if duty_coverage:
        findings.append(duty_coverage.to_dict())

    # ERR Rule 2: Generic vs. Specific Duty Adequacy (Dervin/Trépanier principle)
    duty_specificity = _check_duty_specificity(wd)
    if duty_specificity:
        findings.append(duty_specificity.to_dict())

    return findings


# ── CBA (Collective Agreement) checks ─────────────────────────────────────────

# Article type keywords → JD section-key relevance (Signal 2).
# Conservative: only flag sections that genuinely relate to duties, overview, or classification.
_ARTICLE_RELEVANCE: dict[str, set[str]] = {
    "scope":             {"du", "ov", "cls"},
    "exclusion":         {"du"},
    "application":       {"du", "cls"},
    "recognition":       {"du", "cls"},
    "statement of duties": {"du"},
}

# Curated significant terms per article type (Signal 1 term sources).
# These are CBA-specific terms unlikely to appear in typical duty text by coincidence.
_ARTICLE_TERMS: dict[str, list[str]] = {
    "scope":             ["bargaining unit", "collective agreement", "occupational group"],
    "exclusion":         ["excluded", "exclusion", "managerial", "confidential"],
    "application":       ["apply", "application", "covered by", "subject to"],
    "recognition":       ["bargaining agent", "certified", "recognized", "union"],
    "statement of duties": ["statement of duties", "classification level", "point rating", "current statement"],
}


def _classify_article_type(title: str) -> str | None:
    """Identify the audit-relevant article type from a CBA section title.

    Returns the first matching article type keyword, or None if the title
    is not an audit-relevant article (e.g. 'check-off', 'grievance procedure').
    """
    title_lower = title.lower()
    for article_type in _ARTICLE_RELEVANCE:
        if article_type in title_lower:
            return article_type
    return None


def _extract_duty_text(wd) -> str:
    """Concatenate all duty text for Signal 1 scanning."""
    duties = wd.duties or []
    return " ".join(d.text for d in duties).lower()


def _run_cba_checks(wd, cba_data: dict) -> list[dict]:
    """Evaluate CBA clause matching using the two-signal rule (AUDIT-02).

    Signal 1: A curated significant term from the CBA article appears verbatim in duty text.
    Signal 2: The CBA article type is relevant to at least one JD section key.

    Both signals must be present for a finding to fire. This conservative design
    prefers false negatives over false positives in this legal domain.
    """
    findings = []
    duty_text = _extract_duty_text(wd)
    sections = cba_data.get("sections", [])

    fired_rule_ids: set[str] = set()  # deduplicate: one finding per article type at most

    for section in sections:
        title = section.get("title", "")
        article_type = _classify_article_type(title)
        if article_type is None:
            continue  # Not an audit-relevant article type

        # Signal 2: article type relevant to a JD section
        relevant_sections = _ARTICLE_RELEVANCE.get(article_type, set())
        if not relevant_sections:
            continue  # No relevant section mapping

        # Signal 1: any curated term from this article type appears in duty text
        terms = _ARTICLE_TERMS.get(article_type, [])
        signal_1 = any(term.lower() in duty_text for term in terms)

        if not signal_1:
            continue  # Two-signal rule: both must be present

        # Both signals present — build a finding (deduplicate by article type)
        rule_id = f"CBA_{article_type.upper().replace(' ', '_')}"
        if rule_id in fired_rule_ids:
            continue
        fired_rule_ids.add(rule_id)

        # Determine the primary relevant JD section key for this finding
        section_key = "du" if "du" in relevant_sections else next(iter(relevant_sections))

        findings.append(AuditFinding(
            rule_id=rule_id,
            section=section_key,
            severity="advisory",
            citation=f"{title}: {section.get('text', '')[:300]}...",
            recommendation=(
                f"The duty text contains terms related to a CBA '{article_type}' article. "
                "Verify that the duties accurately reflect what is covered by the collective "
                "agreement for this occupational group."
            ),
        ).to_dict())

    return findings


# ── Public entry point ───────────────────────────────────────────────────────

def run_audit(wd, cba_data: dict | None) -> list[dict]:
    """Run all CBA and ERR checks. Returns list of finding dicts.

    Args:
        wd: WorkDescription instance
        cba_data: Loaded CBA JSON dict, or None if no agreement mapping exists.

    Returns:
        List of AuditFinding.to_dict() results — empty list if no findings.
    """
    findings = []
    if cba_data:
        findings.extend(_run_cba_checks(wd, cba_data))
    findings.extend(_run_err_checks(wd))
    return findings
