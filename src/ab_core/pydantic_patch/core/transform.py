"""Shared recursive model transformation engine."""

from collections.abc import Callable, Mapping
from functools import reduce
from operator import or_
from typing import Annotated, ForwardRef, Protocol, Self, TypeVar, get_args, get_origin

from pydantic import BaseModel

from ab_core.pydantic_patch.core.cache import OperationCacheKey, OperationName
from ab_core.pydantic_patch.core.payload import (
    CreateModelPayload,
    build_payload_from_model,
    create_model_from_payload,
)
from ab_core.pydantic_patch.core.type_hints import assert_no_forward_refs


class TransformConfig(Protocol):
    """Protocol for operation config models used in recursive transforms."""

    child_models: Mapping[type[BaseModel], Self]

    def model_copy(
        self,
        *,
        update: Mapping[str, object] | None = None,
        deep: bool = False,
    ) -> Self:
        """Return a copy of the config, optionally with updated values."""
        ...


ConfigT = TypeVar("ConfigT", bound=TransformConfig)

type PayloadMutator[ConfigT: TransformConfig] = Callable[
    [CreateModelPayload, type[BaseModel], ConfigT],
    CreateModelPayload,
]

type CacheKeyFactory[ConfigT: TransformConfig] = Callable[
    [type[BaseModel], ConfigT, str | None],
    OperationCacheKey,
]

type DiscriminatorChildConfigPreparer[ConfigT: TransformConfig] = Callable[
    [type[BaseModel], ConfigT, str],
    ConfigT,
]

_TRANSFORM_MODEL_CACHE: dict[OperationCacheKey, type[BaseModel]] = {}
_TRANSFORM_BUILD_STACK: list[tuple[type[BaseModel], OperationName, str, str | None]] = []
_TRANSFORM_BUILD_NAMESPACE: dict[str, type[BaseModel]] = {}
_TRANSFORM_BUILD_CREATED_MODELS: list[type[BaseModel]] = []


def prepare_discriminator_child_config_default[ConfigT: TransformConfig](
    _source_model: type[BaseModel],
    config: ConfigT,
    _discriminator_key: str,
) -> ConfigT:
    """Return child config unchanged for discriminator-aware transforms."""
    return config


def with_inherited_child_models(
    config: ConfigT,
    child_models: Mapping[type[BaseModel], ConfigT],
) -> ConfigT:
    """Merge inherited child model config into a specific child config."""
    merged_child_models = dict(child_models)
    merged_child_models.update(config.child_models)

    if merged_child_models == config.child_models:
        return config

    return config.model_copy(update={"child_models": merged_child_models})


def default_model_name(source_model: type[BaseModel], suffix: str) -> str:
    """Build the default transformed model name."""
    return f"{source_model.__name__}{suffix}"


def transformed_model_name(source_model: type[BaseModel], suffix: str, name: str | None) -> str:
    """Return the concrete transformed model name."""
    return name or default_model_name(source_model, suffix)


def transform_build_key(
    source_model: type[BaseModel],
    operation: OperationName,
    suffix: str,
    name: str | None,
) -> tuple[type[BaseModel], OperationName, str, str | None]:
    """Return the key used to identify an in-progress transformed model."""
    return (source_model, operation, suffix, name)


def find_active_build_name(
    source_model: type[BaseModel],
    operation: OperationName,
    suffix: str,
) -> str | None:
    """Return the active generated model name for a recursive transform."""
    for active_source_model, active_operation, active_suffix, active_name in reversed(_TRANSFORM_BUILD_STACK):
        if active_source_model is source_model and active_operation == operation and active_suffix == suffix:
            return transformed_model_name(active_source_model, active_suffix, active_name)

    return None


def rebuild_created_models() -> None:
    """Resolve generated-model forward references created during recursion."""
    if not _TRANSFORM_BUILD_NAMESPACE:
        return

    type_namespace = dict(_TRANSFORM_BUILD_NAMESPACE)

    for model in _TRANSFORM_BUILD_CREATED_MODELS:
        model.model_rebuild(force=True, _types_namespace=type_namespace)


