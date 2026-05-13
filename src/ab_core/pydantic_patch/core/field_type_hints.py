"""Pydantic model-field type-hint and payload helpers."""

from collections.abc import Iterator
from typing import Annotated, get_origin

from pydantic import BaseModel, Discriminator
from pydantic.fields import FieldInfo, PydanticUndefined

from ab_core.pydantic_patch.core.payload_types import CreateModelPayload
from ab_core.pydantic_patch.core.types import Any


def iter_model_field_infos(
    model: type[BaseModel],
) -> Iterator[tuple[str, FieldInfo]]:
    """Yield concrete pydantic model-field names and metadata."""
    yield from model.model_fields.items()


def clone_field_info(field_info: FieldInfo) -> FieldInfo:
    """Return a shallow copy of FieldInfo suitable for mutation."""
    return field_info._copy()  # pyright: ignore[reportPrivateUsage]


def extract_discriminator_metadata(field_info: FieldInfo) -> tuple[Discriminator, ...]:
    """Return discriminator metadata attached to a field."""
    return tuple(item for item in field_info.metadata if isinstance(item, Discriminator))


def get_model_field_annotation(
    field_name: str,
    field_info: FieldInfo,
    resolved_type_hints: dict[str, object],
) -> Any:
    """Return the resolved annotation for a normal pydantic model field."""
    annotation: Any = resolved_type_hints.get(field_name, field_info.annotation)
    discriminator_metadata = extract_discriminator_metadata(field_info)

    if discriminator_metadata and get_origin(annotation) is not Annotated:
        return Annotated[annotation, *discriminator_metadata]

    return annotation


def create_model_field_info(field_info: FieldInfo) -> FieldInfo:
    """Create the field info to use in a generated payload."""
    field_copy = clone_field_info(field_info)
    field_copy.default = PydanticUndefined if field_info.is_required() else field_info.default
    return field_copy


def apply_model_fields_to_payload(
    model: type[BaseModel],
    resolved_type_hints: dict[str, object],
    payload: CreateModelPayload,
) -> None:
    """Insert normal pydantic model fields into a create_model payload."""
    for field_name, field_info in iter_model_field_infos(model):
        payload[field_name] = (
            get_model_field_annotation(field_name, field_info, resolved_type_hints),
            create_model_field_info(field_info),
        )
