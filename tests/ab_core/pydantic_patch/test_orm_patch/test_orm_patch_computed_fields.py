from pydantic import BaseModel, computed_field

from ab_core.pydantic_patch.orm_patch import recursive_patch_orm_scalar


class User(BaseModel):
    first_name: str
    last_name: str


class UserPatch(BaseModel):
    first_name: str | None = None

    @computed_field
    @property
    def full_name(self) -> str:
        return "Ignored Computed Value"


def test_recursive_patch_orm_scalar_ignores_computed_patch_fields() -> None:
    user = User(first_name="Old", last_name="Name")
    patch = UserPatch(first_name="New")

    recursive_patch_orm_scalar(user, patch)

    assert user.first_name == "New"
    assert user.last_name == "Name"
    assert not hasattr(user, "full_name")