Absolutely. The clean architecture is:

```text
pick / omit / partial / required
    ↓
operate on a shared create_model payload
    ↓
patch aggregates those operations
    ↓
recursive type traversal handles BaseModel, lists, dicts, unions, discriminated unions
    ↓
cached model creation avoids duplicate generated classes
```

Below is the implementation plan I’d follow.

---

# 1. Package structure

```text
src/ab_core/pydantic_patch/
    __init__.py

    core/
        __init__.py
        cache.py
        config.py
        errors.py
        fields.py
        payload.py
        transform.py
        types.py

    pick/
        __init__.py
        api.py
        config.py
        operation.py

    omit/
        __init__.py
        api.py
        config.py
        operation.py

    partial/
        __init__.py
        api.py
        config.py
        operation.py

    required/
        __init__.py
        api.py
        config.py
        operation.py

    patch/
        __init__.py
        api.py
        config.py
        operation.py
```

The important bit is that the operation modules are thin wrappers over shared internals.

---

# 2. Public API shape

## Independent operations

```python
UserPick = Pick[User](fields={"name", "email"})
UserOmit = Omit[User](fields={"created_at", "updated_at"})
UserPartial = Partial[User](fields={"name", "email"})
UserRequired = Required[User](fields={"id"})
```

With optional class name:

```python
UserPatchInput = Partial[User](
    fields={"name", "email"},
    name="UserPatchInput",
)
```

Recursive support:

```python
QuotePatch = Partial[Quote](
    fields={"line_items"},
    child_models={
        QuoteLineItem: PartialConfig(fields={"quantity", "description"}),
        BenchmarkMatch: PartialConfig(fields={"selected"}),
    },
)
```

## Aggregated patch operation

```python
QuotePatch = Patch[Quote](
    include={"id", "line_items"},
    exclude={"created_at", "updated_at"},
    partial={"line_items"},
    required={"id"},
    child_models={
        QuoteLineItem: PatchConfig(
            include={"id", "quantity", "benchmark_matches"},
            partial={"quantity", "benchmark_matches"},
            required={"id"},
        ),
        BenchmarkMatch: PatchConfig(
            include={"id", "selected"},
            partial={"selected"},
            required={"id"},
        ),
    },
)
```

---

# 3. Config models

Each independent operation should have its own config because recursive child handling needs to exist at every level.

```python
class PickConfig(BaseModel):
    fields: frozenset[str] | None = None
    child_models: dict[type[BaseModel], "PickConfig"] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)
```

Same idea for:

```python
class OmitConfig(BaseModel):
    fields: frozenset[str] | None = None
    child_models: dict[type[BaseModel], "OmitConfig"] = Field(default_factory=dict)
```

```python
class PartialConfig(BaseModel):
    fields: frozenset[str] | None = None
    child_models: dict[type[BaseModel], "PartialConfig"] = Field(default_factory=dict)
```

```python
class RequiredConfig(BaseModel):
    fields: frozenset[str] | None = None
    child_models: dict[type[BaseModel], "RequiredConfig"] = Field(default_factory=dict)
```

Then the aggregated config:

```python
class PatchConfig(BaseModel):
    include: frozenset[str] | None = None
    exclude: frozenset[str] | None = None
    partial: frozenset[str] | None = None
    required: frozenset[str] | None = None

    child_models: dict[type[BaseModel], "PatchConfig"] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)
```

Then:

```python
PickConfig.model_rebuild()
OmitConfig.model_rebuild()
PartialConfig.model_rebuild()
RequiredConfig.model_rebuild()
PatchConfig.model_rebuild()
```

One naming thing: internally, I would call the aggregated config fields `include`, `exclude`, `partial`, `required`, but the independent APIs can expose `fields`.

---

# 4. Core payload model

Every operation should manipulate this shape:

```python
CreateModelPayload = dict[str, tuple[Any, Any]]
```

Example:

```python
{
    "id": (int, ...),
    "name": (str, ...),
    "description": (str | None, None),
}
```

There should be helpers:

```python
def build_payload_from_model(model: type[BaseModel]) -> CreateModelPayload:
    ...
```

```python
def create_model_from_payload(
    *,
    source_model: type[BaseModel],
    payload: CreateModelPayload,
    name: str,
) -> type[BaseModel]:
    return pydantic.create_model(
        name,
        __base__=BaseModel,
        __module__=source_model.__module__,
        **payload,
    )
```

