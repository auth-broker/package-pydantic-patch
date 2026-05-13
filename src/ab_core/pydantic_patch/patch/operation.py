"""Patch aggregation implementation."""

from collections.abc import Collection

from pydantic import BaseModel

from ab_core.pydantic_patch.core.cache import (
    OperationCacheKey,
    normalise_field_key,
    sort_child_keys,
)
from ab_core.pydantic_patch.core.config import normalise_fields
from ab_core.pydantic_patch.core.errors import InvalidDiscriminatorError
from ab_core.pydantic_patch.core.fields import (
    make_field_optional,
    make_field_required,
    validate_fields_exist_in_payload,
    validate_fields_exist_on_model,
)
from ab_core.pydantic_patch.core.payload import CreateModelPayload
from ab_core.pydantic_patch.core.transform import transform_model
from ab_core.pydantic_patch.patch.config import PatchConfig


def apply_patch_payload(
    payload: CreateModelPayload,
    model: type[BaseModel],
    config: PatchConfig,
) -> CreateModelPayload:
    """Apply pick/omit/partial/required rules to a model payload."""
    validate_fields_exist_on_model(model, config.pick, operation="pick")
    validate_fields_exist_on_model(model, config.omit, operation="omit")
    validate_fields_exist_on_model(model, config.partial, operation="partial")
    validate_fields_exist_on_model(model, config.required, operation="required")

    if config.pick is not None:
        payload = {
            field_name: field_payload for field_name, field_payload in payload.items() if field_name in config.pick
        }

    if config.omit is not None:
        payload = {
            field_name: field_payload for field_name, field_payload in payload.items() if field_name not in config.omit
        }

    validate_fields_exist_in_payload(
        payload,
        config.partial,
        model=model,
        operation="partial",
    )
    validate_fields_exist_in_payload(
        payload,
        config.required,
        model=model,
        operation="required",
    )

    fields_to_partial = set(payload) if config.partial is None else set(config.partial)
    fields_to_require = set() if config.required is None else set(config.required)

    patched_payload: CreateModelPayload = {}

    for field_name, (annotation, default) in payload.items():
        if field_name in fields_to_require:
            patched_payload[field_name] = make_field_required(annotation, default)
            continue

        if field_name in fields_to_partial:
            patched_payload[field_name] = make_field_optional(annotation, default)
            continue

        patched_payload[field_name] = (annotation, default)

    return patched_payload


def make_patch_cache_key(
    source_model: type[BaseModel],
    config: PatchConfig,
    name: str | None,
) -> OperationCacheKey:
    """Build a stable cache key for a composed patch transformation."""
    child_keys = {
        child_model: make_patch_cache_key(child_model, child_config, None)
        for child_model, child_config in config.child_models.items()
    }
    return OperationCacheKey(
        source_model=source_model,
        operation="patch",
        pick=normalise_field_key(config.pick),
        omit=normalise_field_key(config.omit),
        partial=normalise_field_key(config.partial),
        required=normalise_field_key(config.required),
        child_models=sort_child_keys(child_keys),
        name=name,
    )


def prepare_patch_discriminator_child_config(
    source_model: type[BaseModel],
    config: PatchConfig,
    discriminator_key: str,
) -> PatchConfig:
    """Validate and enforce discriminator rules for child patch configs."""
    if config.pick is not None and discriminator_key not in config.pick:
        raise InvalidDiscriminatorError(
            f"Cannot omit discriminator field {discriminator_key!r} "
            f"from discriminated union variant {source_model.__name__!r}."
        )

    if config.omit is not None and discriminator_key in config.omit:
        raise InvalidDiscriminatorError(
            f"Cannot omit discriminator field {discriminator_key!r} "
            f"from discriminated union variant {source_model.__name__!r}."
        )

    if config.partial is not None and discriminator_key in config.partial:
        raise InvalidDiscriminatorError(
            f"Cannot make discriminator field {discriminator_key!r} optional "
            f"on discriminated union variant {source_model.__name__!r}."
        )

    required = set(config.required or frozenset())
    required.add(discriminator_key)

    return config.model_copy(update={"required": frozenset(required)})


def create_patch_model(
    model: type[BaseModel],
    *,
    config: PatchConfig | None = None,
    pick: Collection[str] | None = None,
    omit: Collection[str] | None = None,
    partial: Collection[str] | None = None,
    required: Collection[str] | None = None,
    child_models: dict[type[BaseModel], PatchConfig] | None = None,
    name: str | None = None,
    use_cache: bool = True,
) -> type[BaseModel]:
    """Create a patch-transformed model from composed field operations."""
    patch_config = config or PatchConfig(
        pick=normalise_fields(pick),
        omit=normalise_fields(omit),
        partial=normalise_fields(partial),
        required=normalise_fields(required),
        child_models=child_models or {},
    )

    return transform_model(
        model,
        config=patch_config,
        operation="patch",
        suffix="Patch",
        mutate_payload=apply_patch_payload,
        make_cache_key=make_patch_cache_key,
        prepare_discriminator_child_config=prepare_patch_discriminator_child_config,
        name=name,
        use_cache=use_cache,
    )
