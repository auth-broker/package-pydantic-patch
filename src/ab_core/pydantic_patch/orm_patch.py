from typing import Any

from pydantic import BaseModel
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import RelationshipProperty


def _provided_values(model: BaseModel) -> dict[str, Any]:
    return {name: getattr(model, name) for name in model.model_fields_set}


def _primary_key_names(model_cls: type[Any]) -> set[str]:
    mapper = sa_inspect(model_cls).mapper
    return {column.key for column in mapper.primary_key}


def _relationship_map(model_cls: type[Any]) -> dict[str, RelationshipProperty]:
    mapper = sa_inspect(model_cls).mapper
    return {relationship.key: relationship for relationship in mapper.relationships}


def _identity_tuple(instance_or_patch: Any, pk_names: set[str]) -> tuple[Any, ...] | None:
    values: list[Any] = []

    for name in pk_names:
        value = getattr(instance_or_patch, name, None)
        if value is None:
            return None
        values.append(value)

    return tuple(values)


def recursive_patch_orm_scalar(
    orm_instance: Any,
    values: BaseModel,
) -> None:
    """Recursively apply a Pydantic patch model onto a SQLAlchemy/SQLModel ORM graph.

    Supports:
    - SQLModel mapped models
    - standard SQLAlchemy declarative models
    - scalar field updates
    - one-to-one / many-to-one relationship updates
    - one-to-many relationship updates by primary key
    - creating child objects when no child primary key is provided

    Primary keys in the patch payload are used only for matching existing ORM
    instances and are never updated onto the ORM object.
    """
    orm_cls = type(orm_instance)

    pk_names = _primary_key_names(orm_cls)
    relationships = _relationship_map(orm_cls)

    for key, value in _provided_values(values).items():
        if key in pk_names:
            continue

        relationship = relationships.get(key)

        if relationship is None:
            setattr(orm_instance, key, value)
            continue

        if value is None:
            setattr(orm_instance, key, None)
            continue

        target_cls = relationship.mapper.class_

        if relationship.uselist:
            if not isinstance(value, list):
                msg = f"Expected list patch for relationship {key!r}"
                raise TypeError(msg)

            existing_children = list(getattr(orm_instance, key) or [])
            target_pk_names = _primary_key_names(target_cls)

            existing_by_identity = {
                identity: child
                for child in existing_children
                if (identity := _identity_tuple(child, target_pk_names)) is not None
            }

            collection = getattr(orm_instance, key)

            for child_patch in value:
                if not isinstance(child_patch, BaseModel):
                    msg = f"Expected BaseModel child patch for relationship {key!r}"
                    raise TypeError(msg)

                child_identity = _identity_tuple(child_patch, target_pk_names)

                if child_identity is None:
                    child_instance = target_cls()
                    collection.append(child_instance)
                else:
                    child_instance = existing_by_identity.get(child_identity)
                    if child_instance is None:
                        msg = f"No existing {target_cls.__name__} found for {key!r} primary key {child_identity!r}"
                        raise ValueError(msg)

                recursive_patch_orm_scalar(child_instance, child_patch)

            continue

        if not isinstance(value, BaseModel):
            msg = f"Expected BaseModel patch for relationship {key!r}"
            raise TypeError(msg)

        current_child = getattr(orm_instance, key)

        if current_child is None:
            current_child = target_cls()
            setattr(orm_instance, key, current_child)

        recursive_patch_orm_scalar(current_child, value)
