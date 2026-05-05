import pytest
from pydantic import ValidationError
from tests.helpers.assert_model import assert_field_names, assert_model_equivalent, assert_optional, assert_required

from ab_core.pydantic_patch.patch import Patch, PatchConfig, create_patch_model


def test_patch_user_include_name_email(models):
    result = create_patch_model(models["User"], config=PatchConfig(pick={"name", "email"}, partial=set()))
    assert_field_names(result, {"name", "email"})


def test_patch_user_exclude_audit_fields(models):
    result = create_patch_model(
        models["User"],
        config=PatchConfig(omit={"created_at", "updated_at"}, partial=set()),
    )
    assert_field_names(result, {"id", "name", "email"})


def test_patch_user_partial_name_email(models):
    result = create_patch_model(
        models["User"],
        config=PatchConfig(partial={"name", "email"}),
    )
    assert_optional(result, "name")
    assert_optional(result, "email")
    assert_required(result, "created_at")


def test_patch_user_required_id(models):
    result = create_patch_model(
        models["User"],
        config=PatchConfig(partial=set(), required={"id"}),
    )
    assert_required(result, "id")


def test_patch_user_include_partial_required_expected_model(models, expected_models):
    result = create_patch_model(
        models["User"],
        config=PatchConfig(
            pick={"id", "name", "email"},
            partial={"name", "email"},
            required={"id"},
        ),
    )
    assert_model_equivalent(result, expected_models["UserPatchIdNameEmailExpected"])


def test_patch_generic_api(models):
    result = Patch[models["User"]](
        pick={"id", "name"},
        partial={"name"},
        required={"id"},
    )
    assert_field_names(result, {"id", "name"})
    assert_required(result, "id")
    assert_optional(result, "name")


def test_patch_explicit_partial_only_makes_configured_fields_optional(models):
    User = models["User"]

    result = create_patch_model(
        User,
        config=PatchConfig(
            pick={"id", "name", "email"},
            partial={"name"},
            required={"id"},
        ),
    )

    result.model_validate({"id": 1, "name": "Updated", "email": "a@example.com"})

    with pytest.raises(ValidationError):
        result.model_validate({"id": 1, "name": "Updated"})
