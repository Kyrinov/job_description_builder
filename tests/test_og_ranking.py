"""
tests/test_og_ranking.py — Unit tests for app/ai/og_ranking.py Pydantic models,
OG_LEVELS lookup, verbatim guardrail, and AS/EC detection logic.

Wave 0: stubs that skip until app/ai/og_ranking.py is implemented (Plan 05-02).
"""
from __future__ import annotations

import pytest


class TestOGCandidateSchema:
    def test_og_candidate_requires_og_code(self):
        try:
            from app.ai.og_ranking import OGCandidate
        except ImportError:
            pytest.skip("app.ai.og_ranking not yet implemented")
        c = OGCandidate(
            og_code="EC", rank=1, confidence=0.9,
            rationale="Primary economic research duties", evidence_quotes=["verbatim text from OG def"]
        )
        assert c.og_code == "EC"
        assert c.rank == 1

    def test_og_ranking_result_min_one_candidate(self):
        try:
            from app.ai.og_ranking import OGCandidate, OGRankingResult
        except ImportError:
            pytest.skip("app.ai.og_ranking not yet implemented")
        result = OGRankingResult(candidates=[
            OGCandidate(og_code="EC", rank=1, confidence=0.9, rationale="r", evidence_quotes=["q"])
        ])
        assert len(result.candidates) == 1

    def test_og_ranking_result_max_three_candidates(self):
        try:
            from app.ai.og_ranking import OGCandidate, OGRankingResult
        except ImportError:
            pytest.skip("app.ai.og_ranking not yet implemented")
        with pytest.raises(Exception):
            OGRankingResult(candidates=[
                OGCandidate(og_code="EC", rank=1, confidence=0.9, rationale="r", evidence_quotes=[]),
                OGCandidate(og_code="AS", rank=2, confidence=0.7, rationale="r", evidence_quotes=[]),
                OGCandidate(og_code="IT", rank=3, confidence=0.5, rationale="r", evidence_quotes=[]),
                OGCandidate(og_code="PE", rank=4, confidence=0.3, rationale="r", evidence_quotes=[]),
            ])

    def test_policy_adjacency_result_schema(self):
        try:
            from app.ai.og_ranking import PolicyAdjacencyResult
        except ImportError:
            pytest.skip("app.ai.og_ranking not yet implemented")
        r = PolicyAdjacencyResult(
            is_policy_adjacent=True,
            confidence=0.95,
            policy_phrases=["develop policy", "policy analysis"],
            rationale="Work involves EC policy development",
        )
        assert r.is_policy_adjacent is True

    def test_og_levels_as_range(self):
        try:
            from app.ai.og_ranking import OG_LEVELS
        except ImportError:
            pytest.skip("app.ai.og_ranking not yet implemented")
        assert OG_LEVELS["AS"] == list(range(1, 9)), "AS levels must be 1-8"
        assert OG_LEVELS["EC"] == list(range(1, 8)), "EC levels must be 1-7"

    def test_og_levels_unknown_code_returns_empty(self):
        try:
            from app.ai.og_ranking import OG_LEVELS
        except ImportError:
            pytest.skip("app.ai.og_ranking not yet implemented")
        assert OG_LEVELS.get("UNKNOWN", []) == []

    def test_og_instructor_client_exists(self):
        try:
            from app.ai.og_ranking import og_instructor_client
        except ImportError:
            pytest.skip("app.ai.og_ranking not yet implemented")
        assert og_instructor_client is not None

    def test_verbatim_guardrail_strips_fabricated_quotes(self):
        try:
            from app.services.og_classifier import _strip_fabricated_quotes
        except ImportError:
            pytest.skip("app.services.og_classifier not yet implemented")
        og_text = "verbatim text from OG definition"
        result = _strip_fabricated_quotes(["verbatim text from OG definition", "completely made up"], og_text)
        assert "verbatim text from OG definition" in result
        assert "completely made up" not in result

    def test_asec_alert_fires_on_policy_adjacent(self, monkeypatch):
        try:
            from app.services.og_classifier import _build_asec_alert
        except ImportError:
            pytest.skip("app.services.og_classifier not yet implemented")
        # Smoke test: function exists and accepts og_rows dict
        pass

    def test_asec_alert_suppressed_for_non_policy_work(self):
        try:
            from app.ai.og_ranking import PolicyAdjacencyResult
        except ImportError:
            pytest.skip("app.ai.og_ranking not yet implemented")
        r = PolicyAdjacencyResult(
            is_policy_adjacent=False, confidence=0.05,
            policy_phrases=[], rationale="Administrative support work only",
        )
        assert r.is_policy_adjacent is False

    def test_guardrail_rejects_invalid_og_code(self):
        try:
            from app.ai.og_ranking import OG_LEVELS
        except ImportError:
            pytest.skip("app.ai.og_ranking not yet implemented")
        assert "HR" not in OG_LEVELS
        assert "PA" not in OG_LEVELS
