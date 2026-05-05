Great, I think you've got the right idea.


The independent operations that we support are:

pick, omit, partial, required.



We can independently perform these through 

Pick[SomeModel](fields=["some_field"]) # SomeModelPick
Omit[SomeModel](fields=["some_field"]) # SomeModelOmit
Partial[SomeModel](fields=["some_field"]) # SomeModelPartial
Required[SomeModel](fields=["some_field"]) # SomeModelRequired

You should also support passing in a new class name into this constructor, but you can use the default based on the model that was passed in.

There is a package called `generic-preserver` which is usually pretty good at readin the type args, and I suggest that you use it here.

https://github.com/mattcoulter7/generic-preserver

# generic-preserver

<img src="https://github.com/mattcoulter7/generic-preserver/raw/master/assets/logo.webp" alt="logo" width="500">

**Extracting Generic Type References in Python**

## Introduction

In Python, generic types are a powerful feature for writing reusable and type-safe code. However, one limitation is that generic type arguments are typically not preserved at runtime, making it challenging to access or utilize these types dynamically. **`generic-preserver`** is a Python package that overcomes this limitation by capturing and preserving generic type arguments, allowing you to access them at runtime.

This package is particularly useful when you need to perform operations based on the specific types used in your generic classes, such as serialization, deserialization, or dynamic type checking.

## Features

- **Preserve Generic Types at Runtime**: Capture and retain generic type arguments for classes and instances.
- **Runtime Access to Type Parameters**: Easily access the type parameters passed to generic classes from their instances.
- **Supports Inheritance and Nested Generics**: Works seamlessly with class hierarchies and nested generic types.
- **Simple and Intuitive API**: Use either a metaclass or a decorator to enable functionality with minimal code changes.
- **Python 3.9+ Support**: Leverages modern Python features for type hinting and annotations.

## Installation

Install `generic-preserver` via pip:

```bash
pip install generic-preserver
```

Or install using Poetry:

```bash
poetry add generic-preserver
```

## Requirements

- Python 3.9 or higher

## Usage

### Using the `GenericMeta` Metaclass

To enable capturing generic type arguments, use the `GenericMeta` metaclass in your base class definition.

```python
from typing import TypeVar, Generic
from generic_preserver.metaclass import GenericMeta

# Define type variables
A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")

# Example classes to use as type arguments
class ExampleA:
    pass

class ExampleB:
    pass

class ExampleC:
    pass

# Base class with GenericMeta metaclass
class Parent(Generic[A, B], metaclass=GenericMeta):
    pass

# Child classes specifying some generic type arguments
class Child(Parent[ExampleA, B], Generic[B, C]):
    pass

class GrandChild(Child[ExampleB, C], Generic[C]):
    pass

# Create an instance of the generic class with type arguments
instance = GrandChild[ExampleC]()

# Access the preserved generic type arguments
print(instance[A])  # Output: <class '__main__.ExampleA'>
print(instance[B])  # Output: <class '__main__.ExampleB'>
print(instance[C])  # Output: <class '__main__.ExampleC'>

# View the internal generic map
print(instance.__generic_map__)
# Output:
# {
#     ~A: <class '__main__.ExampleA'>,
#     ~B: <class '__main__.ExampleB'>,
#     ~C: <class '__main__.ExampleC'>,
# }
```

### Using the `@generic_preserver` Decorator

Alternatively, use the `@generic_preserver` decorator to enable capturing generic arguments without explicitly specifying the metaclass.

