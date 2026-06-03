from pydantic import BaseModel

from ab_core.pydantic_patch.null import Null, create_null_model
from tests.helpers.assert_model import (
    assert_field_names,
    get_dict_value_type,
    get_list_item_type,
)


class NullAddress(BaseModel):
    id: int
    street: str
    suburb: str


class NullOrganisation(BaseModel):
    id: int
    name: str
    primary_address: NullAddress
    branch_addresses: list[NullAddress]
    address_lookup: dict[str, NullAddress]


class NullBenchmarkMatch(BaseModel):
    id: int
    benchmark_name: str
    match_score: float


class NullQuoteLineItem(BaseModel):
    id: int
    line_item_name: str
    benchmark_matches: list[NullBenchmarkMatch]


class NullQuote(BaseModel):
    id: int
    quote_number: str
    line_items: list[NullQuoteLineItem]


def test_null_recursively_converts_child_models() -> None:
    result = create_null_model(NullQuote)

    line_item_type = get_list_item_type(result.model_fields["line_items"].annotation)
    match_type = get_list_item_type(line_item_type.model_fields["benchmark_matches"].annotation)

    assert line_item_type is not NullQuoteLineItem
    assert match_type is not NullBenchmarkMatch

    assert_field_names(result, {"id", "quote_number", "line_items"})
    assert_field_names(line_item_type, {"id", "line_item_name", "benchmark_matches"})
    assert_field_names(match_type, {"id", "benchmark_name", "match_score"})


def test_null_reuses_same_child_model_for_repeated_child_annotations() -> None:
    result = Null[NullOrganisation]()

    primary_address_type = result.model_fields["primary_address"].annotation
    branch_address_type = get_list_item_type(result.model_fields["branch_addresses"].annotation)
    address_lookup_value_type = get_dict_value_type(result.model_fields["address_lookup"].annotation)

    assert primary_address_type is branch_address_type
    assert primary_address_type is address_lookup_value_type


def test_null_validates_recursive_payload() -> None:
    result = Null[NullQuote]()

    validated = result.model_validate(
        {
            "id": 1,
            "quote_number": "Q-001",
            "line_items": [
                {
                    "id": 10,
                    "line_item_name": "Fence",
                    "benchmark_matches": [
                        {
                            "id": 100,
                            "benchmark_name": "Timber fence",
                            "match_score": 0.92,
                        }
                    ],
                }
            ],
        }
    )

    dumped = validated.model_dump()

    assert dumped["quote_number"] == "Q-001"
    assert dumped["line_items"][0]["line_item_name"] == "Fence"
    assert dumped["line_items"][0]["benchmark_matches"][0]["match_score"] == 0.92
