from pydantic import BaseModel, computed_field

from ab_core.pydantic_patch.pick import Pick, create_pick_model
from tests.helpers.assert_model import assert_field_names, assert_required


class ComputedFieldModel(BaseModel):
    first_name: str
    last_name: str

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


def test_pick_can_select_computed_field() -> None:
    result = create_pick_model(ComputedFieldModel, fields={"full_name"})

    assert_field_names(result, {"full_name"})
    assert_required(result, "full_name")

    validated = result.model_validate({"full_name": "Monique Kuhn"})
    assert validated.full_name == "Monique Kuhn"


def test_pick_generic_api_can_select_computed_field() -> None:
    result = Pick[ComputedFieldModel](fields={"first_name", "full_name"})

    assert_field_names(result, {"first_name", "full_name"})
