import pytest
from pydantic import BaseModel, computed_field
from sqlalchemy.orm import registry
from sqlmodel import Field, Relationship, SQLModel

from ab_core.pydantic_patch.core.errors import ForwardReferencesNotSupported
from ab_core.pydantic_patch.required import Required, create_required_model

mapper_registry = registry()


class ForwardRefSQLModel(SQLModel, registry=mapper_registry):
    __abstract__ = True


class RequiredForwardPydanticParent(BaseModel):
    id: int
    child: "RequiredForwardPydanticChildMissing"


class RequiredForwardPydanticChild(BaseModel):
    id: int


class RequiredComputedForwardRefModel(BaseModel):
    @computed_field
    @property
    def manager(self) -> "RequiredMissingManager":
        raise NotImplementedError


class RequiredForwardSqlChild(ForwardRefSQLModel, table=True):
    __tablename__ = "required_forward_sql_child"

    id: int | None = Field(default=None, primary_key=True)
    parent_id: int | None = Field(default=None, foreign_key="required_forward_sql_parent.id")
    name: str

    parent: "RequiredForwardSqlParentMissing | None" = Relationship(back_populates="children")


class RequiredForwardSqlParent(ForwardRefSQLModel, table=True):
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
def test_unresolved_pydantic_forward_refs_raise_custom_error(operation):
    with pytest.raises(ForwardReferencesNotSupported):
        operation()


@pytest.mark.parametrize(
    "operation",
    [
        lambda: create_required_model(RequiredForwardSqlParent, fields={"children"}),
        lambda: Required[RequiredForwardSqlParent](fields={"children"}),
    ],
)
def test_resolved_sqlmodel_relationship_forward_refs_are_supported(operation):
    model = operation()

    assert "children" in model.model_fields


def test_required_computed_field_forward_ref_raises_custom_error() -> None:
    with pytest.raises(ForwardReferencesNotSupported, match="manager"):
        Required[RequiredComputedForwardRefModel]()


def teardown_module() -> None:
    mapper_registry.dispose(cascade=True)
    mapper_registry.metadata.clear()
