import pytest
from pydantic import ValidationError

from ab_core.pydantic_patch.required import RequiredConfig, create_required_model


def test_required_discriminated_union_variant_ids(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]
    Dog = models["Dog"]
    Bird = models["Bird"]

    result = create_required_model(
        PetOwner,
        child_models={
            Cat: RequiredConfig(fields={"id"}),
            Dog: RequiredConfig(fields={"id"}),
            Bird: RequiredConfig(fields={"id"}),
        },
    )

    result.model_validate(
        {
            "id": 1,
            "name": "Owner",
            "pet": {"kind": "cat", "id": 1, "name": "Mimi", "lives": 9, "secret_tracking_code": "x"},
            "previous_pets": [],
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
    )

    with pytest.raises(ValidationError):
        result.model_validate(
            {
                "id": 1,
                "name": "Owner",
                "pet": {"kind": "cat", "name": "Mimi", "lives": 9, "secret_tracking_code": "x"},
                "previous_pets": [],
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
            }
        )
