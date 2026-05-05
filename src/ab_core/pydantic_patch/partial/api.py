"""Public Partial API."""

from collections.abc import Collection

from pydantic import BaseModel

from ab_core.pydantic_patch.core.operation import Operation
from ab_core.pydantic_patch.partial.config import PartialConfig
from ab_core.pydantic_patch.partial.operation import create_partial_model


class Partial(Operation):
    """Create a model where selected fields are optional."""

    def __new__(
        cls,
        *,
        fields: Collection[str] | None = None,
        child_models: dict[type[BaseModel], PartialConfig] | None = None,
        name: str | None = None,
    ) -> type[BaseModel]:
        return create_partial_model(
            cls.source_model,
            fields=fields,
            child_models=child_models,
            name=name,
        )
