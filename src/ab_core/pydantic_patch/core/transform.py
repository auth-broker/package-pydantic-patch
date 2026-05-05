"""Shared recursive model transformation engine."""

from collections.abc import Callable, Mapping
from typing import Annotated, Any, Protocol, get_args, get_origin

from pydantic import BaseModel

from ab_core.pydantic_patch.core.cache import OperationCacheKey
from ab_core.pydantic_patch.core.errors import InvalidDiscriminatorError
from ab_core.pydantic_patch.core.fields import make_field_required
from ab_core.pydantic_patch.core.payload import (
    CreateModelPayload,
    build_payload_from_model,
    create_model_from_payload,
)
from ab_core.pydantic_patch.core.types import (
    extract_discriminator,
    is_annotated,
    is_basemodel_type,
    is_union_origin,
    rebuild_annotated,
    rebuild_union,
    split_annotated,
)


class TransformConfig(Protocol):
    child_models: Mapping[type[BaseModel], Any]


PayloadMutator = Callable[
    [CreateModelPayload, type[BaseModel], Any],
    CreateModelPayload,
]

CacheKeyFactory = Callable[[type[BaseModel], Any, str | None], OperationCacheKey]

_TRANSFORM_MODEL_CACHE: dict[OperationCacheKey, type[BaseModel]] = {}


def with_inherited_child_models(config: Any, child_models: Mapping[type[BaseModel], Any]) -> Any:
    """Return a config whose child model map includes inherited entries.

    Child-specific mappings take precedence over inherited mappings.
    """
    config_child_models = getattr(config, "child_models", None)
    if config_child_models is None:
        return config

    merged_child_models = dict(child_models)
    merged_child_models.update(config_child_models)

    if merged_child_models == config_child_models:
        return config

    return config.model_copy(update={"child_models": merged_child_models})


def default_model_name(source_model: type[BaseModel], suffix: str) -> str:
    return f"{source_model.__name__}{suffix}"


def transform_model(
    source_model: type[BaseModel],
    *,
    config: Any,
    operation: str,
    suffix: str,
    mutate_payload: PayloadMutator,
    make_cache_key: CacheKeyFactory,
    name: str | None = None,
) -> type[BaseModel]:
    """Cached public wrapper for transforming a model."""
    cache_key = make_cache_key(source_model, config, name)
    cached_model = _TRANSFORM_MODEL_CACHE.get(cache_key)
    if cached_model is not None:
        return cached_model

    transformed_model = _transform_model_uncached(
        source_model,
        config=config,
        operation=operation,
        suffix=suffix,
        mutate_payload=mutate_payload,
        make_cache_key=make_cache_key,
        name=name,
    )

    _TRANSFORM_MODEL_CACHE[cache_key] = transformed_model
    return transformed_model


def _transform_model_uncached(
    source_model: type[BaseModel],
    *,
    config: Any,
    operation: str,
    suffix: str,
    mutate_payload: PayloadMutator,
    make_cache_key: CacheKeyFactory,
    name: str | None,
) -> type[BaseModel]:
    payload = build_payload_from_model(source_model)

    # Operation-specific payload changes such as pick/omit happen first.
    payload = mutate_payload(payload, source_model, config)

    # Recursive annotation rewriting happens before partial/required style
    # optionality changes are finalized by individual mutators.
    payload = transform_payload_annotations(
        payload,
        config=config,
        operation=operation,
        suffix=suffix,
        mutate_payload=mutate_payload,
        make_cache_key=make_cache_key,
    )

    model_name = name or default_model_name(source_model, suffix)
    return create_model_from_payload(
        source_model=source_model,
        payload=payload,
        name=model_name,
    )


def transform_payload_annotations(
    payload: CreateModelPayload,
    *,
    config: Any,
    operation: str,
    suffix: str,
    mutate_payload: PayloadMutator,
    make_cache_key: CacheKeyFactory,
) -> CreateModelPayload:
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
            ),
            default,
        )

    return transformed


def transform_annotation(
    annotation: Any,
    *,
    child_models: Mapping[type[BaseModel], Any],
    operation: str,
    suffix: str,
    mutate_payload: PayloadMutator,
    make_cache_key: CacheKeyFactory,
) -> Any:
    """Recursively transform BaseModel references inside an annotation."""
    if is_basemodel_type(annotation):
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
        )

    if is_annotated(annotation):
        inner, metadata = split_annotated(annotation)
        discriminator = extract_discriminator(metadata)
        if discriminator is not None:
            transformed_inner = transform_discriminated_union(
                inner,
                operation=operation,
                child_models=child_models,
                discriminator_key=discriminator.discriminator,
                suffix=suffix,
                mutate_payload=mutate_payload,
                make_cache_key=make_cache_key,
            )
            return Annotated[transformed_inner, *metadata]
        else:
            transformed_inner = transform_annotation(
                inner,
                child_models=child_models,
                operation=operation,
                suffix=suffix,
                mutate_payload=mutate_payload,
                make_cache_key=make_cache_key,
            )
        return rebuild_annotated(transformed_inner, metadata)

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is list:
        return list[
            transform_annotation(
                args[0],
                child_models=child_models,
                operation=operation,
                suffix=suffix,
                mutate_payload=mutate_payload,
                make_cache_key=make_cache_key,
            )
        ]

    if origin is dict:
        key_type, value_type = args
        return dict[
            key_type,
            transform_annotation(
                value_type,
                child_models=child_models,
                operation=operation,
                suffix=suffix,
                mutate_payload=mutate_payload,
                make_cache_key=make_cache_key,
            ),
        ]

    if origin is tuple:
        return tuple[
            tuple(
                transform_annotation(
                    arg,
                    child_models=child_models,
                    operation=operation,
                    suffix=suffix,
                    mutate_payload=mutate_payload,
                    make_cache_key=make_cache_key,
                )
                for arg in args
            )
        ]

    if is_union_origin(origin):
        return rebuild_union(
            tuple(
                transform_annotation(
                    arg,
                    child_models=child_models,
                    operation=operation,
                    suffix=suffix,
                    mutate_payload=mutate_payload,
                    make_cache_key=make_cache_key,
                )
                for arg in args
            )
        )

    return annotation


