import pytest
from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel

from ab_core.pydantic_patch.orm_patch import recursive_patch_orm_scalar


class Profile(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    bio: str | None = None
    user_id: int | None = Field(default=None, foreign_key="user.id")


class Pet(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str | None = None
    species: str | None = None
    owner_id: int | None = Field(default=None, foreign_key="user.id")


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str | None = None
    email: str | None = None

    profile: Profile | None = Relationship(sa_relationship_kwargs={"uselist": False})
    pets: list[Pet] = Relationship()


class ProfilePatch(BaseModel):
    id: int | None = None
    bio: str | None = None


class PetPatch(BaseModel):
    id: int | None = None
    name: str | None = None
    species: str | None = None


class UserPatch(BaseModel):
    id: int | None = None
    name: str | None = None
    email: str | None = None
    profile: ProfilePatch | None = None
    pets: list[PetPatch] | None = None


def test_updates_provided_scalar_fields_only() -> None:
    user = User(id=1, name="Old name", email="old@example.com")

    patch = UserPatch(name="New name")

    recursive_patch_orm_scalar(user, patch)

    assert user.name == "New name"
    assert user.email == "old@example.com"


def test_explicit_none_updates_scalar_field() -> None:
    user = User(id=1, name="Monique", email="old@example.com")

    patch = UserPatch(email=None)

    recursive_patch_orm_scalar(user, patch)

    assert user.email is None


def test_primary_key_is_not_updated() -> None:
    user = User(id=1, name="Old name")

    patch = UserPatch(id=999, name="New name")

    recursive_patch_orm_scalar(user, patch)

    assert user.id == 1
    assert user.name == "New name"


def test_updates_existing_one_to_one_relationship() -> None:
    profile = Profile(id=10, bio="Old bio")
    user = User(id=1, profile=profile)

    patch = UserPatch(profile=ProfilePatch(id=999, bio="New bio"))

    recursive_patch_orm_scalar(user, patch)

    assert user.profile is profile
    assert user.profile.id == 10
    assert user.profile.bio == "New bio"


def test_creates_missing_one_to_one_relationship() -> None:
    user = User(id=1, profile=None)

    patch = UserPatch(profile=ProfilePatch(bio="Created bio"))

    recursive_patch_orm_scalar(user, patch)

    assert user.profile is not None
    assert user.profile.bio == "Created bio"


def test_sets_one_to_one_relationship_to_none() -> None:
    user = User(id=1, profile=Profile(id=10, bio="Old bio"))

    patch = UserPatch(profile=None)

    recursive_patch_orm_scalar(user, patch)

    assert user.profile is None


def test_updates_existing_one_to_many_child_by_primary_key() -> None:
    pet = Pet(id=10, name="Mimi", species="cat")
    user = User(id=1, pets=[pet])

    patch = UserPatch(
        pets=[
            PetPatch(id=10, name="Kiki"),
        ]
    )

    recursive_patch_orm_scalar(user, patch)

    assert user.pets == [pet]
    assert pet.id == 10
    assert pet.name == "Kiki"
    assert pet.species == "cat"


def test_creates_new_one_to_many_child_when_primary_key_missing() -> None:
    existing_pet = Pet(id=10, name="Mimi", species="cat")
    user = User(id=1, pets=[existing_pet])

    patch = UserPatch(
        pets=[
            PetPatch(id=10, name="Mimi Updated"),
            PetPatch(name="Kiki", species="cat"),
        ]
    )

    recursive_patch_orm_scalar(user, patch)

    assert len(user.pets) == 2

    assert user.pets[0] is existing_pet
    assert user.pets[0].name == "Mimi Updated"

    new_pet = user.pets[1]
    assert new_pet.id is None
    assert new_pet.name == "Kiki"
    assert new_pet.species == "cat"


def test_raises_when_one_to_many_child_primary_key_does_not_exist() -> None:
    user = User(id=1, pets=[Pet(id=10, name="Mimi")])

    patch = UserPatch(pets=[PetPatch(id=999, name="Unknown")])

    with pytest.raises(ValueError, match="No existing Pet found"):
        recursive_patch_orm_scalar(user, patch)


def test_raises_when_one_to_one_patch_is_not_base_model() -> None:
    user = User(id=1)

    class BadPatch(BaseModel):
        profile: dict[str, str]

    patch = BadPatch(profile={"bio": "Bad"})

    with pytest.raises(TypeError, match="Expected BaseModel patch"):
        recursive_patch_orm_scalar(user, patch)


def test_raises_when_one_to_many_child_patch_is_not_base_model() -> None:
    user = User(id=1, pets=[])

    class BadPatch(BaseModel):
        pets: list[dict[str, str]]

    patch = BadPatch(pets=[{"name": "Bad"}])

    with pytest.raises(TypeError, match="Expected BaseModel child patch"):
        recursive_patch_orm_scalar(user, patch)