```python
from typing import TypeVar, Generic
from generic_preserver.wrapper import generic_preserver
from generic_preserver.utils import canonical_key

# Define type variables
A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")

# Example classes to use as type arguments
class ExampleA:
    pass

class ExampleB:
    pass

class ExampleC:
    pass

# Use the decorator to enable generic preservation
@generic_preserver
class Parent(Generic[A, B]):
    pass

# Child classes specifying some generic type arguments
class Child(Parent[ExampleA, B], Generic[B, C]):
    pass

class GrandChild(Child[ExampleB, C], Generic[C]):
    pass

# Create an instance of the generic class with type arguments
instance = GrandChild[ExampleC]()

# Access the preserved generic type arguments
print(instance[A])  # Output: <class '__main__.ExampleA'>
print(instance[B])  # Output: <class '__main__.ExampleB'>
print(instance[C])  # Output: <class '__main__.ExampleC'>

# View the internal generic map
print(instance.__generic_map__)
# Output:
# {
#     ~A: <class '__main__.ExampleA'>,
#     ~B: <class '__main__.ExampleB'>,
#     ~C: <class '__main__.ExampleC'>,
# }
```

### Accessing Type Variables

You can access the type arguments by indexing the instance with the corresponding `TypeVar`.

```python
print(instance[A])  # Output: <class '__main__.ExampleA'>
```

If you attempt to access a type variable that was not defined or is not in the generic map, a `KeyError` will be raised.

```python
D = TypeVar("D")
try:
    print(instance[D])
except KeyError as e:
    print(e)  # Output: No generic type found for generic arg ~D
```

### Accessing Multiple Type Variables

You can retrieve multiple type variables at once by passing an iterable of `TypeVar` instances.

```python
types = instance[A, B, C]
print(types)
# Output: (<class '__main__.ExampleA'>, <class '__main__.ExampleB'>, <class '__main__.ExampleC'>)
```

## How It Works

The `generic-preserver` package uses a custom metaclass `GenericMeta` to intercept class creation and capture generic type arguments when a generic class is subscripted (e.g., `MyClass[int, str]`). Here's a brief overview:

- **Metaclass (`GenericMeta`)**: Overrides the `__getitem__` method to capture the type arguments and store them in a `__generic_map__`.
- **Class Wrapper**: Creates a wrapper class that inherits from the original class and includes the `__generic_map__`.
- **Instance Access**: Allows instances to access the type arguments via the `__getitem__` method.
- **Decorator (`@generic_preserver`)**: Provides a convenient way to apply `GenericMeta` without altering the class definition directly.

By preserving the generic type arguments in `__generic_map__`, you can access them at runtime, enabling more dynamic and type-aware programming patterns.

## Testing

The package includes a test suite to verify its functionality. To run the tests, first install the development dependencies:

```bash
poetry install --with dev
```

Then, run the tests using `pytest`:

```bash
pytest
```

An example test case is provided in `tests/test_wrapper.py`:

```python
def test_template():
    A = TypeVar("A")
    B = TypeVar("B")
    C = TypeVar("C")

    class ExampleA: pass
    class ExampleB: pass
    class ExampleC: pass

    @generic_preserver
    class Parent(Generic[A, B]): pass

    class Child(Parent[ExampleA, B], Generic[B, C]): pass

    class GrandChild(Child[ExampleB, C], Generic[C]): pass

    instance = GrandChild[ExampleC]()

    assert instance[A] is ExampleA
    assert instance[B] is ExampleB
    assert instance[C] is ExampleC

    D = TypeVar("D")
    with pytest.raises(KeyError):
        instance[D]
```

## Limitations

- **Python Version**: Requires Python 3.9 or higher due to the use of internal structures from the `typing` module.
- **Compatibility**: May not be compatible with other metaclass-based libraries or complex metaclass hierarchies.
- **TypeVar Constraints**: Does not enforce `TypeVar` constraints or bounds at runtime; it only captures the types provided.

## Contributing

Contributions are welcome! If you find a bug or have an idea for a new feature, please open an issue or submit a pull request.

To contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/my-feature`).
3. Commit your changes (`git commit -am 'Add my feature'`).
4. Push to your branch (`git push origin feature/my-feature`).
5. Open a Pull Request.

Please ensure that your code passes all tests and follows the existing coding style.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

- Inspired by the need to access and utilize generic type parameters at runtime in Python applications.
- Special thanks to the Python community for their contributions and support.

To learn more about how I came up with this solution, please read my blog post: [Extracting Generic Type References in Python](https://mica-twig-c4c.notion.site/Extracting-Generic-Type-References-in-Python-14c04289061f802b851ae564e80c251e)

## Contact

For questions, suggestions, or feedback, please contact:

Matthew Coulter  
Email: [mattcoul7@gmail.com](mailto:mattcoul7@gmail.com)

---

Thank you for using `generic-preserver`! If you find this package helpful, consider giving it a star on GitHub.


We will support anything that inherits from pydantic.BaseModel, as well as Discriminated Unions defined as

Annotated[SomeModel1 | SomeModel2, pydantic.Discriminator(key="some_key")]

The modules will be structures as 

src/ab_core/pydantic_patch/pick
src/ab_core/pydantic_patch/partial
src/ab_core/pydantic_patch/omit
src/ab_core/pydantic_patch/required

Each of these should follow a consistent module structure, then later on, we'll support 

src/ab_core/pydantic_patch/patch

which handles aggregating al of those modules together.

src/ab_core/pydantic_patch/patch/config.py

Will define PatchConfig, which has
            include={...},
            exclude={...},
            partial={...},
            required={...},

as well as child_models={
    Cat: PatchConfig(...),
    Dog: PatchConfig(...),
    Bird: PatchConfig(...),
}

so PatchConfig is a recursive model, make sure you do whatever model_rebuild is necessary, as patch config itself is a base model.

I've done a lot of work with pydantic schemas and handling type interpretation in the past.

Here is a bunch of reference code which you can use as reference when building this package for handling pydantic schemas and determining the discriminated union.

"""Reshape environment-derived payloads to match Pydantic core schemas."""

import json
from typing import Any

from pydantic_core.core_schema import CoreSchema


def _clean_field(
    obj: dict[str, Any],
    field_path: list[str] | str,
    *,
    key_delim: str = "_",
) -> None:
    """Remove the branch specified by `field_path`.

    After deleting the leaf,
    recursively delete any parent keys that become empty dictionaries.

    Parameters
    ----------
    obj : dict
        The dictionary to clean (modified in place).
    field_path : list[str] | str
        Either an iterable of keys, e.g. ["a", "b", "c"],
        or a single string with keys joined by `key_delim`, e.g. "a_b_c".
    key_delim : str, default "_"
        Delimiter to split `field_path` when it is given as a string.

    Examples
    --------
    >>> data = {"a": {"b": 1}, "c": {}}
    >>> _clean_field(data, ["a", "b"])
    >>> data
    {}

    >>> data = {"a": {"b": 1, "c": 2}}
    >>> _clean_field(data, ["a", "b"])
    >>> data
    {'a': {'c': 2}}

    """
    # Normalise the path into a list of keys
    if isinstance(field_path, str):
        path: list[str] = field_path.split(key_delim)
    else:
        path = list(field_path)

    if not path:  # safety-guard: empty path means nothing to do
        return

    key = path[0]

    # Key not present → nothing to delete
    if key not in obj:
        return

    # ────────────────────────
    # 1) Leaf level: delete it
    # ────────────────────────
    if len(path) == 1:
        del obj[key]

    # ────────────────────────────────────────────
    # 2) Recurse further, then prune if now empty
    # ────────────────────────────────────────────
    else:
        child = obj[key]
        if isinstance(child, dict):
            _clean_field(child, path[1:], key_delim=key_delim)
            if not child:  # became empty → delete this branch
                del obj[key]


def _align_field(
    obj: dict[str, Any],
    field_name: str,
    *,
    key_delim: str = "_",
) -> None:
    # scenario 1, the whole key was defined in obj
    if field_name in obj:
        return None

    # scenario 2, each part of the key was defined in obj
    # validate that all parts exist in the obj first, before extracting anything
    field_path = field_name.split(key_delim)
    next_value = obj
    while field_path:
        next_part = field_path.pop(0)
        next_value = next_value.get(next_part)
        if not next_value:
            return None

    # if we made it here, there was a value nested by the broke up field path
    # so we need to perform the cleaning. Since it is nested, there may be
    # other values under the same sub branch, so need to ensuure we don't
    # accidentally delete some overlapping data.
    _clean_field(obj, field_name.split(key_delim))
    obj[field_name] = next_value


def _normalise_indexed_list(obj: dict[str, Any]) -> list[Any]:
    indexes = sorted(int(key) for key in obj)

    if indexes != list(range(len(indexes))):
        raise ValueError(f"Sparse list indexes are not supported. Expected contiguous indexes from 0, got {indexes}.")

    return [obj[str(index)] for index in indexes]


def pydanticize_model_fields(
    obj: dict[str, Any],
    schema: CoreSchema,
    *,
    definition_map: dict | None = None,
) -> dict[str, Any]:
    """Transform all model fields according to their child schemas."""
    fields = schema["fields"]
    for field_name, field_schema in fields.items():
        _align_field(obj, field_name)

        if field_name not in obj:
            continue

        obj[field_name] = pydanticize_data(
            obj.pop(field_name),
            field_schema,
            definition_map=definition_map,
        )

    return obj


def pydanticize_model_field(
    obj: dict[str, Any] | Any,
    schema: CoreSchema,
    *,
    definition_map: dict | None = None,
) -> dict[str, Any] | Any:
    """Transform a single model field using its nested schema."""
    inner_schema = schema.get("schema")

    if obj is not None and inner_schema is not None:
        return pydanticize_data(
            obj,
            inner_schema,
            definition_map=definition_map,
        )

    return obj


def pydanticize_list(
    obj: list[Any] | dict[str, Any] | str | Any,
    schema: CoreSchema,
    *,
    definition_map: dict | None = None,
) -> list[Any]:
    """Normalize list-shaped input and transform each list item."""
    if isinstance(obj, str):
        obj = json.loads(obj)

    if isinstance(obj, dict):
        obj = _normalise_indexed_list(obj)

    item_schema = schema["items_schema"]

    return [
        pydanticize_data(
            item,
            item_schema,
            definition_map=definition_map,
        )
        for item in obj
    ]


def pydanticize_tagged_union(
    obj: dict[str, Any],
    schema: CoreSchema,
    *,
    definition_map: dict | None = None,
) -> dict[str, Any]:
    """Flatten tagged-union payloads into the selected branch schema."""
    discriminator = schema["discriminator"]
    discriminator_choice = obj[discriminator]
    if not isinstance(discriminator_choice, str):
        raise TypeError(
            f"Invalid Discriminator Choice. Expected {repr(str)}, found {repr(type(discriminator_choice))}."
        )

    # the name of the field on obj which points to values
    discriminator_values_field = discriminator_choice.lower()

    # apply correction to field for discriminator choice
    _align_field(obj, discriminator_values_field)

    # extract the values and flatten, for pydantic
    if discriminator_values_field in obj:
        discriminator_values = obj.pop(discriminator_choice.lower())
        if not isinstance(discriminator_values, dict):
            raise TypeError(
                f"Invalid Discriminator Body. Expected {repr(dict)}, found {repr(type(discriminator_values))}."
            )
        discriminator_choice_schema = schema["choices"][discriminator_choice]
        pydanticized_body = pydanticize_data(
            discriminator_values,
            discriminator_choice_schema,
            definition_map=definition_map,
        )
        return obj | pydanticized_body

    return obj


def pydanticize_definitions(
    obj: dict[str, Any],
    schema: CoreSchema,
    *,
    definition_map: dict | None = None,
) -> dict[str, Any]:
    """Build a definition lookup map and continue with the root schema."""
    if definition_map is None:
        definition_map = {}
    definitions = schema["definitions"]
    for definition in definitions:
        definition_map[definition["ref"]] = definition

    return pydanticize_data(
        obj,
        schema["schema"],
        definition_map=definition_map,
    )


def pydanticize_definition_ref(
    obj: dict[str, Any],
    schema: CoreSchema,
    *,
    definition_map: dict | None = None,
) -> dict[str, Any]:
    """Resolve a definition-ref schema and transform data against it."""
    schema_ref = schema["schema_ref"]
    schema = definition_map[schema_ref]
    return pydanticize_data(
        obj,
        schema,
        definition_map=definition_map,
    )


def pydanticize_child_schema(
    obj: dict[str, Any],
    schema: CoreSchema,
    *,
    definition_map: dict | None = None,
) -> dict[str, Any]:
    """Transform data using a nested `schema` member."""
    field_schema = schema["schema"]
    return pydanticize_data(
        obj,
        field_schema,
        definition_map=definition_map,
    )


def pydanticize_data(
    obj: list[Any] | dict[str, Any] | str | Any,
    core_schema: CoreSchema,
    *,
    definition_map: dict | None = None,
) -> dict[str, Any]:
    """Dispatch transformation based on core schema type metadata."""
    if definition_map is None:
        definition_map = {}

    if "type" in core_schema:
        type = core_schema["type"]

        if type == "model-field":
            return pydanticize_model_field(
                obj,
                core_schema,
                definition_map=definition_map,
            )
        if type == "model-fields":
            return pydanticize_model_fields(
                obj,
                core_schema,
                definition_map=definition_map,
            )
        if type == "list":
            return pydanticize_list(
                obj,
                core_schema,
                definition_map=definition_map,
            )
        if type == "tagged-union":
            return pydanticize_tagged_union(
                obj,
                core_schema,
                definition_map=definition_map,
            )
        if type == "definition-ref":
            return pydanticize_definition_ref(
                obj,
                core_schema,
                definition_map=definition_map,
            )
        if type == "definitions":
            return pydanticize_definitions(
                obj,
                core_schema,
                definition_map=definition_map,
            )

    if "schema" in core_schema:
        return pydanticize_child_schema(
            obj,
            core_schema,
            definition_map=definition_map,
        )

    # already pydanticised
    return obj

"""Base loader abstractions."""

from abc import ABC, abstractmethod
from copy import deepcopy
from functools import cached_property
from typing import (
    Any,
    TypeVar,
)

from generic_preserver.wrapper import generic_preserver
from generic_preserver.utils import canonical_key
from pydantic import BaseModel, Discriminator, TypeAdapter, model_validator
from pydantic_core.core_schema import CoreSchema

from ab_core.dependency.pydanticize import cached_type_adapter, pydanticize_data, pydanticize_type
from ab_core.dependency.utils import extract_target_types, type_name_intersection

T = TypeVar("T")


@generic_preserver
class LoaderBase[T](BaseModel, ABC):
    """Base class for all loaders."""

    default_value: T | None = None

    def __call__(
        self,
    ) -> T:
        """Load and return the data of the specified type."""
        return self.load()

    @abstractmethod
    def load_raw(
        self,
    ) -> Any:
        """Load the raw data before any processing."""
        ...

    def load(
        self,
    ) -> T:
        """Load and return the data of the specified type, applying type plugins."""
        try:
            data = self.load_raw()
        except Exception as e:
            raise RuntimeError(f"Error loading `{repr(self.type)}`: {e}") from e
        if not data and self.default_value:
            return self.default_value
        data_restructured = pydanticize_data(deepcopy(data), self.core_schema)
        return self.type_adaptor.validate_python(data_restructured)

    @cached_property
    def native_type(self) -> type[T]:
        """The native type T, without any type plugins applied."""
        return self[T]

    @cached_property
    def type(self) -> type[T]:
        """The type T, with any type plugins applied."""
        return pydanticize_type(self.native_type)

    @cached_property
    def type_adaptor(self) -> TypeAdapter:
        """Generates a TypeAdapter for the type, applying any type plugins."""
        return cached_type_adapter(self.type)

    @cached_property
    def core_schema(self) -> CoreSchema:
        """Generates the core schema for the type, applying any type plugins."""
        return self.type_adaptor.core_schema

    @classmethod
    def supports(cls, obj: Any) -> bool:
        """Check if the loader supports the given type."""
        try:
            pydanticize_type(obj)
            return True
        except TypeError:
            return False


class ObjectLoaderBase(LoaderBase[T], ABC):
    """Base class for loaders that handle Pydantic BaseModel objects."""

    default_discriminator_value: Any = None
    discriminator_key: str | None = None

    @model_validator(mode="after")
    def validate_type(self):
        """Ensure that the type is a BaseModel or a Union of BaseModels."""
        if len(self.types) == 0:
            raise Exception(f"Unable to find any BaseModel types in {repr(self.type)}")
        if self.discriminator:
            self.discriminator_key = self.discriminator.discriminator
        return self

    @property
    def alias_name(self) -> str:
        """Generates an alias name for the loader based on the intersection of type names."""
        assumed_name = type_name_intersection(self.types)
        if not assumed_name:
            raise ValueError(
                f"Unable to create an alias for types `{repr(self.types)}`."
                " Ensure there is a naming overlap between each of the types."
            )
        return assumed_name

    @cached_property
    def types(self) -> list[type[BaseModel]]:
        """Extracts all BaseModel types from the provided type."""
        return list(extract_target_types(self.type, BaseModel))

    @cached_property
    def discriminator(self) -> Discriminator | None:
        """Extracts the Discriminator if one exists in the provided type."""
        try:
            return next(extract_target_types(self.type, Discriminator))
        except StopIteration:
            return None

    @cached_property
    def discriminator_choices(self) -> list[str] | None:
        """Extracts the discriminator choices if a discriminator is defined."""
        if not self.discriminator:
            return None
        return [_type.model_fields[self.discriminator_key].default for _type in self.types]

    def discriminate_type(
        self,
    ) -> type[T]:
        """Determine the specific type to use based on the discriminator value."""
        if self.discriminator is None:
            return self.type

        discriminator_value = self.load_raw()[self.discriminator_key]
        return self.type_adaptor.core_schema["choices"][discriminator_value]["schema"]["schema"]["cls"]

Cool I think you have full context of the goal here. What I want you to do, is come up with a detailed implementation plan (with code references of how you want to go about implement it), include every single detail, don't scuff out and don't half ass it. This is a programming level feature, so needs to be handled with careful precision where necessary.

pLease recall our previous conversiation when planning this out as well, in terms of supporting the aggregation for in the patch module, it means that each operation module should support manipulating a pydantic.create_model(...) payload as the input and output combined with the operation's list of fields.

Think about how you will order the operations in the patch module to ensure that all operations are properly considered.

Ensure you address the model caching based on the original model + operations + operation configs as the cache key. Probably cache via func tools, whilst ensuring the caching functionis only a wrapper of the main function.

Lastly, but most importantly, before we code the entire solution, I need you to come up with a full list of test cases for each of the operations, including simple and complex, with the recursive structure. Which reminds me that the child_models configurations even for each operation itself probably needs to exist, not just the list of fields, so we can properly do a single operation with a parent child type of model recursively. SO yeah test the simple, complex cases, even ones where a model has multiple fields of the same type at dfifferent levels of hierarchies, and they all end up with the same pointer type object because we didn''t need to inefficiently compute the manipulated model multiple times.

In the tests, it's important all these sample models are defined in conftest as a fixture, and the expected output models for each operation. It should all be in fixtures, and all each test file needs to do is run the via parametrize, get the result. There should be a helper for checking that the computed model is the same as the expected model, probably through the pydantic schema json with a DeepDiff, or perhaps there is a better way.

Alright, lets do this, do a full write up of this package, and write the full test suite, then we will start implementing once we've reviewed all of that together