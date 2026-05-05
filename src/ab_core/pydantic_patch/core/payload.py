"""Pydantic create_model payload helpers."""

from typing import Annotated, get_args, get_origin, get_type_hints

from pydantic import BaseModel, Discriminator, Field, create_model
from pydantic.fields import FieldInfo, PydanticUndefined

from ab_core.pydantic_patch.core.types import Any

type CreateModelField = tuple[Any, object]
type CreateModelPayload = dict[str, CreateModelField]


def unwrap_sqlalchemy_mapped(annotation: object) -> object:
    """Unwrap SQLAlchemy Mapped[T] annotations to T when present."""
    origin = get_origin(annotation)

    if origin is None:
        return annotation

    if getattr(origin, "__name__", None) == "Mapped":
        mapped_args = get_args(annotation)
        if len(mapped_args) == 1:
            return mapped_args[0]

    return annotation


def clone_field_info(field_info: FieldInfo) -> FieldInfo:
    """Return a shallow copy of FieldInfo suitable for mutation."""
    return field_info._copy()  # pyright: ignore[reportPrivateUsage]


def _extract_discriminator_metadata(field_info: FieldInfo) -> tuple[Discriminator, ...]:
    return tuple(item for item in field_info.metadata if isinstance(item, Discriminator))


def build_payload_from_model(model: type[BaseModel]) -> CreateModelPayload:
    """Build a create_model payload from model fields and relationships."""
    payload: CreateModelPayload = {}

    for field_name, field_info in model.model_fields.items():
        annotation = field_info.annotation
        discriminator_metadata = _extract_discriminator_metadata(field_info)

        if discriminator_metadata:
            annotation = Annotated[annotation, *discriminator_metadata]

        field_copy = clone_field_info(field_info)

        field_copy.default = PydanticUndefined if field_info.is_required() else field_info.default

        payload[field_name] = (annotation, field_copy)

    type_hints = get_type_hints(model, include_extras=True)
    relationship_names = getattr(model, "__sqlmodel_relationships__", {})

    for relationship_name in relationship_names:
        if relationship_name in payload:
            continue

        payload[relationship_name] = (
            unwrap_sqlalchemy_mapped(type_hints[relationship_name]),
            Field(default=None),
        )

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
