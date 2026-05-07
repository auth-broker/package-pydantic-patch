"""Helpers for detecting and reporting unresolved forward references."""

import sys
from textwrap import dedent
from typing import ForwardRef, get_args

from pydantic import BaseModel


def contains_forward_ref(annotation: object) -> bool:
    """Return whether an annotation contains any string or ``ForwardRef`` node."""
    if isinstance(annotation, str | ForwardRef):
        return True

    return any(contains_forward_ref(arg) for arg in get_args(annotation))


def unresolved_annotation_names(model: type[BaseModel]) -> list[str]:
    """List annotation names on ``model`` that still contain forward references."""
    return [
        field_name
        for field_name, annotation in getattr(model, "__annotations__", {}).items()
        if contains_forward_ref(annotation)
    ]


def build_forward_ref_error_message(
    *,
    model: type[BaseModel],
    unresolved_fields: list[str],
) -> str:
    """Build a detailed error message for unresolved SQLModel relationship hints."""
    module_name = model.__module__
    module = sys.modules.get(module_name)

    models_in_module = (
        [
            value
            for value in vars(module).values()
            if isinstance(value, type) and issubclass(value, BaseModel) and value.__module__ == module_name
        ]
        if module is not None
        else [model]
    )

    model_names = ", ".join(cls.__name__ for cls in models_in_module)

    return dedent(
        f"""
        SQLModel relationship forward references are not supported by pydantic-patch.

        pydantic-patch is type-driven and needs real Python types when generating
        Pick/Omit/Partial/Required/Patch models. The model {model.__name__!r} still
        has unresolved relationship annotation(s): {unresolved_fields!r}.

        Resolve the relationship references after all ORM models in the module have
        been imported, then rebuild the models before calling Patch[...], Pick[...],
        Omit[...], Partial[...] or Required[...].

        Suggested pattern for {module_name}:

            # Import every module that defines related ORM models first.
            # Then bind shallow relationship references at module level, for example:
            #
            # some_model_module.RelatedModel = RelatedModel
            #
            # Finally rebuild all affected models:
            for model in ({model_names}):
                model.model_rebuild(force=True)

        In a package with circular SQLModel relationships, this usually belongs in
        the package __init__.py or another central models module that imports all
        ORM model modules first.
        """
    ).strip()
