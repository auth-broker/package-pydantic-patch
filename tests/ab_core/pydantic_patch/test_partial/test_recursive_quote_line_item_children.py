"""Recursive Partial operation tests for Quote/LineItem models."""

from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import BaseModel, ConfigDict, Field

from ab_core.pydantic_patch.partial import Partial, PartialConfig


class QuoteLineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    parent_id: UUID | None = None
    line_item_name: str = ""
    quoted_base_cost: float = 0.0
    internal_notes: str = ""
    children: list[QuoteLineItem] = Field(default_factory=list)


class LineItemComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    quote_line_item: QuoteLineItem
    comparison_notes: str = ""


class Quote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    title: str = ""
    line_items: list[LineItemComparison] = Field(default_factory=list)


for model in (QuoteLineItem, LineItemComparison, Quote):
    model.model_rebuild(force=True)


@pytest.mark.unit
@pytest.mark.local
def test_partial_supports_recursive_quote_line_item_children():
    quote_partial = Partial[Quote](
        fields={"line_items"},
        child_models={
            LineItemComparison: PartialConfig(
                fields={"quote_line_item"},
            ),
            QuoteLineItem: PartialConfig(
                fields={
                    "id",
                    "parent_id",
                    "line_item_name",
                    "quoted_base_cost",
                    "children",
                },
            ),
        },
    )

    partial = quote_partial.model_validate(
        {
            "line_items": [
                {
                    "quote_line_item": {
                        "children": [
                            {
                                "line_item_name": "Colorbond panels",
                            },
                            {
                                "quoted_base_cost": 500.0,
                            },
                        ],
                    },
                }
            ]
        }
    )

    dumped = partial.model_dump(exclude_none=False)

    assert dumped["line_items"][0]["quote_line_item"]["children"][0]["line_item_name"] == ("Colorbond panels")
    assert dumped["line_items"][0]["quote_line_item"]["children"][0]["quoted_base_cost"] is None
    assert dumped["line_items"][0]["quote_line_item"]["children"][1]["line_item_name"] is None
    assert dumped["line_items"][0]["quote_line_item"]["children"][1]["quoted_base_cost"] == 500.0
