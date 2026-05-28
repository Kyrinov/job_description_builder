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
