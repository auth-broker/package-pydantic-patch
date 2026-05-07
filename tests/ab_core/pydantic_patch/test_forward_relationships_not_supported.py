import pytest
from sqlmodel import Field, Relationship, SQLModel

from ab_core.pydantic_patch.core.errors import ForwardReferencesNotSupported
from ab_core.pydantic_patch.omit import Omit, create_omit_model
from ab_core.pydantic_patch.partial import Partial, create_partial_model
from ab_core.pydantic_patch.patch import Patch, PatchConfig, create_patch_model
from ab_core.pydantic_patch.pick import Pick, create_pick_model
from ab_core.pydantic_patch.required import Required, create_required_model


class Child(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    parent_id: int | None = Field(default=None, foreign_key="parent.id")
    name: str

    parent: "Parent | None" = Relationship(back_populates="children")


class Parent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str

    children: list[Child] = Relationship(back_populates="parent")


@pytest.mark.parametrize(
    ("operation_name", "operation"),
    [
        (
            "pick",
            lambda: create_pick_model(
                Parent,
                fields={"id", "children"},
            ),
        ),
        (
            "omit",
            lambda: create_omit_model(
                Parent,
                fields={"name"},
            ),
        ),
        (
            "partial",
            lambda: create_partial_model(
                Parent,
                fields={"children"},
            ),
        ),
        (
            "required",
            lambda: create_required_model(
                Parent,
                fields={"children"},
            ),
        ),
        (
            "patch",
            lambda: create_patch_model(
                Parent,
                config=PatchConfig(
                    pick={"id", "children"},
                    partial={"children"},
                ),
            ),
        ),
    ],
)
def test_sqlmodel_relationship_forward_refs_raise_custom_error(operation_name, operation):
    with pytest.raises(
        ForwardReferencesNotSupported,
    ):
        operation()


@pytest.mark.parametrize(
    ("operation_name", "operation"),
    [
        ("pick", lambda: Pick[Parent](fields={"id", "children"})),
        ("omit", lambda: Omit[Parent](fields={"name"})),
        ("partial", lambda: Partial[Parent](fields={"children"})),
        ("required", lambda: Required[Parent](fields={"children"})),
        (
            "patch",
            lambda: Patch[Parent](
                pick={"id", "children"},
                partial={"children"},
            ),
        ),
    ],
)
def test_sqlmodel_relationship_forward_refs_raise_custom_error_for_generic_api(
    operation_name,
    operation,
):
    with pytest.raises(
        ForwardReferencesNotSupported,
    ):
        operation()
