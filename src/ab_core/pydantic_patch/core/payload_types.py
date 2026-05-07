"""Type aliases used to build ``pydantic.create_model`` payloads."""

from typing import Any

type CreateModelField = tuple[Any, object]
type CreateModelPayload = dict[str, CreateModelField]


__all__ = [
    "CreateModelField",
    "CreateModelPayload",
]
