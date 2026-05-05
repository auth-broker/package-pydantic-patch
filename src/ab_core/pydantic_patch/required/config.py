"""Required configuration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ab_core.pydantic_patch.core.config import normalise_fields


class RequiredConfig(BaseModel):
    fields: frozenset[str] | None = None
    child_models: dict[type[BaseModel], "RequiredConfig"] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def model_post_init(self, __context: object) -> None:
        self.fields = normalise_fields(self.fields)


RequiredConfig.model_rebuild()
