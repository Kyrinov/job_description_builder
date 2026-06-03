"""
test_models.py — contract for the 5 Pydantic v2 models.

Wave 0 stubs: fail because app.models does not exist.
After Plan 02, all 5 instantiations must pass.
"""
import pytest
from datetime import datetime, timezone


def test_work_description_instantiation():
    from app.models import WorkDescription  # Wave 0: ImportError
    wd = WorkDescription(
        id="wd-1",
        record={"title": "Environmental Officer"},
        answers={},
        created_at=datetime.now(timezone.utc),
        last_modified=datetime.now(timezone.utc),
    )
    assert wd.id == "wd-1"
    assert wd.title == ""
    assert wd.step_index == 0
    assert wd.reviewing is False


def test_draft_duty_instantiation():
    from app.models import DraftDuty
    d = DraftDuty(
        id="duty-1",
        text="Plans environmental remediation projects.",
        source="advisor",
    )
    assert d.source == "advisor"
    assert d.plain_trigger is None


def test_classification_instantiation():
    from app.models import Classification
    c = Classification(
        work_type="EC",
        work_type_name="Economics and Social Science Services",
        applicable_standard="EC JES 2017",
    )
    assert c.code is None
    assert c.work_type == "EC"


def test_jes_factor_instantiation():
    from app.models import JESFactor
    f = JESFactor(
        name="Decision making",
        degree=4,
        points=60,
        category="Responsibility",
    )
    assert f.degree == 4
    assert f.category == "Responsibility"


def test_qualification_standard_instantiation():
    from app.models import QualificationStandard
    q = QualificationStandard(
        education="Degree in environmental science.",
        experience="Significant experience in policy analysis.",
        source="EC-05 default",
        last_modified=datetime.now(timezone.utc),
    )
    assert "environmental" in q.education
    assert q.source == "EC-05 default"
