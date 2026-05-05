"""Public Patch API."""



from collections.abc import Collection
from typing import Generic, TypeVar, cast

from generic_preserver.wrapper import generic_preserver
from pydantic import BaseModel

from ab_core.pydantic_patch.patch.config import PatchConfig
from ab_core.pydantic_patch.patch.operation import create_patch_model

T = TypeVar("T", bound=BaseModel)


@generic_preserver
class Patch(Generic[T]):
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
        generic_map = cast(
            dict[str, type[BaseModel]],
            getattr(cls, "__generic_map__", None),
        )
        source_model = generic_map[repr(T)]
        return create_patch_model(
            source_model,
            include=include,
            exclude=exclude,
            partial=partial,
            required=required,
            child_models=child_models,
            name=name,
        )
