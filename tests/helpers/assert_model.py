from __future__ import annotations

from typing import Any, get_args, get_origin

from deepdiff import DeepDiff
from pydantic import BaseModel


def assert_model_equivalent(
    actual: type[BaseModel],
    expected: type[BaseModel],
    *,
    ignore_title: bool = True,
) -> None:
    assert actual.model_fields.keys() == expected.model_fields.keys()

    for field_name, expected_field in expected.model_fields.items():
        actual_field = actual.model_fields[field_name]
        assert actual_field.annotation == expected_field.annotation, field_name
        assert actual_field.is_required() == expected_field.is_required(), field_name
        assert actual_field.default == expected_field.default, field_name

    actual_schema = actual.model_json_schema()
    expected_schema = expected.model_json_schema()

    exclude_regex_paths = []
    if ignore_title:
        exclude_regex_paths.extend([
            r"root\['title'\]",
            r"root\['\$defs'\]\['.*'\]\['title'\]",
        ])

    diff = DeepDiff(
        expected_schema,
        actual_schema,
        ignore_order=True,
        exclude_regex_paths=exclude_regex_paths,
    )

    assert diff == {}


def assert_field_names(model: type[BaseModel], expected: set[str]) -> None:
    assert set(model.model_fields) == expected


def assert_required(model: type[BaseModel], field_name: str) -> None:
    assert model.model_fields[field_name].is_required(), field_name


def assert_optional(model: type[BaseModel], field_name: str) -> None:
    assert not model.model_fields[field_name].is_required(), field_name


def get_list_item_type(annotation: Any) -> Any:
    assert get_origin(annotation) is list
    return get_args(annotation)[0]


def get_dict_value_type(annotation: Any) -> Any:
    assert get_origin(annotation) is dict
    return get_args(annotation)[1]


def assert_same_annotation_object(actual: Any, expected: Any) -> None:
    assert actual is expected
