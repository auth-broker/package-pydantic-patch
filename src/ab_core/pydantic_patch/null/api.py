"""Null operation implementation.

Null creates a plain Pydantic BaseModel equivalent of a source model without
performing pick/omit/partial/required/patch field manipulation.

This is useful for SQLModel response/dump schemas because SQLModel.model_dump()
does not include relationship attributes, while the generated Null model does.
"""


from pydantic import BaseModel

from ab_core.pydantic_patch.core.operation import Operation
from ab_core.pydantic_patch.null.config import NullConfig

from .operation import create_null_model


class Null[T: BaseModel](Operation[T]):
    """Create a plain Pydantic model mirror of a BaseModel/SQLModel."""

    def __new__(
        cls,
        *,
        child_models: dict[type[BaseModel], NullConfig] | None = None,
        exclude_relationships: frozenset[str] | set[str] | None = None,
        name: str | None = None,
        use_cache: bool = True,
    ) -> type[BaseModel]:
        """Create and return a null-transformed model class."""
        return create_null_model(
            cls.source_model,
            child_models=child_models,
            exclude_relationships=exclude_relationships,
            name=name,
            use_cache=use_cache,
        )
