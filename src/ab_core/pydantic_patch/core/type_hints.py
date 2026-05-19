"""Type-hint resolution helpers for patch model generation."""

import sys
from typing import get_type_hints

from pydantic import BaseModel

from ab_core.pydantic_patch.core.errors import ForwardReferencesNotSupported
from ab_core.pydantic_patch.core.forward_references import (
    build_forward_ref_error_message,
    build_model_namespace,
)

from .computed_field_type_hints import (
    computed_field_contains_forward_ref,
    iter_computed_field_infos,
)


def build_augmented_class_type_hints_namespaces(
    model: type[BaseModel],
) -> tuple[dict[str, object], dict[str, object]]:
    """Build get_type_hints namespaces from Python defaults plus sibling models."""
    module = sys.modules.get(model.__module__)
    module_globals = dict(getattr(module, "__dict__", {}))
    model_namespace = build_model_namespace(model)

    globalns = {
        **module_globals,
        **model_namespace,
    }
    localns = {
        **module_globals,
        **model_namespace,
        model.__name__: model,
    }

    return globalns, localns


def get_augmented_class_type_hints(
    cls: type[BaseModel],
    *,
    include_extras: bool,
) -> dict[str, object]:
    """Resolve class type hints using Python defaults plus sibling models."""
    globalns, localns = build_augmented_class_type_hints_namespaces(cls)

    return get_type_hints(
        cls,
        globalns=globalns,
        localns=localns,
        include_extras=include_extras,
    )


def get_resolved_type_hints(model: type[BaseModel]) -> dict[str, object]:
    """Resolve model type hints and raise custom errors on truly unresolved refs."""
    try:
        return get_augmented_class_type_hints(
            model,
            include_extras=True,
        )
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
        if computed_field_contains_forward_ref(model, computed_field_info)
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
