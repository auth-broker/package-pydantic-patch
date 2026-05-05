import pytest
from tests.helpers.assert_model import assert_field_names, assert_optional, assert_required

from ab_core.pydantic_patch.core.errors import ConflictingPatchConfigError
from ab_core.pydantic_patch.patch import PatchConfig, create_patch_model


def test_patch_include_then_exclude(models):
    result = create_patch_model(
        models["User"],
        config=PatchConfig(
            include={"id", "name", "created_at"},
            exclude={"created_at"},
            partial=set(),
        ),
    )
    assert_field_names(result, {"id", "name"})


def test_patch_partial_then_required_required_wins(models):
    result = create_patch_model(
        models["User"],
        config=PatchConfig(partial=None, required={"id"}),
    )
    assert_required(result, "id")
    assert_optional(result, "name")
    assert_optional(result, "email")
    assert_optional(result, "created_at")
    assert_optional(result, "updated_at")


def test_patch_required_field_not_present_after_include_raises(models):
    with pytest.raises(ConflictingPatchConfigError):
        create_patch_model(
            models["User"],
            config=PatchConfig(
                include={"name"},
                required={"id"},
            ),
        )


def test_patch_partial_field_not_present_after_exclude_raises(models):
    with pytest.raises(ConflictingPatchConfigError):
        create_patch_model(
            models["User"],
            config=PatchConfig(
                exclude={"email"},
                partial={"email"},
            ),
        )
