from decimal import Decimal
from typing import Optional

import pytest
from pydantic import Field as PydanticField
from sqlalchemy.orm import registry
from sqlalchemy.pool import StaticPool
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine

from ab_core.pydantic_patch.orm_dump import dump_orm_model

mapper_registry = registry()


class DumpSQLModel(SQLModel, registry=mapper_registry):
    __abstract__ = True


class DumpContractor(DumpSQLModel, table=True):
    __tablename__ = "orm_dump_contractor"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    abn: str | None = None

    quotes: list["DumpQuote"] = Relationship(back_populates="contractor")


class DumpQuote(DumpSQLModel, table=True):
    __tablename__ = "orm_dump_quote"

    id: int | None = Field(default=None, primary_key=True)
    quote_number: str = PydanticField(alias="quoteNumber")
    description: str | None = None
    total_cost: Decimal = Decimal("0.00")

    contractor_id: int | None = Field(
        default=None,
        foreign_key="orm_dump_contractor.id",
    )

    contractor: Optional["DumpContractor"] = Relationship(
        back_populates="quotes",
    )
    line_items: list["DumpLineItem"] = Relationship(
        back_populates="quote",
    )


class DumpLineItem(DumpSQLModel, table=True):
    __tablename__ = "orm_dump_line_item"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    quantity: Decimal
    unit_cost: Decimal

    quote_id: int | None = Field(
        default=None,
        foreign_key="orm_dump_quote.id",
    )

    quote: Optional["DumpQuote"] = Relationship(
        back_populates="line_items",
    )

    detail: Optional["DumpLineItemDetail"] = Relationship(
        back_populates="line_item",
        sa_relationship_kwargs={"uselist": False},
    )


class DumpLineItemDetail(DumpSQLModel, table=True):
    __tablename__ = "orm_dump_line_item_detail"

    id: int | None = Field(default=None, primary_key=True)
    note: str

    line_item_id: int | None = Field(
        default=None,
        foreign_key="orm_dump_line_item.id",
    )

    line_item: Optional["DumpLineItem"] = Relationship(
        back_populates="detail",
    )


