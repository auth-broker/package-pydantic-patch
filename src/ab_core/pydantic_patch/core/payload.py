"""Pydantic create_model payload aggregation helpers."""

from typing import Annotated, get_origin

from pydantic import BaseModel, ConfigDict, create_model, model_validator
from pydantic.fields import FieldInfo, PydanticUndefined

from .computed_field_type_hints import apply_computed_fields_to_payload
from .field_type_hints import apply_model_fields_to_payload
from .hybrid_property_type_hints import apply_hybrid_properties_to_payload, iter_hybrid_property_infos
from .orm_type_hints import apply_orm_relationships_to_payload
from .payload_types import CreateModelPayload
from .type_hints import get_resolved_type_hints


def build_payload_from_model(model: type[BaseModel]) -> CreateModelPayload:
    """Build a create_model payload from fields, computed fields, and relationships."""
    payload: CreateModelPayload = {}
    resolved_type_hints = get_resolved_type_hints(model)

    apply_model_fields_to_payload(model, resolved_type_hints, payload)
    apply_computed_fields_to_payload(model, payload)
    apply_hybrid_properties_to_payload(model, payload)
    apply_orm_relationships_to_payload(model, resolved_type_hints, payload)

    return payload


def field_definition_is_required(default: object) -> bool:
    """Return whether a create_model field default represents a required field."""
    if isinstance(default, FieldInfo):
        return default.is_required()

    return default is ... or default is PydanticUndefined


def get_required_hybrid_property_names(
    source_model: type[BaseModel],
    payload: CreateModelPayload,
) -> tuple[str, ...]:
    """Return hybrid properties still required in the final payload."""
    return tuple(
        field_name
        for field_name, _hybrid_property_info in iter_hybrid_property_infos(source_model)
        if field_name in payload and field_definition_is_required(payload[field_name][1])
    )


def build_hybrid_property_validator(
    source_model: type[BaseModel],
    hybrid_property_names: tuple[str, ...],
):
    """Build a pre-validator that derives missing required hybrid properties."""

    @model_validator(mode="before")
    @classmethod
    def populate_required_hybrid_properties(_cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        missing_fields = tuple(field_name for field_name in hybrid_property_names if field_name not in value)
        if not missing_fields:
            return value

        try:
            source_instance = source_model.model_validate(value)
        except Exception:
            return value

        return {
            **value,
            **{field_name: getattr(source_instance, field_name) for field_name in missing_fields},
        }

    return populate_required_hybrid_properties


def create_model_from_payload(
    *,
    source_model: type[BaseModel],
    payload: CreateModelPayload,
    name: str,
) -> type[BaseModel]:
    """Create a pydantic model from a prepared payload definition."""
    required_hybrid_property_names = get_required_hybrid_property_names(source_model, payload)
    validators = {}

    if required_hybrid_property_names:
        validators["populate_required_hybrid_properties"] = build_hybrid_property_validator(
            source_model,
            required_hybrid_property_names,
        )

    created_model = create_model(
        name,
        __base__=BaseModel,
        __config__=ConfigDict(from_attributes=True),
        __module__=source_model.__module__,
        __validators__=validators,
        **payload,
    )  # ty:ignore[no-matching-overload]

    for field_name, (annotation, _) in payload.items():
        if get_origin(annotation) is Annotated:
            created_model.model_fields[field_name].annotation = annotation

    return created_model
