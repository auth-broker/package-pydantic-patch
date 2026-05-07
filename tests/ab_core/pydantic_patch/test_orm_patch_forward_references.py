import pytest
from pydantic import BaseModel
from sqlalchemy.orm import registry
from sqlmodel import Field, Relationship, SQLModel

from ab_core.pydantic_patch.core.errors import ForwardReferencesNotSupported
from ab_core.pydantic_patch.orm_patch import recursive_patch_orm_scalar


mapper_registry = registry()


class ForwardRefSQLModel(SQLModel, registry=mapper_registry):
    __abstract__ = True


class OrmForwardChildPatch(BaseModel):
    id: int
    parent: "OrmForwardParentPatch | None" = None


class OrmForwardParentPatch(BaseModel):
    id: int
    children: list[OrmForwardChildPatch] = []


class OrmForwardChild(ForwardRefSQLModel, table=True):
    __tablename__ = "orm_forward_child"

    id: int | None = Field(default=None, primary_key=True)
    parent_id: int | None = Field(default=None, foreign_key="orm_forward_parent.id")
    name: str

    parent: "OrmForwardParent | None" = Relationship(back_populates="children")


class OrmForwardParent(ForwardRefSQLModel, table=True):
    __tablename__ = "orm_forward_parent"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    children: list[OrmForwardChild] = Relationship(back_populates="parent")


def test_recursive_patch_orm_scalar_raises_custom_error_for_orm_forward_refs():
    with pytest.raises(ForwardReferencesNotSupported):
        recursive_patch_orm_scalar(
            OrmForwardParent(id=1, name="Parent"),
            OrmForwardParentPatch(id=1, children=[]),
        )


def teardown_module() -> None:
    mapper_registry.dispose(cascade=True)
    mapper_registry.metadata.clear()
