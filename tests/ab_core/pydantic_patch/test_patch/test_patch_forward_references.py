from __future__ import annotations

import pytest
from pydantic import BaseModel, computed_field
from sqlalchemy.orm import registry
from sqlmodel import Field, Relationship, SQLModel
from uuid import UUID

from ab_core.pydantic_patch.core.errors import ForwardReferencesNotSupported
from ab_core.pydantic_patch.core.type_hints import get_resolved_type_hints
from ab_core.pydantic_patch.patch import Patch, PatchConfig, create_patch_model

mapper_registry = registry()


class ForwardRefSQLModel(SQLModel, registry=mapper_registry):
    __abstract__ = True


class PatchForwardPydanticParent(BaseModel):
    id: int
    child: "PatchForwardPydanticChildMissing"


class PatchForwardPydanticChild(BaseModel):
    id: int


class PatchComputedForwardRefModel(BaseModel):
    @computed_field
    @property
    def manager(self) -> "PatchMissingManager":
        """Return the unresolved computed manager type."""
        raise NotImplementedError


class PatchForwardSqlChild(ForwardRefSQLModel, table=True):
    __tablename__ = "patch_forward_sql_child"

    id: int | None = Field(default=None, primary_key=True)
    parent_id: int | None = Field(default=None, foreign_key="patch_forward_sql_parent.id")
    name: str

    parent: "PatchForwardSqlParentMissing | None" = Relationship(back_populates="children")


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
def test_unresolved_pydantic_forward_refs_raise_custom_error(operation):
    with pytest.raises(ForwardReferencesNotSupported):
        operation()


def test_unresolved_forward_ref_error_does_not_suggest_manual_module_binding() -> None:
    with pytest.raises(ForwardReferencesNotSupported) as error:
        Patch[PatchForwardPydanticParent](pick={"id", "child"}, partial={"child"})

    message = str(error.value)

    assert "model_rebuild(force=True)" not in message
    assert "_module." not in message
    assert "ty: ignore[unresolved-attribute]" not in message
    assert "import the model package" in message


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
def test_resolved_sqlmodel_relationship_forward_refs_are_supported(operation):
    model = operation()

    assert "children" in model.model_fields


class PatchResolvedPydanticParent(BaseModel):
    id: int
    child: "PatchResolvedPydanticChild"


class PatchResolvedPydanticChild(BaseModel):
    id: int


class RecursiveTypeHintsModel(BaseModel):
    id: UUID | None = None
    children: list[RecursiveTypeHintsModel] = []


def test_patch_resolved_pydantic_forward_refs_are_supported():
    patch_model = Patch[PatchResolvedPydanticParent](
        pick={"id", "child"},
        partial={"child"},
    )

    assert "child" in patch_model.model_fields


def test_get_resolved_type_hints_handles_recursive_forward_refs_without_type_params() -> None:
    hints = get_resolved_type_hints(RecursiveTypeHintsModel)

    assert "id" in hints
    assert "children" in hints


def test_patch_computed_field_forward_ref_raises_custom_error() -> None:
    with pytest.raises(ForwardReferencesNotSupported, match="manager"):
        Patch[PatchComputedForwardRefModel]()


def teardown_module() -> None:
    mapper_registry.dispose(cascade=True)
    mapper_registry.metadata.clear()
