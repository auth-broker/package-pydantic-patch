"""Field validation and payload mutation helpers."""

from typing import Any, get_args, get_origin

from pydantic import BaseModel

from ab_core.pydantic_patch.core.errors import (
    ConflictingPatchConfigError,
    InvalidPatchFieldError,
)


def validate_fields_exist_on_model(
    model: type[BaseModel],
    fields: frozenset[str] | None,
    *,
    operation: str,
) -> None:
    """Validate that all configured fields exist on the source model."""
    if fields is None:
        return

    missing = sorted(field for field in fields if field not in model.model_fields)
    if missing:
        raise InvalidPatchFieldError(
            f"Unknown field(s) for {operation} on {model.__name__}: {missing}. "
            f"Available fields: {sorted(model.model_fields)}."
        )


def validate_fields_exist_in_payload(
    payload: dict[str, tuple[Any, Any]],
    fields: frozenset[str] | None,
    *,
    model: type[BaseModel],
    operation: str,
) -> None:
    """Validate that all configured fields exist in the currently generated payload."""
    if fields is None:
        return

    missing = sorted(field for field in fields if field not in payload)
    if missing:
        raise ConflictingPatchConfigError(
            f"Field(s) {missing} cannot be used for {operation} on {model.__name__} "
            "because they are not present after include/exclude processing. "
            f"Available payload fields: {sorted(payload)}."
        )


def allows_none(annotation: Any) -> bool:
    """Return whether an annotation already allows None."""
    if annotation is Any:
        return True

    if annotation is None or annotation is type(None):
        return True

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is None:
        return False

    return type(None) in args


def make_optional(annotation: Any) -> Any:
    """Return an annotation that allows None."""
    if allows_none(annotation):
        return annotation
    return annotation | None


def make_field_optional(annotation: Any, default: Any) -> tuple[Any, Any]:
    """Return a create_model field definition where the field is optional."""
    return make_optional(annotation), None


def make_field_required(annotation: Any, default: Any) -> tuple[Any, Any]:
    """Return a create_model field definition where the field is required."""
    return annotation, ...
