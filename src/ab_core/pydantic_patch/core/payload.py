"""Pydantic create_model payload helpers."""

from typing import Annotated, Any, get_origin

from pydantic import BaseModel, Discriminator, create_model
from pydantic.fields import FieldInfo, PydanticUndefined

CreateModelPayload = dict[str, tuple[Any, Any]]


def clone_field_info(field_info: FieldInfo) -> FieldInfo:
    """Create a best-effort copy of FieldInfo metadata for generated models.

    Keeping FieldInfo as the default preserves aliases, descriptions, validation
    metadata, discriminators on fields, etc. The annotation is supplied separately
    in the create_model payload.
    """
    return field_info._copy()  # pyright: ignore[reportPrivateUsage]


def _extract_discriminator_metadata(field_info: FieldInfo) -> tuple[Any, ...]:
    return tuple(item for item in field_info.metadata if isinstance(item, Discriminator))


def build_payload_from_model(model: type[BaseModel]) -> CreateModelPayload:
    payload: CreateModelPayload = {}

    for field_name, field_info in model.model_fields.items():
        annotation = field_info.annotation
        discriminator_metadata = _extract_discriminator_metadata(field_info)

        if discriminator_metadata:
            annotation = Annotated[annotation, *discriminator_metadata]

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
    created_model = create_model(
        name,
        __base__=BaseModel,
        __module__=source_model.__module__,
        **payload,
    )

    for field_name, (annotation, _) in payload.items():
        if get_origin(annotation) is Annotated:
            created_model.model_fields[field_name].annotation = annotation

    return created_model
