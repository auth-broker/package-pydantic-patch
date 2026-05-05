"""Public Pick API."""

from collections.abc import Collection
from typing import Generic, TypeVar, cast

from generic_preserver.wrapper import generic_preserver
from pydantic import BaseModel

from ab_core.pydantic_patch.pick.config import PickConfig
from ab_core.pydantic_patch.pick.operation import create_pick_model

T = TypeVar("T", bound=BaseModel)


@generic_preserver
class Pick(Generic[T]):
    """Create a model containing only selected fields."""

    def __new__(
        cls,
        *,
        fields: Collection[str] | None = None,
        child_models: dict[type[BaseModel], PickConfig] | None = None,
        name: str | None = None,
    ) -> type[BaseModel]:
        generic_map = cast(
            dict[str, type[BaseModel]],
            getattr(cls, "__generic_map__", None),
        )
        source_model = generic_map[repr(T)]
        return create_pick_model(
            source_model,
            fields=fields,
            child_models=child_models,
            name=name,
        )
