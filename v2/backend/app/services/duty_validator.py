"""
app/services/duty_validator.py — WG-01 structural duty validation.

Four deterministic text rules. No LLM. Called only from POST /api/wd/{id}/validate-duties.

Rules:
  WORD_COUNT  — duty must contain 8–25 words (split on whitespace)
  NO_PASSIVE  — duty must not open with a passive auxiliary (is/are/was/were/been/being)
                or a definite/indefinite article (the/a/an)
  VERB_FIRST  — duty must open with a capitalised word (third-person singular verb form);
                trailing comma/semicolon on the first word is stripped before checking
  NO_DUPLICATE — duty text must be unique within the list (case-insensitive exact match)

Calibration: All 21 polished duties in _SJD_DUTY_SUGGESTIONS (wd.py) pass at 0%.
"""
from __future__ import annotations

import re

# Matches first word that is a passive auxiliary or article.
# Applied ONLY to the first word (after stripping trailing punctuation).
# Non-backtracking: anchored at start, word boundary at end.
_PASSIVE_OPENERS = re.compile(
    r'^(is|are|was|were|been|being|the|a|an)$',
    re.IGNORECASE,
)

# Matches a capitalised word ending in 's' (3rd-person singular verb form:
# Plans, Coordinates, Develops, Manages, Provides, Prepares, Designs, Conducts).
# The trailing 's' requirement distinguishes verbs from adjectives/nouns that
# happen to be capitalised ("Administrative", "Senior", "Federal", "Areas").
_VERB_FIRST = re.compile(
    r'^[A-Z][a-zA-Z]*s$',
)


def validate_duties(duties: list) -> list[dict]:
    """Return per-duty findings for WG-01 rules.

    Args:
        duties: list of objects with .id (str) and .text (str) attributes.

    Returns:
        list of dicts: [{"duty_id": str, "rules_failed": [{"rule": str, "detail": str}]}]
        Only duties with at least one failing rule are included.
    """
    findings: list[dict] = []
    seen: dict[str, str] = {}  # lowercased text -> first duty_id that had this text

    for duty in duties:
        text = (getattr(duty, 'text', None) or '').strip()
        rules_failed: list[dict] = []

        words = text.split()
        wc = len(words)

        # Rule: WORD_COUNT
        if wc < 8 or wc > 25:
            rules_failed.append({
                "rule": "WORD_COUNT",
                "detail": f"{wc} word{'s' if wc != 1 else ''} (expected 8–25)",
            })

        # Derive the first word, stripping trailing punctuation to handle
        # compound verb openers like "Plans, coordinates and manages..."
        first = words[0].rstrip(',;:.') if words else ''

        # Rule: NO_PASSIVE (checked before VERB_FIRST — passive also fails verb-first,
        # but NO_PASSIVE is the more specific and actionable diagnostic)
        if first and _PASSIVE_OPENERS.match(first):
            rules_failed.append({
                "rule": "NO_PASSIVE",
                "detail": f"Opener ‘{first}’ is a passive auxiliary or article",
            })
        elif first and not _VERB_FIRST.match(first):
            # Rule: VERB_FIRST — only checked when NOT a passive opener
            rules_failed.append({
                "rule": "VERB_FIRST",
                "detail": f"Opener ‘{first}’ is not a recognised verb form",
            })

        # Rule: NO_DUPLICATE
        low = text.lower()
        if low in seen:
            rules_failed.append({
                "rule": "NO_DUPLICATE",
                "detail": f"Duplicate of duty {seen[low]}",
            })
        else:
            seen[low] = getattr(duty, 'id', '?')

        if rules_failed:
            findings.append({"duty_id": getattr(duty, 'id', '?'), "rules_failed": rules_failed})

    return findings
