"""Patch aggregation configuration."""

from collections.abc import Collection

from pydantic import BaseModel, ConfigDict, Field

from ab_core.pydantic_patch.core.config import normalise_fields


class PatchConfig(BaseModel):
    """Configuration for composed patch transformations."""

    pick: Collection[str] | None = None
    omit: Collection[str] | None = None
    partial: Collection[str] | None = None
    required: Collection[str] | None = None

    child_models: dict[type[BaseModel], "PatchConfig"] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def model_post_init(self, __context: object) -> None:
        """Normalize all configured field collections after initialization."""
        self.pick = normalise_fields(self.pick)
        self.omit = normalise_fields(self.omit)
        self.partial = normalise_fields(self.partial)
        self.required = normalise_fields(self.required)


PatchConfig.model_rebuild()
