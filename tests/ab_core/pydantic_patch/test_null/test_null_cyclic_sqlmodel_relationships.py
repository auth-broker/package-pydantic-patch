from decimal import Decimal
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import registry
from sqlmodel import Field, Relationship, SQLModel

from ab_core.pydantic_patch.null import Null
from ab_core.pydantic_patch.orm_dump import dump_orm_model
from tests.helpers.assert_model import get_list_item_type

mapper_registry = registry()


class NullCycleSQLModel(SQLModel, registry=mapper_registry):
    __abstract__ = True


class NullCycleContractor(NullCycleSQLModel, table=True):
    __tablename__ = "null_cycle_contractor"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    quotes: list["NullCycleQuote"] = Relationship(back_populates="contractor")


class NullCycleQuote(NullCycleSQLModel, table=True):
    __tablename__ = "null_cycle_quote"

    id: int | None = Field(default=None, primary_key=True)
    quote_number: str
    total_cost: Decimal = Decimal("0.00")

    contractor_id: int | None = Field(
        default=None,
        foreign_key="null_cycle_contractor.id",
    )

    contractor: Optional["NullCycleContractor"] = Relationship(
        back_populates="quotes",
    )
    line_items: list["NullCycleLineItem"] = Relationship(
        back_populates="quote",
    )


class NullCycleLineItem(NullCycleSQLModel, table=True):
    __tablename__ = "null_cycle_line_item"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    quote_id: int | None = Field(
        default=None,
        foreign_key="null_cycle_quote.id",
    )

    quote: Optional["NullCycleQuote"] = Relationship(
        back_populates="line_items",
    )


class NullCycleTreeNode(NullCycleSQLModel, table=True):
    __tablename__ = "null_cycle_tree_node"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    parent_id: int | None = Field(
        default=None,
        foreign_key="null_cycle_tree_node.id",
    )

    parent: Optional["NullCycleTreeNode"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={
            "remote_side": "NullCycleTreeNode.id",
        },
    )

    children: list["NullCycleTreeNode"] = Relationship(
        back_populates="parent",
    )


def teardown_module() -> None:
    mapper_registry.dispose(cascade=True)
    mapper_registry.metadata.clear()


def _unwrap_optional_model(annotation: object) -> type[BaseModel]:
    args = getattr(annotation, "__args__", ())
    if not args:
        assert isinstance(annotation, type)
        assert issubclass(annotation, BaseModel)
        return annotation

    model_types = [arg for arg in args if isinstance(arg, type) and issubclass(arg, BaseModel)]

    assert len(model_types) == 1
    return model_types[0]


def test_null_self_referencing_model_excludes_parent_relationship_but_keeps_parent_id() -> None:
    result = Null[NullCycleTreeNode]()

    assert "id" in result.model_fields
    assert "name" in result.model_fields
    assert "parent_id" in result.model_fields
    assert "children" in result.model_fields

    assert "parent" not in result.model_fields


def test_null_self_referencing_child_model_is_recursive_without_parent_backref() -> None:
    result = Null[NullCycleTreeNode]()

    child_type = get_list_item_type(result.model_fields["children"].annotation)

    assert "id" in child_type.model_fields
    assert "name" in child_type.model_fields
    assert "parent_id" in child_type.model_fields
    assert "children" in child_type.model_fields
    assert "parent" not in child_type.model_fields


def test_dump_orm_model_self_referencing_tree_excludes_parent_but_keeps_parent_id() -> None:
    root = NullCycleTreeNode(id=1, name="Root")
    child = NullCycleTreeNode(
        id=2,
        name="Child",
        parent=root,
        parent_id=1,
    )
    grandchild = NullCycleTreeNode(
        id=3,
        name="Grandchild",
        parent=child,
        parent_id=2,
    )

    root.children = [child]
    child.children = [grandchild]

    payload = dump_orm_model(root)

    assert payload == {
        "id": 1,
        "name": "Root",
        "parent_id": None,
        "children": [
            {
                "id": 2,
                "name": "Child",
                "parent_id": 1,
                "children": [
                    {
                        "id": 3,
                        "name": "Grandchild",
                        "parent_id": 2,
                        "children": [],
                    }
                ],
            }
        ],
    }


def test_null_excludes_contractor_quotes_backref_but_keeps_contractor_id() -> None:
    result = Null[NullCycleQuote]()

    contractor_type = _unwrap_optional_model(result.model_fields["contractor"].annotation)

    assert "contractor_id" in result.model_fields
    assert "contractor" in result.model_fields

    assert "id" in contractor_type.model_fields
    assert "name" in contractor_type.model_fields
    assert "quotes" not in contractor_type.model_fields


def test_dump_orm_model_bidirectional_contractor_quote_cycle() -> None:
    contractor = NullCycleContractor(
        id=10,
        name="Cycle Builder",
    )

    quote = NullCycleQuote(
        id=20,
        quote_number="Q-CYCLE",
        contractor=contractor,
        contractor_id=10,
        total_cost=Decimal("100.00"),
    )

    contractor.quotes = [quote]

    payload = dump_orm_model(quote)

    assert payload["id"] == 20
    assert payload["quote_number"] == "Q-CYCLE"
    assert payload["contractor_id"] == 10

    assert payload["contractor"] == {
        "id": 10,
        "name": "Cycle Builder",
    }


def test_null_excludes_line_item_quote_backref_but_keeps_quote_id() -> None:
    result = Null[NullCycleQuote]()

    line_item_type = get_list_item_type(result.model_fields["line_items"].annotation)

    assert "id" in line_item_type.model_fields
    assert "name" in line_item_type.model_fields
    assert "quote_id" in line_item_type.model_fields

    assert "quote" not in line_item_type.model_fields


def test_dump_orm_model_line_item_quote_backref_cycle() -> None:
    quote = NullCycleQuote(
        id=1,
        quote_number="Q-LINE-CYCLE",
        total_cost=Decimal("500.00"),
    )

    line_item = NullCycleLineItem(
        id=2,
        name="Fence section",
        quote=quote,
        quote_id=1,
    )

    quote.line_items = [line_item]

    payload = dump_orm_model(quote)

    assert payload["id"] == 1
    assert payload["quote_number"] == "Q-LINE-CYCLE"

    assert payload["line_items"] == [
        {
            "id": 2,
            "name": "Fence section",
            "quote_id": 1,
        }
    ]
