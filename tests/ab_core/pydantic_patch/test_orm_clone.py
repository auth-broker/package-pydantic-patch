from decimal import Decimal
from typing import Optional

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import registry
from sqlalchemy.pool import StaticPool
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine

from ab_core.pydantic_patch.orm_clone import recursive_clone_scalar

mapper_registry = registry()


class CloneSQLModel(SQLModel, registry=mapper_registry):
    __abstract__ = True


class CloneContractor(CloneSQLModel, table=True):
    __tablename__ = "orm_clone_contractor"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    abn: str | None = None

    quotes: list["CloneQuote"] = Relationship(back_populates="contractor")


class CloneQuote(CloneSQLModel, table=True):
    __tablename__ = "orm_clone_quote"

    id: int | None = Field(default=None, primary_key=True)
    quote_number: str
    description: str | None = None
    total_cost: Decimal = Decimal("0.00")

    contractor_id: int | None = Field(
        default=None,
        foreign_key="orm_clone_contractor.id",
    )

    contractor: CloneContractor | None = Relationship(back_populates="quotes")
    line_items: list["CloneLineItem"] = Relationship(back_populates="quote")


class CloneLineItem(CloneSQLModel, table=True):
    __tablename__ = "orm_clone_line_item"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    quantity: Decimal
    unit_cost: Decimal

    quote_id: int | None = Field(
        default=None,
        foreign_key="orm_clone_quote.id",
    )

    quote: CloneQuote | None = Relationship(back_populates="line_items")

    detail: Optional["CloneLineItemDetail"] = Relationship(
        back_populates="line_item",
    )


class CloneLineItemDetail(CloneSQLModel, table=True):
    __tablename__ = "orm_clone_line_item_detail"

    id: int | None = Field(default=None, primary_key=True)
    note: str

    line_item_id: int | None = Field(
        default=None,
        foreign_key="orm_clone_line_item.id",
    )

    line_item: CloneLineItem | None = Relationship(back_populates="detail")


