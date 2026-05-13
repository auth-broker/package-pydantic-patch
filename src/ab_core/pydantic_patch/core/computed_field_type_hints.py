"""Computed-field type-hint and payload helpers."""

from collections.abc import Iterator
from typing import cast

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



def get_computed_field_return_annotation(
    computed_field_info: ComputedFieldInfo,
) -> Any:
    """Return the computed-field return annotation."""
    if computed_field_info.return_type is PydanticUndefined:
        return Any

    return computed_field_info.return_type



def computed_field_contains_forward_ref(
    computed_field_info: ComputedFieldInfo,
) -> bool:
    """Return whether a computed field has an unresolved return annotation."""
    return contains_forward_ref(
        get_computed_field_return_annotation(computed_field_info)
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
            get_computed_field_return_annotation(computed_field_info),
            create_computed_field_info(computed_field_info),
        )
