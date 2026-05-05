

import pytest

from ab_core.pydantic_patch.core.errors import InvalidPatchFieldError
from ab_core.pydantic_patch.required import Required, create_required_model
from tests.helpers.assert_model import assert_model_equivalent, assert_optional, assert_required


def test_required_user_id(models, expected_models):
    result = create_required_model(models["User"], fields={"id"})
    assert_model_equivalent(result, expected_models["UserRequiredIdExpected"])


def test_required_fields_none_changes_nothing(models):
    result = create_required_model(models["User"], fields=None)
    assert_optional(result, "id")
    assert_required(result, "name")


def test_required_empty_set_changes_nothing(models):
    result = create_required_model(models["User"], fields=set())
    assert_optional(result, "id")
    assert_required(result, "name")


def test_required_unknown_field_raises(models):
    with pytest.raises(InvalidPatchFieldError):
        create_required_model(models["User"], fields={"does_not_exist"})


def test_required_already_required_field_stays_required(models):
    result = create_required_model(models["User"], fields={"name"})
    assert_required(result, "name")


def test_required_custom_name(models):
    result = create_required_model(models["User"], fields={"id"}, name="UserIdRequired")
    assert result.__name__ == "UserIdRequired"


def test_required_repeated_same_config_returns_same_type(models):
    result_a = create_required_model(models["User"], fields={"id"})
    result_b = create_required_model(models["User"], fields={"id"})
    assert result_a is result_b


def test_required_generic_api(models):
    result = Required[models["User"]](fields={"id"})
    assert_required(result, "id")
