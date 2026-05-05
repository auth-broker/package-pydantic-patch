# Pydantic Patch Test Suite

This test suite is intentionally written contract-first. It assumes the package will expose these public APIs:

```python
from ab_core.pydantic_patch.pick import Pick, PickConfig, create_pick_model
from ab_core.pydantic_patch.omit import Omit, OmitConfig, create_omit_model
from ab_core.pydantic_patch.partial import Partial, PartialConfig, create_partial_model
from ab_core.pydantic_patch.required import Required, RequiredConfig, create_required_model
from ab_core.pydantic_patch.patch import Patch, PatchConfig, create_patch_model
from ab_core.pydantic_patch.core.errors import (
    InvalidPatchFieldError,
    InvalidDiscriminatorError,
    ConflictingPatchConfigError,
)
```

The tests also assume:

* repeated identical operations return the same generated class object;
* recursive child model generation reuses the same generated child class object;
* discriminated unions are rebuilt as `Annotated[PatchedVariantA | PatchedVariantB, Discriminator("kind")]`;
* discriminator fields are always required and cannot be omitted or partialed.

---

## `tests/conftest.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, get_args, get_origin

import pytest
from pydantic import BaseModel, Discriminator


class User(BaseModel):
    id: int | None = None
    name: str
    email: str
    created_at: datetime
    updated_at: datetime


class Address(BaseModel):
    id: int | None = None
    line_1: str
    line_2: str | None = None
    suburb: str
    postcode: str
    created_at: datetime
    updated_at: datetime


class Customer(BaseModel):
    id: int | None = None
    name: str
    address: Address
    billing_address: Address


class Organisation(BaseModel):
    id: int | None = None
    name: str
    primary_address: Address
    postal_address: Address
    branch_addresses: list[Address]
    address_lookup: dict[str, Address]
    created_at: datetime
    updated_at: datetime


class BenchmarkMatch(BaseModel):
    id: int | None = None
    category: str
    line_item_name: str
    selected: bool
    match_score: float
    created_at: datetime
    updated_at: datetime


class QuoteLineItem(BaseModel):
    id: int | None = None
    description: str
    quantity: float
    unit: str
    benchmark_matches: list[BenchmarkMatch]
    created_at: datetime
    updated_at: datetime


class Quote(BaseModel):
    id: int | None = None
    quote_number: str
    line_items: list[QuoteLineItem]
    created_at: datetime
    updated_at: datetime


class Cat(BaseModel):
    kind: Literal["cat"] = "cat"
    id: int | None = None
    lives: int
    name: str
    secret_tracking_code: str


class Dog(BaseModel):
    kind: Literal["dog"] = "dog"
    id: int | None = None
    bark_volume: int
    name: str
    secret_tracking_code: str


class Bird(BaseModel):
    kind: Literal["bird"] = "bird"
    id: int | None = None
    wing_span: float
    name: str
    secret_tracking_code: str


Pet = Annotated[Cat | Dog | Bird, Discriminator("kind")]


class PetOwner(BaseModel):
    id: int | None = None
    name: str
    pet: Pet
    previous_pets: list[Pet]
    created_at: datetime
    updated_at: datetime


class BadDiscriminatorVariant(BaseModel):
    id: int | None = None
    name: str


BadPet = Annotated[Cat | BadDiscriminatorVariant, Discriminator("kind")]


class BadPetOwner(BaseModel):
    pet: BadPet


class ArbitraryPayload(BaseModel):
    id: int
    metadata: dict[str, object]
    raw_value: object


class MixedUnionPayload(BaseModel):
    id: int
    value: Address | str


@pytest.fixture

def models():
    return {
        "User": User,
        "Address": Address,
        "Customer": Customer,
        "Organisation": Organisation,
        "BenchmarkMatch": BenchmarkMatch,
        "QuoteLineItem": QuoteLineItem,
        "Quote": Quote,
        "Cat": Cat,
        "Dog": Dog,
        "Bird": Bird,
        "PetOwner": PetOwner,
        "BadPetOwner": BadPetOwner,
        "ArbitraryPayload": ArbitraryPayload,
        "MixedUnionPayload": MixedUnionPayload,
    }


# -----------------------------------------------------------------------------
# Expected model fixtures
# -----------------------------------------------------------------------------


class UserNameEmailPickExpected(BaseModel):
    name: str
    email: str


