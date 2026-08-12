from pydantic_patch.partial import Partial, create_partial_model
from tests.helpers.assert_model import assert_field_names, assert_optional, assert_required
from tests.pydantic_patch.conftest_hybrid_properties import HybridPropertyUser


def test_partial_can_make_hybrid_property_optional() -> None:
    result = create_partial_model(
        HybridPropertyUser,
        fields={"full_name"},
    )

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

    assert_optional(result, "full_name")
    assert_required(result, "first_name")
    assert_required(result, "is_adult")


def test_partial_all_makes_hybrid_properties_optional() -> None:
    result = create_partial_model(HybridPropertyUser, fields=None)

    assert_optional(result, "full_name")
    assert_optional(result, "is_adult")


def test_partial_generic_api_can_make_hybrid_property_optional() -> None:
    result = Partial[HybridPropertyUser](fields={"is_adult"})

    assert_optional(result, "is_adult")
    assert_required(result, "full_name")


def test_partial_validates_optional_hybrid_property_payload() -> None:
    result = create_partial_model(
        HybridPropertyUser,
        fields={"full_name"},
    )

    validated = result.model_validate(
        {
            "first_name": "Monique",
            "last_name": "Kuhn",
            "age": 28,
        }
    )

    assert validated.full_name is None
