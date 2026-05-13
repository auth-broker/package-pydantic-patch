"""Pydantic create_model payload aggregation helpers."""

from typing import Annotated, get_origin

from pydantic import BaseModel, create_model

from .computed_field_type_hints import apply_computed_fields_to_payload
from .field_type_hints import apply_model_fields_to_payload
from .orm_type_hints import apply_orm_relationships_to_payload
from .payload_types import CreateModelPayload
from .type_hints import get_resolved_type_hints


def build_payload_from_model(model: type[BaseModel]) -> CreateModelPayload:
    """Build a create_model payload from fields, computed fields, and relationships."""
    payload: CreateModelPayload = {}
    resolved_type_hints = get_resolved_type_hints(model)

    apply_model_fields_to_payload(model, resolved_type_hints, payload)
    apply_computed_fields_to_payload(model, payload)
    apply_orm_relationships_to_payload(model, resolved_type_hints, payload)

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
