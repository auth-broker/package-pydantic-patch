from __future__ import annotations

from ab_core.pydantic_patch.omit import OmitConfig, create_omit_model
from tests.helpers.assert_model import get_dict_value_type, get_list_item_type


def test_omit_address_audit_fields_everywhere(models):
    Organisation = models["Organisation"]
    Address = models["Address"]

    result = create_omit_model(
        Organisation,
        fields={"created_at", "updated_at"},
        child_models={
            Address: OmitConfig(fields={"created_at", "updated_at"}),
        },
    )

    primary_address_type = result.model_fields["primary_address"].annotation
    postal_address_type = result.model_fields["postal_address"].annotation
    branch_address_type = get_list_item_type(result.model_fields["branch_addresses"].annotation)
    address_lookup_value_type = get_dict_value_type(result.model_fields["address_lookup"].annotation)

    assert primary_address_type is postal_address_type
    assert primary_address_type is branch_address_type
    assert primary_address_type is address_lookup_value_type
    assert "created_at" not in primary_address_type.model_fields
    assert "updated_at" not in primary_address_type.model_fields


def test_omit_deep_quote_match_score(models):
    Quote = models["Quote"]
    QuoteLineItem = models["QuoteLineItem"]
    BenchmarkMatch = models["BenchmarkMatch"]

    result = create_omit_model(
        Quote,
        fields={"created_at", "updated_at"},
        child_models={
            QuoteLineItem: OmitConfig(fields={"created_at", "updated_at"}),
            BenchmarkMatch: OmitConfig(fields={"match_score", "created_at", "updated_at"}),
        },
    )

    line_item_type = get_list_item_type(result.model_fields["line_items"].annotation)
    match_type = get_list_item_type(line_item_type.model_fields["benchmark_matches"].annotation)

    assert "match_score" not in match_type.model_fields
    assert "created_at" not in match_type.model_fields
    assert "updated_at" not in match_type.model_fields
