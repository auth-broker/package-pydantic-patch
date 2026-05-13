from pydantic import BaseModel, computed_field
from sqlmodel import Field, SQLModel

from ab_core.pydantic_patch.orm_patch import recursive_patch_orm_scalar, recursive_patch_scalar


class ComputedFieldOrmUser(SQLModel, table=True):
    __tablename__ = "computed_field_orm_user"

    id: int | None = Field(default=None, primary_key=True)
    first_name: str
    last_name: str


class UserPatch(BaseModel):
    first_name: str | None = None

    @computed_field
    @property
    def full_name(self) -> str:
        """Return a computed field that should not be patched onto the ORM model."""
        return "Ignored Computed Value"


def test_recursive_patch_orm_scalar_ignores_computed_patch_fields() -> None:
    user = ComputedFieldOrmUser(id=1, first_name="Old", last_name="Name")
    patch = UserPatch(first_name="New")

    recursive_patch_orm_scalar(user, patch)

    assert user.first_name == "New"
    assert user.last_name == "Name"
    assert not hasattr(type(user), "full_name")


class PydanticProfile(BaseModel):
    bio: str


class PydanticUser(BaseModel):
    first_name: str
    last_name: str
    profile: PydanticProfile


class PydanticProfilePatch(BaseModel):
    bio: str | None = None


class PydanticUserPatch(BaseModel):
    first_name: str | None = None
    profile: PydanticProfilePatch | None = None

    @computed_field
    @property
    def full_name(self) -> str:
        """Return a computed field that should not be patched onto the Pydantic model."""
        return "Ignored Computed Value"


def test_recursive_patch_scalar_supports_pydantic_models() -> None:
    user = PydanticUser(
        first_name="Old",
        last_name="Name",
        profile=PydanticProfile(bio="Old bio"),
    )
    patch = PydanticUserPatch(
        first_name="New",
        profile=PydanticProfilePatch(bio="New bio"),
    )

    recursive_patch_scalar(user, patch)

    assert user.first_name == "New"
    assert user.last_name == "Name"
    assert user.profile.bio == "New bio"
    assert not hasattr(type(user), "full_name")
