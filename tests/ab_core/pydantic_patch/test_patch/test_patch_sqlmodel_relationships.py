import pytest
from pydantic import ValidationError

from ab_core.pydantic_patch.patch import Patch, PatchConfig, create_patch_model
from tests.ab_core.pydantic_patch.conftest_sqlmodel_relationships import (
    SQLModelRelationshipHousehold,
    SQLModelRelationshipPet,
)
from tests.helpers.assert_model import assert_field_names, assert_optional, assert_required, get_list_item_type


def test_patch_sqlmodel_relationship_field_from_table_model():
    result = create_patch_model(
        SQLModelRelationshipHousehold,
        config=PatchConfig(
            pick={"id", "owner_name", "pets"},
            required={"id"},
            child_models={
                SQLModelRelationshipPet: PatchConfig(
                    pick={"id", "name"},
                    required={"id"},
                ),
            },
        ),
    )

    assert_field_names(result, {"id", "owner_name", "pets"})
    assert_required(result, "id")
    assert_optional(result, "owner_name")
    assert_optional(result, "pets")

    pet_type = get_list_item_type(result.model_fields["pets"].annotation)
    assert_field_names(pet_type, {"id", "name"})
    assert_required(pet_type, "id")
    assert_optional(pet_type, "name")

    result.model_validate(
        {
            "id": 1,
            "pets": [
                {
                    "id": 10,
                    "name": "Mimi Updated",
                }
            ],
        }
    )

    with pytest.raises(ValidationError):
        result.model_validate(
            {
                "pets": [
                    {
                        "id": 10,
                        "name": "Mimi Updated",
                    }
                ],
            }
        )


def test_patch_generic_api_supports_sqlmodel_relationship_field():
    result = Patch[SQLModelRelationshipHousehold](
        pick={"id", "pets"},
        required={"id"},
        child_models={
            SQLModelRelationshipPet: PatchConfig(
                pick={"id", "name"},
                required={"id"},
            ),
        },
    )

    assert_field_names(result, {"id", "pets"})

    pet_type = get_list_item_type(result.model_fields["pets"].annotation)
    assert_field_names(pet_type, {"id", "name"})
