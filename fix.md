`ClassVar` here is almost certainly **not one of your unresolved app forward refs**.

What’s happening:

Your resolver calls:

```python
get_type_hints(
    model,
    globalns=globalns,
    localns=localns,
    include_extras=True,
)
```

But your `build_type_hints_namespaces()` builds `globalns` from:

```python
module_globals + imported sibling BaseModel classes
```

That works for your app models like `FencingQuoteLineItem`, `LineItemComparison`, etc. Your model package does expose those models in `__init__.py`, so the sibling model resolution idea is sound. 

The issue is that `get_type_hints()` is also seeing annotations that reference standard typing names such as `ClassVar`. That can come from inherited `BaseModel` / `SQLModel` internals or model annotations after postponed evaluation. Since you passed an explicit `globalns`, Python no longer has the right typing namespace unless you include it yourself.

So this:

```python
NameError("name 'ClassVar' is not defined")
```

means:

> “Your resolver namespace is missing `typing.ClassVar`.”

It does **not** mean:

> “The user forgot to manually bind circular references again.”

Your current error handling catches every `NameError` and wraps it as `ForwardReferencesNotSupported`, but `ClassVar` is a false positive. The package already has logic for auto-resolving imported sibling model classes in `build_model_namespace()` / `build_type_hints_namespaces()`, but that namespace needs to include standard typing names too. 

The fix should be in `build_type_hints_namespaces()`:

```python
# src/ab_core/pydantic_patch/core/forward_references.py

import sys
import typing
from textwrap import dedent
from typing import ForwardRef, Literal, get_args, get_origin

from pydantic import BaseModel
```

Then update:

```python
def build_type_hints_namespaces(
    model: type[BaseModel],
) -> tuple[dict[str, object], dict[str, object]]:
    """Return globalns/localns for resolving a model's annotations."""
    module = sys.modules.get(model.__module__)
    module_globals: dict[str, object] = {}

    if module is not None:
        module_globals.update(vars(module))

    model_namespace = build_model_namespace(model)
    typing_namespace = vars(typing)

    globalns = {
        **typing_namespace,
        **module_globals,
        **model_namespace,
    }
    localns = {
        **typing_namespace,
        **model_namespace,
        model.__name__: model,
    }

    return globalns, localns
```

This keeps your intended priority:

1. standard typing names available by default, e.g. `ClassVar`, `Annotated`, `Literal`, `Union`
2. model module globals override typing if needed
3. imported sibling models override unresolved string refs like `"LineItemComparison"` / `"FencingQuoteLineItem"`

I’d also consider adjusting your error path so it doesn’t blindly report every `NameError` as a forward-reference problem. For debugging, this is useful:

```python
except NameError as error:
    unresolved_name = getattr(error, "name", None)

    if unresolved_name in vars(typing):
        raise RuntimeError(
            f"Internal pydantic-patch namespace error: missing typing symbol {unresolved_name!r}."
        ) from error

    raise ForwardReferencesNotSupported(...)
```

But once `vars(typing)` is included, you probably won’t hit this for `ClassVar`.

One more thing: this annotation in your actual model is still worth changing:

```python
parent: "FencingQuoteLineItem | None" = Relationship(...)
```

to:

```python
parent: "FencingQuoteLineItem" = Relationship(...)
```

Your own README notes that SQLAlchemy relationship strings should be class names like `"Project"`, not union strings like `"Project | None"`, because SQLAlchemy can resolve the mapped class name but not a union expression as a relationship target. 

So: **`ClassVar` = namespace bug in the resolver.**
**`"FencingQuoteLineItem | None"` = separate SQLAlchemy relationship annotation cleanup.**


The resolver should not do:

```python
custom_globalns = module_globals + model_namespace
get_type_hints(model, globalns=custom_globalns, localns=custom_localns)
```

because the moment you pass explicit namespaces, you take responsibility for all the weird default `get_type_hints()` behaviour: class MRO handling, reversed class lookup order, builtins, imported globals, inherited annotations, `ClassVar`, etc.

Instead, the better implementation is:

> Recreate the **same namespace basis that `get_type_hints()` would have used by default**, then add only your sibling model namespace on top.

For classes, the relevant default behaviour is:

```python
base_globals = getattr(sys.modules.get(base.__module__, None), "__dict__", {})
base_locals = dict(vars(base))

# Then, when both globalns/localns are None:
base_globals, base_locals = base_locals, base_globals
```

That reversal is the important bit. It is weird, but intentional.

So I’d stop having `build_type_hints_namespaces(model)` return one pair for the entire class, because `get_type_hints()` actually resolves annotations **per base class in the MRO**.

The clean fix is to introduce your own class resolver that mirrors `typing.get_type_hints()` for classes, but augments the default locals/globals with sibling models.

Something like this.

