from tests.ab_core.pydantic_patch.conftest_sqlmodel_relationships import (
    SQLModelRelationshipHousehold,
    SQLModelRelationshipPet,
)
from tests.helpers.assert_model import assert_field_names, get_list_item_type

from ab_core.pydantic_patch.omit import OmitConfig, create_omit_model


def test_omit_sqlmodel_relationship_child_fields_from_table_model():
    result = create_omit_model(
        SQLModelRelationshipHousehold,
        fields={"toys"},
        child_models={
            SQLModelRelationshipPet: OmitConfig(fields={"age"}),
        },
    )

    assert_field_names(result, {"id", "owner_name", "pets"})

    pet_type = get_list_item_type(result.model_fields["pets"].annotation)
    assert_field_names(pet_type, {"id", "name", "household_id"})

    result.model_validate(
        {
            "id": 1,
            "owner_name": "Monique",
            "pets": [
                {
                    "id": 10,
                    "name": "Mimi",
                    "household_id": 1,
                }
            ],
        }
    )
