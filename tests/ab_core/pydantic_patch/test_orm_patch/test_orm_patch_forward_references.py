import pytest
from pydantic import BaseModel
from sqlalchemy.orm import registry
from sqlmodel import Field, Relationship, SQLModel

from ab_core.pydantic_patch.orm_patch import recursive_patch_orm_scalar

mapper_registry = registry()


class ForwardRefSQLModel(SQLModel, registry=mapper_registry):
    __abstract__ = True


class OrmForwardChild(ForwardRefSQLModel, table=True):
    __tablename__ = "orm_forward_child"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    parent_id: int | None = Field(default=None, foreign_key="orm_forward_parent.id")
    parent: "OrmForwardParent" = Relationship(back_populates="children")


class OrmForwardParent(ForwardRefSQLModel, table=True):
    __tablename__ = "orm_forward_parent"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    children: list[OrmForwardChild] = Relationship(back_populates="parent")


class OrmForwardChildPatch(BaseModel):
    id: int
    parent: "OrmForwardParentPatch | None" = None


class OrmForwardParentPatch(BaseModel):
    id: int
    children: list[OrmForwardChildPatch] = []


def test_recursive_patch_orm_scalar_raises_custom_error_for_orm_forward_refs():
    parent = OrmForwardParent(id=1, name="Parent")
    patch = OrmForwardParentPatch(id=1, children=[])

    recursive_patch_orm_scalar(parent, patch)

    assert parent.id == 1


def teardown_module() -> None:
    mapper_registry.dispose(cascade=True)
    mapper_registry.metadata.clear()
