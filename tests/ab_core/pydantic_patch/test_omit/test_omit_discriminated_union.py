from __future__ import annotations

import pytest

from ab_core.pydantic_patch.core.errors import InvalidDiscriminatorError
from ab_core.pydantic_patch.omit import OmitConfig, create_omit_model


def test_omit_discriminated_union_variant_fields(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]
    Dog = models["Dog"]
    Bird = models["Bird"]

    result = create_omit_model(
        PetOwner,
        fields={"created_at", "updated_at"},
        child_models={
            Cat: OmitConfig(fields={"secret_tracking_code"}),
            Dog: OmitConfig(fields={"secret_tracking_code"}),
            Bird: OmitConfig(fields={"secret_tracking_code"}),
        },
    )

    validated = result.model_validate(
        {
            "id": 1,
            "name": "Owner",
            "pet": {"kind": "cat", "id": 1, "name": "Mimi", "lives": 9},
            "previous_pets": [{"kind": "dog", "id": 2, "name": "Kiki", "bark_volume": 4}],
        }
    )
    assert validated.pet.kind == "cat"


def test_omit_discriminator_field_raises(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]

    with pytest.raises(InvalidDiscriminatorError):
        create_omit_model(
            PetOwner,
            child_models={
                Cat: OmitConfig(fields={"kind"}),
            },
        )
