"""Shared config helpers."""

from __future__ import annotations

from collections.abc import Collection
from typing import TypeAlias

FieldSet: TypeAlias = frozenset[str] | None


def normalise_fields(fields: Collection[str] | None) -> FieldSet:
    """Normalise user-provided field collections into immutable field sets."""
    if fields is None:
        return None
    return frozenset(fields)