def transform_discriminated_union(
    union_annotation: Any,
    *,
    operation: str,
    child_models: Mapping[type[BaseModel], Any],
    discriminator_key: str,
    suffix: str,
    mutate_payload: PayloadMutator,
    make_cache_key: CacheKeyFactory,
) -> Any:
    """Transform variants in an Annotated discriminated union."""
    origin = get_origin(union_annotation)
    args = get_args(union_annotation)

    if not is_union_origin(origin):
        return transform_annotation(
            union_annotation,
            child_models=child_models,
            operation=operation,
            suffix=suffix,
            mutate_payload=mutate_payload,
            make_cache_key=make_cache_key,
        )

    transformed_variants: list[Any] = []

    for variant in args:
        if not is_basemodel_type(variant):
            transformed_variants.append(variant)
            continue

        if discriminator_key not in variant.model_fields:
            raise InvalidDiscriminatorError(
                f"Discriminator field {discriminator_key!r} is missing from variant {variant.__name__}."
            )

        child_config = child_models.get(variant)
        if child_config is None:
            transformed_variants.append(variant)
            continue

        effective_child_config = with_inherited_child_models(child_config, child_models)

        validate_discriminator_config(
            variant,
            effective_child_config,
            operation=operation,
            discriminator_key=discriminator_key,
        )

        effective_child_config = force_discriminator_required(
            effective_child_config,
            source_model=variant,
            operation=operation,
            discriminator_key=discriminator_key,
        )

        transformed_variants.append(
            transform_model(
                variant,
                config=effective_child_config,
                operation=operation,
                suffix=suffix,
                mutate_payload=mutate_payload,
                make_cache_key=make_cache_key,
            )
        )

    return rebuild_union(tuple(transformed_variants))


def validate_discriminator_config(
    variant: type[BaseModel],
    config: Any,
    *,
    operation: str,
    discriminator_key: str,
) -> None:
    """Ensure a child config does not break discriminated-union validation."""
    fields = getattr(config, "fields", None)
    include = getattr(config, "include", None)
    exclude = getattr(config, "exclude", None)
    partial = getattr(config, "partial", None)

    if operation == "pick" and fields is not None and discriminator_key not in fields:
        raise InvalidDiscriminatorError(
            f"Discriminator field {discriminator_key!r} must be included when "
            f"picking fields for discriminated-union variant {variant.__name__}."
        )

    if operation == "omit" and fields is not None and discriminator_key in fields:
        raise InvalidDiscriminatorError(
            f"Discriminator field {discriminator_key!r} cannot be omitted from "
            f"discriminated-union variant {variant.__name__}."
        )

    if operation == "partial" and fields is not None and discriminator_key in fields:
        raise InvalidDiscriminatorError(
            f"Discriminator field {discriminator_key!r} cannot be partialed for "
            f"discriminated-union variant {variant.__name__}."
        )

    if operation == "patch":
        if include is not None and discriminator_key not in include:
            raise InvalidDiscriminatorError(
                f"Discriminator field {discriminator_key!r} must be included when "
                f"including fields for discriminated-union variant {variant.__name__}."
            )

        if exclude is not None and discriminator_key in exclude:
            raise InvalidDiscriminatorError(
                f"Discriminator field {discriminator_key!r} cannot be excluded from "
                f"discriminated-union variant {variant.__name__}."
            )

        if partial is not None and discriminator_key in partial:
            raise InvalidDiscriminatorError(
                f"Discriminator field {discriminator_key!r} cannot be partial for "
                f"discriminated-union variant {variant.__name__}."
            )


def force_discriminator_required(
    config: Any,
    *,
    source_model: type[BaseModel],
    operation: str,
    discriminator_key: str,
) -> Any:
    """Keep discriminator fields usable for discriminated-union validation."""
    if operation == "partial" and hasattr(config, "fields"):
        fields = config.fields

        if fields is None:
            return config.model_copy(
                update={
                    "fields": frozenset(
                        field_name for field_name in source_model.model_fields if field_name != discriminator_key
                    )
                }
            )

        return config

    if operation == "patch" and hasattr(config, "partial") and hasattr(config, "required"):
        partial = config.partial
        required = config.required or frozenset()

        updates: dict[str, Any] = {
            "required": frozenset(set(required) | {discriminator_key}),
        }

        if partial is not None:
            updates["partial"] = frozenset(set(partial) - {discriminator_key})

        return config.model_copy(update=updates)

    return config


def make_payload_discriminator_required(
    payload: CreateModelPayload,
    *,
    discriminator_key: str,
) -> CreateModelPayload:
    if discriminator_key not in payload:
        return payload

    annotation, default = payload[discriminator_key]
    payload = dict(payload)
    payload[discriminator_key] = make_field_required(annotation, default)
    return payload