Do **not** create the final Pydantic model until every operation has modified the payload.

---

# 5. Operation semantics

## Pick

```python
Pick[SomeModel](fields={"a", "b"})
```

Means:

```text
only keep a and b
```

Rules:

```text
fields=None  -> keep everything
fields=set() -> keep nothing
unknown field -> raise
```

Implementation:

```python
def apply_pick_payload(
    payload: CreateModelPayload,
    *,
    model: type[BaseModel],
    fields: frozenset[str] | None,
) -> CreateModelPayload:
    validate_fields_exist(model, fields)

    if fields is None:
        return payload

    return {
        field_name: field_payload
        for field_name, field_payload in payload.items()
        if field_name in fields
    }
```

## Omit

```python
Omit[SomeModel](fields={"created_at"})
```

Means:

```text
remove these fields
```

Rules:

```text
fields=None  -> omit nothing
fields=set() -> omit nothing
unknown field -> raise
```

Implementation:

```python
def apply_omit_payload(
    payload: CreateModelPayload,
    *,
    model: type[BaseModel],
    fields: frozenset[str] | None,
) -> CreateModelPayload:
    validate_fields_exist(model, fields)

    if not fields:
        return payload

    return {
        field_name: field_payload
        for field_name, field_payload in payload.items()
        if field_name not in fields
    }
```

## Partial

```python
Partial[SomeModel](fields={"name"})
```

Means:

```text
make only these fields optional
```

Important: I now agree with your later correction — **partial should not automatically mean everything is partial unless explicitly configured that way.**

So we need a configurable default.

For independent `Partial`, I would make this ergonomic:

```python
Partial[SomeModel]()
```

means:

```text
make all fields optional
```

But:

```python
Partial[SomeModel](fields={"name"})
```

means:

```text
make only name optional
```

For `PatchConfig`, I would use the same behaviour:

```python
partial=None -> make all fields partial
partial=set() -> make no fields partial
partial={"a"} -> make only a partial
```

This gives you nice patch defaults while preserving escape hatches.

Implementation helper:

```python
def apply_partial_payload(
    payload: CreateModelPayload,
    *,
    model: type[BaseModel],
    fields: frozenset[str] | None,
) -> CreateModelPayload:
    validate_fields_exist(model, fields)

    fields_to_partial = set(payload) if fields is None else set(fields)

    return {
        field_name: make_field_optional(field_type, default)
        if field_name in fields_to_partial
        else (field_type, default)
        for field_name, (field_type, default) in payload.items()
    }
```

`make_field_optional` should preserve existing metadata where possible.

Simple version:

```python
def make_field_optional(annotation: Any, default: Any) -> tuple[Any, Any]:
    return annotation | None, None
```

Better version:

```python
def make_field_optional(annotation: Any, default: Any) -> tuple[Any, Any]:
    if allows_none(annotation):
        return annotation, None

    return annotation | None, None
```

## Required

```python
Required[SomeModel](fields={"id"})
```

Means:

```text
force these fields to be required even if original default is None
```

Rules:

```text
fields=None  -> change nothing
fields=set() -> change nothing
unknown field -> raise
```

Implementation:

```python
def apply_required_payload(
    payload: CreateModelPayload,
    *,
    model: type[BaseModel],
    fields: frozenset[str] | None,
) -> CreateModelPayload:
    validate_fields_exist(model, fields)

    if not fields:
        return payload

    return {
        field_name: (field_type, ...)
        if field_name in fields
        else (field_type, default)
        for field_name, (field_type, default) in payload.items()
    }
```

---

# 6. Patch operation ordering

For `Patch`, I would apply operations in this order:

```text
1. include / pick
2. exclude / omit
3. recursive child model transformation
4. partial
5. required
6. final create_model
```

Why?

## 1. Pick first

This defines the possible field universe.

```python
include={"id", "name", "line_items"}
```

## 2. Omit second

This allows `exclude` to override include.

```python
include={"id", "name", "created_at"}
exclude={"created_at"}
```

Final fields:

```python
{"id", "name"}
```

## 3. Recursive child transformation before partial/required

Because the parent field annotation needs to contain the transformed child type before parent optionality is applied.

Example:

```python
line_items: list[QuoteLineItemPatch] | None = None
```

not:

```python
line_items: list[QuoteLineItem] | None = None
```

## 4. Partial fourth

This relaxes field presence.

## 5. Required last

Required should win.

