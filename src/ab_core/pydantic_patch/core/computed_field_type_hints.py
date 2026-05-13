"""Computed-field type-hint and payload helpers."""

from collections.abc import Callable, Iterator
from functools import cached_property
from inspect import get_annotations
from typing import cast, get_type_hints

from pydantic import BaseModel, Field
from pydantic.fields import ComputedFieldInfo, FieldInfo, PydanticUndefined

from ab_core.pydantic_patch.core.forward_references import contains_forward_ref
from ab_core.pydantic_patch.core.payload_types import CreateModelPayload
from ab_core.pydantic_patch.core.types import Any


def iter_computed_field_infos(
    model: type[BaseModel],
) -> Iterator[tuple[str, ComputedFieldInfo]]:
    """Yield computed-field names and metadata for a model."""
    yield from model.model_computed_fields.items()


def get_computed_field_getter(
    computed_field_info: ComputedFieldInfo,
) -> Callable[..., object]:
    """Return the underlying getter function for a computed field."""
    wrapped_property = computed_field_info.wrapped_property

    if isinstance(wrapped_property, property):
        if wrapped_property.fget is None:
            raise TypeError("Computed field property does not define a getter.")
        return wrapped_property.fget

    if isinstance(wrapped_property, cached_property):
        return wrapped_property.func

    raise TypeError(
        "Unsupported computed field wrapper type: "
        f"{type(wrapped_property).__name__}."
    )


def get_raw_computed_field_return_annotation(
    computed_field_info: ComputedFieldInfo,
) -> object:
    """Return the raw computed-field return annotation without evaluating strings."""
    if computed_field_info.return_type is not PydanticUndefined:
        return computed_field_info.return_type

    getter = get_computed_field_getter(computed_field_info)
    annotations = get_annotations(getter, eval_str=False)

    return annotations.get("return", PydanticUndefined)


def get_resolved_computed_field_return_annotation(
    computed_field_info: ComputedFieldInfo,
) -> Any:
    """Return the resolved computed-field return annotation for payload generation."""
    if computed_field_info.return_type is not PydanticUndefined:
        return computed_field_info.return_type

    getter = get_computed_field_getter(computed_field_info)
    resolved_annotations = get_type_hints(getter, include_extras=True)

    return resolved_annotations.get("return", Any)


def get_computed_field_return_annotation(
    computed_field_info: ComputedFieldInfo,
) -> Any:
    """Return the computed-field return annotation."""
    return get_resolved_computed_field_return_annotation(computed_field_info)


def computed_field_contains_forward_ref(
    computed_field_info: ComputedFieldInfo,
) -> bool:
    """Return whether a computed field has an unresolved return annotation."""
    return contains_forward_ref(
        get_raw_computed_field_return_annotation(computed_field_info)
    )


def create_computed_field_info(
    computed_field_info: ComputedFieldInfo,
) -> FieldInfo:
    """Create a concrete pydantic field definition from a computed field."""
    return cast(
        FieldInfo,
        Field(
            default=PydanticUndefined,
            alias=computed_field_info.alias,
            title=computed_field_info.title,
            description=computed_field_info.description,
            examples=computed_field_info.examples,
            json_schema_extra=computed_field_info.json_schema_extra,
        ),
    )


def apply_computed_fields_to_payload(
    model: type[BaseModel],
    payload: CreateModelPayload,
) -> None:
    """Insert computed fields into a create_model payload."""
    for field_name, computed_field_info in iter_computed_field_infos(model):
        if field_name in payload:
            continue

        payload[field_name] = (
            get_resolved_computed_field_return_annotation(computed_field_info),
            create_computed_field_info(computed_field_info),
        )
