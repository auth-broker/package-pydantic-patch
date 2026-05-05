import pytest
from tests.helpers.assert_model import assert_field_names, assert_model_equivalent

from ab_core.pydantic_patch.core.errors import InvalidPatchFieldError
from ab_core.pydantic_patch.omit import Omit, create_omit_model


def test_omit_user_audit_fields(models, expected_models):
    result = create_omit_model(models["User"], fields={"created_at", "updated_at"})
    assert_model_equivalent(result, expected_models["UserOmitAuditExpected"])


def test_omit_fields_none_changes_nothing(models):
    result = create_omit_model(models["User"], fields=None)
    assert_field_names(result, {"id", "name", "email", "created_at", "updated_at"})


def test_omit_empty_set_changes_nothing(models):
    result = create_omit_model(models["User"], fields=set())
    assert_field_names(result, {"id", "name", "email", "created_at", "updated_at"})


def test_omit_unknown_field_raises(models):
    with pytest.raises(InvalidPatchFieldError):
        create_omit_model(models["User"], fields={"does_not_exist"})


def test_omit_custom_name(models):
    result = create_omit_model(models["User"], fields={"created_at"}, name="UserWithoutCreatedAt")
    assert result.__name__ == "UserWithoutCreatedAt"


def test_omit_repeated_same_config_returns_same_type(models):
    result_a = create_omit_model(models["User"], fields={"created_at", "updated_at"})
    result_b = create_omit_model(models["User"], fields={"updated_at", "created_at"})
    assert result_a is result_b


def test_omit_generic_api(models):
    result = Omit[models["User"]](fields={"created_at", "updated_at"})
    assert_field_names(result, {"id", "name", "email"})
