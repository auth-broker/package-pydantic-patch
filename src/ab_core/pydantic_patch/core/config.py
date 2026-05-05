"""Shared config helpers."""

from collections.abc import Collection

type FieldSet = frozenset[str] | None


def normalise_fields(fields: Collection[str] | None) -> FieldSet:
    """Normalise user-provided field collections into immutable field sets."""
    if fields is None:
        return None
    return frozenset(fields)
