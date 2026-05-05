"""Public Required API."""

from collections.abc import Collection

from pydantic import BaseModel

from ab_core.pydantic_patch.core.operation import Operation
from ab_core.pydantic_patch.required.config import RequiredConfig
from ab_core.pydantic_patch.required.operation import create_required_model


class Required(Operation):
    """Create a model where selected fields are required."""

    def __new__(
        cls,
        *,
        fields: Collection[str] | None = None,
        child_models: dict[type[BaseModel], RequiredConfig] | None = None,
        name: str | None = None,
    ) -> type[BaseModel]:
        """Create and return a required-transformed model class."""
        return create_required_model(
            cls.source_model,
            fields=fields,
            child_models=child_models,
            name=name,
        )