class UserEmptyPickExpected(BaseModel):
    pass


class UserOmitAuditExpected(BaseModel):
    id: int | None = None
    name: str
    email: str


class UserPartialAllExpected(BaseModel):
    id: int | None = None
    name: str | None = None
    email: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserPartialNameExpected(BaseModel):
    id: int | None = None
    name: str | None = None
    email: str
    created_at: datetime
    updated_at: datetime


class UserRequiredIdExpected(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime
    updated_at: datetime


class UserPatchIdNameEmailExpected(BaseModel):
    id: int
    name: str | None = None
    email: str | None = None


class AddressPickSuburbPostcodeExpected(BaseModel):
    suburb: str
    postcode: str


class AddressOmitAuditExpected(BaseModel):
    id: int | None = None
    line_1: str
    line_2: str | None = None
    suburb: str
    postcode: str


class AddressPartialAllExpected(BaseModel):
    id: int | None = None
    line_1: str | None = None
    line_2: str | None = None
    suburb: str | None = None
    postcode: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AddressRequiredIdExpected(BaseModel):
    id: int
    line_1: str
    line_2: str | None = None
    suburb: str
    postcode: str
    created_at: datetime
    updated_at: datetime


@pytest.fixture

def expected_models():
    return {
        "UserNameEmailPickExpected": UserNameEmailPickExpected,
        "UserEmptyPickExpected": UserEmptyPickExpected,
        "UserOmitAuditExpected": UserOmitAuditExpected,
        "UserPartialAllExpected": UserPartialAllExpected,
        "UserPartialNameExpected": UserPartialNameExpected,
        "UserRequiredIdExpected": UserRequiredIdExpected,
        "UserPatchIdNameEmailExpected": UserPatchIdNameEmailExpected,
        "AddressPickSuburbPostcodeExpected": AddressPickSuburbPostcodeExpected,
        "AddressOmitAuditExpected": AddressOmitAuditExpected,
        "AddressPartialAllExpected": AddressPartialAllExpected,
        "AddressRequiredIdExpected": AddressRequiredIdExpected,
    }
```

---

## `tests/helpers/assert_model.py`

```python
from __future__ import annotations

from typing import Any, get_args, get_origin

from deepdiff import DeepDiff
from pydantic import BaseModel


def assert_model_equivalent(
    actual: type[BaseModel],
    expected: type[BaseModel],
    *,
    ignore_title: bool = True,
) -> None:
    assert actual.model_fields.keys() == expected.model_fields.keys()

    for field_name, expected_field in expected.model_fields.items():
        actual_field = actual.model_fields[field_name]
        assert actual_field.annotation == expected_field.annotation, field_name
        assert actual_field.is_required() == expected_field.is_required(), field_name
        assert actual_field.default == expected_field.default, field_name

    actual_schema = actual.model_json_schema()
    expected_schema = expected.model_json_schema()

    exclude_regex_paths = []
    if ignore_title:
        exclude_regex_paths.extend([
            r"root\['title'\]",
            r"root\['\$defs'\]\['.*'\]\['title'\]",
        ])

    diff = DeepDiff(
        expected_schema,
        actual_schema,
        ignore_order=True,
        exclude_regex_paths=exclude_regex_paths,
    )

    assert diff == {}


def assert_field_names(model: type[BaseModel], expected: set[str]) -> None:
    assert set(model.model_fields) == expected


def assert_required(model: type[BaseModel], field_name: str) -> None:
    assert model.model_fields[field_name].is_required(), field_name


def assert_optional(model: type[BaseModel], field_name: str) -> None:
    assert not model.model_fields[field_name].is_required(), field_name


def get_list_item_type(annotation: Any) -> Any:
    assert get_origin(annotation) is list
    return get_args(annotation)[0]


def get_dict_value_type(annotation: Any) -> Any:
    assert get_origin(annotation) is dict
    return get_args(annotation)[1]


def assert_same_annotation_object(actual: Any, expected: Any) -> None:
    assert actual is expected
```

---

## `tests/pick/test_pick_simple.py`

```python
from __future__ import annotations

import pytest

from ab_core.pydantic_patch.core.errors import InvalidPatchFieldError
from ab_core.pydantic_patch.pick import Pick, create_pick_model
from tests.helpers.assert_model import assert_field_names, assert_model_equivalent


@pytest.mark.parametrize(
    ("fields", "expected_key"),
    [
        ({"name", "email"}, "UserNameEmailPickExpected"),
        (set(), "UserEmptyPickExpected"),
    ],
)
def test_pick_user_fields(models, expected_models, fields, expected_key):
    result = create_pick_model(models["User"], fields=fields)
    assert_model_equivalent(result, expected_models[expected_key])


def test_pick_fields_none_keeps_all_fields(models):
    result = create_pick_model(models["User"], fields=None)
    assert_field_names(result, {"id", "name", "email", "created_at", "updated_at"})


def test_pick_unknown_field_raises(models):
    with pytest.raises(InvalidPatchFieldError):
        create_pick_model(models["User"], fields={"does_not_exist"})


def test_pick_custom_name(models):
    result = create_pick_model(models["User"], fields={"name"}, name="UserNameOnlyInput")
    assert result.__name__ == "UserNameOnlyInput"


def test_pick_repeated_same_config_returns_same_type(models):
    result_a = create_pick_model(models["User"], fields={"name", "email"})
    result_b = create_pick_model(models["User"], fields={"email", "name"})
    assert result_a is result_b


def test_pick_generic_api(models):
    result = Pick[models["User"]](fields={"name", "email"})
    assert_field_names(result, {"name", "email"})
```

---

## `tests/pick/test_pick_recursive.py`

```python
from __future__ import annotations

from ab_core.pydantic_patch.pick import PickConfig, create_pick_model
from tests.helpers.assert_model import get_dict_value_type, get_list_item_type


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
```

---

## `tests/pick/test_pick_discriminated_union.py`

```python
from __future__ import annotations

import pytest

from ab_core.pydantic_patch.core.errors import InvalidDiscriminatorError
from ab_core.pydantic_patch.pick import PickConfig, create_pick_model
from tests.helpers.assert_model import get_list_item_type


def test_pick_discriminated_union_preserves_union_and_variants(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]
    Dog = models["Dog"]
    Bird = models["Bird"]

    result = create_pick_model(
        PetOwner,
        fields={"pet", "previous_pets"},
        child_models={
            Cat: PickConfig(fields={"kind", "name", "lives"}),
            Dog: PickConfig(fields={"kind", "name", "bark_volume"}),
            Bird: PickConfig(fields={"kind", "name", "wing_span"}),
        },
    )

    pet_annotation = result.model_fields["pet"].annotation
    previous_pet_annotation = get_list_item_type(result.model_fields["previous_pets"].annotation)

    assert pet_annotation == previous_pet_annotation

    payload = {
        "pet": {"kind": "cat", "name": "Mimi", "lives": 9},
        "previous_pets": [
            {"kind": "dog", "name": "Kiki", "bark_volume": 5},
            {"kind": "bird", "name": "Pip", "wing_span": 12.5},
        ],
    }
    validated = result.model_validate(payload)
    assert validated.pet.kind == "cat"
    assert validated.previous_pets[0].kind == "dog"
    assert validated.previous_pets[1].kind == "bird"


def test_pick_discriminator_field_cannot_be_omitted_from_variant(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]
    Dog = models["Dog"]
    Bird = models["Bird"]

    with pytest.raises(InvalidDiscriminatorError):
        create_pick_model(
            PetOwner,
            fields={"pet"},
            child_models={
                Cat: PickConfig(fields={"name", "lives"}),
                Dog: PickConfig(fields={"kind", "name", "bark_volume"}),
                Bird: PickConfig(fields={"kind", "name", "wing_span"}),
            },
        )
```

---

## `tests/omit/test_omit_simple.py`

```python
from __future__ import annotations

import pytest

from ab_core.pydantic_patch.core.errors import InvalidPatchFieldError
from ab_core.pydantic_patch.omit import Omit, create_omit_model
from tests.helpers.assert_model import assert_field_names, assert_model_equivalent


def test_omit_user_audit_fields(models, expected_models):
    result = create_omit_model(models["User"], fields={"created_at", "updated_at"})
    assert_model_equivalent(result, expected_models["UserOmitAuditExpected"])


def test_omit_fields_none_changes_nothing(models):
    result = create_omit_model(models["User"], fields=None)
    assert_field_names(result, {"id", "name", "email", "created_at", "updated_at"})


def test_omit_empty_set_changes_nothing(models):
    result = create_omit_model(models["User"], fields=set())
    assert_field_names(result, {"id", "name", "email", "created_at", "updated_at"})


def test_omit_unknown_field_raises(models):
    with pytest.raises(InvalidPatchFieldError):
        create_omit_model(models["User"], fields={"does_not_exist"})


def test_omit_custom_name(models):
    result = create_omit_model(models["User"], fields={"created_at"}, name="UserWithoutCreatedAt")
    assert result.__name__ == "UserWithoutCreatedAt"


def test_omit_repeated_same_config_returns_same_type(models):
    result_a = create_omit_model(models["User"], fields={"created_at", "updated_at"})
    result_b = create_omit_model(models["User"], fields={"updated_at", "created_at"})
    assert result_a is result_b


def test_omit_generic_api(models):
    result = Omit[models["User"]](fields={"created_at", "updated_at"})
    assert_field_names(result, {"id", "name", "email"})
```

---

## `tests/omit/test_omit_recursive.py`

```python
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
```

---

## `tests/omit/test_omit_discriminated_union.py`

```python
from __future__ import annotations

import pytest

from ab_core.pydantic_patch.core.errors import InvalidDiscriminatorError
from ab_core.pydantic_patch.omit import OmitConfig, create_omit_model


def test_omit_discriminated_union_variant_fields(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]
    Dog = models["Dog"]
    Bird = models["Bird"]

    result = create_omit_model(
        PetOwner,
        fields={"created_at", "updated_at"},
        child_models={
            Cat: OmitConfig(fields={"secret_tracking_code"}),
            Dog: OmitConfig(fields={"secret_tracking_code"}),
            Bird: OmitConfig(fields={"secret_tracking_code"}),
        },
    )

    validated = result.model_validate(
        {
            "id": 1,
            "name": "Owner",
            "pet": {"kind": "cat", "id": 1, "name": "Mimi", "lives": 9},
            "previous_pets": [{"kind": "dog", "id": 2, "name": "Kiki", "bark_volume": 4}],
        }
    )
    assert validated.pet.kind == "cat"


def test_omit_discriminator_field_raises(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]

    with pytest.raises(InvalidDiscriminatorError):
        create_omit_model(
            PetOwner,
            child_models={
                Cat: OmitConfig(fields={"kind"}),
            },
        )
```

---

## `tests/partial/test_partial_simple.py`

```python
from __future__ import annotations

import pytest

from ab_core.pydantic_patch.core.errors import InvalidPatchFieldError
from ab_core.pydantic_patch.partial import Partial, create_partial_model
from tests.helpers.assert_model import assert_model_equivalent, assert_optional, assert_required


def test_partial_user_no_fields_makes_all_fields_optional(models, expected_models):
    result = create_partial_model(models["User"], fields=None)
    assert_model_equivalent(result, expected_models["UserPartialAllExpected"])


def test_partial_user_specific_field(models, expected_models):
    result = create_partial_model(models["User"], fields={"name"})
    assert_model_equivalent(result, expected_models["UserPartialNameExpected"])


def test_partial_empty_set_makes_no_fields_optional(models):
    result = create_partial_model(models["User"], fields=set())
    assert_required(result, "name")
    assert_required(result, "email")
    assert_optional(result, "id")


def test_partial_unknown_field_raises(models):
    with pytest.raises(InvalidPatchFieldError):
        create_partial_model(models["User"], fields={"does_not_exist"})


def test_partial_optional_id_remains_optional(models):
    result = create_partial_model(models["User"], fields={"name"})
    assert_optional(result, "id")


def test_partial_required_original_field_becomes_optional_when_selected(models):
    result = create_partial_model(models["User"], fields={"email"})
    assert_optional(result, "email")


def test_partial_custom_name(models):
    result = create_partial_model(models["User"], fields={"name"}, name="UserNamePartial")
    assert result.__name__ == "UserNamePartial"


def test_partial_repeated_same_config_returns_same_type(models):
    result_a = create_partial_model(models["User"], fields={"name", "email"})
    result_b = create_partial_model(models["User"], fields={"email", "name"})
    assert result_a is result_b


def test_partial_generic_api(models):
    result = Partial[models["User"]](fields={"name"})
    assert_optional(result, "name")
```

---

## `tests/partial/test_partial_recursive.py`

```python
from __future__ import annotations

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
```

---

## `tests/partial/test_partial_discriminated_union.py`

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from ab_core.pydantic_patch.core.errors import InvalidDiscriminatorError
from ab_core.pydantic_patch.partial import PartialConfig, create_partial_model


def test_partial_discriminated_union_variants_keep_kind_required(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]
    Dog = models["Dog"]
    Bird = models["Bird"]

    result = create_partial_model(
        PetOwner,
        fields=None,
        child_models={
            Cat: PartialConfig(fields=None),
            Dog: PartialConfig(fields=None),
            Bird: PartialConfig(fields=None),
        },
    )

    validated = result.model_validate(
        {
            "pet": {"kind": "cat"},
            "previous_pets": [{"kind": "dog"}, {"kind": "bird"}],
        }
    )
    assert validated.pet.kind == "cat"

    with pytest.raises(ValidationError):
        result.model_validate({"pet": {"name": "Missing kind"}, "previous_pets": []})


def test_partial_discriminator_field_cannot_be_partialed(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]

    with pytest.raises(InvalidDiscriminatorError):
        create_partial_model(
            PetOwner,
            child_models={
                Cat: PartialConfig(fields={"kind"}),
            },
        )
```

---

## `tests/required/test_required_simple.py`

```python
from __future__ import annotations

import pytest

from ab_core.pydantic_patch.core.errors import InvalidPatchFieldError
from ab_core.pydantic_patch.required import Required, create_required_model
from tests.helpers.assert_model import assert_model_equivalent, assert_optional, assert_required


def test_required_user_id(models, expected_models):
    result = create_required_model(models["User"], fields={"id"})
    assert_model_equivalent(result, expected_models["UserRequiredIdExpected"])


def test_required_fields_none_changes_nothing(models):
    result = create_required_model(models["User"], fields=None)
    assert_optional(result, "id")
    assert_required(result, "name")


def test_required_empty_set_changes_nothing(models):
    result = create_required_model(models["User"], fields=set())
    assert_optional(result, "id")
    assert_required(result, "name")


def test_required_unknown_field_raises(models):
    with pytest.raises(InvalidPatchFieldError):
        create_required_model(models["User"], fields={"does_not_exist"})


def test_required_already_required_field_stays_required(models):
    result = create_required_model(models["User"], fields={"name"})
    assert_required(result, "name")


def test_required_custom_name(models):
    result = create_required_model(models["User"], fields={"id"}, name="UserIdRequired")
    assert result.__name__ == "UserIdRequired"


def test_required_repeated_same_config_returns_same_type(models):
    result_a = create_required_model(models["User"], fields={"id"})
    result_b = create_required_model(models["User"], fields={"id"})
    assert result_a is result_b


def test_required_generic_api(models):
    result = Required[models["User"]](fields={"id"})
    assert_required(result, "id")
```

---

## `tests/required/test_required_recursive.py`

```python
from __future__ import annotations

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
```

---

## `tests/required/test_required_discriminated_union.py`

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from ab_core.pydantic_patch.required import RequiredConfig, create_required_model


def test_required_discriminated_union_variant_ids(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]
    Dog = models["Dog"]
    Bird = models["Bird"]

    result = create_required_model(
        PetOwner,
        child_models={
            Cat: RequiredConfig(fields={"id"}),
            Dog: RequiredConfig(fields={"id"}),
            Bird: RequiredConfig(fields={"id"}),
        },
    )

    result.model_validate(
        {
            "id": 1,
            "name": "Owner",
            "pet": {"kind": "cat", "id": 1, "name": "Mimi", "lives": 9, "secret_tracking_code": "x"},
            "previous_pets": [],
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
    )

    with pytest.raises(ValidationError):
        result.model_validate(
            {
                "id": 1,
                "name": "Owner",
                "pet": {"kind": "cat", "name": "Mimi", "lives": 9, "secret_tracking_code": "x"},
                "previous_pets": [],
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
            }
        )
```

---

## `tests/patch/test_patch_simple.py`

```python
from __future__ import annotations

from ab_core.pydantic_patch.patch import Patch, PatchConfig, create_patch_model
from tests.helpers.assert_model import assert_field_names, assert_model_equivalent, assert_optional, assert_required


def test_patch_user_include_name_email(models):
    result = create_patch_model(models["User"], config=PatchConfig(include={"name", "email"}, partial=set()))
    assert_field_names(result, {"name", "email"})


def test_patch_user_exclude_audit_fields(models):
    result = create_patch_model(
        models["User"],
        config=PatchConfig(exclude={"created_at", "updated_at"}, partial=set()),
    )
    assert_field_names(result, {"id", "name", "email"})


def test_patch_user_partial_name_email(models):
    result = create_patch_model(
        models["User"],
        config=PatchConfig(partial={"name", "email"}),
    )
    assert_optional(result, "name")
    assert_optional(result, "email")
    assert_required(result, "created_at")


def test_patch_user_required_id(models):
    result = create_patch_model(
        models["User"],
        config=PatchConfig(partial=set(), required={"id"}),
    )
    assert_required(result, "id")


def test_patch_user_include_partial_required_expected_model(models, expected_models):
    result = create_patch_model(
        models["User"],
        config=PatchConfig(
            include={"id", "name", "email"},
            partial={"name", "email"},
            required={"id"},
        ),
    )
    assert_model_equivalent(result, expected_models["UserPatchIdNameEmailExpected"])


def test_patch_generic_api(models):
    result = Patch[models["User"]](
        include={"id", "name"},
        partial={"name"},
        required={"id"},
    )
    assert_field_names(result, {"id", "name"})
    assert_required(result, "id")
    assert_optional(result, "name")
```

---

## `tests/patch/test_patch_operation_order.py`

```python
from __future__ import annotations

import pytest

from ab_core.pydantic_patch.core.errors import ConflictingPatchConfigError
from ab_core.pydantic_patch.patch import PatchConfig, create_patch_model
from tests.helpers.assert_model import assert_field_names, assert_optional, assert_required


def test_patch_include_then_exclude(models):
    result = create_patch_model(
        models["User"],
        config=PatchConfig(
            include={"id", "name", "created_at"},
            exclude={"created_at"},
            partial=set(),
        ),
    )
    assert_field_names(result, {"id", "name"})


def test_patch_partial_then_required_required_wins(models):
    result = create_patch_model(
        models["User"],
        config=PatchConfig(partial=None, required={"id"}),
    )
    assert_required(result, "id")
    assert_optional(result, "name")
    assert_optional(result, "email")
    assert_optional(result, "created_at")
    assert_optional(result, "updated_at")


def test_patch_required_field_not_present_after_include_raises(models):
    with pytest.raises(ConflictingPatchConfigError):
        create_patch_model(
            models["User"],
            config=PatchConfig(
                include={"name"},
                required={"id"},
            ),
        )


def test_patch_partial_field_not_present_after_exclude_raises(models):
    with pytest.raises(ConflictingPatchConfigError):
        create_patch_model(
            models["User"],
            config=PatchConfig(
                exclude={"email"},
                partial={"email"},
            ),
        )
```

---

## `tests/patch/test_patch_recursive.py`

```python
from __future__ import annotations

from ab_core.pydantic_patch.patch import PatchConfig, create_patch_model
from tests.helpers.assert_model import assert_optional, assert_required, get_list_item_type


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
```

---

## `tests/patch/test_patch_multiple_same_child_model.py`

```python
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
```

---

## `tests/patch/test_patch_discriminated_union.py`

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from ab_core.pydantic_patch.core.errors import InvalidDiscriminatorError
from ab_core.pydantic_patch.patch import PatchConfig, create_patch_model


def test_patch_discriminated_union_flat_child_configs(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]
    Dog = models["Dog"]
    Bird = models["Bird"]

    result = create_patch_model(
        PetOwner,
        config=PatchConfig(
            include={"pet", "previous_pets"},
            partial=None,
            child_models={
                Cat: PatchConfig(
                    include={"kind", "id", "name", "lives"},
                    partial={"name", "lives"},
                    required={"id"},
                ),
                Dog: PatchConfig(
                    include={"kind", "id", "name", "bark_volume"},
                    partial={"name", "bark_volume"},
                    required={"id"},
                ),
                Bird: PatchConfig(
                    include={"kind", "id", "name", "wing_span"},
                    partial={"name", "wing_span"},
                    required={"id"},
                ),
            },
        ),
    )

    result.model_validate(
        {
            "pet": {"kind": "cat", "id": 1},
            "previous_pets": [
                {"kind": "dog", "id": 2},
                {"kind": "bird", "id": 3},
            ],
        }
    )

    with pytest.raises(ValidationError):
        result.model_validate({"pet": {"id": 1}, "previous_pets": []})


def test_patch_discriminator_field_cannot_be_partial(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]

    with pytest.raises(InvalidDiscriminatorError):
        create_patch_model(
            PetOwner,
            config=PatchConfig(
                include={"pet"},
                child_models={
                    Cat: PatchConfig(partial={"kind"}),
                },
            ),
        )


def test_patch_discriminator_field_cannot_be_omitted(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]

    with pytest.raises(InvalidDiscriminatorError):
        create_patch_model(
            PetOwner,
            config=PatchConfig(
                include={"pet"},
                child_models={
                    Cat: PatchConfig(exclude={"kind"}),
                },
            ),
        )


def test_patch_discriminator_field_missing_from_variant_raises(models):
    BadPetOwner = models["BadPetOwner"]

    with pytest.raises(InvalidDiscriminatorError):
        create_patch_model(BadPetOwner, config=PatchConfig(partial=None))
```

---

## `tests/patch/test_patch_cache.py`

```python
from __future__ import annotations

from ab_core.pydantic_patch.omit import create_omit_model
from ab_core.pydantic_patch.patch import PatchConfig, create_patch_model
from ab_core.pydantic_patch.partial import PartialConfig, create_partial_model
from ab_core.pydantic_patch.pick import PickConfig, create_pick_model
from ab_core.pydantic_patch.required import create_required_model
from tests.helpers.assert_model import get_dict_value_type, get_list_item_type


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
```

---

## `tests/patch/test_patch_validation.py`

```python
from __future__ import annotations

import pytest

from ab_core.pydantic_patch.core.errors import (
    ConflictingPatchConfigError,
    InvalidDiscriminatorError,
    InvalidPatchFieldError,
)
from ab_core.pydantic_patch.patch import PatchConfig, create_patch_model
from ab_core.pydantic_patch.pick import create_pick_model
from tests.helpers.assert_model import assert_field_names


@pytest.mark.parametrize(
    "config",
    [
        PatchConfig(include={"does_not_exist"}),
        PatchConfig(exclude={"does_not_exist"}),
        PatchConfig(partial={"does_not_exist"}),
        PatchConfig(required={"does_not_exist"}),
    ],
)
def test_unknown_fields_raise(models, config):
    with pytest.raises(InvalidPatchFieldError):
        create_patch_model(models["User"], config=config)


def test_required_field_not_in_payload_raises(models):
    with pytest.raises(ConflictingPatchConfigError):
        create_patch_model(
            models["User"],
            config=PatchConfig(include={"name"}, required={"id"}),
        )


def test_partial_field_not_in_payload_raises(models):
    with pytest.raises(ConflictingPatchConfigError):
        create_patch_model(
            models["User"],
            config=PatchConfig(exclude={"email"}, partial={"email"}),
        )


def test_discriminator_field_omitted_raises(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]

    with pytest.raises(InvalidDiscriminatorError):
        create_patch_model(
            PetOwner,
            config=PatchConfig(
                child_models={Cat: PatchConfig(exclude={"kind"})},
            ),
        )


def test_discriminator_field_partial_raises(models):
    PetOwner = models["PetOwner"]
    Cat = models["Cat"]

    with pytest.raises(InvalidDiscriminatorError):
        create_patch_model(
            PetOwner,
            config=PatchConfig(
                child_models={Cat: PatchConfig(partial={"kind"})},
            ),
        )


def test_discriminator_field_missing_from_variant_raises(models):
    with pytest.raises(InvalidDiscriminatorError):
        create_patch_model(models["BadPetOwner"], config=PatchConfig())


def test_unsupported_arbitrary_non_pydantic_type_is_preserved(models):
    result = create_patch_model(
        models["ArbitraryPayload"],
        config=PatchConfig(partial=set()),
    )

    assert result.model_fields["metadata"].annotation == dict[str, object]
    assert result.model_fields["raw_value"].annotation is object


def test_mixed_union_with_non_basemodel_variant_is_preserved_for_non_model_member(models):
    Address = models["Address"]
    MixedUnionPayload = models["MixedUnionPayload"]

    result = create_pick_model(
        MixedUnionPayload,
        fields={"value"},
    )

    assert_field_names(result, {"value"})
    # The exact transformed annotation will be implementation-sensitive, but the
    # contract is that str is not discarded or treated as a BaseModel.
```
