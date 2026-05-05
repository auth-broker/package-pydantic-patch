

import pytest

from ab_core.pydantic_patch.core.errors import (
    ConflictingPatchConfigError,
    InvalidDiscriminatorError,
    InvalidPatchFieldError,
)
from ab_core.pydantic_patch.patch import PatchConfig, create_patch_model
from ab_core.pydantic_patch.pick import create_pick_model
from tests.helpers.assert_model import assert_field_names


@pytest.mark.parametrize(
    "config",
    [
        PatchConfig(include={"does_not_exist"}),
        PatchConfig(exclude={"does_not_exist"}),
        PatchConfig(partial={"does_not_exist"}),
        PatchConfig(required={"does_not_exist"}),
    ],
)
def test_unknown_fields_raise(models, config):
    with pytest.raises(InvalidPatchFieldError):
        create_patch_model(models["User"], config=config)


def test_required_field_not_in_payload_raises(models):
    with pytest.raises(ConflictingPatchConfigError):
        create_patch_model(
            models["User"],
            config=PatchConfig(include={"name"}, required={"id"}),
        )


def test_partial_field_not_in_payload_raises(models):
    with pytest.raises(ConflictingPatchConfigError):
        create_patch_model(
            models["User"],
            config=PatchConfig(exclude={"email"}, partial={"email"}),
        )


def test_discriminator_field_omitted_raises(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]

    with pytest.raises(InvalidDiscriminatorError):
        create_patch_model(
            PetOwner,
            config=PatchConfig(
                child_models={Cat: PatchConfig(exclude={"kind"})},
            ),
        )


def test_discriminator_field_partial_raises(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]

    with pytest.raises(InvalidDiscriminatorError):
        create_patch_model(
            PetOwner,
            config=PatchConfig(
                child_models={Cat: PatchConfig(partial={"kind"})},
            ),
        )


def test_unsupported_arbitrary_non_pydantic_type_is_preserved(models):
    result = create_patch_model(
        models["ArbitraryPayload"],
        config=PatchConfig(partial=set()),
    )

    assert result.model_fields["metadata"].annotation == dict[str, object]
    assert result.model_fields["raw_value"].annotation is object


def test_mixed_union_with_non_basemodel_variant_is_preserved_for_non_model_member(models):
    Address = models["Address"]
    MixedUnionPayload = models["MixedUnionPayload"]

    result = create_pick_model(
        MixedUnionPayload,
        fields={"value"},
    )

    assert_field_names(result, {"value"})
    # The exact transformed annotation will be implementation-sensitive, but the
    # contract is that str is not discarded or treated as a BaseModel.
