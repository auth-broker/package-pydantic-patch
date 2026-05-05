from __future__ import annotations

from ab_core.pydantic_patch.patch import Patch, PatchConfig, create_patch_model
from tests.helpers.assert_model import assert_field_names, assert_model_equivalent, assert_optional, assert_required


def test_patch_user_include_name_email(models):
    result = create_patch_model(models["User"], config=PatchConfig(include={"name", "email"}, partial=set()))
    assert_field_names(result, {"name", "email"})


def test_patch_user_exclude_audit_fields(models):
    result = create_patch_model(
        models["User"],
        config=PatchConfig(exclude={"created_at", "updated_at"}, partial=set()),
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
            include={"id", "name", "email"},
            partial={"name", "email"},
            required={"id"},
        ),
    )
    assert_model_equivalent(result, expected_models["UserPatchIdNameEmailExpected"])


def test_patch_generic_api(models):
    result = Patch[models["User"]](
        include={"id", "name"},
        partial={"name"},
        required={"id"},
    )
    assert_field_names(result, {"id", "name"})
    assert_required(result, "id")
    assert_optional(result, "name")
