"""Typing helpers for recursive model transformation."""



import types as py_types
from functools import reduce
from operator import or_
from typing import Annotated, Any, get_args, get_origin

from pydantic import BaseModel, Discriminator


def is_basemodel_type(annotation: Any) -> bool:
    """Return whether an annotation is a BaseModel subclass."""
    return isinstance(annotation, type) and issubclass(annotation, BaseModel)


def is_union_origin(origin: Any) -> bool:
    """Return whether an origin represents a typing union."""
    return origin is py_types.UnionType or str(origin) == "typing.Union"


def rebuild_union(args: tuple[Any, ...]) -> Any:
    """Rebuild a PEP 604 union from args."""
    if not args:
        raise ValueError("Cannot rebuild a union from no args.")
    return reduce(or_, args)


def extract_discriminator(metadata: tuple[Any, ...]) -> Discriminator | None:
    """Extract a pydantic.Discriminator from Annotated metadata."""
    for item in metadata:
        if isinstance(item, Discriminator):
            return item
    return None


def get_discriminator_key(discriminator: Discriminator) -> str:
    """Return the discriminator key from a pydantic.Discriminator."""
    key = discriminator.discriminator
    if not isinstance(key, str):
        raise TypeError("Only string discriminator keys are supported.")
    return key


def is_annotated(annotation: Any) -> bool:
    return get_origin(annotation) is Annotated


def split_annotated(annotation: Any) -> tuple[Any, tuple[Any, ...]]:
    args = get_args(annotation)
    return args[0], args[1:]


def rebuild_annotated(inner: Any, metadata: tuple[Any, ...]) -> Any:
    return Annotated[inner, *metadata]


def union_args(annotation: Any) -> tuple[Any, ...]:
    origin = get_origin(annotation)
    if is_union_origin(origin):
        return get_args(annotation)
    return ()
