"""ORM patch tests for self-referencing 1..many SQLModel trees."""

from sqlalchemy.orm import registry
from sqlmodel import Field, Relationship, SQLModel

from ab_core.pydantic_patch.orm_patch import recursive_patch_orm_scalar
from ab_core.pydantic_patch.patch import Patch, PatchConfig

mapper_registry = registry()


class TreeSQLModel(SQLModel, registry=mapper_registry):
    """Isolated SQLModel base for this test module."""

    __abstract__ = True


class QuoteLineItem(TreeSQLModel, table=True):
    """Self-referencing quote line item tree."""

    __tablename__ = "recursive_quote_line_item"

    id: int | None = Field(default=None, primary_key=True)
    parent_id: int | None = Field(default=None, foreign_key="recursive_quote_line_item.id")

    line_item_name: str = ""
    quoted_base_cost: float = 0.0
    internal_notes: str = ""

    parent: "QuoteLineItem" = Relationship(
        back_populates="children",
        sa_relationship_kwargs={
            "remote_side": "QuoteLineItem.id",
        },
    )
    children: list["QuoteLineItem"] = Relationship(back_populates="parent")


def test_recursive_patch_orm_scalar_updates_self_referencing_tree_children() -> None:
    line_item_patch = Patch[QuoteLineItem](
        name="QuoteLineItemPatch",
        pick={
            "id",
            "line_item_name",
            "quoted_base_cost",
            "children",
        },
        partial={
            "id",
            "line_item_name",
            "quoted_base_cost",
            "children",
        },
        child_models={
            QuoteLineItem: PatchConfig(
                pick={
                    "id",
                    "line_item_name",
                    "quoted_base_cost",
                    "children",
                },
                partial={
                    "id",
                    "line_item_name",
                    "quoted_base_cost",
                    "children",
                },
            ),
        },
    )

    existing = QuoteLineItem(
        id=1,
        line_item_name="Fence",
        quoted_base_cost=1200.0,
        internal_notes="Do not expose",
        children=[
            QuoteLineItem(
                id=10,
                parent_id=1,
                line_item_name="Old panels",
                quoted_base_cost=700.0,
                internal_notes="Keep hidden",
            ),
            QuoteLineItem(
                id=11,
                parent_id=1,
                line_item_name="Posts",
                quoted_base_cost=500.0,
                internal_notes="Keep hidden",
            ),
        ],
    )

    patch = line_item_patch.model_validate(
        {
            "id": 1,
            "line_item_name": "Colorbond fence",
            "children": [
                {
                    "id": 10,
                    "line_item_name": "Colorbond panels",
                    "quoted_base_cost": 725.0,
                },
                {
                    "id": 11,
                    "quoted_base_cost": 525.0,
                },
            ],
        }
    )

    recursive_patch_orm_scalar(existing, patch)

    assert existing.id == 1
    assert existing.line_item_name == "Colorbond fence"
    assert existing.quoted_base_cost == 1200.0
    assert existing.internal_notes == "Do not expose"

    assert len(existing.children) == 2

    assert existing.children[0].id == 10
    assert existing.children[0].line_item_name == "Colorbond panels"
    assert existing.children[0].quoted_base_cost == 725.0
    assert existing.children[0].internal_notes == "Keep hidden"

    assert existing.children[1].id == 11
    assert existing.children[1].line_item_name == "Posts"
    assert existing.children[1].quoted_base_cost == 525.0
    assert existing.children[1].internal_notes == "Keep hidden"


def test_recursive_patch_orm_scalar_creates_new_self_referencing_child() -> None:
    line_item_patch = Patch[QuoteLineItem](
        name="QuoteLineItemPatchCreateChild",
        pick={
            "id",
            "line_item_name",
            "quoted_base_cost",
            "children",
        },
        partial={
            "id",
            "line_item_name",
            "quoted_base_cost",
            "children",
        },
        child_models={
            QuoteLineItem: PatchConfig(
                pick={
                    "id",
                    "line_item_name",
                    "quoted_base_cost",
                    "children",
                },
                partial={
                    "id",
                    "line_item_name",
                    "quoted_base_cost",
                    "children",
                },
            ),
        },
    )

    existing = QuoteLineItem(
        id=1,
        line_item_name="Fence",
        quoted_base_cost=1200.0,
        children=[],
    )

    patch = line_item_patch.model_validate(
        {
            "id": 1,
            "children": [
                {
                    "line_item_name": "New child line item",
                    "quoted_base_cost": 300.0,
                },
            ],
        }
    )

    recursive_patch_orm_scalar(existing, patch)

    assert len(existing.children) == 1
    assert existing.children[0].id is None
    assert existing.children[0].line_item_name == "New child line item"
    assert existing.children[0].quoted_base_cost == 300.0


def test_recursive_patch_orm_scalar_updates_grandchildren_in_self_referencing_tree() -> None:
    line_item_patch = Patch[QuoteLineItem](
        name="QuoteLineItemPatchGrandchildren",
        pick={
            "id",
            "line_item_name",
            "quoted_base_cost",
            "children",
        },
        partial={
            "id",
            "line_item_name",
            "quoted_base_cost",
            "children",
        },
        child_models={
            QuoteLineItem: PatchConfig(
                pick={
                    "id",
                    "line_item_name",
                    "quoted_base_cost",
                    "children",
                },
                partial={
                    "id",
                    "line_item_name",
                    "quoted_base_cost",
                    "children",
                },
            ),
        },
    )

    existing = QuoteLineItem(
        id=1,
        line_item_name="Fence",
        children=[
            QuoteLineItem(
                id=10,
                parent_id=1,
                line_item_name="Materials",
                children=[
                    QuoteLineItem(
                        id=100,
                        parent_id=10,
                        line_item_name="Old screws",
                        quoted_base_cost=25.0,
                    ),
                ],
            ),
        ],
    )

    patch = line_item_patch.model_validate(
        {
            "id": 1,
            "children": [
                {
                    "id": 10,
                    "children": [
                        {
                            "id": 100,
                            "line_item_name": "Galvanised screws",
                            "quoted_base_cost": 30.0,
                        },
                    ],
                },
            ],
        }
    )

    recursive_patch_orm_scalar(existing, patch)

    grandchild = existing.children[0].children[0]

    assert grandchild.id == 100
    assert grandchild.line_item_name == "Galvanised screws"
    assert grandchild.quoted_base_cost == 30.0


def teardown_module() -> None:
    mapper_registry.dispose(cascade=True)
    mapper_registry.metadata.clear()
