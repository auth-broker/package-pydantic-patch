"""Patch aggregation configuration."""

from pydantic import BaseModel, ConfigDict, Field

from ab_core.pydantic_patch.core.config import normalise_fields


class PatchConfig(BaseModel):
    include: frozenset[str] | None = None
    exclude: frozenset[str] | None = None
    partial: frozenset[str] | None = None
    required: frozenset[str] | None = None

    child_models: dict[type[BaseModel], "PatchConfig"] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def model_post_init(self, __context: object) -> None:
        self.include = normalise_fields(self.include)
        self.exclude = normalise_fields(self.exclude)
        self.partial = normalise_fields(self.partial)
        self.required = normalise_fields(self.required)


PatchConfig.model_rebuild()
