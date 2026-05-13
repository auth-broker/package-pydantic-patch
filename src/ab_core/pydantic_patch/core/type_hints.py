"""Type-hint resolution helpers for patch model generation."""

from typing import get_type_hints

from pydantic import BaseModel

from .computed_field_type_hints import (
    computed_field_contains_forward_ref,
    iter_computed_field_infos,
)
from .errors import ForwardReferencesNotSupported
from .forward_references import build_forward_ref_error_message


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


def unresolved_computed_field_names(model: type[BaseModel]) -> list[str]:
    """Return computed fields with unresolved return annotations."""
    return sorted(
        field_name
        for field_name, computed_field_info in iter_computed_field_infos(model)
        if computed_field_contains_forward_ref(computed_field_info)
    )


def assert_no_forward_refs(model: type[BaseModel]) -> None:
    """Raise only when forward references cannot actually be resolved."""
    get_resolved_type_hints(model)

    unresolved_computed_fields = unresolved_computed_field_names(model)

    if unresolved_computed_fields:
        raise ForwardReferencesNotSupported(
            build_forward_ref_error_message(
                model=model,
                unresolved_fields=unresolved_computed_fields,
            )
        )
