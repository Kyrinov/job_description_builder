"""
tests/test_jd_ranking.py — Unit tests for app/ai/jd_ranking.py Pydantic models,
DutyRankingResult guardrail logic, OrphanFlag schema, and ProvenanceTag construction.

Wave 0: stubs that skip until app/ai/jd_ranking.py is implemented (Plan 06-02).
"""
from __future__ import annotations

import pytest
from datetime import date


class TestDutySelectionSchema:
    def test_duty_selection_requires_integer_row_id(self):
        try:
            from app.ai.jd_ranking import DutySelection
        except ImportError:
            pytest.skip("app.ai.jd_ranking not yet implemented")
        ds = DutySelection(row_id=42, rank=1, rationale="Most relevant to EC OG")
        assert ds.row_id == 42
        assert isinstance(ds.row_id, int)

    def test_duty_selection_rank_must_be_positive(self):
        try:
            from app.ai.jd_ranking import DutySelection
        except ImportError:
            pytest.skip("app.ai.jd_ranking not yet implemented")
        with pytest.raises(Exception):
            DutySelection(row_id=1, rank=0, rationale="bad rank")

    def test_duty_ranking_result_min_one_selection(self):
        try:
            from app.ai.jd_ranking import DutySelection, DutyRankingResult
        except ImportError:
            pytest.skip("app.ai.jd_ranking not yet implemented")
        result = DutyRankingResult(
            selections=[DutySelection(row_id=1, rank=1, rationale="r")],
            selection_rationale="Selected top 1",
        )
        assert len(result.selections) == 1

    def test_duty_ranking_result_max_15_selections(self):
        try:
            from app.ai.jd_ranking import DutySelection, DutyRankingResult
        except ImportError:
            pytest.skip("app.ai.jd_ranking not yet implemented")
        with pytest.raises(Exception):
            DutyRankingResult(
                selections=[DutySelection(row_id=i, rank=i, rationale="r") for i in range(1, 17)],
                selection_rationale="Too many",
            )

    def test_duty_ranking_result_requires_selection_rationale(self):
        try:
            from app.ai.jd_ranking import DutySelection, DutyRankingResult
        except ImportError:
            pytest.skip("app.ai.jd_ranking not yet implemented")
        with pytest.raises(Exception):
            DutyRankingResult(
                selections=[DutySelection(row_id=1, rank=1, rationale="r")],
            )


class TestGuardrailLogic:
    def test_guardrail_drops_invalid_row_id(self):
        """Row IDs not in the pre-loaded candidate set are dropped before building duties."""
        try:
            from app.ai.jd_ranking import DutySelection, DutyRankingResult
        except ImportError:
            pytest.skip("app.ai.jd_ranking not yet implemented")
        # Simulate: candidates loaded for NOC 21232 have IDs {1, 2, 3}
        # LLM returns {1, 2, 999} — ID 999 is not in candidate set
        candidate_map = {1: "Duty A", 2: "Duty B", 3: "Duty C"}
        selections = [
            DutySelection(row_id=1, rank=1, rationale="Relevant"),
            DutySelection(row_id=999, rank=2, rationale="Invalid ID"),
        ]
        valid = [s for s in selections if s.row_id in candidate_map]
        assert len(valid) == 1
        assert valid[0].row_id == 1

    def test_guardrail_drops_negative_row_id(self):
        """Negative row IDs from LLM are not valid noc_elements IDs."""
        try:
            from app.ai.jd_ranking import DutySelection
        except ImportError:
            pytest.skip("app.ai.jd_ranking not yet implemented")
        candidate_map = {1: "Duty A", 2: "Duty B"}
        selections = [DutySelection(row_id=-1, rank=1, rationale="Negative ID")]
        valid = [s for s in selections if s.row_id in candidate_map]
        assert len(valid) == 0

    def test_guardrail_drops_id_from_wrong_noc(self):
        """IDs from a different NOC code are absent from the candidate_map."""
        try:
            from app.ai.jd_ranking import DutySelection
        except ImportError:
            pytest.skip("app.ai.jd_ranking not yet implemented")
        # candidate_map built from WHERE noc_code='21232' — IDs 1,2,3
        # LLM returns ID 500 which belongs to NOC 41200 — not in map
        candidate_map = {1: "Duty A", 2: "Duty B", 3: "Duty C"}
        selections = [DutySelection(row_id=500, rank=1, rationale="Wrong NOC")]
        valid = [s for s in selections if s.row_id in candidate_map]
        assert len(valid) == 0


