"""Recursive Patch operation tests for Quote/LineItem models."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ab_core.pydantic_patch.patch import Patch, PatchConfig


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
def test_patch_supports_recursive_quote_line_item_children():
    quote_patch = Patch[Quote](
        pick={"line_items"},
        child_models={
            LineItemComparison: PatchConfig(
                pick={"id", "quote_line_item"},
            ),
            QuoteLineItem: PatchConfig(
                pick={
                    "id",
                    "parent_id",
                    "line_item_name",
                    "quoted_base_cost",
                    "children",
                },
            ),
        },
        use_cache=False,
    )

    patch = quote_patch.model_validate(
        {
            "line_items": [
                {
                    "id": str(uuid4()),
                    "quote_line_item": {
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
            ]
        }
    )

    dumped = patch.model_dump(exclude_none=False)

    assert dumped["line_items"][0]["quote_line_item"]["children"][0]["line_item_name"] == ("Colorbond panels")
    assert dumped["line_items"][0]["quote_line_item"]["children"][1]["quoted_base_cost"] == 500.0


@pytest.mark.unit
@pytest.mark.local
def test_patch_supports_recursive_quote_line_item_children_with_combined_operations():
    quote_patch = Patch[Quote](
        pick={"id", "line_items"},
        partial={"line_items"},
        required={"id"},
        child_models={
            LineItemComparison: PatchConfig(
                pick={"id", "quote_line_item"},
                partial={"quote_line_item"},
                required={"id"},
            ),
            QuoteLineItem: PatchConfig(
                pick={
                    "id",
                    "parent_id",
                    "line_item_name",
                    "quoted_base_cost",
                    "children",
                },
                partial={
                    "id",
                    "parent_id",
                    "line_item_name",
                    "quoted_base_cost",
                    "children",
                },
            ),
        },
        use_cache=False,
    )

    quote_id = uuid4()
    comparison_id = uuid4()

    patch = quote_patch.model_validate(
        {
            "id": str(quote_id),
            "line_items": [
                {
                    "id": str(comparison_id),
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
            ],
        }
    )

    dumped = patch.model_dump(exclude_none=False)

    assert dumped["id"] == quote_id
    assert dumped["line_items"][0]["id"] == comparison_id
    assert dumped["line_items"][0]["quote_line_item"]["children"][0]["line_item_name"] == ("Colorbond panels")
    assert dumped["line_items"][0]["quote_line_item"]["children"][0]["quoted_base_cost"] is None
    assert dumped["line_items"][0]["quote_line_item"]["children"][1]["line_item_name"] is None
    assert dumped["line_items"][0]["quote_line_item"]["children"][1]["quoted_base_cost"] == 500.0

    with pytest.raises(ValidationError):
        quote_patch.model_validate(
            {
                # id is required at the root.
                "line_items": [],
            }
        )


@pytest.mark.unit
@pytest.mark.local
def test_patch_supports_recursive_quote_line_item_grandchildren():
    quote_patch = Patch[Quote](
        pick={"line_items"},
        child_models={
            LineItemComparison: PatchConfig(
                pick={"quote_line_item"},
            ),
            QuoteLineItem: PatchConfig(
                pick={
                    "line_item_name",
                    "quoted_base_cost",
                    "children",
                },
            ),
        },
        use_cache=False,
    )

    patch = quote_patch.model_validate(
        {
            "line_items": [
                {
                    "quote_line_item": {
                        "line_item_name": "Fence",
                        "quoted_base_cost": 1200.0,
                        "children": [
                            {
                                "line_item_name": "Panels",
                                "quoted_base_cost": 700.0,
                                "children": [
                                    {
                                        "line_item_name": "Panel fixings",
                                        "quoted_base_cost": 100.0,
                                    }
                                ],
                            }
                        ],
                    },
                }
            ]
        }
    )

    dumped = patch.model_dump(exclude_none=False)
    grandchild = dumped["line_items"][0]["quote_line_item"]["children"][0]["children"][0]

    assert grandchild["line_item_name"] == "Panel fixings"
    assert grandchild["quoted_base_cost"] == 100.0


@pytest.mark.unit
@pytest.mark.local
def test_patch_supports_direct_recursive_root_model_with_custom_name_and_cache():
    class QuoteLineItem(BaseModel):
        model_config = ConfigDict(extra="forbid")

        id: UUID | None = None
        line_item_name: str = ""
        quoted_base_cost: float = 0.0
        children: list[QuoteLineItem] = Field(default_factory=list)

    QuoteLineItem.model_rebuild(force=True)

    quote_line_item_patch = Patch[QuoteLineItem](
        name="QuoteLineItemUpdate",
        pick={"id", "line_item_name", "quoted_base_cost", "children"},
        partial={"id", "line_item_name", "quoted_base_cost", "children"},
        child_models={
            QuoteLineItem: PatchConfig(
                pick={"id", "line_item_name", "quoted_base_cost", "children"},
                partial={"id", "line_item_name", "quoted_base_cost", "children"},
            )
        },
    )

    patch = quote_line_item_patch.model_validate(
        {
            "line_item_name": "Parent fence",
            "children": [
                {"line_item_name": "Panels"},
                {"quoted_base_cost": 500.0},
            ],
        }
    )

    dumped = patch.model_dump(exclude_none=False)

    assert dumped["line_item_name"] == "Parent fence"
    assert dumped["children"][0]["line_item_name"] == "Panels"
    assert dumped["children"][0]["quoted_base_cost"] is None
    assert dumped["children"][1]["line_item_name"] is None
    assert dumped["children"][1]["quoted_base_cost"] == 500.0
