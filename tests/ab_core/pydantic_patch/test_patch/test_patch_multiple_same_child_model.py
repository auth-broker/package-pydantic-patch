from __future__ import annotations

from ab_core.pydantic_patch.patch import PatchConfig, create_patch_model
from tests.helpers.assert_model import get_dict_value_type, get_list_item_type


def test_patch_multiple_same_child_model_reuses_same_type(models):
    Organisation = models["Organisation"]
    Address = models["Address"]

    result = create_patch_model(
        Organisation,
        config=PatchConfig(
            include={"primary_address", "postal_address", "branch_addresses", "address_lookup"},
            partial=None,
            child_models={
                Address: PatchConfig(
                    include={"id", "suburb", "postcode"},
                    partial={"suburb", "postcode"},
                    required={"id"},
                ),
            },
        ),
    )

    primary_address_type = result.model_fields["primary_address"].annotation
    postal_address_type = result.model_fields["postal_address"].annotation
    branch_address_type = get_list_item_type(result.model_fields["branch_addresses"].annotation)
    address_lookup_value_type = get_dict_value_type(result.model_fields["address_lookup"].annotation)

    assert primary_address_type is postal_address_type
    assert primary_address_type is branch_address_type
    assert primary_address_type is address_lookup_value_type
    assert set(primary_address_type.model_fields) == {"id", "suburb", "postcode"}