Example:

```python
PatchConfig(
    include={"id", "quantity"},
    partial=None,
    required={"id"},
)
```

Should produce:

```python
id: int
quantity: float | None = None
```

So `required` must happen after `partial`.

---

# 7. Recursive type transformation

This should live in:

```text
core/types.py
core/transform.py
```

The core recursive function:

```python
def transform_annotation(
    annotation: Any,
    *,
    operation: OperationKind,
    child_config: ChildConfigMap,
    cache_context: CacheContext,
) -> Any:
    ...
```

It should support:

```text
BaseModel
list[BaseModel]
dict[str, BaseModel]
tuple[BaseModel, ...]
BaseModel | None
Union[BaseModelA, BaseModelB]
Annotated[Union[...], Discriminator(...)]
```

At minimum for v1:

```text
BaseModel
list
dict
Union / |
Annotated
Discriminated Union
```

## BaseModel

```python
if is_basemodel_type(annotation):
    config = child_models.get(annotation)
    return transform_model(annotation, config=config)
```

Important default:

```text
if no child config exists:
    for independent Pick/Omit/Required -> leave child unchanged
    for Partial -> probably recursively partial everything only if recursive=True
    for Patch -> recursively patch child with default PatchConfig()
```

I would make this explicit with an option:

```python
recursive: bool = True
```

For patch endpoints, recursive default should be true.

## List

```python
list[Child]
```

becomes:

```python
list[ChildPatch]
```

## Dict

```python
dict[str, Child]
```

becomes:

```python
dict[str, ChildPatch]
```

## Optional

```python
Child | None
```

becomes:

```python
ChildPatch | None
```

## Plain union

```python
Cat | Dog
```

becomes:

```python
CatPatch | DogPatch
```

## Discriminated union

Input:

```python
Annotated[
    Cat | Dog | Bird,
    Discriminator("kind"),
]
```

Output:

```python
Annotated[
    CatPatch | DogPatch | BirdPatch,
    Discriminator("kind"),
]
```

Strict discriminator rules:

```text
The discriminator field must exist on every variant.
The discriminator field must not be omitted.
The discriminator field must not be partial.
The discriminator field must be required.
```

So when transforming a discriminated union, inject required behaviour into each variant config.

Pseudo:

```python
def transform_discriminated_union(annotation: Any, config_map: dict[type[BaseModel], PatchConfig]) -> Any:
    union_type, discriminator = extract_annotated_union_and_discriminator(annotation)
    variants = extract_union_args(union_type)

    patched_variants = []

    for variant in variants:
        variant_config = config_map.get(variant, PatchConfig())

        variant_config = force_discriminator_required(
            variant_config,
            discriminator_key=discriminator.discriminator,
        )

        patched_variants.append(
            transform_model(
                variant,
                config=variant_config,
            )
        )

    return Annotated[
        reduce(operator.or_, patched_variants),
        discriminator,
    ]
```

---

# 8. Field validation

All operations should validate fields against the **source model**, not the currently narrowed payload.

Example:

```python
PatchConfig(
    include={"id", "name"},
    exclude={"created_at"},
)
```

Should still accept `created_at` in exclude if it exists on the source model, even though include removed it.

But this scenario should raise:

```python
PatchConfig(
    include={"id"},
    required={"created_at"},
)
```

because `required` is trying to require a field that is no longer present after pick/omit.

So I’d distinguish:

```python
validate_fields_exist_on_model(...)
validate_fields_exist_in_payload(...)
```

Rules:

```text
include -> validate against model
exclude -> validate against model
partial -> validate against final included/omitted payload
required -> validate against final included/omitted payload
```

That prevents nonsense like requiring an excluded field.

---

# 9. Caching strategy

You want the same generated class object when the input model and config are identical.

Use an internal cached wrapper:

```python
@lru_cache(maxsize=None)
def _cached_transform_model(
    source_model: type[BaseModel],
    operation_key: str,
    config_key: HashableConfig,
    name: str | None,
) -> type[BaseModel]:
    return _transform_model_uncached(...)
```

Important: Pydantic models and config dicts are not naturally hash-safe, so create frozen cache keys.

Example:

```python
@dataclass(frozen=True)
class OperationCacheKey:
    source_model: type[BaseModel]
    operation: Literal["pick", "omit", "partial", "required", "patch"]
    fields: tuple[str, ...] | None = None
    include: tuple[str, ...] | None = None
    exclude: tuple[str, ...] | None = None
    partial: tuple[str, ...] | None = None
    required: tuple[str, ...] | None = None
    child_models: tuple[tuple[type[BaseModel], "OperationCacheKey"], ...] = ()
    name: str | None = None
```

