"""Public Partial API."""

from __future__ import annotations

from collections.abc import Collection
from typing import Generic, TypeVar, cast

from generic_preserver.wrapper import generic_preserver
from pydantic import BaseModel

from ab_core.pydantic_patch.partial.config import PartialConfig
from ab_core.pydantic_patch.partial.operation import create_partial_model

T = TypeVar("T", bound=BaseModel)


@generic_preserver
class Partial(Generic[T]):
    """Create a model where selected fields are optional."""

    def __new__(
        cls,
        *,
        fields: Collection[str] | None = None,
        child_models: dict[type[BaseModel], PartialConfig] | None = None,
        name: str | None = None,
    ) -> type[BaseModel]:
        generic_map = cast(
            dict[str, type[BaseModel]],
            getattr(cls, "__generic_map__", None),
        )
        source_model = generic_map[repr(T)]
        return create_partial_model(
            source_model,
            fields=fields,
            child_models=child_models,
            name=name,
        )
