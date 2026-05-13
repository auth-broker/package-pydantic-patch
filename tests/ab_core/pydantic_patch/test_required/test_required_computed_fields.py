from pydantic import BaseModel, computed_field

from ab_core.pydantic_patch.required import create_required_model
from tests.helpers.assert_model import assert_field_names, assert_required


class ComputedFieldModel(BaseModel):
    first_name: str | None = None
    last_name: str | None = None

    @computed_field
    @property
    def full_name(self) -> str:
        """Return the computed full name."""
        return f"{self.first_name} {self.last_name}"


def test_required_can_force_computed_field_required() -> None:
    result = create_required_model(ComputedFieldModel, fields={"full_name"})

    assert_field_names(result, {"first_name", "last_name", "full_name"})
    assert_required(result, "full_name")

    validated = result.model_validate({"full_name": "Monique Kuhn"})
    assert validated.full_name == "Monique Kuhn"
