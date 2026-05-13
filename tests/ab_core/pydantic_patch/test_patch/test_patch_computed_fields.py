from pydantic import BaseModel, computed_field

from ab_core.pydantic_patch.patch import Patch, PatchConfig, create_patch_model
from tests.helpers.assert_model import assert_field_names, assert_optional, assert_required


class ComputedFieldModel(BaseModel):
    first_name: str
    last_name: str

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


def test_patch_can_pick_partial_and_require_computed_field() -> None:
    result = create_patch_model(
        ComputedFieldModel,
        config=PatchConfig(
            pick={"first_name", "full_name"},
            partial={"first_name"},
            required={"full_name"},
        ),
    )

    assert_field_names(result, {"first_name", "full_name"})
    assert_optional(result, "first_name")
    assert_required(result, "full_name")


def test_patch_generic_api_supports_computed_field() -> None:
    result = Patch[ComputedFieldModel](
        pick={"full_name"},
        required={"full_name"},
    )

    assert_field_names(result, {"full_name"})
    assert_required(result, "full_name")
