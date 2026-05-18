"""Helpers for detecting and resolving forward references."""

import sys
from textwrap import dedent
from typing import ForwardRef, Literal, get_args, get_origin

from pydantic import BaseModel


def contains_forward_ref(annotation: object) -> bool:
    """Return whether an annotation still contains string or ForwardRef nodes."""
    if isinstance(annotation, str | ForwardRef):
        return True

    if get_origin(annotation) is Literal:
        return False

    return any(contains_forward_ref(arg) for arg in get_args(annotation))


def _iter_models_in_module(module_name: str) -> list[type[BaseModel]]:
    module = sys.modules.get(module_name)
    if module is None:
        return []

    return sorted(
        {
            value
            for value in vars(module).values()
            if (isinstance(value, type) and issubclass(value, BaseModel) and value.__module__ == module_name)
        },
        key=lambda model: model.__name__,
    )


def _iter_model_modules(root_model: type[BaseModel]) -> list[str]:
    package_prefix = root_model.__module__.rsplit(".", 1)[0]

    module_names = {
        module_name
        for module_name in sys.modules
        if module_name == root_model.__module__ or module_name.startswith(f"{package_prefix}.")
    }

    return sorted(module_name for module_name in module_names if _iter_models_in_module(module_name))


def build_model_namespace(root_model: type[BaseModel]) -> dict[str, type[BaseModel]]:
    """Build a temporary namespace of imported sibling BaseModel classes.

    This is used to resolve string / ForwardRef annotations without requiring
    developers to manually bind circular model references onto their modules.
    """
    return {
        model.__name__: model
        for module_name in _iter_model_modules(root_model)
        for model in _iter_models_in_module(module_name)
    }


def build_type_hints_namespaces(
    model: type[BaseModel],
) -> tuple[dict[str, object], dict[str, object]]:
    """Return globalns/localns for resolving a model's annotations."""
    module = sys.modules.get(model.__module__)
    module_globals: dict[str, object] = {}

    if module is not None:
        module_globals.update(vars(module))

    model_namespace = build_model_namespace(model)

    globalns = {
        **module_globals,
        **model_namespace,
    }
    localns = {
        **model_namespace,
        model.__name__: model,
    }

    return globalns, localns


def unresolved_annotation_names(model: type[BaseModel]) -> list[str]:
    """Collect unresolved forward-reference annotation names for model modules."""
    unresolved: list[str] = []

    for module_name in _iter_model_modules(model):
        for current_model in _iter_models_in_module(module_name):
            annotations = getattr(current_model, "__annotations__", {})

            for field_name, annotation in annotations.items():
                if contains_forward_ref(annotation):
                    if current_model is model:
                        unresolved.append(field_name)
                    else:
                        unresolved.append(f"{current_model.__name__}.{field_name}")

    return sorted(set(unresolved))


def build_forward_ref_error_message(
    *,
    model: type[BaseModel],
    unresolved_fields: list[str],
) -> str:
    """Build a guidance-rich error message for unresolved forward references."""
    return dedent(
        f"""
        Forward references could not be resolved automatically.

        pydantic-patch tried to resolve imported sibling BaseModel / SQLModel
        classes before generating Pick/Omit/Partial/Required/Patch models, but
        the model {model.__name__!r} still has unresolved forward-reference
        annotation(s): {sorted(set(unresolved_fields))!r}.

        This usually means the referenced model has not been imported anywhere
        reachable from the root model's package/module tree, or the annotation
        points to a genuinely missing type.

        To fix this, import the model package or module that exposes the related
        model classes before generating patch schemas.

        Example:

        ```python
        from my_app.models import Project, ProjectMilestone, ProjectTask, TaskComment

        ProjectPatch = Patch[Project](
            pick={{"id", "name", "milestones"}},
            child_models={{
                ProjectMilestone: PatchConfig(pick={{"id", "name", "tasks"}}),
                ProjectTask: PatchConfig(pick={{"id", "title", "comments"}}),
                TaskComment: PatchConfig(pick={{"id", "body"}}),
            }},
        )
        ```

        If the referenced type is intentionally external, make sure it is
        importable in the module where the source model is defined.
        """
    ).strip()
