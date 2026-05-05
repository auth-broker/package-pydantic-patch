import pytest
from tests.helpers.assert_model import assert_field_names, assert_model_equivalent

from ab_core.pydantic_patch.core.errors import InvalidPatchFieldError
from ab_core.pydantic_patch.pick import Pick, create_pick_model


@pytest.mark.parametrize(
    ("fields", "expected_key"),
    [
        ({"name", "email"}, "UserNameEmailPickExpected"),
        (set(), "UserEmptyPickExpected"),
    ],
)
def test_pick_user_fields(models, expected_models, fields, expected_key):
    result = create_pick_model(models["User"], fields=fields)
    assert_model_equivalent(result, expected_models[expected_key])


def test_pick_fields_none_keeps_all_fields(models):
    result = create_pick_model(models["User"], fields=None)
    assert_field_names(result, {"id", "name", "email", "created_at", "updated_at"})


def test_pick_unknown_field_raises(models):
    with pytest.raises(InvalidPatchFieldError):
        create_pick_model(models["User"], fields={"does_not_exist"})


def test_pick_custom_name(models):
    result = create_pick_model(models["User"], fields={"name"}, name="UserNameOnlyInput")
    assert result.__name__ == "UserNameOnlyInput"


def test_pick_repeated_same_config_returns_same_type(models):
    result_a = create_pick_model(models["User"], fields={"name", "email"})
    result_b = create_pick_model(models["User"], fields={"email", "name"})
    assert result_a is result_b


def test_pick_generic_api(models):
    result = Pick[models["User"]](fields={"name", "email"})
    assert_field_names(result, {"name", "email"})
