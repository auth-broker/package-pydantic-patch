from ab_core.pydantic_patch.omit import Omit, create_omit_model
from tests.ab_core.pydantic_patch.conftest_hybrid_properties import HybridPropertyUser
from tests.helpers.assert_model import assert_field_names


def test_omit_can_remove_hybrid_property() -> None:
    result = create_omit_model(HybridPropertyUser, fields={"full_name"})

    assert_field_names(
        result,
        {
            "id",
            "first_name",
            "last_name",
            "age",
            "is_adult",
        },
    )


def test_omit_includes_hybrid_property_when_not_omitted() -> None:
    result = create_omit_model(HybridPropertyUser, fields={"last_name"})

    assert_field_names(
        result,
        {
            "id",
            "first_name",
            "age",
            "full_name",
            "is_adult",
        },
    )


def test_omit_generic_api_can_remove_hybrid_property() -> None:
    result = Omit[HybridPropertyUser](fields={"is_adult"})

    assert_field_names(
        result,
        {
            "id",
            "first_name",
            "last_name",
            "age",
            "full_name",
        },
    )


def test_omit_validates_hybrid_property_from_attributes() -> None:
    result = create_omit_model(
        HybridPropertyUser,
        fields={"last_name", "age"},
    )

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
        "first_name": "Monique",
        "full_name": "Monique Kuhn",
        "is_adult": True,
    }