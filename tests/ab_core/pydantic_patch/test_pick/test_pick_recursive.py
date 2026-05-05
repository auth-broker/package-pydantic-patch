from tests.helpers.assert_model import get_dict_value_type, get_list_item_type

from ab_core.pydantic_patch.pick import PickConfig, create_pick_model


def test_pick_organisation_recursively_reuses_same_address_pick(models):
    Address = models["Address"]
    Organisation = models["Organisation"]

    result = create_pick_model(
        Organisation,
        fields={"primary_address", "postal_address", "branch_addresses", "address_lookup"},
        child_models={
            Address: PickConfig(fields={"suburb", "postcode"}),
        },
    )

    primary_address_type = result.model_fields["primary_address"].annotation
    postal_address_type = result.model_fields["postal_address"].annotation
    branch_address_type = get_list_item_type(result.model_fields["branch_addresses"].annotation)
    address_lookup_value_type = get_dict_value_type(result.model_fields["address_lookup"].annotation)

    assert primary_address_type is postal_address_type
    assert primary_address_type is branch_address_type
    assert primary_address_type is address_lookup_value_type
    assert set(primary_address_type.model_fields) == {"suburb", "postcode"}


def test_pick_deep_quote_line_item_benchmark_match(models):
    Quote = models["Quote"]
    QuoteLineItem = models["QuoteLineItem"]
    BenchmarkMatch = models["BenchmarkMatch"]

    result = create_pick_model(
        Quote,
        fields={"id", "line_items"},
        child_models={
            QuoteLineItem: PickConfig(fields={"id", "benchmark_matches"}),
            BenchmarkMatch: PickConfig(fields={"id", "selected"}),
        },
    )

    line_item_type = get_list_item_type(result.model_fields["line_items"].annotation)
    match_type = get_list_item_type(line_item_type.model_fields["benchmark_matches"].annotation)

    assert set(result.model_fields) == {"id", "line_items"}
    assert set(line_item_type.model_fields) == {"id", "benchmark_matches"}
    assert set(match_type.model_fields) == {"id", "selected"}


def test_pick_unconfigured_child_model_remains_unchanged(models):
    Organisation = models["Organisation"]
    Address = models["Address"]

    result = create_pick_model(
        Organisation,
        fields={"primary_address"},
        child_models={},
    )

    assert result.model_fields["primary_address"].annotation is Address