class TestProvenanceTagConstruction:
    def test_provenance_tag_fields(self):
        """DraftDuty built from DB row has source_type='NOC', source_id=noc_code, source_version='NOC 2021 v1.0'."""
        try:
            from app.models.work_description import DraftDuty, ProvenanceTag
        except ImportError:
            pytest.skip("app.models.work_description not available")
        duty = DraftDuty(
            text="Design and develop software systems.",
            provenance=ProvenanceTag(
                source_type="NOC",
                source_id="21232",
                source_version="NOC 2021 v1.0",
                retrieved_date=date.today(),
            ),
            advisor_modified=False,
        )
        assert duty.provenance.source_type == "NOC"
        assert duty.provenance.source_id == "21232"
        assert duty.provenance.source_version == "NOC 2021 v1.0"

    def test_advisor_provenance_tag_fields(self):
        """Advisor-added duty has source_type='ADVISOR', source_id='advisor-input'."""
        try:
            from app.models.work_description import DraftDuty, ProvenanceTag
        except ImportError:
            pytest.skip("app.models.work_description not available")
        duty = DraftDuty(
            text="Advises on emerging IT security frameworks.",
            provenance=ProvenanceTag(
                source_type="ADVISOR",
                source_id="advisor-input",
                source_version="advisor-added",
                retrieved_date=date.today(),
            ),
            advisor_modified=False,
        )
        assert duty.provenance.source_type == "ADVISOR"
        assert duty.provenance.source_id == "advisor-input"


class TestOrphanFlagSchema:
    def test_orphan_flag_requires_all_citation_fields(self):
        """OrphanFlag must carry duty_text, rule_violated, source_document, source_section, severity."""
        try:
            from app.ai.jd_ranking import OrphanFlag
        except ImportError:
            pytest.skip("app.ai.jd_ranking not yet implemented")
        flag = OrphanFlag(
            duty_text="Provides HR classification advice to management.",
            rule_violated="administrative support work directed internally to the Public Service",
            source_document="TBS OCHRO OG Definitions",
            source_section="EC — Exclusions",
            severity="hard",
        )
        assert flag.duty_text
        assert flag.rule_violated
        assert flag.source_document
        assert flag.source_section
        assert flag.severity in ("hard", "soft")

    def test_orphan_flag_cites_source(self):
        """OrphanFlag.source_document must be non-empty and source_section must be non-empty."""
        try:
            from app.ai.jd_ranking import OrphanFlag
        except ImportError:
            pytest.skip("app.ai.jd_ranking not yet implemented")
        flag = OrphanFlag(
            duty_text="Processes payroll transactions.",
            rule_violated="not a policy or program function",
            source_document="TBS OCHRO OG Definitions",
            source_section="EC — Exclusions",
            severity="soft",
        )
        assert len(flag.source_document) > 0
        assert len(flag.source_section) > 0

    def test_orphan_check_result_empty_flags_is_valid(self):
        """OrphanCheckResult with empty flags list is valid — not an error (JD-04)."""
        try:
            from app.ai.jd_ranking import OrphanCheckResult
        except ImportError:
            pytest.skip("app.ai.jd_ranking not yet implemented")
        result = OrphanCheckResult(flags=[], summary="No orphan statements detected.")
        assert result.flags == []
        assert result.summary

    def test_orphan_check_result_with_flags(self):
        """OrphanCheckResult with populated flags includes all required fields per flag."""
        try:
            from app.ai.jd_ranking import OrphanFlag, OrphanCheckResult
        except ImportError:
            pytest.skip("app.ai.jd_ranking not yet implemented")
        result = OrphanCheckResult(
            flags=[
                OrphanFlag(
                    duty_text="Provides HR advice to public service employees.",
                    rule_violated="administrative support work directed internally",
                    source_document="TBS OCHRO OG Definitions",
                    source_section="EC — Exclusions",
                    severity="hard",
                )
            ],
            summary="1 duty flagged as potential orphan statement.",
        )
        assert len(result.flags) == 1


class TestJDInstructorClient:
    def test_jd_instructor_client_exists(self):
        try:
            from app.ai.jd_ranking import jd_instructor_client
        except ImportError:
            pytest.skip("app.ai.jd_ranking not yet implemented")
        assert jd_instructor_client is not None

    def test_system_prompt_constants_exist(self):
        try:
            from app.ai.jd_ranking import DUTY_SELECTION_SYSTEM_PROMPT, ORPHAN_CHECK_SYSTEM_PROMPT
        except ImportError:
            pytest.skip("app.ai.jd_ranking not yet implemented")
        assert "row_id" in DUTY_SELECTION_SYSTEM_PROMPT.lower() or "id" in DUTY_SELECTION_SYSTEM_PROMPT.lower()
        assert len(ORPHAN_CHECK_SYSTEM_PROMPT) > 50
