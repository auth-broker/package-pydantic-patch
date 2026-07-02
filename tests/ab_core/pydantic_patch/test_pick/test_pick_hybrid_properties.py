from sqlalchemy import select

from ab_core.pydantic_patch.pick import Pick, create_pick_model
from tests.ab_core.pydantic_patch.conftest_hybrid_properties import HybridPropertyUser
from tests.helpers.assert_model import assert_field_names, assert_required


def test_pick_can_select_hybrid_property() -> None:
    result = create_pick_model(HybridPropertyUser, fields={"full_name"})

    assert_field_names(result, {"full_name"})
    assert_required(result, "full_name")

    validated = result.model_validate({"full_name": "Monique Kuhn"})

    assert validated.full_name == "Monique Kuhn"


def test_pick_generic_api_can_select_hybrid_property() -> None:
    result = Pick[HybridPropertyUser](fields={"first_name", "full_name"})

    assert_field_names(result, {"first_name", "full_name"})


def test_pick_fields_none_includes_hybrid_properties() -> None:
    result = create_pick_model(HybridPropertyUser, fields=None)

    assert_field_names(
        result,
        {
            "id",
            "first_name",
            "last_name",
            "age",
            "full_name",
            "is_adult",
        },
    )


def test_pick_validates_hybrid_property_from_attributes() -> None:
    result = Pick[HybridPropertyUser](fields={"id", "full_name", "is_adult"})

    validated = result.model_validate(
        HybridPropertyUser(
            id=1,
            first_name="Monique",
            last_name="Kuhn",
            age=28,
        )
    )

    assert validated.model_dump() == {
        "id": 1,
        "full_name": "Monique Kuhn",
        "is_adult": True,
    }


def test_pick_preserves_hybrid_property_sql_expression() -> None:
    result = Pick[HybridPropertyUser](fields={"full_name", "is_adult"})

    assert result.model_fields["full_name"].annotation is str
    assert result.model_fields["is_adult"].annotation is bool

    statement = select(HybridPropertyUser).where(
        HybridPropertyUser.is_adult == True  # noqa: E712
    )

    assert "hybrid_property_user.age" in str(statement)