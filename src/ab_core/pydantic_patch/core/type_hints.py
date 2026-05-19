"""Type-hint resolution helpers for patch model generation."""

import sys

# src/ab_core/pydantic_patch/core/type_hints.py
import types
from typing import (
    ForwardRef,
    _eval_type,  # pyright: ignore[reportPrivateUsage]  # noqa: PLC2701
    _strip_annotations,  # pyright: ignore[reportPrivateUsage]  # noqa: PLC2701
)

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


def get_augmented_class_type_hints(
    cls: type[BaseModel],
    *,
    include_extras: bool,
) -> dict[str, object]:
    """Resolve class type hints using Python's default class behaviour plus sibling models.

    This intentionally mirrors the class branch of typing.get_type_hints(),
    but extends the namespace with imported sibling BaseModel / SQLModel classes.
    """
    hints: dict[str, object] = {}
    model_namespace = build_model_namespace(cls)

    for base in reversed(cls.__mro__):
        base_globals = getattr(sys.modules.get(base.__module__, None), "__dict__", {})
        annotations = base.__dict__.get("__annotations__", {})

        if isinstance(annotations, types.GetSetDescriptorType):
            annotations = {}

        base_locals = dict(vars(base))

        # Match typing.get_type_hints() class behaviour when globalns/localns
        # are not passed. This reversal is required for backwards compatibility.
        eval_globals = base_locals
        eval_locals = {
            **base_globals,
            **model_namespace,
            cls.__name__: cls,
            base.__name__: base,
        }

        type_params = getattr(base, "__type_params__", ())

        for name, value in annotations.items():
            if value is None:
                value = type(None)

            if isinstance(value, str):
                value = ForwardRef(
                    value,
                    is_argument=False,
                    is_class=True,
                )

            hints[name] = _eval_type(
                value,
                eval_globals,
                eval_locals,
                type_params,
            )

    if include_extras:
        return hints

    return {key: _strip_annotations(value) for key, value in hints.items()}


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
