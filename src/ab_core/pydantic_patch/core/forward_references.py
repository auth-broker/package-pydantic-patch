"""Helpers for detecting and reporting unresolved forward references."""

import sys
from textwrap import dedent, indent
from typing import ForwardRef, Literal, get_args, get_origin

from pydantic import BaseModel

RESOLVED_EXAMPLE_URL = (
    "https://github.com/auth-broker/package-pydantic-patch/blob/"
    "6af1ffaea06fc4cd893df49ce3194bea9aa8f97e/"
    "src/ab_core/pydantic_patch/examples/sqlmodel_examples/"
    "app_resolved.py#L34-L61"
)


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


def _module_alias(module_name: str) -> str:
    return f"{module_name.rsplit('.', 1)[-1]}_module"


def _forward_ref_name(annotation: object) -> str | None:
    if isinstance(annotation, str):
        return annotation.replace('"', "").replace("'", "").split("|", 1)[0].strip()

    if isinstance(annotation, ForwardRef):
        return annotation.__forward_arg__.split("|", 1)[0].strip()

    for arg in get_args(annotation):
        name = _forward_ref_name(arg)
        if name:
            return name

    return None


def _build_resolution_example(root_model: type[BaseModel]) -> str:
    module_names = _iter_model_modules(root_model)
    models_by_name = {
        model.__name__: model for module_name in module_names for model in _iter_models_in_module(module_name)
    }

    imports = [f"import {module_name} as {_module_alias(module_name)}" for module_name in module_names]

    model_imports = sorted(f"from {model.__module__} import {model.__name__}" for model in models_by_name.values())

    bindings: list[str] = []

    for module_name in module_names:
        module_alias = _module_alias(module_name)

        for model in _iter_models_in_module(module_name):
            for annotation in getattr(model, "__annotations__", {}).values():
                ref_name = _forward_ref_name(annotation)
                if ref_name is None or ref_name not in models_by_name:
                    continue

                if hasattr(sys.modules[module_name], ref_name):
                    continue

                bindings.append(f"{module_alias}.{ref_name} = {ref_name}  # ty: ignore[unresolved-attribute]")

    rebuild_models = ", ".join(
        model.__name__ for model in sorted(models_by_name.values(), key=lambda value: value.__name__)
    )

    return "\n".join(
        [
            *imports,
            "",
            *model_imports,
            "",
            *sorted(set(bindings)),
            "",
            f"for model in ({rebuild_models}):",
            "    model.model_rebuild(force=True)",
        ]
    )


def build_forward_ref_error_message(
    *,
    model: type[BaseModel],
    unresolved_fields: list[str],
) -> str:
    """Build a guidance-rich error message for unresolved forward references."""
    resolution_example = indent(_build_resolution_example(model), "    ")

    return dedent(
        f"""
        Forward references are not supported by pydantic-patch until they are resolved.

        pydantic-patch is type-driven and needs real Python types when generating
        Pick/Omit/Partial/Required/Patch models. The model {model.__name__!r} has
        unresolved forward-reference annotation(s): {sorted(set(unresolved_fields))!r}.

        This usually happens with SQLModel relationships split across modules, where
        relationship attributes are declared with strings to avoid circular imports.

        See the resolved SQLModel example here:
        {RESOLVED_EXAMPLE_URL}

        Import every related ORM module first, bind the shallow circular references
        onto their source modules, then rebuild every affected model before calling
        Patch[...], Pick[...], Omit[...], Partial[...] or Required[...].

        Suggested fix:

        ```python
{resolution_example}
        ```

        This setup usually belongs in your models package __init__.py, or in another
        central models module that imports and prepares all ORM models before patch
        schemas are generated.
        """
    ).strip()
