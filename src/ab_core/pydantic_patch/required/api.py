"""Public Required API."""



from collections.abc import Collection
from typing import Generic, TypeVar, cast

from generic_preserver.wrapper import generic_preserver
from pydantic import BaseModel

from ab_core.pydantic_patch.required.config import RequiredConfig
from ab_core.pydantic_patch.required.operation import create_required_model

T = TypeVar("T", bound=BaseModel)


@generic_preserver
class Required(Generic[T]):
    """Create a model where selected fields are required."""

    def __new__(
        cls,
        *,
        fields: Collection[str] | None = None,
        child_models: dict[type[BaseModel], RequiredConfig] | None = None,
        name: str | None = None,
    ) -> type[BaseModel]:
        generic_map = cast(
            dict[str, type[BaseModel]],
            getattr(cls, "__generic_map__", None),
        )
        source_model = generic_map[repr(T)]
        return create_required_model(
            source_model,
            fields=fields,
            child_models=child_models,
            name=name,
        )