Config normalisation:

```python
def normalise_fields(fields: Collection[str] | None) -> tuple[str, ...] | None:
    if fields is None:
        return None
    return tuple(sorted(fields))
```

For child config:

```python
tuple(
    sorted(
        (child_model, make_cache_key(child_model, child_config))
        for child_model, child_config in child_models.items()
    ),
    key=lambda item: f"{item[0].__module__}.{item[0].__qualname__}",
)
```

Also cache transformed annotations if needed, but model-level caching may be enough.

---

# 10. Generic-preserver usage

The public operation classes can use `generic-preserver`.

Something like:

```python
T = TypeVar("T", bound=BaseModel)

@generic_preserver
class Pick(Generic[T]):
    def __new__(
        cls,
        *,
        fields: Collection[str] | None = None,
        child_models: dict[type[BaseModel], PickConfig] | None = None,
        name: str | None = None,
    ) -> type[T]:
        source_model = cls[T]
        return create_pick_model(
            source_model,
            fields=fields,
            child_models=child_models,
            name=name,
        )
```

Same for:

```python
Omit[T]
Partial[T]
Required[T]
Patch[T]
```

This gives the syntax:

```python
UserPick = Pick[User](fields={"name"})
```

Rather than:

```python
create_pick_model(User, fields={"name"})
```

I would still expose function APIs too, because they are easier to test and debug:

```python
create_pick_model(User, fields={"name"})
create_omit_model(User, fields={"id"})
create_partial_model(User)
create_required_model(User, fields={"id"})
create_patch_model(User, config=PatchConfig(...))
```

---

# 11. Error classes

Use clear, typed errors:

```python
class PydanticPatchError(Exception):
    pass

class InvalidPatchFieldError(PydanticPatchError):
    pass

class InvalidDiscriminatorError(PydanticPatchError):
    pass

class UnsupportedAnnotationError(PydanticPatchError):
    pass

class ConflictingPatchConfigError(PydanticPatchError):
    pass
```

Example message:

```text
Field 'created_at' cannot be required on UserPatch because it was excluded from the generated payload.
```

---

# 12. Test suite structure

```text
tests/
    conftest.py

    helpers/
        assert_model.py

    pick/
        test_pick_simple.py
        test_pick_recursive.py
        test_pick_discriminated_union.py

    omit/
        test_omit_simple.py
        test_omit_recursive.py
        test_omit_discriminated_union.py

    partial/
        test_partial_simple.py
        test_partial_recursive.py
        test_partial_discriminated_union.py

    required/
        test_required_simple.py
        test_required_recursive.py
        test_required_discriminated_union.py

    patch/
        test_patch_simple.py
        test_patch_recursive.py
        test_patch_discriminated_union.py
        test_patch_operation_order.py
        test_patch_cache.py
        test_patch_validation.py
```

---

# 13. `conftest.py` fixtures

Define all sample models here.

```python
class AuditFields(BaseModel):
    created_at: datetime
    updated_at: datetime


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


class Customer(BaseModel):
    id: int | None = None
    name: str
    address: Address
    billing_address: Address
```

Multiple same child type test:

```python
class Organisation(BaseModel):
    id: int | None = None
    name: str
    primary_address: Address
    postal_address: Address
    branch_addresses: list[Address]
    address_lookup: dict[str, Address]
```

Deep hierarchy:

```python
class BenchmarkMatch(BaseModel):
    id: int | None = None
    category: str
    line_item_name: str
    selected: bool
    match_score: float
    created_at: datetime


class QuoteLineItem(BaseModel):
    id: int | None = None
    description: str
    quantity: float
    unit: str
    benchmark_matches: list[BenchmarkMatch]


class Quote(BaseModel):
    id: int | None = None
    quote_number: str
    line_items: list[QuoteLineItem]
    created_at: datetime
    updated_at: datetime
```

Discriminated union:

```python
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


Pet = Annotated[
    Cat | Dog | Bird,
    Discriminator("kind"),
]


class PetOwner(BaseModel):
    id: int | None = None
    name: str
    pet: Pet
    previous_pets: list[Pet]
```

Expected output models should also be fixtures, not repeated in tests.

