from typing import Any

type CreateModelField = tuple[Any, object]
type CreateModelPayload = dict[str, CreateModelField]


__all__ = [
    "CreateModelField",
    "CreateModelPayload",
]
