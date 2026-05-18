"""Recursive Required operation tests for Quote/LineItem models."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ab_core.pydantic_patch.required import Required, RequiredConfig


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
def test_required_supports_recursive_quote_line_item_children():
    quote_required = Required[Quote](
        fields={"line_items"},
        child_models={
            LineItemComparison: RequiredConfig(
                fields={"id", "quote_line_item"},
            ),
            QuoteLineItem: RequiredConfig(
                fields={"line_item_name", "quoted_base_cost"},
            ),
        },
    )

    required = quote_required.model_validate(
        {
            "id": str(uuid4()),
            "title": "Fence quote",
            "line_items": [
                {
                    "id": str(uuid4()),
                    "quote_line_item": {
                        "id": str(uuid4()),
                        "line_item_name": "New Colorbond fence",
                        "quoted_base_cost": 1200.0,
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
            ],
        }
    )

    dumped = required.model_dump(exclude_none=False)

    assert dumped["line_items"][0]["quote_line_item"]["children"][0]["line_item_name"] == ("Colorbond panels")
    assert dumped["line_items"][0]["quote_line_item"]["children"][1]["quoted_base_cost"] == 500.0

    with pytest.raises(ValidationError):
        quote_required.model_validate(
            {
                "id": str(uuid4()),
                "title": "Fence quote",
                "line_items": [
                    {
                        "id": str(uuid4()),
                        "quote_line_item": {
                            "line_item_name": "New Colorbond fence",
                            "quoted_base_cost": 1200.0,
                            "children": [
                                {
                                    "line_item_name": "Colorbond panels",
                                    # quoted_base_cost is required recursively.
                                }
                            ],
                        },
                    }
                ],
            }
        )
