"""Public Patch API."""

from collections.abc import Collection

from pydantic import BaseModel

from ab_core.pydantic_patch.core.operation import Operation
from ab_core.pydantic_patch.patch.config import PatchConfig
from ab_core.pydantic_patch.patch.operation import create_patch_model


class Patch(Operation):
    """Create a patch model by composing pick/omit/partial/required."""

    def __new__(
        cls,
        *,
        pick: Collection[str] | None = None,
        omit: Collection[str] | None = None,
        partial: Collection[str] | None = None,
        required: Collection[str] | None = None,
        child_models: dict[type[BaseModel], PatchConfig] | None = None,
        name: str | None = None,
        use_cache: bool = True,
    ) -> type[BaseModel]:
        return create_patch_model(
            cls.source_model,
            pick=pick,
            omit=omit,
            partial=partial,
            required=required,
            child_models=child_models,
            name=name,
            use_cache=use_cache,
        )
