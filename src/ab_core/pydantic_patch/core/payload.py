"""Pydantic create_model payload helpers."""

from typing import Annotated, get_origin

from pydantic import BaseModel, Discriminator, create_model
from pydantic.fields import FieldInfo, PydanticUndefined

from .orm_type_hints import apply_orm_relationship_fields
from .payload_types import CreateModelPayload
from .type_hints import get_resolved_type_hints


def clone_field_info(field_info: FieldInfo) -> FieldInfo:
    """Return a shallow copy of FieldInfo suitable for mutation."""
    return field_info._copy()  # pyright: ignore[reportPrivateUsage]


def _extract_discriminator_metadata(field_info: FieldInfo) -> tuple[Discriminator, ...]:
    return tuple(item for item in field_info.metadata if isinstance(item, Discriminator))


def build_payload_from_model(model: type[BaseModel]) -> CreateModelPayload:
    """Build a create_model payload from model fields and relationships."""
    payload: CreateModelPayload = {}
    type_hints = get_resolved_type_hints(model)

    for field_name, field_info in model.model_fields.items():
        annotation = type_hints.get(field_name, field_info.annotation)
        discriminator_metadata = _extract_discriminator_metadata(field_info)

        if discriminator_metadata and get_origin(annotation) is not Annotated:
            annotation = Annotated[annotation, *discriminator_metadata]

        field_copy = clone_field_info(field_info)

        field_copy.default = PydanticUndefined if field_info.is_required() else field_info.default

        payload[field_name] = (annotation, field_copy)

    apply_orm_relationship_fields(model, type_hints, payload)

    return payload


def create_model_from_payload(
    *,
    source_model: type[BaseModel],
    payload: CreateModelPayload,
    name: str,
) -> type[BaseModel]:
    """Create a pydantic model from a prepared payload definition."""
    created_model = create_model(
        name,
        __base__=BaseModel,
        __module__=source_model.__module__,
        **payload,
    )  # ty:ignore[no-matching-overload]

    for field_name, (annotation, _) in payload.items():
        if get_origin(annotation) is Annotated:
            created_model.model_fields[field_name].annotation = annotation

    return created_model
