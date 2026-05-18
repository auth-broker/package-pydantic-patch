"""Recursive Pick operation tests for Quote/LineItem models."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ConfigDict, Field

from ab_core.pydantic_patch.pick import Pick, PickConfig


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


@pytest.mark.unit
@pytest.mark.local
def test_pick_supports_recursive_quote_line_item_children():
    quote_pick = Pick[Quote](
        fields={"line_items"},
        child_models={
            LineItemComparison: PickConfig(
                fields={"id", "quote_line_item"},
            ),
            QuoteLineItem: PickConfig(
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

    picked = quote_pick.model_validate(
        {
            "line_items": [
                {
                    "id": str(uuid4()),
                    "comparison_notes": "should be rejected by pick",
                    "quote_line_item": {
                        "line_item_name": "New Colorbond fence",
                        "quoted_base_cost": 1200.0,
                        "internal_notes": "should be rejected by recursive pick",
                        "children": [
                            {
                                "line_item_name": "Colorbond panels",
                                "quoted_base_cost": 700.0,
                            },
                            {
                                "line_item_name": "Posts and rails",
                                "quoted_base_cost": 500.0,
                            },
                        ],
                    },
                }
            ]
        }
    )

    dumped = picked.model_dump(exclude_none=False)

    assert set(dumped) == {"line_items"}
    assert set(dumped["line_items"][0]) == {"id", "quote_line_item"}
    assert "comparison_notes" not in dumped["line_items"][0]
    assert "internal_notes" not in dumped["line_items"][0]["quote_line_item"]
    assert dumped["line_items"][0]["quote_line_item"]["children"][0]["line_item_name"] == ("Colorbond panels")
    assert dumped["line_items"][0]["quote_line_item"]["children"][1]["quoted_base_cost"] == 500.0


@pytest.mark.unit
@pytest.mark.local
def test_pick_supports_recursive_quote_line_item_grandchildren():
    quote_pick = Pick[Quote](
        fields={"line_items"},
        child_models={
            LineItemComparison: PickConfig(
                fields={"quote_line_item"},
            ),
            QuoteLineItem: PickConfig(
                fields={
                    "line_item_name",
                    "quoted_base_cost",
                    "children",
                },
            ),
        },
    )

    picked = quote_pick.model_validate(
        {
            "line_items": [
                {
                    "quote_line_item": {
                        "line_item_name": "Fence",
                        "quoted_base_cost": 1200.0,
                        "internal_notes": "should be rejected at root child",
                        "children": [
                            {
                                "line_item_name": "Panels",
                                "quoted_base_cost": 700.0,
                                "internal_notes": "should be rejected at child",
                                "children": [
                                    {
                                        "line_item_name": "Panel fixings",
                                        "quoted_base_cost": 100.0,
                                        "internal_notes": "should be rejected at grandchild",
                                    }
                                ],
                            }
                        ],
                    },
                }
            ]
        }
    )

    dumped = picked.model_dump(exclude_none=False)
    grandchild = dumped["line_items"][0]["quote_line_item"]["children"][0]["children"][0]

    assert grandchild["line_item_name"] == "Panel fixings"
    assert grandchild["quoted_base_cost"] == 100.0
    assert "internal_notes" not in grandchild
