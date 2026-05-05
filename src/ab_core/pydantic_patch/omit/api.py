"""Public Omit API."""

from __future__ import annotations

from collections.abc import Collection
from typing import Generic, TypeVar, cast

from generic_preserver.wrapper import generic_preserver
from pydantic import BaseModel

from ab_core.pydantic_patch.omit.config import OmitConfig
from ab_core.pydantic_patch.omit.operation import create_omit_model

T = TypeVar("T", bound=BaseModel)


@generic_preserver
class Omit(Generic[T]):
    """Create a model excluding selected fields."""

    def __new__(
        cls,
        *,
        fields: Collection[str] | None = None,
        child_models: dict[type[BaseModel], OmitConfig] | None = None,
        name: str | None = None,
    ) -> type[BaseModel]:
        generic_map = cast(
            dict[str, type[BaseModel]],
            getattr(cls, "__generic_map__", None),
        )
        source_model = generic_map[repr(T)]
        return create_omit_model(
            source_model,
            fields=fields,
            child_models=child_models,
            name=name,
        )
