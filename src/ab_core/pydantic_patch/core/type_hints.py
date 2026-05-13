"""Type-hint resolution helpers for patch model generation."""

from typing import get_type_hints

from pydantic import BaseModel
from pydantic.fields import PydanticUndefined

from .errors import ForwardReferencesNotSupported
from .forward_references import build_forward_ref_error_message, contains_forward_ref


def get_resolved_type_hints(model: type[BaseModel]) -> dict[str, object]:
    """Resolve model type hints and raise custom errors on unresolved refs."""
    try:
        return get_type_hints(model, include_extras=True)
    except NameError as error:
        raise ForwardReferencesNotSupported(
            build_forward_ref_error_message(
                model=model,
                unresolved_fields=list(getattr(model, "__annotations__", {})),
            )
        ) from error


def assert_no_forward_refs(model: type[BaseModel]) -> None:
    """Raise only when forward references cannot actually be resolved."""
    get_resolved_type_hints(model)

    unresolved_computed_fields = [
        field_name
        for field_name, computed_field_info in model.model_computed_fields.items()
        if (
            return_type := getattr(
                computed_field_info,
                "return_type",
                PydanticUndefined,
            )
        )
        is not PydanticUndefined
        and contains_forward_ref(return_type)
    ]

    if unresolved_computed_fields:
        raise ForwardReferencesNotSupported(
            build_forward_ref_error_message(
                model=model,
                unresolved_fields=unresolved_computed_fields,
            )
        )
