import pytest
from pydantic import ValidationError

from ab_core.pydantic_patch.required import RequiredConfig, create_required_model
from tests.ab_core.pydantic_patch.conftest_sqlmodel_relationships import (
    SQLModelRelationshipHousehold,
    SQLModelRelationshipPet,
)
from tests.helpers.assert_model import assert_required, get_list_item_type


def test_required_sqlmodel_relationship_child_field_from_table_model():
    result = create_required_model(
        SQLModelRelationshipHousehold,
        fields={"pets"},
        child_models={
            SQLModelRelationshipPet: RequiredConfig(fields={"id"}),
        },
    )

    assert_required(result, "pets")

    pet_type = get_list_item_type(result.model_fields["pets"].annotation)
    assert_required(pet_type, "id")

    result.model_validate(
        {
            "id": 1,
            "owner_name": "Monique",
            "pets": [
                {
                    "id": 10,
                    "name": "Mimi",
                    "age": 3,
                }
            ],
            "toys": [],
        }
    )

    with pytest.raises(ValidationError):
        result.model_validate(
            {
                "id": 1,
                "owner_name": "Monique",
                "pets": [
                    {
                        "name": "Mimi",
                        "age": 3,
                    }
                ],
                "toys": [],
            }
        )
