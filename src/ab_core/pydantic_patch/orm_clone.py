"""Utility for cloning SQLModel ORM objects without copying SQLAlchemy instance state."""

from __future__ import annotations

from typing import Any

from sqlalchemy import inspect
from sqlalchemy.orm.attributes import NO_VALUE
from sqlmodel import SQLModel


def recursive_clone_scalar[T: SQLModel](
    obj: T,
    *,
    include_primary_keys: bool = False,
    include_foreign_keys: bool = True,
    _memo: dict[int, SQLModel] | None = None,
) -> T:
    """Clone a SQLModel ORM object graph without copying SQLAlchemy instance state.

    - Copies mapped column values.
    - Copies already-loaded relationships.
    - Recursively clones related SQLModel objects.
    - Handles cycles/shared objects via memo.
    - Does not use model_dump(), so relationships are preserved.
    - Does not copy _sa_instance_state.
    """
    if _memo is None:
        _memo = {}

    obj_id = id(obj)
    if obj_id in _memo:
        return _memo[obj_id]  # type: ignore[return-value]

    state = inspect(obj)
    mapper = state.mapper
    cls = type(obj)

    column_values: dict[str, Any] = {}

    primary_key_column_keys = {column.key for column in mapper.primary_key}

    foreign_key_column_keys = {column.key for column in mapper.columns if column.foreign_keys}

    for column_attr in mapper.column_attrs:
        key = column_attr.key

        if not include_primary_keys and key in primary_key_column_keys:
            continue

        if not include_foreign_keys and key in foreign_key_column_keys:
            continue

        attr_state = state.attrs[key]
        value = attr_state.loaded_value

        if value is NO_VALUE:
            # Avoid triggering lazy loads / missing state.
            continue

        column_values[key] = value

    clone = cls(**column_values)
    _memo[obj_id] = clone

    for relationship in mapper.relationships:
        key = relationship.key

        attr_state = state.attrs[key]
        value = attr_state.loaded_value

        if value is NO_VALUE:
            # Relationship was not populated, so don't accidentally lazy-load it.
            continue

        if value is None:
            setattr(clone, key, None)
            continue

        if relationship.uselist:
            cloned_items = [
                recursive_clone_scalar(
                    item,
                    include_primary_keys=include_primary_keys,
                    include_foreign_keys=include_foreign_keys,
                    _memo=_memo,
                )
                for item in value
            ]

            setattr(clone, key, cloned_items)

        else:
            cloned_related = recursive_clone_scalar(
                value,
                include_primary_keys=include_primary_keys,
                include_foreign_keys=include_foreign_keys,
                _memo=_memo,
            )

            setattr(clone, key, cloned_related)

    return clone
