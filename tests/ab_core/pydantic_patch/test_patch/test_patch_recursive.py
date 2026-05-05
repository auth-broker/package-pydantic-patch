from tests.helpers.assert_model import assert_optional, assert_required, get_list_item_type

from ab_core.pydantic_patch.patch import PatchConfig, create_patch_model


def test_patch_quote_line_items_and_benchmark_matches(models):
    Quote = models["Quote"]
    QuoteLineItem = models["QuoteLineItem"]
    BenchmarkMatch = models["BenchmarkMatch"]

    result = create_patch_model(
        Quote,
        config=PatchConfig(
            include={"id", "line_items"},
            partial={"line_items"},
            required={"id"},
            child_models={
                QuoteLineItem: PatchConfig(
                    include={"id", "quantity", "benchmark_matches"},
                    partial={"quantity", "benchmark_matches"},
                    required={"id"},
                    child_models={
                        BenchmarkMatch: PatchConfig(
                            include={"id", "selected"},
                            partial={"selected"},
                            required={"id"},
                        ),
                    },
                ),
            },
        ),
    )

    assert set(result.model_fields) == {"id", "line_items"}
    assert_required(result, "id")
    assert_optional(result, "line_items")

    line_item_type = get_list_item_type(result.model_fields["line_items"].annotation)
    assert set(line_item_type.model_fields) == {"id", "quantity", "benchmark_matches"}
    assert_required(line_item_type, "id")
    assert_optional(line_item_type, "quantity")
    assert_optional(line_item_type, "benchmark_matches")

    match_type = get_list_item_type(line_item_type.model_fields["benchmark_matches"].annotation)
    assert set(match_type.model_fields) == {"id", "selected"}
    assert_required(match_type, "id")
    assert_optional(match_type, "selected")
