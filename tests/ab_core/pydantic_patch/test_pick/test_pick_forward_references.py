import pytest
from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel

from ab_core.pydantic_patch.core.errors import ForwardReferencesNotSupported
from ab_core.pydantic_patch.pick import Pick, create_pick_model


class PickForwardPydanticParent(BaseModel):
    id: int
    child: "PickForwardPydanticChild"


class PickForwardPydanticChild(BaseModel):
    id: int


class PickForwardSqlChild(SQLModel, table=True):
    __tablename__ = "pick_forward_sql_child"

    id: int | None = Field(default=None, primary_key=True)
    parent_id: int | None = Field(default=None, foreign_key="pick_forward_sql_parent.id")
    name: str

    parent: "PickForwardSqlParent | None" = Relationship(back_populates="children")


class PickForwardSqlParent(SQLModel, table=True):
    __tablename__ = "pick_forward_sql_parent"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    children: list[PickForwardSqlChild] = Relationship(back_populates="parent")


@pytest.mark.parametrize(
    "operation",
    [
        lambda: create_pick_model(PickForwardPydanticParent, fields={"id", "child"}),
        lambda: Pick[PickForwardPydanticParent](fields={"id", "child"}),
    ],
)
def test_pick_pydantic_forward_refs_raise_custom_error(operation):
    with pytest.raises(ForwardReferencesNotSupported):
        operation()


@pytest.mark.parametrize(
    "operation",
    [
        lambda: create_pick_model(PickForwardSqlParent, fields={"id", "children"}),
        lambda: Pick[PickForwardSqlParent](fields={"id", "children"}),
    ],
)
def test_pick_sqlmodel_relationship_forward_refs_raise_custom_error(operation):
    with pytest.raises(ForwardReferencesNotSupported):
        operation()