class CloneTreeNode(CloneSQLModel, table=True):
    __tablename__ = "orm_clone_tree_node"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    parent_id: int | None = Field(
        default=None,
        foreign_key="orm_clone_tree_node.id",
    )

    parent: Optional["CloneTreeNode"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={
            "remote_side": "CloneTreeNode.id",
        },
    )

    children: list["CloneTreeNode"] = Relationship(
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
def populated_unflushed_quote() -> CloneQuote:
    contractor = CloneContractor(
        name="Test Builder Pty Ltd",
        abn="12 345 678 901",
    )

    quote = CloneQuote(
        quote_number="Q-001",
        description="Fence replacement quote",
        total_cost=Decimal("1234.56"),
        contractor=contractor,
    )

    quote.line_items = [
        CloneLineItem(
            name="Timber paling fence",
            quantity=Decimal("12"),
            unit_cost=Decimal("100"),
            detail=CloneLineItemDetail(note="Main fence section"),
        ),
        CloneLineItem(
            name="Timber gate",
            quantity=Decimal("1"),
            unit_cost=Decimal("250"),
            detail=CloneLineItemDetail(note="Side access gate"),
        ),
    ]

    return quote


def test_clones_normal_mapped_fields(populated_unflushed_quote: CloneQuote):
    clone = recursive_clone_scalar(populated_unflushed_quote)

    assert clone is not populated_unflushed_quote

    assert clone.quote_number == "Q-001"
    assert clone.description == "Fence replacement quote"
    assert clone.total_cost == Decimal("1234.56")


def test_clone_does_not_copy_primary_keys_by_default(
    populated_unflushed_quote: CloneQuote,
):
    populated_unflushed_quote.id = 123

    clone = recursive_clone_scalar(populated_unflushed_quote)

    assert clone.id is None


def test_clone_can_copy_primary_keys_when_explicitly_requested(
    populated_unflushed_quote: CloneQuote,
):
    populated_unflushed_quote.id = 123

    clone = recursive_clone_scalar(
        populated_unflushed_quote,
        include_primary_keys=True,
    )

    assert clone.id == 123


def test_clones_scalar_relationship(populated_unflushed_quote: CloneQuote):
    clone = recursive_clone_scalar(populated_unflushed_quote)

    assert clone.contractor is not None
    assert clone.contractor is not populated_unflushed_quote.contractor

    assert clone.contractor.name == "Test Builder Pty Ltd"
    assert clone.contractor.abn == "12 345 678 901"


def test_clones_list_relationship(populated_unflushed_quote: CloneQuote):
    clone = recursive_clone_scalar(populated_unflushed_quote)

    assert clone.line_items is not populated_unflushed_quote.line_items
    assert len(clone.line_items) == 2

    original_item = populated_unflushed_quote.line_items[0]
    cloned_item = clone.line_items[0]

    assert cloned_item is not original_item
    assert cloned_item.name == "Timber paling fence"
    assert cloned_item.quantity == Decimal("12")
    assert cloned_item.unit_cost == Decimal("100")


def test_clones_nested_scalar_relationship_inside_list_relationship(
    populated_unflushed_quote: CloneQuote,
):
    clone = recursive_clone_scalar(populated_unflushed_quote)

    original_item = populated_unflushed_quote.line_items[0]
    cloned_item = clone.line_items[0]

    assert cloned_item.detail is not None
    assert original_item.detail is not None

    assert cloned_item.detail is not original_item.detail
    assert cloned_item.detail.note == "Main fence section"


def test_back_populated_relationships_point_to_cloned_parent(
    populated_unflushed_quote: CloneQuote,
):
    clone = recursive_clone_scalar(populated_unflushed_quote)

    for cloned_item in clone.line_items:
        assert cloned_item.quote is clone

    assert clone.contractor is not None
    assert clone in clone.contractor.quotes


def test_clone_does_not_reuse_sqlalchemy_instance_state(
    populated_unflushed_quote: CloneQuote,
):
    clone = recursive_clone_scalar(populated_unflushed_quote)

    original_state = inspect(populated_unflushed_quote)
    clone_state = inspect(clone)

    assert clone_state is not original_state
    assert clone_state.session is None
    assert clone_state.transient

    assert inspect(clone.contractor).transient

    for item in clone.line_items:
        assert inspect(item).transient
        assert item.detail is not None
        assert inspect(item.detail).transient


def test_can_clone_pending_unflushed_graph_and_flush_both_original_and_clone(
    engine,
    populated_unflushed_quote: CloneQuote,
):
    with Session(engine) as session:
        session.add(populated_unflushed_quote)

        assert inspect(populated_unflushed_quote).pending
        assert populated_unflushed_quote.id is None

        clone = recursive_clone_scalar(populated_unflushed_quote)

        assert inspect(clone).transient
        assert clone.id is None

        session.add(clone)
        session.flush()

        assert populated_unflushed_quote.id is not None
        assert clone.id is not None
        assert clone.id != populated_unflushed_quote.id

        assert populated_unflushed_quote.contractor is not None
        assert clone.contractor is not None
        assert clone.contractor.id is not None
        assert clone.contractor.id != populated_unflushed_quote.contractor.id

        assert len(populated_unflushed_quote.line_items) == 2
        assert len(clone.line_items) == 2

        original_item_ids = {item.id for item in populated_unflushed_quote.line_items}
        cloned_item_ids = {item.id for item in clone.line_items}

        assert None not in original_item_ids
        assert None not in cloned_item_ids
        assert original_item_ids.isdisjoint(cloned_item_ids)


def test_include_foreign_keys_true_copies_loaded_foreign_key_columns():
    quote = CloneQuote(
        quote_number="Q-002",
        contractor_id=999,
        total_cost=Decimal("10.00"),
    )

    clone = recursive_clone_scalar(
        quote,
        include_foreign_keys=True,
    )

    assert clone.contractor_id == 999


def test_include_foreign_keys_false_excludes_foreign_key_columns():
    quote = CloneQuote(
        quote_number="Q-002",
        contractor_id=999,
        total_cost=Decimal("10.00"),
    )

    clone = recursive_clone_scalar(
        quote,
        include_foreign_keys=False,
    )

    assert clone.contractor_id is None


def test_handles_none_scalar_relationship():
    quote = CloneQuote(
        quote_number="Q-003",
        description="No contractor quote",
        total_cost=Decimal("99.00"),
        contractor=None,
    )

    clone = recursive_clone_scalar(quote)

    assert clone.contractor is None
    assert clone.quote_number == "Q-003"
    assert clone.description == "No contractor quote"


def test_handles_empty_list_relationship():
    quote = CloneQuote(
        quote_number="Q-004",
        description="No line items yet",
        total_cost=Decimal("0.00"),
        line_items=[],
    )

    clone = recursive_clone_scalar(quote)

    assert clone.line_items == []
    assert clone.quote_number == "Q-004"


def test_preserves_shared_relationship_identity_within_cloned_graph():
    contractor = CloneContractor(name="Shared Contractor")

    quote_a = CloneQuote(
        quote_number="Q-A",
        contractor=contractor,
        total_cost=Decimal("100.00"),
    )

    quote_b = CloneQuote(
        quote_number="Q-B",
        contractor=contractor,
        total_cost=Decimal("200.00"),
    )

    contractor.quotes = [quote_a, quote_b]

    cloned_contractor = recursive_clone_scalar(contractor)

    assert cloned_contractor is not contractor
    assert len(cloned_contractor.quotes) == 2

    cloned_quote_a = cloned_contractor.quotes[0]
    cloned_quote_b = cloned_contractor.quotes[1]

    assert cloned_quote_a is not quote_a
    assert cloned_quote_b is not quote_b

    assert cloned_quote_a.contractor is cloned_contractor
    assert cloned_quote_b.contractor is cloned_contractor


def test_cycle_does_not_recurse_forever(populated_unflushed_quote: CloneQuote):
    clone = recursive_clone_scalar(populated_unflushed_quote)

    assert clone.line_items[0].quote is clone
    assert clone.line_items[1].quote is clone


def test_clones_self_referential_parent_child_graph():
    root = CloneTreeNode(name="Root")
    child = CloneTreeNode(name="Child", parent=root)
    grandchild = CloneTreeNode(name="Grandchild", parent=child)

    root.children = [child]
    child.children = [grandchild]

    clone = recursive_clone_scalar(root)

    assert clone is not root
    assert clone.name == "Root"

    assert len(clone.children) == 1

    cloned_child = clone.children[0]

    assert cloned_child is not child
    assert cloned_child.name == "Child"
    assert cloned_child.parent is clone

    assert len(cloned_child.children) == 1

    cloned_grandchild = cloned_child.children[0]

    assert cloned_grandchild is not grandchild
    assert cloned_grandchild.name == "Grandchild"
    assert cloned_grandchild.parent is cloned_child


def test_can_flush_cloned_self_referential_graph(engine):
    root = CloneTreeNode(name="Root")
    child = CloneTreeNode(name="Child", parent=root)
    grandchild = CloneTreeNode(name="Grandchild", parent=child)

    root.children = [child]
    child.children = [grandchild]

    with Session(engine) as session:
        session.add(root)

        clone = recursive_clone_scalar(root)

        session.add(clone)
        session.flush()

        assert root.id is not None
        assert clone.id is not None
        assert clone.id != root.id

        original_child = root.children[0]
        cloned_child = clone.children[0]

        assert original_child.id is not None
        assert cloned_child.id is not None
        assert cloned_child.id != original_child.id

        assert cloned_child.parent_id == clone.id

        original_grandchild = original_child.children[0]
        cloned_grandchild = cloned_child.children[0]

        assert original_grandchild.id is not None
        assert cloned_grandchild.id is not None
        assert cloned_grandchild.id != original_grandchild.id

        assert cloned_grandchild.parent_id == cloned_child.id


def test_does_not_lazy_load_unloaded_relationships(engine):
    with Session(engine) as session:
        contractor = CloneContractor(name="Lazy Contractor")
        quote = CloneQuote(
            quote_number="Q-LAZY",
            contractor=contractor,
            total_cost=Decimal("10.00"),
        )
        quote.line_items = [
            CloneLineItem(
                name="Loaded later",
                quantity=Decimal("1"),
                unit_cost=Decimal("10"),
            ),
        ]

        session.add(quote)
        session.commit()

        quote_id = quote.id

    with Session(engine) as session:
        quote = session.get(CloneQuote, quote_id)

        assert quote is not None
        assert "line_items" in inspect(quote).unloaded

        clone = recursive_clone_scalar(quote)

        assert clone.quote_number == "Q-LAZY"

        # The helper should not trigger a lazy load.
        assert "line_items" in inspect(quote).unloaded

        # Since line_items was not loaded, it should not be copied into
        # the clone's __dict__ as a populated relationship.
        assert "line_items" not in clone.__dict__


def test_clones_loaded_none_column_values():
    quote = CloneQuote(
        quote_number="Q-NONE",
        description=None,
        total_cost=Decimal("0.00"),
    )

    clone = recursive_clone_scalar(quote)

    assert clone.quote_number == "Q-NONE"
    assert clone.description is None
    assert clone.total_cost == Decimal("0.00")
