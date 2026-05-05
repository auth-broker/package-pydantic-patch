"""Public Pick API."""

from collections.abc import Collection

from pydantic import BaseModel

from ab_core.pydantic_patch.core.operation import Operation
from ab_core.pydantic_patch.pick.config import PickConfig
from ab_core.pydantic_patch.pick.operation import create_pick_model


class Pick(Operation):
    """Create a model containing only selected fields."""

    def __new__(
        cls,
        *,
        fields: Collection[str] | None = None,
        child_models: dict[type[BaseModel], PickConfig] | None = None,
        name: str | None = None,
    ) -> type[BaseModel]:
        """Create and return a pick-transformed model class."""
        return create_pick_model(
            cls.source_model,
            fields=fields,
            child_models=child_models,
            name=name,
        )
