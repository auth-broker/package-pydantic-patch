from decimal import Decimal
from typing import Optional

import pytest
from pydantic import BaseModel, TypeAdapter
from sqlalchemy.orm import registry
from sqlalchemy.pool import StaticPool
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine

from ab_core.pydantic_patch.null import Null, create_null_model
from ab_core.pydantic_patch.orm_dump import dump_orm_model

mapper_registry = registry()


class NullRelationshipSQLModel(SQLModel, registry=mapper_registry):
    __abstract__ = True


class NullContractor(NullRelationshipSQLModel, table=True):
    __tablename__ = "null_contractor"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    abn: str | None = None

    quotes: list["NullQuote"] = Relationship(back_populates="contractor")


class NullQuote(NullRelationshipSQLModel, table=True):
    __tablename__ = "null_quote"

    id: int | None = Field(default=None, primary_key=True)
    quote_number: str
    description: str | None = None
    total_cost: Decimal = Decimal("0.00")

    contractor_id: int | None = Field(
        default=None,
        foreign_key="null_contractor.id",
    )

    contractor: Optional["NullContractor"] = Relationship(
        back_populates="quotes",
    )
    line_items: list["NullLineItem"] = Relationship(
        back_populates="quote",
    )


class NullLineItem(NullRelationshipSQLModel, table=True):
    __tablename__ = "null_line_item"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    quantity: Decimal
    unit_cost: Decimal

    quote_id: int | None = Field(
        default=None,
        foreign_key="null_quote.id",
    )

    quote: Optional["NullQuote"] = Relationship(
        back_populates="line_items",
    )

    detail: Optional["NullLineItemDetail"] = Relationship(
        back_populates="line_item",
        sa_relationship_kwargs={"uselist": False},
    )


class NullLineItemDetail(NullRelationshipSQLModel, table=True):
    __tablename__ = "null_line_item_detail"

    id: int | None = Field(default=None, primary_key=True)
    note: str

    line_item_id: int | None = Field(
        default=None,
        foreign_key="null_line_item.id",
    )

    line_item: Optional["NullLineItem"] = Relationship(
        back_populates="detail",
    )


