"""Helpers for detecting and reporting unresolved forward references."""

import sys
from textwrap import dedent
from typing import ForwardRef, Literal, get_args, get_origin

from pydantic import BaseModel


def contains_forward_ref(annotation: object) -> bool:
    """Return whether an annotation contains unresolved forward references."""
    if isinstance(annotation, str | ForwardRef):
        return True

    origin = get_origin(annotation)

    # Literal values like Literal["cat"] are data values, not forward references.
    if origin is Literal:
        return False

    return any(contains_forward_ref(arg) for arg in get_args(annotation))


def _iter_related_models(annotation: object) -> set[type[BaseModel]]:
    related_models: set[type[BaseModel]] = set()

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        related_models.add(annotation)

    for arg in get_args(annotation):
        related_models.update(_iter_related_models(arg))

    return related_models


def unresolved_annotation_names(model: type[BaseModel]) -> list[str]:
    """List field names that still contain forward references on a model graph."""
    unresolved_fields: list[str] = []
    to_visit: list[type[BaseModel]] = [model]
    visited: set[type[BaseModel]] = set()

    while to_visit:
        current_model = to_visit.pop()

        if current_model in visited:
            continue

        visited.add(current_model)

        annotations = dict(getattr(current_model, "__annotations__", {}))

        relationship_names = getattr(current_model, "__sqlmodel_relationships__", {})
        for relationship_name in relationship_names:
            if relationship_name in annotations:
                continue

            # SQLModel relationship annotations may bypass model_fields and only
            # be discoverable from the class annotation namespace.
            raw_annotation = getattr(current_model, relationship_name, None)
            if raw_annotation is not None:
                annotations[relationship_name] = raw_annotation

        for field_name, annotation in annotations.items():
            if contains_forward_ref(annotation):
                if current_model is model:
                    unresolved_fields.append(field_name)
                else:
                    unresolved_fields.append(f"{current_model.__name__}.{field_name}")

            for related_model in _iter_related_models(annotation):
                if related_model not in visited:
                    to_visit.append(related_model)

    return unresolved_fields

def build_forward_ref_error_message(
    *,
    model: type[BaseModel],
    unresolved_fields: list[str],
) -> str:
    """Build a detailed error message for unresolved forward-reference hints."""
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
        Forward references are not supported by pydantic-patch until they are resolved.

        pydantic-patch is type-driven and needs real Python types when generating
        Pick/Omit/Partial/Required/Patch models. The model {model.__name__!r} has
        unresolved annotation(s): {unresolved_fields!r}.

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

        For SQLModel relationships, this often means binding shallow imports at
        module level before calling model_rebuild(force=True).

        In a package with circular SQLModel relationships, this usually belongs
        in the package __init__.py or another central models module that imports
        all ORM model modules first.
        """
    ).strip()
