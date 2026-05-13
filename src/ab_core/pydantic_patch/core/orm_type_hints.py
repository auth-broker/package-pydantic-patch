"""SQLModel relationship type-hint and payload helpers."""

from collections.abc import Iterator
from typing import get_args, get_origin

from pydantic import BaseModel, Field

from ab_core.pydantic_patch.core.types import Any

from .payload_types import CreateModelPayload


def iter_orm_relationship_names(model: type[BaseModel]) -> Iterator[str]:
    """Yield SQLModel relationship field names for a model."""
    yield from getattr(model, "__sqlmodel_relationships__", {})


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


def get_orm_relationship_annotation(
    relationship_name: str,
    resolved_type_hints: dict[str, Any],
) -> object:
    """Return the resolved annotation for a SQLModel relationship."""
    return unwrap_sqlalchemy_mapped(resolved_type_hints[relationship_name])


def apply_orm_relationships_to_payload(
    model: type[BaseModel],
    resolved_type_hints: dict[str, Any],
    payload: CreateModelPayload,
) -> None:
    """Insert SQLModel relationship fields into a create_model payload."""
    for relationship_name in iter_orm_relationship_names(model):
        if relationship_name in payload:
            continue

        payload[relationship_name] = (
            get_orm_relationship_annotation(relationship_name, resolved_type_hints),
            Field(default=None),
        )
