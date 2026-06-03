from pydantic import BaseModel, computed_field

from ab_core.pydantic_patch.null import Null, create_null_model
from tests.helpers.assert_model import assert_field_names


class NullComputedUser(BaseModel):
    first_name: str
    last_name: str
    age: int

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @computed_field
    @property
    def is_adult(self) -> bool:
        return self.age >= 18


def test_null_includes_computed_fields() -> None:
    result = create_null_model(NullComputedUser)

    assert_field_names(
        result,
        {
            "first_name",
            "last_name",
            "age",
            "full_name",
            "is_adult",
        },
    )


def test_null_validates_and_dumps_computed_fields() -> None:
    result = Null[NullComputedUser]()

    validated = result.model_validate(
        NullComputedUser(
            first_name="Monique",
            last_name="Kuhn",
            age=28,
        )
    )

    dumped = validated.model_dump()

    assert dumped == {
        "first_name": "Monique",
        "last_name": "Kuhn",
        "age": 28,
        "full_name": "Monique Kuhn",
        "is_adult": True,
    }
