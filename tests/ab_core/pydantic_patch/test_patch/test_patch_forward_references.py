import pytest
from pydantic import BaseModel
from sqlalchemy.orm import registry
from sqlmodel import Field, Relationship, SQLModel

from ab_core.pydantic_patch.core.errors import ForwardReferencesNotSupported
from ab_core.pydantic_patch.patch import Patch, PatchConfig, create_patch_model


mapper_registry = registry()


class ForwardRefSQLModel(SQLModel, registry=mapper_registry):
    __abstract__ = True


class PatchForwardPydanticParent(BaseModel):
    id: int
    child: "PatchForwardPydanticChild"


class PatchForwardPydanticChild(BaseModel):
    id: int


class PatchForwardSqlChild(ForwardRefSQLModel, table=True):
    __tablename__ = "patch_forward_sql_child"

    id: int | None = Field(default=None, primary_key=True)
    parent_id: int | None = Field(default=None, foreign_key="patch_forward_sql_parent.id")
    name: str

    parent: "PatchForwardSqlParent | None" = Relationship(back_populates="children")


class PatchForwardSqlParent(ForwardRefSQLModel, table=True):
    __tablename__ = "patch_forward_sql_parent"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    children: list[PatchForwardSqlChild] = Relationship(back_populates="parent")


@pytest.mark.parametrize(
    "operation",
    [
        lambda: create_patch_model(
            PatchForwardPydanticParent,
            config=PatchConfig(
                pick={"id", "child"},
                partial={"child"},
            ),
        ),
        lambda: Patch[PatchForwardPydanticParent](pick={"id", "child"}, partial={"child"}),
    ],
)
def test_patch_pydantic_forward_refs_raise_custom_error(operation):
    with pytest.raises(ForwardReferencesNotSupported):
        operation()


@pytest.mark.parametrize(
    "operation",
    [
        lambda: create_patch_model(
            PatchForwardSqlParent,
            config=PatchConfig(
                pick={"id", "children"},
                partial={"children"},
            ),
        ),
        lambda: Patch[PatchForwardSqlParent](pick={"id", "children"}, partial={"children"}),
    ],
)
def test_patch_sqlmodel_relationship_forward_refs_raise_custom_error(operation):
    with pytest.raises(ForwardReferencesNotSupported):
        operation()


def teardown_module() -> None:
    mapper_registry.dispose(cascade=True)
    mapper_registry.metadata.clear()
