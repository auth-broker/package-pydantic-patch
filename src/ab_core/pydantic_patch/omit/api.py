"""Public Omit API."""

from collections.abc import Collection

from pydantic import BaseModel

from ab_core.pydantic_patch.core.operation import Operation
from ab_core.pydantic_patch.omit.config import OmitConfig
from ab_core.pydantic_patch.omit.operation import create_omit_model


class Omit(Operation):
    """Create a model excluding selected fields."""

    def __new__(
        cls,
        *,
        fields: Collection[str] | None = None,
        child_models: dict[type[BaseModel], OmitConfig] | None = None,
        name: str | None = None,
    ) -> type[BaseModel]:
        """Create and return an omit-transformed model class."""
        return create_omit_model(
            cls.source_model,
            fields=fields,
            child_models=child_models,
            name=name,
        )
