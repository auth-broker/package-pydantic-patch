from tests.helpers.assert_model import get_dict_value_type, get_list_item_type

from ab_core.pydantic_patch.omit import create_omit_model
from ab_core.pydantic_patch.partial import PartialConfig, create_partial_model
from ab_core.pydantic_patch.patch import PatchConfig, create_patch_model
from ab_core.pydantic_patch.pick import PickConfig, create_pick_model
from ab_core.pydantic_patch.required import create_required_model


def test_same_operation_same_model_same_config_returns_same_type(models):
    User = models["User"]

    assert create_pick_model(User, fields={"name"}) is create_pick_model(User, fields={"name"})
    assert create_omit_model(User, fields={"created_at"}) is create_omit_model(User, fields={"created_at"})
    assert create_partial_model(User, fields={"name"}) is create_partial_model(User, fields={"name"})
    assert create_required_model(User, fields={"id"}) is create_required_model(User, fields={"id"})


def test_different_operation_configs_return_different_type_objects(models):
    User = models["User"]

    assert create_pick_model(User, fields={"name"}) is not create_pick_model(User, fields={"email"})


def test_different_custom_names_return_different_type_objects(models):
    User = models["User"]

    result_a = create_pick_model(User, fields={"name"}, name="UserNameA")
    result_b = create_pick_model(User, fields={"name"}, name="UserNameB")

    assert result_a is not result_b


def test_same_custom_name_same_config_returns_same_type_object(models):
    User = models["User"]

    result_a = create_pick_model(User, fields={"name"}, name="UserName")
    result_b = create_pick_model(User, fields={"name"}, name="UserName")

    assert result_a is result_b


def test_child_model_cache_hit_inside_recursive_parent_generation(models):
    Organisation = models["Organisation"]
    Address = models["Address"]

    address_config = PatchConfig(include={"id", "suburb"}, required={"id"}, partial={"suburb"})

    parent_a = create_patch_model(
        Organisation,
        config=PatchConfig(
            include={"primary_address"},
            child_models={Address: address_config},
        ),
    )
    parent_b = create_patch_model(
        Organisation,
        config=PatchConfig(
            include={"postal_address"},
            child_models={Address: address_config},
        ),
    )

    assert parent_a.model_fields["primary_address"].annotation is parent_b.model_fields["postal_address"].annotation


def test_same_operation_same_config_in_different_field_locations_reuses_child(models):
    Organisation = models["Organisation"]
    Address = models["Address"]

    result = create_pick_model(
        Organisation,
        fields={"primary_address", "postal_address", "branch_addresses", "address_lookup"},
        child_models={Address: PickConfig(fields={"suburb"})},
    )

    primary_address_type = result.model_fields["primary_address"].annotation
    postal_address_type = result.model_fields["postal_address"].annotation
    branch_address_type = get_list_item_type(result.model_fields["branch_addresses"].annotation)
    address_lookup_value_type = get_dict_value_type(result.model_fields["address_lookup"].annotation)

    assert primary_address_type is postal_address_type
    assert primary_address_type is branch_address_type
    assert primary_address_type is address_lookup_value_type


def test_discriminated_union_variants_reuse_cached_generated_classes(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]
    Dog = models["Dog"]
    Bird = models["Bird"]

    cat_config = PartialConfig(fields=None)
    dog_config = PartialConfig(fields=None)
    bird_config = PartialConfig(fields=None)

    result_a = create_partial_model(
        PetOwner,
        child_models={Cat: cat_config, Dog: dog_config, Bird: bird_config},
    )
    result_b = create_partial_model(
        PetOwner,
        child_models={Cat: cat_config, Dog: dog_config, Bird: bird_config},
    )

    assert result_a is result_b
