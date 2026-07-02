import pytest
from pydantic import ValidationError

from ab_core.pydantic_patch.partial import create_partial_model
from ab_core.pydantic_patch.required import Required, create_required_model
from tests.ab_core.pydantic_patch.conftest_hybrid_properties import HybridPropertyUser
from tests.helpers.assert_model import assert_optional, assert_required


def test_required_can_make_hybrid_property_required() -> None:
    partial = create_partial_model(HybridPropertyUser, fields=None)

    result = create_required_model(
        partial,
        fields={"full_name"},
    )

    assert_required(result, "full_name")
    assert_optional(result, "is_adult")


def test_required_generic_api_can_make_hybrid_property_required() -> None:
    partial = create_partial_model(HybridPropertyUser, fields=None)

    result = Required[partial](fields={"is_adult"})

    assert_required(result, "is_adult")
    assert_optional(result, "full_name")


def test_required_hybrid_property_validation_error_when_missing() -> None:
    partial = create_partial_model(HybridPropertyUser, fields=None)

    result = create_required_model(
        partial,
        fields={"full_name"},
    )

    with pytest.raises(ValidationError):
        result.model_validate(
            {
                "id": 1,
                "first_name": "Monique",
                "last_name": "Kuhn",
                "age": 28,
            }
        )


def test_required_validates_required_hybrid_property_payload() -> None:
    partial = create_partial_model(HybridPropertyUser, fields=None)

    result = create_required_model(
        partial,
        fields={"full_name"},
    )

    validated = result.model_validate(
        {
            "id": 1,
            "first_name": "Monique",
            "last_name": "Kuhn",
            "age": 28,
            "full_name": "Monique Kuhn",
        }
    )

    assert validated.full_name == "Monique Kuhn"