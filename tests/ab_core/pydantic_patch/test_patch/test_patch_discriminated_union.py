

import pytest
from pydantic import ValidationError

from ab_core.pydantic_patch.core.errors import InvalidDiscriminatorError
from ab_core.pydantic_patch.patch import PatchConfig, create_patch_model


def test_patch_discriminated_union_flat_child_configs(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]
    Dog = models["Dog"]
    Bird = models["Bird"]

    result = create_patch_model(
        PetOwner,
        config=PatchConfig(
            include={"pet", "previous_pets"},
            partial=None,
            child_models={
                Cat: PatchConfig(
                    include={"kind", "id", "name", "lives"},
                    partial={"name", "lives"},
                    required={"id"},
                ),
                Dog: PatchConfig(
                    include={"kind", "id", "name", "bark_volume"},
                    partial={"name", "bark_volume"},
                    required={"id"},
                ),
                Bird: PatchConfig(
                    include={"kind", "id", "name", "wing_span"},
                    partial={"name", "wing_span"},
                    required={"id"},
                ),
            },
        ),
    )

    result.model_validate(
        {
            "pet": {"kind": "cat", "id": 1},
            "previous_pets": [
                {"kind": "dog", "id": 2},
                {"kind": "bird", "id": 3},
            ],
        }
    )

    with pytest.raises(ValidationError):
        result.model_validate({"pet": {"id": 1}, "previous_pets": []})


def test_patch_discriminator_field_cannot_be_partial(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]

    with pytest.raises(InvalidDiscriminatorError):
        create_patch_model(
            PetOwner,
            config=PatchConfig(
                include={"pet"},
                child_models={
                    Cat: PatchConfig(partial={"kind"}),
                },
            ),
        )


def test_patch_discriminator_field_cannot_be_omitted(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]

    with pytest.raises(InvalidDiscriminatorError):
        create_patch_model(
            PetOwner,
            config=PatchConfig(
                include={"pet"},
                child_models={
                    Cat: PatchConfig(exclude={"kind"}),
                },
            ),
        )
