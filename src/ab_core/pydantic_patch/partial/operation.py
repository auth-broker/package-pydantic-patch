"""Partial operation implementation."""

from __future__ import annotations

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
    validate_fields_exist_in_payload,
    validate_fields_exist_on_model,
)
from ab_core.pydantic_patch.core.payload import CreateModelPayload
from ab_core.pydantic_patch.core.transform import transform_model
from ab_core.pydantic_patch.partial.config import PartialConfig


def apply_partial_payload(
    payload: CreateModelPayload,
    model: type[BaseModel],
    config: PartialConfig,
) -> CreateModelPayload:
    validate_fields_exist_on_model(model, config.fields, operation="partial")
    validate_fields_exist_in_payload(payload, config.fields, model=model, operation="partial")

    fields_to_partial = set(payload) if config.fields is None else set(config.fields)

    return {
        field_name: make_field_optional(annotation, default)
        if field_name in fields_to_partial
        else (annotation, default)
        for field_name, (annotation, default) in payload.items()
    }


def make_partial_cache_key(
    source_model: type[BaseModel],
    config: PartialConfig,
    name: str | None,
) -> OperationCacheKey:
    child_keys = {
        child_model: make_partial_cache_key(child_model, child_config, None)
        for child_model, child_config in config.child_models.items()
    }
    return OperationCacheKey(
        source_model=source_model,
        operation="partial",
        fields=normalise_field_key(config.fields),
        child_models=sort_child_keys(child_keys),
        name=name,
    )


def create_partial_model(
    model: type[BaseModel],
    *,
    fields: Collection[str] | None = None,
    child_models: dict[type[BaseModel], PartialConfig] | None = None,
    name: str | None = None,
) -> type[BaseModel]:
    config = PartialConfig(fields=normalise_fields(fields), child_models=child_models or {})
    return transform_model(
        model,
        config=config,
        operation="partial",
        suffix="Partial",
        mutate_payload=apply_partial_payload,
        make_cache_key=make_partial_cache_key,
        name=name,
    )
