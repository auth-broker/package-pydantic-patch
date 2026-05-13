"""PATCH support for SQLAlchemy/SQLModel ORM graphs."""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from ab_core.pydantic_patch.core.type_hints import assert_no_forward_refs

if TYPE_CHECKING:
    from sqlalchemy.orm import RelationshipProperty
else:
    RelationshipProperty = object

try:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.exc import NoInspectionAvailable
except ImportError:  # pragma: no cover
    sa_inspect = None  # ty:ignore[invalid-assignment]

    class NoInspectionAvailable(Exception):
        pass


def _provided_values(model: BaseModel) -> dict[str, object]:
    return {name: getattr(model, name) for name in model.model_fields_set}


def _mapper_for(model_cls: type[Any]) -> Any | None:
    if sa_inspect is None:
        return None

    try:
        return sa_inspect(model_cls).mapper
    except NoInspectionAvailable:
        return None


def _is_orm_mapped(model_cls: type[Any]) -> bool:
    return _mapper_for(model_cls) is not None


def _primary_key_names(model_cls: type[Any]) -> set[str]:
    mapper = _mapper_for(model_cls)
    if mapper is None:
        raise RuntimeError('SQLAlchemy support is not installed. Install it with: pip install "pydantic-patch[orm]"')

    return {column.key for column in mapper.primary_key}


def _relationship_map(model_cls: type[Any]) -> dict[str, RelationshipProperty]:
    mapper = _mapper_for(model_cls)
    if mapper is None:
        raise RuntimeError('SQLAlchemy support is not installed. Install it with: pip install "pydantic-patch[orm]"')

    return {relationship.key: relationship for relationship in mapper.relationships}


def _scalar_attribute_names(model_cls: type[Any]) -> set[str]:
    mapper = _mapper_for(model_cls)
    if mapper is None:
        raise RuntimeError('SQLAlchemy support is not installed. Install it with: pip install "pydantic-patch[orm]"')

    return {column.key for column in mapper.column_attrs}


def _identity_tuple(
    instance_or_patch: Any,
    pk_names: set[str],
) -> tuple[object, ...] | None:
    values: list[object] = []

    for name in pk_names:
        value = getattr(instance_or_patch, name, None)
        if value is None:
            return None
        values.append(value)

    return tuple(values)


def _recursive_patch_pydantic_scalar(
    instance: BaseModel,
    values: BaseModel,
) -> None:
    target_fields = set(instance.model_fields)

    for key, value in _provided_values(values).items():
        if key not in target_fields:
            continue

        current_value = getattr(instance, key, None)

        if isinstance(current_value, BaseModel) and isinstance(value, BaseModel):
            recursive_patch_scalar(current_value, value)
            continue

        if isinstance(current_value, list) and isinstance(value, list):
            setattr(instance, key, value)
            continue

        setattr(instance, key, value)


def _recursive_patch_orm_scalar(
    orm_instance: Any,
    values: BaseModel,
) -> None:
    """Recursively apply a Pydantic patch model onto a SQLAlchemy/SQLModel ORM graph."""
    orm_cls = type(orm_instance)

    pk_names = _primary_key_names(orm_cls)
    relationships = _relationship_map(orm_cls)
    scalar_attributes = _scalar_attribute_names(orm_cls)

    for key, value in _provided_values(values).items():
        if key in pk_names:
            continue

        relationship = relationships.get(key)

        if relationship is None:
            if key not in scalar_attributes:
                continue
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

                recursive_patch_scalar(child_instance, child_patch)

            continue

        if not isinstance(value, BaseModel):
            msg = f"Expected BaseModel patch for relationship {key!r}"
            raise TypeError(msg)

        current_child = getattr(orm_instance, key)

        if current_child is None:
            current_child = target_cls()
            setattr(orm_instance, key, current_child)

        recursive_patch_scalar(current_child, value)


def recursive_patch_scalar(
    instance: Any,
    values: BaseModel,
) -> None:
    """Recursively apply a Pydantic patch model onto Pydantic or ORM object graphs."""
    assert_no_forward_refs(type(instance))
    assert_no_forward_refs(type(values))

    if _is_orm_mapped(type(instance)):
        _recursive_patch_orm_scalar(instance, values)
        return

    if isinstance(instance, BaseModel):
        _recursive_patch_pydantic_scalar(instance, values)
        return

    msg = f"Unsupported patch target type: {type(instance).__name__}"
    raise TypeError(msg)


def recursive_patch_orm_scalar(
    orm_instance: Any,
    values: BaseModel,
) -> None:
    """Backward-compatible alias for recursive_patch_scalar."""
    recursive_patch_scalar(orm_instance, values)
