"""Public Patch API."""

from collections.abc import Collection

from pydantic import BaseModel

from ab_core.pydantic_patch.core.operation import Operation
from ab_core.pydantic_patch.patch.config import PatchConfig
from ab_core.pydantic_patch.patch.operation import create_patch_model


class Patch(Operation):
    """Create a patch model by composing include/exclude/partial/required."""

    def __new__(
        cls,
        *,
        include: Collection[str] | None = None,
        exclude: Collection[str] | None = None,
        partial: Collection[str] | None = None,
        required: Collection[str] | None = None,
        child_models: dict[type[BaseModel], PatchConfig] | None = None,
        name: str | None = None,
    ) -> type[BaseModel]:
        return create_patch_model(
            cls.source_model,
            include=include,
            exclude=exclude,
            partial=partial,
            required=required,
            child_models=child_models,
            name=name,
        )