Example:

```python
class UserNameEmailPick(BaseModel):
    name: str
    email: str
```

```python
class AddressPartial(BaseModel):
    id: int | None = None
    line_1: str | None = None
    line_2: str | None = None
    suburb: str | None = None
    postcode: str | None = None
```

```python
class OrganisationAddressPatch(BaseModel):
    id: int | None = None
    name: str | None = None
    primary_address: AddressPartial | None = None
    postal_address: AddressPartial | None = None
    branch_addresses: list[AddressPartial] | None = None
    address_lookup: dict[str, AddressPartial] | None = None
```

---

# 14. Model assertion helper

Use JSON schema + field checks.

```python
def assert_model_equivalent(actual: type[BaseModel], expected: type[BaseModel]) -> None:
    actual_schema = actual.model_json_schema()
    expected_schema = expected.model_json_schema()

    diff = DeepDiff(
        expected_schema,
        actual_schema,
        ignore_order=True,
        exclude_regex_paths=[
            r"root\['title'\]",
            r"root\['$defs'\]\['.*'\]\['title'\]",
        ],
    )

    assert diff == {}
```

But JSON schema alone may hide Python type identity issues, so also check annotations:

```python
def assert_field_annotations_equivalent(actual, expected):
    assert actual.model_fields.keys() == expected.model_fields.keys()

    for field_name in expected.model_fields:
        assert actual.model_fields[field_name].annotation == expected.model_fields[field_name].annotation
        assert actual.model_fields[field_name].is_required() == expected.model_fields[field_name].is_required()
```

For generated class cache identity:

```python
assert result_a is result_b
```

For reused child class identity:

```python
assert OrganisationPatch.model_fields["primary_address"].annotation is AddressPatch
assert OrganisationPatch.model_fields["postal_address"].annotation is AddressPatch
```

For list/dict annotations, extract inner types.

---

# 15. Test cases

## Pick simple

```text
Pick User name/email only
Pick User with fields=None keeps all fields
Pick User with empty set creates empty model
Pick unknown field raises InvalidPatchFieldError
Custom name produces expected class name
Repeated same Pick returns same class object
```

## Pick recursive

```text
Pick Organisation fields primary_address/postal_address
Child Address pick keeps only suburb/postcode
Both primary_address and postal_address use same AddressPick class object
List[Address] gets transformed to list[AddressPick]
dict[str, Address] gets transformed to dict[str, AddressPick]
Deep Quote -> QuoteLineItem -> BenchmarkMatch pick works
Unconfigured child model either remains unchanged or receives default pick behaviour depending chosen policy
```

## Pick discriminated union

```text
Pick PetOwner pet only
Cat/Dog/Bird each get transformed via child config
Discriminator field kind is preserved
Discriminator field cannot be excluded from variant
Union remains Annotated[..., Discriminator("kind")]
previous_pets: list[Pet] also receives patched discriminated union
Validation still discriminates cat/dog/bird payloads correctly
```

## Omit simple

```text
Omit User created_at/updated_at
Omit fields=None changes nothing
Omit empty set changes nothing
Omit unknown field raises
Custom name works
Repeated same Omit returns same class object
```

## Omit recursive

```text
Omit Address created_at-style fields from every Address occurrence
Multiple fields of Address type reuse same AddressOmit class
list[Address] and dict[str, Address] transformed
Deep Quote omits match_score from BenchmarkMatch recursively
```

## Omit discriminated union

```text
Omit secret_tracking_code from Cat/Dog/Bird
Discriminator field kind cannot be omitted
PetOwner.pet validates correctly
PetOwner.previous_pets validates correctly
```

## Partial simple

```text
Partial User with no fields makes all fields optional
Partial User fields={"name"} makes only name optional
Partial User fields=set() makes no fields optional
Partial unknown field raises
Optional id remains optional
Required original field becomes optional only when selected
Custom name works
Repeated same Partial returns same class object
```

## Partial recursive

```text
Partial Quote all fields recursively
Quote.line_items optional
QuoteLineItem fields optional
BenchmarkMatch fields optional
Partial Organisation recursively transforms all Address fields
Same AddressPartial object reused across primary_address/postal_address/list/dict
Partial parent only does not necessarily partial child unless recursive=True
```

## Partial discriminated union

```text
Partial PetOwner recursively
Cat/Dog/Bird become partial
kind remains required and not optional
Cat.name/lives optional
Dog.name/bark_volume optional
Bird.name/wing_span optional
Validation without kind fails
Validation with kind and partial body succeeds
```

