"""PATCH support for SQLAlchemy/SQLModel ORM graphs."""

from dataclasses import dataclass, field
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
    from sqlalchemy.orm import MANYTOONE
    from sqlalchemy.orm.attributes import NO_VALUE
except ImportError:  # pragma: no cover
    sa_inspect = None  # ty:ignore[invalid-assignment]
    MANYTOONE = None  # ty:ignore[invalid-assignment]
    NO_VALUE = object()  # ty:ignore[invalid-assignment]

    class NoInspectionAvailable(Exception):
        """Fallback SQLAlchemy inspection error when SQLAlchemy is unavailable."""

        pass


@dataclass
class OrmPatchContext:
    identity_map: dict[tuple[type[Any], tuple[object, ...]], Any] = field(default_factory=dict)


def _provided_values(model: BaseModel) -> dict[str, object]:
    return {name: getattr(model, name) for name in type(model).model_fields if name in model.model_fields_set}


def _patch_scalar_value(
    instance: Any,
    key: str,
    value: Any,
    *,
    copy_nested_basemodel: bool = False,
) -> None:
    current_value = getattr(instance, key, None)

    if isinstance(current_value, BaseModel) and isinstance(value, BaseModel):
        target_value = current_value.model_copy(deep=True) if copy_nested_basemodel else current_value

        recursive_patch_scalar(target_value, value)

        # Important for ORM scalar JSON/Pydantic fields:
        # reassign the merged current value so SQLAlchemy sees the column changed.
        setattr(instance, key, target_value)
        return

    setattr(instance, key, value)


def _mapper_for(model_cls: type[Any]) -> Any | None:
    if sa_inspect is None:
        return None

    try:
        return sa_inspect(model_cls).mapper
    except NoInspectionAvailable:
        return None


def _is_orm_mapped(model_cls: type[Any]) -> bool:
    return _mapper_for(model_cls) is not None


def _primary_key_names(model_cls: type[Any]) -> tuple[str, ...]:
    mapper = _mapper_for(model_cls)
    if mapper is None:
        raise RuntimeError('SQLAlchemy support is not installed. Install it with: pip install "pydantic-patch[orm]"')

    return tuple(column.key for column in mapper.primary_key)


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
    pk_names: tuple[str, ...],
) -> tuple[object, ...] | None:
    values: list[object] = []

    for name in pk_names:
        value = getattr(instance_or_patch, name, None)
        if value is None:
            return None
        values.append(value)

    return tuple(values)


def _identity_key(instance: Any) -> tuple[type[Any], tuple[object, ...]] | None:
    mapper = _mapper_for(type(instance))
    if mapper is None:
        return None

    pk_names = _primary_key_names(type(instance))
    identity = _identity_tuple(instance, pk_names)
    if identity is None:
        return None

    return mapper.class_, identity


def _index_loaded_graph(
    instance: Any,
    context: OrmPatchContext,
    seen: set[int] | None = None,
) -> None:
    if seen is None:
        seen = set()

    if id(instance) in seen:
        return

    seen.add(id(instance))

    key = _identity_key(instance)
    if key is not None:
        context.identity_map[key] = instance

    mapper = _mapper_for(type(instance))
    if mapper is None or sa_inspect is None:
        return

    state = sa_inspect(instance)

    for relationship in mapper.relationships:
        attr_state = state.attrs[relationship.key]
        value = attr_state.loaded_value

        if value is NO_VALUE or value is None:
            continue

        if relationship.uselist:
            for child in value:
                _index_loaded_graph(child, context, seen)
            continue

        _index_loaded_graph(value, context, seen)


def _many_to_one_relationship_for_fk_key(
    orm_cls: type[Any],
    fk_key: str,
) -> RelationshipProperty | None:
    mapper = _mapper_for(orm_cls)
    if mapper is None:
        return None

    relationships = []

    for relationship in mapper.relationships:
        if relationship.direction is not MANYTOONE:
            continue

        matching_columns = [column for column in relationship.local_columns if column.key == fk_key]
        if not matching_columns:
            continue

        if any(not column.foreign_keys for column in matching_columns):
            continue

        relationships.append(relationship)

    if len(relationships) != 1:
        return None

    return relationships[0]


def _patch_foreign_key_relationship_if_possible(
    orm_instance: Any,
    key: str,
    value: Any,
    context: OrmPatchContext,
) -> bool:
    relationship = _many_to_one_relationship_for_fk_key(type(orm_instance), key)
    if relationship is None:
        return False

    target_cls = relationship.mapper.class_
    target_pk_names = _primary_key_names(target_cls)

    if len(target_pk_names) != 1:
        return False

    if value is None:
        setattr(orm_instance, relationship.key, None)
        setattr(orm_instance, key, None)
        return True

    target = context.identity_map.get((target_cls, (value,)))
    if target is None:
        msg = (
            f"Foreign key patch for {type(orm_instance).__name__}.{key} points to "
            f"{target_cls.__name__} primary key {(value,)!r}, which is not loaded in the current ORM graph"
        )
        raise ValueError(msg)

    # Set the relationship so SQLAlchemy updates the in-memory graph and inverse collections.
    setattr(orm_instance, relationship.key, target)

    # Also set the scalar FK so the in-memory column value reflects the patch immediately,
    # even before the object is flushed in a Session.
    setattr(orm_instance, key, value)

    return True


def _recursive_patch_pydantic_scalar(
    instance: BaseModel,
    values: BaseModel,
) -> None:
    target_fields = set(type(instance).model_fields)

    for key, value in _provided_values(values).items():
        if key not in target_fields:
            continue

        current_value = getattr(instance, key, None)

        if isinstance(current_value, list) and isinstance(value, list):
            setattr(instance, key, value)
            continue

        _patch_scalar_value(instance, key, value)


def _recursive_patch_orm_scalar(
    orm_instance: Any,
    values: BaseModel,
    context: OrmPatchContext,
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
            if not _patch_foreign_key_relationship_if_possible(orm_instance, key, value, context):
                _patch_scalar_value(
                    orm_instance,
                    key,
                    value,
                    copy_nested_basemodel=True,
                )
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
                        child_instance = context.identity_map.get((target_cls, child_identity))
                    if child_instance is None:
                        msg = f"No existing {target_cls.__name__} found for {key!r} primary key {child_identity!r}"
                        raise ValueError(msg)

                _recursive_patch_orm_scalar(child_instance, child_patch, context)

            continue

        if not isinstance(value, BaseModel):
            msg = f"Expected BaseModel patch for relationship {key!r}"
            raise TypeError(msg)

        current_child = getattr(orm_instance, key)

        if current_child is None:
            current_child = target_cls()
            setattr(orm_instance, key, current_child)

        _recursive_patch_orm_scalar(current_child, value, context)


def recursive_patch_scalar(
    instance: Any,
    values: BaseModel,
) -> None:
    """Recursively apply a Pydantic patch model onto Pydantic or ORM object graphs."""
    assert_no_forward_refs(type(instance))
    assert_no_forward_refs(type(values))

    if _is_orm_mapped(type(instance)):
        context = OrmPatchContext()
        _index_loaded_graph(instance, context)
        _recursive_patch_orm_scalar(instance, values, context)
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
