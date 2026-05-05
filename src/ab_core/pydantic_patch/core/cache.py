"""Cache-key helpers for generated pydantic_patch models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

OperationName = Literal["pick", "omit", "partial", "required", "patch"]


@dataclass(frozen=True)
class OperationCacheKey:
    """Hashable key describing a generated model transformation."""

    source_model: type[BaseModel]
    operation: OperationName
    fields: tuple[str, ...] | None = None
    include: tuple[str, ...] | None = None
    exclude: tuple[str, ...] | None = None
    partial: tuple[str, ...] | None = None
    required: tuple[str, ...] | None = None
    child_models: tuple[tuple[type[BaseModel], "OperationCacheKey"], ...] = ()
    name: str | None = None


def normalise_field_key(fields: frozenset[str] | None) -> tuple[str, ...] | None:
    if fields is None:
        return None
    return tuple(sorted(fields))


def sort_child_keys(
    child_keys: Mapping[type[BaseModel], OperationCacheKey],
) -> tuple[tuple[type[BaseModel], OperationCacheKey], ...]:
    return tuple(
        sorted(
            child_keys.items(),
            key=lambda item: f"{item[0].__module__}.{item[0].__qualname__}",
        )
    )
