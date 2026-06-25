"""Unit tests for WorkDescription and ProvenanceTag Pydantic models (DATA-01)."""
import pytest
from datetime import date
from uuid import UUID


def test_provenance_tag_instantiation():
    """ProvenanceTag must instantiate with required fields."""
    from app.models.work_description import ProvenanceTag
    tag = ProvenanceTag(
        source_type="NOC",
        source_id="21232",
        source_version="NOC 2021",
        retrieved_date=date.today(),
    )
    assert tag.source_type == "NOC"
    assert tag.source_id == "21232"
    assert tag.modified_by_advisor is False


def test_provenance_tag_required_fields():
    """ProvenanceTag raises ValidationError if source_type, source_id, source_version, or retrieved_date is missing."""
    import pydantic
    from app.models.work_description import ProvenanceTag
    with pytest.raises(pydantic.ValidationError):
        ProvenanceTag(source_type="NOC")


def test_draft_duty_has_provenance():
    """DraftDuty must carry a ProvenanceTag — the provenance field is required."""
    import pydantic
    from app.models.work_description import DraftDuty
    with pytest.raises(pydantic.ValidationError):
        DraftDuty(text="Analyzes policy options")


def test_og_recommendation_has_provenance():
    """OGRecommendation must directly carry a ProvenanceTag."""
    import pydantic
    from app.models.work_description import OGRecommendation
    with pytest.raises(pydantic.ValidationError):
        OGRecommendation(
            og_code="EC",
            og_name="Economics and Social Science Services",
            confidence=0.8,
            rationale="Policy analysis duties align to EC.",
        )


def test_work_description_instantiation():
    """WorkDescription instantiates with only the required raw_input and session_id fields."""
    from app.models.work_description import WorkDescription
    wd = WorkDescription(raw_input="Manages the finance team.", session_id="sess-001")
    assert wd.raw_input == "Manages the finance team."
    assert wd.session_id == "sess-001"
    assert wd.stage == "input"
    assert isinstance(wd.id, UUID)
    assert wd.schema_version == 1


def test_work_description_tbs_fields_present():
    """WorkDescription must have all TBS-required WD header fields (even if None at init)."""
    from app.models.work_description import WorkDescription
    wd = WorkDescription(raw_input="x", session_id="s")
    assert hasattr(wd, "position_title")
    assert hasattr(wd, "position_number")
    assert hasattr(wd, "og_level")
    assert hasattr(wd, "supervisor_title")
    assert hasattr(wd, "supervisor_position_number")
    assert hasattr(wd, "review_date")
    assert hasattr(wd, "organizational_context")


def test_provenance_tag_source_types_exhaustive():
    """ProvenanceTag source_type literal must include all required variants."""
    from app.models.work_description import ProvenanceTag
    import typing
    hints = typing.get_type_hints(ProvenanceTag)
    args = hints["source_type"].__args__
    required_types = {"NOC", "CA", "JES", "TBS_OG_DEF", "TBS_DIRECTIVE", "QUAL_STD", "DRF", "ADVISOR", "AI_GENERATED"}
    assert required_types.issubset(set(args)), f"Missing source types: {required_types - set(args)}"


def test_work_description_dnd_fields_defaults():
    """WorkDescription has is_dnd_position (default False) and drf_linkages (default [])."""
    from app.models.work_description import WorkDescription
    wd = WorkDescription(raw_input="test", session_id="sess-drf")
    assert wd.is_dnd_position is False
    assert wd.drf_linkages == []


def test_work_description_dnd_fields_settable():
    """WorkDescription.is_dnd_position and drf_linkages can be set by the advisor."""
    from app.models.work_description import WorkDescription
    wd = WorkDescription(
        raw_input="test",
        session_id="sess-drf-set",
        is_dnd_position=True,
        drf_linkages=[
            {
                "core_responsibility": "Readiness",
                "departmental_result": "Canada is prepared to defend itself",
                "fiscal_year": "2024-2025",
                "row_index": 0,
                "confirmed": True,
                "provenance_source_id": "42",
            }
        ],
    )
    assert wd.is_dnd_position is True
    assert len(wd.drf_linkages) == 1
    link = wd.drf_linkages[0]
    assert link["core_responsibility"] == "Readiness"
    assert link["departmental_result"] == "Canada is prepared to defend itself"
    assert link["fiscal_year"] == "2024-2025"
    assert link["row_index"] == 0
    assert link["confirmed"] is True
    assert link["provenance_source_id"] == "42"
