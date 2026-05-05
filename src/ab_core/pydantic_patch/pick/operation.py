"""Pick operation implementation."""



from collections.abc import Collection

from pydantic import BaseModel

from ab_core.pydantic_patch.core.cache import (
    OperationCacheKey,
    normalise_field_key,
    sort_child_keys,
)
from ab_core.pydantic_patch.core.config import normalise_fields
from ab_core.pydantic_patch.core.fields import validate_fields_exist_on_model
from ab_core.pydantic_patch.core.payload import CreateModelPayload
from ab_core.pydantic_patch.core.transform import transform_model
from ab_core.pydantic_patch.pick.config import PickConfig


def apply_pick_payload(
    payload: CreateModelPayload,
    model: type[BaseModel],
    config: PickConfig,
) -> CreateModelPayload:
    validate_fields_exist_on_model(model, config.fields, operation="pick")

    if config.fields is None:
        return payload

    return {
        field_name: field_payload
        for field_name, field_payload in payload.items()
        if field_name in config.fields
    }


def make_pick_cache_key(
    source_model: type[BaseModel],
    config: PickConfig,
    name: str | None,
) -> OperationCacheKey:
    child_keys = {
        child_model: make_pick_cache_key(child_model, child_config, None)
        for child_model, child_config in config.child_models.items()
    }
    return OperationCacheKey(
        source_model=source_model,
        operation="pick",
        fields=normalise_field_key(config.fields),
        child_models=sort_child_keys(child_keys),
        name=name,
    )


def create_pick_model(
    model: type[BaseModel],
    *,
    fields: Collection[str] | None = None,
    child_models: dict[type[BaseModel], PickConfig] | None = None,
    name: str | None = None,
) -> type[BaseModel]:
    config = PickConfig(fields=normalise_fields(fields), child_models=child_models or {})
    return transform_model(
        model,
        config=config,
        operation="pick",
        suffix="Pick",
        mutate_payload=apply_pick_payload,
        make_cache_key=make_pick_cache_key,
        name=name,
    )
