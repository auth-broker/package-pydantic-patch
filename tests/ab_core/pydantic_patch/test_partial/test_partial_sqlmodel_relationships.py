from tests.ab_core.pydantic_patch.conftest_sqlmodel_relationships import (
    SQLModelRelationshipHousehold,
    SQLModelRelationshipPet,
)
from tests.helpers.assert_model import assert_optional, get_list_item_type

from ab_core.pydantic_patch.partial import PartialConfig, create_partial_model


def test_partial_sqlmodel_relationship_field_from_table_model():
    result = create_partial_model(
        SQLModelRelationshipHousehold,
        fields={"owner_name", "pets"},
        child_models={
            SQLModelRelationshipPet: PartialConfig(fields={"name"}),
        },
    )

    assert_optional(result, "owner_name")
    assert_optional(result, "pets")

    pet_type = get_list_item_type(result.model_fields["pets"].annotation)
    assert_optional(pet_type, "name")

    result.model_validate(
        {
            "id": 1,
            "pets": [
                {
                    "id": 10,
                    "age": 3,
                }
            ],
        }
    )
