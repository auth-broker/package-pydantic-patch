"""Null operation implementation.

Null creates a plain Pydantic BaseModel equivalent of a source model without
performing pick/omit/partial/required/patch field manipulation.

This is useful for SQLModel response/dump schemas because SQLModel.model_dump()
does not include relationship attributes, while the generated Null model does.
"""

from collections.abc import Mapping
from typing import TypeVar, get_args, get_origin

from pydantic import BaseModel
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import NoInspectionAvailable

from ab_core.pydantic_patch.core.cache import OperationCacheKey, sort_child_keys
from ab_core.pydantic_patch.core.payload import CreateModelPayload, build_payload_from_model
from ab_core.pydantic_patch.core.transform import transform_model
from ab_core.pydantic_patch.core.type_hints import assert_no_forward_refs
from ab_core.pydantic_patch.null.config import NullConfig

T = TypeVar("T", bound=BaseModel)


def apply_null_payload(
    payload: CreateModelPayload,
    _model: type[BaseModel],
    config: NullConfig,
) -> CreateModelPayload:
    """Return the source payload with configured relationships removed."""
    return {
        field_name: field_definition
        for field_name, field_definition in payload.items()
        if field_name not in config.exclude_relationships
    }


def make_null_cache_key(
    source_model: type[BaseModel],
    config: NullConfig,
    name: str | None,
) -> OperationCacheKey:
    """Build a stable cache key for null transformations."""
    return make_null_cache_key_inner(
        source_model,
        config,
        name,
        seen=frozenset(),
    )


def make_null_cache_key_inner(
    source_model: type[BaseModel],
    config: NullConfig,
    name: str | None,
    *,
    seen: frozenset[type[BaseModel]],
) -> OperationCacheKey:
    """Build a cache key without recursing through cyclic child configs."""
    next_seen = seen | {source_model}
    child_keys = {
        child_model: make_null_cache_key_inner(
            child_model,
            child_config,
            None,
            seen=next_seen,
        )
        for child_model, child_config in config.child_models.items()
        if child_model not in seen
    }

    return OperationCacheKey(
        source_model=source_model,
        operation="null",
        fields=tuple(sorted(config.exclude_relationships)),
        child_models=sort_child_keys(child_keys),
        name=name,
    )


def iter_basemodel_types(annotation: object) -> set[type[BaseModel]]:
    """Return BaseModel subclasses contained in an annotation."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return {annotation}

    model_types: set[type[BaseModel]] = set()

    for arg in get_args(annotation):
        model_types.update(iter_basemodel_types(arg))

    origin = get_origin(annotation)

    if origin is not None:
        for arg in get_args(annotation):
            model_types.update(iter_basemodel_types(arg))

    return model_types


def get_relationships(model: type[BaseModel]):
    """Return SQLAlchemy relationships for a mapped model."""
    try:
        return sa_inspect(model).relationships
    except NoInspectionAvailable:
        return ()


def relationship_creates_backref_cycle(
    *,
    relationship,
    current_model: type[BaseModel],
    ancestor_models: tuple[type[BaseModel], ...],
) -> bool:
    """Return whether a relationship points back to an ancestor model."""
    target_model = relationship.mapper.class_

    if target_model not in ancestor_models:
        return False

    is_self_relationship = target_model is current_model
    is_one_to_many = relationship.direction.name == "ONETOMANY"

    if is_self_relationship and is_one_to_many:
        return False

    return True


def discover_relationship_excludes(
    model: type[BaseModel],
    *,
    ancestor_models: tuple[type[BaseModel], ...],
) -> frozenset[str]:
    """Discover relationship names that should be excluded to avoid cycles."""
    excluded: set[str] = set()

    for relationship in get_relationships(model):
        if relationship_creates_backref_cycle(
            relationship=relationship,
            current_model=model,
            ancestor_models=ancestor_models,
        ):
            excluded.add(relationship.key)

    return frozenset(excluded)


def merge_null_configs(
    left: NullConfig,
    right: NullConfig,
) -> NullConfig:
    """Merge two null configs for the same model."""
    return NullConfig(
        child_models=merge_child_models(left.child_models, right.child_models),
        exclude_relationships=left.exclude_relationships | right.exclude_relationships,
    )


def discover_null_child_models(
    model: type[BaseModel],
    *,
    ancestor_models: tuple[type[BaseModel], ...] = (),
) -> dict[type[BaseModel], NullConfig]:
    """Discover nested BaseModel/SQLModel children for recursive null conversion."""
    if model in ancestor_models:
        return {}

    payload = build_payload_from_model(model)
    child_models: dict[type[BaseModel], NullConfig] = {}
    next_ancestor_models = (*ancestor_models, model)

    for annotation, _default in payload.values():
        for child_model in iter_basemodel_types(annotation):
            exclude_relationships = discover_relationship_excludes(
                child_model,
                ancestor_models=next_ancestor_models,
            )

            nested_child_models = discover_null_child_models(
                child_model,
                ancestor_models=next_ancestor_models,
            )

            child_config = NullConfig(
                child_models=nested_child_models,
                exclude_relationships=exclude_relationships,
            )

            existing_config = child_models.get(child_model)
            if existing_config is not None:
                child_config = merge_null_configs(existing_config, child_config)

            child_models[child_model] = child_config

    return child_models


def merge_child_models(
    discovered: Mapping[type[BaseModel], NullConfig],
    explicit: Mapping[type[BaseModel], NullConfig],
) -> dict[type[BaseModel], NullConfig]:
    """Merge explicit child configs over auto-discovered child configs."""
    merged = dict(discovered)
    merged.update(explicit)
    return merged


def create_null_model(
    model: type[BaseModel],
    *,
    config: NullConfig | None = None,
    child_models: dict[type[BaseModel], NullConfig] | None = None,
    exclude_relationships: frozenset[str] | set[str] | None = None,
    name: str | None = None,
    use_cache: bool = True,
) -> type[BaseModel]:
    """Create a plain Pydantic model from a BaseModel/SQLModel source model.

    The generated model keeps the same fields and recursively converts nested
    configured or auto-discovered BaseModel/SQLModel annotations into Null
    models as well.
    """
    explicit_config = config or NullConfig(
        child_models=child_models or {},
        exclude_relationships=frozenset(exclude_relationships or set()),
    )

    assert_no_forward_refs(model)

    discovered_exclude_relationships = discover_relationship_excludes(
        model,
        ancestor_models=(model,),
    )
    discovered_child_models = discover_null_child_models(model)

    effective_config = explicit_config.model_copy(
        update={
            "child_models": merge_child_models(
                discovered_child_models,
                explicit_config.child_models,
            ),
            "exclude_relationships": (discovered_exclude_relationships | explicit_config.exclude_relationships),
        }
    )

    return transform_model(
        model,
        config=effective_config,
        operation="null",
        suffix="Null",
        mutate_payload=apply_null_payload,
        make_cache_key=make_null_cache_key,
        name=name,
        use_cache=use_cache,
    )
