"""Patch aggregation implementation."""

from collections.abc import Collection

from pydantic import BaseModel

from ab_core.pydantic_patch.core.cache import (
    OperationCacheKey,
    normalise_field_key,
    sort_child_keys,
)
from ab_core.pydantic_patch.core.config import normalise_fields
from ab_core.pydantic_patch.core.fields import (
    make_field_optional,
    make_field_required,
    validate_fields_exist_in_payload,
    validate_fields_exist_on_model,
)
from ab_core.pydantic_patch.core.payload import (
    CreateModelPayload,
    build_payload_from_model,
    create_model_from_payload,
)
from ab_core.pydantic_patch.core.transform import transform_payload_annotations
from ab_core.pydantic_patch.patch.config import PatchConfig


_PATCH_MODEL_CACHE: dict[OperationCacheKey, type[BaseModel]] = {}


def apply_patch_payload(
    payload: CreateModelPayload,
    model: type[BaseModel],
    config: PatchConfig,
) -> CreateModelPayload:
    """Apply all non-recursive patch operations to a payload.

    Ordering:
    1. include
    2. exclude
    3. partial
    4. required

    Recursive annotation rewriting is performed outside this function between
    exclude and partial.
    """
    validate_fields_exist_on_model(model, config.include, operation="include")
    validate_fields_exist_on_model(model, config.exclude, operation="exclude")
    validate_fields_exist_on_model(model, config.partial, operation="partial")
    validate_fields_exist_on_model(model, config.required, operation="required")

    if config.include is not None:
        payload = {
            field_name: field_payload for field_name, field_payload in payload.items() if field_name in config.include
        }

    if config.exclude:
        payload = {
            field_name: field_payload
            for field_name, field_payload in payload.items()
            if field_name not in config.exclude
        }

    validate_fields_exist_in_payload(payload, config.partial, model=model, operation="partial")
    validate_fields_exist_in_payload(payload, config.required, model=model, operation="required")

    fields_to_partial = set(payload) if config.partial is None else set(config.partial)
    payload = {
        field_name: make_field_optional(annotation, default)
        if field_name in fields_to_partial
        else (annotation, default)
        for field_name, (annotation, default) in payload.items()
    }

    if config.required:
        payload = {
            field_name: make_field_required(annotation, default)
            if field_name in config.required
            else (annotation, default)
            for field_name, (annotation, default) in payload.items()
        }

    return payload


def apply_patch_scope_payload(
    payload: CreateModelPayload,
    model: type[BaseModel],
    config: PatchConfig,
) -> CreateModelPayload:
    """Apply only include/exclude before recursive annotation rewriting."""
    validate_fields_exist_on_model(model, config.include, operation="include")
    validate_fields_exist_on_model(model, config.exclude, operation="exclude")

    if config.include is not None:
        payload = {
            field_name: field_payload for field_name, field_payload in payload.items() if field_name in config.include
        }

    if config.exclude:
        payload = {
            field_name: field_payload
            for field_name, field_payload in payload.items()
            if field_name not in config.exclude
        }

    return payload


def apply_patch_presence_payload(
    payload: CreateModelPayload,
    model: type[BaseModel],
    config: PatchConfig,
) -> CreateModelPayload:
    """Apply partial/required after recursive annotation rewriting."""
    validate_fields_exist_on_model(model, config.partial, operation="partial")
    validate_fields_exist_on_model(model, config.required, operation="required")
    validate_fields_exist_in_payload(payload, config.partial, model=model, operation="partial")
    validate_fields_exist_in_payload(payload, config.required, model=model, operation="required")

    fields_to_partial = set(payload) if config.partial is None else set(config.partial)
    payload = {
        field_name: make_field_optional(annotation, default)
        if field_name in fields_to_partial
        else (annotation, default)
        for field_name, (annotation, default) in payload.items()
    }

    if config.required:
        payload = {
            field_name: make_field_required(annotation, default)
            if field_name in config.required
            else (annotation, default)
            for field_name, (annotation, default) in payload.items()
        }

    return payload


def make_patch_cache_key(
    source_model: type[BaseModel],
    config: PatchConfig,
    name: str | None,
) -> OperationCacheKey:
    child_keys = {
        child_model: make_patch_cache_key(child_model, child_config, None)
        for child_model, child_config in config.child_models.items()
    }
    return OperationCacheKey(
        source_model=source_model,
        operation="patch",
        include=normalise_field_key(config.include),
        exclude=normalise_field_key(config.exclude),
        partial=normalise_field_key(config.partial),
        required=normalise_field_key(config.required),
        child_models=sort_child_keys(child_keys),
        name=name,
    )


def create_patch_model(
    model: type[BaseModel],
    *,
    config: PatchConfig | None = None,
    include: Collection[str] | None = None,
    exclude: Collection[str] | None = None,
    partial: Collection[str] | None = None,
    required: Collection[str] | None = None,
    child_models: dict[type[BaseModel], PatchConfig] | None = None,
    name: str | None = None,
) -> type[BaseModel]:
    if config is None:
        config = PatchConfig(
            include=normalise_fields(include),
            exclude=normalise_fields(exclude),
            partial=normalise_fields(partial),
            required=normalise_fields(required),
            child_models=child_models or {},
        )

    cache_key = make_patch_cache_key(model, config, name)
    cached_model = _PATCH_MODEL_CACHE.get(cache_key)
    if cached_model is not None:
        return cached_model

    patched_model = _create_patch_model_uncached(model, config, name)
    _PATCH_MODEL_CACHE[cache_key] = patched_model
    return patched_model


def _create_patch_model_uncached(
    model: type[BaseModel],
    config: PatchConfig,
    name: str | None,
) -> type[BaseModel]:
    payload = build_payload_from_model(model)
    payload = apply_patch_scope_payload(payload, model, config)
    payload = transform_payload_annotations(
        payload,
        config=config,
        operation="patch",
        suffix="Patch",
        mutate_payload=apply_patch_payload,
        make_cache_key=make_patch_cache_key,
    )
    payload = apply_patch_presence_payload(payload, model, config)

    return create_model_from_payload(
        source_model=model,
        payload=payload,
        name=name or f"{model.__name__}Patch",
    )
