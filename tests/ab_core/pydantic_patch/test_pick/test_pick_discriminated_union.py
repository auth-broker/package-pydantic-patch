from __future__ import annotations

import pytest

from ab_core.pydantic_patch.core.errors import InvalidDiscriminatorError
from ab_core.pydantic_patch.pick import PickConfig, create_pick_model
from tests.helpers.assert_model import get_list_item_type


def test_pick_discriminated_union_preserves_union_and_variants(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]
    Dog = models["Dog"]
    Bird = models["Bird"]

    result = create_pick_model(
        PetOwner,
        fields={"pet", "previous_pets"},
        child_models={
            Cat: PickConfig(fields={"kind", "name", "lives"}),
            Dog: PickConfig(fields={"kind", "name", "bark_volume"}),
            Bird: PickConfig(fields={"kind", "name", "wing_span"}),
        },
    )

    pet_annotation = result.model_fields["pet"].annotation
    previous_pet_annotation = get_list_item_type(result.model_fields["previous_pets"].annotation)

    assert pet_annotation == previous_pet_annotation

    payload = {
        "pet": {"kind": "cat", "name": "Mimi", "lives": 9},
        "previous_pets": [
            {"kind": "dog", "name": "Kiki", "bark_volume": 5},
            {"kind": "bird", "name": "Pip", "wing_span": 12.5},
        ],
    }
    validated = result.model_validate(payload)
    assert validated.pet.kind == "cat"
    assert validated.previous_pets[0].kind == "dog"
    assert validated.previous_pets[1].kind == "bird"


def test_pick_discriminator_field_cannot_be_omitted_from_variant(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]
    Dog = models["Dog"]
    Bird = models["Bird"]

    with pytest.raises(InvalidDiscriminatorError):
        create_pick_model(
            PetOwner,
            fields={"pet"},
            child_models={
                Cat: PickConfig(fields={"name", "lives"}),
                Dog: PickConfig(fields={"kind", "name", "bark_volume"}),
                Bird: PickConfig(fields={"kind", "name", "wing_span"}),
            },
        )
