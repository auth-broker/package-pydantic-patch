"""Pydantic create_model payload helpers."""

from typing import get_args, get_origin

from pydantic import BaseModel, Field

from ab_core.pydantic_patch.core.types import Any

from .payload_types import CreateModelPayload


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


def apply_orm_relationship_fields(
    model: type[BaseModel],
    type_hints: dict[str, Any],
    payload: CreateModelPayload,
) -> None:
    """Insert SQLModel relationship fields into the payload when they are omitted."""
    # we don't create a strict dependenct on sqlmodel, since we can extract relationship via the annotation
    relationship_names = getattr(model, "__sqlmodel_relationships__", {})

    for relationship_name in relationship_names:
        if relationship_name in payload:
            continue
        payload[relationship_name] = (
            unwrap_sqlalchemy_mapped(type_hints[relationship_name]),
            Field(default=None),
        )
