

from ab_core.pydantic_patch.required import RequiredConfig, create_required_model
from tests.helpers.assert_model import assert_required, get_dict_value_type, get_list_item_type


def test_required_quote_ids_recursively(models):
    Quote = models["Quote"]
    QuoteLineItem = models["QuoteLineItem"]
    BenchmarkMatch = models["BenchmarkMatch"]

    result = create_required_model(
        Quote,
        fields={"id"},
        child_models={
            QuoteLineItem: RequiredConfig(fields={"id"}),
            BenchmarkMatch: RequiredConfig(fields={"id"}),
        },
    )

    line_item_type = get_list_item_type(result.model_fields["line_items"].annotation)
    match_type = get_list_item_type(line_item_type.model_fields["benchmark_matches"].annotation)

    assert_required(result, "id")
    assert_required(line_item_type, "id")
    assert_required(match_type, "id")


def test_required_address_id_everywhere(models):
    Organisation = models["Organisation"]
    Address = models["Address"]

    result = create_required_model(
        Organisation,
        fields={"id"},
        child_models={
            Address: RequiredConfig(fields={"id"}),
        },
    )

    primary_address_type = result.model_fields["primary_address"].annotation
    postal_address_type = result.model_fields["postal_address"].annotation
    branch_address_type = get_list_item_type(result.model_fields["branch_addresses"].annotation)
    address_lookup_value_type = get_dict_value_type(result.model_fields["address_lookup"].annotation)

    assert primary_address_type is postal_address_type
    assert primary_address_type is branch_address_type
    assert primary_address_type is address_lookup_value_type
    assert_required(primary_address_type, "id")
