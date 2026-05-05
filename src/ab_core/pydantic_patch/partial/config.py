"""Partial configuration."""

from collections.abc import Collection

from pydantic import BaseModel, ConfigDict, Field

from ab_core.pydantic_patch.core.config import normalise_fields


class PartialConfig(BaseModel):
    """Configuration for partial operations."""

    fields: Collection[str] | None = None
    child_models: dict[type[BaseModel], "PartialConfig"] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def model_post_init(self, __context: object) -> None:
        """Normalize field collections after model initialization."""
        self.fields = normalise_fields(self.fields)


PartialConfig.model_rebuild()
