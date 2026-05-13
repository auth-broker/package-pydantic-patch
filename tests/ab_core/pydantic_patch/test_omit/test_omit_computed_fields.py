from pydantic import BaseModel, computed_field

from ab_core.pydantic_patch.omit import create_omit_model
from tests.helpers.assert_model import assert_field_names


class ComputedFieldModel(BaseModel):
    first_name: str
    last_name: str

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


def test_omit_can_remove_computed_field() -> None:
    result = create_omit_model(ComputedFieldModel, fields={"full_name"})

    assert_field_names(result, {"first_name", "last_name"})


def test_omit_includes_computed_field_when_not_omitted() -> None:
    result = create_omit_model(ComputedFieldModel, fields={"last_name"})

    assert_field_names(result, {"first_name", "full_name"})
