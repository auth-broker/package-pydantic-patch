from tests.ab_core.pydantic_patch.conftest_sqlmodel_relationships import (
    SQLModelRelationshipHousehold,
    SQLModelRelationshipPet,
)
from tests.helpers.assert_model import assert_field_names, get_list_item_type

from ab_core.pydantic_patch.pick import PickConfig, create_pick_model


def test_pick_sqlmodel_relationship_field_from_table_model():
    result = create_pick_model(
        SQLModelRelationshipHousehold,
        fields={"id", "pets"},
        child_models={
            SQLModelRelationshipPet: PickConfig(fields={"id", "name"}),
        },
    )

    assert_field_names(result, {"id", "pets"})

    pet_type = get_list_item_type(result.model_fields["pets"].annotation)
    assert_field_names(pet_type, {"id", "name"})

    result.model_validate(
        {
            "id": 1,
            "pets": [
                {
                    "id": 10,
                    "name": "Mimi",
                }
            ],
        }
    )
