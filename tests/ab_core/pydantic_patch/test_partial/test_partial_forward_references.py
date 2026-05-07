import pytest
from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel

from ab_core.pydantic_patch.core.errors import ForwardReferencesNotSupported
from ab_core.pydantic_patch.partial import Partial, create_partial_model


class PartialForwardPydanticParent(BaseModel):
    id: int
    child: "PartialForwardPydanticChild"


class PartialForwardPydanticChild(BaseModel):
    id: int


class PartialForwardSqlChild(SQLModel, table=True):
    __tablename__ = "partial_forward_sql_child"

    id: int | None = Field(default=None, primary_key=True)
    parent_id: int | None = Field(default=None, foreign_key="partial_forward_sql_parent.id")
    name: str

    parent: "PartialForwardSqlParent | None" = Relationship(back_populates="children")


class PartialForwardSqlParent(SQLModel, table=True):
    __tablename__ = "partial_forward_sql_parent"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    children: list[PartialForwardSqlChild] = Relationship(back_populates="parent")


@pytest.mark.parametrize(
    "operation",
    [
        lambda: create_partial_model(PartialForwardPydanticParent, fields={"child"}),
        lambda: Partial[PartialForwardPydanticParent](fields={"child"}),
    ],
)
def test_partial_pydantic_forward_refs_raise_custom_error(operation):
    with pytest.raises(ForwardReferencesNotSupported):
        operation()


@pytest.mark.parametrize(
    "operation",
    [
        lambda: create_partial_model(PartialForwardSqlParent, fields={"children"}),
        lambda: Partial[PartialForwardSqlParent](fields={"children"}),
    ],
)
def test_partial_sqlmodel_relationship_forward_refs_raise_custom_error(operation):
    with pytest.raises(ForwardReferencesNotSupported):
        operation()
