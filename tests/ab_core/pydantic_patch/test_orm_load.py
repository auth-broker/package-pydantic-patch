from decimal import Decimal
from typing import Optional

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import registry
from sqlalchemy.pool import StaticPool
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine

from ab_core.pydantic_patch.orm_dump import dump_orm_model
from ab_core.pydantic_patch.orm_load import load_orm_model

mapper_registry = registry()


class LoadSQLModel(SQLModel, registry=mapper_registry):
    __abstract__ = True


class LoadContractor(LoadSQLModel, table=True):
    __tablename__ = "orm_load_contractor"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    abn: str | None = None

    quotes: list["LoadQuote"] = Relationship(back_populates="contractor")


class LoadQuote(LoadSQLModel, table=True):
    __tablename__ = "orm_load_quote"

    id: int | None = Field(default=None, primary_key=True)
    quote_number: str
    description: str | None = None
    total_cost: Decimal = Decimal("0.00")

    contractor_id: int | None = Field(
        default=None,
        foreign_key="orm_load_contractor.id",
    )

    contractor: Optional["LoadContractor"] = Relationship(
        back_populates="quotes",
    )
    line_items: list["LoadLineItem"] = Relationship(
        back_populates="quote",
    )


class LoadLineItem(LoadSQLModel, table=True):
    __tablename__ = "orm_load_line_item"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    quantity: Decimal
    unit_cost: Decimal

    quote_id: int | None = Field(
        default=None,
        foreign_key="orm_load_quote.id",
    )

    quote: Optional["LoadQuote"] = Relationship(
        back_populates="line_items",
    )

    detail: Optional["LoadLineItemDetail"] = Relationship(
        back_populates="line_item",
        sa_relationship_kwargs={"uselist": False},
    )


class LoadLineItemDetail(LoadSQLModel, table=True):
    __tablename__ = "orm_load_line_item_detail"

    id: int | None = Field(default=None, primary_key=True)
    note: str

    line_item_id: int | None = Field(
        default=None,
        foreign_key="orm_load_line_item.id",
    )

    line_item: Optional["LoadLineItem"] = Relationship(
        back_populates="detail",
    )


class LoadTreeNode(LoadSQLModel, table=True):
    __tablename__ = "orm_load_tree_node"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    parent_id: int | None = Field(
        default=None,
        foreign_key="orm_load_tree_node.id",
    )

    parent: Optional["LoadTreeNode"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={
            "remote_side": "LoadTreeNode.id",
        },
    )

    children: list["LoadTreeNode"] = Relationship(
        back_populates="parent",
    )


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    mapper_registry.metadata.create_all(engine)

    return engine


def test_loads_normal_scalar_fields_from_json() -> None:
    quote = load_orm_model(
        LoadQuote,
        {
            "id": 1,
            "quote_number": "Q-001",
            "description": "Fence quote",
            "total_cost": "1234.56",
        },
    )

    assert isinstance(quote, LoadQuote)
    assert quote.id == 1
    assert quote.quote_number == "Q-001"
    assert quote.description == "Fence quote"
    assert quote.total_cost == Decimal("1234.56")


def test_loaded_instance_is_transient() -> None:
    quote = load_orm_model(
        LoadQuote,
        {
            "id": 1,
            "quote_number": "Q-001",
            "total_cost": "1234.56",
        },
    )

    state = inspect(quote)

    assert state.transient
    assert state.session is None


def test_loads_scalar_relationship_from_json() -> None:
    quote = load_orm_model(
        LoadQuote,
        {
            "id": 1,
            "quote_number": "Q-001",
            "contractor_id": 10,
            "contractor": {
                "id": 10,
                "name": "Test Builder Pty Ltd",
                "abn": "12 345 678 901",
            },
        },
    )

    assert quote.contractor is not None
    assert isinstance(quote.contractor, LoadContractor)

    assert quote.contractor.id == 10
    assert quote.contractor.name == "Test Builder Pty Ltd"
    assert quote.contractor.abn == "12 345 678 901"


def test_loads_list_relationship_from_json() -> None:
    quote = load_orm_model(
        LoadQuote,
        {
            "id": 1,
            "quote_number": "Q-001",
            "line_items": [
                {
                    "id": 10,
                    "name": "Fence section",
                    "quantity": "12",
                    "unit_cost": "100",
                    "quote_id": 1,
                },
                {
                    "id": 11,
                    "name": "Gate",
                    "quantity": "1",
                    "unit_cost": "250",
                    "quote_id": 1,
                },
            ],
        },
    )

    assert len(quote.line_items) == 2

    assert quote.line_items[0].id == 10
    assert quote.line_items[0].name == "Fence section"
    assert quote.line_items[0].quantity == Decimal("12")
    assert quote.line_items[0].unit_cost == Decimal("100")

    assert quote.line_items[1].id == 11
    assert quote.line_items[1].name == "Gate"


def test_loads_nested_scalar_relationship_inside_list_relationship() -> None:
    quote = load_orm_model(
        LoadQuote,
        {
            "id": 1,
            "quote_number": "Q-001",
            "line_items": [
                {
                    "id": 10,
                    "name": "Fence section",
                    "quantity": "12",
                    "unit_cost": "100",
                    "detail": {
                        "id": 100,
                        "note": "Main fence section",
                        "line_item_id": 10,
                    },
                }
            ],
        },
    )

    assert len(quote.line_items) == 1

    line_item = quote.line_items[0]

    assert line_item.detail is not None
    assert line_item.detail.id == 100
    assert line_item.detail.note == "Main fence section"


