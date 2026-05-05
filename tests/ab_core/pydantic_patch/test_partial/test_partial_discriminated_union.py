from __future__ import annotations

import pytest
from pydantic import ValidationError

from ab_core.pydantic_patch.core.errors import InvalidDiscriminatorError
from ab_core.pydantic_patch.partial import PartialConfig, create_partial_model


def test_partial_discriminated_union_variants_keep_kind_required(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]
    Dog = models["Dog"]
    Bird = models["Bird"]

    result = create_partial_model(
        PetOwner,
        fields=None,
        child_models={
            Cat: PartialConfig(fields=None),
            Dog: PartialConfig(fields=None),
            Bird: PartialConfig(fields=None),
        },
    )

    validated = result.model_validate(
        {
            "pet": {"kind": "cat"},
            "previous_pets": [{"kind": "dog"}, {"kind": "bird"}],
        }
    )
    assert validated.pet.kind == "cat"

    with pytest.raises(ValidationError):
        result.model_validate({"pet": {"name": "Missing kind"}, "previous_pets": []})


def test_partial_discriminator_field_cannot_be_partialed(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]

    with pytest.raises(InvalidDiscriminatorError):
        create_partial_model(
            PetOwner,
            child_models={
                Cat: PartialConfig(fields={"kind"}),
            },
        )
