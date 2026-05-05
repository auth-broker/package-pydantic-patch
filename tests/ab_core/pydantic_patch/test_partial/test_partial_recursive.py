

from ab_core.pydantic_patch.partial import PartialConfig, create_partial_model
from tests.helpers.assert_model import assert_optional, get_dict_value_type, get_list_item_type


def test_partial_quote_all_fields_recursively(models):
    Quote = models["Quote"]
    QuoteLineItem = models["QuoteLineItem"]
    BenchmarkMatch = models["BenchmarkMatch"]

    result = create_partial_model(
        Quote,
        fields=None,
        child_models={
            QuoteLineItem: PartialConfig(fields=None),
            BenchmarkMatch: PartialConfig(fields=None),
        },
    )

    assert_optional(result, "line_items")

    line_item_type = get_list_item_type(result.model_fields["line_items"].annotation)
    match_type = get_list_item_type(line_item_type.model_fields["benchmark_matches"].annotation)

    for field_name in line_item_type.model_fields:
        assert_optional(line_item_type, field_name)

    for field_name in match_type.model_fields:
        assert_optional(match_type, field_name)


def test_partial_organisation_reuses_same_address_partial(models):
    Organisation = models["Organisation"]
    Address = models["Address"]

    result = create_partial_model(
        Organisation,
        fields=None,
        child_models={
            Address: PartialConfig(fields=None),
        },
    )

    primary_address_type = result.model_fields["primary_address"].annotation
    postal_address_type = result.model_fields["postal_address"].annotation
    branch_address_type = get_list_item_type(result.model_fields["branch_addresses"].annotation)
    address_lookup_value_type = get_dict_value_type(result.model_fields["address_lookup"].annotation)

    assert primary_address_type is postal_address_type
    assert primary_address_type is branch_address_type
    assert primary_address_type is address_lookup_value_type


def test_partial_parent_only_does_not_partial_child_without_child_config(models):
    Organisation = models["Organisation"]
    Address = models["Address"]

    result = create_partial_model(
        Organisation,
        fields={"primary_address"},
        child_models={},
    )

    assert_optional(result, "primary_address")
    assert result.model_fields["primary_address"].annotation is Address
