"""Type-hint resolution helpers for patch model generation."""

from typing import get_type_hints

from pydantic import BaseModel

from .errors import ForwardReferencesNotSupported
from .forward_references import build_forward_ref_error_message, unresolved_annotation_names


def assert_no_forward_refs(model: type[BaseModel]) -> None:
    """Raise a custom error when unresolved forward references are present."""
    unresolved = unresolved_annotation_names(model)

    if unresolved:
        raise ForwardReferencesNotSupported(
            build_forward_ref_error_message(
                model=model,
                unresolved_fields=unresolved,
            )
        )


def get_resolved_type_hints(model: type[BaseModel]) -> dict[str, object]:
    """Resolve model type hints and raise custom errors on unresolved refs."""
    assert_no_forward_refs(model)

    try:
        return get_type_hints(model, include_extras=True)
    except NameError as error:
        raise ForwardReferencesNotSupported(
            build_forward_ref_error_message(
                model=model,
                unresolved_fields=list(getattr(model, "__annotations__", {})),
            )
        ) from error
