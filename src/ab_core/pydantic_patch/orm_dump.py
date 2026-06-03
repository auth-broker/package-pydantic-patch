"""Relationship-aware dump helpers for SQLModel / SQLAlchemy objects."""

from typing import Any, Literal

from pydantic import BaseModel, TypeAdapter

from ab_core.pydantic_patch.null import Null


def dump_orm_model(
    instance: BaseModel,
    *,
    mode: Literal["json", "python"] = "python",
    include: Any = None,
    exclude: Any = None,
    by_alias: bool | None = None,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
    exclude_none: bool = False,
    round_trip: bool = False,
    warnings: bool | Literal["none", "warn", "error"] = True,
) -> dict[str, Any]:
    """Dump a SQLModel/Pydantic instance using a Null response model.

    This preserves SQLModel relationships because validation happens through
    a generated Pydantic BaseModel that includes relationship fields.

    Note:
        For bidirectional ORM graphs, pass an `exclude` map to avoid circular
        parent/child serialisation.

    """
    null_model = Null[type(instance)]()

    validated = TypeAdapter(null_model).validate_python(
        instance,
        from_attributes=True,
        by_name=True,
    )

    return validated.model_dump(
        mode=mode,
        include=include,
        exclude=exclude,
        by_alias=by_alias,
        exclude_unset=exclude_unset,
        exclude_defaults=exclude_defaults,
        exclude_none=exclude_none,
        round_trip=round_trip,
        warnings=warnings,
    )
