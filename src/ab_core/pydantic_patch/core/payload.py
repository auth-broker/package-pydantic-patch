"""Pydantic create_model payload helpers."""



from typing import Any

from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo, PydanticUndefined

CreateModelPayload = dict[str, tuple[Any, Any]]


def clone_field_info(field_info: FieldInfo) -> FieldInfo:
    """Create a best-effort copy of FieldInfo metadata for generated models.

    Keeping FieldInfo as the default preserves aliases, descriptions, validation
    metadata, discriminators on fields, etc. The annotation is supplied separately
    in the create_model payload.
    """
    return field_info._copy()  # pyright: ignore[reportPrivateUsage]


def build_payload_from_model(model: type[BaseModel]) -> CreateModelPayload:
    """Build a pydantic.create_model payload from a BaseModel class."""
    payload: CreateModelPayload = {}

    for field_name, field_info in model.model_fields.items():
        annotation = field_info.annotation
        field_copy = clone_field_info(field_info)

        if field_info.is_required():
            field_copy.default = PydanticUndefined
        else:
            field_copy.default = field_info.default

        payload[field_name] = (annotation, field_copy)

    return payload


def create_model_from_payload(
    *,
    source_model: type[BaseModel],
    payload: CreateModelPayload,
    name: str,
) -> type[BaseModel]:
    """Create a Pydantic model from a create_model payload."""
    return create_model(
        name,
        __base__=BaseModel,
        __module__=source_model.__module__,
        **payload,
    )
