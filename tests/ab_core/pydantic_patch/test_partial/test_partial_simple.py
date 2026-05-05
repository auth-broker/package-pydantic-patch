import pytest
from tests.helpers.assert_model import assert_model_equivalent, assert_optional, assert_required

from ab_core.pydantic_patch.core.errors import InvalidPatchFieldError
from ab_core.pydantic_patch.partial import Partial, create_partial_model


def test_partial_user_no_fields_makes_all_fields_optional(models, expected_models):
    result = create_partial_model(models["User"], fields=None)
    assert_model_equivalent(result, expected_models["UserPartialAllExpected"])


def test_partial_user_specific_field(models, expected_models):
    result = create_partial_model(models["User"], fields={"name"})
    assert_model_equivalent(result, expected_models["UserPartialNameExpected"])


def test_partial_empty_set_makes_no_fields_optional(models):
    result = create_partial_model(models["User"], fields=set())
    assert_required(result, "name")
    assert_required(result, "email")
    assert_optional(result, "id")


def test_partial_unknown_field_raises(models):
    with pytest.raises(InvalidPatchFieldError):
        create_partial_model(models["User"], fields={"does_not_exist"})


def test_partial_optional_id_remains_optional(models):
    result = create_partial_model(models["User"], fields={"name"})
    assert_optional(result, "id")


def test_partial_required_original_field_becomes_optional_when_selected(models):
    result = create_partial_model(models["User"], fields={"email"})
    assert_optional(result, "email")


def test_partial_custom_name(models):
    result = create_partial_model(models["User"], fields={"name"}, name="UserNamePartial")
    assert result.__name__ == "UserNamePartial"


def test_partial_repeated_same_config_returns_same_type(models):
    result_a = create_partial_model(models["User"], fields={"name", "email"})
    result_b = create_partial_model(models["User"], fields={"email", "name"})
    assert result_a is result_b


def test_partial_generic_api(models):
    result = Partial[models["User"]](fields={"name"})
    assert_optional(result, "name")
