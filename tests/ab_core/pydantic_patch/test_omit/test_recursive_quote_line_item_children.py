"""Recursive Omit operation tests for Quote/LineItem models."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from ab_core.pydantic_patch.omit import Omit, OmitConfig
from pydantic import BaseModel, ConfigDict, Field


class QuoteLineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    parent_id: UUID | None = None
    line_item_name: str = ""
    quoted_base_cost: float = 0.0
    internal_notes: str = ""
    children: list["QuoteLineItem"] = Field(default_factory=list)


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
def test_omit_supports_recursive_quote_line_item_children():
    quote_omit = Omit[Quote](
        fields={"title"},
        child_models={
            LineItemComparison: OmitConfig(
                fields={"comparison_notes"},
            ),
            QuoteLineItem: OmitConfig(
                fields={"internal_notes"},
            ),
        },
    )

    omitted = quote_omit.model_validate(
        {
            "id": str(uuid4()),
            "line_items": [
                {
                    "id": str(uuid4()),
                    "comparison_notes": "should be rejected by omit",
                    "quote_line_item": {
                        "id": str(uuid4()),
                        "line_item_name": "New Colorbond fence",
                        "quoted_base_cost": 1200.0,
                        "internal_notes": "should be rejected by recursive omit",
                        "children": [
                            {
                                "line_item_name": "Colorbond panels",
                                "quoted_base_cost": 700.0,
                                "internal_notes": "should also be rejected recursively",
                            },
                            {
                                "line_item_name": "Posts and rails",
                                "quoted_base_cost": 500.0,
                                "internal_notes": "should also be rejected recursively",
                            },
                        ],
                    },
                }
            ],
        }
    )

    dumped = omitted.model_dump(exclude_none=False)

    assert "title" not in dumped
    assert "comparison_notes" not in dumped["line_items"][0]
    assert "internal_notes" not in dumped["line_items"][0]["quote_line_item"]
    assert "internal_notes" not in dumped["line_items"][0]["quote_line_item"]["children"][0]
    assert dumped["line_items"][0]["quote_line_item"]["children"][0]["line_item_name"] == (
        "Colorbond panels"
    )
    assert dumped["line_items"][0]["quote_line_item"]["children"][1]["quoted_base_cost"] == 500.0
