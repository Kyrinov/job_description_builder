from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestNOCCandidateSchema:
    def test_noc_candidate_schema(self):
        """NOCCandidate accepts valid data and rejects non-digit noc_code."""
        try:
            from app.ai.noc_ranking import NOCCandidate
        except ImportError:
            pytest.skip("app.ai.noc_ranking not yet implemented")
        c = NOCCandidate(
            noc_code="21232", title="Software engineers and designers",
            teer=2, rank=1, matched_duties=["Develop software systems."],
            justification="This unit group matches because it covers software development work."
        )
        assert c.noc_code == "21232"
        with pytest.raises(ValidationError):
            NOCCandidate(
                noc_code="ABCDE", title="X", teer=2, rank=1,
                matched_duties=["x"], justification="x" * 30,
            )

    def test_teer_is_integer(self):
        """NOCCandidate.teer accepts 0–5, rejects 6."""
        try:
            from app.ai.noc_ranking import NOCCandidate
        except ImportError:
            pytest.skip("app.ai.noc_ranking not yet implemented")
        c = NOCCandidate(
            noc_code="21232", title="T", teer=0, rank=1,
            matched_duties=["d"], justification="x" * 30,
        )
        assert c.teer == 0
        with pytest.raises(ValidationError):
            NOCCandidate(
                noc_code="21232", title="T", teer=6, rank=1,
                matched_duties=["d"], justification="x" * 30,
            )

    def test_duties_not_blank(self):
        """matched_duties must not contain blank strings."""
        try:
            from app.ai.noc_ranking import NOCCandidate
        except ImportError:
            pytest.skip("app.ai.noc_ranking not yet implemented")
        with pytest.raises(ValidationError):
            NOCCandidate(
                noc_code="21232", title="T", teer=2, rank=1,
                matched_duties=["valid duty", ""],
                justification="x" * 30,
            )

    def test_ranks_are_sequential(self):
        """NOCRankingResult rejects non-sequential ranks (gap: [1,3]) and accepts [1,2]."""
        try:
            from app.ai.noc_ranking import NOCCandidate, NOCRankingResult
        except ImportError:
            pytest.skip("app.ai.noc_ranking not yet implemented")

        def make_candidate(rank: int) -> NOCCandidate:
            return NOCCandidate(
                noc_code="21232", title="T", teer=2, rank=rank,
                matched_duties=["d"], justification="x" * 30,
            )

        # valid sequential ranks
        NOCRankingResult(candidates=[make_candidate(1), make_candidate(2)])
        # gap in ranks — must raise
        with pytest.raises(ValidationError):
            NOCRankingResult(candidates=[make_candidate(1), make_candidate(3)])

    def test_instructor_client_mode_json(self):
        """instructor_client singleton exists and is not None."""
        try:
            from app.ai.noc_ranking import instructor_client
        except ImportError:
            pytest.skip("app.ai.noc_ranking not yet implemented")
        assert instructor_client is not None