class DumpTreeNode(DumpSQLModel, table=True):
    __tablename__ = "orm_dump_tree_node"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    parent_id: int | None = Field(
        default=None,
        foreign_key="orm_dump_tree_node.id",
    )

    parent: Optional["DumpTreeNode"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={
            "remote_side": "DumpTreeNode.id",
        },
    )

    children: list["DumpTreeNode"] = Relationship(
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


@pytest.fixture()
def quote() -> DumpQuote:
    contractor = DumpContractor(
        id=10,
        name="Test Builder Pty Ltd",
        abn="12 345 678 901",
    )

    quote = DumpQuote(
        id=1,
        quoteNumber="Q-001",
        description="Fence replacement quote",
        total_cost=Decimal("1234.56"),
        contractor=contractor,
        contractor_id=10,
    )

    quote.line_items = [
        DumpLineItem(
            id=20,
            name="Timber paling fence",
            quantity=Decimal("12"),
            unit_cost=Decimal("100"),
            quote_id=1,
            detail=DumpLineItemDetail(
                id=30,
                note="Main fence section",
                line_item_id=20,
            ),
        ),
        DumpLineItem(
            id=21,
            name="Timber gate",
            quantity=Decimal("1"),
            unit_cost=Decimal("250"),
            quote_id=1,
            detail=DumpLineItemDetail(
                id=31,
                note="Side access gate",
                line_item_id=21,
            ),
        ),
    ]

    return quote


def test_dump_orm_model_includes_scalar_fields(quote: DumpQuote) -> None:
    payload = dump_orm_model(quote)

    assert payload["id"] == 1
    assert payload["quote_number"] == "Q-001"
    assert payload["description"] == "Fence replacement quote"
    assert payload["total_cost"] == Decimal("1234.56")
    assert payload["contractor_id"] == 10


def test_dump_orm_model_includes_scalar_relationship(quote: DumpQuote) -> None:
    payload = dump_orm_model(quote)

    assert payload["contractor"] == {
        "id": 10,
        "name": "Test Builder Pty Ltd",
        "abn": "12 345 678 901",
    }


def test_dump_orm_model_includes_list_relationship(quote: DumpQuote) -> None:
    payload = dump_orm_model(quote)

    assert len(payload["line_items"]) == 2

    assert payload["line_items"][0]["id"] == 20
    assert payload["line_items"][0]["name"] == "Timber paling fence"
    assert payload["line_items"][0]["quantity"] == Decimal("12")
    assert payload["line_items"][0]["unit_cost"] == Decimal("100")
    assert payload["line_items"][0]["quote_id"] == 1

    assert payload["line_items"][1]["id"] == 21
    assert payload["line_items"][1]["name"] == "Timber gate"


def test_dump_orm_model_includes_nested_scalar_relationship(quote: DumpQuote) -> None:
    payload = dump_orm_model(quote)

    assert payload["line_items"][0]["detail"] == {
        "id": 30,
        "note": "Main fence section",
        "line_item_id": 20,
    }


def test_dump_orm_model_does_not_include_automatically_excluded_backrefs(
    quote: DumpQuote,
) -> None:
    payload = dump_orm_model(quote)

    assert "quotes" not in payload["contractor"]
    assert "quote" not in payload["line_items"][0]
    assert "line_item" not in payload["line_items"][0]["detail"]


def test_dump_orm_model_respects_include(quote: DumpQuote) -> None:
    payload = dump_orm_model(
        quote,
        include={
            "quote_number": True,
            "contractor": {
                "name": True,
            },
            "line_items": {
                "__all__": {
                    "name": True,
                }
            },
        },
    )

    assert payload == {
        "quote_number": "Q-001",
        "contractor": {
            "name": "Test Builder Pty Ltd",
        },
        "line_items": [
            {
                "name": "Timber paling fence",
            },
            {
                "name": "Timber gate",
            },
        ],
    }


def test_dump_orm_model_respects_exclude(quote: DumpQuote) -> None:
    payload = dump_orm_model(
        quote,
        exclude={
            "description": True,
            "contractor": {
                "abn": True,
            },
            "line_items": {
                "__all__": {
                    "detail": True,
                }
            },
        },
    )

    assert "description" not in payload

    assert payload["contractor"] == {
        "id": 10,
        "name": "Test Builder Pty Ltd",
    }

    assert "detail" not in payload["line_items"][0]
    assert "detail" not in payload["line_items"][1]


def test_dump_orm_model_respects_exclude_none() -> None:
    quote = DumpQuote(
        id=1,
        quoteNumber="Q-NONE",
        description=None,
        total_cost=Decimal("0.00"),
        contractor=None,
        contractor_id=None,
        line_items=[],
    )

    payload = dump_orm_model(
        quote,
        exclude_none=True,
    )

    assert payload == {
        "id": 1,
        "quote_number": "Q-NONE",
        "total_cost": Decimal("0.00"),
        "line_items": [],
    }


def test_dump_orm_model_respects_exclude_defaults() -> None:
    quote = DumpQuote(
        quoteNumber="Q-DEFAULTS",
        total_cost=Decimal("0.00"),
        line_items=[],
    )

    payload = dump_orm_model(
        quote,
        exclude_defaults=True,
        exclude_none=True,
    )

    assert payload == {
        "quote_number": "Q-DEFAULTS",
        "line_items": [],
    }


def test_dump_orm_model_respects_by_alias(quote: DumpQuote) -> None:
    payload = dump_orm_model(
        quote,
        by_alias=True,
    )

    assert "quoteNumber" in payload
    assert "quote_number" not in payload
    assert payload["quoteNumber"] == "Q-001"


def test_dump_orm_model_supports_python_mode(quote: DumpQuote) -> None:
    payload = dump_orm_model(
        quote,
        mode="python",
    )

    assert payload["total_cost"] == Decimal("1234.56")
    assert payload["line_items"][0]["quantity"] == Decimal("12")
    assert payload["line_items"][0]["unit_cost"] == Decimal("100")


def test_dump_orm_model_supports_json_mode(quote: DumpQuote) -> None:
    payload = dump_orm_model(
        quote,
        mode="json",
    )

    assert payload["total_cost"] == "1234.56"
    assert payload["line_items"][0]["quantity"] == "12"
    assert payload["line_items"][0]["unit_cost"] == "100"


def test_dump_orm_model_supports_round_trip(quote: DumpQuote) -> None:
    payload = dump_orm_model(
        quote,
        round_trip=True,
    )

    assert payload["quote_number"] == "Q-001"
    assert payload["total_cost"] == Decimal("1234.56")


def test_dump_orm_model_handles_empty_relationship_list() -> None:
    quote = DumpQuote(
        id=1,
        quoteNumber="Q-EMPTY",
        total_cost=Decimal("0.00"),
        line_items=[],
    )

    payload = dump_orm_model(quote)

    assert payload["line_items"] == []


def test_dump_orm_model_handles_none_scalar_relationship() -> None:
    quote = DumpQuote(
        id=1,
        quoteNumber="Q-NONE-REL",
        contractor=None,
        line_items=[],
    )

    payload = dump_orm_model(quote)

    assert payload["contractor"] is None
    assert payload["line_items"] == []


def test_dump_orm_model_self_referencing_tree_excludes_parent_but_keeps_parent_id() -> None:
    root = DumpTreeNode(id=1, name="Root")
    child = DumpTreeNode(
        id=2,
        name="Child",
        parent=root,
        parent_id=1,
    )
    grandchild = DumpTreeNode(
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


def test_dump_orm_model_persisted_graph_loaded_from_database(engine) -> None:
    with Session(engine) as session:
        contractor = DumpContractor(
            name="Persisted Builder",
            abn="98 765 432 109",
        )

        quote = DumpQuote(
            quoteNumber="Q-DB",
            total_cost=Decimal("500.00"),
            contractor=contractor,
        )

        quote.line_items = [
            DumpLineItem(
                name="Database item",
                quantity=Decimal("1"),
                unit_cost=Decimal("500.00"),
                detail=DumpLineItemDetail(
                    note="Database detail",
                ),
            )
        ]

        session.add(quote)
        session.commit()

        quote_id = quote.id

    with Session(engine) as session:
        quote = session.get(DumpQuote, quote_id)

        assert quote is not None

        # Explicitly load relationships so this test is about dumping,
        # not lazy loading behaviour.
        assert quote.contractor is not None
        assert len(quote.line_items) == 1
        assert quote.line_items[0].detail is not None

        payload = dump_orm_model(quote)

    assert payload["quote_number"] == "Q-DB"
    assert payload["total_cost"] == Decimal("500.00")

    assert payload["contractor"]["name"] == "Persisted Builder"
    assert payload["contractor"]["abn"] == "98 765 432 109"

    assert payload["line_items"][0]["name"] == "Database item"
    assert payload["line_items"][0]["detail"]["note"] == "Database detail"


def test_dump_orm_model_matches_manual_relationship_payload_shape(
    quote: DumpQuote,
) -> None:
    payload = dump_orm_model(quote)

    assert payload == {
        "id": 1,
        "quote_number": "Q-001",
        "description": "Fence replacement quote",
        "total_cost": Decimal("1234.56"),
        "contractor_id": 10,
        "contractor": {
            "id": 10,
            "name": "Test Builder Pty Ltd",
            "abn": "12 345 678 901",
        },
        "line_items": [
            {
                "id": 20,
                "name": "Timber paling fence",
                "quantity": Decimal("12"),
                "unit_cost": Decimal("100"),
                "quote_id": 1,
                "detail": {
                    "id": 30,
                    "note": "Main fence section",
                    "line_item_id": 20,
                },
            },
            {
                "id": 21,
                "name": "Timber gate",
                "quantity": Decimal("1"),
                "unit_cost": Decimal("250"),
                "quote_id": 1,
                "detail": {
                    "id": 31,
                    "note": "Side access gate",
                    "line_item_id": 21,
                },
            },
        ],
    }


def test_dump_orm_model_validates_from_attribute_name_when_field_has_alias(
    quote: DumpQuote,
) -> None:
    payload = dump_orm_model(quote)

    assert payload["quote_number"] == "Q-001"


def teardown_module() -> None:
    mapper_registry.dispose(cascade=True)
    mapper_registry.metadata.clear()
