"""Relationship-aware loading helpers for SQLModel / SQLAlchemy objects."""

from collections.abc import Mapping
from typing import Any, cast

from pydantic import BaseModel, TypeAdapter
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import RelationshipProperty
from sqlmodel import SQLModel

from ab_core.pydantic_patch.null import Null


def load_orm_model[T: SQLModel](
    model: type[T],
    payload: Mapping[str, Any] | BaseModel,
    *,
    include_primary_keys: bool = True,
    include_foreign_keys: bool = True,
) -> T:
    """Load a SQLModel ORM instance graph from a JSON-like payload.

    The payload is first validated through the generated Null[...] Pydantic
    model, which means relationship fields are supported.

    The validated payload is then recursively converted into real SQLModel ORM
    instances using SQLAlchemy mapper metadata.

    Args:
        model: The root SQLModel table model to construct.
        payload: A dict-like JSON payload or compatible Pydantic model.
        include_primary_keys: Whether to copy primary key scalar fields.
        include_foreign_keys: Whether to copy foreign key scalar fields.

    Returns:
        A new transient SQLModel ORM object graph.

    """
    null_model = Null[model]()

    validated = TypeAdapter(null_model).validate_python(
        payload,
        from_attributes=True,
    )

    return _load_orm_model_from_validated(
        model,
        validated,
        include_primary_keys=include_primary_keys,
        include_foreign_keys=include_foreign_keys,
    )


def _load_orm_model_from_validated[T: SQLModel](
    model: type[T],
    validated: BaseModel,
    *,
    include_primary_keys: bool,
    include_foreign_keys: bool,
) -> T:
    """Recursively construct a SQLModel object from a validated Null model."""
    mapper = sa_inspect(model)

    field_names_set = _provided_field_names(validated)

    primary_key_column_keys = {column.key for column in mapper.primary_key}

    foreign_key_column_keys = {column.key for column in mapper.columns if column.foreign_keys}

    column_values: dict[str, Any] = {}

    for column_attr in mapper.column_attrs:
        key = column_attr.key

        if key not in field_names_set:
            continue

        if not include_primary_keys and key in primary_key_column_keys:
            continue

        if not include_foreign_keys and key in foreign_key_column_keys:
            continue

        column_values[key] = getattr(validated, key)

    instance = model(**column_values)

    for relationship in mapper.relationships:
        _load_relationship(
            instance,
            relationship,
            validated,
            include_primary_keys=include_primary_keys,
            include_foreign_keys=include_foreign_keys,
        )

    return instance


def _load_relationship(
    instance: SQLModel,
    relationship: RelationshipProperty,
    validated: BaseModel,
    *,
    include_primary_keys: bool,
    include_foreign_keys: bool,
) -> None:
    """Load one relationship from a validated Null model onto an ORM instance."""
    key = relationship.key
    field_names_set = _provided_field_names(validated)

    if key not in field_names_set:
        return

    value = getattr(validated, key)

    if value is None:
        setattr(instance, key, None)
        return

    target_model = cast(type[SQLModel], relationship.mapper.class_)

    if relationship.uselist:
        if not isinstance(value, list):
            raise TypeError(
                f"Expected relationship {type(instance).__name__}.{key} to be a list, got {type(value).__name__}."
            )

        children = [
            _load_orm_model_from_validated(
                target_model,
                child,
                include_primary_keys=include_primary_keys,
                include_foreign_keys=include_foreign_keys,
            )
            for child in value
        ]

        setattr(instance, key, children)
        return

    if not isinstance(value, BaseModel):
        raise TypeError(
            f"Expected relationship {type(instance).__name__}.{key} to be a BaseModel, got {type(value).__name__}."
        )

    child = _load_orm_model_from_validated(
        target_model,
        value,
        include_primary_keys=include_primary_keys,
        include_foreign_keys=include_foreign_keys,
    )

    setattr(instance, key, child)


def _provided_field_names(model: BaseModel) -> set[str]:
    """Return fields explicitly present after validation.

    Pydantic v2 tracks explicitly provided fields using model_fields_set.
    Falling back to model_fields keeps this safe for constructed/internal models.
    """
    fields_set = getattr(model, "model_fields_set", None)

    if fields_set is not None:
        return set(fields_set)

    return set(model.model_fields)
