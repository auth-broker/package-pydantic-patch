import pytest
from pydantic import BaseModel, computed_field
from sqlalchemy.orm import registry
from sqlmodel import Field, Relationship, SQLModel

from ab_core.pydantic_patch.core.errors import ForwardReferencesNotSupported
from ab_core.pydantic_patch.null import Null, create_null_model
from tests.helpers.assert_model import get_list_item_type

mapper_registry = registry()


class NullForwardSQLModel(SQLModel, registry=mapper_registry):
    __abstract__ = True


class NullForwardPydanticParent(BaseModel):
    id: int
    child: "NullForwardPydanticChildMissing"


class NullForwardPydanticChild(BaseModel):
    id: int


class NullComputedForwardRefModel(BaseModel):
    @computed_field
    @property
    def manager(self) -> "NullMissingManager":
        raise NotImplementedError


class NullForwardSqlChild(NullForwardSQLModel, table=True):
    __tablename__ = "null_forward_sql_child"

    id: int | None = Field(default=None, primary_key=True)
    parent_id: int | None = Field(
        default=None,
        foreign_key="null_forward_sql_parent.id",
    )
    name: str

    parent: "NullForwardSqlParent" = Relationship(back_populates="children")


class NullForwardSqlParent(NullForwardSQLModel, table=True):
    __tablename__ = "null_forward_sql_parent"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    children: list[NullForwardSqlChild] = Relationship(back_populates="parent")


@pytest.mark.parametrize(
    "operation",
    [
        lambda: create_null_model(NullForwardPydanticParent),
        lambda: Null[NullForwardPydanticParent](),
    ],
)
def test_unresolved_pydantic_forward_refs_raise_custom_error(operation) -> None:
    with pytest.raises(ForwardReferencesNotSupported):
        operation()


@pytest.mark.parametrize(
    "operation",
    [
        lambda: create_null_model(NullForwardSqlParent),
        lambda: Null[NullForwardSqlParent](),
    ],
)
def test_resolved_sqlmodel_relationship_forward_refs_are_supported(operation) -> None:
    model = operation()

    assert "children" in model.model_fields

    child_type = get_list_item_type(model.model_fields["children"].annotation)

    assert "id" in child_type.model_fields
    assert "name" in child_type.model_fields
    assert "parent_id" in child_type.model_fields

    # Backref should be excluded for the cyclic dump-safe schema.
    assert "parent" not in child_type.model_fields


def test_null_computed_field_forward_ref_raises_custom_error() -> None:
    with pytest.raises(ForwardReferencesNotSupported, match="manager"):
        Null[NullComputedForwardRefModel]()


def teardown_module() -> None:
    mapper_registry.dispose(cascade=True)
    mapper_registry.metadata.clear()