def build_transformed_model(
    source_model: type[BaseModel],
    *,
    config: ConfigT,
    operation: OperationName,
    suffix: str,
    mutate_payload: PayloadMutator[ConfigT],
    make_cache_key: CacheKeyFactory[ConfigT],
    prepare_discriminator_child_config: DiscriminatorChildConfigPreparer[ConfigT],
    name: str | None,
    use_cache: bool,
) -> type[BaseModel]:
    """Build a transformed model and recursively transform nested annotations."""
    build_key = transform_build_key(source_model, operation, suffix, name)
    is_root_build = not _TRANSFORM_BUILD_STACK
    _TRANSFORM_BUILD_STACK.append(build_key)

    try:
        assert_no_forward_refs(source_model)

        payload = build_payload_from_model(source_model)
        payload = mutate_payload(payload, source_model, config)

        payload = transform_payload_annotations(
            payload,
            config=config,
            operation=operation,
            suffix=suffix,
            mutate_payload=mutate_payload,
            make_cache_key=make_cache_key,
            prepare_discriminator_child_config=prepare_discriminator_child_config,
            use_cache=use_cache,
        )

        model_name = transformed_model_name(source_model, suffix, name)
        transformed_model = create_model_from_payload(
            source_model=source_model,
            payload=payload,
            name=model_name,
        )
        _TRANSFORM_BUILD_NAMESPACE[model_name] = transformed_model
        _TRANSFORM_BUILD_CREATED_MODELS.append(transformed_model)

        return transformed_model
    finally:
        _TRANSFORM_BUILD_STACK.pop()

        if is_root_build:
            try:
                rebuild_created_models()
            finally:
                _TRANSFORM_BUILD_NAMESPACE.clear()
                _TRANSFORM_BUILD_CREATED_MODELS.clear()


def transform_model_cached(
    source_model: type[BaseModel],
    *,
    config: ConfigT,
    operation: OperationName,
    suffix: str,
    mutate_payload: PayloadMutator[ConfigT],
    make_cache_key: CacheKeyFactory[ConfigT],
    prepare_discriminator_child_config: DiscriminatorChildConfigPreparer[ConfigT],
    name: str | None = None,
) -> type[BaseModel]:
    """Transform a model using and populating the shared operation cache."""
    cache_key = make_cache_key(source_model, config, name)
    cached_model = _TRANSFORM_MODEL_CACHE.get(cache_key)
    if cached_model is not None:
        return cached_model

    transformed_model = build_transformed_model(
        source_model,
        config=config,
        operation=operation,
        suffix=suffix,
        mutate_payload=mutate_payload,
        make_cache_key=make_cache_key,
        prepare_discriminator_child_config=prepare_discriminator_child_config,
        name=name,
        use_cache=True,
    )

    _TRANSFORM_MODEL_CACHE[cache_key] = transformed_model
    return transformed_model


def transform_model(
    source_model: type[BaseModel],
    *,
    config: ConfigT,
    operation: OperationName,
    suffix: str,
    mutate_payload: PayloadMutator[ConfigT],
    make_cache_key: CacheKeyFactory[ConfigT],
    prepare_discriminator_child_config: DiscriminatorChildConfigPreparer[
        ConfigT
    ] = prepare_discriminator_child_config_default,
    name: str | None = None,
    use_cache: bool = True,
) -> type[BaseModel]:
    """Transform a model according to an operation configuration."""
    active_model_name = find_active_build_name(source_model, operation, suffix)
    if active_model_name is not None:
        return ForwardRef(active_model_name)

    if use_cache:
        return transform_model_cached(
            source_model,
            config=config,
            operation=operation,
            suffix=suffix,
            mutate_payload=mutate_payload,
            make_cache_key=make_cache_key,
            prepare_discriminator_child_config=prepare_discriminator_child_config,
            name=name,
        )

    return build_transformed_model(
        source_model,
        config=config,
        operation=operation,
        suffix=suffix,
        mutate_payload=mutate_payload,
        make_cache_key=make_cache_key,
        prepare_discriminator_child_config=prepare_discriminator_child_config,
        name=name,
        use_cache=False,
    )


def transform_payload_annotations(
    payload: CreateModelPayload,
    *,
    config: ConfigT,
    operation: OperationName,
    suffix: str,
    mutate_payload: PayloadMutator[ConfigT],
    make_cache_key: CacheKeyFactory[ConfigT],
    prepare_discriminator_child_config: DiscriminatorChildConfigPreparer[ConfigT],
    use_cache: bool,
) -> CreateModelPayload:
    """Recursively transform all field annotations in a payload."""
    transformed: CreateModelPayload = {}

    for field_name, (annotation, default) in payload.items():
        transformed[field_name] = (
            transform_annotation(
                annotation,
                child_models=config.child_models,
                operation=operation,
                suffix=suffix,
                mutate_payload=mutate_payload,
                make_cache_key=make_cache_key,
                prepare_discriminator_child_config=prepare_discriminator_child_config,
                use_cache=use_cache,
            ),
            default,
        )

    return transformed


