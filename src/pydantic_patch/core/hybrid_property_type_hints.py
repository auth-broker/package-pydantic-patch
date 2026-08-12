"""SQLAlchemy hybrid-property type-hint and payload helpers."""

from collections.abc import Iterator
from inspect import get_annotations
from typing import TYPE_CHECKING, get_type_hints

from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo, PydanticUndefined

from pydantic_patch.core.forward_references import (
    build_model_namespace,
    contains_forward_ref,
)
from pydantic_patch.core.payload_types import CreateModelPayload
from pydantic_patch.core.types import Any

if TYPE_CHECKING:
    from sqlalchemy.ext.hybrid import hybrid_property


def _get_hybrid_property_type() -> type | None:
    try:
        from sqlalchemy.ext.hybrid import hybrid_property
    except ImportError:
        return None

    return hybrid_property


def iter_hybrid_property_infos(
    model: type[BaseModel],
) -> Iterator[tuple[str, "hybrid_property"]]:
    """Yield SQLAlchemy hybrid-property names and descriptors for a model."""
    hybrid_property_type = _get_hybrid_property_type()
    if hybrid_property_type is None:
        return

    for base in reversed(model.__mro__):
        for field_name, value in vars(base).items():
            if isinstance(value, hybrid_property_type):
                yield field_name, value


def get_raw_hybrid_property_return_annotation(
    hybrid_property_info: "hybrid_property",
) -> object:
    """Return the raw hybrid-property return annotation without evaluating strings."""
    annotations = get_annotations(hybrid_property_info.fget, eval_str=False)

    return annotations.get("return", PydanticUndefined)


def get_resolved_hybrid_property_return_annotation(
    model: type[BaseModel],
    hybrid_property_info: "hybrid_property",
) -> Any:
    """Return the resolved hybrid-property return annotation for payload generation."""
    getter = hybrid_property_info.fget

    globalns = getattr(getter, "__globals__", {})
    localns = {
        **globalns,
        **build_model_namespace(model),
        model.__name__: model,
    }

    resolved_annotations = get_type_hints(
        getter,
        globalns=globalns,
        localns=localns,
        include_extras=True,
    )

    return resolved_annotations.get("return", Any)


def hybrid_property_contains_forward_ref(
    model: type[BaseModel],
    hybrid_property_info: "hybrid_property",
) -> bool:
    """Return whether a hybrid property has an unresolved return annotation."""
    raw_annotation = get_raw_hybrid_property_return_annotation(hybrid_property_info)

    if not contains_forward_ref(raw_annotation):
        return False

    try:
        get_resolved_hybrid_property_return_annotation(model, hybrid_property_info)
    except NameError:
        return True

    return False


def create_hybrid_property_field_info() -> FieldInfo:
    """Create a concrete pydantic field definition from a hybrid property."""
    return Field(default=PydanticUndefined)


def apply_hybrid_properties_to_payload(
    model: type[BaseModel],
    payload: CreateModelPayload,
) -> None:
    """Insert SQLAlchemy hybrid properties into a create_model payload."""
    for field_name, hybrid_property_info in iter_hybrid_property_infos(model):
        if field_name in payload:
            continue

        payload[field_name] = (
            get_resolved_hybrid_property_return_annotation(model, hybrid_property_info),
            create_hybrid_property_field_info(),
        )