def test_back_populated_relationships_are_wired_after_loading() -> None:
    quote = load_orm_model(
        LoadQuote,
        {
            "id": 1,
            "quote_number": "Q-001",
            "contractor": {
                "id": 10,
                "name": "Test Builder Pty Ltd",
            },
            "line_items": [
                {
                    "id": 20,
                    "name": "Fence section",
                    "quantity": "12",
                    "unit_cost": "100",
                }
            ],
        },
    )

    assert quote.contractor is not None
    assert quote in quote.contractor.quotes

    assert quote.line_items[0].quote is quote


def test_load_preserves_primary_keys_by_default() -> None:
    quote = load_orm_model(
        LoadQuote,
        {
            "id": 123,
            "quote_number": "Q-PK",
        },
    )

    assert quote.id == 123


def test_load_can_exclude_primary_keys() -> None:
    quote = load_orm_model(
        LoadQuote,
        {
            "id": 123,
            "quote_number": "Q-PK",
        },
        include_primary_keys=False,
    )

    assert quote.id is None
    assert quote.quote_number == "Q-PK"


def test_load_preserves_foreign_keys_by_default() -> None:
    quote = load_orm_model(
        LoadQuote,
        {
            "id": 1,
            "quote_number": "Q-FK",
            "contractor_id": 10,
        },
    )

    assert quote.contractor_id == 10


def test_load_can_exclude_foreign_keys() -> None:
    quote = load_orm_model(
        LoadQuote,
        {
            "id": 1,
            "quote_number": "Q-FK",
            "contractor_id": 10,
        },
        include_foreign_keys=False,
    )

    assert quote.contractor_id is None


def test_load_handles_none_scalar_relationship() -> None:
    quote = load_orm_model(
        LoadQuote,
        {
            "id": 1,
            "quote_number": "Q-NONE",
            "contractor": None,
        },
    )

    assert quote.contractor is None


def test_load_handles_empty_list_relationship() -> None:
    quote = load_orm_model(
        LoadQuote,
        {
            "id": 1,
            "quote_number": "Q-EMPTY",
            "line_items": [],
        },
    )

    assert quote.line_items == []


def test_load_self_referential_tree_without_parent_relationship_in_json() -> None:
    root = load_orm_model(
        LoadTreeNode,
        {
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
        },
    )

    assert root.id == 1
    assert root.name == "Root"
    assert root.parent_id is None

    child = root.children[0]

    assert child.id == 2
    assert child.name == "Child"
    assert child.parent_id == 1
    assert child.parent is root

    grandchild = child.children[0]

    assert grandchild.id == 3
    assert grandchild.name == "Grandchild"
    assert grandchild.parent_id == 2
    assert grandchild.parent is child


def test_load_round_trips_from_dumped_orm_model() -> None:
    original = LoadQuote(
        id=1,
        quote_number="Q-ROUND-TRIP",
        description="Round trip quote",
        total_cost=Decimal("1234.56"),
        contractor=LoadContractor(
            id=10,
            name="Round Trip Builder",
            abn="12 345 678 901",
        ),
        contractor_id=10,
        line_items=[
            LoadLineItem(
                id=20,
                name="Fence section",
                quantity=Decimal("12"),
                unit_cost=Decimal("100"),
                quote_id=1,
                detail=LoadLineItemDetail(
                    id=30,
                    note="Round trip detail",
                    line_item_id=20,
                ),
            )
        ],
    )

    dumped = dump_orm_model(original)

    loaded = load_orm_model(LoadQuote, dumped)

    assert loaded is not original
    assert loaded.id == original.id
    assert loaded.quote_number == original.quote_number
    assert loaded.total_cost == original.total_cost

    assert loaded.contractor is not None
    assert original.contractor is not None
    assert loaded.contractor is not original.contractor
    assert loaded.contractor.name == "Round Trip Builder"

    assert len(loaded.line_items) == 1
    assert loaded.line_items[0] is not original.line_items[0]
    assert loaded.line_items[0].name == "Fence section"
    assert loaded.line_items[0].quote is loaded

    assert loaded.line_items[0].detail is not None
    assert loaded.line_items[0].detail.note == "Round trip detail"


def test_loaded_graph_can_be_flushed(engine) -> None:
    quote = load_orm_model(
        LoadQuote,
        {
            "quote_number": "Q-FLUSH",
            "description": "Flushable graph",
            "total_cost": "500.00",
            "contractor": {
                "name": "Flush Builder",
            },
            "line_items": [
                {
                    "name": "Database item",
                    "quantity": "1",
                    "unit_cost": "500.00",
                    "detail": {
                        "note": "Database detail",
                    },
                }
            ],
        },
        include_primary_keys=False,
        include_foreign_keys=False,
    )

    with Session(engine) as session:
        session.add(quote)
        session.flush()

        assert quote.id is not None

        assert quote.contractor is not None
        assert quote.contractor.id is not None

        assert len(quote.line_items) == 1

        line_item = quote.line_items[0]

        assert line_item.id is not None
        assert line_item.quote_id == quote.id

        assert line_item.detail is not None
        assert line_item.detail.id is not None
        assert line_item.detail.line_item_id == line_item.id


def teardown_module() -> None:
    mapper_registry.dispose(cascade=True)
    mapper_registry.metadata.clear()
