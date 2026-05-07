import pytest
from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel

from ab_core.pydantic_patch.core.errors import ForwardReferencesNotSupported
from ab_core.pydantic_patch.omit import Omit, create_omit_model


class OmitForwardPydanticParent(BaseModel):
    id: int
    child: "OmitForwardPydanticChild"


class OmitForwardPydanticChild(BaseModel):
    id: int


class OmitForwardSqlChild(SQLModel, table=True):
    __tablename__ = "omit_forward_sql_child"

    id: int | None = Field(default=None, primary_key=True)
    parent_id: int | None = Field(default=None, foreign_key="omit_forward_sql_parent.id")
    name: str

    parent: "OmitForwardSqlParent | None" = Relationship(back_populates="children")


class OmitForwardSqlParent(SQLModel, table=True):
    __tablename__ = "omit_forward_sql_parent"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    children: list[OmitForwardSqlChild] = Relationship(back_populates="parent")


@pytest.mark.parametrize(
    "operation",
    [
        lambda: create_omit_model(OmitForwardPydanticParent, fields={"id"}),
        lambda: Omit[OmitForwardPydanticParent](fields={"id"}),
    ],
)
def test_omit_pydantic_forward_refs_raise_custom_error(operation):
    with pytest.raises(ForwardReferencesNotSupported):
        operation()


@pytest.mark.parametrize(
    "operation",
    [
        lambda: create_omit_model(OmitForwardSqlParent, fields={"name"}),
        lambda: Omit[OmitForwardSqlParent](fields={"name"}),
    ],
)
def test_omit_sqlmodel_relationship_forward_refs_raise_custom_error(operation):
    with pytest.raises(ForwardReferencesNotSupported):
        operation()