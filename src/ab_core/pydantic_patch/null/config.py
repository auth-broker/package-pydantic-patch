"""Null operation configuration."""

from pydantic import BaseModel, ConfigDict, Field


class NullConfig(BaseModel):
    """Configuration for null transformations.

    Null creates a Pydantic BaseModel mirror of the source model, including
    SQLModel relationships as normal fields unless they are excluded.
    """

    child_models: dict[type[BaseModel], "NullConfig"] = Field(default_factory=dict)
    exclude_relationships: frozenset[str] = Field(default_factory=frozenset)

    model_config = ConfigDict(arbitrary_types_allowed=True)


NullConfig.model_rebuild()