class NullTreeNode(NullRelationshipSQLModel, table=True):
    __tablename__ = "null_tree_node"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    parent_id: int | None = Field(
        default=None,
        foreign_key="null_tree_node.id",
    )

    parent: Optional["NullTreeNode"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={
            "remote_side": "NullTreeNode.id",
        },
    )

    children: list["NullTreeNode"] = Relationship(
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


def teardown_module() -> None:
    mapper_registry.dispose(cascade=True)
    mapper_registry.metadata.clear()


@pytest.fixture()
def populated_quote() -> NullQuote:
    contractor = NullContractor(
        name="Test Builder Pty Ltd",
        abn="12 345 678 901",
    )

    quote = NullQuote(
        quote_number="Q-001",
        description="Fence replacement quote",
        total_cost=Decimal("1234.56"),
        contractor=contractor,
    )

    quote.line_items = [
        NullLineItem(
            name="Timber paling fence",
            quantity=Decimal("12"),
            unit_cost=Decimal("100"),
            detail=NullLineItemDetail(note="Main fence section"),
        ),
        NullLineItem(
            name="Timber gate",
            quantity=Decimal("1"),
            unit_cost=Decimal("250"),
            detail=NullLineItemDetail(note="Side access gate"),
        ),
    ]

    return quote


def test_null_creates_plain_pydantic_model():
    result = create_null_model(NullQuote)

    assert issubclass(result, BaseModel)
    assert not issubclass(result, SQLModel)

    assert "id" in result.model_fields
    assert "quote_number" in result.model_fields
    assert "description" in result.model_fields
    assert "total_cost" in result.model_fields


def test_null_includes_scalar_relationship_field():
    result = create_null_model(NullQuote)

    assert "contractor" in result.model_fields


def test_null_includes_list_relationship_field():
    result = create_null_model(NullQuote)

    assert "line_items" in result.model_fields


def test_null_generic_api():
    result = Null[NullQuote]()

    assert issubclass(result, BaseModel)
    assert "contractor" in result.model_fields
    assert "line_items" in result.model_fields


def test_null_repeated_same_config_returns_same_type():
    result_a = Null[NullQuote]()
    result_b = Null[NullQuote]()

    assert result_a is result_b


def test_type_adapter_validate_python_preserves_scalar_relationship(
    populated_quote: NullQuote,
):
    NullQuoteDump = Null[NullQuote]()

    validated = TypeAdapter(NullQuoteDump).validate_python(
        populated_quote,
        from_attributes=True,
    )

    assert validated.quote_number == "Q-001"
    assert validated.contractor is not None
    assert validated.contractor.name == "Test Builder Pty Ltd"


def test_type_adapter_validate_python_preserves_list_relationship(
    populated_quote: NullQuote,
):
    NullQuoteDump = Null[NullQuote]()

    validated = TypeAdapter(NullQuoteDump).validate_python(
        populated_quote,
        from_attributes=True,
    )

    assert len(validated.line_items) == 2
    assert validated.line_items[0].name == "Timber paling fence"
    assert validated.line_items[1].name == "Timber gate"


def test_type_adapter_validate_python_preserves_nested_scalar_relationship(
    populated_quote: NullQuote,
):
    NullQuoteDump = Null[NullQuote]()

    validated = TypeAdapter(NullQuoteDump).validate_python(
        populated_quote,
        from_attributes=True,
    )

    assert validated.line_items[0].detail is not None
    assert validated.line_items[0].detail.note == "Main fence section"


def test_sqlmodel_model_dump_does_not_include_relationships(
    populated_quote: NullQuote,
):
    payload = populated_quote.model_dump()

    assert "quote_number" in payload
    assert "contractor" not in payload
    assert "line_items" not in payload


def test_dump_orm_model_includes_relationships(populated_quote: NullQuote):
    payload = dump_orm_model(
        populated_quote,
        exclude={
            "contractor": {
                "quotes": True,
            },
            "line_items": {
                "__all__": {
                    "quote": True,
                    "detail": {
                        "line_item": True,
                    },
                }
            },
        },
    )

    assert payload["quote_number"] == "Q-001"

    assert payload["contractor"]["name"] == "Test Builder Pty Ltd"

    assert len(payload["line_items"]) == 2
    assert payload["line_items"][0]["name"] == "Timber paling fence"
    assert payload["line_items"][0]["detail"]["note"] == "Main fence section"


def test_dump_orm_model_can_exclude_none_relationships():
    quote = NullQuote(
        quote_number="Q-NONE",
        description=None,
        total_cost=Decimal("0.00"),
        contractor=None,
        line_items=[],
    )

    payload = dump_orm_model(
        quote,
        exclude_none=True,
    )

    assert payload["quote_number"] == "Q-NONE"
    assert "description" not in payload
    assert "contractor" not in payload
    assert payload["line_items"] == []


def test_null_supports_self_referential_model():
    result = Null[NullTreeNode]()

    assert "parent" not in result.model_fields
    assert "children" in result.model_fields


def test_null_self_referencing_model_excludes_parent_relationship_but_keeps_parent_id():
    NullTreeNodeDump = Null[NullTreeNode]()

    assert "name" in NullTreeNodeDump.model_fields
    assert "parent_id" in NullTreeNodeDump.model_fields
    assert "children" in NullTreeNodeDump.model_fields
    assert "parent" not in NullTreeNodeDump.model_fields


def test_null_can_validate_cyclic_self_referencing_tree_without_recursion_error():
    root = NullTreeNode(id=1, name="Root")
    child = NullTreeNode(id=2, name="Child", parent=root, parent_id=1)
    grandchild = NullTreeNode(
        id=3,
        name="Grandchild",
        parent=child,
        parent_id=2,
    )

    root.children = [child]
    child.children = [grandchild]

    NullTreeNodeDump = Null[NullTreeNode]()

    validated = TypeAdapter(NullTreeNodeDump).validate_python(
        root,
        from_attributes=True,
    )

    payload = validated.model_dump()

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


def test_dump_orm_model_automatically_excludes_parent_backref_but_keeps_parent_id():
    root = NullTreeNode(id=1, name="Root")
    child = NullTreeNode(id=2, name="Child", parent=root, parent_id=1)
    grandchild = NullTreeNode(
        id=3,
        name="Grandchild",
        parent=child,
        parent_id=2,
    )

    root.children = [child]
    child.children = [grandchild]

    payload = dump_orm_model(root)

    assert payload["name"] == "Root"
    assert payload["parent_id"] is None
    assert "parent" not in payload

    child_payload = payload["children"][0]

    assert child_payload["name"] == "Child"
    assert child_payload["parent_id"] == 1
    assert "parent" not in child_payload

    grandchild_payload = child_payload["children"][0]

    assert grandchild_payload["name"] == "Grandchild"
    assert grandchild_payload["parent_id"] == 2
    assert "parent" not in grandchild_payload


def test_null_excludes_non_self_relationship_backrefs_from_child_models():
    NullQuoteDump = Null[NullQuote]()

    contractor_field = NullQuoteDump.model_fields["contractor"]
    contractor_model = contractor_field.annotation

    contractor_args = getattr(contractor_model, "__args__", ())
    if contractor_args:
        contractor_model = next(arg for arg in contractor_args if isinstance(arg, type) and issubclass(arg, BaseModel))

    assert "name" in contractor_model.model_fields
    assert "abn" in contractor_model.model_fields
    assert "quotes" not in contractor_model.model_fields


def test_dump_orm_model_with_bidirectional_contractor_quote_cycle():
    contractor = NullContractor(
        id=10,
        name="Cycle Builder",
        abn="12 345 678 901",
    )

    quote = NullQuote(
        id=20,
        quote_number="Q-CYCLE",
        description="Bidirectional graph",
        total_cost=Decimal("100.00"),
        contractor=contractor,
        contractor_id=10,
    )

    contractor.quotes = [quote]

    payload = dump_orm_model(quote)

    assert payload["id"] == 20
    assert payload["quote_number"] == "Q-CYCLE"
    assert payload["contractor_id"] == 10
    assert payload["contractor"]["id"] == 10
    assert payload["contractor"]["name"] == "Cycle Builder"
    assert "quotes" not in payload["contractor"]


def test_dump_orm_model_with_line_item_quote_backref_cycle():
    quote = NullQuote(
        id=1,
        quote_number="Q-LINE-CYCLE",
        total_cost=Decimal("500.00"),
    )

    line_item = NullLineItem(
        id=2,
        name="Fence section",
        quantity=Decimal("5"),
        unit_cost=Decimal("100"),
        quote=quote,
        quote_id=1,
    )

    quote.line_items = [line_item]

    payload = dump_orm_model(quote)

    assert payload["id"] == 1
    assert payload["line_items"][0]["id"] == 2
    assert payload["line_items"][0]["name"] == "Fence section"
    assert payload["line_items"][0]["quote_id"] == 1
    assert "quote" not in payload["line_items"][0]


def test_dump_self_referential_tree_excluding_parent_backref():
    root = NullTreeNode(name="Root")
    child = NullTreeNode(name="Child", parent=root)
    grandchild = NullTreeNode(name="Grandchild", parent=child)

    root.children = [child]
    child.children = [grandchild]

    payload = dump_orm_model(
        root,
        exclude={
            "parent": True,
            "children": {
                "__all__": {
                    "parent": True,
                    "children": {
                        "__all__": {
                            "parent": True,
                        }
                    },
                }
            },
        },
    )

    assert payload["name"] == "Root"
    assert payload["children"][0]["name"] == "Child"
    assert payload["children"][0]["children"][0]["name"] == "Grandchild"


def test_dump_persisted_graph_loaded_from_database(engine):
    with Session(engine) as session:
        contractor = NullContractor(name="Persisted Builder")
        quote = NullQuote(
            quote_number="Q-DB",
            total_cost=Decimal("500.00"),
            contractor=contractor,
        )
        quote.line_items = [
            NullLineItem(
                name="Database item",
                quantity=Decimal("1"),
                unit_cost=Decimal("500.00"),
            )
        ]

        session.add(quote)
        session.commit()

        quote_id = quote.id

    with Session(engine) as session:
        quote = session.get(NullQuote, quote_id)

        assert quote is not None

        # Intentionally load relationships before dumping.
        assert quote.contractor is not None
        assert len(quote.line_items) == 1

        payload = dump_orm_model(
            quote,
            exclude={
                "contractor": {
                    "quotes": True,
                },
                "line_items": {
                    "__all__": {
                        "quote": True,
                        "detail": True,
                    }
                },
            },
        )

    assert payload["quote_number"] == "Q-DB"
    assert payload["contractor"]["name"] == "Persisted Builder"
    assert payload["line_items"][0]["name"] == "Database item"


def test_dump_orm_model_respects_exclude():
    quote = NullQuote(
        quote_number="Q-EXCLUDE",
        description="Should hide this",
        total_cost=Decimal("10.00"),
    )

    payload = dump_orm_model(
        quote,
        exclude={
            "description": True,
        },
    )

    assert payload["quote_number"] == "Q-EXCLUDE"
    assert "description" not in payload


def test_null_model_dump_matches_type_adapter_dump(
    populated_quote: NullQuote,
) -> None:
    NullQuoteDump = Null[NullQuote]()

    validated = TypeAdapter(NullQuoteDump).validate_python(
        populated_quote,
        from_attributes=True,
    )

    adapter_payload = validated.model_dump(
        exclude={
            "contractor": {
                "quotes": True,
            },
            "line_items": {
                "__all__": {
                    "quote": True,
                    "detail": {
                        "line_item": True,
                    },
                }
            },
        }
    )

    utility_payload = dump_orm_model(
        populated_quote,
        exclude={
            "contractor": {
                "quotes": True,
            },
            "line_items": {
                "__all__": {
                    "quote": True,
                    "detail": {
                        "line_item": True,
                    },
                }
            },
        },
    )

    assert utility_payload == adapter_payload


def test_dump_orm_model_respects_include(populated_quote: NullQuote) -> None:
    payload = dump_orm_model(
        populated_quote,
        include={
            "quote_number": True,
            "contractor": {
                "name": True,
            },
        },
    )

    assert payload == {
        "quote_number": "Q-001",
        "contractor": {
            "name": "Test Builder Pty Ltd",
        },
    }


def test_dump_orm_model_respects_exclude_defaults() -> None:
    quote = NullQuote(
        quote_number="Q-DEFAULTS",
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


def test_dump_orm_model_supports_json_mode(populated_quote: NullQuote) -> None:
    payload = dump_orm_model(
        populated_quote,
        mode="json",
        exclude={
            "contractor": {
                "quotes": True,
            },
            "line_items": {
                "__all__": {
                    "quote": True,
                    "detail": {
                        "line_item": True,
                    },
                }
            },
        },
    )

    assert payload["total_cost"] == "1234.56"
    assert payload["line_items"][0]["quantity"] == "12"
    assert payload["line_items"][0]["unit_cost"] == "100"
