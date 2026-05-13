"""Required operation implementation."""

from collections.abc import Collection

from pydantic import BaseModel

from ab_core.pydantic_patch.core.cache import (
    OperationCacheKey,
    normalise_field_key,
    sort_child_keys,
)
from ab_core.pydantic_patch.core.config import normalise_fields
from ab_core.pydantic_patch.core.fields import (
    get_computed_field_names,
    make_field_required,
    validate_fields_exist_in_payload,
    validate_fields_exist_on_model,
)
from ab_core.pydantic_patch.core.errors import ConflictingPatchConfigError
from ab_core.pydantic_patch.core.payload import CreateModelPayload
from ab_core.pydantic_patch.core.transform import transform_model
from ab_core.pydantic_patch.required.config import RequiredConfig


def apply_required_payload(
    payload: CreateModelPayload,
    model: type[BaseModel],
    config: RequiredConfig,
) -> CreateModelPayload:
    """Mark configured payload fields as required."""
    validate_fields_exist_on_model(model, config.fields, operation="required")
    validate_fields_exist_in_payload(payload, config.fields, model=model, operation="required")

    invalid_computed_fields = sorted(set(config.fields or ()) & get_computed_field_names(model))
    if invalid_computed_fields:
        raise ConflictingPatchConfigError(
            f"Computed field(s) {invalid_computed_fields} cannot be made required on {model.__name__} "
            "because computed fields are derived values, not input fields."
        )

    if not config.fields:
        return payload

    return {
        field_name: make_field_required(annotation, default) if field_name in config.fields else (annotation, default)
        for field_name, (annotation, default) in payload.items()
    }


def make_required_cache_key(
    source_model: type[BaseModel],
    config: RequiredConfig,
    name: str | None,
) -> OperationCacheKey:
    """Build a stable cache key for a required transformation."""
    child_keys = {
        child_model: make_required_cache_key(child_model, child_config, None)
        for child_model, child_config in config.child_models.items()
    }
    return OperationCacheKey(
        source_model=source_model,
        operation="required",
        fields=normalise_field_key(config.fields),
        child_models=sort_child_keys(child_keys),
        name=name,
    )


def create_required_model(
    model: type[BaseModel],
    *,
    fields: Collection[str] | None = None,
    child_models: dict[type[BaseModel], RequiredConfig] | None = None,
    name: str | None = None,
    use_cache: bool = True,
) -> type[BaseModel]:
    """Create a required-transformed model from a source model."""
    config = RequiredConfig(fields=normalise_fields(fields), child_models=child_models or {})
    return transform_model(
        model,
        config=config,
        operation="required",
        suffix="Required",
        mutate_payload=apply_required_payload,
        make_cache_key=make_required_cache_key,
        name=name,
        use_cache=use_cache,
    )
