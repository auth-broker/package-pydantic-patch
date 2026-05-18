"""Self-referencing quote line item SQLModel."""

from sqlmodel import Field, Relationship, SQLModel


class QuoteLineItem(SQLModel, table=True):
    """A quote line item that can contain child line items."""

    __tablename__ = "self_referencing_quote_line_item"

    id: int | None = Field(default=None, primary_key=True)
    parent_id: int | None = Field(default=None, foreign_key="self_referencing_quote_line_item.id")

    line_item_name: str = ""
    quoted_base_cost: float = 0.0

    parent: "QuoteLineItem" = Relationship(
        back_populates="children",
        sa_relationship_kwargs={
            "remote_side": "QuoteLineItem.id",
        },
    )
    children: list["QuoteLineItem"] = Relationship(back_populates="parent")