```python
# src/ab_core/pydantic_patch/core/type_hints.py

import sys
import types
from typing import ForwardRef, get_type_hints
from typing import _eval_type  # pyright: ignore[reportPrivateUsage]  # noqa: PLC2701
from typing import _strip_annotations  # pyright: ignore[reportPrivateUsage]  # noqa: PLC2701

from pydantic import BaseModel

from ab_core.pydantic_patch.core.errors import ForwardReferencesNotSupported
from ab_core.pydantic_patch.core.forward_references import (
    build_forward_ref_error_message,
    build_model_namespace,
)
```

```python
def get_resolved_type_hints(model: type[BaseModel]) -> dict[str, object]:
    """Resolve model type hints and raise custom errors on truly unresolved refs."""
    try:
        return get_augmented_class_type_hints(
            model,
            include_extras=True,
        )
    except NameError as error:
        raise ForwardReferencesNotSupported(
            build_forward_ref_error_message(
                model=model,
                unresolved_fields=list(getattr(model, "__annotations__", {})),
            )
        ) from error
```

```python
def get_augmented_class_type_hints(
    cls: type[BaseModel],
    *,
    include_extras: bool,
) -> dict[str, object]:
    """Resolve class type hints using Python's default class behaviour plus sibling models.

    This intentionally mirrors the class branch of typing.get_type_hints(),
    but extends the namespace with imported sibling BaseModel / SQLModel classes.
    """
    hints: dict[str, object] = {}
    model_namespace = build_model_namespace(cls)

    for base in reversed(cls.__mro__):
        base_globals = getattr(sys.modules.get(base.__module__, None), "__dict__", {})
        annotations = base.__dict__.get("__annotations__", {})

        if isinstance(annotations, types.GetSetDescriptorType):
            annotations = {}

        base_locals = dict(vars(base))

        # Match typing.get_type_hints() class behaviour when globalns/localns
        # are not passed. This reversal is required for backwards compatibility.
        eval_globals = base_locals
        eval_locals = {
            **base_globals,
            **model_namespace,
            cls.__name__: cls,
            base.__name__: base,
        }

        type_params = getattr(base, "__type_params__", ())

        for name, value in annotations.items():
            if value is None:
                value = type(None)

            if isinstance(value, str):
                value = ForwardRef(
                    value,
                    is_argument=False,
                    is_class=True,
                )

            hints[name] = _eval_type(
                value,
                eval_globals,
                eval_locals,
                type_params,
            )

    if include_extras:
        return hints

    return {key: _strip_annotations(value) for key, value in hints.items()}
```

That gives you the “single shot” behaviour you’re describing:

```text
for each base class:
    use the same globals/locals Python would normally use
    add sibling model refs into the lookup path
    evaluate once
```

This is better than my previous fallback suggestion because it does **not** resolve once, fail, then retry. It directly resolves with an augmented version of the default environment.

One important ordering detail: because `get_type_hints()` says “for classes, the search order is globals first then locals”, but internally reverses `base_globals` / `base_locals`, the actual `_eval_type()` call gets:

```python
_eval_type(value, base_locals, base_globals, ...)
```

So if we want sibling models to behave like extra module globals, they should go into the second dict after the reversal:

```python
eval_locals = {
    **base_globals,
    **model_namespace,
}
```

That means normal class locals still have their normal role, and missing module-level forward refs can be filled by `model_namespace`.

I would also rename your existing namespace helper. This function:

```python
build_type_hints_namespaces(model)
```

is now a bit misleading because there is no single correct namespace pair for a class MRO. The package already builds a sibling model namespace by scanning imported models in the package/module tree, which is the useful bit to keep. 

So I’d keep:

```python
build_model_namespace(model)
```

and delete or stop using:

```python
build_type_hints_namespaces(model)
```

Then computed fields still need function-style resolution. For this part:

```python
resolved_annotations = get_type_hints(
    getter,
    globalns=globalns,
    localns=localns,
    include_extras=True,
)
```

don’t reuse the class resolver. Instead, use the getter’s default globals and add sibling models only to locals:

```python
def get_resolved_computed_field_return_annotation(
    model: type[BaseModel],
    computed_field_info: ComputedFieldInfo,
) -> Any:
    if computed_field_info.return_type is not PydanticUndefined:
        return computed_field_info.return_type

    getter = get_computed_field_getter(computed_field_info)

    globalns = getattr(getter, "__globals__", {})
    localns = {
        **globalns,
        **build_model_namespace(model),
        model.__name__: model,
    }

    resolved_annotations = get_type_hints(
        getter,
        globalns=globalns,
        localns=localns,
        include_extras=True,
    )

    return resolved_annotations.get("return", Any)
```

That avoids the same fragility for computed fields.

So the design becomes:

```text
Model class annotations:
    custom class resolver that mirrors typing.get_type_hints class branch
    + sibling model namespace

Computed field getter return annotations:
    normal function get_type_hints()
    + sibling model namespace in localns
```

That matches the intent in your README: automatically resolve forward references among already imported sibling model classes, without making users manually patch modules. 


