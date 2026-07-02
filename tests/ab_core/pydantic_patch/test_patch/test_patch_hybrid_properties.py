import pytest
from pydantic import ValidationError

from ab_core.pydantic_patch.patch import Patch, PatchConfig, create_patch_model
from tests.ab_core.pydantic_patch.conftest_hybrid_properties import HybridPropertyUser
from tests.helpers.assert_model import assert_field_names, assert_optional, assert_required


def test_patch_can_pick_hybrid_property() -> None:
    result = create_patch_model(
        HybridPropertyUser,
        config=PatchConfig(
            pick={"id", "full_name"},
            required={"id"},
        ),
    )

    assert_field_names(result, {"id", "full_name"})
    assert_required(result, "id")
    assert_optional(result, "full_name")


def test_patch_can_require_hybrid_property() -> None:
    result = create_patch_model(
        HybridPropertyUser,
        config=PatchConfig(
            pick={"id", "full_name"},
            required={"id", "full_name"},
        ),
    )

    assert_field_names(result, {"id", "full_name"})
    assert_required(result, "id")
    assert_required(result, "full_name")


def test_patch_can_make_hybrid_property_partial() -> None:
    result = create_patch_model(
        HybridPropertyUser,
        config=PatchConfig(
            pick={"id", "full_name"},
            partial={"full_name"},
            required={"id"},
        ),
    )

    assert_field_names(result, {"id", "full_name"})
    assert_required(result, "id")
    assert_optional(result, "full_name")

    validated = result.model_validate({"id": 1})

    assert validated.id == 1
    assert validated.full_name is None


def test_patch_generic_api_can_pick_hybrid_property() -> None:
    result = Patch[HybridPropertyUser](
        pick={"id", "first_name", "full_name"},
        required={"id"},
    )

    assert_field_names(result, {"id", "first_name", "full_name"})


def test_patch_validates_hybrid_property_from_attributes() -> None:
    result = Patch[HybridPropertyUser](
        pick={"id", "full_name", "is_adult"},
        required={"id", "full_name", "is_adult"},
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
        "full_name": "Monique Kuhn",
        "is_adult": True,
    }


def test_patch_required_hybrid_property_validation_error_when_missing() -> None:
    result = Patch[HybridPropertyUser](
        pick={"id", "full_name"},
        required={"id", "full_name"},
    )

    with pytest.raises(ValidationError):
        result.model_validate({"id": 1})