## Required simple

```text
Required User id makes id required even though original default None
Required User fields=None changes nothing
Required User fields=set() changes nothing
Required unknown field raises
Required already-required field stays required
Custom name works
Repeated same Required returns same class object
```

## Required recursive

```text
Required Quote id
Required QuoteLineItem id recursively
Required BenchmarkMatch id recursively
Address id required everywhere Organisation uses Address
Same AddressRequired class reused
```

## Required discriminated union

```text
Required Cat/Dog/Bird id
kind remains required
pet union validation requires id for selected variant
```

## Patch simple

```text
Patch User include name/email
Patch User exclude created_at/updated_at
Patch User partial name/email
Patch User required id
Patch User include id/name/email + partial name/email + required id
id is required despite original id optional
name/email optional
created_at/updated_at absent
```

## Patch operation order

```text
include then exclude:
include={id,name,created_at}
exclude={created_at}
final={id,name}

partial then required:
partial=None
required={id}
id is required
all other fields optional

required excluded field raises:
include={name}
required={id}
raises because id not in payload

partial excluded field raises:
exclude={email}
partial={email}
raises because email not in final payload
```

## Patch recursive

```text
Quote patch:
Quote include id,line_items
Quote required id
Quote partial line_items

QuoteLineItem include id,quantity,benchmark_matches
QuoteLineItem required id
QuoteLineItem partial quantity,benchmark_matches

BenchmarkMatch include id,selected
BenchmarkMatch required id
BenchmarkMatch partial selected

Expected:
QuotePatch.id required
QuotePatch.line_items optional list[QuoteLineItemPatch]
QuoteLineItemPatch.id required
QuoteLineItemPatch.quantity optional
QuoteLineItemPatch.benchmark_matches optional list[BenchmarkMatchPatch]
BenchmarkMatchPatch.id required
BenchmarkMatchPatch.selected optional
```

## Patch multiple same child model

```text
OrganisationPatch uses AddressPatch for:
primary_address
postal_address
branch_addresses inner type
address_lookup value type

All point to same generated AddressPatch class
AddressPatch itself was only generated once for identical config
```

## Patch discriminated union

```text
PetOwnerPatch includes pet and previous_pets
Cat/Dog/Bird configs are flat in child_models
Each variant transformed independently
Discriminator union rebuilt with patched variants
kind field forced required
kind field cannot be partial
kind field cannot be omitted
Validation works for cat payload
Validation works for dog payload
Validation works for bird payload
Validation fails when kind missing
Validation fails when kind excluded by bad config
```

## Cache tests

```text
Same operation + same model + same config returns same type object
Same operation + same config in different field locations reuses same child model object
Different operation configs return different type objects
Different custom names return different type objects
Same custom name + same config returns same type object
Child model cache hit works inside recursive parent generation
Discriminated union variants reuse cached generated variant classes
```

## Validation tests

```text
Unknown include field raises
Unknown exclude field raises
Unknown partial field raises
Unknown required field raises
Required field not present after include/exclude raises
Partial field not present after include/exclude raises
Discriminator field omitted raises
Discriminator field partial raises
Discriminator field missing from variant raises
Unsupported arbitrary non-Pydantic type remains unchanged
Unsupported union with non-BaseModel variant is preserved or raises depending policy
```

---

# 16. Implementation phases

I’d implement in this order:

```text
1. Core payload builder from BaseModel
2. Field validation helpers
3. Pick operation without recursion
4. Omit operation without recursion
5. Partial operation without recursion
6. Required operation without recursion
7. Shared model cache
8. Type traversal for BaseModel/list/dict/union/Annotated
9. Recursive support for each independent operation
10. PatchConfig and patch aggregation
11. Discriminated union preservation
12. Full cache identity tests
13. Validation/error polish
```

The highest-risk parts are:

```text
1. preserving Annotated discriminated union metadata
2. required overriding partial
3. cache keys for recursive configs
4. extracting inner types from list/dict/union robustly
5. preserving Pydantic field metadata/defaults
```

The main design decision I’d lock in now is:

```text
PatchConfig.partial=None means “make all final payload fields optional”
PatchConfig.partial=set() means “make no fields optional”
PatchConfig.required always runs last
```

That gives patch ergonomics while still supporting strict/non-partial pick-style use cases through the independent operations.
