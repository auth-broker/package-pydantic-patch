import pytest
from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel

from ab_core.pydantic_patch.core.errors import ForwardReferencesNotSupported
from ab_core.pydantic_patch.required import Required, create_required_model


class RequiredForwardPydanticParent(BaseModel):
    id: int
    child: "RequiredForwardPydanticChild"


class RequiredForwardPydanticChild(BaseModel):
    id: int


class RequiredForwardSqlChild(SQLModel, table=True):
    __tablename__ = "required_forward_sql_child"

    id: int | None = Field(default=None, primary_key=True)
    parent_id: int | None = Field(default=None, foreign_key="required_forward_sql_parent.id")
    name: str

    parent: "RequiredForwardSqlParent | None" = Relationship(back_populates="children")


class RequiredForwardSqlParent(SQLModel, table=True):
    __tablename__ = "required_forward_sql_parent"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    children: list[RequiredForwardSqlChild] = Relationship(back_populates="parent")


@pytest.mark.parametrize(
    "operation",
    [
        lambda: create_required_model(RequiredForwardPydanticParent, fields={"child"}),
        lambda: Required[RequiredForwardPydanticParent](fields={"child"}),
    ],
)
def test_required_pydantic_forward_refs_raise_custom_error(operation):
    with pytest.raises(ForwardReferencesNotSupported):
        operation()


@pytest.mark.parametrize(
    "operation",
    [
        lambda: create_required_model(RequiredForwardSqlParent, fields={"children"}),
        lambda: Required[RequiredForwardSqlParent](fields={"children"}),
    ],
)
def test_required_sqlmodel_relationship_forward_refs_raise_custom_error(operation):
    with pytest.raises(ForwardReferencesNotSupported):
        operation()