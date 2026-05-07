import pytest
from pydantic import BaseModel
from sqlalchemy.orm import registry
from sqlmodel import Field, Relationship, SQLModel

from ab_core.pydantic_patch.core.errors import ForwardReferencesNotSupported
from ab_core.pydantic_patch.pick import Pick, create_pick_model

mapper_registry = registry()


class ForwardRefSQLModel(SQLModel, registry=mapper_registry):
    __abstract__ = True


class PickForwardPydanticParent(BaseModel):
    id: int
    child: "PickForwardPydanticChildMissing"


class PickForwardPydanticChild(BaseModel):
    id: int


class PickForwardSqlChild(ForwardRefSQLModel, table=True):
    __tablename__ = "pick_forward_sql_child"

    id: int | None = Field(default=None, primary_key=True)
    parent_id: int | None = Field(default=None, foreign_key="pick_forward_sql_parent.id")
    name: str

    parent: "PickForwardSqlParentMissing | None" = Relationship(back_populates="children")


class PickForwardSqlParent(ForwardRefSQLModel, table=True):
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
def test_unresolved_pydantic_forward_refs_raise_custom_error(operation):
    with pytest.raises(ForwardReferencesNotSupported):
        operation()


@pytest.mark.parametrize(
    "operation",
    [
        lambda: create_pick_model(PickForwardSqlParent, fields={"id", "children"}),
        lambda: Pick[PickForwardSqlParent](fields={"id", "children"}),
    ],
)
def test_resolved_sqlmodel_relationship_forward_refs_are_supported(operation):
    model = operation()

    assert "children" in model.model_fields


def teardown_module() -> None:
    mapper_registry.dispose(cascade=True)
    mapper_registry.metadata.clear()