def transform_annotation(
    annotation: object,
    *,
    child_models: Mapping[type[BaseModel], ConfigT],
    operation: OperationName,
    suffix: str,
    mutate_payload: PayloadMutator[ConfigT],
    make_cache_key: CacheKeyFactory[ConfigT],
    prepare_discriminator_child_config: DiscriminatorChildConfigPreparer[ConfigT],
    use_cache: bool,
) -> object:
    """Transform a single annotation, handling models, containers, and unions."""
    origin = get_origin(annotation)
    args = get_args(annotation)

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        child_config = child_models.get(annotation)
        if child_config is None:
            return annotation

        effective_child_config = with_inherited_child_models(child_config, child_models)
        return transform_model(
            annotation,
            config=effective_child_config,
            operation=operation,
            suffix=suffix,
            mutate_payload=mutate_payload,
            make_cache_key=make_cache_key,
            prepare_discriminator_child_config=prepare_discriminator_child_config,
            use_cache=use_cache,
        )

    if origin is Annotated:
        base_annotation, *metadata = args
        discriminator = next(
            (item for item in metadata if hasattr(item, "discriminator")),
            None,
        )

        if discriminator is not None:
            transformed_base = transform_discriminated_union(
                base_annotation,
                child_models=child_models,
                operation=operation,
                suffix=suffix,
                mutate_payload=mutate_payload,
                make_cache_key=make_cache_key,
                prepare_discriminator_child_config=prepare_discriminator_child_config,
                discriminator_key=discriminator.discriminator,
                use_cache=use_cache,
            )
        else:
            transformed_base = transform_annotation(
                base_annotation,
                child_models=child_models,
                operation=operation,
                suffix=suffix,
                mutate_payload=mutate_payload,
                make_cache_key=make_cache_key,
                prepare_discriminator_child_config=prepare_discriminator_child_config,
                use_cache=use_cache,
            )

        return Annotated[transformed_base, *metadata]

    if origin in (list, set, frozenset):
        transformed_args = tuple(
            transform_annotation(
                arg,
                child_models=child_models,
                operation=operation,
                suffix=suffix,
                mutate_payload=mutate_payload,
                make_cache_key=make_cache_key,
                prepare_discriminator_child_config=prepare_discriminator_child_config,
                use_cache=use_cache,
            )
            for arg in args
        )
        return origin[transformed_args]

    if origin is dict:
        key_type, value_type = args
        transformed_value_type = transform_annotation(
            value_type,
            child_models=child_models,
            operation=operation,
            suffix=suffix,
            mutate_payload=mutate_payload,
            make_cache_key=make_cache_key,
            prepare_discriminator_child_config=prepare_discriminator_child_config,
            use_cache=use_cache,
        )
        return dict[key_type, transformed_value_type]

    if origin in (type(None) | str).__class__.__mro__:
        return annotation

    if args:
        transformed_args = tuple(
            transform_annotation(
                arg,
                child_models=child_models,
                operation=operation,
                suffix=suffix,
                mutate_payload=mutate_payload,
                make_cache_key=make_cache_key,
                prepare_discriminator_child_config=prepare_discriminator_child_config,
                use_cache=use_cache,
            )
            for arg in args
        )
        try:
            return origin[transformed_args]
        except TypeError:
            return annotation

    return annotation


def transform_discriminated_union(
    union_annotation: object,
    *,
    child_models: Mapping[type[BaseModel], ConfigT],
    operation: OperationName,
    suffix: str,
    mutate_payload: PayloadMutator[ConfigT],
    make_cache_key: CacheKeyFactory[ConfigT],
    prepare_discriminator_child_config: DiscriminatorChildConfigPreparer[ConfigT],
    discriminator_key: str,
    use_cache: bool,
) -> object:
    """Transform discriminated union variants while preserving discriminator rules."""
    transformed_variants: list[object] = []

    for variant in get_args(union_annotation):
        if not isinstance(variant, type) or not issubclass(variant, BaseModel):
            transformed_variants.append(variant)
            continue

        child_config = child_models.get(variant)
        if child_config is None:
            transformed_variants.append(variant)
            continue

        child_config = prepare_discriminator_child_config(
            variant,
            child_config,
            discriminator_key,
        )
        child_config = with_inherited_child_models(child_config, child_models)

        transformed_variants.append(
            transform_model(
                variant,
                config=child_config,
                operation=operation,
                suffix=suffix,
                mutate_payload=mutate_payload,
                make_cache_key=make_cache_key,
                prepare_discriminator_child_config=prepare_discriminator_child_config,
                use_cache=use_cache,
            )
        )

    return reduce(or_, transformed_variants)
