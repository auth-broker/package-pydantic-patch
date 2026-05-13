from pydantic import BaseModel, computed_field

from ab_core.pydantic_patch.partial import create_partial_model
from tests.helpers.assert_model import assert_field_names, assert_optional, assert_required


class ComputedFieldModel(BaseModel):
    first_name: str
    last_name: str

    @computed_field
    @property
    def full_name(self) -> str:
        """Return the computed full name."""
        return f"{self.first_name} {self.last_name}"


def test_partial_can_make_computed_field_optional() -> None:
    result = create_partial_model(ComputedFieldModel, fields={"full_name"})

    assert_field_names(result, {"first_name", "last_name", "full_name"})
    assert_optional(result, "full_name")
    assert_required(result, "first_name")


def test_partial_none_makes_computed_field_optional() -> None:
    result = create_partial_model(ComputedFieldModel, fields=None)

    assert_optional(result, "first_name")
    assert_optional(result, "last_name")
    assert_optional(result, "full_name")
